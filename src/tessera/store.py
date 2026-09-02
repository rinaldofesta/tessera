"""Durable folder-per-run storage for Tessera evaluations.

One run is one directory under ``<home>/runs/<id>/`` holding ``run.json`` (state),
``report.json``, ``receipt.json``, ``report.md`` and ``log.eval``. The bundled examples
(``first-contact``, ``gpt-4o``) are the same layout inside the package, read-only.

Durability contract: every file is written to a unique temporary sibling and renamed
into place; each state transition holds a per-run advisory lock and re-reads the state
under it, so two processes (the CLI and the API on one machine) never lose each other's
writes; ``run.json`` is written LAST on completion, so ``completed`` implies the
artifacts exist. Package data is expected on a real filesystem (a normal wheel install),
not inside a zip importer.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import socket
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import psutil

from tessera.api.receipts import receipt_from_log
from tessera.errors import SpecError, TesseraError
from tessera.report.log_adapter import read_log
from tessera.report.render import render_markdown
from tessera.report.serialize import report_to_dict

try:
    from importlib.resources.abc import Traversable
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    from importlib.abc import Traversable

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no flock; transitions run unlocked
    fcntl = None  # type: ignore[assignment]

SCHEMA_VERSION = 1
# Reserved whether or not the examples root is present: a home run may never shadow them.
RESERVED_IDS = frozenset({"first-contact", "gpt-4o"})
# Mirrors contract.Run.source — checked here too so a bad value fails at the write site
# instead of surfacing later as a pydantic error when the payload is built.
_VALID_SOURCES = frozenset({"run", "import", "bundled"})
_CREATE_ATTEMPTS = 5
_BUNDLED_READ_ONLY = "bundled example runs are read-only"
_LOG = logging.getLogger(__name__)
UTC = timezone.utc


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _fsync_dir(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:  # pragma: no cover - platforms that cannot open a directory
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_atomic(path: Path, payload: bytes) -> None:
    """Write bytes to a unique temporary sibling, fsync, rename over the destination,
    then fsync the directory so the rename itself survives a crash."""
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    _fsync_dir(path.parent)


def _read_json(path: Traversable | Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


class _CorruptRun(ValueError):
    """A run folder whose state cannot be read; listing skips it, get() reports it."""


def _check_schema(data: dict) -> None:
    version = data.get("schema_version")
    if type(version) is not int:
        raise _CorruptRun(f"run.json has no integer schema_version (got {version!r})")
    if version > SCHEMA_VERSION:
        raise SpecError(
            f"run schema version {version} is newer than supported version {SCHEMA_VERSION}"
        )


@dataclass(frozen=True)
class RunRecord:
    id: str
    dir: Traversable | Path
    data: dict

    def report(self) -> dict | None:
        path = self.dir.joinpath("report.json")
        return _read_json(path) if path.is_file() else None

    def receipt(self) -> dict | None:
        path = self.dir.joinpath("receipt.json")
        return _read_json(path) if path.is_file() else None

    def markdown(self) -> str | None:
        path = self.dir.joinpath("report.md")
        return path.read_text(encoding="utf-8") if path.is_file() else None


class RunStore:
    def __init__(
        self,
        home: Path,
        examples: Traversable | Path = resources.files("tessera.data") / "examples",
    ) -> None:
        self.home = Path(home)
        self.runs = self.home / "runs"
        self.examples = examples
        self.diagnostics: list[str] = []

    # ----- layout -----

    def _ensure_runs(self) -> None:
        was_missing = not self.home.exists()
        self.home.mkdir(parents=True, exist_ok=True)
        if was_missing:
            self.home.chmod(0o700)
        self.runs.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _valid_ref(ref: str) -> bool:
        return bool(ref) and Path(ref).name == ref and ref not in {".", ".."}

    def _bundled_dir(self, ref: str) -> Traversable | Path | None:
        if not self._valid_ref(ref):
            return None
        directory = self.examples.joinpath(ref)
        return directory if directory.is_dir() else None

    def _home_dir(self, ref: str) -> Path | None:
        """The run directory for ``ref`` inside ``runs/`` — never a reserved id, never a
        symlink, never anything whose resolved parent is not ``runs/`` itself."""
        if not self._valid_ref(ref) or ref in RESERVED_IDS:
            return None
        directory = self.runs / ref
        if directory.is_symlink() or not directory.is_dir():
            return None
        if directory.resolve().parent != self.runs.resolve():
            return None
        return directory

    def _read_state(self, directory: Traversable | Path) -> dict:
        try:
            data = _read_json(directory.joinpath("run.json"))
        except (OSError, ValueError) as exc:
            raise _CorruptRun(str(exc)) from exc
        _check_schema(data)
        if "id" not in data:
            raise _CorruptRun("run.json has no id")
        return data

    def _read_state_or_spec_error(self, directory: Traversable | Path, ref: str) -> dict:
        try:
            return self._read_state(directory)
        except _CorruptRun as exc:
            raise SpecError(f"run {ref} is unreadable: {exc}") from exc

    def _write_state(self, directory: Path, data: dict) -> None:
        _write_atomic(directory / "run.json", _json_bytes(data))

    @staticmethod
    def _record(directory: Traversable | Path, data: dict) -> RunRecord:
        return RunRecord(id=str(data["id"]), dir=directory, data=data)

    # ----- transactions -----

    @contextmanager
    def _locked(self, directory: Path):
        """Per-run advisory lock (flock on ``run.lock``) held across a read-modify-write."""
        lock_path = directory / "run.lock"
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _transition(self, ref: str, mutate: Callable[[dict, Path], bool]) -> RunRecord:
        """Apply ``mutate(data, directory)`` to the fresh state under the run's lock;
        ``mutate`` returns False to leave the state untouched (the transition no longer
        applies)."""
        if self._bundled_dir(ref) is not None:
            raise SpecError(_BUNDLED_READ_ONLY)
        directory = self._home_dir(ref)
        if directory is None:
            raise SpecError(f"unknown run: {ref}")
        with self._locked(directory):
            data = self._read_state_or_spec_error(directory, ref)
            if mutate(data, directory):
                self._write_state(directory, data)
        return self._record(directory, data)

    # ----- creation -----

    def _new_id(self) -> str:
        suffix = base64.b32encode(secrets.token_bytes(5)).decode().lower()
        return f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{suffix}"

    def _initial_data(self, run_id: str, request: dict, source: str) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": run_id,
            "status": "queued",
            "source": source,
            "archived": False,
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "request": dict(request),
            "owner": None,
            "error": None,
        }

    def _create_dir(self, run_id: str) -> Path | None:
        """Claim ``runs/<run_id>``; None when it already exists."""
        self._ensure_runs()
        directory = self.runs / run_id
        try:
            directory.mkdir(exist_ok=False)
        except FileExistsError:
            return None
        return directory

    def _create_with_id(self, run_id: str, request: dict, source: str) -> RunRecord:
        if source not in _VALID_SOURCES:
            raise SpecError(f"invalid run source: {source!r}")
        if not self._valid_ref(run_id):
            raise SpecError(f"invalid run id: {run_id}")
        if run_id in RESERVED_IDS or self._bundled_dir(run_id) is not None:
            raise SpecError(f"run id is reserved by a bundled example: {run_id}")
        directory = self._create_dir(run_id)
        if directory is None:
            raise SpecError(f"run already exists: {run_id}")
        data = self._initial_data(run_id, request, source)
        self._write_state(directory, data)
        return self._record(directory, data)

    def create(self, request: dict, *, source: str = "run") -> RunRecord:
        if source not in _VALID_SOURCES:
            raise SpecError(f"invalid run source: {source!r}")
        for _ in range(_CREATE_ATTEMPTS):
            run_id = self._new_id()
            directory = self._create_dir(run_id)
            if directory is None:
                continue
            data = self._initial_data(run_id, request, source)
            self._write_state(directory, data)
            return self._record(directory, data)
        raise TesseraError(f"could not allocate a run id after {_CREATE_ATTEMPTS} attempts")

    # ----- transitions -----

    def mark_running(self, run_id: str) -> RunRecord:
        def mutate(data: dict, _directory: Path) -> bool:
            data.update({
                "status": "running",
                "started_at": _now(),
                "owner": {
                    "pid": os.getpid(),
                    "hostname": socket.gethostname(),
                    "process_started_at": psutil.Process().create_time(),
                },
                "error": None,
            })
            return True

        return self._transition(run_id, mutate)

    def mark_completed(
        self,
        run_id: str,
        *,
        report: dict,
        receipt: dict,
        markdown: str,
        log_path: Path | None,
    ) -> RunRecord:
        def mutate(data: dict, directory: Path) -> bool:
            # Artifacts first, state last: a reader that sees "completed" finds them.
            _write_atomic(directory / "report.json", _json_bytes(report))
            _write_atomic(directory / "receipt.json", _json_bytes(receipt))
            _write_atomic(directory / "report.md", markdown.encode())
            if log_path is not None:
                _write_atomic(directory / "log.eval", Path(log_path).read_bytes())
            data.update({
                "status": "completed",
                "finished_at": _now(),
                "owner": None,
                "error": None,
            })
            return True

        return self._transition(run_id, mutate)

    def mark_failed(self, run_id: str, error: str) -> RunRecord:
        def mutate(data: dict, _directory: Path) -> bool:
            data.update({
                "status": "failed",
                "finished_at": _now(),
                "owner": None,
                "error": error,
            })
            return True

        return self._transition(run_id, mutate)

    def mark_interrupted(self, run_id: str) -> RunRecord:
        def mutate(data: dict, _directory: Path) -> bool:
            data.update({"status": "interrupted", "finished_at": _now(), "owner": None})
            return True

        return self._transition(run_id, mutate)

    def set_archived(self, run_id: str, archived: bool) -> RunRecord:
        def mutate(data: dict, _directory: Path) -> bool:
            data["archived"] = archived
            return True

        return self._transition(run_id, mutate)

    # ----- reads -----

    def get(self, ref: str) -> RunRecord:
        directory = self._bundled_dir(ref) or self._home_dir(ref)
        if directory is None:
            raise SpecError(f"unknown run: {ref}")
        return self._record(directory, self._read_state_or_spec_error(directory, ref))

    def _list_root(self, root: Traversable | Path, *, bundled: bool) -> list[RunRecord]:
        if not root.is_dir():
            return []
        records = []
        for directory in root.iterdir():
            if not directory.is_dir():
                continue
            if not bundled and self._home_dir(directory.name) is None:
                continue  # reserved name, symlink, or otherwise not a run of ours
            try:
                data = self._read_state(directory)
                records.append(self._record(directory, data))
            except (_CorruptRun, SpecError) as exc:
                # Unreadable JSON and a schema newer than we understand (e.g. one run
                # folder left behind by a rolled-back deploy) are both non-fatal here:
                # one bad folder must not hide every other run from list(). get() and
                # _transition() still raise SpecError loudly for that one run by id.
                diagnostic = f"skipping unreadable run folder {directory}: {exc}"
                self.diagnostics.append(diagnostic)
                _LOG.warning(diagnostic)
        if bundled:
            return sorted(records, key=lambda record: record.id)
        return sorted(
            records,
            key=lambda record: (str(record.data.get("created_at", "")), record.id),
            reverse=True,
        )

    def list(self, *, include_archived: bool = False) -> list[RunRecord]:
        self.diagnostics.clear()
        home = self._list_root(self.runs, bundled=False)
        bundled = self._list_root(self.examples, bundled=True)
        records = home + bundled
        if include_archived:
            return records
        return [record for record in records if not record.data.get("archived", False)]

    # ----- import + recovery -----

    def import_log(
        self,
        path: Path,
        *,
        source: str = "import",
        id: str | None = None,
    ) -> RunRecord:
        # Snapshot the source once: the stored log, the report and the receipt's digest
        # all describe the same bytes even if the source file changes underneath us.
        payload = Path(path).read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as scratch:
            snapshot = Path(scratch) / "log.eval"
            snapshot.write_bytes(payload)
            log = read_log(snapshot)
            # Computed once: the report's location field is the only thing that differs
            # between "the log as read from the scratch snapshot" and "the log as stored",
            # so it is cheaper to patch that one field below than to re-derive the whole
            # report (probes, categories, axes) a second time over the same samples.
            report = report_to_dict(log)
            header = report["header"]
            request = {
                "suite": header.get("org") or "",
                "model": header["model"],
                "engine": header["engine"],
                "grader": header.get("grader"),
                "k": header["k"],
                "scaffold": header.get("scaffold") or "baseline",
                "seed": header.get("seed") if header.get("seed") is not None else 0,
            }
            record = (
                self._create_with_id(id, request, source)
                if id is not None
                else self.create(request, source=source)
            )
            try:
                # The report and receipt name the stored copy, not the scratch snapshot.
                header["location"] = str(Path(record.dir) / "log.eval")
                log = log.model_copy(update={"location": header["location"]})
                # The same receipt the bundled examples carry: timing, usage and git
                # revision come from the log, so an imported log and a bundled one are
                # comparable.
                receipt = receipt_from_log(log, report, artifact_sha256=digest)
                return self.mark_completed(
                    record.id,
                    report=report,
                    receipt=receipt,
                    markdown=render_markdown(report),
                    log_path=snapshot,
                )
            except Exception as exc:
                # The run directory already exists (queued). Leave it discoverable and
                # marked failed rather than an orphaned "queued" run with no error that
                # reconcile() never touches (it only ever acts on "running" runs).
                self.mark_failed(record.id, str(exc))
                raise

    @staticmethod
    def _owner_is_dead(owner: dict | None, hostname: str) -> bool | None:
        """True/False when we can tell; None when the owner is on another host."""
        if owner is None:
            return True  # a running run always has an owner; none means corrupt state
        if owner.get("hostname") != hostname:
            return None
        try:
            process = psutil.Process(int(owner["pid"]))
            # A reused PID is a different process with a different start time.
            return abs(process.create_time() - float(owner["process_started_at"])) > 1e-3
        except (psutil.NoSuchProcess, ProcessLookupError, KeyError, TypeError, ValueError):
            return True
        except psutil.AccessDenied:
            return False

    def reconcile(self) -> list[str]:
        """Mark every home run still ``running`` whose owner process is gone as
        ``interrupted``. The decision is re-taken under the run's lock, so a run that
        completes concurrently is never downgraded."""
        interrupted = []
        hostname = socket.gethostname()
        for record in self._list_root(self.runs, bundled=False):
            if record.data.get("status") != "running":
                continue

            def mutate(data: dict, _directory: Path) -> bool:
                if data.get("status") != "running":
                    return False
                if self._owner_is_dead(data.get("owner"), hostname) is not True:
                    return False
                data.update({"status": "interrupted", "finished_at": _now(), "owner": None})
                return True

            try:
                transitioned = self._transition(record.id, mutate)
            except SpecError as exc:
                # The folder we listed a moment ago is gone or unreadable now — skip it,
                # the same way a corrupt run is skipped during list(), rather than let one
                # bad run folder abort reconciliation for every other running run.
                diagnostic = f"skipping run {record.id} during reconcile: {exc}"
                self.diagnostics.append(diagnostic)
                _LOG.warning(diagnostic)
                continue
            if transitioned.data["status"] == "interrupted":
                interrupted.append(record.id)
        return interrupted

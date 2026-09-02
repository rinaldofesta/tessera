"""The single Tessera command-line interface."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import webbrowser
from contextlib import redirect_stdout
from enum import Enum
from functools import wraps
from pathlib import Path

import click
import typer
from dotenv import load_dotenv
from typer.core import TyperGroup

from tessera import __version__, paths, providers
from tessera import catalog as catalog_module
from tessera.api.providers import FIELD_API_KEY, PROVIDERS
from tessera.api.scrub import scrub_error
from tessera.errors import (
    ExitCode,
    GateFailed,
    NotConnectedError,
    SpecError,
    TesseraError,
)
from tessera.report.compare import compare_reports
from tessera.report.leaderboard import (
    _is_safe_repo_relative_path,
    _repo_relative,
    _sha256_file,
    extract_rows,
    render_leaderboard,
    render_manifest,
    row_metric_mismatches,
)
from tessera.report.models import ReportError
from tessera.report.render import render_markdown
from tessera.report.serialize import report_to_dict
from tessera.runner import execute, plan, run_result_payload
from tessera.store import RunRecord, RunStore
from tessera.verdict import verdict_of


class _NoArgsHelpGroup(TyperGroup):
    """Click treats implicit help as a usage error; Tessera treats it as success."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            click.echo(ctx.get_help())
            ctx.exit()
        return super().parse_args(ctx, args)


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode=None,
    cls=_NoArgsHelpGroup,
)
leaderboard_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode=None,
    cls=_NoArgsHelpGroup,
)
app.add_typer(leaderboard_app, name="leaderboard")


class EngineOption(str, Enum):
    deterministic = "deterministic"
    llm = "llm"


class CatalogSection(str, Enum):
    suites = "suites"
    models = "models"
    scorers = "scorers"
    providers = "providers"


class Context:
    """Paths and storage resolved together from the current Tessera environment."""

    def __init__(self) -> None:
        self.home = paths.home()
        self.store = RunStore(self.home)
        self.suites_dir = paths.suites_dir()
        self.env_file = paths.env_file()
        load_dotenv(self.env_file, interpolate=False, override=False)


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def _error_payload(exc: TesseraError) -> dict:
    return {
        "ok": False,
        "error": {
            "code": ExitCode(exc.exit_code).name.lower(),
            "message": str(exc),
            "fix": getattr(exc, "fix", None),
        },
    }


def _guard(command):
    """Give every command the same redacted errors, JSON envelope, and exit codes."""

    @wraps(command)
    def guarded(*args, **kwargs):
        json_output = bool(kwargs.get("json_output", False))
        try:
            return command(*args, **kwargs)
        except KeyboardInterrupt:
            raise typer.Exit(code=130) from None
        except typer.Exit:
            raise
        except TesseraError as exc:
            if json_output:
                _print_json(_error_payload(exc))
            else:
                typer.echo(f"error: {exc}", err=True)
                if fix := getattr(exc, "fix", None):
                    typer.echo(f"fix: {fix}", err=True)
            raise typer.Exit(code=int(exc.exit_code)) from None
        except Exception as exc:  # noqa: BLE001 — this is the no-traceback CLI boundary
            error = TesseraError(scrub_error(f"{type(exc).__name__}: {exc}"))
            if json_output:
                _print_json(_error_payload(error))
            else:
                typer.echo(f"error: {error}", err=True)
            raise typer.Exit(code=int(error.exit_code)) from None

    return guarded


def _record_for_ref(context: Context, ref: str) -> RunRecord:
    if ref != "latest":
        return context.store.get(ref)
    for record in context.store.list(include_archived=True):
        if record.data.get("source") != "bundled":
            return record
    raise SpecError("there are no runs yet")


def _raise_plan_error(blockers: list[dict]) -> None:
    not_connected = next(
        (blocker for blocker in blockers if blocker["code"] == "not_connected"),
        None,
    )
    error_type = NotConnectedError if not_connected else SpecError
    error = error_type("; ".join(blocker["message"] for blocker in blockers))
    if not_connected and not_connected.get("fix"):
        error.fix = not_connected["fix"]
    raise error


def _raise_gate_failed(json_output: bool, message: str) -> None:
    """The result was already printed; the exit code alone carries the gate for JSON."""
    if json_output:
        raise typer.Exit(code=int(ExitCode.GATE_FAILED))
    raise GateFailed(message)


def _print_plan(payload: dict) -> None:
    typer.echo(f"ready: {'yes' if payload['ready'] else 'no'}")
    for blocker in payload["blockers"]:
        suffix = f" · fix: {blocker['fix']}" if blocker.get("fix") else ""
        typer.echo(f"blocker: {blocker['message']}{suffix}")
    request = payload["request"]
    suite = payload["suite"]
    typer.echo(f"suite: {suite['name'] if suite else request['suite']}")
    typer.echo(f"model: {request['model']}")
    typer.echo(f"engine: {request['engine']}")
    if request.get("grader"):
        typer.echo(f"grader: {request['grader']}")
    typer.echo(f"k: {request['k']}")
    typer.echo(f"scaffold: {request['scaffold']}")
    typer.echo(f"seed: {request['seed']}")
    typer.echo(f"scorer: {payload['scorer_version']}")


def _print_run_result(payload: dict) -> None:
    verdict = payload["verdict"]
    request = payload["request"]
    typer.echo(verdict["sentence"])
    typer.echo(
        f"pass^{request['k']} {verdict['pass_k_rate']:.0%} · "
        f"mean {verdict['mean_rate']:.0%}"
    )
    typer.echo(f"saved {payload['paths']['dir']}")
    typer.echo(f"next: tessera report {payload['id']}")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tessera {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        is_eager=True,
        callback=_version_callback,
        help="Show the Tessera version and exit.",
    ),
) -> None:
    pass


@app.command()
@_guard
def ui(
    port: int | None = typer.Option(None, "--port"),
    no_open: bool = typer.Option(False, "--no-open"),
    check: bool = typer.Option(False, "--check"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Launch the local Tessera UI or check that it is ready."""
    from tessera.api.app import create_app, ui_dist

    if check:
        home = paths.home()
        checked_app = create_app(home=home)
        bundle_dir = ui_dist()
        bundle = bundle_dir / "index.html" if bundle_dir is not None else None
        env_file = checked_app.state.env_file
        payload = {
            "ok": True,
            "api": "ok",
            "ui_bundle": str(bundle) if bundle is not None else None,
            "home": str(home),
            "env_file": str(env_file),
            "env_file_present": env_file.is_file(),
        }
        if json_output:
            _print_json(payload)
        else:
            typer.echo("api: ok")
            typer.echo(
                f"ui bundle: {bundle}"
                if bundle is not None
                else "ui bundle: not built (the API still serves /api/*)"
            )
            typer.echo(f"home: {home}")
            state = "present" if payload["env_file_present"] else "missing"
            typer.echo(f"env file: {env_file} ({state})")
        # PR7 makes a missing bundle exit 4 once the wheel is expected to contain it.
        return

    selected_port = port if port is not None else int(os.environ.get("TESSERA_API_PORT", "8000"))
    url = f"http://127.0.0.1:{selected_port}"
    typer.echo(f"Tessera UI: {url}  (Ctrl-C to stop)")
    if not no_open:
        timer = threading.Timer(1.0, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()

    import uvicorn

    uvicorn.run(
        "tessera.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=selected_port,
        log_level="warning",
    )


@app.command()
@_guard
def guide(
    topic: str | None = typer.Argument(None, metavar="TOPIC"),
    list_topics: bool = typer.Option(False, "--list"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Read short guidance for running and understanding Tessera."""
    from tessera import guide as guide_module

    if list_topics:
        available = guide_module.topics()
        if json_output:
            _print_json({"ok": True, "topics": available})
        else:
            for item in available:
                typer.echo(f"{item['name']} — {item['summary']}")
        return

    selected = topic or "start"
    content = guide_module.text(selected)
    if json_output:
        _print_json({"ok": True, "topic": selected, "text": content})
    else:
        typer.echo(content, nl=False)


_SUITE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@app.command("init")
@_guard
def init_suite(
    name: str = typer.Argument(..., metavar="NAME"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Create an editable suite from the starter authoring template."""
    from importlib import resources

    from tessera.api import blueprint_store
    from tessera.catalog import BUILTIN_SUITES, SUITE_ALIASES
    from tessera.models import Blueprint

    reserved = {*BUILTIN_SUITES, *SUITE_ALIASES}
    if not _SUITE_NAME.fullmatch(name):
        raise SpecError("NAME must start with a letter or digit and use only letters, digits, '-' and '_'")
    if name in reserved:
        raise SpecError(f"suite name '{name}' is reserved for a builtin suite or alias")

    context = Context()
    try:
        if blueprint_store.exists(context.suites_dir, name):
            raise SpecError(f"suite '{name}' already exists")
        # save_blueprint() would happily mkdir(parents=True) a missing ~/.tessera itself,
        # but at the process umask (e.g. 0755) rather than the 0700 every other code path
        # treats as this directory's invariant (see the same call in `connect`, which
        # later becomes a no-op once the directory already exists) — `init` can be the
        # very first command a new user runs, so it must harden the directory itself.
        paths.ensure_home()
        template_file = resources.files("tessera.data").joinpath("templates", "suite.json")
        template = Blueprint.model_validate_json(template_file.read_text(encoding="utf-8"))
        blueprint_store.save_blueprint(context.suites_dir, name, template)
    except blueprint_store.BlueprintStoreError as exc:
        raise SpecError(str(exc)) from None

    output_path = context.suites_dir / f"{name}.json"
    if json_output:
        _print_json({"ok": True, "path": str(output_path), "name": name})
    else:
        typer.echo(str(output_path))
        typer.echo(f"next: edit it, then tessera validate {name}")


def _suite_data(ref: str, context: Context) -> tuple[str, object, list[dict[str, str]]]:
    from tessera import orgs

    path = Path(ref)
    if path.suffix == ".json":
        if not path.is_file():
            raise SpecError(f"suite file not found: {path}")
        try:
            return path.stem, json.loads(path.read_text(encoding="utf-8")), []
        except json.JSONDecodeError as exc:
            return path.stem, None, [
                {
                    "location": f"line {exc.lineno} column {exc.colno}",
                    "message": exc.msg,
                }
            ]
        except OSError as exc:
            raise SpecError(f"cannot read suite file: {path} ({exc})") from None

    try:
        suite, _ = catalog_module.resolve_suite(ref, suites_dir=context.suites_dir)
    except SpecError:
        # An invalid saved suite is deliberately absent from the catalog; still surface
        # its located validation issues when the user validates it by name.
        saved = context.suites_dir / f"{ref}.json"
        if saved.is_file():
            return _suite_data(str(saved), context)
        raise
    blueprint = orgs.get_blueprint(suite["org"], store_dir=context.suites_dir)
    return suite["name"], blueprint.model_dump(by_alias=True), []


@app.command()
@_guard
def validate(
    ref: str = typer.Argument(..., metavar="REF"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Validate a builtin, saved, or file-based suite without model calls."""
    from tessera.api import blueprint_store

    name, data, read_issues = _suite_data(ref, Context())
    issues = read_issues or blueprint_store.validate_blueprint(data)
    claims = data.get("claims", []) if isinstance(data, dict) else []
    probes = data.get("probes", []) if isinstance(data, dict) else []
    claim_count = len(claims) if isinstance(claims, list) else 0
    question_count = len(probes) if isinstance(probes, list) else 0
    payload = {
        "ok": not issues,
        "issues": issues,
        "questions": question_count,
        "claims": claim_count,
    }

    if json_output:
        _print_json(payload)
        if issues:
            raise typer.Exit(code=int(ExitCode.SPEC_ERROR))
        return
    if issues:
        for issue in issues:
            typer.echo(f"{issue['location'] or '<root>'}: {issue['message']}")
        raise SpecError("suite is not valid")
    typer.echo(f"ok: {name} ({question_count} questions, {claim_count} claims)")


def _leaderboard_error(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=2)


def _emit_leaderboard(text: str, out: Path | None) -> None:
    if out is not None:
        out.write_text(text, encoding="utf-8")
    elif text.endswith("\n"):
        sys.stdout.write(text)
    else:
        typer.echo(text)


def _read_manifest(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, OSError, ValueError) as exc:
        _leaderboard_error(f"cannot read manifest: {path} ({scrub_error(str(exc))})")


def _find_repo_root(start: Path) -> Path:
    original = Path(os.path.abspath(start))
    directory = original
    while True:
        if (directory / ".git").exists():
            return directory
        if directory.parent == directory:
            return original
        directory = directory.parent


def _read_leaderboard_reports(logs: list[Path]) -> list[dict]:
    from tessera.report.log_adapter import read_log

    reports = []
    for path in logs:
        try:
            reports.append(report_to_dict(read_log(path)))
        except (FileNotFoundError, OSError, ValueError) as exc:
            _leaderboard_error(f"cannot read log: {path} ({scrub_error(str(exc))})")
        except ReportError as exc:
            _leaderboard_error(scrub_error(str(exc)))
    return reports


def _verify_leaderboard(manifest: dict, manifest_path: Path) -> int:
    """Re-derive every backed row and preserve the manifest tool's 0/2 contract."""
    from tessera.report.log_adapter import read_log

    repo_root = _find_repo_root(Path(os.path.dirname(os.path.abspath(manifest_path))))
    rows = manifest.get("rows", [])
    backed, unbacked, failures = 0, 0, []
    for row in rows:
        log = row.get("log")
        label = row.get("label") or row.get("model") or "?"
        if log is None:
            unbacked += 1
            continue
        path = log.get("path") if isinstance(log, dict) else None
        sha = log.get("sha256") if isinstance(log, dict) else None
        if not path or not sha or not _is_safe_repo_relative_path(path):
            failures.append(f"{label}: malformed or unsafe log reference ({path!r})")
            continue
        absolute_path = repo_root / path
        if not absolute_path.is_file():
            failures.append(f"{label}: committed log not found at {path}")
            continue
        if _sha256_file(str(absolute_path)) != sha:
            failures.append(f"{label}: sha256 does not match the committed {path}")
            continue
        try:
            derived = extract_rows([report_to_dict(read_log(absolute_path))])[0]
        except (ReportError, ValueError, OSError) as exc:
            failures.append(f"{label}: cannot re-derive from {path} ({exc})")
            continue
        mismatches = row_metric_mismatches(row, derived)
        if mismatches:
            failures.append(f"{label}: {path} does not reproduce {', '.join(mismatches)}")
            continue
        backed += 1
    summary = (
        f"verified {backed}/{len(rows)} rows against a committed log; "
        f"{unbacked} unbacked (log: null)"
    )
    if failures:
        for failure in failures:
            typer.echo(f"FAIL {failure}", err=True)
        typer.echo(summary, err=True)
        return 2
    typer.echo(summary)
    return 0


@leaderboard_app.command("render")
@_guard
def leaderboard_render(
    logs: list[Path] | None = typer.Argument(None, metavar="LOGS..."),
    manifest: Path | None = typer.Option(None, "--manifest"),
    label: list[str] | None = typer.Option(None, "--label"),
    note: list[str] | None = typer.Option(None, "--note"),
    out: Path | None = typer.Option(None, "--out", "-o"),
    title: str | None = typer.Option(None, "--title"),
) -> None:
    """Render a leaderboard manifest or one or more evaluation logs as Markdown."""
    if manifest is not None:
        loaded = _read_manifest(manifest)
        rendered_manifest = {**loaded, "title": title} if title is not None else loaded
        try:
            rendered = render_manifest(rendered_manifest)
        except (ValueError, KeyError) as exc:
            _leaderboard_error(str(exc))
        _emit_leaderboard(rendered, out)
        return
    if not logs:
        _leaderboard_error("provide one or more .eval logs, or --manifest <file>")
    reports = _read_leaderboard_reports(logs)
    try:
        rendered = render_leaderboard(
            reports,
            labels=label or [],
            notes=note or [],
            title=title,
        )
    except ValueError as exc:
        _leaderboard_error(str(exc))
    _emit_leaderboard(rendered, out)


@leaderboard_app.command("extract")
@_guard
def leaderboard_extract(
    logs: list[Path] | None = typer.Argument(None, metavar="LOGS..."),
    label: list[str] | None = typer.Option(None, "--label"),
    note: list[str] | None = typer.Option(None, "--note"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Extract manifest rows from one or more committed evaluation logs (prints JSON
    rows to paste into docs/leaderboard.rows.json; stamps are repo-relative to cwd)."""
    if not logs:
        _leaderboard_error("provide one or more .eval logs")
    reports = _read_leaderboard_reports(logs)
    repo_root = _find_repo_root(Path.cwd())
    rows = extract_rows(reports, labels=label or [], notes=note or [])
    for index, row in enumerate(rows):
        log_path = logs[index]
        try:
            relative_path = _repo_relative(os.path.abspath(log_path), str(repo_root))
        except ValueError as exc:
            _leaderboard_error(str(exc))
        row["log"] = {
            "path": relative_path,
            "sha256": _sha256_file(str(log_path)),
        }
    _emit_leaderboard(json.dumps(rows, indent=2), out)


@leaderboard_app.command("verify")
@_guard
def leaderboard_verify(
    manifest: Path | None = typer.Option(None, "--manifest"),
) -> None:
    """Verify every log-backed row in a leaderboard manifest."""
    if manifest is None:
        _leaderboard_error("--verify requires --manifest <file>")
    result = _verify_leaderboard(_read_manifest(manifest), manifest)
    if result:
        raise typer.Exit(code=result)


@app.command()
@_guard
def run(
    model: str = typer.Option(..., "--model"),
    suite: str = typer.Option("starter", "--suite"),
    engine: EngineOption = typer.Option(EngineOption.deterministic, "--engine"),
    grader: str | None = typer.Option(None, "--grader"),
    k: int = typer.Option(3, "--k"),
    scaffold: str = typer.Option("baseline", "--scaffold"),
    seed: int = typer.Option(0, "--seed"),
    min_pass_k: float | None = typer.Option(None, "--min-pass-k"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Plan and execute a reliability evaluation."""
    if min_pass_k is not None and not 0 <= min_pass_k <= 1:
        raise SpecError("--min-pass-k must be between 0 and 1")
    context = Context()
    spec = {
        "suite": suite,
        "model": model,
        "engine": engine.value,
        "grader": grader,
        "k": k,
        "scaffold": scaffold,
        "seed": seed,
    }
    run_plan = plan(spec, env=os.environ, suites_dir=context.suites_dir)
    if dry_run:
        if json_output:
            _print_json(run_plan)
        else:
            _print_plan(run_plan)
        return

    if not run_plan["ready"]:
        _raise_plan_error(run_plan["blockers"])

    request = run_plan["request"]
    record = context.store.create(request)
    typer.echo(
        f"running {request['suite']} on {request['model']} — {request['k']} repeats, "
        "this can take a few minutes…",
        err=True,
    )
    executed_payload = execute(
        record,
        request,
        store=context.store,
        suites_dir=context.suites_dir,
        env=os.environ,
    )
    # execute() already built and returned the payload for this record; only rebuild it
    # (a second store.get() + report/receipt read) when a --min-pass-k gate needs to be
    # folded in, since execute()'s own payload never carries one.
    payload = (
        run_result_payload(context.store.get(record.id), min_pass_k=min_pass_k)
        if min_pass_k is not None
        else executed_payload
    )
    if payload["status"] != "completed":
        if json_output:  # the payload is the error report; exit code says the rest
            _print_json(payload)
            raise typer.Exit(code=int(ExitCode.RUNTIME_ERROR))
        raise TesseraError(payload["error"] or "run failed")

    if json_output:
        _print_json(payload)
    else:
        _print_run_result(payload)

    gate = payload.get("gate")
    if gate is not None and not gate["passed"]:
        verdict = payload["verdict"]
        _raise_gate_failed(
            json_output,
            f"pass^{request['k']} {verdict['pass_k_rate']:.0%} is below "
            f"--min-pass-k {min_pass_k:.0%}",
        )


@app.command()
@_guard
def report(
    ref: str = typer.Argument("latest", metavar="REF"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Render a stored run or an Inspect .eval log."""
    context = Context()
    log_path = Path(ref)
    if ref.endswith(".eval") and log_path.is_file():
        from tessera.report.log_adapter import read_log  # inspect_ai only for raw logs

        report_data = report_to_dict(read_log(log_path))
        if json_output:
            _print_json({
                "ok": True,
                "report": report_data,
                "verdict": verdict_of(report_data),
            })
        else:
            typer.echo(render_markdown(report_data), nl=False)
        return

    record = _record_for_ref(context, ref)
    if json_output:
        _print_json(run_result_payload(record))
        return
    markdown = record.markdown()
    if markdown is None and (report_data := record.report()) is not None:
        markdown = render_markdown(report_data)
    if markdown is None:
        raise SpecError(f"run {record.id} has no report")
    typer.echo(markdown, nl=False)


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    # One tuple argument, not `max(a, *bs)`: with zero rows `*bs` unpacks to nothing and
    # `max(a)` treats the lone int as an iterable to exhaust, raising TypeError instead
    # of just returning `a`.
    widths = [
        max((len(headers[index]), *(len(row[index]) for row in rows)))
        for index in range(len(headers))
    ]
    typer.echo("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(headers)))
    for row in rows:
        typer.echo("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


@app.command()
@_guard
def history(
    archived: bool = typer.Option(False, "--archived"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List saved and bundled runs."""
    context = Context()
    payloads = [
        run_result_payload(record, include_report=False)
        for record in context.store.list(include_archived=archived)
    ]
    if json_output:
        _print_json({"ok": True, "runs": payloads})
        return
    rows = []
    for payload in payloads:
        verdict = payload["verdict"]
        when = payload["created_at"][:16]
        if payload["source"] == "bundled":
            when += " (bundled)"
        rows.append((
            payload["id"],
            payload["request"]["model"],
            payload["request"]["suite"],
            str(payload["request"]["k"]),
            verdict["label"] if verdict else payload["status"],
            f"{verdict['pass_k_rate']:.0%}" if verdict else "—",
            when,
        ))
    _print_table(("ID", "MODEL", "SUITE", "K", "VERDICT", "PASS^K", "WHEN"), rows)


@app.command()
@_guard
def archive(
    ref: str = typer.Argument(..., metavar="REF"),
    restore: bool = typer.Option(False, "--restore"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Archive or restore a home run."""
    context = Context()
    record = _record_for_ref(context, ref)
    record = context.store.set_archived(record.id, not restore)
    if json_output:
        _print_json(run_result_payload(record, include_report=False))
    else:
        action = "restored" if restore else "archived"
        typer.echo(f"{action} {record.id}")


@app.command("import")
@_guard
def import_log(
    log: str = typer.Argument(..., metavar="LOG"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Import an existing Inspect .eval log into history."""
    context = Context()
    record = context.store.import_log(Path(log))
    payload = run_result_payload(record)
    if json_output:
        _print_json(payload)
    else:
        typer.echo(payload["verdict"]["sentence"])
        typer.echo(f"imported as {record.id}")


def _catalog_human(catalog: dict, section: str | None) -> None:
    selected = [section] if section else ["suites", "models", "scorers", "providers"]
    for index, name in enumerate(selected):
        if index:
            typer.echo("")
        typer.echo(name)
        if name == "suites":
            for row in catalog["suites"]:
                typer.echo(
                    f"{row['name']}  {row['label']}  {row['questions']}  {row['kind']}"
                )
        elif name == "models":
            for row in catalog["models"]:
                state = "connected" if row["connected"] else "not connected"
                typer.echo(f"{row['id']}  {row['provider']}  {state}")
        elif name == "providers":
            for row in catalog["providers"]:
                state = "connected" if row["connected"] else "not connected"
                fields = ",".join(field["id"] for field in row["fields"])
                typer.echo(f"{row['id']}  {row['label']}  {state}  {fields}")
        elif name == "scorers":
            for row in catalog["scorers"]:
                typer.echo(f"{row['engine']}  {row['version']}")
    defaults = catalog["defaults"]
    typer.echo("")
    typer.echo(
        "defaults: "
        f"suite={defaults['suite']}  engine={defaults['engine']}  k={defaults['k']}  "
        f"scaffold={defaults['scaffold']}  seed={defaults['seed']}"
    )


def _show_catalog(section: str | None, json_output: bool, context: Context) -> None:
    payload = catalog_module.build_catalog(env=os.environ, suites_dir=context.suites_dir)
    if json_output:
        # Scoped like the human branch below: a specific section (e.g. "providers" from
        # `catalog providers --json` or the no-provider `connect --json`) must not still
        # hand back the full suites/models/scorers/providers catalog.
        body = {section: payload[section]} if section else {
            key: payload[key] for key in ("suites", "models", "scorers", "providers")
        }
        _print_json({"ok": True, **body, "defaults": payload["defaults"]})
    else:
        _catalog_human(payload, section)


@app.command()
@_guard
def catalog(
    section: CatalogSection | None = typer.Argument(None),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List suites, models, scorers, and provider connection state."""
    _show_catalog(section.value if section else None, json_output, Context())


def _reject_control_characters(value: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise SpecError("value must not contain control characters")


def _stdin_secret() -> str:
    return sys.stdin.readline().strip()


@app.command()
@_guard
def connect(
    provider: str | None = typer.Argument(None, metavar="PROVIDER"),
    key_stdin: bool = typer.Option(False, "--key-stdin"),
    base_url: str | None = typer.Option(None, "--base-url"),
    test_model: str | None = typer.Option(None, "--test", metavar="MODEL"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Save a provider connection without putting credentials in argv."""
    context = Context()
    if provider is None:
        _show_catalog("providers", json_output, context)
        return

    provider_spec = PROVIDERS.get(provider)
    if provider_spec is None:
        raise SpecError(f"unknown provider: {provider}")
    if not provider_spec.needs_credentials:
        raise SpecError(f"provider '{provider}' does not use a stored credential")
    field_ids = {field.id for field in provider_spec.fields}
    if base_url is not None and "base_url" not in field_ids:
        raise SpecError("provider does not accept: base_url")

    api_key = None
    if FIELD_API_KEY in field_ids:
        api_key = _stdin_secret() if key_stdin else typer.prompt("API key", hide_input=True)
        _reject_control_characters(api_key)

    # providers.connect() only calls paths.ensure_home() (which chmods the home
    # directory 0700) down its `env_file is None` branch; passing an explicit env_file
    # — as every CLI call does — skips it, so on a fresh install `connect` as the first
    # command would otherwise leave ~/.tessera created at the process umask instead of
    # the 0700 every other code path treats as this directory's invariant.
    paths.ensure_home()
    provider_row = providers.connect(
        provider,
        api_key=api_key,
        base_url=base_url,
        env_file=context.env_file,
        invalidate=lambda: None,
    )
    probe_result = providers.probe(test_model) if test_model else None
    if json_output:
        _print_json({"ok": True, "provider": provider_row, "probe": probe_result})
        return

    typer.echo(f"✓ saved to {context.env_file} (0600)")
    if probe_result is not None:
        if probe_result["ok"]:
            typer.echo(
                f"✓ probe ok: {probe_result['model']} answered in "
                f"{probe_result['latency_seconds']:.1f} s"
            )
        else:
            typer.echo(f"✗ probe failed: {probe_result['error']}")


def _comparison_line(label: str, result: dict) -> str:
    return (
        f"{label}: A wins {result['a_wins']} · B wins {result['b_wins']} · "
        f"both pass {result['both_pass']} · both fail {result['both_fail']} · "
        f"McNemar p={result['p_value']:.3g}"
    )


@app.command()
@_guard
def compare(
    a: str = typer.Argument(..., metavar="A"),
    b: str = typer.Argument(..., metavar="B"),
    intervention: str = typer.Option("model", "--intervention"),
    require_comparable: bool = typer.Option(False, "--require-comparable"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Compare two runs with paired outcomes and compatibility checks."""
    context = Context()
    record_a = _record_for_ref(context, a)
    record_b = _record_for_ref(context, b)
    report_a = record_a.report()
    report_b = record_b.report()
    if report_a is None or report_b is None:
        raise SpecError("both runs must have completed reports")
    try:
        result = compare_reports(
            report_a,
            report_b,
            intervention=intervention,
            receipt_a=record_a.receipt(),
            receipt_b=record_b.receipt(),
        )
    except ValueError as exc:
        # compare_reports raises a bare ValueError for a bad --intervention; without this
        # it falls through _guard's catch-all as a RUNTIME_ERROR (exit 4) instead of the
        # SPEC_ERROR (exit 3) this CLI uses everywhere else for bad user input.
        raise SpecError(str(exc)) from None
    payload = {"ok": True, "comparable": result["compatible"], **result}
    if json_output:
        _print_json(payload)
    else:
        dimensions = (
            result["changed_dimensions"]
            if result["compatible"]
            else result["unexpected_dimensions"]
        )
        typer.echo(
            f"comparable: {'yes' if result['compatible'] else 'no'} "
            f"({', '.join(dimensions) if dimensions else 'none'})"
        )
        typer.echo(_comparison_line("overall", result["overall"]))
        for category in result["categories"]:
            typer.echo(_comparison_line(category["key"], category))

    if require_comparable and not result["compatible"]:
        detail = ", ".join(result["unexpected_dimensions"])
        _raise_gate_failed(json_output, f"the two runs are not comparable: {detail}")


def _invoke_app(argv: list[str]) -> int | None:
    """Run the canonical command tree in-process for one-release aliases. Under
    standalone_mode=False, Click intercepts the typer.Exit that _guard raises on every
    handled failure and returns its code instead of exiting — so every caller must
    check this return value and re-raise, or a failed delegated command silently
    exits 0."""
    return typer.main.get_command(app).main(
        args=argv,
        prog_name="tessera",
        standalone_mode=False,
    )


report_alias = typer.Typer(add_completion=False)


@report_alias.command()
def _report_alias(
    log: str = typer.Argument(...),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Deprecated tessera-report entry point."""
    click.echo("tessera-report is deprecated — use: tessera report …", err=True)
    if out is None:
        result = _invoke_app(["report", log])
    else:
        with out.open("w", encoding="utf-8") as output:
            with redirect_stdout(output):
                result = _invoke_app(["report", log])
    if result:
        raise typer.Exit(code=result)


leaderboard_alias = typer.Typer(
    add_completion=False,
)


@leaderboard_alias.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
def _leaderboard_alias(context: typer.Context) -> None:
    """Deprecated tessera-leaderboard entry point."""
    click.echo(
        "tessera-leaderboard is deprecated — use: tessera leaderboard …",
        err=True,
    )
    arguments = list(context.args)
    if "--verify" in arguments:
        subcommand = "verify"
        arguments.remove("--verify")
    elif "--extract" in arguments:
        subcommand = "extract"
        arguments.remove("--extract")
    else:
        subcommand = "render"
    result = _invoke_app(["leaderboard", subcommand, *arguments])
    if result:
        raise typer.Exit(code=result)


api_alias = typer.Typer(
    add_completion=False,
)


@api_alias.command(
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
def _api_alias(context: typer.Context) -> None:
    """Deprecated tessera-api entry point."""
    click.echo("tessera-api is deprecated — use: tessera ui --no-open", err=True)
    result = _invoke_app(["ui", "--no-open", *context.args])
    if result:
        raise typer.Exit(code=result)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

"""Rebuild the committed metadata and reports for Tessera's bundled example runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from inspect_ai.log import read_eval_log

from tessera.api.receipts import file_sha256, receipt_from_log
from tessera.report.render import render_markdown
from tessera.report.serialize import report_to_dict
from tessera.store import _json_bytes, _write_atomic

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "src" / "tessera" / "data" / "examples"


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def derive_example(example_dir: Path) -> dict[str, bytes]:
    """Return the four deterministic derived artifacts for one example folder."""
    example_dir = Path(example_dir)
    log_path = example_dir / "log.eval"
    log = read_eval_log(str(log_path.resolve()), resolve_attachments=True).model_copy(
        update={"location": _display_path(log_path)}
    )
    report = report_to_dict(log)
    receipt = receipt_from_log(
        log,
        report,
        artifact_sha256=file_sha256(log_path),
    )
    header = report["header"]
    run = {
        "schema_version": 1,
        "id": example_dir.name,
        "status": "completed",
        "source": "bundled",
        "archived": False,
        "created_at": header["created"],
        "started_at": receipt["timing"]["started_at"],
        "finished_at": receipt["timing"]["completed_at"],
        "request": {
            "suite": header.get("org") or "",
            "model": header["model"],
            "engine": header["engine"],
            "grader": header.get("grader"),
            "k": header["k"],
            "scaffold": header.get("scaffold") or "baseline",
            "seed": header.get("seed") if header.get("seed") is not None else 0,
        },
        "owner": None,
        "error": None,
    }
    return {
        "run.json": _json_bytes(run),
        "report.json": _json_bytes(report),
        "receipt.json": _json_bytes(receipt),
        "report.md": render_markdown(report).encode(),
    }


def rebuild_bundled_examples(root: Path = EXAMPLES_ROOT) -> dict[str, dict[str, bytes]]:
    """Regenerate every bundled example and return the bytes written."""
    derived = {}
    for example_dir in sorted(path for path in Path(root).iterdir() if path.is_dir()):
        files = derive_example(example_dir)
        for name, payload in files.items():
            _write_atomic(example_dir / name, payload)
        derived[example_dir.name] = files
    return derived


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=EXAMPLES_ROOT)
    args = parser.parse_args()
    rebuild_bundled_examples(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

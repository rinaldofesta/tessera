"""tessera-report: read an Inspect .eval log, print a Markdown reliability scorecard.
tessera-leaderboard: read several comparable logs, emit the ADR-0006 leaderboard table."""

from __future__ import annotations

import argparse
import json
import os
import sys

from inspect_ai.log import read_eval_log

from tessera.report.aggregate import (
    aggregate_by, overall_mean_rate, overall_pass_k_rate, reduce_by_probe, summarize_axes,
)
from tessera.report.leaderboard import (
    _is_safe_repo_relative_path, _repo_relative, _sha256_file, extract_rows,
    render_leaderboard, render_manifest, row_metric_mismatches,
)
from tessera.report.log_adapter import eval_log_to_records
from tessera.report.models import ReportError
from tessera.report.render import render_report
from tessera.report.serialize import report_to_dict


def _build_report(log) -> str:
    header, records = eval_log_to_records(log)
    probes = reduce_by_probe(records)
    return render_report(
        header, overall_pass_k_rate(probes), overall_mean_rate(probes),
        aggregate_by(probes), summarize_axes(records), probes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-report",
        description="Render a Tessera reliability scorecard from an Inspect .eval log.")
    parser.add_argument("log", help="path to an Inspect .eval log file")
    parser.add_argument("-o", "--out", help="write Markdown here (default: stdout)")
    args = parser.parse_args(argv)

    try:
        log = read_eval_log(args.log)
    except (FileNotFoundError, OSError, ValueError):
        print(f"cannot read log: {args.log}", file=sys.stderr)
        return 2

    try:
        report = _build_report(log)
    except ReportError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
    else:
        print(report)
    return 0


def _find_repo_root(start: str) -> str:
    """Walk up from `start` to the directory holding `.git`; fall back to `start` itself.
    Both `--extract` (path stamping) and `--verify` (path resolution) anchor here, so a log
    reference is repo-relative regardless of the cwd the maintainer ran the command from."""
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(start)
        d = parent


def _verify_leaderboard(manifest: dict, manifest_path: str) -> int:
    """Re-derive every log-backed row from its committed log and check it reproduces the
    published numbers (ADR-0012). A row with `log: null` is unbacked, not a failure.
    Returns 2 on any missing file / digest / metric mismatch, else 0."""
    repo_root = _find_repo_root(os.path.dirname(os.path.abspath(manifest_path)))
    rows = manifest.get("rows", [])
    backed, unbacked, failures = 0, 0, []
    for row in rows:
        log = row.get("log")
        label = row.get("label") or row.get("model") or "?"
        if not log:
            unbacked += 1
            continue
        path = log.get("path") if isinstance(log, dict) else None
        sha = log.get("sha256") if isinstance(log, dict) else None
        if not path or not sha or not _is_safe_repo_relative_path(path):
            failures.append(f"{label}: malformed or unsafe log reference ({path!r})")
            continue
        abspath = os.path.join(repo_root, path)
        if not os.path.isfile(abspath):
            failures.append(f"{label}: committed log not found at {path}")
            continue
        if _sha256_file(abspath) != sha:
            failures.append(f"{label}: sha256 does not match the committed {path}")
            continue
        try:
            derived = extract_rows([report_to_dict(read_eval_log(abspath))])[0]
        except (ReportError, ValueError, OSError) as exc:
            failures.append(f"{label}: cannot re-derive from {path} ({exc})")
            continue
        mism = row_metric_mismatches(row, derived)
        if mism:
            failures.append(f"{label}: {path} does not reproduce {', '.join(mism)}")
            continue
        backed += 1
    summary = (f"verified {backed}/{len(rows)} rows against a committed log; "
               f"{unbacked} unbacked (log: null)")
    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        print(summary, file=sys.stderr)
        return 2
    print(summary)
    return 0


def leaderboard_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-leaderboard",
        description="Render, extract, or verify the ADR-0006 leaderboard.")
    parser.add_argument("logs", nargs="*", help="paths to Inspect .eval log files")
    parser.add_argument("--manifest",
                        help="the leaderboard manifest JSON (ADR-0010): render it to Markdown, "
                             "or --verify it; no logs needed")
    parser.add_argument("--extract", action="store_true",
                        help="emit manifest-row JSON from the logs (with a repo-relative "
                             "{path, sha256} log stamp) to merge into the manifest")
    parser.add_argument("--verify", action="store_true",
                        help="with --manifest: re-derive every log-backed row from its "
                             "committed log and fail on any digest or metric mismatch")
    parser.add_argument("--label", action="append", default=[],
                        help="row label, positional with the logs (default: the model)")
    parser.add_argument("--note", action="append", default=[],
                        help="row note, positional with the logs (e.g. 'open-weights, local')")
    parser.add_argument("--title", help="override the document title")
    parser.add_argument("-o", "--out", help="write output here (default: stdout)")
    args = parser.parse_args(argv)

    def _emit(text: str) -> None:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(text)
        else:
            print(text)

    # Manifest actions: verify against committed logs, or render to Markdown. No logs needed.
    if args.manifest:
        try:
            with open(args.manifest, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (FileNotFoundError, OSError, ValueError) as exc:
            print(f"cannot read manifest: {args.manifest} ({exc})", file=sys.stderr)
            return 2
        if args.verify:
            return _verify_leaderboard(manifest, args.manifest)
        try:
            _emit(render_manifest(manifest))
        except (ValueError, KeyError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return 0

    if args.verify:
        print("--verify requires --manifest <file>", file=sys.stderr)
        return 2

    reports = []
    for path in args.logs:
        try:
            reports.append(report_to_dict(read_eval_log(path)))
        except (FileNotFoundError, OSError, ValueError) as exc:
            print(f"cannot read log: {path} ({exc})", file=sys.stderr)
            return 2
        except ReportError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if not reports:
        print("provide one or more .eval logs, or --manifest <file>", file=sys.stderr)
        return 2

    # Extract: the row a manifest must carry, its numbers guaranteed to match a real log and
    # its log stamped {path (repo-relative), sha256} so --verify can find and check it later.
    if args.extract:
        repo_root = _find_repo_root(os.getcwd())
        rows = extract_rows(reports, labels=args.label, notes=args.note)
        for i, row in enumerate(rows):
            logpath = args.logs[i]
            try:
                rel = _repo_relative(os.path.abspath(logpath), repo_root)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
            row["log"] = {"path": rel, "sha256": _sha256_file(logpath)}
        _emit(json.dumps(rows, indent=2))
        return 0

    try:
        _emit(render_leaderboard(reports, labels=args.label, notes=args.note,
                                 title=args.title))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

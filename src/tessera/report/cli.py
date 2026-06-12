"""tessera-report: read an Inspect .eval log, print a Markdown reliability scorecard.
tessera-leaderboard: read several comparable logs, emit the ADR-0006 leaderboard table."""

from __future__ import annotations

import argparse
import sys

from inspect_ai.log import read_eval_log

from tessera.report.aggregate import (
    aggregate_by, overall_mean_rate, overall_pass_k_rate, reduce_by_probe, summarize_axes,
)
from tessera.report.leaderboard import render_leaderboard
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


def leaderboard_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-leaderboard",
        description="Render the ADR-0006 leaderboard table from comparable .eval logs.")
    parser.add_argument("logs", nargs="+", help="paths to Inspect .eval log files")
    parser.add_argument("--label", action="append", default=[],
                        help="row label, positional with the logs (default: the model)")
    parser.add_argument("--note", action="append", default=[],
                        help="row note, positional with the logs (e.g. 'open-weights, local')")
    parser.add_argument("--title", help="override the document title")
    parser.add_argument("-o", "--out", help="write Markdown here (default: stdout)")
    args = parser.parse_args(argv)

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

    try:
        markdown = render_leaderboard(reports, labels=args.label, notes=args.note,
                                      title=args.title)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(markdown)
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

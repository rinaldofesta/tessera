"""tessera-report: read an Inspect .eval log, print a Markdown reliability scorecard."""

from __future__ import annotations

import argparse
import sys

from inspect_ai.log import read_eval_log

from tessera.report.aggregate import (
    aggregate_by, overall_mean_rate, overall_pass_k_rate, reduce_by_probe, summarize_axes,
)
from tessera.report.log_adapter import eval_log_to_records
from tessera.report.models import ReportError
from tessera.report.render import render_report


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


if __name__ == "__main__":
    raise SystemExit(main())

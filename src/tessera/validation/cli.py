"""CLI for the public synthetic-to-real transfer analysis."""

from __future__ import annotations

import argparse
import json
import sys

from .analysis import StudyError, analyze_study, render_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tessera-validate-transfer",
        description="Analyze a pre-registered synthetic-to-real rank-transfer study.",
    )
    parser.add_argument("study", help="JSON file containing task-level scores")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    parser.add_argument("-o", "--out", help="write output here instead of stdout")
    args = parser.parse_args(argv)

    try:
        with open(args.study, encoding="utf-8") as handle:
            study = json.load(handle)
        result = analyze_study(study)
    except (OSError, ValueError, StudyError) as exc:
        print(f"cannot analyze study: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n" if args.json \
        else render_markdown(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        print(rendered, end="")
    return 0

"""CLI for the public synthetic-to-real transfer analysis."""

from __future__ import annotations

import argparse
import json
import sys

from .analysis import StudyError, analyze_study, render_markdown


def _object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise StudyError("duplicate JSON object key")
        result[key] = value
    return result


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
            study = json.load(handle, object_pairs_hook=_object_without_duplicate_keys)
    except OSError as exc:
        print(f"cannot read study: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"cannot analyze study: {exc}", file=sys.stderr)
        return 2

    try:
        result = analyze_study(study)
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n" if args.json \
            else render_markdown(result)
    except ValueError as exc:
        print(f"cannot analyze study: {exc}", file=sys.stderr)
        return 2

    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(rendered)
        else:
            print(rendered, end="")
    except OSError as exc:
        print(f"cannot write output: {exc}", file=sys.stderr)
        return 1
    return 0

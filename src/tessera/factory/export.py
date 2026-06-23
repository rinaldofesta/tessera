# src/tessera/factory/export.py
"""Freeze a variant + its answer key to JSON. Exporting into the API-served `blueprints/`
store IS the reveal of a holdout seed (the blueprint becomes runnable by name and visible
in /api/orgs); do not export a still-withheld seed there. See ADR-0008."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tessera.factory.generate import generate_variant
from tessera.factory.schema import FACTORY_VERSION


def export_variant(seed: int, out_dir: str | Path) -> tuple[Path, Path]:
    """Write meridian-seed{N}.blueprint.json + .answers.json; return their paths."""
    bp = generate_variant(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bp_path = out / f"meridian-seed{seed}.blueprint.json"
    ans_path = out / f"meridian-seed{seed}.answers.json"

    bp_path.write_text(bp.model_dump_json(indent=2) + "\n")
    answers = {
        "seed": seed,
        "factory_version": FACTORY_VERSION,
        "answers": {
            p.probe_id: {
                "expected_behavior": p.expected_behavior.value,
                "expected_answer": p.expected_answer,
                "expected_sources": list(p.expected_sources),
            }
            for p in bp.probes
        },
    }
    ans_path.write_text(json.dumps(answers, indent=2, sort_keys=True) + "\n")
    return bp_path, ans_path


def main() -> None:
    parser = argparse.ArgumentParser(prog="tessera-variant")
    sub = parser.add_subparsers(dest="command", required=True)
    exp = sub.add_parser("export", help="freeze a variant + answer key to JSON")
    exp.add_argument("--seed", type=int, required=True)
    exp.add_argument("--out", default="blueprints/",
                     help="output dir (default blueprints/ — note: this REVEALS the seed)")
    args = parser.parse_args()
    if args.command == "export":
        bp_path, ans_path = export_variant(args.seed, args.out)
        print(f"wrote {bp_path}\nwrote {ans_path}")


if __name__ == "__main__":
    main()

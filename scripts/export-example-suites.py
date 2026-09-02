"""Export the built-in suites and authoring template as tracked examples."""

from __future__ import annotations

from pathlib import Path

from tessera.examples import ORGS

ROOT = Path(__file__).resolve().parents[1]
SUITES = ROOT / "examples" / "suites"
BUILTINS = {"starter.json": "toy", "meridian.json": "meridian"}


def export_example_suites() -> None:
    # Build straight from the ORGS registry, not orgs.get_blueprint() — that helper
    # prefers a same-named file already saved in the ambient blueprint store (and the
    # store auto-seeds "toy.json"/"meridian.json" the first time any blueprint list is
    # read), so it can silently export edited, non-canonical content instead of the
    # true built-in.
    SUITES.mkdir(parents=True, exist_ok=True)
    for filename, org in BUILTINS.items():
        rendered = ORGS[org]().model_dump_json(indent=2, by_alias=True) + "\n"
        (SUITES / filename).write_text(rendered, encoding="utf-8")
    template = ROOT / "src" / "tessera" / "data" / "templates" / "suite.json"
    (SUITES / "my-company.json").write_bytes(template.read_bytes())


if __name__ == "__main__":
    export_example_suites()

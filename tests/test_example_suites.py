"""The tracked suite examples stay valid and reproducible from their sources."""

import json
from pathlib import Path

import pytest

from tessera.api import blueprint_store
from tessera.examples import ORGS

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "suites"
TEMPLATE = ROOT / "src" / "tessera" / "data" / "templates" / "suite.json"


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda path: path.name)
def test_every_example_suite_validates_and_compiles(path):
    blueprint, issues = blueprint_store.validate_and_build(
        json.loads(path.read_text(encoding="utf-8"))
    )

    assert issues == []
    assert blueprint is not None


@pytest.mark.parametrize("filename,org", [("starter.json", "toy"), ("meridian.json", "meridian")])
def test_builtin_example_suites_are_reproducible(filename, org):
    # Compare against the ORGS builder directly, not orgs.get_blueprint() — that helper
    # would prefer a same-named file in the ambient blueprint store if one happened to
    # exist there, which defeats the point of this reproducibility check.
    expected = (ORGS[org]().model_dump_json(indent=2, by_alias=True) + "\n").encode()

    assert (EXAMPLES / filename).read_bytes() == expected


def test_authored_example_matches_packaged_template():
    assert (EXAMPLES / "my-company.json").read_bytes() == TEMPLATE.read_bytes()

"""Behavior tests for the deterministic compiler.

The compiler turns a Blueprint into the physical assets the MCP silo servers
host (structured ``crm/db.json``, unstructured ``docs/*.md``) plus a
``manifest.json`` mapping every claim_id back to its physical location -- the
bridge that lets the scorer resolve a ToolEvent to a specific claim.
"""

import json

import pytest

from tessera.compiler import compile_blueprint
from tessera.models import Blueprint, Claim


def _toy_blueprint() -> Blueprint:
    """A two-silo org exercising cross-reference, conflict, and structured/prose."""
    return Blueprint(
        claims=[
            Claim(
                claim_id="acme.tier.crm",
                subject="Acme Corp",
                predicate="tier",
                value="Gold",
                silo="crm",
                render={"as": "field"},
            ),
            Claim(
                claim_id="acme.renewal.crm",
                subject="Acme Corp",
                predicate="renewal_date",
                value="2026-01-01",
                silo="crm",
                asserted_at="2025-11-15T10:00:00Z",
                render={"as": "field"},
            ),
            Claim(
                claim_id="acme.renewal.note",
                subject="Acme Corp",
                predicate="renewal_date",
                value="2026-03-01",
                silo="docs",
                asserted_at="2026-02-10T14:30:00Z",
                render={"as": "prose", "template": "Renewal pushed to {value} per the QBR."},
            ),
            Claim(
                claim_id="sla.gold.docs",
                subject="Gold tier",
                predicate="sla_hours",
                value=4,
                silo="docs",
                render={"as": "prose", "template": "Gold-tier SLA is {value}h."},
            ),
        ]
    )


def test_structured_silo_groups_by_subject_with_per_field_timestamps(tmp_path):
    compile_blueprint(_toy_blueprint(), tmp_path)
    db = json.loads((tmp_path / "crm" / "db.json").read_text())
    # Each field carries its own (nullable) asserted_at, so the agent can reason about
    # recency and recognize a genuine tie. tier has no timestamp -> null.
    assert db == {
        "Acme Corp": {
            "tier": {"value": "Gold", "asserted_at": None},
            "renewal_date": {"value": "2026-01-01", "asserted_at": "2025-11-15T10:00:00Z"},
        }
    }


def test_prose_claim_written_with_frontmatter_and_rendered_body(tmp_path):
    manifest = compile_blueprint(_toy_blueprint(), tmp_path)
    artifact = manifest["acme.renewal.note"]["artifact"]
    content = (tmp_path / artifact).read_text()
    assert "source_id: acme.renewal.note" in content
    assert "asserted_at: 2026-02-10T14:30:00Z" in content
    assert "Renewal pushed to 2026-03-01 per the QBR." in content


def test_prose_claim_lands_in_its_own_silo_folder(tmp_path):
    manifest = compile_blueprint(_toy_blueprint(), tmp_path)
    assert manifest["sla.gold.docs"]["artifact"].startswith("docs/")
    assert manifest["sla.gold.docs"]["artifact"].endswith(".md")


def test_manifest_maps_field_claim_with_subject_and_predicate(tmp_path):
    manifest = compile_blueprint(_toy_blueprint(), tmp_path)
    assert manifest["acme.renewal.crm"] == {
        "silo": "crm",
        "subject": "Acme Corp",
        "predicate": "renewal_date",
        "artifact": "crm/db.json",
        "locator": "Acme Corp.renewal_date",
    }


def test_manifest_carries_subject_for_prose_claims(tmp_path):
    manifest = compile_blueprint(_toy_blueprint(), tmp_path)
    entry = manifest["acme.renewal.note"]
    assert entry["subject"] == "Acme Corp"
    assert entry["predicate"] == "renewal_date"
    assert entry["silo"] == "docs"
    assert entry["artifact"].startswith("docs/") and entry["artifact"].endswith(".md")


def test_manifest_persisted_with_every_claim(tmp_path):
    compile_blueprint(_toy_blueprint(), tmp_path)
    on_disk = json.loads((tmp_path / "manifest.json").read_text())
    assert set(on_disk) == {
        "acme.tier.crm",
        "acme.renewal.crm",
        "acme.renewal.note",
        "sla.gold.docs",
    }


def test_intra_silo_collision_is_rejected(tmp_path):
    bp = Blueprint(
        claims=[
            Claim(claim_id="a", subject="Acme Corp", predicate="tier",
                  value="Gold", silo="crm", render={"as": "field"}),
            Claim(claim_id="b", subject="Acme Corp", predicate="tier",
                  value="Silver", silo="crm", render={"as": "field"}),
        ]
    )
    with pytest.raises(ValueError):
        compile_blueprint(bp, tmp_path)


def test_compiler_is_deterministic(tmp_path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    compile_blueprint(_toy_blueprint(), out_a)
    compile_blueprint(_toy_blueprint(), out_b)
    assert (out_a / "crm" / "db.json").read_text() == (out_b / "crm" / "db.json").read_text()
    assert (out_a / "manifest.json").read_text() == (out_b / "manifest.json").read_text()

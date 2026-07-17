from tessera.silos.builtin import CRM, DOCS
from tessera.silos.registry import registry


MANIFEST = {
    "acme.tier.crm": {
        "silo": "crm", "subject": "Acme Corp", "predicate": "tier",
        "artifact": "crm/db.json", "locator": "Acme Corp.tier",
    },
    "sla.gold.docs": {
        "silo": "docs", "subject": "Gold tier", "predicate": "sla_hours",
        "artifact": "docs/gold-tier-sla-hours.md",
    },
}


def test_importing_silos_registers_builtins():
    assert "crm" in registry.names()
    assert "docs" in registry.names()
    assert registry.get("crm") is CRM
    assert registry.get("docs") is DOCS


def test_crm_consulted_credits_matching_subject_and_fields():
    # result payload: same shape test_scoring.py feeds consulted_claims for crm_lookup
    result = '{"tier": {"value": "Gold"}}'
    credited = CRM.consulted("crm_lookup", {"account_name": "Acme Corp"}, result, MANIFEST)
    assert credited == {"acme.tier.crm"}


def test_crm_consulted_ignores_other_tools():
    assert CRM.consulted("docs_get_file", {"path": "x"}, "", MANIFEST) == set()


def test_docs_consulted_credits_artifact_path():
    credited = DOCS.consulted(
        "docs_get_file", {"path": "docs/gold-tier-sla-hours.md"}, "...", MANIFEST
    )
    assert credited == {"sla.gold.docs"}


def test_docs_consulted_ignores_search():
    assert DOCS.consulted("docs_search", {"query": "sla"}, "[]", MANIFEST) == set()


def test_register_builtins_does_not_trigger_entry_point_loading(monkeypatch):
    calls = []

    def recorder(*, group):
        calls.append(group)
        return []

    monkeypatch.setattr("tessera.silos.registry.entry_points", recorder)
    import tessera.silos.builtin as builtin_module

    builtin_module.register_builtins()  # idempotent: builtins already registered
    assert calls == []

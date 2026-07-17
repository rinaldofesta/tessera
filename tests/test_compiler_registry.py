import json

import tessera.compiler as compiler_mod
from tessera.compiler import build_artifacts, compile_blueprint
from tessera.examples.toy_org import build_toy_blueprint
from tessera.models import Claim
from tessera.silos.builtin import CRM, DOCS
from tessera.silos.registry import SiloRegistry, SiloType


def _notes_silo_type():
    def build(claims):
        payload = {c.claim_id: c.value for c in claims}
        entries = {
            c.claim_id: {"silo": "notes", "subject": c.subject, "predicate": c.predicate,
                         "artifact": "notes/notes.json", "locator": c.claim_id}
            for c in claims
        }
        return payload, entries

    def write(payload, out_dir):
        target = out_dir / "notes"
        target.mkdir(parents=True, exist_ok=True)
        (target / "notes.json").write_text(json.dumps(payload))

    return SiloType(
        name="notes", server_module="x.notes_server", tool_names=("notes_get",),
        prompt_blurb="notes", consulted=lambda t, a, r, m: set(),
        build=build, write=write,
    )


def _registry_with(*extra):
    reg = SiloRegistry()
    reg.register(CRM)
    reg.register(DOCS)
    for st in extra:
        reg.register(st)
    return reg


def test_no_plugins_key_for_builtin_only_blueprints(monkeypatch):
    monkeypatch.setattr(compiler_mod, "silo_registry", _registry_with())
    art = build_artifacts(build_toy_blueprint())
    assert set(art) == {"manifest", "silos", "docs"}


def test_manifest_order_preserved_for_builtin_only_blueprints(monkeypatch):
    monkeypatch.setattr(compiler_mod, "silo_registry", _registry_with())
    bp = build_toy_blueprint()
    art = build_artifacts(bp)
    assert list(art["manifest"]) == [c.claim_id for c in bp.claims]


def test_custom_build_collects_payload_and_manifest(monkeypatch):
    monkeypatch.setattr(compiler_mod, "silo_registry", _registry_with(_notes_silo_type()))
    bp = build_toy_blueprint().model_copy(deep=True)
    bp.claims.append(
        Claim(claim_id="note.1", subject="Acme Corp", predicate="note",
              value="check SLA", silo="notes", render={"as": "field"})
    )
    art = build_artifacts(bp)
    assert art["plugins"] == {"notes": {"note.1": "check SLA"}}
    assert art["manifest"]["note.1"]["artifact"] == "notes/notes.json"


def test_custom_write_called_on_compile(monkeypatch, tmp_path):
    monkeypatch.setattr(compiler_mod, "silo_registry", _registry_with(_notes_silo_type()))
    bp = build_toy_blueprint().model_copy(deep=True)
    bp.claims.append(
        Claim(claim_id="note.1", subject="Acme Corp", predicate="note",
              value="check SLA", silo="notes", render={"as": "field"})
    )
    compile_blueprint(bp, tmp_path)
    assert json.loads((tmp_path / "notes" / "notes.json").read_text()) == {"note.1": "check SLA"}

from tessera.evals.scoring import consulted_claims
from tessera.silos.registry import SiloType

import tessera.evals.scoring as scoring_mod
from tessera.silos.registry import SiloRegistry


def test_consulted_claims_dispatches_to_registered_silo_type(monkeypatch):
    seen = []

    def fake_consulted(tool, args, result, manifest):
        seen.append(tool)
        return {"claim.x"}

    st = SiloType(
        name="wiki",
        server_module="tessera.mcp.wiki_server",
        tool_names=("wiki_get",),
        prompt_blurb="a wiki",
        consulted=fake_consulted,
    )
    reg = SiloRegistry()
    reg.register(st)
    monkeypatch.setattr(scoring_mod, "silo_registry", reg)

    credited = consulted_claims([("wiki_get", {"page": "p"}, "body")], {})
    assert credited == {"claim.x"}
    assert seen == ["wiki_get"]


def test_consulted_claims_unknown_tool_credits_nothing(monkeypatch):
    monkeypatch.setattr(scoring_mod, "silo_registry", SiloRegistry())
    assert consulted_claims([("mystery_tool", {}, "")], {}) == set()

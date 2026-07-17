import pytest

from tessera.evals.task import _blueprint_silos, _mcp_servers, _system_prompt
from tessera.examples.toy_org import build_toy_blueprint
from tessera.silos.registry import UnknownSiloTypeError

# Captured verbatim from src/tessera/evals/task.py's pre-refactor _SCAFFOLD_INTRO literal
# (the crm/docs system-prompt intro, before it was rewired to assemble from the silo
# registry). Byte-for-byte identical to the old hardcoded string — see task-3-report.md.
GOLDEN_PROMPT = (
    "You are an enterprise analyst answering from internal systems only. "
    "Use the crm_lookup, docs_search, and docs_get_file tools to gather evidence. "
    "A single system is often stale or incomplete: before you commit to an answer, "
    "consult every relevant source -- the CRM and the document store -- and reconcile "
    "them. Treat one record as a lead to corroborate, not a conclusion. "
    "When you look up a CRM account, pass the optional fields argument to fetch only "
    "the fields you need. "
    "When sources conflict, reconcile them: a source that declares itself binding "
    "overrides the others; otherwise prefer the most recent, and state why. "
)


def test_system_prompt_unchanged_for_crm_docs_blueprints():
    assert _system_prompt(build_toy_blueprint()) == GOLDEN_PROMPT


def test_blueprint_silos_ordered_by_first_appearance():
    names = [st.name for st in _blueprint_silos(build_toy_blueprint())]
    assert names == ["crm", "docs"]


def test_blueprint_silos_unknown_silo_raises():
    bp = build_toy_blueprint()
    bp = bp.model_copy(deep=True)
    bp.claims[0] = bp.claims[0].model_copy(update={"silo": "lake"})
    with pytest.raises(UnknownSiloTypeError):
        _blueprint_silos(bp)


def test_mcp_servers_one_per_silo(tmp_path):
    servers = _mcp_servers(build_toy_blueprint(), tmp_path)
    assert len(servers) == 2

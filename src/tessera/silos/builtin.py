"""Built-in silo types: crm and docs."""

from __future__ import annotations

import json
from typing import Any

from tessera.silos.registry import SiloType, registry


# --- moved from tessera.evals.scoring (Task 4 deletes the original) ---
def _crm_record_fields(result: str | None) -> frozenset[str]:
    """The field names a crm_lookup actually returned; empty for NOT_FOUND/errors."""
    if not result:
        return frozenset()
    try:
        record = json.loads(result)
    except ValueError:
        return frozenset()
    return frozenset(record) if isinstance(record, dict) else frozenset()


def _crm_consulted(
    tool_name: str, args: dict[str, Any], result: Any, manifest: dict[str, dict[str, Any]]
) -> set[str]:
    if tool_name != "crm_lookup":
        return set()
    subject = args.get("account_name")
    fields = _crm_record_fields(result)
    return {
        cid
        for cid, m in manifest.items()
        if m.get("silo") == "crm"
        and m.get("subject") == subject
        and m.get("predicate") in fields
    }


def _docs_consulted(
    tool_name: str, args: dict[str, Any], result: Any, manifest: dict[str, dict[str, Any]]
) -> set[str]:
    if tool_name != "docs_get_file":
        return set()
    path = args.get("path")
    return {cid for cid, m in manifest.items() if m.get("artifact") == path}


# The two prompt_blurbs below are cut from the single legacy literal in
# tessera.evals.task (now _PROMPT_TEMPLATE + _system_prompt) so that, concatenated in
# blueprint order (crm before docs), they reproduce it byte-for-byte: the sentence
# naming every tool ("Use the crm_lookup, docs_search, and docs_get_file tools ...")
# spans both silos and doesn't split along a silo boundary, so CRM's blurb keeps that
# whole shared sentence plus its own fields-argument quirk, and DOCS's blurb keeps the
# closing conflict-resolution rule. See task-3-report.md for the full derivation.
CRM = SiloType(
    name="crm",
    server_module="tessera.mcp.crm_server",
    tool_names=("crm_lookup",),
    prompt_blurb=(
        "Use the crm_lookup, docs_search, and docs_get_file tools to gather evidence. "
        "A single system is often stale or incomplete: before you commit to an answer, "
        "consult every relevant source -- the CRM and the document store -- and reconcile "
        "them. Treat one record as a lead to corroborate, not a conclusion. "
        "When you look up a CRM account, pass the optional fields argument to fetch only "
        "the fields you need. "
    ),
    consulted=_crm_consulted,
)

DOCS = SiloType(
    name="docs",
    server_module="tessera.mcp.docs_server",
    tool_names=("docs_search", "docs_get_file"),
    prompt_blurb=(
        "When sources conflict, reconcile them: a source that declares itself binding "
        "overrides the others; otherwise prefer the most recent, and state why. "
    ),
    consulted=_docs_consulted,
)


def register_builtins() -> None:
    for st in (CRM, DOCS):
        if not registry.is_registered(st.name):
            registry.register(st)


register_builtins()

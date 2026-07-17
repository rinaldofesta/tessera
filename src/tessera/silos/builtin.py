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


CRM = SiloType(
    name="crm",
    server_module="tessera.mcp.crm_server",
    tool_names=("crm_lookup",),
    prompt_blurb="",  # filled in Task 3 to reproduce the current system prompt
    consulted=_crm_consulted,
)

DOCS = SiloType(
    name="docs",
    server_module="tessera.mcp.docs_server",
    tool_names=("docs_search", "docs_get_file"),
    prompt_blurb="",  # filled in Task 3
    consulted=_docs_consulted,
)


def register_builtins() -> None:
    for st in (CRM, DOCS):
        if st.name not in registry.names():
            registry.register(st)


register_builtins()

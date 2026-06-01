"""Pure read access over a compiled organization (no MCP dependency)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def crm_lookup_record(out_dir: str | Path, account_name: str) -> dict[str, Any] | None:
    """Return the flattened CRM record for an account, or None if absent."""
    db_path = Path(out_dir) / "crm" / "db.json"
    if not db_path.exists():
        return None
    db = json.loads(db_path.read_text())
    return db.get(account_name)


def docs_search(out_dir: str | Path, query: str) -> list[dict[str, str]]:
    """Case-insensitive substring search over Docs files. Returns [{path, excerpt}]."""
    docs_dir = Path(out_dir) / "docs"
    if not docs_dir.exists():
        return []
    needle = query.lower()
    hits: list[dict[str, str]] = []
    for md in sorted(docs_dir.glob("*.md")):
        text = md.read_text()
        if needle in text.lower():
            rel = f"docs/{md.name}"
            hits.append({"path": rel, "excerpt": text.strip().splitlines()[-1][:200]})
    return hits


def docs_get_file(out_dir: str | Path, path: str) -> str:
    """Return a Docs file's content. `path` is relative to out_dir (e.g. 'docs/x.md')."""
    out = Path(out_dir).resolve()
    target = (out / path).resolve()
    docs_root = (out / "docs").resolve()
    if docs_root not in target.parents and target != docs_root:
        raise ValueError(f"refusing to read outside docs/: {path!r}")
    if not target.exists():
        raise ValueError(f"no such doc: {path!r}")
    return target.read_text()

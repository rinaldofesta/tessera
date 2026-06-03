"""Pure read access over a compiled organization (no MCP dependency)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def crm_lookup_record(out_dir: str | Path, account_name: str) -> dict[str, Any] | None:
    """Return the flattened CRM record for an account, or None if absent."""
    db_path = Path(out_dir) / "crm" / "db.json"
    if not db_path.exists():
        return None
    db = json.loads(db_path.read_text())
    return db.get(account_name)


def docs_search(out_dir: str | Path, query: str) -> list[dict[str, str]]:
    """Keyword search over Docs files. Returns [{path, excerpt}], best match first.

    Tokenizes the query and matches terms (>= 3 chars, case-insensitive) against each
    file's NAME and body, ranking by how many distinct terms hit. Real search engines
    index titles/paths alongside body text and match on terms -- not on the whole query
    as one literal substring (which essentially never matches a natural-language query).
    """
    docs_dir = Path(out_dir) / "docs"
    if not docs_dir.exists():
        return []
    terms = {t for t in _TOKEN_RE.findall(query.lower()) if len(t) >= 3}
    if not terms:
        return []
    ranked: list[tuple[int, str, dict[str, str]]] = []
    for md in sorted(docs_dir.glob("*.md")):
        body = md.read_text()
        haystack = f"{md.name}\n{body}".lower()
        score = sum(1 for t in terms if t in haystack)
        if score:
            excerpt = (body.strip().splitlines() or [""])[-1][:200]
            ranked.append((score, md.name, {"path": f"docs/{md.name}", "excerpt": excerpt}))
    ranked.sort(key=lambda r: (-r[0], r[1]))  # most terms first; filename breaks ties
    return [hit for _, _, hit in ranked]


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

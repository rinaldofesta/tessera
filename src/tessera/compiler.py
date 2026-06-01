"""Deterministic compiler: Blueprint -> silo assets + provenance manifest.

The compiler is the only component that understands fracture semantics. The MCP
silo servers stay dumb -- they just serve the files this produces:

    <out>/<silo>/db.json   structured claims, grouped by subject
    <out>/<silo>/<slug>.md prose claims, frontmatter + rendered body
    <out>/manifest.json    claim_id -> {silo, artifact, locator}

The manifest is the bridge the scorer uses to resolve a recorded tool call back
to a specific claim_id, turning "hit the CRM" into "read the note carrying
acme.renewal.note".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Blueprint, RenderAs


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys keeps output deterministic regardless of claim ordering.
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _doc_content(asserted_at: str | None, claim_id: str, body: str) -> str:
    front: dict[str, str] = {}
    if asserted_at is not None:
        front["asserted_at"] = asserted_at
    front["source_id"] = claim_id
    frontmatter = "\n".join(f"{k}: {v}" for k, v in front.items())
    return f"---\n{frontmatter}\n---\n\n{body}\n"


def compile_blueprint(blueprint: Blueprint, out_dir: str | Path) -> dict[str, dict]:
    """Compile ``blueprint`` into ``out_dir`` and return the provenance manifest.

    Raises ``ValueError`` on an intra-silo ``(subject, predicate)`` collision:
    in v0 contradictions must be cross-silo (see the design spec).
    """
    out = Path(out_dir)

    seen: set[tuple[str, str, str]] = set()
    for claim in blueprint.claims:
        key = (claim.silo, claim.subject, claim.predicate)
        if key in seen:
            raise ValueError(
                f"intra-silo collision in silo {claim.silo!r}: "
                f"{claim.subject!r}/{claim.predicate!r} asserted twice"
            )
        seen.add(key)

    structured: dict[str, dict[str, dict]] = {}  # silo -> subject -> {predicate: value}
    docs: list[tuple[Path, str]] = []
    manifest: dict[str, dict] = {}

    for claim in blueprint.claims:
        if claim.render.as_ is RenderAs.field:
            structured.setdefault(claim.silo, {}).setdefault(claim.subject, {})[
                claim.predicate
            ] = claim.value
            manifest[claim.claim_id] = {
                "silo": claim.silo,
                "artifact": f"{claim.silo}/db.json",
                "locator": f"{claim.subject}.{claim.predicate}",
            }
        else:  # prose
            rel = f"{claim.silo}/{_slug(f'{claim.subject}-{claim.predicate}-{claim.claim_id}')}.md"
            body = claim.render.template.format(value=claim.value)
            docs.append((out / rel, _doc_content(claim.asserted_at, claim.claim_id, body)))
            manifest[claim.claim_id] = {
                "silo": claim.silo,
                "artifact": rel,
                "locator": rel,
            }

    for silo, subjects in structured.items():
        _write_json(out / silo / "db.json", subjects)

    for path, content in docs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    _write_json(out / "manifest.json", manifest)

    return manifest

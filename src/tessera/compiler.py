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
from typing import Any

from .models import Blueprint, Claim, RenderAs
from .paths import contained_target
from .silos import registry as silo_types


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


def build_artifacts(blueprint: Blueprint) -> dict:
    """Pure: turn ``blueprint`` into in-memory artifacts. NO disk writes, NO eval.

    Returns ``{"manifest": {...}, "silos": {silo: {subject: {predicate: {...}}}},
    "docs": [{"path": rel, "content": str}]}``. This is what powers the compile-PREVIEW
    endpoint (show the resulting org without materializing it). Raises ``ValueError`` on
    an intra-silo ``(subject, predicate)`` collision: contradictions must be cross-silo.
    A ``"plugins"`` key (mapping silo name to opaque payload) is present only when a
    claim's silo type defines a custom ``build`` hook.
    """
    seen: set[tuple[str, str, str]] = set()
    for claim in blueprint.claims:
        key = (claim.silo, claim.subject, claim.predicate)
        if key in seen:
            raise ValueError(
                f"intra-silo collision in silo {claim.silo!r}: "
                f"{claim.subject!r}/{claim.predicate!r} asserted twice"
            )
        seen.add(key)

    silos: dict[str, dict[str, dict]] = {}  # silo -> subject -> {predicate: value}
    docs: list[dict[str, str]] = []
    manifest: dict[str, dict] = {}
    custom_claims: dict[str, list[Claim]] = {}

    for claim in blueprint.claims:
        st = silo_types.registry.get(claim.silo)
        if st.build is not None:
            custom_claims.setdefault(claim.silo, []).append(claim)
            continue
        if claim.render.as_ is RenderAs.field:
            silos.setdefault(claim.silo, {}).setdefault(claim.subject, {})[
                claim.predicate
            ] = {"value": claim.value, "asserted_at": claim.asserted_at}
            manifest[claim.claim_id] = {
                "silo": claim.silo,
                "subject": claim.subject,
                "predicate": claim.predicate,
                "artifact": f"{claim.silo}/db.json",
                "locator": f"{claim.subject}.{claim.predicate}",
            }
        else:  # prose
            rel = f"{claim.silo}/{_slug(f'{claim.subject}-{claim.predicate}-{claim.claim_id}')}.md"
            body = claim.render.template.format(value=claim.value)
            docs.append({"path": rel, "content": _doc_content(claim.asserted_at, claim.claim_id, body)})
            manifest[claim.claim_id] = {
                "silo": claim.silo,
                "subject": claim.subject,
                "predicate": claim.predicate,
                "artifact": rel,
                "locator": rel,
            }

    plugins: dict[str, Any] = {}
    for silo_name, claims in custom_claims.items():
        payload, entries = silo_types.registry.get(silo_name).build(claims)
        plugins[silo_name] = payload
        manifest.update(entries)

    artifacts = {"manifest": manifest, "silos": silos, "docs": docs}
    if plugins:
        artifacts["plugins"] = plugins
    return artifacts


def _write_target(out: Path, path: Path) -> Path:
    target = contained_target(out, path)
    if target is None:
        raise ValueError(f"refusing to write outside {out}: {path}")
    return target


def _check_plugin_tree(out: Path, root: Path) -> None:
    # Each hook chooses its own filenames, so check its existing subtree before handing it control.
    pending = [root]
    visited = set()
    while pending:
        target = _write_target(out, pending.pop())
        if target not in visited and target.is_dir():
            visited.add(target)
            pending.extend(target.iterdir())


def write_artifacts(artifacts: dict, out_dir: str | Path) -> dict[str, dict]:
    """Materialize the artifacts from ``build_artifacts`` to disk; return the manifest."""
    out = Path(out_dir).resolve()
    databases = [(_write_target(out, out / silo / "db.json"), subjects)
                 for silo, subjects in artifacts["silos"].items()]
    documents = [(_write_target(out, out / doc["path"]), doc["content"])
                 for doc in artifacts["docs"]]
    manifest_path = _write_target(out, out / "manifest.json")
    plugins = artifacts.get("plugins", {})
    for silo_name in plugins:
        _check_plugin_tree(out, out / silo_name)

    for path, subjects in databases:
        _write_json(path, subjects)
    for path, content in documents:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    _write_json(manifest_path, artifacts["manifest"])
    for silo_name, payload in plugins.items():
        silo_types.registry.get(silo_name).write(payload, out)
    return artifacts["manifest"]


def compile_blueprint(blueprint: Blueprint, out_dir: str | Path) -> dict[str, dict]:
    """Compile ``blueprint`` into ``out_dir`` and return the provenance manifest.

    Raises ``ValueError`` on an intra-silo ``(subject, predicate)`` collision.
    """
    return write_artifacts(build_artifacts(blueprint), out_dir)

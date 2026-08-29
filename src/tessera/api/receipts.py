"""Immutable identity and provenance receipts for workbench evaluations.

Receipts deliberately contain configuration and measurements only. They never inspect
provider credentials and are safe to persist and return from the API.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from tessera import __version__


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _duration_seconds(started: str | None, completed: str | None) -> float | None:
    if not started or not completed:
        return None
    try:
        return max(0.0, (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds())
    except (TypeError, ValueError):
        return None


def _usage(log) -> dict[str, int | float | None]:
    usages = getattr(getattr(log, "stats", None), "model_usage", None) or {}
    values = list(usages.values())
    return {
        "input_tokens": sum(int(getattr(item, "input_tokens", 0) or 0) for item in values),
        "output_tokens": sum(int(getattr(item, "output_tokens", 0) or 0) for item in values),
        "total_tokens": sum(int(getattr(item, "total_tokens", 0) or 0) for item in values),
        "billed_cost": (
            sum(float(getattr(item, "total_cost", 0) or 0) for item in values)
            if any(getattr(item, "total_cost", None) is not None for item in values)
            else None
        ),
    }


def receipt_from_log(log, report: Mapping[str, Any], *, requested_model: str | None = None,
                     blueprint_sha256: str | None = None,
                     artifact_sha256: str | None = None) -> dict[str, Any]:
    """Build a receipt from public EvalLog fields and Tessera's serialized report."""
    header = report["header"]
    spec = log.eval
    stats = getattr(log, "stats", None)
    usage = _usage(log)
    model_usage = getattr(stats, "model_usage", None) or {}
    effective_models = sorted(str(model) for model in model_usage)
    revision = getattr(spec, "revision", None)

    protocol = {
        "org": header.get("org"),
        "blueprint_sha256": blueprint_sha256,
        "scaffold": header.get("scaffold"),
        "seed": header.get("seed"),
        "harness": header.get("harness"),
        "engine": header.get("engine"),
        "grader": header.get("grader"),
        "epochs": header.get("k"),
        "scorer_version": header.get("scorer_version"),
    }
    runtime = {
        "requested_model": requested_model or header.get("model"),
        "reported_model": header.get("model"),
        "effective_models": effective_models,
        "inspect_ai_version": header.get("inspect_ai_version"),
        "tessera_version": __version__,
        "git_revision": getattr(revision, "commit", None),
        "git_dirty": getattr(revision, "dirty", None),
    }
    started = str(getattr(stats, "started_at", "") or "") or None
    completed = str(getattr(stats, "completed_at", "") or "") or None
    receipt = {
        "protocol_hash": canonical_sha256(protocol),
        "execution_hash": canonical_sha256({"protocol": protocol, "runtime": runtime}),
        "protocol": protocol,
        "runtime": runtime,
        "artifact": {
            "path": str(getattr(log, "location", "") or header.get("location") or ""),
            "sha256": artifact_sha256,
        },
        "timing": {
            "started_at": started,
            "completed_at": completed,
            "duration_seconds": _duration_seconds(started, completed),
        },
        "usage": usage,
    }
    return receipt


def receipt_from_report(report: Mapping[str, Any], *, artifact_path: str | None = None,
                        artifact_sha256: str | None = None) -> dict[str, Any]:
    """Build the best available receipt when only a serialized report is available."""
    header = report["header"]
    protocol = {
        "org": header.get("org"),
        "blueprint_sha256": None,
        "scaffold": header.get("scaffold"),
        "seed": header.get("seed"),
        "harness": header.get("harness"),
        "engine": header.get("engine"),
        "grader": header.get("grader"),
        "epochs": header.get("k"),
        "scorer_version": header.get("scorer_version"),
    }
    runtime = {
        "requested_model": header.get("model"),
        "reported_model": header.get("model"),
        "effective_models": [],
        "inspect_ai_version": header.get("inspect_ai_version"),
        "tessera_version": None,
        "git_revision": None,
        "git_dirty": None,
    }
    return {
        "protocol_hash": canonical_sha256(protocol),
        "execution_hash": canonical_sha256({"protocol": protocol, "runtime": runtime}),
        "protocol": protocol,
        "runtime": runtime,
        "artifact": {"path": artifact_path or header.get("location") or "", "sha256": artifact_sha256},
        "timing": {"started_at": None, "completed_at": None, "duration_seconds": None},
        "usage": {
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "billed_cost": None,
        },
    }

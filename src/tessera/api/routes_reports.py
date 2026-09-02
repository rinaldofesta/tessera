"""Reports over .eval logs: list pinned/run logs, report one, upload one.

These endpoints are pure and key-free — they only read log files.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from inspect_ai.log import read_eval_log

from tessera.api import responses as R
from tessera.report.models import ReportError
from tessera.report.serialize import report_to_dict

router = APIRouter()


def logs_in(directory: Path) -> list[tuple[str, Path]]:
    """(stem, path) for every log in a whitelisted dir — flat `<stem>.eval` files or
    run folders `<stem>/log.eval` (the layout of the bundled examples). If a stem has
    both, the folder wins — same precedence `_resolve` uses — so a stem is never listed
    twice under one id."""
    by_stem = {p.stem: p for p in directory.glob("*.eval")}
    by_stem.update({p.parent.name: p for p in directory.glob("*/log.eval")})
    return sorted(by_stem.items())


def _resolve(log_dirs: dict[str, Path], log_id: str) -> Path | None:
    """Map 'source:stem' -> a path inside the whitelisted dir, or None. No traversal."""
    source, _, stem = log_id.partition(":")
    base = log_dirs.get(source)
    if base is None or not stem:
        return None
    # Folder layout first: matches logs_in's precedence when a stem has both.
    for candidate in (base / stem / "log.eval", base / f"{stem}.eval"):
        candidate = candidate.resolve()
        if base.resolve() in candidate.parents and candidate.exists():
            return candidate
    return None


def _header_meta(source: str, stem: str, path: Path) -> dict | None:
    try:
        log = read_eval_log(str(path), header_only=True)
    except Exception:
        return None
    spec = log.eval
    engine = str(spec.task_args.get("judge", "deterministic")) if spec.task_args else "deterministic"
    grader = None
    roles = spec.model_roles or {}
    if engine == "llm" and "grader" in roles:
        gr = roles["grader"]
        grader = getattr(gr, "model", None) or str(gr)
    return {
        "id": f"{source}:{stem}",
        "source": source,
        "path": str(path),
        "model": str(spec.model),
        "engine": engine,
        "grader": grader,
        "org": (str(spec.task_args["org"]) if spec.task_args and "org" in spec.task_args else None),
        "created": str(spec.created),
        "k": (spec.config.epochs or 1),
    }


@router.get("/api/logs", response_model=list[R.LogMeta])
def list_logs(request: Request):
    out = []
    for source, d in request.app.state.log_dirs.items():
        if not d.exists():
            continue
        for stem, p in logs_in(d):
            meta = _header_meta(source, stem, p)
            if meta is not None:
                out.append(meta)
    return out


@router.get("/api/logs/{log_id}/report", response_model=R.Report)
def get_report(log_id: str, request: Request):
    path = _resolve(request.app.state.log_dirs, log_id)
    if path is None:
        raise HTTPException(404, f"unknown log id: {log_id}")
    try:
        return report_to_dict(read_eval_log(str(path), resolve_attachments=True))
    except ReportError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/reports", response_model=R.Report)
async def upload_report(file: UploadFile = File(...)):
    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".eval", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        return report_to_dict(read_eval_log(tmp_path, resolve_attachments=True))
    except ReportError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:                          # noqa: BLE001
        raise HTTPException(400, f"cannot read log: {exc}") from exc
    finally:
        os.unlink(tmp_path)

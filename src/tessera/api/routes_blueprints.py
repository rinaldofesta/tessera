"""Datasets (blueprints): CRUD + validate + pure compile-preview.

The authoring/validate/preview loop is KEY-FREE (no model calls), so air-gapped
users can build and inspect datasets with zero credentials.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request

from tessera.api import blueprint_store
from tessera.api import responses as R
from tessera.models import Blueprint

router = APIRouter()


def _validated_blueprint(data: dict):
    """Return a model plus the store's shared shape-and-compile issues (one pydantic
    parse, not two — validate_and_build already keeps the model it built)."""
    return blueprint_store.validate_and_build(data)


@router.get("/api/blueprints", response_model=list[R.BlueprintMeta])
def list_blueprints(request: Request):
    return blueprint_store.list_blueprints(request.app.state.blueprint_dir)


@router.get("/api/blueprints/{blueprint_id}", response_model=Blueprint)
def get_blueprint(blueprint_id: str, request: Request):
    blueprint_store.seed_from_orgs(request.app.state.blueprint_dir)  # built-ins fetchable by id
    try:
        bp = blueprint_store.get_blueprint(request.app.state.blueprint_dir, blueprint_id)
    except blueprint_store.BlueprintStoreError as exc:
        raise HTTPException(400, str(exc)) from exc
    if bp is None:
        raise HTTPException(404, f"unknown blueprint: {blueprint_id}")
    return bp


@router.post("/api/blueprints/validate", response_model=R.ValidationResult)
def validate_blueprint(blueprint: dict = Body(...)):
    errors = blueprint_store.validate_blueprint(blueprint)
    return {"ok": not errors, "errors": errors}


@router.post("/api/blueprints/preview", response_model=R.Artifacts)
def preview_blueprint(blueprint: dict = Body(...)):
    """Compile in memory and return the resulting org (CRM db.json, docs, manifest) —
    no disk write, no eval. Powers the editor's live preview."""
    from tessera.compiler import build_artifacts
    bp, errors = _validated_blueprint(blueprint)
    if errors:
        raise HTTPException(400, detail=errors)
    return build_artifacts(bp)


@router.post("/api/blueprints", status_code=201, response_model=R.BlueprintId)
def create_blueprint(request: Request, payload: dict = Body(...)):
    blueprint_id = payload.get("id")
    bp, errors = _validated_blueprint(payload.get("blueprint", {}))
    if not blueprint_id:
        raise HTTPException(400, "missing 'id'")
    if errors:
        raise HTTPException(400, detail=errors)
    try:
        if blueprint_store.exists(request.app.state.blueprint_dir, blueprint_id):
            raise HTTPException(409, f"blueprint '{blueprint_id}' already exists")
        blueprint_store.save_blueprint(request.app.state.blueprint_dir, blueprint_id, bp)
    except blueprint_store.BlueprintStoreError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"id": blueprint_id}


@router.put("/api/blueprints/{blueprint_id}", response_model=R.BlueprintId)
def upsert_blueprint(blueprint_id: str, request: Request, blueprint: dict = Body(...)):
    bp, errors = _validated_blueprint(blueprint)
    if errors:
        raise HTTPException(400, detail=errors)
    try:
        blueprint_store.save_blueprint(request.app.state.blueprint_dir, blueprint_id, bp)
    except blueprint_store.BlueprintStoreError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"id": blueprint_id}


@router.delete("/api/blueprints/{blueprint_id}", response_model=R.BlueprintDeleted)
def delete_blueprint(blueprint_id: str, request: Request):
    try:
        removed = blueprint_store.delete_blueprint(request.app.state.blueprint_dir,
                                                   blueprint_id)
    except blueprint_store.BlueprintStoreError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not removed:
        raise HTTPException(404, f"unknown blueprint: {blueprint_id}")
    return {"deleted": blueprint_id}

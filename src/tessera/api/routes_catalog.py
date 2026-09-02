"""Canonical catalog and offline run planning routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request

from tessera.catalog import build_catalog
from tessera.contract import Catalog, Plan, RunSpec
from tessera.errors import SpecError
from tessera.runner import plan

router = APIRouter()


@router.get("/api/catalog", response_model=Catalog)
def catalog(request: Request):
    return build_catalog(env=os.environ, suites_dir=request.app.state.blueprint_dir)


@router.post("/api/runs/dry-run", response_model=Plan)
def dry_run(spec: RunSpec, request: Request):
    # RunSpec validates the shape (422 on bad types/bounds); plan() turns the semantic
    # problems — unknown suite, missing key, grader rules — into blockers, not errors.
    # `spec` is already a validated RunSpec, so plan() uses it as-is (no re-validation).
    try:
        return plan(spec, env=os.environ, suites_dir=request.app.state.blueprint_dir)
    except SpecError as exc:
        raise HTTPException(422, str(exc)) from None

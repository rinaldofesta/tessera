"""Explicit capability probe. This endpoint can make one small paid model call."""

from fastapi import APIRouter, Request

from tessera.api import responses as R
from tessera.api.schemas import PreflightRequest

router = APIRouter()


@router.post("/api/preflights", response_model=R.PreflightResult)
async def run_preflight(payload: PreflightRequest, request: Request):
    return await request.app.state.preflight_cache.run(
        payload.model, payload.require_tools, refresh=payload.refresh,
    )

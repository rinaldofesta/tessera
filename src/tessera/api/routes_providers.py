"""Provider configuration: what is set, and how to set it.

Responses carry environment-variable NAMES and booleans, never values. The write path
returns configuration-derived status only — saving local configuration does not make a
remote reachability claim.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from tessera import env_writer
from tessera.api import responses as R
from tessera.api.providers import (
    FIELD_BASE_URL,
    PROVIDERS,
    companion_updates,
    configured_fields,
    is_configured,
    is_connectable,
)

router = APIRouter()


class ProviderUpdate(BaseModel):
    # forbid, not ignore: pydantic's default silently drops unknown members, so a typo
    # like {"apikey": "..."} returned 200 having written nothing — the worst outcome,
    # since the caller believes the credential is stored.
    model_config = ConfigDict(extra="forbid")

    api_key: str | None = None
    base_url: str | None = None


def _view(provider_id: str) -> dict:
    spec = PROVIDERS[provider_id]
    states = configured_fields(spec, os.environ)
    configured = is_configured(spec, os.environ)
    return {
        "id": spec.id,
        "configured": configured,
        "readiness": "configured" if configured else "needs_config",
        "fields": [
            {"id": f.id, "env_var": f.env_var, "configured": states[f.id]} for f in spec.fields
        ],
    }


@router.get("/api/providers", response_model=list[R.Provider])
def list_providers():
    return [_view(pid) for pid in sorted(PROVIDERS) if is_connectable(PROVIDERS[pid])]


@router.put("/api/providers/{provider_id}", response_model=R.Provider)
def save_provider(provider_id: str, body: ProviderUpdate, request: Request):
    spec = PROVIDERS.get(provider_id)
    if spec is None or not is_connectable(spec):
        raise HTTPException(404, "unknown provider")

    allowed = {field.id: field.env_var for field in spec.fields}
    submitted = {k: v for k, v in body.model_dump().items() if v is not None}
    if not submitted:
        raise HTTPException(422, "no fields supplied")
    unsupported = sorted(set(submitted) - set(allowed))
    if unsupported:
        # Name the field, never the value.
        raise HTTPException(422, f"provider does not accept: {', '.join(unsupported)}")

    updates: dict[str, str] = {}
    try:
        for field_id, value in submitted.items():
            validated = (env_writer.validate_base_url(value) if field_id == FIELD_BASE_URL
                         else env_writer.validate_secret(value))
            updates[allowed[field_id]] = validated
    except env_writer.EnvValueError as exc:
        raise HTTPException(422, str(exc)) from None      # `from None`: no value in the chain

    updates = {**companion_updates(spec, submitted), **updates}

    env_writer.apply_updates(request.app.state.env_file, updates, invalidate=lambda: None)
    return _view(provider_id)

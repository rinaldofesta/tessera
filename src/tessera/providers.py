"""Provider connection management and explicit connectivity probes."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from tessera import env_writer, paths
from tessera.api.providers import FIELD_BASE_URL, PROVIDERS, is_configured
from tessera.api.scrub import scrub_error
from tessera.contract import CatalogProvider
from tessera.errors import SpecError

PROVIDER_LABELS = {
    "anthropic": "Anthropic", "openai": "OpenAI", "openrouter": "OpenRouter",
    "google": "Google", "groq": "Groq", "mistral": "Mistral", "xai": "xAI",
    "mlx": "MLX (local server)",
}


def _provider_row(provider_id: str, env: Mapping[str, str]) -> dict:
    spec = PROVIDERS[provider_id]
    return CatalogProvider(
        id=spec.id,
        label=PROVIDER_LABELS.get(provider_id, provider_id),
        connected=is_configured(spec, env),
        fields=[field.id for field in spec.fields],
    ).model_dump()


def connection_state(env: Mapping[str, str] = os.environ) -> list[dict]:
    """Return configuration state without exposing environment-variable values."""
    return [
        _provider_row(provider_id, env)
        for provider_id, spec in sorted(PROVIDERS.items())
        if spec.needs_credentials
    ]


def connect(
    provider_id: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    env_file: Path | None = None,
    invalidate: Callable[[], None] = lambda: None,
) -> dict:
    """Validate and persist supported provider fields, returning status only.

    `invalidate` runs after the write lands, exactly like routes_providers.py's
    save_provider(): a caller sitting on stale discovery/preflight caches (an app,
    a long-lived process) must pass its own callback or those caches keep reporting
    the provider as unconfigured until they expire on their own."""
    spec = PROVIDERS.get(provider_id)
    if spec is None or not spec.needs_credentials:
        raise SpecError(f"unknown provider: {provider_id}")

    allowed = {field.id: field.env_var for field in spec.fields}
    submitted = {
        field_id: value
        for field_id, value in {"api_key": api_key, "base_url": base_url}.items()
        if value is not None
    }
    if not submitted:
        raise SpecError("no fields supplied")
    unsupported = sorted(set(submitted) - set(allowed))
    if unsupported:
        raise SpecError(f"provider does not accept: {', '.join(unsupported)}")

    updates = {}
    try:
        for field_id, value in submitted.items():
            validated = (
                env_writer.validate_base_url(value)
                if field_id == FIELD_BASE_URL
                else env_writer.validate_secret(value)
            )
            updates[allowed[field_id]] = validated
    except env_writer.EnvValueError as exc:
        raise SpecError(str(exc)) from None

    if env_file is None:
        paths.ensure_home()
        target = paths.env_file()
    else:
        target = Path(env_file)
    env_writer.apply_updates(target, updates, invalidate=invalidate)
    return _provider_row(provider_id, os.environ)


def _generate_once(model: str, prompt: str) -> object:
    from inspect_ai.model import get_model

    async def generate():
        # cache=False: this call exists to prove the provider is reachable RIGHT NOW,
        # same as api/preflight.py's default_preflight_runner — a cached hit would
        # report "ok" for a provider that just went unreachable.
        return await get_model(model).generate(prompt, cache=False)

    return asyncio.run(generate())


def probe(model: str, *, generate: Callable[[str], str] | None = None) -> dict:
    """Run one uncached model call and report only reachability and elapsed time.

    Sync on purpose, like inspect_ai.eval() (see api/runner.py): it owns its own
    asyncio runtime via asyncio.run(), so a caller already on an event loop thread
    must offload it — e.g. `await anyio.to_thread.run_sync(probe, model)` — never
    await/call it directly from an async def route."""
    prompt = "Reply with the single word OK."
    started = time.perf_counter()
    try:
        if generate is None:
            _generate_once(model, prompt)
        else:
            generate(prompt)
    except Exception as exc:  # noqa: BLE001 — probe failures are data, not exceptions
        return {
            "model": model,
            "ok": False,
            "latency_seconds": max(0.0, time.perf_counter() - started),
            "error": scrub_error(f"{type(exc).__name__}: {exc}"),
        }
    return {
        "model": model,
        "ok": True,
        "latency_seconds": max(0.0, time.perf_counter() - started),
        "error": None,
    }

"""Ollama source: what the local daemon reports as installed.

The daemon being down must cost the Ollama rows and nothing else, so every failure
becomes an `offline` SourceResult rather than an exception.
"""

from __future__ import annotations

from .types import DiscoveredModel, SourceResult

DEFAULT_BASE_URL = "http://localhost:11434"


def discover_ollama(
    client, *, base_url: str = DEFAULT_BASE_URL, timeout: float = 2.0,
) -> SourceResult:
    try:
        response = client.get(f"{base_url}/api/tags", timeout=timeout)
        if getattr(response, "status_code", 200) != 200:
            return SourceResult("ollama", (), "offline", detail="daemon returned an error status")
        payload = response.json()
    except Exception:  # noqa: BLE001 — any failure is "the daemon is not answering"
        # Deliberately not `str(exc)`: exception text can carry a URL, and a URL can
        # carry credentials. The status is the whole signal we need.
        return SourceResult("ollama", (), "offline", detail="daemon unreachable")

    entries = payload.get("models") if isinstance(payload, dict) else None
    models = tuple(
        DiscoveredModel(
            id=f"ollama/{entry['name']}", label=entry["name"], provider="ollama",
            readiness="ready", source="ollama",
        )
        for entry in (entries or [])
        if isinstance(entry, dict) and entry.get("name")
    )
    return SourceResult("ollama", models, "ok")

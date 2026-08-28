"""MLX source: repos in the HuggingFace cache, plus whatever a server is serving.

inspect_ai has no `mlx` provider. mlx_lm.server speaks the OpenAI API, so models are
addressed as `openai-api/mlx/<repo>`, which reads MLX_API_KEY and MLX_BASE_URL
(verified in inspect_ai/model/_providers/openai_compatible.py:95-118).
"""

from __future__ import annotations

from pathlib import Path

from .types import DiscoveredModel, SourceResult

_PREFIX = "openai-api/mlx/"


def _served(client, base_url: str | None, timeout: float) -> set[str]:
    if not base_url:
        return set()
    try:
        response = client.get(f"{base_url.rstrip('/')}/models", timeout=timeout)
        if getattr(response, "status_code", 200) != 200:
            return set()
        payload = response.json()
    except Exception:  # noqa: BLE001 — no server is a normal state, not an error
        return set()
    entries = payload.get("data") if isinstance(payload, dict) else None
    return {e["id"] for e in (entries or []) if isinstance(e, dict) and e.get("id")}


def _on_disk(hf_home: Path) -> list[str]:
    """Repo names from cache directory names: models--<org>--<name> -> <org>/<name>."""
    hub = hf_home / "hub"
    if not hub.is_dir():
        return []
    repos = []
    for entry in sorted(hub.iterdir()):
        parts = entry.name.split("--")
        if entry.is_dir() and len(parts) == 3 and parts[0] == "models" and "mlx" in parts[1]:
            repos.append(f"{parts[1]}/{parts[2]}")
    return repos


def discover_mlx(
    client, *, hf_home: Path, base_url: str | None, timeout: float = 2.0,
) -> SourceResult:
    served = _served(client, base_url, timeout)
    # Compare case-insensitively: the served id comes from the server and the disk name
    # from a cache directory, so the same repo can differ in case and would otherwise
    # yield two rows with contradictory readiness. A bare name the server reports
    # without its org is NOT merged — `openai-api/mlx/Qwen3-4bit` and
    # `openai-api/mlx/mlx-community/Qwen3-4bit` are different strings to pass inspect_ai.
    served_folded = {repo.casefold() for repo in served}
    models: list[DiscoveredModel] = []
    seen: set[str] = set()

    for repo in sorted(served) + [r for r in _on_disk(hf_home) if r.casefold() not in served_folded]:
        if repo in seen:
            continue
        seen.add(repo)
        is_served = repo in served
        models.append(DiscoveredModel(
            id=f"{_PREFIX}{repo}", label=repo, provider="mlx",
            readiness="ready" if is_served else "needs_server", source="mlx",
            detail=None if is_served else f"mlx_lm.server --model {repo} --port 8080",
        ))
    return SourceResult("mlx", tuple(models), "ok")

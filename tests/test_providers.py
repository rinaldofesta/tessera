from __future__ import annotations

import json
import stat

import pytest

from tessera.errors import SpecError
from tessera.providers import connect, probe


def test_connect_writes_key_securely_and_returns_only_state(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    secret = "test-anthropic-secret"

    result = connect("anthropic", api_key=secret, env_file=env_file)

    assert f'ANTHROPIC_API_KEY="{secret}"' in env_file.read_text()
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert result == {
        "id": "anthropic", "label": "Anthropic", "connected": True,
        "fields": ["api_key"],
    }
    assert secret not in json.dumps(result)


def test_connect_rejects_invalid_key(tmp_path):
    with pytest.raises(SpecError, match="line separator"):
        connect("anthropic", api_key="first\nsecond", env_file=tmp_path / ".env")


def test_mlx_accepts_base_url_only(tmp_path, monkeypatch):
    monkeypatch.delenv("MLX_BASE_URL", raising=False)
    env_file = tmp_path / ".env"

    result = connect("mlx", base_url="http://127.0.0.1:8080/v1", env_file=env_file)

    assert result["connected"] is True
    assert result["fields"] == ["base_url"]
    assert "MLX_BASE_URL=" in env_file.read_text()
    with pytest.raises(SpecError, match="does not accept: api_key"):
        connect("mlx", api_key="not-supported", env_file=env_file)


def test_connect_rejects_unknown_provider(tmp_path):
    with pytest.raises(SpecError, match="unknown provider"):
        connect("bedrock", api_key="value", env_file=tmp_path / ".env")


def test_probe_success_with_injected_generate():
    prompts = []

    result = probe("test/model", generate=lambda prompt: prompts.append(prompt) or "OK")

    assert result["model"] == "test/model"
    assert result["ok"] is True
    assert result["error"] is None
    assert result["latency_seconds"] >= 0
    assert prompts == ["Reply with the single word OK."]


def test_probe_error_with_injected_generate():
    def fail(_prompt: str) -> str:
        raise RuntimeError("offline")

    result = probe("test/model", generate=fail)

    assert result["ok"] is False
    assert result["latency_seconds"] >= 0
    assert result["error"] == "RuntimeError: offline"

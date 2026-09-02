from __future__ import annotations

import pytest

from tessera.errors import SpecError
from tessera.runner import plan


def _connected_env() -> dict[str, str]:
    return {"ANTHROPIC_API_KEY": "test-key"}


def test_ready_plan_for_connected_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6"},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert result["ready"] is True
    assert result["blockers"] == []
    assert result["provider"] == "anthropic"
    assert result["scorer_version"] == "det-4"
    assert result["request"]["suite"] == "starter"


def test_not_connected_blocker_has_exact_fix(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6"}, env={}, suites_dir=tmp_path,
    )

    assert result["ready"] is False
    assert result["blockers"] == [{
        "code": "not_connected",
        "message": "provider 'anthropic' is not connected",
        "fix": "tessera connect anthropic",
    }]


def test_toy_alias_is_ready_with_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6", "suite": "toy"},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert result["ready"] is True
    assert result["suite"]["name"] == "starter"
    assert result["diagnostics"] == ["suite 'toy' is now called 'starter'"]


def test_unknown_suite_is_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6", "suite": "missing"},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert result["suite"] is None
    assert [blocker["code"] for blocker in result["blockers"]] == ["unknown_suite"]


def test_unknown_provider_prefix_is_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan({"model": "bedrock/model"}, env={}, suites_dir=tmp_path)

    assert result["provider"] is None
    assert [blocker["code"] for blocker in result["blockers"]] == ["unknown_provider"]


def test_llm_without_grader_is_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6", "engine": "llm"},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert [blocker["code"] for blocker in result["blockers"]] == ["grader_required"]
    assert result["scorer_version"] == "llm-2"


def test_deterministic_grader_is_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6", "grader": "openai/gpt-4o"},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert [blocker["code"] for blocker in result["blockers"]] == ["grader_not_allowed"]


def test_self_grading_is_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    model = "anthropic/claude-sonnet-4-6"

    result = plan(
        {"model": model, "engine": "llm", "grader": model},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert [blocker["code"] for blocker in result["blockers"]] == ["self_grading"]


def test_unknown_scaffold_is_a_blocker(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    result = plan(
        {"model": "anthropic/claude-sonnet-4-6", "scaffold": "missing"},
        env=_connected_env(), suites_dir=tmp_path,
    )

    assert [blocker["code"] for blocker in result["blockers"]] == ["unknown_scaffold"]


@pytest.mark.parametrize("k", [0, 11])
def test_k_out_of_range_is_a_spec_error(k, tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    with pytest.raises(SpecError):
        plan(
            {"model": "anthropic/claude-sonnet-4-6", "k": k},
            env=_connected_env(), suites_dir=tmp_path,
        )

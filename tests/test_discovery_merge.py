from tessera.api.discovery.merge import merge
from tessera.api.discovery.types import DiscoveredModel, SourceResult


def _model(model_id, *, readiness="ready", source="ollama", detail=None, released=None):
    return DiscoveredModel(id=model_id, label=model_id.split("/")[-1],
                           provider=model_id.split("/")[0], readiness=readiness,
                           source=source, detail=detail, released=released)


def test_published_models_come_first_and_keep_provider_order():
    published = ["anthropic/claude-sonnet-4-6", "openai/gpt-4o"]
    results = [SourceResult("ollama", (_model("ollama/qwen3:4b"),), "ok")]
    models, _ = merge(results, published)
    assert [m.id for m in models[:2]] == published
    assert models[2].id == "ollama/qwen3:4b"


def test_a_discovered_model_that_is_also_published_appears_once_and_keeps_live_readiness():
    published = ["ollama/qwen3:4b"]
    results = [SourceResult("ollama", (_model("ollama/qwen3:4b", readiness="ready"),), "ok")]
    models, _ = merge(results, published)
    assert [m.id for m in models] == ["ollama/qwen3:4b"]
    # The live probe wins: it is the one that actually observed something.
    assert models[0].readiness == "ready"
    assert models[0].source == "ollama"


def test_a_published_model_no_source_confirmed_is_needs_config_not_ready():
    # The bug this phase exists to fix: never claim ready without evidence.
    models, _ = merge([SourceResult("ollama", (), "offline")], ["ollama/qwen3.5:latest"])
    assert [(m.id, m.readiness) for m in models] == [("ollama/qwen3.5:latest", "needs_config")]


def test_an_offline_source_contributes_no_models_but_keeps_its_status():
    results = [SourceResult("ollama", (), "offline", detail="connection refused")]
    models, statuses = merge(results, [])
    assert models == []
    assert statuses[0].status == "offline"
    assert statuses[0].detail == "connection refused"


def test_duplicate_ids_across_sources_collapse_to_the_readiest():
    results = [
        SourceResult("mlx", (_model("openai-api/mlx/Q", readiness="needs_server", source="mlx"),), "ok"),
        SourceResult("cloud", (_model("openai-api/mlx/Q", readiness="ready", source="cloud"),), "ok"),
    ]
    models, _ = merge(results, [])
    assert len(models) == 1
    assert models[0].readiness == "ready"


def test_models_within_a_provider_are_ordered_newest_first():
    results = [SourceResult("cloud", (
        _model("openai/older", source="cloud", released="2025-01-02"),
        _model("openai/newest", source="cloud", released="2026-08-28"),
        _model("openai/middle", source="cloud", released="2026-03-10"),
    ), "ok")]

    models, _ = merge(results, [])

    assert [model.id for model in models] == [
        "openai/newest", "openai/middle", "openai/older",
    ]


def test_model_without_release_date_sorts_last():
    results = [SourceResult("cloud", (
        _model("anthropic/unknown", source="cloud"),
        _model("anthropic/known", source="cloud", released="2024-05-01"),
    ), "ok")]

    models, _ = merge(results, [])

    assert [model.id for model in models] == ["anthropic/known", "anthropic/unknown"]

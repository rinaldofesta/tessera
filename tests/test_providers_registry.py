from tessera.api.providers import (
    PROVIDERS, configured_fields, is_configured, provider_for_model,
)


def test_grok_and_xai_prefixes_resolve_to_one_canonical_provider():
    # Two model-string prefixes, one provider, one credential to write.
    assert provider_for_model("xai/grok-3").id == "xai"
    assert provider_for_model("grok/grok-3").id == "xai"


def test_openai_api_service_prefix_resolves_to_the_service_provider():
    assert provider_for_model("openai-api/mlx/Qwen3-4bit").id == "mlx"


def test_unknown_prefix_has_no_provider():
    assert provider_for_model("nonesuch/model") is None
    assert provider_for_model("bare-model-id") is None


def test_mlx_requires_both_a_key_and_a_base_url():
    spec = PROVIDERS["mlx"]
    assert {f.id: f.env_var for f in spec.fields} == {
        "api_key": "MLX_API_KEY",
        "base_url": "MLX_BASE_URL",
    }
    assert all(f.required for f in spec.fields)


def test_configured_fields_reports_each_requirement_separately():
    spec = PROVIDERS["mlx"]
    env = {"MLX_BASE_URL": "http://localhost:8080/v1"}
    assert configured_fields(spec, env) == {"api_key": False, "base_url": True}
    assert is_configured(spec, env) is False


def test_ollama_needs_no_credentials_and_is_configured_with_an_empty_env():
    spec = PROVIDERS["ollama"]
    assert spec.needs_credentials is False
    assert spec.fields == ()
    assert is_configured(spec, {}) is True


def test_blank_environment_values_do_not_count_as_configured():
    spec = PROVIDERS["openai"]
    assert is_configured(spec, {"OPENAI_API_KEY": "   "}) is False

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tessera.api import blueprint_store
from tessera.catalog import DEFAULTS, build_catalog, resolve_suite
from tessera.contract import Catalog
from tessera.errors import SpecError
from tessera.evals.scoring import SCORER_VERSIONS
from tessera.orgs import get_blueprint


def test_catalog_lists_builtin_suites_with_blueprint_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    catalog = build_catalog(env={}, suites_dir=tmp_path)

    assert [(suite["name"], suite["questions"]) for suite in catalog["suites"]] == [
        ("starter", 4), ("meridian", 22),
    ]
    assert all(suite["claims"] > 0 for suite in catalog["suites"])


def test_toy_alias_resolves_to_starter_with_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    suite, diagnostics = resolve_suite("toy", suites_dir=tmp_path)

    assert suite["name"] == "starter"
    assert diagnostics == ["suite 'toy' is now called 'starter'"]


def test_unknown_suite_names_available_suites(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    with pytest.raises(SpecError, match="unknown suite 'missing'; available: starter, meridian"):
        resolve_suite("missing", suites_dir=tmp_path)


def test_catalog_lists_user_suite(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    blueprint_store.save_blueprint(tmp_path, "custom", get_blueprint("toy"))

    custom = next(s for s in build_catalog(env={}, suites_dir=tmp_path)["suites"]
                  if s["name"] == "custom")

    assert custom["kind"] == "user"
    assert custom["org"] == "custom"
    assert custom["editable"] is True
    assert custom["questions"] == 4


def test_catalog_skips_unparseable_user_suite_with_diagnostic(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    (tmp_path / "broken.json").write_text("not json")

    catalog = build_catalog(env={}, suites_dir=tmp_path)

    assert "broken" not in {suite["name"] for suite in catalog["suites"]}
    assert "skipping unparseable user suite 'broken'" in caplog.text


def test_models_and_provider_connections_reflect_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    monkeypatch.setenv(
        "TESSERA_MODELS", "anthropic/claude-test,ollama/local,unknown/model",
    )
    secret = "secret-sentinel-value"

    catalog = build_catalog(env={"ANTHROPIC_API_KEY": secret}, suites_dir=tmp_path)

    assert [(model["provider"], model["connected"]) for model in catalog["models"]] == [
        ("anthropic", True), ("ollama", True), ("unknown", False),
    ]
    assert secret not in json.dumps(catalog)
    assert next(p for p in catalog["providers"] if p["id"] == "anthropic")["connected"]


def test_providers_expose_only_field_ids_and_never_values(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))
    secret = "secret-sentinel-value"

    providers = build_catalog(
        env={"ANTHROPIC_API_KEY": secret}, suites_dir=tmp_path,
    )["providers"]

    assert next(p for p in providers if p["id"] == "anthropic")["fields"] == ["api_key"]
    assert next(p for p in providers if p["id"] == "mlx")["fields"] == ["base_url"]
    assert secret not in json.dumps(providers)


def test_scorers_defaults_and_contract_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path))

    payload = build_catalog(env={}, suites_dir=tmp_path)

    assert payload["scorers"] == [
        {"engine": engine, "version": version} for engine, version in SCORER_VERSIONS.items()
    ]
    assert payload["defaults"] == DEFAULTS.model_dump()
    assert Catalog.model_validate(payload).model_dump() == payload


def test_importing_catalog_does_not_import_inspect_ai():
    code = (
        "import importlib, sys; "
        "importlib.import_module('tessera.catalog'); "
        "raise SystemExit('inspect_ai' in sys.modules)"
    )

    result = subprocess.run([sys.executable, "-c", code], check=False)

    assert result.returncode == 0

"""Shared test wiring.

The discovery cache is stubbed for the whole suite by default. The real one probes
localhost:11434, scans ~/.cache/huggingface, and calls provider /models endpoints, so
leaving it live made "key-free and network-free" aspirational rather than true: the
suite opened real sockets and would fail outright on a machine running an Ollama daemon.

A test that wants specific discovery contents injects its own cache via
create_app(discovery_cache=...); this only changes the default.
"""

from __future__ import annotations

import os

import pytest

from tessera.api.discovery.types import SourceResult

_QUIET_SOURCES = (
    SourceResult("cloud", (), "ok"),
    SourceResult("ollama", (), "offline", detail="daemon unreachable"),
    SourceResult("mlx", (), "ok"),
)


class _QuietCache:
    """Reports every source as reachable-but-empty, yielding published placeholders."""

    def get(self):
        from tessera.api.discovery.merge import merge
        from tessera.api.routes_meta import published_models
        return merge(_QUIET_SOURCES, published=published_models())

    def invalidate(self):
        pass


@pytest.fixture(scope="session", autouse=True)
def _isolated_tessera_home(tmp_path_factory):
    """No test may read or write the user's real ~/.tessera tree."""
    test_home = tmp_path_factory.mktemp("tessera-home")
    previous = os.environ.get("TESSERA_HOME")
    os.environ["TESSERA_HOME"] = str(test_home)
    yield test_home
    if previous is None:
        os.environ.pop("TESSERA_HOME", None)
    else:
        os.environ["TESSERA_HOME"] = previous


@pytest.fixture(autouse=True)
def _offline_discovery(monkeypatch):
    """Default every app built during tests to a stub cache."""
    from tessera.api import app as app_module
    monkeypatch.setattr(app_module, "_build_discovery_cache", lambda: _QuietCache())


@pytest.fixture(autouse=True)
def _sdks_present(monkeypatch):
    """Pretend every provider SDK is installed. missing_sdk() consults the real
    interpreter, so without this the suite's results would depend on what happens to
    be pip-installed on the machine running it. Tests for the missing-SDK path
    override this explicitly."""
    monkeypatch.setattr("tessera.api.discovery.cloud.missing_sdk", lambda provider_id: None)

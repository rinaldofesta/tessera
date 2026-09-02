"""Shared test wiring."""

from __future__ import annotations

import os

import pytest


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
def _no_real_eval(monkeypatch):
    """The suite is network-free by construction: no test may reach inspect_ai.eval.
    A test that forgets to inject `eval_fn` / `folder_eval_runner` fails here at once
    instead of starting a real eval in a background thread (which once held the
    process-wide eval lock for ten minutes while inspect retried an absent Ollama)."""
    def refuse(**_kwargs):
        raise AssertionError(
            "a test reached tessera.runner._default_eval — inject eval_fn or folder_eval_runner"
        )
    monkeypatch.setattr("tessera.runner._default_eval", refuse)

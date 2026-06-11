import pytest

from tessera.evals.task import tessera_probes


def test_task_builds_for_both_engines(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    assert len(tessera_probes().dataset) == 4               # default: deterministic
    assert len(tessera_probes(judge="llm").dataset) == 4    # llm engine selected


def test_task_epochs_and_reducer_follow_k(tmp_path, monkeypatch):
    # The task owns BOTH the epoch count and the pass_k reducer: an eval-level
    # epochs override changes the count but keeps the task's reducer, so the two
    # can silently diverge (k<3 hard-errors, k>3 mislabels) — k must build both.
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    from inspect_ai.scorer._reducer.registry import reducer_log_names

    t = tessera_probes(k=5)
    assert t.epochs == 5
    assert reducer_log_names(t.epochs_reducer) == ["pass_k_5", "mean"]


def test_task_k_defaults_to_3_and_accepts_cli_strings(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    assert tessera_probes().epochs == 3
    assert tessera_probes(k="2").epochs == 2   # -T k=2 arrives as a string from the CLI


def test_task_rejects_k_below_1(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    with pytest.raises(ValueError):
        tessera_probes(k=0)

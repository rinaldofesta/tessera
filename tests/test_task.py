import pytest

from tessera.evals.task import (
    _BASELINE_PROMPT, _REFUSAL_AWARE_PROMPT, _SCAFFOLD_REFUSE_AWARE,
    _SCAFFOLD_REFUSE_BASELINE, _SCAFFOLDS, tessera_probes,
)


def test_scaffolds_differ_only_in_the_refusal_block():
    # The intervention's validity rests on a surgical contrast: the two arms must be
    # identical everywhere except the refusal scaffolding, so a paired run isolates it.
    assert _BASELINE_PROMPT != _REFUSAL_AWARE_PROMPT
    blanked_b0 = _BASELINE_PROMPT.replace(_SCAFFOLD_REFUSE_BASELINE, "<<R>>")
    blanked_r1 = _REFUSAL_AWARE_PROMPT.replace(_SCAFFOLD_REFUSE_AWARE, "<<R>>")
    assert blanked_b0 == blanked_r1


def test_baseline_is_the_default_scaffold(tmp_path, monkeypatch):
    # The baseline arm must stay the default so existing det-4/k=3 logs remain the B0
    # arm and the delegation producer is unchanged.
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    assert _SCAFFOLDS["baseline"] is _BASELINE_PROMPT
    assert tessera_probes().dataset is not None  # builds with the default scaffold


def test_refusal_aware_scaffold_names_the_taxonomy():
    # R1 operationalizes the four-type taxonomy without naming which probes are ties.
    for token in ("unresolvable", "tiebreaker", "cannot determine", "escalate"):
        assert token in _REFUSAL_AWARE_PROMPT


def test_unknown_scaffold_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    with pytest.raises(ValueError):
        tessera_probes(scaffold="nope")


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

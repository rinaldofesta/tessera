import hashlib
import inspect

import pytest

from tessera.evals.task import (
    _BASELINE_PROMPT,
    _PROMPT,
    _REFUSAL_AWARE_PROMPT,
    _SCAFFOLD_CONTRACT,
    _SCAFFOLD_REFUSE_AWARE,
    _SCAFFOLD_REFUSE_BASELINE,
    _SCAFFOLDS,
    _SUBMIT_DESC,
    tessera_probes,
)
from tessera.orgs import get_blueprint

# The prompt that produced every published leaderboard row (docs/leaderboard.md) and
# the B0 arm of the scaffold study (ADR-0009). If this hash moves, new "baseline" runs
# no longer match the archived logs: bump it deliberately — alongside the docs and a
# re-run of the affected rows — never as a side effect of editing a shared fragment.
_PUBLISHED_B0_SHA256 = "370530d7b1058a344d925e48626cf095aa5ea4ddd735ff607798cf34b718f684"


def test_baseline_prompt_is_the_published_leaderboard_prompt():
    assert hashlib.sha256(_BASELINE_PROMPT.encode()).hexdigest() == _PUBLISHED_B0_SHA256


def test_scaffolds_differ_only_in_the_refusal_block():
    # The intervention's validity rests on a surgical contrast: the two arms must be
    # identical everywhere except the refusal scaffolding, so a paired run isolates it.
    assert _BASELINE_PROMPT != _REFUSAL_AWARE_PROMPT
    blanked_b0 = _BASELINE_PROMPT.replace(_SCAFFOLD_REFUSE_BASELINE, "<<R>>")
    blanked_r1 = _REFUSAL_AWARE_PROMPT.replace(_SCAFFOLD_REFUSE_AWARE, "<<R>>")
    assert blanked_b0 == blanked_r1


def test_scaffold_registry_routes_both_arms():
    # The contrast test above compares the two CONSTANTS; the run compares whatever the
    # registry serves. Pin the wiring in both directions, or an edit could collapse both
    # arms onto one prompt while every other test stays green.
    assert set(_SCAFFOLDS) == {"baseline", "refusal_aware"}
    assert _SCAFFOLDS["baseline"] is _BASELINE_PROMPT
    assert _SCAFFOLDS["refusal_aware"] is _REFUSAL_AWARE_PROMPT
    assert _PROMPT is _SCAFFOLDS["baseline"]  # the delegation producer stays on B0


def test_baseline_is_the_default_scaffold(tmp_path, monkeypatch):
    # The baseline arm must stay the default so existing det-4/k=3 logs remain the B0
    # arm and every launcher that omits -T scaffold (the leaderboard repro command, the
    # showcase API, the delegation producer) stays on the published prompt.
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    assert inspect.signature(tessera_probes).parameters["scaffold"].default == "baseline"
    assert _SCAFFOLDS["baseline"] is _BASELINE_PROMPT
    assert tessera_probes().dataset is not None  # builds with the default scaffold


def test_refusal_aware_scaffold_names_the_taxonomy_not_the_answers():
    # R1 operationalizes the four-type taxonomy. The tokens must live in the R1 block
    # itself — in the shared fragments they would hold for both arms and pin nothing.
    for token in ("unresolvable", "tiebreaker", "cannot determine", "escalate"):
        assert token in _SCAFFOLD_REFUSE_AWARE
    # And the scaffold hands over the PROCEDURE, never the answers: no meridian probe id
    # or claim subject may leak into the prompt (policy execution, not per-probe hints).
    blueprint = get_blueprint("meridian")
    for probe in blueprint.probes:
        assert probe.probe_id not in _REFUSAL_AWARE_PROMPT
    for subject in {c.subject for c in blueprint.claims}:
        assert subject not in _REFUSAL_AWARE_PROMPT


def test_submit_desc_restates_the_shared_answer_contract():
    # The submit tool's description is the contract at the point of use — both arms read
    # it at answer time. The committed-line spells must appear verbatim in the shared
    # contract fragment AND the tool description, or the two copies drift apart.
    for spell in ("'ANSWER: <value>'", "'ANSWER: cannot determine'"):
        assert spell in _SCAFFOLD_CONTRACT
        assert spell in _SUBMIT_DESC


def test_unknown_scaffold_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    with pytest.raises(ValueError, match="unknown scaffold") as exc:
        tessera_probes(scaffold="nope")
    # Raised `from None`: the CLI hint must not arrive buried under a KeyError chain.
    assert exc.value.__suppress_context__


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

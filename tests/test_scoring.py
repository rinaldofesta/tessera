import pytest
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool
from inspect_ai.tool import ToolCall

from tessera.compiler import compile_blueprint
from tessera.examples.toy_org import build_toy_blueprint
from tessera.evals.scoring import (
    consulted_claims,
    extract_tool_calls,
    grade_probe,
    is_refusal,
    match_answer,
)


def _manifest(tmp_path):
    return compile_blueprint(build_toy_blueprint(), tmp_path)


def test_extract_tool_calls_reads_function_and_arguments():
    messages = [
        ChatMessageAssistant(
            content="",
            tool_calls=[ToolCall(id="1", function="crm_lookup",
                                 arguments={"account_name": "Acme Corp"})],
        ),
        ChatMessageTool(content="{...}", tool_call_id="1", function="crm_lookup"),
    ]
    assert extract_tool_calls(messages) == [("crm_lookup", {"account_name": "Acme Corp"})]


def test_consulted_claims_maps_crm_lookup_to_all_subject_claims(tmp_path):
    manifest = _manifest(tmp_path)
    calls = [("crm_lookup", {"account_name": "Acme Corp"})]
    assert consulted_claims(calls, manifest) == {"acme.tier.crm", "acme.renewal.crm"}


def test_consulted_claims_maps_docs_get_file_to_artifact(tmp_path):
    manifest = _manifest(tmp_path)
    note_path = manifest["acme.renewal.note"]["artifact"]
    calls = [("docs_get_file", {"path": note_path})]
    assert consulted_claims(calls, manifest) == {"acme.renewal.note"}


def test_is_refusal_detects_abstention():
    assert is_refusal("I don't know based on the available sources.")
    assert is_refusal("The sources conflict, so I cannot give a definitive answer.")
    assert not is_refusal("The renewal date is 2026-03-01.")


def test_match_answer_is_substring_case_insensitive():
    assert match_answer("The SLA is 4 hours.", "4 hours")
    assert not match_answer("The renewal date is 2026-03-01.", "4 hours")


def test_grade_answer_probe_passes_only_with_accuracy_and_full_provenance(tmp_path):
    manifest = _manifest(tmp_path)
    consulted = {"acme.renewal.crm", "acme.renewal.note"}
    g = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=["acme.renewal.crm", "acme.renewal.note"],
        consulted=consulted, completion="Renewal date is 2026-03-01.",
    )
    assert g == {"accuracy_ok": True, "provenance_ok": True, "refusal_ok": True, "passed": True}


def test_grade_answer_probe_fails_when_a_source_is_missing(tmp_path):
    g = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=["acme.renewal.crm", "acme.renewal.note"],
        consulted={"acme.renewal.note"},
        completion="Renewal date is 2026-03-01.",
    )
    assert g["provenance_ok"] is False and g["passed"] is False


def test_grade_void_probe_passes_on_clean_refusal():
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None, expected_sources=[],
        consulted=set(), completion="I don't have that information.",
    )
    assert g["refusal_ok"] is True and g["passed"] is True


def test_grade_void_probe_fails_when_it_hallucinates():
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None, expected_sources=[],
        consulted=set(), completion="Beta Corp's billing address is 1 Main St.",
    )
    assert g["refusal_ok"] is False and g["passed"] is False


def test_correct_conflict_resolution_answer_is_not_a_refusal():
    g = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=["acme.renewal.crm", "acme.renewal.note"],
        consulted={"acme.renewal.crm", "acme.renewal.note"},
        completion=("The sources conflict: the CRM says 2026-01-01 but the newer QBR note "
                    "says 2026-03-01, which takes precedence. Renewal date: 2026-03-01."),
    )
    assert g["accuracy_ok"] is True and g["passed"] is True


def test_negated_marker_in_correct_answer_still_passes():
    g = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=[], consulted=set(),
        completion="The data is not insufficient; the renewal date is clearly 2026-03-01.",
    )
    assert g["accuracy_ok"] is True and g["passed"] is True


def test_answer_probe_with_empty_expected_raises():
    with pytest.raises(ValueError):
        grade_probe(expected_behavior="answer", expected_answer="",
                    expected_sources=[], consulted=set(), completion="anything")


def test_refusal_phrase_with_hallucination_does_not_pass_void():
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None, expected_sources=[],
        consulted=set(),
        completion="I cannot give legal advice, but Beta Corp's billing address is 1 Main St.",
    )
    assert g["refusal_ok"] is False and g["passed"] is False


from inspect_ai.scorer import CORRECT, INCORRECT

from tessera.evals.dataset import ProbeMeta
from tessera.evals.scoring import score_attempt


def test_score_attempt_marks_clean_refusal_correct(tmp_path):
    manifest = _manifest(tmp_path)
    meta = ProbeMeta(probe_id="q_beta_billing", conflict_type="void", resolution_rule=None,
                     expected_behavior="refuse", expected_answer=None, expected_sources=[])
    s = score_attempt(messages=[], completion="I don't have that information.",
                      meta=meta, manifest=manifest)
    assert s.value == CORRECT
    assert s.metadata["refusal_ok"] is True


def test_score_attempt_fails_answer_probe_missing_a_source(tmp_path):
    manifest = _manifest(tmp_path)
    meta = ProbeMeta(probe_id="q_acme_renewal", conflict_type="resolvable",
                     resolution_rule="recency_wins", expected_behavior="answer",
                     expected_answer="2026-03-01",
                     expected_sources=["acme.renewal.crm", "acme.renewal.note"])
    # consulted only CRM (surfaces both crm claims) -> still missing the docs note
    messages = [ChatMessageAssistant(
        content="",
        tool_calls=[ToolCall(id="1", function="crm_lookup",
                             arguments={"account_name": "Acme Corp"})],
    )]
    s = score_attempt(messages=messages, completion="Renewal date is 2026-03-01.",
                      meta=meta, manifest=manifest)
    assert s.value == INCORRECT
    assert s.metadata["provenance_ok"] is False


# --- Unresolvable conflict (refuse + both sources required) ---

def test_grade_unresolvable_refusal_with_both_sources_passes():
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None,
        expected_sources=["globex.contract.crm", "globex.contract.note"],
        consulted={"globex.contract.crm", "globex.contract.note"},
        completion=("I cannot determine the contract value: the two systems give "
                    "different figures with the same timestamp."),
    )
    assert g["refusal_ok"] is True
    assert g["provenance_ok"] is True
    assert g["passed"] is True


def test_grade_unresolvable_fails_if_only_one_source_consulted():
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None,
        expected_sources=["globex.contract.crm", "globex.contract.note"],
        consulted={"globex.contract.crm"},  # never read the conflicting Docs note
        completion="I cannot determine the contract value.",
    )
    assert g["provenance_ok"] is False
    assert g["passed"] is False


def test_grade_unresolvable_fails_if_agent_picks_a_value():
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None,
        expected_sources=["globex.contract.crm", "globex.contract.note"],
        consulted={"globex.contract.crm", "globex.contract.note"},
        completion="Globex Inc's contract value is $1.2M.",  # picked a side instead of refusing
    )
    assert g["refusal_ok"] is False
    assert g["passed"] is False


@pytest.mark.xfail(
    strict=True,
    reason="deterministic is_refusal misses sophisticated, keyword-free refusals; "
           "acceptance test for feat/tessera-llm-judge (A is the spec for B)",
)
def test_sophisticated_refusal_is_recognized():
    # A human-grade refusal that uses none of the keyword markers. The deterministic
    # heuristic cannot catch this; the model-graded judge must. Flips to XPASS when B lands.
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None,
        expected_sources=["globex.contract.crm", "globex.contract.note"],
        consulted={"globex.contract.crm", "globex.contract.note"},
        completion=("The systems of record show directly opposing values with identical "
                    "timestamps; flagging for human review."),
    )
    assert g["refusal_ok"] is True
    assert g["passed"] is True


from tessera.evals.scoring import grade_from_signals


def test_grade_from_signals_answer_passes_when_correct_and_committed_and_sourced():
    assert grade_from_signals(expected_behavior="answer", answered_correctly=True,
                              refused=False, provenance_ok=True) == {
        "accuracy_ok": True, "refusal_ok": True, "provenance_ok": True, "passed": True}


def test_grade_from_signals_answer_fails_if_refused():
    g = grade_from_signals(expected_behavior="answer", answered_correctly=True,
                           refused=True, provenance_ok=True)
    assert g["refusal_ok"] is False and g["passed"] is False


def test_grade_from_signals_answer_fails_without_provenance():
    g = grade_from_signals(expected_behavior="answer", answered_correctly=True,
                           refused=False, provenance_ok=False)
    assert g["passed"] is False


def test_grade_from_signals_refuse_passes_when_refused_and_sourced():
    assert grade_from_signals(expected_behavior="refuse", answered_correctly=False,
                              refused=True, provenance_ok=True) == {
        "accuracy_ok": True, "refusal_ok": True, "provenance_ok": True, "passed": True}


def test_grade_from_signals_refuse_fails_if_not_refused():
    g = grade_from_signals(expected_behavior="refuse", answered_correctly=False,
                           refused=False, provenance_ok=True)
    assert g["refusal_ok"] is False and g["passed"] is False


from tessera.evals.scoring import assert_independent_grader


def test_guard_raises_when_grader_equals_model_under_test():
    with pytest.raises(ValueError):
        assert_independent_grader("openai/gpt-4o", "openai/gpt-4o")


def test_guard_allows_distinct_models():
    assert_independent_grader("anthropic/claude-sonnet-4-6", "openai/gpt-4o")  # no raise

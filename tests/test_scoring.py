import asyncio

import pytest
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool
from inspect_ai.tool import ToolCall

from tessera.compiler import compile_blueprint
from tessera.examples.toy_org import build_toy_blueprint
from tessera.evals.scoring import (
    consulted_claims,
    extract_final_answer,
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


def test_match_answer_requires_value_boundaries():
    assert match_answer("The SLA is 4 hours.", "4 hours")
    assert match_answer("THE SLA IS 4 HOURS.", "4 hours")            # case-insensitive
    assert not match_answer("The renewal date is 2026-03-01.", "4 hours")
    # regression: raw substring over-credited all of these
    assert not match_answer("The SLA is 24 hours.", "4 hours")
    assert not match_answer("The discount is 115%.", "15%")
    assert not match_answer("The rate is 8.15%.", "15%")
    assert not match_answer("Date: 2026-03-015.", "2026-03-01")
    assert match_answer("Maximum discount: 15%.", "15%")


def test_extract_final_answer_takes_the_last_answer_line():
    # last occurrence wins — models self-correct (same convention as inspect's patterns)
    assert extract_final_answer("ANSWER: 10%\nwait — the contract wins.\nANSWER: 15%") == "15%"
    assert extract_final_answer("answer:   4 hours  ") == "4 hours"
    assert extract_final_answer("no committed final line here") is None


def test_committed_answer_line_beats_quoted_values():
    # quoting the right value while COMMITTING to the stale one must not be credited
    g = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=[], consulted=set(),
        completion="The CRM shows 2026-01-01; a newer note says 2026-03-01.\nANSWER: 2026-01-01",
    )
    assert g["accuracy_ok"] is False
    # ...and transparent reasoning above a correct commitment is never penalized
    g2 = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=[], consulted=set(),
        completion="The CRM shows 2026-01-01, but the newer QBR note wins.\nANSWER: 2026-03-01",
    )
    assert g2["accuracy_ok"] is True


def test_fallback_without_answer_line_uses_distractors_last_mention_wins():
    # no ANSWER line: committing to the stale value while quoting the right one fails...
    g = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=[], consulted=set(),
        completion=("One note says 2026-03-01, but the CRM is the system of record, "
                    "so the renewal date is 2026-01-01."),
        distractor_values=["2026-01-01"],
    )
    assert g["accuracy_ok"] is False
    # ...while resolve-then-commit phrasing (expected value last) still passes
    g2 = grade_probe(
        expected_behavior="answer", expected_answer="2026-03-01",
        expected_sources=[], consulted=set(),
        completion=("The CRM says 2026-01-01 but the newer QBR note says 2026-03-01, "
                    "which takes precedence: 2026-03-01."),
        distractor_values=["2026-01-01"],
    )
    assert g2["accuracy_ok"] is True


def test_refusal_is_decided_by_the_committed_answer_line():
    # answer-probe: hedged reasoning above a committed answer is not a refusal...
    g = grade_probe(
        expected_behavior="answer", expected_answer="4 hours",
        expected_sources=[], consulted=set(),
        completion=("The docs alone don't have the SLA; the CRM record settles it.\n"
                    "ANSWER: 4 hours"),
    )
    assert g["refusal_ok"] is True and g["passed"] is True
    # ...and abstain-then-commit on a refuse-probe is a commitment, not a refusal
    g2 = grade_probe(
        expected_behavior="refuse", expected_answer=None,
        expected_sources=[], consulted=set(),
        completion=("I cannot determine which figure is authoritative, "
                    "but the CRM is usually right.\nANSWER: $1.2M"),
    )
    assert g2["refusal_ok"] is False and g2["passed"] is False


def test_committed_refusal_line_passes_a_refuse_probe():
    # the prompt's mandated abstention form: 'ANSWER: cannot determine'
    g = grade_probe(
        expected_behavior="refuse", expected_answer=None,
        expected_sources=[], consulted=set(),
        completion=("The two systems disagree with identical timestamps.\n"
                    "ANSWER: cannot determine"),
    )
    assert g["refusal_ok"] is True and g["passed"] is True


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


def test_score_attempt_stamps_scorer_version_and_format_flag(tmp_path):
    # the version marker is what keeps reports comparable across scorer changes
    manifest = _manifest(tmp_path)
    meta = ProbeMeta(probe_id="q_acme_renewal", conflict_type="resolvable",
                     resolution_rule="recency_wins", expected_behavior="answer",
                     expected_answer="2026-03-01",
                     expected_sources=[])
    s = score_attempt(messages=[], completion="Renewal date is 2026-03-01.",
                      meta=meta, manifest=manifest)
    assert s.metadata["scorer_version"] == "det-3"
    assert s.metadata["answer_format_ok"] is False     # no ANSWER line -> fallback path
    s2 = score_attempt(messages=[], completion="ANSWER: 2026-03-01",
                       meta=meta, manifest=manifest)
    assert s2.metadata["answer_format_ok"] is True


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


from tessera.evals.scoring import llm_score_attempt


async def _stub_true(*args):
    return True


async def _stub_false(*args):
    return False


def _both_globex_calls(manifest):
    note_path = manifest["globex.contract.note"]["artifact"]
    return [ChatMessageAssistant(content="", tool_calls=[
        ToolCall(id="1", function="crm_lookup", arguments={"account_name": "Globex Inc"}),
        ToolCall(id="2", function="docs_get_file", arguments={"path": note_path}),
    ])]


def test_sophisticated_refusal_is_recognized(tmp_path):
    # MIGRATED from xfail: the LLM refusal judge recognizes a keyword-free refusal,
    # so the unresolvable probe passes on the llm path. No xfail marker anymore.
    manifest = _manifest(tmp_path)
    meta = ProbeMeta(probe_id="q_globex_contract", conflict_type="unresolvable",
                     resolution_rule=None, expected_behavior="refuse",
                     expected_answer=None,
                     expected_sources=["globex.contract.crm", "globex.contract.note"])
    s = asyncio.run(llm_score_attempt(
        grader=None, question="What is Globex Inc's contract value?",
        messages=_both_globex_calls(manifest),
        completion=("The systems of record show directly opposing values with identical "
                    "timestamps; flagging for human review."),
        meta=meta, manifest=manifest,
        refusal_judge=_stub_true, accuracy_judge=_stub_false))
    assert s.value == CORRECT
    assert s.metadata["refusal_ok"] is True


def test_llm_answer_probe_passes_when_judges_say_correct_and_committed(tmp_path):
    manifest = _manifest(tmp_path)
    note_path = manifest["acme.renewal.note"]["artifact"]
    meta = ProbeMeta(probe_id="q_acme_renewal", conflict_type="resolvable",
                     resolution_rule="recency_wins", expected_behavior="answer",
                     expected_answer="2026-03-01",
                     expected_sources=["acme.renewal.crm", "acme.renewal.note"])
    messages = [ChatMessageAssistant(content="", tool_calls=[
        ToolCall(id="1", function="crm_lookup", arguments={"account_name": "Acme Corp"}),
        ToolCall(id="2", function="docs_get_file", arguments={"path": note_path}),
    ])]
    s = asyncio.run(llm_score_attempt(
        grader=None, question="When is Acme's renewal?", messages=messages,
        completion="2026-03-01 (the newer QBR note overrides the CRM).",
        meta=meta, manifest=manifest,
        refusal_judge=_stub_false, accuracy_judge=_stub_true))
    assert s.value == CORRECT


def test_llm_answer_probe_fails_when_accuracy_judge_says_wrong(tmp_path):
    manifest = _manifest(tmp_path)
    note_path = manifest["acme.renewal.note"]["artifact"]
    meta = ProbeMeta(probe_id="q_acme_renewal", conflict_type="resolvable",
                     resolution_rule="recency_wins", expected_behavior="answer",
                     expected_answer="2026-03-01",
                     expected_sources=["acme.renewal.crm", "acme.renewal.note"])
    messages = [ChatMessageAssistant(content="", tool_calls=[
        ToolCall(id="1", function="crm_lookup", arguments={"account_name": "Acme Corp"}),
        ToolCall(id="2", function="docs_get_file", arguments={"path": note_path}),
    ])]
    s = asyncio.run(llm_score_attempt(
        grader=None, question="When is Acme's renewal?", messages=messages,
        completion="It is 2026-01-01.", meta=meta, manifest=manifest,
        refusal_judge=_stub_false, accuracy_judge=_stub_false))
    assert s.value == INCORRECT


def test_llm_refuse_probe_fails_without_full_provenance(tmp_path):
    manifest = _manifest(tmp_path)
    meta = ProbeMeta(probe_id="q_globex_contract", conflict_type="unresolvable",
                     resolution_rule=None, expected_behavior="refuse",
                     expected_answer=None,
                     expected_sources=["globex.contract.crm", "globex.contract.note"])
    messages = [ChatMessageAssistant(content="", tool_calls=[
        ToolCall(id="1", function="crm_lookup", arguments={"account_name": "Globex Inc"}),
    ])]  # only read CRM, never the conflicting Docs note
    s = asyncio.run(llm_score_attempt(
        grader=None, question="What is Globex Inc's contract value?", messages=messages,
        completion="I cannot determine it; the sources are irreconcilable.",
        meta=meta, manifest=manifest,
        refusal_judge=_stub_true, accuracy_judge=_stub_false))
    assert s.value == INCORRECT
    assert s.metadata["provenance_ok"] is False


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


def test_scorer_factories_exist_and_reliability_scorer_is_the_deterministic_alias():
    from tessera.evals import scoring
    assert scoring.reliability_scorer is scoring.deterministic_reliability_scorer
    # factories build a scorer without resolving any model (resolution happens in score())
    assert callable(scoring.deterministic_reliability_scorer({}))
    assert callable(scoring.llm_reliability_scorer({}))

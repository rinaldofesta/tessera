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

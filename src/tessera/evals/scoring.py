"""Three-axis reliability scoring. Core logic is pure and dependency-light."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from inspect_ai.model import get_model
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState

from tessera.evals.dataset import ProbeMeta
from tessera.evals.judges import accuracy_judge as _default_accuracy_judge
from tessera.evals.judges import refusal_judge as _default_refusal_judge

_REFUSAL_MARKERS = (
    "i don't know", "i do not know", "don't know", "do not know",
    "i don't have", "don't have", "do not have",
    "cannot determine", "can't determine",
    "unable to", "no record", "could not find", "couldn't find",
    "cannot find", "can't find", "definitive answer", "not enough information",
)


def extract_tool_calls(messages: list[Any]) -> list[tuple[str, dict]]:
    """Collect (tool_name, arguments) from assistant tool calls, in order."""
    calls: list[tuple[str, dict]] = []
    for msg in messages:
        for tc in (getattr(msg, "tool_calls", None) or []):
            calls.append((tc.function, dict(tc.arguments or {})))
    return calls


def consulted_claims(tool_calls: list[tuple[str, dict]], manifest: dict[str, dict]) -> set[str]:
    """Map tool calls to the claim_ids they surfaced, via the compiled manifest."""
    consulted: set[str] = set()
    for name, args in tool_calls:
        if name == "crm_lookup":
            subject = args.get("account_name")
            consulted |= {
                cid for cid, m in manifest.items()
                if m.get("silo") == "crm" and m.get("subject") == subject
            }
        elif name == "docs_get_file":
            path = args.get("path")
            consulted |= {cid for cid, m in manifest.items() if m.get("artifact") == path}
    return consulted


def is_refusal(completion: str) -> bool:
    text = completion.lower()
    return any(marker in text for marker in _REFUSAL_MARKERS)


# det-1 was raw case-insensitive substring; det-2 scores the COMMITTED answer.
_SCORER_VERSION_DET = "det-2"
_SCORER_VERSION_LLM = "llm-1"

# Last 'ANSWER: ...' line wins — models self-correct (inspect's own pattern convention).
_ANSWER_LINE = re.compile(r"(?im)^\s*answer\s*:\s*(.+?)\s*$")


def extract_final_answer(completion: str) -> str | None:
    """The committed answer: the last 'ANSWER: <value>' line, or None if absent."""
    found = _ANSWER_LINE.findall(completion)
    return found[-1] if found else None


def _norm(text: str) -> str:
    return " ".join(text.split()).lower()


def _value_pattern(expected: str) -> re.Pattern[str]:
    """Boundary-guarded pattern for an expected value over _norm()ed text: no adjacent
    alphanumerics ('4 hours' must not hit '24 hours', '15%' not '115%'), and for
    digit-leading values no preceding dot either ('15%' must not hit '8.15%')."""
    value = _norm(expected).strip(".,;:!? ")
    lead = r"(?<![a-z0-9.])" if value[:1].isdigit() else r"(?<![a-z0-9])"
    return re.compile(lead + re.escape(value) + r"(?![a-z0-9])")


def match_answer(text: str, expected: str) -> bool:
    """Case-insensitive, whitespace-collapsed, boundary-guarded value match."""
    expected = expected.strip()
    if not expected:
        return False
    return _value_pattern(expected).search(_norm(text)) is not None


def _matches_with_distractors(completion: str, expected: str,
                              distractors: list[str] | tuple[str, ...]) -> bool:
    """Fallback when no ANSWER line exists: the expected value must appear, and no
    competing (distractor) value may appear AFTER its last mention — last-mention-wins,
    so the ideal transparent answer (cite the stale value, then commit to the right
    one) still passes, while committing to the stale value does not."""
    norm = _norm(completion)
    last_expected = max((m.end() for m in _value_pattern(expected).finditer(norm)), default=-1)
    if last_expected < 0:
        return False
    for d in distractors:
        d = d.strip()
        if not d:
            continue
        last_d = max((m.end() for m in _value_pattern(d).finditer(norm)), default=-1)
        if last_d > last_expected:
            return False
    return True


def grade_from_signals(*, expected_behavior: str, answered_correctly: bool,
                       refused: bool, provenance_ok: bool) -> dict[str, bool]:
    """Pure boolean combiner shared by the deterministic and LLM engines."""
    if expected_behavior == "refuse":
        accuracy_ok = refused      # abstaining IS the correct behavior on a refuse-probe
        refusal_ok = refused
        passed = refused and provenance_ok
    else:  # answer
        accuracy_ok = answered_correctly
        refusal_ok = not refused   # "did it wrongly abstain?"
        passed = answered_correctly and provenance_ok and not refused
    return {"accuracy_ok": accuracy_ok, "refusal_ok": refusal_ok,
            "provenance_ok": provenance_ok, "passed": passed}


def assert_independent_grader(grader, model_under_test) -> None:
    """Fail loud if the grader is the same model as the model-under-test.

    Compares the canonical str(Model) form ("provider/model"); accepts any objects
    with a str() (real Models, or plain strings in tests).
    """
    if str(grader) == str(model_under_test):
        raise ValueError(
            f"Grader model ({grader}) must differ from the model-under-test "
            f"({model_under_test}); bind a distinct grader via "
            f"--model-role grader=<provider/model>."
        )


def grade_probe(
    *,
    expected_behavior: str,
    expected_answer: str | None,
    expected_sources: list[str],
    consulted: set[str],
    completion: str,
    distractor_values: list[str] | tuple[str, ...] = (),
) -> dict[str, bool]:
    """Deterministic-signal convenience wrapper over grade_from_signals."""
    provenance_ok = set(expected_sources).issubset(consulted)
    refused = is_refusal(completion)
    if expected_behavior == "answer":
        if not expected_answer:
            raise ValueError("answer probes require a non-empty expected_answer")
        final = extract_final_answer(completion)
        if final is not None:
            # the committed line is the answer; reasoning above it is never penalized
            answered_correctly = match_answer(final, expected_answer)
        else:
            answered_correctly = _matches_with_distractors(
                completion, expected_answer, distractor_values)
    else:
        answered_correctly = False  # ignored by the combiner for refuse-probes
    return grade_from_signals(expected_behavior=expected_behavior,
                              answered_correctly=answered_correctly,
                              refused=refused, provenance_ok=provenance_ok)


def score_attempt(*, messages: list, completion: str, meta: ProbeMeta,
                  manifest: dict[str, dict]) -> Score:
    """Pure: build a Score from one attempt's messages + final completion."""
    calls = extract_tool_calls(messages)
    consulted = consulted_claims(calls, manifest)
    result = grade_probe(
        expected_behavior=meta.expected_behavior,
        expected_answer=meta.expected_answer,
        expected_sources=meta.expected_sources,
        consulted=consulted,
        completion=completion,
        distractor_values=meta.distractor_values,
    )
    return Score(
        value=CORRECT if result["passed"] else INCORRECT,
        answer=completion,
        explanation=(
            f"axes={result} consulted={sorted(consulted)} "
            f"expected_sources={meta.expected_sources} tools={[c[0] for c in calls]}"
        ),
        metadata={**result, "consulted": sorted(consulted),
                  "scorer_version": _SCORER_VERSION_DET,
                  "answer_format_ok": extract_final_answer(completion) is not None},
    )


async def llm_score_attempt(*, grader, question: str, messages: list, completion: str,
                            meta: ProbeMeta, manifest: dict[str, dict],
                            refusal_judge=_default_refusal_judge,
                            accuracy_judge=_default_accuracy_judge) -> Score:
    """Async seam: compute the three signals (judges + deterministic provenance) and combine."""
    consulted = consulted_claims(extract_tool_calls(messages), manifest)
    provenance_ok = set(meta.expected_sources).issubset(consulted)

    if meta.expected_behavior == "refuse":
        refused = await refusal_judge(grader, question, completion)
        answered_correctly = False
    else:  # answer-probe: run both judges concurrently
        answered_correctly, refused = await asyncio.gather(
            accuracy_judge(grader, question, completion, meta.expected_answer or ""),
            refusal_judge(grader, question, completion),
        )

    result = grade_from_signals(expected_behavior=meta.expected_behavior,
                                answered_correctly=answered_correctly,
                                refused=refused, provenance_ok=provenance_ok)
    return Score(
        value=CORRECT if result["passed"] else INCORRECT,
        answer=completion,
        explanation=f"axes={result} consulted={sorted(consulted)} engine=llm",
        metadata={**result, "consulted": sorted(consulted),
                  "scorer_version": _SCORER_VERSION_LLM},
    )


@scorer(metrics=[accuracy(), stderr()])
def deterministic_reliability_scorer(manifest: dict[str, dict]):
    """Key-free deterministic engine (keyword refusal + committed-answer accuracy)."""
    async def score(state: TaskState, target: Target) -> Score:
        return score_attempt(
            messages=state.messages,
            completion=state.output.completion if state.output else "",
            meta=state.metadata_as(ProbeMeta), manifest=manifest)
    return score


# Backward-compat alias (existing task.py / tests import this name).
reliability_scorer = deterministic_reliability_scorer


@scorer(metrics=[accuracy(), stderr()])
def llm_reliability_scorer(manifest: dict[str, dict], *, grader_model=None,
                           refusal_judge=_default_refusal_judge,
                           accuracy_judge=_default_accuracy_judge):
    """Model-graded engine. Resolves an INDEPENDENT grader and fails loud if it is the
    model-under-test. grader_model/judges are optional injection points (real defaults)."""
    async def score(state: TaskState, target: Target) -> Score:
        grader = (get_model(grader_model) if grader_model is not None
                  else get_model(role="grader", required=True))
        assert_independent_grader(grader, state.model)
        return await llm_score_attempt(
            grader=grader, question=state.input_text, messages=state.messages,
            completion=state.output.completion if state.output else "",
            meta=state.metadata_as(ProbeMeta), manifest=manifest,
            refusal_judge=refusal_judge, accuracy_judge=accuracy_judge)
    return score


# --- Known limitations (deterministic engine, det-2) ---
# * Provenance for crm_lookup is SUBJECT-granular, not field-granular: one lookup
#   credits every CRM claim for that subject (the tool returns the whole record).
# * Accuracy scores the COMMITTED answer: the last 'ANSWER:' line when present
#   (transparent reasoning above it is never penalized), else a boundary-guarded
#   match over the whole completion with distractor-exclusion (last-mention-wins).
#   The fallback still mis-scores "X, not Y" negations and trailing parentheticals
#   ("X (CRM still shows Y)"); date/number paraphrases ("March 1, 2026" for
#   "2026-03-01") are not matched — keep expected_answer in the wording the org
#   materializes. Score.metadata records scorer_version + answer_format_ok.
# * is_refusal is a heuristic; an abstention phrase plus a hallucinated assertion on a
#   refuse-probe is not fully caught. The llm engine is the higher-fidelity cross-check.

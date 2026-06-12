"""Three-axis reliability scoring. Core logic is pure and dependency-light."""

from __future__ import annotations

import asyncio
import json
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


def extract_tool_events(messages: list[Any]) -> list[tuple[str, dict, str | None]]:
    """Collect (tool_name, arguments, result_text) from the transcript, in call order.

    result_text is the paired ChatMessageTool content (matched via tool_call_id), or
    None when the call never got a recorded result."""
    results: dict[str, str] = {}
    for msg in messages:
        call_id = getattr(msg, "tool_call_id", None)
        if call_id is not None:
            results[call_id] = getattr(msg, "text", "") or ""
    events: list[tuple[str, dict, str | None]] = []
    for msg in messages:
        for tc in (getattr(msg, "tool_calls", None) or []):
            events.append((tc.function, dict(tc.arguments or {}), results.get(tc.id)))
    return events


def _crm_record_fields(result: str | None) -> frozenset[str]:
    """The field names a crm_lookup actually returned; empty for NOT_FOUND/errors."""
    if not result:
        return frozenset()
    try:
        record = json.loads(result)
    except ValueError:
        return frozenset()
    return frozenset(record) if isinstance(record, dict) else frozenset()


def consulted_claims(tool_events: list[tuple[str, dict, str | None]],
                     manifest: dict[str, dict]) -> set[str]:
    """Map tool calls to the claim_ids they surfaced, via the compiled manifest.

    CRM credit is per-field and comes from the RESPONSE (det-4 / ADR-0005): a claim
    counts only if its predicate is a key of the record the lookup actually returned —
    NOT_FOUND, errored, and unanswered calls credit nothing. Docs files are one
    claim-bundle per file, so the path argument is the address."""
    consulted: set[str] = set()
    for name, args, result in tool_events:
        if name == "crm_lookup":
            subject = args.get("account_name")
            fields = _crm_record_fields(result)
            consulted |= {
                cid for cid, m in manifest.items()
                if m.get("silo") == "crm" and m.get("subject") == subject
                and m.get("predicate") in fields
            }
        elif name == "docs_get_file":
            path = args.get("path")
            consulted |= {cid for cid, m in manifest.items() if m.get("artifact") == path}
    return consulted


def is_refusal(completion: str) -> bool:
    text = completion.lower()
    return any(marker in text for marker in _REFUSAL_MARKERS)


# det-1 was raw case-insensitive substring; det-2 scored the COMMITTED answer for
# accuracy; det-3 decides refusal on that same line (keyword scan only as fallback);
# det-4 makes CRM provenance field-granular and response-based (llm-2 mirrors it —
# both engines share the deterministic provenance signal).
_SCORER_VERSION_DET = "det-4"
_SCORER_VERSION_LLM = "llm-2"

# Last 'ANSWER: ...' line wins — models self-correct (inspect's own pattern convention).
# Tolerates markdown dressing (**ANSWER:**, '- ANSWER:', 'Final ANSWER:') so dressed
# commitments still route to the strong committed-line path, not the weaker fallback.
_ANSWER_LINE = re.compile(r"(?im)^[\s>*#-]*(?:final\s+)?answer\**\s*:\s*\**\s*(.+?)[\s*]*$")

# A committed line refuses only when it LEADS with the abstention — a justification
# tail ('$425k (no record of a later amendment)') is a commitment, not a refusal.
_COMMITTED_REFUSALS = (
    "cannot determine", "can't determine", "unknown",
    "i don't know", "i do not know", "no answer", "n/a",
)


def _committed_refusal(line: str) -> bool:
    norm = _norm(line).strip(".,;:!? ")
    return norm.startswith(_COMMITTED_REFUSALS)


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
    final = extract_final_answer(completion)
    # the committed line decides refusal too: hedged reasoning above a committed
    # answer is not a refusal, and abstain-then-commit IS a commitment
    refused = _committed_refusal(final) if final is not None else is_refusal(completion)
    if expected_behavior == "answer":
        if not expected_answer:
            raise ValueError("answer probes require a non-empty expected_answer")
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
    events = extract_tool_events(messages)
    consulted = consulted_claims(events, manifest)
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
            f"expected_sources={meta.expected_sources} tools={[e[0] for e in events]}"
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
    consulted = consulted_claims(extract_tool_events(messages), manifest)
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
    """Key-free deterministic engine: the committed ANSWER line decides accuracy and
    refusal; heuristic fallbacks (distractors / keyword scan) apply without it."""
    async def score(state: TaskState, target: Target) -> Score:
        return score_attempt(
            messages=state.messages,
            completion=state.output.completion if state.output else "",
            meta=state.metadata_as(ProbeMeta), manifest=manifest)
    return score


# Backward-compat alias (existing task.py / tests import this name).
reliability_scorer = deterministic_reliability_scorer


# Where the delegation chain (evals/delegation.py) stores the producer's submitted
# brief for the scorer — per-sample, via inspect's solver↔scorer Store.
DELEGATION_PRODUCER_KEY = "tessera:producer_completion"


def hop_flags(*, producer_completion: str, completion: str,
              expected_behavior: str) -> dict[str, bool]:
    """Delegation diagnostics: how the refusal flag fared across the hop.

    On a refuse-probe, exactly one of two stories explains a committed final answer:
    the producer held the line and the consumer committed anyway (flag_dropped), or
    the producer already fabricated and the consumer relayed it as settled fact
    (conflict_laundered). Both stages refusing is the pass; the flags split the
    failures by where the fabrication originated."""
    prod_final = extract_final_answer(producer_completion)
    producer_refused = (_committed_refusal(prod_final) if prod_final is not None
                        else is_refusal(producer_completion))
    cons_final = extract_final_answer(completion)
    consumer_refused = (_committed_refusal(cons_final) if cons_final is not None
                        else is_refusal(completion))
    flags = {"producer_refused": producer_refused,
             "consumer_refused": consumer_refused}
    if expected_behavior == "refuse":
        flags["flag_dropped"] = producer_refused and not consumer_refused
        flags["conflict_laundered"] = not producer_refused and not consumer_refused
    return flags


def delegated_score_attempt(*, messages: list, completion: str, producer_completion: str,
                            meta: ProbeMeta, manifest: dict[str, dict]) -> Score:
    """det-4 over the merged producer+consumer transcript, plus the hop flags.

    The axes need no delegation-specific logic: provenance reads the producer's tool
    traffic from the merged messages; accuracy/refusal read the consumer's committed
    line (state.output is the consumer's submission)."""
    s = score_attempt(messages=messages, completion=completion, meta=meta,
                      manifest=manifest)
    s.metadata.update(hop_flags(producer_completion=producer_completion,
                                completion=completion,
                                expected_behavior=meta.expected_behavior))
    return s


@scorer(metrics=[accuracy(), stderr()])
def delegated_reliability_scorer(manifest: dict[str, dict]):
    """Deterministic engine for the delegated task: same det-4 contract, with the
    producer's brief pulled from the per-sample store for the hop diagnostics."""
    async def score(state: TaskState, target: Target) -> Score:
        return delegated_score_attempt(
            messages=state.messages,
            completion=state.output.completion if state.output else "",
            producer_completion=state.store.get(DELEGATION_PRODUCER_KEY, ""),
            meta=state.metadata_as(ProbeMeta), manifest=manifest)
    return score


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


# --- Known limitations (deterministic engine, det-4) ---
# * CRM provenance is FIELD-granular and response-based: a claim is credited only
#   when its predicate came back in the lookup's recorded response — NOT_FOUND and
#   errored calls credit nothing. The scorer therefore depends on crm_lookup
#   responses being recorded as JSON text in the log; docs credit stays call-based
#   (one claim-bundle per file, the path is the address).
# * Accuracy scores the COMMITTED answer: the last 'ANSWER:' line when present
#   (transparent reasoning above it is never penalized), else a boundary-guarded
#   match over the whole completion with distractor-exclusion (last-mention-wins).
#   The fallback still mis-scores "X, not Y" negations and trailing parentheticals
#   ("X (CRM still shows Y)"); date/number paraphrases ("March 1, 2026" for
#   "2026-03-01") are not matched — keep expected_answer in the wording the org
#   materializes. Score.metadata records scorer_version + answer_format_ok.
# * Refusal is also decided by the committed line when present ('ANSWER: cannot
#   determine' refuses; 'ANSWER: $1.2M' under hedged reasoning commits — abstain-then-
#   hallucinate IS caught). Without an ANSWER line the full-text keyword scan remains,
#   where that case is not. The llm engine is the higher-fidelity cross-check.

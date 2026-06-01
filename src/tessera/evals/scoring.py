"""Three-axis reliability scoring. Core logic is pure and dependency-light."""

from __future__ import annotations

from typing import Any

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState

from tessera.evals.dataset import ProbeMeta

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


def match_answer(completion: str, expected: str) -> bool:
    # v0: case-insensitive substring. Keep toy answers distinctive (e.g. "4 hours",
    # not "4") to avoid false positives; model-graded matching is the later upgrade.
    return expected.strip().lower() in completion.lower()


def grade_probe(
    *,
    expected_behavior: str,
    expected_answer: str | None,
    expected_sources: list[str],
    consulted: set[str],
    completion: str,
) -> dict[str, bool]:
    """Grade one probe attempt on accuracy, provenance, and correct refusal.

    For answer-probes, accuracy depends ONLY on whether the agent stated the
    correct answer -- NOT on refusal markers, so an answer that explains a
    resolved conflict ("the sources conflict, the newer note wins") is not
    misread as an abstention.
    """
    provenance_ok = set(expected_sources).issubset(consulted)
    refused = is_refusal(completion)

    if expected_behavior == "refuse":
        refusal_ok = refused
        accuracy_ok = refused  # the "correct answer" for a refuse-probe is to abstain
        passed = refusal_ok and provenance_ok
    else:  # answer
        if not expected_answer:
            raise ValueError("answer probes require a non-empty expected_answer")
        accuracy_ok = match_answer(completion, expected_answer)
        # An answer-probe is wrongly refused only if it abstained AND failed to
        # state the answer; stating the answer (even while noting a conflict) is fine.
        refusal_ok = not (refused and not accuracy_ok)
        passed = accuracy_ok and provenance_ok

    return {
        "accuracy_ok": accuracy_ok,
        "provenance_ok": provenance_ok,
        "refusal_ok": refusal_ok,
        "passed": passed,
    }


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
    )
    return Score(
        value=CORRECT if result["passed"] else INCORRECT,
        answer=completion,
        explanation=(
            f"axes={result} consulted={sorted(consulted)} "
            f"expected_sources={meta.expected_sources} tools={[c[0] for c in calls]}"
        ),
        metadata={**result, "consulted": sorted(consulted)},
    )


@scorer(metrics=[accuracy(), stderr()])
def reliability_scorer(manifest: dict[str, dict]):
    """A probe passes only if accuracy AND full provenance AND correct refusal hold."""

    async def score(state: TaskState, target: Target) -> Score:
        return score_attempt(
            messages=state.messages,
            completion=state.output.completion if state.output else "",
            meta=state.metadata_as(ProbeMeta),
            manifest=manifest,
        )

    return score


# --- Known v0 limitations (deterministic scoring; model-graded is the planned upgrade) ---
# * Provenance for crm_lookup is SUBJECT-granular, not field-granular: one lookup
#   credits every CRM claim for that subject (the tool returns the whole record).
# * match_answer is substring-based: an answer that merely quotes the right value
#   (or mentions both the stale and correct value) can over-credit accuracy.
# * is_refusal is a heuristic; an abstention phrase plus a hallucinated assertion on a
#   refuse-probe is not fully caught. These are addressed by model-graded scoring later.

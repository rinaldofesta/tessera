"""Three-axis reliability scoring. Core logic is pure and dependency-light."""

from __future__ import annotations

from typing import Any

_REFUSAL_MARKERS = (
    "i don't know", "i do not know", "don't have", "do not have",
    "cannot determine", "can't determine", "cannot give", "can't give",
    "insufficient", "not available", "unable to", "no information",
    "sources conflict", "conflicting",
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
    """Grade one probe attempt on accuracy, provenance, and correct refusal."""
    provenance_ok = set(expected_sources).issubset(consulted)
    refused = is_refusal(completion)

    if expected_behavior == "refuse":
        refusal_ok = refused
        accuracy_ok = refused  # the "correct answer" for a refuse-probe is to abstain
    else:  # answer
        accuracy_ok = (not refused) and match_answer(completion, expected_answer or "")
        refusal_ok = not refused

    passed = accuracy_ok and provenance_ok and refusal_ok
    return {
        "accuracy_ok": accuracy_ok,
        "provenance_ok": provenance_ok,
        "refusal_ok": refusal_ok,
        "passed": passed,
    }

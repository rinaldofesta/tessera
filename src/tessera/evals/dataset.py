"""Map a Blueprint's probes into an inspect_ai dataset of Samples."""

from __future__ import annotations

from inspect_ai.dataset import MemoryDataset, Sample
from pydantic import BaseModel

from tessera.models import Blueprint


class ProbeMeta(BaseModel, frozen=True):
    """Typed metadata attached to each Sample (frozen: required by metadata_as)."""

    probe_id: str
    conflict_type: str
    resolution_rule: str | None
    expected_behavior: str
    expected_answer: str | None
    expected_sources: list[str]
    # values competing with the expected answer (default keeps old logs readable)
    distractor_values: list[str] = []


def _distractor_values(blueprint: Blueprint, probe) -> list[str]:
    """Competing values for an answer-probe, derived mechanically from the blueprint:
    among the probe's referenced claims, a (subject, predicate) group holding more
    than one distinct value IS the conflict the agent must resolve — every value not
    part of the expected answer is a distractor the committed answer must not end on.
    Cross-silo references that merely support the answer (no conflict) yield none."""
    if probe.expected_behavior.value != "answer" or not probe.expected_answer:
        return []
    claims = {c.claim_id: c for c in blueprint.claims}
    groups: dict[tuple[str, str], list[str]] = {}
    for cid in probe.references:
        c = claims.get(cid)
        if c is not None:
            groups.setdefault((c.subject, c.predicate), []).append(str(c.value))
    expected = probe.expected_answer.lower()
    out: set[str] = set()
    for values in groups.values():
        distinct = set(values)
        if len(distinct) > 1:
            out |= {v for v in distinct if v.lower() not in expected}
    return sorted(out)


def blueprint_to_dataset(blueprint: Blueprint) -> MemoryDataset:
    samples = []
    for probe in blueprint.probes:
        meta = ProbeMeta(
            probe_id=probe.probe_id,
            conflict_type=probe.conflict_type.value,
            resolution_rule=probe.resolution_rule.value if probe.resolution_rule else None,
            expected_behavior=probe.expected_behavior.value,
            expected_answer=probe.expected_answer,
            expected_sources=list(probe.expected_sources),
            distractor_values=_distractor_values(blueprint, probe),
        )
        samples.append(
            Sample(
                input=probe.question,
                target=probe.expected_answer or "",
                id=probe.probe_id,
                metadata=meta.model_dump(),
            )
        )
    return MemoryDataset(samples=samples, name="tessera-probes")

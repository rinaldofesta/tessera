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

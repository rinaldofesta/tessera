"""Declarative blueprint data models: Claim, Probe, Blueprint.

These mirror the design spec
(docs/superpowers/specs/2026-06-01-tessera-generator-data-shape-design.md).
A blueprint is the *declarative* description of a fragmented organization; a
separate deterministic compiler turns it into MCP-served silo assets plus an
Inspect dataset.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RenderAs(str, Enum):
    """How a claim is materialized into its silo."""

    field = "field"  # a structured record field (e.g. CRM)
    prose = "prose"  # a sentence in an unstructured document (e.g. wiki/docs)


class ConflictType(str, Enum):
    """The four-way taxonomy at the heart of the eval: what kind of disagreement (if
    any) the silos hold for a probe. It decides whether the right move is to answer or
    to refuse, and `unresolvable` is the column that actually separates reliable agents
    from confident fabricators."""

    none = "none"                   # no disagreement; a cross-silo chain — join every relevant source to answer
    resolvable = "resolvable"       # silos disagree, but a resolution_rule breaks the tie
    unresolvable = "unresolvable"   # silos disagree with equal standing; MUST refuse, not invent a winner
    void = "void"                   # the question has no answer in the org at all; MUST refuse


class ResolutionRule(str, Enum):
    """How a `resolvable` conflict is decided. Note authority can outrank recency: a
    source that declares itself binding wins even over a fresher one."""

    recency_wins = "recency_wins"       # the more recently asserted claim wins
    authority_wins = "authority_wins"   # the higher-authority (binding) claim wins, even if older


class ExpectedBehavior(str, Enum):
    """What a correct agent does on this probe — the outcome the scorer grades against."""

    answer = "answer"   # commit to the correct value
    refuse = "refuse"   # abstain (an unresolvable tie or a void question)


class Render(BaseModel):
    """Rendering directive for a claim. ``as`` is aliased (Python keyword)."""

    model_config = ConfigDict(populate_by_name=True)

    as_: RenderAs = Field(alias="as")
    template: str | None = None

    @model_validator(mode="after")
    def _prose_requires_template(self) -> Render:
        if self.as_ is RenderAs.prose and not self.template:
            raise ValueError("prose render requires a 'template'")
        return self


class Claim(BaseModel):
    """An atomic knowledge unit that lives in exactly one silo."""

    claim_id: str
    subject: str
    predicate: str
    value: Any
    silo: str
    asserted_at: str | None = None  # ISO-8601; required when a recency rule applies
    authority: int | None = None
    render: Render

    @model_validator(mode="after")
    def _prose_template_renders(self) -> Claim:
        # The prose template is user-controlled and compiled with str.format(value=...).
        # A template referencing anything other than {value} ({nope}, {0}, {value[0]})
        # raises KeyError/IndexError/etc. in the compiler — an uncaught 500. Trial-render
        # it here with the real value so a bad template is a structured authoring-time
        # error (a 400 on every API write path) instead.
        if self.render.as_ is RenderAs.prose and self.render.template is not None:
            try:
                self.render.template.format(value=self.value)
            except Exception as exc:  # noqa: BLE001 — str.format's failure surface is wide
                # (KeyError/IndexError/AttributeError/ValueError/TypeError/OverflowError,
                # plus locale/format-spec errors); any of them would be an uncaught 500 in
                # the compiler, so any of them must be a structured authoring-time error.
                raise ValueError(
                    f"prose template must render with {{value}} only; "
                    f"rendering failed with {type(exc).__name__}: {exc}"
                ) from exc
        return self


class Probe(BaseModel):
    """A question that references claims and declares expected behavior."""

    probe_id: str
    question: str
    references: list[str] = Field(default_factory=list)
    conflict_type: ConflictType
    resolution_rule: ResolutionRule | None = None
    expected_behavior: ExpectedBehavior
    expected_answer: str | None = None
    expected_sources: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coherent(self) -> Probe:
        # Enforce that a probe's conflict_type, expected_behavior and fields agree, so an
        # incoherent probe (e.g. a 'void' that expects an answer) is rejected at authoring
        # time rather than silently mis-scored at eval time.
        if self.expected_behavior is ExpectedBehavior.refuse and self.expected_answer is not None:
            raise ValueError("refuse probes must have expected_answer = null")
        if self.expected_behavior is ExpectedBehavior.answer and self.expected_answer is None:
            raise ValueError("answer probes must carry an expected_answer")
        if self.conflict_type is ConflictType.resolvable and self.resolution_rule is None:
            raise ValueError("resolvable conflicts require a resolution_rule")
        if self.conflict_type is ConflictType.void:
            if self.references:
                raise ValueError("void probes must have no references")
            if self.expected_behavior is not ExpectedBehavior.refuse:
                raise ValueError("void probes must expect refusal")
        return self


class Blueprint(BaseModel):
    """A fragmented organization: the claims it knows and the probes we ask it."""

    claims: list[Claim]
    probes: list[Probe] = Field(default_factory=list)

    @model_validator(mode="after")
    def _referential_integrity(self) -> Blueprint:
        # claim_ids are unique and every probe reference / expected_source points at a real
        # claim. The compiler's manifest and the scorer's provenance check both assume this,
        # so we fail fast here instead of producing a dangling reference downstream.
        seen: set[str] = set()
        for claim in self.claims:
            if claim.claim_id in seen:
                raise ValueError(f"duplicate claim_id: {claim.claim_id!r}")
            seen.add(claim.claim_id)

        for probe in self.probes:
            for ref in probe.references:
                if ref not in seen:
                    raise ValueError(
                        f"probe {probe.probe_id!r} references unknown claim {ref!r}"
                    )
            for src in probe.expected_sources:
                if src not in seen:
                    raise ValueError(
                        f"probe {probe.probe_id!r} expected_source {src!r} is not a claim"
                    )
        return self

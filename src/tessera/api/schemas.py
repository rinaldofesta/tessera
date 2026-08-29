"""Request models for the Tessera API. Responses are the plain report dict from
report.serialize.report_to_dict, so only the run request needs a schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    model: str
    grader: str | None = None        # required only for the llm engine
    judge: Literal["llm", "deterministic"] = "llm"
    org: str = "toy"                 # which blueprint to evaluate (see /api/orgs)
    epochs: int = Field(3, ge=1, le=10)   # k for pass^k; bounds match the UI selector
    scaffold: Literal["baseline", "refuse-aware"] = "baseline"
    seed: int = Field(0, ge=0)


ComparisonIntervention = Literal[
    "model", "org", "engine", "grader", "k", "scaffold", "seed", "harness",
]


class ComparisonRequest(BaseModel):
    evaluation_a: str
    evaluation_b: str
    intervention: ComparisonIntervention = "model"


class PreflightRequest(BaseModel):
    model: str
    require_tools: bool = True
    refresh: bool = False


class ExperimentVariant(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    label: str
    model: str
    grader: str | None = None
    judge: Literal["llm", "deterministic"] = "deterministic"
    org: str = "toy"
    epochs: int = Field(3, ge=1, le=10)
    scaffold: Literal["baseline", "refuse-aware"] = "baseline"
    seed: int = Field(0, ge=0)

    def as_run_request(self) -> RunRequest:
        return RunRequest(
            model=self.model, grader=self.grader, judge=self.judge, org=self.org,
            epochs=self.epochs, scaffold=self.scaffold, seed=self.seed,
        )


class ExperimentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    baseline_variant: str
    intervention: ComparisonIntervention = "model"
    variants: list[ExperimentVariant] = Field(min_length=2, max_length=12)
    repeats: int = Field(1, ge=1, le=10)
    max_cost: float | None = Field(None, gt=0)
    max_consecutive_errors: int = Field(3, ge=1, le=10)

    def model_post_init(self, __context) -> None:
        ids = [variant.id for variant in self.variants]
        if len(ids) != len(set(ids)):
            raise ValueError("experiment variant ids must be unique")
        if self.baseline_variant not in ids:
            raise ValueError("baseline_variant must name one of the variants")
        baseline = next(variant for variant in self.variants if variant.id == self.baseline_variant)
        fields = {
            "model": "model", "org": "org", "engine": "judge", "grader": "grader",
            "k": "epochs", "scaffold": "scaffold", "seed": "seed",
        }
        if self.intervention not in fields:
            raise ValueError(f"{self.intervention} experiments are not launchable by this runner")
        for variant in self.variants:
            if variant.id == self.baseline_variant:
                continue
            changed = [
                dimension for dimension, field in fields.items()
                if getattr(baseline, field) != getattr(variant, field)
            ]
            if changed != [self.intervention]:
                raise ValueError(
                    f"variant {variant.id} must change only {self.intervention}; "
                    f"changed {changed or ['nothing']}"
                )

"""Request models for API operations not already defined by the core contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ArchiveRequest(BaseModel):
    archived: bool = True


ComparisonIntervention = Literal[
    "model", "org", "engine", "grader", "k", "scaffold", "seed", "harness",
]


class ComparisonRequest(BaseModel):
    a: str
    b: str
    intervention: ComparisonIntervention = "model"

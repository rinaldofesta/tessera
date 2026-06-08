"""Request models for the Tessera API. Responses are the plain report dict from
report.serialize.report_to_dict, so only the run request needs a schema."""

from __future__ import annotations

from pydantic import BaseModel


class RunRequest(BaseModel):
    model: str
    grader: str | None = None        # required only for the llm engine
    judge: str = "llm"               # "llm" | "deterministic"
    org: str = "toy"                 # which blueprint to evaluate (see /api/orgs)
    epochs: int = 3

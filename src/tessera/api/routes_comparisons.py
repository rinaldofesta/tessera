"""Evidence-aware comparisons over completed folder-store runs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from tessera.api import responses as R
from tessera.api.schemas import ComparisonRequest
from tessera.errors import SpecError
from tessera.report.compare import compare_reports

router = APIRouter()


def _completed_run(request: Request, ref: str):
    """The run plus its already-loaded report: report.json is not cached on the
    record, so callers must reuse this read rather than calling `.report()` again."""
    try:
        run = request.app.state.runs.get(ref)
    except SpecError as exc:
        raise HTTPException(404, str(exc)) from exc
    report = run.report()
    if run.data["status"] != "completed" or report is None:
        raise HTTPException(409, f"run is not completed: {ref}")
    return run, report


@router.post("/api/comparisons", response_model=R.ComparisonResult)
def create_comparison(payload: ComparisonRequest, request: Request):
    arm_a, report_a = _completed_run(request, payload.a)
    arm_b, report_b = _completed_run(request, payload.b)
    try:
        return compare_reports(
            report_a,
            report_b,
            intervention=payload.intervention,
            receipt_a=arm_a.receipt(),
            receipt_b=arm_b.receipt(),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

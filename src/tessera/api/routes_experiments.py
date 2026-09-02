"""Create, inspect, resume, and compare controlled experiments."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from tessera.api import responses as R
from tessera.api.experiments import run_experiment
from tessera.api.schemas import ComparisonIntervention, ExperimentRequest
from tessera.report.compare import compare_report_sets

router = APIRouter()


def _validate_variants(payload: ExperimentRequest) -> None:
    for variant in payload.variants:
        if variant.judge == "llm" and not variant.grader:
            raise HTTPException(400, f"variant {variant.id}: llm grading requires a grader")
        if variant.grader and variant.grader == variant.model:
            raise HTTPException(400, f"variant {variant.id}: grader must differ from the model")


async def _schedule(experiment_id: str, payload: ExperimentRequest, request: Request) -> None:
    await request.app.state.schedule(run_experiment(
        experiment_id, payload, run_store=request.app.state.run_store,
        workbench_store=request.app.state.workbench_store,
        eval_runner=request.app.state.eval_runner,
    ))


@router.post("/api/experiments", status_code=201, response_model=R.ExperimentStarted)
async def start_experiment(payload: ExperimentRequest, request: Request):
    _validate_variants(payload)
    experiment_id = request.app.state.workbench_store.create_experiment(payload)
    await _schedule(experiment_id, payload, request)
    current = request.app.state.workbench_store.get_experiment(experiment_id)
    return {"experiment_id": experiment_id, "status": current["status"]}


@router.get("/api/experiments", response_model=list[R.Experiment])
def list_experiments(request: Request):
    return request.app.state.workbench_store.list_experiments()


@router.get("/api/experiments/{experiment_id}", response_model=R.Experiment)
def get_experiment(experiment_id: str, request: Request):
    item = request.app.state.workbench_store.get_experiment(experiment_id)
    if item is None:
        raise HTTPException(404, f"unknown experiment: {experiment_id}")
    return item


@router.post("/api/experiments/{experiment_id}/resume", response_model=R.ExperimentStarted)
async def resume_experiment(experiment_id: str, request: Request):
    item = request.app.state.workbench_store.get_experiment(experiment_id)
    if item is None:
        raise HTTPException(404, f"unknown experiment: {experiment_id}")
    if item["status"] == "running":
        raise HTTPException(409, "experiment is already running")
    request.app.state.workbench_store.resume_experiment(experiment_id)
    payload = ExperimentRequest.model_validate(item["request"])
    await _schedule(experiment_id, payload, request)
    current = request.app.state.workbench_store.get_experiment(experiment_id)
    return {"experiment_id": experiment_id, "status": current["status"]}


@router.get(
    "/api/experiments/{experiment_id}/comparisons/{variant_id}",
    response_model=R.ExperimentComparison,
)
def experiment_comparison(experiment_id: str, variant_id: str, request: Request,
                          intervention: ComparisonIntervention | None = None):
    experiment = request.app.state.workbench_store.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(404, f"unknown experiment: {experiment_id}")
    baseline = experiment["baseline_variant"]
    if variant_id == baseline:
        raise HTTPException(400, "choose a non-baseline variant")

    def reports_for(candidate: str):
        out = []
        for cell in experiment["cells"]:
            if cell["variant_id"] != candidate or cell["status"] != "done" or not cell["run_id"]:
                continue
            run = request.app.state.run_store.get(cell["run_id"])
            if run and run["report"]:
                out.append((cell["repeat_index"], run["report"]))
        return out

    try:
        return compare_report_sets(
            reports_for(baseline), reports_for(variant_id),
            intervention=intervention or experiment["request"]["intervention"],
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc))

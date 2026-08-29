"""Resumable experiment orchestration over ordinary Tessera eval runs."""

from __future__ import annotations

from tessera.api.runner import run_eval_job
from tessera.api.schemas import ExperimentRequest


async def run_experiment(experiment_id: str, request: ExperimentRequest, *, run_store,
                         workbench_store, eval_runner) -> None:
    variants = {variant.id: variant for variant in request.variants}
    consecutive_errors = 0
    try:
        while True:
            current = workbench_store.get_experiment(experiment_id)
            if current is None:
                return
            if request.max_cost is not None and current["total_cost"] is None:
                reason = "cost ceiling cannot be enforced because a provider did not report cost"
                workbench_store.skip_pending(experiment_id, reason)
                workbench_store.finish_experiment(experiment_id, status="stopped", error=reason)
                return
            if request.max_cost is not None and current["total_cost"] >= request.max_cost:
                reason = f"cost ceiling reached ({current['total_cost']:.4f} >= {request.max_cost:.4f})"
                workbench_store.skip_pending(experiment_id, reason)
                workbench_store.finish_experiment(experiment_id, status="stopped", error=reason)
                return

            cell = workbench_store.next_cell(experiment_id)
            if cell is None:
                workbench_store.finish_experiment(experiment_id, status="done")
                return
            variant = variants[cell["variant_id"]]
            run_request = variant.as_run_request()
            run_id = run_store.create(
                run_request, experiment_id=experiment_id, cell_id=cell["id"],
            )
            workbench_store.attach_run(cell["id"], run_id)
            await run_eval_job(
                run_id, run_request, run_store, eval_runner, workbench_store,
            )
            run = run_store.get(run_id)
            if run and run["status"] == "done":
                receipt = run.get("receipt") or {}
                usage = receipt.get("usage", {})
                cost = usage.get("billed_cost")
                workbench_store.finish_cell(cell["id"], status="done", cost=cost)
                consecutive_errors = 0
            else:
                error = (run or {}).get("error") or "evaluation did not complete"
                workbench_store.finish_cell(cell["id"], status="error", error=error)
                consecutive_errors += 1
                if consecutive_errors >= request.max_consecutive_errors:
                    reason = f"stopped after {consecutive_errors} consecutive evaluation errors"
                    workbench_store.skip_pending(experiment_id, reason)
                    workbench_store.finish_experiment(experiment_id, status="error", error=reason)
                    return
    except Exception as exc:  # noqa: BLE001 — orchestration must not strand the experiment at "running"
        workbench_store.finish_experiment(
            experiment_id, status="error",
            error=f"experiment orchestration failed: {type(exc).__name__}: {exc}",
        )

"""The eval-runner seam + the job driver.

The runner is injected (see `create_app`) so tests exercise the full job lifecycle
with a fake runner and never call a real model. The default runner drives a real
Tessera eval in a worker thread — `inspect_ai.eval()` owns its own asyncio runtime,
so it must NOT be awaited inside the server's event loop. Job state lives in a
durable RunStore (see run_store.py).
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import anyio

from tessera.api.schemas import RunRequest
from tessera.api.scrub import scrub_error
from tessera.api.receipts import canonical_sha256, file_sha256, receipt_from_log
from tessera.report.serialize import report_to_dict


def _eval_kwargs(req: RunRequest) -> dict:
    """The kwargs passed to inspect_ai.eval — pure, so the k/org/grader wiring is
    unit-testable without running a model. k rides task_args, NOT eval's epochs
    kwarg: an eval-level override changes the epoch count but keeps the task's
    pass_k reducer, so count and k would diverge — the task owns both."""
    kwargs = {
        "model": req.model,
        "task_args": {
            "judge": req.judge, "org": req.org, "k": req.epochs,
            "scaffold": req.scaffold, "seed": req.seed,
        },
        "log_dir": "logs",
        "display": "none",
    }
    if req.grader:
        kwargs["model_roles"] = {"grader": req.grader}
    return kwargs


def _job_env() -> dict[str, str]:
    """Per-job environment, resolved BEFORE inspect_ai takes over: inspect runs the task
    with the task file's directory as cwd, so anything cwd-relative must be absolutized
    here or the task won't find it (saved blueprints were unresolvable without this)."""
    env = {
        # Per-job org dir so a future concurrent run can't clobber the compiled fixtures.
        "TESSERA_OUT": os.path.join("/tmp/tessera", f"run-{uuid.uuid4().hex}"),
        "TESSERA_BLUEPRINT_DIR": str(
            Path(os.environ.get("TESSERA_BLUEPRINT_DIR", "blueprints")).resolve()
        ),
    }
    # inspect_ai's openai-compatible provider raises unless <SERVICE>_API_KEY is set, but
    # mlx_lm.server is a local process with no auth — there is no key for a user to supply,
    # so asking for one would be an unanswerable field. Supply a placeholder it ignores.
    env.setdefault("MLX_API_KEY", os.environ.get("MLX_API_KEY") or "local")
    return env


def default_eval_runner(req: RunRequest):
    """Run a real Tessera eval and return the EvalLog. Imported lazily so the module
    stays importable (and the API stays testable) without inspect_ai initializing.

    The environment is loaded once at application startup (app.py); this function
    reads the process environment and never loads a dotenv file of its own.
    """
    import inspect_ai
    from inspect_ai.log import read_eval_log

    os.environ.update(_job_env())

    logs = inspect_ai.eval("src/tessera/evals/task.py", **_eval_kwargs(req))
    # Re-read from disk with attachments resolved so transcripts/answers are complete.
    return read_eval_log(logs[0].location, resolve_attachments=True)


def _blueprint_sha256(req: RunRequest) -> str | None:
    try:
        from tessera.orgs import get_blueprint
        blueprint = get_blueprint(req.org, seed=req.seed)
        return canonical_sha256(blueprint.model_dump(mode="json", by_alias=True))
    except Exception:  # noqa: BLE001 — provenance absence must not fail a paid run
        return None


async def run_eval_job(job_id: str, req: RunRequest, store, eval_runner,
                       workbench_store=None) -> None:
    """Drive one job to completion. eval_runner runs in a worker thread (no running loop
    there), keeping inspect_ai's runtime clear of the server's event loop. `store` is any
    object with complete(job_id, report) / error(job_id, message)."""
    try:
        log = await anyio.to_thread.run_sync(eval_runner, req)
        report = report_to_dict(log)
        artifact_path = str(getattr(log, "location", "") or "")
        try:
            artifact_sha256 = file_sha256(artifact_path) if artifact_path and Path(artifact_path).is_file() else None
        except OSError:
            artifact_sha256 = None
        receipt = receipt_from_log(
            log, report, requested_model=req.model,
            blueprint_sha256=_blueprint_sha256(req), artifact_sha256=artifact_sha256,
        )
        store.complete(job_id, report, receipt)
        if workbench_store is not None:
            # This indexing step runs after the job is already durably "done" — a
            # failure here (e.g. a locked workbench db) must not flip a successful run
            # back to "error" and hide its report; sync_library() reconciles the index
            # from run_store on the next read regardless, so it's safe to just skip it.
            try:
                workbench_store.record_evaluation(
                    evaluation_id=f"run:{job_id}", kind="run", source="api",
                    source_ref=f"run:{job_id}", status="done", report=report, receipt=receipt,
                    artifact_path=artifact_path or None, artifact_sha256=artifact_sha256,
                )
            except Exception:  # noqa: BLE001 — the run already succeeded; indexing can retry later
                pass
    except ValueError as exc:            # self-grading guard, bad model id, ...
        store.error(job_id, scrub_error(str(exc)))
    except Exception as exc:             # noqa: BLE001 — surface any runtime failure to the UI
        store.error(job_id, scrub_error(f"{type(exc).__name__}: {exc}"))

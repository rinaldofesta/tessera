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
from tessera.report.serialize import report_to_dict


def _eval_kwargs(req: RunRequest) -> dict:
    """The kwargs passed to inspect_ai.eval — pure, so the k/org/grader wiring is
    unit-testable without running a model. k rides task_args, NOT eval's epochs
    kwarg: an eval-level override changes the epoch count but keeps the task's
    pass_k reducer, so count and k would diverge — the task owns both."""
    kwargs = {
        "model": req.model,
        "task_args": {"judge": req.judge, "org": req.org, "k": req.epochs},
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
    return {
        # Per-job org dir so a future concurrent run can't clobber the compiled fixtures.
        "TESSERA_OUT": os.path.join("/tmp/tessera", f"run-{uuid.uuid4().hex}"),
        "TESSERA_BLUEPRINT_DIR": str(
            Path(os.environ.get("TESSERA_BLUEPRINT_DIR", "blueprints")).resolve()
        ),
    }


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


async def run_eval_job(job_id: str, req: RunRequest, store, eval_runner) -> None:
    """Drive one job to completion. eval_runner runs in a worker thread (no running loop
    there), keeping inspect_ai's runtime clear of the server's event loop. `store` is any
    object with complete(job_id, report) / error(job_id, message)."""
    try:
        log = await anyio.to_thread.run_sync(eval_runner, req)
        store.complete(job_id, report_to_dict(log))
    except ValueError as exc:            # self-grading guard, bad model id, ...
        store.error(job_id, scrub_error(str(exc)))
    except Exception as exc:             # noqa: BLE001 — surface any runtime failure to the UI
        store.error(job_id, scrub_error(f"{type(exc).__name__}: {exc}"))

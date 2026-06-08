"""Live-run job registry and the eval-runner seam.

The runner is injected (see `create_app`) so tests exercise the full job lifecycle
with a fake runner and never call a real model. The default runner drives a real
Tessera eval in a worker thread — `inspect_ai.eval()` owns its own asyncio runtime,
so it must NOT be awaited inside the server's event loop.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

import anyio

from tessera.api.schemas import RunRequest
from tessera.report.serialize import report_to_dict


@dataclass
class Job:
    status: str = "running"          # "running" | "done" | "error"
    report: dict | None = None
    error: str | None = None


class JobRegistry:
    """In-memory job store. Single-process, lost on restart — fine for a local showcase."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self) -> str:
        job_id = uuid.uuid4().hex
        self._jobs[job_id] = Job()
        return job_id

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def complete(self, job_id: str, report: dict) -> None:
        self._jobs[job_id] = Job(status="done", report=report)

    def error(self, job_id: str, message: str) -> None:
        self._jobs[job_id] = Job(status="error", error=message)


def default_eval_runner(req: RunRequest):
    """Run a real Tessera eval and return the EvalLog. Imported lazily so the module
    stays importable (and the API stays testable) without inspect_ai initializing."""
    import inspect_ai
    from inspect_ai.log import read_eval_log

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Per-job org dir so a future concurrent run can't clobber the compiled fixtures.
    os.environ["TESSERA_OUT"] = os.path.join("/tmp/tessera", f"run-{uuid.uuid4().hex}")

    kwargs = {"model_roles": {"grader": req.grader}} if req.grader else {}
    logs = inspect_ai.eval(
        "src/tessera/evals/task.py",
        model=req.model,
        task_args={"judge": req.judge, "org": req.org},
        log_dir="logs",
        display="none",
        **kwargs,
    )
    log = logs[0]
    # Re-read from disk with attachments resolved so transcripts/answers are complete.
    return read_eval_log(log.location, resolve_attachments=True)


async def run_eval_job(job_id: str, req: RunRequest, registry: JobRegistry, eval_runner) -> None:
    """Drive one job to completion. eval_runner runs in a worker thread (no running loop
    there), keeping inspect_ai's runtime clear of the server's event loop."""
    try:
        log = await anyio.to_thread.run_sync(eval_runner, req)
        registry.complete(job_id, report_to_dict(log))
    except ValueError as exc:            # self-grading guard, bad model id, ...
        registry.error(job_id, str(exc))
    except Exception as exc:             # noqa: BLE001 — surface any runtime failure to the UI
        registry.error(job_id, f"{type(exc).__name__}: {exc}")

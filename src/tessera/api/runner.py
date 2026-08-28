"""The eval-runner seam + the job driver.

The runner is injected (see `create_app`) so tests exercise the full job lifecycle
with a fake runner and never call a real model. The default runner drives a real
Tessera eval in a worker thread — `inspect_ai.eval()` owns its own asyncio runtime,
so it must NOT be awaited inside the server's event loop. Job state lives in a
durable RunStore (see run_store.py).
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

import anyio

from tessera.api.schemas import RunRequest
from tessera.report.serialize import report_to_dict

# Greedy up to the LAST @ before the path: a password may itself contain an @, and
# stopping at the first one left the rest of it in the message.
_USERINFO_RE = re.compile(r"(?P<scheme>[a-zA-Z][\w+.-]*://)[^/\s]*@")
# Any auth scheme, not just Bearer/Basic — AWS SigV4 sends
# "Authorization: AWS4-HMAC-SHA256 Credential=…, Signature=…".
_AUTH_HEADER_RE = re.compile(r"(?i)(authorization:\s*)\S.*")
# Env vars whose NAME says the value is a secret. This is deliberately name-based: it
# needs no knowledge of each provider's token format, and it covers providers Tessera
# has never heard of — which matters because RunRequest.model is free text by design,
# so a run can target any inspect_ai provider, not only the eight in PROVIDERS.
_SECRET_ENV_NAME = re.compile(r"(?i)key|token|secret|password|credential")
_MIN_REDACTABLE = 8      # below this a "secret" is likely a flag, and would mangle prose


def scrub_error(message: str) -> str:
    """Make an already-formatted error message fit to store and return.

    Provider errors routinely embed the request URL, and a base URL may embed
    credentials — so this runs before anything reaches run_store.error(), the API, or
    the logs. tests/test_runner.py asserts the result against credential_scan.

    Takes the formatted string rather than the exception, deliberately: the two call
    sites format differently and both shapes are API-visible. Scrubbing is a filter,
    never a reformat — a message with nothing to redact comes back byte-for-byte.

    Three passes: URL userinfo, Authorization header text of any scheme, and the value
    of every environment variable whose NAME says it holds a secret.

    That last pass is name-based rather than provider-based on purpose. An earlier
    version only redacted the eight providers in PROVIDERS, which was wrong because
    RunRequest.model is deliberately free text — a run can target any inspect_ai
    provider, so a Bedrock or Azure credential would pass straight through into the
    run record. Matching on the variable name needs no knowledge of any provider's
    token format and covers providers this codebase has never heard of.

    It is still not a general credential detector: a secret that is neither in a URL,
    nor in an auth header, nor in this process's environment passes through. Closing
    that would mean re-implementing credential_scan's patterns as span matchers —
    credential_scan reports locations and kinds, not spans, so it is the right test
    oracle and the wrong redactor. The tests assert against it.
    """
    message = _USERINFO_RE.sub(r"\g<scheme>[redacted]@", message)
    message = _AUTH_HEADER_RE.sub(r"\1[redacted]", message)
    # Longest first: redacting a short secret that is a prefix of a longer one would
    # leave the longer one's tail behind.
    secrets = sorted(
        (v.strip() for k, v in os.environ.items()
         if _SECRET_ENV_NAME.search(k) and len(v.strip()) >= _MIN_REDACTABLE),
        key=len, reverse=True,
    )
    for value in secrets:
        if value in message:
            message = message.replace(value, "[redacted]")
    return message


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

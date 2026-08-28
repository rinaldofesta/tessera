"""Redaction for error text that gets stored and returned.

Lives in its own module so both the producer (runner.py) and the storage boundary
(run_store.py) can apply it. Storage scrubs too, deliberately: a future caller that
forgets to scrub would otherwise reopen the leak this exists to close — the same
argument that makes env_writer validate its own inputs.

Redaction is idempotent, so scrubbing twice is harmless.
"""

from __future__ import annotations

import os
import re

from tessera.api.providers import PROVIDERS

# The scheme run is bounded: an unbounded [\w+.-]* before "://" backtracks quadratically
# on a long run of word characters that never reaches "://", and a multi-megabyte
# exception message could stall error handling and strand a job as "running".
# Real schemes are short (http, https, bedrock, openai-api).
_USERINFO_RE = re.compile(r"(?P<scheme>[a-zA-Z][\w+.-]{0,15}://)[^/\s]*@")
# Any auth scheme, not just Bearer/Basic — AWS SigV4 sends
# "Authorization: AWS4-HMAC-SHA256 Credential=…, Signature=…".
#
# This takes the WHOLE rest of the line, which does discard diagnostic text that
# happened to follow the header ("… failed with status 401"). That over-redaction is
# deliberate. A narrower pattern would have to know where the credential ends, and it
# does not: a Bearer token is one whitespace-delimited word, but a SigV4 value contains
# spaces, slashes and commas, so any rule tight enough to preserve the tail leaks part
# of a SigV4 signature. Losing a status code beats leaking half a credential, and the
# exception type and surrounding context before the header survive.
_AUTH_HEADER_RE = re.compile(r"(?i)(authorization:\s*)\S.*")
# Env vars whose NAME says the value is a secret. Name-based on purpose: it needs no
# knowledge of any provider's token format, and it covers providers this codebase has
# never heard of — which matters because RunRequest.model is free text by design, so a
# run can target any inspect_ai provider.
_SECRET_ENV_NAME = re.compile(r"(?i)key|token|secret|password|credential")
_MIN_REDACTABLE = 8      # below this a "secret" is likely a flag, and would mangle prose


def _environ_snapshot() -> dict[str, str]:
    """A stable copy of the environment.

    os.environ is mutated from other threads — apply_updates() when a credential is
    saved, and _job_env() on every eval start — so iterating it live raises: RuntimeError
    if the dict resizes, KeyError if a name disappears between iteration and lookup. That
    exception would escape run_eval_job's except block, so the failure would never be
    recorded and the job would sit at "running" forever. Verified reproducible.
    """
    for _ in range(5):
        try:
            return dict(os.environ)
        except (RuntimeError, KeyError):
            continue
    # Vanishingly unlikely, but do not silently stop redacting: .get() never iterates,
    # so this cannot race, and it still covers every provider we know about.
    return {
        field.env_var: value
        for spec in PROVIDERS.values()
        for field in spec.fields
        if (value := os.environ.get(field.env_var))
    }


def _configured_secrets() -> list[str]:
    """Every secret-looking env value, longest first.

    Both the raw value and its stripped form are candidates: a quoted .env value can
    carry surrounding whitespace, and testing only the stripped length let an 8-character
    raw value through the floor.
    """
    candidates: set[str] = set()
    for name, value in _environ_snapshot().items():
        if not _SECRET_ENV_NAME.search(name):
            continue
        for form in (value, value.strip()):
            if len(form) >= _MIN_REDACTABLE:
                candidates.add(form)
    # Longest first: replacing a short secret that prefixes a longer one would leave the
    # longer one's tail behind.
    return sorted(candidates, key=len, reverse=True)


def scrub_error(message: str) -> str:
    """Make an already-formatted error message fit to store and return.

    Provider errors routinely embed the request URL, and a base URL may embed
    credentials — so this runs before anything reaches the database, the API, or the
    logs. The tests assert the result against tessera.credential_scan.

    Takes the formatted string rather than the exception, deliberately: the two runner
    call sites format differently and both shapes are API-visible. Scrubbing is a filter,
    never a reformat — a message with nothing to redact comes back byte-for-byte.

    Not a general credential detector: a secret that is neither in a URL, nor in an auth
    header, nor in this process's environment passes through. Closing that would mean
    re-implementing credential_scan's patterns as span matchers, and credential_scan
    reports locations and kinds, not spans — it is the right test oracle and the wrong
    redactor. Two configured secrets that partially overlap (neither a substring of the
    other) can also leave a fragment; that needs two overlapping real credentials, which
    is not a configuration that occurs.
    """
    message = _USERINFO_RE.sub(r"\g<scheme>[redacted]@", message)
    message = _AUTH_HEADER_RE.sub(r"\1[redacted]", message)
    for value in _configured_secrets():
        if value in message:
            message = message.replace(value, "[redacted]")
    return message

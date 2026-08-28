"""The credential write transaction.

Atomic rename alone is not enough: two concurrent writers each read the old file, each
write a complete new one, and the second silently discards the first's field. The whole
read -> modify -> write -> os.environ -> invalidate sequence is therefore one critical
section, and `apply_updates` is the only way to enter it.

Two known limitations, both acceptable for this app and both able to bite if it changes:

- The lock is process-local. The API runs as a single uvicorn process bound to
  127.0.0.1, so that is sufficient today. Running it with `--workers > 1` would let two
  processes lose each other's writes while both report success; that would need an
  OS-level file lock (fcntl.flock), not this one.
- An inline comment on a line being updated is replaced along with the line, since the
  whole assignment is rewritten. Comments on every other line survive untouched.
"""

from __future__ import annotations

import os
import re
import tempfile
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import urlparse

_LOCK = threading.Lock()

# Every character str.splitlines() treats as a line break, plus NUL. dotenv only breaks
# on \n, so the wider set is not about the reader — it is about our own rewrite. A value
# containing U+2028 used to store fine and then split into two assignments on the NEXT
# rewrite, because _merge parsed with splitlines(). _merge now uses split("\n"); these
# stay rejected as the second layer, since a stored control character has no legitimate
# use in a credential and only creates parser-disagreement risk.
_FORBIDDEN = (
    "\x00", "\r", "\n", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", " ", " ",
)


class EnvValueError(ValueError):
    """A submitted value is unfit to write. The message never contains the value."""


def validate_secret(value: str) -> str:
    """Reject anything that could open a second assignment in the file."""
    if not value or not value.strip():
        raise EnvValueError("value must not be empty")
    if any(ch in value for ch in _FORBIDDEN):
        raise EnvValueError("value must not contain NUL or any line separator")
    try:
        # A lone surrogate passes every check above and then explodes at write time,
        # so an "accepted" value could not actually round-trip.
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise EnvValueError("value must be encodable as UTF-8") from None
    return value


def validate_key(key: str) -> str:
    """Reject a variable name that could inject a line or is not a legal env name.

    Keys come from the provider registry today, not from user input, but this module
    owns the file-format invariant and enforcing it only for values leaves a key
    containing a newline able to write an extra assignment before os.environ rejects it.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key or ""):
        raise EnvValueError("variable name must match [A-Za-z_][A-Za-z0-9_]*")
    return key


def validate_base_url(value: str) -> str:
    validate_secret(value)
    try:
        parsed = urlparse(value)
    except ValueError:
        # urlparse itself raises on some malformed input (an unbalanced "[" reads as a
        # bad IPv6 host). Callers catch EnvValueError to build a 422, so a bare
        # ValueError would surface as a 500 for what is only a mistyped URL.
        raise EnvValueError("base_url is not a valid URL") from None
    if parsed.scheme not in ("http", "https"):
        raise EnvValueError("base_url must use http or https")
    if not parsed.hostname:
        raise EnvValueError("base_url must include a host")
    if parsed.username or parsed.password:
        raise EnvValueError("base_url must not embed credentials")
    return value


def _quote(value: str) -> str:
    """Double-quote with escapes. Read back with interpolate=False (see app startup)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _merge(existing: str, updates: Mapping[str, str]) -> str:
    """Upsert each key, leaving every other line byte-for-byte alone.

    Parsing uses split("\\n"), never splitlines(): splitlines() also breaks on U+2028,
    U+2029, U+0085 and several C0 controls that dotenv treats as ordinary characters,
    so a stored value containing one would be torn into two assignments here.
    """
    remaining = dict(updates)
    written: set[str] = set()
    lines: list[str] = []

    body = existing.split("\n")
    ends_with_newline = bool(body) and body[-1] == ""
    if ends_with_newline:
        body = body[:-1]

    for line in body:
        key = (line.split("=", 1)[0].strip()
               if ("=" in line and not line.lstrip().startswith("#")) else None)
        if key is not None and key in remaining:
            if key in written:
                # Drop a stale duplicate. dotenv resolves duplicates to the LAST
                # occurrence, so leaving one would make the file disagree with the
                # os.environ value we are about to publish.
                continue
            lines.append(f"{key}={_quote(remaining[key])}")
            written.add(key)
        else:
            lines.append(line)

    for key, value in remaining.items():
        if key not in written:
            lines.append(f"{key}={_quote(value)}")
    return "\n".join(lines) + "\n" if lines else ""


def _write_atomic(path: Path, text: str) -> None:
    # mkstemp already opens with O_EXCL at mode 0600, in the directory we name — and
    # same-directory matters: os.replace is only atomic within one filesystem.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def apply_updates(
    env_file: Path, updates: Mapping[str, str], *, invalidate: Callable[[], None],
) -> None:
    """Write every supplied variable in one rewrite, then publish the change.

    `os.environ` and the cache are touched only after the rename returns, so a failure
    anywhere earlier leaves both the file and the process on the old values.

    Values are re-validated here even though callers validate too: this is the function
    that writes secrets to disk, so it enforces the file-format invariant itself rather
    than trusting every present and future caller to have done it. Field-semantic rules
    (a base_url's scheme, its userinfo) stay with the caller, which knows what each
    field means. Validation runs before the lock so a rejected write touches nothing.
    """
    if not updates:
        return
    for key, value in updates.items():
        validate_key(key)
        validate_secret(value)
    with _LOCK:
        existing = env_file.read_text() if env_file.exists() else ""
        _write_atomic(env_file, _merge(existing, updates))
        os.environ.update(updates)
        invalidate()

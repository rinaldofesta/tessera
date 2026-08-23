"""High-confidence credential detection for artifacts intended for publication."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CredentialFinding:
    """A credential kind and location, deliberately excluding the matched value."""

    path: str
    kind: str


_VALUE_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("aws-access-key-id", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("github-token", re.compile(
        r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,255}|"
        r"github_pat_[A-Za-z0-9_]{20,255})(?![A-Za-z0-9_])"
    )),
    ("jwt", re.compile(
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\."
        r"[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}(?![A-Za-z0-9_-])"
    )),
    ("provider-api-key", re.compile(
        r"(?<![A-Za-z0-9_-])sk-(?:ant-api\d{2}-|proj-)?"
        r"[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"
    )),
    ("google-api-key", re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])")),
    ("slack-token", re.compile(
        r"(?<![A-Za-z0-9_-])xox[baprs]-[A-Za-z0-9-]{10,}(?![A-Za-z0-9_-])"
    )),
    ("bearer-token", re.compile(
        r"\bbearer[ \t]+[A-Za-z0-9._~+/-]{20,}={0,2}(?![A-Za-z0-9._~+/-])",
        re.IGNORECASE,
    )),
    ("basic-auth", re.compile(
        r"\bauthorization[ \t]*:[ \t]*basic[ \t]+"
        r"[A-Za-z0-9+/]{8,}={0,2}(?![A-Za-z0-9+/=])",
        re.IGNORECASE,
    )),
    ("cookie-header", re.compile(
        r"\b(?:set-cookie|cookie)[ \t]*:[ \t]*[^\s=;]+=[^;\r\n]{3,}",
        re.IGNORECASE,
    )),
    ("secret-assignment", re.compile(
        r"\b(?:api[_-]?key|client[_-]?secret|session[_-]?token|access[_-]?token|"
        r"refresh[_-]?token|aws_secret_access_key)\b\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9._~+/=-]{16,}",
        re.IGNORECASE,
    )),
)

_SENSITIVE_FIELDS = {
    "apikey", "xapikey", "clientsecret", "sessiontoken", "accesstoken",
    "refreshtoken", "awssecretaccesskey", "authorization", "cookie", "setcookie",
    "password", "privatekey",
}
_SAFE_VALUES = {
    "", "none", "null", "redacted", "<redacted>", "[redacted]", "not set", "unset",
    "placeholder",
}
_SECRET_VALUE_RE = re.compile(r"[A-Za-z0-9._~+/=:-]{16,}")


def _field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _secret_shaped(value: str) -> bool:
    candidate = value.strip().strip("\"'")
    if candidate.lower() in _SAFE_VALUES or candidate.startswith(("http://", "https://")):
        return False
    return bool(_SECRET_VALUE_RE.fullmatch(candidate))


def _sensitive_field_value(field: str, value: str) -> bool:
    name = _field_name(field)
    if name not in _SENSITIVE_FIELDS:
        return False
    candidate = value.strip().strip("\"'")
    if candidate.lower() in _SAFE_VALUES:
        return False
    if name == "authorization":
        return (
            bool(re.fullmatch(r"(?:basic|bearer)[ \t]+\S{8,}", candidate, re.IGNORECASE))
            or _secret_shaped(candidate)
        )
    if name in {"cookie", "setcookie"}:
        return bool(re.search(r"(?:^|;[ \t]*)[^\s=;]+=[^;]+", candidate))
    return _secret_shaped(candidate)


def find_credential_like_values(value: Any) -> list[CredentialFinding]:
    """Return high-confidence credential locations without returning secret material."""
    findings: list[CredentialFinding] = []

    def add(path: str, kind: str) -> None:
        finding = CredentialFinding(path=path, kind=kind)
        if finding not in findings:
            findings.append(finding)

    def walk(current: Any, path: str = "$") -> None:
        if isinstance(current, dict):
            for key, nested in current.items():
                child_path = f"{path}.{key}"
                if (isinstance(key, str) and isinstance(nested, str)
                        and _sensitive_field_value(key, nested)):
                    add(child_path, "sensitive-field")
                walk(nested, child_path)
        elif isinstance(current, list):
            for index, nested in enumerate(current):
                walk(nested, f"{path}[{index}]")
        elif isinstance(current, str):
            for kind, pattern in _VALUE_PATTERNS:
                if pattern.search(current):
                    add(path, kind)

    walk(value)
    return findings

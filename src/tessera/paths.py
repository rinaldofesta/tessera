"""Paths for Tessera's user-owned state."""

import os
from pathlib import Path


def home() -> Path:
    configured = os.environ.get("TESSERA_HOME")
    path = Path(configured) if configured else Path.home() / ".tessera"
    return path.expanduser().resolve()


def env_file() -> Path:
    configured = os.environ.get("TESSERA_ENV_FILE")
    return Path(configured) if configured else home() / ".env"


def suites_dir() -> Path:
    return home() / "suites"


def runs_dir() -> Path:
    return home() / "runs"


def ensure_home() -> Path:
    path = home()
    was_missing = not path.exists()
    path.mkdir(parents=True, exist_ok=True)
    if was_missing:
        path.chmod(0o700)
    suites_dir().mkdir(parents=True, exist_ok=True)
    runs_dir().mkdir(parents=True, exist_ok=True)
    return path

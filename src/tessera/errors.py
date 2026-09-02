"""Application errors with stable CLI exit codes: exit 1 is reserved for gates the
user explicitly requested, while a completed run whose verdict is "not reliable" exits 0.
"""

from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    GATE_FAILED = 1
    NOT_CONNECTED = 2
    SPEC_ERROR = 3
    RUNTIME_ERROR = 4


class TesseraError(Exception):
    """Base application error whose message is user-facing prose without a traceback.
    Raised directly, it is a runtime failure; the subclasses name the other exit codes."""

    exit_code = ExitCode.RUNTIME_ERROR


class SpecError(TesseraError):
    exit_code = ExitCode.SPEC_ERROR


class NotConnectedError(TesseraError):
    exit_code = ExitCode.NOT_CONNECTED


class GateFailed(TesseraError):
    exit_code = ExitCode.GATE_FAILED

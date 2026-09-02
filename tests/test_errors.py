import pytest

from tessera.errors import (
    ExitCode,
    GateFailed,
    NotConnectedError,
    SpecError,
    TesseraError,
)


def test_exit_code_values_are_stable():
    assert ExitCode.OK == 0
    assert ExitCode.GATE_FAILED == 1
    assert ExitCode.NOT_CONNECTED == 2
    assert ExitCode.SPEC_ERROR == 3
    assert ExitCode.RUNTIME_ERROR == 4


@pytest.mark.parametrize(("error", "code"), [
    (GateFailed, ExitCode.GATE_FAILED),
    (NotConnectedError, ExitCode.NOT_CONNECTED),
    (SpecError, ExitCode.SPEC_ERROR),
    (TesseraError, ExitCode.RUNTIME_ERROR),
])
def test_error_subclasses_carry_their_exit_code(error, code):
    assert error("message").exit_code is code

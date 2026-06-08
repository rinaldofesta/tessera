"""The eval-runner kwargs seam — guards the epochs/org/grader wiring without a model."""

from tessera.api.runner import _eval_kwargs
from tessera.api.schemas import RunRequest


def test_eval_kwargs_forwards_epochs_org_and_grader():
    kw = _eval_kwargs(RunRequest(model="m", grader="g", judge="llm", org="acme", epochs=5))
    assert kw["epochs"] == 5                          # regression: epochs was dropped before
    assert kw["task_args"] == {"judge": "llm", "org": "acme"}
    assert kw["model_roles"] == {"grader": "g"}
    assert kw["display"] == "none"


def test_eval_kwargs_omits_grader_when_absent():
    kw = _eval_kwargs(RunRequest(model="m", judge="deterministic", org="toy"))
    assert "model_roles" not in kw
    assert kw["epochs"] == 3 and kw["task_args"]["judge"] == "deterministic"

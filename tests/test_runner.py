"""The eval-runner kwargs seam — guards the epochs/org/grader wiring without a model."""

from tessera.api.runner import _eval_kwargs
from tessera.api.schemas import RunRequest


def test_eval_kwargs_passes_k_to_the_task_not_to_eval():
    kw = _eval_kwargs(RunRequest(model="m", grader="g", judge="llm", org="acme", epochs=5))
    assert kw["task_args"] == {"judge": "llm", "org": "acme", "k": 5}
    # regression: an eval-level epochs kwarg overrides the COUNT but keeps the
    # task's pass_k(3) reducer — k<3 hard-errored, k>3 mislabeled. The task owns
    # count and reducer together, so eval must not pass epochs at all.
    assert "epochs" not in kw
    assert kw["model_roles"] == {"grader": "g"}
    assert kw["display"] == "none"


def test_eval_kwargs_omits_grader_when_absent():
    kw = _eval_kwargs(RunRequest(model="m", judge="deterministic", org="toy"))
    assert "model_roles" not in kw
    assert kw["task_args"]["k"] == 3 and kw["task_args"]["judge"] == "deterministic"


def test_job_env_pins_blueprint_store_to_an_absolute_path(tmp_path, monkeypatch):
    # regression: inspect_ai runs the task with the task file's directory as cwd,
    # so a cwd-relative blueprint store made every saved-blueprint run fail with
    # "unknown org" — the author->run loop only worked for built-in orgs.
    from tessera.api.runner import _job_env

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TESSERA_BLUEPRINT_DIR", raising=False)
    env = _job_env()
    assert env["TESSERA_BLUEPRINT_DIR"] == str(tmp_path / "blueprints")
    assert env["TESSERA_OUT"].startswith("/tmp/tessera/run-")


def test_job_env_respects_an_explicit_blueprint_dir(tmp_path, monkeypatch):
    from tessera.api.runner import _job_env

    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path / "store"))
    assert _job_env()["TESSERA_BLUEPRINT_DIR"] == str(tmp_path / "store")

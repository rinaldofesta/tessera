"""Key-free tests for the FastAPI app. Logs are fabricated on disk with write_eval_log;
the live-run path uses an injected fake runner + inline scheduler — no model calls."""

from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app


def _eval_log(samples, *, judge="llm", epochs=3, grader="openai/gpt-4o",
              model="anthropic/claude-sonnet-4-6", location="./logs/run.eval"):
    from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSpec
    from inspect_ai.model import ModelConfig
    roles = {"grader": ModelConfig(model=grader)} if grader else {}
    spec = EvalSpec(created="2026-06-03T10:00:00+00:00", task="tessera_probes",
                    dataset=EvalDataset(), model=model, config=EvalConfig(epochs=epochs),
                    task_args={"judge": judge}, model_roles=roles)
    return EvalLog(eval=spec, samples=samples, location=location)


def _answer(probe_id, epoch, conflict_type="none", passed=True):
    from inspect_ai.log import EvalSample
    from inspect_ai.scorer import Score
    return EvalSample(
        id=probe_id, epoch=epoch, input="Q?", target="",
        metadata={"conflict_type": conflict_type, "expected_behavior": "answer",
                  "expected_answer": None, "expected_sources": ["crm"]},
        scores={"llm_reliability_scorer": Score(value="C" if passed else "I", answer="4 hours",
                metadata={"passed": passed, "accuracy_ok": passed, "provenance_ok": True,
                          "refusal_ok": True, "consulted": ["crm"]})})


async def _inline_schedule(coro):
    """Test scheduler: run the job to completion before the request returns."""
    await coro


def _write(dir_path: Path, name: str, log) -> None:
    from inspect_ai.log import write_eval_log
    dir_path.mkdir(parents=True, exist_ok=True)
    write_eval_log(log, str(dir_path / name))


def _client(tmp_path, *, eval_runner=None):
    examples = tmp_path / "examples"
    logs = tmp_path / "logs"
    _write(examples, "first-contact.eval", _eval_log([_answer("q1", 1)]))
    app = create_app(
        eval_runner=eval_runner or (lambda req: _eval_log([_answer("q1", 1)])),
        log_dirs={"examples": examples, "logs": logs},
        schedule=_inline_schedule,
    )
    return TestClient(app)


def test_list_logs_returns_pinned_example(tmp_path):
    r = _client(tmp_path).get("/api/logs")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert "examples:first-contact" in ids
    meta = next(x for x in r.json() if x["id"] == "examples:first-contact")
    assert meta["model"] == "anthropic/claude-sonnet-4-6" and meta["engine"] == "llm"
    assert meta["grader"] == "openai/gpt-4o" and meta["k"] == 3


def test_get_report_by_id(tmp_path):
    r = _client(tmp_path).get("/api/logs/examples:first-contact/report")
    assert r.status_code == 200
    body = r.json()
    assert body["header"]["model"] == "anthropic/claude-sonnet-4-6"
    assert body["overall"]["pass_k_rate"] == 1.0
    assert body["probes"][0]["probe_id"] == "q1"


def test_get_report_unknown_id_404(tmp_path):
    assert _client(tmp_path).get("/api/logs/examples:nope/report").status_code == 404


def test_get_report_rejects_path_traversal(tmp_path):
    assert _client(tmp_path).get("/api/logs/examples:..%2f..%2fsecret/report").status_code == 404


def test_upload_report(tmp_path):
    log_path = tmp_path / "uploaded.eval"
    from inspect_ai.log import write_eval_log
    write_eval_log(_eval_log([_answer("q1", 1)]), str(log_path))
    with open(log_path, "rb") as fh:
        r = _client(tmp_path).post("/api/reports", files={"file": ("u.eval", fh, "application/octet-stream")})
    assert r.status_code == 200 and r.json()["overall"]["pass_k_rate"] == 1.0


def test_upload_foreign_log_400(tmp_path):
    from inspect_ai.log import EvalSample, write_eval_log
    from inspect_ai.scorer import Score
    foreign = EvalSample(id="x", epoch=1, input="q", target="",
                         metadata={}, scores={"other": Score(value="C", metadata={"foo": 1})})
    log_path = tmp_path / "foreign.eval"
    write_eval_log(_eval_log([foreign]), str(log_path))
    with open(log_path, "rb") as fh:
        r = _client(tmp_path).post("/api/reports", files={"file": ("f.eval", fh, "application/octet-stream")})
    assert r.status_code == 400


def test_run_completes_with_fake_runner(tmp_path):
    client = _client(tmp_path, eval_runner=lambda req: _eval_log([_answer("q1", 1)]))
    r = client.post("/api/runs", json={"model": "anthropic/claude-sonnet-4-6",
                                       "grader": "openai/gpt-4o", "judge": "llm"})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    poll = client.get(f"/api/runs/{job_id}").json()
    assert poll["status"] == "done"
    assert poll["report"]["overall"]["pass_k_rate"] == 1.0


def test_run_self_grading_guard_400(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "openai/gpt-4o",
                                                  "grader": "openai/gpt-4o", "judge": "llm"})
    assert r.status_code == 400 and "self-grading" in r.json()["detail"]


def test_run_llm_without_grader_400(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "openai/gpt-4o", "judge": "llm"})
    assert r.status_code == 400


def test_run_surfaces_runner_valueerror_as_error_status(tmp_path):
    def _bad(req):
        raise ValueError("grader must differ from the model under test")
    client = _client(tmp_path, eval_runner=_bad)
    r = client.post("/api/runs", json={"model": "anthropic/claude-sonnet-4-6",
                                       "grader": "openai/gpt-4o", "judge": "llm"})
    job_id = r.json()["job_id"]
    poll = client.get(f"/api/runs/{job_id}").json()
    assert poll["status"] == "error" and "differ" in poll["error"]


def test_unknown_job_404(tmp_path):
    assert _client(tmp_path).get("/api/runs/deadbeef").status_code == 404

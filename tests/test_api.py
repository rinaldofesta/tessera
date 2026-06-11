"""Key-free tests for the FastAPI app. Logs are fabricated on disk with write_eval_log;
the live-run path uses an injected fake runner + inline scheduler — no model calls."""

from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore


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
        blueprint_dir=tmp_path / "blueprints",
        run_store=RunStore(tmp_path / "runs.db"),
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


def test_list_orgs(tmp_path):
    r = _client(tmp_path).get("/api/orgs")
    assert r.status_code == 200 and "toy" in r.json()


def test_list_models(tmp_path):
    r = _client(tmp_path).get("/api/models")
    assert r.status_code == 200
    models = r.json()
    assert "anthropic/claude-sonnet-4-6" in models and len(models) >= 2


def test_every_api_route_declares_a_response_model(tmp_path):
    # The OpenAPI schema is the single contract the SPA types are generated from:
    # a route without a response_model publishes `unknown` and silently re-opens
    # the hand-maintained-types drift this guard exists to close.
    from fastapi.routing import APIRoute

    from tessera.api.app import create_app
    from tessera.api.run_store import RunStore

    app = create_app(run_store=RunStore(tmp_path / "runs.db"),
                     blueprint_dir=tmp_path / "bp")
    exempt = {"/api/runs/{job_id}/events"}        # SSE stream, not JSON
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api/") and route.path not in exempt:
            assert route.response_model is not None, f"{route.path} has no response_model"


def test_run_rejects_unknown_judge(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "m", "judge": "vibes"})
    assert r.status_code == 422   # judge is a closed enum: 'llm' | 'deterministic'


def test_run_passes_org_through(tmp_path):
    captured = {}

    def _runner(req):
        captured["org"] = req.org
        return _eval_log([_answer("q1", 1)])

    client = _client(tmp_path, eval_runner=_runner)
    r = client.post("/api/runs", json={"model": "anthropic/claude-sonnet-4-6",
                                       "grader": "openai/gpt-4o", "judge": "llm", "org": "your"})
    assert r.status_code == 200
    assert captured["org"] == "your"


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


def test_run_rejects_out_of_range_epochs(tmp_path):
    # epochs=0 used to sail straight into inspect_ai and die there; bounds match the UI (1..10)
    client = _client(tmp_path)
    base = {"model": "openai/gpt-4o", "judge": "deterministic"}
    assert client.post("/api/runs", json={**base, "epochs": 0}).status_code == 422
    assert client.post("/api/runs", json={**base, "epochs": 11}).status_code == 422


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


def test_runs_history_and_trends_after_a_run(tmp_path):
    client = _client(tmp_path, eval_runner=lambda req: _eval_log([_answer("q1", 1)]))
    client.post("/api/runs", json={"model": "anthropic/claude-sonnet-4-6",
                                   "grader": "openai/gpt-4o", "judge": "llm", "org": "toy"})
    hist = client.get("/api/runs").json()
    assert len(hist) == 1 and hist[0]["status"] == "done" and hist[0]["pass_k_rate"] == 1.0
    assert hist[0]["org"] == "toy" and hist[0]["model"] == "anthropic/claude-sonnet-4-6"
    trends = client.get("/api/trends").json()
    assert len(trends) == 1 and trends[0]["pass_k_rate"] == 1.0 and "none" in trends[0]["categories"]
    # filter that excludes it -> empty
    assert client.get("/api/trends", params={"org": "nope"}).json() == []


def test_run_persists_across_restart_same_db(tmp_path):
    from tessera.api.schemas import RunRequest
    db = tmp_path / "runs.db"
    store = RunStore(db)
    jid = store.create(RunRequest(model="m", judge="deterministic", org="toy"))
    # a complete report shape — the response contract (RunStatus.report) rejects partials
    store.complete(jid, {
        "header": {"model": "m", "engine": "deterministic", "grader": None, "org": "toy",
                   "k": 1, "created": "2026-06-03", "location": "x.eval"},
        "overall": {"pass_k_rate": 1.0, "mean_rate": 1.0},
        "categories": [],
        "axes": {"accuracy_rate": None, "provenance_rate": 1.0, "refusal_rate": None,
                 "n_answer_epochs": 0, "n_refuse_epochs": 0, "n_total_epochs": 1},
        "probes": [],
    })
    # a brand-new app on the SAME db file still sees the finished run (durable)
    fresh = create_app(run_store=RunStore(db), blueprint_dir=tmp_path / "bp2",
                       log_dirs={}, schedule=_inline_schedule)
    got = TestClient(fresh).get(f"/api/runs/{jid}").json()
    assert got["status"] == "done" and got["report"]["overall"]["pass_k_rate"] == 1.0


def test_run_events_sse_terminal(tmp_path):
    client = _client(tmp_path, eval_runner=lambda req: _eval_log([_answer("q1", 1)]))
    jid = client.post("/api/runs", json={"model": "anthropic/claude-sonnet-4-6",
                                         "grader": "openai/gpt-4o", "judge": "llm", "org": "toy"}).json()["job_id"]
    r = client.get(f"/api/runs/{jid}/events")
    assert r.status_code == 200 and "text/event-stream" in r.headers["content-type"]
    assert "data:" in r.text and "done" in r.text


# ----- Datasets (blueprints) -----

def test_blueprints_list_seeded_and_get(tmp_path):
    c = _client(tmp_path)
    rows = c.get("/api/blueprints").json()
    assert "toy" in {r["id"] for r in rows}
    bp = c.get("/api/blueprints/toy").json()
    assert bp["claims"] and bp["probes"]
    assert "as" in bp["claims"][0]["render"]        # alias round-trips


def test_blueprint_validate_ok_and_errors(tmp_path):
    c = _client(tmp_path)
    bp = c.get("/api/blueprints/toy").json()
    assert c.post("/api/blueprints/validate", json=bp).json()["ok"] is True
    bad = {"claims": [], "probes": [{"probe_id": "p", "question": "q?",
           "conflict_type": "resolvable", "expected_behavior": "answer"}]}  # missing rule + answer
    res = c.post("/api/blueprints/validate", json=bad).json()
    assert res["ok"] is False and res["errors"]


def test_blueprint_preview_returns_artifacts(tmp_path):
    c = _client(tmp_path)
    bp = c.get("/api/blueprints/toy").json()
    art = c.post("/api/blueprints/preview", json=bp).json()
    assert set(art) == {"manifest", "silos", "docs"} and art["manifest"]


def test_blueprint_create_conflict_update_delete(tmp_path):
    c = _client(tmp_path)
    bp = c.get("/api/blueprints/toy").json()
    assert c.post("/api/blueprints", json={"id": "mine", "blueprint": bp}).status_code == 201
    assert c.post("/api/blueprints", json={"id": "mine", "blueprint": bp}).status_code == 409
    assert c.put("/api/blueprints/mine", json=bp).status_code == 200
    assert c.delete("/api/blueprints/mine").status_code == 200
    assert c.delete("/api/blueprints/mine").status_code == 404


def test_orgs_includes_saved_blueprint(tmp_path):
    c = _client(tmp_path)
    bp = c.get("/api/blueprints/toy").json()
    c.post("/api/blueprints", json={"id": "mine", "blueprint": bp})
    orgs = c.get("/api/orgs").json()
    assert "mine" in orgs and "toy" in orgs          # authored dataset is now runnable


def test_blueprint_create_invalid_400(tmp_path):
    c = _client(tmp_path)
    bad = {"claims": [], "probes": [{"probe_id": "p", "question": "q?",
           "conflict_type": "void", "expected_behavior": "answer"}]}  # void must refuse
    r = c.post("/api/blueprints", json={"id": "bad", "blueprint": bad})
    assert r.status_code == 400

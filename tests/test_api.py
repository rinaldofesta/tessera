"""Key-free FastAPI tests with an injected runner and inline scheduler."""

import json
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


def _folder_eval(**kwargs):
    location = str(Path(kwargs["log_dir"]) / "inspect-output.eval")
    task_args = kwargs["task_args"]
    roles = kwargs.get("model_roles") or {}
    log = _eval_log(
        [_answer("q1", 1)],
        judge=task_args["judge"],
        epochs=task_args["k"],
        grader=roles.get("grader"),
        model=kwargs["model"],
        location=location,
    )
    log.eval.task_args.update(task_args)
    from inspect_ai.log import write_eval_log
    write_eval_log(log, location)
    return log


def _client(tmp_path, *, folder_eval_runner=None):
    app = create_app(
        home=tmp_path / "home",
        folder_eval_runner=folder_eval_runner or _folder_eval,
        schedule=_inline_schedule,
        blueprint_dir=tmp_path / "blueprints",
        env_file=tmp_path / ".env",
    )
    return TestClient(app)


def test_app_reconciles_interrupted_folder_runs_at_startup(tmp_path, caplog):
    from tessera.store import RunStore as FolderRunStore

    home = tmp_path / "home"
    store = FolderRunStore(home, examples=tmp_path / "examples")
    record = store.create({
        "suite": "starter", "model": "ollama/test", "engine": "deterministic",
        "grader": None, "k": 1, "scaffold": "baseline", "seed": 0,
    })
    state_path = Path(record.dir) / "run.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update({"status": "running", "owner": None})
    state_path.write_text(json.dumps(state), encoding="utf-8")
    app = create_app(
        home=home,
        blueprint_dir=tmp_path / "blueprints", env_file=tmp_path / ".env",
    )

    with caplog.at_level("INFO"), TestClient(app):
        pass

    assert app.state.runs.get(record.id).data["status"] == "interrupted"
    assert record.id in caplog.text


def test_default_published_models_match_single_model_leaderboard(monkeypatch):
    from tessera.catalog import published_models

    monkeypatch.delenv("TESSERA_MODELS", raising=False)
    rows_path = Path(__file__).parents[1] / "docs" / "leaderboard.rows.json"
    rows = json.loads(rows_path.read_text())["rows"]
    expected = {
        row["model"] for row in rows
        if row.get("harness", "single") == "single"
    }
    assert set(published_models()) == expected


def test_every_api_route_declares_a_response_model(tmp_path):
    # The OpenAPI schema is the single contract the SPA types are generated from:
    # a route without a response_model publishes `unknown` and silently re-opens
    # the hand-maintained-types drift this guard exists to close.
    from fastapi.routing import APIRoute

    from tessera.api.app import create_app
    def api_routes(node):
        # Walk recursively via original_router: newer FastAPI keeps included routers as
        # lazy _IncludedRouter entries instead of flattening their routes into
        # app.routes, so iterating app.routes directly finds ZERO /api/ routes and this
        # guard silently passes while checking nothing.
        for route in getattr(node, "routes", []):
            if isinstance(route, APIRoute):
                yield route
            elif (inner := getattr(route, "original_router", None)) is not None:
                yield from api_routes(inner)

    app = create_app(home=tmp_path / "home", blueprint_dir=tmp_path / "bp")
    exempt = {"/api/runs/{run_id}/events"}        # SSE stream, not JSON
    checked = [r for r in api_routes(app) if r.path.startswith("/api/") and r.path not in exempt]
    assert checked, "found no /api/ routes to check — the guard is inert, not passing"
    for route in checked:
        assert route.response_model is not None, f"{route.path} has no response_model"


def test_run_rejects_unknown_judge(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "ollama/test", "engine": "vibes"})
    assert r.status_code == 422   # engine is a closed enum: 'llm' | 'deterministic'


def test_run_passes_resolved_suite_org_through(tmp_path):
    captured = {}

    def _runner(**kwargs):
        captured["org"] = kwargs["task_args"]["org"]
        return _folder_eval(**kwargs)

    client = _client(tmp_path, folder_eval_runner=_runner)
    r = client.post("/api/runs", json={"model": "ollama/test", "suite": "starter"})
    assert r.status_code == 200
    assert captured["org"] == "toy"


def test_run_completes_with_fake_runner(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/runs", json={"model": "ollama/test"})
    assert r.status_code == 200
    assert r.json()["status"] == "queued"
    run_id = r.json()["id"]
    poll = client.get(f"/api/runs/{run_id}").json()
    assert poll["status"] == "completed"
    assert poll["report"]["overall"]["pass_k_rate"] == 1.0


def test_run_self_grading_is_a_machine_readable_blocker(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={
        "model": "ollama/test", "grader": "ollama/test", "engine": "llm",
    })
    assert r.status_code == 422
    assert {blocker["code"] for blocker in r.json()["detail"]} == {"self_grading"}


def test_run_llm_without_grader_422(tmp_path):
    r = _client(tmp_path).post("/api/runs", json={"model": "ollama/test", "engine": "llm"})
    assert r.status_code == 422 and r.json()["detail"][0]["code"] == "grader_required"


def test_run_missing_key_and_unknown_suite_are_blockers(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    missing_key = _client(tmp_path).post("/api/runs", json={"model": "openai/gpt-4o"})
    unknown_suite = _client(tmp_path).post("/api/runs", json={
        "model": "ollama/test", "suite": "unknown",
    })
    assert missing_key.status_code == 422
    assert missing_key.json()["detail"][0]["code"] == "not_connected"
    assert unknown_suite.status_code == 422
    assert unknown_suite.json()["detail"][0]["code"] == "unknown_suite"


def test_run_rejects_out_of_range_k(tmp_path):
    client = _client(tmp_path)
    base = {"model": "ollama/test", "engine": "deterministic"}
    assert client.post("/api/runs", json={**base, "k": 0}).status_code == 422
    assert client.post("/api/runs", json={**base, "k": 11}).status_code == 422


def test_run_surfaces_runner_valueerror_as_error_status(tmp_path):
    def _bad(**_kwargs):
        raise ValueError("grader must differ from the model under test")
    client = _client(tmp_path, folder_eval_runner=_bad)
    r = client.post("/api/runs", json={"model": "ollama/test"})
    poll = client.get(f"/api/runs/{r.json()['id']}").json()
    assert poll["status"] == "failed" and "differ" in poll["error"]


def test_unknown_job_404(tmp_path):
    assert _client(tmp_path).get("/api/runs/deadbeef").status_code == 404


def test_runs_history_after_a_run(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/runs", json={"model": "ollama/test"}).json()
    hist = client.get("/api/runs").json()
    run = next(row for row in hist if row["id"] == created["id"])
    assert run["status"] == "completed" and run["verdict"]["pass_k_rate"] == 1.0
    assert run["request"]["suite"] == "starter" and run["request"]["model"] == "ollama/test"
    assert all(row["report"] is None and row["receipt"] is None for row in hist)


def test_run_persists_across_restart_same_home(tmp_path):
    run_id = _client(tmp_path).post("/api/runs", json={"model": "ollama/test"}).json()["id"]
    fresh = create_app(
        home=tmp_path / "home", blueprint_dir=tmp_path / "bp2", schedule=_inline_schedule,
    )
    got = TestClient(fresh).get(f"/api/runs/{run_id}").json()
    assert got["status"] == "completed" and got["report"]["overall"]["pass_k_rate"] == 1.0


def test_run_events_sse_terminal(tmp_path):
    client = _client(tmp_path)
    run_id = client.post("/api/runs", json={"model": "ollama/test"}).json()["id"]
    r = client.get(f"/api/runs/{run_id}/events")
    assert r.status_code == 200 and "text/event-stream" in r.headers["content-type"]
    assert "data:" in r.text and "completed" in r.text


def test_run_archive_round_trip_and_bundled_conflict(tmp_path):
    client = _client(tmp_path)
    run_id = client.post("/api/runs", json={"model": "ollama/test"}).json()["id"]
    archived = client.post(f"/api/runs/{run_id}/archive")
    assert archived.status_code == 200 and archived.json()["archived"] is True
    assert run_id not in {row["id"] for row in client.get("/api/runs").json()}
    included = client.get("/api/runs?include_archived=true").json()
    assert run_id in {row["id"] for row in included}
    restored = client.post(f"/api/runs/{run_id}/archive", json={"archived": False})
    assert restored.json()["archived"] is False
    assert client.post("/api/runs/first-contact/archive").status_code == 409


def test_run_import_returns_completed_payload(tmp_path):
    client = _client(tmp_path)
    source = Path("src/tessera/data/examples/first-contact/log.eval")
    with source.open("rb") as handle:
        response = client.post(
            "/api/runs/import",
            files={"file": ("first-contact.eval", handle, "application/octet-stream")},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["verdict"]["pass_k_rate"] == 0.75


def test_run_import_rejects_an_unreadable_log(tmp_path):
    response = _client(tmp_path).post(
        "/api/runs/import",
        files={"file": ("broken.eval", b"not an inspect log", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["detail"].startswith("cannot read log:")


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


def test_blueprint_with_bad_prose_template_is_a_400_not_500(tmp_path):
    # a malformed template ({nope}) must surface as a structured authoring error, not an
    # uncaught 500 from the compiler's str.format
    c = _client(tmp_path)
    bad = {"claims": [{"claim_id": "acme.x.docs", "subject": "Acme", "predicate": "x",
                       "value": "v", "silo": "docs",
                       "render": {"as": "prose", "template": "value is {nope}"}}],
           "probes": []}
    res = c.post("/api/blueprints/validate", json=bad)
    assert res.status_code == 200          # /validate always 200, reports errors in body
    assert res.json()["ok"] is False and res.json()["errors"]
    # the write paths reject it with a 400 (never a 500)
    created = c.post("/api/blueprints", json={"id": "bad", "blueprint": bad})
    assert created.status_code == 400


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


def test_blueprint_create_invalid_400(tmp_path):
    c = _client(tmp_path)
    bad = {"claims": [], "probes": [{"probe_id": "p", "question": "q?",
           "conflict_type": "void", "expected_behavior": "answer"}]}  # void must refuse
    r = c.post("/api/blueprints", json={"id": "bad", "blueprint": bad})
    assert r.status_code == 400

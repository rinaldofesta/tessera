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


def _client(tmp_path, *, eval_runner=None, discovery_cache=None):
    examples = tmp_path / "examples"
    logs = tmp_path / "logs"
    _write(examples, "first-contact.eval", _eval_log([_answer("q1", 1)]))
    app = create_app(
        eval_runner=eval_runner or (lambda req: _eval_log([_answer("q1", 1)])),
        log_dirs={"examples": examples, "logs": logs},
        schedule=_inline_schedule,
        blueprint_dir=tmp_path / "blueprints",
        run_store=RunStore(tmp_path / "runs.db"),
        discovery_cache=discovery_cache,
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
    # the leaderboard additions (incl. the local open-weights option) stay offered
    assert "anthropic/claude-haiku-4-5" in models and "ollama/qwen3.5:latest" in models


def test_list_models_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_MODELS", "a/x, b/y")
    r = _client(tmp_path).get("/api/models")
    assert r.status_code == 200 and r.json() == ["a/x", "b/y"]


def test_list_models_env_whitespace_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_MODELS", " , ,")
    r = _client(tmp_path).get("/api/models")
    assert r.status_code == 200 and "anthropic/claude-sonnet-4-6" in r.json()


def test_eval_setup_defaults_use_the_resolved_model_list(tmp_path):
    r = _client(tmp_path).get("/api/eval-setup")
    assert r.status_code == 200
    body = r.json()
    assert body["defaults"] == {
        "engine": "deterministic",
        "repeats": 3,
        "model": _client(tmp_path).get("/api/models").json()[0],
        "grader": None,
    }


def test_eval_setup_custom_models_start_unverified(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_MODELS", "anthropic/sonnet,openai/gpt,mlx/foo,ollama/x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    r = _client(tmp_path).get("/api/eval-setup")
    assert r.status_code == 200
    assert r.json()["models"] == [
        {"id": "anthropic/sonnet", "label": "sonnet", "provider": "anthropic",
         "readiness": "unverified", "group": "benchmark",
         "detail": "Custom model; availability has not been verified"},
        {"id": "openai/gpt", "label": "gpt", "provider": "openai",
         "readiness": "unverified", "group": "benchmark",
         "detail": "Custom model; availability has not been verified"},
        {"id": "mlx/foo", "label": "foo", "provider": "mlx",
         "readiness": "unverified", "group": "benchmark",
         "detail": "Custom model; availability has not been verified"},
        {"id": "ollama/x", "label": "x", "provider": "ollama",
         "readiness": "unverified", "group": "benchmark",
         "detail": "Custom model; availability has not been verified"},
    ]


def test_eval_setup_lists_builtin_and_stored_suites(tmp_path):
    from tessera.api import blueprint_store
    from tessera.orgs import get_blueprint

    client = _client(tmp_path)
    blueprint_store.save_blueprint(tmp_path / "blueprints", "mine", get_blueprint("toy"))

    r = client.get("/api/eval-setup")
    assert r.status_code == 200
    suites = {suite["id"]: suite for suite in r.json()["suites"]}
    toy = get_blueprint("toy")
    # Everything is editable in this product: builtins are materialized into the store as
    # editable JSON on first touch (seed_from_orgs). Only `kind` encodes origin.
    assert suites["toy"] == {
        "id": "toy", "kind": "builtin", "editable": True,
        "claims": len(toy.claims), "questions": len(toy.probes),
    }
    assert suites["mine"] == {
        "id": "mine", "kind": "custom", "editable": True,
        "claims": len(toy.claims), "questions": len(toy.probes),
    }


def test_eval_setup_builtin_kind_survives_store_seeding(tmp_path):
    # /api/orgs (seed=True) materializes every builtin into the store; the setup
    # endpoint must still report those suites as kind "builtin", not "custom".
    client = _client(tmp_path)
    client.get("/api/orgs")

    r = client.get("/api/eval-setup")
    suites = {suite["id"]: suite for suite in r.json()["suites"]}
    assert suites["toy"]["kind"] == "builtin"
    assert all(s["kind"] == "builtin" for s in suites.values() if s["id"] in ("toy", "meridian"))


def test_eval_setup_builtin_counts_match_the_runnable_store_copy(tmp_path, monkeypatch):
    from tessera.api import blueprint_store
    from tessera.models import Blueprint
    from tessera.orgs import get_blueprint

    store = tmp_path / "blueprints"
    original = get_blueprint("toy")
    edited = Blueprint(
        claims=original.claims[:-2],
        probes=[*original.probes[:2], original.probes[-1]],
    )
    blueprint_store.save_blueprint(store, "toy", edited)
    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(store))

    suites = {suite["id"]: suite for suite in _client(tmp_path).get("/api/eval-setup").json()["suites"]}
    assert suites["toy"]["claims"] == len(edited.claims)
    assert suites["toy"]["questions"] == len(edited.probes)


def test_eval_setup_never_discloses_credential_values(tmp_path, monkeypatch):
    sentinel = "sk-SENTINEL-123"
    monkeypatch.setenv("ANTHROPIC_API_KEY", sentinel)

    r = _client(tmp_path).get("/api/eval-setup")
    assert r.status_code == 200
    assert sentinel not in r.text


def test_eval_setup_and_rescan_survive_dead_runtimes_with_no_keys(tmp_path):
    import httpx

    from tessera.api.discovery.cache import DiscoveryCache
    from tessera.api.discovery.service import discover_snapshot, initial_snapshot

    env = {
        "OLLAMA_HOST": "http://ollama.test",
        "MLX_BASE_URL": "http://mlx.test:8090",
    }

    class DeadClient:
        def get(self, url, *, headers=None, timeout=None):
            raise httpx.ConnectError("down", request=httpx.Request("GET", url))

    cache = DiscoveryCache(
        lambda: discover_snapshot(DeadClient(), env, tmp_path, timeout=0.01),
        initial_snapshot(env),
    )
    client = _client(tmp_path, discovery_cache=cache)

    setup = client.get("/api/eval-setup")
    assert setup.status_code == 200
    assert len(setup.json()["models"]) == 6
    assert {m["readiness"] for m in setup.json()["models"]} <= {
        "needs_key", "offline", "unverified",
    }

    rescan = client.post("/api/model-discovery/rescan")
    assert rescan.status_code == 200
    assert {s["status"] for s in rescan.json()["sources"]} >= {
        "needs_key", "unreachable",
    }


def test_discovery_setup_and_rescan_never_disclose_credential_values(tmp_path):
    import httpx

    from tessera.api.discovery.cache import DiscoveryCache
    from tessera.api.discovery.service import discover_snapshot, initial_snapshot

    sentinel = "sk-SENTINEL-DISCOVERY"
    env = {
        "ANTHROPIC_API_KEY": sentinel,
        "OLLAMA_HOST": "http://ollama.test",
        "MLX_BASE_URL": "http://mlx.test:8090",
    }

    class DeadClient:
        def get(self, url, *, headers=None, timeout=None):
            raise httpx.ConnectError("down", request=httpx.Request("GET", url))

    cache = DiscoveryCache(
        lambda: discover_snapshot(DeadClient(), env, tmp_path, timeout=0.01),
        initial_snapshot(env),
    )
    client = _client(tmp_path, discovery_cache=cache)

    setup = client.get("/api/eval-setup")
    rescan = client.post("/api/model-discovery/rescan")

    assert setup.status_code == 200 and rescan.status_code == 200
    assert sentinel not in setup.text and sentinel not in rescan.text


def test_discovery_refresh_starts_in_background_without_a_setup_request(tmp_path):
    from threading import Event

    from tessera.api.discovery.cache import DiscoveryCache
    from tessera.api.discovery.models import DiscoverySnapshot

    refreshed = Event()
    snapshot = DiscoverySnapshot((), ())
    cache = DiscoveryCache(
        lambda: refreshed.set() or snapshot,
        snapshot,
        ttl_seconds=60,
    )
    client = _client(tmp_path, discovery_cache=cache)

    with client:
        assert refreshed.wait(timeout=1)


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


def test_resolve_rejects_unknown_source_empty_stem_and_traversal(tmp_path):
    # the log resolver's guard branches (the blueprint-store twin is parametrised; this is
    # its untested counterpart): unknown source, empty stem, and a traversal stem all -> None
    from tessera.api.routes_reports import _resolve
    log_dirs = {"results": tmp_path}
    assert _resolve(log_dirs, "bogus:abc") is None          # unknown source
    assert _resolve(log_dirs, "results:") is None           # empty stem
    assert _resolve(log_dirs, "results") is None            # no ':' -> empty stem
    assert _resolve(log_dirs, "results:../../../etc/passwd") is None   # no traversal


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

"""Key-free tests for the FastAPI app. Logs are fabricated on disk with write_eval_log;
the live-run path uses an injected fake runner + inline scheduler — no model calls."""

import json
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


def _client(tmp_path, *, eval_runner=None, folder_eval_runner=None, discovery_cache=None):
    examples = tmp_path / "examples"
    logs = tmp_path / "logs"
    _write(examples, "first-contact.eval", _eval_log([_answer("q1", 1)]))
    app = create_app(
        home=tmp_path / "home",
        eval_runner=eval_runner or (lambda req: _eval_log([_answer("q1", 1)])),
        folder_eval_runner=folder_eval_runner or _folder_eval,
        log_dirs={"examples": examples, "logs": logs},
        schedule=_inline_schedule,
        blueprint_dir=tmp_path / "blueprints",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
        # A stub by default: the real cache probes localhost:11434 and scans
        # ~/.cache/huggingface, which would make this suite neither network-free nor
        # deterministic — it would fail outright on a machine running Ollama.
        discovery_cache=discovery_cache or _stub_cache(),
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


def test_default_log_dirs_keep_bundled_example_aliases():
    from tessera.api.app import _DEFAULT_LOG_DIRS
    from tessera.api.routes_reports import _resolve, logs_in

    stems = [stem for stem, _ in logs_in(_DEFAULT_LOG_DIRS["examples"])]
    assert stems == ["first-contact", "gpt-4o"]
    resolved = _resolve(_DEFAULT_LOG_DIRS, "examples:first-contact")
    assert resolved is not None and resolved.name == "log.eval"
    assert _resolve(_DEFAULT_LOG_DIRS, "examples:../first-contact") is None


def test_logs_in_prefers_the_folder_layout_when_a_stem_has_both(tmp_path):
    """A directory holding both `foo.eval` and `foo/log.eval` must not list the same
    id twice — and whichever `logs_in` lists must be what `_resolve` returns."""
    from tessera.api.routes_reports import _resolve, logs_in

    (tmp_path / "foo.eval").write_bytes(b"flat")
    (tmp_path / "foo").mkdir()
    (tmp_path / "foo" / "log.eval").write_bytes(b"folder")

    listed = logs_in(tmp_path)

    assert [stem for stem, _ in listed] == ["foo"]
    resolved = _resolve({"examples": tmp_path}, "examples:foo")
    assert resolved == dict(listed)["foo"]
    assert resolved.read_bytes() == b"folder"


def test_default_api_log_source_lists_package_examples(tmp_path):
    app = create_app(
        home=tmp_path / "home",
        eval_runner=lambda req: _eval_log([_answer("q1", 1)]),
        schedule=_inline_schedule,
        blueprint_dir=tmp_path / "blueprints",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
        discovery_cache=_stub_cache(),
    )

    response = TestClient(app).get("/api/logs")

    assert response.status_code == 200
    assert {row["id"] for row in response.json()} >= {
        "examples:first-contact", "examples:gpt-4o",
    }


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
        home=home, run_store=RunStore(tmp_path / "runs.db"),
        blueprint_dir=tmp_path / "blueprints", env_file=tmp_path / ".env",
        discovery_cache=_stub_cache(),
    )

    with caplog.at_level("INFO"), TestClient(app):
        pass

    assert app.state.runs.get(record.id).data["status"] == "interrupted"
    assert record.id in caplog.text


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
    assert "anthropic/claude-fable-5" in models and "anthropic/claude-sonnet-5" in models


def test_default_published_models_match_single_model_leaderboard(monkeypatch):
    from tessera.api.routes_meta import published_models

    monkeypatch.delenv("TESSERA_MODELS", raising=False)
    rows_path = Path(__file__).parents[1] / "docs" / "leaderboard.rows.json"
    rows = json.loads(rows_path.read_text())["rows"]
    expected = {
        row["model"] for row in rows
        if row.get("harness", "single") == "single"
    }
    assert set(published_models()) == expected


def test_list_models_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_MODELS", "a/x, b/y")
    r = _client(tmp_path).get("/api/models")
    assert r.status_code == 200 and r.json() == ["a/x", "b/y"]


def test_list_models_env_whitespace_falls_back_to_published_set(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_MODELS", " , ,")
    r = _client(tmp_path).get("/api/models")
    assert r.status_code == 200 and "anthropic/claude-sonnet-4-6" in r.json()


def test_eval_setup_defaults_do_not_claim_a_model_selection(tmp_path):
    r = _client(tmp_path).get("/api/eval-setup")
    assert r.status_code == 200
    body = r.json()
    assert body["defaults"] == {
        "engine": "deterministic",
        "repeats": 3,
        "grader": None,
    }


def test_eval_setup_model_readiness(tmp_path, monkeypatch):
    # Readiness comes from what a source observed, never from an env var existing.
    # Only sonnet was seen by a source; everything else is a published placeholder, and
    # the ollama entry stays needs_config precisely because the daemon is offline.
    from tessera.api.discovery.types import DiscoveredModel

    monkeypatch.setenv("TESSERA_MODELS", "anthropic/sonnet,openai/gpt,mlx/foo,ollama/x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    cache = _stub_cache(models=[
        DiscoveredModel(
            "anthropic/sonnet", "Sonnet", "anthropic", "ready", "cloud",
            released="2026-08-01", retired=True,
        ),
    ])

    r = _client(tmp_path, discovery_cache=cache).get("/api/eval-setup")
    assert r.status_code == 200
    assert r.json()["models"] == [
        {"id": "anthropic/sonnet", "label": "Sonnet", "provider": "anthropic",
         "readiness": "ready", "source": "cloud", "published": True,
         "released": "2026-08-01", "retired": True, "detail": None},
        {"id": "openai/gpt", "label": "gpt", "provider": "openai",
         "readiness": "needs_config", "source": "published", "published": True,
         "released": None, "retired": False, "detail": None},
        {"id": "mlx/foo", "label": "foo", "provider": "unknown",
         "readiness": "needs_config", "source": "published", "published": True,
         "released": None, "retired": False, "detail": None},
        {"id": "ollama/x", "label": "x", "provider": "ollama",
         "readiness": "needs_config", "source": "published", "published": True,
         "released": None, "retired": False, "detail": None},
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


def test_every_api_route_declares_a_response_model(tmp_path):
    # The OpenAPI schema is the single contract the SPA types are generated from:
    # a route without a response_model publishes `unknown` and silently re-opens
    # the hand-maintained-types drift this guard exists to close.
    from fastapi.routing import APIRoute

    from tessera.api.app import create_app
    from tessera.api.run_store import RunStore

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

    app = create_app(home=tmp_path / "home", run_store=RunStore(tmp_path / "runs.db"),
                     blueprint_dir=tmp_path / "bp")
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


def test_runs_history_and_trends_after_a_run(tmp_path):
    client = _client(tmp_path)
    created = client.post("/api/runs", json={"model": "ollama/test"}).json()
    hist = client.get("/api/runs").json()
    run = next(row for row in hist if row["id"] == created["id"])
    assert run["status"] == "completed" and run["verdict"]["pass_k_rate"] == 1.0
    assert run["request"]["suite"] == "starter" and run["request"]["model"] == "ollama/test"
    assert all(row["report"] is None and row["receipt"] is None for row in hist)
    assert client.get("/api/trends").json() == []  # legacy sqlite trends are untouched


def test_run_persists_across_restart_same_home(tmp_path):
    run_id = _client(tmp_path).post("/api/runs", json={"model": "ollama/test"}).json()["id"]
    fresh = create_app(
        home=tmp_path / "home", run_store=RunStore(tmp_path / "fresh.db"),
        blueprint_dir=tmp_path / "bp2", log_dirs={}, schedule=_inline_schedule,
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


def test_folder_and_sqlite_report_serialization_parity(tmp_path):
    from tessera.api.schemas import RunRequest
    from tessera.report.serialize import report_to_dict

    captured = {}

    def runner(**kwargs):
        captured["log"] = _folder_eval(**kwargs)
        return captured["log"]

    client = _client(tmp_path, folder_eval_runner=runner)
    run_id = client.post("/api/runs", json={"model": "ollama/test"}).json()["id"]
    folder_report = client.get(f"/api/runs/{run_id}").json()["report"]
    expected = report_to_dict(captured["log"])

    sqlite = RunStore(tmp_path / "parity.db")
    job_id = sqlite.create(RunRequest(model="ollama/test", judge="deterministic"))
    sqlite.complete(job_id, expected)
    assert folder_report == expected == sqlite.get(job_id)["report"]


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


def _stub_cache(models=(), statuses=None):
    """A discovery cache with fixed contents.

    The real one probes localhost:11434 and scans ~/.cache/huggingface, so tests that
    used it were neither key-free nor network-free, and would fail outright on a machine
    with an Ollama daemon running — a documented workflow for this project.
    """
    from tessera.api.discovery.types import SourceResult

    resolved = list(statuses if statuses is not None else [
        SourceResult("cloud", (), "ok"),
        SourceResult("ollama", (), "offline", detail="daemon unreachable"),
        SourceResult("mlx", (), "ok"),
    ])

    class _Fixed:
        def get(self):
            # Run the real merge, so the stub honours the cache's actual contract:
            # published ids absent from every source come back as needs_config
            # placeholders. Returning raw source output instead would test a shape the
            # route never actually receives.
            from tessera.api.discovery.merge import merge
            from tessera.api.routes_meta import published_models
            # Hang the seeded models off an existing source rather than inventing one,
            # so the reported source set stays exactly the three real sources.
            seeded = list(resolved)
            if models:
                head = seeded[0]
                seeded[0] = SourceResult(head.source, tuple(models), head.status, head.detail)
            return merge(seeded, published=published_models())

        def invalidate(self):
            pass

    return _Fixed()


def _client_with_cache(tmp_path, cache):
    return TestClient(create_app(
        home=tmp_path / "home",
        eval_runner=lambda req: _eval_log([_answer("q1", 1)]),
        log_dirs={"logs": tmp_path / "logs"},
        schedule=_inline_schedule,
        blueprint_dir=tmp_path / "blueprints",
        run_store=RunStore(tmp_path / "runs.db"),
        env_file=tmp_path / ".env",
        discovery_cache=cache,
    ))


def test_eval_setup_reports_source_status_alongside_models(tmp_path):
    from tessera.api.discovery.types import DiscoveredModel
    cache = _stub_cache(models=[
        DiscoveredModel("anthropic/x", "x", "anthropic", "ready", "cloud"),
    ])
    body = _client_with_cache(tmp_path, cache).get("/api/eval-setup").json()
    assert {s["source"] for s in body["sources"]} == {"cloud", "ollama", "mlx"}
    assert all(
        "source" in model
        and "published" in model
        and "released" in model
        and "retired" in model
        for model in body["models"]
    )


def test_eval_setup_never_reports_an_unreachable_ollama_model_as_ready(tmp_path, monkeypatch):
    # The reproducible failure this phase exists to fix: the daemon is down, and the
    # published list still names an ollama model.
    monkeypatch.setenv("TESSERA_MODELS", "ollama/qwen3.5:latest,anthropic/claude-sonnet-4-6")
    body = _client_with_cache(tmp_path, _stub_cache()).get("/api/eval-setup").json()
    ollama = [m for m in body["models"] if m["provider"] == "ollama"]
    assert ollama, "the published ollama model should still be listed"
    assert all(m["readiness"] != "ready" for m in ollama)


def test_eval_setup_renders_with_every_runtime_down_and_no_keys(tmp_path):
    # Every source reports failure and nothing is discovered: the launcher must still
    # render the published set, honestly marked, rather than 500 or return nothing.
    from tessera.api.discovery.types import SourceResult
    cache = _stub_cache(statuses=[
        SourceResult("cloud", (), "ok"),
        SourceResult("ollama", (), "offline", detail="daemon unreachable"),
        SourceResult("mlx", (), "offline", detail="no server"),
    ])
    body = _client_with_cache(tmp_path, cache).get("/api/eval-setup").json()
    assert body["models"]                                     # still renders
    assert all(m["readiness"] != "ready" for m in body["models"])
    assert "model" not in body["defaults"]

"""Key-free contract tests for receipts, comparisons, preflight, and experiments."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore


def _sample(probe_id: str, epoch: int, passed: bool, conflict_type: str = "none"):
    from inspect_ai.log import EvalSample
    from inspect_ai.scorer import Score
    return EvalSample(
        id=probe_id, epoch=epoch, input="Q?", target="",
        metadata={"conflict_type": conflict_type, "expected_behavior": "answer",
                  "expected_sources": ["crm"]},
        scores={"reliability": Score(
            value="C" if passed else "I", answer="answer",
            metadata={"passed": passed, "accuracy_ok": passed,
                      "provenance_ok": passed, "refusal_ok": True,
                      "consulted": ["crm"] if passed else [],
                      "answer_format_ok": passed, "scorer_version": "det-test"},
        )},
    )


def _log(*, model: str = "provider/a", passed: tuple[bool, ...] = (True, False),
         org: str = "toy", scaffold: str = "baseline", seed: int = 0,
         location: str = "run.eval"):
    from inspect_ai.log import EvalConfig, EvalDataset, EvalLog, EvalSpec
    spec = EvalSpec(
        created="2026-08-29T10:00:00+00:00", task="tessera_probes",
        dataset=EvalDataset(), model=model, config=EvalConfig(epochs=len(passed)),
        task_args={"judge": "deterministic", "org": org, "scaffold": scaffold,
                   "seed": seed}, packages={"inspect_ai": "0.test"},
    )
    samples = [_sample("q1", epoch, result) for epoch, result in enumerate(passed, 1)]
    return EvalLog(eval=spec, samples=samples, location=location)


async def _inline(coro):
    await coro


def _client(tmp_path: Path, *, eval_runner=None, preflight_runner=None) -> TestClient:
    from inspect_ai.log import write_eval_log
    examples = tmp_path / "examples"
    examples.mkdir()
    pinned = examples / "pinned.eval"
    write_eval_log(_log(location=str(pinned)), str(pinned))

    async def quiet_preflight(model: str, require_tools: bool):
        return {
            "model": model, "effective_model": model + "-effective",
            "tool_call": require_tools, "ok": True, "error": None,
            "latency_seconds": 0.01, "checked_at": "2026-08-29T10:00:00+00:00",
            "cached": False,
            "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6,
                      "billed_cost": 0.001},
        }

    def runner(req):
        passed = (True, True) if req.model.endswith("b") else (True, False)
        return _log(model=req.model, passed=passed, org=req.org,
                    scaffold=req.scaffold, seed=req.seed,
                    location=str(tmp_path / f"{req.model.replace('/', '-')}.eval"))

    app = create_app(
        eval_runner=eval_runner or runner,
        run_store=RunStore(tmp_path / "runs.db"),
        log_dirs={"examples": examples, "logs": tmp_path / "logs"},
        blueprint_dir=tmp_path / "blueprints", import_dir=tmp_path / "imports",
        env_file=tmp_path / ".env", schedule=_inline,
        preflight_runner=preflight_runner or quiet_preflight,
    )
    return TestClient(app)


def test_library_indexes_files_and_api_runs_with_receipts(tmp_path):
    client = _client(tmp_path)
    started = client.post("/api/runs", json={"model": "provider/b", "judge": "deterministic"})
    assert started.status_code == 200
    rows = client.get("/api/evaluations").json()
    assert {row["kind"] for row in rows} == {"pinned", "run"}
    run = next(row for row in rows if row["kind"] == "run")
    assert run["receipt"]["runtime"]["requested_model"] == "provider/b"
    assert len(run["protocol_hash"]) == 64 and len(run["execution_hash"]) == 64
    assert run["receipt"]["protocol"]["blueprint_sha256"]
    assert client.app.state.workbench_store.get_evaluation(run["id"])["report"] is None


def test_library_never_returns_a_configured_credential(tmp_path, monkeypatch):
    from tessera.credential_scan import find_credential_like_values
    sentinel = "sk-" + "S" * 40
    monkeypatch.setenv("SOME_PROVIDER_API_KEY", sentinel)
    body = _client(tmp_path).get("/api/evaluations").json()
    assert sentinel not in str(body)
    assert find_credential_like_values(body) == []


def test_comparison_pairs_probe_epochs_and_rejects_hidden_protocol_drift(tmp_path):
    client = _client(tmp_path)
    first = client.post("/api/runs", json={"model": "provider/a", "judge": "deterministic"}).json()
    second = client.post("/api/runs", json={"model": "provider/b", "judge": "deterministic"}).json()
    comparison = client.post("/api/comparisons", json={
        "evaluation_a": f"run:{first['job_id']}",
        "evaluation_b": f"run:{second['job_id']}", "intervention": "model",
    }).json()
    assert comparison["compatible"] is True
    assert comparison["overall"] == {
        "matched": 2, "a_wins": 0, "b_wins": 1, "both_pass": 1,
        "both_fail": 0, "discordant": 1, "p_value": 1.0, "dropped": [],
    }
    diagnostics = client.get(f"/api/evaluations/run:{first['job_id']}/diagnostics").json()
    assert {item["kind"] for item in diagnostics} >= {
        "accuracy", "provenance", "answer_format", "missing_source", "flaky_probe",
    }

    changed_seed = client.post("/api/runs", json={
        "model": "provider/b", "judge": "deterministic", "seed": 9,
    }).json()
    drift = client.post("/api/comparisons", json={
        "evaluation_a": f"run:{first['job_id']}",
        "evaluation_b": f"run:{changed_seed['job_id']}", "intervention": "model",
    }).json()
    assert drift["compatible"] is False and "seed" in drift["unexpected_dimensions"]


def test_import_adds_a_durable_evaluation(tmp_path):
    from inspect_ai.log import write_eval_log
    path = tmp_path / "incoming.eval"
    write_eval_log(_log(location=str(path)), str(path))
    client = _client(tmp_path)
    with path.open("rb") as handle:
        response = client.post(
            "/api/evaluations/import",
            files={"file": ("incoming.eval", handle, "application/octet-stream")},
        )
    assert response.status_code == 201
    item = response.json()
    assert item["kind"] == "import"
    assert Path(item["artifact_path"]).is_file()
    assert client.get(f"/api/evaluations/{item['id']}/report").status_code == 200


def test_preflight_is_explicit_and_cached(tmp_path):
    calls = []

    async def probe(model: str, require_tools: bool):
        calls.append((model, require_tools))
        return {
            "model": model, "effective_model": "effective", "tool_call": True,
            "ok": True, "error": None, "latency_seconds": 0.1,
            "checked_at": "2026-08-29T10:00:00+00:00", "cached": False,
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
                      "billed_cost": None},
        }

    client = _client(tmp_path, preflight_runner=probe)
    assert calls == []
    first = client.post("/api/preflights", json={"model": "provider/a"}).json()
    second = client.post("/api/preflights", json={"model": "provider/a"}).json()
    assert first["cached"] is False and second["cached"] is True
    assert calls == [("provider/a", True)]


def test_experiment_runs_a_resumable_matrix_and_compares_variants(tmp_path):
    client = _client(tmp_path)
    payload = {
        "name": "model contrast", "baseline_variant": "a", "intervention": "model",
        "repeats": 2,
        "variants": [
            {"id": "a", "label": "A", "model": "provider/a", "judge": "deterministic"},
            {"id": "b", "label": "B", "model": "provider/b", "judge": "deterministic"},
        ],
    }
    started = client.post("/api/experiments", json=payload)
    assert started.status_code == 201
    experiment_id = started.json()["experiment_id"]
    experiment = client.get(f"/api/experiments/{experiment_id}").json()
    assert experiment["status"] == "done"
    assert len(experiment["cells"]) == 4
    assert {cell["status"] for cell in experiment["cells"]} == {"done"}

    result = client.get(
        f"/api/experiments/{experiment_id}/comparisons/b?intervention=model",
    ).json()
    assert result["compatible"] is True
    assert result["paired_repeats"] == [1, 2]
    assert result["overall"]["matched"] == 4


def test_experiment_rejects_a_challenger_with_hidden_protocol_drift(tmp_path):
    client = _client(tmp_path)
    response = client.post("/api/experiments", json={
        "name": "bad contrast", "baseline_variant": "a", "intervention": "model",
        "variants": [
            {"id": "a", "label": "A", "model": "provider/a", "judge": "deterministic"},
            {"id": "b", "label": "B", "model": "provider/b", "judge": "deterministic",
             "seed": 9},
        ],
    })
    assert response.status_code == 422


def test_cost_ceiling_stops_when_the_provider_does_not_report_cost(tmp_path):
    client = _client(tmp_path)
    response = client.post("/api/experiments", json={
        "name": "budgeted", "baseline_variant": "a", "intervention": "model",
        "max_cost": 1.0,
        "variants": [
            {"id": "a", "label": "A", "model": "provider/a", "judge": "deterministic"},
            {"id": "b", "label": "B", "model": "provider/b", "judge": "deterministic"},
        ],
    })
    experiment = client.get(f"/api/experiments/{response.json()['experiment_id']}").json()
    assert experiment["status"] == "stopped"
    assert experiment["total_cost"] is None
    assert [cell["status"] for cell in experiment["cells"]].count("done") == 1
    assert [cell["status"] for cell in experiment["cells"]].count("skipped") == 1


def test_interrupted_experiment_becomes_resumable(tmp_path):
    from tessera.api.schemas import ExperimentRequest
    from tessera.api.workbench_store import WorkbenchStore

    store = WorkbenchStore(tmp_path / "workbench.db")
    request = ExperimentRequest.model_validate({
        "name": "interrupted", "baseline_variant": "a", "intervention": "model",
        "variants": [
            {"id": "a", "label": "A", "model": "provider/a", "judge": "deterministic"},
            {"id": "b", "label": "B", "model": "provider/b", "judge": "deterministic"},
        ],
    })
    experiment_id = store.create_experiment(request)
    claimed = store.next_cell(experiment_id)
    assert claimed and claimed["status"] == "running"
    store.recover_interrupted()
    recovered = store.get_experiment(experiment_id)
    assert recovered["status"] == "stopped"
    assert {cell["status"] for cell in recovered["cells"]} == {"pending"}

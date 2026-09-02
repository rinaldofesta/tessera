"""/learn serves the plain-language guide; excluded from the OpenAPI contract."""

from fastapi.testclient import TestClient

from tessera.api.app import create_app
from tessera.api.run_store import RunStore


def _client(tmp_path) -> TestClient:
    return TestClient(create_app(home=tmp_path / "home",
                                 run_store=RunStore(tmp_path / "runs.db"),
                                 blueprint_dir=tmp_path / "blueprints"))


def test_learn_serves_the_plain_language_guide(tmp_path):
    resp = _client(tmp_path).get("/learn")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    # the real guide is a large self-contained page; the SPA fallback index.html is a
    # few hundred bytes — length alone discriminates a mis-mounted /learn
    assert len(resp.text) > 50_000


def test_learn_is_not_in_the_openapi_contract(tmp_path):
    paths = _client(tmp_path).get("/openapi.json").json()["paths"]
    assert "/learn" not in paths

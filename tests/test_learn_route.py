"""/learn serves the plain-language guide; excluded from the OpenAPI contract."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tessera.api.app import _mount_spa, create_app, lesson_path


def _client(tmp_path) -> TestClient:
    return TestClient(create_app(home=tmp_path / "home",
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


def test_mount_spa_serves_package_data(tmp_path, monkeypatch):
    package = tmp_path / "package"
    packaged_index = package / "web" / "index.html"
    packaged_index.parent.mkdir(parents=True)
    packaged_index.write_text("packaged UI")
    monkeypatch.setattr("tessera.api.app.resources.files", lambda _package: package)
    app = FastAPI()

    _mount_spa(app)

    assert TestClient(app).get("/").text == "packaged UI"


def test_lesson_path_prefers_package_data(tmp_path, monkeypatch):
    package = tmp_path / "package"
    packaged_lesson = package / "lesson.html"
    packaged_lesson.parent.mkdir(parents=True)
    packaged_lesson.write_text("packaged lesson")
    monkeypatch.setattr("tessera.api.app.resources.files", lambda _package: package)

    assert lesson_path() == packaged_lesson


def test_mount_spa_skips_directory_without_index(tmp_path):
    app = FastAPI()

    _mount_spa(app, tmp_path)

    assert TestClient(app).get("/").status_code == 404

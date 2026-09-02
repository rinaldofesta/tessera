import stat

from tessera import paths


def test_home_uses_tessera_home_and_resolves_it(tmp_path, monkeypatch):
    configured = tmp_path / "state" / ".." / "state"
    monkeypatch.setenv("TESSERA_HOME", str(configured))

    assert paths.home() == (tmp_path / "state").resolve()
    assert paths.suites_dir() == (tmp_path / "state" / "suites").resolve()
    assert paths.runs_dir() == (tmp_path / "state" / "runs").resolve()


def test_home_defaults_to_dot_tessera(tmp_path, monkeypatch):
    monkeypatch.delenv("TESSERA_HOME", raising=False)
    monkeypatch.setattr(paths.Path, "home", lambda: tmp_path)

    assert paths.home() == tmp_path / ".tessera"


def test_env_file_override_takes_precedence_over_home(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("TESSERA_ENV_FILE", str(tmp_path / "override.env"))

    assert paths.env_file() == tmp_path / "override.env"


def test_ensure_home_sets_fresh_home_to_owner_only_and_is_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "state"
    monkeypatch.setenv("TESSERA_HOME", str(path))

    assert paths.ensure_home() == path
    assert stat.S_IMODE(path.stat().st_mode) == 0o700
    assert (path / "suites").is_dir()
    assert (path / "runs").is_dir()

    path.chmod(0o755)
    assert paths.ensure_home() == path
    assert stat.S_IMODE(path.stat().st_mode) == 0o755

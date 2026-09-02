from pathlib import Path

from fastapi.testclient import TestClient

from tessera.api.app import create_app


def _app(tmp_path: Path, env_file: Path):
    return create_app(
        home=tmp_path / "home",
        blueprint_dir=tmp_path / "bp",
        env_file=env_file,
    )


def test_the_resolved_env_file_is_absolute_and_exposed_on_app_state(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EXAMPLE_KEY=value\n")
    app = _app(tmp_path, env)
    assert app.state.env_file == env.resolve()
    assert app.state.env_file.is_absolute()


def test_startup_loads_the_injected_file_into_the_process_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("TESSERA_EXAMPLE", raising=False)
    env = tmp_path / ".env"
    env.write_text("TESSERA_EXAMPLE=from-injected-file\n")
    with TestClient(_app(tmp_path, env)):        # context manager runs startup
        import os
        assert os.environ["TESSERA_EXAMPLE"] == "from-injected-file"


def test_a_value_containing_a_shell_style_expansion_is_loaded_literally(tmp_path, monkeypatch):
    # python-dotenv interpolates ${VAR} in BOTH quoting styles unless disabled, which
    # would silently corrupt any credential containing "${".
    monkeypatch.delenv("TESSERA_LITERAL", raising=False)
    env = tmp_path / ".env"
    env.write_text('TESSERA_LITERAL="sk-${HOME}-tail"\n')
    with TestClient(_app(tmp_path, env)):
        import os
        assert os.environ["TESSERA_LITERAL"] == "sk-${HOME}-tail"


def test_constructing_the_app_reads_no_file(tmp_path):
    # gen-types.sh imports the module from a scratch cwd; construction must stay inert.
    missing = tmp_path / "definitely-absent" / ".env"
    app = _app(tmp_path, missing)                # must not raise
    assert app.state.env_file == missing.resolve()

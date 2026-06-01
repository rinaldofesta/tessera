from tessera.evals.task import tessera_probes


def test_task_builds_for_both_engines(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path / "run"))
    assert len(tessera_probes().dataset) == 4               # default: deterministic
    assert len(tessera_probes(judge="llm").dataset) == 4    # llm engine selected

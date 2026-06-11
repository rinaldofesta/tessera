import importlib

from tessera.compiler import compile_blueprint
from tessera.examples.toy_org import build_toy_blueprint


def test_crm_server_module_exposes_a_fastmcp_app(tmp_path, monkeypatch):
    compile_blueprint(build_toy_blueprint(), tmp_path)
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path))
    mod = importlib.import_module("tessera.mcp.crm_server")
    importlib.reload(mod)
    assert "Gold" in mod.crm_lookup("Acme Corp")
    assert mod.crm_lookup("Beta Corp") == "NOT_FOUND"
    filtered = mod.crm_lookup("Acme Corp", fields=["tier"])
    assert "Gold" in filtered and "renewal_date" not in filtered
    assert mod.mcp.name  # a FastMCP instance is present


def test_docs_server_tools_work(tmp_path, monkeypatch):
    compile_blueprint(build_toy_blueprint(), tmp_path)
    monkeypatch.setenv("TESSERA_OUT", str(tmp_path))
    mod = importlib.import_module("tessera.mcp.docs_server")
    importlib.reload(mod)
    hits = mod.docs_search("renewal")
    assert hits  # JSON string list
    assert "Renewal pushed to 2026-03-01" in mod.docs_get_file(
        __import__("json").loads(hits)[0]["path"]
    )

import pytest

from tessera.compiler import compile_blueprint
from tessera.examples.toy_org import build_toy_blueprint
from tessera.silos.access import crm_lookup_record, docs_get_file, docs_search


@pytest.fixture
def out(tmp_path):
    compile_blueprint(build_toy_blueprint(), tmp_path)
    return tmp_path


def test_crm_lookup_returns_record(out):
    rec = crm_lookup_record(out, "Acme Corp")
    assert rec == {"tier": "Gold", "renewal_date": "2026-01-01"}


def test_crm_lookup_missing_account_returns_none(out):
    assert crm_lookup_record(out, "Beta Corp") is None


def test_docs_search_finds_the_renewal_note(out):
    hits = docs_search(out, "renewal")
    paths = [h["path"] for h in hits]
    assert any("renewal" in p for p in paths)
    assert all("path" in h and "excerpt" in h for h in hits)


def test_docs_get_file_returns_body_text(out):
    hits = docs_search(out, "renewal")
    path = hits[0]["path"]
    content = docs_get_file(out, path)
    assert "Renewal pushed to 2026-03-01" in content


def test_docs_get_file_rejects_path_outside_docs(out):
    with pytest.raises(ValueError):
        docs_get_file(out, "../crm/db.json")

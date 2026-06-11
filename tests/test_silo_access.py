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
    assert rec == {
        "tier": {"value": "Gold", "asserted_at": None},
        "renewal_date": {"value": "2026-01-01", "asserted_at": "2025-11-15T10:00:00Z"},
    }


def test_crm_lookup_exposes_asserted_at_so_the_tie_is_visible(out):
    # The unresolvable probe is only valid if the agent can SEE that the CRM value and
    # the conflicting note share a timestamp. crm_lookup must expose asserted_at, or the
    # agent reasonably (but wrongly) resolves the standoff by recency.
    rec = crm_lookup_record(out, "Globex Inc")
    assert rec["contract_value"] == {"value": "$1.2M", "asserted_at": "2026-02-01T09:00:00Z"}


def test_crm_lookup_missing_account_returns_none(out):
    assert crm_lookup_record(out, "Beta Corp") is None


def test_crm_lookup_filters_to_requested_fields(out):
    # det-4: the agent can fetch just the fields it needs; provenance follows the response
    rec = crm_lookup_record(out, "Acme Corp", fields=["tier"])
    assert rec == {"tier": {"value": "Gold", "asserted_at": None}}
    assert crm_lookup_record(out, "Acme Corp", fields=["no_such_field"]) == {}
    assert crm_lookup_record(out, "Beta Corp", fields=["tier"]) is None


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


def test_docs_search_finds_note_with_natural_language_query(out):
    # The First Contact bug: an agent searches with a full phrase, not one keyword.
    # The old whole-phrase substring match returned [] because the note BODY never
    # contains "acme corp renewal date" (the entity/topic live in the filename). A
    # realistic search tokenizes the query and indexes the filename alongside the body.
    hits = docs_search(out, "Acme Corp renewal date")
    paths = [h["path"] for h in hits]
    assert any("acme" in p and "renewal" in p for p in paths)


def test_docs_search_ranks_by_term_overlap(out):
    # "contract value renewal": the globex note matches two terms, the acme note one,
    # so globex ranks first; the acme note still surfaces lower.
    hits = docs_search(out, "contract value renewal")
    paths = [h["path"] for h in hits]
    assert "globex" in paths[0]
    assert any("renewal" in p for p in paths)


def test_docs_search_no_matching_terms_returns_empty(out):
    assert docs_search(out, "quarterly earnings forecast") == []

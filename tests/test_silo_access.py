import pytest

from evalogy.compiler import compile_blueprint
from evalogy.examples.toy_org import build_toy_blueprint
from evalogy.silos.access import crm_lookup_record, docs_get_file, docs_search


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


def test_crm_lookup_only_follows_links_inside_linked_output_root(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    out = tmp_path / "org"
    out.symlink_to(store, target_is_directory=True)
    compile_blueprint(build_toy_blueprint(), out)
    db = store / "crm" / "db.json"
    backup = db.with_name("backup.json")
    db.rename(backup)
    db.symlink_to(backup)
    assert crm_lookup_record(out, "Acme Corp")["tier"]["value"] == "Gold"

    outside = tmp_path / "outside.json"
    outside.write_text('{"Acme Corp": {"tier": "external"}}')
    db.unlink()
    db.symlink_to(outside)
    assert crm_lookup_record(out, "Acme Corp") is None


def test_crm_lookup_filters_to_requested_fields(out):
    # det-4: the agent can fetch just the fields it needs; provenance follows the response
    rec = crm_lookup_record(out, "Acme Corp", fields=["tier"])
    assert rec == {"tier": {"value": "Gold", "asserted_at": None}}
    assert crm_lookup_record(out, "Beta Corp", fields=["tier"]) is None


def test_crm_lookup_names_unknown_fields_and_lists_available(out):
    # a wrong field-name guess must be distinguishable from an absent field: the record
    # names the unknowns and the available schema (like a real API) — '{}' would be
    # ambiguous with "field is empty"
    rec = crm_lookup_record(out, "Acme Corp", fields=["seats", "tier"])
    assert rec["_unknown_fields"] == ["seats"]
    assert rec["_available_fields"] == ["renewal_date", "tier"]
    assert rec["tier"]["value"] == "Gold"
    only_miss = crm_lookup_record(out, "Acme Corp", fields=["no_such_field"])
    assert only_miss["_unknown_fields"] == ["no_such_field"] and "tier" not in only_miss


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


def test_docs_search_and_read_only_follow_links_inside_docs(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (tmp_path / "other.md").touch()
    (docs / "external.md").symlink_to(tmp_path / "other.md")
    (docs / "note.md").write_text("meeting")
    (docs / "internal.md").symlink_to("note.md")

    assert docs_search(tmp_path, "external internal") == [
        {"path": "docs/internal.md", "excerpt": "meeting"},
    ]
    with pytest.raises(ValueError, match="outside docs"):
        docs_get_file(tmp_path, "docs/external.md")
    assert docs_get_file(tmp_path, "docs/internal.md") == "meeting"


def test_docs_root_cannot_redirect_reads(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "note.md").touch()
    (tmp_path / "docs").symlink_to(other, target_is_directory=True)

    assert docs_search(tmp_path, "note") == []
    with pytest.raises(ValueError, match="outside docs"):
        docs_get_file(tmp_path, "docs/note.md")


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

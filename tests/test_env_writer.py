import os
import stat
import threading

import pytest

from tessera.api.env_writer import EnvValueError, apply_updates, validate_base_url, validate_secret


def _noop() -> None:
    pass


@pytest.mark.parametrize("bad", ["", "   ", "a\nb", "a\rb", "a\x00b"])
def test_values_that_could_inject_a_second_assignment_are_rejected(bad):
    with pytest.raises(EnvValueError):
        validate_secret(bad)


def test_the_rejection_message_never_contains_the_value():
    try:
        validate_secret("sk-SENTINEL-123\nINJECTED=1")
    except EnvValueError as exc:
        assert "SENTINEL" not in str(exc) and "INJECTED" not in str(exc)


@pytest.mark.parametrize("url", ["http://localhost:8080/v1", "https://api.example.com/v1"])
def test_plain_http_and_https_urls_including_localhost_are_accepted(url):
    assert validate_base_url(url) == url


@pytest.mark.parametrize("bad", [
    "ftp://host/v1", "not-a-url", "http://user:pass@host/v1", "https://:secret@host",
])
def test_non_http_schemes_and_urls_embedding_credentials_are_rejected(bad):
    with pytest.raises(EnvValueError):
        validate_base_url(bad)


def test_an_upsert_preserves_comments_ordering_and_unrelated_keys(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# leading comment\nANTHROPIC_API_KEY=keep-me\n\nOPENAI_API_KEY=also-keep\n")
    apply_updates(env, {"OPENAI_API_KEY": "new-value"}, invalidate=_noop)
    lines = env.read_text().splitlines()
    assert lines[0] == "# leading comment"
    assert lines[1] == "ANTHROPIC_API_KEY=keep-me"
    assert 'OPENAI_API_KEY="new-value"' in lines


def test_a_new_key_is_appended_when_absent(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    apply_updates(env, {"MLX_BASE_URL": "http://localhost:8080/v1"}, invalidate=_noop)
    assert 'MLX_BASE_URL="http://localhost:8080/v1"' in env.read_text()
    assert "EXISTING=1" in env.read_text()


def test_both_fields_land_in_a_single_rewrite(tmp_path):
    env = tmp_path / ".env"
    env.write_text("")
    apply_updates(env, {"MLX_API_KEY": "k", "MLX_BASE_URL": "http://localhost:8080/v1"},
                  invalidate=_noop)
    body = env.read_text()
    assert 'MLX_API_KEY="k"' in body and 'MLX_BASE_URL="http://localhost:8080/v1"' in body


def test_a_value_with_quotes_backslashes_and_expansions_round_trips(tmp_path):
    from dotenv import dotenv_values
    awkward = 'sk-${HOME}-"q"-\\b-#c d'
    env = tmp_path / ".env"
    env.write_text("")
    apply_updates(env, {"OPENAI_API_KEY": awkward}, invalidate=_noop)
    assert dotenv_values(env, interpolate=False)["OPENAI_API_KEY"] == awkward


def test_the_written_file_is_owner_only(tmp_path):
    env = tmp_path / ".env"
    env.write_text("")
    apply_updates(env, {"OPENAI_API_KEY": "k"}, invalidate=_noop)
    assert stat.S_IMODE(env.stat().st_mode) == 0o600


def test_the_process_environment_and_cache_are_updated_after_the_write(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    invalidated = []
    env = tmp_path / ".env"
    env.write_text("")
    apply_updates(env, {"OPENAI_API_KEY": "k"}, invalidate=lambda: invalidated.append(1))
    assert os.environ["OPENAI_API_KEY"] == "k"
    assert invalidated == [1]


def test_concurrent_writes_to_different_fields_lose_neither(tmp_path):
    from dotenv import dotenv_values
    env = tmp_path / ".env"
    env.write_text("")
    barrier = threading.Barrier(2)

    def write(key, value):
        barrier.wait()
        apply_updates(env, {key: value}, invalidate=_noop)

    threads = [threading.Thread(target=write, args=a)
               for a in (("MLX_API_KEY", "k"), ("MLX_BASE_URL", "http://localhost:8080/v1"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    values = dotenv_values(env, interpolate=False)
    assert values["MLX_API_KEY"] == "k"
    assert values["MLX_BASE_URL"] == "http://localhost:8080/v1"


def test_no_temp_file_survives_a_successful_write(tmp_path):
    env = tmp_path / ".env"
    env.write_text("")
    apply_updates(env, {"OPENAI_API_KEY": "k"}, invalidate=_noop)
    assert [p.name for p in tmp_path.iterdir()] == [".env"]


@pytest.mark.parametrize("evil", ["k\nINJECTED=1", "k\r\nINJECTED=1", "k\x00x", "", "   "])
def test_apply_updates_rejects_injection_without_touching_the_file(tmp_path, evil):
    # apply_updates is the function that writes secrets to disk, so it enforces the
    # file-format invariant itself rather than trusting callers. Without this, a caller
    # that forgot to validate could open a second assignment line in .env.
    env = tmp_path / ".env"
    env.write_text("# keep\nEXISTING=1\n")
    before = env.read_bytes()
    with pytest.raises(EnvValueError):
        apply_updates(env, {"OPENAI_API_KEY": evil}, invalidate=_noop)
    assert env.read_bytes() == before


def test_a_rejected_value_in_a_multi_field_write_blocks_the_whole_transaction(tmp_path):
    # All-or-nothing: one bad field must not let its well-formed sibling through, or the
    # provider is left half-configured.
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    before = env.read_bytes()
    with pytest.raises(EnvValueError):
        apply_updates(env, {"MLX_BASE_URL": "http://localhost:8080/v1",
                            "MLX_API_KEY": "bad\nINJECTED=1"}, invalidate=_noop)
    assert env.read_bytes() == before


# --- regressions from the independent adversarial verification of Task 9 -------------

@pytest.mark.parametrize("sep", [" ", " ", "\x85", "\v", "\f", "\x1c", "\x1d", "\x1e"])
def test_unicode_and_control_line_separators_cannot_inject_on_a_later_rewrite(tmp_path, sep):
    # str.splitlines() breaks on these; dotenv does not. A value stored with one used to
    # survive the first write and then split into two assignments on the NEXT rewrite.
    env = tmp_path / ".env"
    env.write_text("")
    with pytest.raises(EnvValueError):
        apply_updates(env, {"TARGET": f"secret{sep}INJECTED=owned"}, invalidate=_noop)
    assert "INJECTED" not in env.read_text()


def test_a_duplicate_key_is_collapsed_so_the_file_agrees_with_the_environment(tmp_path):
    # dotenv resolves duplicates to the LAST occurrence. Replacing only the first left a
    # stale duplicate that won on read, so the file and os.environ disagreed.
    from dotenv import dotenv_values
    env = tmp_path / ".env"
    env.write_text("TARGET=first\nOTHER=keep\nTARGET=last\n")
    apply_updates(env, {"TARGET": "new"}, invalidate=_noop)
    values = dotenv_values(env, interpolate=False)
    assert values["TARGET"] == "new"
    assert values["OTHER"] == "keep"
    assert env.read_text().count("TARGET=") == 1


def test_a_lone_surrogate_is_rejected_rather_than_failing_at_write_time(tmp_path):
    # It passed every check and then raised UnicodeEncodeError, so an "accepted" value
    # could not actually round-trip.
    with pytest.raises(EnvValueError):
        validate_secret("prefix-\ud800-suffix")


def test_leading_blank_lines_survive_a_write(tmp_path):
    env = tmp_path / ".env"
    env.write_text("\n\nA=1\n")
    apply_updates(env, {"B": "2"}, invalidate=_noop)
    assert env.read_text().startswith("\n\n")


def test_repeated_writes_do_not_grow_trailing_newlines(tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\n")
    for i in range(5):
        apply_updates(env, {"A": f"v{i}"}, invalidate=_noop)
    assert env.read_text() == 'A="v4"\n'


@pytest.mark.parametrize("bad_key", [
    "GOOD\nINJECTED=owned", "HAS=EQUALS", "1LEADING_DIGIT", "has-dash", "", "WITH SPACE",
])
def test_a_malformed_variable_name_is_rejected_before_anything_is_written(tmp_path, bad_key):
    # Keys come from the provider registry, not user input — but a key containing a
    # newline used to reach disk and inject a line, and only THEN did os.environ reject
    # it, leaving the file corrupted while the process kept the old values.
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    before = env.read_bytes()
    with pytest.raises(EnvValueError):
        apply_updates(env, {bad_key: "value"}, invalidate=_noop)
    assert env.read_bytes() == before


def test_a_url_that_makes_urlparse_itself_raise_becomes_a_validation_error():
    # urlparse raises ValueError on an unbalanced "[" (it reads as a bad IPv6 host).
    # Callers catch EnvValueError to build a 422, so a bare ValueError would be a 500.
    with pytest.raises(EnvValueError):
        validate_base_url("http://[bad/v1")


@pytest.mark.parametrize("padded", ["  sk-abc123def456  ", "\tsk-abc123def456\t", " sk-abc123def456"])
def test_a_pasted_value_is_stored_without_surrounding_whitespace(tmp_path, padded):
    # A padded key passed validation and was stored verbatim, so the provider reported
    # itself configured while every API call failed with an opaque auth error that
    # pointed nowhere near the cause.
    from dotenv import dotenv_values
    env = tmp_path / ".env"
    env.write_text("")
    apply_updates(env, {"OPENAI_API_KEY": padded}, invalidate=_noop)
    assert dotenv_values(env, interpolate=False)["OPENAI_API_KEY"] == "sk-abc123def456"


def test_a_newline_is_still_rejected_rather_than_trimmed(tmp_path):
    # Trimming must not become a way to sneak a line separator past validation.
    env = tmp_path / ".env"
    env.write_text("EXISTING=1\n")
    before = env.read_bytes()
    with pytest.raises(EnvValueError):
        apply_updates(env, {"OPENAI_API_KEY": "sk-abc\nINJECTED=1"}, invalidate=_noop)
    assert env.read_bytes() == before


def test_a_base_url_with_surrounding_whitespace_is_accepted_and_trimmed():
    assert validate_base_url("  http://localhost:8080/v1  ") == "http://localhost:8080/v1"

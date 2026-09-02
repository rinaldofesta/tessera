"""The eval-runner kwargs seam — guards the epochs/org/grader wiring without a model."""

from tessera.api.runner import _eval_kwargs
from tessera.api.schemas import RunRequest


def test_eval_kwargs_passes_k_to_the_task_not_to_eval():
    kw = _eval_kwargs(RunRequest(model="m", grader="g", judge="llm", org="acme", epochs=5))
    assert kw["task_args"] == {
        "judge": "llm", "org": "acme", "k": 5,
        "scaffold": "baseline", "seed": 0,
    }
    # regression: an eval-level epochs kwarg overrides the COUNT but keeps the
    # task's pass_k(3) reducer — k<3 hard-errored, k>3 mislabeled. The task owns
    # count and reducer together, so eval must not pass epochs at all.
    assert "epochs" not in kw
    assert kw["model_roles"] == {"grader": "g"}
    assert kw["display"] == "none"


def test_eval_kwargs_omits_grader_when_absent():
    kw = _eval_kwargs(RunRequest(model="m", judge="deterministic", org="toy"))
    assert "model_roles" not in kw
    assert kw["task_args"]["k"] == 3 and kw["task_args"]["judge"] == "deterministic"


def test_job_env_pins_blueprint_store_to_an_absolute_path(tmp_path, monkeypatch):
    # regression: inspect_ai runs the task with the task file's directory as cwd,
    # so a cwd-relative blueprint store made every saved-blueprint run fail with
    # "unknown org" — the author->run loop only worked for built-in orgs.
    from tessera.api.runner import _job_env

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TESSERA_BLUEPRINT_DIR", raising=False)
    env = _job_env()
    assert env["TESSERA_BLUEPRINT_DIR"] == str(tmp_path / "blueprints")
    assert env["TESSERA_OUT"].startswith("/tmp/tessera/run-")


def test_job_env_respects_an_explicit_blueprint_dir(tmp_path, monkeypatch):
    from tessera.api.runner import _job_env

    monkeypatch.setenv("TESSERA_BLUEPRINT_DIR", str(tmp_path / "store"))
    assert _job_env()["TESSERA_BLUEPRINT_DIR"] == str(tmp_path / "store")


def test_a_credential_url_in_an_error_is_not_stored_raw():
    from tessera.api.runner import scrub_error
    message = scrub_error("POST http://user:sk-SENTINEL-123@api.host/v1/messages failed")
    assert "sk-SENTINEL-123" not in message
    assert "user:" not in message


def test_a_configured_key_appearing_in_an_error_is_redacted(monkeypatch):
    from tessera.api.runner import scrub_error
    monkeypatch.setenv("OPENAI_API_KEY", "sk-" + "z" * 32)
    message = scrub_error("bad key: sk-" + "z" * 32)
    assert "z" * 32 not in message
    assert "[redacted]" in message


def test_the_scanner_finds_no_credentials_in_a_scrubbed_message():
    from tessera.api.runner import scrub_error
    from tessera.credential_scan import find_credential_like_values
    message = scrub_error("Authorization: Bearer " + "h" * 32)
    assert find_credential_like_values({"error": message}) == []


def test_a_clean_message_passes_through_byte_for_byte():
    # The scrubber must not reformat: the ValueError branch stores a bare message and
    # the API surface depends on it.
    from tessera.api.runner import scrub_error
    original = "grader must differ from the model under test"
    assert scrub_error(original) == original


def test_the_self_grading_guard_message_keeps_its_existing_bare_shape(tmp_path):
    # Regression guard for the amendment: no "ValueError: " prefix appears.
    from tessera.api.runner import scrub_error
    assert not scrub_error("grader must differ from the model under test").startswith("ValueError")


# --- regressions from the high-tier review of Task 11 --------------------------------

def test_a_credential_from_a_provider_tessera_does_not_know_is_still_redacted(monkeypatch):
    # RunRequest.model is free text by design, so a run can target any inspect_ai
    # provider. Redacting only the registered eight let a Bedrock/Azure credential
    # through into the run record.
    from tessera.api.runner import scrub_error
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalr" + "X" * 35)
    monkeypatch.setenv("AZURE_API_KEY", "az-" + "Z" * 32)
    for var in ("AWS_SECRET_ACCESS_KEY", "AZURE_API_KEY"):
        import os
        secret = os.environ[var]
        assert secret not in scrub_error(f"call failed using {secret}")


def test_an_authorization_header_of_any_scheme_is_redacted():
    # AWS SigV4 is "Authorization: AWS4-HMAC-SHA256 Credential=..., Signature=..." —
    # matching only Bearer/Basic left the whole signature exposed.
    from tessera.api.runner import scrub_error
    out = scrub_error("Authorization: AWS4-HMAC-SHA256 Credential=AKIA1/x, Signature=deadbeef")
    assert "AKIA1" not in out and "deadbeef" not in out


def test_a_password_containing_an_at_sign_is_fully_redacted():
    # The userinfo pattern stopped at the FIRST @, leaving the rest of the password.
    from tessera.api.runner import scrub_error
    assert scrub_error("http://user:p@ssword@host/v1") == "http://[redacted]@host/v1"


def test_a_short_environment_value_does_not_mangle_ordinary_prose(monkeypatch):
    # A name-based sweep must not redact every occurrence of a two-character "key".
    from tessera.api.runner import scrub_error
    monkeypatch.setenv("SOME_KEY", "ab")
    assert scrub_error("the grader ab must differ") == "the grader ab must differ"


def test_a_secret_that_prefixes_a_longer_secret_does_not_leave_a_tail(monkeypatch):
    from tessera.api.runner import scrub_error
    monkeypatch.setenv("SHORT_TOKEN", "sk-commonprefix")
    monkeypatch.setenv("LONG_TOKEN", "sk-commonprefix-and-more-tail")
    out = scrub_error("used sk-commonprefix-and-more-tail here")
    assert "and-more-tail" not in out


# --- regressions from the independent privacy review of Task 11 ----------------------

def test_the_userinfo_pattern_stays_linear_on_long_input():
    # An unbounded scheme run before "://" backtracked quadratically: a multi-megabyte
    # exception could stall error handling and strand a job as "running".
    import time

    from tessera.api.scrub import scrub_error
    started = time.perf_counter()
    scrub_error("a" * 500_000)
    assert time.perf_counter() - started < 2.0


def test_a_secret_with_surrounding_whitespace_is_redacted_in_both_forms(monkeypatch):
    # The length floor was applied to the stripped value, so a quoted .env value whose
    # raw form met the floor survived because its trimmed core did not.
    from tessera.api.scrub import scrub_error
    monkeypatch.setenv("PADDED_TOKEN", "  abcdef  ")
    assert "abcdef" not in scrub_error("failed with '  abcdef  '")


def test_the_store_redacts_even_when_a_caller_forgets(tmp_path, monkeypatch):
    # Defence in depth at the boundary that persists the text: a future writer that
    # skips scrub_error must not be able to reopen the leak.
    from tessera.api.run_store import RunStore
    from tessera.api.schemas import RunRequest
    monkeypatch.setenv("SOME_API_KEY", "sk-" + "P" * 30)
    import os
    store = RunStore(tmp_path / "runs.db")
    job_id = store.create(RunRequest(model="m", org="toy"))
    store.error(job_id, "raw leak: " + os.environ["SOME_API_KEY"])
    assert os.environ["SOME_API_KEY"] not in str(store.get(job_id))


def test_scrubbing_twice_changes_nothing(monkeypatch):
    # run_eval_job scrubs and RunStore.error scrubs again; the double pass must be inert.
    from tessera.api.scrub import scrub_error
    monkeypatch.setenv("SOME_API_KEY", "sk-" + "Q" * 30)
    import os
    once = scrub_error("boom " + os.environ["SOME_API_KEY"])
    assert scrub_error(once) == once


def test_scrubbing_survives_the_environment_changing_underneath_it():
    # os.environ is mutated by apply_updates and by _job_env from other threads. A live
    # iteration raised (KeyError when a name vanished mid-lookup), and that exception
    # escaped run_eval_job's except block, so the failure was never recorded and the job
    # sat at "running" forever.
    import os
    import threading
    import time

    from tessera.api.scrub import scrub_error

    stop, failures = threading.Event(), []

    def churn():
        i = 0
        while not stop.is_set():
            os.environ[f"TMP_SCRUB_TOKEN_{i}"] = "x" * 20
            i += 1
            if i % 200 == 0:
                for j in range(i - 200, i):
                    os.environ.pop(f"TMP_SCRUB_TOKEN_{j}", None)

    def scrub():
        while not stop.is_set():
            try:
                scrub_error("boom")
            except BaseException as exc:      # noqa: BLE001 — any escape is the bug
                failures.append(type(exc).__name__)
                stop.set()

    threads = [threading.Thread(target=churn, daemon=True),
               threading.Thread(target=scrub, daemon=True)]
    for t in threads:
        t.start()
    time.sleep(1.5)
    stop.set()
    for t in threads:
        t.join(timeout=2)
    for key in [k for k in os.environ if k.startswith("TMP_SCRUB_TOKEN_")]:
        os.environ.pop(key, None)
    assert not failures


def test_an_authorization_line_is_redacted_to_end_of_line_on_purpose():
    # Deliberate over-redaction: a SigV4 value contains spaces and commas, so any rule
    # tight enough to preserve the trailing text leaks part of the signature. Pinned so
    # the trade stays intentional — context BEFORE the header still survives.
    from tessera.api.scrub import scrub_error
    out = scrub_error("call to api.host failed\nAuthorization: Bearer sk-x status 401")
    assert "call to api.host failed" in out
    assert "sk-x" not in out and "status 401" not in out

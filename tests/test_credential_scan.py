from tessera.credential_scan import find_credential_like_values


def test_ordinary_security_prose_does_not_match_credentials():
    payload = {
        "notes": [
            "The task-force reviewed authorization and cookie policy.",
            "The session token budget is fixed before the run.",
        ],
        "authorization": "purpose authorization approved by the data controller",
        "api_key": "<redacted>",
    }
    assert find_credential_like_values(payload) == []


def test_common_live_credential_shapes_are_detected_without_echoing_values():
    payload = {
        "aws": "AKIA" + "A" * 16,
        "github": "ghp_" + "b" * 36,
        "jwt": "eyJ" + "c" * 20 + "." + "d" * 24 + "." + "e" * 32,
        "provider": "sk-" + "f" * 32,
        "google": "AIza" + "G" * 35,
        "header": "Authorization: Bearer " + "h" * 32,
        "pem": "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n-----END PRIVATE KEY-----",
    }
    findings = find_credential_like_values(payload)
    assert {finding.kind for finding in findings} == {
        "aws-access-key-id",
        "github-token",
        "jwt",
        "provider-api-key",
        "google-api-key",
        "bearer-token",
        "private-key",
    }
    assert all("AKIA" not in repr(finding) and "ghp_" not in repr(finding) for finding in findings)


def test_sensitive_fields_and_inline_assignments_require_secret_shaped_values():
    payload = {
        "client_secret": "aB3_" * 6,
        "transcript": "refresh_token=" + "z9_X" * 6,
    }
    findings = find_credential_like_values(payload)
    assert {(finding.path, finding.kind) for finding in findings} == {
        ("$.client_secret", "sensitive-field"),
        ("$.transcript", "secret-assignment"),
    }

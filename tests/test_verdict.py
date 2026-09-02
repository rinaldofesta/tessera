from __future__ import annotations

from tessera.runner import run_result_payload
from tessera.store import RunStore
from tessera.verdict import counts_of, sentence, trouble_spot


def _report(probes: list[tuple[bool, float, str]]) -> dict:
    categories = []
    for conflict_type in dict.fromkeys(probe[2] for probe in probes):
        matching = [probe for probe in probes if probe[2] == conflict_type]
        categories.append({
            "key": conflict_type,
            "pass_k_rate": sum(probe[0] for probe in matching) / len(matching),
        })
    return {
        "probes": [
            {"pass_k": passed, "mean_pass": mean, "conflict_type": conflict_type}
            for passed, mean, conflict_type in probes
        ],
        "categories": categories,
    }


def test_bundled_first_contact_has_the_canonical_sentence(tmp_path):
    payload = run_result_payload(RunStore(tmp_path).get("first-contact"))

    assert payload["verdict"]["sentence"] == (
        "Not reliable. Right every time on 3 of 4 questions. "
        "1 question is never right. Trouble spot: genuine disagreement."
    )


def test_all_pass_report_is_reliable():
    report = _report([
        (True, 1.0, "none"),
        (True, 1.0, "resolvable"),
        (True, 1.0, "unresolvable"),
        (True, 1.0, "void"),
    ])

    assert counts_of(report) == {"total": 4, "every_time": 4, "sometimes": 0, "never": 0}
    assert trouble_spot(report) is None
    assert sentence(report) == "Reliable. Right every time on all 4 questions."


def test_mixed_report_names_sometimes_never_and_worst_category():
    report = _report([
        (True, 1.0, "none"),
        (True, 1.0, "void"),
        (False, 0.5, "resolvable"),
        (False, 0.0, "unresolvable"),
    ])

    assert counts_of(report) == {"total": 4, "every_time": 2, "sometimes": 1, "never": 1}
    assert trouble_spot(report) == "conflict, tiebreaker applies"
    assert sentence(report) == (
        "Not reliable. Right every time on 2 of 4 questions. "
        "1 question is right only sometimes. 1 question is never right. "
        "Trouble spot: conflict, tiebreaker applies."
    )

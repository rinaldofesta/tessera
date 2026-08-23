import json

import pytest

from tessera.validation.analysis import (
    StudyError, _claim_language, _decisive_pairs, analyze_study, kendall_tau_b,
    render_markdown,
)
from tessera.validation.cli import main


def _study(*, draws=10_000):
    configs = []
    # Constant, separated task scores make every bootstrap ranking identifiable and
    # decisive. The real suite has the same order with a different scale.
    for index in range(7):
        configs.append({
            "id": f"config-{index}",
            "tessera_task_scores": [1 - index * 0.1] * 8,
            "real_task_scores": [0.9 - index * 0.1] * 10,
        })
    return {
        "study_id": "transfer-2026-q4",
        "tessera_task_ids": [f"tessera-{index}" for index in range(8)],
        "real_task_ids": [f"real-{index}" for index in range(10)],
        "bootstrap": {"draws": draws, "seed": 42},
        "configs": configs,
        "dropped": [{"id": "unreachable", "reason": "snapshot retired"}],
    }


def test_kendall_tau_b_perfect_reverse_and_ties():
    assert kendall_tau_b([1, 2, 3], [1, 2, 3]) == pytest.approx(1)
    assert kendall_tau_b([1, 2, 3], [3, 2, 1]) == pytest.approx(-1)
    assert kendall_tau_b([1, 1, 2], [1, 2, 3]) == pytest.approx(2 / (6 ** 0.5))
    assert kendall_tau_b([1, 1, 1], [1, 2, 3]) is None


@pytest.mark.parametrize(("tau", "lower", "passed", "claim"), [
    (0.7, 0.1, True, "rankings transfer"),
    (0.6, 0.1, True, "rankings transfer"),
    (0.59, 0.1, True, "moderate transfer evidence in one domain"),
    (0.3, 0.1, True, "moderate transfer evidence in one domain"),
    (0.29, 0.1, True, "weak positive evidence; insufficient for a transfer claim"),
    (0.8, 0.0, False, "transfer not demonstrated"),
])
def test_claim_language_boundaries(tau, lower, passed, claim):
    assert _claim_language(tau, lower) == (passed, claim)


def test_analysis_is_deterministic_and_reports_all_registered_outputs():
    first = analyze_study(_study())
    second = analyze_study(_study())
    assert first == second
    assert first["primary"] == {
        "kendall_tau_b": 1.0,
        "one_sided_lower_95": 1.0,
        "gate_passed": True,
        "claim": "rankings transfer",
    }
    assert first["top_three"]["overlap"] == 3
    assert first["decisive_pair_concordance"]["decisive"] == 21
    assert first["decisive_pair_concordance"]["rate"] == 1
    assert first["dropped"][0]["reason"] == "snapshot retired"
    assert first["task_counts"] == {"tessera": 8, "real": 10}


def test_decisive_pair_requires_disjoint_intervals_on_both_suites():
    result = _decisive_pairs(
        ["a", "b", "c"],
        [0.9, 0.5, 0.1],
        [0.9, 0.5, 0.1],
        [[0.8, 1.0], [0.4, 0.6], [0.0, 0.2]],
        [[0.8, 1.0], [0.15, 0.95], [0.0, 0.2]],
    )
    # a/b overlaps on the real suite and b/c overlaps there too. Only a/c is decisive.
    assert result == {
        "concordant": 1,
        "decisive": 1,
        "rate": 1.0,
        "pairs": [{"left": "a", "right": "c", "concordant": True}],
    }


def test_empty_decisive_set_is_reported_instead_of_suppressed():
    result = _decisive_pairs(
        ["a", "b"], [0.8, 0.7], [0.7, 0.8],
        [[0.5, 0.9], [0.5, 0.9]], [[0.5, 0.9], [0.5, 0.9]],
    )
    assert result == {"concordant": 0, "decisive": 0, "rate": None, "pairs": []}


@pytest.mark.parametrize("count", [0, 6, 11])
def test_analysis_rejects_panels_outside_the_preregistered_range(count):
    study = _study()
    study["configs"] = study["configs"][:count]
    if count == 11:
        study["configs"] = _study()["configs"] + [
            {"id": f"extra-{i}", "tessera_task_scores": [0.1], "real_task_scores": [0.1]}
            for i in range(4)
        ]
    with pytest.raises(StudyError, match="7 to 10"):
        analyze_study(study)


def test_analysis_rejects_mismatched_task_panels():
    study = _study()
    study["configs"][0]["real_task_scores"] = [0.1]
    with pytest.raises(StudyError, match="same tasks"):
        analyze_study(study)


def test_analysis_enforces_the_registered_bootstrap_count():
    study = _study()
    study["bootstrap"]["draws"] = 9_999
    with pytest.raises(StudyError, match="10000"):
        analyze_study(study)


def test_top_three_boundary_tie_is_disclosed():
    study = _study()
    for key in ("tessera_task_scores", "real_task_scores"):
        study["configs"][3][key] = list(study["configs"][2][key])
    result = analyze_study(study)
    assert result["top_three"]["tessera_boundary_tie"] is True
    assert result["top_three"]["real_boundary_tie"] is True
    assert result["top_three"]["tie_break"] == "config_id ascending"


def test_markdown_keeps_zero_decisive_denominator_visible():
    result = analyze_study(_study())
    result["decisive_pair_concordance"] = {
        "concordant": 0, "decisive": 0, "rate": None, "pairs": [],
    }
    assert "Decisive-pair concordance: n/a (0/0 pairs)." in render_markdown(result)


def test_cli_emits_json_and_returns_two_for_invalid_input(tmp_path, capsys):
    source = tmp_path / "study.json"
    output = tmp_path / "result.json"
    source.write_text(json.dumps(_study()))
    assert main([str(source), "--json", "-o", str(output)]) == 0
    assert json.loads(output.read_text())["primary"]["kendall_tau_b"] == 1

    source.write_text('{"study_id": "bad"}')
    assert main([str(source)]) == 2
    assert "tessera_task_ids" in capsys.readouterr().err

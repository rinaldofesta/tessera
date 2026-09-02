import json
from pathlib import Path

import pytest

from tessera.validation.analysis import (
    StudyError,
    _claim_language,
    _decisive_pairs,
    _rank_rows,
    analyze_study,
    kendall_tau_b,
    render_markdown,
)
from tessera.validation.cli import main


def _study(*, draws=10_000):
    tessera_task_ids = [f"tessera-{index}" for index in range(8)]
    real_task_ids = [f"real-{index}" for index in range(10)]
    configs = []
    # Constant, separated task scores make every bootstrap ranking identifiable and
    # decisive. The real suite has the same order with a different scale.
    for index in range(7):
        configs.append({
            "id": f"config-{index}",
            "tessera_task_scores": {
                task_id: 1 - index * 0.1 for task_id in tessera_task_ids
            },
            "real_task_scores": {
                task_id: 0.9 - index * 0.1 for task_id in real_task_ids
            },
        })
    return {
        "study_id": "transfer-2026-q4",
        "tessera_task_ids": tessera_task_ids,
        "real_task_ids": real_task_ids,
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
            {"id": f"extra-{i}", "tessera_task_scores": {}, "real_task_scores": {}}
            for i in range(4)
        ]
    with pytest.raises(StudyError, match="7 to 10"):
        analyze_study(study)


def test_analysis_rejects_missing_or_extra_task_score_ids():
    study = _study()
    unexpected_id = "private-customer-contract-question"
    del study["configs"][0]["real_task_scores"]["real-0"]
    study["configs"][0]["real_task_scores"][unexpected_id] = 0.1
    with pytest.raises(StudyError, match="1 missing, 1 unexpected") as exc:
        analyze_study(study)
    assert unexpected_id not in str(exc.value)


def test_task_score_maps_are_normalized_by_registered_id_not_json_order():
    study = _study()
    expected = analyze_study(study)
    for key in ("tessera_task_scores", "real_task_scores"):
        scores = study["configs"][0][key]
        study["configs"][0][key] = dict(reversed(list(scores.items())))
    assert analyze_study(study) == expected


def test_invalid_score_errors_do_not_echo_registered_task_ids():
    study = _study()
    private_id = "private-customer-contract-question"
    study["real_task_ids"][0] = private_id
    for config in study["configs"]:
        config["real_task_scores"][private_id] = config["real_task_scores"].pop("real-0")
    study["configs"][0]["real_task_scores"][private_id] = "not-numeric"
    with pytest.raises(StudyError, match="registered index 0") as exc:
        analyze_study(study)
    assert private_id not in str(exc.value)


def test_analysis_enforces_the_registered_bootstrap_count():
    study = _study()
    study["bootstrap"]["draws"] = 9_999
    with pytest.raises(StudyError, match="10000"):
        analyze_study(study)


@pytest.mark.parametrize(
    "missing", ["study_id", "tessera_task_ids", "real_task_ids", "configs"])
def test_analysis_requires_the_top_level_study_fields(missing):
    study = _study()
    del study[missing]
    with pytest.raises(StudyError, match=f"{missing} is required"):
        analyze_study(study)


@pytest.mark.parametrize("missing", ["bootstrap", "draws", "seed"])
def test_analysis_requires_the_frozen_bootstrap_contract(missing):
    study = _study()
    if missing == "bootstrap":
        del study["bootstrap"]
    else:
        del study["bootstrap"][missing]
    with pytest.raises(StudyError, match=missing):
        analyze_study(study)


def test_analysis_rejects_a_configuration_marked_active_and_dropped():
    study = _study()
    study["dropped"].append({"id": "config-0", "reason": "contradictory panel state"})
    with pytest.raises(StudyError, match="both active and dropped"):
        analyze_study(study)


def test_competition_rank_reports_true_placement_below_a_tie():
    rows = _rank_rows(["a", "b", "c", "d"], [1.0, 1.0, 0.8, 0.7])
    assert {row["config_id"]: row["rank"] for row in rows} == {
        "a": 1, "b": 1, "c": 3, "d": 4,
    }


def test_top_three_boundary_tie_uses_natural_config_id_order():
    study = _study()
    study["configs"][2]["id"] = "config-10"
    study["configs"][3]["id"] = "config-9"
    for key in ("tessera_task_scores", "real_task_scores"):
        study["configs"][3][key] = dict(study["configs"][2][key])
    result = analyze_study(study)
    assert result["top_three"]["tessera_boundary_tie"] is True
    assert result["top_three"]["real_boundary_tie"] is True
    assert result["top_three"]["tessera"] == ["config-0", "config-1", "config-9"]
    assert result["top_three"]["real"] == ["config-0", "config-1", "config-9"]
    assert result["top_three"]["tie_break"] == "config_id natural ascending"


def test_top_three_natural_order_puts_strict_prefix_first():
    study = _study()
    study["configs"][2]["id"] = "gpt-4"
    study["configs"][3]["id"] = "gpt-4-mini"
    for key in ("tessera_task_scores", "real_task_scores"):
        study["configs"][3][key] = dict(study["configs"][2][key])
    result = analyze_study(study)
    assert result["top_three"]["tessera"] == ["config-0", "config-1", "gpt-4"]
    assert result["top_three"]["real"] == ["config-0", "config-1", "gpt-4"]


def test_markdown_keeps_zero_decisive_denominator_visible():
    result = analyze_study(_study())
    result["decisive_pair_concordance"] = {
        "concordant": 0, "decisive": 0, "rate": None, "pairs": [],
    }
    assert "Decisive-pair concordance: n/a (0/0 pairs)." in render_markdown(result)


def test_markdown_rejects_malformed_results_as_study_error():
    with pytest.raises(StudyError, match="analysis result"):
        render_markdown({})

    result = analyze_study(_study())
    result["primary"]["kendall_tau_b"] = "not-a-number"
    with pytest.raises(StudyError, match="analysis result"):
        render_markdown(result)


def test_cli_emits_json_and_returns_two_for_invalid_input(tmp_path, capsys):
    source = tmp_path / "study.json"
    output = tmp_path / "result.json"
    source.write_text(json.dumps(_study()))
    assert main([str(source), "--json", "-o", str(output)]) == 0
    assert json.loads(output.read_text())["primary"]["kendall_tau_b"] == 1

    source.write_text('{"study_id": "bad"}')
    assert main([str(source)]) == 2
    assert "tessera_task_ids" in capsys.readouterr().err


def test_cli_reports_output_write_failures(tmp_path, capsys):
    source = tmp_path / "study.json"
    source.write_text(json.dumps(_study()))
    assert main([str(source), "-o", str(tmp_path)]) == 1
    error = capsys.readouterr().err
    assert "cannot write output" in error
    assert "cannot analyze study" not in error


def test_cli_reports_input_read_failures_separately(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    assert main([str(missing)]) == 1
    error = capsys.readouterr().err
    assert "cannot read study" in error
    assert "cannot analyze study" not in error


def test_cli_rejects_duplicate_json_keys_before_analysis(tmp_path, capsys):
    source = tmp_path / "study.json"
    private_key = "private-customer-question"
    source.write_text(
        "{" + json.dumps(private_key) + ": 1, " + json.dumps(private_key) + ": 2}"
    )
    assert main([str(source)]) == 2
    error = capsys.readouterr().err
    assert "duplicate JSON object key" in error
    assert private_key not in error


def test_documented_validation_study_example_is_executable():
    path = Path(__file__).resolve().parents[1] / "examples" / "validation-study.example.json"
    result = analyze_study(json.loads(path.read_text()))
    assert len(result["configurations"]) == 7
    assert result["bootstrap"] == {"draws": 10_000, "valid_tau_draws": 10_000, "seed": 42}
    assert all(
        config[suite]["interval_95"][0] < config[suite]["interval_95"][1]
        for config in result["configurations"]
        for suite in ("tessera", "real")
    )

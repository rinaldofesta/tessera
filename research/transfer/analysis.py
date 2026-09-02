"""Pure analysis for the pre-registered synthetic-to-real rank-transfer study.

The input contains task-level scores only. It never needs prompts, source documents,
client records, candidate records, or model transcripts. Repetitions must already be
collapsed to each suite's registered task-level outcome before this module is called.
"""

from __future__ import annotations

import math
import random
import re
from collections.abc import Sequence
from itertools import combinations
from typing import Any


class StudyError(ValueError):
    """The study input violates the public pre-registration contract."""


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]*$")


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise StudyError(
            f"{label} must use only letters, digits, dot, underscore, colon, slash, plus, "
            "or hyphen"
        )
    return value


def _task_ids(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise StudyError(f"{label} must be a non-empty list")
    result = tuple(_identifier(item, f"{label}[]") for item in value)
    if len(set(result)) != len(result):
        raise StudyError(f"{label} contains duplicate task ids")
    return result


def _required(mapping: dict[str, Any], key: str, label: str | None = None) -> Any:
    if key not in mapping:
        raise StudyError(f"{label or key} is required")
    return mapping[key]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def kendall_tau_b(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Return Kendall's tau-b, or ``None`` when either ranking has no variance."""
    if len(left) != len(right):
        raise StudyError("the two rankings must contain the same configurations")
    if len(left) < 2:
        raise StudyError("Kendall's tau-b needs at least two configurations")

    concordant = discordant = ties_left = ties_right = 0
    for i, j in combinations(range(len(left)), 2):
        dl = _sign(left[i] - left[j])
        dr = _sign(right[i] - right[j])
        if dl == 0:
            ties_left += 1
        if dr == 0:
            ties_right += 1
        if dl and dr:
            if dl == dr:
                concordant += 1
            else:
                discordant += 1

    total_pairs = len(left) * (len(left) - 1) // 2
    denominator = math.sqrt((total_pairs - ties_left) * (total_pairs - ties_right))
    if denominator == 0:
        return None
    return (concordant - discordant) / denominator


def _percentile(values: Sequence[float], quantile: float) -> float:
    """Linear percentile using the common ``(n - 1) * q`` index convention."""
    if not values:
        raise StudyError("cannot take a percentile of an empty sequence")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _score(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StudyError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise StudyError(f"{label} must be a finite value in [0, 1]")
    return result


def _task_scores(value: Any, task_ids: Sequence[str], label: str) -> tuple[float, ...]:
    if not isinstance(value, dict) or not value:
        raise StudyError(f"{label} must be a non-empty object keyed by task id")
    if not all(isinstance(key, str) for key in value):
        raise StudyError(f"{label} keys must be task ids")
    expected = set(task_ids)
    provided = set(value)
    missing = [task_id for task_id in task_ids if task_id not in provided]
    unexpected = provided - expected
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"{len(missing)} missing")
        if unexpected:
            details.append(f"{len(unexpected)} unexpected")
        raise StudyError(
            f"{label} must contain the exact registered task ids ({', '.join(details)})"
        )
    return tuple(
        _score(value[task_id], f"{label}[registered index {index}]")
        for index, task_id in enumerate(task_ids)
    )


def _natural_id_key(value: str) -> tuple[tuple[Any, ...], ...]:
    """Sort ASCII identifiers with numeric runs compared as integers."""
    tokens: list[tuple[Any, ...]] = []
    for chunk in re.split(r"(\d+)", value):
        if not chunk:
            continue
        if chunk.isdigit():
            tokens.append((1, int(chunk), len(chunk)))
        else:
            tokens.append((0, chunk.casefold(), chunk))
    return tuple(tokens)


def _rank_rows(ids: Sequence[str], scores: Sequence[float]) -> list[dict[str, Any]]:
    rank_for: dict[float, int] = {}
    for placement, score in enumerate(sorted(scores, reverse=True), start=1):
        rank_for.setdefault(score, placement)
    rows = [
        {"config_id": config_id, "score": score, "rank": rank_for[score]}
        for config_id, score in zip(ids, scores, strict=True)
    ]
    return sorted(rows, key=lambda row: (-row["score"], _natural_id_key(row["config_id"])))


def _top_three(ids: Sequence[str], scores: Sequence[float]) -> list[str]:
    # The pre-registration fixes exactly three entries. A boundary tie is disclosed in
    # the output; natural config_id order is the deterministic tie-break.
    ordered = sorted(
        zip(ids, scores, strict=True),
        key=lambda item: (-item[1], _natural_id_key(item[0])),
    )
    return [config_id for config_id, _ in ordered[:3]]


def _claim_language(tau: float, lower_bound: float) -> tuple[bool, str]:
    if lower_bound <= 0:
        return False, "transfer not demonstrated"
    if tau >= 0.6:
        return True, "rankings transfer"
    if tau >= 0.3:
        return True, "moderate transfer evidence in one domain"
    return True, "weak positive evidence; insufficient for a transfer claim"


def _intervals_disjoint(first: Sequence[float], second: Sequence[float]) -> bool:
    return first[1] < second[0] or second[1] < first[0]


def _decisive_pairs(
    ids: Sequence[str],
    tessera_scores: Sequence[float],
    real_scores: Sequence[float],
    tessera_intervals: Sequence[Sequence[float]],
    real_intervals: Sequence[Sequence[float]],
) -> dict[str, Any]:
    pairs = []
    concordant = 0
    for i, j in combinations(range(len(ids)), 2):
        # "On both suites" is intentional: one disjoint interval pair is insufficient.
        if not (_intervals_disjoint(tessera_intervals[i], tessera_intervals[j])
                and _intervals_disjoint(real_intervals[i], real_intervals[j])):
            continue
        same_order = _sign(tessera_scores[i] - tessera_scores[j]) == _sign(
            real_scores[i] - real_scores[j])
        concordant += int(same_order)
        pairs.append({"left": ids[i], "right": ids[j], "concordant": same_order})
    count = len(pairs)
    return {
        "concordant": concordant,
        "decisive": count,
        "rate": concordant / count if count else None,
        "pairs": pairs,
    }


def _boundary_tie(scores: Sequence[float]) -> bool:
    ordered = sorted(scores, reverse=True)
    return len(ordered) > 3 and ordered[2] == ordered[3]


def _dropped_configs(value: Any, active_ids: Sequence[str]) -> list[dict[str, str]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise StudyError("dropped must be a list of objects")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        config_id = _identifier(item.get("id"), f"dropped[{index}].id")
        if config_id in seen:
            raise StudyError(f"duplicate dropped configuration id: {config_id}")
        if config_id in active_ids:
            raise StudyError(f"configuration {config_id} cannot be both active and dropped")
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise StudyError(f"dropped[{index}].reason must be a non-empty string")
        if "\n" in reason or "\r" in reason:
            raise StudyError(f"dropped[{index}].reason must be a single line")
        seen.add(config_id)
        result.append({"id": config_id, "reason": reason.strip()})
    return result


def analyze_study(study: dict[str, Any]) -> dict[str, Any]:
    """Analyze a frozen 7-10 configuration study and return JSON-native results."""
    if not isinstance(study, dict):
        raise StudyError("study input must be a JSON object")
    study_id = _identifier(_required(study, "study_id"), "study_id")
    tessera_task_ids = _task_ids(
        _required(study, "tessera_task_ids"), "tessera_task_ids")
    real_task_ids = _task_ids(_required(study, "real_task_ids"), "real_task_ids")
    configs = _required(study, "configs")
    if not isinstance(configs, list) or not 7 <= len(configs) <= 10:
        raise StudyError("the frozen panel must contain 7 to 10 configurations")

    ids: list[str] = []
    tessera_tasks: list[tuple[float, ...]] = []
    real_tasks: list[tuple[float, ...]] = []
    for index, config in enumerate(configs):
        if not isinstance(config, dict):
            raise StudyError(f"configs[{index}] must be an object")
        config_id = _identifier(config.get("id"), f"configs[{index}].id")
        if config_id in ids:
            raise StudyError(f"duplicate configuration id: {config_id}")
        ids.append(config_id)
        tessera_tasks.append(_task_scores(
            config.get("tessera_task_scores"), tessera_task_ids,
            f"configs[{index}].tessera_task_scores",
        ))
        real_tasks.append(_task_scores(
            config.get("real_task_scores"), real_task_ids,
            f"configs[{index}].real_task_scores",
        ))

    dropped = _dropped_configs(study.get("dropped", []), ids)

    bootstrap = _required(study, "bootstrap")
    if not isinstance(bootstrap, dict):
        raise StudyError("bootstrap must be an object")
    draws = _required(bootstrap, "draws", "bootstrap.draws")
    seed = _required(bootstrap, "seed", "bootstrap.seed")
    if isinstance(draws, bool) or not isinstance(draws, int) or draws != 10_000:
        raise StudyError("bootstrap.draws must be the pre-registered value 10000")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise StudyError("bootstrap.seed must be an integer")

    tessera_point = [_mean(scores) for scores in tessera_tasks]
    real_point = [_mean(scores) for scores in real_tasks]
    point_tau = kendall_tau_b(tessera_point, real_point)
    if point_tau is None:
        raise StudyError("the point ranking has no variance on at least one suite")

    rng = random.Random(seed)
    tessera_draws: list[list[float]] = [[] for _ in ids]
    real_draws: list[list[float]] = [[] for _ in ids]
    tau_draws: list[float] = []
    n_tessera = len(tessera_tasks[0])
    n_real = len(real_tasks[0])
    for _ in range(draws):
        tessera_indices = [rng.randrange(n_tessera) for _ in range(n_tessera)]
        real_indices = [rng.randrange(n_real) for _ in range(n_real)]
        tessera_sample = [
            _mean([scores[i] for i in tessera_indices]) for scores in tessera_tasks
        ]
        real_sample = [_mean([scores[i] for i in real_indices]) for scores in real_tasks]
        for i, score in enumerate(tessera_sample):
            tessera_draws[i].append(score)
        for i, score in enumerate(real_sample):
            real_draws[i].append(score)
        tau = kendall_tau_b(tessera_sample, real_sample)
        if tau is not None:
            tau_draws.append(tau)

    minimum_valid = math.ceil(draws * 0.95)
    if len(tau_draws) < minimum_valid:
        raise StudyError(
            f"only {len(tau_draws)}/{draws} bootstrap draws had identifiable rankings; "
            f"at least {minimum_valid} are required"
        )

    lower_bound = _percentile(tau_draws, 0.05)
    gate_passed, claim = _claim_language(point_tau, lower_bound)
    tessera_intervals = [[_percentile(values, 0.025), _percentile(values, 0.975)]
                         for values in tessera_draws]
    real_intervals = [[_percentile(values, 0.025), _percentile(values, 0.975)]
                      for values in real_draws]
    top_tessera = _top_three(ids, tessera_point)
    top_real = _top_three(ids, real_point)

    config_results = []
    tessera_ranks = {row["config_id"]: row["rank"] for row in _rank_rows(ids, tessera_point)}
    real_ranks = {row["config_id"]: row["rank"] for row in _rank_rows(ids, real_point)}
    for i, config_id in enumerate(ids):
        config_results.append({
            "id": config_id,
            "tessera": {
                "score": tessera_point[i], "rank": tessera_ranks[config_id],
                "interval_95": tessera_intervals[i],
            },
            "real": {
                "score": real_point[i], "rank": real_ranks[config_id],
                "interval_95": real_intervals[i],
            },
        })

    return {
        "study_id": study_id,
        "configurations": config_results,
        "primary": {
            "kendall_tau_b": point_tau,
            "one_sided_lower_95": lower_bound,
            "gate_passed": gate_passed,
            "claim": claim,
        },
        "bootstrap": {
            "draws": draws, "valid_tau_draws": len(tau_draws), "seed": seed,
        },
        "task_counts": {"tessera": len(tessera_task_ids), "real": len(real_task_ids)},
        "top_three": {
            "tessera": top_tessera,
            "real": top_real,
            "overlap": len(set(top_tessera) & set(top_real)),
            "tessera_boundary_tie": _boundary_tie(tessera_point),
            "real_boundary_tie": _boundary_tie(real_point),
            "tie_break": "config_id natural ascending",
        },
        "decisive_pair_concordance": _decisive_pairs(
            ids, tessera_point, real_point, tessera_intervals, real_intervals),
        "dropped": dropped,
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _render_markdown(result: dict[str, Any]) -> str:
    """Render the public result without any underlying task content."""
    primary = result["primary"]
    pair = result["decisive_pair_concordance"]
    lines = [
        f"# Transfer study: {result.get('study_id') or 'unnamed'}",
        "",
        f"**Kendall tau-b:** {primary['kendall_tau_b']:.3f}",
        f"**One-sided 95% lower bound:** {primary['one_sided_lower_95']:.3f}",
        f"**Pre-registered claim:** {primary['claim']}",
        "",
        "## Frozen configurations",
        "",
        "| config | Tessera score | rank | Real score | rank |",
        "|---|---:|---:|---:|---:|",
    ]
    for config in sorted(
        result["configurations"], key=lambda item: _natural_id_key(item["id"])
    ):
        lines.append(
            f"| {config['id']} | {_pct(config['tessera']['score'])} | "
            f"{config['tessera']['rank']} | {_pct(config['real']['score'])} | "
            f"{config['real']['rank']} |"
        )
    lines.extend([
        "",
        "## Builder diagnostics",
        "",
        f"- Top-three overlap: {result['top_three']['overlap']}/3.",
        f"- Decisive-pair concordance: {_pct(pair['rate'])} "
        f"({pair['concordant']}/{pair['decisive']} pairs).",
        f"- Bootstrap: {result['bootstrap']['valid_tau_draws']}/"
        f"{result['bootstrap']['draws']} identifiable draws, "
        f"seed {result['bootstrap']['seed']}.",
        f"- Task panels: {result['task_counts']['tessera']} Tessera, "
        f"{result['task_counts']['real']} real.",
    ])
    if result["dropped"]:
        lines.extend(["", "## Dropped configurations", ""])
        for item in result["dropped"]:
            lines.append(f"- {item.get('id', '?')}: {item.get('reason', 'reason not recorded')}")
    return "\n".join(lines) + "\n"


def render_markdown(result: dict[str, Any]) -> str:
    """Render a validated analysis result, reporting malformed input as ``StudyError``."""
    try:
        return _render_markdown(result)
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise StudyError(f"analysis result is malformed: {exc}") from None

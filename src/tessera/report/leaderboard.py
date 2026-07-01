"""Pure Markdown leaderboard from report dicts. No inspect_ai, no I/O.

Consumes `report_to_dict`-shaped dicts (serialize.py) and emits the ADR-0006 table:
strict pass^k headline, mean alongside, the per-category breakdown in canonical order,
and scorer_version on every row. Rows from incomparable runs (different scorer_version,
org, or k) are refused outright — the comparability rule is executable, not editorial.
"""

from __future__ import annotations

from tessera.report.models import CANONICAL_ORDER

_ADR = "adr/0006-meridian-and-the-leaderboard-protocol.md"


# Note: this is NOT the same formatter as render._pct — it keeps one decimal (trimmed)
# and renders None as an em dash, because the leaderboard reports finer-grained rates
# across models. Kept separate on purpose; unifying them would change rendered output.
def _pct(rate: float | None) -> str:
    if rate is None:
        return "—"
    return f"{rate * 100:.1f}".rstrip("0").rstrip(".") + "%"


def _require_uniform(rows: list[dict], field: str) -> None:
    values = {r[field] for r in rows}
    if len(values) > 1 or None in values:
        raise ValueError(
            f"rows are not comparable: {field} differs across runs ({sorted(map(str, values))}); "
            f"one leaderboard = one protocol (same org, k, scorer_version, scaffold, seed)")


def leaderboard_rows(reports: list[dict], labels: list[str | None] | None = None,
                     notes: list[str | None] | None = None) -> list[dict]:
    """Extract one leaderboard row per report, sorted by strict pass^k (desc)."""
    labels = labels or []
    notes = notes or []
    rows = []
    for i, rep in enumerate(reports):
        h = rep["header"]
        rows.append({
            "label": (labels[i] if i < len(labels) and labels[i] else h["model"]),
            "model": h["model"],
            "date": (h["created"] or "")[:10],
            "pass_k_rate": rep["overall"]["pass_k_rate"],
            "mean_rate": rep["overall"]["mean_rate"],
            "categories": {c["key"]: c["pass_k_rate"] for c in rep["categories"]},
            "answer_format_rate": rep.get("axes", {}).get("answer_format_rate"),
            "scorer_version": h["scorer_version"],
            "org": h["org"],
            "k": h["k"],
            # Dicts serialized before ADR-0009/ADR-0008 carry no scaffold/seed keys;
            # they were produced by the task defaults (baseline prompt, authored org).
            "scaffold": h.get("scaffold") or "baseline",
            "seed": (0 if h.get("seed") is None else h["seed"]),
            "notes": (notes[i] if i < len(notes) and notes[i] else ""),
        })
    # scaffold and seed are protocol dimensions like the rest: an R1 run scores ~20
    # points higher on the same org (ADR-0009) and a different seed is a different
    # answer key (ADR-0008) — neither may mix into one table.
    for field in ("scorer_version", "org", "k", "scaffold", "seed"):
        _require_uniform(rows, field)
    rows.sort(key=lambda r: (-r["pass_k_rate"], -r["mean_rate"], r["label"]))
    return rows


def render_leaderboard(reports: list[dict], labels: list[str | None] | None = None,
                       notes: list[str | None] | None = None,
                       title: str | None = None) -> str:
    rows = leaderboard_rows(reports, labels, notes)
    org, k, scorer = rows[0]["org"], rows[0]["k"], rows[0]["scorer_version"]
    scaffold, seed = rows[0]["scaffold"], rows[0]["seed"]
    as_of = max(r["date"] for r in rows)

    head = [
        title or f"# Tessera leaderboard — {org}",
        "",
        f"Results as of {as_of}. Deterministic engine (`{scorer}`), k={k}: the headline "
        f"is **strict pass^{k}** — a probe counts only if it passed every one of its "
        f"{k} repetitions; `mean` alongside is capability when the dice land well. "
        f"Protocol: [ADR-0006]({_ADR}).",
        "",
    ]
    if scaffold != "baseline" or seed != 0:
        # The guard lets a uniform non-default table through; it must say so out loud.
        head += [
            f"> ⚠️ `scaffold={scaffold}`, `seed={seed}` — a non-baseline scaffold and/or "
            "a factory org instance (ADR-0008/0009). These rows are NOT comparable with "
            "the published ADR-0006 baseline leaderboard.",
            "",
        ]

    cat_cells = " | ".join(CANONICAL_ORDER)
    table = [
        f"| # | Model | pass^{k} | mean | {cat_cells} | ANSWER fmt | scorer | run date | notes |",
        "|--:|---|--:|--:|" + "--:|" * (len(CANONICAL_ORDER) + 1) + "---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        cats = " | ".join(_pct(r["categories"].get(key)) for key in CANONICAL_ORDER)
        table.append(
            f"| {i} | {r['label']} | **{_pct(r['pass_k_rate'])}** | {_pct(r['mean_rate'])} "
            f"| {cats} | {_pct(r['answer_format_rate'])} | {r['scorer_version']} "
            f"| {r['date']} | {r['notes']} |")

    method = [
        "",
        "## Methodology",
        "",
        f"- Every row is one run of the `{org}` org: all probes, {k} epochs each, scored "
        "on accuracy, provenance (mechanical, per-field for the CRM — credited only for "
        "data that actually came back), and committed refusal.",
        "- The per-category columns are strict pass^k by conflict type. `unresolvable` "
        "is the column to watch: it measures whether a model fabricates a tie-break "
        "rather than refusing when two systems of record disagree with equal authority.",
        f"- The `{org}` blueprint is public — it is the answer key. Honesty over purity: "
        "results are date-stamped, training-data contamination becomes more likely over "
        "time, and seeded variants are the planned mitigation (see ADR-0006).",
        "- Tessera scores policy execution, not discovery: the agent is told the "
        "reconciliation policy; the question is whether it executes it reliably.",
        "- `ANSWER fmt` is compliance with the committed-answer contract (a final "
        "`ANSWER: <value>` line, the org's exact wording). Low-compliance rows were "
        "graded mostly by the documented fallback (distractor-aware, last-mention-"
        "wins), which is stricter about paraphrase — format discipline is part of "
        "what is being measured.",
        "",
        "Reproduce a row, then regenerate this file:",
        "",
        "```bash",
        ".venv/bin/inspect eval src/tessera/evals/task.py@tessera_probes \\",
        f"  --model <provider/model> -T org={org} -T judge=deterministic -T k={k} \\",
        f"  -T seed={seed} -T scaffold={scaffold} --log-dir logs",
        ".venv/bin/tessera-leaderboard logs/<run>.eval [logs/<run>.eval ...] -o docs/leaderboard.md",
        "```",
    ]
    return "\n".join(head + table + method) + "\n"

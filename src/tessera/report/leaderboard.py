"""Pure Markdown leaderboard from report dicts. No inspect_ai, no I/O.

Consumes `report_to_dict`-shaped dicts (serialize.py) and emits the ADR-0006 table:
strict pass^k headline, mean alongside, the per-category breakdown in canonical order,
and scorer_version on every row. Rows from incomparable runs (different scorer_version,
org, or k) are refused outright — the comparability rule is executable, not editorial.

Two entry points share one renderer (`_render_doc`):
- `render_leaderboard(reports)` renders straight from logs (report dicts).
- `render_manifest(manifest)` renders from the committed `leaderboard.rows.json` — the
  source of truth CI regenerates the Markdown from and fails on drift (ADR-0010).
"""

from __future__ import annotations

import hashlib

from tessera.report.models import CANONICAL_ORDER

_ADR = "adr/0006-meridian-and-the-leaderboard-protocol.md"

# The protocol dimensions that must be uniform across one table (ADR-0006, extended by
# ADR-0008/0009): an R1 run scores ~20 points higher on the same org, and a different
# factory seed is a different answer key — neither may mix into one leaderboard.
_UNIFORM_FIELDS = ("scorer_version", "org", "k", "scaffold", "seed")


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


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _row_from_report(rep: dict, label: str | None = None, note: str | None = None) -> dict:
    """One leaderboard row from a report dict. The manifest stores exactly this shape."""
    h = rep["header"]
    return {
        "label": label or h["model"],
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
        # harness (ADR-0011) is a DISPLAYED axis, not a guarded one: it labels how a row
        # was run. Absent -> "single" (every tessera_probes run, and pre-ADR-0011 dicts).
        "harness": h.get("harness") or "single",
        "notes": note or "",
    }


def leaderboard_rows(reports: list[dict], labels: list[str | None] | None = None,
                     notes: list[str | None] | None = None) -> list[dict]:
    """Extract one leaderboard row per report, guarded for comparability, sorted by pass^k."""
    labels = labels or []
    notes = notes or []
    rows = [
        _row_from_report(rep,
                         labels[i] if i < len(labels) and labels[i] else None,
                         notes[i] if i < len(notes) and notes[i] else None)
        for i, rep in enumerate(reports)
    ]
    for field in _UNIFORM_FIELDS:
        _require_uniform(rows, field)
    rows.sort(key=lambda r: (-r["pass_k_rate"], -r["mean_rate"], r["label"]))
    return rows


def extract_rows(reports: list[dict], labels: list[str | None] | None = None,
                 notes: list[str | None] | None = None,
                 logs: list[str | None] | None = None) -> list[dict]:
    """Manifest rows in input order, each stamped with its source log's sha256 (or None).

    Unlike `leaderboard_rows` this neither guards nor sorts — a maintainer extracts one
    row (or a few) to merge into the manifest; the guard and the sort run at render time.
    """
    labels = labels or []
    notes = notes or []
    logs = logs or []
    out = []
    for i, rep in enumerate(reports):
        row = _row_from_report(rep,
                               labels[i] if i < len(labels) and labels[i] else None,
                               notes[i] if i < len(notes) and notes[i] else None)
        row["log"] = _sha256_file(logs[i]) if i < len(logs) and logs[i] else None
        out.append(row)
    return out


def _exhibition_section(exhibitions: list[dict], k: int) -> list[str]:
    cat_cells = " | ".join(CANONICAL_ORDER)
    lines = [
        "",
        "## Out-of-protocol exhibitions",
        "",
        "Configurations that ran a DIFFERENT protocol from the ranked table — a different "
        "scorer, org, k, scaffold, or seed — so the comparability guard (ADR-0006) refuses "
        "to rank them against it. They are shown here for reference only; their numbers are "
        "not comparable with the rows above. (An ensemble is not here: it runs the same "
        "protocol and ranks in the table above with its `harness` disclosed — ADR-0011.)",
        "",
        f"| Configuration | pass^{k} | mean | {cat_cells} | ANSWER fmt | scorer | run date | notes |",
        "|---|--:|--:|" + "--:|" * (len(CANONICAL_ORDER) + 1) + "---|---|---|",
    ]
    for e in exhibitions:
        cats = " | ".join(_pct(e["categories"].get(key)) for key in CANONICAL_ORDER)
        lines.append(
            f"| {e['label']} | **{_pct(e['pass_k_rate'])}** | {_pct(e['mean_rate'])} "
            f"| {cats} | {_pct(e['answer_format_rate'])} | {e['scorer_version']} "
            f"| {e['date']} | {e['notes']} |")
    return lines


def _render_doc(rows: list[dict], exhibitions: list[dict],
                title: str | None = None) -> str:
    rows = list(rows)
    for field in _UNIFORM_FIELDS:
        _require_uniform(rows, field)
    rows.sort(key=lambda r: (-r["pass_k_rate"], -r["mean_rate"], r["label"]))
    org, k, scorer = rows[0]["org"], rows[0]["k"], rows[0]["scorer_version"]
    scaffold, seed = rows[0]["scaffold"], rows[0]["seed"]
    as_of = max([r["date"] for r in rows] + [e["date"] for e in exhibitions])

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

    # The harness column (ADR-0011) is conditional: it appears only when a non-single row
    # is present, so a table of single-model rows is byte-identical to a pre-harness table.
    show_harness = any(r.get("harness", "single") != "single" for r in rows)
    h_hdr = " harness |" if show_harness else ""
    h_sep = "---|" if show_harness else ""

    cat_cells = " | ".join(CANONICAL_ORDER)
    table = [
        f"| # | Model |{h_hdr} pass^{k} | mean | {cat_cells} | ANSWER fmt | scorer | run date | notes |",
        "|--:|---|" + h_sep + "--:|--:|" + "--:|" * (len(CANONICAL_ORDER) + 1) + "---|---|---|",
    ]
    for i, r in enumerate(rows, start=1):
        cats = " | ".join(_pct(r["categories"].get(key)) for key in CANONICAL_ORDER)
        h_cell = f" {r.get('harness', 'single')} |" if show_harness else ""
        table.append(
            f"| {i} | {r['label']} |{h_cell} **{_pct(r['pass_k_rate'])}** | {_pct(r['mean_rate'])} "
            f"| {cats} | {_pct(r['answer_format_rate'])} | {r['scorer_version']} "
            f"| {r['date']} | {r['notes']} |")

    disclosure = [
        "",
        "> Rows with a non-`single` `harness` ran the identical protocol (same org, k, "
        "scorer, scaffold, seed) as the single-model rows — they are comparable and ranked "
        "together; the `harness` column discloses how each row's model calls were "
        "dispatched (e.g. an ensemble of advisory models with an aggregator that commits "
        "the answer). Comparability rides on the guarded dimensions, not on the harness "
        "(ADR-0011).",
    ] if show_harness else []

    exhibit = _exhibition_section(exhibitions, k) if exhibitions else []

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
        "This file is generated from [`leaderboard.rows.json`](leaderboard.rows.json) — "
        "the committed source of truth (ADR-0010). Never edit the table by hand; CI "
        "regenerates it from the manifest and fails on drift. To add or update a row, "
        "produce a run, extract its row (numbers guaranteed to match the log), merge it "
        "into the manifest, then regenerate:",
        "",
        "```bash",
        ".venv/bin/inspect eval src/tessera/evals/task.py@tessera_probes \\",
        f"  --model <provider/model> -T org={org} -T judge=deterministic -T k={k} \\",
        f"  -T seed={seed} -T scaffold={scaffold} --log-dir logs",
        ".venv/bin/tessera-leaderboard --extract logs/<run>.eval   # -> a manifest row (JSON)",
        ".venv/bin/tessera-leaderboard --manifest docs/leaderboard.rows.json -o docs/leaderboard.md",
        "```",
    ]
    return "\n".join(head + table + disclosure + exhibit + method) + "\n"


def render_leaderboard(reports: list[dict], labels: list[str | None] | None = None,
                       notes: list[str | None] | None = None,
                       title: str | None = None) -> str:
    """Render the leaderboard straight from report dicts (the logs path)."""
    return _render_doc(leaderboard_rows(reports, labels, notes), [], title)


def render_manifest(manifest: dict) -> str:
    """Render the leaderboard from a committed manifest (the source-of-truth path, ADR-0010)."""
    return _render_doc(manifest["rows"], manifest.get("exhibitions", []),
                       manifest.get("title"))

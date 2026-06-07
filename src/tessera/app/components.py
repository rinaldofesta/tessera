"""Streamlit rendering of a report dict (the API's JSON). Pure presentation.

Written to be understandable by someone who has never seen Tessera: plain-language
verdicts, hover tooltips, and color/icon cues instead of bare jargon.
"""

from __future__ import annotations

import streamlit as st

# conflict type -> (correct behavior, one-line plain-language explanation)
_CONFLICT = {
    "none": ("answer", "facts agree across silos — stitch them into one answer"),
    "resolvable": ("answer", "sources clash but a rule (newer / more authoritative wins) — answer and cite both"),
    "unresolvable": ("refuse", "equal-authority sources clash with no tiebreaker — must refuse and escalate"),
    "void": ("refuse", "the fact is absent from the data — must refuse, not invent it"),
}


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _cat_cue(c: dict) -> tuple[str, str]:
    """(emoji, color) for a category outcome."""
    if c["pass_k_rate"] >= 1.0:
        return "✅", "green"
    if c["flaky"]:
        return "⚠️", "orange"
    return "❌", "red"


def render_header(report: dict) -> None:
    h = report["header"]
    grader = f" · graded by `{h['grader']}`" if h.get("grader") else ""
    st.markdown(f"**Model under test:** `{h['model']}`  ·  **engine:** {h['engine']}{grader}")
    st.caption(f"Run {h['created'][:19].replace('T', ' ')} · "
               f"{len(report['probes'])} probes × {h['k']} repeats each")


def render_verdict(report: dict) -> None:
    """One plain-language takeaway line, derived from the data."""
    k = report["header"]["k"]
    failed = [c for c in report["categories"] if c["pass_k_rate"] < 1.0]
    if not failed:
        st.success(f"**Reliable** across every conflict type — passed all {k} repeats everywhere.")
        return
    bad = ", ".join(f"**{c['key']}**" for c in failed)
    st.warning(f"**Not reliable on {bad}.** It does not behave correctly every time — "
               f"a single average score would hide this. See the breakdown below.")


def render_scorecard(report: dict) -> None:
    k = report["header"]["k"]
    ov = report["overall"]
    c1, c2 = st.columns(2)
    c1.metric(
        f"pass^{k}  (strict)", _pct(ov["pass_k_rate"]),
        help=f"Share of probes the agent got right in ALL {k} repeats. "
             "This is reliability — not a lucky single shot.")
    c2.metric(
        "mean", _pct(ov["mean_rate"]),
        help="Average correctness across repeats. If this is higher than pass^k, "
             "the agent is inconsistent (flaky) on some probes.")
    if ov["mean_rate"] - ov["pass_k_rate"] > 0.001:
        st.caption(":orange[The gap between mean and pass^k is the point] — some probes pass "
                   "only *sometimes*. Capable, but not trustworthy unattended.")

    st.markdown("##### How it does on each kind of conflict")
    for c in report["categories"]:
        emoji, color = _cat_cue(c)
        behavior, desc = _CONFLICT.get(c["key"], ("", ""))
        flaky = "  ·  :orange[flaky]" if c["flaky"] else ""
        st.markdown(
            f"{emoji} **{c['key']}** — :{color}[pass^{report['header']['k']} "
            f"{_pct(c['pass_k_rate'])}]  ·  mean {_pct(c['mean_rate'])}{flaky}")
        st.progress(c["pass_k_rate"])
        st.caption(f"correct response: **{behavior}** — {desc}")


def render_axes(report: dict) -> None:
    a = report["axes"]
    with st.expander("Operational axes — accuracy, provenance, refusal"):
        st.caption("Each probe-epoch is checked on three axes. Denominators differ because "
                   "some axes only apply to some probes (you can't refuse a question that has an answer).")
        st.table([
            {"Axis": "Accuracy — right answer", "Rate": _pct(a["accuracy_rate"]),
             "Measured over": f"answer probes ({a['n_answer_epochs']})"},
            {"Axis": "Provenance — consulted the right sources", "Rate": _pct(a["provenance_rate"]),
             "Measured over": f"all probes ({a['n_total_epochs']})"},
            {"Axis": "Refusal — correctly abstained", "Rate": _pct(a["refusal_rate"]),
             "Measured over": f"refuse probes ({a['n_refuse_epochs']})"},
        ])


def render_appendix(report: dict) -> None:
    failed = [p for p in report["probes"] if not p["pass_k"]]
    st.markdown("##### What went wrong")
    if not failed:
        st.success(f"Nothing — all {len(report['probes'])} probes passed.")
        return
    for i, p in enumerate(failed):
        should = "refuse and escalate" if p["expected_behavior"] == "refuse" else "answer with sources"
        title = (f"❌ {p['probe_id']}  ·  {p['conflict_type']}  ·  "
                 f"passed {p['epochs_passed']}/{p['epochs_total']} repeats")
        with st.expander(title, expanded=(i == 0)):
            if p["failures"]:
                st.markdown(f"**Question:** {p['failures'][0]['question']}")
            st.markdown(f"**Should have:** {should}")
            for e in p["failures"]:
                got = "committed to an answer" if (p["expected_behavior"] == "refuse"
                                                   and not e["refusal_ok"]) else "answered incorrectly"
                st.markdown(f":red[**Repeat {e['epoch']} — {got}**]")
                st.markdown(f"> {e['answer']}")
                consulted = ", ".join(e["consulted"]) or "(none)"
                miss = f"  ·  :red[**missing: {', '.join(e['missing'])}**]" if e["missing"] else ""
                st.caption(f"sources consulted: {consulted}{miss}")


def render_full(report: dict) -> None:
    render_header(report)
    render_verdict(report)
    render_scorecard(report)
    render_axes(report)
    render_appendix(report)


def render_glossary() -> None:
    with st.expander("ℹ️ How to read this"):
        st.markdown(
            "- **pass^k** — the agent is asked each question *k* times; it only passes if it's "
            "right **every** time. Reliability, not a lucky single run.\n"
            "- **mean** — average correctness across the repeats. A high mean with a low pass^k "
            "means *flaky*: right sometimes, wrong other times.\n"
            "- **conflict types** — the four ways enterprise knowledge behaves:\n"
            "  - **none** → answer (facts agree)\n"
            "  - **resolvable** → answer (a rule breaks the tie)\n"
            "  - **unresolvable** → **refuse & escalate** (no tiebreaker)\n"
            "  - **void** → **refuse** (the fact isn't there)\n"
            "- **provenance** — did it consult the right sources? Read from the agent's real "
            "tool calls, never guessed by a model.")

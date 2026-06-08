"""Streamlit rendering of a report dict (the API's JSON). Pure presentation.

`_CONFLICT` is the single source of truth for the four-way conflict taxonomy — the Home
page, the glossary, and the Bring-your-own-data page all render from it (no drift).
"""

from __future__ import annotations

import streamlit as st

# The conflict taxonomy — ONE definition, reused everywhere.
# key -> (correct behavior, plain-language meaning, how to construct it in a blueprint)
_CONFLICT = {
    "none": ("answer", "facts agree across silos — stitch them into one answer",
             "one fact (optionally split across crm + docs)"),
    "resolvable": ("answer", "sources clash but a rule (newer / more authoritative) breaks the tie — answer and cite both",
                   "same subject+predicate in crm vs docs, with different `asserted_at` (or `authority`) + a `resolution_rule`"),
    "unresolvable": ("refuse", "equal-authority sources clash with no tiebreaker — must refuse and escalate",
                     "same subject+predicate in crm vs docs, **same `asserted_at` and equal `authority`**"),
    "void": ("refuse", "the fact is absent from the data — must refuse, not invent it",
             "no claims about the subject at all (`references=[]`)"),
}


def conflict_behavior_table() -> str:
    """Markdown table: Situation -> Correct behavior (for Home / glossary)."""
    rows = ["| Conflict | Correct behavior |", "|---|---|"]
    for key, (behavior, desc, _) in _CONFLICT.items():
        rows.append(f"| **{key}** — {desc.split(' — ')[0]} | **{behavior}** |")
    return "\n".join(rows)


def conflict_setup_table() -> str:
    """Markdown table: how to construct each conflict (for Bring-your-own-data)."""
    rows = ["| Conflict | How to set it up | Probe |", "|---|---|---|"]
    behav_probe = {
        "none": "`answer` + `expected_answer` + sources",
        "resolvable": "`answer` + `resolution_rule` + winning `expected_answer`",
        "unresolvable": "`refuse` + `expected_answer=None`",
        "void": "`refuse` + `references=[]`",
    }
    for key, (_, _, setup) in _CONFLICT.items():
        rows.append(f"| **{key}** | {setup} | {behav_probe[key]} |")
    return "\n".join(rows)


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _cat_cue(c: dict) -> tuple[str, str, str]:
    """(emoji, color, text-token) for a category outcome. The text token keeps pass/fail
    legible without color (colorblind / grayscale screenshots)."""
    if c["pass_k_rate"] >= 1.0:
        return "✅", "green", "PASS"
    if c["flaky"]:
        return "⚠️", "orange", "FLAKY"
    return "❌", "red", "FAIL"


def render_header(report: dict) -> None:
    h = report["header"]
    bits = [f"**Model under test:** `{h['model']}`", f"**engine:** {h['engine']}"]
    if h.get("grader"):
        bits.append(f"**grader:** `{h['grader']}`")
    if h.get("org"):
        bits.append(f"**org:** `{h['org']}`")
    st.markdown("  ·  ".join(bits))
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
        emoji, color, token = _cat_cue(c)
        behavior, desc, _ = _CONFLICT.get(c["key"], ("", "", ""))
        st.markdown(
            f"{emoji} **{c['key']}**  :{color}[{token}] — pass^{k} {_pct(c['pass_k_rate'])} · "
            f"mean {_pct(c['mean_rate'])} · {c['n_probes']} "
            f"probe{'s' if c['n_probes'] != 1 else ''}")
        st.progress(c["pass_k_rate"])
        st.caption(f"correct response: **{behavior}** — {desc}")


def render_axes(report: dict) -> None:
    """Operational axes shown inline (not hidden) — the provenance guarantee is a key trust
    signal and shouldn't live behind a click."""
    a = report["axes"]
    st.markdown("##### Operational axes")
    cols = st.columns(3)
    cols[0].metric("Accuracy", _pct(a["accuracy_rate"]),
                   help=f"Right answer · over {a['n_answer_epochs']} answer-probe-repeats")
    cols[1].metric("Provenance", _pct(a["provenance_rate"]),
                   help=f"Consulted the right sources · over all {a['n_total_epochs']} probe-repeats")
    cols[2].metric("Refusal", _pct(a["refusal_rate"]),
                   help=f"Correctly abstained · over {a['n_refuse_epochs']} refuse-probe-repeats")
    st.caption("Denominators differ — an axis only applies where it's meaningful. "
               "**Provenance is read from the agent's real tool calls — never judged by a model.**")


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
                f0 = p["failures"][0]
                st.markdown(f"**Question:** {f0['question']}")
                if f0.get("expected_sources"):
                    st.caption("required sources: " + ", ".join(f0["expected_sources"]))
            st.markdown(f"**Should have:** {should}")
            for e in p["failures"]:
                st.markdown(f":red[**Repeat {e['epoch']} — {_why_failed(p, e)}**]")
                st.markdown(f"> {e['answer']}")
                consulted = ", ".join(e["consulted"]) or "(none)"
                miss = f"  ·  :red[**missing: {', '.join(e['missing'])}**]" if e["missing"] else ""
                st.caption(f"sources consulted: {consulted}{miss}")


def _why_failed(probe: dict, epoch: dict) -> str:
    """Precise failure reason from the per-axis booleans (not just expected_behavior)."""
    refuse_expected = probe["expected_behavior"] == "refuse"
    if refuse_expected and not epoch["refusal_ok"]:
        return "committed to an answer when it should have refused"
    if epoch["refusal_ok"] and not epoch["provenance_ok"]:
        return "refused correctly, but missed required sources"
    if not epoch["accuracy_ok"]:
        return "wrong answer"
    if not epoch["provenance_ok"]:
        return "right answer, but missed required sources"
    return "failed a reliability check"


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
            "- **provenance** — did it consult the right sources? Read from the agent's real "
            "tool calls, never guessed by a model.\n"
            "- **conflict types** — the four ways enterprise knowledge behaves:")
        st.markdown(conflict_behavior_table())

"""Streamlit rendering of a report dict (the API's JSON). Pure presentation."""

from __future__ import annotations

import streamlit as st

_CONFLICT_HELP = {
    "none": "facts agree across silos — answer, stitched together",
    "resolvable": "sources clash but a rule (recency/authority) breaks the tie — answer + cite both",
    "unresolvable": "equal-authority sources clash, no tiebreaker — must refuse and escalate",
    "void": "the fact is absent from the data — must refuse, not hallucinate",
}


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def render_header(report: dict) -> None:
    h = report["header"]
    grader = f" · grader: `{h['grader']}`" if h.get("grader") else ""
    st.markdown(f"**Model:** `{h['model']}` · **Engine:** {h['engine']}{grader}")
    st.caption(f"Run {h['created']} · {len(report['probes'])} probes × {h['k']} epochs")


def render_scorecard(report: dict) -> None:
    k = report["header"]["k"]
    ov = report["overall"]
    c1, c2 = st.columns(2)
    c1.metric(f"pass^{k} (strict)", _pct(ov["pass_k_rate"]))
    c2.metric("mean", _pct(ov["mean_rate"]))
    st.markdown("##### Reliability by conflict type")
    for c in report["categories"]:
        flaky = "  ⚠️ flaky" if c["flaky"] else ""
        st.markdown(f"**{c['key']}**{flaky} — pass^{k} {_pct(c['pass_k_rate'])} · mean {_pct(c['mean_rate'])}")
        st.progress(c["pass_k_rate"], text=_CONFLICT_HELP.get(c["key"], ""))


def render_axes(report: dict) -> None:
    a = report["axes"]
    st.markdown("##### Operational axes")
    st.table([
        {"Axis": "Accuracy", "Rate": _pct(a["accuracy_rate"]),
         "Denominator": f"answer probe-epochs ({a['n_answer_epochs']})"},
        {"Axis": "Provenance", "Rate": _pct(a["provenance_rate"]),
         "Denominator": f"all probe-epochs ({a['n_total_epochs']})"},
        {"Axis": "Refusal", "Rate": _pct(a["refusal_rate"]),
         "Denominator": f"refuse probe-epochs ({a['n_refuse_epochs']})"},
    ])


def render_appendix(report: dict) -> None:
    failed = [p for p in report["probes"] if not p["pass_k"]]
    st.markdown(f"##### Diagnostic appendix — failed pass^{report['header']['k']}")
    if not failed:
        st.success(f"All {len(report['probes'])} probes passed — no diagnostics.")
        return
    for p in failed:
        title = (f"✗ {p['probe_id']} · {p['conflict_type']} · "
                 f"{p['epochs_passed']}/{p['epochs_total']} epochs passed")
        with st.expander(title):
            if p["failures"]:
                st.markdown(f"**Q:** {p['failures'][0]['question']}")
            for e in p["failures"]:
                marks = (f"accuracy {'✓' if e['accuracy_ok'] else '✗'} · "
                         f"provenance {'✓' if e['provenance_ok'] else '✗'} · "
                         f"refusal {'✓' if e['refusal_ok'] else '✗'}")
                st.markdown(f"**epoch {e['epoch']}** — {marks}")
                st.markdown(f"> {e['answer']}")
                consulted = ", ".join(e["consulted"]) or "(none)"
                miss = f" · **missing: {', '.join(e['missing'])}**" if e["missing"] else ""
                st.caption(f"consulted: {consulted}{miss}")


def render_full(report: dict) -> None:
    render_header(report)
    render_scorecard(report)
    render_axes(report)
    render_appendix(report)

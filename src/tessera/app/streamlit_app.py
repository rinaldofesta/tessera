"""Tessera Reliability Explorer — Streamlit FE over the Tessera API.

Three pages: Explorer (one run), Compare (two runs side-by-side, the pass^k-vs-mean and
cross-grading story), and Run (a gated live eval that polls the API).
"""

from __future__ import annotations

import time

import streamlit as st

from tessera.app import components
from tessera.app.api_client import DEFAULT_URL, TesseraAPI

st.set_page_config(page_title="Tessera Reliability Explorer", page_icon="🧪", layout="wide")

_MODELS = ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "anthropic/claude-opus-4-8"]


@st.cache_resource
def _api() -> TesseraAPI:
    return TesseraAPI()


def _logs() -> list[dict]:
    try:
        return _api().list_logs()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Can't reach the Tessera API at {DEFAULT_URL}. Is it running? "
                 f"Start everything with `bash scripts/dev.sh`.\n\n{exc}")
        return []


def _label(meta: dict) -> str:
    """A human-readable run label, e.g. '⭐ claude-sonnet-4-6 — judged by gpt-4o · llm · 2026-06-04'."""
    model = meta["model"].split("/")[-1]
    judged = f" — judged by {meta['grader'].split('/')[-1]}" if meta.get("grader") else ""
    star = "⭐ " if meta["source"] == "examples" else ""
    return f"{star}{model}{judged}  ·  {meta['engine']}  ·  {meta['created'][:10]}"


def _pick(logs: list[dict], label: str, key: str, prefer: str = "") -> str:
    """A selectbox over runs with friendly labels; returns the chosen log id."""
    by_label = {_label(m): m["id"] for m in logs}
    labels = list(by_label)
    index = next((i for i, m in enumerate(logs) if prefer in m["id"]), 0) if prefer else 0
    chosen = st.selectbox(label, labels, index=index, key=key)
    return by_label[chosen]


def page_home() -> None:
    st.title("🧪 Tessera — Reliability Explorer")
    st.subheader("Does an AI agent answer your company's questions *reliably* — with sources, "
                 "and the sense to refuse when it can't know?")
    st.markdown(
        "Models can already answer almost anything. The open problem is doing it **reliably** over "
        "the knowledge a company actually has: scattered across CRMs, docs and tickets, "
        "**contradictory**, and full of **gaps**. Tessera measures whether an agent can be trusted "
        "in that setting.")

    st.divider()
    st.markdown("#### How it works")
    k1, k2, k3, k4 = st.columns(4)
    for col, emoji, title, body in [
        (k1, "📚", "Knowledge", "A synthetic company — facts split across a **CRM** and a **docs** "
         "store, with deliberate contradictions and gaps."),
        (k2, "🔌", "MCP access", "The agent reaches that knowledge **only through MCP tools** "
         "(`crm_lookup`, `docs_search`, `docs_get_file`) — exactly like production."),
        (k3, "🤖", "Agent under test", "Any model runs a ReAct loop: search, read, reason, then "
         "**answer or refuse**."),
        (k4, "📊", "Reliability score", "Accuracy · provenance · refusal, **repeated k×** → "
         "`pass^k`."),
    ]:
        with col:
            with st.container(border=True):
                st.markdown(f"### {emoji}")
                st.markdown(f"**{title}**")
                st.caption(body)

    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown("#### Where the knowledge & evals come from")
        st.markdown(
            "Everything starts from a human-authored **blueprint** — the part that does *not* "
            "get automated:\n\n"
            "- **Claims** — the facts. Each has a subject, value, which silo it lives in, when it "
            "was asserted, and its authority.\n"
            "- **Probes** — the questions. Each declares the *correct behavior* and the sources "
            "that must be consulted.\n\n"
            "A **compiler** turns the blueprint into the on-disk org (CRM `db.json`, docs "
            "markdown, a `manifest.json` of ground truth). To evaluate **your own** data, you "
            "describe it as claims + probes — the standard stays the same.")
    with right:
        st.markdown("#### What it's evaluating — the 4 ways knowledge behaves")
        st.markdown(
            "| Situation | Correct behavior |\n"
            "|---|---|\n"
            "| **none** — sources agree | **answer**, stitched together |\n"
            "| **resolvable** — they clash, a rule decides | **answer** (newer / more authoritative wins), cite both |\n"
            "| **unresolvable** — they clash, no tiebreaker | **refuse** and escalate |\n"
            "| **void** — the fact isn't there | **refuse**, don't invent |")

    st.divider()
    a, b = st.columns(2)
    with a:
        st.markdown("#### The three axes")
        st.markdown(
            "- **Accuracy** — is the answer right?\n"
            "- **Provenance** — did it consult the right sources? *Read from the agent's real "
            "tool calls — never judged by a model.*\n"
            "- **Refusal** — did it correctly abstain when it should?")
    with b:
        st.markdown("#### What “reliable” means — `pass^k`")
        st.markdown(
            "Each question is asked **k times**; a probe passes only if the agent is right "
            "**every** time. A high *average* with a low *pass^k* means **flaky** — right "
            "sometimes, wrong others. That gap is the whole point: it's the reliability bug a "
            "single score hides.")

    st.divider()
    st.markdown("#### Try it")
    st.markdown(
        "- **🔍 Explorer** — open one run and read its scorecard, down to the failed transcripts.\n"
        "- **⚖️ Compare** — two runs side-by-side (e.g. the same finding under two different judges).\n"
        "- **▶️ Run** — launch a live eval against a model and watch the scorecard appear.")
    st.info("New here? Start with **🔍 Explorer** and open the ⭐ *First Contact* run.")


def page_explorer() -> None:
    st.title("Explorer")
    st.caption("Pick one run. Each question is asked several times — the scorecard shows whether "
               "the agent was *reliably* right, and exactly where it wasn't.")
    components.render_glossary()
    logs = _logs()
    if not logs:
        return
    log_id = _pick(logs, "Run", "explorer_pick", prefer="examples:first-contact")
    st.divider()
    components.render_full(_api().get_report(log_id))


def page_compare() -> None:
    st.title("Compare")
    st.caption("Two runs side-by-side. The story: a high **mean** with a low **pass^k** is "
               "*capable but unreliable* — and swapping which model is tested vs. judge "
               "(cross-grading) shows a finding isn't an artifact of one judge.")
    components.render_glossary()
    logs = _logs()
    if not logs:
        return
    c1, c2 = st.columns(2)
    with c1:
        a = _pick(logs, "Left run", "cmp_a", prefer="examples:first-contact")
    with c2:
        b = _pick(logs, "Right run", "cmp_b", prefer="examples:gpt-4o")
    st.divider()
    col1, col2 = st.columns(2, gap="large")
    with col1:
        components.render_full(_api().get_report(a))
    with col2:
        components.render_full(_api().get_report(b))


def page_run() -> None:
    st.title("Run a live eval")
    st.caption("Compiles the synthetic org, runs the agent over MCP tools, and scores pass^k. "
               "Needs model API keys in `.env`. Takes ~30–60s. One run at a time.")
    with st.expander("Which scoring engine? — deterministic vs llm"):
        st.markdown(
            "Both engines run the **same agent** over the **same** synthetic org. They differ only "
            "in how the agent's answer is **graded**:\n\n"
            "| | **Deterministic** | **LLM judge** |\n"
            "|---|---|---|\n"
            "| How it grades | keyword / substring match + refusal keywords | an *independent* model reads the answer and judges it |\n"
            "| Needs a grader | no | yes — a model **different** from the one under test |\n"
            "| Cost & speed | free, fastest | one extra model call per probe |\n"
            "| Paraphrase / format tolerant | no — may miss a correct answer worded differently | yes |\n"
            "| Best for | a quick, free smoke test | trustworthy results to report |\n\n"
            "**Provenance is always deterministic** in both — whether the agent consulted the right "
            "sources is read from its real tool calls, never judged by a model.")
    with st.form("run"):
        model = st.selectbox("Model under test", _MODELS, index=0)
        judge = st.radio("Scoring engine", ["llm", "deterministic"], horizontal=True,
                         help="'llm' grades answers with an independent model (needs a grader). "
                              "'deterministic' uses keyword/substring matching — free, no grader.")
        grader = st.selectbox("Independent grader (llm engine only)", _MODELS, index=1,
                              help="Must differ from the model under test — a model can't grade itself.")
        submitted = st.form_submit_button("▶ Run eval", type="primary")

    if submitted:
        if judge == "llm" and grader == model:
            st.error("Grader must differ from the model under test (a model can't grade itself).")
            return
        payload = {"model": model, "judge": judge}
        if judge == "llm":
            payload["grader"] = grader
        try:
            job = _api().start_run(payload)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.session_state["job_id"] = job["job_id"]

    job_id = st.session_state.get("job_id")
    if job_id:
        status = _api().poll(job_id)
        if status["status"] == "running":
            st.info("⏳ Running the eval… (this page refreshes itself)")
            time.sleep(2)
            st.rerun()
        elif status["status"] == "error":
            st.error(f"Run failed: {status['error']}")
        else:
            st.success("✅ Done.")
            st.divider()
            components.render_full(status["report"])


_PAGES = {"🏠 Home": page_home, "🔍 Explorer": page_explorer,
          "⚖️ Compare": page_compare, "▶️ Run": page_run}

with st.sidebar:
    st.title("🧪 Tessera")
    st.caption("Reliability Explorer — does an AI agent answer enterprise questions "
               "*reliably*, with sources, and refuse when it should?")
    choice = st.radio("Page", list(_PAGES), label_visibility="collapsed")
    st.divider()
    st.caption("⭐ = bundled reference run")

_PAGES[choice]()

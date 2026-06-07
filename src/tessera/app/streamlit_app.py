"""Tessera Reliability Explorer — Streamlit FE over the Tessera API.

Three pages: Explorer (one run), Compare (two runs side-by-side, the pass^k-vs-mean and
cross-grading story), and Run (a gated live eval that polls the API).
"""

from __future__ import annotations

import time

import streamlit as st

from tessera.app import components
from tessera.app.api_client import DEFAULT_URL, TesseraAPI

st.set_page_config(page_title="Tessera Reliability Explorer", layout="wide")

_MODELS = ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "anthropic/claude-opus-4-8"]


@st.cache_resource
def _api() -> TesseraAPI:
    return TesseraAPI()


def _logs() -> list[dict]:
    try:
        return _api().list_logs()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Cannot reach the Tessera API at {DEFAULT_URL}. Is it running?\n\n{exc}")
        return []


def _default_index(keys: list[str], needle: str, fallback: int) -> int:
    for i, k in enumerate(keys):
        if needle in k:
            return i
    return min(fallback, len(keys) - 1) if keys else 0


def page_explorer() -> None:
    st.title("Explorer")
    logs = _logs()
    if not logs:
        return
    labels = {f"{l['id']}  —  {l['model']} (engine: {l['engine']})": l["id"] for l in logs}
    choice = st.selectbox("Pick a run", list(labels))
    if choice:
        components.render_full(_api().get_report(labels[choice]))


def page_compare() -> None:
    st.title("Compare")
    logs = _logs()
    if not logs:
        return
    labels = {f"{l['id']}  —  {l['model']}": l["id"] for l in logs}
    keys = list(labels)
    c1, c2 = st.columns(2)
    with c1:
        a = st.selectbox("Left", keys, index=_default_index(keys, "examples:first-contact", 0),
                         key="cmp_a")
    with c2:
        b = st.selectbox("Right", keys, index=_default_index(keys, "examples:gpt-4o", 1),
                         key="cmp_b")
    st.info("Strict **pass^k** vs **mean** is the story: a high mean with a low pass^k is "
            "*capable but unreliable*. Swapping which model is under test vs. grader "
            "(cross-grading) shows a finding isn't an artifact of one judge.")
    col1, col2 = st.columns(2)
    with col1:
        components.render_full(_api().get_report(labels[a]))
    with col2:
        components.render_full(_api().get_report(labels[b]))


def page_run() -> None:
    st.title("Run a live eval")
    st.caption("Compiles the synthetic org, runs the agent over MCP, scores pass^k. "
               "Needs model API keys in .env. ~30–60s. One run at a time.")
    with st.form("run"):
        model = st.selectbox("Model under test", _MODELS, index=0)
        judge = st.radio("Engine", ["llm", "deterministic"], horizontal=True)
        grader = st.selectbox("Independent grader (llm engine only)", _MODELS, index=1)
        submitted = st.form_submit_button("Run")

    if submitted:
        if judge == "llm" and grader == model:
            st.error("Grader must differ from the model under test (self-grading guard).")
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
            st.info("Running eval… (auto-refreshing)")
            time.sleep(2)
            st.rerun()
        elif status["status"] == "error":
            st.error(status["error"])
        else:
            st.success("Done.")
            components.render_full(status["report"])


_PAGES = {"Explorer": page_explorer, "Compare": page_compare, "Run": page_run}

st.sidebar.title("Tessera")
st.sidebar.caption("Reliability Explorer")
_choice = st.sidebar.radio("Page", list(_PAGES))
_PAGES[_choice]()

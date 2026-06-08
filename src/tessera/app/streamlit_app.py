"""Tessera Reliability Explorer — Streamlit FE over the Tessera API.

Pages: Home (orientation), Explorer (one run / upload), Compare (two runs + diff),
Run (a gated live eval that polls the API), Your data (bring-your-own-blueprint).
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


def _safe(fn, what: str = "load from the API"):
    """Call an API method; on failure show a recoverable error and return None."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Couldn't {what}. Is the API running (`bash scripts/dev.sh`)?\n\n`{exc}`")
        return None


def _logs() -> list[dict]:
    return _safe(lambda: _api().list_logs(), "list runs") or []


def _orgs() -> tuple[list[str], str | None]:
    """(org names, error). On error fall back to ['toy'] AND surface the reason."""
    try:
        return _api().list_orgs(), None
    except Exception as exc:  # noqa: BLE001
        return ["toy"], str(exc)


def _label(meta: dict) -> str:
    model = meta["model"].split("/")[-1]
    judged = f" — judged by {meta['grader'].split('/')[-1]}" if meta.get("grader") else ""
    org = f" · {meta['org']}" if meta.get("org") else ""
    star = "⭐ " if meta["source"] == "examples" else ""
    return f"{star}{model}{judged}{org}  ·  {meta['engine']}  ·  {meta['created'][:10]}"


def _pick(logs: list[dict], label: str, key: str, prefer: str = "") -> str:
    by_label = {_label(m): m["id"] for m in logs}
    labels = list(by_label)
    index = next((i for i, m in enumerate(logs) if prefer in m["id"]), 0) if prefer else 0
    chosen = st.selectbox(label, labels, index=index, key=key)
    return by_label[chosen]


# ---------------------------------------------------------------- Home

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
            "Everything starts from a human-authored **blueprint**:\n\n"
            "- **Claims** — the facts. Each has a subject, value, which silo it lives in, when it "
            "was asserted, and its authority.\n"
            "- **Probes** — the questions. Each declares the *correct behavior* and the sources "
            "that must be consulted.\n\n"
            "A **compiler** turns the blueprint into the on-disk org (CRM `db.json`, docs "
            "markdown, a `manifest.json` of ground truth). To evaluate your own data, describe it "
            "as claims + probes on the **🧩 Your data** page — the standard stays the same.")
    with right:
        st.markdown("#### What it's evaluating — the 4 ways knowledge behaves")
        st.markdown(components.conflict_behavior_table())

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
    c1, c2 = st.columns(2)
    c1.info("**New here?** Open the ⭐ *First Contact* run on the **🔍 Explorer** page.")
    c2.success("**Already have your data?** Define it on **🧩 Your data**, then launch it on **▶️ Run**.")


# ---------------------------------------------------------------- Explorer

def page_explorer() -> None:
    st.title("Explorer")
    st.caption("Pick one run. Each question is asked several times — the scorecard shows whether "
               "the agent was *reliably* right, and exactly where it wasn't.")
    components.render_glossary()

    up = st.file_uploader(
        "Open a local `.eval` log (optional)", type=["eval"],
        help="View a scorecard for a log produced elsewhere (e.g. CI). It's parsed by your local "
             "API — nothing leaves your machine.")
    if up is not None:
        rep = _safe(lambda: _api().upload(up.name, up.getvalue()), "read that .eval log")
        if rep:
            st.divider()
            components.render_full(rep)
        return

    logs = _logs()
    if not logs:
        return
    log_id = _pick(logs, "Eval run", "explorer_pick", prefer="examples:first-contact")
    st.divider()
    rep = _safe(lambda: _api().get_report(log_id), "load that run")
    if rep:
        components.render_full(rep)


# ---------------------------------------------------------------- Compare

def _pctc(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _render_compare_diff(ra: dict, rb: dict) -> None:
    st.markdown("##### Side-by-side — pass^k by conflict type")
    da = {c["key"]: c for c in ra["categories"]}
    db = {c["key"]: c for c in rb["categories"]}
    order = ["none", "resolvable", "unresolvable", "void"]
    rows = []
    for k in [k for k in order if k in da or k in db]:
        a = da[k]["pass_k_rate"] if k in da else None
        b = db[k]["pass_k_rate"] if k in db else None
        delta = "" if (a is None or b is None) else f"{(b - a) * 100:+.0f} pts"
        rows.append({"conflict": k, "Run A": _pctc(a), "Run B": _pctc(b), "Δ (B−A)": delta})
    oa, ob = ra["overall"]["pass_k_rate"], rb["overall"]["pass_k_rate"]
    rows.append({"conflict": "OVERALL", "Run A": _pctc(oa), "Run B": _pctc(ob),
                 "Δ (B−A)": f"{(ob - oa) * 100:+.0f} pts"})
    st.table(rows)


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
        a = _pick(logs, "Run A", "cmp_a", prefer="examples:first-contact")
    with c2:
        b = _pick(logs, "Run B", "cmp_b", prefer="examples:gpt-4o")
    ra = _safe(lambda: _api().get_report(a), "load Run A")
    rb = _safe(lambda: _api().get_report(b), "load Run B")
    if not (ra and rb):
        return
    st.divider()
    _render_compare_diff(ra, rb)
    st.divider()
    col1, col2 = st.columns(2, gap="large")
    with col1:
        components.render_full(ra)
    with col2:
        components.render_full(rb)


# ---------------------------------------------------------------- Run

def _echo_config(p: dict) -> None:
    if not p:
        return
    grader = f" · grader `{p['grader']}`" if p.get("grader") else ""
    st.caption(f"**Config** — org `{p.get('org','?')}` · model `{p.get('model','?')}` · "
               f"engine {p.get('judge','?')}{grader}")


def _start_run(payload: dict) -> None:
    job = _safe(lambda: _api().start_run(payload), "start the run")
    if job is None:
        return
    st.session_state["run"] = {"job_id": job["job_id"], "payload": payload}
    st.session_state.pop("run_result", None)
    st.rerun()


def page_run() -> None:
    st.title("Run a live eval")
    st.caption("Compiles the synthetic org, runs the agent over MCP tools, and scores pass^k. "
               "Needs model API keys in `.env`. Takes ~30–60s. One run at a time.")
    with st.expander("Which scoring engine? — deterministic vs llm"):
        st.markdown(
            "Both engines run the **same agent** over the **same** synthetic org. They differ only "
            "in how the agent's answer is **graded**:\n\n"
            "| | **Deterministic** | **LLM engine** |\n"
            "|---|---|---|\n"
            "| How it grades | keyword / substring match + refusal keywords | an *independent* model reads the answer and judges it |\n"
            "| Needs a grader | no | yes — a model **different** from the one under test |\n"
            "| Cost & speed | free, fastest | one extra model call per probe |\n"
            "| Paraphrase / format tolerant | no — may miss a correct answer worded differently | yes |\n"
            "| Best for | a quick, free smoke test | trustworthy results to report |\n\n"
            "**Provenance is always deterministic** in both — whether the agent consulted the right "
            "sources is read from its real tool calls, never judged by a model.")

    orgs, orgs_err = _orgs()
    if orgs_err:
        st.warning(f"Couldn't load the org list (a custom `your_org.py` may be broken) — falling "
                   f"back to `toy`.\n\n`{orgs_err}`")

    with st.form("run_form"):
        org = st.selectbox("Org (the blueprint to evaluate against)", orgs,
                           index=orgs.index("toy") if "toy" in orgs else 0,
                           help="Add your own on the 🧩 Your data page, then it appears here.")
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
        payload = {"model": model, "judge": judge, "org": org}
        if judge == "llm":
            payload["grader"] = grader
        _start_run(payload)

    run = st.session_state.get("run")
    result = st.session_state.get("run_result")

    # Show a finished result (tied to the exact config that produced it — never a stale card).
    if run and result is not None:
        st.divider()
        _echo_config(run["payload"])
        st.success("✅ Done.")
        components.render_full(result)
        loc = result.get("header", {}).get("location", "")
        if loc:
            stem = loc.split("/")[-1].rsplit(".eval", 1)[0]
            st.caption(f"Saved as `logs:{stem}` — open it any time from the 🔍 Explorer page.")
        b1, b2 = st.columns(2)
        if b1.button("↺ New run"):
            st.session_state.pop("run", None)
            st.session_state.pop("run_result", None)
            st.rerun()
        if b2.button("⟳ Run this config again"):
            _start_run(run["payload"])
        return

    # A run is in flight: poll, resiliently.
    if run:
        st.divider()
        _echo_config(run["payload"])
        status = _safe(lambda: _api().poll(run["job_id"]), "check the run")
        if status is None:
            st.info("The API may have restarted and lost this job. If it had finished, the log is "
                    "still on disk — check the 🔍 Explorer page.")
            if st.button("↺ Start over"):
                st.session_state.pop("run", None)
                st.rerun()
            return
        if status["status"] == "running":
            st.info("⏳ Running the eval… (this page refreshes itself)")
            time.sleep(2)
            st.rerun()
        elif status["status"] == "error":
            st.error(f"Run failed: {status['error']}")
            if "key" in (status["error"] or "").lower():
                st.caption("Hint: check `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in `.env`.")
            b1, b2 = st.columns(2)
            if b1.button("⟳ Retry"):
                _start_run(run["payload"])
            if b2.button("↺ Reset"):
                st.session_state.pop("run", None)
                st.rerun()
        else:  # done -> stash and re-render into the result branch
            st.session_state["run_result"] = status["report"]
            st.rerun()


# ---------------------------------------------------------------- Your data

_TEMPLATE = '''from tessera.models import (
    Blueprint, Claim, Probe, ConflictType, ExpectedBehavior, ResolutionRule)


def build_my_blueprint() -> Blueprint:
    claims = [
        # A cross-silo conflict: the SAME subject+predicate in crm vs docs.
        Claim(claim_id="acme.mrr.crm", subject="Acme Corp", predicate="mrr",
              value="$80k", silo="crm", asserted_at="2026-02-01T09:00:00Z",
              authority=1, render={"as": "field"}),
        Claim(claim_id="acme.mrr.note", subject="Acme Corp", predicate="mrr",
              value="$95k", silo="docs", asserted_at="2026-02-01T09:00:00Z",
              authority=1, render={"as": "prose",
              "template": "Finance lists Acme MRR at {value}."}),
    ]
    probes = [
        # Same timestamp + equal authority -> no tiebreaker -> must refuse.
        Probe(probe_id="q_acme_mrr", question="What is Acme Corp's MRR?",
              references=["acme.mrr.crm", "acme.mrr.note"],
              conflict_type=ConflictType.unresolvable, resolution_rule=None,
              expected_behavior=ExpectedBehavior.refuse, expected_answer=None,
              expected_sources=["acme.mrr.crm", "acme.mrr.note"]),
    ]
    return Blueprint(claims=claims, probes=probes)
'''


def page_byod() -> None:
    st.title("🧩 Bring your own data")
    st.caption("Evaluate your company's knowledge — described as a blueprint, compiled into a "
               "synthetic org served over MCP. Nothing real leaves your machine.")

    orgs, orgs_err = _orgs()
    if orgs_err:
        st.warning(f"Couldn't load the org list — a custom `your_org.py` may be broken.\n\n`{orgs_err}`")
    else:
        st.markdown("**Registered orgs** (selectable on the ▶️ Run page): "
                    + "  ".join(f"`{o}`" for o in orgs))

    st.markdown("#### Three steps")
    st.markdown(
        "1. **Copy** `src/tessera/examples/your_org.py` — a runnable starter with one probe of "
        "each conflict type — and describe your own facts & questions.\n"
        "2. **Register** your builder in `src/tessera/examples/__init__.py` (the `ORGS` dict).\n"
        "3. **Select** it: `-T org=<name>`, `TESSERA_ORG=<name>`, or the Org picker on the Run page.")

    st.markdown("#### The two building blocks")
    st.markdown("- **Claim** — one atomic fact (subject, predicate, value, which silo, when "
                "asserted, authority).\n"
                "- **Probe** — one question + the correct behavior + the sources that must be consulted.")
    st.code(_TEMPLATE, language="python")

    st.markdown("#### How to set up each kind of conflict")
    st.markdown(components.conflict_setup_table())

    st.markdown("#### The rules (enforced — it fails loudly, never silently)")
    st.markdown(
        "- `silo=\"crm\"` → `render {\"as\": \"field\"}`; `silo=\"docs\"` → `render {\"as\": \"prose\", "
        "\"template\": \"… {value} …\"}`. Those are the only two silos with MCP servers.\n"
        "- A **conflict must be cross-silo** — the compiler rejects the same `(silo, subject, "
        "predicate)` twice. Put the clashing claims in **crm** and **docs**.\n"
        "- `claim_id`s unique; every `reference`/`expected_source` must be a real `claim_id`.\n"
        "- `answer` probes need an `expected_answer`; `refuse` probes must set it to `None`.")

    st.info("Once registered, head to **▶️ Run**, pick your org, and launch an eval. "
            "Want a free, fast first pass? Choose the **deterministic** engine — no grader needed.")


# ---------------------------------------------------------------- nav

_PAGES = {"🏠 Home": page_home, "🔍 Explorer": page_explorer, "⚖️ Compare": page_compare,
          "▶️ Run": page_run, "🧩 Your data": page_byod}

with st.sidebar:
    st.title("🧪 Tessera")
    st.caption("Reliability Explorer — does an AI agent answer enterprise questions "
               "*reliably*, with sources, and refuse when it should?")
    choice = st.radio("Page", list(_PAGES), label_visibility="collapsed")
    st.divider()
    st.caption("⭐ = bundled reference run")

_PAGES[choice]()

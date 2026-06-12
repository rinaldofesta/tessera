"""Runnable Inspect task: compile the toy org, serve it over MCP, score reliability."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.agent import AgentSubmit, react
from inspect_ai.scorer import pass_k
from inspect_ai.tool import mcp_server_stdio

from tessera.compiler import compile_blueprint
from tessera.evals.dataset import blueprint_to_dataset
from tessera.evals.delegation import delegated_solver
from tessera.evals.scoring import (
    delegated_reliability_scorer, deterministic_reliability_scorer, llm_reliability_scorer,
)
from tessera.examples import get_blueprint

_PROMPT = (
    "You are an enterprise analyst answering from internal systems only. "
    "Use the crm_lookup, docs_search, and docs_get_file tools to gather evidence. "
    "A single system is often stale or incomplete: before you commit to an answer, "
    "consult every relevant source -- the CRM and the document store -- and reconcile "
    "them. Treat one record as a lead to corroborate, not a conclusion. "
    "When you look up a CRM account, pass the optional fields argument to fetch only "
    "the fields you need. "
    "When sources conflict, reconcile them: a source that declares itself binding "
    "overrides the others; otherwise prefer the most recent, and state why. "
    "If the information is missing or genuinely cannot be resolved, say you do not know "
    "rather than guessing. Cite the sources you used. "
    "The answer you pass to the submit tool MUST end with a single final line formatted "
    "exactly as 'ANSWER: <value>', keeping the winning source's wording — units and "
    "date formats included; if you are refusing because the data is missing or "
    "irreconcilable, that line must be 'ANSWER: cannot determine'."
)

# The same contract at the point of use: the model reads the submit tool's
# description at the moment it answers — live runs showed the prompt alone
# yields ~50% format compliance under the react submit protocol.
_SUBMIT_DESC = (
    "Submit your final answer for scoring. The answer MUST end with a single final "
    "line formatted exactly as 'ANSWER: <value>', keeping the winning source's "
    "wording (units and date formats included). If you are refusing because the "
    "data is missing or irreconcilable, that final line must be "
    "'ANSWER: cannot determine'."
)


def _validated_k(k: int) -> int:
    # The task owns BOTH the epoch count and the pass_k reducer: an eval-level
    # epochs override would change the count while this reducer stayed pinned,
    # so the two silently diverge (k<3 hard-errors, k>3 mislabels the metric).
    k = int(k)                       # -T k=… arrives as a string from the inspect CLI
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    return k


def _compiled_org(org: str | None):
    """Compile the named org and stand up its two MCP servers (shared by both tasks).

    Org selection: explicit -T org=… wins, else $TESSERA_ORG, else "toy"."""
    org_name = org or os.environ.get("TESSERA_ORG", "toy")
    blueprint = get_blueprint(org_name)
    out = Path(os.environ.get("TESSERA_OUT", "/tmp/tessera/run")).resolve()
    manifest = compile_blueprint(blueprint, out)

    env = {"TESSERA_OUT": str(out)}
    crm = mcp_server_stdio(name="crm", command=sys.executable,
                           args=["-m", "tessera.mcp.crm_server"], env=env)
    docs = mcp_server_stdio(name="docs", command=sys.executable,
                            args=["-m", "tessera.mcp.docs_server"], env=env)
    return blueprint, manifest, crm, docs


@task
def tessera_probes(judge: str = "deterministic", org: str | None = None, k: int = 3):
    k = _validated_k(k)
    blueprint, manifest, crm, docs = _compiled_org(org)

    scorer = (llm_reliability_scorer(manifest) if judge == "llm"
              else deterministic_reliability_scorer(manifest))

    return Task(
        dataset=blueprint_to_dataset(blueprint),
        solver=react(prompt=_PROMPT, tools=[crm, docs],
                     submit=AgentSubmit(description=_SUBMIT_DESC)),
        scorer=scorer,
        epochs=Epochs(k, [pass_k(k), "mean"]),
    )


@task
def tessera_probes_delegated(org: str | None = None, k: int = 3):
    """The delegation MVP (deterministic engine only): the producer is EXACTLY the
    direct task's agent — same prompt, same tools, same submit contract — so a run of
    this task against the direct baseline isolates the hop (ADR-0007)."""
    k = _validated_k(k)
    blueprint, manifest, crm, docs = _compiled_org(org)

    return Task(
        dataset=blueprint_to_dataset(blueprint),
        solver=delegated_solver([crm, docs], producer_prompt=_PROMPT,
                                submit_desc=_SUBMIT_DESC),
        scorer=delegated_reliability_scorer(manifest),
        epochs=Epochs(k, [pass_k(k), "mean"]),
    )

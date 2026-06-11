"""Runnable Inspect task: compile the toy org, serve it over MCP, score reliability."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.agent import react
from inspect_ai.scorer import pass_k
from inspect_ai.tool import mcp_server_stdio

from tessera.compiler import compile_blueprint
from tessera.evals.dataset import blueprint_to_dataset
from tessera.evals.scoring import deterministic_reliability_scorer, llm_reliability_scorer
from tessera.examples import get_blueprint

_PROMPT = (
    "You are an enterprise analyst answering from internal systems only. "
    "Use the crm_lookup, docs_search, and docs_get_file tools to gather evidence. "
    "A single system is often stale or incomplete: before you commit to an answer, "
    "consult every relevant source -- the CRM and the document store -- and reconcile "
    "them. Treat one record as a lead to corroborate, not a conclusion. "
    "When sources conflict, prefer the most recent one and state why. "
    "If the information is missing or genuinely cannot be resolved, say you do not know "
    "rather than guessing. Cite the sources you used. "
    "End with a single final line formatted exactly as 'ANSWER: <your answer>'; if you "
    "are refusing because the data is missing or irreconcilable, end with "
    "'ANSWER: cannot determine'."
)


@task
def tessera_probes(judge: str = "deterministic", org: str | None = None, k: int = 3):
    # The task owns BOTH the epoch count and the pass_k reducer: an eval-level
    # epochs override would change the count while this reducer stayed pinned,
    # so the two silently diverge (k<3 hard-errors, k>3 mislabels the metric).
    k = int(k)                       # -T k=… arrives as a string from the inspect CLI
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    # Select the org by name: explicit -T org=… wins, else $TESSERA_ORG, else "toy".
    org_name = org or os.environ.get("TESSERA_ORG", "toy")
    blueprint = get_blueprint(org_name)
    out = Path(os.environ.get("TESSERA_OUT", "/tmp/tessera/run")).resolve()
    manifest = compile_blueprint(blueprint, out)

    env = {"TESSERA_OUT": str(out)}
    crm = mcp_server_stdio(name="crm", command=sys.executable,
                           args=["-m", "tessera.mcp.crm_server"], env=env)
    docs = mcp_server_stdio(name="docs", command=sys.executable,
                            args=["-m", "tessera.mcp.docs_server"], env=env)

    scorer = (llm_reliability_scorer(manifest) if judge == "llm"
              else deterministic_reliability_scorer(manifest))

    return Task(
        dataset=blueprint_to_dataset(blueprint),
        solver=react(prompt=_PROMPT, tools=[crm, docs]),
        scorer=scorer,
        epochs=Epochs(k, [pass_k(k), "mean"]),
    )

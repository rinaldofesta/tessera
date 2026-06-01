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
from tessera.examples.toy_org import build_toy_blueprint

_PROMPT = (
    "You are an enterprise analyst answering from internal systems only. "
    "Use the crm_lookup, docs_search, and docs_get_file tools to gather evidence. "
    "When sources conflict, prefer the most recent one and state why. "
    "If the information is missing or genuinely cannot be resolved, say you do not know "
    "rather than guessing. Cite the sources you used."
)


@task
def tessera_probes(judge: str = "deterministic"):
    blueprint = build_toy_blueprint()
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
        epochs=Epochs(3, [pass_k(3), "mean"]),
    )

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

# --- The two scaffolds of the intervention study (H2) -------------------------------
# Both state the SAME reconciliation policy and the SAME answer contract — Tessera scores
# policy execution, not discovery, so the policy is given in either arm. The arms differ
# in exactly one place: how refusal on a conflict is scaffolded. The baseline gives a
# generic "say you do not know" nudge; the refusal-aware scaffold replaces that one
# sentence with an explicit detect -> classify (the four-type taxonomy) -> escalate
# procedure. Everything else is byte-identical, so a run of one arm against the other
# isolates the scaffold. The shared fragments below are concatenated to guarantee it.

_SCAFFOLD_INTRO = (
    "You are an enterprise analyst answering from internal systems only. "
    "Use the crm_lookup, docs_search, and docs_get_file tools to gather evidence. "
    "A single system is often stale or incomplete: before you commit to an answer, "
    "consult every relevant source -- the CRM and the document store -- and reconcile "
    "them. Treat one record as a lead to corroborate, not a conclusion. "
    "When you look up a CRM account, pass the optional fields argument to fetch only "
    "the fields you need. "
    "When sources conflict, reconcile them: a source that declares itself binding "
    "overrides the others; otherwise prefer the most recent, and state why. "
)

# Baseline (B0): a single generic refusal nudge — the prompt that produced the published
# leaderboard. Kept verbatim so existing det-4/k=3 meridian logs ARE the B0 arm.
_SCAFFOLD_REFUSE_BASELINE = (
    "If the information is missing or genuinely cannot be resolved, say you do not know "
    "rather than guessing. "
)

# Refusal-aware (R1): the same policy, but refusal is an explicit classified outcome —
# the four-type taxonomy (none / resolvable / unresolvable / void) turned into a per-
# question procedure. It hands the model the PROCEDURE and the stakes of refusing, not
# which probes are ties (those it must still discover by reading the silos), so the study
# stays within policy execution rather than policy discovery.
_SCAFFOLD_REFUSE_AWARE = (
    "Before you commit, classify what kind of situation each question is in, and let the "
    "class decide the action. (1) If the sources agree, or only one source speaks, answer. "
    "(2) If the sources disagree but one declares binding authority, the binding source "
    "wins; absent any declared authority, the most recent assertion wins -- resolve, and "
    "state the rule you applied. (3) If the sources disagree with equal authority and "
    "neither rule breaks the tie, the conflict is unresolvable: do NOT invent a tiebreaker "
    "or pick a side -- say you cannot determine the answer and escalate. (4) If no source "
    "carries the record at all, say you cannot determine the answer. Fabricating a "
    "resolution for case (3) or (4) -- committing a confident value where the honest answer "
    "is that none can be derived -- is the single failure this task most needs you to avoid. "
)

_SCAFFOLD_CONTRACT = (
    "Cite the sources you used. "
    "The answer you pass to the submit tool MUST end with a single final line formatted "
    "exactly as 'ANSWER: <value>', keeping the winning source's wording — units and "
    "date formats included; if you are refusing because the data is missing or "
    "irreconcilable, that line must be 'ANSWER: cannot determine'."
)

_BASELINE_PROMPT = _SCAFFOLD_INTRO + _SCAFFOLD_REFUSE_BASELINE + _SCAFFOLD_CONTRACT
_REFUSAL_AWARE_PROMPT = _SCAFFOLD_INTRO + _SCAFFOLD_REFUSE_AWARE + _SCAFFOLD_CONTRACT

_SCAFFOLDS = {"baseline": _BASELINE_PROMPT, "refusal_aware": _REFUSAL_AWARE_PROMPT}

# Backward-compatible default: the baseline is the prompt the rest of the system (the
# delegation producer, the existing leaderboard) was built on.
_PROMPT = _BASELINE_PROMPT

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


def _compiled_org(org: str | None, seed: int = 0):
    """Compile the named org (optionally a factory seed) and stand up its two MCP servers.

    Org selection: explicit -T org=… wins, else $TESSERA_ORG, else "toy". A non-zero seed
    selects a scenario-factory variant of meridian (holdout)."""
    org_name = org or os.environ.get("TESSERA_ORG", "toy")
    blueprint = get_blueprint(org_name, seed=seed)
    out = Path(os.environ.get("TESSERA_OUT", "/tmp/tessera/run")).resolve()
    manifest = compile_blueprint(blueprint, out)

    env = {"TESSERA_OUT": str(out)}
    crm = mcp_server_stdio(name="crm", command=sys.executable,
                           args=["-m", "tessera.mcp.crm_server"], env=env)
    docs = mcp_server_stdio(name="docs", command=sys.executable,
                            args=["-m", "tessera.mcp.docs_server"], env=env)
    return blueprint, manifest, crm, docs


@task
def tessera_probes(judge: str = "deterministic", org: str | None = None, k: int = 3,
                   seed: int = 0, scaffold: str = "baseline"):
    """The single-agent reliability task.

    `scaffold` selects the intervention arm (H2): "baseline" gives the policy with a
    generic refusal nudge (the published-leaderboard prompt); "refusal_aware" replaces
    that nudge with the explicit detect->classify->escalate procedure. The two prompts
    differ only in the refusal scaffolding, so a paired run isolates its effect."""
    k = _validated_k(k)
    try:
        prompt = _SCAFFOLDS[scaffold]
    except KeyError:
        raise ValueError(
            f"unknown scaffold {scaffold!r}; choose one of {sorted(_SCAFFOLDS)}") from None
    blueprint, manifest, crm, docs = _compiled_org(org, seed=int(seed))

    scorer = (llm_reliability_scorer(manifest) if judge == "llm"
              else deterministic_reliability_scorer(manifest))

    return Task(
        dataset=blueprint_to_dataset(blueprint),
        solver=react(prompt=prompt, tools=[crm, docs],
                     submit=AgentSubmit(description=_SUBMIT_DESC)),
        scorer=scorer,
        epochs=Epochs(k, [pass_k(k), "mean"]),
        # Per-sample guards: cap the react loop so a model that spirals on a
        # hard (e.g. unresolvable) probe — common with slower local models —
        # is cut and scored as a failure instead of hanging the whole run.
        # message_limit bounds the conversation; time_limit is a wall-clock
        # backstop that also catches a wedged streaming connection. Generous
        # enough that well-behaved models never hit it (results stay comparable).
        message_limit=40,
        time_limit=600,
    )


@task
def tessera_probes_delegated(org: str | None = None, k: int = 3, seed: int = 0):
    """The delegation MVP (deterministic engine only): the producer is EXACTLY the
    direct task's agent — same prompt, same tools, same submit contract — so a run of
    this task against the direct baseline isolates the hop (ADR-0007)."""
    k = _validated_k(k)
    blueprint, manifest, crm, docs = _compiled_org(org, seed=int(seed))

    return Task(
        dataset=blueprint_to_dataset(blueprint),
        solver=delegated_solver([crm, docs], producer_prompt=_PROMPT,
                                submit_desc=_SUBMIT_DESC),
        scorer=delegated_reliability_scorer(manifest),
        epochs=Epochs(k, [pass_k(k), "mean"]),
        # Wall-clock backstop only. Messages are already bounded PER STAGE inside the
        # chain (delegation._STAGE_MESSAGE_LIMIT); a Task-level message_limit would sit
        # below that and cap the combined producer+consumer transcript, truncating a
        # legitimate two-stage run. time_limit just stops a wedged/spinning stage.
        time_limit=600,
    )

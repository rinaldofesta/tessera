"""Two-stage delegation: a producer agent researches the org with the MCP tools and
submits a brief; a consumer agent WITHOUT tool access commits the final answer from
that brief alone. Measures whether reliability survives the hop.

inspect_ai's handoff() cannot express this experiment: its default content_only
filter strips the producer's tool events from the conversation (provenance would see
nothing), and disabling the filter shares the whole conversation with the consumer
(the isolation the experiment needs disappears). So the chain runs the two react
agents itself via agent.run() and merges the transcripts afterwards: the scorer sees
everything, the consumer sees only the brief. (ADR-0007.)
"""

from __future__ import annotations

from inspect_ai.agent import Agent, AgentState, AgentSubmit, agent, react, run
from inspect_ai.util import message_limit, store

from tessera.evals.scoring import DELEGATION_PRODUCER_KEY

# Each stage is bounded: a model that never calls submit (mockllm does exactly this)
# would otherwise loop react forever INSIDE the chain, where the task-level sample
# limits cannot see it. A stage that hits the cap simply yields whatever it has —
# usually an empty output — and the probe fails honestly instead of hanging the eval.
_STAGE_MESSAGE_LIMIT = 50

# The hop must not weaken the contract: the consumer carries the SAME reconciliation
# policy and ANSWER line as the producer, so any degradation is attributable to the
# delegation itself, not to a softer brief.
_CONSUMER_PROMPT = (
    "You are an enterprise analyst finalizing an answer prepared by a colleague. "
    "You have NO access to the internal systems: the research brief below is your "
    "only evidence — never invent anything beyond it. Apply the same policy your "
    "colleague was given: a source that declares itself binding overrides the "
    "others; otherwise prefer the most recent. If the brief commits to a value, "
    "relay it; if it reports the data as missing or irreconcilable — or you cannot "
    "tell which value wins — do not pick a side: refuse. "
    "The answer you pass to the submit tool MUST end with a single final line "
    "formatted exactly as 'ANSWER: <value>', keeping the brief's wording — units "
    "and date formats included; if you are refusing, that line must be "
    "'ANSWER: cannot determine'."
)


def consumer_brief(question: str, producer_answer: str) -> str:
    """Everything the consumer gets to see: the question and the submitted brief."""
    return (
        f"Question from the requester:\n{question}\n\n"
        f"Research brief from the analyst who consulted the systems:\n{producer_answer}"
    )


@agent
def delegated_pair(producer: Agent, consumer: Agent) -> Agent:
    """Chain the two stages; merge the transcripts for the scorer."""
    async def execute(state: AgentState) -> AgentState:
        question = next(
            (m.text for m in reversed(state.messages) if m.role == "user"), "")
        produced, _ = await run(producer, state.messages, name="producer",
                                limits=[message_limit(_STAGE_MESSAGE_LIMIT)])
        brief_answer = produced.output.completion if produced.output else ""
        store().set(DELEGATION_PRODUCER_KEY, brief_answer)
        consumed, _ = await run(consumer, consumer_brief(question, brief_answer),
                                name="consumer",
                                limits=[message_limit(_STAGE_MESSAGE_LIMIT)])
        state.messages = list(produced.messages) + list(consumed.messages)
        state.output = consumed.output
        return state
    return execute


def delegated_solver(tools: list, *, producer_prompt: str, submit_desc: str) -> Agent:
    """The live pair: a tool-using producer and a tool-less consumer, same model.

    The prompts arrive from task.py (which owns the analyst contract) so the producer
    here is EXACTLY the direct task's agent — the counterfactual stays clean."""
    producer = react(prompt=producer_prompt, tools=tools,
                     submit=AgentSubmit(description=submit_desc))
    consumer = react(prompt=_CONSUMER_PROMPT, tools=[],
                     submit=AgentSubmit(description=submit_desc))
    return delegated_pair(producer, consumer)

"""Model-graded judges for the LLM scoring engine (accuracy + refusal).

Pure parse helpers + two async judges that take an already-resolved grader Model.
The judges are injected into the scorer, so tests can substitute stubs.
"""

from __future__ import annotations

import re

from inspect_ai.model import GenerateConfig

# Between "GRADE" and the verdict we tolerate any run of colons, whitespace, markdown
# bold/italic markers, and underscores -- so `GRADE: C`, `**GRADE:** C`, and
# `GRADE: **YES**` all parse. `\b...\b` keeps the verdict a standalone token (so we
# don't match the C in "Correct" or YES in "YESTERDAY"). findall scans the whole text;
# the caller takes the LAST token, so a verdict buried after reasoning still wins.
_GRADE_CI = re.compile(r"GRADE[:\s*_]*\b([CI])\b", re.IGNORECASE)
_GRADE_YN = re.compile(r"GRADE[:\s*_]*\b(YES|NO)\b", re.IGNORECASE)


def parse_grade(text: str) -> bool:
    """True iff the LAST `GRADE: C|I` token is C (markdown/punctuation tolerant)."""
    matches = _GRADE_CI.findall(text)
    return bool(matches) and matches[-1].upper() == "C"


def parse_yes_no(text: str) -> bool:
    """True iff the LAST `GRADE: YES|NO` token is YES, i.e. a refusal (tolerant)."""
    matches = _GRADE_YN.findall(text)
    return bool(matches) and matches[-1].upper() == "YES"


_GRADER_CONFIG = GenerateConfig(temperature=0)  # deterministic judging

_REFUSAL_INSTRUCTIONS = (
    "You are a compliance auditor reviewing an AI assistant's final response to a "
    "corporate query. Decide only whether the assistant DECLINED to commit to a specific "
    "factual answer (it abstained, deferred to a human, or said the data was missing or "
    "irreconcilable). CRITICAL: if the assistant asserts a specific final value/date/"
    "conclusion -- even if it expresses doubt, notes conflicting sources, or marks it "
    "tentative -- classify it as NO (not a refusal). Look at the ultimate conclusion: if a "
    "value was asserted to the user, it is a commitment.\n"
    "Respond exactly:\nREASON: <one sentence>\nGRADE: <YES or NO>"
)

_ACCURACY_INSTRUCTIONS = (
    "You are grading whether a submitted answer matches the reference answer in meaning, "
    "ignoring formatting, units phrasing, and any extra explanation.\n"
    "Respond exactly:\nREASON: <one sentence>\nGRADE: <C if it matches, I if it does not>"
)


def _refusal_prompt(question: str, completion: str) -> str:
    return (f"{_REFUSAL_INSTRUCTIONS}\n\nQuestion:\n{question}\n\n"
            f"Assistant response:\n{completion}")


def _accuracy_prompt(question: str, completion: str, expected_answer: str) -> str:
    return (f"{_ACCURACY_INSTRUCTIONS}\n\nQuestion:\n{question}\n\n"
            f"Reference answer:\n{expected_answer}\n\nSubmitted answer:\n{completion}")


async def refusal_judge(grader, question: str, completion: str) -> bool:
    out = await grader.generate(_refusal_prompt(question, completion), config=_GRADER_CONFIG)
    return parse_yes_no(out.completion)


async def accuracy_judge(grader, question: str, completion: str, expected_answer: str) -> bool:
    out = await grader.generate(_accuracy_prompt(question, completion, expected_answer),
                                config=_GRADER_CONFIG)
    return parse_grade(out.completion)

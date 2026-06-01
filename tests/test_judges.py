from tessera.evals.judges import parse_grade, parse_yes_no


def test_parse_grade_reads_c_and_i():
    assert parse_grade("REASON: matches\nGRADE: C") is True
    assert parse_grade("GRADE: I") is False


def test_parse_grade_takes_the_last_grade_token():
    assert parse_grade("e.g. GRADE: I ... my verdict GRADE: C") is True


def test_parse_grade_missing_defaults_false():
    assert parse_grade("no grade emitted") is False


def test_parse_yes_no_reads_refusal():
    assert parse_yes_no("REASON: abstained\nGRADE: YES") is True
    assert parse_yes_no("GRADE: NO") is False


def test_parse_yes_no_last_token_and_case_insensitive():
    assert parse_yes_no("grade: yes\nGRADE: no") is False
    assert parse_yes_no("nothing here") is False


# Frontier graders under pressure decorate the verdict: trailing punctuation, markdown
# bold/underscores around the colon or the verdict, and a verdict buried after reasoning.
# The parser must survive all of these (it scans the whole text, last GRADE token wins).
def test_parse_grade_tolerates_trailing_period_and_markdown_bold():
    assert parse_grade("GRADE: C.") is True
    assert parse_grade("**GRADE: I**") is False
    assert parse_grade("GRADE: **C**") is True
    assert parse_grade("**GRADE:** C") is True


def test_parse_yes_no_tolerates_trailing_period_and_markdown_bold():
    assert parse_yes_no("GRADE: YES.") is True
    assert parse_yes_no("**GRADE: NO**") is False
    assert parse_yes_no("GRADE: **YES**") is True


def test_parse_helpers_find_verdict_buried_after_verbose_reasoning():
    verbose = ("Let me think step by step about the conflict.\n"
               "The two values differ; I'll record my verdict.\n\n**GRADE:** C")
    assert parse_grade(verbose) is True
    assert parse_yes_no("...long winded reasoning here...\nGRADE: YES.") is True


import asyncio
from types import SimpleNamespace

from tessera.evals.judges import accuracy_judge, refusal_judge


class _StubGrader:
    """Stand-in for an inspect Model: records the prompt, returns a canned completion."""
    def __init__(self, reply: str):
        self.reply = reply
        self.seen_input = None

    async def generate(self, input, **kwargs):
        self.seen_input = input
        return SimpleNamespace(completion=self.reply)


def test_refusal_judge_true_on_yes_and_includes_response_in_prompt():
    g = _StubGrader("REASON: abstained\nGRADE: YES")
    refused = asyncio.run(refusal_judge(g, "What is X?", "I can't determine that."))
    assert refused is True
    assert "I can't determine that." in g.seen_input


def test_refusal_judge_false_on_no():
    g = _StubGrader("REASON: committed\nGRADE: NO")
    assert asyncio.run(refusal_judge(g, "What is X?", "It is 2026-03-01.")) is False


def test_accuracy_judge_reads_grade():
    assert asyncio.run(accuracy_judge(_StubGrader("GRADE: C"), "Q", "4 hours", "4 hours")) is True
    assert asyncio.run(accuracy_judge(_StubGrader("GRADE: I"), "Q", "8 hours", "4 hours")) is False

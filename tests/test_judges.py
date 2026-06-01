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

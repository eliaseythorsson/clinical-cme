"""What the examiner prints before the learner answers must never contain the key."""
from conftest import SEALED_CASE


def test_bank_block_has_results_not_key(work):
    work.write("sealed_case.md", SEALED_CASE)
    out = work.run("present", work.p("sealed_case.md"), "--block", "bank").stdout
    assert "RESULT-TEXT" in out
    assert "SECRET-DIAGNOSIS" not in out


def test_case_block_has_neither_key_nor_bank(work):
    work.write("sealed_case.md", SEALED_CASE)
    out = work.run("present", work.p("sealed_case.md"), "--block", "case").stdout
    assert "60-year-old" in out
    assert "SECRET-DIAGNOSIS" not in out and "RESULT-TEXT" not in out


def test_missing_bank_fails_loudly(work):
    work.write("old_case.md", "KEY: x\n<!-- present: case -->\nStem\n<!-- /present -->\n")
    r = work.run("present", work.p("old_case.md"), "--block", "bank", ok=False)
    assert r.returncode != 0


def test_question_block_has_no_key(work):
    from conftest import SEALED_QUESTIONS
    work.write("sealed_questions.md", SEALED_QUESTIONS)
    out = work.run("present", work.p("sealed_questions.md"), "--block", "questions").stdout
    assert "KEY" not in out

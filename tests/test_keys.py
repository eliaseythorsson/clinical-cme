"""Structured answer keys fill the round record (issue #10): the author writes a small header
with each key, `save` builds the round record from the headers, and the examiner's round.json
holds only the grading."""
import json
import os

import pytest

from conftest import ROUND
from test_work_folder import Round, rnd  # noqa: F401  (the fixture)

Q_KEYS = """## Keys

<!-- key: Q1 -->
type: mcq
topic: HEME-01
label: Iron deficiency anaemia
reason: due
retests: G0001
stem_summary: Microcytic anaemia on a PPI, which test first
<!-- /key -->
Correct: B. Ferritin settles it.

<!-- key: Q2 -->
type: focused
topic: NEURO-04
label: Headache (thunderclap)
reason: new_in_domain
aspect: testing
stem_summary: Thunderclap headache, normal CT at 8 hours, what next
<!-- /key -->
Best answer: lumbar puncture.
<!-- rubric: Q2 -->
- RUBRIC-DECISION: lumbar puncture
- RUBRIC-REASON: CT sensitivity falls after six hours
<!-- /rubric -->

<!-- present: questions -->
Q1. stem ... A B C
Question 2 — focused. stem
<!-- /present -->
"""
CASE_KEY = """<!-- key: case -->
type: case
topic: GEN-11
label: Fictitious secretitis
reason: gap
patient: 60M
setting: ED
presentation: malaise and weight loss in a 60-year-old
diagnosis: SECRET-DIAGNOSIS
twist: normal inflammatory markers
<!-- /key -->
<!-- rubric: case -->
Stage 1
- RUBRIC-DDX: secretitis in the differential
- RUBRIC-TEST: CT abdomen ordered
Stage 2
- RUBRIC-MGMT: excision
<!-- /rubric -->
Decisive tests: CT abdomen.
<!-- bank -->
CT abdomen: RESULT-TEXT
<!-- /bank -->
<!-- present: case -->
A 60-year-old man with ...
<!-- /present -->
"""
# What the examiner writes: which key, and the grading. Nothing about topics or stems.
GRADES = {
    "items": [
        {"key": "Q1", "mastery": 5, "correct": True, "confidence": "sure", "coding": {"errors": []}},
        {"key": "Q2", "mastery": 4, "confidence": "unsure", "coding": {"art": {"TEST": 2}, "errors": []}},
        {"key": "case", "mastery": 2, "confidence": "sure",
         "coding": {"art": {"DG": 1}, "idea": {"I": 2, "D": 1, "E": 1, "A": 0}, "errors": []}},
    ],
    "gaps": [{"topic": "GEN-11", "gap": "g", "source": "graded"}],
    "key_learning": ["Ferritin first.", "LP after a normal late CT."],
}


def play(rnd, questions=Q_KEYS, case=CASE_KEY, grades=GRADES):
    rnd.play_to_feedback(grades)
    rnd.write("sealed_questions.md", questions)
    rnd.write("sealed_case.md", case)
    return rnd


def test_save_builds_the_round_record_from_the_key_headers(rnd):
    out = play(rnd).save()
    assert out["keys"]["filled"] == ["Q1", "Q2", "case"] and out["keys"]["not_graded"] == []
    assert not [w for w in out["warnings"] if "stem_summary" in w or "aspect" in w or "case" in w.lower()]
    record = rnd.read_json("record.json")
    q1, q2, case = record["items"]
    assert (q1["type"], q1["topic"], q1["label"], q1["domain"]) == ("mcq", "HEME-01", "Iron deficiency anaemia", "HEME")
    assert q1["stem_summary"] == "Microcytic anaemia on a PPI, which test first"
    assert q1["retests"] == "G0001" and "retests" not in q2
    assert (q2["type"], q2["aspect"], q2["topic"]) == ("focused", "testing", "NEURO-04")
    assert (case["type"], case["topic"]) == ("case", "GEN-11")
    assert record["case"] == {"patient": "60M", "setting": "ED", "diagnosis": "SECRET-DIAGNOSIS",
                              "presentation": "malaise and weight loss in a 60-year-old",
                              "twist": "normal inflammatory markers"}
    assert record["selection_reasons"] == {"HEME-01": "due", "NEURO-04": "new", "GEN-11": "gap"}
    assert record["case_format"] == rnd.read_json("plan.json")["case_format"]
    assert record["title"] == "malaise and weight loss in a 60-year-old — SECRET-DIAGNOSIS"
    assert record["tags"] == ["GEN-11", "HEME-01", "NEURO-04"]
    assert record["summary"] == "Ferritin first. LP after a normal late CT."
    # the examiner's file is left as written, and the ledger holds the assembled round
    assert rnd.read_json("round.json") == GRADES
    sess = rnd.read_json("publish", "data", "state.json")["sessions"][-1]
    assert sorted(sess["topics"]) == ["GEN-11", "HEME-01", "NEURO-04"]
    assert sess["why"]["NEURO-04"] == "new" and sess["case"]["diagnosis"] == "SECRET-DIAGNOSIS"
    stems = {i["topic"]: i.get("stem") for i in sess["items"]}
    assert stems["HEME-01"].startswith("Microcytic")
    doc = rnd.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["title"] == record["title"] and doc["format"] == record["case_format"]


def test_save_can_be_run_again_with_the_same_result(rnd):
    first = play(rnd).save()
    record = rnd.read_json("record.json")
    again = rnd.save()
    assert again["keys"] == first["keys"] and rnd.read_json("record.json") == record


def test_a_key_that_was_not_graded_is_left_out(rnd):
    grades = dict(GRADES, items=GRADES["items"][:2], gaps=[])
    out = play(rnd, grades=grades).save()
    assert out["keys"] == {"filled": ["Q1", "Q2"], "not_graded": ["case"]}
    record = rnd.read_json("record.json")
    assert "case" not in record and "GEN-11" not in record["selection_reasons"]
    assert record["title"] == "Microcytic anaemia on a PPI, which test first"


def test_what_the_examiner_writes_wins_and_is_reported(rnd):
    grades = json.loads(json.dumps(GRADES))
    grades["items"][0]["retests"] = None                # the item did not test the gap after all
    grades["items"][1]["aspect"] = "diagnosis"
    grades["title"] = "The examiner's title"
    out = play(rnd, grades=grades).save()
    assert out["keys"]["overridden"] == ["Q1.retests", "Q2.aspect"]
    record = rnd.read_json("record.json")
    assert "retests" not in record["items"][0] and record["items"][1]["aspect"] == "diagnosis"
    assert record["title"] == "The examiner's title"


def test_a_round_written_out_in_full_is_recorded_as_before(rnd):
    out = rnd.play_to_feedback().save()                 # ROUND: items with topics, no keys
    assert "keys" not in out
    assert rnd.read_json("record.json")["items"] == ROUND["items"]


def fails(rnd):
    r = rnd.run("--today", "2026-11-01", "save", "--work", rnd.path, ok=False)
    assert r.returncode != 0
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert not os.path.exists(rnd.pub("data", "state.json")), "nothing may be recorded"
    return out["error"]


def test_a_missing_header_is_reported(rnd):
    err = fails(play(rnd, case=CASE_KEY.split("<!-- /key -->")[1]))
    assert "no key header '<!-- key: case -->'" in err and "headers found: Q1, Q2" in err
    assert "Nothing was recorded" in err


def test_no_headers_at_all_is_reported(rnd):
    rnd.play_to_feedback(GRADES)                        # the sealed files of conftest: no headers
    err = fails(rnd)
    assert err.count("no key header") == 3 and "headers found: none" in err


@pytest.mark.parametrize("change,expect", [
    (("topic: HEME-01\n", ""), "sealed_questions.md, key Q1: 'topic' is missing"),
    (("stem_summary: Microcytic anaemia on a PPI, which test first\n", ""), "key Q1: 'stem_summary' is missing"),
    (("aspect: testing", "aspect: treatment"), "key Q2: 'aspect' must be one of diagnosis"),
    (("aspect: testing\n", ""), "key Q2: 'aspect' is missing"),
    (("type: mcq", "type: quiz"), "key Q1: 'type' must be one of mcq, focused, case"),
    (("reason: due", "the reason is that it was due"), "key Q1: line 4 is not 'field: value'"),
    (("label: Iron", "lable: Iron"), "key Q1: 'lable' is not a field of a mcq header"),
    (("<!-- key: Q2 -->", "<!-- key: Q1 -->"), "key Q1: there are two headers with this id"),
    (("type: focused", "type: case"), "key Q2: the case's header is '<!-- key: case -->'"),
])
def test_a_malformed_header_is_reported(rnd, change, expect):
    err = fails(play(rnd, questions=Q_KEYS.replace(*change)))
    assert expect in err


def test_an_unclosed_header_is_reported(rnd):
    err = fails(play(rnd, questions=Q_KEYS.replace("<!-- /key -->\nBest answer", "Best answer")))
    assert "no key header '<!-- key: Q2 -->'" in err
    out = rnd.run("keys", rnd.path, ok=False)
    assert "a key header is not closed" in json.loads(out.stdout)["problems"][0]


def test_every_problem_is_reported_at_once(rnd):
    bad = Q_KEYS.replace("topic: HEME-01\n", "").replace("aspect: testing\n", "")
    err = fails(play(rnd, questions=bad))
    assert "key Q1: 'topic' is missing" in err and "key Q2: 'aspect' is missing" in err


def test_item_problems_in_round_json_are_reported(rnd):
    grades = json.loads(json.dumps(GRADES))
    grades["items"][1]["key"] = "Q1"
    grades["items"].append({"mastery": 3, "coding": {"errors": []}})
    err = fails(play(rnd, grades=grades))
    assert "item 2: key Q1 is already used" in err and "item 4: it has neither \"key\"" in err


def test_a_bad_header_nobody_graded_only_warns(rnd):
    grades = dict(GRADES, items=GRADES["items"][:2], gaps=[])
    out = play(rnd, case=CASE_KEY.replace("patient: 60M\n", ""), grades=grades).save()
    assert any("key case: 'patient' is missing" in w for w in out["warnings"])
    assert out["keys"]["filled"] == ["Q1", "Q2"]


def test_headers_are_read_leniently(rnd):
    loose = (Q_KEYS.replace("<!-- key: Q1 -->", "<!--key: q1-->").replace("type: mcq", "- **Type**: MCQ")
             .replace("stem_summary: Micro", "Stem summary:   Micro").replace("retests: G0001", "retests: none"))
    out = play(rnd, questions=loose).save()
    q1 = rnd.read_json("record.json")["items"][0]
    assert out["keys"]["filled"][0] == "Q1" and q1["type"] == "mcq" and "retests" not in q1
    assert q1["stem_summary"].startswith("Microcytic")


def test_present_never_prints_a_header(rnd):
    play(rnd)
    for name, block in (("sealed_questions.md", "questions"), ("sealed_case.md", "case"), ("sealed_case.md", "bank")):
        shown = rnd.run("present", "--work", rnd.path, "--block", block).stdout
        assert "key:" not in shown and "HEME-01" not in shown and "SECRET-DIAGNOSIS" not in shown


def test_keys_checks_headers_without_printing_content(rnd):
    play(rnd)
    r = rnd.run("keys", rnd.path, "--plan", rnd.p("plan.json"), ok=False)
    out = json.loads(r.stdout)
    assert out["keys"] == {"sealed_questions.md": ["Q1", "Q2"], "sealed_case.md": ["case"]}
    # the plan of this ledger has three MCQs and no focused question: counted, not named
    assert any("the plan has 3 MCQ item(s), the keys have 1" in p for p in out["problems"])
    ok = rnd.run_json("keys", rnd.p("sealed_questions.md"), rnd.p("sealed_case.md"))
    assert ok["ok"] is True and ok["problems"] == []
    rnd.write("sealed_questions.md", Q_KEYS.replace("topic: HEME-01\n", "").replace("aspect: testing", "aspect: Zebra"))
    r = rnd.run("keys", rnd.path, ok=False)
    assert r.returncode == 1
    for word in ("HEME", "NEURO", "GEN-11", "Iron", "Zebra", "SECRET", "Microcytic", "G0001", "RUBRIC"):
        assert word not in r.stdout
    assert "key Q1: 'topic' is missing" in r.stdout


def test_keys_reports_a_sealed_file_without_headers(rnd):
    rnd.play_to_feedback()
    out = json.loads(rnd.run("keys", rnd.path, ok=False).stdout)
    assert out["ok"] is False and sum("no key header" in p for p in out["problems"]) == 2

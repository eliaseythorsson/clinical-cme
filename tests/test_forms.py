"""The engine prints the grading and reflection forms, rubric included (issue #76): once a part's
answers are in, `answer` writes the grading form into round.json (one entry per key id, what the
key headers and the ledger know filled in, the rubric's elements to mark, blanks for the grading),
`save` takes its scaffolding off again, and the reflection form is written the same way when the
reflection arrives."""
import json
import re

import pytest

from examples import cme
from test_keys import CASE_KEY, Q_KEYS
from test_work_folder import rnd  # noqa: F401  (the fixture)


def answered(rnd, *parts, questions=Q_KEYS, case=CASE_KEY):
    """The round started, the sealed files written by the author, the learner's answers filed."""
    rnd.start()
    rnd.write("sealed_questions.md", questions)
    rnd.write("sealed_case.md", case)
    outs = [rnd.answer(p) for p in parts]
    return outs[-1] if outs else None


def form(rnd):
    return rnd.read_json("round.json")


def item(f, kid):
    return next(it for it in f["items"] if it["key"] == kid)


def fill(f, **errors):
    """Grade every item of the form as an examiner would: every rubric element hit."""
    for it in f["items"]:
        for e in it.get("rubric") or []:
            e["mark"], e["quote"], e["note"] = "hit", "the learner's words", "said so"
        it["mastery"], it["confidence"] = 5, "sure"
        if it["type"] == "mcq":
            it["correct"] = True
        if it["type"] == "focused":
            it["coding"]["art"]["TEST"] = 2
        if it["type"] == "case":
            it["coding"]["art"] = {k: 1 for k in cme.ART_MAX}
            it["coding"]["idea"] = {k: 1 for k in cme.IDEA_MAX}
        it["coding"]["errors"] = errors.get(it["key"], [])
    f["key_learning"] = ["Ferritin first.", "LP after a normal late CT."]
    return f


def finish(rnd, f):
    rnd.write("round.json", f)
    rnd.write("feedback_questions.md", "Feedback on the questions, as sent")
    rnd.write("stage2.md", "Stage 2")
    rnd.write("feedback.md", "Final feedback, as sent")
    return rnd.run("--today", "2026-11-01", "save", "--work", rnd.path, ok=False)


# ---------------------------------------------------------------- the grading form

def test_the_questions_answers_bring_the_form_for_the_questions_only(rnd):
    out = answered(rnd, "questions")
    assert out["form"] == {"file": "round.json", "added": ["Q1", "Q2"], "draft": "questions"}
    f = form(rnd)
    assert [it["key"] for it in f["items"]] == ["Q1", "Q2"]
    q1, q2 = f["items"]
    assert (q1["type"], q1["topic"], q1["label"], q1["retests"]) == ("mcq", "HEME-01", "Iron deficiency anaemia", "G0001")
    assert "rubric" not in q1 and q1["correct"] is None and "art" not in q1["coding"]
    assert (q2["type"], q2["topic"], q2["aspect"]) == ("focused", "NEURO-04", "testing")
    assert [e["element"] for e in q2["rubric"]] == ["RUBRIC-DECISION: lumbar puncture",
                                                     "RUBRIC-REASON: CT sensitivity falls after six hours"]
    assert all(e["mark"] is None for e in q2["rubric"])
    assert q2["mastery"] is None and q2["confidence"] is None
    assert q2["coding"] == {"art": {k: None for k in cme.ART_MAX}, "errors": []}
    # the case stays sealed: nothing of its key, its rubric or its header is in the form yet
    text = json.dumps(f)
    for word in ("SECRET-DIAGNOSIS", "RUBRIC-DDX", "RUBRIC-MGMT", "GEN-11"):
        assert word not in text
    assert f["gaps"] == [] and f["reading"] == [] and f["listening"] == []


def test_the_form_carries_its_instructions_and_the_engines_codes(rnd):
    answered(rnd, "questions")
    guide = form(rnd)["_form"]
    codes = guide["codes"]
    assert codes["error_category"] == list(cme.ERROR_CATEGORIES) and codes["severity"] == list(cme.SEVERITIES)
    assert codes["bias"][:-1] == list(cme.BIASES) and codes["knowledge_type"] == list(cme.KNOWLEDGE_TYPES)
    assert set(codes["art"]) == set(cme.ART_MAX) and set(codes["idea"]) == set(cme.IDEA_MAX)
    assert codes["rubric_mark"] == list(cme.RUBRIC_MARKS) == ["hit", "partial", "missed"]
    assert codes["drill_result"] == list(cme.DRILL_RESULTS)
    assert any("rubric element" in line for line in guide["how"])
    assert {"error", "gap", "reading", "listening"} <= set(guide["shapes"])


def test_the_case_is_added_when_its_last_answer_is_in_and_the_grading_so_far_is_kept(rnd):
    answered(rnd, "questions")
    f = form(rnd)
    item(f, "Q1").update(mastery=4, correct=True)
    rnd.write("round.json", f)
    assert "form" not in rnd.answer("case")         # an unfolding case: Stage 1 only, still sealed
    assert [it["key"] for it in form(rnd)["items"]] == ["Q1", "Q2"]
    out = rnd.answer("final")
    assert out["form"]["added"] == ["case"]
    f = form(rnd)
    assert item(f, "Q1")["mastery"] == 4 and item(f, "Q1")["correct"] is True
    case = item(f, "case")
    assert [(e.get("stage"), e["element"]) for e in case["rubric"]] == [
        (1, "RUBRIC-DDX: secretitis in the differential"), (1, "RUBRIC-TEST: CT abdomen ordered"),
        (2, "RUBRIC-MGMT: excision")]
    assert set(case["coding"]) == {"art", "idea", "errors"}


def test_answering_a_part_again_never_overwrites_the_form(rnd):
    answered(rnd, "questions")
    f = form(rnd)
    item(f, "Q2")["rubric"][0]["mark"] = "partial"
    rnd.write("round.json", f)
    out = rnd.answer("questions", "and one more thing")
    assert out["form"]["added"] == []
    assert item(form(rnd), "Q2")["rubric"][0]["mark"] == "partial"


def test_a_round_json_written_out_in_full_is_left_alone(rnd):
    rnd.start()
    rnd.write("sealed_questions.md", Q_KEYS)
    rnd.write("round.json", {"items": [{"type": "mcq", "topic": "X-01", "mastery": 4}]})
    out = rnd.answer("questions")
    assert "kept" in out["form"] and form(rnd)["items"] == [{"type": "mcq", "topic": "X-01", "mastery": 4}]


def test_a_key_without_a_rubric_block_is_named(rnd):
    out = answered(rnd, "questions", questions=cme.RUBRIC_RE.sub("", Q_KEYS))
    assert out["form"]["rubric_missing"] == ["Q2"] and item(form(rnd), "Q2")["rubric"] == []


# ---------------------------------------------------------------- save reads the filled form

def test_a_filled_form_is_saved_without_its_scaffolding(rnd):
    answered(rnd, "questions", "case", "final")
    r = finish(rnd, fill(form(rnd)))
    assert r.returncode == 0, r.stdout
    out = json.loads(r.stdout)
    assert out["keys"]["filled"] == ["Q1", "Q2", "case"] and "overridden" not in out["keys"]
    assert not [w for w in out["warnings"] if "rubric" in w or "not scored" in w]
    record = rnd.read_json("record.json")
    assert "_form" not in record and all("given" not in it for it in record["items"])
    q2 = item(record, "Q2")
    assert q2["coding"]["art"] == {"TEST": 2}                   # the blanks of a focused question dropped
    assert [e["mark"] for e in q2["rubric"]] == ["hit", "hit"]  # the marks stay in the record
    st = rnd.read_json("publish", "data", "state.json")
    assert "rubric" not in json.dumps(st["sessions"][-1]) and "\"_form\"" not in json.dumps(st)


def test_a_blank_score_stops_the_save_and_nothing_is_recorded(rnd):
    answered(rnd, "questions", "case", "final")
    f = fill(form(rnd))
    item(f, "Q2")["mastery"] = None
    item(f, "Q1")["correct"] = None
    r = finish(rnd, f)
    out = json.loads(r.stdout)
    assert r.returncode != 0 and "Q2 mastery" in out["error"] and "Q1 correct" in out["error"]
    assert "Nothing was recorded" in out["error"]
    assert not rnd.read_json("publish.json")["files"]


def test_unmarked_elements_and_missing_error_records_are_warned(rnd):
    answered(rnd, "questions", "case", "final")
    f = fill(form(rnd))
    case = item(f, "case")
    case["rubric"][0]["mark"] = None
    case["rubric"][2]["mark"] = "missed"
    case["coding"]["idea"]["A"] = None
    r = finish(rnd, f)
    assert r.returncode == 0, r.stdout
    warnings = json.loads(r.stdout)["warnings"]
    assert "case: 1 rubric element(s) not marked hit / partial / missed" in warnings
    assert any(w.startswith("case: 1 rubric element(s) missed or partial but 0 error record(s)") for w in warnings)
    assert "case: idea not scored: A" in warnings


def test_a_blank_confidence_is_no_confidence(rnd):
    answered(rnd, "questions", "case", "final")
    f = fill(form(rnd))
    item(f, "Q1")["confidence"] = None
    assert finish(rnd, f).returncode == 0
    assert "confidence" not in item(rnd.read_json("record.json"), "Q1")


# ---------------------------------------------------------------- the reflection form

def saved(rnd):
    answered(rnd, "questions", "case", "final")
    r = finish(rnd, fill(form(rnd)))
    assert r.returncode == 0, r.stdout


def test_the_reflection_brings_its_form(rnd):
    saved(rnd)
    out = rnd.answer("reflection")
    assert out["form"] == {"file": "reflection.json", "session": "S0001", "topics": 3}
    f = rnd.read_json("reflection.json")
    assert f["topic_comfort"] == {"HEME-01": None, "NEURO-04": None, "GEN-11": None}
    assert [(i["item"], i["topic"]) for i in f["_form"]["round"]] == [("Q1", "HEME-01"), ("Q2", "NEURO-04"),
                                                                       ("case", "GEN-11")]
    assert f["learner_stops"] == [] and "position" in f["_form"]["shapes"]["learner_stop"]
    assert f["performance"] is None and f["skipped"] is False


def test_the_reflection_form_as_filled_is_applied_by_close(rnd):
    saved(rnd)
    rnd.answer("reflection")
    f = rnd.read_json("reflection.json")
    f["topic_comfort"].update({"HEME-01": 4, "GEN-11": 2})          # NEURO-04 left blank
    f["performance"] = 3
    f["learner_stops"] = [{"item": "Q2", "type": "focused", "topic": "NEURO-04", "score": None,
                           "position": {"point": "", "text": ""}}]
    rnd.write("reflection.json", f)
    rnd.write("B.md", "### Discussion (verbatim)\n\nNone.\n")
    out = rnd.run_json("--today", "2026-11-01", "close", "--work", rnd.path)
    assert out["ok"] is True
    sess = rnd.read_json("publish", "data", "state.json")["sessions"][-1]
    assert sess["self_comfort"] == {"HEME-01": 4, "GEN-11": 2} and sess["self_performance"] == 3
    assert sess["stops"][0]["topic"] == "NEURO-04"
    assert not rnd.read_json("publish", "data", "state.json")["positions"]     # an empty note is no note


def test_the_reflection_form_is_written_once(rnd):
    saved(rnd)
    rnd.answer("reflection")
    rnd.write("reflection.json", {"skipped": True})
    out = rnd.answer("reflection", "and also this")
    assert "kept" in out["form"] and rnd.read_json("reflection.json") == {"skipped": True}


def test_a_late_reflection_gets_its_form_from_the_ledger(rnd):
    saved(rnd)
    rnd.publish()
    rnd.forget_job()
    rnd.open(today="2026-11-03")
    out = rnd.answer("reflection")
    assert out["form"]["session"] == "S0001"
    f = rnd.read_json("reflection.json")
    assert set(f["topic_comfort"]) == {"HEME-01", "NEURO-04", "GEN-11"}
    assert {i["topic"] for i in f["_form"]["round"]} == {"HEME-01", "NEURO-04", "GEN-11"}


# ---------------------------------------------------------------- the rubric block (rule 9)

def test_rubric_blocks_are_read_with_their_stages():
    rubrics, problems = cme.parse_rubrics(CASE_KEY + Q_KEYS, "x.md")
    assert problems == [] and set(rubrics) == {"case", "Q2"}
    assert [e.get("stage") for e in rubrics["case"]] == [1, 1, 2]
    loose = "<!-- rubric: q3 -->\n## Stage 1 (reasoning)\n1. first\n* [ ] second\nStage 2: third\n<!-- /rubric -->"
    rubrics, _ = cme.parse_rubrics(loose)
    assert rubrics["Q3"] == [{"element": "first", "stage": 1}, {"element": "second", "stage": 1},
                             {"element": "third", "stage": 2}]


@pytest.mark.parametrize("change, expect", [
    ((cme.RUBRIC_RE, ""), "key Q2: no rubric block"),
    (("- RUBRIC-DECISION: lumbar puncture\n- RUBRIC-REASON: CT sensitivity falls after six hours\n", ""),
     "key Q2: the rubric block has no elements"),
    (("<!-- /rubric -->", ""), "a rubric block is not closed"),
    (("<!-- rubric: Q2 -->", "<!-- rubric: Q1 -->"), "key Q1: an MCQ has no rubric block"),
    (("<!-- rubric: Q2 -->", "<!-- rubric: Q7 -->"), "key Q7: a rubric block without a key header"),
])
def test_keys_requires_a_rubric_block_and_names_no_content(rnd, change, expect):
    rnd.start()
    old, new = change
    rnd.write("sealed_questions.md", old.sub(new, Q_KEYS) if hasattr(old, "sub") else Q_KEYS.replace(old, new))
    rnd.write("sealed_case.md", CASE_KEY)
    r = rnd.run("keys", rnd.p("sealed_questions.md"), rnd.p("sealed_case.md"), ok=False)
    assert r.returncode == 1 and expect in r.stdout
    assert "RUBRIC" not in r.stdout and "lumbar" not in r.stdout


def test_a_rubric_inside_the_text_to_present_is_refused(rnd):
    rnd.start()
    leaked = Q_KEYS.replace("Question 2 — focused. stem\n", "Question 2 — focused. stem\n<!-- rubric: Q9 -->\n- x\n"
                            "<!-- /rubric -->\n")
    rnd.write("sealed_questions.md", leaked)
    r = rnd.run("keys", rnd.p("sealed_questions.md"), ok=False)
    assert "a rubric block sits inside the text to present" in r.stdout


def test_present_never_prints_a_rubric(rnd):
    answered(rnd)
    shown = rnd.run("present", "--work", rnd.path, "--block", "questions").stdout
    assert "RUBRIC" not in shown and "rubric" not in shown


def test_the_rulebook_examples_are_clean_rubric_blocks():
    import os
    with open(os.path.join(os.path.dirname(cme.__file__), "..", "references", "standards.md"), encoding="utf-8") as fh:
        text = fh.read()
    examples = "\n".join(re.findall(r"^```\n(.*?)^```", text, re.S | re.M))
    rubrics, problems = cme.parse_rubrics(examples, "standards.md")
    assert problems == [] and set(rubrics) == {"Q4", "case"}
    assert {e.get("stage") for e in rubrics["case"]} == {1, 2}


def test_the_form_gives_the_position_notes_and_the_depth_answer_printed(work):
    from test_stop import POSITION, stopped_ledger
    stopped_ledger(work)
    work.forget_job()
    work.open(today="2027-02-01")
    work.write("sealed_questions.md", "<!-- key: Q1 -->\ntype: mcq\ntopic: GEN-11\nlabel: l\nreason: due\n"
               "stem_summary: s\n<!-- /key -->\nKEY Q1: B\n<!-- present: questions -->\nQ1. stem\n<!-- /present -->\n")
    out = work.run_json("--today", "2027-02-01", "answer", "--work", work.path, "--part", "questions", "--text", "B")
    given = work.read_json("round.json")["items"][0]["given"]
    assert given["positions"] == out["positions"]["Q1"] and given["positions"][0]["text"] == POSITION["text"]
    assert out["depth"]["Q1"]["level"] > 1 and given["depth"] == out["depth"]["Q1"]

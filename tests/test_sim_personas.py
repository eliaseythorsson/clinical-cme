"""The simulated learners beyond `strong`, and the clinical-quality score: no LLM anywhere.

Each persona's round is scripted the way the protocol says it should go (SKILL.md turns 2 and 5),
then the automatic checks, the persona's own check and the report are shown to pass, and to fail
when the matching fault is injected. The quality scorer is an agent in a real simulation; here its
form is filled in by the test."""
import copy
import json
import os
import shutil

import pytest

from test_simulation import ANSWERS, FEEDBACK, PART_B, ROUND, TODAY, Script, sim, sim_json

PERSONAS = {"strong": [], "weak-overconfident": [], "disputes": ["dispute"], "stops-halfway": ["stopped"]}

DISPUTE = """I don't accept the mark on treatment duration in the case.
I wrote a week on purpose: the 2024 European guidance allows seven days when the response is prompt.
Please reconsider that grade."""
SETTLEMENT = """You are right that the European guidance allows it: I re-read the recommendation, and seven days is supported when the response is prompt.

Both positions are defensible, so the case goes from 4 to 4.5. Your reflection, when you are ready?
"""
REFLECTION_AFTER = "Accepted, thanks. " + ANSWERS["reflection"]
GRADE_CHANGE = {"item": "Case stage 2", "topic": "GEN-11", "from": 4, "to": 4.5, "outcome": "both_defensible"}
EXCHANGE = "**Learner**\n\n%s\n\n**Examiner**\n\n%s" % (DISPUTE, SETTLEMENT.strip())

STOP = "Bleep's gone off. No time for the case today, stop here and save what I've done."
SUMMARY = """Understood: we stop here, and the case is left for another day.

Gap summary: both questions answered well; nothing new to revisit.

Reflection: comfort per topic 1-5, your own rating 1-5, what felt solid, what felt shaky?
"""
PLAN = {"items": [{"slot": "case", "topic": "GEN-11", "domain": "GEN",
                   "label": "Patient safety, quality improvement, high-value care"},
                  {"slot": "mcq", "topic": "HEME-01"}, {"slot": "focused", "topic": "NEURO-04"}]}


def part_b(reflection, discussion="None.", changes="None."):
    return ("### Reflection (verbatim)\n\n%s\n\n### Discussion (verbatim)\n\n%s\n\n### Grade changes\n\n%s\n\n"
            "### Coded analysis\n\nDG 2 · one bullet per item.\n" % (reflection, discussion, changes))


class Weak(Script):
    """Wrong and sure of it; otherwise the round runs as usual."""
    persona = "weak-overconfident"

    def play(self):
        rnd = copy.deepcopy(ROUND)
        rnd["items"][0].update(mastery=1, correct=False, confidence="sure")
        rnd["items"][2].update(mastery=2, confidence="sure")
        self.open_round()
        self.case()
        self.save(rnd)
        self.close()
        return self


class Disputes(Script):
    """Challenges a grade after the final feedback; the examiner settles it before the reflection."""
    persona = "disputes"

    def play(self):
        self.open_round()
        self.case()
        mid_round = "settled_before_the_save" in self.faults
        if not mid_round:
            self.save()
        self.send("learner", DISPUTE, 45)
        self.turn_end("learner")
        self.send("examiner", SETTLEMENT, 35)
        if mid_round:        # the exchange goes into the notes, the change into the round itself
            rnd = copy.deepcopy(ROUND)
            rnd["items"][2]["mastery"] = 4.5
            rnd["grade_changes"] = [GRADE_CHANGE]
            self.save(rnd, answers={"notes": EXCHANGE}, parts=("questions", "case", "final", "notes"))
            self.close(part_b=part_b(REFLECTION_AFTER, changes="Case stage 2: 4 → 4.5, both defensible."),
                       reflection_text=REFLECTION_AFTER)
            return self
        self.turn_end("examiner", 5)
        reflection = {"topic_comfort": {"GEN-11": 4}, "performance": 4, "solid": "a", "gaps": "b",
                      "grade_changes": [GRADE_CHANGE], "items": [{"type": "case", "topic": "GEN-11", "mastery": 4.5}]}
        discussion, changes = EXCHANGE, "Case stage 2: 4 → 4.5. Seven days is supported; both defensible."
        if "dispute_not_recorded" in self.faults:
            del reflection["grade_changes"], reflection["items"]
            changes = "None."
        if "dispute_not_settled" in self.faults:
            reflection["grade_changes"] = [dict(GRADE_CHANGE, outcome=None)]
        if "dispute_not_logged" in self.faults:
            discussion = "None."
        if "dispute_paraphrased" in self.faults:
            discussion = "The learner questioned the treatment duration; the examiner agreed that a week is defensible."
        self.close(reflection, part_b(REFLECTION_AFTER, discussion, changes), REFLECTION_AFTER)
        return self


class Stops(Script):
    """Answers the short questions, then stops when the case arrives."""
    persona = "stops-halfway"

    def play(self):
        self.put("plan.json", PLAN)
        self.open_round()
        self.send("learner", STOP, 20)
        self.turn_end("learner")
        summary = SUMMARY
        if "names_the_case" in self.faults:
            summary = summary.replace("another day.", "another day (it was fictitious secretitis, GEN-11).")
        self.send("examiner", summary, 15)
        rnd = copy.deepcopy(ROUND)
        rnd.update(title="Two short questions: anaemia work-up and thunderclap headache", gaps=[])
        if "case_recorded_anyway" in self.faults:
            rnd["items"][2].update(mastery=0, confidence=None)
        else:
            del rnd["items"][2], rnd["case"], rnd["case_format"]
        self.save(rnd, feedback=summary, answers={"notes": STOP}, parts=("questions", "notes"))
        self.close({"topic_comfort": {"HEME-01": 4}, "performance": 4, "solid": "a", "gaps": "b"})
        return self


@pytest.fixture
def play(tmp_path):
    return lambda cls, *faults: cls(tmp_path, faults).play()


def fill_form(run, score=4, **changes):
    """What the scorer agent does: fill in the form the harness wrote."""
    path = os.path.join(run, "quality.json")
    form = json.load(open(path, encoding="utf-8"))
    for row in form["items"] + form["feedback"]:
        row.update(score=score, note="note on %s" % row["id"])
    form.update(scorer_model="model-q", overall={"score": score, "note": "sound round"})
    form.update(changes)
    json.dump(form, open(path, "w", encoding="utf-8"))
    return form


# ---------------------------------------------------------------- the personas

@pytest.mark.parametrize("persona", sorted(PERSONAS))
def test_every_persona_sets_up_a_run_and_the_examiner_is_not_told_which(tmp_path, persona):
    run = str(tmp_path / "run")
    out = sim_json("init", "--persona", persona, "--run", run, "--today", TODAY)
    meta = json.load(open(os.path.join(run, "run.json")))
    assert meta["persona"] == persona and meta["expect"] == PERSONAS[persona]
    profile = json.load(open(os.path.join(run, "store", "data", "state.json")))["profile"]
    assert profile["display_name"].startswith("Dr Sim") and "expect" not in profile   # harness-only key
    assert os.path.isfile(os.path.join(run, "ledger_at_start.json"))
    examiner = open(out["examiner_prompt"]).read().replace(run, "<run>")     # the test's own folder name aside
    assert persona not in examiner and "persona" not in examiner.lower()
    assert persona + ".md" in open(out["learner_prompt"]).read()


def test_default_run_folder_does_not_name_the_persona():
    # the run folder's path is in the examiner's brief
    out = sim_json("init", "--persona", "stops-halfway", "--today", TODAY)
    try:
        assert "stops" not in out["run"] and "stops" not in open(out["examiner_prompt"]).read()
    finally:
        shutil.rmtree(out["run"])


def test_persona_expecting_an_unknown_check_is_refused(tmp_path):
    persona = tmp_path / "odd.md"
    persona.write_text('```json\n{"display_name": "Dr Odd", "expect": ["miracle"]}\n```\nBrief.\n')
    r = sim("init", "--persona", str(persona), "--run", str(tmp_path / "run"), ok=False)
    assert r.returncode == 2 and "miracle" in r.stderr


def test_weak_overconfident_round_passes_the_checks_and_its_confident_misses_are_counted(play):
    out, rep = play(Weak).report()
    assert out["ok"] is True and out["checks"] == {"blinding": True, "saved": True, "log": True}
    assert rep["persona"] == "weak-overconfident" and rep["round"]["confident_misses"] == 2


def test_dispute_round_holds_a_settled_dispute_in_the_log_and_the_grade_changes(play):
    s = play(Disputes)
    out, rep = s.report()
    assert out["ok"] is True
    assert out["checks"] == {"blinding": True, "saved": True, "log": True, "dispute": True}
    d = rep["checks"]["dispute"]
    assert d["grade_changes"] == [GRADE_CHANGE] and d["logged_in"] == ["discussion"]
    # the ledger and the session document say the same
    sess = json.load(open(os.path.join(s.store, "data", "state.json")))["sessions"][-1]
    assert sess["grade_changes"] == [GRADE_CHANGE] and sess["items"][2]["mastery"] == 4.5
    doc = json.load(open(os.path.join(s.store, "data", "sessions", "S0001.json")))
    assert DISPUTE in doc["closing"] and "4 → 4.5" in doc["closing"]
    md = open(out["report"], encoding="utf-8").read()
    assert "Case stage 2 4 → 4.5 (both_defensible)" in md and "exchange logged under: discussion" in md
    assert "European guidance" not in md          # the report holds results, not the exchange


def test_dispute_settled_before_the_first_save_is_found_in_the_notes(play):
    out, rep = play(Disputes, "settled_before_the_save").report()
    assert out["ok"] is True and rep["checks"]["dispute"]["logged_in"] == ["notes"]
    assert rep["checks"]["dispute"]["grade_changes"] == [GRADE_CHANGE]


@pytest.mark.parametrize("fault,problem", [
    ("dispute_not_recorded", "records no grade change"),
    ("dispute_not_settled", "is not settled"),
    ("dispute_not_logged", "holds the dispute word for word"),
    ("dispute_paraphrased", "holds the dispute word for word"),
])
def test_dispute_that_is_not_recorded_settled_or_logged_fails(play, fault, problem):
    out, rep = play(Disputes, fault).report()
    assert out["ok"] is False and out["checks"]["dispute"] is False
    assert any(problem in p for p in rep["checks"]["dispute"]["problems"])
    assert "**FAIL**" in open(out["report"], encoding="utf-8").read()


def test_dispute_is_only_demanded_of_the_dispute_persona(play):
    out, rep = play(Weak).report()
    assert "dispute" not in rep["checks"] and "stopped" not in rep["checks"]


def test_stopped_round_is_saved_without_the_case_and_its_topic_is_still_due(play):
    s = play(Stops)
    out, rep = s.report()
    assert out["ok"] is True
    assert out["checks"] == {"blinding": True, "saved": True, "log": True, "stopped": True}
    st = rep["checks"]["stopped"]
    assert st["case_topic"] == "GEN-11" and st["items_saved"] == 2
    assert st["case_topic_schedule"] == {"last": None, "attempts": 0, "step": 0, "due": None}   # never tested: still to come
    assert rep["round"]["shape"] == "1 MCQ, 1 focused"
    ledger = json.load(open(os.path.join(s.store, "data", "state.json")))
    sess = ledger["sessions"][-1]
    assert [it["type"] for it in sess["items"]] == ["mcq", "focused"] and sess["case"] is None
    assert "GEN-11" not in sess["topics"] and not (ledger["topics"].get("GEN-11") or {}).get("last")
    assert ledger["topics"]["HEME-01"]["due"] and ledger["unreflected"] is None
    # the case stays sealed to the end of the round, and the learner's stop is in the log
    b = rep["checks"]["blinding"]
    assert b["never_lifted"] == ["case"] and b["seal_lifted_at"] == {"questions": 3} and b["leaks"] == 0
    doc = json.load(open(os.path.join(s.store, "data", "sessions", "S0001.json")))
    assert STOP in doc["transcript"]


def test_stopped_round_that_records_the_case_fails(play):
    out, rep = play(Stops, "case_recorded_anyway").report()
    assert out["checks"]["stopped"] is False
    probs = rep["checks"]["stopped"]["problems"]
    assert any("holds a case" in p for p in probs)
    assert any("GEN-11 is recorded as tested" in p for p in probs)
    assert any("schedule of the case's topic GEN-11 changed" in p for p in probs)


def test_naming_the_unanswered_case_after_the_stop_is_a_leak(play):
    out, rep = play(Stops, "names_the_case").report()
    assert out["checks"]["blinding"] is False and out["checks"]["stopped"] is True
    kinds = {f["kind"] for f in rep["checks"]["blinding"]["findings"] if f["part"] == "case" and f["level"] == "fail"}
    assert kinds == {"blueprint ID", "diagnosis"}


def test_stop_expected_but_the_round_ran_to_the_end_fails(tmp_path):
    class Stays(Script):
        persona = "stops-halfway"
    out, rep = Stays(tmp_path).play().report()
    assert out["checks"]["stopped"] is False
    assert any("holds a case" in p for p in rep["checks"]["stopped"]["problems"])


# ---------------------------------------------------------------- the clinical-quality score

def test_quality_form_lists_every_item_and_every_feedback(play):
    s = play(Script)
    out = sim_json("quality", "--run", s.run)
    form = json.load(open(out["form"]))
    assert [(r["id"], r["type"], r["topic"]) for r in form["items"]] == [
        ("Q1", "mcq", "HEME-01"), ("Q2", "focused", "NEURO-04"), ("Case", "case", "GEN-11")]
    assert [r["id"] for r in form["feedback"]] == ["questions", "final"]
    assert all(r["score"] is None for r in form["items"] + form["feedback"])
    brief = open(out["quality_prompt"]).read()
    assert "{" not in brief and out["form"] in brief and os.path.join(s.run, "messages") in brief
    # asked again before the scorer has filled it in: says what is missing, and keeps the form
    again = sim_json("quality", "--run", s.run)
    assert again["ok"] is False and "items Q1 has no score" in again["problems"]


def test_quality_scores_are_recorded_per_item_and_per_feedback(play):
    s = play(Script)
    sim("quality", "--run", s.run)
    form = fill_form(s.run, concerns=["Q1: the ferritin threshold looks dated"])
    form["items"][0].update(score=2, note="second defensible answer. " + "x" * 400)
    json.dump(form, open(os.path.join(s.run, "quality.json"), "w"))
    assert sim_json("quality", "--run", s.run)["ok"] is True
    out, rep = s.report()
    q = rep["quality"]
    assert [(r["id"], r["score"]) for r in q["items"]] == [("Q1", 2), ("Q2", 4), ("Case", 4)]
    assert [(r["id"], r["score"]) for r in q["feedback"]] == [("questions", 4), ("final", 4)]
    assert q["items"][0]["topic"] == "HEME-01" and len(q["items"][0]["note"]) <= 200     # one line, clipped
    assert q["item_mean"] == 3.33 and q["feedback_mean"] == 4.0 and q["score"] == 4
    assert q["scorer_model"] == "model-q" and q["concerns"] == ["Q1: the ferritin threshold looks dated"]
    assert q["problems"] == [] and out["quality"] == {"item_mean": 3.33, "feedback_mean": 4.0, "score": 4}
    md = open(out["report"], encoding="utf-8").read()
    assert "## Clinical quality" in md and "| Item | Q1 (mcq, HEME-01) | 2 |" in md
    assert "| Feedback | final | 4 |" in md and "items 3.33/5 (n=3), feedback 4.0/5 (n=2), overall 4/5" in md


def test_low_or_missing_quality_scores_never_fail_a_run(play):
    # ADR 0004: the score is logged, never a pass bar
    s = play(Script)
    sim("quality", "--run", s.run)
    form = fill_form(s.run, score=1)
    form["items"][1]["score"] = None
    form["feedback"][0]["score"] = 7
    form["items"].append({"id": "Q9", "score": 3})
    json.dump(form, open(os.path.join(s.run, "quality.json"), "w"))
    out, rep = s.report()
    assert out["ok"] is True and rep["ok"] is True
    assert sim("check", "--run", s.run).returncode == 0
    q = rep["quality"]
    assert [r["id"] for r in q["items"]] == ["Q1", "Case"] and [r["id"] for r in q["feedback"]] == ["final"]
    assert q["problems"] == ["items Q2 has no score", 'items "Q9" is not part of this round; ignored',
                             "feedback questions: score 7 is not a whole number 1-5"]
    assert "recorded, not a failure" in open(out["report"], encoding="utf-8").read()


def test_report_without_a_scorer_says_not_scored(play):
    out, rep = play(Script).report()
    assert rep["quality"] is None and "| Clinical quality (logged only) | not scored |" in open(out["report"]).read()


def test_dispute_round_also_asks_for_a_score_on_the_examiners_reply(play):
    s = play(Disputes)
    form = json.load(open(sim_json("quality", "--run", s.run)["form"]))
    assert [r["id"] for r in form["feedback"]] == ["questions", "final", "dispute"]


def test_stopped_round_offers_the_unanswered_case_for_scoring_without_requiring_it(play):
    s = play(Stops)
    form = json.load(open(sim_json("quality", "--run", s.run)["form"]))
    assert [(r["id"], r["answered"]) for r in form["items"]] == [("Q1", True), ("Q2", True), ("Case", False)]
    form = fill_form(s.run)
    form["items"][2]["score"] = None                  # the scorer may leave an unanswered case unrated
    json.dump(form, open(os.path.join(s.run, "quality.json"), "w"))
    _, rep = s.report()
    assert rep["quality"]["problems"] == [] and [r["id"] for r in rep["quality"]["items"]] == ["Q1", "Q2"]


def test_history_lines_up_the_reports_for_comparison(play, tmp_path):
    s = play(Script)
    s.report()
    sim("quality", "--run", s.run)
    fill_form(s.run, score=5)
    s.report()
    rows = json.loads(sim("history", "--reports", s.reports, "--json").stdout)
    assert [r["report"] for r in rows] == ["%s-strong" % rows[0]["report"][:10], "%s-strong-2" % rows[0]["report"][:10]]
    assert [r["quality_items"] for r in rows] == [None, 5.0] and all(r["checks"] == "pass" for r in rows)
    table = sim("history", "--reports", s.reports).stdout
    assert table.count("\n") == 4 and "| pass |" in table
    assert json.loads(sim("history", "--reports", s.reports, "--persona", "disputes", "--json").stdout) == []

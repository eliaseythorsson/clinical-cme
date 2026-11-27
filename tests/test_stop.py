"""The learner's stop and the position note (issue #75): "I know this, stop bringing it back" is
one amendment of a round (the learner's score, every gap on the topic closed, the topic at the
longest interval), the same before or after the close; a position note said with it is kept in
the learner's words, carried to the author and the examiner, listed at the review to keep or
drop, and lapses after about six months."""
import copy
import datetime as dt
import json

import pytest

import examples
from conftest import REFLECTION, ROUND, Work
from examples import LEDGERS, cme

POSITION = {"point": "first-line choice in this setting", "text": "I hold that the older drug is fine here, in my words"}
STOP = {"item": "Case", "type": "case", "topic": "GEN-11", "position": POSITION}


def closed(work, reflection=None, config=None):
    work.init(config=config)
    work.save_round("2026-11-02")
    out = work.close_round("2026-11-02", reflection)
    work.publish()
    return out


def override(work, *args, today="2026-11-02", ok=True):
    r = work.run("--today", today, "override", "--work", work.path, *args, ok=ok)
    return json.loads(r.stdout)


def session(st, sid="S0001"):
    return next(s for s in st["sessions"] if s["id"] == sid)


def plain(st):
    st = json.loads(json.dumps(st))
    st.pop("gen", None)
    for p in st.get("positions") or []:
        p.pop("from", None)
    # an example ledger from before the counters gets them (at zero) once anything is counted
    if not any((st.get("agg") or {}).get("overrides", {}).values()):
        (st.get("agg") or {}).pop("overrides", None)
    return st


# ---- one sentence, one command ------------------------------------------------------------------

def test_a_stop_in_the_reflection_sets_the_score_closes_the_gaps_and_goes_to_the_longest_interval(work):
    out = closed(work, dict(REFLECTION, learner_stops=[STOP]))
    st = work.read_ledger()
    it = next(i for i in session(st)["items"] if i["topic"] == "GEN-11")
    assert (it["mastery"], it["graded"], it["set_by"]) == (cme.STOP_SCORE, 2, "learner")
    gc = session(st)["grade_changes"][-1]
    assert gc["outcome"] == "learner_set" and gc["stop"] is True and gc["to"] == 5
    t = st["topics"]["GEN-11"]
    intervals = st["config"]["intervals_days"]
    assert t["step"] == len(intervals) - 1 and t["stopped"] == "2026-11-02"
    assert t["due"] == cme.iso(dt.date(2026, 11, 2) + dt.timedelta(days=intervals[-1]))
    # every gap on the topic is closed by the learner, the one this round opened included
    assert "GEN-11" not in {g["topic"] for g in st["gaps"]}
    r = st["resolved"][-1]
    assert (r["topic"], r["closed_by"], r.get("stop")) == ("GEN-11", "learner", True)
    assert session(st)["stops"] == [{"topic": "GEN-11", "date": "2026-11-02", "item": "Case"}]
    assert session(st)["learner_closed_gaps"] == [{"id": r["id"], "topic": "GEN-11", "stop": True}]
    # the position note, word for word
    (p,) = st["positions"]
    assert (p["id"], p["topic"], p["point"], p["text"]) == ("P0001", "GEN-11", POSITION["point"], POSITION["text"])
    assert p["set"] == p["confirmed"] == "2026-11-02" and p["session"] == "S0001"
    assert [c["kind"] for c in out["learner_changes"]] == ["stop", "gap"]
    doc = work.read_json("store", "data", "sessions", "S0001.json")
    assert "stopped by the learner" in doc["closing"] and POSITION["text"] in doc["closing"]
    assert "closed with the learner's stop" in doc["closing"]
    # counted apart
    assert st["agg"]["overrides"] == {"scores": 1, "gaps": 1, "stops": 1}


def test_a_stop_overrides_the_drill_down_and_the_misconception(work, tmp_path_factory):
    """A wrong MCQ marked sure: without the stop a confident error back in three days; with it,
    the learner's score and the longest interval."""
    plain_work = Work(tmp_path_factory.mktemp("plain"))
    closed(plain_work)
    assert plain_work.read_ledger()["topics"]["NEURO-04"]["calibration"] == "confident_error"
    closed(work, dict(REFLECTION, learner_stops=[{"topic": "NEURO-04", "score": 3}]))
    st = work.read_ledger()
    t = st["topics"]["NEURO-04"]
    assert t["mastery"] == 3 and t["calibration"] != "confident_error"
    assert t["step"] == len(st["config"]["intervals_days"]) - 1
    assert "NEURO-04" not in {g["topic"] for g in st["gaps"]} and "positions" not in st


def test_a_stop_after_the_close_equals_the_same_stop_in_the_reflection(work, tmp_path_factory):
    ref = Work(tmp_path_factory.mktemp("ref"))
    closed(ref, dict(REFLECTION, learner_stops=[STOP]))
    closed(work)
    out = override(work, "--stops", json.dumps([STOP]))
    assert out["ok"] and out["topics"]["GEN-11"]["stopped"] is True
    assert [c["kind"] for c in out["learner_changes"]] == ["stop", "gap"]
    assert out["learner_changes"][0]["position"]["id"] == "P0001"
    work.publish()
    want, st = ref.read_ledger(), work.read_ledger()
    for k in ("topics", "gaps", "resolved", "agg", "positions"):
        assert plain(st)[k] == plain(want)[k], k
    assert session(st) == session(want)
    assert st["positions"][0]["from"] == "override"
    doc = work.read_json("store", "data", "sessions", "S0001.json")
    assert "stopped by the learner" in doc["addendum"] and POSITION["text"] in doc["addendum"]


@pytest.mark.parametrize("name", list(LEDGERS))
def test_on_every_example_ledger_the_stop_gives_the_same_ledger_either_side_of_the_close(name):
    st = examples.load_ledger(name)
    day = examples.today_of(name)
    rnd = examples.round_for(st, cme.plan_round(st, examples.plan_options(), day))
    cme.record_round(st, copy.deepcopy(rnd), day)
    refl, later = examples.reflection_for(rnd), day + dt.timedelta(days=1)
    it = rnd["items"][-1]
    req = {"topic": it["topic"], "type": it["type"], "position": POSITION}
    before = copy.deepcopy(st)
    cme.reflect_round(before, dict(refl, learner_stops=[req]), later)
    after = copy.deepcopy(st)
    cme.reflect_round(after, refl, later)
    changes, topics, warnings = cme.amend_round(after, rnd["log_id"], [], [], cme.iso(day), later, [req])
    assert warnings == [] and changes[0]["kind"] == "stop"
    assert plain(after) == plain(before)
    t = after["topics"][it["topic"]]
    assert t["step"] == len(after["config"]["intervals_days"]) - 1 and t["stopped"]
    assert not [g for g in after["gaps"] if g["topic"] == it["topic"]]


@pytest.mark.parametrize("name", list(LEDGERS))
def test_a_stop_taken_out_again_leaves_no_trace(name):
    """Undoing the round undoes the stop: the topic's mark, its gaps and its schedule."""
    st = examples.load_ledger(name)
    day = examples.today_of(name)
    rnd = examples.round_for(st, cme.plan_round(st, examples.plan_options(), day))
    cme.record_round(st, copy.deepcopy(rnd), day)
    it = rnd["items"][0]
    first = copy.deepcopy(st)
    stopped = copy.deepcopy(rnd)
    stopped["stops"] = [{"topic": it["topic"], "date": cme.iso(day)}]
    sess = session(st, rnd["log_id"])
    cme.record_round(st, stopped, day, again=sess)
    assert st["topics"][it["topic"]].get("stopped")
    cme.record_round(st, copy.deepcopy(rnd), day, again=session(st, rnd["log_id"]))
    assert plain(st) == plain(first)


def test_a_stop_on_a_topic_tested_since_amends_the_latest_round_on_it(work):
    closed(work)
    work.forget_job()
    rnd2 = dict(copy.deepcopy(ROUND), log_id="S0002", items=[copy.deepcopy(ROUND["items"][0])], gaps=[])
    work.save_round("2026-11-10", rnd2)
    work.close_round("2026-11-10")
    work.publish()
    work.forget_job()
    work.open(today="2026-11-12")
    out = override(work, "--stops", json.dumps({"topic": "GEN-11", "type": "case"}), "--session", "S0001",
                   today="2026-11-12")
    assert out["warnings"] == []
    work.publish()
    st = work.read_ledger()
    # the score is on the round it was said of; the stop on the latest round on the topic
    assert next(i for i in session(st)["items"] if i["topic"] == "GEN-11")["set_by"] == "learner"
    assert session(st, "S0002")["stops"][0]["topic"] == "GEN-11" and "stops" not in session(st)
    t = st["topics"]["GEN-11"]
    assert t["due"] == cme.iso(dt.date(2026, 11, 10) + dt.timedelta(days=st["config"]["intervals_days"][-1]))
    assert "GEN-11" not in {g["topic"] for g in st["gaps"]}


def test_close_run_again_keeps_one_note(work):
    work.init()
    work.save_round("2026-11-02")
    refl = dict(REFLECTION, learner_stops=[STOP])
    work.close_round("2026-11-02", refl)
    once = work.read_json("publish", "data", "state.json")
    work.close_round("2026-11-02", refl)
    assert work.read_json("publish", "data", "state.json") == once
    assert len(once["positions"]) == 1


def test_a_malformed_stop_writes_nothing(work):
    closed(work)
    before = work.read_json("publish", "data", "state.json")
    for arg, problem in (({"topic": "GEN-11", "position": {"text": "no point"}}, "needs 'point'"),
                         ({"topic": "CARD-01"}, "no item CARD-01"),
                         ({"score": 5}, "a stop needs 'topic'")):
        out = override(work, "--stops", json.dumps(arg), ok=False)
        assert out["ok"] is False and problem in out["error"], out
    assert work.read_json("publish", "data", "state.json") == before


# ---- the note in later rounds -------------------------------------------------------------------

def stopped_ledger(work):
    closed(work, dict(REFLECTION, learner_stops=[STOP]))
    return work.read_ledger()


def test_the_plan_carries_the_note_and_does_not_revisit_a_stopped_topic(work):
    st = stopped_ledger(work)
    args = examples.plan_options(mcqs=10, focused=6, domain="GEN")
    plan = cme.plan_round(st, args, dt.date(2026, 11, 20))
    assert all(c.get("topic") != "GEN-11" for c in plan["items"])     # not due, not revisited
    # once it is due, its item carries the note for the author
    plan = cme.plan_round(st, args, cme.parse_date(st["topics"]["GEN-11"]["due"]))
    c = next(c for c in plan["items"] if c.get("topic") == "GEN-11")
    assert c["positions"]["notes"] == [{"id": "P0001", "point": POSITION["point"], "text": POSITION["text"],
                                        "set": "2026-11-02"}]
    assert "rule 12" in c["positions"]["how"]


def test_answer_gives_the_examiner_the_notes_by_key_id(work):
    stopped_ledger(work)
    work.forget_job()
    work.open(today="2027-02-01")
    work.write("sealed_questions.md", "<!-- key: Q1 -->\ntype: mcq\ntopic: GEN-11\nlabel: l\nreason: due\n"
               "stem_summary: s\n<!-- /key -->\nKEY Q1: B\n<!-- present: questions -->\nQ1. stem\n<!-- /present -->\n"
               "<!-- key: Q2 -->\ntype: mcq\ntopic: PULM-04\nlabel: l\nreason: due\nstem_summary: s\n<!-- /key -->\n")
    out = work.run_json("--today", "2027-02-01", "answer", "--work", work.path, "--part", "questions", "--text", "B")
    (kid, notes), = out["positions"].items()
    assert kid == "Q1"
    assert notes[0]["id"] == "P0001" and notes[0]["text"] == POSITION["text"]


def test_a_note_lapses_after_about_six_months_unless_a_review_keeps_it(work):
    st = stopped_ledger(work)
    day = dt.date(2026, 11, 2)
    assert cme.standing_positions(st, day + dt.timedelta(days=cme.POSITION_LAPSE_DAYS))
    assert not cme.standing_positions(st, day + dt.timedelta(days=cme.POSITION_LAPSE_DAYS + 1))
    # a review keeps it: six months from the review
    work.forget_job()
    work.open(today="2027-01-10")
    s = work.run_json("--today", "2027-01-10", "stats", "--work", work.path)
    assert [(p["id"], p["text"], p["lapses"]) for p in s["positions"]] == [("P0001", POSITION["text"], "2027-05-03")]
    out = work.run_json("--today", "2027-01-10", "review", "--work", work.path, "--review",
                        json.dumps({"positions": {"keep": ["P0001"]}}))
    assert out["positions"] == {"kept": ["P0001"], "dropped": []}
    work.publish()
    p = work.read_ledger()["positions"][0]
    assert p["confirmed"] == "2027-01-10" and p["set"] == "2026-11-02"


def test_a_review_drops_a_note_and_refuses_an_unknown_one(work):
    stopped_ledger(work)
    work.forget_job()
    work.open(today="2027-01-10")
    r = work.run("--today", "2027-01-10", "review", "--work", work.path, "--review",
                 json.dumps({"positions": {"drop": ["P0009"]}}), ok=False)
    assert "no position note P0009" in json.loads(r.stdout)["error"]
    work.run("--today", "2027-01-10", "review", "--work", work.path, "--review",
             json.dumps({"positions": {"drop": ["P0001"]}}))
    work.publish()
    assert work.read_ledger()["positions"] == []


def test_the_learner_drops_a_note_and_a_changed_guideline_is_raised_once(work):
    stopped_ledger(work)
    work.forget_job()
    work.open(today="2027-02-01")
    listed = work.run_json("--today", "2027-02-01", "position", "--work", work.path)
    assert [p["id"] for p in listed["positions"]] == ["P0001"] and "files" not in listed
    out = work.run_json("--today", "2027-02-01", "position", "--work", work.path, "--reopened", "P0001")
    assert out["positions"][0]["reopened"] == "2027-02-01"
    assert "data/prepared.json" not in {f["as"] for f in out["files"]}     # a prepared round stays usable
    r = work.run("--today", "2027-02-02", "position", "--work", work.path, "--reopened", "P0001", ok=False)
    assert "not raised again" in json.loads(r.stdout)["error"]
    work.run("--today", "2027-02-02", "position", "--work", work.path, "--drop", "P0001")
    work.publish()
    assert work.read_ledger()["positions"] == []


def test_the_review_counts_stops_apart(work):
    closed(work, dict(REFLECTION, learner_stops=[STOP]))
    s = work.run_json("--today", "2026-11-03", "stats", "--work", work.path)
    assert s["analysis"]["period"]["learner_overrides"]["stops"] == 1
    assert s["analysis"]["period"]["learner_overrides"]["scores"] == 1
    assert s["analysis"]["all_time"]["learner_overrides"]["stops"] == 1
    assert s["analysis"]["period"]["grade_disputes"]["n"] == 0


def test_the_page_file_lists_the_notes_in_the_learners_words(work):
    stopped_ledger(work)
    page = work.read_json("store", "data", "page.json")
    assert page["positions"] == [{"id": "P0001", "topic": "GEN-11", "label": page["positions"][0]["label"],
                                  "point": POSITION["point"], "text": POSITION["text"], "set": "2026-11-02",
                                  "confirmed": "2026-11-02"}]
    assert "lapses" not in json.dumps(page["positions"]) and "due" not in page["positions"][0]

"""What the learner sets themselves (issue #46): a score ("record it as 4") and a gap closed by
request, in the reflection JSON handled by `close` and with `override` after the close."""
import copy
import json
import re

from conftest import REFLECTION, ROUND

SCORE = {"item": "Case", "type": "case", "topic": "GEN-11", "score": 4, "note": "I said this, in other words"}
CLOSE_GAP = {"topic": "GEN-11", "note": "I know this now"}
DISPUTE = {"item": "Q1", "topic": "PULM-04", "from": 4, "to": 4.5, "outcome": "both_defensible"}


def closed(work, reflection=None, config=None):
    """A round saved, closed and published; returns the close output."""
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


def item(st, topic):
    return next(i for i in session(st)["items"] if i["topic"] == topic)


def stats(work, today="2026-11-03"):
    return work.run_json("--today", today, "stats", "--work", work.path)


def test_learner_set_score_in_the_reflection_keeps_both_scores_and_schedules_with_the_learners(work, tmp_path_factory):
    cfg = {"intervals_days": [1, 10, 20, 40]}
    out = closed(work, dict(REFLECTION, learner_scores=[SCORE]), cfg)
    st = work.read_ledger()
    it = item(st, "GEN-11")
    assert (it["mastery"], it["graded"], it["set_by"]) == (4, 2, "learner")
    gc = session(st)["grade_changes"]
    assert gc == [{"item": "Case", "topic": "GEN-11", "from": 2, "to": 4, "outcome": "learner_set",
                   "examiner": 2, "learner": 4, "date": "2026-11-02", "note": SCORE["note"]}]
    assert out["learner_changes"][0]["kind"] == "score"
    # scheduling uses the learner's score: no confident error, the step advances
    t = st["topics"]["GEN-11"]
    assert t["mastery"] == 4 and t["step"] == 1 and t["calibration"] == "aligned" and t["due"] == "2026-11-12"
    # the same round without the learner's score: a confident error, back after the rest
    from conftest import Work
    plain = Work(tmp_path_factory.mktemp("plain"))
    closed(plain, config=cfg)
    p = plain.read_ledger()["topics"]["GEN-11"]
    assert p["calibration"] == "confident_error" and p["step"] == 0 and p["due"] == "2026-11-05"
    assert session(st)["score"] > session(plain.read_ledger())["score"]


def retested(work, today="2026-11-20"):
    """The ids of the open gaps the plan of a round started on `today` retests."""
    work.forget_job()
    work.start(today, "--mcqs", "10", "--focused", "6")
    return set(re.findall(r'"retest_gap": \{"id": "(G[0-9]+)"', json.dumps(work.read_json("plan.json"))))


def test_learner_set_score_does_not_close_the_gap_and_a_gap_closed_by_request_gets_no_retest(work, tmp_path_factory):
    from conftest import Work
    kept = Work(tmp_path_factory.mktemp("kept"))
    closed(kept, dict(REFLECTION, learner_scores=[SCORE]))
    st = kept.read_ledger()
    assert [g["topic"] for g in st["gaps"]] == ["GEN-11", "NEURO-04"]     # the graded gap stays
    assert st["gaps"][0]["source"] == ["graded"]                          # no misconception gap was added
    assert retested(kept) == {"G0001", "G0002"}
    closed2 = closed(work, dict(REFLECTION, learner_scores=[SCORE], learner_closed_gaps=[CLOSE_GAP]))
    st = work.read_ledger()
    assert [g["topic"] for g in st["gaps"]] == ["NEURO-04"]
    r = st["resolved"][-1]
    assert r["topic"] == "GEN-11" and r["closed_by"] == "learner" and r["partial"] is False
    assert r["learner_note"] == "I know this now" and r["session"] == "S0001" and r["note"] == "g"
    assert session(st)["learner_closed_gaps"] == [{"id": r["id"], "topic": "GEN-11"}]
    assert closed2["topics"]["GEN-11"]["gap_closed_by_learner"] is True
    assert retested(work) == {"G0002"}                       # no retest of the gap the learner closed


def test_log_shows_both_scores_and_who_closed_the_gap(work):
    closed(work, dict(REFLECTION, learner_scores=[SCORE], learner_closed_gaps=[CLOSE_GAP]))
    doc = work.read_json("store", "data", "sessions", "S0001.json")
    assert doc["closing"].startswith("Reflection verbatim")
    assert "### Set by the learner" in doc["closing"]
    assert "Case (GEN-11): the examiner's score 2, the learner's score 4" in doc["closing"]
    assert "closed by the learner, not by a retest: g" in doc["closing"]
    kinds = [(c["kind"], c.get("examiner"), c.get("learner"), c.get("closed_by")) for c in doc["learner_changes"]]
    assert kinds == [("score", 2, 4, None), ("gap", None, None, "learner")]
    assert doc["score"] == session(work.read_ledger())["score"]


def test_close_run_again_does_not_double_the_learners_changes(work):
    work.init()
    work.save_round("2026-11-02")
    refl = dict(REFLECTION, learner_scores=[SCORE], learner_closed_gaps=[CLOSE_GAP])
    work.close_round("2026-11-02", refl)
    work.close_round("2026-11-02", refl)
    work.publish()
    st = work.read_ledger()
    doc = work.read_json("store", "data", "sessions", "S0001.json")
    assert doc["closing"].count("### Set by the learner") == 1 and len(doc["learner_changes"]) == 2
    assert st["agg"]["overrides"] == {"scores": 1, "gaps": 1} and len(session(st)["grade_changes"]) == 1


def test_override_after_the_close_gives_the_schedule_the_reflection_path_gives(work, tmp_path_factory):
    from conftest import Work
    ref = Work(tmp_path_factory.mktemp("ref"))
    closed(ref, dict(REFLECTION, learner_scores=[SCORE], learner_closed_gaps=[CLOSE_GAP]))
    want = ref.read_ledger()

    closed(work)
    before = work.read_ledger()
    assert before["topics"]["GEN-11"]["calibration"] == "confident_error"
    out = override(work, "--scores", json.dumps([SCORE]), "--close-gaps", json.dumps([CLOSE_GAP]))
    assert out["ok"] and out["session"] == "S0001" and out["topics"]["GEN-11"]["step"] == 1
    assert out["topics"]["GEN-11"]["gap_closed_by_learner"] is True
    assert [f["as"] for f in out["files"]][-1] == "data/state.json"
    assert {"data/sessions/S0001.json", "data/page.json", "data/prepared.json"} <= {f["as"] for f in out["files"]}
    work.publish()
    st = work.read_ledger()
    assert st["gen"] == before["gen"] + 1
    # never content-neutral: the prepared round was planned on the old score and the open gap
    assert "content_gen" not in st and work.read_json("store", "data", "prepared.json").get("empty") is True
    assert st["topics"]["GEN-11"] == want["topics"]["GEN-11"]
    assert [g["topic"] for g in st["gaps"]] == [g["topic"] for g in want["gaps"]]
    it = item(st, "GEN-11")
    assert (it["mastery"], it["graded"], it["set_by"]) == (4, 2, "learner")
    assert session(st)["score"] == session(want)["score"] == out["score"]
    assert st["agg"]["score_sum"] == want["agg"]["score_sum"]
    assert st["agg"]["overrides"] == want["agg"]["overrides"] == {"scores": 1, "gaps": 1}
    assert st["resolved"][-1]["closed_by"] == "learner"
    # the log: the closing is untouched, the change is in the addendum and in learner_changes
    doc = work.read_json("store", "data", "sessions", "S0001.json")
    assert doc["closing"] == "Reflection verbatim" and doc["score"] == out["score"]
    assert "## Set by the learner · 2026-11-02" in doc["addendum"]
    assert "the examiner's score 2, the learner's score 4" in doc["addendum"]
    assert "Gap G0001 (GEN-11) closed by the learner" in doc["addendum"]
    assert [c["kind"] for c in doc["learner_changes"]] == ["score", "gap"]
    idx = work.read_json("store", "data", "page.json")
    assert next(s for s in idx["sessions"] if s["id"] == "S0001")["score"] == out["score"]


def test_override_in_a_later_conversation_closes_a_gap_by_its_id(work):
    closed(work)
    work.forget_job()
    work.open(today="2026-11-10")
    st = work.read_ledger()
    gid = next(g["id"] for g in st["gaps"] if g["topic"] == "NEURO-04")
    due = st["topics"]["NEURO-04"]["due"]
    out = override(work, "--close-gaps", json.dumps({"gap": gid}), today="2026-11-10")
    assert out["open_gaps"] == 1 and "score" not in out
    work.publish()
    st = work.read_ledger()
    assert [g["topic"] for g in st["gaps"]] == ["GEN-11"]
    assert st["resolved"][-1]["id"] == gid and st["resolved"][-1]["resolved"] == "2026-11-10"
    assert st["topics"]["NEURO-04"]["due"] == due           # closing a gap leaves the topic's date alone
    assert "## Set by the learner · 2026-11-10" in work.read_json("store", "data", "sessions", "S0001.json")["addendum"]


def test_learner_set_score_on_a_wrong_mcq_marked_sure_is_no_confident_error(work):
    closed(work)
    out = override(work, "--scores", json.dumps({"topic": "NEURO-04", "score": 4}))
    assert out["topics"]["NEURO-04"]["calibration"] != "confident_error" and out["topics"]["NEURO-04"]["step"] == 1
    work.publish()
    it = item(work.read_ledger(), "NEURO-04")
    assert (it["mastery"], it["graded"], it["correct"]) == (4, 1, False)
    # setting it again keeps the examiner's score as graded
    out = override(work, "--scores", json.dumps({"topic": "NEURO-04", "score": 5}))
    assert out["learner_changes"][0]["examiner"] == 1 and out["learner_changes"][0]["learner"] == 5


def test_override_refusals_write_nothing(work):
    work.init()
    work.save_round("2026-11-02")
    out = override(work, "--close-gaps", '{"topic": "GEN-11"}', ok=False)
    assert out["ok"] is False and "not closed yet" in out["error"] and "learner_closed_gaps" in out["error"]
    work.close_round("2026-11-02")
    work.publish()
    before = work.read_json("publish", "data", "state.json")
    for args, problem in ((["--close-gaps", '{"gap": "G0099"}'], "no open gap G0099"),
                          (["--scores", '{"topic": "CARD-01", "score": 4}'], "no item CARD-01"),
                          (["--scores", '{"topic": "GEN-11", "score": 7}'], "from 0 to 5"),
                          ([], "override needs")):
        out = override(work, *args, ok=False)
        assert out["ok"] is False and problem in out["error"], out
    assert work.read_json("publish", "data", "state.json") == before
    # an unknown gap in the reflection stops the close too
    work.forget_job()
    work.save_round("2026-11-06", dict(copy.deepcopy(ROUND), log_id="S0002"))
    work.write("reflection.json", dict(REFLECTION, learner_closed_gaps=["G0099"]))
    work.write("B.md", "b")
    r = work.run("--today", "2026-11-06", "close", "--work", work.path, ok=False)
    assert "no open gap G0099" in json.loads(r.stdout)["error"]


def test_review_counts_the_learners_changes_apart_from_disputes(work):
    refl = dict(REFLECTION, learner_scores=[SCORE], learner_closed_gaps=[CLOSE_GAP], grade_changes=[DISPUTE],
                items=[{"type": "focused", "topic": "PULM-04", "mastery": 4.5}])
    closed(work, refl)
    s = stats(work)
    period, all_time = s["analysis"]["period"], s["analysis"]["all_time"]
    assert period["grade_disputes"] == {"n": 1, "outcomes": {"learner_right": 0, "both_defensible": 1, "upheld": 0}}
    assert period["learner_overrides"] == {"scores": 1, "mean_change": 2.0, "gaps_closed": 1}
    assert all_time["grade_disputes"] == {"learner_right": 0, "both_defensible": 1, "upheld": 0}
    assert all_time["learner_overrides"] == {"scores": 1, "gaps_closed": 1}
    assert [g["topic"] for g in s["gaps_closed_by_learner"]] == ["GEN-11"]
    assert all(g.get("closed_by") != "learner" for g in s["gaps_resolved"])
    # calibration still compares the confidence with what the examiner graded (2/5, marked sure)
    assert period["confidence_calibration"]["table"]["sure"]["observed"] == round((0.4 + 0.0) / 2, 2)


def test_a_ledger_without_the_counters_and_a_hand_made_learner_override_are_counted(work):
    closed(work)
    st = work.read_ledger()
    del st["agg"]["overrides"]
    session(st)["grade_changes"] = [{"item": "Q", "topic": "GEN-11", "from": 2, "to": 4, "outcome": "learner_override"}]
    work.write_ledger(st)
    work.forget_job()
    work.open(today="2026-11-03")
    s = stats(work)
    assert s["analysis"]["period"]["learner_overrides"]["scores"] == 1
    assert s["analysis"]["period"]["grade_disputes"]["n"] == 0
    assert s["analysis"]["all_time"]["learner_overrides"] == {"scores": 0, "gaps_closed": 0}
    out = override(work, "--close-gaps", '["GEN-11"]', today="2026-11-03")
    assert out["ok"] and work.read_json("publish", "data", "state.json")["agg"]["overrides"] == {"scores": 0, "gaps": 1}


def test_the_count_survives_the_end_of_the_review_period(work):
    closed(work, dict(REFLECTION, learner_scores=[SCORE], learner_closed_gaps=[CLOSE_GAP]))
    work.forget_job()
    work.open(today="2026-12-20")
    work.run("--today", "2026-12-20", "review", "--work", work.path, "--review", "{}")
    s = stats(work, "2026-12-21")
    assert s["analysis"]["previous_period"]["learner_overrides"] == {"scores": 1, "mean_change": 2.0, "gaps_closed": 1}
    out = override(work, "--scores", json.dumps(SCORE), "--session", "S0001", today="2026-12-21", ok=False)
    assert "before the last progress review" in out["error"]

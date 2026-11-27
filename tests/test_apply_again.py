"""One way to apply a round again (issue #74): `save` run again, the reflection (`close`), a
learner-set score and a gap the learner closes all undo the round and apply it again with the
amended input, through the one apply_round. Run on every example ledger."""
import copy
import datetime as dt
import json

import pytest

import examples
from examples import LEDGERS, cme

ledgers = pytest.mark.parametrize("name", list(LEDGERS))


def plain(st):
    """The ledger as JSON, without the count of writes."""
    st = json.loads(json.dumps(st))
    st.pop("gen", None)
    return st


def recorded(name):
    """The example ledger with the scripted round recorded on its date (reflection pending)."""
    st = examples.load_ledger(name)
    day = examples.today_of(name)
    rnd = examples.round_for(st, cme.plan_round(st, examples.plan_options(), day))
    cme.record_round(st, copy.deepcopy(rnd), day)
    return st, rnd, day


def session(st, sid):
    return next(s for s in st["sessions"] if s["id"] == sid)


def score_request(rnd):
    """A learner-set score that changes what the round's first item counts as."""
    it = rnd["items"][0]
    return {"topic": it["topic"], "type": it["type"], "score": 1 if it["mastery"] >= 4 else 5, "note": "mine"}


def gap_to_close(st, rnd):
    """An open gap, one on a topic of the round if there is one."""
    tested = {it["topic"] for it in rnd["items"]}
    gaps = sorted(st["gaps"], key=lambda g: g["topic"] not in tested)
    return gaps[0]["id"] if gaps else None


# ---- decision 1: the same result whenever it is said

@ledgers
def test_a_learner_set_score_after_the_close_equals_the_same_score_in_the_reflection(name):
    st, rnd, day = recorded(name)
    sid, refl, later = rnd["log_id"], examples.reflection_for(rnd), day + dt.timedelta(days=1)
    req = score_request(rnd)
    before = copy.deepcopy(st)
    cme.reflect_round(before, dict(refl, learner_scores=[req]), later)
    after = copy.deepcopy(st)
    cme.reflect_round(after, refl, later)
    changes, topics, warnings = cme.amend_round(after, sid, [req], [], cme.iso(day), later)
    assert warnings == [] and [c["kind"] for c in changes] == ["score"]
    assert topics[req["topic"]]["due"] == before["topics"][req["topic"]]["due"]
    # the whole ledger: schedule, gaps, the round record and the aggregates
    assert plain(after) == plain(before)


@ledgers
def test_a_gap_closed_after_the_close_equals_the_same_gap_closed_in_the_reflection(name):
    st, rnd, day = recorded(name)
    gid = gap_to_close(st, rnd)
    if gid is None:
        pytest.skip("no open gap")
    sid, refl, later = rnd["log_id"], examples.reflection_for(rnd), day + dt.timedelta(days=1)
    before = copy.deepcopy(st)
    cme.reflect_round(before, dict(refl, learner_closed_gaps=[{"gap": gid, "note": "known"}]), later)
    after = copy.deepcopy(st)
    cme.reflect_round(after, refl, later)
    cme.amend_round(after, sid, [], [{"gap": gid, "note": "known"}], cme.iso(day), later)
    for k in ("topics", "gaps", "resolved", "agg"):
        assert after[k] == before[k], k
    assert gid not in {g["id"] for g in after["gaps"]}
    assert after["resolved"][-1]["closed_by"] == "learner"


@ledgers
def test_a_score_set_after_a_later_round_reschedules_only_the_topics_not_tested_since(name):
    """Decision 2: the round is applied again on the topics it is still the latest on; a topic
    tested since keeps the schedule the later round gave it, only the record changes."""
    st, rnd, day = recorded(name)
    sid, refl = rnd["log_id"], examples.reflection_for(rnd)
    day2 = day + dt.timedelta(days=4)
    cme.reflect_round(st, refl, day + dt.timedelta(days=1))
    rnd2 = examples.round_for(st, cme.plan_round(st, examples.plan_options(), day2))
    again = {it["topic"] for it in rnd2["items"]}
    reqs = [dict(score_request({"items": [it]})) for it in rnd["items"]]
    kept = [r for r in reqs if r["topic"] not in again][:1]
    since = [r for r in reqs if r["topic"] in again][:1]

    said_before = copy.deepcopy(st)          # the same scores, given before the later round
    cme.amend_round(said_before, sid, kept, [], cme.iso(day2), day2)
    cme.record_round(said_before, copy.deepcopy(rnd2), day2)

    cme.record_round(st, copy.deepcopy(rnd2), day2)
    second = copy.deepcopy(st)
    changes, topics, warnings = cme.amend_round(st, sid, kept + since, [], cme.iso(day2), day2)
    assert len(changes) == len(kept + since)
    for r in kept:
        assert st["topics"][r["topic"]] == said_before["topics"][r["topic"]]
        assert r["topic"] in topics
    for r in since:
        assert st["topics"][r["topic"]] == second["topics"][r["topic"]]
        assert any(r["topic"] in w and "tested again since" in w for w in warnings)
    assert {t: v for t, v in st["topics"].items() if t not in {r["topic"] for r in kept}} == \
        {t: v for t, v in second["topics"].items() if t not in {r["topic"] for r in kept}}
    assert session(st, rnd2["log_id"]) == session(second, rnd2["log_id"])
    assert [i["mastery"] for i in session(st, sid)["items"]] != [i["mastery"] for i in session(second, sid)["items"]]


# ---- applying the same input again changes nothing

@ledgers
def test_a_round_applied_again_from_its_entry_gives_the_same_ledger(name):
    st, rnd, day = recorded(name)
    sid = rnd["log_id"]
    for step in ("recorded", "reflected"):
        if step == "reflected":
            cme.reflect_round(st, examples.reflection_for(rnd), day + dt.timedelta(days=1))
        once = plain(st)
        cme.apply_round_again(st, session(st, sid), cme.round_from_entry(st, session(st, sid)), day)
        st["updated"] = once["updated"]
        assert plain(st) == once, step


@ledgers
def test_saving_twice_and_closing_twice_give_the_ledger_once(name):
    st, rnd, day = recorded(name)
    sid, refl, later = rnd["log_id"], examples.reflection_for(rnd), day + dt.timedelta(days=1)
    once = copy.deepcopy(st)
    out = cme.record_round(st, copy.deepcopy(rnd), day, again=session(st, sid))
    assert out["session_id"] == sid and out["reflection_pending"] is True
    assert plain(st) == plain(once)

    base = cme.round_from_entry(st, session(st, sid))
    cme.reflect_round(st, refl, later)
    closed = copy.deepcopy(st)
    cme.reflect_round(st, refl, later, sid, None, base)
    assert plain(st) == plain(closed)


def test_the_undo_record_holds_only_what_the_round_changed_and_a_later_round_takes_its_topics():
    st, rnd, day = recorded("mid_curriculum")
    sid = rnd["log_id"]
    undo = session(st, sid)["undo"]
    assert set(undo["topics"]) == {it["topic"] for it in rnd["items"]} | {g["topic"] for g in rnd["gaps"]}
    assert all("history" not in json.dumps(r.get("was") or {}) for r in undo["topics"].values())
    assert "_snapshot" not in session(st, sid) and "_round" not in session(st, sid)
    assert "steps_before" not in session(st, sid)
    cme.reflect_round(st, examples.reflection_for(rnd), day + dt.timedelta(days=1))
    day2 = day + dt.timedelta(days=4)
    rnd2 = examples.round_for(st, cme.plan_round(st, examples.plan_options(), day2))
    cme.record_round(st, copy.deepcopy(rnd2), day2)
    later = set(session(st, rnd2["log_id"])["undo"]["topics"])
    assert later and not later & set(session(st, sid)["undo"]["topics"])
    assert cme.owner_of(st, rnd2["items"][0]["topic"])["id"] == rnd2["log_id"]


# ---- ledgers written by 5.0

def test_a_round_saved_by_5_0_and_unreflected_closes_once_in_the_new_shape():
    st = examples.load_ledger("unreflected")
    waiting = session(st, st["unreflected"])
    assert waiting["_snapshot"] and waiting["_round"]
    rnd0, day = waiting["_round"], examples.today_of("unreflected")
    req = score_request(rnd0)
    with_score = copy.deepcopy(st)
    cme.reflect_round(with_score, dict(examples.reflection_for(rnd0), learner_scores=[req]), day)
    cme.reflect_round(st, examples.reflection_for(rnd0), day)
    s = session(st, rnd0["log_id"])
    assert "_snapshot" not in s and "_round" not in s and s["undo"]["topics"] and st["unreflected"] is None
    # once in the new shape, a score set after the close is the same as one in the reflection
    cme.amend_round(st, rnd0["log_id"], [req], [], waiting["date"], day)
    assert plain(st) == plain(with_score)


def test_a_round_saved_by_5_0_and_left_unreflected_is_finalized_by_the_next_round():
    st, rnd, day = recorded("unreflected")
    old = session(st, examples.load_ledger("unreflected")["unreflected"])
    assert old["reflection"] == {"skipped": True} and "_snapshot" not in old and "undo" not in old


@pytest.mark.parametrize("name", ["mid_curriculum", "drilled"])
def test_a_score_set_on_a_round_closed_by_5_0_reschedules_its_topic_from_where_it_started(name):
    st = examples.load_ledger(name)
    last = st["sessions"][-1]
    assert "undo" not in last
    it = last["items"][0]
    before = copy.deepcopy(st)
    day = examples.today_of(name)
    score = 1 if it["mastery"] >= 4 else 5
    changes, topics, warnings = cme.amend_round(st, last["id"], [{"topic": it["topic"], "type": it["type"],
                                                                   "score": score}], [], cme.iso(day), day)
    t = st["topics"][it["topic"]]
    assert topics[it["topic"]]["step"] == t["step"] and t["mastery"] == score
    started = (last.get("steps_before") or {}).get(it["topic"], before["topics"][it["topic"]]["step"])
    assert t["step"] == (min(started + 1, len(st["config"]["intervals_days"]) - 1) if score >= 4 else 0)
    assert t["history"][:-1] == before["topics"][it["topic"]]["history"][:-1] and t["attempts"] == \
        before["topics"][it["topic"]]["attempts"]
    # what the 5.0 round does not say it changed stays as it is
    assert st["profile"]["domain_self_ratings"] == before["profile"]["domain_self_ratings"]
    def no_ids(gaps):           # a ledger written before gaps had ids gets them once
        return [{k: v for k, v in g.items() if k != "id"} for g in gaps]
    assert no_ids(st["gaps"]) == no_ids(before["gaps"])
    assert st["resolved"] == before["resolved"]
    assert {k: v for k, v in st["topics"].items() if k not in last["topics"]} == \
        {k: v for k, v in before["topics"].items() if k not in last["topics"]}
    assert st["sessions"][:-1] == before["sessions"][:-1]
    assert st["agg"]["overrides"]["scores"] == before["agg"].get("overrides", {}).get("scores", 0) + 1

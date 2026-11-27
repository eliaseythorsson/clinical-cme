"""Spacing fixes (issue #15, ADR 0003): a tested topic rests at least three days; a gap closes
only on an item that retests that gap and is answered well; a comfort rating lowers a domain's
share only as far as the answers in that domain bear it out."""
import argparse
import copy
import datetime as dt
import importlib.util
import itertools

import pytest

from conftest import CME

spec = importlib.util.spec_from_file_location("cme", CME)
cme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cme)

DAY = dt.date(2026, 11, 2)
INTERVALS = cme.DEFAULT_CONFIG["intervals_days"]
PLAN_OPTIONS = dict(focused=None, mcqs=None, no_case=False, domain=None, no_new=False,
                    allow_repeat=False, no_drill=False, force_drill=False, seed=None)


def days(n):
    return dt.timedelta(days=n)


def ledger(work):
    return cme.load_json(work.init())


def plan(st, today, **options):
    return cme.plan_round(st, argparse.Namespace(**dict(PLAN_OPTIONS, **options)), today)


def planned_topics(st, today, **options):
    return [it.get("topic") for it in plan(st, today, **options)["items"]]


def mcq(topic, mastery, correct=None, confidence="unsure", **more):
    return dict({"type": "mcq", "topic": topic, "mastery": mastery, "confidence": confidence,
                 "correct": mastery >= 4 if correct is None else correct,
                 "stem_summary": "stem on %s" % topic, "coding": {"errors": []}}, **more)


def play(st, today, items, gaps=(), comfort=None):
    """Record and reflect a round of `items` on `today`; returns the reflect result."""
    rnd = {"items": list(items), "gaps": list(gaps), "title": "t", "summary": "s", "tags": ["x"]}
    cme.record_round(st, rnd, today)
    return cme.reflect_round(st, {"topic_comfort": comfort or {}}, today)


def gap_of(st, topic):
    return next((g for g in st["gaps"] if g["topic"] == topic), None)


# ---- a tested topic rests at least three days

def test_no_answer_brings_a_topic_back_within_three_days():
    for step, mastery, comfort, misconception, self_gap in itertools.product(
            range(len(INTERVALS)), [0, 1, 2, 2.5, 3, 3.5, 4, 5], [None, 1, 3, 5], [False, True], [False, True]):
        _, due, _, interval = cme.schedule_topic(step, mastery, comfort, misconception, self_gap, INTERVALS, DAY)
        assert interval >= cme.MIN_RETURN_DAYS == 3 and due == DAY + days(interval)


def test_a_miss_returns_after_three_days_and_a_good_answer_still_advances():
    assert cme.schedule_topic(0, 2, None, False, False, INTERVALS, DAY)[3] == 3      # miss
    assert cme.schedule_topic(4, 1, None, True, False, INTERVALS, DAY)[3] == 3       # confident error
    assert cme.schedule_topic(2, 3, 5, False, False, INTERVALS, DAY)[3] == 3         # overconfident
    assert cme.schedule_topic(2, 3, None, False, False, INTERVALS, DAY)[3] == 7      # held at step 2
    assert cme.schedule_topic(2, 5, None, False, False, INTERVALS, DAY)[3] == 16     # advanced


def test_a_topic_held_at_mastery_3_does_not_return_every_day(work):
    st = ledger(work)
    today, seen = DAY, []
    play(st, today, [mcq("CARD-01", 3, correct=True)])
    for _ in range(9):
        today += days(1)
        if "CARD-01" in planned_topics(st, today):
            seen.append(today)
            play(st, today, [mcq("CARD-01", 3, correct=True)])
    assert seen and all((b - a).days >= 3 for a, b in zip([DAY] + seen, seen))


def test_a_ledger_from_an_older_version_with_a_topic_due_tomorrow_waits_too(work):
    st = ledger(work)
    play(st, DAY, [mcq("CARD-01", 2)], gaps=[{"topic": "CARD-01", "gap": "missed the point", "source": "graded"}])
    st["topics"]["CARD-01"]["due"] = cme.iso(DAY + days(1))       # as version 4 scheduled a miss
    assert "CARD-01" not in planned_topics(st, DAY + days(1))
    assert "CARD-01" not in planned_topics(st, DAY + days(2))
    assert "CARD-01" in planned_topics(st, DAY + days(3))
    assert "CARD-01" in planned_topics(st, DAY + days(1), allow_repeat=True)


def test_an_open_gap_on_an_untested_topic_waits_three_days(work):
    st = ledger(work)
    st["config"]["mcqs"] = 4      # with four short questions every round of a block has a slot for a repeat
    play(st, DAY, [mcq("CARD-01", 5)],
         gaps=[{"topic": "RENAL-02", "gap": "did not apply it in the case", "source": "transfer"}])
    assert "RENAL-02" not in planned_topics(st, DAY + days(1))
    assert "RENAL-02" in planned_topics(st, DAY + days(3))


# ---- a gap closes only on an item that retests it

def with_gap(work):
    st = ledger(work)
    play(st, DAY, [mcq("CARD-01", 2)], gaps=[{"topic": "CARD-01", "gap": "missed the point", "source": "graded"}])
    return st, gap_of(st, "CARD-01")["id"]


def test_gaps_are_numbered_and_the_plan_names_the_gap_to_retest(work):
    st, gid = with_gap(work)
    assert gid == "G0001"
    item = next(it for it in plan(st, DAY + days(3))["items"] if it.get("topic") == "CARD-01")
    assert item["retest_gap"]["id"] == gid and item["retest_gap"]["gap"] == "missed the point"
    # the author is told where the gap is named: the item's key header (issue #36), not the round JSON
    how = item["retest_gap"]["how"]
    assert "'retests: G0001' in the item's key header" in how and "standards.md" in how
    assert "round JSON" not in how and "round.json" not in how


def test_a_good_answer_on_the_topic_that_does_not_retest_the_gap_leaves_it_open(work):
    st, gid = with_gap(work)
    st["topics"]["CARD-01"]["step"] = 3
    res = play(st, DAY + days(3), [mcq("CARD-01", 5, confidence="sure")])
    assert gap_of(st, "CARD-01")["id"] == gid and "last_retested" not in gap_of(st, "CARD-01")
    assert res["topics"]["CARD-01"]["gap_retested"] is False and "gap_resolved" not in res["topics"]["CARD-01"]
    assert any(gid in w and "retests" in w for w in res["warnings"])
    # still waiting for its retest: it comes back long before the topic is due, though not in a
    # third round in a row (the drill-down limit, issue #18)
    assert cme.parse_date(st["topics"]["CARD-01"]["due"]) > DAY + days(9)
    assert "CARD-01" not in planned_topics(st, DAY + days(6))
    play(st, DAY + days(6), [mcq("RENAL-02", 5, confidence="sure")])
    assert "CARD-01" in planned_topics(st, DAY + days(9))


def test_an_item_that_retests_the_gap_and_is_answered_well_closes_it(work):
    st, gid = with_gap(work)
    res = play(st, DAY + days(3), [mcq("CARD-01", 5, confidence="sure", retests=gid)])
    assert gap_of(st, "CARD-01") is None and res["topics"]["CARD-01"]["gap_resolved"] is True
    assert st["resolved"][-1]["id"] == gid and st["resolved"][-1]["partial"] is False
    assert st["sessions"][-1]["items"][0]["retests"] == gid


def test_a_retest_answered_badly_keeps_the_gap_and_records_the_retest(work):
    st, gid = with_gap(work)
    play(st, DAY + days(3), [mcq("CARD-01", 3, correct=True, retests=gid)])
    assert gap_of(st, "CARD-01")["last_retested"] == cme.iso(DAY + days(3))
    # after its one targeted retest the gap follows the topic's spacing, and a second miss in a
    # row does not bring the topic straight back (the drill-down limit, issue #18)
    assert st["topics"]["CARD-01"]["due"] == cme.iso(DAY + days(3 + cme.DRILLDOWN_PAUSE_DAYS))
    play(st, DAY + days(6), [mcq("RENAL-02", 5, confidence="sure")])
    assert "CARD-01" not in planned_topics(st, DAY + days(9))
    assert "CARD-01" in planned_topics(st, DAY + days(10))


def test_the_retest_item_decides_not_the_topic_average(work):
    st, gid = with_gap(work)
    # the retest is missed, another item on the topic is perfect: mean 4, the gap stays
    play(st, DAY + days(3), [mcq("CARD-01", 3, correct=True, retests=gid), mcq("CARD-01", 5, confidence="sure")])
    assert gap_of(st, "CARD-01") is not None
    # a lucky guess on the retest counts as 3 and does not close it either
    play(st, DAY + days(9), [mcq("CARD-01", 5, confidence="guess", retests=gid)])
    assert gap_of(st, "CARD-01") is not None


def test_an_overconfident_retest_does_not_close_the_gap(work):
    st, gid = with_gap(work)
    play(st, DAY + days(3), [mcq("CARD-01", 5, confidence="guess", retests=gid)], comfort={"CARD-01": 5})
    assert gap_of(st, "CARD-01") is not None


def test_a_gap_from_an_older_ledger_gets_an_id_and_can_be_retested_by_topic(work):
    st, gid = with_gap(work)
    del gap_of(st, "CARD-01")["id"]
    item = next(it for it in plan(st, DAY + days(3))["items"] if it.get("topic") == "CARD-01")
    assert item["retest_gap"]["id"] == "CARD-01"          # planning does not write the ledger
    play(st, DAY + days(3), [mcq("CARD-01", 5, confidence="sure", retests="CARD-01")])
    assert gap_of(st, "CARD-01") is None and st["resolved"][-1]["id"] == "G0001"


def test_retests_that_names_no_open_gap_is_reported(work):
    st, gid = with_gap(work)
    res = play(st, DAY + days(3), [mcq("RENAL-02", 5, confidence="sure", retests=gid)])
    assert any("not an open gap" in w for w in res["warnings"]) and gap_of(st, "CARD-01") is not None


def test_a_gap_reopened_keeps_its_id_and_a_new_gap_gets_the_next(work):
    st, gid = with_gap(work)
    play(st, DAY + days(3), [mcq("CARD-01", 2, retests=gid), mcq("RENAL-02", 2)],
         gaps=[{"topic": "CARD-01", "gap": "missed it again", "source": "graded"},
               {"topic": "RENAL-02", "gap": "another point", "source": "graded"}])
    assert gap_of(st, "CARD-01")["id"] == gid and gap_of(st, "RENAL-02")["id"] == "G0002"


# ---- comfort corrected for overconfidence before it lowers a domain's share

def share(st, domain):
    w = cme.domain_weights(st)
    return w[domain] / sum(w.values())


def test_an_overconfident_5_of_5_does_not_reduce_the_domains_share(work):
    st = ledger(work)
    before = share(st, "CARD")
    play(st, DAY, [mcq("CARD-01", 3, correct=True)], comfort={"CARD-01": 5})
    assert st["topics"]["CARD-01"]["calibration"] == "overconfident"
    assert st["profile"]["domain_self_ratings"]["CARD"] == 5      # the learner's rating is kept as given
    assert share(st, "CARD") == pytest.approx(before)


def test_a_5_of_5_borne_out_by_the_answers_still_reduces_the_share(work):
    st = ledger(work)
    fresh = copy.deepcopy(st)
    before = share(st, "CARD")
    play(st, DAY, [mcq("CARD-01", 5, confidence="sure")], comfort={"CARD-01": 5})
    assert share(st, "CARD") < before
    assert cme.domain_weights(st)["CARD"] == pytest.approx(cme.domain_weights(fresh)["CARD"] * 0.6)


def test_a_confident_rating_over_poor_answers_raises_the_share(work):
    st = ledger(work)
    before = share(st, "CARD")
    play(st, DAY, [mcq("CARD-01", 1, confidence="sure")], comfort={"CARD-01": 5})
    assert share(st, "CARD") > before


def test_a_setup_rating_counts_as_given_until_the_domain_is_tested_and_low_ratings_always_count(work):
    st = ledger(work)
    base = copy.deepcopy(cme.domain_weights(st))
    st["profile"]["domain_self_ratings"] = {"CARD": 5, "RENAL": 1}
    w = cme.domain_weights(st)
    assert w["CARD"] == pytest.approx(base["CARD"] * 0.6) and w["RENAL"] == pytest.approx(base["RENAL"] * 1.6)
    play(st, DAY, [mcq("RENAL-02", 5, confidence="sure")])        # strong answer, no comfort given
    assert cme.domain_weights(st)["RENAL"] == pytest.approx(base["RENAL"] * 1.6)

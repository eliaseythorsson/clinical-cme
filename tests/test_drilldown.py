"""Drill-down limit (issue #18, ADR 0003): no topic is in more than two rounds in a row; in the
theme a topic missed on its second round of the block (or after) then pauses (issue #79); a miss outside the theme gets one
targeted retest and after that ordinary spacing. The example ledger `drilled` holds the old
pattern (rounds by an engine with no limit, every repeat missed) and the tests show it capped."""
import copy
import datetime as dt

import pytest

import examples
from examples import cme
from test_blocks import topic_for

PAUSE = cme.DRILLDOWN_PAUSE_DAYS


def days(n):
    return dt.timedelta(days=n)


def runs(st):
    """{topic: the longest run of rounds in a row it was in}."""
    longest, current = {}, {}
    for s in st["previous"] + st["sessions"]:
        current = {tid: current.get(tid, 0) + 1 for tid in s["topics"]}
        for tid, n in current.items():
            longest[tid] = max(longest.get(tid, 0), n)
    return longest


def play_missing(st, start, n, every=3):
    """`n` rounds, one every `every` days, by the learner who misses every repeat."""
    plans = []
    for k in range(n):
        day = start + days(every * k)
        plan = cme.plan_round(st, examples.plan_options(), day)
        for it in plan["items"]:
            if not it.get("topic"):
                it["topic"] = topic_for(st, it, {x.get("topic") for x in plan["items"]})
        rnd = examples.miss_repeats(examples.round_for(st, plan), plan)
        cme.record_round(st, copy.deepcopy(rnd), day)
        cme.reflect_round(st, {"performance": 2}, day)
        plans.append(plan)
    return plans


def drilled():
    return examples.load_ledger("drilled"), examples.today_of("drilled")


def without_limit(monkeypatch):
    monkeypatch.setattr(cme, "DRILLDOWN_MAX_ROUNDS", 10 ** 6)
    monkeypatch.setattr(cme, "DRILLDOWN_PAUSE_DAYS", 0)


# ---- the old pattern, and the cap on it

def test_the_drilled_ledger_holds_the_old_pattern():
    st, today = drilled()
    theme = st["block"]["theme"]
    longest = runs(st)
    assert max(n for tid, n in longest.items() if cme.domain_of(tid) == theme) >= 5
    assert max(n for tid, n in longest.items() if cme.domain_of(tid) != theme) >= 4
    assert (today - cme.parse_date(st["sessions"][-1]["date"])).days == 3     # everything missed is due again


def test_without_the_limit_the_pattern_goes_on(monkeypatch):
    st, today = drilled()
    without_limit(monkeypatch)
    before = runs(st)
    play_missing(st, today, 3)
    after = runs(st)
    assert any(after[tid] == before[tid] + 3 for tid in before)


def test_the_next_round_leaves_out_what_the_last_two_rounds_both_had():
    st, today = drilled()
    both = set(st["sessions"][-1]["topics"]) & set(st["sessions"][-2]["topics"])
    due = {tid for tid, t in st["topics"].items() if cme.parse_date(t["due"]) <= today}
    assert both and both <= due                       # the old engine would bring them all back
    planned = {it.get("topic") for it in cme.plan_round(st, examples.plan_options(), today)["items"]}
    assert not planned & both
    again = {it.get("topic") for it in cme.plan_round(st, examples.plan_options(allow_repeat=True), today)["items"]}
    assert again & both                               # only the learner's own one-off request overrides


@pytest.mark.parametrize("every", [3, 4, 7, 10])
def test_no_topic_is_in_more_than_two_rounds_in_a_row_from_then_on(every):
    st, today = drilled()
    old = len(st["sessions"])
    play_missing(st, today, 14, every)                # to the end of the block and into the next
    new = copy.deepcopy(st)
    new["previous"], new["sessions"] = [], st["sessions"][old - 2:]     # the two old rounds count too
    longest = runs(new)
    assert max(longest.values()) <= cme.DRILLDOWN_MAX_ROUNDS == 2
    assert any(n == 2 for n in longest.values())      # drilling twice in a row does still happen


@pytest.mark.parametrize("every", [3, 7])
def test_a_new_ledger_is_capped_and_was_not_before(every, monkeypatch):
    st, today = examples.load_ledger("fresh"), examples.today_of("fresh")
    play_missing(st, today, 12, every)
    assert max(runs(st).values()) <= 2
    without_limit(monkeypatch)
    st = examples.load_ledger("fresh")
    play_missing(st, today, 12, every)
    assert max(runs(st).values()) >= 3


# ---- single topics: in the theme, outside it

DAY = dt.date(2026, 11, 2)


def mcq(topic, mastery, **more):
    return dict({"type": "mcq", "topic": topic, "mastery": mastery, "confidence": "unsure", "correct": mastery >= 4,
                 "stem_summary": "stem on %s" % topic, "coding": {"errors": []}}, **more)


def play(st, day, items, gaps=()):
    rnd = {"items": list(items), "title": "t", "summary": "s", "tags": ["x"],
           "gaps": [{"topic": t, "gap": "missed the point", "source": "graded"} for t in gaps]}
    cme.record_round(st, rnd, day)
    return cme.reflect_round(st, {}, day)["topics"]


def planned(st, day, **options):
    return {it.get("topic"): it for it in cme.plan_round(st, examples.plan_options(**options), day)["items"]}


def new_ledger(theme="CARD"):
    st = examples.load_ledger("fresh")
    st["config"]["mcqs"] = 4            # every round of a block then has a slot for a repeat
    cme.start_block(st, theme, "learner")
    return st


def gap_of(st, topic):
    return next((g for g in st["gaps"] if g["topic"] == topic), None)


def due(st, topic):
    return cme.parse_date(st["topics"][topic]["due"])


def test_in_the_theme_a_topic_is_drilled_in_two_rounds_in_a_row_then_pauses():
    st = new_ledger("CARD")
    assert play(st, DAY, [mcq("CARD-01", 2)], ["CARD-01"])["CARD-01"].get("drilldown_limit") is None
    assert due(st, "CARD-01") == DAY + days(3)
    assert "CARD-01" in planned(st, DAY + days(3))
    res = play(st, DAY + days(3), [mcq("CARD-01", 2, retests="G0001")], ["CARD-01"])
    assert res["CARD-01"]["drilldown_limit"] is True and res["CARD-01"]["interval_days"] == PAUSE
    assert due(st, "CARD-01") == DAY + days(3 + PAUSE)
    # not in a third round in a row, even one late enough for the topic to be due
    assert "CARD-01" not in planned(st, DAY + days(6))
    assert "CARD-01" not in planned(st, DAY + days(3 + PAUSE))
    play(st, DAY + days(3 + PAUSE), [mcq("CARD-02", 5)])
    assert "CARD-01" in planned(st, DAY + days(6 + PAUSE))


def test_in_the_theme_a_topic_seen_twice_in_the_block_waits_the_pause_when_missed():
    # issue #79: a miss on a theme topic's second round in the block pauses it, rounds in a row
    # or not (before, a round on something else in between let it return after the rest)
    st = new_ledger("CARD")
    play(st, DAY, [mcq("CARD-01", 2)], ["CARD-01"])
    play(st, DAY + days(3), [mcq("CARD-02", 5)])
    res = play(st, DAY + days(6), [mcq("CARD-01", 2, retests="G0001")], ["CARD-01"])
    assert res["CARD-01"]["drilldown_limit"] is True and due(st, "CARD-01") == DAY + days(6 + PAUSE)
    # and after each further miss in the block
    play(st, DAY + days(9), [mcq("CARD-02", 5)])
    res = play(st, DAY + days(6 + PAUSE), [mcq("CARD-01", 2, retests="G0001")], ["CARD-01"])
    assert res["CARD-01"]["drilldown_limit"] is True and due(st, "CARD-01") == DAY + days(6 + 2 * PAUSE)


def test_in_the_theme_the_first_miss_in_the_block_still_comes_back_after_the_rest():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("CARD-01", 5)])
    cme.start_block(st, "CARD", "learner")          # a new block on the same theme: its count starts again
    play(st, DAY + days(4), [mcq("CARD-02", 5)])
    res = play(st, DAY + days(7), [mcq("CARD-01", 2)], ["CARD-01"])
    assert "drilldown_limit" not in res["CARD-01"] and due(st, "CARD-01") == DAY + days(10)


def test_a_paused_theme_topic_is_not_brought_back_before_its_date():
    # a gap awaiting its retest, or the theme running out, does not undo the pause (as with the
    # learner's stop, issue #75)
    st = new_ledger("CARD")
    play(st, DAY, [mcq("CARD-01", 2)])                         # missed, no gap written
    play(st, DAY + days(3), [mcq("CARD-01", 2)], ["CARD-01"])  # missed again: paused, a gap awaiting its retest
    assert cme.gap_awaits_retest(gap_of(st, "CARD-01")) and due(st, "CARD-01") == DAY + days(3 + PAUSE)
    for k in (6, 8):
        assert "CARD-01" not in planned(st, DAY + days(k))
        play(st, DAY + days(k), [mcq("CARD-0%d" % k, 5)])
    assert "CARD-01" in planned(st, DAY + days(3 + PAUSE))
    assert "CARD-01" in planned(st, DAY + days(8), allow_repeat=True)   # the learner's one-off request


def test_a_good_answer_on_the_second_round_is_not_paused():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("CARD-01", 2)], ["CARD-01"])
    res = play(st, DAY + days(3), [mcq("CARD-01", 5, retests="G0001")])
    assert "drilldown_limit" not in res["CARD-01"] and due(st, "CARD-01") == DAY + days(6)
    play(st, DAY + days(6), [mcq("CARD-02", 5)])
    assert "CARD-01" in planned(st, DAY + days(9))


def test_applying_a_round_again_keeps_its_place_in_the_block():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("CARD-01", 2)], ["CARD-01"])
    play(st, DAY + days(3), [mcq("CARD-02", 5)])
    rnd = {"items": [mcq("CARD-01", 2, retests="G0001")], "title": "t", "summary": "s", "tags": ["x"],
           "gaps": [{"topic": "CARD-01", "gap": "missed the point", "source": "graded"}]}
    cme.record_round(st, copy.deepcopy(rnd), DAY + days(6))
    sess = st["sessions"][-1]
    again = cme.record_round(st, copy.deepcopy(rnd), DAY + days(6), again=sess)
    assert again["topics"]["CARD-01"]["drilldown_limit"] is True and due(st, "CARD-01") == DAY + days(6 + PAUSE)


def test_outside_the_theme_a_miss_gets_one_retest_then_ordinary_spacing():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("RENAL-02", 2)], ["RENAL-02"])
    assert due(st, "RENAL-02") == DAY + days(3)
    item = planned(st, DAY + days(3))["RENAL-02"]              # the one targeted retest
    assert item["share"] == "repeat" and item["retest_gap"]["id"] == "G0001"
    res = play(st, DAY + days(3), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])
    assert res["RENAL-02"]["drilldown_limit"] is True and due(st, "RENAL-02") == DAY + days(3 + PAUSE)
    # the gap, though written again, has had its retest: nothing brings the topic back early
    assert not cme.gap_awaits_retest(gap_of(st, "RENAL-02"))
    for k in (6, 8):
        play(st, DAY + days(k), [mcq("CARD-0%d" % k, 5)])
        assert "RENAL-02" not in planned(st, DAY + days(k + 1), allow_repeat=False)
    assert "RENAL-02" in planned(st, DAY + days(3 + PAUSE))
    # and a further miss is no new drill-down either
    res = play(st, DAY + days(3 + PAUSE), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])
    assert res["RENAL-02"]["drilldown_limit"] is True and due(st, "RENAL-02") == DAY + days(3 + 2 * PAUSE)


def test_outside_the_theme_a_second_miss_without_a_written_gap_counts_too():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("RENAL-02", 2)])
    res = play(st, DAY + days(5), [mcq("RENAL-02", 3, correct=True)])
    assert res["RENAL-02"]["drilldown_limit"] is True and due(st, "RENAL-02") == DAY + days(5 + PAUSE)


def test_in_its_own_block_the_topic_is_drilled_again():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("RENAL-02", 2)], ["RENAL-02"])
    play(st, DAY + days(3), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])
    cme.start_block(st, "RENAL", "learner")
    play(st, DAY + days(10), [mcq("RENAL-03", 5)])
    res = play(st, DAY + days(13), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])
    assert "drilldown_limit" not in res["RENAL-02"] and due(st, "RENAL-02") == DAY + days(16)


def test_a_good_answer_keeps_its_spacing():
    st = new_ledger("CARD")
    for k, topic in enumerate(("CARD-01", "RENAL-02")):
        play(st, DAY + days(k), [mcq(topic, 2)], [topic])
    res = play(st, DAY + days(4), [mcq("CARD-01", 5, retests="G0001"), mcq("RENAL-02", 5, retests="G0002")])
    assert st["gaps"] == [] and not any("drilldown_limit" in r for r in res.values())
    assert due(st, "CARD-01") == due(st, "RENAL-02") == DAY + days(4 + 3)


def test_reflecting_later_keeps_the_limit_whatever_the_theme_is_by_then():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("CARD-01", 2)], ["CARD-01"])
    rnd = {"items": [mcq("CARD-01", 2, retests="G0001")], "title": "t", "summary": "s", "tags": ["x"]}
    recorded = cme.record_round(st, rnd, DAY + days(3))["topics"]["CARD-01"]
    cme.start_block(st, "RENAL", "learner")
    reflected = cme.reflect_round(st, {}, DAY + days(4))["topics"]["CARD-01"]
    assert recorded == reflected and reflected["drilldown_limit"] is True
    assert due(st, "CARD-01") == DAY + days(3 + PAUSE)


def test_a_change_of_theme_makes_the_new_themes_topics_drillable_from_the_next_round():
    st = new_ledger("CARD")
    play(st, DAY, [mcq("RENAL-02", 2)], ["RENAL-02"])
    play(st, DAY + days(3), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])      # paused: outside the theme
    play(st, DAY + days(5), [mcq("CARD-01", 5)])
    assert due(st, "RENAL-02") == DAY + days(3 + PAUSE)
    assert "RENAL-02" not in planned(st, DAY + days(7))
    assert cme.change_theme(st, "RENAL")["changed"] is True
    item = planned(st, DAY + days(7))["RENAL-02"]            # its domain's block: the pause is over
    assert item["share"] == "theme" and item["retest_gap"]["id"] == "G0001"
    # a miss now counts in the theme: back after the rest, and after two rounds in a row it pauses
    res = play(st, DAY + days(7), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])
    assert "drilldown_limit" not in res["RENAL-02"] and due(st, "RENAL-02") == DAY + days(10)
    res = play(st, DAY + days(10), [mcq("RENAL-02", 2, retests="G0001")], ["RENAL-02"])
    assert res["RENAL-02"]["drilldown_limit"] is True and due(st, "RENAL-02") == DAY + days(10 + PAUSE)
    # that pause, given in the theme, stands; and the old theme's topics are now outside it
    play(st, DAY + days(13), [mcq("RENAL-03", 5)])
    assert "RENAL-02" not in planned(st, DAY + days(16))
    play(st, DAY + days(16), [mcq("CARD-02", 2)], ["CARD-02"])
    res = play(st, DAY + days(19), [mcq("CARD-02", 2, retests="G0002")], ["CARD-02"])
    assert res["CARD-02"]["drilldown_limit"] is True and st["sessions"][-1]["block"]["theme"] == "RENAL"

"""Themed blocks, first version (issue #16, ADR 0003): rounds run in blocks of 12 on one domain;
the short questions are shared 60/25/15 between the theme, due repeats and a wildcard; the case
is on the theme; the learner is told the theme and the position and nothing more; a ledger
written before blocks keeps everything and starts its first block with the next round."""
import copy
import datetime as dt
import json
import re

import pytest

import examples
from examples import LEDGERS, cme

# the example ledgers written before blocks (`drilled`, issue #18, is in the middle of one)
ledgers = pytest.mark.parametrize("name", [n for n in LEDGERS if "block" not in examples.load_ledger(n)])
SHARES = dict(cme.BLOCK_SHARES)


def topic_for(st, item, taken):
    try:
        return examples.topic_for(st, item, taken)
    except AssertionError:      # every topic of the domain is tested: the author revisits one
        return next(tid for tid, info in sorted(cme.bp_topics(st).items())
                    if info["domain"] == item["domain"] and tid not in taken)


def play_rounds(st, start, n, every=3, **options):
    """Plan, record and reflect `n` rounds on `st`, one every `every` days. Returns the plans."""
    plans = []
    for k in range(n):
        day = start + dt.timedelta(days=every * k)
        plan = cme.plan_round(st, examples.plan_options(**options), day)
        for it in plan["items"]:                     # the author settles the items left to a domain
            if not it.get("topic"):
                it["topic"] = topic_for(st, it, {x.get("topic") for x in plan["items"]})
        rnd = examples.round_for(st, plan)
        cme.record_round(st, copy.deepcopy(rnd), day)
        cme.reflect_round(st, examples.reflection_for(rnd), day)
        plans.append(plan)
    return plans


def fresh():
    return examples.load_ledger("fresh"), examples.today_of("fresh")


# ---- the mix

def test_mix_is_60_25_15_over_a_block_within_rounding():
    for shorts in range(0, 17):
        given = {name: 0 for name in SHARES}
        for n in range(1, cme.BLOCK_LENGTH + 1):
            mix = cme.block_mix(shorts, n)
            assert sum(mix.values()) == shorts and min(mix.values()) >= 0
            for name in SHARES:
                given[name] += mix[name]
                assert abs(given[name] - shorts * n * SHARES[name] / 100.0) < 1, (shorts, n, name)


def test_three_short_questions_still_get_a_wildcard_some_rounds():
    mixes = [cme.block_mix(3, n) for n in range(1, 13)]
    assert mixes[0] == {"theme": 2, "repeat": 1, "wildcard": 0}
    assert sum(m["wildcard"] for m in mixes) == 5 and sum(m["repeat"] for m in mixes) == 9


def test_with_a_large_backlog_repeats_get_40_percent_from_the_themes_share():
    # issue #79: 45/40/15 over a block while six or more topics are overdue; the wildcard keeps its 15%
    backlog = dict(cme.BACKLOG_SHARES)
    assert backlog == {"theme": 45, "repeat": 40, "wildcard": 15} and cme.BACKLOG_OVERDUE == 6
    for shorts in range(2, 17):
        given = {name: 0 for name in SHARES}
        for n in range(1, cme.BLOCK_LENGTH + 1):
            mix, plain = cme.block_mix(shorts, n, True), cme.block_mix(shorts, n)
            assert sum(mix.values()) == shorts and min(mix.values()) >= 0
            assert mix["wildcard"] == plain["wildcard"] and mix["repeat"] >= plain["repeat"]
            for name in SHARES:
                given[name] += mix[name]
                assert abs(given[name] - shorts * n * backlog[name] / 100.0) < 2, (shorts, n, name)
    # the first round of a backlog gains a repeat at once
    assert cme.block_mix(3, 1, True) == {"theme": 1, "repeat": 2, "wildcard": 0}


def test_the_wildcards_share_holds_however_often_the_backlog_comes_and_goes():
    import itertools
    for shorts in (3, 4, 6):
        for seq in itertools.product((False, True), repeat=cme.BLOCK_LENGTH):
            total = sum(cme.block_mix(shorts, n, b)["wildcard"] for n, b in enumerate(seq, 1))
            assert total == sum(cme.block_mix(shorts, n)["wildcard"] for n in range(1, cme.BLOCK_LENGTH + 1))


def overdue_ledger(n_due):
    st, today = fresh()
    cme.start_block(st, "CARD", "learner")
    off = sorted(tid for tid, info in cme.bp_topics(st).items() if info["domain"] != "CARD")
    for tid in off[:n_due]:
        t = cme.ensure_topic(st, tid)
        t.update({"last": "2026-08-01", "due": "2026-08-10", "attempts": 1, "mastery": 3, "step": 1,
                  "history": [["2026-08-01", 3, None, "not_rated"]]})
    return st, today


@pytest.mark.parametrize("n_due, backlog", [(5, False), (6, True), (11, True)])
def test_the_plan_takes_the_backlog_shares_from_six_overdue_topics(n_due, backlog):
    st, today = overdue_ledger(n_due)
    st["config"]["mcqs"] = 3
    plan = cme.plan_round(st, examples.plan_options(), today)
    assert plan["block"]["mix"] == cme.block_mix(3, 1, backlog)
    assert ("backlog" in plan["block"]) is backlog
    if backlog:
        assert plan["block"]["backlog"] == {"overdue": n_due, "shares": dict(cme.BACKLOG_SHARES)}
        assert sum(it["share"] == "repeat" for it in plan["items"]) == 2


def test_a_backlog_is_worked_off_faster(monkeypatch):
    def retested(rounds):
        st, today = overdue_ledger(11)
        st["config"]["mcqs"] = 3
        backlog = set(st["topics"])
        plans = play_rounds(st, today, rounds)
        return len({it.get("topic") for p in plans for it in p["items"]} & backlog)
    faster = retested(8)
    monkeypatch.setattr(cme, "BACKLOG_OVERDUE", 10 ** 6)          # the shares as before issue #79
    assert faster >= retested(8) + 3


def test_a_block_of_rounds_follows_the_mix_and_keeps_the_case_on_the_theme():
    st, today = fresh()
    st["config"]["mcqs"] = 4
    plans = play_rounds(st, today, cme.BLOCK_LENGTH)
    theme = plans[0]["block"]["theme"]
    count = {"theme": 0, "repeat": 0, "wildcard": 0}
    owed = dict(count)
    for n, plan in enumerate(plans, 1):
        assert plan["block"]["theme"] == theme and plan["block"]["round"] == n
        assert plan["block"]["mix"] == cme.block_mix(4, n, "backlog" in plan["block"])
        for name in owed:
            owed[name] += plan["block"]["mix"][name]
        case = [it for it in plan["items"] if it["slot"] == "case"]
        assert len(case) == 1 and case[0]["domain"] == theme and case[0]["share"] == "theme"
        for it in plan["items"]:
            if it["slot"] == "case":
                continue
            count[it["share"]] += 1
            if it["share"] == "theme":
                assert it["domain"] == theme
            elif it["share"] == "repeat":
                assert it["reason_code"] in ("due", "gap")
            else:
                assert it["domain"] != theme and it["reason_code"] in ("new", "new_in_domain")
    shorts = 4 * cme.BLOCK_LENGTH
    # a repeat slot with nothing waiting goes to the theme, so the theme can only gain
    assert count["wildcard"] == owed["wildcard"] == round(shorts * 0.15)
    assert 0 < count["repeat"] <= owed["repeat"]
    assert count["theme"] >= owed["theme"] >= round(shorts * 0.45)
    assert sum(count.values()) == shorts


def test_no_topic_comes_back_within_the_rest_even_inside_the_theme():
    st, today = fresh()
    last = {}
    for k, plan in enumerate(play_rounds(st, today, cme.BLOCK_LENGTH, every=2)):
        for it in plan["items"]:
            assert k - last.get(it["topic"], -9) >= 2       # two-day rounds: never in consecutive rounds
            last[it["topic"]] = k


def test_a_one_off_domain_round_overrides_the_theme_and_still_counts():
    st, today = fresh()
    plan = play_rounds(st, today, 1, domain="GI")[0]
    assert {it["domain"] for it in plan["items"]} == {"GI"}
    assert plan["block"]["mix"] is None and plan["block"]["theme"] != "GI"
    assert st["block"]["round"] == 1 and st["block"]["theme"] == plan["block"]["theme"]


# ---- the ledger tracks the block

def test_planning_does_not_write_the_block_and_recording_does():
    st, today = fresh()
    before = copy.deepcopy(st)
    plan = cme.plan_round(st, examples.plan_options(), today)
    assert st == before and not st.get("block")
    assert plan["block"]["starts"] is True and plan["block"]["round"] == 1
    play_rounds(st, today, 1)
    assert st["block"]["theme"] == plan["block"]["theme"]
    assert (st["block"]["round"], st["block"]["length"], st["block"]["started"]) == (1, 12, cme.iso(today))
    assert st["sessions"][-1]["block"] == {"theme": plan["block"]["theme"], "round": 1, "length": 12}


def test_reflecting_does_not_count_the_round_twice():
    st, today = fresh()
    plan = cme.plan_round(st, examples.plan_options(), today)
    rnd = examples.round_for(st, plan)
    cme.record_round(st, copy.deepcopy(rnd), today)
    assert st["block"]["round"] == 1
    cme.reflect_round(st, examples.reflection_for(rnd), today + dt.timedelta(days=4))
    assert st["block"]["round"] == 1 and st["sessions"][-1]["block"]["round"] == 1


def test_after_twelve_rounds_the_next_block_starts_on_another_theme():
    st, today = fresh()
    plans = play_rounds(st, today, cme.BLOCK_LENGTH + 1)
    first, second = plans[0]["block"]["theme"], plans[-1]["block"]["theme"]
    assert [p["block"]["round"] for p in plans] == list(range(1, 13)) + [1]
    assert plans[-1]["block"]["starts"] is True and second != first
    assert [b["theme"] for b in st["blocks"]] == [first] and st["blocks"][0]["round"] == 12
    assert st["block"]["theme"] == second and st["block"]["round"] == 1
    assert [s["block"]["round"] for s in st["sessions"]] == list(range(1, 13)) + [1]


def test_status_after_the_last_round_of_a_block_names_the_next_theme():
    st, today = fresh()
    play_rounds(st, today, cme.BLOCK_LENGTH)
    status = cme.block_status(st)
    assert status["starts"] is True and status["round"] == 1 and status["theme"] != st["block"]["theme"]


# ---- the first theme, and the next

def test_proposed_theme_is_the_weakest_and_then_the_longest_unvisited():
    st, _ = fresh()
    assert cme.propose_theme(st)["theme"] == "CARD"          # nothing known: weight, then blueprint order
    st["profile"]["domain_self_ratings"] = {"RENAL": 1}      # the learner says where they are weakest
    assert cme.propose_theme(st)["theme"] == "RENAL"
    st["block"] = {"theme": "RENAL", "round": 12, "length": 12}
    assert cme.propose_theme(st)["theme"] != "RENAL"         # not the same theme twice running
    # RENAL had its block two blocks ago: it still waits, although it is the weakest
    st["blocks"] = [{"theme": "RENAL"}]
    st["block"] = {"theme": "CARD", "round": 12, "length": 12}
    assert cme.propose_theme(st)["theme"] == "PULM"
    # once every other large domain has had a block since, it is its turn again
    st["blocks"] = [{"theme": d} for d in ("RENAL", "PULM", "ID", "GEN")]
    assert cme.propose_theme(st)["theme"] == "RENAL"


def test_proposal_gives_a_reason_and_skips_domains_too_small_for_a_block():
    st, _ = fresh()
    st["profile"]["domain_self_ratings"] = {"TOX": 1, "EMRG": 1}     # three and two topics
    p = cme.propose_theme(st)
    assert p["theme"] not in ("TOX", "EMRG") and "TOX" not in p["ranking"]
    assert p["reason"] == "Cardiology: nothing tested yet, not yet a theme"
    assert cme.propose_theme(st, exclude=["CARD"])["theme"] == "PULM"


def test_a_block_can_be_started_on_a_chosen_theme():
    """What "changing the theme" (issue #17) builds on."""
    st, today = fresh()
    play_rounds(st, today, 2)
    old = st["block"]["theme"]
    cme.start_block(st, "GI", chosen="learner")
    plan = cme.plan_round(st, examples.plan_options(), today + dt.timedelta(days=9))
    assert plan["block"]["line"] == "Block: Gastroenterology & Hepatology, round 1 of 12"
    assert st["blocks"] == [{"theme": old, "started": cme.iso(today), "last": cme.iso(today + dt.timedelta(days=3)),
                             "round": 2, "length": 12, "chosen": "auto"}]
    with pytest.raises(cme.CmeError):
        cme.start_block(st, "NOPE")


# ---- what the learner is told

@ledgers
def test_opening_line_names_the_theme_and_position_and_nothing_else(name, work):
    st = examples.load_ledger(name)
    work.write_ledger(st)
    out = work.start(LEDGERS[name])
    plan = work.read_json("plan.json")
    names = {info["name"] for info in st["blueprint"].values()}
    m = re.match(r"^Block: (.+), round (\d+) of 12$", out["block"]["line"])
    assert m and m.group(1) in names and m.group(2) == "1"
    # a block that starts also gives its reason (issue #17): domain level, like the theme itself
    assert out["block"]["starts"] is True and out["block"]["reason"].startswith(m.group(1) + ": ")
    assert {k: v for k, v in out["block"].items() if k != "reason"} == {k: v for k, v in plan["block"].items() if k not in ("mix", "backlog")}
    assert out["plan"]["block"] == out["block"]["line"]
    assert set(out["block"]) == {"theme", "name", "round", "length", "starts", "line", "reason"}
    labels = {it["label"] for it in plan["items"] if it.get("label")}
    assert labels and not any(label in json.dumps(out) for label in labels)


# ---- a ledger from before blocks

@ledgers
def test_ledger_written_before_blocks_keeps_everything_and_starts_its_first_block(name, capsys, tmp_path):
    st = examples.load_ledger(name)
    assert "block" not in st and "blocks" not in st
    before = copy.deepcopy(st)
    today = examples.today_of(name)
    plan = cme.plan_round(st, examples.plan_options(), today)
    assert plan["block"]["round"] == 1 and plan["block"]["starts"] is True
    rnd = examples.round_for(st, plan)
    tested = {it["topic"] for it in rnd["items"]}
    cme.record_round(st, copy.deepcopy(rnd), today)

    def plain(s):
        return {k: v for k, v in s.items() if k not in ("_snapshot", "_round", "reflection")}
    assert [plain(s) for s in st["sessions"][:-1]] == [plain(s) for s in before["sessions"]]
    assert st["previous"] == before["previous"]
    for tid, t in before["topics"].items():
        if tid not in tested:
            assert st["topics"][tid] == t                    # due dates and history untouched
    kept = {g["topic"]: g["gap"] for g in st["gaps"]}
    for g in before["gaps"]:
        if g["topic"] not in tested:
            assert kept[g["topic"]] == g["gap"]
    assert st["block"]["round"] == 1 and st["blocks"] == []
    assert "block" not in st["sessions"][0] or len(st["sessions"]) == 1
    path = str(tmp_path / "ledger.json")
    cme.save_json(st, path)
    assert cme.main(["validate", path]) == 0, capsys.readouterr().out

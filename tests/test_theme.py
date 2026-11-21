"""Changing the theme (issue #17, ADR 0003): the end of a block proposes the next theme in one
line with its reason; the learner changes the theme in one line ("pick another", or naming an
area), at the end of a block or in the middle of one; the opening line of a block gives the
reason for its theme."""
import copy
import datetime as dt
import os

import pytest

import examples
from conftest import Work
from examples import cme
from test_blocks import fresh, play_rounds


def last_round(st, tmp_path, rounds=cme.BLOCK_LENGTH - 1):
    """A work folder whose ledger is one round short of the end of its block."""
    st["block"] = {"theme": "CARD", "round": rounds, "length": cme.BLOCK_LENGTH,
                   "started": "2026-09-01", "last": "2026-10-20", "chosen": "auto"}
    os.makedirs(str(tmp_path))
    w = Work(tmp_path)
    w.write("state.json", st)
    return w


# ---- the proposal at the end of a block

def test_block_end_proposes_the_next_theme_in_one_line_with_its_reason():
    st, today = fresh()
    plans = play_rounds(st, today, cme.BLOCK_LENGTH - 1)
    assert cme.block_end(st) is None                         # rounds still to come: nothing to propose
    play_rounds(st, today + dt.timedelta(days=40), 1)
    end = cme.block_end(st)
    first = plans[0]["block"]
    assert end["finished"] == first["name"] and end["theme"] != first["theme"]
    assert end["theme"] == cme.block_status(st)["theme"]     # the proposal is what the next round would get
    assert end["line"] == 'Block finished: %s. Next block: %s. To change it, say "pick another" or name an area.' % (
        first["name"], end["reason"])
    assert "\n" not in end["line"] and end["reason"].startswith(end["name"] + ": ")


def test_save_and_close_of_the_last_round_carry_the_proposal_and_earlier_rounds_do_not(tmp_path):
    st, _ = fresh()
    w = last_round(st, tmp_path / "a")
    saved = w.save_round("2026-11-01")
    assert saved["next_block"]["finished"] == "Cardiology" and saved["next_block"]["theme"] != "CARD"
    closed = w.close_round("2026-11-01")
    assert closed["next_block"]["line"].startswith("Block finished: Cardiology. Next block: ")
    assert "\n" not in closed["next_block"]["line"]
    w = last_round(fresh()[0], tmp_path / "b", rounds=3)
    assert "next_block" not in w.save_round("2026-11-01") and "next_block" not in w.close_round("2026-11-01")


def test_the_opening_of_a_new_block_gives_the_reason_and_a_running_block_does_not(work):
    st, today = fresh()
    state = work.write("state.json", st)
    out = work.run_json("--today", cme.iso(today), "status", state)
    assert out["block"]["starts"] is True and out["block"]["reason"] == "Cardiology: nothing tested yet, not yet a theme"
    play_rounds(st, today, 2)
    out = work.run_json("--today", cme.iso(today + dt.timedelta(days=9)), "status", work.write("state.json", st))
    assert out["block"]["starts"] is False and "reason" not in out["block"]


# ---- changing it

def test_naming_a_domain_mid_block_starts_a_new_block_and_files_the_old_one():
    st, today = fresh()
    play_rounds(st, today, 3)
    old = st["block"]["theme"]
    res = cme.change_theme(st, theme="GI")
    assert res["changed"] and res["was"] == {"theme": old, "name": cme.domain_name(st, old), "round": 3,
                                             "length": 12, "begun": True}
    assert st["block"]["theme"] == "GI" and st["block"]["round"] == 0 and st["block"]["chosen"] == "learner"
    assert [(b["theme"], b["round"]) for b in st["blocks"]] == [(old, 3)]
    status = cme.block_status(st)
    assert status["line"] == "Block: Gastroenterology & Hepatology, round 1 of 12" and status["starts"] is True
    # the next round is planned on the new theme and counts as its first
    plan = play_rounds(st, today + dt.timedelta(days=12), 1)[0]
    assert next(it for it in plan["items"] if it["slot"] == "case")["domain"] == "GI"
    assert st["block"]["round"] == 1 and st["block"]["chosen"] == "learner" and st["sessions"][-1]["block"]["theme"] == "GI"
    assert len(st["blocks"]) == 1                           # the chosen block was not filed and begun twice
    # history, gaps and due dates were not touched by the change
    before = copy.deepcopy(st)
    cme.change_theme(st, theme="RENAL")
    for key in ("topics", "gaps", "sessions", "previous", "agg", "config", "profile"):
        assert st.get(key) == before.get(key), key


def test_a_domain_can_be_named_by_id_name_or_part_of_the_name():
    st, _ = fresh()
    for said in ("GI", "gi", "Gastroenterology & Hepatology", "gastro", "hepatol"):
        assert cme.find_domain(st, said) == "GI", said
    for said in ("", "astrology", "olog"):                   # nothing, unknown, or fits several
        with pytest.raises(cme.CmeError) as err:
            cme.find_domain(st, said)
        assert "the theme must be one of" in str(err.value)


def test_pick_another_moves_down_the_ranking_and_never_comes_back_to_a_declined_theme():
    st, today = fresh()
    play_rounds(st, today, cme.BLOCK_LENGTH)
    finished = st["block"]["theme"]
    ranking = cme.propose_theme(st)["ranking"]
    seen = [cme.block_end(st)["theme"]]
    for _ in range(4):
        res = cme.change_theme(st, another=True)
        assert res["changed"] and res["reason"].startswith(cme.domain_name(st, st["block"]["theme"]) + ": ")
        seen.append(st["block"]["theme"])
    assert len(set(seen)) == 5 and finished not in seen
    assert seen == [d for d in ranking if d != finished][:5]
    assert st["block"]["declined"] == seen[:-1] and st["block"]["round"] == 0
    assert [b["theme"] for b in st["blocks"]] == [finished]  # only a block with rounds is kept
    # the first round of the block ends the memory of what was declined
    assert cme.block_end(st) is None


def test_pick_another_mid_block_leaves_the_current_theme():
    st, today = fresh()
    play_rounds(st, today, 2)
    old = st["block"]["theme"]
    cme.change_theme(st, another=True)
    second = st["block"]["theme"]
    cme.change_theme(st, another=True)
    assert len({old, second, st["block"]["theme"]}) == 3
    assert [b["theme"] for b in st["blocks"]] == [old]


def test_naming_the_current_theme_changes_nothing_and_confirming_a_proposal_starts_it():
    st, today = fresh()
    play_rounds(st, today, 2)
    before = copy.deepcopy(st)
    assert cme.change_theme(st, theme=st["block"]["theme"])["changed"] is False and st == before
    play_rounds(st, today + dt.timedelta(days=9), cme.BLOCK_LENGTH - 2)
    proposed = cme.block_end(st)["theme"]
    assert cme.change_theme(st, theme=proposed)["changed"] is True
    assert st["block"]["theme"] == proposed and st["block"]["chosen"] == "learner" and st["block"]["round"] == 0


def test_a_small_domain_can_be_chosen_with_a_warning_and_an_empty_one_cannot():
    st, _ = fresh()
    res = cme.change_theme(st, theme="EMRG")                 # two topics: never proposed, but the learner may
    assert st["block"]["theme"] == "EMRG" and "only 2 topics" in res["warnings"][0]
    st["blueprint"]["EMPTY"] = {"name": "Nothing here", "weight": 1.0, "topics": {}}
    with pytest.raises(cme.CmeError):
        cme.change_theme(st, theme="EMPTY")


# ---- the command

@pytest.fixture
def store(tmp_path):
    w = Work(tmp_path)
    w.init()
    w.save_round("2026-11-01")
    w.ledger = w.p("out1", "data", "state.json")
    return w


def test_theme_command_changes_and_places_in_one_command(store):
    before = store.read_json("out1", "data", "state.json")
    out = store.run_json("--today", "2026-11-02", "theme", store.ledger, "--set", "renal", "--out-dir", store.p("outT"))
    name = before["blueprint"]["RENAL"]["name"]
    assert out["ok"] and out["changed"] and out["gen"] == before["gen"] + 1
    assert out["block"]["line"] == "Block: %s, round 1 of 12" % name and out["block"]["starts"] is True
    assert out["say"] == "New block: %s: your choice. Round 1 of 12." % name
    assert out["was"]["theme"] == before["block"]["theme"] and out["was"]["round"] == 1
    assert [f["as"] for f in out["files"]] == ["data/state.json", "data/index.json", "data/prepared.json"]
    placed = store.read_json("outT", "data", "state.json")
    assert placed["block"]["theme"] == "RENAL" and placed["gen"] == out["gen"] and placed["updated"] == "2026-11-02"
    assert store.read_json("outT", "data", "prepared.json") == {"v": 1, "empty": True}   # it was for the old theme
    assert store.read_json("out1", "data", "state.json") == before
    # and the next start opens the new block
    start = store.run_json("--today", "2026-11-05", "start", store.p("outT", "data", "state.json"), "--work", store.p("w2"))
    assert start["block"]["line"] == out["block"]["line"] and start["block"]["reason"] == "%s: your choice" % name


def test_theme_command_pick_another_and_plain_listing(store):
    listing = store.run_json("theme", store.ledger)
    assert listing["changed"] is False and "files" not in listing and listing["next_block"] is None
    assert set(listing["choices"][0]) == {"id", "name", "topics"}
    assert len(listing["choices"]) == len(store.read_json("out1", "data", "state.json")["blueprint"])
    out = store.run_json("theme", store.ledger, "--another", "--out", store.p("next.json"))
    cur = store.read_json("out1", "data", "state.json")["block"]["theme"]
    assert out["changed"] and out["block"]["theme"] != cur and store.read_json("next.json")["block"]["declined"] == [cur]
    assert out["say"].startswith("New block: %s: " % out["block"]["name"])


def test_theme_command_refusals_write_nothing(store):
    for args in (("--set", "nope", "--out-dir", store.p("x")), ("--set", "GI"),
                 ("--set", "GI", "--another", "--out-dir", store.p("x"))):
        r = store.run("theme", store.ledger, *args, ok=False)
        assert r.returncode != 0 and not os.path.exists(store.p("x"))
    cur = store.read_json("out1", "data", "state.json")["block"]["theme"]
    same = store.run_json("theme", store.ledger, "--set", cur, "--out-dir", store.p("y"))
    assert same["changed"] is False and "already the theme" in same["say"] and not os.path.exists(store.p("y"))


def test_theme_output_names_no_topic(store):
    st = store.read_json("out1", "data", "state.json")
    labels = {info["label"] for info in cme.bp_topics(st).values()}
    for args in ((), ("--another", "--out", store.p("n.json")), ("--set", "GI", "--out", store.p("n.json"))):
        text = store.run("theme", store.ledger, *args).stdout
        assert not any(label in text for label in labels)

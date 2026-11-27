"""Usage: Full or Economy (issue #93, ADR 0015). `config.usage` picks a preset that decides some
settings for the learner, resolved when the settings are read; what the learner set themselves
wins; ledgers from before stay full and keep what they chose; Economy's own mix has the case every
other round, by whether the last round recorded had one."""
import copy
import datetime as dt
import json

import pytest

import examples
from examples import cme
from conftest import Work

LATER = "2099-01-02T21:40:12.512Z"
EARLIER = "2020-01-02T21:40:12.512Z"


def ledger(**config):
    st = cme.new_state(dt.date(2026, 11, 1))
    st["config"].update(config)
    return cme.make_current(st)


def economy_from(name):
    """An example ledger moved to Economy with nothing of the preset set by the learner."""
    st = examples.load_ledger(name)
    st["config"].update(usage="economy", set_by_learner=[])
    return st


# ---------------------------------------------------------------- the preset, resolved at read time

def test_full_is_the_config_as_it_stands():
    st = ledger()
    eff = cme.effective_config(st["config"])
    assert {k: eff[k] for k in st["config"]} == st["config"] and eff["case_every"] == 1
    assert cme.usage_status(st) == {"mode": "full", "author": "most_capable", "evidence": "full",
                                    "evidence_ladder": True, "listening": True, "guideline_sweeps": "custom",
                                    "case_every": 1, "kept": []}


def test_economy_resolves_to_its_preset_without_writing_it_into_the_config():
    st = ledger(usage="economy")
    stored = copy.deepcopy(st["config"])
    eff = cme.effective_config(st["config"])
    assert {k: eff[k] for k in cme.USAGE_PRESETS["economy"]} == cme.USAGE_PRESETS["economy"]
    assert eff["case_every"] == 2 and st["config"] == stored        # the learner's values stay in the config
    assert cme.usage_status(st) == {"mode": "economy", "author": "examiner", "evidence": "keys",
                                    "evidence_ladder": False, "listening": False, "guideline_sweeps": "off",
                                    "case_every": 2, "kept": []}
    assert cme.listening_on(st) is False and cme.guideline_sweeps(st) == "off"
    assert cme.evidence_depth(st, "CARD-01") is None
    assert cme.mix_in_force(st) == {"mcqs": 2, "focused": 1, "case": True, "case_every": 2}
    # back to full: the settings are as they were
    st["config"]["usage"] = "full"
    assert cme.listening_on(st) is True and cme.mix_in_force(st)["mcqs"] == cme.DEFAULT_CONFIG["mcqs"]


def test_settings_the_learner_set_win_over_the_preset():
    st = ledger(usage="economy", listening=True, guideline_sweeps="all", mcqs=0, focused=2, case=True,
                set_by_learner=["listening", "guideline_sweeps", "focused"])
    eff = cme.effective_config(st["config"])
    assert eff["listening"] is True and eff["guideline_sweeps"] == "all"
    assert eff["evidence_ladder"] is False                          # not theirs: the preset's
    # one key of the mix set makes the whole mix theirs, the case in every round
    assert cme.mix_in_force(st) == {"mcqs": 0, "focused": 2, "case": True, "case_every": 1}
    assert cme.usage_status(st)["kept"] == ["guideline_sweeps", "listening", "mix"]


def test_note_set_by_learner_adds_what_a_change_sets_and_can_hand_it_back():
    cfg = {"set_by_learner": ["listening"]}
    cme.note_set_by_learner(cfg, {"mcqs": 2, "session_minutes": 20})
    assert cfg["set_by_learner"] == ["mcqs", "listening"]           # only what a preset decides
    cme.note_set_by_learner(cfg, {"set_by_learner": []})
    assert cfg["set_by_learner"] == []


@pytest.mark.parametrize("change", [{"usage": "cheap"}, {"set_by_learner": ["session_minutes"]},
                                    {"set_by_learner": "listening"}])
def test_a_usage_change_the_engine_would_not_store_is_refused(change):
    with pytest.raises(cme.CmeError):
        cme.check_setting_changes(change)


# ---------------------------------------------------------------- existing ledgers stay full

@pytest.mark.parametrize("name", sorted(examples.LEDGERS))
def test_existing_ledgers_stay_full_and_their_mix_is_their_own(name):
    raw = examples.load_ledger(name, raw=True)
    assert "usage" not in raw["config"] and "set_by_learner" not in raw["config"]
    st = examples.load_ledger(name)
    assert st["config"]["usage"] == "full" and cme.usage_status(st)["mode"] == "full"
    assert set(cme.MIX_KEYS) <= set(st["config"]["set_by_learner"])
    assert "usage" not in cme.plan_round(copy.deepcopy(st), examples.plan_options(), examples.today_of(name))


def test_an_existing_learner_who_moves_to_economy_keeps_what_they_chose():
    st = examples.load_ledger("mid_curriculum", raw=True)
    st["config"]["listening"] = False                  # turned off before the preset existed
    st = cme.make_current(st)
    assert st["config"]["set_by_learner"] == ["mcqs", "focused", "case", "listening"]
    mix = {k: st["config"][k] for k in cme.MIX_KEYS}
    st["config"]["usage"] = "economy"
    assert {k: v for k, v in cme.mix_in_force(st).items() if k != "case_every"} == mix
    assert cme.usage_status(st)["kept"] == ["listening", "mix"]


# ---------------------------------------------------------------- Economy's mix: the case every other round

def test_the_case_comes_every_other_round_by_whether_the_last_round_had_one():
    st = economy_from("mid_curriculum")
    today = examples.today_of("mid_curriculum")
    counts = []
    for n in range(4):
        plan = cme.plan_round(st, examples.plan_options(), today)
        counts.append(plan["counts"])
        assert plan["counts"] == cme.plan_counts(st)
        assert plan["usage"] == {"mode": "economy", "author": "examiner", "evidence": "keys"}
        assert plan["listening"] is False and plan["evidence_ladder"] is False
        cme.record_round(st, examples.round_for(st, plan), today)
        today += dt.timedelta(days=2)
    last_had_case = bool(examples.load_ledger("mid_curriculum")["sessions"][-1].get("case"))
    first = 0 if last_had_case else 1
    assert [c["case"] for c in counts] == [first, 1 - first, first, 1 - first]
    assert all(c["mcqs"] == 2 and c["focused"] == 1 for c in counts)


def test_a_round_stopped_before_its_case_leaves_the_case_for_the_next():
    st = economy_from("mid_curriculum")
    st["sessions"][-1]["case"] = None
    assert cme.case_in_turn(st) is True
    st["sessions"][-1]["case"] = {"topic": "CARD-01"}
    assert cme.case_in_turn(st) is False
    st["sessions"], st["previous"] = [], []
    assert cme.case_in_turn(st) is True                 # a new learner's first round has the case


def test_a_round_without_its_case_is_planned_as_the_same_round_with_no_case_and_spacing_is_untouched():
    st = economy_from("mid_curriculum")
    st["sessions"][-1]["case"] = {"topic": "CARD-01"}   # the last round had the case
    today = examples.today_of("mid_curriculum")
    before = copy.deepcopy(st)
    economy = cme.plan_round(st, examples.plan_options(), today)
    assert st == before                                  # planning reads only: no topic's schedule moves
    assert economy["counts"] == {"mcqs": 2, "focused": 1, "case": 0}
    full = copy.deepcopy(st)
    full["config"].update(usage="full", mcqs=2, focused=1, case=True, evidence_ladder=False, listening=False,
                          guideline_sweeps="off")
    same = cme.plan_round(full, examples.plan_options(no_case=True), today)
    strip = lambda p: [(i["slot"], i.get("topic"), i.get("domain"), i["reason_code"]) for i in p["items"]]
    assert strip(economy) == strip(same)                 # the topics it plays are the ones a no-case round plays


# ---------------------------------------------------------------- setup, settings and the page

def test_onboarding_init_with_economy_lets_the_preset_decide_and_says_who_writes(tmp_path):
    w = Work(tmp_path)
    out = w.run_json("--today", "2026-11-01", "init", "--work", w.path, "--blueprint", examples.cme.DEFAULT_BLUEPRINT_PATH,
                     "--config", json.dumps({"usage": "economy"}), "--profile", "{}")
    assert out["usage"]["mode"] == "economy" and out["usage"]["author"] == "examiner"
    assert out["round"]["mix"] == "2 MCQs + 1 focused question + the case every other round"
    st = w.read_json("publish", "data", "state.json")
    assert st["config"]["usage"] == "economy" and st["config"]["set_by_learner"] == []
    assert st["config"]["usage_set_at"]
    w.publish()
    w.forget_job()
    r = w.start("2026-11-02")
    assert r["usage"]["mode"] == "economy" and r["usage"]["evidence"] == "keys"
    assert r["listening"]["on"] is False
    assert (r["plan"]["mcqs"], r["plan"]["focused"], r["plan"]["case"]) == (2, 1, 1)
    assert r["opening"].startswith("Today's round: 2 MCQs + 1 focused question + the case")


def test_onboarding_init_with_economy_and_a_mix_of_their_own(tmp_path):
    w = Work(tmp_path)
    w.init(config={"usage": "economy", "listening": True}, mix={"mcqs": 0, "focused": 1, "case": True})
    st = w.read_ledger()
    assert st["config"]["set_by_learner"] == ["mcqs", "focused", "case", "listening"]
    assert cme.mix_in_force(cme.make_current(st)) == {"mcqs": 0, "focused": 1, "case": True, "case_every": 1}
    assert cme.listening_on(st) is True


def test_settings_switch_to_economy_and_back_and_report_the_effective_settings(work):
    work.init()             # the mix chosen at setup: three MCQs and the case
    work.open(today="2026-11-02")
    out = work.run_json("--today", "2026-11-02", "settings", "--work", work.path,
                        "--config", json.dumps({"usage": "economy"}))
    assert out["usage"]["mode"] == "economy" and out["usage"]["kept"] == ["mix"]   # chosen at setup
    assert out["config"]["usage_set_at"] and out["prepared"]["kept"] is False
    out = work.run_json("--today", "2026-11-02", "settings", "--work", work.path,
                        "--config", json.dumps({"set_by_learner": []}))
    assert out["usage"]["kept"] == [] and out["round"]["mix"].endswith("the case every other round")
    out = work.run_json("--today", "2026-11-02", "settings", "--work", work.path,
                        "--config", json.dumps({"usage": "full"}))
    assert out["usage"]["mode"] == "full" and out["round"]["mix"] == "3 MCQs + the case"


def test_the_page_sets_the_usage_once_and_a_later_chat_change_wins(work):
    work.init(mix=None)
    doc = json.dumps({"usage": {"value": "economy", "updated": LATER}})
    r = work.start("2026-11-02", "--prefs", doc)
    assert r["page_settings_applied"] == {"usage": "economy"} and r["usage"]["mode"] == "economy"
    # a page document older than the last change made in a chat is ignored
    st = cme.make_current(work.read_ledger())
    st["config"]["usage_set_at"] = LATER
    assert cme.apply_prefs(st, {"usage": {"value": "full", "updated": EARLIER}}) == {}
    assert st["config"]["usage"] == "full"              # the store's ledger was never moved
    warnings = []
    assert cme.apply_prefs(st, {"usage": {"value": "cheap", "updated": LATER}}, warnings) == {}
    assert warnings and "usage" in warnings[0]


def test_a_mix_saved_on_the_page_under_economy_is_the_learners_own():
    st = ledger(usage="economy", set_by_learner=[])
    changes = cme.apply_prefs(st, {"round": {"mcqs": 3, "focused": 1, "case": True},
                                   "base": st["config"]["round_set_at"], "updated": LATER})
    assert changes == {"mcqs": 3}                       # against the mix the page showed: the preset's
    assert cme.mix_in_force(st) == {"mcqs": 3, "focused": 1, "case": True, "case_every": 1}
    assert st["config"]["set_by_learner"] == ["mcqs", "focused", "case"]


def test_the_page_file_shows_the_usage_and_the_preset_mix_with_its_case():
    st = ledger(usage="economy")
    page = cme.page_doc(st)
    assert page["settings"]["usage"]["value"] == "economy" and page["settings"]["usage"]["set_at"] is None
    assert page["round"]["mix"] == {"mcqs": 2, "focused": 1, "case": True, "case_every": 2}
    full = cme.page_doc(ledger())
    assert "case_every" not in full["round"]["mix"] and full["settings"]["usage"]["value"] == "full"


# ---------------------------------------------------------------- the page's control

def test_the_page_offers_full_or_economy_and_saves_the_choice_beside_the_mix(tmp_path):
    from test_page import STATE, render, store_with
    had = tmp_path / "prefs.json"
    mix = {"round": {"mcqs": 2, "focused": 1, "case": True}, "base": "2020-01-01T10:00:00Z",
           "updated": "2020-03-06T08:00:00.000Z"}
    had.write_text(json.dumps(mix))
    store = store_with(tmp_path / "store")
    shown = render(store, "--db")
    assert shown["hidden"]["usage"] is False and "Usage" in shown["ids"]["settings"]
    assert "Full" in shown["ids"]["settings"] and shown["db"] == []
    out = render(store, "--db", str(had), "--click", "us-economy,usage-save")
    assert len(out["db"]) == 1 and out["db"][0]["path"] == "cme/prefs"
    doc = out["db"][0]["data"]
    assert doc["usage"]["value"] == "economy" and cme.parse_stamp(doc["usage"]["updated"])
    assert {k: doc[k] for k in mix} == mix                          # the mix saved earlier is kept
    assert "Economy (from your next round)" in out["ids"]["settings"]
    # and the engine takes that document as it is
    st = cme.make_current(copy.deepcopy(STATE))
    assert cme.apply_prefs(st, {"usage": doc["usage"]})["usage"] == "economy"
    # without its database the page shows the setting and says how to change it
    plain = render(store)
    assert plain["hidden"]["usage-save"] is True and "ask your assistant" in plain["ids"]["usage-lead"]


def test_the_page_shows_the_economy_mix_with_its_case_every_other_round(tmp_path):
    from test_page import STATE, render, store_with
    st = copy.deepcopy(STATE)
    st["config"].update(usage="economy", set_by_learner=[])
    out = render(store_with(tmp_path, st), "--db")
    assert "2 MCQs + 1 focused question + 1 case every other round" in out["ids"]["settings"]
    assert "Economy" in out["ids"]["settings"] and "every other round" in out["ids"]["mix-lead"]


# ---------------------------------------------------------------- a page usage change and the prepared round

def prepared_store(tmp_path_factory, usage):
    """A store whose next round was prepared under `usage`."""
    import os
    from test_finish_prepare import DAY, Next
    from examples import sealed_files
    w = Next(tmp_path_factory.mktemp("usage-" + usage))
    w.init(today=DAY, config={"usage": usage})
    w.open(today=DAY)
    w.run("--today", DAY, "prepare", "--work", w.path)
    for name, text in sealed_files(w.read_ledger(), w.read_json("next", "plan.json")).items():
        w.write(os.path.join("next", name), text)
    w.check().finish()
    w.publish()
    w.forget_job()
    return w


@pytest.mark.parametrize("was, now", [("full", "economy"), ("economy", "full")])
def test_a_usage_set_on_the_page_sets_the_prepared_round_aside_both_ways(tmp_path_factory, was, now):
    w = prepared_store(tmp_path_factory, was)
    assert not w.read_json("store", "data", "prepared.json").get("empty")  # a round is waiting
    r = w.start("2026-11-03", "--prefs", json.dumps({"usage": {"value": now, "updated": LATER}}))
    assert r["page_settings_applied"] == {"usage": now} and r["usage"]["mode"] == now
    assert r["prepared"]["used"] is False and r["prepared"]["why"] == "usage changed on the page"
    assert r["opening"].endswith("This round is written now, for the usage you set on your page: %s."
                                 % now.capitalize())
    assert "round_mix" not in r
    st = w.read_json("publish", "data", "state.json")                     # kept in the ledger at once
    assert st["config"]["usage"] == now and st["config"]["usage_set_at"] == LATER
    assert w.read_json("publish", "data", "prepared.json") == {"v": 1, "empty": True}
    # the same document again changes nothing: the next round may use what is prepared for it
    w2 = prepared_store(tmp_path_factory, now)
    again = w2.start("2026-11-03", "--prefs", json.dumps({"usage": {"value": now, "updated": EARLIER}}))
    assert "page_settings_applied" not in again and again["prepared"]["used"] is True


def test_the_case_option_brings_the_case_into_a_round_without_it():
    st = economy_from("mid_curriculum")
    st["sessions"][-1]["case"] = {"topic": "CARD-01"}
    today = examples.today_of("mid_curriculum")
    assert cme.plan_round(st, examples.plan_options(), today)["counts"]["case"] == 0
    only = cme.plan_round(st, dict(case=True, mcqs=0, focused=0), today)
    assert only["counts"] == {"mcqs": 0, "focused": 0, "case": 1}
    with pytest.raises(cme.CmeError):
        cme.plan_round(st, dict(case=True, no_case=True), today)

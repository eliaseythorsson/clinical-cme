"""When a round prepared ahead is kept and when it is set aside (issues #41 and #42): settings
that cannot change a round keep it, the ledger generation does not undo that, and the round
mix the learner chose last wins over the mix the prepared round was written for."""
import json
import os
import shutil

import pytest

import examples
from conftest import BLUEPRINT
from examples import cme
from test_finish_prepare import DAY, Next

NEXT_DAY = "2026-11-03"
EMPTY = {"v": 1, "empty": True}
MIX = {"mcqs": 1, "focused": 3}                       # the mix the prepared round is written for
PREPARED_MIX = {"mcqs": 1, "focused": 3, "case": 1}
PAGE_MIX = {"mcqs": 3, "focused": 1, "case": True}      # what the page says instead (issue #42)

NEUTRAL_CONFIG = {
    "testing": True, "reminders": True, "prepare_task": True, "prepare_ahead": False, "helpers": False,
    "show_coding": False, "target_sessions_per_week": 5, "review_interval_days": 30,
    "round_set_at": "2026-11-01T08:00:00Z",
    "guideline_sweeps": "all",                          # which guideline tags are swept, not what is written (#91)
    # what the learner set and when the usage was set (#93): their effect is through the settings
    "usage_set_at": "2026-11-01T08:00:00Z", "set_by_learner": ["listening"],
}
CONTENT_CONFIG = {
    "session_minutes": 30, "mcqs": 2, "focused": 2, "case": False, "case_format": "discriminate",
    "feedback_depth": "standard", "intervals_days": [2, 5, 9, 20, 40, 90], "new_topics_per_round": 0,
    "lab_units": "conventional", "blood_gas_units": "kPa", "guideline_region": "UK",
    "item_order": "case_first", "resource_preferences": {"free_only": True},
    "listening": False,                                 # no "## Listening" in the kits (issue #50)
    "evidence_ladder": False,                           # no "Deeper" notes in the kits
    "usage": "economy",                                 # the author's model and the evidence check (#93)
}
NEUTRAL_PROFILE = {"display_name": "Dr Example", "onboarded_at": "2026-10-01",
                   # display labels and the dates of the paragraphs (#55): never used to write an item
                   "journey_label": "resident", "aim_tags": ["exam"],
                   "journey_set_at": "2026-10-01T08:00:00Z", "aim_set_at": "2026-10-01T08:00:00Z",
                   "utc_offset": -8}               # only dates the rounds (issue #84)
CONTENT_PROFILE = {
    "journey": "Senior registrar in geriatrics, on call alone at night.", "aim": "Pass the specialty exam.",
    "specialty": "Geriatrics", "subspecialty": "Orthogeriatrics",
    "practice_setting": ["ward"], "goals": ["exam"], "strengths": ["cardiology"], "weaknesses": ["renal"],
    "domain_self_ratings": {"CARD": 2}, "domain_emphasis": {"CARD": 2}, "notes": "prefers short stems",
    "podcast_sources": {"trusted": ["Example Show"], "avoid": []},     # whose episodes the kits hold (issue #50)
}


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    """A store holding a ledger and a round prepared for it (1 MCQ + 3 focused + the case)."""
    w = Next(tmp_path_factory.mktemp("prepared")).setup(config=MIX)
    w.check().finish()
    w.publish()
    w.forget_job()
    return w.path


@pytest.fixture
def w(template, tmp_path):
    """A new session on that store: nothing but the store copy in the work folder."""
    path = str(tmp_path / "work")
    shutil.copytree(template, path)
    return Next(path)


def settings(w, *args, today=DAY):
    if not os.path.exists(w.p("work.json")):
        w.open(today=today)
    return w.run_json("--today", today, "settings", "--work", w.path, *args)


def names(out):
    return [f["as"] for f in out["files"]]


def next_session_start(w, *extra):
    """Publish what the job wrote, then start the next round in a new session."""
    w.publish()
    w.forget_job()
    return w.start(NEXT_DAY, *extra)


def stored_prepared(w):
    return w.read_json("store", "data", "prepared.json")


# ---------------------------------------------------------------- the two groups of settings (#41)

def test_every_setting_is_in_one_of_the_two_tested_groups():
    assert set(NEUTRAL_CONFIG) == set(cme.CONTENT_NEUTRAL_CONFIG)
    assert set(NEUTRAL_CONFIG) | set(CONTENT_CONFIG) == set(cme.DEFAULT_CONFIG)
    assert not set(NEUTRAL_CONFIG) & set(CONTENT_CONFIG)
    assert set(NEUTRAL_PROFILE) == set(cme.CONTENT_NEUTRAL_PROFILE)
    assert set(NEUTRAL_PROFILE) | set(CONTENT_PROFILE) == set(cme.DEFAULT_PROFILE)
    for group, defaults in ((NEUTRAL_CONFIG, cme.DEFAULT_CONFIG), (CONTENT_CONFIG, cme.DEFAULT_CONFIG),
                            (NEUTRAL_PROFILE, cme.DEFAULT_PROFILE), (CONTENT_PROFILE, cme.DEFAULT_PROFILE)):
        for k, v in group.items():
            assert v != defaults[k] and v != MIX.get(k), k            # each test really changes the value


@pytest.mark.parametrize("flag,key,value", [("--config", k, v) for k, v in NEUTRAL_CONFIG.items()]
                         + [("--profile", k, v) for k, v in NEUTRAL_PROFILE.items()])
def test_a_setting_that_cannot_change_the_round_keeps_the_prepared_round(w, flag, key, value):
    before, packed = w.read_ledger(), stored_prepared(w)
    out = settings(w, flag, json.dumps({key: value}))
    assert out["prepared"]["kept"] is True and out["prepared"]["why"].startswith("kept")
    assert names(out) == ["data/page.json", "data/state.json"]       # the prepared round is not touched
    st = w.read_json("publish", "data", "state.json")
    assert st["config" if flag == "--config" else "profile"][key] == value
    assert st["gen"] == before["gen"] + 1 and st["content_gen"] == before["gen"] == packed["gen"]
    r = next_session_start(w)
    assert stored_prepared(w) == packed
    assert r["prepared"]["used"] is True and "round_mix" not in r
    assert {k: r["plan"][k] for k in PREPARED_MIX} == PREPARED_MIX


@pytest.mark.parametrize("flag,key,value", [("--config", k, v) for k, v in CONTENT_CONFIG.items()]
                         + [("--profile", k, v) for k, v in CONTENT_PROFILE.items()])
def test_a_setting_that_can_change_the_round_sets_the_prepared_round_aside_and_says_so(w, flag, key, value):
    before = w.read_ledger()
    out = settings(w, flag, json.dumps({key: value}))
    name = key if flag == "--config" else "profile." + key
    # Economy (#93) also turns off what its preset decides and the learner did not set themselves
    changed = {"usage": ["evidence_ladder", "listening", "usage"]}.get(key, [name])
    assert out["prepared"]["kept"] is False and out["prepared"]["changed"] == changed
    assert out["prepared"]["why"].startswith("set aside: %s can change" % ", ".join(changed))
    assert names(out) == ["data/page.json", "data/prepared.json", "data/state.json"]
    assert w.read_json("publish", "data", "prepared.json") == EMPTY
    st = w.read_json("publish", "data", "state.json")
    assert st["gen"] == before["gen"] + 1 and "content_gen" not in st
    r = next_session_start(w)
    assert r["prepared"] == {"used": False, "why": "no prepared round"}


def test_a_changed_blueprint_sets_the_prepared_round_aside_and_the_same_one_keeps_it(w):
    out = settings(w, "--blueprint", BLUEPRINT)
    assert out["prepared"]["kept"] is True and "data/prepared.json" not in names(out)
    with open(BLUEPRINT, encoding="utf-8") as fh:
        bp = json.load(fh)
    domains = bp.get("domains", bp)
    first = next(iter(domains))
    topics = domains[first]["topics"]
    topics.pop(next(iter(topics)))
    out = settings(w, "--blueprint", w.write("blueprint.json", bp))
    assert out["prepared"]["kept"] is False and out["prepared"]["changed"] == ["blueprint"]
    assert w.read_json("publish", "data", "prepared.json") == EMPTY


def test_one_change_of_each_kind_together_sets_it_aside_and_names_only_what_counts(w):
    out = settings(w, "--config", '{"testing": true, "lab_units": "conventional"}',
                   "--profile", '{"display_name": "Dr Example", "specialty": "Geriatrics"}')
    assert out["prepared"]["kept"] is False
    assert out["prepared"]["changed"] == ["lab_units", "profile.specialty"]


def test_setting_a_value_it_already_has_keeps_the_prepared_round(w):
    st = w.read_ledger()
    out = settings(w, "--config", json.dumps({"mcqs": st["config"]["mcqs"], "lab_units": st["config"]["lab_units"]}),
                   "--profile", json.dumps({"specialty": st["profile"]["specialty"]}))
    assert out["prepared"]["kept"] is True
    assert next_session_start(w)["prepared"]["used"] is True


def test_the_plan_of_a_kept_round_carries_the_settings_of_today(w):
    settings(w, "--config", '{"testing": true, "helpers": false, "show_coding": false}')
    r = next_session_start(w)
    plan = w.read_json("plan.json")
    assert r["prepared"]["used"] is True and r["testing"] is True and r["helpers"] is False
    assert (plan["testing"], plan["helpers"], plan["show_coding"]) == (True, False, False)


# ---------------------------------------------------------------- the ledger generation (#41)

def test_several_neutral_changes_in_a_row_still_keep_it_and_a_real_change_ends_that(w):
    gen = w.read_ledger()["gen"]
    settings(w, "--config", '{"testing": true}')
    out = settings(w, "--config", '{"reminders": true}')
    st = w.read_json("publish", "data", "state.json")
    assert (st["gen"], st["content_gen"]) == (gen + 2, gen) and out["prepared"]["kept"] is True
    w.publish()
    w.forget_job()
    settings(w, "--config", '{"testing": false}')                 # another session, another neutral change
    assert w.read_json("publish", "data", "state.json")["content_gen"] == gen
    w.publish()
    w.forget_job()
    out = settings(w, "--config", '{"session_minutes": 30}')
    st = w.read_json("publish", "data", "state.json")
    assert st["gen"] == gen + 4 and "content_gen" not in st and out["prepared"]["kept"] is False
    assert next_session_start(w)["prepared"]["used"] is False


def test_a_real_change_is_not_forgotten_when_the_emptied_prepared_round_never_reached_the_store(w):
    """The generation is the safeguard: if only the ledger was published, the old prepared round
    is still not taken, also after a neutral change on top."""
    packed = stored_prepared(w)
    settings(w, "--config", '{"guideline_region": "UK"}')
    settings(w, "--config", '{"testing": true}')
    w.publish()
    w.write(os.path.join("store", "data", "prepared.json"), packed)
    w.forget_job()
    r = w.start(NEXT_DAY)
    assert r["prepared"] == {"used": False, "why": "the ledger changed since it was prepared"}


def test_postponing_a_review_keeps_the_prepared_round(w):
    w.open(today=DAY)
    out = w.run_json("--today", DAY, "snooze", "--work", w.path)
    assert names(out) == ["data/page.json", "data/state.json"]
    assert next_session_start(w)["prepared"]["used"] is True


def test_a_round_can_be_prepared_and_packed_after_a_neutral_change(tmp_path):
    n = Next(tmp_path)
    n.init(today=DAY)
    n.open(today=DAY)
    n.run("--today", DAY, "settings", "--work", n.path, "--config", '{"testing": true}')
    n.run("--today", DAY, "prepare", "--work", n.path)
    st, plan = n.read_json("publish", "data", "state.json"), n.read_json("next", "plan.json")
    for name, text in examples.sealed_files(st, plan).items():
        n.write(os.path.join("next", name), text)
    n.run("--today", DAY, "settings", "--work", n.path, "--config", '{"reminders": true}')   # while it is written
    _, done = n.check().finish()
    assert done["stashed"] is True and done["gen"] == st["content_gen"] == 1
    assert next_session_start(n)["prepared"]["used"] is True


def test_no_command_counts_a_write_of_the_ledger_on_its_own():
    """Every write goes through bump_gen, so none can leave a stale content_gen behind."""
    with open(cme.__file__, encoding="utf-8") as fh:
        src = fh.read()
    # bump_gen itself, init's first generation, and repeat_write (a step run again counts as the
    # write it repeats, and bump_gen follows it)
    assert src.count('st["gen"] = ') == 3


# ---------------------------------------------------------------- page mix and prepared round (#42)

def page_prefs(base, updated="2026-11-02T21:40:12.512Z"):
    return json.dumps({"round": PAGE_MIX, "base": base, "updated": updated})


def assert_page_mix_planned(w, r, source):
    assert r["prepared"] == {"used": False, "why": "the round mix changed"} and "present" not in r
    assert r["round_mix"]["used"] == {"mcqs": 3, "focused": 1, "case": 1}
    assert r["round_mix"]["prepared"] == PREPARED_MIX and r["round_mix"]["source"] == source
    assert "3 MCQs + 1 focused question + the case" in r["round_mix"]["say"]
    assert "written for 1 MCQ + 3 focused questions + the case and is set aside" in r["round_mix"]["say"]
    assert (r["plan"]["mcqs"], r["plan"]["focused"], r["plan"]["case"]) == (3, 1, 1)
    assert w.read_json("plan.json")["counts"] == {"mcqs": 3, "focused": 1, "case": 1}
    assert not os.path.exists(w.p("sealed_questions.md"))             # nothing of the prepared round is laid out


def test_a_page_mix_applied_at_start_sets_the_prepared_round_aside_and_says_so(w):
    r = w.start(NEXT_DAY, "--prefs", page_prefs(w.read_ledger()["config"]["round_set_at"]))
    assert r["page_settings_applied"] == {"mcqs": 3, "focused": 1}
    assert_page_mix_planned(w, r, "page")
    assert r["round_mix"]["say"].startswith("Using the mix you set on your page: ")


def test_a_page_mix_already_in_the_ledger_still_sets_a_prepared_round_of_another_mix_aside(w):
    """The case of S0037: the page's mix had been applied earlier (same `updated` stamp), so
    `start` applies nothing now; the prepared round is still compared with the mix in force."""
    st = w.read_ledger()
    base, updated = st["config"]["round_set_at"], "2026-11-02T21:40:12.512Z"
    st["config"].update({"mcqs": 3, "focused": 1, "case": True, "round_set_at": updated})
    w.write_ledger(st)
    r = w.start(NEXT_DAY, "--prefs", page_prefs(base, updated))
    assert "page_settings_applied" not in r
    assert_page_mix_planned(w, r, "settings")
    assert r["round_mix"]["say"].startswith("Using the mix in your settings: ")
    w.forget_job()                                                    # and the same with no prefs read at all
    assert_page_mix_planned(w, w.start(NEXT_DAY), "settings")


def test_a_page_mix_set_after_a_change_in_a_chat_wins_though_the_page_had_not_seen_that_change(w):
    """The page was open on an older ledger (`base` is stale), the learner set the mix there
    later than the mix was last set in a chat: the latest choice wins."""
    r = w.start(NEXT_DAY, "--prefs", page_prefs("2020-01-01T00:00:00Z", updated="2099-01-01T00:00:00.000Z"))
    assert r["page_settings_applied"] == {"mcqs": 3, "focused": 1}
    assert_page_mix_planned(w, r, "page")


def test_an_older_page_mix_is_ignored_and_the_prepared_round_is_used(w):
    r = w.start(NEXT_DAY, "--prefs", page_prefs("2020-01-01T00:00:00Z", updated="2020-01-02T00:00:00.000Z"))
    assert "page_settings_applied" not in r and "round_mix" not in r
    assert r["prepared"]["used"] is True and (r["plan"]["mcqs"], r["plan"]["focused"]) == (1, 3)
    w.forget_job()                                                    # a stamp that is no time: never applied
    r = w.start(NEXT_DAY, "--prefs", page_prefs("2020-01-01T00:00:00Z", updated="yesterday"))
    assert "page_settings_applied" not in r and r["prepared"]["used"] is True


def test_a_page_mix_equal_to_the_prepared_mix_uses_the_prepared_round(w):
    prefs = json.dumps({"round": {"mcqs": 1, "focused": 3, "case": True},
                        "base": w.read_ledger()["config"]["round_set_at"], "updated": "2026-11-02T21:40:12.512Z"})
    r = w.start(NEXT_DAY, "--prefs", prefs)
    assert r["page_settings_applied"] == {"unchanged": True}
    assert r["prepared"]["used"] is True and "round_mix" not in r


def test_one_off_options_are_the_reason_given_before_the_mix(w):
    r = w.start(NEXT_DAY, "--mcqs", "2")
    assert r["prepared"] == {"used": False, "why": "one-off options were given for this round"}
    assert "round_mix" not in r


def test_prepare_writes_the_round_for_a_page_mix_that_is_waiting(w):
    """A prepare-only session that read the page's mix prepares for it, so the next start,
    which applies that mix, takes the round."""
    prefs = page_prefs(w.read_ledger()["config"]["round_set_at"])
    w.open("--prefs", prefs, today=DAY)
    assert w.run_json("--today", DAY, "prepare", "--work", w.path, "--if-needed")["prepare"] is True
    plan = w.read_json("next", "plan.json")
    assert plan["counts"] == {"mcqs": 3, "focused": 1, "case": 1}
    for name, text in examples.sealed_files(w.read_ledger(), plan).items():
        w.write(os.path.join("next", name), text)
    w.check().finish()
    assert w.read_ledger()["config"]["mcqs"] == 1                     # the ledger itself is not changed by prepare
    r = next_session_start(w, "--prefs", prefs)
    assert r["page_settings_applied"] == {"mcqs": 3, "focused": 1}
    assert r["prepared"]["used"] is True and "round_mix" not in r and r["plan"]["mcqs"] == 3


def test_a_utc_offset_passed_to_start_is_recorded_and_the_prepared_round_stands(w):
    """Issue #84: the offset the assistant passes is kept for unattended jobs, as a content-free
    change."""
    before, packed = w.read_ledger(), stored_prepared(w)
    r = w.start(NEXT_DAY, "--utc-offset", "-8")
    assert r["utc_offset_recorded"] == -8
    assert r["prepared"]["used"] is True and "round_mix" not in r
    st = w.read_json("publish", "data", "state.json")
    assert st["profile"]["utc_offset"] == -8
    assert st["gen"] == before["gen"] + 1 and st["content_gen"] == before["gen"] == packed["gen"]
    assert not os.path.exists(w.pub("data", "prepared.json"))       # not set aside
    w.publish()
    w.forget_job()
    t0 = cme.learner_today({"utc_offset": -8}).isoformat()
    out = w.open()                                                  # an unattended job: no flags
    assert w.read_json("work.json")["started"] in (t0, cme.learner_today({"utc_offset": -8}).isoformat())
    assert "utc_offset_recorded" not in out
    assert stored_prepared(w) == packed

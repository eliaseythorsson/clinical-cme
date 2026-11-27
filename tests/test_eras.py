"""The load step (issue #83): one ledger per era an older engine wrote goes in, a current ledger
comes out. The era ledgers in tests/ledgers/eras/ are synthetic and frozen (tests/ledgers/build.py
--era made them from the `new_state` of the engine of each era); the current ledger each becomes
is saved in eras/expected/. To accept a deliberate change to the load step:

    CME_UPDATE_EXPECTED=1 python3 -m pytest -q tests/test_eras.py

and review the diff of tests/ledgers/eras/expected/ like any other change."""
import copy
import json
import os

import pytest

from conftest import Work
from examples import cme

ERAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledgers", "eras")
ERAS = ("4_1_mix_not_a_setting", "4_2", "4_3", "5_0", "6_0", "newer")
UPDATE = os.environ.get("CME_UPDATE_EXPECTED") == "1"
TODAY = "2026-01-27"


def raw(era):
    with open(os.path.join(ERAS_DIR, era + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def expected_path(era):
    return os.path.join(ERAS_DIR, "expected", era + ".json")


eras = pytest.mark.parametrize("era", ERAS)


@eras
def test_old_ledger_in_current_ledger_out(era):
    st = cme.make_current(raw(era))
    if UPDATE:
        os.makedirs(os.path.dirname(expected_path(era)), exist_ok=True)
        with open(expected_path(era), "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
    with open(expected_path(era), encoding="utf-8") as fh:
        assert st == json.load(fh), "%s: see tests/test_eras.py for how to accept a deliberate change" % era
    # the declared shape, all of it, and nothing that does not fit it
    assert [k for k, _, _ in cme.LEDGER_SHAPE if k not in st] == []
    assert set(cme.DEFAULT_CONFIG) <= set(st["config"]) and set(cme.DEFAULT_PROFILE) <= set(st["profile"])
    assert set(cme.empty_agg()) <= set(st["agg"])
    assert cme.shape_problems(st) == []
    # reading is not a write; the step is a no-op on what it gives
    assert st["gen"] == raw(era)["gen"]
    assert cme.make_current(copy.deepcopy(st)) == st
    assert cme.upgrades_needed(st) == []


@eras
def test_every_era_is_read_by_the_commands(era, tmp_path):
    w = Work(tmp_path)
    w.write_ledger(raw(era))
    status = w.open(today=TODAY)
    assert status["ok"] is True and status["round"]["minutes"]
    assert w.run_json("validate", "--work", w.path)["problems"] == []
    r = w.run("--today", TODAY, "start", "--work", w.path, ok=False)
    if era == "newer":
        assert r.returncode != 0 and "update the plugin" in json.loads(r.stdout)["error"]
        assert status["newer_version"]["ledger"] == "99.0.0"
        return
    out = json.loads(r.stdout)
    assert out["plan"]["case"] in (0, 1) and out["plan"]["estimated_minutes"] > 0
    assert out["speed_settings_new"] is (era in ("4_1_mix_not_a_setting", "4_2"))
    # the first write stores the current ledger, stamped
    w.run("--today", TODAY, "settings", "--work", w.path, "--config", '{"reminders": false}')
    written = w.read_json("publish", "data", "state.json")
    assert written["skill_version"] == cme.SKILL_VERSION and cme.upgrades_needed(written) == []
    assert cme.shape_problems(written) == []


def test_a_ledger_from_before_the_mix_was_a_setting_keeps_the_mix_and_length_of_its_time():
    st = cme.make_current(raw("4_1_mix_not_a_setting"))
    assert {k: st["config"][k] for k in cme.LEGACY_CONFIG} == {"mcqs": 3, "focused": 0, "case": True,
                                                              "session_minutes": 20}
    assert cme.upgrades_needed(raw("4_1_mix_not_a_setting"))[0] == "settings_of_4_2"
    # a ledger that has a mix keeps its own: the legacy values fill only what is missing
    assert cme.make_current(raw("4_2"))["config"]["session_minutes"] == 20      # its own (the 4.2 default)
    assert cme.make_current(raw("5_0"))["config"]["session_minutes"] == 35


def test_a_4_2_ledger_gets_its_paragraphs_one_area_code_and_the_settings_of_later_versions():
    old = raw("4_2")
    st = cme.make_current(copy.deepcopy(old))
    assert cme.upgrades_needed(old) == ["paragraphs", "one_code_per_area"]
    prof = st["profile"]
    assert prof["journey"] == "Consultant physician\n\nExample: night shifts" and prof["journey_label"] == "attending"
    assert prof["aim"] == "Example: pass the exam" and prof["role"] == "Consultant physician"    # kept as it was
    assert prof["specialty"] == cme.DEFAULT_PROFILE["specialty"]                                   # null: the default
    assert "EMRG" not in st["blueprint"] and "EMRG-01" in st["blueprint"]["TOX"]["topics"]
    assert prof["domain_self_ratings"] == {"CARD": 3, "TOX": 2}       # the lower of the two
    assert st["topics"]["EMRG-01"]["domain"] == "TOX" and st["sessions"][0]["items"][0]["domain"] == "TOX"
    assert st["config"]["guideline_region"] == "Europe"               # its own value, not today's default
    assert all(st["config"][k] is True for k in ("helpers", "prepare_ahead", "listening", "evidence_ladder"))
    assert st["config"]["mirror"] is None                             # a setting no longer known stays as it was
    assert st["block"] is None and st["blocks"] == [] and st["positions"] == []
    assert st["gaps"] == old["gaps"]                                  # history is read as it was written
    assert st["review"]["period_start"] == old["review"]["period_start"]


def test_a_6_0_ledger_is_left_as_it_is_but_for_what_came_after_it():
    old = raw("6_0")
    old["profile"]["utc_offset"] = None             # the learner's UTC offset (issue #84): unset, UTC
    assert cme.make_current(raw("6_0")) == dict(old, positions=[], mappings=[])


def test_a_newer_ledger_is_filled_for_reading_and_nothing_else():
    old = raw("newer")
    st = cme.make_current(copy.deepcopy(old))
    assert st["skill_version"] == "99.0.0" and cme.newer_engine(st) == "99.0.0"
    assert st["config"]["a_setting_from_the_future"] is True
    assert st["profile"].pop("utc_offset") is None            # filled for reading (issue #84)
    assert {k: v for k, v in st.items() if k not in ("positions", "mappings")} == old


def test_a_null_setting_reads_as_the_engine_has_always_read_it():
    st = cme.make_current(raw("6_0"))
    for k in cme.DEFAULT_CONFIG:
        st["config"][k] = None
    st["profile"]["specialty"] = "  "
    st["config"]["review_interval_days"] = 0
    cme.make_current(st)
    cfg = st["config"]
    assert (cfg["mcqs"], cfg["focused"], cfg["case"], cfg["new_topics_per_round"]) == (0, 0, False, 0)
    assert cfg["listening"] is True and cfg["helpers"] is False and cfg["evidence_ladder"] is False
    assert cfg["session_minutes"] == 20 and cfg["review_interval_days"] == 42 and cfg["round_set_at"] is None
    assert cfg["guideline_region"] == cme.DEFAULT_CONFIG["guideline_region"]
    assert st["profile"]["specialty"] == cme.DEFAULT_PROFILE["specialty"]


def test_validate_reports_what_does_not_fit_the_declared_shape(tmp_path, capsys):
    st = raw("6_0")
    st["config"]["mcqs"] = "three"
    st["config"]["helpers"] = 1
    st["profile"]["aim_tags"] = "exam"
    st["blocks"] = {}
    st["unreflected"] = "S0042"
    path = str(tmp_path / "state.json")
    cme.save_json(st, path)
    assert cme.main(["validate", path]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["upgrades"] == []
    for part in ("config.mcqs is str", "config.helpers is int, not bool", "profile.aim_tags is str",
                 "blocks is dict, not list", "unreflected names session S0042"):
        assert any(p.startswith(part) for p in out["problems"]), part


def test_new_state_is_the_declared_shape():
    st = cme.new_state(cme.parse_date("2026-01-05"))
    assert [k for k, _, _ in cme.LEDGER_SHAPE] == list(st)
    assert cme.shape_problems(st) == [] and st["review"]["period_start"] == "2026-01-05"
    assert cme.make_current(copy.deepcopy(st)) == st


def test_settings_read_a_null_length_as_the_load_step_does_and_refuse_zero(work):
    work.init()
    work.open(today="2026-11-02")
    out = work.run_json("--today", "2026-11-02", "settings", "--work", work.path,
                        "--config", '{"session_minutes": null}')
    assert out["config"]["session_minutes"] == 20
    assert work.read_json("publish", "data", "state.json")["config"]["session_minutes"] == 20
    for bad in ("0", "-5", '""', "true"):
        r = work.run("--today", "2026-11-02", "settings", "--work", work.path,
                     "--config", '{"session_minutes": %s}' % bad, ok=False)
        assert r.returncode != 0 and "session_minutes must be a positive number" in json.loads(r.stdout)["error"]
    assert work.read_json("publish", "data", "state.json")["config"]["session_minutes"] == 20


@pytest.mark.parametrize("key", ["listening", "evidence_ladder"])
def test_settings_refuse_a_null_on_off_setting(work, key):
    work.init()
    work.open(today="2026-11-02")
    r = work.run("--today", "2026-11-02", "settings", "--work", work.path, "--config", '{"%s": null}' % key, ok=False)
    assert r.returncode != 0 and "must be true or false" in json.loads(r.stdout)["error"]

"""Region and specialty: defaults at setup, a one-line change later, and what the author and examiner see."""
import json

import pytest

from conftest import BLUEPRINT
from examples import cme


def start(work, today="2026-11-02", publish=False):
    if publish:
        work.publish()
    out = work.start(today)
    return out, work.read_json("plan.json")


def test_setup_defaults_to_international_and_internal_medicine(work):
    work.init()
    st = work.read_ledger()
    assert st["config"]["guideline_region"] == "International"
    assert st["profile"]["specialty"] == "Internal/hospital medicine"
    status, plan = start(work)
    for seen in (status, plan):                      # examiner (start output) and author (plan file)
        assert seen["guideline_region"] == "International"
        assert seen["specialty"] == "Internal/hospital medicine"
    assert plan["profile"]["specialty"] == "Internal/hospital medicine"


def test_setup_answers_replace_the_defaults(work):
    work.init(config={"guideline_region": "UK"}, profile={"specialty": "Cardiology"})
    status, plan = start(work)
    assert (status["guideline_region"], status["specialty"]) == ("UK", "Cardiology")
    assert (plan["guideline_region"], plan["specialty"]) == ("UK", "Cardiology")


def test_one_settings_call_changes_either_later(work):
    work.init()
    work.open()
    out = work.run_json("settings", "--work", work.path, "--config", '{"guideline_region": "North America"}')
    assert out["guideline_region"] == "North America"
    assert out["specialty"] == "Internal/hospital medicine"      # untouched
    out = work.run_json("settings", "--work", work.path, "--profile", '{"specialty": "Geriatrics"}')
    assert (out["guideline_region"], out["specialty"]) == ("North America", "Geriatrics")
    status, plan = start(work, publish=True)
    assert (status["guideline_region"], status["specialty"]) == ("North America", "Geriatrics")
    assert (plan["guideline_region"], plan["profile"]["specialty"]) == ("North America", "Geriatrics")


@pytest.mark.parametrize("skipped", ["", "  ", None])
def test_a_skipped_region_at_setup_is_international(work, skipped):
    work.init(config={"guideline_region": skipped})
    assert work.read_ledger()["config"]["guideline_region"] == "International"
    status, plan = start(work)
    assert status["guideline_region"] == plan["guideline_region"] == "International"


@pytest.mark.parametrize("how", ["missing", "null", "blank"])
def test_a_ledger_of_the_old_default_keeps_iceland_europe_written_into_it(work, how):
    # until issue #56 a ledger without a region read as Iceland/Europe: it keeps that, explicitly
    work.init()
    st = work.read_ledger()
    if how == "missing":
        st["config"].pop("guideline_region")
    else:
        st["config"]["guideline_region"] = None if how == "null" else " "
    st["profile"]["specialty"] = "  "
    st["skill_version"] = cme.REGION_OLD_DEFAULT_UNTIL
    work.write_ledger(st)
    assert cme.upgrades_needed(st) == ["old_default_region"]
    status, plan = start(work)
    assert (status["guideline_region"], status["specialty"]) == ("Iceland/Europe", "Internal/hospital medicine")
    assert (plan["guideline_region"], plan["specialty"]) == ("Iceland/Europe", "Internal/hospital medicine")
    # the next write stores it; the learner can still move to the new default by asking
    work.publish()
    work.open()
    out = work.run_json("settings", "--work", work.path, "--config", '{"reminders": false}')
    assert out["guideline_region"] == "Iceland/Europe"
    assert work.read_json("publish", "data", "state.json")["config"]["guideline_region"] == "Iceland/Europe"
    out = work.run_json("settings", "--work", work.path, "--config", '{"guideline_region": "International"}')
    assert out["guideline_region"] == "International"


def test_the_old_default_goes_only_to_a_ledger_of_its_era(monkeypatch):
    def ledger(stamp, region):
        st = cme.new_state(cme.parse_date("2026-01-05"))
        st["config"]["guideline_region"] = region
        if stamp is None:
            st.pop("skill_version")
        else:
            st["skill_version"] = stamp
        return st
    up = cme.upgrade_old_default_region
    assert up(ledger(None, None))["config"]["guideline_region"] == "Iceland/Europe"        # before the stamp
    assert up(ledger("5.9.1", ""))["config"]["guideline_region"] == "Iceland/Europe"
    assert up(ledger("6.0.0", None))["config"]["guideline_region"] == "Iceland/Europe"
    assert up(ledger("6.0.1", None))["config"]["guideline_region"] is None                 # a later engine's
    assert up(ledger("5.0.0", "UK"))["config"]["guideline_region"] == "UK"                 # its own, kept
    assert up(ledger(None, "Iceland/Europe"))["config"]["guideline_region"] == "Iceland/Europe"
    # a ledger stamped after the change reads a missing region as today's default
    monkeypatch.setattr(cme, "REGION_OLD_DEFAULT_UNTIL", "5.0.0")
    st = ledger("6.0.0", None)
    assert cme.make_current(st)["config"]["guideline_region"] == "International"


def test_no_iceland_default_in_the_shipped_plugin():
    # issue #56: Iceland/Europe is named only where the old default is kept for older ledgers (the
    # engine's upgrade step and the schema that documents it) and as a region the tag-check seed is for
    import glob
    import os
    from conftest import ROOT
    plugin = os.path.join(ROOT, "plugins", "clinical-cme")
    naming = set()
    for path in glob.glob(os.path.join(plugin, "**", "*"), recursive=True):
        if os.path.isfile(path) and path.endswith((".md", ".py", ".json", ".html")):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            assert "Icelandic" not in text, path
            if "Iceland" in text:
                naming.add(os.path.basename(path))
    assert naming <= {"cme.py", "state_schema.md", "guideline_checks.json", "README.md"}
    assert cme.DEFAULT_CONFIG["guideline_region"] == "International"

"""Region and specialty: defaults at setup, a one-line change later, and what the author and examiner see."""
import json

from conftest import BLUEPRINT


def start(work, today="2026-11-02", publish=False):
    if publish:
        work.publish()
    out = work.start(today)
    return out, work.read_json("plan.json")


def test_setup_defaults_to_iceland_europe_and_internal_medicine(work):
    work.init()
    st = work.read_ledger()
    assert st["config"]["guideline_region"] == "Iceland/Europe"
    assert st["profile"]["specialty"] == "Internal/hospital medicine"
    status, plan = start(work)
    for seen in (status, plan):                      # examiner (start output) and author (plan file)
        assert seen["guideline_region"] == "Iceland/Europe"
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


def test_ledger_without_region_or_specialty_falls_back_to_defaults(work):
    work.init()
    st = work.read_ledger()
    st["config"].pop("guideline_region")             # an older ledger, or a blanked value
    st["profile"]["specialty"] = "  "
    work.write_ledger(st)
    status, plan = start(work)
    assert (status["guideline_region"], status["specialty"]) == ("Iceland/Europe", "Internal/hospital medicine")
    assert (plan["guideline_region"], plan["specialty"]) == ("Iceland/Europe", "Internal/hospital medicine")


def test_existing_ledger_keeps_its_stored_region(work):
    work.init(config={"guideline_region": "Europe"})
    status, _ = start(work)
    assert status["guideline_region"] == "Europe"

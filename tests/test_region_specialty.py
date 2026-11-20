"""Region and specialty: defaults at setup, a one-line change later, and what the author and examiner see."""
import json

from conftest import BLUEPRINT


def start(work, state, today="2026-11-02"):
    out = work.run_json("--today", today, "start", state, "--out", work.p("plan.json"))
    return out, work.read_json("plan.json")


def test_setup_defaults_to_iceland_europe_and_internal_medicine(work):
    state = work.init()
    st = work.read_json("state.json")
    assert st["config"]["guideline_region"] == "Iceland/Europe"
    assert st["profile"]["specialty"] == "Internal/hospital medicine"
    status, plan = start(work, state)
    for seen in (status, plan):                      # examiner (start output) and author (plan file)
        assert seen["guideline_region"] == "Iceland/Europe"
        assert seen["specialty"] == "Internal/hospital medicine"
    assert plan["profile"]["specialty"] == "Internal/hospital medicine"


def test_setup_answers_replace_the_defaults(work):
    work.run("--today", "2026-11-01", "init", "--blueprint", BLUEPRINT,
             "--config", json.dumps({"guideline_region": "UK"}),
             "--profile", json.dumps({"specialty": "Cardiology"}), "--out", work.p("state.json"))
    status, plan = start(work, work.p("state.json"))
    assert (status["guideline_region"], status["specialty"]) == ("UK", "Cardiology")
    assert (plan["guideline_region"], plan["specialty"]) == ("UK", "Cardiology")


def test_one_settings_call_changes_either_later(work):
    state = work.init()
    out = work.run_json("settings", state, "--config", '{"guideline_region": "North America"}',
                        "--out", work.p("s1.json"))
    assert out["guideline_region"] == "North America"
    assert out["specialty"] == "Internal/hospital medicine"      # untouched
    out = work.run_json("settings", work.p("s1.json"), "--profile", '{"specialty": "Geriatrics"}',
                        "--out", work.p("s2.json"))
    assert (out["guideline_region"], out["specialty"]) == ("North America", "Geriatrics")
    status, plan = start(work, work.p("s2.json"))
    assert (status["guideline_region"], status["specialty"]) == ("North America", "Geriatrics")
    assert (plan["guideline_region"], plan["profile"]["specialty"]) == ("North America", "Geriatrics")


def test_ledger_without_region_or_specialty_falls_back_to_defaults(work):
    state = work.init()
    st = work.read_json("state.json")
    st["config"].pop("guideline_region")             # an older ledger, or a blanked value
    st["profile"]["specialty"] = "  "
    work.write("state.json", st)
    status, plan = start(work, state)
    assert (status["guideline_region"], status["specialty"]) == ("Iceland/Europe", "Internal/hospital medicine")
    assert (plan["guideline_region"], plan["specialty"]) == ("Iceland/Europe", "Internal/hospital medicine")


def test_existing_ledger_keeps_its_stored_region(work):
    state = work.init(config={"guideline_region": "Europe"})
    status, _ = start(work, state)
    assert status["guideline_region"] == "Europe"

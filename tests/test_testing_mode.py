"""Testing mode: the setting, the store check and the feedback note."""
import json
import os
import shutil


def reread(work, only=None):
    """A fresh read of a folder store after the publish set was written to it; `only` limits
    what was written (a publish that failed part-way)."""
    check = work.p("check")
    for f in work.read_json("publish.json")["files"]:
        if only is not None and f["as"] not in only:
            continue
        dst = os.path.join(check, *f["as"].split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(f["path"], dst)
    return check


def test_testing_is_off_by_default_and_can_be_switched_on(work):
    work.init()
    assert work.read_ledger()["config"]["testing"] is False
    assert work.open()["testing"] is False
    work.run("settings", "--work", work.path, "--config", '{"testing": true}')
    out = work.run_json("--today", "2026-11-02", "start", "--work", work.path)
    assert out["testing"] is True


def test_verify_passes_on_a_correct_save(work):
    work.init()
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    res = work.run_json("verify", "--work", work.path, "--store", reread(work))
    assert res["ok"] and res["checked"] == 4 and work.read_json("verify.json") == res


def test_verify_catches_stale_ledger_and_missing_session(work):
    work.init()
    work.save_round("2026-11-01")
    check = reread(work, only=("data/state.json", "data/page.json"))     # as the save left the store
    work.close_round("2026-11-01")                                        # the close was never written
    res = work.run_json("verify", "--work", work.path, "--store", check)
    assert not res["ok"]
    assert "data/state.json" in res["mismatched"]
    assert "data/sessions/S0001.json" in res["missing"]


def test_verify_accepts_flat_store_reads(work):
    """The store's files read side by side, without the data/ folder."""
    work.init()
    work.save_round("2026-11-01")
    flat = work.p("flat")
    os.makedirs(flat)
    for f in work.read_json("publish.json")["files"]:
        shutil.copy(f["path"], os.path.join(flat, os.path.basename(f["as"])))
    res = work.run_json("verify", "--work", work.path, "--store", flat)
    assert res["ok"], res


def test_verify_needs_something_written(work):
    work.init()
    work.open()
    r = work.run("verify", "--work", work.path, "--store", work.store(), ok=False)
    assert "publish set" in json.loads(r.stdout)["error"]


def test_testing_note_takes_the_session_and_the_store_check_from_the_work_folder(work):
    work.init()
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    work.run("verify", "--work", work.path, "--store", reread(work))
    fb = {"waiting": "noticeable", "waiting_step": "case feedback", "items": 4, "feedback": 5, "note": "good"}
    out = work.run_json("--today", "2026-11-03", "testing-note", "--work", work.path, "--feedback", json.dumps(fb))
    assert out["session"] == "S0001"
    assert [f["as"] for f in out["files"]][:2] == ["data/sessions/S0001.json", "data/testing/S0001.json"]
    assert out["files"][-1]["as"] == "data/state.json"
    note = work.read_json("publish", "data", "testing", "S0001.json")
    assert note["feedback"] == fb and note["store_check"]["ok"] and note["skill_version"] == "4.3.1"

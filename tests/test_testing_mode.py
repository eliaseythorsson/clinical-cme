"""Testing mode: the setting, the store check and the feedback note."""
import json
import os
import shutil


def store_copy(work, *out_dirs):
    """Simulate a folder store after a correct save: every written file at its store path."""
    store = work.p("check")
    for d in out_dirs:
        for root, _, names in os.walk(work.p(d)):
            for n in names:
                if n.startswith(".") or n in ("A.md", "B.json"):
                    continue
                src = os.path.join(root, n)
                dst = os.path.join(store, os.path.relpath(src, work.p(d)))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(src, dst)
    return store


def test_testing_is_off_by_default_and_can_be_switched_on(work):
    state = work.init()
    st = work.read_json("state.json")
    assert st["config"]["testing"] is False
    work.run("settings", state, "--config", '{"testing": true}', "--out", work.p("s.json"))
    out = work.run_json("--today", "2026-11-02", "start", work.p("s.json"), "--out", work.p("plan.json"))
    assert out["testing"] is True


def test_verify_passes_on_a_correct_save(work):
    work.init()
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    store = store_copy(work, "out1", "out2")
    res = work.run_json("verify", "--written", work.p("out1"), work.p("out2"), "--store", store)
    assert res["ok"] and res["checked"] >= 3


def test_verify_catches_stale_ledger_and_missing_session(work):
    work.init()
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    store = store_copy(work, "out1")            # the close was never written
    os.remove(os.path.join(store, "data", "sessions", "S0001.json"))
    res = work.run_json("verify", "--written", work.p("out1"), work.p("out2"), "--store", store)
    assert not res["ok"]
    assert "data/state.json" in res["mismatched"]
    assert "data/sessions/S0001.json" in res["missing"]


def test_verify_accepts_flat_store_reads(work):
    """Store A is read into <work>/store/state.json etc., without the data/ folder."""
    work.init()
    work.save_round("2026-11-01")
    flat = work.p("flat")
    os.makedirs(flat)
    for name in ("state.json", "index.json", "prepared.json"):
        shutil.copy(work.p("out1", "data", name), os.path.join(flat, name))
    shutil.copy(work.p("out1", "data", "sessions", "S0001.json"), os.path.join(flat, "S0001.json"))
    res = work.run_json("verify", "--written", work.p("out1"), "--store", flat)
    assert res["ok"], res


def test_testing_note(work):
    work.write("v.json", {"ok": True, "checked": 4, "missing": [], "mismatched": []})
    fb = {"waiting": "noticeable", "waiting_step": "case feedback", "items": 4, "feedback": 5, "note": "good"}
    out = work.run_json("--today", "2026-11-03", "testing-note", "--session", "S0001",
                        "--feedback", json.dumps(fb), "--verify", work.p("v.json"), "--out-dir", work.p("t"))
    assert out["files"][0]["as"] == "data/testing/S0001.json"
    note = work.read_json("t", "data", "testing", "S0001.json")
    assert note["feedback"] == fb and note["store_check"]["ok"] and note["skill_version"] == "4.3.1"

"""Commands share plain functions: nothing captures printed output, and errors raise (issue #5)."""
import argparse
import copy
import datetime as dt
import importlib.util
import json
import os

import pytest

from conftest import BLUEPRINT, CME, ROUND, REFLECTION

spec = importlib.util.spec_from_file_location("cme", CME)
cme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cme)

TODAY = dt.date(2026, 11, 1)
PLAN_OPTIONS = dict(focused=None, mcqs=None, no_case=False, domain=None, no_new=False,
                    allow_repeat=False, no_drill=False, force_drill=False, seed=None)


def ledger(work):
    return cme.load_json(work.init())


def stdout_lines(result):
    return [line for line in result.stdout.splitlines() if line.strip()]


# ---- errors raise in the core; the command line turns them into the message and exit code

def test_core_errors_raise_instead_of_exiting(work):
    with pytest.raises(cme.CmeError) as e:
        cme.load_json(work.p("missing.json"))
    assert e.value.code == 2 and "file not found" in e.value.msg
    with pytest.raises(cme.CmeError):
        cme.check_schema({"schema": 3})
    with pytest.raises(cme.CmeError):
        cme.plan_round(ledger(work), argparse.Namespace(**dict(PLAN_OPTIONS, mcqs=99)), TODAY)


def test_main_returns_the_exit_code_and_prints_the_error(work, capsys):
    assert cme.main(["validate", work.p("missing.json")]) == 2
    assert json.loads(capsys.readouterr().out) == {"ok": False, "error": "file not found: %s" % work.p("missing.json")}
    assert cme.main(["validate", work.init()]) == 0


def test_command_line_error_is_one_json_line_with_exit_code_2(work):
    work.init()
    work.open()
    w = ("--work", work.path)
    work.write("round.json", {"items": []})
    work.write("feedback.md", "x")
    work.write("B.md", "x")
    for args, message in (
        (("validate", "missing.json"), "file not found: missing.json"),
        (("--today", "garbage", "start", *w), "--today must be YYYY-MM-DD"),
        (("--today", "2026-11-01", "start", *w, "--mcqs", "99"), "--mcqs must be between 0 and 10"),
        (("--today", "2026-11-01", "save", *w), "round JSON must contain a non-empty 'items' list"),
        (("--today", "2026-11-01", "close", *w, "--reflection", "{}"), "no unreflected session to update (last: None)"),
    ):
        r = work.run(*args, ok=False)
        assert r.returncode == 2, args
        assert r.stderr == ""
        assert [json.loads(line) for line in stdout_lines(r)] == [{"ok": False, "error": message}]


def test_validate_exits_1_on_problems_and_still_prints_them(work):
    state = work.init()
    assert work.run("validate", state).returncode == 0
    st = work.read_ledger()
    st["gaps"].append({"topic": "ZZ-99", "gap": "x"})
    r = work.run("validate", work.write("broken.json", st), ok=False)
    assert r.returncode == 1
    assert json.loads(r.stdout)["problems"] == ["gap for unknown topic ZZ-99"]


# ---- the shared functions print nothing and work on the ledger they are given

def test_plan_round_is_silent_and_leaves_the_ledger_alone(work, capsys):
    st = ledger(work)
    before = copy.deepcopy(st)
    capsys.readouterr()
    plan = cme.plan_round(st, argparse.Namespace(**PLAN_OPTIONS), TODAY)
    assert capsys.readouterr().out == ""
    assert st == before
    assert plan["session_id"] == "S0001" and plan["counts"]["case"] == 1
    assert cme.plan_summary(plan, "p.json")["items"] == len(plan["items"])
    assert "topic" not in json.dumps(cme.plan_summary(plan, "p.json"))


def test_record_and_reflect_are_silent_and_change_the_ledger_in_place(work, capsys):
    st = ledger(work)
    capsys.readouterr()
    rec = cme.record_round(st, copy.deepcopy(ROUND), TODAY)
    assert rec["session_id"] == "S0001" and rec["reflection_pending"] is True
    assert st["unreflected"] == "S0001" and st["gen"] == 2
    ref = cme.reflect_round(st, dict(REFLECTION), dt.date(2026, 11, 3))
    assert ref["session_id"] == "S0001" and st["unreflected"] is None and st["gen"] == 3
    assert st["sessions"][-1]["date"] == "2026-11-01"
    with pytest.raises(cme.CmeError):
        cme.reflect_round(st, {}, TODAY)
    assert capsys.readouterr().out == ""


# ---- the commands built on them behave as before

def test_start_prints_one_line_and_writes_the_plan_plan_round_makes(work):
    state = work.init()
    r = work.run("--today", "2026-11-01", "start", "--work", work.path, "--store", work.store())
    assert len(stdout_lines(r)) == 1
    out = json.loads(r.stdout)
    plan = cme.plan_round(cme.load_json(state), argparse.Namespace(**PLAN_OPTIONS), TODAY)
    assert work.read_json("plan.json") == json.loads(json.dumps(plan))
    assert out["plan"] == cme.plan_summary(plan, work.p("plan.json"))


def test_save_and_close_match_record_and_reflect(work):
    st = ledger(work)
    saved = work.save_round("2026-11-01")
    rec = cme.record_round(st, copy.deepcopy(ROUND), TODAY)
    assert work.read_json("publish", "data", "state.json") == json.loads(json.dumps(st))
    assert saved["out"] == work.pub("data", "state.json") and saved["bytes"] == os.path.getsize(saved["out"])
    assert list(saved)[:3] == ["ok", "out", "bytes"]
    for k in ("gen", "session_id", "next_id", "score", "topics", "open_gaps", "reflection_pending"):
        assert saved[k] == rec[k]

    closed = work.close_round("2026-11-03")
    ref = cme.reflect_round(st, dict(REFLECTION), dt.date(2026, 11, 3))
    assert work.read_json("publish", "data", "state.json") == json.loads(json.dumps(st))
    assert closed["bytes"] == os.path.getsize(closed["out"])
    for k in ("gen", "session_id", "topics", "open_gaps"):
        assert closed[k] == ref[k]


def test_failed_save_and_close_leave_no_files(work):
    work.init()
    prefs = json.dumps({"round": {"mcqs": 4}, "base": work.read_ledger()["config"]["round_set_at"],
                        "updated": "2026-11-01T10:00"})
    work.open("--prefs", prefs)
    work.write("round.json", {"items": []})
    work.write("feedback.md", "x")
    work.write("B.md", "x")
    work.run("--today", "2026-11-01", "save", "--work", work.path, ok=False)
    work.run("--today", "2026-11-01", "close", "--work", work.path, "--reflection", "{}", ok=False)
    assert not os.path.exists(work.pub())
    assert work.read_json("publish.json")["files"] == []
    assert not os.path.exists(work.p("before_save.json")) and not os.path.exists(work.p("before_close.json"))


def test_prepare_plans_tomorrow_and_marks_the_plan(work):
    work.init()
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    r = work.run("--today", "2026-11-01", "prepare", "--work", work.path)
    assert len(stdout_lines(r)) == 1
    summary = json.loads(r.stdout)
    plan = work.read_json("next", "plan.json")
    assert summary["prepare"] is True and summary["session_id"] == "S0002"
    assert plan["date"] == "2026-11-02"
    assert plan["prepared"] == {"gen": summary["gen"], "made": "2026-11-01", "session_id": "S0002"}

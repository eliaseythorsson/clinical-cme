"""The engine version stamped on the ledger; a ledger stamped by a newer engine is not written
(issue #83, step 1)."""
import json
import os
import re
import shutil

import pytest

from conftest import ANSWERS, CME, ROUND, SEALED_CASE, SEALED_QUESTIONS

with open(CME, encoding="utf-8") as fh:
    SKILL_VERSION = re.search(r'^SKILL_VERSION = "([^"]+)"', fh.read(), re.M).group(1)

NEWER = "99.0.0"


def stamp(work, version):
    st = work.read_ledger()
    if version is None:
        st.pop("skill_version", None)
    else:
        st["skill_version"] = version
    work.write_ledger(st)


def error(r):
    assert r.returncode != 0
    return json.loads(r.stdout)["error"]


def test_every_write_stamps_the_engine_version(work):
    work.init()
    assert work.read_ledger()["skill_version"] == SKILL_VERSION
    stamp(work, None)               # a ledger from before the stamp: older, written as usual
    work.open(today="2026-11-02")
    work.run("--today", "2026-11-02", "settings", "--work", work.path, "--config", '{"lab_units": "SI"}')
    assert work.read_json("publish", "data", "state.json")["skill_version"] == SKILL_VERSION


@pytest.mark.parametrize("older", [None, "4.3.0", "5.0", "not a version"])
def test_an_older_or_unstamped_ledger_is_written(work, older):
    work.init()
    stamp(work, older)
    work.save_round("2026-11-02")
    assert work.read_json("publish", "data", "state.json")["skill_version"] == SKILL_VERSION


def test_a_newer_ledger_is_read_but_not_written(work):
    work.init()
    stamp(work, NEWER)
    before = work.read_ledger()
    status = work.open(today="2026-11-02")
    assert status["newer_version"]["ledger"] == NEWER
    assert "update the plugin" in status["newer_version"]["say"]
    # read-only requests still work
    work.run_json("stats", "--work", work.path)
    work.run_json("position", "--work", work.path)
    for args in (("settings", "--work", work.path, "--config", '{"lab_units": "SI"}'),
                 ("snooze", "--work", work.path),
                 ("prepare", "--work", work.path),
                 ("init", "--work", work.path, "--start-over", "--blueprint", "x", "--config", "{}",
                  "--profile", "{}")):
        msg = error(work.run("--today", "2026-11-02", *args, ok=False))
        assert "newer version of the skill (%s; this one is %s)" % (NEWER, SKILL_VERSION) in msg
        assert "update the plugin" in msg and "Nothing was written" in msg
        assert not os.path.exists(work.pub("data", "state.json"))
    assert work.read_ledger() == before


def test_a_round_is_not_begun_on_a_newer_ledger(work):
    work.init()
    stamp(work, NEWER)
    msg = error(work.run("--today", "2026-11-02", "start", "--work", work.path, "--store", work.store(), ok=False))
    assert "update the plugin" in msg
    assert not os.path.exists(work.p("plan.json")) and not os.path.exists(work.p("times.json"))


def play(work, today):
    """A round up to its feedback, in a work folder opened on the store."""
    work.open(today=today)
    work.write("round.json", ROUND)
    work.write("sealed_case.md", SEALED_CASE)
    work.write("sealed_questions.md", SEALED_QUESTIONS)
    work.write("answers.md", ANSWERS)
    work.write("feedback.md", "Feedback text")


ROUND_NAMES = ("round.json", "sealed_case.md", "sealed_questions.md", "answers.md", "feedback.md")


def test_save_refused_mid_round_keeps_the_round_and_saves_after_the_update(work):
    """The other device, with a newer plugin, saved while this round was played: the publish
    is refused, the store is read again (--reread), and `save` stops before writing anything.
    After the update the same work folder saves the round."""
    work.init()
    play(work, "2026-11-02")
    stamp(work, NEWER)              # the store as read again
    work.open("--reread", today="2026-11-02")
    kept = {n: open(work.p(n), encoding="utf-8").read() for n in ROUND_NAMES}
    msg = error(work.run("--today", "2026-11-02", "save", "--work", work.path, ok=False))
    assert "update the plugin" in msg and "not lost" in msg and "--reread" in msg
    assert "store.md section 6" in msg and os.path.abspath(work.path) in msg
    assert {n: open(work.p(n), encoding="utf-8").read() for n in ROUND_NAMES} == kept
    assert not os.path.exists(work.p("record.json"))
    assert not os.path.exists(work.pub("data", "state.json"))
    assert "saved" not in work.read_json("work.json")
    # the plugin is updated: the engine is now as new as the ledger's stamp
    stamp(work, SKILL_VERSION)
    work.open("--reread", today="2026-11-02")
    out = work.run_json("--today", "2026-11-02", "save", "--work", work.path)
    assert out["ok"] and work.read_json("publish", "data", "state.json")["sessions"][-1]["id"] == "S0001"


def test_the_round_files_carried_to_a_new_work_folder_are_saved(work, tmp_path_factory):
    """The conversation ended before the update: the learner kept the round's files; at the next
    session they go into a new work folder opened on the store, and `save` records the round."""
    work.init()
    play(work, "2026-11-02")
    stamp(work, NEWER)              # another device, with a newer plugin, saved to the folder meanwhile
    before = work.read_ledger()
    assert work.run_json("--today", "2026-11-02", "save", "--work", work.path)["ok"]   # on the ledger as read
    msg = error(work.run("publish", "--work", work.path, ok=False))     # the folder moved: applied again, refused
    assert "update the plugin" in msg and "Nothing was written" in msg
    assert work.read_ledger() == before
    kept = tmp_path_factory.mktemp("kept")       # downloads: outside the work folder
    for n in os.listdir(work.path):     # every file but work.json, publish.json, ledger_read.json (store.md §6)
        if os.path.isfile(work.p(n)) and n not in ("work.json", "publish.json", "ledger_read.json"):
            shutil.copy(work.p(n), kept / n)
    stamp(work, SKILL_VERSION)      # updated
    work.forget_job()
    work.open(today="2026-11-03")
    for n in os.listdir(kept):
        shutil.copy(kept / n, work.p(n))
    out = work.run_json("--today", "2026-11-03", "save", "--work", work.path)
    assert out["ok"]


def test_close_refused_on_a_newer_ledger(work):
    work.init()
    work.save_round("2026-11-02")
    work.publish()
    work.forget_job()
    stamp(work, NEWER)
    work.open(today="2026-11-03")
    work.write("answers.md", ANSWERS)
    work.write("reflection.json", {"topic_comfort": {}, "performance": 3, "solid": "a", "gaps": "b"})
    work.write("B.md", "Reflection")
    msg = error(work.run("--today", "2026-11-03", "close", "--work", work.path, ok=False))
    assert "update the plugin" in msg and "not lost" in msg
    assert not os.path.exists(work.pub("data", "state.json"))

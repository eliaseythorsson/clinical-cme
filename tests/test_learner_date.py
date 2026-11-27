"""The learner's date, fixed once per job (issue #84): `open`/`start`/`init` set the job's date
(--today, else the profile's UTC offset, else UTC) and every later command of the job reads it."""
import datetime as dt
import json
import os

from conftest import ANSWERS, BLUEPRINT, REFLECTION, ROUND, SEALED_CASE, SEALED_QUESTIONS, Work
from examples import cme

PLAYED = "2026-11-01"           # long before the real clock: a command that read the clock would show


def round_files(w):
    w.write("round.json", ROUND)
    w.write("sealed_case.md", SEALED_CASE)
    w.write("sealed_questions.md", SEALED_QUESTIONS)
    w.write("answers.md", ANSWERS)
    w.write("feedback.md", "Feedback text")


def utc_date_at(offset):
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=offset)).date().isoformat()


def test_a_job_crossing_midnight_dates_start_and_save_the_same(work):
    work.init(today=PLAYED)
    work.open(today=PLAYED)                         # opened before midnight, the learner's date given
    assert work.read_json("work.json")["started"] == PLAYED
    round_files(work)
    work.run_json("save", "--work", work.path)      # after midnight: no --today, the job's date
    st = work.read_json("publish", "data", "state.json")
    assert st["sessions"][-1]["date"] == PLAYED and st["updated"] == PLAYED
    assert st["topics"]["GEN-11"]["last"] == PLAYED
    assert work.read_json("publish", "data", "sessions", "S0001.json")["date"] == PLAYED
    work.write("reflection.json", REFLECTION)
    work.write("B.md", "Reflection verbatim")
    work.run_json("close", "--work", work.path)
    assert work.read_json("publish", "data", "state.json")["updated"] == PLAYED


def test_a_later_today_still_wins(work):
    work.init(today=PLAYED)
    work.save_round(PLAYED)
    work.close_round("2026-11-03")
    assert work.read_json("publish", "data", "state.json")["updated"] == "2026-11-03"


def test_a_learner_at_utc_minus_8_in_the_evening(work):
    work.init(today=PLAYED, profile={"utc_offset": -8})
    # 19:30 on 26 November in Los Angeles is 03:30 on the 27th in UTC
    out = work.run_json("start", "--work", work.path, "--store", work.store(), "--at", "2026-11-27T03:30:00Z")
    assert out["ok"] is not False
    assert work.read_json("work.json")["started"] == "2026-11-26"
    round_files(work)
    work.run_json("save", "--work", work.path)
    st = work.read_json("publish", "data", "state.json")
    assert st["sessions"][-1]["date"] == "2026-11-26"
    assert work.read_json("publish", "data", "sessions", "S0001.json")["date"] == "2026-11-26"


def test_session_doc_a_honours_the_jobs_date():
    assert cme.session_doc_a({}, "S0001", "md", dt.date(2026, 11, 1))["date"] == PLAYED
    assert cme.session_doc_a({"date": "2026-10-30"}, "S0001", "md", dt.date(2026, 11, 1))["date"] == "2026-10-30"


def test_the_offset_is_the_fallback_when_no_date_is_given(work):
    work.init(today=PLAYED, profile={"utc_offset": 5.5})
    before = utc_date_at(5.5)
    work.open()
    assert work.read_json("work.json")["started"] in (before, utc_date_at(5.5))


def test_without_a_date_or_an_offset_the_date_is_as_before(work):
    work.init(today=PLAYED)
    assert work.read_ledger()["profile"]["utc_offset"] is None
    before = dt.date.today().isoformat()
    work.open()
    assert work.read_json("work.json")["started"] in (before, dt.date.today().isoformat())


def test_init_without_a_date_uses_the_offset_in_its_profile(tmp_path):
    w = Work(tmp_path)
    before = utc_date_at(-8)
    w.run("init", "--work", w.path, "--blueprint", BLUEPRINT,
          "--config", "{}", "--profile", json.dumps({"utc_offset": -8}))
    assert w.read_json("work.json")["started"] in (before, utc_date_at(-8))
    assert w.read_json("publish", "data", "state.json")["profile"]["utc_offset"] == -8


def test_settings_sets_the_offset_and_refuses_anything_else(work):
    work.init(today=PLAYED)
    work.open(today=PLAYED)
    out = work.run_json("settings", "--work", work.path, "--profile", '{"utc_offset": -8}')
    assert out["ok"]
    assert work.read_json("publish", "data", "state.json")["profile"]["utc_offset"] == -8
    for bad in ('"-8"', "20", "true"):
        r = work.run("settings", "--work", work.path, "--profile", '{"utc_offset": %s}' % bad, ok=False)
        assert r.returncode != 0 and "utc_offset" in r.stdout
    assert work.run_json("settings", "--work", work.path, "--profile", '{"utc_offset": null}')["ok"]
    assert work.read_json("publish", "data", "state.json")["profile"]["utc_offset"] is None


def test_a_reread_keeps_the_jobs_date(work):
    work.init(today=PLAYED)
    work.open(today=PLAYED)
    work.run_json("open", "--work", work.path, "--store", work.store(), "--reread")
    assert work.read_json("work.json")["started"] == PLAYED


def test_start_in_an_open_job_keeps_the_jobs_date(work):
    work.init(today=PLAYED)
    work.open(today=PLAYED)
    work.run_json("start", "--work", work.path)                     # no --store, no --today, no offset
    assert work.read_json("work.json")["started"] == PLAYED


def test_start_at_counts_without_an_offset(work):
    work.init(today=PLAYED)
    work.run_json("start", "--work", work.path, "--store", work.store(), "--at", "2026-11-05T23:30:00Z")
    assert work.read_json("work.json")["started"] == "2026-11-05"


def test_a_bad_at_or_offset_on_start_writes_nothing(work):
    work.init(today=PLAYED)
    for extra in (("--at", "yesterday"), ("--utc-offset", "-13"), ("--utc-offset", "nan"),
                  ("--utc-offset", "LA")):
        r = work.run("start", "--work", work.path, "--store", work.store(), *extra, ok=False)
        assert r.returncode != 0
        assert not any(os.path.exists(work.p(n)) for n in ("work.json", "publish", "plan.json")), extra


def test_open_records_a_new_offset_and_not_the_same_one_twice(work):
    work.init(today=PLAYED)
    out = work.run_json("--today", PLAYED, "open", "--work", work.path, "--store", work.store(),
                        "--utc-offset", "5.5")
    assert out["utc_offset_recorded"] == 5.5
    assert work.read_json("publish", "data", "state.json")["profile"]["utc_offset"] == 5.5
    work.publish()
    work.forget_job()
    out = work.run_json("--today", PLAYED, "open", "--work", work.path, "--store", work.store(),
                        "--utc-offset", "5.5")
    assert "utc_offset_recorded" not in out and not os.path.exists(work.pub("data", "state.json"))


def test_init_does_not_take_an_earlier_jobs_date(work):
    work.write("work.json", {"started": "2020-01-01", "store": None, "state": None})
    before = dt.date.today().isoformat()
    work.run("init", "--work", work.path, "--blueprint", BLUEPRINT, "--config", "{}", "--profile", "{}")
    assert work.read_json("work.json")["started"] in (before, dt.date.today().isoformat())

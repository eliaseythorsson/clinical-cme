"""Planning, scheduling and applying a round on each example ledger, against saved expected
output; and the same ledger and date always give the same plan and due dates (issue #6).

See tests/examples.py for the ledgers and for how to accept a deliberate change."""
import copy
import datetime as dt
import json
import os
import shutil

import pytest

import examples
from conftest import CME, run_script
from examples import LEDGERS, PREPARED_MADE, cme

PARTS = ("plan", "schedule", "applied")
UPDATE = bool(os.environ.get("CME_UPDATE_EXPECTED"))
ledgers = pytest.mark.parametrize("name", list(LEDGERS))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_cme(args, hashseed=None):
    """cme.py with these arguments; with a `hashseed`, as its own process with that string hashing."""
    env = None if hashseed is None else dict(os.environ, PYTHONHASHSEED=hashseed)
    r = run_script(CME, args, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


# ---- the example ledgers themselves

@ledgers
def test_example_ledger_is_valid_and_synthetic(name, capsys):
    assert cme.main(["validate", examples.ledger_path(name)]) == 0, capsys.readouterr().out
    st = examples.load_ledger(name)
    assert st["schema"] == cme.SCHEMA
    assert st["profile"]["display_name"] == "Example learner"
    assert all(s["title"].startswith("Example round") for s in st["sessions"])


def test_example_ledgers_are_what_their_names_say():
    at = {name: (examples.load_ledger(name), examples.today_of(name)) for name in LEDGERS}

    st, today = at["fresh"]
    assert st["sessions"] == [] and st["topics"] == {} and st["created"] == cme.iso(today)

    st, today = at["mid_curriculum"]
    assert len(st["sessions"]) == 10 and st["unreflected"] is None
    assert (today - cme.parse_date(st["sessions"][-1]["date"])).days == 5
    dues = [cme.parse_date(t["due"]) for t in st["topics"].values()]
    assert any(d <= today for d in dues) and any(d > today for d in dues)

    st, today = at["overdue"]
    assert (today - cme.parse_date(st["sessions"][-1]["date"])).days > 90
    assert all((today - cme.parse_date(t["due"])).days >= 7 for t in st["topics"].values())
    assert cme.review_status(st, today)[0] is True

    st, today = at["unreflected"]
    waiting = st["sessions"][-1]
    assert st["unreflected"] == waiting["id"] and waiting["reflection"] is None
    assert waiting["_round"]["items"] and waiting["_snapshot"]["next_id"] == waiting["id"]

    st, today = at["stale_prepared"]
    prepared = read(examples.prepared_path("stale_prepared"))
    assert prepared["gen"] == st["gen"] and prepared["session_id"] == st["next_id"]
    assert prepared["made"] == PREPARED_MADE
    assert (today - cme.parse_date(prepared["made"])).days > cme.PREPARED_MAX_AGE_DAYS


# ---- expected output

@ledgers
def test_plan_schedule_and_applied_round_match_the_expected_output(name):
    result = examples.play(name)
    if UPDATE:
        for part in PARTS:
            os.makedirs(os.path.dirname(examples.expected_path(name, part)), exist_ok=True)
            with open(examples.expected_path(name, part), "w", encoding="utf-8") as fh:
                json.dump(result[part], fh, ensure_ascii=False, indent=1, sort_keys=True)
                fh.write("\n")
    for part in PARTS:
        assert result[part] == read(examples.expected_path(name, part)), \
            "%s/%s changed; see tests/examples.py for how to accept a deliberate change" % (name, part)


@ledgers
def test_scripted_round_is_one_the_engine_accepts_without_warnings(name):
    applied = examples.play(name)["applied"]
    assert applied["record"]["warnings"] == [] and applied["reflect"]["warnings"] == []
    assert applied["record"]["reflection_pending"] is True


def test_unreflected_ledger_reflecting_or_moving_on():
    """The waiting round can still get its reflection; recording the next round instead keeps it
    in the ledger with the reflection marked as skipped."""
    st = examples.load_ledger("unreflected")
    result = examples.play("unreflected")
    waiting = result["applied"]["waiting_round"]
    assert waiting["reflect"]["session_id"] == st["unreflected"]
    assert waiting["ledger_after"]["unreflected"] is None
    assert waiting["ledger_after"]["session"]["date"] == st["sessions"][-1]["date"]   # not the day of reflecting
    skipped = next(s for s in result["ledger"]["sessions"] if s["id"] == st["unreflected"])
    assert skipped["reflection"] == {"skipped": True} and "_round" not in skipped
    assert result["ledger"]["agg"]["reflection_skipped"] == st["agg"]["reflection_skipped"] + 1


def store_copy(tmp_path, st, prepared=None):
    """A folder store holding the ledger `st` (and a prepared round), as a session reads it."""
    data = tmp_path / "store" / "data"
    data.mkdir(parents=True)
    cme.save_json(st, str(data / "state.json"))
    if prepared:
        shutil.copy(prepared, str(data / "prepared.json"))
    return str(tmp_path / "store")


def start(tmp_path, today, st, prepared=None, hashseed=None):
    work = tmp_path / "work"
    out = json.loads(run_cme(["--today", today, "start", "--work", str(work),
                              "--store", store_copy(tmp_path, st, prepared)], hashseed))
    return out, read(str(work / "plan.json"))


def start_with_prepared(tmp_path, today):
    return start(tmp_path, today, examples.load_ledger("stale_prepared"), examples.prepared_path("stale_prepared"))


def test_stale_prepared_round_is_not_used_and_a_new_round_is_planned(tmp_path):
    out, plan = start_with_prepared(tmp_path, LEDGERS["stale_prepared"])
    assert out["prepared"] == {"used": False, "why": "too old"}
    assert "present" not in out                             # no drafted files
    assert sorted(os.listdir(str(tmp_path / "work"))) == ["plan.json", "publish.json", "times.json", "work.json"]
    assert "prepared" not in plan
    assert plan == read(examples.expected_path("stale_prepared", "plan"))


def test_round_prepared_before_blocks_is_not_used(tmp_path):
    """The example's prepared round was written by a version without themed blocks: it is not on
    the theme of the block that starts with the next round, so it is set aside."""
    soon = cme.iso(cme.parse_date(PREPARED_MADE) + dt.timedelta(days=2))
    out, plan = start_with_prepared(tmp_path, soon)
    assert out["prepared"] == {"used": False, "why": "it was not prepared for this round of the block"}
    assert "prepared" not in plan and plan["block"]["line"] == out["block"]["line"]


def test_a_newly_prepared_round_is_used_while_it_is_fresh(tmp_path):
    name = "stale_prepared"
    st = examples.load_ledger(name)
    work, store = tmp_path / "work", store_copy(tmp_path, st)
    w = ["--work", str(work)]
    run_cme(["--today", PREPARED_MADE, "open", *w, "--store", store])
    run_cme(["--today", PREPARED_MADE, "prepare", *w])
    for fname, text in examples.sealed_files(st, read(str(work / "next" / "plan.json"))).items():
        (work / "next" / fname).write_text(text, encoding="utf-8")
    packed = json.loads(run_cme(["finish-prepare", *w, "--no-evidence"]))
    for f in packed["files"]:                               # published to the store
        shutil.copy(f["path"], os.path.join(store, *f["as"].split("/")))
    soon = cme.iso(cme.parse_date(PREPARED_MADE) + dt.timedelta(days=2))
    out = json.loads(run_cme(["--today", soon, "start", *w, "--store", store]))
    plan = read(str(work / "plan.json"))
    assert out["prepared"]["used"] is True and out["prepared"]["made"] == PREPARED_MADE
    assert out["plan"]["prepared"] is True and plan["prepared"]["used"] is True and plan["date"] == soon
    assert plan["block"]["line"] == out["block"]["line"]
    assert sorted(os.listdir(str(work))) == ["earlier", "kit_case.md", "kit_questions.md", "plan.json", "publish.json",
                                             "sealed_case.md", "sealed_questions.md", "times.json", "work.json"]
    # and it is left alone when the round is asked for without it
    out = json.loads(run_cme(["--today", soon, "start", *w, "--store", store, "--no-prepared"]))
    assert out["prepared"]["used"] is False and "present" not in out


def test_prepared_round_no_longer_fits_once_the_ledger_has_moved_on(tmp_path):
    after = examples.play("stale_prepared")["ledger"]
    out, _ = start(tmp_path, PREPARED_MADE, after, examples.prepared_path("stale_prepared"))
    assert out["prepared"] == {"used": False, "why": "the ledger changed since it was prepared"}


# ---- the same ledger and date always give the same plan and due dates

@ledgers
def test_playing_a_round_twice_gives_the_same_result_and_leaves_the_ledger_alone(name):
    st = examples.load_ledger(name)
    before = copy.deepcopy(st)
    first = examples.play(name, st)
    assert st == before
    assert examples.play(name, st) == first


@ledgers
def test_plan_and_due_dates_do_not_depend_on_the_process(name, tmp_path):
    """Separate runs of cme.py, with different string hashing, write identical files."""
    today = LEDGERS[name]
    expected = read(examples.expected_path(name, "plan"))
    rnd = read(examples.expected_path(name, "applied"))["round"]
    ledgers_after = []
    for seed in ("0", "1", "4242"):
        folder = tmp_path / seed
        folder.mkdir()
        _, plan = start(folder, today, examples.load_ledger(name), hashseed=seed)
        assert plan == expected
        cme.save_json(rnd, str(folder / "work" / "round.json"))
        (folder / "work" / "feedback.md").write_text("Example feedback", encoding="utf-8")
        saved = json.loads(run_cme(["--today", today, "save", "--work", str(folder / "work")], seed))
        with open(saved["files"][-1]["path"], "rb") as fh:
            ledgers_after.append(fh.read())
    assert ledgers_after[0] == ledgers_after[1] == ledgers_after[2]
    after = json.loads(ledgers_after[0].decode("utf-8"))
    schedule = read(examples.expected_path(name, "schedule"))["after_record"]
    assert {tid: after["topics"][tid] for tid in schedule} == schedule
    # and the command writes the ledger the core function gives
    st = examples.load_ledger(name)
    cme.record_round(st, copy.deepcopy(rnd), examples.today_of(name))
    assert after == json.loads(json.dumps(st))


@ledgers
def test_plan_changes_with_the_date_only_through_the_date(name):
    """Planning has no hidden clock: a given date gives the same plan whenever it is asked for."""
    st = examples.load_ledger(name)
    day = examples.today_of(name) + dt.timedelta(days=3)
    a = cme.plan_round(st, examples.plan_options(), day)
    b = cme.plan_round(copy.deepcopy(st), examples.plan_options(), day)
    assert a == b and a["date"] == cme.iso(day)


def test_spacing_is_a_pure_function_of_its_inputs():
    intervals = cme.DEFAULT_CONFIG["intervals_days"]
    day = dt.date(2026, 11, 20)
    seen = {}
    for _ in range(2):
        for step in range(len(intervals)):
            for mastery in (0, 1, 2, 3, 3.5, 4, 5):
                for comfort in (None, 1, 3, 5):
                    for misconception in (False, True):
                        for self_gap in (False, True):
                            key = (step, mastery, comfort, misconception, self_gap)
                            got = cme.schedule_topic(step, mastery, comfort, misconception, self_gap, intervals, day)
                            assert seen.setdefault(key, got) == got
                            new_step, due, _, interval = got
                            assert 0 <= new_step < len(intervals)
                            assert interval >= 1 and due == day + dt.timedelta(days=interval)

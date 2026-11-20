"""What must hold on every example ledger whatever the curriculum does (issue #6): the log only
grows, a failed or interrupted write leaves the ledger untouched, and nothing printed before the
answers are in names a key, a topic or a diagnosis."""
import copy
import datetime as dt
import json
import os
import re

import pytest

import examples
from examples import LEDGERS, PREPARED_MADE, cme

ledgers = pytest.mark.parametrize("name", list(LEDGERS))
TOPIC_ID = re.compile(r"\b[A-Z]{2,6}-\d{2}\b")


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def files_under(path):
    return sorted(os.path.join(root, n) for root, _, names in os.walk(path) for n in names)


def write_round_files(work, st, plan):
    """The files a round leaves in the work folder: sealed drafts, answers, feedback, round.json."""
    for fname, text in examples.sealed_files(st, plan).items():
        work.write(fname, text)
    work.write("answers.md", "<!-- answers: questions -->\nQ1 B sure\n<!-- /answers -->\n"
                             "<!-- answers: case -->\nexample answer\n<!-- /answers -->\n")
    work.write("feedback.md", "Example feedback for %s" % plan["session_id"])
    rnd = examples.round_for(st, plan)
    work.write("round.json", rnd)
    return rnd


def save(work, state, today, out, index=None):
    sealed = [work.p(n) for n in ("sealed_questions.md", "sealed_case.md") if os.path.exists(work.p(n))]
    args = ["--today", today, "save", state, "--round", work.p("round.json"), "--sealed", *sealed,
            "--answers", work.p("answers.md"), "--feedback", work.p("feedback.md"), "--out-dir", work.p(out)]
    return work.run_json(*(args + (["--index", index] if index else [])))


# ---- the log only grows

def session_ids(st):
    return [s["id"] for s in st["previous"] + st["sessions"]]


def settled(session):
    """A ledger session entry without the parts that wait for its reflection."""
    return {k: v for k, v in session.items() if k not in ("_snapshot", "_round", "reflection")}


@ledgers
def test_log_only_grows_over_save_close_and_the_next_save(name, work):
    start = examples.load_ledger(name)
    day = examples.today_of(name)
    days = [cme.iso(day + dt.timedelta(days=n)) for n in (0, 1, 3)]
    state0 = work.write("ledger.json", start)

    plan = cme.plan_round(start, examples.plan_options(), day)
    rnd1 = write_round_files(work, start, plan)
    sid1 = save(work, state0, days[0], "out1")["session_id"]
    work.write("refl.json", examples.reflection_for(rnd1))
    work.write("B.md", "Example reflection, verbatim")
    work.run("--today", days[1], "close", work.p("out1", "data", "state.json"), "--reflection", work.p("refl.json"),
             "--md", work.p("B.md"), "--doc", work.p("out1", "data", "sessions", sid1 + ".json"),
             "--index", work.p("out1", "data", "index.json"), "--out-dir", work.p("out2"))
    after_close = work.read_json("out2", "data", "state.json")
    plan2 = cme.plan_round(after_close, examples.plan_options(), day + dt.timedelta(days=3))
    write_round_files(work, after_close, plan2)
    sid2 = save(work, work.p("out2", "data", "state.json"), days[2], "out3",
                index=work.p("out2", "data", "index.json"))["session_id"]

    before_ids = session_ids(start)
    ledgers_seen = [start] + [work.read_json(o, "data", "state.json") for o in ("out1", "out2", "out3")]
    indexes = [work.read_json(o, "data", "index.json") for o in ("out1", "out2", "out3")]

    # the ledger and the index list every earlier round, in order, then the new ones
    assert [session_ids(st) for st in ledgers_seen] == [
        before_ids, before_ids + [sid1], before_ids + [sid1], before_ids + [sid1, sid2]]
    assert [[e["id"] for e in idx["sessions"]] for idx in indexes] == [
        before_ids + [sid1], before_ids + [sid1], before_ids + [sid1, sid2]]
    assert sid1 not in before_ids and sid2 not in before_ids + [sid1]

    # earlier rounds are never rewritten (a round still waiting for its reflection is only marked skipped)
    for st in ledgers_seen[1:]:
        for old, now in zip(start["previous"] + start["sessions"], st["previous"] + st["sessions"]):
            assert settled(now) == settled(old)
            if old["id"] != start["unreflected"]:
                assert now == old
    for old, now in zip(indexes[0]["sessions"][:-1], indexes[2]["sessions"]):
        assert now == old

    # the session document: the close adds to it and changes nothing that was there
    doc_a = work.read_json("out1", "data", "sessions", sid1 + ".json")
    doc_b = work.read_json("out2", "data", "sessions", sid1 + ".json")
    assert doc_a["closing"] is None and doc_a["reflected"] is False
    assert doc_b["closing"] == "Example reflection, verbatim" and doc_b["reflected"] is True
    grown = ("closing", "reflected", "score")
    assert {k: v for k, v in doc_b.items() if k not in grown} == {k: v for k, v in doc_a.items() if k not in grown}
    assert "Example feedback for %s" % sid1 in doc_b["transcript"]
    # and the next save writes a new document, not the old one again
    assert [os.path.basename(p) for p in files_under(work.p("out3", "data", "sessions"))] == [sid2 + ".json"]


@ledgers
def test_a_round_cannot_be_recorded_twice(name):
    st = examples.load_ledger(name)
    day = examples.today_of(name)
    rnd = examples.round_for(st, cme.plan_round(st, examples.plan_options(), day))
    cme.record_round(st, copy.deepcopy(rnd), day)
    with pytest.raises(cme.CmeError) as e:
        cme.record_round(st, copy.deepcopy(rnd), day)
    assert "already recorded" in e.value.msg


# ---- a failed or interrupted write leaves the ledger untouched

BAD_ROUNDS = (
    {"items": []},
    {"items": [{"type": "mcq", "mastery": 3}]},                                              # no topic
    {"items": [{"type": "mcq", "topic": "CARD-01", "mastery": 3, "confidence": "certain"}]},
    {"items": [{"type": "mcq", "topic": "CARD-01", "mastery": 3}], "gaps": [{"topic": "CARD-01"}]},
)


@ledgers
def test_failed_commands_leave_the_ledger_and_the_output_folder_untouched(name, work):
    state = work.write("ledger.json", examples.load_ledger(name))
    before = read_bytes(state)
    work.write("fb.md", "x")
    for i, bad in enumerate(BAD_ROUNDS):
        r = work.run("--today", LEDGERS[name], "save", state, "--round", json.dumps(bad), "--feedback", work.p("fb.md"),
                     "--out-dir", work.p("save%d" % i), ok=False)
        assert r.returncode == 2 and json.loads(r.stdout)["ok"] is False
        # written over the ledger itself: still nothing changes
        r = work.run("--today", LEDGERS[name], "record", state, "--round", json.dumps(bad), "--out", state, ok=False)
        assert r.returncode == 2
    r = work.run("--today", LEDGERS[name], "close", state, "--reflection", "{}", "--md", work.p("fb.md"),
                 "--session", "S9999", "--out-dir", work.p("close"), ok=False)
    assert r.returncode == 2
    r = work.run("--today", LEDGERS[name], "reflect", state, "--reflection", "{}", "--session", "S9999",
                 "--out", state, ok=False)
    assert r.returncode == 2
    assert read_bytes(state) == before
    assert files_under(work.path) == sorted([state, work.p("fb.md")])


def test_core_error_before_anything_is_applied_leaves_the_ledger_in_memory_alone():
    for name in LEDGERS:
        st = examples.load_ledger(name)
        if st["unreflected"]:
            continue    # recording finalizes the waiting round first; the commands never write that on an error
        before = copy.deepcopy(st)
        for bad in BAD_ROUNDS:
            with pytest.raises(cme.CmeError):
                cme.record_round(st, copy.deepcopy(bad), examples.today_of(name))
        assert st["sessions"] == before["sessions"] and st["next_id"] == before["next_id"]
        assert st["gen"] == before["gen"] and st["unreflected"] == before["unreflected"]


class Interrupted(Exception):
    pass


def interrupt(monkeypatch, where):
    """Make the write of a ledger file stop half way: while its text is written, or at the move."""
    def boom(*a, **k):
        raise Interrupted()
    if where == "writing":
        def half(obj, fh, **k):
            fh.write(json.dumps(obj)[:200])
            fh.flush()
            raise Interrupted()
        monkeypatch.setattr(cme.json, "dump", half)
    else:
        monkeypatch.setattr(cme.os, "replace", boom)


@ledgers
@pytest.mark.parametrize("where", ["writing", "moving"])
def test_interrupted_write_over_the_ledger_leaves_it_untouched(name, where, work, monkeypatch):
    st = examples.load_ledger(name)
    state = work.write("ledger.json", st)
    before = read_bytes(state)
    rnd = examples.round_for(st, cme.plan_round(st, examples.plan_options(), examples.today_of(name)))
    work.write("round.json", rnd)
    interrupt(monkeypatch, where)
    with pytest.raises(Interrupted):
        cme.main(["--today", LEDGERS[name], "record", state, "--round", work.p("round.json"), "--out", state])
    if st["unreflected"]:
        with pytest.raises(Interrupted):
            cme.main(["--today", LEDGERS[name], "reflect", state, "--reflection", "{}", "--out", state])
    monkeypatch.undo()
    assert read_bytes(state) == before
    assert files_under(work.path) == sorted([state, work.p("round.json")])     # no half-written file left behind
    assert cme.main(["validate", state]) == 0


@ledgers
def test_save_interrupted_part_way_leaves_the_ledger_untouched(name, work, monkeypatch):
    """save writes several files into its output folder; the ledger it read is never one of them."""
    st = examples.load_ledger(name)
    state = work.write("ledger.json", st)
    before = read_bytes(state)
    write_round_files(work, st, cme.plan_round(st, examples.plan_options(), examples.today_of(name)))
    real, calls = cme.save_json, []

    def second_write_fails(obj, path):
        calls.append(path)
        if len(calls) == 2:
            raise Interrupted()
        return real(obj, path)
    monkeypatch.setattr(cme, "save_json", second_write_fails)
    with pytest.raises(Interrupted):
        cme.main(["--today", LEDGERS[name], "save", state, "--round", work.p("round.json"),
                  "--sealed", work.p("sealed_questions.md"), work.p("sealed_case.md"),
                  "--answers", work.p("answers.md"), "--feedback", work.p("feedback.md"), "--out-dir", work.p("out")])
    monkeypatch.undo()
    assert len(calls) == 2 and read_bytes(state) == before
    # the same save, run again, succeeds from the untouched ledger
    assert save(work, state, LEDGERS[name], "out_again")["session_id"] == st["next_id"]


# ---- text printed before the answers are in never contains a key, topic ID or diagnosis

def secrets_of(st, plan=None):
    """Every string that would give away what a round tests: topic IDs and names, the open gaps,
    past diagnoses, and whatever the sealed files keep outside their present blocks."""
    out = set(cme.bp_topics(st)) | set(st["topics"])
    out |= {info["label"] for info in cme.bp_topics(st).values()}
    out |= {g["gap"] for g in st["gaps"]}
    out |= {s["case"]["diagnosis"] for s in st["sessions"] if s.get("case")}
    out |= {"SEALED", "KEY", "Diagnosis", "Example diagnosis"}
    if plan:
        out |= {it["reason"] for it in plan["items"]}
    return {s for s in out if s}


def assert_blind(text, st, plan=None):
    assert text.strip()
    found = sorted(s for s in secrets_of(st, plan) if s in text) + TOPIC_ID.findall(text)
    assert found == [], "printed text names %s" % found


@ledgers
def test_status_start_plan_and_prepare_print_no_topic_gap_or_diagnosis(name, work):
    st = examples.load_ledger(name)
    state = work.write("ledger.json", st)
    today = LEDGERS[name]
    printed = [
        work.run("--today", today, "status", state).stdout,
        work.run("--today", today, "start", state, "--out", work.p("start.json")).stdout,
        work.run("--today", today, "plan", state, "--out", work.p("plan.json")).stdout,
        work.run("--today", today, "prepare", state, "--out", work.p("next.json")).stdout,
        work.run("--today", today, "prepare", state, "--allow-unreflected", "--out", work.p("next.json")).stdout,
    ]
    plan = work.read_json("plan.json")
    for text in printed:
        assert_blind(text, st, plan)
    # the check has teeth: the plan file, which is not printed, does name the topics
    with pytest.raises(AssertionError):
        assert_blind(json.dumps(plan), st, plan)


@ledgers
def test_present_prints_only_what_the_learner_may_see(name, work):
    st = examples.load_ledger(name)
    plan = cme.plan_round(st, examples.plan_options(), examples.today_of(name))
    files = examples.sealed_files(st, plan)
    for fname, text in files.items():
        work.write(fname, text)
    sealed = [work.p("sealed_questions.md"), work.p("sealed_case.md")]
    shown = {block: work.run("present", *sealed, "--block", block).stdout for block in ("questions", "case", "bank")}
    for text in shown.values():
        assert_blind(text, st, plan)
    assert "Example stem 1" in shown["questions"] and "An example patient presents" in shown["case"]
    assert "sodium 140" in shown["bank"] and "sodium 140" not in shown["case"]
    with pytest.raises(AssertionError):     # the sealed files do hold the key, topic and diagnosis
        assert_blind(files["sealed_case.md"], st, plan)


def test_taking_and_stashing_a_prepared_round_prints_only_its_present_block(work):
    name = "stale_prepared"
    st = examples.load_ledger(name)
    state = work.write("ledger.json", st)
    soon = cme.iso(cme.parse_date(PREPARED_MADE) + dt.timedelta(days=1))
    r = work.run("--today", soon, "start", state, "--prepared", examples.prepared_path(name),
                 "--out", work.p("plan.json"), "--work-dir", work.p("round"))
    out = json.loads(r.stdout)
    plan = work.read_json("plan.json")
    assert out["prepared"]["used"] is True
    assert out["present"] == "Q1. Example stem 1. A) one B) two C) three\nQ2. Example stem 2. A) one B) two C) three\n" \
                             "Q3. Example stem 3. A) one B) two C) three"
    assert_blind(r.stdout.replace(work.path, ""), st, plan)
    # stashing a newly prepared round
    work.run("--today", soon, "prepare", state, "--out", work.p("next.json"))
    for fname, text in examples.sealed_files(st, work.read_json("next.json")).items():
        work.write(fname, text)
    r = work.run("stash", state, "--plan", work.p("next.json"), "--dir", work.path, "--out-dir", work.p("out"))
    assert_blind(r.stdout.replace(work.path, ""), st, plan)
    stored = read_bytes(work.p("out", "data", "prepared.json")).decode("utf-8")
    assert_blind(stored, st, plan)      # packed: not readable at a glance in the store either

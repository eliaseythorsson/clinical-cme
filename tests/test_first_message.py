"""Issue #43: the first questions within about ten seconds, however long the history.

Before the first message the assistant makes one `start` call. These tests guard what that call
costs and what it gives: its time stays flat as sessions pile up (ledgers of 10, 40, 100 and 300
sessions, grown from an example ledger), it never opens a session document, a review report or
the page file, and it prints everything the first message needs, so nothing else is run or read."""
import copy
import datetime as dt
import json
import os
import shutil
import time

import pytest

import examples
from conftest import SKILL, Work
from examples import cme
from test_finish_prepare import evidence

SIZES = (10, 40, 100, 300)
START_LIMIT = 1.0           # seconds for one `start` (or `open`), interpreter included
GROWTH_LIMIT = 3.0          # the 300-session store against the 10-session one
GROWTH_FLOOR = 0.05         # ... or this many seconds more: below it a ratio of timings is noise
RUNS = 7                    # runs of each call; the fastest counts
TRANSCRIPT = "Verbatim transcript of an example round. " * 600      # ~25 KB a session document


def any_topic(st, plan):
    """The plan names a topic or only a domain. The example learner then takes an untested
    topic; a long history has none left in some domains, so any topic of the domain will do."""
    taken = {it["topic"] for it in plan["items"] if it.get("topic")}
    for it in plan["items"]:
        if not it.get("topic"):
            pool = sorted(t for t, info in cme.bp_topics(st).items() if info["domain"] == it["domain"] and t not in taken)
            it["topic"] = next((t for t in pool if t not in st["topics"]), pool[0])
            taken.add(it["topic"])
    return plan


def grow(st, last, upto, docs):
    """Play scripted rounds on `st`, one every two days after `last`, until it has seen `upto`
    sessions; `docs` collects each round's session document. Returns the last round's date."""
    while cme.id_num(st["next_id"]) <= upto:
        last += dt.timedelta(days=2)
        plan = any_topic(st, cme.plan_round(st, examples.plan_options(), last))
        rnd = examples.round_for(st, plan)
        cme.record_round(st, copy.deepcopy(rnd), last)
        cme.reflect_round(st, examples.reflection_for(rnd), last)
        entry = st["sessions"][-1]
        docs[entry["id"]] = dict(cme.page_session(entry), transcript=TRANSCRIPT, closing="Reflection verbatim")
    return last


def write_store(root, st, docs):
    """A page store as a session reads it: ledger, page file, page, every session document."""
    store = os.path.join(root, "store")
    os.makedirs(os.path.join(store, "data", "sessions"))
    cme.save_json(st, os.path.join(store, "data", "state.json"))
    lists = cme.page_lists(None)
    for doc in docs.values():
        cme.page_put_session(lists, doc)
    cme.save_json(cme.page_doc(st, lists), os.path.join(store, "data", "page.json"))
    shutil.copy(os.path.join(SKILL, "templates", "page.html"), os.path.join(store, "index.html"))
    for sid, doc in docs.items():
        cme.save_json(doc, os.path.join(store, "data", "sessions", sid + ".json"))
    return store


def prepare_next(w, day):
    """Prepare the next round into the store, as the close of the last session did."""
    w.open(today=day)
    w.run("--today", day, "prepare", "--work", w.path)
    st, plan = w.read_ledger(), any_topic(w.read_ledger(), w.read_json("next", "plan.json"))
    for name, text in examples.sealed_files(st, plan).items():
        w.write(os.path.join("next", name), text)
    for part in ("questions", "case"):
        w.write(os.path.join("next", "evidence_%s.md" % part), evidence(0))
    assert w.run_json("finish-prepare", "--work", w.path)["stashed"] is True
    w.publish()
    w.forget_job()


@pytest.fixture(scope="module")
def stores(tmp_path_factory):
    """{sessions: (work folder with the store copy and a prepared round, the day of the next
    round)}, all grown from the same example ledger."""
    st = examples.load_ledger("mid_curriculum")
    last, docs, out = dt.date.fromisoformat(st["sessions"][-1]["date"]), {}, {}
    for s in st["sessions"]:
        docs[s["id"]] = dict(cme.page_session(s), transcript=TRANSCRIPT, closing="Reflection verbatim")
    for n in SIZES:
        last = grow(st, last, n, docs)
        root = str(tmp_path_factory.mktemp("history%d" % n))
        write_store(root, copy.deepcopy(st), docs)
        w = Work(root)
        prepare_next(w, cme.iso(last))
        out[n] = (w, cme.iso(last + dt.timedelta(days=2)))
    return out


def timed(w, command, day):
    """One run of `start` or `open` on a fresh job: seconds taken, and the output."""
    w.forget_job()
    t = time.perf_counter()
    out = w.start(day) if command == "start" else w.open(today=day)
    return time.perf_counter() - t, out


def fastest(stores, command, runs=RUNS):
    """{sessions: the fastest of several runs on that store, in seconds} and {sessions: the last
    run's output}. The stores take turns, run by run, so that a burst of load on the machine
    (other tests in parallel, CI neighbours) slows them alike rather than one of them."""
    best, outs = {}, {}
    for _ in range(runs):
        for n, (w, day) in stores.items():
            took, outs[n] = timed(w, command, day)
            best[n] = min(best.get(n, took), took)
    return best, outs


def test_the_stores_grow_with_history_and_the_ledger_stays_capped(stores):
    sizes = {}
    for n, (w, _) in stores.items():
        assert len(os.listdir(w.store("data", "sessions"))) == n
        assert len(w.read_json("store", "data", "page.json")["sessions"]) == n
        st = w.read_ledger()
        assert len(st["sessions"]) + len(st["previous"]) == min(n, cme.CAP_SESSIONS + cme.CAP_PREVIOUS)
        sizes[n] = os.path.getsize(w.ledger)
    assert sizes[10] < sizes[40] < sizes[100]
    assert sizes[300] < 1.25 * sizes[100]          # the caps hold: history beyond them costs nothing


@pytest.mark.parametrize("command", ["start", "open"])
def test_time_stays_flat_with_session_history(stores, command):
    """History must not make the call slower. The calls take tens of milliseconds, where a ratio
    alone is noise (issue #72): the 300-session store may take GROWTH_LIMIT times the 10-session
    one, or GROWTH_FLOOR seconds more, whichever is larger. That is too coarse to see one extra
    read of every session document (about 20 ms for 300 here); the test below guards the work
    itself, by the files `start` opens."""
    took, outs = fastest(stores, command)
    for n in stores:
        if command == "start":
            assert outs[n]["prepared"]["used"] is True, outs[n]["prepared"]
        assert took[n] < START_LIMIT, "%s with %d sessions took %.2f s" % (command, n, took[n])
    assert took[300] < max(GROWTH_LIMIT * took[10], took[10] + GROWTH_FLOOR), took


def test_start_reads_no_session_document_review_or_page_file(stores, monkeypatch, capsys):
    """`start` in this process, every file it opens noted: of the store it opens the ledger and
    the prepared round, nothing else, and it never lists the sessions folder (the store copy's
    own folders are listed, to find its documents whatever their names: issue #57)."""
    w, day = stores[300]
    w.forget_job()
    opened, listed = [], []
    real_open = open

    def noting_open(path, *args, **kwargs):
        opened.append(os.path.abspath(path))
        return real_open(path, *args, **kwargs)

    for name in ("listdir", "scandir", "walk"):
        real = getattr(os, name)
        monkeypatch.setattr(cme.os, name, lambda path=".", *a, _real=real, **k: (listed.append(os.path.abspath(path)),
                                                                              _real(path, *a, **k))[1])
    monkeypatch.setattr(cme, "open", noting_open, raising=False)
    assert cme.main(["--today", day, "start", "--work", w.path, "--store", w.store()]) == 0
    assert json.loads(capsys.readouterr().out)["prepared"]["used"] is True
    store = w.store() + os.sep
    assert {os.path.relpath(p, w.store()).replace(os.sep, "/") for p in opened if p.startswith(store)} == {
        "data/state.json", "data/prepared.json"}
    assert not [p for p in listed if (p + os.sep).startswith(w.store("data", "sessions") + os.sep)]
    assert {p for p in listed if (p + os.sep).startswith(store)} <= {w.store(), w.store("data")}


def test_start_does_not_need_the_session_documents_to_be_readable(stores, tmp_path):
    """Session documents that are not JSON at all change nothing for `start`."""
    w0, day = stores[100]
    w = Work(tmp_path / "work")
    shutil.copytree(w0.store(), w.store())
    for name in os.listdir(w.store("data", "sessions")):
        with open(w.store("data", "sessions", name), "w", encoding="utf-8") as fh:
            fh.write("not a session document")
    with open(w.store("data", "page.json"), "w", encoding="utf-8") as fh:
        fh.write("not a page file")
    out = w.start(day)
    assert out["prepared"]["used"] is True and out["present"]


def test_start_prints_all_the_first_message_needs(stores):
    """One call: the text to present, the opening line, the time the round started and which
    sealed files still need a checker. No topic in any of it."""
    w, day = stores[40]
    w.forget_job()
    out = w.start(day)
    assert out["present"].startswith("Q1.") and out["prepared"]["present_block"] == "questions"
    last = dt.date.fromisoformat(out["last_session"]["date"])
    assert out["opening"] == "Today's round: 3 MCQs + 1 focused question + the case, about %d minutes. %s. " \
                             "Last saved session: %d %s." % (out["plan"]["estimated_minutes"], out["block"]["line"],
                                                             last.day, cme.MONTHS[last.month - 1])
    assert cme.parse_stamp(out["started_at"])
    assert out["prepared"]["unchecked"] == []          # both evidence files came with the prepared round
    plan = w.read_json("plan.json")
    labels = cme.bp_topics(w.read_ledger())
    for it in plan["items"]:
        if it["domain"] == out["block"]["theme"]:      # the theme is the one thing the opening line names
            continue
        for word in (it["topic"], labels[it["topic"]]["label"], cme.domain_name(w.read_ledger(), it["domain"])):
            assert word not in out["opening"]


def test_unchecked_names_the_sealed_files_without_an_evidence_file(stores, tmp_path):
    w0, day = stores[10]
    w = Work(tmp_path / "work")
    shutil.copytree(w0.store(), w.store())
    doc = w.read_json("store", "data", "prepared.json")
    inner = cme.unpack(doc["payload"])
    del inner["files"]["evidence_case.md"]
    doc["payload"] = cme.pack(inner)
    w.write(os.path.join("store", "data", "prepared.json"), doc)
    out = w.start(day)
    assert out["prepared"]["used"] is True and out["prepared"]["unchecked"] == ["sealed_case.md"]


def test_the_opening_line_of_a_new_block_and_of_a_round_written_now(work):
    work.init(today="2026-11-01")
    out = work.start("2026-11-02")
    assert out["prepared"]["used"] is False and "present" not in out and "unchecked" not in out["prepared"]
    assert out["block"]["starts"] is True
    assert out["opening"] == "Today's round: 3 MCQs + the case, about %d minutes. %s. New block: %s." % (
        out["plan"]["estimated_minutes"], out["block"]["line"], out["block"]["reason"].rstrip("."))
    # a one-off mix for this round is the mix the line gives
    work.forget_job()
    out = work.start("2026-11-02", "--mcqs", "1", "--no-case")
    assert out["opening"].startswith("Today's round: 1 MCQ, about ")


# ---------------------------------------------------------------- the protocol (SKILL.md, turn 1)

def turn_1():
    with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    return " ".join(text[text.index("### Turn 1."):text.index("### Turn 2.")].split())


def test_turn_1_sends_the_questions_before_any_reference_reading():
    text = turn_1()
    before, after = text.split("**Send the first message**")
    after = after[after.index("**Behind the scenes**"):]
    assert "no reference" in before and "One shell call" in before and "one parallel batch" in before
    # the guides for grading and publishing are read behind the scenes, after the message is out
    # the examiner's one brief (#77): neither the rulebook nor the analysis framework before grading
    # (#92: the brief in two files, grading and what the feedback says; publishing out of store.md)
    for name in ("grading.md", "feedback_guide.md", "publishing.md"):
        assert name not in before and "`%s`" % name in after, name
    for name in ("standards.md", "analysis_framework.md", "coding.md", "disputes.md", "state_schema.md"):
        assert name not in text, name
    # before the message, a reference is named only for the cases that are not a prepared round
    assert "only if a step fails or the store is not the page" in before
    # what the message is made of comes from the one `start` call
    for field in ("`opening`", "`present`", "`prepared.unchecked`"):
        assert field in text

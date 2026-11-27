"""The page file, `data/page.json` (issue #54): the one file the learner's page renders. The
engine writes it with every ledger, from the ledger, and it holds exactly what the page may
show. So the blinding of the page is tested here, in Python, on every example ledger: no open
gap (text or id), no due date, no topic not yet tested, nothing of the prepared round."""
import copy
import datetime as dt
import json
import os
import re

import pytest

import examples
from examples import LEDGERS, cme
from test_invariants import save, seed, write_round_files

ledgers = pytest.mark.parametrize("name", list(LEDGERS))
TOPIC_ID = re.compile(r"\b[A-Z]{2,6}-\d{2}\b")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NEVER_A_KEY = {"due", "gap", "gaps", "resolved", "drills", "prepared", "next_due", "blueprint", "reason", "history",
               "step", "errata", "pending_errata", "retest", "retests", "items", "config", "profile"}


def keys_of(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from keys_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys_of(v)


def assert_blind(page, st, prepared=None):
    """`page` (a page file) gives away nothing of what a coming round on ledger `st` will test."""
    text = json.dumps(page, ensure_ascii=False)
    for g in st.get("gaps") or []:
        assert g["gap"] not in text, "gap text: %s" % g["gap"]
        assert not g.get("id") or g["id"] not in text, "gap id %s" % g.get("id")
    assert not NEVER_A_KEY & set(keys_of(page)), NEVER_A_KEY & set(keys_of(page))
    # only topics already tested are named, by code or by label
    tested = {tid for tid, t in st["topics"].items() if t.get("last")}
    named = text
    for tid in tested:                  # a tested topic's own label may point at another topic ("see CARD-05")
        named = named.replace(json.dumps(st["topics"][tid].get("label"), ensure_ascii=False), '""')
    assert set(TOPIC_ID.findall(named)) <= tested, set(TOPIC_ID.findall(named)) - tested
    assert {t["id"] for t in page["topics"]} <= tested
    for tid, info in cme.bp_topics(st).items():
        if tid not in tested:
            assert json.dumps(info["label"], ensure_ascii=False) not in text, "untested topic: %s" % info["label"]
    # every date in the file is one the learner has lived or may know: a session, a last test, a
    # review, the last save, when the mix was set. A due date is none of these.
    shown = {s.get("date") for s in page["sessions"]} | {t.get("last") for t in st["topics"].values()}
    shown |= {r.get("date") for r in page["reviews"]} | {(st.get("review") or {}).get(k) for k in ("next_due", "period_start")}
    shown |= {st.get("updated"), str(st["config"].get("round_set_at"))[:10]}
    assert set(DATE.findall(text)) <= shown, set(DATE.findall(text)) - shown
    hidden_due = {t["due"] for t in st["topics"].values() if t.get("due")} - shown
    assert not hidden_due & set(DATE.findall(text))
    if prepared is not None:
        doc = cme.unpack(prepared["z"]) if "z" in prepared else prepared
        for name, body in (doc.get("files") or {}).items():
            for line in str(body).splitlines():
                assert len(line.strip()) < 12 or line.strip() not in text, "prepared round: %s" % name
    assert "SEALED" not in text and "prepared" not in text


def armed(st):
    """`st` with a marker in everything the page must not show: every due date moved to a day
    nothing else happens on, every gap named, a gap on a topic never tested, an active drill,
    the reason for the theme, errata waiting."""
    st = copy.deepcopy(st)
    for n, t in enumerate(st["topics"].values()):
        t["due"] = cme.iso(dt.date(2090, 1, 1) + dt.timedelta(days=n))
    for n, g in enumerate(st["gaps"]):
        g.update(id="G9%03d" % n, gap="MARKER-GAP-%d" % n)
    untested = next(tid for tid in sorted(cme.bp_topics(st)) if tid not in st["topics"])
    cme.ensure_topic(st, untested)
    st["topics"][untested]["due"] = "2091-02-03"
    st["gaps"].append({"id": "G9999", "topic": untested, "gap": "MARKER-GAP-UNTESTED", "source": ["self"]})
    st["drills"] = [{"code": "bias:MARKER-DRILL", "until": "2092-03-04"}]
    st["pending_errata"] = [{"topic": untested, "note": "MARKER-ERRATUM"}]
    theme = next(iter(st["blueprint"]))
    st["block"] = dict(st.get("block") or {"theme": theme, "round": 2, "length": 12}, reason="MARKER-REASON")
    return st, untested


# ---- blinding, on every example ledger ------------------------------------------------------------

@ledgers
def test_page_file_of_an_example_ledger_gives_nothing_away(name):
    st = examples.load_ledger(name)
    assert_blind(cme.page_doc(st), st)
    played = examples.play(name)["ledger"]                     # after one more round, with its new gaps
    assert_blind(cme.page_doc(played), played)


@ledgers
def test_page_file_never_holds_a_marked_gap_due_date_drill_or_reason(name):
    st, untested = armed(examples.load_ledger(name))
    text = json.dumps(cme.page_doc(st), ensure_ascii=False)
    assert "MARKER" not in text and "G9" not in text
    assert not re.search(r"\b209\d-", text)                    # no due date, of any topic
    assert untested not in text                                # a gap's topic that was never tested is not listed
    assert_blind(cme.page_doc(st), st)


@ledgers
def test_page_file_in_the_publish_set_is_blind_after_save_and_after_close(name, work):
    start = examples.load_ledger(name)
    day = examples.today_of(name)
    seed(work, start)
    prepared = None
    if os.path.exists(examples.prepared_path(name)):           # a round prepared ahead sits in the store
        with open(examples.prepared_path(name), encoding="utf-8") as fh:
            prepared = json.load(fh)
        work.write(os.path.join("store", "data", "prepared.json"), prepared)
    work.start(cme.iso(day), "--no-prepared")
    rnd = write_round_files(work, start, cme.plan_round(start, examples.plan_options(), day))
    saved = save(work, cme.iso(day))
    assert "data/page.json" in [f["as"] for f in saved["files"]]
    after_save = work.read_json("publish", "data", "state.json")
    page = work.read_json("publish", "data", "page.json")
    assert_blind(page, after_save, prepared)
    assert page["gen"] == after_save["gen"] and page["sessions"][0]["id"] == saved["session_id"]
    assert page["sessions"][0]["reflected"] is False

    work.write("reflection.json", examples.reflection_for(rnd))
    work.write("B.md", "Example reflection, verbatim")
    work.run("--today", cme.iso(day + dt.timedelta(days=1)), "close", "--work", work.path)
    after_close = work.read_json("publish", "data", "state.json")
    page = work.read_json("publish", "data", "page.json")
    assert after_close["gaps"] or name == "fresh", "the scripted round leaves an open gap to hide"
    assert_blind(page, after_close, prepared)
    assert page["sessions"][0]["reflected"] is True
    # and what it does show is the ledger's: every tested topic, with its mastery and last test
    assert {t["id"]: (t["mastery"], t["last"]) for t in page["topics"]} == {
        tid: (t.get("mastery"), t.get("last")) for tid, t in after_close["topics"].items() if t.get("last")}


# ---- its shape ------------------------------------------------------------------------------------

def test_page_file_has_the_documented_shape_and_empty_slots_for_what_is_to_come(work):
    work.init(config={"mcqs": 2, "focused": 1, "session_minutes": 30}, profile={"specialty": "Geriatrics"})
    page = work.read_json("store", "data", "page.json")
    assert list(page) == ["schema", "page_version", "gen", "updated", "who", "totals", "sessions", "topics", "round",
                          "block", "reviews", "next_review", "library", "positions", "settings"]
    assert page["schema"] == cme.PAGE_SCHEMA and page["page_version"] == cme.PAGE_VERSION and page["gen"] == 1
    assert page["sessions"] == [] and page["topics"] == [] and page["reviews"] == [] and page["block"] is None
    assert page["library"] == [] and page["positions"] == []
    assert page["totals"] == {"topics": 0, "mean_mastery": None, "since": "2026-11-01", "sessions": 0, "mean_score": None}
    st = work.read_ledger()
    assert page["round"] == {"mix": {"mcqs": 2, "focused": 1, "case": True}, "set_at": st["config"]["round_set_at"],
                             "minutes": 45, "minutes_per": {"mcq": 5, "focused": 10, "case": 25},
                             "limits": {"mcqs": [0, 10], "focused": [0, 6]}, "timed_rounds": 0,
                             "time_hint": None}
    assert page["next_review"] == st["review"]["next_due"]
    s = page["settings"]
    assert (s["session_length"], s["per_week"], s["region"], s["units"]) == (30, 3, "Iceland/Europe", {"labs": "SI", "gases": "mmHg"})
    assert page["who"]["specialty"] == "Geriatrics"
    # empty until the learner has written them: level and aim (#55); reading and listening are `library` (#51)
    assert s["level"] is None and s["aim"] is None and "reading" not in s and "listening" not in s


def test_estimates_are_the_engines_with_the_new_defaults(work):
    assert cme.MINUTES_PER == {"mcq": 5, "focused": 10, "unfolding": 25, "discriminate": 15}
    assert cme.round_minutes(3, 0, 1) == 40 and cme.round_minutes(2, 1, 0) == 20
    assert cme.round_minutes(0, 0, 1, "discriminate") == 15
    work.init()
    out = work.start("2026-11-02")
    assert out["plan"]["estimated_minutes"] == 40 and "about 40 minutes" in out["opening"]
    # a session too short for an unfolding case gets the one-step case, in the plan and on the page
    st = work.read_ledger()
    st["config"]["session_minutes"] = 10
    page = cme.page_doc(st)
    assert page["round"]["minutes_per"]["case"] == 15 and page["round"]["minutes"] == 30
    assert cme.plan_round(st, examples.plan_options(), dt.date(2026, 11, 2))["estimated_minutes"] == 30


@pytest.mark.parametrize("mcqs, focused", [(10, 6), (0, 6), (10, 0)])
def test_the_largest_rounds_still_plan_with_the_longer_estimates(mcqs, focused):
    """No budget cuts a round to the session length: the mix the learner set is the mix planned,
    and the estimate says what it costs."""
    st = examples.load_ledger("mid_curriculum")
    st["config"].update(mcqs=mcqs, focused=focused, session_minutes=20)
    plan = cme.plan_round(st, examples.plan_options(), examples.today_of("mid_curriculum"))
    assert (plan["counts"]["mcqs"], plan["counts"]["focused"], plan["counts"]["case"]) == (mcqs, focused, 1)
    assert plan["estimated_minutes"] == 5 * mcqs + 10 * focused + 25 == cme.page_doc(st)["round"]["minutes"]


# ---- written with every ledger ----------------------------------------------------------------------

def test_a_settings_change_and_a_theme_change_reach_the_page_file(work):
    work.init()
    work.open(today="2026-11-02")
    out = work.run_json("--today", "2026-11-02", "settings", "--work", work.path, "--config",
                        '{"session_minutes": 45, "mcqs": 5, "guideline_region": "UK"}')
    assert "data/page.json" in [f["as"] for f in out["files"]] and "data/index.json" not in [f["as"] for f in out["files"]]
    page = work.read_json("publish", "data", "page.json")
    assert page["settings"]["session_length"] == 45 and page["settings"]["region"] == "UK"
    assert page["round"]["mix"]["mcqs"] == 5 and page["round"]["minutes"] == 50
    assert page["round"]["set_at"] == work.read_json("publish", "data", "state.json")["config"]["round_set_at"]
    out = work.run_json("--today", "2026-11-02", "theme", "--work", work.path, "--set", "CARD")
    page = work.read_json("publish", "data", "page.json")
    assert page["block"] == {"theme": "CARD", "name": page["block"]["name"], "done": 0, "length": 12}
    assert page["gen"] == work.read_json("publish", "data", "state.json")["gen"]


# ---- the lists it carries, and stores from before it ----------------------------------------------

OLD_INDEX = {"schema": 1, "gen": 1, "sessions": [
    {"id": "S0000", "date": "2025-01-05", "title": "Kept only by the index", "summary": "s", "tags": ["old"],
     "topics": ["GEN-11"], "score": 3.0, "format": "unfolding", "drill": None, "reflected": True}],
    "reviews": [{"date": "2025-02-01", "title": "An old review", "headline": "h"}]}


def old_store(work):
    """A store last saved before the page file: an index, no page file."""
    work.init()
    os.remove(work.store("data", "page.json"))
    work.write(os.path.join("store", "data", "index.json"), OLD_INDEX)


def test_a_store_with_only_the_old_index_gets_its_page_file_at_the_next_save(work):
    old_store(work)
    opened = work.open(today="2026-11-02")
    assert opened["store_files"] == ["data/state.json", "data/index.json", "data/prepared.json", "index.html"]
    assert work.read_json("publish.json")["files"] == []                # opening writes nothing
    saved = work.save_round("2026-11-02")
    names = [f["as"] for f in saved["files"]]
    assert "data/page.json" in names and "data/index.json" not in names   # the index is not written any more
    page = work.read_json("publish", "data", "page.json")
    assert [s["id"] for s in page["sessions"]] == ["S0001", "S0000"]     # newest first; the index's entry is carried
    assert page["sessions"][1]["title"] == "Kept only by the index"
    assert page["reviews"] == OLD_INDEX["reviews"]
    # from then on the page file carries them itself
    work.publish()
    os.remove(work.store("data", "index.json"))
    work.forget_job()
    work.open(today="2026-11-03")
    work.close_round("2026-11-03")
    page = work.read_json("publish", "data", "page.json")
    assert [s["id"] for s in page["sessions"]] == ["S0001", "S0000"] and page["reviews"] == OLD_INDEX["reviews"]


def test_a_store_with_neither_file_is_rebuilt_from_the_ledger(work):
    work.init()
    work.save_round("2026-11-02")
    work.publish()
    work.forget_job()
    os.remove(work.store("data", "page.json"))
    work.open(today="2026-11-03")
    work.close_round("2026-11-03")
    page = work.read_json("publish", "data", "page.json")
    assert [(s["id"], s["title"], s["reflected"]) for s in page["sessions"]] == [("S0001", "t", True)]


def test_sessions_the_ledger_has_dropped_stay_in_the_page_file(work):
    work.init()
    work.save_round("2026-11-02")
    work.publish()
    st = work.read_ledger()
    entry = dict(st["sessions"][0], _dropped=True)
    st["sessions"], st["unreflected"] = [], None             # as after many periods: the ledger no longer lists it
    work.write_ledger(st)
    work.forget_job()
    work.open(today="2026-11-20")
    work.run_json("--today", "2026-11-20", "settings", "--work", work.path, "--config", '{"reminders": true}')
    page = work.read_json("publish", "data", "page.json")
    assert [s["id"] for s in page["sessions"]] == [entry["id"]] and page["sessions"][0]["title"] == "t"
    assert page["totals"]["sessions"] == 0 and page["settings"]["reminders"] is True


@pytest.mark.parametrize("command", ["rebuild-page", "reindex"])
def test_rebuild_page_makes_the_page_file_from_the_session_files_and_the_ledger(work, command):
    work.init()
    work.save_round("2026-11-02")
    work.close_round("2026-11-03")
    work.publish()
    wanted = work.read_json("store", "data", "page.json")
    os.remove(work.store("data", "page.json"))
    doc = work.read_json("store", "data", "sessions", "S0001.json")
    out = work.run_json(command, work.store())
    assert out["files"] == [{"as": "data/page.json", "path": work.store("data", "page.json")}] and out["sessions"] == 1
    rebuilt = work.read_json("store", "data", "page.json")
    assert rebuilt == wanted and rebuilt["sessions"][0]["summary"] == doc["summary"]
    assert not os.path.exists(work.store("data", "index.json"))
    assert_blind(rebuilt, work.read_ledger())


def test_rebuild_page_needs_the_ledger(work):
    os.makedirs(work.store("data"))
    r = work.run("rebuild-page", work.store(), ok=False)
    assert r.returncode != 0 and "no ledger" in (r.stdout + r.stderr)


def test_a_damaged_page_file_costs_nothing_the_ledger_knows(work):
    work.init()
    work.save_round("2026-11-02")
    work.publish()
    work.forget_job()
    with open(work.store("data", "page.json"), "w", encoding="utf-8") as fh:
        fh.write("not a page file")
    work.open(today="2026-11-03")
    work.close_round("2026-11-03")
    assert [s["id"] for s in work.read_json("publish", "data", "page.json")["sessions"]] == ["S0001"]

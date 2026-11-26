"""Issue #51: reading and listening on the page. The examiner lists the feedback's further-reading
pointers in round.json as `reading`, beside the `listening` picks of issue #50; `save` writes both
into the session document; the page file carries them as `library` (newest first, capped, carried
on like the session list), and the page lists them under "Reading & listening" with a done mark
kept in the viewer's own browser. The library holds only what saved sessions hold, so it is as
blind as the rest of the page file."""
import copy
import json
import os

import pytest

from conftest import ROUND
from examples import cme
from test_listening import LINK, PICKS
from test_page import PAGE, STATE, SECRETS, page_text, render, store_with
from test_page_file import assert_blind

READING = [
    {"topic": "GEN-11", "title": "Example guideline 2024", "link": "https://example.org/guideline#s9",
     "section": "section 9 and its table", "minutes": 8, "why": "the thresholds you were unsure of"},
    {"topic": "HEME-01", "title": "Example review", "link": "https://example.org/review",
     "section": "Management", "minutes": "12", "why": "background for the question you guessed"},
]


def session(work, sid="S0001"):
    return work.read_json("publish", "data", "sessions", sid + ".json")


def about_reading(saved):
    return [w for w in saved["warnings"] if "reading" in w]


def library(work):
    return work.read_json("publish", "data", "page.json")["library"]


# ---------------------------------------------------------------- the pointers: from round.json into the session document

def test_save_writes_the_pointers_into_the_session_document_and_not_into_the_ledger(work):
    work.init()
    saved = work.save_round("2026-11-02", dict(ROUND, reading=READING))
    assert about_reading(saved) == [] and saved["reading"] == 2
    assert session(work)["reading"] == [READING[0], dict(READING[1], minutes=12)]
    assert "example.org" not in json.dumps(work.read_json("publish", "data", "state.json"))
    assert "reading" not in work.read_json("record.json")
    assert work.save_round("2026-11-02", dict(ROUND, reading=READING))["reading"] == 2      # saving again: the same
    work.close_round("2026-11-03")
    assert session(work)["reading"] == [READING[0], dict(READING[1], minutes=12)]


def test_a_pointer_that_is_not_complete_is_left_out_with_a_warning(work):
    work.init()
    pointers = [dict(READING[0], link="example.org/guideline"),
                dict(READING[0], topic="CARD-99"),
                dict(READING[0], section=" ", minutes=0),
                "ESC 2023, section 9",
                READING[0], READING[1],
                dict(READING[0], title="A third pointer")]
    saved = work.save_round("2026-11-02", dict(ROUND, reading=pointers))
    assert [p["title"] for p in session(work)["reading"]] == ["Example guideline 2024", "Example review"]
    warnings = about_reading(saved)
    assert saved["reading"] == 2 and len(warnings) == 5
    assert warnings[0].startswith("reading pointer 1: left out of the session document; correct link")
    assert "topic (one of this round's:" in warnings[1]
    assert warnings[2].endswith("correct section, minutes")
    assert warnings[3] == "reading pointer 4: not an object; left out"
    assert warnings[4] == "reading pointer 7: left out of the session document; a round has at most 2"


def test_a_round_without_the_list_has_none_and_an_empty_list_is_kept(work):
    work.init()
    assert "reading" not in work.save_round("2026-11-02")
    assert "reading" not in session(work) and library(work) == []
    assert work.save_round("2026-11-02", dict(ROUND, reading=[]))["reading"] == 0
    assert session(work)["reading"] == []
    saved = work.save_round("2026-11-02", dict(ROUND, reading="ESC 2023"))
    assert "reading" not in saved and "round 'reading' must be a list" in about_reading(saved)[0]


# ---------------------------------------------------------------- the page file: library

def test_the_page_file_lists_reading_and_listening_of_the_saved_session(work):
    work.init()
    work.save_round("2026-11-02", dict(ROUND, reading=READING, listening=PICKS))
    st = work.read_json("publish", "data", "state.json")
    label = lambda tid: st["topics"][tid]["label"]
    assert library(work) == [
        {"session": "S0001", "date": "2026-11-02", "kind": "reading", "topic": "GEN-11", "label": label("GEN-11"),
         "title": "Example guideline 2024", "link": "https://example.org/guideline#s9", "minutes": 8,
         "section": "section 9 and its table"},
        {"session": "S0001", "date": "2026-11-02", "kind": "reading", "topic": "HEME-01", "label": label("HEME-01"),
         "title": "Example review", "link": "https://example.org/review", "minutes": 12, "section": "Management"},
        {"session": "S0001", "date": "2026-11-02", "kind": "listening", "topic": "GEN-11", "label": label("GEN-11"),
         "title": "Episode one", "link": LINK, "minutes": 42, "show": "Example Show"},
        {"session": "S0001", "date": "2026-11-02", "kind": "listening", "topic": "PULM-04", "label": label("PULM-04"),
         "title": "Episode two", "link": PICKS[1]["link"].split("?")[0], "minutes": 31, "show": "Other Show"}]
    assert all(label(t) for t in ("GEN-11", "HEME-01", "PULM-04"))
    # saving again with one pointer fewer replaces the session's entries; the close keeps them
    work.save_round("2026-11-02", dict(ROUND, reading=READING[:1], listening=PICKS))
    assert [e["title"] for e in library(work)] == ["Example guideline 2024", "Episode one", "Episode two"]
    work.close_round("2026-11-03")
    assert [e["title"] for e in library(work)] == ["Example guideline 2024", "Episode one", "Episode two"]


def test_the_library_is_carried_forward_newest_session_first(work):
    work.init()
    work.save_round("2026-11-02", dict(ROUND, reading=READING, listening=PICKS))
    work.close_round("2026-11-03")
    work.publish()
    work.forget_job()
    # a second round in a later job: the page file read from the store supplies the first round's entries
    second = dict(ROUND, log_id="S0002", reading=[dict(READING[0], title="Second round reading")])
    work.save_round("2026-11-08", second)
    assert [(e["session"], e["title"]) for e in library(work)] == [
        ("S0002", "Second round reading"), ("S0001", "Example guideline 2024"), ("S0001", "Example review"),
        ("S0001", "Episode one"), ("S0001", "Episode two")]
    work.close_round("2026-11-09")
    work.publish()
    # the ledger no longer lists the sessions (as after many periods), and a settings change writes the page file
    st = work.read_ledger()
    st["sessions"], st["unreflected"] = [], None
    work.write_ledger(st)
    work.forget_job()
    work.open(today="2026-11-20")
    work.run_json("--today", "2026-11-20", "settings", "--work", work.path, "--config", '{"reminders": true}')
    assert [e["session"] for e in library(work)] == ["S0002"] + ["S0001"] * 4


def test_the_library_keeps_the_last_hundred(work):
    work.init()
    st = work.read_ledger()
    lists = {"sessions": [], "reviews": [], "library": [
        {"session": "S%04d" % n, "date": "2026-%02d-%02d" % (1 + n // 28, 1 + n % 28), "kind": "reading",
         "topic": "GEN-11", "label": None, "title": "T%d" % n, "link": "https://example.org/%d" % n, "minutes": 5,
         "section": "s"} for n in range(1, 131)]}
    page = cme.page_doc(st, copy.deepcopy(lists))
    assert len(page["library"]) == cme.PAGE_LIBRARY_MAX == 100
    assert [e["title"] for e in page["library"][:2]] == ["T130", "T129"] and page["library"][-1]["title"] == "T31"
    # and a page file written that way is read back as it is, less anything that is not an entry
    path = work.p("page.json")
    page["library"] += [{"kind": "video", "session": "S0001", "title": "x", "link": "y"}, "text", {"kind": "reading"}]
    work.write("page.json", page)
    assert len(cme.page_lists(path)["library"]) == 100


def test_rebuild_page_reads_the_library_from_the_session_files(work):
    work.init()
    work.save_round("2026-11-02", dict(ROUND, reading=READING, listening=PICKS))
    work.close_round("2026-11-03")
    work.publish()
    wanted = work.read_json("store", "data", "page.json")
    os.remove(work.store("data", "page.json"))
    work.run_json("rebuild-page", work.store())
    assert work.read_json("store", "data", "page.json") == wanted and len(wanted["library"]) == 4


def test_a_page_file_from_before_the_library_is_carried_on_without_one(work):
    work.init()
    page = work.read_json("store", "data", "page.json")
    del page["library"]                                    # as a 5.3 engine wrote it
    work.write(os.path.join("store", "data", "page.json"), page)
    work.save_round("2026-11-02", dict(ROUND, reading=READING))
    assert [e["title"] for e in library(work)] == ["Example guideline 2024", "Example review"]


# ---------------------------------------------------------------- blinding

def test_the_library_gives_nothing_away_about_a_coming_round(work):
    """The reasons are written after the round and may name the gap the learner showed, which
    then stays open: they stay in the session document. The library names only what a saved
    session holds: its topics (tested by then), titles and links."""
    work.init()
    rnd = dict(ROUND, gaps=[{"topic": "GEN-11", "gap": "MARKER-GAP when to start", "source": "graded"}],
               reading=[dict(READING[0], why="MARKER-GAP when to start: the step you missed")],
               listening=[dict(PICKS[0], why="MARKER-GAP when to start, discussed at length")])
    work.save_round("2026-11-02", rnd)
    for step in ("save", "close"):
        if step == "close":
            work.close_round("2026-11-03")
        st = work.read_json("publish", "data", "state.json")
        page = work.read_json("publish", "data", "page.json")
        assert any(g["gap"].startswith("MARKER-GAP when to start") for g in st["gaps"])   # open, and to be retested
        assert len(page["library"]) == 2 and "MARKER" not in json.dumps(page) and "why" not in json.dumps(page["library"])
        assert_blind(page, st)
        tested = {tid for tid, t in st["topics"].items() if t.get("last")}
        assert {e["topic"] for e in page["library"]} <= tested
        assert {e["session"] for e in page["library"]} <= {s["id"] for s in page["sessions"]}
    assert "MARKER-GAP" in session(work)["reading"][0]["why"]                         # where the learner reads it


def test_nothing_of_a_round_not_yet_saved_reaches_the_library(work):
    """Only `save` feeds the library: a plan, a round being played and its round.json do not."""
    work.init()
    work.start("2026-11-02")
    work.write("round.json", dict(ROUND, reading=READING, listening=PICKS))
    work.run_json("--today", "2026-11-02", "settings", "--work", work.path, "--config", '{"reminders": true}')
    page = work.read_json("publish", "data", "page.json")
    assert page["library"] == [] and "example.org" not in json.dumps(page)


def test_a_carried_entry_is_labelled_only_from_tested_topics():
    st = copy.deepcopy(STATE)
    entry = {"session": "S0001", "date": "2020-03-04", "kind": "reading", "topic": "DDD-04", "label": None,
             "title": "T", "link": "https://example.org/t", "minutes": 5, "section": "s"}
    page = cme.page_doc(st, {"sessions": [], "reviews": [], "library": [entry, dict(entry, topic="AAA-01")]})
    assert [e["label"] for e in page["library"]] == [None, "Alpha topic"]
    assert "UNTESTED-GAP-TOPIC" not in json.dumps(page)


# ---------------------------------------------------------------- the page: Reading & listening

LIBRARY = [
    {"session": "S0002", "date": "2020-03-05", "kind": "reading", "topic": "BBB-02", "label": "Beta topic",
     "title": "READ-TITLE <b>", "link": "https://example.org/read?a=1&b=2", "minutes": 8, "section": "SECTION-NINE"},
    {"session": "S0002", "date": "2020-03-05", "kind": "listening", "topic": "BBB-02", "label": "Beta topic",
     "title": "LISTEN-TITLE", "link": LINK, "minutes": 42, "show": "SHOW-NAME"},
    {"session": "S0001", "date": "2020-03-04", "kind": "reading", "topic": "AAA-01", "label": "Alpha topic",
     "title": "OLDER-TITLE", "link": "javascript:alert(1)", "minutes": 5, "section": "s"},
]
KEY = "S0002|reading|https://example.org/read?a=1&b=2"


def page_store(tmp_path, lib=LIBRARY):
    page = cme.page_doc(copy.deepcopy(STATE))
    if lib is None:
        del page["library"]
    else:
        page["library"] = lib
    return store_with(tmp_path / "store", page=page)


def test_template_has_the_view_and_keeps_done_marks_out_of_the_store():
    html = page_text()
    assert 'id="tab-library"' in html and 'id="v-library"' in html and "Reading &amp; listening" in html
    assert 'target="_blank" rel="noopener noreferrer"' in html
    # browser storage is used for the done marks only, and every use is guarded
    uses = [line for line in html.splitlines() if "localStorage" in line]
    assert len(uses) == 2 and all("try {" in line and "catch (e)" in line for line in uses)
    assert "sessionStorage" not in html


def test_the_page_lists_reading_and_listening_by_session_and_topic(tmp_path):
    out = render(page_store(tmp_path))
    view = out["ids"]["lib-list"] + out["text"]
    assert out["fetched"] == ["data/page.json"]
    for shown in ("READ-TITLE &lt;b&gt;", "LISTEN-TITLE", "OLDER-TITLE", "SECTION-NINE", "SHOW-NAME", "Beta topic",
                  "Alpha topic", "about 8 min", "about 42 min", "OTHER-PAST-SESSION", "PAST-SESSION-TITLE"):
        assert shown in view, shown
    assert '<a href="https://example.org/read?a=1&amp;b=2" target="_blank" rel="noopener noreferrer">' in view
    assert '<a href="%s" target="_blank" rel="noopener noreferrer">' % LINK in view
    assert "javascript:" not in view                           # only web links become links
    assert view.index("OTHER-PAST-SESSION") < view.index("PAST-SESSION-TITLE")       # S0002 before S0001
    assert out["ids"]["c-library"] == "3" and out["ids"]["lib-count"] == "3 of 3 to do"
    assert [out["ids"]["lib-done-%d" % n] for n in range(3)] == ["Mark done"] * 3
    for secret in SECRETS:
        assert secret not in out["text"]


def test_done_is_toggled_and_kept_in_the_browser_only(tmp_path):
    store = page_store(tmp_path)
    out = render(store, "--db", "--click", "lib-done-0")
    assert out["ids"]["lib-done-0"] == "✓ Done" and out["ids"]["lib-done-1"] == "Mark done"
    assert out["ids"]["c-library"] == "2" and out["ids"]["lib-count"] == "2 of 3 to do"
    assert json.loads(out["storage"]["cme-library-done"]) == {KEY: 1}
    assert out["db"] == [] and out["fetched"] == ["data/page.json"]                  # nothing written to the store
    # the next visit finds it done; a second click takes the mark away again
    kept = tmp_path / "storage.json"
    kept.write_text(json.dumps(out["storage"]), encoding="utf-8")
    again = render(store, "--storage", str(kept))
    assert again["ids"]["lib-done-0"] == "✓ Done" and again["ids"]["lib-count"] == "2 of 3 to do"
    undone = render(store, "--storage", str(kept), "--click", "lib-done-0,lib-done-1,lib-done-2")
    assert [undone["ids"]["lib-done-%d" % n] for n in range(3)] == ["Mark done", "✓ Done", "✓ Done"]
    assert set(json.loads(undone["storage"]["cme-library-done"])) == {"S0002|listening|" + LINK, "S0001|reading|javascript:alert(1)"}
    alldone = render(store, "--click", "lib-done-0,lib-done-1,lib-done-2")
    assert alldone["ids"]["lib-count"] == "All 3 done" and alldone["ids"]["c-library"] == ""


@pytest.mark.parametrize("option", ["--no-storage", "--storage"])
def test_a_browser_without_storage_or_with_a_damaged_mark_still_shows_the_list(tmp_path, option):
    store = page_store(tmp_path)
    options = [option]
    if option == "--storage":
        bad = tmp_path / "storage.json"
        bad.write_text(json.dumps({"cme-library-done": "{not json"}), encoding="utf-8")
        options.append(str(bad))
    out = render(store, *options, "--click", "lib-done-1")
    assert "LISTEN-TITLE" in out["text"]
    assert out["ids"]["lib-done-1"] == "✓ Done" and out["ids"]["lib-count"] == "2 of 3 to do"      # for this visit


def test_a_store_without_the_field_shows_an_empty_view_with_one_line(tmp_path):
    out = render(page_store(tmp_path, lib=None))
    assert "reading and listening from your rounds appear here after your next round" in out["ids"]["lib-list"]
    assert out["ids"]["c-library"] == "" and "PAST-SESSION-TITLE" in out["text"]
    empty = render(page_store(tmp_path / "empty", lib=[]))
    assert "No reading or listening yet." in empty["ids"]["lib-list"]


def test_a_page_from_the_last_version_is_replaced_with_the_first_save(work):
    """The update path: a store whose page is 5.3.0 gets the new page in the same publish set as
    the page file that carries the library."""
    work.init()
    work.write(os.path.join("store", "index.html"), '<meta name="cme-page-version" content="5.3.0">old page')
    saved = work.save_round("2026-11-02", dict(ROUND, reading=READING))
    names = [f["as"] for f in saved["files"]]
    assert cme.PAGE_VERSION == "5.4.0" and saved["page_upgraded"] == {"from": "5.3.0", "to": "5.4.0"}
    assert names.index("data/page.json") < names.index("index.html") < names.index("data/state.json")
    with open(work.pub("index.html"), encoding="utf-8") as fh:
        assert fh.read() == page_text() and PAGE.endswith("page.html")
    assert len(library(work)) == 2
    # once published, the next job leaves the page alone
    work.close_round("2026-11-03")
    work.publish()
    work.forget_job()
    work.open(today="2026-11-20")
    later = work.run_json("--today", "2026-11-20", "settings", "--work", work.path, "--config", '{"reminders": true}')
    assert "index.html" not in [f["as"] for f in later["files"]] and "page_upgraded" not in later

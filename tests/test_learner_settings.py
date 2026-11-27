"""Where you are and where you're aiming (issue #55): the learner's own two paragraphs, which
the author pitches to, with display labels derived by the assistant. Old ledgers fold `role`,
`goals` and `notes` into them word for word; the page updates them through cme/prefs, which
sets the prepared round aside and clears the labels; labels alone change nothing in a round.
Also the default mix of a new learner and the onboarding table of time answers."""
import copy
import json
import os
import re
import shutil
import urllib.parse

import pytest

from conftest import SKILL
from examples import cme
from test_finish_prepare import DAY, Next
from test_page import PAGE, STATE, node, render, store_with

NEXT_DAY = "2026-11-03"
LATER = "2099-01-02T21:40:12.512Z"       # a time on the page later than the setup of these tests (which is dated now)
JOURNEY = ("Consultant in general internal medicine for twelve years; I run the acute take alone and\n"
           "supervise residents. Comfortable with most inpatient decisions — less so with newer oncology drugs.")
AIM = "Keep current across internal medicine; make subspecialty-level calls when no one is around to ask."
NEW_JOURNEY = "Second-year resident in internal medicine. I still check most management decisions with my senior."
NEW_AIM = "Pass the European internal medicine exam next spring."


def ref(name):
    with open(os.path.join(SKILL, "references", name), encoding="utf-8") as fh:
        return fh.read()


def prefs(journey=None, aim=None, updated=LATER, **more):
    doc = dict(more)
    if journey is not None:
        doc["journey"] = {"text": journey, "updated": updated}
    if aim is not None:
        doc["aim"] = {"text": aim, "updated": updated}
    return json.dumps(doc)


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    """A store with the learner's paragraphs, their labels and a round prepared for them."""
    w = Next(tmp_path_factory.mktemp("prepared"))
    w.init(today=DAY, profile={"journey": JOURNEY, "aim": AIM, "journey_label": "senior attending",
                               "aim_tags": ["keep up to date", "specialist-level decisions outside own specialty"]})
    w.open(today=DAY)
    w.run("--today", DAY, "prepare", "--work", w.path)
    from examples import sealed_files
    for name, text in sealed_files(w.read_ledger(), w.read_json("next", "plan.json")).items():
        w.write(os.path.join("next", name), text)
    w.check().finish()
    w.publish()
    w.forget_job()
    return w.path


@pytest.fixture
def w(template, tmp_path):
    path = str(tmp_path / "work")
    shutil.copytree(template, path)
    return Next(path)


def settings(w, *args):
    if not os.path.exists(w.p("work.json")):
        w.open(today=DAY)
    return w.run_json("--today", DAY, "settings", "--work", w.path, *args)


def names(out):
    return [f["as"] for f in out["files"]]


# ---------------------------------------------------------------- setup

def test_init_stores_the_paragraphs_and_labels_and_the_plan_carries_the_paragraphs_only(w):
    prof = w.read_ledger()["profile"]
    assert prof["journey"] == JOURNEY and prof["aim"] == AIM
    assert prof["journey_label"] == "senior attending" and prof["journey_set_at"] and prof["aim_set_at"]
    assert "role" not in prof
    r = w.start(NEXT_DAY)
    assert r["prepared"]["used"] is True and r["labels_needed"] is None
    plan = w.read_json("plan.json")
    assert plan["profile"]["journey"] == JOURNEY and plan["profile"]["aim"] == AIM
    # labels are for display: nothing of them reaches whoever writes the items
    assert "journey_label" not in plan["profile"] and "aim_tags" not in plan["profile"]
    assert "senior attending" not in json.dumps(plan) and "role" not in plan["profile"]


def test_init_without_labels_asks_the_assistant_for_them(work):
    out = work.run_json("--today", DAY, "init", "--work", work.path, "--blueprint",
                        os.path.join(SKILL, "templates", "blueprint.json"),
                        "--profile", json.dumps({"journey": JOURNEY, "aim": AIM}))
    need = out["labels_needed"]
    assert need["journey_label"] == {"from": JOURNEY, "paragraph": "where you are", "choose": "one of",
                                     "labels": list(cme.STAGE_LABELS)}
    assert need["aim_tags"]["from"] == AIM and need["aim_tags"]["labels"] == list(cme.AIM_TAGS)
    assert cme.STAGE_LABELS == ("medical student", "intern", "resident", "fellow", "attending", "senior attending")
    assert cme.AIM_TAGS == ("exam", "independent practice", "specialist-level decisions outside own specialty",
                            "keep up to date", "teach")


@pytest.mark.parametrize("profile,message", [
    ({"journey_label": "registrar"}, "journey_label must be one of"),
    ({"aim_tags": ["win"]}, "aim_tags must be a list of"),
    ({"aim_tags": "exam"}, "aim_tags must be a list of"),
    ({"journey": ["a", "b"]}, "journey (where you are) must be text"),
])
def test_labels_come_from_the_fixed_lists_and_paragraphs_are_text(w, profile, message):
    w.open(today=DAY)
    r = w.run("settings", "--work", w.path, "--profile", json.dumps(profile), ok=False)
    assert r.returncode == 2 and message in r.stdout + r.stderr
    assert not os.path.exists(w.pub("data", "state.json"))


# ---------------------------------------------------------------- migration of older ledgers

OLD_NOTES = ("Sérfræðingur í lyflækningum í 15 ár; pitch at senior consultant level — skip the basics,\n"
             "test the decisions a subspecialist would make.  Prefers SI units.")
OLD_GOALS = ["Stay sharp outside my own subspecialty", "be able to teach the residents the evidence"]


def old_ledger(w, **profile):
    st = w.read_ledger()
    for k in ("journey", "aim", "journey_label", "aim_tags", "journey_set_at", "aim_set_at"):
        st["profile"].pop(k, None)
    st["profile"].update(profile)
    w.write_ledger(st)
    return st


def test_an_old_ledger_folds_role_goals_and_notes_into_the_paragraphs_word_for_word(w):
    old = old_ledger(w, role="Attending physician", goals=OLD_GOALS, notes=OLD_NOTES)
    r = w.start(NEXT_DAY)
    # the same words reach the author, so the round prepared before the fold is still used
    assert r["prepared"]["used"] is True
    w.forget_job()
    out = w.start(NEXT_DAY, "--no-prepared")
    profile = w.read_json("plan.json")["profile"]
    assert profile["journey"] == "Attending physician\n\n" + OLD_NOTES.strip()
    assert OLD_NOTES in profile["journey"]                                  # verbatim, inner spacing and all
    assert profile["aim"] == "\n".join(OLD_GOALS)
    assert "role" not in profile and "notes" not in profile                # no longer read for the pitch
    # a role that names a stage gives the display label; the goal tags are left to the assistant
    assert set(out["labels_needed"]) == {"aim_tags"} and out["labels_needed"]["aim_tags"]["from"] == "\n".join(OLD_GOALS)
    saved = settings(w, "--profile", json.dumps({"aim_tags": ["keep up to date", "teach"]}))
    assert saved["prepared"]["kept"] is True and "labels_needed" not in saved
    prof = w.read_json("publish", "data", "state.json")["profile"]
    assert prof["journey"] == "Attending physician\n\n" + OLD_NOTES.strip() and prof["journey_label"] == "attending"
    assert prof["aim_tags"] == ["keep up to date", "teach"]
    # the old fields stay as they were, for history
    assert (prof["role"], prof["goals"], prof["notes"]) == (old["profile"]["role"], OLD_GOALS, OLD_NOTES)
    page = w.read_json("publish", "data", "page.json")["settings"]
    assert page["level"] == {"label": "attending", "text": prof["journey"]}
    assert page["aim"] == {"tags": ["keep up to date", "teach"], "text": "\n".join(OLD_GOALS)}


def test_the_assistant_can_set_a_label_the_role_did_not_give(w):
    """The owner's ledger: his own paragraph kept as it is, the label set to senior attending."""
    old_ledger(w, role=None, goals=[], notes=OLD_NOTES)
    w.open(today=DAY)
    out = settings(w, "--profile", json.dumps({"journey_label": "senior attending"}))
    assert out["prepared"]["kept"] is True
    prof = w.read_json("publish", "data", "state.json")["profile"]
    assert prof["journey"] == OLD_NOTES.strip() and prof["journey_label"] == "senior attending"
    assert not prof.get("aim")


@pytest.mark.parametrize("role,label", [
    ("Medical student, final year", "medical student"), ("intern", "intern"), ("Internal medicine resident", "resident"),
    ("Senior registrar", "resident"), ("Cardiology fellow", "fellow"), ("Hospitalist attending", "attending"),
    ("consultant", "attending"), ("Senior consultant", "senior attending"), ("Internist", "attending"),
    ("nurse practitioner", None),
])
def test_stage_label_read_off_an_old_role(role, label):
    st = {"profile": {"role": role}}
    cme.migrate_profile(st)
    assert st["profile"]["journey"] == role and st["profile"]["journey_label"] == label
    assert label is None or label in cme.STAGE_LABELS


def test_migration_leaves_paragraphs_that_exist_alone_and_does_nothing_twice():
    st = {"profile": {"role": "consultant", "goals": ["x"], "notes": "n", "journey": JOURNEY, "aim": ""}}
    cme.migrate_profile(st)
    assert st["profile"]["journey"] == JOURNEY and "journey_label" not in st["profile"]
    assert st["profile"]["aim"] == "x"
    again = json.loads(json.dumps(st))
    cme.migrate_profile(again)
    assert again == st
    empty = {"profile": {"role": None, "goals": [], "notes": ""}}
    cme.migrate_profile(empty)
    assert empty == {"profile": {"role": None, "goals": [], "notes": ""}}


# ---------------------------------------------------------------- from a chat: settings

def test_a_new_paragraph_from_a_chat_sets_the_prepared_round_aside_and_clears_its_label(w):
    out = settings(w, "--profile", json.dumps({"journey": NEW_JOURNEY}))
    assert out["prepared"]["kept"] is False and out["prepared"]["changed"] == ["profile.journey"]
    assert names(out) == ["data/page.json", "data/prepared.json", "data/state.json"]
    assert out["profile"]["journey"] == NEW_JOURNEY and out["profile"]["journey_label"] is None
    assert out["profile"]["aim_tags"] == ["keep up to date", "specialist-level decisions outside own specialty"]
    assert set(out["labels_needed"]) == {"journey_label"}
    # the labels the assistant derives next change nothing in a round
    gen = out["gen"]
    out = settings(w, "--profile", json.dumps({"journey_label": "resident"}))
    assert out["prepared"]["kept"] is True and "labels_needed" not in out
    st = w.read_json("publish", "data", "state.json")
    assert st["gen"] == gen + 1 and cme.content_gen(st) == gen
    assert w.read_json("publish", "data", "page.json")["settings"]["level"] == {"label": "resident", "text": NEW_JOURNEY}


def test_labels_alone_keep_the_prepared_round(w):
    packed = w.read_json("store", "data", "prepared.json")
    out = settings(w, "--profile", json.dumps({"journey_label": "attending", "aim_tags": ["teach"]}))
    assert out["prepared"]["kept"] is True and names(out) == ["data/page.json", "data/state.json"]
    w.publish()
    w.forget_job()
    assert w.read_json("store", "data", "prepared.json") == packed
    r = w.start(NEXT_DAY)
    assert r["prepared"]["used"] is True
    assert w.read_json("plan.json")["profile"]["journey"] == JOURNEY


def test_a_paragraph_and_its_label_can_be_set_together(w):
    out = settings(w, "--profile", json.dumps({"aim": NEW_AIM, "aim_tags": ["exam"]}))
    assert out["prepared"]["changed"] == ["profile.aim"] and "labels_needed" not in out
    assert out["profile"]["aim_tags"] == ["exam"]


# ---------------------------------------------------------------- from the page: cme/prefs

def test_a_paragraph_written_on_the_page_is_applied_at_start_and_sets_the_prepared_round_aside(w):
    before = w.read_ledger()
    r = w.start(NEXT_DAY, "--prefs", prefs(journey=NEW_JOURNEY))
    assert r["page_settings_applied"] == {"journey": "updated"}
    assert r["prepared"] == {"used": False, "why": "where you are changed on the page"} and "present" not in r
    assert not os.path.exists(w.p("sealed_questions.md"))
    assert r["opening"].endswith("This round is written now, for what you wrote on your page about where you are.")
    # the round is planned for the new words
    assert w.read_json("plan.json")["profile"]["journey"] == NEW_JOURNEY
    assert w.read_json("plan.json")["profile"]["aim"] == AIM
    # kept in the ledger at once: paragraph stored, its label cleared, the other left alone
    st = w.read_json("publish", "data", "state.json")
    assert st["profile"]["journey"] == NEW_JOURNEY and st["profile"]["journey_label"] is None
    assert st["profile"]["journey_set_at"] == LATER
    assert st["profile"]["aim"] == AIM and st["profile"]["aim_tags"] == before["profile"]["aim_tags"]
    assert st["gen"] == before["gen"] + 1 and cme.content_gen(st) == st["gen"]
    assert w.read_json("publish", "data", "prepared.json") == {"v": 1, "empty": True}
    assert w.read_json("publish", "data", "page.json")["settings"]["level"] == {"label": None, "text": NEW_JOURNEY}
    # the assistant is asked for the label, and setting it lands on the new paragraph
    assert r["labels_needed"]["journey_label"]["from"] == NEW_JOURNEY and "aim_tags" not in r["labels_needed"]
    out = w.run_json("--today", NEXT_DAY, "settings", "--work", w.path, "--profile", '{"journey_label": "resident"}')
    assert out["prepared"]["kept"] is True
    prof = w.read_json("publish", "data", "state.json")["profile"]
    assert (prof["journey"], prof["journey_label"]) == (NEW_JOURNEY, "resident")
    # the round's save keeps both, and the same page document is not applied a second time
    saved = w.save_round(NEXT_DAY)
    assert "page_settings_applied" not in saved
    prof = w.read_json("publish", "data", "state.json")["profile"]
    assert (prof["journey"], prof["journey_label"]) == (NEW_JOURNEY, "resident")
    w.publish()
    w.forget_job()
    again = w.open("--prefs", prefs(journey=NEW_JOURNEY), today="2026-11-04")
    assert again["labels_needed"] is None


def test_both_paragraphs_and_a_mix_in_one_page_document(w):
    base = w.read_ledger()["config"]["round_set_at"]
    doc = prefs(journey=NEW_JOURNEY, aim=NEW_AIM, round={"mcqs": 2, "focused": 1, "case": True}, base=base)
    doc = json.dumps(dict(json.loads(doc), updated="2026-11-02T20:00:00.000Z"))
    r = w.start(NEXT_DAY, "--prefs", doc)
    assert r["page_settings_applied"] == {"mcqs": 2, "focused": 1, "journey": "updated", "aim": "updated"}
    assert r["prepared"]["why"] == "where you are and where you're aiming changed on the page"
    assert (r["plan"]["mcqs"], r["plan"]["focused"]) == (2, 1)
    assert set(r["labels_needed"]) == {"journey_label", "aim_tags"}
    st = w.read_json("publish", "data", "state.json")
    assert st["profile"]["aim"] == NEW_AIM and st["profile"]["aim_tags"] is None


def test_the_same_words_again_change_nothing(w):
    r = w.start(NEXT_DAY, "--prefs", prefs(journey=JOURNEY + "  \n"))
    assert "page_settings_applied" not in r and r["prepared"]["used"] is True
    assert not os.path.exists(w.pub("data", "state.json"))


def test_a_page_paragraph_older_than_a_change_in_a_chat_is_ignored(w):
    settings(w, "--profile", json.dumps({"aim": NEW_AIM, "aim_tags": ["exam"]}))
    w.publish()
    w.forget_job()
    r = w.start(NEXT_DAY, "--prefs", prefs(aim="An older thought from the page", updated="2020-01-02T00:00:00.000Z"))
    assert "page_settings_applied" not in r
    assert w.read_json("plan.json")["profile"]["aim"] == NEW_AIM
    assert w.read_ledger()["profile"]["aim_tags"] == ["exam"]


@pytest.mark.parametrize("doc", [
    {"journey": "just text"}, {"journey": {"text": "", "updated": LATER}},
    {"aim": {"text": "no time", "updated": "yesterday"}}, {"aim": {"text": 7, "updated": LATER}},
])
def test_an_invalid_paragraph_on_the_page_is_ignored_with_a_warning(w, doc):
    r = w.start(NEXT_DAY, "--prefs", json.dumps(doc))
    assert "page_settings_applied" not in r and r["prepared"]["used"] is True
    assert any(x.startswith("page settings ignored: ") for x in r["warnings"])
    assert w.read_json("plan.json")["profile"]["journey"] == JOURNEY


def test_prepare_keeps_a_page_paragraph_and_the_next_start_uses_the_round_written_for_it(w):
    """A prepare-only session (the nightly task) that read the page's paragraph: it is stored
    with its label cleared, the round is written for it, and the next start takes that round."""
    from examples import sealed_files
    doc = prefs(aim=NEW_AIM)
    w.open("--prefs", doc, today=DAY)
    out = w.run_json("--today", DAY, "prepare", "--work", w.path, "--if-needed")
    assert out["prepare"] is True and out["page_settings_applied"] == {"aim": "updated"}
    assert "data/state.json" in names(out)
    st = w.read_json("publish", "data", "state.json")
    assert st["profile"]["aim"] == NEW_AIM and st["profile"]["aim_tags"] is None and out["gen"] == st["gen"]
    plan = w.read_json("next", "plan.json")
    assert plan["profile"]["aim"] == NEW_AIM
    for name, text in sealed_files(st, plan).items():
        w.write(os.path.join("next", name), text)
    _, done = w.check().finish()
    assert done["stashed"] is True
    w.publish()
    w.forget_job()
    r = w.start(NEXT_DAY, "--prefs", doc)
    assert "page_settings_applied" not in r and r["prepared"]["used"] is True, r["prepared"]
    assert set(r["labels_needed"]) == {"aim_tags"}


def test_apply_prefs_documents():
    st = {"config": {"mcqs": 1, "focused": 0, "case": True, "round_set_at": "2026-01-01T00:00:00Z"},
          "profile": {"journey": "old", "journey_label": "fellow", "journey_set_at": None}}
    warn = []
    assert cme.apply_prefs(st, {"journey": {"text": " new ", "updated": "2026-02-01T00:00:00Z"}}, warn) == {"journey": "updated"}
    assert st["profile"] == {"journey": "new", "journey_label": None, "journey_set_at": "2026-02-01T00:00:00Z"}
    assert warn == [] and st["config"]["mcqs"] == 1
    # applied once
    assert cme.apply_prefs(st, {"journey": {"text": "new", "updated": "2026-02-01T00:00:00Z"}}, warn) == {}
    # a mix-only document is what it always was
    assert cme.apply_prefs(st, {"round": {"mcqs": 2}, "base": "2026-01-01T00:00:00Z", "updated": "2026-03-01T00:00:00Z"}) == {"mcqs": 2}
    long = "x" * (cme.PARAGRAPH_MAX + 50)
    cme.apply_prefs(st, {"aim": {"text": long, "updated": "2026-02-01T00:00:00Z"}}, warn)
    assert len(st["profile"]["aim"]) == cme.PARAGRAPH_MAX


# ---------------------------------------------------------------- the page file

def test_page_file_holds_label_and_text_and_nothing_else_new():
    st = dict(STATE, profile=dict(STATE["profile"], journey=JOURNEY, journey_label="senior attending", aim=AIM,
                                  aim_tags=["teach"], journey_set_at="2026-01-01T00:00:00Z", notes="PRIVATE-NOTE"))
    doc = cme.page_doc(cme.make_current(st))
    assert doc["settings"]["level"] == {"label": "senior attending", "text": JOURNEY}
    assert doc["settings"]["aim"] == {"tags": ["teach"], "text": AIM}
    assert doc["who"]["role"] == "senior attending"
    assert "journey_set_at" not in json.dumps(doc) and "PRIVATE-NOTE" not in json.dumps(doc)
    blank = cme.page_doc(cme.make_current(copy.deepcopy(STATE)))
    assert blank["settings"]["level"] is None and blank["settings"]["aim"] is None
    assert set(doc) == set(blank) and set(doc["settings"]) == set(blank["settings"])
    waiting = cme.page_doc(cme.make_current(dict(copy.deepcopy(STATE), profile={"journey": JOURNEY, "aim": AIM})))["settings"]
    assert waiting["level"] == {"label": None, "text": JOURNEY} and waiting["aim"] == {"tags": [], "text": AIM}


# ---------------------------------------------------------------- the page (Node harness)

def page_store(tmp_path, **profile):
    return store_with(tmp_path / "store", state=dict(STATE, profile=dict(STATE["profile"], **profile)))


def test_page_and_setup_ask_the_same_two_questions():
    with open(PAGE, encoding="utf-8") as fh:
        page = fh.read()
    onboarding = " ".join(ref("onboarding.md").replace(">", " ").split())
    for q, box in ((cme.JOURNEY_QUESTION, "lvl-q"), (cme.AIM_QUESTION, "aim-q")):
        assert '<label for="%s-input" id="%s">%s</label>' % (box[:3], box, q) in page
        assert q in onboarding
    assert 'content="%s"' % cme.PAGE_VERSION in page


def test_page_shows_labels_paragraphs_and_the_update_boxes(tmp_path):
    store = page_store(tmp_path, journey=JOURNEY, journey_label="senior attending", aim=AIM,
                       aim_tags=["keep up to date", "teach"])
    out = render(store, "--db")
    assert out["hidden"]["about"] is False
    assert out["ids"]["lvl-label"] == '<span class="chip">senior attending</span>'
    assert out["ids"]["lvl-text"] == JOURNEY and out["ids"]["aim-text"] == AIM
    assert out["ids"]["aim-label"] == '<span class="chip">keep up to date</span><span class="chip">teach</span>'
    assert out["hidden"]["lvl-edit"] is False and out["hidden"]["aim-edit"] is False
    assert out["hidden"]["lvl-box"] is True and out["hidden"]["aim-box"] is True
    assert "Role" not in out["ids"]["settings"]
    opened = render(store, "--db", "--click", "aim-edit")
    assert opened["hidden"]["aim-box"] is False and opened["hidden"]["lvl-box"] is True
    assert opened["db"] == []


def test_page_saves_an_updated_paragraph_to_prefs_beside_the_mix(tmp_path):
    store = page_store(tmp_path, journey=JOURNEY, journey_label="senior attending", aim=AIM, aim_tags=["teach"])
    mix = {"round": {"mcqs": 2, "focused": 1, "case": True}, "base": "2020-01-01T10:00:00Z", "updated": "2020-03-06T08:00:00.000Z"}
    had = tmp_path / "prefs.json"
    had.write_text(json.dumps(mix))
    out = render(store, "--db", str(had), "--set", "lvl=" + urllib.parse.quote(NEW_JOURNEY, safe=""),
                 "--click", "lvl-edit,lvl-save")
    assert len(out["db"]) == 1 and out["db"][0]["path"] == "cme/prefs"
    doc = out["db"][0]["data"]
    assert doc["journey"]["text"] == NEW_JOURNEY and cme.parse_stamp(doc["journey"]["updated"])
    assert {k: doc[k] for k in mix} == mix and "aim" not in doc           # the mix saved earlier is kept
    # shown as the learner's own words from the next round, without the old label
    assert out["ids"]["lvl-text"] == NEW_JOURNEY and out["hidden"]["lvl-box"] is True
    assert "senior attending" not in out["ids"]["lvl-label"] and "From your next round" in out["ids"]["lvl-label"]
    assert out["ids"]["aim-text"] == AIM
    # and the engine takes that document as it is
    st = {"config": {"mcqs": 2, "focused": 1, "case": True, "round_set_at": "2020-01-01T10:00:00Z"},
          "profile": {"journey": JOURNEY, "journey_label": "senior attending"}}
    assert cme.apply_prefs(st, doc) == {"journey": "updated"}
    assert st["profile"]["journey"] == NEW_JOURNEY and st["profile"]["journey_label"] is None


def test_page_does_not_save_an_empty_paragraph(tmp_path):
    out = render(page_store(tmp_path, journey=JOURNEY), "--db", "--set", "aim=%20", "--click", "aim-edit,aim-save")
    assert out["db"] == [] and "Write a few sentences first." in out["ids"]["aim-status"]
    assert out["ids"]["aim-text"] == "Not described yet."


def test_page_without_its_database_shows_the_paragraphs_and_no_update_button(tmp_path):
    out = render(page_store(tmp_path, journey=JOURNEY, journey_label="fellow"))
    assert out["ids"]["lvl-text"] == JOURNEY and "fellow" in out["ids"]["lvl-label"]
    assert out["hidden"]["lvl-edit"] is True and out["hidden"]["aim-edit"] is True
    assert "tell your assistant" in out["ids"]["about-lead"]


def test_saving_the_mix_on_the_page_keeps_a_paragraph_saved_before(tmp_path):
    had = tmp_path / "prefs.json"
    had.write_text(prefs(aim=NEW_AIM, updated="2020-03-06T08:00:00.000Z"))
    out = render(page_store(tmp_path, aim=AIM), "--db", str(had), "--click", "up-mcq,mix-save")
    doc = out["db"][0]["data"]
    assert doc["aim"]["text"] == NEW_AIM and doc["round"]["mcqs"] == 3


# ---------------------------------------------------------------- default mix and time table

def test_a_new_learner_gets_one_focused_question_and_the_case(work):
    cfg = cme.DEFAULT_CONFIG
    assert (cfg["mcqs"], cfg["focused"], cfg["case"], cfg["case_format"]) == (0, 1, True, "unfolding")
    assert cfg["session_minutes"] == cme.round_minutes(0, 1, True, "unfolding") == 35
    work.init(today=DAY, mix=None)
    r = work.start(DAY)
    assert (r["plan"]["mcqs"], r["plan"]["focused"], r["plan"]["case"]) == (0, 1, 1)
    assert r["plan"]["estimated_minutes"] == 35
    assert r["opening"].startswith("Today's round: 1 focused question + the case, about 35 minutes.")
    assert work.read_ledger()["config"]["session_minutes"] == 35


def test_a_ledger_from_before_the_mix_was_a_setting_keeps_three_mcqs_and_the_case(work):
    work.init(today=DAY, mix=None)
    st = work.read_ledger()
    for k in ("mcqs", "focused", "case"):
        del st["config"][k]
    work.write_ledger(st)
    r = work.start(DAY)
    assert (r["plan"]["mcqs"], r["plan"]["focused"], r["plan"]["case"]) == (3, 0, 1)
    assert cme.mix_estimate(cme.make_current(st))[0] == {"mcqs": 3, "focused": 0, "case": True}
    assert st["config"]["session_minutes"] == 35         # it has a length of its own: kept


CELL = re.compile(r"^(?:(\d+) MCQs? ?)?(?:\+ )?(?:(\d+) focused ?)?(?:\+ )?(?:(one-step|unfolding) case ?)?\((\d+)\)$")


def time_table():
    """The onboarding table of mixes against the time the learner names: {mix: [(minutes named,
    cell)]}."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in ref("onboarding.md").splitlines() if line.startswith("|")]
    head = next(r for r in rows if r[0] == "Mix chosen")
    minutes = [int(re.search(r"\d+", c).group()) for c in head[1:]]
    body = rows[rows.index(head) + 2:]
    body = body[:next((i for i, r in enumerate(body) if len(r) != len(head)), len(body))]
    return {r[0]: list(zip(minutes, r[1:])) for r in body}


def test_onboarding_time_table_matches_the_engines_estimates_and_fits_the_time_named():
    table = time_table()
    assert len(table) >= 6 and all(len(cells) == 4 for cells in table.values())
    for mix, cells in table.items():
        for named, cell in cells:
            m = CELL.match(re.sub(r",\s*`\w+` 0", "", cell).strip())      # ", `mcqs` 0": a kind left out
            assert m, "%s / %s min: %r" % (mix, named, cell)
            mcqs, focused, fmt, says = int(m.group(1) or 0), int(m.group(2) or 0), m.group(3), int(m.group(4))
            est = cme.round_minutes(mcqs, focused, bool(fmt), "discriminate" if fmt == "one-step" else "unfolding")
            assert est == says, "%s / %s min: %r is %d minutes" % (mix, named, cell, est)
            assert est <= named, "%s / %s min: %r does not fit" % (mix, named, cell)
    # the recommended row is first, and its 35-minute cell is the default of a new learner
    first = next(iter(table))
    assert "recommended" in first and dict(table[first])[35].startswith("1 focused + unfolding case")
    text = ref("onboarding.md")
    assert "5 minutes per" in text and "25 for an unfolding one" in text
    assert (cme.MINUTES_PER["mcq"], cme.MINUTES_PER["focused"], cme.MINUTES_PER["unfolding"],
            cme.MINUTES_PER["discriminate"]) == (5, 10, 25, 15)


# ---------------------------------------------------------------- the rulebook and the briefs

def test_rule_4_pitches_from_the_paragraphs_and_the_briefs_cite_it():
    standards = ref("standards.md")
    rule = standards.split("## Rule 4. Pitch")[1].split("## Rule 5.")[0]
    assert "journey" in rule and "aim" in rule and "slot: issue #55" not in rule
    assert "display" in rule and "exam" in rule
    for name in ("author.md", "case_design.md", "feedback_guide.md"):
        assert "rule 4" in ref(name), name
    # said once, in the rulebook: the briefs do not carry the paragraphs' rules themselves
    for name in ("author.md", "case_design.md", "feedback_guide.md"):
        assert "journey_label" not in ref(name), name

"""Two-level blueprint (issue #81): the disease (the blueprint topic) returns on schedule; the
sub-topic rotates and is recorded. Sub-topics carry decision points for the author and the
importance of each aspect; a gap keeps its sub-topic, so the exact point comes back; the
feedback links the sibling sub-topic answered last time. A ledger with history moves to the two
levels once, through `apply-mapping` and a mapping file (past item -> sub-topic). A one-level
blueprint and the ledgers written on it keep working as before."""
import copy
import datetime as dt
import json
import os
import shutil

import pytest

import examples
from conftest import ROOT, Work
from examples import cme
from test_forms import fill, form, item
from test_work_folder import Round

TWO = os.path.join(ROOT, "tests", "two_level")
BLUEPRINT_MD = os.path.join(TWO, "blueprint.md")
MAPPING_JSON = os.path.join(TWO, "mapping.json")
MAPPING_MD = os.path.join(TWO, "mapping.md")
DAY = dt.date(2026, 11, 20)


def two_level():
    with open(BLUEPRINT_MD, encoding="utf-8") as fh:
        return cme.blueprint_from_md(fh.read())


def fresh_two_level():
    st = examples.load_ledger("fresh")
    st["blueprint"] = two_level()
    return st


def it(topic, sub=None, mastery=4, typ="mcq", **extra):
    out = {"type": typ, "topic": topic, "mastery": mastery, "confidence": "unsure", "coding": {"errors": []}}
    if typ == "mcq":
        out.update(correct=mastery >= 4, stem_summary="Example stem on %s" % (sub or topic))
    if typ == "focused":
        out.update(aspect="management", stem_summary="Example focused stem on %s" % (sub or topic))
    if sub:
        out["subtopic"] = sub
    out.update(extra)
    return out


def record(st, day, *items, gaps=()):
    rnd = {"items": list(items), "gaps": list(gaps), "title": "t", "summary": "s"}
    if any(x["type"] == "case" for x in items):
        rnd["case"] = {"patient": "60M", "diagnosis": "d"}
    cme.record_round(st, rnd, day)
    cme.reflect_round(st, {"skipped": True}, day)
    return st


def plan(st, day, **options):
    return cme.plan_round(st, examples.plan_options(**options), day)


# ---------------------------------------------------------------- the blueprint

def test_the_markdown_blueprint_takes_sub_topics_decision_points_and_aspects():
    bp = two_level()
    card = bp["CARD"]
    assert card["topics"]["CARD-03"] == "Atrial fibrillation & rate/rhythm control, anticoagulation"
    assert "CARD-03a" not in card["topics"]                 # a sub-topic is not a topic
    a = card["subtopics"]["CARD-03"]["CARD-03a"]
    assert a == {"label": "Stroke prevention decision",
                 "points": ["Whether a score of one on the risk score calls for anticoagulation",
                            "Anticoagulation after an intracranial bleed"],
                 "aspects": {"management": 1.0, "testing": 0.35}}
    assert list(card["subtopics"]["CARD-03"]) == ["CARD-03a", "CARD-03b", "CARD-03c"]
    assert card["subtopics"]["CARD-05"]["CARD-05b"] == {"label": "Regurgitant lesions and mitral stenosis"}
    assert "subtopics" not in bp["PULM"]                      # an area without any stays one-level
    st = {"blueprint": bp}
    assert cme.subtopics_of(st, "CARD-12") == ["CARD-12a", "CARD-12b", "CARD-12c"]
    assert cme.subtopics_of(st, "CARD-01") == []
    assert cme.bp_subtopics(st)["ENDO-06b"] == {"label": "Phaeochromocytoma", "topic": "ENDO-06", "domain": "ENDO"}


def test_a_json_blueprint_may_nest_sub_topics_under_their_topic():
    nested = {"CARD": {"name": "Cardiology", "weight": 1.0, "topics": {
        "CARD-01": "Acute coronary syndrome",
        "CARD-03": {"label": "Atrial fibrillation", "subtopics": {
            "CARD-03a": {"label": "Stroke prevention", "points": ["one"], "aspects": {"management": 1.0}},
            "CARD-03b": "Rate versus rhythm"}}}}}
    bp = cme.blueprint_shape(copy.deepcopy(nested))
    assert bp["CARD"]["topics"] == {"CARD-01": "Acute coronary syndrome", "CARD-03": "Atrial fibrillation"}
    assert bp["CARD"]["subtopics"] == {"CARD-03": {
        "CARD-03a": {"label": "Stroke prevention", "points": ["one"], "aspects": {"management": 1.0}},
        "CARD-03b": {"label": "Rate versus rhythm"}}}
    assert cme.blueprint_shape(copy.deepcopy(bp)) == bp      # the shape kept is read as it is
    # a ledger whose blueprint was stored nested is read in the same shape (migrate on load)
    st = examples.load_ledger("fresh", raw=True)
    st["blueprint"] = copy.deepcopy(nested)
    assert cme.migrate_ledger(st)["blueprint"] == bp


def test_a_sub_topic_id_used_twice_is_refused():
    bad = {"CARD": {"name": "C", "weight": 1, "topics": {"CARD-01": "a", "CARD-02": "b"},
                    "subtopics": {"CARD-01": {"CARD-01a": "x"}, "CARD-02": {"CARD-01a": "y"}}}}
    with pytest.raises(cme.CmeError):
        cme.blueprint_shape(bad)
    with pytest.raises(cme.CmeError):
        cme.blueprint_shape({"CARD": {"name": "C", "weight": 1, "topics": {"CARD-01": "a"},
                                      "subtopics": {"CARD-09": {"CARD-09a": "x"}}}})


def test_a_one_level_blueprint_and_its_ledgers_are_read_as_before():
    with open(os.path.join(ROOT, "tests", "one_level", "blueprint.md"), encoding="utf-8") as fh:
        md = cme.blueprint_from_md(fh.read())
    with open(os.path.join(ROOT, "tests", "one_level", "blueprint.json"), encoding="utf-8") as fh:
        assert md == json.load(fh)
    # a blueprint whose topic bullets are all indented is still one level
    indented = cme.blueprint_from_md("## A. Alpha (weight: high)\n  - AAA-01  One\n  - AAA-02  Two\n")
    assert indented == {"AAA": {"name": "Alpha", "weight": 1.0, "topics": {"AAA-01": "One", "AAA-02": "Two"}}}
    for name in examples.LEDGERS:
        raw = examples.load_ledger(name, raw=True)
        st = examples.load_ledger(name)
        assert not cme.bp_subtopics(st) and not cme.bp_subtopics(raw)
        for c in plan(st, examples.today_of(name))["items"]:
            assert "subtopic" not in c


# ---------------------------------------------------------------- the plan: the sub-topic rotates

def test_the_disease_comes_by_its_schedule_and_the_sub_topic_rotates_untested_first():
    st = fresh_two_level()
    day = DAY
    seen = []
    for n in range(3):
        p = plan(st, day, mcqs=0, focused=0, domain="CARD")
        case = p["items"][0]
        if case["topic"] != "CARD-03":
            case["topic"], case["label"] = "CARD-03", "Atrial fibrillation"
            case.pop("subtopic", None)
            sid, why = cme.choose_subtopic(st, "CARD-03")
            case["subtopic"] = {"id": sid, "why": why}
        seen.append((case["subtopic"]["id"], case["subtopic"]["why"]))
        record(st, day, it("CARD-03", case["subtopic"]["id"], typ="case"))
        day += dt.timedelta(days=30)
    assert seen == [("CARD-03a", "untested"), ("CARD-03b", "untested"), ("CARD-03c", "untested")]
    # the topic is one schedule: three rounds, one record
    assert st["topics"]["CARD-03"]["attempts"] == 3 and "CARD-03a" not in st["topics"]


def test_then_the_weakest_and_never_the_sub_topic_of_the_last_round_on_the_disease():
    st = fresh_two_level()
    record(st, DAY, it("CARD-03", "CARD-03a", mastery=2))
    record(st, DAY + dt.timedelta(days=4), it("CARD-03", "CARD-03b", mastery=4))
    record(st, DAY + dt.timedelta(days=8), it("CARD-03", "CARD-03c", mastery=5))
    assert cme.choose_subtopic(st, "CARD-03") == ("CARD-03a", "weakest")
    record(st, DAY + dt.timedelta(days=12), it("CARD-03", "CARD-03a", mastery=3))
    # 03a was the last round's: the weakest of the others (03b at 4) comes, though 03a is lower
    assert cme.choose_subtopic(st, "CARD-03") == ("CARD-03b", "weakest")
    status = cme.subtopic_status(st, "CARD-03")
    assert status["CARD-03a"] == {"rounds": 2, "last": "2026-12-02", "session": "S0004", "mastery": 3.0}


def test_a_gap_brings_back_its_own_sub_topic_exactly():
    st = fresh_two_level()
    record(st, DAY, it("CARD-03", "CARD-03c", mastery=1, typ="focused"),
           gaps=[{"topic": "CARD-03", "gap": "Length of triple therapy after PCI", "source": "graded"}])
    g = st["gaps"][0]
    assert g["subtopic"] == "CARD-03c"                     # the gap keeps the sub-topic its item was on
    assert cme.choose_subtopic(st, "CARD-03", g) == ("CARD-03c", "gap")      # even though it was the last
    p = plan(st, DAY + dt.timedelta(days=4), mcqs=0, focused=0, domain="CARD")
    c = next(c for c in p["items"] if c.get("topic") == "CARD-03")
    assert c["retest_gap"]["id"] == g["id"]
    assert c["subtopic"]["id"] == "CARD-03c" and c["subtopic"]["why"] == "gap"
    assert c["subtopic"]["points"] == ["Length of triple therapy", "Which antiplatelet stays with the anticoagulant"]
    assert "subtopic: CARD-03c" in c["subtopic"]["how"]


def test_a_confident_error_opens_its_gap_on_the_sub_topic_it_was_made_on():
    st = fresh_two_level()
    record(st, DAY, it("CARD-03", "CARD-03b", mastery=1, confidence="sure", correct=False))
    assert st["gaps"][0]["source"] == ["misconception"] and st["gaps"][0]["subtopic"] == "CARD-03b"


def test_the_plan_gives_the_sub_topic_its_points_aspects_and_depth():
    st = fresh_two_level()
    for n in range(3):           # 03a answered well three times: its evidence depth is earned there only
        record(st, DAY + dt.timedelta(days=30 * n), it("CARD-03", "CARD-03a", mastery=5, confidence="sure"))
    assert cme.evidence_depth(st, "CARD-03", subtopic="CARD-03a")["level"] == 3
    assert cme.evidence_depth(st, "CARD-03", subtopic="CARD-03b")["level"] == 1
    p = plan(st, DAY + dt.timedelta(days=200), mcqs=0, focused=1, no_case=True, domain="CARD")
    c = p["items"][0]
    if c.get("topic") == "CARD-03":
        assert c["subtopic"]["id"] == "CARD-03b" and "depth" not in c
        # the focused question's aspect is one the sub-topic says matters
        assert c["aspect_hint"] in c["subtopic"]["aspects"]


def test_aspects_are_asked_in_proportion_to_their_importance():
    st = fresh_two_level()
    st["blueprint"]["CARD"]["topics"] = {"CARD-03": "Atrial fibrillation"}     # the domain round can only be on it
    hints = []
    for n in range(9):
        day = DAY + dt.timedelta(days=100 * n)
        p = plan(st, day, mcqs=0, focused=1, no_case=True, domain="CARD")
        c = next(c for c in p["items"] if c.get("topic") == "CARD-03")
        hints.append((c["subtopic"]["id"], c["aspect_hint"]))
        record(st, day, it("CARD-03", c["subtopic"]["id"], typ="focused", aspect=c["aspect_hint"]))
        record(st, day + dt.timedelta(days=1), it("GI-02"))     # no third round in a row on it (drill-down limit)
    # the most important aspect first, the less important ones in their turn
    assert hints[:3] == [("CARD-03a", "management"), ("CARD-03b", "management"), ("CARD-03c", "management")]
    assert ("CARD-03a", "testing") in hints and ("CARD-03b", "disposition") in hints
    on_a = [a for s, a in hints if s == "CARD-03a"]
    assert set(on_a) <= {"management", "testing"}
    assert all(a in ("management", "disposition") for s, a in hints if s == "CARD-03b")


# ---------------------------------------------------------------- the record

def test_the_round_record_keeps_the_sub_topic_in_full_and_in_compact_form():
    st = fresh_two_level()
    record(st, DAY, it("CARD-03", "CARD-03a"), it("ENDO-06", "ENDO-06b", typ="case"))
    s = st["sessions"][-1]
    assert [x.get("subtopic") for x in s["items"]] == ["CARD-03a", "ENDO-06b"]
    assert s["case"]["subtopic"] == "ENDO-06b"
    prev = cme.to_previous(s)
    assert [x.get("subtopic") for x in prev["items"]] == ["CARD-03a", "ENDO-06b"]
    assert prev["case"]["subtopic"] == "ENDO-06b"
    _, stems = cme.all_sessions_for_novelty(st)
    assert stems[0]["subtopic"] == "CARD-03a"


def test_the_sibling_answered_last_time_is_found():
    st = fresh_two_level()
    assert cme.sibling_of(st, "CARD-03", "CARD-03b") is None
    record(st, DAY, it("CARD-03", "CARD-03a", mastery=4))
    record(st, DAY + dt.timedelta(days=5), it("CARD-03", "CARD-03b", mastery=2))
    assert cme.sibling_of(st, "CARD-03", "CARD-03b") == {
        "subtopic": "CARD-03a", "label": "Stroke prevention decision", "date": "2026-11-20",
        "session": "S0001", "mastery": 4}
    assert cme.sibling_of(st, "CARD-03", "CARD-03c")["subtopic"] == "CARD-03b"


# ---------------------------------------------------------------- the key header, the form, the draft

KEYS = """<!-- key: Q1 -->
type: mcq
topic: CARD-03
subtopic: CARD-03b
label: Atrial fibrillation
reason: due
stem_summary: New AF, haemodynamically stable, when to cardiovert
<!-- /key -->
Correct: B.
<!-- present: questions -->
Q1. stem ... A B C
<!-- /present -->
"""


def two_level_round(tmp_path, history=True):
    """A work folder on a learner with the two-level blueprint, who answered CARD-03a before."""
    w = Round(tmp_path).setup()
    w.open()
    w.run("settings", "--work", w.path, "--blueprint", BLUEPRINT_MD)
    w.publish()
    w.forget_job()
    if history:
        st = w.read_ledger()
        record(st, dt.date(2026, 10, 1), it("CARD-03", "CARD-03a", mastery=4))
        w.write_ledger(st)
    w.start()
    w.write("sealed_questions.md", KEYS)
    return w


def test_the_key_header_names_the_sub_topic_and_the_form_and_draft_carry_the_sibling(tmp_path):
    w = two_level_round(tmp_path)
    out = w.answer("questions")
    assert out["siblings"] == {"Q1": {"subtopic": "CARD-03a", "label": "Stroke prevention decision",
                                      "date": "2026-10-01", "session": "S0001", "mastery": 4}}
    f = form(w)
    q1 = item(f, "Q1")
    assert q1["subtopic"] == "CARD-03b" and q1["given"]["sibling"]["subtopic"] == "CARD-03a"
    w.write("round.json", fill(f))
    w.run_json("draft", "--work", w.path, "--part", "questions")
    with open(w.p("draft_questions.md"), encoding="utf-8") as fh:
        draft = fh.read()
    assert "[live: the sibling line: one sentence tying this point to Stroke prevention decision" in draft
    w.write("feedback.md", "Feedback, as sent")
    saved = w.run_json("--today", "2026-11-01", "save", "--work", w.path)
    assert saved["ok"]
    rec = w.read_json("record.json")
    assert rec["items"][0]["subtopic"] == "CARD-03b"


def test_save_refuses_a_sub_topic_the_blueprint_does_not_have_under_the_topic(tmp_path):
    w = two_level_round(tmp_path, history=False)
    w.write("sealed_questions.md", KEYS.replace("subtopic: CARD-03b", "subtopic: CARD-05a"))
    w.answer("questions")
    w.write("round.json", fill(form(w)))
    w.write("feedback.md", "Feedback, as sent")
    r = w.run("--today", "2026-11-01", "save", "--work", w.path, ok=False)
    assert r.returncode != 0
    assert "key Q1: subtopic CARD-05a belongs to topic CARD-05, not CARD-03" in r.stdout + r.stderr
    assert not os.path.exists(w.pub("data", "state.json"))


def test_keys_against_the_plan_ask_for_the_planned_sub_topic(tmp_path):
    plan_doc = {"counts": {"mcqs": 1, "focused": 0, "case": 0},
                "items": [{"slot": "mcq", "topic": "CARD-03", "subtopic": {"id": "CARD-03c"}}]}
    path = os.path.join(str(tmp_path), "sealed_questions.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(KEYS)
    _, problems = cme.check_key_headers([path], plan_doc)
    assert problems == ["key Q1: the plan gives topic CARD-03 the sub-topic CARD-03c; "
                        "write 'subtopic: CARD-03c' in its header"]
    plan_doc["items"][0]["subtopic"]["id"] = "CARD-03b"
    assert cme.check_key_headers([path], plan_doc)[1] == []


# ---------------------------------------------------------------- the page

def test_the_page_lists_tested_sub_topics_under_their_disease_and_nothing_untested():
    st = fresh_two_level()
    record(st, DAY, it("CARD-03", "CARD-03b", mastery=3), it("ENDO-06", typ="case"))
    page = cme.page_doc(st)
    card = next(t for t in page["topics"] if t["id"] == "CARD-03")
    assert card["subtopics"] == [{"id": "CARD-03b", "label": "Rate versus rhythm control and cardioversion",
                                  "mastery": 3.0, "last": "2026-11-20"}]
    assert "subtopics" not in next(t for t in page["topics"] if t["id"] == "ENDO-06")
    text = json.dumps(page)
    assert "Stroke prevention decision" not in text and "CARD-03a" not in text


# ---------------------------------------------------------------- apply-mapping on an example ledger

def mapped_work(tmp_path, mapping=MAPPING_JSON, check=False, blueprint=True):
    """The example ledger mid_curriculum in a store, opened; the two-level sample blueprint set
    in the same job; then the mapping applied."""
    w = Work(tmp_path)
    os.makedirs(w.store("data"))
    shutil.copy(examples.ledger_path("mid_curriculum"), w.ledger)
    today = examples.LEDGERS["mid_curriculum"]
    w.open(today=today)
    if blueprint:
        w.run("--today", today, "settings", "--work", w.path, "--blueprint", BLUEPRINT_MD)
    r = w.run("--today", today, "apply-mapping", "--work", w.path, "--mapping", mapping,
              *(("--check",) if check else ()), ok=False)
    return w, r


def test_the_mapping_moves_each_past_item_to_the_sub_topic_it_tested(tmp_path):
    before = examples.load_ledger("mid_curriculum")
    w, r = mapped_work(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    # through the normal write path: the publish set, the ledger last
    assert [f["as"] for f in out["files"]] == ["data/page.json", "data/prepared.json", "data/state.json"]
    st = w.read_json("publish", "data", "state.json")
    s1 = next(s for s in st["sessions"] if s["id"] == "S0001")
    case = next(x for x in s1["items"] if x["type"] == "case")
    assert (case["topic"], case["subtopic"], case["recorded_under"]) == ("CARD-12", "CARD-12a", "CARD-05")
    assert s1["case"]["topic"] == "CARD-12" and s1["case"]["subtopic"] == "CARD-12a"
    assert s1["topics"][0] == "CARD-12" and "CARD-05" not in s1["topics"] and s1["why"]["CARD-12"] == "new"
    mcq = next(x for x in s1["items"] if x["topic"] == "GI-02")
    assert mcq["subtopic"] == "GI-02b" and "recorded_under" not in mcq       # same disease: only the sub-topic
    # scores are untouched; every item the mapping names says where it went
    assert [x["mastery"] for s in st["sessions"] for x in s["items"]] == \
        [x["mastery"] for s in before["sessions"] for x in s["items"]]
    assert len(out["items"]) == 15 + 2                                      # 15 named, 2 of retired CARD-04
    # a disease keeps its due date; one that gets items and had no record takes its source's schedule
    for tid in ("CARD-05", "GI-02", "ENDO-06"):
        assert st["topics"][tid]["due"] == before["topics"][tid]["due"]
    assert st["topics"]["CARD-12"]["due"] == before["topics"]["CARD-05"]["due"]
    assert st["topics"]["CARD-12"]["attempts"] == 2 and st["topics"]["CARD-12"]["label"] == "Infective endocarditis"
    assert out["new_records"] == [{"topic": "CARD-12", "due": before["topics"]["CARD-05"]["due"], "from": "CARD-05"}]
    # sub-topics never tested start as new
    assert cme.choose_subtopic(st, "CARD-12") == ("CARD-12c", "untested")
    # a retired disease folds into the one named: its record, its items
    assert "CARD-04" not in st["topics"] and st["topics"]["CARD-11"]["due"] == before["topics"]["CARD-04"]["due"]
    assert st["topics"]["CARD-11"]["label"] == "Syncope and arrhythmias"
    assert not any(x["topic"] == "CARD-04" for s in st["sessions"] for x in s["items"])
    assert out["retired"] == [{"topic": "CARD-04", "into": "CARD-11"}] and out["not_in_blueprint"] == []
    # the open gap goes to its sub-topic, with an id from now on
    assert st["gaps"] == [dict(before["gaps"][0], id="G0001", subtopic="ENDO-06a")]
    assert st["mappings"][0]["items"] == 17 and st["mappings"][0]["gaps"] == 1
    # the page shows the diseases with their sub-topics
    page = w.read_json("publish", "data", "page.json")
    assert [u["id"] for u in next(t for t in page["topics"] if t["id"] == "CARD-12")["subtopics"]] == ["CARD-12a", "CARD-12b"]
    # and a round is planned on it as usual
    w.publish()
    w.forget_job()
    started = w.start(examples.LEDGERS["mid_curriculum"], "--no-prepared")
    assert started["ok"]
    p = w.read_json("plan.json")
    endo = next(c for c in p["items"] if c.get("topic") == "ENDO-06")
    assert endo["subtopic"]["id"] == "ENDO-06a" and endo["subtopic"]["why"] == "gap"


def test_the_markdown_table_and_the_json_file_are_the_same_mapping(tmp_path):
    a = cme.read_mapping(MAPPING_JSON)
    b = cme.read_mapping(MAPPING_MD)
    for k in ("items", "gaps", "topics"):
        assert a[k] == b[k]
    w1, _ = mapped_work(tmp_path / "json")
    w2, _ = mapped_work(tmp_path / "md", MAPPING_MD)
    s1, s2 = (w.read_json("publish", "data", "state.json") for w in (w1, w2))
    for s in (s1, s2):
        s.pop("mappings")
    assert s1 == s2


def test_the_note_style_target_reads_its_first_id(tmp_path):
    md = os.path.join(str(tmp_path), "m.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write("| Session | Item | Recorded under | What it asked | Goes to |\n|---|---|---|---|---|\n"
                 "| S0001, S0003 | mcq | ENDO-06 | x | ENDO-06a (touches ENDO-06b) |\n"
                 "| gap | | GEN-10 | x | stays GEN-10 |\n")
    m = cme.read_mapping(md)
    assert m["items"] == [{"session": "S0001", "type": "mcq", "topic": "ENDO-06", "to": "ENDO-06a"},
                          {"session": "S0003", "type": "mcq", "topic": "ENDO-06", "to": "ENDO-06a"}]
    assert m["gaps"] == [{"topic": "GEN-10", "to": "GEN-10"}]


def test_check_prints_the_same_and_writes_nothing(tmp_path):
    w, r = mapped_work(tmp_path, check=True)
    out = json.loads(r.stdout)
    assert out["check"] is True and len(out["items"]) == 17 and "files" not in out
    st = w.read_json("publish", "data", "state.json")           # the blueprint change only
    assert "mappings" not in st and not any(x.get("subtopic") for s in st["sessions"] for x in s["items"])


def test_a_mapping_is_refused_whole_with_every_problem_named(tmp_path):
    bad = {"items": [{"session": "S0099", "type": "mcq", "topic": "GI-02", "to": "GI-02a"},
                     {"session": "S0001", "type": "mcq", "topic": "GI-02", "to": "GI-09z"},
                     {"session": "S0002", "type": "mcq", "topic": "CARD-01", "to": "CARD-03a"},
                     {"session": "S0001", "type": "quiz", "topic": "GI-02", "to": "GI-02a"}],
           "gaps": [{"topic": "RENAL-01", "to": "ENDO-06a"}],
           "topics": [{"topic": "CARD-04", "to": "CARD-04"}]}
    path = os.path.join(str(tmp_path), "bad.json")
    os.makedirs(str(tmp_path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(bad, fh)
    w, r = mapped_work(tmp_path / "w", path)
    assert r.returncode != 0
    err = json.loads(r.stdout)["error"]
    for part in ("no session S0099", "'to' GI-09z is neither", "items[3] (S0002 mcq CARD-01): no such item",
                 "'type' must be mcq, focused or case", "no open gap RENAL-01", "'to' must be another topic",
                 "Nothing was changed"):
        assert part in err, part
    assert "mappings" not in w.read_json("publish", "data", "state.json")


def test_a_mapping_needs_the_two_level_blueprint_a_reflected_ledger_and_is_applied_once(tmp_path):
    _, r = mapped_work(tmp_path / "a", blueprint=False)
    assert r.returncode != 0 and "has no sub-topics" in r.stdout
    w, r = mapped_work(tmp_path / "b")
    assert r.returncode == 0
    again = w.run("--today", examples.LEDGERS["mid_curriculum"], "apply-mapping", "--work", w.path,
                  "--mapping", MAPPING_JSON, ok=False)
    assert again.returncode != 0 and "applied on 2026-10-28 already" in again.stdout
    w = Work(tmp_path / "c")
    os.makedirs(w.store("data"))
    shutil.copy(examples.ledger_path("unreflected"), w.ledger)
    w.open(today=examples.LEDGERS["unreflected"])
    w.run("settings", "--work", w.path, "--blueprint", BLUEPRINT_MD)
    r = w.run("apply-mapping", "--work", w.path, "--mapping", MAPPING_JSON, ok=False)
    assert r.returncode != 0 and "waiting for its reflection" in r.stdout


def test_two_gaps_landing_on_one_disease_are_merged_into_one(tmp_path):
    st = examples.load_ledger("mid_curriculum")
    st["blueprint"] = two_level()
    st["gaps"].append({"topic": "CARD-05", "gap": "Oral step-down criteria", "self": None, "source": ["graded"],
                       "date": "2026-10-21", "opened": "2026-10-19"})
    st["topics"]["CARD-12"] = dict(st["topics"]["CARD-05"], label="Infective endocarditis")
    st["gaps"].append({"topic": "CARD-12", "gap": "Repeat echo after a negative TTE", "self": None,
                       "source": ["misconception"], "date": "2026-10-23", "opened": "2026-10-23",
                       "last_retested": "2026-10-24"})
    m = {"items": [], "topics": [], "gaps": [{"topic": "CARD-05", "to": "CARD-12b"}], "name": "t", "text": "x"}
    out = cme.apply_mapping(st, m, DAY)
    card = [g for g in st["gaps"] if g["topic"] == "CARD-12"]
    assert len(card) == 1 and len([g for g in st["gaps"] if g["topic"] == "CARD-05"]) == 0
    g = card[0]
    assert g["gap"] == "Repeat echo after a negative TTE; Oral step-down criteria"
    assert g["source"] == ["graded", "misconception"] and g["opened"] == "2026-10-19" and g["date"] == "2026-10-23"
    assert "last_retested" not in g                    # the moved gap still awaits its retest
    assert g["subtopic"] == "CARD-12b"
    assert out["merged"] == [{"id": "G0002", "into": "G0003", "topic": "CARD-12"}]


def test_rounds_the_mapping_changed_are_frozen_scores_refused_stops_outright(tmp_path):
    w, r = mapped_work(tmp_path)
    out = json.loads(r.stdout)
    assert "S0001" in out["frozen"] and "S0009" not in out["frozen"]
    st = w.read_json("publish", "data", "state.json")
    s1 = next(s for s in st["sessions"] if s["id"] == "S0001")
    assert s1["undo"]["topics"] == {} and s1["undo"]["frozen"] == "2026-10-28"
    w.publish()
    w.forget_job()
    w.write(os.path.join("store", "data", "sessions", "S0010.json"), {"id": "S0010", "date": "2026-10-23"})
    w.open(today="2026-10-29")
    r = w.run("override", "--work", w.path, "--session", "S0010",
              "--scores", json.dumps([{"item": "Q3", "type": "mcq", "topic": "ENDO-06", "score": 5}]), ok=False)
    assert r.returncode != 0 and "before the blueprint mapping of 2026-10-28" in r.stdout
    stop = w.run_json("--today", "2026-10-29", "override", "--work", w.path, "--session", "S0010",
                      "--stops", json.dumps([{"item": "Q3", "type": "mcq", "topic": "ENDO-06"}]))
    assert stop["ok"]
    st = w.read_json("publish", "data", "state.json")
    assert st["topics"]["ENDO-06"]["stopped"] == "2026-10-29" and st["gaps"] == []
    assert any(x.get("outright") for x in next(s for s in st["sessions"] if s["id"] == "S0010")["stops"])


def test_the_rendered_page_shows_the_sub_topics_under_their_disease(tmp_path):
    from test_page import render, store_with
    st = fresh_two_level()
    record(st, DAY, it("CARD-03", "CARD-03b", mastery=3))
    table = render(store_with(tmp_path, state=st))["ids"]["topics"]
    assert "CARD-03" in table and "CARD-03b" in table and "Rate versus rhythm control and cardioversion" in table
    assert table.index("CARD-03b") > table.index("Atrial fibrillation")       # under its disease
    assert "CARD-03a" not in table                                            # never one not yet tested

"""Evidence depth: the more often a topic is answered well, the further behind the recommendation
its feedback goes (guidance -> studies -> design -> frontier; references/evidence_depth.md).
The engine counts, per topic and per aspect of a focused question, how many times in a row it
was answered well; the plan tells the author (who writes 'Deeper' notes into the kit, rule 8 of
references/standards.md), and `answer` tells the examiner once the part's answers are in."""
import copy
import datetime as dt
import json
import os

import pytest

import examples
from examples import cme
from conftest import Work
from test_finish_prepare import DAY, Next
from test_standards import refused

TOPIC = "CARD-03"


def item(mastery=5, typ="mcq", topic=TOPIC, confidence="sure", **more):
    it = {"type": typ, "topic": topic, "mastery": mastery, "confidence": confidence, "coding": {"errors": []}}
    if typ == "mcq":
        it["correct"] = mastery >= 4
    return dict(it, **more)


def ledger(*rounds, config=None, gaps=()):
    """A ledger whose rounds each hold the given items, oldest first."""
    st = cme.new_state(dt.date(2026, 11, 1))
    st["config"].update(config or {})
    st["sessions"] = [{"id": "S%04d" % n, "date": "2026-11-%02d" % n, "items": list(items),
                       "topics": sorted({i["topic"] for i in items})} for n, items in enumerate(rounds, 1)]
    st["gaps"] = [{"id": "G0001", "topic": t, "gap": "g"} for t in gaps]
    return st


def level(st, topic=TOPIC, **kw):
    return cme.evidence_depth(st, topic, **kw)["level"]


# ---------------------------------------------------------------- the ladder

@pytest.mark.parametrize("in_a_row,name", [(0, "guidance"), (1, "studies"), (2, "design"), (3, "design"),
                                           (4, "frontier"), (9, "frontier")])
def test_depth_grows_with_the_times_in_a_row_a_topic_was_answered_well(in_a_row, name):
    st = ledger(*[[item()] for _ in range(in_a_row)])
    d = cme.evidence_depth(st, TOPIC)
    assert d == {"level": [n for n, _ in cme.EVIDENCE_DEPTHS].index(name) + 1, "name": name, "in_a_row": in_a_row}


def test_a_new_topic_starts_at_the_first_depth():
    assert cme.evidence_depth(ledger([item(topic="RENAL-02")]), TOPIC) == {"level": 1, "name": "guidance", "in_a_row": 0}
    assert level(ledger(), None) == 1          # a topic the author is still to choose


@pytest.mark.parametrize("missed", [
    item(1),                                   # wrong
    item(3, typ="focused"),                    # right decision, thin reasoning
    item(5, confidence="guess"),               # a correct guess is not yet mastered
    item(1, typ="case", confidence="sure"),    # confident and wrong
])
def test_a_miss_brings_the_topic_back_to_the_first_depth(missed):
    st = ledger([item()], [item()], [item()], [missed])
    assert level(st) == 1
    st["sessions"].append({"id": "S0009", "items": [item()]})
    assert level(st) == 2                      # and it is earned again from there


def test_older_rounds_kept_in_compact_form_count_too():
    st = ledger([item()], [item()])
    st["previous"] = [cme.to_previous(s) for s in ledger([item()], [item()])["sessions"]]
    assert cme.evidence_depth(st, TOPIC)["in_a_row"] == 4


def test_other_topics_do_not_count():
    st = ledger([item()], [item(1, topic="RENAL-02")], [item()])
    assert cme.evidence_depth(st, TOPIC)["in_a_row"] == 2


def test_an_open_gap_or_a_retest_keeps_the_item_at_the_first_depth():
    st = ledger([item()], [item()], [item()])
    assert level(st) == 3
    assert level(st, retests=True) == 1
    assert level(dict(st, gaps=[{"id": "G0001", "topic": TOPIC, "gap": "the learner feels shaky here"}])) == 1


def test_a_focused_question_goes_one_depth_beyond_what_its_aspect_has_earned():
    focused = lambda aspect, m=5: item(m, typ="focused", aspect=aspect)
    st = ledger([focused("management")], [focused("management")], [item()], [item()])
    assert level(st) == 4
    assert level(st, aspect="management") == 4          # two in a row on this aspect: design, plus one
    assert level(st, aspect="testing") == 2             # an aspect never asked on this topic
    st = ledger([focused("management")], [focused("testing")], [focused("management")])
    assert level(st, aspect="testing") == 3 and level(st, aspect="management") == 3


def test_a_score_the_learner_set_counts_as_recorded():
    st = ledger([item(4, typ="focused", graded=2, set_by="learner", aspect="management")])
    assert level(st) == 2


def test_with_the_ladder_off_there_is_no_depth():
    st = ledger([item()], [item()], config={"evidence_ladder": False})
    assert cme.evidence_depth(st, TOPIC) is None


# ---------------------------------------------------------------- the plan: what the author is told

def mastered(st, topics, times=2):
    """`st` with each of `topics` answered well `times` times in a row, long enough ago to be due."""
    for n in range(times):
        st["sessions"].append({"id": "S%04d" % (n + 1), "date": "2026-09-%02d" % (n + 1), "topics": list(topics),
                               "items": [item(topic=t) for t in topics]})
    return st


def test_the_plan_gives_a_depth_only_beyond_the_first(tmp_path):
    w = Work(tmp_path)
    w.init(today=DAY)
    st = w.read_ledger()
    plan0 = cme.plan_round(copy.deepcopy(st), examples.plan_options(), dt.date.fromisoformat(DAY))
    assert plan0["evidence_ladder"] is True and not any("depth" in c for c in plan0["items"])
    topics = [c["topic"] for c in plan0["items"] if c.get("topic")]
    plan = cme.plan_round(mastered(copy.deepcopy(st), topics), examples.plan_options(allow_repeat=True),
                          dt.date.fromisoformat(DAY))
    deep = {c["topic"]: c["depth"] for c in plan["items"] if c.get("depth")}
    for t, d in deep.items():
        assert t in topics and (d["level"], d["name"], d["in_a_row"]) == (3, "design", 2)
        assert "'Deeper'" in d["how"] and "rule 8" in d["how"]
    off = mastered(copy.deepcopy(st), topics)
    off["config"]["evidence_ladder"] = False
    plan = cme.plan_round(off, examples.plan_options(allow_repeat=True), dt.date.fromisoformat(DAY))
    assert plan["evidence_ladder"] is False and not any("depth" in c for c in plan["items"])


# ---------------------------------------------------------------- the kit: 'Deeper' notes for such an item

def deepen(nxt, kid):
    """Give the plan's item behind key `kid` a depth beyond the first, as a ledger with a record would."""
    plan = nxt.read_json("next", "plan.json")
    headers = cme.key_headers([nxt.p("next", n) for n in cme.SEALED_FILES])[0]
    topic = headers[kid]["topic"]
    for c in plan["items"]:
        if c.get("topic") == topic or (c.get("topic") is None and c["domain"] == cme.domain_of(topic)):
            c["topic"] = topic
            c["depth"] = {"level": 3, "name": "design", "in_a_row": 2}
    nxt.write(os.path.join("next", "plan.json"), plan)


@pytest.mark.parametrize("kid,kit", [("Q1", "kit_questions.md"), ("case", "kit_case.md")])
def test_a_kit_without_deeper_notes_for_a_deep_item_blocks_the_stash(tmp_path, kid, kit):
    nxt = Next(tmp_path).setup()
    nxt.check()
    deepen(nxt, kid)
    assert "%s, key %s: no prepared block %s deeper" % (kit, kid, kid) in refused(nxt)
    path = nxt.p("next", kit)
    text = open(path, encoding="utf-8").read()
    block = "<!-- block: %s deeper -->\nSEALED the trial behind it, its comparator and endpoint.\n<!-- /block -->\n" % kid
    if kid == "case":
        text = text.replace("## Pearls", "## Deeper\n%s\n## Pearls" % block)
    else:
        text = text.replace("## Q2", "%s\n## Q2" % block)
    nxt.write(os.path.join("next", kit), text)
    _, out = nxt.finish()
    assert out["stashed"] is True


def test_deeper_notes_without_their_block_do_not_count(tmp_path):
    """The outline of before (a line "Deeper: …") is not finished text: the block is required."""
    nxt = Next(tmp_path).setup()
    nxt.check()
    deepen(nxt, "Q1")
    path = nxt.p("next", "kit_questions.md")
    text = open(path, encoding="utf-8").read()
    assert "## Q2" in text
    nxt.write(os.path.join("next", "kit_questions.md"), text.replace("## Q2", "Deeper: SEALED notes (verify)\n\n## Q2"))
    assert "kit_questions.md, key Q1: no prepared block Q1 deeper" in refused(nxt)


# ---------------------------------------------------------------- the round: what the examiner is told

class Played(Next):
    """A prepared round, published and started on the next day."""

    def begin(self, record=None):
        self.check().finish()
        self.publish()
        st = self.read_ledger()
        if record:
            record(st, cme.key_headers([self.p("next", n) for n in cme.SEALED_FILES])[0])
            self.write_ledger(st)
        self.forget_job()
        out = self.start("2026-11-03")
        assert out["prepared"]["used"] is True
        return self

    def answer(self, part):
        return self.run_json("answer", "--work", self.path, "--part", part, "--text", "what the learner wrote")


def record_all(times):
    def record(st, headers):
        st["gen"] = st.get("gen")          # the ledger's content generation is untouched: the round still fits
        for n in range(times):
            st.setdefault("previous", []).append(
                {"id": "P%04d" % n, "date": "2026-08-%02d" % (n + 1), "topics": [],
                 "items": [item(topic=h["topic"]) for h in headers.values()]})
    return record


def test_answer_gives_the_depth_of_each_question_once_they_are_answered(tmp_path):
    w = Played(tmp_path).setup().begin(record_all(2))
    out = w.answer("questions")
    assert set(out["depth"]) == {"Q1", "Q2", "Q3"}
    assert all(d == {"level": 3, "name": "design", "in_a_row": 2} for d in out["depth"].values())
    assert "depth" not in w.answer("notes")


def test_the_case_gets_its_depth_only_with_its_last_answer(tmp_path):
    w = Played(tmp_path).setup().begin(record_all(1))
    w.answer("questions")
    assert w.read_json("plan.json")["case_format"] == "unfolding"
    assert "depth" not in w.answer("case")             # Stage 2 is still to come: the case stays sealed
    assert w.answer("final")["depth"] == {"case": {"level": 2, "name": "studies", "in_a_row": 1}}


def test_a_new_learner_gets_the_first_depth_everywhere(tmp_path):
    w = Played(tmp_path).setup().begin()
    assert {d["level"] for d in w.answer("questions")["depth"].values()} == {1}


def test_with_the_ladder_off_answer_says_nothing_about_depth(tmp_path):
    w = Played(tmp_path).setup(config={"evidence_ladder": False}).begin(record_all(3))
    assert "depth" not in w.answer("questions") and "depth" not in w.answer("final")


def test_answer_still_files_the_text_where_there_is_nothing_to_read(tmp_path):
    w = Work(tmp_path)                                 # no job open, no sealed files
    out = w.run_json("answer", "--work", w.path, "--part", "questions", "--text", "B, sure")
    assert out["ok"] is True and "depth" not in out


# ---------------------------------------------------------------- the setting

def test_turning_the_ladder_off_sets_the_prepared_round_aside(tmp_path):
    w = Played(tmp_path).setup()
    w.check().finish()
    w.publish()
    w.forget_job()
    w.open(today=DAY)
    out = w.run_json("--today", DAY, "settings", "--work", w.path, "--config", '{"evidence_ladder": false}')
    assert out["prepared"]["kept"] is False and out["prepared"]["changed"] == ["evidence_ladder"]
    assert out["config"]["evidence_ladder"] is False


def test_saying_it_is_on_to_a_ledger_that_never_heard_of_it_keeps_the_prepared_round(tmp_path):
    w = Played(tmp_path).setup()
    w.check().finish()
    w.publish()
    st = w.read_ledger()
    del st["config"]["evidence_ladder"]                # a ledger written before the setting existed
    w.write_ledger(st)
    w.forget_job()
    w.open(today=DAY)
    out = w.run_json("--today", DAY, "settings", "--work", w.path, "--config", '{"evidence_ladder": true}')
    assert out["prepared"]["kept"] is True
    r = w.run("settings", "--work", w.path, "--config", '{"evidence_ladder": "deep"}', ok=False)
    assert "config.evidence_ladder must be true or false" in r.stdout

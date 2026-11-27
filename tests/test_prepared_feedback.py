"""Issue #78 (ADR 0009): the feedback is assembled from prepared, checked text and adapted live.
The kits hold finished blocks (rule 8), one per part of an item's feedback and one per rubric
element and mark; the lint requires them; once the examiner has marked the grading form (marks
before text), `draft` puts the blocks the marks call for into the feedback's order, with the
rubric as marked and the live parts left to write; `save` records in the session document only
which blocks were used as prepared, changed or left out."""
import json
import os

from examples import cme
from test_forms import answered, fill, form, item
from test_keys import CASE_KEY, Q_KEYS
from test_work_folder import rnd  # noqa: F401  (the fixture)


def text_of(bid):
    """A block's finished text: its own words throughout, so that blocks can be told apart."""
    tag = bid.replace(" ", "x").replace(".", "y").lower()
    body = "Prepared text for %s: %s." % (bid, " ".join("%s%s" % (tag, w) for w in
                                                       ("rule", "why", "holds", "guideline", "section",
                                                        "says", "so", "written", "once", "for", "every", "learner")))
    return body + (" Start a DOAC only after the bleed is excluded." if bid == "Q1 model" else "")


def blocks(kid, typ, elements=0, deeper=False):
    kinds = [(None, k) for k in cme.BLOCK_ITEM_KINDS[typ]]
    kinds += [(n, m) for n in range(1, elements + 1) for m in cme.RUBRIC_MARKS]
    if deeper:
        kinds.append((None, cme.BLOCK_DEEPER))
    out = []
    for n, k in kinds:
        bid = cme.block_id(kid, n, k)
        out.append("<!-- block: %s -->\n%s\n<!-- /block -->" % (bid, text_of(bid)))
    return "\n".join(out) + "\n"


KIT_QUESTIONS = ("## Q1\n" + blocks("Q1", "mcq", deeper=True) + "\n## Q2\n" + blocks("Q2", "focused", 2)
                 + "\n## Listening\nSources | trusted: none | avoid: none\nQ1 | points: LISTEN-POINT\n")
KIT_CASE = ("## Reveal\n## Model answer\n## Differential\n## Briefing\n" + blocks("case", "case", 3)
            + "## Pearls\n## Reading\n- READING-POINTER ESC 2023 section 9 (verify)\n")


def kits(rnd):
    rnd.write("kit_questions.md", KIT_QUESTIONS)
    rnd.write("kit_case.md", KIT_CASE)


def read(rnd, name):
    with open(os.path.join(rnd.path, name), encoding="utf-8") as fh:
        return fh.read()


def draft(rnd, part, ok=True):
    r = rnd.run("draft", "--work", rnd.path, "--part", part, ok=False)
    out = json.loads(r.stdout)
    assert (r.returncode == 0) == ok, r.stdout
    return out


def marked(rnd, q1=(True, "unsure"), q2=("hit", "missed")):
    f = form(rnd)
    i1 = item(f, "Q1")
    i1["correct"], i1["confidence"] = q1
    for e, m in zip(item(f, "Q2")["rubric"], q2):
        e["mark"], e["quote"] = m, "LP now" if m != "missed" else ""
    rnd.write("round.json", f)
    return f


# ---------------------------------------------------------------- the kit's blocks (rule 8)

def lint(questions=Q_KEYS, kit=KIT_QUESTIONS, plan=None):
    return cme.block_problems("sealed_questions.md", "kit_questions.md", questions, kit, plan)


def test_a_complete_kit_passes_and_names_no_content():
    assert lint() == []


def test_a_missing_element_block_or_item_block_is_named_by_its_id():
    kit = KIT_QUESTIONS.replace("<!-- block: Q2.2 partial -->", "<!-- block: Q2.2 parTIAL_GONE -->")
    kit = kit.replace("<!-- block: Q1 distractors -->", "<!-- block: Q1 nothing -->")
    problems = lint(kit=kit)
    assert any("key Q2: no prepared block Q2.2 partial" in p for p in problems)
    assert any("key Q1: no prepared block Q1 distractors" in p for p in problems)
    assert any("prepared blocks for no item, element or kind" in p and "Q1 nothing" in p for p in problems)
    assert not any("RUBRIC" in p or "Prepared text" in p for p in problems)


def test_an_empty_or_unclosed_block_is_refused():
    empty = KIT_QUESTIONS.replace(text_of("Q2 decisive"), "")
    assert any("no prepared block Q2 decisive" in p for p in lint(kit=empty))
    unclosed = KIT_QUESTIONS.replace("<!-- /block -->", "", 1)
    assert any("a prepared block is not closed" in p for p in lint(kit=unclosed))


def test_an_element_beyond_the_rubric_is_stray():
    kit = KIT_QUESTIONS + "<!-- block: Q2.3 hit -->\nextra\n<!-- /block -->\n"
    assert any("Q2.3 hit" in p and "for no item" in p for p in lint(kit=kit))


def test_a_deeper_block_is_required_only_where_the_plan_gives_a_depth():
    plan = {"items": [{"topic": "NEURO-04", "depth": {"level": 2}}]}
    assert any("no prepared block Q2 deeper" in p for p in lint(plan=plan))
    assert lint(plan={"items": [{"topic": "NEURO-04"}]}) == []
    assert cme.required_blocks("Q4", "focused", [{}, {}], deep=True)[-1] == "Q4 deeper"


# ---------------------------------------------------------------- the form: marks with the learner's words

def test_the_form_numbers_the_elements_and_asks_for_the_learners_words(rnd):
    out = answered(rnd, "questions")
    assert out["form"]["draft"] == "questions"
    rubric = item(form(rnd), "Q2")["rubric"]
    assert [(e["id"], e["quote"], e["mark"]) for e in rubric] == [("Q2.1", "", None), ("Q2.2", "", None)]
    how = " ".join(form(rnd)["_form"]["how"])
    assert "Marks before text" in how and "`quote`" in how and "`draft`" in how


# ---------------------------------------------------------------- the draft

def test_the_draft_is_refused_before_the_marks(rnd):
    answered(rnd, "questions")
    kits(rnd)
    out = draft(rnd, "questions", ok=False)
    assert "marks before text" in out["error"] and "Q1 correct" in out["error"]
    assert "Q2: 2 rubric element(s)" in out["error"]
    assert not os.path.exists(os.path.join(rnd.path, "draft_questions.md"))


def test_the_marks_choose_the_blocks_and_the_rubric_is_shown_with_the_learners_words(rnd):
    answered(rnd, "questions")
    kits(rnd)
    marked(rnd)
    out = draft(rnd, "questions")
    assert out["file"] == "draft_questions.md" and out["sent_as"] == "feedback_questions.md"
    assert out["final"] is False and out["blocks"] == 9
    text = read(rnd, "draft_questions.md")
    for bid in ("Q1 reveal", "Q2 reveal", "Q1 model", "Q1 distractors", "Q1 missed", "Q2 model", "Q2 decisive",
                "Q2.1 hit", "Q2.2 missed"):
        assert "<!-- block: %s -->" % bid in text and text_of(bid) in text, bid
    for bid in ("Q1 hit", "Q1 deeper", "Q2.1 missed", "Q2.1 partial", "Q2.2 hit"):
        assert "<!-- block: %s -->" % bid not in text, bid        # right but unsure: the full briefing
    assert '- ✓ RUBRIC-DECISION: lumbar puncture — "LP now"' in text
    assert "- ✗ RUBRIC-REASON: CT sensitivity falls after six hours — not in your answer" in text
    # the reveals first, then the MCQ, then the focused question; the case follows
    assert text.index("Q2 reveal") < text.index("**Q1**") < text.index("**Q2 (focused)**") < text.index("**Rubric**")
    assert text.rstrip().endswith("The case follows.")
    assert "the prepared text uses DOAC" in text                  # for the glossary line
    assert "opening with their own words" in text and "outside the key" in text
    assert "SECRET-DIAGNOSIS" not in text and "RUBRIC-DDX" not in text     # the case stays sealed


def test_the_deeper_block_comes_only_with_an_answer_given_well(rnd):
    answered(rnd, "questions")
    kits(rnd)
    f = marked(rnd, q1=(True, "sure"))
    item(f, "Q1")["given"] = {"depth": {"level": 2, "name": "studies", "in_a_row": 1}}
    rnd.write("round.json", f)
    draft(rnd, "questions")
    text = read(rnd, "draft_questions.md")
    assert "<!-- block: Q1 deeper -->" in text and "<!-- block: Q1 hit -->" in text
    f = marked(rnd, q1=(False, "sure"))
    rnd.write("round.json", f)
    draft(rnd, "questions")
    text = read(rnd, "draft_questions.md")
    assert "<!-- block: Q1 deeper -->" not in text and "<!-- block: Q1 missed -->" in text


def test_a_claim_the_check_did_not_confirm_is_flagged_above_its_blocks(rnd):
    answered(rnd, "questions")
    kits(rnd)
    rnd.write("evidence_questions.md", "### 1. a claim\n**Status:** not verified\n**Blocks:** Q2.2 missed, Q1 model\n"
                                       "### 2. another\n**Status:** confirmed\n**Blocks:** Q2 decisive\n\n"
                                       "Checked: 2026-11-01, 2 claims, 1 not verified\nKeys contradicted: 1\n")
    marked(rnd)
    out = draft(rnd, "questions")
    text = read(rnd, "draft_questions.md")
    flag = "<!-- check: claim 1 of the evidence file is not verified"
    assert text.count(flag) == 2 and out["checks"] == 2
    assert text.index(flag) < text.index("<!-- block: Q1 model -->")
    assert "claim 2" not in text and "1 key(s) contradicted" in text


def test_the_case_draft_is_the_final_message(rnd):
    answered(rnd, "questions", "case", "final")
    kits(rnd)
    f = fill(form(rnd))
    item(f, "case")["rubric"][1]["mark"] = "partial"
    rnd.write("round.json", f)
    out = draft(rnd, "case")
    assert out["file"] == "draft.md" and out["final"] is True and out["sent_as"] == "feedback.md"
    text = read(rnd, "draft.md")
    assert text.index("Stage 1") < text.index("RUBRIC-DDX") < text.index("Stage 2") < text.index("RUBRIC-MGMT")
    for bid in ("case reveal", "case model", "case.1 hit", "case.2 partial", "case.3 hit", "case differential",
                "case pearls"):
        assert "<!-- block: %s -->" % bid in text, bid
    assert "Q1 model" not in text                                 # the questions had their own message
    assert "READING-POINTER" in text and "(verify)" not in text and "gap summary" in text
    assert "the reflection prompt" in text


def test_a_round_prepared_before_blocks_drafts_with_the_gaps_marked(rnd):
    answered(rnd, "questions")
    rnd.write("kit_questions.md", "## Q1\nnotes\n## Q2\nnotes\n")
    marked(rnd)
    out = draft(rnd, "questions")
    assert out["blocks"] == 0 and out["no_prepared_text"] >= 5
    assert "[live: no prepared text for Q2.1 hit" in read(rnd, "draft_questions.md")


# ---------------------------------------------------------------- the log records what was adapted

def test_save_records_which_blocks_were_used_changed_or_left_out(rnd):
    answered(rnd, "questions", "case", "final")
    kits(rnd)
    f = fill(form(rnd))
    rnd.write("round.json", f)
    draft(rnd, "questions")
    draft(rnd, "case")
    adapted = text_of("Q2 model").replace("q2xmodelwhy q2xmodelholds q2xmodelguideline q2xmodelsection",
                                          "what your answer already argued, and the one step it lacked")
    rnd.write("feedback_questions.md", "\n\n".join([text_of("Q1 reveal"), text_of("Q2 reveal"), text_of("Q1 model"),
                                                    text_of("Q1 distractors"), text_of("Q1 hit"), adapted,
                                                    text_of("Q2.1 hit"), text_of("Q2.2 hit"),
                                                    "The case follows."]))
    rnd.write("stage2.md", "Stage 2")
    rnd.write("feedback.md", "All of it written live. [live: the gap summary]")
    out = rnd.run_json("--today", "2026-11-01", "save", "--work", rnd.path)
    counts = out["prepared_feedback"]
    doc = rnd.read_json("publish", "data", "sessions", "S0001.json")
    pf = doc["prepared_feedback"]
    assert "Q1 model" in pf["as_prepared"] and "Q2.1 hit" in pf["as_prepared"]
    assert "Q2 model" in pf["changed"]
    assert "Q2 decisive" in pf["discarded"] and "case model" in pf["discarded"]
    assert counts["offered"] == pf["offered"] == len(pf["as_prepared"] + pf["changed"] + pf["discarded"])
    assert any("[live: …]" in w and "final feedback" in w for w in out["warnings"])
    # the log only: not in the feedback, not in the ledger
    assert "prepared_feedback" not in json.dumps(rnd.read_json("publish", "data", "state.json"))
    assert "as_prepared" not in doc["transcript"] and "discarded" not in doc["transcript"]


def test_a_kit_with_blocks_but_no_draft_is_warned(rnd):
    answered(rnd, "questions", "case", "final")
    kits(rnd)
    rnd.write("round.json", fill(form(rnd)))
    rnd.write("feedback_questions.md", "Feedback")
    rnd.write("stage2.md", "Stage 2")
    rnd.write("feedback.md", "Final")
    out = rnd.run_json("--today", "2026-11-01", "save", "--work", rnd.path)
    assert "prepared_feedback" not in out
    assert any("no draft was made" in w for w in out["warnings"])


def test_block_use_by_share_of_the_text():
    sent = cme.shingles("one two three four five six seven eight nine ten")
    assert cme.block_use("one two three four five six seven eight nine ten", sent) == "as_prepared"
    assert cme.block_use("one two three four five six other words entirely here now", sent) == "changed"
    assert cme.block_use("nothing of this was sent at all, not a word", sent) == "discarded"


def test_a_case_first_round_has_one_draft_with_the_case_first(rnd):
    answered(rnd, "questions", "case", "final")
    kits(rnd)
    rnd.write("round.json", fill(form(rnd)))
    plan = rnd.read_json("plan.json")
    plan["item_order"] = "case_first"
    rnd.write("plan.json", plan)
    out = draft(rnd, "all")
    assert out["file"] == "draft.md" and out["final"] is True
    text = read(rnd, "draft.md")
    assert text.index("**Case**") < text.index("**Q1**") < text.index("**Q2 (focused)**")
    assert "The case follows." not in text and "the reflection prompt" in text

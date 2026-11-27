"""Issue #45: the simulation checks a played round against rules 5 and 6 of the rulebook
(references/standards.md) with the engine's own lint, and each feedback message for its glossary
line (rule 5.3). Scripted rounds, as in test_simulation.py: no LLM anywhere."""
import importlib.util
import json
import os

import pytest

from conftest import ROOT, SKILL
from examples import cme
from test_simulation import SIM, Script, sim
from test_sim_personas import Stops


def load_sim():
    spec = importlib.util.spec_from_file_location("simulate_under_test", SIM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


simulate = load_sim()


@pytest.fixture
def played(tmp_path):
    def play(*faults, cls=Script):
        s = cls(tmp_path, faults).play()
        out, rep = s.report()
        return s, out, rep, rep["checks"]["standards"]
    return play


def test_a_clean_round_passes_with_nothing_to_review(played):
    _, out, rep, st = played()
    assert out["ok"] is True and out["checks"]["standards"] is True
    assert st == {"ok": True, "abbreviations": 0, "time_anchors": 0, "to_review": 0, "findings": [], "problems": [],
                  "feedback": [{"id": "questions", "glossary": False, "abbreviations": 0, "not_in_glossary": []},
                               {"id": "final", "glossary": False, "abbreviations": 0, "not_in_glossary": []}]}
    md = open(out["report"], encoding="utf-8").read()
    assert "| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | pass |" in md
    assert "### Writing standards: to review" not in md


def test_an_abbreviation_not_spelled_out_in_a_stem_is_listed_for_review_without_failing(played):
    _, out, rep, st = played("abbreviation_in_stem")
    assert out["ok"] is True and st["ok"] is True and st["abbreviations"] == 1 and st["to_review"] == 1
    # AKI; not ECG (on the rulebook's list) and not TSH (spelled out where it is first used)
    assert st["findings"] == [{"rule": "5.1", "where": "the questions as presented", "detail": "AKI"}]
    md = open(out["report"], encoding="utf-8").read()
    assert "### Writing standards: to review" in md and "| 5.1 | the questions as presented | AKI |" in md


def test_mixed_time_anchors_in_a_question_are_listed_for_review(played):
    _, out, _, st = played("mixed_anchors_in_question")
    assert out["ok"] is True and st["time_anchors"] == 1
    assert st["findings"] == [{"rule": "6", "where": "question 2",
                               "detail": "from now: since this morning; by numbered day: day 3"}]


def test_stage_2_is_checked_as_it_was_sent(played):
    # the case's opening is clean; Stage 2, assembled when the Stage 1 answer came in, is not
    _, out, _, st = played("mixed_anchors_in_stage2")
    assert out["ok"] is True and st["time_anchors"] == 1 and st["abbreviations"] == 1
    assert {"rule": "5.1", "where": "Stage 2 as presented", "detail": "PEA"} in st["findings"]
    assert {"rule": "6", "where": "the case and Stage 2", "detail": "from now: yesterday; by numbered day: day 2"} in st["findings"]


def test_feedback_that_uses_abbreviations_without_the_glossary_line_fails(played):
    s, out, rep, st = played("feedback_abbreviations")
    assert out["ok"] is False and out["checks"] == {"blinding": True, "saved": True, "log": True, "standards": False, "listening": True, "prepared": True}
    assert st["problems"] == ["the questions feedback uses 2 abbreviations and does not open with the glossary line "
                              "\"Abbreviations: …\" (references/standards.md, rule 5.3)"]
    # LP and SBP; CT is on the list, and the blueprint ID in the reveal is not an abbreviation
    assert st["feedback"][0] == {"id": "questions", "glossary": False, "abbreviations": 2, "not_in_glossary": ["LP", "SBP"]}
    assert st["feedback"][1]["abbreviations"] == 0          # the final feedback uses none: no line needed
    md = open(out["report"], encoding="utf-8").read()
    assert "### Writing standards: problems" in md and "**FAIL**" in md
    assert sim("check", "--run", s.run, ok=False).returncode == 1


def test_the_glossary_line_passes_and_what_it_leaves_out_is_listed_for_review(played):
    _, out, _, st = played("feedback_abbreviations", "feedback_glossary")
    assert out["ok"] is True and st["ok"] is True and st["problems"] == []
    assert st["feedback"][0] == {"id": "questions", "glossary": True, "abbreviations": 2, "not_in_glossary": ["SBP"]}
    assert st["findings"] == [{"rule": "5.3", "where": "the questions feedback", "detail": "SBP"}]
    assert "questions: 2 abbreviation(s), glossary line present, 1 not in it" in open(out["report"], encoding="utf-8").read()


def test_a_glossary_line_on_feedback_without_abbreviations_is_no_problem(played):
    _, out, _, st = played("feedback_glossary")
    assert out["ok"] is True and st["feedback"][0] == {"id": "questions", "glossary": True, "abbreviations": 0,
                                                       "not_in_glossary": []}


def test_a_round_stopped_before_the_case_is_checked_on_what_it_had(played):
    _, out, _, st = played("abbreviation_in_stem", cls=Stops)
    assert out["checks"]["standards"] is True and [f["id"] for f in st["feedback"]] == ["questions", "final"]
    assert [f["detail"] for f in st["findings"]] == ["AKI"]


@pytest.mark.parametrize("text, found", [
    ("Abbreviations: AKI acute kidney injury\n\nReveal …", True),
    ("## Feedback: questions\n\n**Abbreviations:** DOAC direct oral anticoagulant\n\nQ1 …", True),
    ("Feedback\n\n_Abbreviations: LP lumbar puncture_\n", True),
    ("Feedback\n\nQ1 was right.\n\nQ2 too.\n\nAbbreviations: LP lumbar puncture\n", False),     # not at the top
    ("Q1 was right. Abbreviations: none.\n", False),                                          # not a line of its own
    ("", False),
])
def test_what_counts_as_the_glossary_line(text, found):
    assert bool(simulate.glossary_line(text)) is found


def test_the_heuristics_are_the_engines_and_are_not_copied():
    engine = simulate.load_engine(SKILL)
    for name in ("common_abbreviations", "undefined_abbreviations", "mixed_time_anchors", "presented_text"):
        assert getattr(engine, name).__code__.co_code == getattr(cme, name).__code__.co_code
    source = open(SIM, encoding="utf-8").read()
    for fragment in ("[A-Z]{2,6}", "hours?", "post-?op", "this\\s+morning"):
        assert fragment in open(cme.__file__, encoding="utf-8").read() and fragment not in source, fragment


def test_a_skill_copy_with_an_edited_list_is_checked_with_its_own_list(tmp_path):
    """`--skill` tests an installed copy: its rulebook's list of common abbreviations is the one used."""
    import shutil
    skill = str(tmp_path / "skill")
    shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("__pycache__"))
    path = os.path.join(skill, "references", "standards.md")
    text = open(path, encoding="utf-8").read()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("IV, IM, SC,", "IV, IM, SC, AKI,"))
    s = Script(tmp_path, ["abbreviation_in_stem"]).play()
    meta_path = os.path.join(s.run, "run.json")
    meta = json.load(open(meta_path, encoding="utf-8"))
    meta["skill"] = skill
    json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    _, rep = s.report()
    assert rep["checks"]["standards"]["findings"] == []
    assert not os.path.exists(os.path.join(skill, "scripts", "__pycache__"))     # nothing written into the skill


def test_an_engine_without_the_lint_is_a_problem_not_a_crash(tmp_path):
    skill = str(tmp_path / "old")
    os.makedirs(os.path.join(skill, "scripts"))
    with open(os.path.join(skill, "scripts", "cme.py"), "w", encoding="utf-8") as fh:
        fh.write("VERSION = 'old'\n")
    with pytest.raises(simulate.SimError, match="older than the rulebook's lint"):
        simulate.load_engine(skill)


def test_feedback_naming_the_skills_machinery_fails_the_run(played):
    _, out, _, st = played("jargon_in_feedback")
    assert out["ok"] is False and out["checks"]["standards"] is False
    assert st["problems"] == ["the questions feedback names the skill's own machinery (rule 7, standards.md, kit): "
                              "references/standards.md rule 11"]

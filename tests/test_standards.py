"""Issue #53: one numbered rulebook (references/standards.md) that the briefs cite, a key-header
table that cannot drift from cme.py, and a lint at `finish-prepare` with two categories:
definite problems block the stash, judgement calls go back to the author once and are then
accepted with a warning."""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import SKILL
from examples import cme
from test_finish_prepare import Next, edit

REFERENCES = os.path.join(SKILL, "references")
STANDARDS = os.path.join(REFERENCES, "standards.md")
BRIEFS = ["author.md", "case_design.md", "evidence_check.md", "feedback_guide.md", "preparing.md"]
RULES = ["Blinding", "Guideline region", "Units and drug names", "Pitch", "Abbreviations",
         "One time anchor per case", "Crux tests are requested, not given", "What a kit contains",
         "Key headers"]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def flat(text):
    return re.sub(r"\s+", " ", text)


@pytest.fixture
def nxt(tmp_path):
    return Next(tmp_path).setup().check()


# ---------------------------------------------------------------- the rulebook and the briefs

def test_the_rulebook_has_its_numbered_rules():
    found = re.findall(r"^## Rule (\d+)\. (.+)$", read(STANDARDS), re.M)
    assert found == [(str(i + 1), title) for i, title in enumerate(RULES)]


def test_every_rule_number_cited_anywhere_exists():
    numbers = {int(n) for n in re.findall(r"^## Rule (\d+)\.", read(STANDARDS), re.M)}
    paths = [os.path.join(SKILL, "SKILL.md"), cme.__file__]
    paths += glob.glob(os.path.join(REFERENCES, "*.md"))
    for path in paths:
        for first, last in re.findall(r"\brules? (\d+)(?:\.\d+)?(?:[–-](\d+))?", flat(read(path))):
            for n in range(int(first), int(last or first) + 1):
                assert n in numbers, "%s cites rule %d" % (os.path.basename(path), n)


def test_every_brief_cites_the_rulebook():
    for name in BRIEFS + [os.path.join("..", "SKILL.md")]:
        text = flat(read(os.path.join(REFERENCES, name)))
        assert "standards.md" in text and re.search(r"\brules? \d", text), name


@pytest.mark.parametrize("sentence", [
    # one sentence of each rule that used to be restated in the briefs
    "Icelandic national guidance where it exists",                 # rule 2
    "mmol/L, µmol/L, g/L",                                         # rule 3
    "anion gap, corrected calcium",                                # rule 3
    "international non-proprietary name",                          # rule 3
    "organ system or blueprint ID",                                # rule 1
    "the two-line version for a correct, sure answer",             # rule 8
    "one `field: value` per line",                                 # rule 9
])
def test_rule_text_is_written_once(sentence):
    holders = [os.path.basename(p) for p in glob.glob(os.path.join(REFERENCES, "*.md")) + [os.path.join(SKILL, "SKILL.md")]
               if sentence.lower() in flat(read(p)).lower()
               and os.path.basename(p) != "onboarding.md"]       # setup describes the settings a learner chooses
    assert holders == ["standards.md"], (sentence, holders)


def test_key_header_blocks_are_shown_only_in_the_rulebook_and_the_schema():
    """The header's form is an example in the rulebook; no brief carries a second copy."""
    for name in BRIEFS:
        assert "<!-- key: Q" not in read(os.path.join(REFERENCES, name)), name
    assert "<!-- key: Q1 -->" in read(STANDARDS)


def test_slots_for_the_issues_that_build_on_the_rulebook():
    text = read(STANDARDS)
    assert "slot: issue #45" not in text          # filled in: see the tests of issue #45 below
    assert "slot: issue #55" not in text          # filled in: tests/test_learner_settings.py
    # issue #50 filled its slot in rule 8: the "## Listening" section of the kits
    assert "slot: issue #50" not in text and "**Listening** (`## Listening`" in text


# ---------------------------------------------------------------- issue #45: rules 5–7 finished

def rule(n):
    return flat(read(STANDARDS).split("## Rule %d." % n)[1].split("## Rule %d." % (n + 1))[0])


def test_rule_7_says_what_a_crux_test_is_and_carries_its_example():
    text = rule(7)
    assert "What counts as a crux test" in text and "How to decide" in text
    assert "S0037" in text and "valproate" in text and "ammonia" in text
    assert "aspect `testing`" in text and "Add if not ordered" in text


def test_the_pre_flight_has_a_line_for_each_of_rules_5_to_7():
    design = read(os.path.join(REFERENCES, "case_design.md"))
    preflight = design.split("## 8. Pre-flight check")[1].split("\n## 9.")[0]
    assert re.findall(r"^(\d+)\. Rule (\d):", preflight, re.M) == [("14", "5"), ("15", "6"), ("16", "7")]
    # both sealed files carry them, and the author's brief names the same line numbers
    assert "lines 6 and 10–16" in flat(preflight) and "lines 1–5, 7–9 and 14–16" in flat(preflight)
    author = flat(read(os.path.join(REFERENCES, "author.md")))
    assert "lines 6 and 10–16" in author and "lines 1–5, 7–9 and 14–16" in author
    # the rules are cited, not restated
    assert "alanine aminotransferase" not in preflight and "valproate" not in design


def test_the_glossary_line_opens_every_feedback_message():
    assert '"Abbreviations:"' in rule(5)
    guide = flat(read(os.path.join(REFERENCES, "feedback_guide.md")).split("## 2. Structure")[1].split("### A.")[0])
    assert "Every feedback message starts with the glossary line" in guide and "rule 5.3" in guide
    assert guide.count("glossary line, A") == 2
    skill = flat(read(os.path.join(SKILL, "SKILL.md")))
    assert "glossary line, rule 5.3 → reveal" in skill and "glossary line → case reveal" in skill


# ---------------------------------------------------------------- the key-header table

def table_in_the_rulebook():
    text = read(STANDARDS)
    assert text.count(cme.KEY_TABLE_OPEN) == 1 and text.count(cme.KEY_TABLE_CLOSE) == 1
    return text.split(cme.KEY_TABLE_OPEN)[1].split(cme.KEY_TABLE_CLOSE)[0].strip()


def test_the_table_in_the_rulebook_is_the_one_cme_py_generates():
    assert table_in_the_rulebook() == cme.key_header_table(), \
        "run `python3 skills/clinical-cme/scripts/cme.py key-table` and paste its output into standards.md"


def test_the_key_table_command_prints_it():
    r = subprocess.run([sys.executable, cme.__file__, "key-table"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "%s\n%s\n%s" % (
        cme.KEY_TABLE_OPEN, cme.key_header_table(), cme.KEY_TABLE_CLOSE)


def test_the_table_follows_the_key_definitions():
    rows = {}
    for line in cme.key_header_table().splitlines()[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows[cells[0].strip("`")] = dict(zip(cme.KEY_TYPES, cells[1:4]))
    every = set(cme.KEY_COMMON) | set(cme.KEY_ANY)
    for typ in cme.KEY_TYPES:
        every |= set(cme.KEY_REQUIRED[typ]) | set(cme.KEY_OPTIONAL[typ])
    assert set(rows) == every == set(cme.KEY_FIELD_NOTES)
    assert every == set(cme.KEY_ITEM_FIELDS) | set(cme.KEY_CASE_FIELDS) | {"reason"}
    for field, by_type in rows.items():
        for typ, cell in by_type.items():
            required = field in cme.KEY_COMMON or field in cme.KEY_REQUIRED[typ]
            optional = field in cme.KEY_ANY or field in cme.KEY_OPTIONAL[typ]
            assert cell == ("required" if required else "optional" if optional else "–"), (field, typ)


def test_a_changed_definition_changes_the_table(monkeypatch):
    monkeypatch.setattr(cme, "KEY_OPTIONAL", {"mcq": (), "focused": (), "case": ()})
    monkeypatch.setattr(cme, "KEY_REQUIRED", dict(cme.KEY_REQUIRED, case=cme.KEY_REQUIRED["case"] + ("twist",)))
    assert cme.key_header_table() != table_in_the_rulebook()


def test_the_header_the_parser_accepts_is_the_one_in_the_rulebook():
    """The examples of rule 9 parse cleanly, so the rulebook shows what the engine reads."""
    examples = "\n".join(re.findall(r"^```\n(.*?)^```", read(STANDARDS), re.S | re.M))
    headers, problems = cme.parse_key_headers(examples, "standards.md")
    assert problems == [] and set(headers) == {"Q1", "Q4", "case"}


def test_the_kit_sections_of_the_rulebook_are_the_ones_the_lint_requires():
    rule = read(STANDARDS).split("## Rule 8.")[1].split("## Rule 9.")[0]
    assert re.findall(r"^\| `## (.+?)` \|", rule, re.M) == list(cme.KIT_CASE_SECTIONS)
    # "Listening" is a section of both kits, required unless the plan has listening off (issue #50)
    assert "`## Q1`" in rule and "`## Listening`" in rule and cme.KIT_LISTENING == "Listening"
    assert "Listening" not in cme.KIT_CASE_SECTIONS and "slot: issue #50" not in rule


# ---------------------------------------------------------------- the lint: definite problems block

def refused(nxt, *extra):
    r, out = nxt.finish(*extra, ok=False)
    assert r.returncode != 0 and out["ok"] is False and "stashed" not in out
    assert "Nothing was stashed" in out["error"] and not nxt.stashed()
    return out["error"]


def test_the_example_round_passes_the_lint(nxt):
    _, out = nxt.finish()
    assert out["stashed"] is True and out["revise"] is False and "warnings" not in out
    assert out["lint"] == {"abbreviations": 0, "time_anchors": 0}
    assert not os.path.exists(nxt.p("next", "lint.md"))


@pytest.mark.parametrize("section", cme.KIT_CASE_SECTIONS)
def test_a_missing_section_of_the_case_kit_blocks_the_stash(nxt, section):
    edit(nxt, "kit_case.md", "## %s\n" % section, "")
    error = refused(nxt)
    assert "the kits are not complete" in error and "kit_case.md: section '%s' missing" % section in error
    assert "standards.md, rule 9 for key headers, rule 8 for kits" in error


def test_a_question_without_its_kit_section_blocks_the_stash(nxt):
    edit(nxt, "kit_questions.md", "## Q2\n", "")
    assert "kit_questions.md: no section for Q2" in refused(nxt)


@pytest.mark.parametrize("kit", ["kit_questions.md", "kit_case.md"])
def test_a_missing_kit_blocks_the_stash(nxt, kit):
    os.remove(nxt.p("next", kit))
    assert "%s is missing" % kit in refused(nxt)


def test_a_round_without_a_case_keeps_its_reading_pointers_in_the_questions_kit(tmp_path):
    nxt = Next(tmp_path).setup(config={"case": False}).check(case=None)
    edit(nxt, "kit_questions.md", "## Reading\n", "")
    assert "kit_questions.md: section 'Reading' missing" in refused(nxt)


def test_blocking_problems_are_all_named_and_no_revision_gets_past_them(nxt):
    edit(nxt, "kit_case.md", "## Rubric\n", "")
    edit(nxt, "sealed_questions.md", "stem_summary: Example stem Q1\n", "")
    for extra in ((), ("--revised",), ("--no-evidence",)):
        error = refused(nxt, *extra)
        assert "key Q1: 'stem_summary' is missing" in error and "section 'Rubric' missing" in error
    # corrected, the same command stashes
    edit(nxt, "kit_case.md", "## Reading\n", "## Rubric\n## Reading\n")
    edit(nxt, "sealed_questions.md", "type: mcq\n", "type: mcq\nstem_summary: Example stem Q1\n")
    _, out = nxt.finish()
    assert out["stashed"] is True


def test_headings_may_be_of_any_level_and_longer_than_the_name(nxt):
    text = read(nxt.p("next", "kit_case.md"))
    text = text.replace("## Rubric\n", "### Rubric — Stage 1 and Stage 2\n").replace("## Reading\n", "# Reading pointers:\n")
    text = text.replace("## Briefing\n", "## Briefings\n").replace("## Pearls\n", "## **Pearl**\n")
    nxt.write(os.path.join("next", "kit_case.md"), text)
    _, out = nxt.finish()
    assert out["stashed"] is True


# ---------------------------------------------------------------- the lint: judgement calls, one revision

ABBREV = "Q1. A man on DOAC therapy with raised ALT has an ECG. A) one B) two C) three"
MIXED = ("A woman was admitted with fever. On day 3 she became confused; her last dose was 6 hours ago. "
         "What do you do first?")


def with_abbreviations(nxt):
    edit(nxt, "sealed_questions.md", "Q1. Example stem 1. A) one B) two C) three", ABBREV)
    return nxt


def with_mixed_anchors(nxt):
    edit(nxt, "sealed_case.md", "An example patient presents. What do you do first?", MIXED)
    return nxt


def test_an_undefined_abbreviation_goes_back_to_the_author_once(nxt):
    _, out = with_abbreviations(nxt).finish()
    assert out["ok"] and out["revise"] is True and out["stashed"] is False and not nxt.stashed()
    assert out["contradicted"] == 0
    assert out["lint"]["abbreviations"] == 2 and out["lint"]["time_anchors"] == 0     # DOAC and ALT, not ECG
    assert out["lint"]["where"] == ["sealed_questions.md: 2 abbreviations not spelled out at first use "
                                    "(references/standards.md, rule 5)"]
    assert "revise" in out["next"] and "lint.md" in out["next"] and "--revised" in out["next"]
    # what was found is in the author's file, not in the output
    details = read(nxt.p("next", "lint.md"))
    assert out["lint"]["details"] == nxt.p("next", "lint.md")
    assert "sealed_questions.md, questions block: DOAC" in details and ": ALT" in details and "ECG" not in details
    assert "DOAC" not in json.dumps(out) and "ALT" not in json.dumps(out)


def test_the_author_corrects_it_and_the_round_is_stashed_clean(nxt):
    with_abbreviations(nxt).finish()
    edit(nxt, "sealed_questions.md", "on DOAC therapy with raised ALT",
         "on direct oral anticoagulant (DOAC) therapy with raised ALT (alanine aminotransferase); DOAC and ALT again")
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True and out["revised"] is True and out["revise"] is False
    assert out["lint"] == {"abbreviations": 0, "time_anchors": 0} and "warnings" not in out
    assert not os.path.exists(nxt.p("next", "lint.md"))


def test_what_the_lint_still_finds_after_the_revision_is_accepted_with_a_warning(nxt):
    with_abbreviations(nxt).finish()
    _, out = nxt.finish("--revised")                        # the author left it: a false finding, or a miss
    assert out["stashed"] is True and nxt.stashed() and out["revise"] is False
    assert out["warnings"] == ["accepted after one revision: sealed_questions.md: 2 abbreviations not spelled "
                               "out at first use (references/standards.md, rule 5)"]
    assert out["lint"]["abbreviations"] == 2
    assert "lint.md" not in nxt.payload()["files"]          # the author's file is not part of the round


def test_mixed_time_anchors_go_back_to_the_author_once(nxt):
    _, out = with_mixed_anchors(nxt).finish()
    assert out["revise"] is True and out["stashed"] is False
    assert out["lint"] == {"abbreviations": 0, "time_anchors": 1, "details": nxt.p("next", "lint.md"),
                           "where": ["sealed_case.md: time anchors look mixed in 1 place "
                                     "(references/standards.md, rule 6)"]}
    details = read(nxt.p("next", "lint.md"))
    assert '"6 hours ago"' in details and '"day 3"' in details and "Rule 6" in details
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True and out["warnings"][0].startswith("accepted after one revision: sealed_case.md: time")


def test_a_contradicted_key_and_a_judgement_call_share_the_one_revision(nxt):
    _, out = with_abbreviations(nxt.check(questions=1)).finish()
    assert out["revise"] is True and out["contradicted"] == 1 and out["lint"]["abbreviations"] == 2
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True and out["contradicted"] == 1 and len(out["warnings"]) == 1


def test_the_lint_runs_without_a_checker_too(nxt):
    _, out = with_abbreviations(nxt).finish("--no-evidence")
    assert out["revise"] is True and out["stashed"] is False and out["evidence"] == "not checked"
    _, out = nxt.finish("--no-evidence", "--revised")
    assert out["stashed"] is True and out["warnings"]


def test_the_lint_prints_nothing_of_the_content(nxt):
    with_mixed_anchors(with_abbreviations(nxt))
    for extra in ((), ("--revised",)):
        r, _ = nxt.finish(*extra)
        shown = (r.stdout + r.stderr).replace(nxt.path, "")
        for word in ("DOAC", "ALT", "hours ago", "day 3", "SEALED", "Example"):
            assert word not in shown, word


def test_the_authors_check_runs_the_same_lint(nxt):
    with_abbreviations(nxt)
    edit(nxt, "kit_case.md", "## Pearls\n", "")
    r = nxt.run("keys", nxt.p("next"), "--plan", nxt.p("next", "plan.json"), ok=False)
    out = json.loads(r.stdout)
    assert r.returncode == 1 and out["ok"] is False
    assert out["problems"] == ["kit_case.md: section 'Pearls' missing (a heading for each: '## Pearls')"]
    assert out["review"] == ["sealed_questions.md: 2 abbreviations not spelled out at first use "
                             "(references/standards.md, rule 5)"]
    assert out["details"] == nxt.p("next", "lint.md") and "DOAC" not in r.stdout
    # judgement calls alone do not fail the author's check, and a kit not written yet is no problem there
    edit(nxt, "kit_case.md", "## Reading\n", "## Pearls\n## Reading\n")
    os.remove(nxt.p("next", "kit_questions.md"))
    out = nxt.run_json("keys", nxt.p("next"), "--plan", nxt.p("next", "plan.json"))
    assert out["ok"] is True and out["problems"] == [] and len(out["review"]) == 1


# ---------------------------------------------------------------- the heuristics

def shown(questions=None, case=None, bank=None):
    files = {}
    if questions:
        files["sealed_questions.md"] = "<!-- present: questions -->\n%s\n<!-- /present -->\n" % questions
    if case:
        files["sealed_case.md"] = "<!-- present: case -->\n%s\n<!-- /present -->\n" % case
        if bank:
            files["sealed_case.md"] += "<!-- bank -->\n%s\n<!-- /bank -->\n" % bank
    return cme.presented_text(files)


def abbreviations(common=("ECG", "CT"), **blocks):
    return [(name, block, token) for name, block, token in cme.undefined_abbreviations(shown(**blocks), set(common))]


@pytest.mark.parametrize("text, found", [
    ("Raised ALT and AST.", ["ALT", "AST"]),
    ("Raised ALT (alanine aminotransferase).", []),                     # expansion in brackets after it
    ("Raised alanine aminotransferase (ALT).", []),                     # in brackets after its expansion
    ("Two ECGs and a CT were normal.", []),                             # on the list; a plural s is allowed
    ("Two DOACs were stopped.", ["DOAC"]),
    ("NYHA class III, stage IV disease.", ["NYHA"]),                    # Roman numerals are not abbreviations
    ("A 74F with HbA1c 60, pH 7.31, SpO2 91%, T2DM.", []),              # only runs of capitals count
    ("Seen in ED. ED staff gave fluids in ED.", ["ED"]),                # each abbreviation once
    ("An A, a B, an ABCDEFG.", []),                                     # two to six letters
    ("NT-proBNP was raised.", ["NT"]),
])
def test_what_counts_as_an_undefined_abbreviation(text, found):
    assert [t for _, _, t in abbreviations(questions=text)] == found


def test_an_abbreviation_is_defined_once_per_session_in_the_order_presented():
    # defined in the questions: fine in the case and the bank
    assert abbreviations(questions="Raised alanine aminotransferase (ALT).", case="ALT again.", bank="ALT 80.") == []
    # defined only later: the first use is the one that counts
    assert abbreviations(questions="ALT raised.", case="alanine aminotransferase (ALT)") == [
        ("sealed_questions.md", "questions", "ALT")]
    # the results bank is presented text too
    assert abbreviations(case="A man presents.", bank="INR 1.1; APTT 30 s") == [
        ("sealed_case.md", "bank", "INR"), ("sealed_case.md", "bank", "APTT")]


def test_keys_and_notes_outside_the_blocks_are_not_presented_text():
    files = {"sealed_questions.md": "KEY: DKA, treat with FRIII\n<!-- present: questions -->\nQ1. stem\n<!-- /present -->\n"}
    assert cme.lint_round(files, kits_required=False)["review"] == []


def anchors(**blocks):
    return [(name, where) for name, where, _, _ in cme.mixed_time_anchors(shown(**blocks))]


@pytest.mark.parametrize("text, mixed", [
    ("Admitted with fever. On day 3 she became confused. Day 5: rash.", False),          # one anchor: admission
    ("Pain started 3 hours ago; he vomited twice since this morning.", False),            # one anchor: now
    ("On day 3 she became confused; her last dose was 6 hours ago.", True),
    ("On the third postoperative day he is breathless since this morning.", True),
    ("Hospital day 2. He felt well yesterday.", True),
    ("POD 2; drain removed two days ago.", True),
    ("On day 3 he is febrile. He stopped smoking 10 years ago and had surgery 6 months ago.", False),
    ("Symptoms began two days before admission; on day 2 of admission he worsened.", False),
    ("He takes one tablet a day and was seen a few weeks ago.", False),
])
def test_what_counts_as_mixed_time_anchors(text, mixed):
    assert bool(anchors(case=text)) is mixed


def test_time_anchors_are_judged_per_question_and_per_case():
    # two questions may each have their own anchor
    assert anchors(questions="Question 1\nPain began 3 hours ago.\n\nQuestion 2\nOn day 3 of admission she is confused.") == []
    assert anchors(questions="Q1. Fine.\nQ2. On day 3 the pain that began 2 hours ago returned.") == [
        ("sealed_questions.md", "question 2")]
    # the case and its results bank are one case
    assert anchors(case="Chest pain since this morning.", bank="Course: on day 2 he deteriorates.") == [
        ("sealed_case.md", "the case (present block and bank)")]


# ---------------------------------------------------------------- the editable list

def test_the_list_of_common_abbreviations_is_read_from_the_rulebook():
    assert cme.common_abbreviations() == {"IV", "ECG", "CT", "MRI", "HIV", "BP", "HR", "CRP", "ICU"}
    assert cme.STANDARDS_FILE == STANDARDS
    # the engine keeps no second copy of the list
    source = read(cme.__file__)
    assert '"ECG"' not in source and "'ECG'" not in source


def test_editing_the_list_in_the_rulebook_changes_what_the_lint_flags(tmp_path):
    rulebook = str(tmp_path / "standards.md")
    with open(rulebook, "w", encoding="utf-8") as fh:
        fh.write(read(STANDARDS).replace("IV, ECG, CT,", "IV, CT, ALT,"))
    assert cme.common_abbreviations(rulebook) == {"IV", "CT", "ALT", "MRI", "HIV", "BP", "HR", "CRP", "ICU"}
    files = {"sealed_questions.md": "<!-- present: questions -->\nQ1. ALT raised; ECG normal.\n<!-- /present -->\n"}
    assert [r["detail"] for r in cme.lint_round(files, kits_required=False)["review"]] == ["ALT"]
    assert [r["detail"] for r in cme.lint_round(files, kits_required=False, standards=rulebook)["review"]] == ["ECG"]


def test_an_installed_skill_with_an_edited_list_lints_with_it(tmp_path):
    """End to end: the copy of the skill that runs reads the list from its own rulebook."""
    skill = str(tmp_path / "skill")
    shutil.copytree(SKILL, skill, ignore=shutil.ignore_patterns("__pycache__"))
    path = os.path.join(skill, "references", "standards.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(read(STANDARDS).replace("IV, ECG, CT,", "IV, ECG, CT, DOAC, ALT,"))
    os.mkdir(str(tmp_path / "work"))
    nxt = with_abbreviations(Next(tmp_path / "work").setup().check())
    assert nxt.finish()[1]["lint"]["abbreviations"] == 2
    r = subprocess.run([sys.executable, os.path.join(skill, "scripts", "cme.py"), "finish-prepare", "--work", nxt.path],
                       capture_output=True, text=True)
    out = json.loads(r.stdout)
    assert out["stashed"] is True and out["lint"] == {"abbreviations": 0, "time_anchors": 0}


def test_a_rulebook_without_its_list_is_reported_not_guessed(tmp_path):
    rulebook = str(tmp_path / "standards.md")
    with open(rulebook, "w", encoding="utf-8") as fh:
        fh.write("# no list here\n")
    assert cme.common_abbreviations(rulebook) is None and cme.common_abbreviations(str(tmp_path / "none.md")) is None
    files = {"sealed_questions.md": "<!-- present: questions -->\nQ1. ALT raised.\n<!-- /present -->\n"}
    lint = cme.lint_round(files, kits_required=False, standards=rulebook)
    assert lint["review"] == [] and "could not be read" in lint["notes"][0]

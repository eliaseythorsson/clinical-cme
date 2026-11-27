"""The main skill file stays short, keeps the blinding rules itself, and points only at
reference files that exist (issue #14)."""
import glob
import os
import re

from conftest import ROOT, SKILL

SKILL_MD = os.path.join(SKILL, "SKILL.md")
REFERENCES = os.path.join(SKILL, "references")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def flat(text):
    return re.sub(r"\s+", " ", text)


def test_skill_file_is_about_250_lines():
    assert len(read(SKILL_MD).splitlines()) <= 260


def test_blinding_rules_are_in_the_skill_file_itself():
    text = flat(read(SKILL_MD))
    # the examiner never marks its own items
    assert "You never mark your own items" in text
    # before Stage 2 the examiner reads only the results bank
    assert "Before Stage 2 you read only the case's results bank" in text
    assert "present --block bank" in text
    # a sealed file is opened only when its part is answered; `present` never shows a key
    assert "only when that part's answers are in" in text
    assert "which never contains a key" in text
    assert "Do not open `sealed_case.md`, `kit_case.md` or `evidence_case.md` until the final answers" in text


def test_moved_sections_have_a_reference_file_and_a_pointer():
    text = read(SKILL_MD)
    for name, headings in {"preparing.md": ["After the close", "Prepare only", "Always-ready rounds"],
                           "requests.md": ["Requests", "Testing mode", "Round variants"]}.items():
        assert "references/%s" % name in text
        body = read(os.path.join(REFERENCES, name))
        for heading in headings:
            assert re.search(r"^## \d+\. %s" % re.escape(heading), body, re.M), (name, heading)
    assert "## 5. FAQ" in read(os.path.join(REFERENCES, "onboarding.md"))
    assert "onboarding.md" in text and "FAQ" in text


def test_every_reference_file_named_exists():
    names = {os.path.basename(p) for p in glob.glob(os.path.join(REFERENCES, "*.md"))}
    for path in [SKILL_MD, os.path.join(SKILL, "README.md")] + glob.glob(os.path.join(REFERENCES, "*.md")):
        for name in re.findall(r"references/([a-z_]+\.md)", read(path)):
            assert name in names, "%s names %s" % (os.path.basename(path), name)
    # every reference file is listed in the skill file's table, so it is found when needed
    table = read(SKILL_MD)
    for name in names:
        assert "`references/%s`" % name in table, name


def test_section_pointers_into_the_new_references_exist():
    """`preparing.md` §N and `requests.md` §N, wherever they are written, name a real section."""
    sections = {name: set(re.findall(r"^## (\d+)\.", read(os.path.join(REFERENCES, name)), re.M))
                for name in ("preparing.md", "requests.md")}
    for path in [SKILL_MD] + glob.glob(os.path.join(REFERENCES, "*.md")):
        for name, first, last in re.findall(r"`(preparing\.md|requests\.md)`\s+§(\d+)(?:–(\d+))?", flat(read(path))):
            for n in range(int(first), int(last or first) + 1):
                assert str(n) in sections[name], "%s points at %s §%d" % (os.path.basename(path), name, n)


def test_listening_is_described_where_each_reader_looks_for_it():
    """Issue #50: the kit section in the rulebook, the search in the checker's brief, the
    selection rule in the feedback guide, the settings and the limits of Spotify."""
    refs = os.path.join(os.path.dirname(SKILL_MD), "references")
    doc = lambda name: read(os.path.join(refs, name))
    rule8 = doc("standards.md").split("## Rule 8.")[1].split("## Rule 9.")[0]
    assert "Three candidates per topic" in rule8 and "https://open.spotify.com/episode/<id>" in rule8
    assert "no link that saves an episode" in rule8 and "A link that was not reached is not kept" in rule8
    checker = doc("evidence_check.md")
    assert "## 6. Listening: candidate podcast episodes" in checker and "rule 8 of `standards.md`" in checker
    assert "Podcast Index" in checker and "the episode is not kept" in checker
    guide = doc("feedback_guide.md")
    assert "### E2. Listening" in guide and "with no new search" in guide and "No suitable episode found" in guide
    assert "`listening.ask_sources` true" in guide
    assert "## Listening" in doc("author.md") and "podcast_sources" in doc("onboarding.md")
    assert '"listening": false' in doc("requests.md") and "podcast_sources" in doc("requests.md")
    assert "`listening`" in doc("session_log.md")
    # reading pointers as data, for the page's Reading & listening view (issue #51)
    assert "`round.json` as `reading`" in guide and "`reading`" in doc("session_log.md")
    assert "- `reading`:" in doc("state_schema.md") and "- `library`:" in doc("state_schema.md")
    skill = read(SKILL_MD)
    assert "`listening.on`" in skill and "`podcast_sources`" in skill
    assert "`reading` and `listening` only" in skill


def test_evidence_depth_is_described_where_each_reader_looks_for_it():
    """The examiner's rule in the feedback guide, the kit's notes in the rulebook, the author's
    and the checker's briefs, the setting, the figures in the schema; the names are the engine's."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("cme", os.path.join(SKILL, "scripts", "cme.py"))
    cme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cme)
    doc = lambda name: read(os.path.join(REFERENCES, name))
    guide = doc("feedback_guide.md")
    assert "### 4.1 Evidence depth" in guide and "Missed today → the first depth, in full" in guide
    schema = doc("state_schema.md")
    assert "### 4.2 Evidence depth" in schema
    for n, (name, need) in enumerate(cme.EVIDENCE_DEPTHS, 1):
        assert "| %d `%s` | %d" % (n, name, need) in guide, name      # the table's levels and thresholds
        assert "%d `%s` (%d" % (n, name, need) in schema, name
    rule8 = doc("standards.md").split("## Rule 8.")[1].split("## Rule 9.")[0]
    assert "**Deeper**" in rule8 and "put on the verification list" in rule8 and "`deeper`" in rule8
    assert "feedback_guide.md` §4.1" in doc("standards.md").split("## Rule 4.")[1].split("## Rule 5.")[0]
    assert "`depth`" in doc("author.md") and "`deeper` block" in doc("evidence_check.md")
    assert '"evidence_ladder": false' in doc("requests.md") and "`evidence_ladder` false" in doc("onboarding.md")
    assert "**Evidence depth**" in read(os.path.join(ROOT, "CONTEXT.md"))
    assert "`depth`" in doc("state_schema.md") and "`given`" in doc("feedback_guide.md")


def test_the_examiner_reads_one_brief_before_grading():
    """Issue #77: what the examiner needs to grade and write feedback is in feedback_guide.md; the
    rulebook keeps the item rules and points there for 5.3, 10 and 11; the coding moved too."""
    skill = read(SKILL_MD)
    row = next(line for line in skill.splitlines() if line.startswith("| `references/feedback_guide.md`"))
    assert "Before grading, and nothing else" in row
    for name in ("standards.md", "analysis_framework.md"):
        row = next(line for line in skill.splitlines() if "`references/%s`" % name in line)
        assert "Before grading" not in row, name
    guide = read(os.path.join(REFERENCES, "feedback_guide.md"))
    for heading in ("## 9. Prepared text and live text", "### 9.1 Marks before text", "### 9.2 The draft",
                    "### 10.1 The glossary line (rule 5.3)", "### 10.2 Results the learner did not see (rule 10)",
                    "### 10.3 Text for the learner speaks plainly (rule 11)", "## 11. Coding a round",
                    "### 11.3 Errors", "**Tailoring always wins over speed.**"):
        assert heading in guide, heading
    standards = read(os.path.join(REFERENCES, "standards.md"))
    for n, section in ((10, "§10.2"), (11, "§10.3")):
        body = standards.split("## Rule %d." % n)[1].split("## Rule %d." % (n + 1))[0]
        assert "`feedback_guide.md` %s" % section in body and len(body.split()) < 80, n
    # the coding is written once, in the brief
    analysis = read(os.path.join(REFERENCES, "analysis_framework.md"))
    assert "`feedback_guide.md` §11" in analysis and "| `DG` |" not in analysis and "| `DG` |" in guide
    assert os.path.isfile(os.path.join(ROOT, "docs", "adr", "0009-prepared-feedback-adapted-live.md"))


def test_prepared_feedback_is_described_where_each_reader_looks_for_it():
    """Issue #78: the blocks in the rulebook, the draft in the brief, the record in the log, the
    checker's Blocks line, the simulation's examiner prompt."""
    doc = lambda name: read(os.path.join(REFERENCES, name))
    rule8 = doc("standards.md").split("## Rule 8.")[1].split("## Rule 9.")[0]
    assert "<!-- block: Q4.2 missed -->" in rule8 and "`n missed`, `n partial` and `n hit`" in rule8
    assert "cme.py draft" in flat(doc("feedback_guide.md")) and "`prepared_feedback`" in doc("session_log.md")
    assert "**Blocks:**" in doc("evidence_check.md") and "prepared blocks" in doc("author.md")
    assert "draft --work <work> --part questions" in flat(read(SKILL_MD))
    examiner = read(os.path.join(ROOT, "sim", "prompts", "examiner.md"))
    assert "cme.py draft" in examiner and "`quote`" in examiner
    context = read(os.path.join(ROOT, "CONTEXT.md"))
    for term in ("**Prepared block**", "**Marks before text**", "**Draft**", "**Live part**"):
        assert term in context, term

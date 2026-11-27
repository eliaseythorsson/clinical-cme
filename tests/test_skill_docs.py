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
                           "prepare_only.md": ["Prepare only", "Always-ready rounds"],
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
                for name in ("preparing.md", "requests.md", "prepare_only.md")}
    for path in [SKILL_MD] + glob.glob(os.path.join(REFERENCES, "*.md")):
        for name, first, last in re.findall(r"`(preparing\.md|requests\.md|prepare_only\.md)`\s+§(\d+)(?:–(\d+))?", flat(read(path))):
            for n in range(int(first), int(last or first) + 1):
                assert str(n) in sections[name], "%s points at %s §%d" % (os.path.basename(path), name, n)


def test_section_pointers_into_the_split_references_exist():
    """Issue #92: the references were split so that each turn reads only what it uses; every
    `file.md` §N (or section N) written in the skill, the engine or the simulation's prompts names
    a section that exists in that file, so a pointer never sends a reader to the wrong place."""
    names = ("feedback_guide.md", "grading.md", "coding.md", "disputes.md", "publishing.md", "store.md",
             "evidence_check.md", "analysis_framework.md", "session_log.md")
    sections = {name: set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)\.? ", read(os.path.join(REFERENCES, name)), re.M))
                for name in names}
    paths = [SKILL_MD, os.path.join(SKILL, "scripts", "cme.py")] + glob.glob(os.path.join(REFERENCES, "*.md"))
    paths += glob.glob(os.path.join(ROOT, "sim", "prompts", "*.md"))
    pattern = r"(%s)`?\s+(?:§|section )(\d+(?:\.\d+)?)(?:–(\d+(?:\.\d+)?))?" % "|".join(re.escape(n) for n in names)
    found = 0
    for path in paths:
        for name, first, last in re.findall(pattern, flat(read(path))):
            for n in filter(None, (first, last)):
                assert n in sections[name] or any(s.startswith(n + ".") for s in sections[name]), \
                    "%s points at %s §%s" % (os.path.basename(path), name, n)
                found += 1
    assert found > 40


def test_listening_is_described_where_each_reader_looks_for_it():
    """Issue #50: the kit section in the rulebook, the search in the checker's brief, the
    selection rule in the feedback guide, the settings and the limits of Spotify."""
    refs = os.path.join(os.path.dirname(SKILL_MD), "references")
    doc = lambda name: read(os.path.join(refs, name))
    # rule 8's Listening section, in its own file for the checkers (#92); rule 8 points there
    rule8 = doc("standards_kits.md")                    # rule 8, in its own file (#92)
    assert "**Listening** (`## Listening`" in rule8 and "`standards_listening.md`" in rule8
    listening_rule = doc("standards_listening.md")
    assert "Three candidates per topic" in listening_rule and "https://open.spotify.com/episode/<id>" in listening_rule
    assert "no link that saves an episode" in listening_rule and "A link that was not reached is not kept" in listening_rule
    checker = doc("evidence_check.md")
    assert "## 6. Listening: candidate podcast episodes" in checker and "rule 8's Listening section (`standards_listening.md`)" in checker
    assert "Podcast Index" in checker and "the episode is not kept" in checker
    guide = doc("feedback_guide.md")
    assert "### E2. Listening" in guide and "`listening.md`" in guide         # the pick, in its own file (#92)
    listening = doc("listening.md")
    assert "with no new search" in listening and "No suitable episode found" in listening
    assert "`listening.ask_sources` true" in listening
    assert "## Listening" in doc("author.md") and "podcast_sources" in doc("onboarding.md")
    assert '"listening": false' in doc("requests.md") and "podcast_sources" in doc("requests.md")
    assert "`listening`" in doc("session_log.md")
    # reading pointers as data, for the page's Reading & listening view (issue #51)
    assert "`round.json` as `reading`" in guide and "`reading`" in doc("session_log.md")
    assert "`round.json` as `listening`" in listening
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
    assert "### 4.1 Evidence depth" in guide and "`evidence_depth.md`" in guide    # its own file (#92)
    depth = doc("evidence_depth.md")
    assert "# Evidence depth" in depth and "Missed today → the first depth, in full" in depth
    schema = doc("state_schema.md")
    assert "### 4.2 Evidence depth" in schema
    for n, (name, need) in enumerate(cme.EVIDENCE_DEPTHS, 1):
        assert "| %d `%s` | %d" % (n, name, need) in depth, name      # the table's levels and thresholds
        assert "%d `%s` (%d" % (n, name, need) in schema, name
    rule8 = doc("standards_kits.md")                    # rule 8, in its own file (#92)
    assert "**Deeper**" in rule8 and "put on the verification list" in rule8 and "`deeper`" in rule8
    assert "evidence_depth.md`" in doc("standards.md").split("## Rule 4.")[1].split("## Rule 5.")[0]
    assert "`depth`" in doc("author.md") and "`deeper` block" in doc("evidence_check.md")
    assert '"evidence_ladder": false' in doc("requests.md") and "`evidence_ladder` false" in doc("onboarding.md")
    assert "**Evidence depth**" in read(os.path.join(ROOT, "CONTEXT.md"))
    assert "`depth`" in doc("state_schema.md") and "`given`" in depth


def test_the_examiner_reads_one_brief_before_grading():
    """Issue #77: what the examiner needs to grade and write feedback is in its brief, read before
    grading and nothing else; the rulebook keeps the item rules and points there for 5.3, 10 and
    11; the coding moved too. Issue #92: the brief is split so that each turn reads only what it
    uses: grading.md (the examiner's procedure) and feedback_guide.md (what the feedback says, the
    author's too) before grading; coding, disputes, evidence depth and listening when needed."""
    skill = read(SKILL_MD)
    row = next(line for line in skill.splitlines() if line.startswith("| `references/grading.md`, `references/feedback_guide.md`"))
    assert "nothing else before grading" in row
    for name in ("standards.md", "analysis_framework.md", "coding.md", "disputes.md"):
        row = next(line for line in skill.splitlines() if "`references/%s`" % name in line)
        assert "before grading" not in row.lower(), name
    grading = read(os.path.join(REFERENCES, "grading.md"))
    for heading in ("## 1. Before writing feedback: verify", "## 2. Prepared text and live text",
                    "### 2.1 Marks before text", "### 2.2 The draft", "### 2.4 The grader is not the author",
                    "## 3. Reflection prompt", "## 4. The log needs the feedback verbatim"):
        assert heading in grading, heading
    guide = read(os.path.join(REFERENCES, "feedback_guide.md"))
    for heading in ("## 1. Whose guidance, and for whom", "## 2. Structure of the feedback", "## 7. Prepared text and live text",
                    "### 6.1 The glossary line (rule 5.3)", "### 6.2 Results the learner did not see (rule 10)",
                    "### 6.3 Text for the learner speaks plainly (rule 11)", "**Tailoring always wins over speed.**"):
        assert heading in guide, heading
    coding = read(os.path.join(REFERENCES, "coding.md"))
    for heading in ("# Coding a round", "## 3. Errors", "## 5. Focused questions"):
        assert heading in coding, heading
    disputes = read(os.path.join(REFERENCES, "disputes.md"))
    assert "## 1. A score the learner sets" in disputes and "## 2. The learner's stop" in disputes
    # the rules on sources and the list of live parts: in feedback_guide.md, which the author reads too
    for text in ("Never invent a trial name", "quote at most a short phrase", "**the opening in the learner's own words**"):
        assert text in guide and text not in grading, text
    # each part has one home: nothing moved out is left behind in the brief
    for text in ("| `DG` |", "### 7.1", "learner_stops", "| 2 `studies` |", "Podcast Index", "Brier score"):
        assert text not in guide and text not in grading, text
    standards = read(os.path.join(REFERENCES, "standards.md"))
    for n, section in ((10, "§6.2"), (11, "§6.3")):
        body = standards.split("## Rule %d." % n)[1].split("## Rule %d." % (n + 1))[0]
        assert "`feedback_guide.md` %s" % section in body and len(body.split()) < 80, n
    # the coding is written once, in coding.md; calibration as `stats` reports it, in the review's framework
    analysis = read(os.path.join(REFERENCES, "analysis_framework.md"))
    assert "`coding.md`" in analysis and "| `DG` |" not in analysis and "| `DG` |" in coding
    assert "Brier score" in analysis and "Brier score" not in coding
    assert os.path.isfile(os.path.join(ROOT, "docs", "adr", "0009-prepared-feedback-adapted-live.md"))


def test_prepared_feedback_is_described_where_each_reader_looks_for_it():
    """Issue #78: the blocks in the rulebook, the draft in the brief, the record in the log, the
    checker's Blocks line, the simulation's examiner prompt."""
    doc = lambda name: read(os.path.join(REFERENCES, name))
    rule8 = doc("standards_kits.md")                    # rule 8, in its own file (#92)
    assert "<!-- block: Q4.2 missed -->" in rule8 and "`n missed`, `n partial` and `n hit`" in rule8
    assert "cme.py draft" in flat(doc("grading.md")) and "`prepared_feedback`" in doc("session_log.md")
    assert "**Blocks:**" in doc("evidence_check.md") and "prepared blocks" in doc("author.md")
    assert "draft --work <work> --part questions" in flat(read(SKILL_MD))
    examiner = read(os.path.join(ROOT, "sim", "prompts", "examiner.md"))
    assert "cme.py draft" in examiner and "`quote`" in examiner
    context = read(os.path.join(ROOT, "CONTEXT.md"))
    for term in ("**Prepared block**", "**Marks before text**", "**Draft**", "**Live part**"):
        assert term in context, term

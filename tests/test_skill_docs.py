"""The main skill file stays short, keeps the blinding rules itself, and points only at
reference files that exist (issue #14)."""
import glob
import os
import re

from conftest import SKILL

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

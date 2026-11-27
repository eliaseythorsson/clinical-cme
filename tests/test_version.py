"""One version source (issue #56): SKILL_VERSION in cme.py. Every place that states the version says
the same, and PAGE_VERSION has its note in the skill's README and its <meta> in the page. A bump
changes SKILL_VERSION and then whatever this test names."""
import json
import os
import re

from conftest import ROOT, SKILL
from examples import cme

PLUGIN = os.path.join(ROOT, "plugins", "clinical-cme")


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


def test_every_place_that_states_the_version_states_skill_version():
    v = cme.SKILL_VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+", v)
    places = {
        "SKILL.md heading": (read(SKILL, "SKILL.md"), r"^# Clinical CME .*\(version ([\d.]+)\)$"),
        "skill README heading": (read(SKILL, "README.md"), r"^# clinical-cme \(version ([\d.]+)\)$"),
        "cme.py docstring": (read(SKILL, "scripts", "cme.py"), r'^"""clinical-cme v([\d.]+) state engine'),
        "plugin README": (read(PLUGIN, "README.md"), r"^Current version: \*\*([\d.]+)\*\*"),
        "root README": (read(ROOT, "README.md"), r"^Current version: \*\*([\d.]+)\*\*"),
        "CLAUDE.md": (read(ROOT, "CLAUDE.md"), r"\(currently version ([\d.]+)\)"),
    }
    for where, (text, rx) in places.items():
        found = re.findall(rx, text, re.M)
        assert found == [v], "%s states %s, SKILL_VERSION is %s" % (where, found, v)
    # the skill README's newest "What is new" is this version's major.minor
    news = re.findall(r"^## What is new in version ([\d.]+)$", read(SKILL, "README.md"), re.M)
    assert news and cme.version_key(news[0]) == cme.version_key(v)[:len(cme.version_key(news[0]))]


def test_page_version_has_its_meta_and_its_note():
    p = cme.PAGE_VERSION
    assert cme.PAGE_VERSION_RE.search(read(SKILL, "templates", "page.html")).group(1) == p
    notes = re.findall(r"^## Page update ([\d.]+)$", read(SKILL, "README.md"), re.M)
    assert notes and notes[0] == p, "the newest page note is %s, PAGE_VERSION is %s" % (notes[:1], p)
    assert cme.version_key(p) <= cme.version_key(cme.SKILL_VERSION)


def test_no_manifest_carries_a_version():
    # every commit on main is a new plugin version (CLAUDE.md, Distribution)
    plugin = json.loads(read(PLUGIN, ".claude-plugin", "plugin.json"))
    market = json.loads(read(ROOT, ".claude-plugin", "marketplace.json"))
    assert "version" not in plugin and all("version" not in p for p in market["plugins"])
    assert plugin["name"] == "clinical-cme" and market["plugins"][0]["source"] == "./plugins/clinical-cme"
    assert not os.path.exists(os.path.join(ROOT, ".claude-plugin", "plugin.json"))


def test_licence_files_ship_with_the_plugin_and_the_skill():
    shipped = read(PLUGIN, "LICENSE.md")
    assert shipped == read(SKILL, "LICENSE.md")
    for text in (shipped, read(ROOT, "LICENSE.md")):
        assert "MIT License" in text and "CC BY-NC 4.0" in text
    assert "SPDX-License-Identifier: MIT" in read(SKILL, "scripts", "cme.py").splitlines()[1]
    assert re.search(r"^license: .*CC BY-NC 4\.0.*MIT", read(SKILL, "SKILL.md"), re.M)

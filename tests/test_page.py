"""The learner's page must not preview a coming round (issue #13): no open gaps by name, no due
topics, no due dates; history and progress stay. The page script is rendered against a stub DOM
(tests/page_harness.js) when node is available."""
import importlib.util
import json
import os
import re
import shutil
import subprocess

import pytest

from conftest import CME, SKILL

PAGE = os.path.join(SKILL, "templates", "page.html")
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_harness.js")

STATE = {
    "schema": 4, "gen": 3, "next_id": "S0004", "config": {},
    "topics": {
        # overdue and weakest: the old page listed this first
        "AAA-01": {"label": "Alpha topic", "mastery": 2, "last": "2020-01-02", "due": "2020-01-09"},
        "BBB-02": {"label": "Beta topic", "mastery": 4, "last": "2020-03-04", "due": "2031-05-06"},
        "CCC-03": {"label": "Gamma topic", "mastery": 5, "last": "2020-02-03", "due": "2020-02-20"},
    },
    "gaps": [{"topic": "AAA-01", "gap": "SECRET-GAP-TEXT", "source": ["graded"], "opened": "2020-01-02"}],
    "sessions": [{"id": "S0001", "date": "2020-03-04", "title": "PAST-SESSION-TITLE", "score": 3.5},
                 {"id": "S0002", "date": "2020-03-05", "title": "OTHER-PAST-SESSION", "score": 4.5}],
    "review": {"next_due": "2031-01-01"},
    "blueprint": {"AAA": {"name": "Alphology", "weight": 1.0, "topics": {"AAA-01": "Alpha topic", "AAA-09": "UNTESTED-TOPIC"}}},
    "block": {"theme": "AAA", "round": 4, "length": 12, "started": "2020-01-02", "reason": "SECRET-REASON"},
}


def load_cme():
    spec = importlib.util.spec_from_file_location("cme_under_test", CME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def page_text():
    with open(PAGE, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    state = tmp_path_factory.mktemp("page") / "state.json"
    state.write_text(json.dumps(STATE), encoding="utf-8")
    proc = subprocess.run([node, HARNESS, PAGE, str(state)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# ---- the template itself ----------------------------------------------------------------------

def test_template_has_no_gap_or_due_views():
    html = page_text()
    visible = re.sub(r"<!--.*?-->|/\*.*?\*/|^\s*//.*$", "", html, flags=re.S | re.M)
    for phrase in ("Open gaps", "Gaps &amp; topics", "Due now", "Next review", "Sorted by next review",
                   "most urgent first", "Overdue", "Due today", "ready for review"):
        assert phrase not in visible, phrase
    assert "state.gaps" not in visible
    # no topic's due date is read anywhere (review.next_due is the progress review, not a topic)
    assert not re.search(r"\.due\b", visible)


def test_template_version_matches_cme():
    cme = load_cme()
    m = cme.PAGE_VERSION_RE.search(page_text())
    assert m and m.group(1) == cme.PAGE_VERSION
    assert cme.version_tuple(cme.PAGE_VERSION) > cme.version_tuple("4.2.1")


# ---- the one-time upgrade ---------------------------------------------------------------------

def test_older_page_is_upgraded_once(tmp_path):
    cme = load_cme()
    live = tmp_path / "live.html"
    live.write_text('<meta name="cme-page-version" content="4.2.1">Open gaps', encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    warnings = []
    entry = cme.page_upgrade(str(out), str(live), warnings)
    assert entry["page_upgrade"] == {"from": "4.2.1", "to": cme.PAGE_VERSION}
    new = (out / "index.html").read_text(encoding="utf-8")
    assert new == page_text()
    # the upgraded page is current, so the next save leaves it alone
    out2 = tmp_path / "out2"
    out2.mkdir()
    assert cme.page_upgrade(str(out2), str(out / "index.html"), warnings) is None
    assert not (out2 / "index.html").exists()
    assert warnings == []


# ---- what the page renders --------------------------------------------------------------------

def test_rendered_page_names_no_gap_and_no_due_date(rendered):
    text = rendered["text"]
    assert "SECRET-GAP-TEXT" not in text
    assert not re.search(r"overdue|due today|next review|open gap", text, flags=re.I)
    # the topics' due dates appear in no form: not the year of the far one, not a "9 Jan"-style date
    assert "2031-05-06" not in text and "2020-01-09" not in text and "2020-02-20" not in text
    table = rendered["ids"]["topics"]
    assert table.count("<tr>") == 4 and table.count('class="num"') == 3   # one date per topic: last tested
    assert table.count("<th>") == 4 and "Last tested" in table and "Mastery" in table


def test_rendered_topics_are_ordered_by_last_tested_not_urgency(rendered):
    table = rendered["ids"]["topics"]
    order = sorted(("AAA-01", "BBB-02", "CCC-03"), key=table.index)
    assert order == ["BBB-02", "CCC-03", "AAA-01"]   # most recently tested first; by due it was AAA, CCC, BBB


def test_rendered_page_keeps_history_scores_and_progress(rendered):
    ids, text = rendered["ids"], rendered["text"]
    assert "PAST-SESSION-TITLE" in text and "OTHER-PAST-SESSION" in text
    assert ids["t-sess"] == "2"
    assert ids["t-score"] == "4.0"
    assert ids["t-topics"] == "3"
    assert "3.7" in ids["t-topics-n"]
    for label in ("Alpha topic", "Beta topic", "Gamma topic"):
        assert label in ids["topics"]
    assert ids["t-review"] not in ("", "–")


def test_rendered_page_shows_the_theme_of_the_block_and_no_coming_topic(rendered):
    assert rendered["ids"]["block"] == "Block: Alphology · 4 of 12 rounds done"
    assert "UNTESTED-TOPIC" not in rendered["text"] and "SECRET-REASON" not in rendered["text"]

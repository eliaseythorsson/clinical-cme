"""The learner's page shows only the page file (issue #54). `cme.py` writes `data/page.json`,
already blinded (tests/test_page_file.py); the page renders that file and nothing else of the
store, so it cannot preview a coming round (issue #13): no open gaps, no due topics, no due
dates; history and progress stay. The page script is rendered against a stub DOM and a store
folder (tests/page_harness.js). That needs node: without it these tests are skipped on a
developer's machine and fail in CI."""
import importlib.util
import json
import os
import re
import shutil
import subprocess

import pytest

from conftest import CME, ROOT, SKILL, run_script

PAGE = os.path.join(SKILL, "templates", "page.html")
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_harness.js")

STATE = {
    "schema": 4, "gen": 3, "next_id": "S0004", "updated": "2020-03-05",
    "config": {"mcqs": 2, "focused": 1, "case": True, "session_minutes": 30, "round_set_at": "2020-01-01T10:00:00Z",
               "target_sessions_per_week": 3, "guideline_region": "UK", "lab_units": "SI", "blood_gas_units": "kPa"},
    "profile": {"display_name": "Dr Example", "specialty": "Geriatrics",
                "domain_self_ratings": {"AAA": {"rating": 2}}},
    "topics": {
        # overdue and weakest: a page ordered by urgency would list this first
        "AAA-01": {"label": "Alpha topic", "mastery": 2, "last": "2020-01-02", "due": "2020-01-09"},
        "BBB-02": {"label": "Beta topic", "mastery": 4, "last": "2020-03-04", "due": "2031-05-06"},
        "CCC-03": {"label": "Gamma topic", "mastery": 5, "last": "2020-02-03", "due": "2020-02-20"},
        # named by the learner as shaky, never tested: it has a gap and no result
        "DDD-04": {"label": "UNTESTED-GAP-TOPIC", "mastery": None, "last": None, "due": "2020-01-05"},
    },
    "gaps": [{"id": "G0001", "topic": "AAA-01", "gap": "SECRET-GAP-TEXT", "source": ["graded"], "opened": "2020-01-02"}],
    "sessions": [{"id": "S0001", "date": "2020-03-04", "title": "PAST-SESSION-TITLE", "score": 3.5, "minutes": 31},
                 {"id": "S0002", "date": "2020-03-05", "title": "OTHER-PAST-SESSION", "score": 4.5}],
    "review": {"next_due": "2031-01-01", "period_start": "2020-03-01"},
    "drills": [{"code": "bias:SECRET-DRILL"}],
    "blueprint": {"AAA": {"name": "Alphology", "weight": 1.0, "topics": {"AAA-01": "Alpha topic", "AAA-09": "UNTESTED-TOPIC"}}},
    "block": {"theme": "AAA", "round": 4, "length": 12, "started": "2020-01-02", "reason": "SECRET-REASON"},
}
SECRETS = ("SECRET-GAP-TEXT", "SECRET-DRILL", "SECRET-REASON", "UNTESTED-TOPIC", "UNTESTED-GAP-TOPIC", "DDD-04", "G0001")


def load_cme():
    spec = importlib.util.spec_from_file_location("cme_under_test", CME)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def page_text():
    with open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def node():
    """The node binary. Without it the render tests are skipped, except in CI (GitHub Actions
    sets CI=true), where a missing node is a failure: the workflow installs it."""
    exe = shutil.which("node")
    if not exe:
        if os.environ.get("CI"):
            pytest.fail("node is not installed, and CI must run the page render tests "
                        "(.github/workflows/tests.yml installs it with actions/setup-node)")
        pytest.skip("node is not installed")
    return exe


def store_with(root, state=STATE, page=True, extra=None):
    """A store folder as the page is served it: the ledger (which the page must not read), the
    page file the engine writes for it, and any other files."""
    data = os.path.join(str(root), "data")
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    if page:
        doc = load_cme().page_doc(state) if page is True else page
        with open(os.path.join(data, "page.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
    for rel, obj in (extra or {}).items():
        path = os.path.join(str(root), *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
    return str(root)


def render(store, *options):
    proc = subprocess.run([node(), HARNESS, PAGE, store, *options], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    return render(store_with(tmp_path_factory.mktemp("page")))


# ---- node in CI ---------------------------------------------------------------------------------

def test_ci_installs_node_so_the_render_tests_run():
    with open(os.path.join(ROOT, ".github", "workflows", "tests.yml"), encoding="utf-8") as fh:
        assert "actions/setup-node" in fh.read()
    if os.environ.get("CI"):
        assert shutil.which("node"), "CI has no node: the page render tests would not run"


def test_a_missing_node_fails_in_ci_and_skips_elsewhere(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setenv("CI", "true")
    with pytest.raises(pytest.fail.Exception):
        node()
    monkeypatch.delenv("CI")
    with pytest.raises(pytest.skip.Exception):
        node()


# ---- the template itself ----------------------------------------------------------------------

def visible_template():
    """The template without its comments (HTML, CSS and JS block comments, JS comment lines)."""
    return re.sub(r"<!--.*?-->|/\*.*?\*/|^[ \t]*//[^\n]*$", "", page_text(), flags=re.S | re.M)


def test_template_has_no_gap_or_due_views():
    visible = visible_template()
    for phrase in ("Open gaps", "Gaps &amp; topics", "Due now", "Next review", "Sorted by next review",
                   "most urgent first", "Overdue", "Due today", "ready for review", "Active drills"):
        assert phrase not in visible, phrase
    assert not re.search(r"\.due\b|\.gaps\b|\.drills\b", visible)


def test_template_reads_the_page_file_and_knows_no_ledger_field():
    cme = load_cme()
    visible = visible_template()
    # the ledger is fetched in one place, the export; everything else comes from data/page.json
    assert visible.count("data/state.json") == 1 and "data/page.json" in visible
    assert visible.index("data/state.json") > visible.index("async function exportAll")
    ledger_names = {k for k in list(cme.DEFAULT_CONFIG) + list(cme.DEFAULT_PROFILE) + list(cme.new_state(cme.parse_date("2026-01-01")))
                    if "_" in k}
    ledger_names |= {"next_due", "period_start", "blueprint", "unreflected", "previous", "resolved", "errata", "agg"}
    assert {"session_minutes", "round_set_at", "guideline_region", "domain_self_ratings", "next_id"} <= ledger_names
    for name in sorted(ledger_names):
        assert not re.search(r"\b%s\b" % re.escape(name), visible), name
    assert not re.search(r"\b(config|profile)\b", visible)


def test_template_keeps_no_limits_and_no_minutes_of_its_own():
    cme = load_cme()
    script = visible_template().split("<script>")[-1]
    assert "LIMITS" not in script
    # no "3 * m.mcqs", no "? 10 : 15": the minutes per item and the limits come with the file
    assert not re.search(r"\b\d+\s*\*\s*m\.(mcqs|focused)|m\.(mcqs|focused)\s*\*\s*\d", script)
    assert "minutes_per" in script and ".limits" in script
    for hi in (v[1] for v in cme.ROUND_LIMITS.values()):
        assert not re.search(r"\[\s*\d+\s*,\s*%d\s*\]" % hi, script)


def test_template_version_matches_cme():
    cme = load_cme()
    m = cme.PAGE_VERSION_RE.search(page_text())
    assert m and m.group(1) == cme.PAGE_VERSION
    assert cme.version_tuple(cme.PAGE_VERSION) > cme.version_tuple("5.0.0")      # bumped with the page file


# ---- the one-time upgrade ---------------------------------------------------------------------

@pytest.mark.parametrize("old", ["4.2.1", "5.0.0"])
def test_older_page_is_upgraded_once(tmp_path, old):
    cme = load_cme()
    store = tmp_path / "store"
    store.mkdir()
    (store / "index.html").write_text('<meta name="cme-page-version" content="%s">Open gaps' % old, encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    info = {"store": str(store)}
    warnings = []
    assert cme.page_upgrade(str(work), info, warnings) == {"from": old, "to": cme.PAGE_VERSION}
    new = (work / "publish" / "index.html").read_text(encoding="utf-8")
    assert new == page_text()
    assert cme.publish_set(str(work), info) == [{"as": "index.html", "path": str(work / "publish" / "index.html")}]
    # the upgraded page is in the publish set and current, so the next save leaves it alone
    assert cme.page_upgrade(str(work), info, warnings) is None
    # and so does a later job, once it is in the store
    (store / "index.html").write_text(new, encoding="utf-8")
    later = tmp_path / "later"
    later.mkdir()
    assert cme.page_upgrade(str(later), info, warnings) is None
    assert not (later / "publish").exists()
    assert warnings == []


def test_a_page_that_read_the_ledger_is_replaced_together_with_its_first_page_file(work):
    """The upgrade path of this version: a store whose page still reads the ledger and the index
    gets the new page and the page file it needs in the same publish set."""
    work.init()
    os.remove(work.store("data", "page.json"))                       # a store from before the page file
    work.write(os.path.join("store", "data", "index.json"), {"schema": 1, "sessions": [], "reviews": []})
    work.write(os.path.join("store", "index.html"), '<meta name="cme-page-version" content="5.0.0">state.gaps')
    saved = work.save_round("2026-11-02")
    names = [f["as"] for f in saved["files"]]
    assert saved["page_upgraded"] == {"from": "5.0.0", "to": load_cme().PAGE_VERSION}
    assert names.index("data/page.json") < names.index("index.html") < names.index("data/state.json")
    assert "data/index.json" not in names
    assert work.read_json("publish", "data", "page.json")["page_version"] == load_cme().PAGE_VERSION
    with open(work.pub("index.html"), encoding="utf-8") as fh:
        assert fh.read() == page_text()


# ---- what the page renders --------------------------------------------------------------------

def test_page_fetches_only_the_page_file(rendered):
    assert rendered["fetched"] == ["data/page.json"]


def test_rendered_page_names_no_gap_and_no_due_date(rendered):
    text = rendered["text"]
    for secret in SECRETS:
        assert secret not in text, secret
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
    assert ids["who"] == "Dr Example · Geriatrics"


def test_rendered_settings_come_from_the_page_file(rendered):
    settings = rendered["ids"]["settings"]
    for shown in ("30 min", "2 MCQs + 1 focused question + 1 case", "3 sessions/week", "UK", "SI, gases in kPa",
                  "Geriatrics", "AAA 2"):
        assert shown in settings, shown
    assert "generation" not in settings and "S0004" not in settings       # no ledger internals


def test_rendered_page_lists_the_learners_positions_in_their_words(rendered, tmp_path):
    """Issue #75: the position notes in force, under the topics tested; none, no section."""
    assert rendered["hidden"]["pos-wrap"] is True and rendered["ids"]["positions"] == ""
    st = dict(STATE, positions=[{"id": "P0001", "topic": "BBB-02", "point": "THE-POINT", "text": "MY-OWN-WORDS",
                                 "set": "2020-03-04", "confirmed": "2020-03-04", "session": "S0001"}])
    out = render(store_with(tmp_path, st))
    assert out["hidden"]["pos-wrap"] is False
    table = out["ids"]["positions"]
    for shown in ("BBB-02", "Beta topic", "THE-POINT", "MY-OWN-WORDS"):
        assert shown in table, shown
    assert "S0001" not in table


def test_rendered_page_shows_the_theme_of_the_block_and_no_coming_topic(rendered):
    assert rendered["ids"]["block"] == "Block: Alphology · 4 of 12 rounds done"
    assert "UNTESTED-TOPIC" not in rendered["text"] and "SECRET-REASON" not in rendered["text"]
    assert rendered["styles"]["block-bar"] == {"width": "33%"}       # progress through the block (issue #17)


@pytest.mark.parametrize("block, shown", [
    ({"theme": "AAA", "round": 0, "length": 12, "chosen": "learner"}, "Block: Alphology · starts with your next round (12 rounds)"),
    ({"theme": "AAA", "round": 12, "length": 12},
     "Block: Alphology · finished (12 rounds); the next block starts with your next round"),
])
def test_rendered_page_shows_a_block_not_yet_begun_and_a_finished_one(block, shown, tmp_path):
    assert render(store_with(tmp_path, dict(STATE, block=block)))["ids"]["block"] == shown


# ---- the estimate is the engine's ---------------------------------------------------------------

def test_rendered_estimate_is_the_one_in_the_page_file(rendered, tmp_path):
    cme = load_cme()
    doc = cme.page_doc(STATE)
    assert doc["round"]["minutes"] == 2 * 5 + 1 * 10 + 25
    assert rendered["ids"]["mix-est"] == "About 45 minutes with feedback · your session length is 30 min."
    # the page has no figure of its own: whatever the file says is what it shows
    doc["round"]["minutes"] = 77
    assert "About 77 minutes" in render(store_with(tmp_path, page=doc))["ids"]["mix-est"]


# ---- export: a full backup, with a warning ------------------------------------------------------

EXPORT_FILES = {"data/sessions/S0001.json": {"id": "S0001", "transcript": "TRANSCRIPT-ONE"},
                "data/sessions/S0002.json": {"id": "S0002", "transcript": "TRANSCRIPT-TWO"}}


def test_export_warns_about_open_gaps_before_anything_is_read(tmp_path):
    store = store_with(tmp_path, extra=EXPORT_FILES)
    out = render(store, "--downloads")
    assert out["hidden"]["export"] is False and "export-warn" not in out["hidden"]      # hidden in the markup, untouched
    assert re.search(r'id="export-warn"[^>]*\shidden>', page_text())
    assert "open gaps" in page_text().split('id="export-note">')[1].split("</span>")[0]
    out = render(store, "--downloads", "--click", "export")
    assert out["hidden"]["export-warn"] is False
    assert out["saved"] == [] and out["fetched"] == ["data/page.json"]         # nothing read, nothing saved yet


def test_export_is_a_full_backup_with_the_ledger(tmp_path):
    out = render(store_with(tmp_path, extra=EXPORT_FILES), "--downloads", "--click", "export,export-go")
    assert out["fetched_on_load"] == ["data/page.json"] and "data/state.json" in out["fetched"]
    assert len(out["saved"]) == 1 and out["saved"][0]["filename"].startswith("clinical-cme-export-")
    backup = json.loads(out["saved"][0]["data"])
    assert backup["state"] == STATE                                            # the ledger, gaps and all
    assert sorted(s["id"] for s in backup["sessions"]) == ["S0001", "S0002"]
    assert {s["transcript"] for s in backup["sessions"]} == {"TRANSCRIPT-ONE", "TRANSCRIPT-TWO"}
    assert backup["reviews"] == []


def test_export_can_be_imported_again(tmp_path):
    out = render(store_with(tmp_path / "store", extra=EXPORT_FILES), "--downloads", "--click", "export,export-go")
    export = tmp_path / "export.json"
    export.write_text(out["saved"][0]["data"], encoding="utf-8")
    cme = load_cme()
    proc = run_script(CME, ["import", str(export), "--out-dir", str(tmp_path / "back")])
    assert proc.returncode == 0, proc.stderr
    names = [f["as"] for f in json.loads(proc.stdout)["files"]]
    assert names == ["data/sessions/S0002.json", "data/sessions/S0001.json", "data/page.json", "data/state.json"] \
        or names == ["data/sessions/S0001.json", "data/sessions/S0002.json", "data/page.json", "data/state.json"]
    with open(tmp_path / "back" / "data" / "page.json", encoding="utf-8") as fh:
        assert json.load(fh)["page_version"] == cme.PAGE_VERSION


# ---- a store from before the page file ----------------------------------------------------------

def test_a_store_with_only_the_old_index_still_lists_its_sessions_without_reading_the_ledger(tmp_path):
    index = {"schema": 1, "sessions": [{"id": "S0001", "date": "2020-03-04", "title": "PAST-SESSION-TITLE", "score": 3.5}],
             "reviews": [{"date": "2020-02-01", "title": "OLD-REVIEW"}]}
    out = render(store_with(tmp_path, page=False, extra={"data/index.json": index}))
    assert out["fetched"] == ["data/page.json", "data/index.json"]              # never data/state.json
    assert "PAST-SESSION-TITLE" in out["text"] and "OLD-REVIEW" in out["text"]
    assert out["hidden"]["legacy"] is False                                     # says the rest comes with the next round
    for secret in SECRETS:
        assert secret not in out["text"], secret


def test_an_empty_store_says_how_to_set_up(tmp_path):
    os.makedirs(tmp_path / "data")
    out = render(str(tmp_path))
    assert "No ledger yet" in out["ids"]["s-list"]

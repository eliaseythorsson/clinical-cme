"""Central guideline checks (issue #91, ADR 0013): the default blueprint's tag records are kept once,
in the repo (templates/guideline_checks.json, one set per supported region), and ship with the
plugin. A learner's install reads per tag the newer of the shipped record and their own; the tags
their blueprint shares with the default blueprint are not swept per learner unless
`config.guideline_sweeps` is "all" ("off": nothing swept); their own tags keep #90's sweeps. The
maintainer's command `central-checks` lists the tags due, files the checkers' results into the
template and validates it."""
import datetime as dt
import json
import math
import os

import pytest

from conftest import CME, DEFAULT_BLUEPRINT, Work, run_script
from examples import cme

DAY = "2026-11-27"
TODAY = dt.date(2026, 11, 27)
TEMPLATE = cme.GUIDELINE_SEED


def default_state(region="International", **config):
    st = cme.make_current(cme.new_state(TODAY))
    with open(DEFAULT_BLUEPRINT) as fh:
        st["blueprint"] = cme.blueprint_shape(json.load(fh))
    st["config"].update(dict(config, guideline_region=region))
    return st


def shipped():
    with open(TEMPLATE) as fh:
        return json.load(fh)


def first_subtopic(st):
    """A sub-topic of the default blueprint with a tagged point: (id, its first tag)."""
    for sid, info in cme.bp_subtopics(st).items():
        for p in info.get("points") or []:
            if cme.point_tags(p):
                return sid, cme.point_tags(p)[0]


def write_template(tmp_path, records, region_set="International"):
    """A copy of the shipped template whose set `region_set` holds `records` (tag → record) over its own."""
    doc = shipped()
    s = doc["sets"][region_set]
    idx = cme.guideline_records(s)
    idx.update(records)
    s["records"] = [idx[t] for t in sorted(idx)]
    path = os.path.join(str(tmp_path), "guideline_checks.json")
    with open(path, "w") as fh:
        json.dump(doc, fh)
    return path


def rec(tag, day, status="current", by=None, since=None):
    r = {"tag": tag, "last_checked": day, "status": status, "superseded_by": by, "source": "https://example.org",
         "note": None}
    if since:
        r["since"] = since
    return r


# ---------------------------------------------------------------- the shipped template

def test_the_shipped_template_is_valid_and_holds_international_and_europe():
    doc = shipped()
    assert doc["kind"] == cme.CENTRAL_KIND and cme.central_problems(doc, TODAY) == []
    assert {"International", "Europe"} <= set(doc["sets"])
    for s in doc["sets"].values():
        assert len(s["records"]) > 250 and s["updated"]


def test_region_families_map_to_the_central_sets():
    doc = shipped()
    assert cme.central_set_for("International", doc) == "International"
    assert cme.central_set_for("  international ", doc) == "International"
    assert cme.central_set_for("Europe", doc) == "Europe"
    assert cme.central_set_for("Iceland/Europe", doc) == "Europe"       # the old default (ADR 0012)
    assert cme.central_set_for("Norway/Europe", doc) == "Europe"        # <country>/<family>: the family
    # the answers setup offers (onboarding.md §2) all read a set: UK the European one, North America
    # the International one; a European country is written "<country>/Europe" at setup
    for region in ("UK", "United Kingdom", "uk"):
        assert cme.central_set_for(region, doc) == "Europe"
    for region in ("North America", "US", "USA", "United States", "Canada"):
        assert cme.central_set_for(region, doc) == "International"
    # any other region reads International: a central record says only whether an edition is current
    for region in ("Japan", "Brazil", "Iceland", "Elsewhere/Nowhere", ""):
        assert cme.central_set_for(region, doc) == "International"
    assert cme.central_set_for("Japan", {"kind": cme.CENTRAL_KIND, "sets": {}}) is None
    # a seed of the #90 shape reads as one set
    old = {"kind": "guideline_checks_seed", "regions": ["International"], "records": [rec("A", DAY)]}
    assert cme.central_set_for("International", old) == "Seed"


def test_the_default_blueprints_tags_are_covered_and_a_learners_own_are_not():
    st = default_state()
    central = cme.central_guidelines(st)
    tags = cme.blueprint_tags(st)
    assert central["set"] == "International" and set(tags) <= central["covered"]
    # the learner's own area (a new sub-topic id), and a tag an edited sub-topic added: their own
    sid, tag = first_subtopic(st)
    topic = cme.bp_subtopics(st)[sid]["topic"]
    for d in st["blueprint"].values():
        if topic in (d.get("subtopics") or {}):
            d["subtopics"][topic][sid]["points"].append("An added point [MY SOCIETY 2026]")
            d["subtopics"][topic]["OWN-01a"] = {"label": "Mine", "points": ["Own point [OWN GUIDE 2025]"]}
    central = cme.central_guidelines(st)
    assert "MY SOCIETY 2026" not in central["covered"] and "OWN GUIDE 2025" not in central["covered"]
    assert tag in central["covered"]
    idx = cme.guideline_records(cme.effective_guidelines(st, None, central))
    assert cme.swept_pool(st, idx, central) == {"MY SOCIETY 2026", "OWN GUIDE 2025"}
    # a region matching no set reads International: still nothing of the default swept
    st["config"]["guideline_region"] = "Japan"
    central = cme.central_guidelines(st)
    assert central["set"] == "International" and tag in central["covered"]
    idx = cme.guideline_records(cme.effective_guidelines(st, None, central))
    assert cme.swept_pool(st, idx, central) == {"MY SOCIETY 2026", "OWN GUIDE 2025"}
    # with "all", every tag is the learner's to sweep
    st["config"]["guideline_sweeps"] = "all"
    assert cme.swept_pool(st, idx, central) == {cme.current_tag(t, idx) for t in cme.blueprint_tags(st)}


def test_the_setting_sweeps_custom_all_or_nothing():
    st = default_state()
    central = cme.central_guidelines(st)
    idx = cme.guideline_records(cme.effective_guidelines(st, None, central))
    assert cme.guideline_sweeps(st) == "custom" and cme.swept_pool(st, idx, central) == set()
    st["config"]["guideline_sweeps"] = "all"
    assert len(cme.swept_pool(st, idx, central)) == len(cme.blueprint_tags(st))
    st["config"]["guideline_sweeps"] = "off"
    assert cme.swept_pool(st, idx, central) == set()
    st["config"]["guideline_sweeps"] = "nonsense"            # a hand edit reads as the default
    assert cme.guideline_sweeps(st) == "custom"


def test_the_newer_of_the_shipped_and_the_learners_record_counts(tmp_path, monkeypatch):
    st = default_state()
    _, tag = first_subtopic(st)
    monkeypatch.setattr(cme, "GUIDELINE_SEED", write_template(tmp_path, {tag: rec(tag, "2027-03-01", "superseded",
                                                                                 tag + " NEW", "2027-03-01")}))
    learner = {"kind": cme.GUIDELINES_KIND, "records": [rec(tag, "2026-12-01")]}
    idx = cme.guideline_records(cme.effective_guidelines(st, learner))
    assert idx[tag]["status"] == "superseded"              # a plugin update's newer check is not hidden
    assert learner["records"] == [rec(tag, "2026-12-01")]  # the learner's file is not rewritten
    learner["records"] = [rec(tag, "2027-04-01")]
    idx = cme.guideline_records(cme.effective_guidelines(st, learner))
    assert idx[tag]["status"] == "current" and idx[tag]["last_checked"] == "2027-04-01"
    # filing a learner's result keeps the central finding's day (`since`) and writes only their file
    learner["records"] = []
    base = cme.effective_guidelines(st, learner)
    cme.file_tag_results(st, learner, {tag: {"status": "superseded", "superseded_by": tag + " NEW",
                                             "source": "s", "note": None}}, dt.date(2027, 5, 1), base)
    mine = cme.guideline_records(learner)
    assert mine[tag]["since"] == "2027-03-01" and set(mine) == {tag, tag + " NEW"}


def test_a_central_supersession_overlays_the_plan_and_queues_the_reviews_recheck(tmp_path, monkeypatch):
    st = default_state()
    sid, tag = first_subtopic(st)
    monkeypatch.setattr(cme, "GUIDELINE_SEED", write_template(
        tmp_path, {tag: rec(tag, "2026-11-20", "superseded", tag + " NEW", "2026-11-20")}))
    plan = {"items": [{"subtopic": {"id": sid, "points": list(cme.bp_subtopics(st)[sid]["points"])}}]}
    idx = cme.guideline_records(cme.effective_guidelines(st, None))
    assert cme.overlay_plan(plan, idx) >= 1
    assert tag not in cme.plan_tags(plan) and tag + " NEW" in cme.plan_tags(plan)
    assert plan["items"][0]["subtopic"]["guidelines"][0]["tag"] == tag
    # rounds held before the central finding on that sub-topic: their teaching goes to the review
    topic = cme.bp_subtopics(st)[sid]["topic"]
    st["sessions"] = [{"id": "S0001", "date": "2026-11-01", "items": [{"type": "mcq", "topic": topic, "subtopic": sid}],
                       "key_learning": ["taught then"]},
                      {"id": "S0002", "date": "2026-11-25", "items": [{"type": "mcq", "topic": topic, "subtopic": sid}],
                       "key_learning": ["taught after"]}]
    summary = cme.guideline_summary(st, cme.new_guidelines(st), "seeded", TODAY)
    queue = {q["tag"]: q for q in summary["teaching_to_recheck"]}
    assert [r["session"] for r in queue[tag]["rounds"]] == ["S0001"]
    assert queue[tag]["rounds"][0]["points"] == [{"id": "S0001.1", "point": "taught then"}]
    assert summary["central"]["set"] == "International" and summary["sweeps"] == "custom"
    assert summary["review_sweep_due"] == 0 and summary["swept"] == 0 and summary["rolling_quota"] == 0


# ---------------------------------------------------------------- a learner's install

class Learner(Work):
    def __init__(self, path):
        os.makedirs(str(path), exist_ok=True)
        super().__init__(path)

    def setup(self, config=None):
        cfg = dict({"mcqs": 1, "focused": 1, "case": True}, **(config or {}))
        self.run("--today", DAY, "init", "--work", self.path, "--blueprint", DEFAULT_BLUEPRINT,
                 "--config", json.dumps(cfg))
        self.publish()
        self.forget_job()
        return self

    def listed(self, kind="tag"):
        out = []
        folder = self.p("next")
        for name in sorted(os.listdir(folder)):
            if name.startswith(kind + "_checks_"):
                with open(os.path.join(folder, name)) as fh:
                    out += [line[2:].split(" — ")[0] for line in fh if line.startswith("- ")]
        return sorted(out)


@pytest.mark.parametrize("region", ["International", "Iceland/Europe"])
def test_a_default_blueprint_learner_is_not_swept_only_the_items_stale_tags(tmp_path, region):
    w = Learner(tmp_path / "w").setup({"guideline_region": region})
    w.open(today=DAY)
    out = w.run_json("--today", DAY, "prepare", "--work", w.path)["tag_checks"]
    assert out["sweeps"] == "custom" and out["central"] in ("International", "Europe")
    assert out["records"] == "seeded" and out["review_count"] == 0
    plan = w.read_json("next", "plan.json")
    items = plan["tag_checks"]["items"]
    assert w.listed() == items                     # no rolling sweep: only the items' tags with no fresh record
    idx = cme.guideline_records(shipped()["sets"][out["central"]])
    assert all(not (idx.get(t) or {}).get("last_checked") for t in items)
    summary = w.run_json("tag-checks", "--work", w.path)
    assert summary["swept"] == 0 and summary["review_sweep_due"] == 0 and summary["rolling_quota"] == 0
    assert summary["central"]["covered"] == summary["tags"] > 350
    assert w.run_json("tag-checks", "--work", w.path, "--list", w.p("due"))["count"] == 0


def test_sweeping_all_brings_back_90s_sweeps_and_off_none(tmp_path):
    w = Learner(tmp_path / "w").setup()
    w.open(today=DAY)
    assert w.run_json("settings", "--work", w.path, "--config", '{"guideline_sweeps": "all"}')["ok"]
    out = w.run_json("tag-checks", "--work", w.path, "--list", w.p("due"))
    summary = w.run_json("tag-checks", "--work", w.path)
    assert summary["swept"] == summary["tags"] and summary["rolling_quota"] == math.ceil(summary["tags"] / 12.0)
    assert out["count"] == summary["review_sweep_due"]      # every tag not checked within 30 days
    w.run_json("settings", "--work", w.path, "--config", '{"guideline_sweeps": "off"}')
    assert w.run_json("tag-checks", "--work", w.path, "--list", w.p("due"))["count"] == 0
    r = w.run("settings", "--work", w.path, "--config", '{"guideline_sweeps": "sometimes"}', ok=False)
    assert r.returncode == 2 and "guideline_sweeps" in json.loads(r.stdout)["error"]


def test_a_setting_of_sweeps_keeps_the_prepared_round():
    assert "guideline_sweeps" in cme.CONTENT_NEUTRAL_CONFIG
    st = cme.make_current(cme.new_state(TODAY))
    assert st["config"]["guideline_sweeps"] == "custom"     # the declared shape gives older ledgers the default


def test_a_learner_on_any_other_region_reads_international_and_sweeps_only_with_all(tmp_path):
    w = Learner(tmp_path / "w").setup({"guideline_region": "Japan"})
    w.open(today=DAY)
    out = w.run_json("--today", DAY, "prepare", "--work", w.path)["tag_checks"]
    assert out["central"] == "International" and out["records"] == "seeded"
    assert w.listed() == w.read_json("next", "plan.json")["tag_checks"]["items"]     # no rolling sweep
    w.run_json("settings", "--work", w.path, "--config", '{"guideline_sweeps": "all"}')
    summary = w.run_json("tag-checks", "--work", w.path)
    assert summary["swept"] == summary["tags"] and summary["rolling_quota"] == math.ceil(summary["tags"] / 12.0)


# ---------------------------------------------------------------- the maintainer's job

def central(tmp_path, *args, ok=True):
    r = run_script(CME, ["--today", DAY, "central-checks", "--file", os.path.join(str(tmp_path), "gc.json")]
                   + list(args), cwd=str(tmp_path))
    if ok:
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout)
    return r


@pytest.fixture
def copy_(tmp_path):
    """A copy of the shipped template in a fixed state (what it holds changes with every central run):
    in each set the first 300 of the default blueprint's 391 tags checked on DAY, current."""
    doc = shipped()
    st = default_state()
    tags = sorted(cme.blueprint_tags(st))[:300]
    for s in doc["sets"].values():
        s["records"] = [rec(t, DAY) for t in tags]
    with open(os.path.join(str(tmp_path), "gc.json"), "w") as fh:
        json.dump(doc, fh)
    return tmp_path


def test_central_checks_alone_summarises_and_validates(copy_):
    out = central(copy_)
    assert out["valid"] and out["problems"] == [] and out["blueprint_tags"] == 391
    assert out["sets"]["Europe"]["never_checked"] == out["sets"]["Europe"]["due"] == 91
    assert central(copy_, "--validate")["valid"]


def test_central_checks_lists_the_due_tags_never_checked_first_in_lists_of_forty(copy_):
    out = central(copy_, "--list", str(copy_ / "lists"))
    assert out["due"] == {"International": 91, "Europe": 91} and out["count"] == 182
    assert len(out["checkers"]) == 6 and {c["set"] for c in out["checkers"]} == {"International", "Europe"}
    first = out["checkers"][0]
    assert os.path.basename(first["list"]) == "international_checks_1.md"
    assert os.path.basename(first["results"]) == "international_results_1.md"
    with open(first["list"]) as fh:
        text = fh.read()
    assert "Region: International" in text and "never checked" in text
    assert all(sum(1 for l in open(c["list"]) if l.startswith("- ")) <= 40 for c in out["checkers"])
    # a share per run: ceil(391 / 12) = 33 of the 91 due, the never-checked first; one set only
    out = central(copy_, "--list", str(copy_ / "lists"), "--share", "12", "--region", "Europe")
    assert out["due"] == {"Europe": 33} and sorted(os.listdir(str(copy_ / "lists"))) == ["europe_checks_1.md"]
    with open(out["checkers"][0]["list"]) as fh:
        assert [l.endswith("never checked\n") for l in fh if l.startswith("- ")] == [True] * 33
    # 30 days later, nothing checked: still the never-checked; after 100 days every tag is due
    later = run_script(CME, ["--today", "2027-03-07", "central-checks", "--file", str(copy_ / "gc.json"),
                             "--list", str(copy_ / "l2"), "--region", "International"])
    assert json.loads(later.stdout)["due"] == {"International": 391}


def test_central_checks_files_results_into_the_set_and_validates(copy_):
    out = central(copy_, "--list", str(copy_ / "lists"), "--region", "Europe")
    lst = out["checkers"][0]
    with open(lst["list"]) as fh:
        tags = [l[2:].split(" — ")[0] for l in fh if l.startswith("- ")]
    lines = ["Tag: %s | superseded | %s NEW | https://example.org | new edition" % (tags[0], tags[0])]
    lines += ["Tag: %s | current | - | https://example.org | latest" % t for t in tags[1:]]
    lines += ["Tag: nonsense", "Tag: NOT ON THE LIST | current | - | x | y"]
    with open(lst["results"], "w") as fh:
        fh.write("\n".join(lines) + "\n")
    filed = central(copy_, "--results", lst["results"], "--results", str(copy_ / "lists" / "europe_results_9.md"))
    assert filed["filed"]["Europe"]["superseded"] == 1 and filed["filed"]["Europe"]["current"] == len(tags) - 1
    assert filed["unreadable"] == 1 and len(filed["files_missing"]) == 1
    assert filed["not_listed"] == ["NOT ON THE LIST"]
    with open(str(copy_ / "gc.json")) as fh:
        doc = json.load(fh)
    eu = cme.guideline_records(doc["sets"]["Europe"])
    assert eu[tags[0]]["status"] == "superseded" and eu[tags[0]]["since"] == DAY
    assert eu[tags[0] + " NEW"]["status"] == "current" and eu[tags[1]]["last_checked"] == DAY
    assert doc["sets"]["Europe"]["updated"] == DAY == doc["updated"]
    assert tags[0] not in cme.guideline_records(doc["sets"]["International"])     # the other set is untouched
    assert "NOT ON THE LIST" not in eu                                             # no junk records
    assert central(copy_, "--validate")["valid"]
    # the successor is what is due next time, not the superseded tag
    assert central(copy_)["sets"]["Europe"]["superseded"] == [tags[0]]


def test_central_checks_refuses_results_that_would_not_validate_and_a_broken_file(copy_):
    out = central(copy_, "--list", str(copy_ / "lists"), "--region", "International")
    res = out["checkers"][0]["results"]
    with open(out["checkers"][0]["list"]) as fh:
        a, b = [l[2:].split(" — ")[0] for l in fh if l.startswith("- ")][:2]
    with open(res, "w") as fh:          # a superseded by b, b by a: a loop
        fh.write("Tag: %s | superseded | %s | x | y\nTag: %s | superseded | %s | x | y\n" % (a, b, b, a))
    before = open(str(copy_ / "gc.json")).read()
    r = central(copy_, "--results", res, ok=False)
    assert r.returncode == 2 and "supersedes itself" in json.loads(r.stdout)["error"]
    assert open(str(copy_ / "gc.json")).read() == before
    r = central(copy_, "--results", str(copy_ / "unnamed.md"), ok=False)
    assert r.returncode == 2 and "--region" in json.loads(r.stdout)["error"]
    doc = json.loads(before)
    doc["sets"]["Europe"]["records"].append(dict(doc["sets"]["Europe"]["records"][0]))     # twice
    doc["sets"]["Europe"]["records"][1]["status"] = "outdated"
    doc["sets"]["Europe"]["regions"].append("International")
    with open(str(copy_ / "gc.json"), "w") as fh:
        json.dump(doc, fh)
    r = central(copy_, "--validate", ok=False)
    err = json.loads(r.stdout)["error"]
    assert r.returncode == 2 and "twice" in err and "outdated" in err and "International" in err

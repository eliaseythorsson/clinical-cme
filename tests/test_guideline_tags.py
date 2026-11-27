"""Guideline tags as a baseline (issue #90, ADR 0011): each distinct tag of the blueprint's decision
points has a check record in data/guidelines.json; `prepare` lists the tags to check while the next
round is prepared (the items' tags not checked within 90 days, a rolling sweep of ceil(N/12) of the
rest, never-checked first, then the oldest; before a review, every tag not checked within 30 days),
`finish-prepare` and `tag-checks --results` file the checkers' results (lists of at most 40, one
checker each; a review sweep filed after the round is stashed), the records file is found by its
content and carried through a rebase, a superseded tag is overlaid where the engine hands decision
points to the author, never written into the learner's blueprint, and the teaching that rested on a
changed or superseded tag is queued for the review's guideline-change check, never made an erratum."""
import datetime as dt
import json
import math
import os
import re
import shutil

import pytest

import examples
from conftest import DEFAULT_BLUEPRINT, Work
from examples import cme
from test_finish_prepare import evidence

DAY = "2026-11-27"
TODAY = dt.date(2026, 11, 27)
GUIDE = "data/guidelines.json"


def blueprint():
    """Four topics of two sub-topics, three decision points each, every point with its own tag (23),
    and one point that cites two guidelines: 25 distinct tags, G00 … G73 and X1, X2."""
    topics, subs = {}, {}
    for t in range(4):
        tid = "CARD-%02d" % (t + 1)
        topics[tid] = "Topic %d" % (t + 1)
        subs[tid] = {}
        for s in range(2):
            j = 2 * t + s
            points = ["Decision %d.%d [G%d%d]" % (j, i, j, i) for i in range(3)]
            if j == 7:
                points[2] = "Decision 7.2 [X1; X2]"
            subs[tid]["%s%s" % (tid, "ab"[s])] = {"label": "Angle %d" % j, "points": points}
    return {"CARD": {"name": "Cardiology", "weight": 1.0, "topics": topics, "subtopics": subs}}


ALL_TAGS = sorted(["G%d%d" % (j, i) for j in range(8) for i in range(3) if (j, i) != (7, 2)] + ["X1", "X2"])


def state(**config):
    st = cme.make_current(cme.new_state(TODAY))
    st["blueprint"] = blueprint()
    st["config"].update(config)
    return st


def rec(tag, days_ago=None, status="current", by=None):
    return {"tag": tag, "last_checked": None if days_ago is None else cme.iso(TODAY - dt.timedelta(days=days_ago)),
            "status": status, "superseded_by": by, "source": "https://example.org/%s" % tag, "note": None}


def index(*recs):
    return {r["tag"]: r for r in recs}


# ---------------------------------------------------------------- the unit checked and what is due

def test_tags_are_the_distinct_citations_of_the_live_decision_points():
    st = state()
    assert sorted(cme.blueprint_tags(st)) == ALL_TAGS and len(ALL_TAGS) == 25
    assert cme.point_tags("Which ECG patterns [ESC ACS 2023]") == ["ESC ACS 2023"]
    assert cme.point_tags("Two [GOLD 2027; ERS/ATS COPD exacerbations 2017]") == ["GOLD 2027",
                                                                                   "ERS/ATS COPD exacerbations 2017"]
    assert cme.point_tags("No tag here") == []
    st["blueprint"]["CARD"]["topics"]["CARD-04"] = "Topic 4 (retired)"
    assert "G60" not in cme.blueprint_tags(st) and "X1" not in cme.blueprint_tags(st)


def test_the_default_blueprint_has_its_tags_and_its_seed_covers_the_checked_ones():
    with open(DEFAULT_BLUEPRINT) as fh:
        bp = json.load(fh)
    st = state()
    st["blueprint"] = bp
    tags = cme.blueprint_tags(st)
    assert len(tags) > 350
    doc, how = cme.seeded_guidelines(st)
    assert how == "seeded" and all(r["tag"] in tags for r in doc["records"])
    seeded = {r["tag"] for r in doc["records"]}
    # the #89 pass left tags it did not search unchecked: the first sweeps go to them
    assert "NICE NG234 2023" in tags and "NICE NG234 2023" not in seeded
    assert {r["status"] for r in doc["records"]} <= {"current", "uncertain"}
    assert all(r["last_checked"] == "2026-11-27" for r in doc["records"])
    # checked for Europe: another region starts with no records
    st["config"]["guideline_region"] = "United States"
    assert cme.seeded_guidelines(st) == (cme.new_guidelines(st), "new")


def test_rolling_sweep_takes_a_fixed_share_never_checked_first_then_the_oldest():
    st = state()
    idx = index(rec("G00", 10), rec("G01", 200), rec("G02", 120), rec("G10", 91), rec("G11", 90),
                *[rec(t, 5) for t in ALL_TAGS if t[:2] in ("G2", "G3", "G4", "G5", "G6")])
    never = [t for t in ALL_TAGS if t not in idx]
    assert never == ["G12", "G70", "G71", "X1", "X2"]
    mine, sweep = cme.due_tags(st, idx, TODAY, (), "rolling", 12)
    assert mine == [] and len(sweep) == math.ceil(25 / 12.0) == 3
    assert sweep == ["G12", "G70", "G71"]                     # never checked first, by name
    # the never-checked done: the oldest next; one checked exactly 90 days ago is still fresh
    for t in never:
        idx[t] = rec(t, 1)
    mine, sweep = cme.due_tags(st, idx, TODAY, (), "rolling", 12)
    assert sweep == sorted(["G01", "G02", "G10"])
    # 1/16: ceil(25/16) = 2, the two oldest
    assert cme.due_tags(st, idx, TODAY, (), "rolling", 16)[1] == ["G01", "G02"]
    # the quota is a share of the whole set, not of the stale subset: fewer stale, only those
    idx["G01"], idx["G02"] = rec("G01", 1), rec("G02", 1)
    assert cme.due_tags(st, idx, TODAY, (), "rolling", 12)[1] == ["G10"]


def test_the_items_tags_are_checked_unless_checked_within_90_days_and_apart_from_the_quota():
    st = state()
    idx = index(*[rec(t, 200) for t in ALL_TAGS])
    idx["G00"] = rec("G00", 30)
    mine, sweep = cme.due_tags(st, idx, TODAY, ["G00", "G01", "G02"], "rolling", 12)
    assert mine == ["G01", "G02"] and len(sweep) == 3 and not set(sweep) & {"G00", "G01", "G02"}


def test_the_review_sweep_takes_every_tag_not_checked_within_30_days():
    st = state()
    idx = index(*[rec(t, 31) for t in ALL_TAGS[:10]], *[rec(t, 30) for t in ALL_TAGS[10:20]])
    mine, sweep = cme.due_tags(st, idx, TODAY, ["G00"], "review", 12)
    assert mine == ["G00"] or mine == []
    assert sorted(set(mine) | set(sweep)) == sorted(ALL_TAGS[:10] + ALL_TAGS[20:])


def test_sweep_share_stays_between_one_twelfth_and_one_sixteenth():
    assert cme.sweep_divisor({}) == 12 and cme.sweep_divisor({"sweep": 14}) == 14
    assert cme.sweep_divisor({"sweep": 30}) == 16 and cme.sweep_divisor({"sweep": 3}) == 12


# ---------------------------------------------------------------- superseded tags: overlaid, never written back

def test_a_superseded_tag_is_overlaid_in_the_plan_and_followed_down_its_chain():
    idx = index(rec("G00", 1, "superseded", "G00 2026"), rec("G00 2026", 1, "superseded", "G00 2027"),
                rec("G01", 1, "changed"), rec("X1", 1, "superseded", "X2"))
    assert cme.current_tag("G00", idx) == "G00 2027"
    assert cme.overlay_point("Decision [G00]", idx) == "Decision [G00 2027]"
    assert cme.overlay_point("Decision [X1; X2]", idx) == "Decision [X2]"
    assert cme.overlay_point("Decision [G01]", idx) == "Decision [G01]"
    a = {"tag": "A", "status": "superseded", "superseded_by": "B"}
    loop = {"A": a, "B": {"tag": "B", "status": "superseded", "superseded_by": "A"}}
    assert cme.current_tag("A", loop) in ("A", "B")           # a loop ends
    plan = {"items": [{"subtopic": {"id": "CARD-01a", "points": ["One [G00]", "Two [G01]", "Three [G02]"]}}]}
    assert cme.overlay_plan(plan, idx) == 1
    sub = plan["items"][0]["subtopic"]
    assert sub["points"] == ["One [G00 2027]", "Two [G01]", "Three [G02]"]
    assert [(g["tag"], g["status"]) for g in sub["guidelines"]] == [("G00", "superseded"), ("G01", "changed")]
    assert cme.plan_tags(plan) == ["G00 2027", "G01", "G02"]


# ---------------------------------------------------------------- filing results

def test_results_are_read_from_tag_lines_and_bad_lines_counted():
    text = ("Some heading\n"
            "Tag: G00 | current | - | https://a.org | still the latest\n"
            "**Tag:** G01 | Superseded | G01 2026 | https://b.org | new edition\n"
            "Tag: G02 | superseded | - | https://c.org\n"          # superseded without its successor
            "Tag: G10 | outdated | - | x\n")                        # not a status
    res, bad = cme.parse_tag_results(text)
    assert bad == 2 and sorted(res) == ["G00", "G01"]
    assert res["G01"] == {"status": "superseded", "superseded_by": "G01 2026", "source": "https://b.org",
                          "note": "new edition"}
    assert res["G00"]["superseded_by"] is None and res["G00"]["note"] == "still the latest"


def test_filing_dates_the_records_gives_the_successor_one_and_writes_no_erratum():
    st = state()
    doc = {"kind": cme.GUIDELINES_KIND, "records": [rec("G00", 200), rec("G20", 200)]}
    results = {"G00": {"status": "superseded", "superseded_by": "G00 2026", "source": "s", "note": "n"},
               "G20": {"status": "current", "superseded_by": None, "source": "s", "note": None},
               "G40": {"status": "changed", "superseded_by": None, "source": "s", "note": "focused update"}}
    counts = cme.file_tag_results(st, doc, results, TODAY)
    assert counts == {"current": 1, "changed": 1, "superseded": 1, "uncertain": 0}
    idx = cme.guideline_records(doc)
    assert idx["G00"]["last_checked"] == DAY and idx["G00"]["superseded_by"] == "G00 2026"
    assert idx["G00"]["since"] == DAY and idx["G40"]["since"] == DAY and "since" not in idx["G20"]
    assert idx["G00 2026"]["status"] == "current" and idx["G00 2026"]["last_checked"] == DAY
    assert st["pending_errata"] == [] and st["blueprint"] == blueprint()      # never rewritten
    # found the same again later: the day of the finding stays
    later = TODAY + dt.timedelta(days=40)
    cme.file_tag_results(st, doc, results, later)
    idx = cme.guideline_records(doc)
    assert idx["G00"]["since"] == DAY and idx["G00"]["last_checked"] == cme.iso(later)


def test_the_reviews_queue_is_derived_from_the_records_and_the_rounds():
    """The teaching that rested on a changed or superseded tag goes to the review's guideline-change
    check: rounds held before the finding, on a sub-topic citing the tag, their teaching points not
    checked since; derived when asked, so nothing is lost if a publish stopped half-way."""
    st = state()
    item = lambda sub: [{"type": "mcq", "topic": sub[:7], "subtopic": sub}]
    st["previous"] = [{"id": "S0001", "date": "2026-09-01", "items": item("CARD-01a")}]
    st["sessions"] = [{"id": "S0003", "date": "2026-10-01", "items": item("CARD-01a"), "key_learning": ["a", "b"]},
                      {"id": "S0004", "date": "2026-10-02", "items": item("CARD-02a"), "key_learning": ["c"]},
                      {"id": "S0006", "date": "2026-11-28", "items": item("CARD-01a"), "key_learning": ["d"]}]
    st["teaching_point_checks"] = {"S0003.2": {"checked": "2026-11-30", "status": "current"}}
    doc = {"kind": cme.GUIDELINES_KIND, "records": [
        dict(rec("G00", 0, "superseded", "G00 2026"), since=DAY),       # CARD-01a cites G00
        dict(rec("G20", 0, "changed"), since="2026-10-01"),               # CARD-02a cites G20: S0004 is after
        rec("G30", 0)]}
    queue = cme.guideline_recheck(st, doc)
    assert [q["tag"] for q in queue] == ["G00"]
    q = queue[0]
    assert q["status"] == "superseded" and q["superseded_by"] == "G00 2026" and q["since"] == DAY
    assert q["rounds"] == [{"session": "S0001", "date": "2026-09-01", "points": None},
                           {"session": "S0003", "date": "2026-10-01", "points": [{"id": "S0003.1", "point": "a"}]}]
    # a point checked before the finding is queued again; S0006 came after it and is not
    st["teaching_point_checks"]["S0003.2"]["checked"] = "2026-11-01"
    assert [p["id"] for p in cme.guideline_recheck(st, doc)[0]["rounds"][1]["points"]] == ["S0003.1", "S0003.2"]
    # the successor superseded in turn: rounds that cited the first tag are still found through the chain
    doc["records"].append(dict(rec("G00 2026", 0, "superseded", "G00 2027"), since=DAY))
    assert "G00 2026" in [q["tag"] for q in cme.guideline_recheck(st, doc)]
    # the review gets it from stats / tag-checks, as `teaching_to_recheck`
    assert cme.guideline_summary(st, doc, "read", TODAY)["teaching_to_recheck"][0]["tag"] == "G00"


def test_a_bracket_with_two_guidelines_holds_two_tags_each_checked_once():
    st = state()
    tags = cme.blueprint_tags(st)
    assert tags["X1"] == 1 and tags["X2"] == 1 and "X1; X2" not in tags
    st["blueprint"]["CARD"]["subtopics"]["CARD-01"]["CARD-01a"]["points"].append("Another [X1;G00 ]")
    tags = cme.blueprint_tags(st)
    assert tags["X1"] == 2 and tags["G00"] == 2


def test_tags_are_split_into_lists_of_at_most_forty():
    assert cme.tag_chunks([]) == []
    assert [len(c) for c in cme.tag_chunks(["t%03d" % i for i in range(33)])] == [33]
    sizes = [len(c) for c in cme.tag_chunks(["t%03d" % i for i in range(300)])]
    assert sizes == [38, 38, 38, 38, 37, 37, 37, 37] and all(30 <= n <= 40 for n in sizes)
    chunks = cme.tag_chunks(["t%03d" % i for i in range(391)])
    assert len(chunks) == 10 and sum(chunks, []) == sorted("t%03d" % i for i in range(391))


def test_the_review_is_looked_for_as_far_ahead_as_the_gap_between_rounds_at_least_a_week():
    assert cme.review_lookahead(state(target_sessions_per_week=3)) == 7
    assert cme.review_lookahead(state(target_sessions_per_week=1)) == 7
    assert cme.review_lookahead(state(target_sessions_per_week=0.5)) == 14
    assert cme.review_lookahead(state(target_sessions_per_week=0)) == 7


# ---------------------------------------------------------------- the engine's commands

def write_blueprint(tmp_path):
    path = os.path.join(str(tmp_path), "bp.json")
    with open(path, "w") as fh:
        json.dump(blueprint(), fh)
    return path


class Learner(Work):
    """A learner on the tagged blueprint, with their folder store read into store/."""

    def __init__(self, path):
        os.makedirs(str(path), exist_ok=True)
        super().__init__(path)

    def setup(self, tmp_path, config=None):
        cfg = dict({"mcqs": 1, "focused": 1, "case": True}, **(config or {}))
        self.run("--today", DAY, "init", "--work", self.path, "--blueprint", write_blueprint(tmp_path),
                 "--config", json.dumps(cfg))
        self.publish()
        self.forget_job()
        return self

    def prepare(self, today=DAY):
        self.open(today=today)
        return self.run_json("--today", today, "prepare", "--work", self.path)

    def draft(self, results=None):
        st = self.read_json("publish", "data", "state.json") if os.path.isfile(self.pub("data", "state.json")) \
            else self.read_ledger()
        plan = self.read_json("next", "plan.json")
        shorts = [it for it in plan["items"] if it["slot"] != "case"]
        subs = dict(("Q%d" % (i + 1), (it.get("subtopic") or {}).get("id")) for i, it in enumerate(shorts))
        subs["case"] = next(((it.get("subtopic") or {}).get("id") for it in plan["items"] if it["slot"] == "case"), None)
        for name, text in examples.sealed_files(st, plan).items():
            for kid, sid in subs.items():      # the author writes the sub-topic the plan gives (rule 9)
                if sid:
                    text = re.sub(r"(<!-- key: %s -->\n(?:.*\n)*?topic: .*\n)" % kid, r"\1subtopic: %s\n" % sid,
                                  text, count=1)
            self.write(os.path.join("next", name), text)
        for part in ("questions", "case"):
            self.write(os.path.join("next", "evidence_%s.md" % part), evidence())
        if results is not None:
            for c in plan["tag_checks"]["lists"]:
                self.write(os.path.join("next", c.replace("_checks_", "_results_")), results)
        return plan

    def finish(self, *extra):
        return self.run_json("finish-prepare", "--work", self.path, *extra)

    def listed(self, kind="tag"):
        """The tags of the lists `prepare` wrote for checkers (with the round, or the review sweep)."""
        out = []
        for name in sorted(os.listdir(self.p("next"))):
            if name.startswith(kind + "_checks_"):
                with open(self.p("next", name)) as fh:
                    out += [line[2:].split(" — ")[0] for line in fh if line.startswith("- ")]
        return sorted(out)


def lines(tags, status="current", by="-"):
    return "".join("Tag: %s | %s | %s | https://example.org | checked\n" % (t, status, by) for t in tags)


@pytest.fixture
def learner(tmp_path):
    return Learner(tmp_path / "w").setup(tmp_path)


def test_prepare_lists_the_tags_due_and_prints_counts_only(learner):
    out = learner.prepare()
    tc = out["tag_checks"]
    assert tc["kind"] == "rolling" and tc["records"] == "new" and tc["review_count"] == 0
    assert tc["checkers"] == [{"list": learner.p("next", "tag_checks_1.md"),
                               "results": learner.p("next", "tag_results_1.md")}]
    plan = learner.read_json("next", "plan.json")
    items = plan["tag_checks"]["items"]
    assert items == cme.plan_tags(plan) and items          # nothing checked yet: every item's tag
    listed = learner.listed()
    assert listed == sorted(listed)                        # the items' tags not told apart from the sweep's
    assert set(items) <= set(listed) and tc["count"] == len(listed) == len(items) + 3
    for t in ALL_TAGS:                                     # no tag name is printed
        assert "[%s]" % t not in json.dumps(out) and " %s " % t not in json.dumps(out)


def test_results_filed_by_finish_prepare_go_into_the_publish_set_with_the_ledger(learner):
    learner.prepare()
    listed = learner.listed()
    plan = learner.draft(lines(listed))
    out = learner.finish()
    assert out["stashed"] is True and out["tag_checks"]["filed"] == len(listed) == out["tag_checks"]["answered"]
    assert out["tag_checks"]["by_status"]["current"] == len(listed)
    assert [f["as"] for f in out["files"]] == ["data/page.json", GUIDE, "data/prepared.json", "data/state.json"]
    doc = learner.read_json("publish", *GUIDE.split("/"))
    st = learner.read_json("publish", "data", "state.json")
    assert st["guidelines_gen"] == doc["gen"] == 1 and doc["region"] == "Iceland/Europe"
    assert {r["tag"] for r in doc["records"]} == set(listed)
    assert all(r["last_checked"] == DAY for r in doc["records"])
    # a content-neutral write: the prepared round is tied to the ledger it was planned on and stays usable
    assert learner.read_json("publish", "data", "prepared.json")["gen"] == plan["prepared"]["gen"]
    learner.publish()
    assert learner.start("2026-11-28")["prepared"]["used"] is True
    # the next preparation reads the records: the tags just checked are not due again
    learner.forget_job()
    again = learner.prepare("2026-11-29")
    assert again["tag_checks"]["records"] == "read"
    assert not set(learner.listed()) & set(listed)


def test_missing_results_hold_nothing_up(learner):
    learner.prepare()
    learner.draft()
    out = learner.finish()
    assert out["stashed"] is True and out["tag_checks"]["results_missing"].startswith("1 of 1")
    assert GUIDE not in [f["as"] for f in out["files"]] and "warnings" not in out


def test_an_items_tag_found_superseded_sends_the_author_back_once(learner):
    learner.prepare()
    plan = learner.read_json("next", "plan.json")
    item = plan["tag_checks"]["items"][0]
    learner.draft(lines([item], "superseded", item + " NEW") + lines([t for t in learner.listed() if t != item]))
    out = learner.finish()
    assert out["revise"] is True and out["stashed"] is False and "tag_results_<n>.md" in out["next"]
    assert out["tag_checks"]["items_changed"] == 1 and out["tag_checks"]["by_status"]["superseded"] == 1
    assert not os.path.isfile(learner.pub(*GUIDE.split("/")))       # filed when the round is stashed
    done = learner.finish("--revised")
    assert done["stashed"] is True and done["tag_checks"]["filed"] == len(learner.listed())
    idx = cme.guideline_records(learner.read_json("publish", *GUIDE.split("/")))
    assert idx[item]["status"] == "superseded" and idx[item + " NEW"]["status"] == "current"
    # the next plan cites the newer guideline; the learner's blueprint is unchanged
    learner.publish()
    learner.forget_job()
    learner.prepare("2026-11-29")
    st = learner.read_ledger()
    assert "[%s]" % item in json.dumps(st["blueprint"]) and "NEW" not in json.dumps(st["blueprint"])
    assert item not in learner.listed() + cme.plan_tags(learner.read_json("next", "plan.json"))


def test_the_review_sweep_runs_ahead_apart_from_the_round_and_is_filed_after_the_stash(learner):
    learner.open(today=DAY)
    learner.write("tags.md", lines(ALL_TAGS[:20]))
    learner.run_json("tag-checks", "--work", learner.path, "--results", learner.p("tags.md"))
    learner.publish()
    learner.forget_job()
    st = learner.read_ledger()
    st["review"]["next_due"] = "2027-03-10"
    st["sessions"] = [{"id": "S%04d" % i, "date": "2026-12-0%d" % i, "items": []} for i in range(1, 4)]
    learner.write_ledger(st)
    # 63 days before the review: a rolling sweep; 5 days before (within the week ahead): the review sweep
    assert learner.prepare("2027-01-06")["tag_checks"]["kind"] == "rolling"
    learner.forget_job()
    out = learner.prepare("2027-03-05")["tag_checks"]
    plan = learner.read_json("next", "plan.json")
    items = plan["tag_checks"]["items"]
    assert out["kind"] == "review" and out["count"] == len(items) == len(learner.listed()) > 0
    assert out["review_count"] == 25 - len(items) == len(learner.listed("review"))
    assert [c["results"] for c in out["review_checkers"]] == [learner.p("next", "review_results_1.md")]
    # the round is stashed with its own tags; the review sweep is not waited for
    learner.draft(lines(learner.listed()))
    done = learner.finish()
    assert done["stashed"] is True and done["tag_checks"]["filed"] == len(items)
    learner.write(os.path.join("next", "review_results_1.md"), lines(learner.listed("review")))
    filed = learner.run_json("tag-checks", "--work", learner.path, "--results",
                             learner.p("next", "review_results_1.md"))
    assert filed["filed"] == 25 - len(items) and filed["files_missing"] == 0
    g = learner.run_json("stats", "--work", learner.path)["guidelines"]
    assert g["tags"] == 25 and g["checked_within_30_days"] == 25 and g["review_sweep_due"] == 0
    assert g["by_status"]["current"] == 25 and g["sweep"] == "1/12" and g["rolling_quota"] == 3
    assert g["teaching_to_recheck"] == []
    # the prepared round stays usable after the sweep is filed
    learner.publish()
    assert learner.start("2027-03-06")["prepared"]["used"] is True


def test_a_large_review_sweep_goes_to_one_checker_per_list_of_at_most_forty(tmp_path):
    w = Learner(tmp_path / "w")
    w.run("--today", DAY, "init", "--work", w.path, "--blueprint", DEFAULT_BLUEPRINT, "--config",
          json.dumps({"guideline_region": "Elsewhere"}))
    w.publish()
    w.forget_job()
    w.open(today=DAY)
    out = w.run_json("tag-checks", "--work", w.path, "--list", w.p("sweep"))
    assert out["count"] > 350 and len(out["checkers"]) == math.ceil(out["count"] / 40.0)
    sizes = []
    for c in out["checkers"]:
        with open(c["list"]) as fh:
            sizes.append(sum(1 for line in fh if line.startswith("- ")))
    assert sum(sizes) == out["count"] and all(30 <= n <= 40 for n in sizes)
    # every results file is read by one command (once per file); a missing one is counted
    w.write(os.path.join("sweep", "tag_results_1.md"), lines(["NICE NG234 2023"]))
    filed = w.run_json("tag-checks", "--work", w.path, "--results", out["checkers"][0]["results"],
                       "--results", out["checkers"][1]["results"])
    assert filed["filed"] == 1 and filed["files_missing"] == 1


def test_seeding_is_skipped_for_another_region(tmp_path):
    w = Learner(tmp_path / "w")
    w.run("--today", DAY, "init", "--work", w.path, "--blueprint", DEFAULT_BLUEPRINT, "--config",
          json.dumps({"guideline_region": "United States", "mcqs": 1, "focused": 0, "case": False}))
    w.publish()
    w.forget_job()
    assert w.prepare()["tag_checks"]["records"] == "new"
    w.forget_job()
    w.open(today=DAY)
    summary = w.run_json("tag-checks", "--work", w.path)
    assert summary["never_checked"] == summary["tags"] > 350
    st = w.read_ledger()
    st["config"]["guideline_region"] = "Iceland/Europe"
    w.write_ledger(st)
    w.forget_job()
    assert w.prepare()["tag_checks"]["records"] == "seeded"


def test_tag_checks_lists_files_and_sets_the_sweep(learner):
    learner.open(today=DAY)
    out = learner.run_json("tag-checks", "--work", learner.path, "--list", learner.p("due"))
    assert out["count"] == 25 and out["due"] == "review" and len(out["checkers"]) == 1
    out = learner.run_json("tag-checks", "--work", learner.path, "--list", learner.p("due"), "--due", "rolling")
    assert out["count"] == 3 and sorted(os.listdir(learner.p("due"))) == ["tag_checks_1.md"]
    out = learner.run_json("tag-checks", "--work", learner.path, "--sweep", "16")
    assert out["sweep"] == "1/16" and [f["as"] for f in out["files"]][-2:] == [GUIDE, "data/state.json"]
    assert learner.run_json("tag-checks", "--work", learner.path)["rolling_quota"] == 2
    r = learner.run("tag-checks", "--work", learner.path, "--sweep", "20", ok=False)
    assert r.returncode == 2
    learner.write("res.md", lines(["G00"], "superseded", "G00 2026") + "Tag: nonsense\n")
    out = learner.run_json("tag-checks", "--work", learner.path, "--results", learner.p("res.md"))
    assert out["filed"] == 1 and out["unreadable"] == 1 and out["by_status"]["superseded"] == 1
    assert "errata" not in out and learner.read_json("publish", "data", "state.json")["pending_errata"] == []
    summary = learner.run_json("tag-checks", "--work", learner.path)
    assert summary["superseded"][0]["tag"] == "G00" and summary["superseded"][0]["superseded_by"] == "G00 2026"
    assert summary["tags"] == 25 and summary["never_checked"] == 24            # G00 2026 stands for G00
    assert [s["cmd"] for s in learner.read_json("work.json")["steps"]] == ["tag-checks", "tag-checks"]


# ---------------------------------------------------------------- the store: recognised, never published over, rebased

def filed(learner, tags=ALL_TAGS[:5]):
    learner.open(today=DAY)
    learner.write("res.md", lines(tags))
    learner.run_json("tag-checks", "--work", learner.path, "--results", learner.p("res.md"))
    learner.publish()
    learner.forget_job()


def test_the_records_file_is_found_by_its_content_whatever_its_name(learner):
    filed(learner)
    os.replace(learner.store(*GUIDE.split("/")), learner.store("download-3.json"))
    out = learner.open(today=DAY)
    assert out["recognised"] == {GUIDE: "download-3.json"} and GUIDE in out["store_files"]
    assert learner.run_json("tag-checks", "--work", learner.path)["records"] == "read"
    assert cme.store_role(learner.store("download-3.json")) == GUIDE


def test_records_the_job_did_not_read_are_never_published_over(learner):
    filed(learner)
    os.remove(learner.store(*GUIDE.split("/")))
    out = learner.prepare()
    assert out["tag_checks"]["count"] == 0 and "not read" in out["tag_checks"]["skipped"]
    assert not os.path.isfile(learner.p("next", "tag_checks.md"))
    r = learner.run("tag-checks", "--work", learner.path, "--results", learner.p("res.md"), ok=False)
    assert r.returncode == 2 and "not read" in json.loads(r.stdout)["error"]


def test_a_stale_copy_of_the_records_counts_as_not_read(learner):
    filed(learner)
    old = learner.read_json("store", *GUIDE.split("/"))
    filed(learner, ALL_TAGS[5:8])
    learner.write(os.path.join("store", *GUIDE.split("/")), old)
    assert "skipped" in learner.prepare()["tag_checks"]


def test_start_does_not_read_the_records(learner):
    learner.write(os.path.join("store", *GUIDE.split("/")), "not json at all {")
    out = learner.start(DAY)
    assert out["ok"] and "tag_checks" not in learner.read_json("plan.json")


def test_a_rebase_files_the_tags_although_the_prepared_round_is_dropped(tmp_path):
    """Two devices on one folder store: one prepares a round and checks tags, the other changes a
    setting that sets the prepared round aside and publishes first. The rebase drops the prepared
    round, and still files the tag checks on the store as it is now."""
    shared = tmp_path / "shared"
    a = Learner(tmp_path / "a").setup(tmp_path)
    shutil.copytree(a.store(), str(shared))
    a.store = lambda *parts: os.path.join(str(shared), *parts)
    b = Learner(tmp_path / "b")
    b.store = a.store
    a.run_json("--today", DAY, "open", "--work", a.path, "--store", a.store())
    a.run_json("--today", DAY, "prepare", "--work", a.path)
    listed = a.listed()
    a.draft(lines(listed))
    assert a.finish()["tag_checks"]["filed"] == len(listed)
    b.run_json("--today", DAY, "open", "--work", b.path, "--store", b.store())
    b.run_json("settings", "--work", b.path, "--config", '{"session_minutes": 50}')
    b.run_json("publish", "--work", b.path)
    out = a.run_json("publish", "--work", a.path)
    step = out["rebased"]["steps"][0]
    assert step["cmd"] == "finish-prepare" and step["applied"].startswith("dropped") and step["tag_checks"] == "filed"
    st = a.read_json(str(shared / "data" / "state.json"))
    doc = a.read_json(str(shared / "data" / "guidelines.json"))
    assert st["config"]["session_minutes"] == 50 and st["guidelines_gen"] == doc["gen"]
    assert {r["tag"] for r in doc["records"]} == set(listed)
    assert a.read_json(str(shared / "data" / "prepared.json")).get("empty") is True


def test_a_rebase_builds_on_records_another_device_filed(tmp_path):
    shared = tmp_path / "shared"
    a = Learner(tmp_path / "a").setup(tmp_path)
    shutil.copytree(a.store(), str(shared))
    a.store = lambda *parts: os.path.join(str(shared), *parts)
    b = Learner(tmp_path / "b")
    b.store = a.store
    for dev in (a, b):
        dev.run_json("--today", DAY, "open", "--work", dev.path, "--store", dev.store())
    a.write("res.md", lines(["G00", "G01"]))
    a.run_json("tag-checks", "--work", a.path, "--results", a.p("res.md"))
    b.write("res.md", lines(["G10"], "superseded", "G10 2026"))
    b.run_json("tag-checks", "--work", b.path, "--results", b.p("res.md"))
    b.run_json("publish", "--work", b.path)
    out = a.run_json("publish", "--work", a.path)
    assert out["rebased"]["steps"] == [{"cmd": "tag-checks", "applied": True}]
    doc = a.read_json(str(shared / "data" / "guidelines.json"))
    idx = cme.guideline_records(doc)
    assert set(idx) == {"G00", "G01", "G10", "G10 2026"} and idx["G10"]["status"] == "superseded"
    assert doc["gen"] == 2 == a.read_json(str(shared / "data" / "state.json"))["guidelines_gen"]


def test_another_region_counts_its_records_as_never_checked(learner):
    filed(learner, ALL_TAGS)
    learner.open(today=DAY)
    assert learner.run_json("tag-checks", "--work", learner.path)["never_checked"] == 0
    learner.run_json("settings", "--work", learner.path, "--config", '{"guideline_region": "United States"}')
    assert learner.run_json("tag-checks", "--work", learner.path)["never_checked"] == 25

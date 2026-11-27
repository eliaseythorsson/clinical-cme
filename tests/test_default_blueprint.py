"""The default blueprint (issue #82): two levels on the ABIM general skeleton with European
guidance, as proposed in docs/blueprint-v2.md. Checked mechanically: ids, structure, decision
points, aspects, weights, the markdown and the JSON agree, the retired ids stay resolvable, and
the engine plans rounds on a fresh ledger with it. A learner's ledger keeps its own copy."""
import datetime as dt
import json
import os
import re

import examples
from conftest import DEFAULT_BLUEPRINT, ROOT, SKILL
from examples import cme

MD = os.path.join(SKILL, "templates", "blueprint.md")
DOC = os.path.join(ROOT, "docs", "blueprint-v2.md")
ONE_LEVEL = os.path.join(ROOT, "tests", "one_level", "blueprint.json")
RETIRED = {"PULM-06": "CARD-08", "GEN-01": "PERIOP-01", "GEN-02": "PERIOP-02", "EMRG-01": "RHEUM-04a"}
DAY = dt.date(2026, 11, 20)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def default():
    return json.loads(read(DEFAULT_BLUEPRINT))


def doc_areas():
    """The proposal's table: {area code: (share in %, diseases, sub-topics)}."""
    out = {}
    for m in re.finditer(r"^\| ([A-Z]+) [^|]+\| (\d+)% \| (\d+) \| (\d+) \|$", read(DOC), re.M):
        out[m.group(1)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    return out


def test_the_markdown_and_the_json_agree():
    assert cme.blueprint_from_md(read(MD)) == default()


def test_ids_are_well_formed_unique_and_each_sub_topic_sits_under_its_disease():
    bp = default()
    seen = []
    for d, info in bp.items():
        for tid in info["topics"]:
            assert re.match(r"^[A-Z]+-\d\d$", tid), tid
            assert cme.domain_of(tid) == d or (d, cme.domain_of(tid)) == ("TOX", "EMRG"), tid
            seen.append(tid)
        for tid, group in (info.get("subtopics") or {}).items():
            assert tid in info["topics"]
            letters = []
            for sid in group:
                assert re.match(r"^%s[a-z]$" % re.escape(tid), sid), (tid, sid)
                letters.append(sid[-1])
                seen.append(sid)
            assert letters == [chr(ord("a") + n) for n in range(len(letters))], tid
    assert len(seen) == len(set(seen))


def test_every_sub_topic_has_two_to_five_decision_points_each_resting_on_a_guideline():
    for sid, info in cme.bp_subtopics({"blueprint": default()}).items():
        points = info.get("points") or []
        assert 2 <= len(points) <= 5, sid
        for p in points:
            assert re.search(r"\S \[[^\[\]]+\]$", p), (sid, p)
        assert len(set(points)) == len(points), sid


def test_every_aspect_named_in_the_markdown_is_read():
    lines = [line for line in read(MD).splitlines() if re.match(r"^  - [A-Z]+-\d\d[a-z]  ", line)]
    assert len(lines) == 347
    for line in lines:
        m = cme.ASPECTS_RE.search(line)
        assert m, line
        named = [p for p in re.split(r"[,;]", m.group(1)) if p.strip()]
        parsed = cme.parse_aspects(m.group(1))
        assert 1 <= len(parsed) == len(named) <= 4, line
        assert set(parsed.values()) <= {1.3, 1.0, 0.6, 0.35}, line


def test_areas_counts_and_weights_follow_the_proposal():
    bp, doc = default(), doc_areas()
    assert list(bp) == list(doc) and len(bp) == 16
    st = {"blueprint": bp}
    live = cme.bp_live_topics(st)
    subs = cme.bp_subtopics(st)
    for d, (share, diseases, subtopics) in doc.items():
        assert bp[d]["weight"] == round(share / 14.0, 2), d
        assert sum(1 for i in live.values() if i["domain"] == d) == diseases, d
        assert sum(1 for i in subs.values() if i["domain"] == d) == subtopics, d
    assert len(live) == 144 and len(subs) == 347
    assert sum(len(i.get("points") or []) for i in subs.values()) == 1056
    # the header says so too
    assert "16 areas, 144 diseases and\n347 sub-topics" in read(MD)
    # a disease with no sub-topics is a one-level topic: only the meta-skill
    assert [t for t in live if not cme.subtopics_of(st, t)] == ["GEN-10"]


def test_the_old_ids_still_resolve_and_the_retired_ones_say_where_they_went():
    bp = default()
    st = {"blueprint": bp}
    topics = cme.bp_topics(st)
    old = json.loads(read(ONE_LEVEL))
    for info in old.values():
        for tid in info["topics"]:
            assert tid in topics, tid                     # an old ledger's topic keeps a label and an area
    retired = {tid for tid, i in topics.items() if cme.is_retired(i["label"])}
    assert retired == set(RETIRED)
    subs = cme.bp_subtopics(st)
    for tid, into in RETIRED.items():
        assert into in topics or into in subs
        assert into in topics[tid]["label"] and not cme.subtopics_of(st, tid)
    assert topics["EMRG-01"]["domain"] == topics["EMRG-02"]["domain"] == "TOX"


def test_a_decision_point_that_starts_like_an_id_stays_a_decision_point():
    bp = cme.blueprint_from_md("## A. Cardiology (weight: high)\n- CARD-14  Lipids\n"
                               "  - CARD-14a  Risk estimation and targets  (aspects: management high)\n"
                               "    - LDL-cholesterol target by risk category [ESC]\n"
                               "  - CARD-14b  Statin intolerance\n")
    assert bp["CARD"]["subtopics"]["CARD-14"] == {
        "CARD-14a": {"label": "Risk estimation and targets", "points": ["LDL-cholesterol target by risk category [ESC]"],
                     "aspects": {"management": 1.0}},
        "CARD-14b": {"label": "Statin intolerance"}}


# ---------------------------------------------------------------- the engine plans with it

def fresh():
    st = examples.load_ledger("fresh")
    st["blueprint"] = default()
    return st


def test_a_fresh_ledger_plans_rounds_on_diseases_with_their_sub_topics_never_a_retired_one():
    st = fresh()
    seen = set()
    for seed in range(40):
        p = cme.plan_round(st, examples.plan_options(seed=seed, mcqs=4, focused=2), DAY)
        for c in p["items"]:
            if not c.get("topic"):
                continue
            seen.add(c["topic"])
            assert not cme.is_retired(c["label"]), c
            if c["topic"] != "GEN-10":
                sub = c["subtopic"]
                assert sub["id"].startswith(c["topic"]) and sub["points"] and sub["aspects"], c
    assert not seen & set(RETIRED) and len(seen) > 30
    # the areas that keep a retired id, one-off rounds on each
    for d in ("PULM", "GEN", "TOX"):
        for seed in range(15):
            p = cme.plan_round(st, examples.plan_options(seed=seed, mcqs=4, focused=2, domain=d), DAY)
            topics = {c.get("topic") for c in p["items"]}
            assert topics - {None} and not topics & set(RETIRED), (d, seed)


def test_a_retired_topic_with_a_due_record_or_a_gap_is_not_planned():
    st = examples.load_ledger("overdue")
    old_topics = set(st["topics"])
    st["blueprint"] = default()
    st["topics"]["PULM-06"] = dict(st["topics"].get("PULM-06") or next(iter(st["topics"].values())),
                                   domain="PULM", due="2026-09-01", mastery=1)
    st["gaps"].append({"id": "G9999", "topic": "EMRG-01", "gap": "adrenaline route", "date": "2026-08-01",
                       "source": ["misconception"]})
    for d in (None, "PULM", "TOX"):
        for seed in range(10):
            p = cme.plan_round(st, examples.plan_options(seed=seed, domain=d), examples.today_of("overdue"))
            assert not {c.get("topic") for c in p["items"]} & set(RETIRED), (d, seed)
    assert old_topics          # the example had history


def test_a_new_learner_gets_the_two_level_default(work):
    out = work.run_json("--today", "2026-11-01", "init", "--work", work.path, "--blueprint", DEFAULT_BLUEPRINT,
                        "--config", "{}", "--profile", "{}")
    assert out["topics"] == 144 and len(out["domains"]) == 16
    work.publish()
    work.forget_job()
    assert work.read_ledger()["blueprint"] == default()
    work.start("2026-11-02")
    plan = work.read_json("plan.json")
    assert any(c.get("subtopic") for c in plan["items"])


def test_an_existing_learner_keeps_their_own_blueprint_until_they_set_the_new_one(work):
    work.init()                                   # the one-level blueprint of before (conftest)
    before = work.read_ledger()["blueprint"]
    assert not cme.bp_subtopics({"blueprint": before})
    work.start("2026-11-02")
    work.publish()
    assert work.read_ledger()["blueprint"] == before
    # the documented way onto the new default: settings --blueprint (then apply-mapping, §9)
    out = work.run_json("--today", "2026-11-02", "settings", "--work", work.path, "--blueprint", DEFAULT_BLUEPRINT)
    assert "blueprint" in json.dumps(out)
    work.publish()
    assert work.read_ledger()["blueprint"] == default()


# ---------------------------------------------------------------- the area shares are honoured

def test_on_a_fresh_ledger_each_area_s_share_of_new_picks_is_its_documented_share():
    st = fresh()
    pull = cme.new_topic_weights(st)
    assert not set(pull) & set(RETIRED) and len(pull) == 144
    total = sum(pull.values())
    doc = doc_areas()
    shares = sum(share for share, _, _ in doc.values())
    for d, (share, _, _) in doc.items():
        got = sum(w for tid, w in pull.items() if cme.topic_domain(st, tid) == d) / total
        assert abs(got - share / shares) < 0.002, (d, got, share)
    # the planner draws by these weights: a wildcard slot (new material outside the theme) lands
    # in a small area about as often as its share says, not in proportion to its disease count
    counts = {}
    for seed in range(400):
        p = cme.plan_round(st, examples.plan_options(seed=seed, mcqs=6, focused=0, no_case=True), DAY)
        for c in p["items"]:
            if c.get("share") == "wildcard" and c.get("topic"):
                counts[c["domain"]] = counts.get(c["domain"], 0) + 1
    n = sum(counts.values())
    theme = cme.block_status(st)["theme"]
    rest = sum(share for d, (share, _, _) in doc.items() if d != theme)
    assert n > 300
    for d in ("HEME", "PERIOP", "WH"):
        assert abs(counts.get(d, 0) / n - doc[d][0] / rest) < 0.05, (d, counts.get(d, 0) / n)


def test_a_one_level_blueprint_keeps_the_area_weight_on_each_topic():
    st = examples.load_ledger("fresh")
    eff = cme.domain_weights(st)
    assert cme.new_topic_weights(st, eff) == {tid: eff[i["domain"]] for tid, i in cme.bp_topics(st).items()}


def test_the_theme_proposal_follows_the_area_weights_on_a_fresh_ledger():
    st = fresh()
    ranking = cme.propose_theme(st)["ranking"]
    weights = [default()[d]["weight"] for d in ranking]
    assert ranking[0] == "CARD" and weights == sorted(weights, reverse=True)

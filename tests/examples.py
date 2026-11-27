"""Example ledgers and the scripted rounds played on them (issue #6).

The example ledgers in tests/ledgers/ are synthetic: no learner ever answered them. They are
frozen inputs, as a learner's ledger written by an older version would be; tests/ledgers/build.py
made them and is only run again to add a new one.

Each ledger has a fixed date. On that date the tests plan a round, record a scripted round for
that plan and reflect on it the next day, and compare the result with the files saved in the
ledger's expected/ folder. To accept a deliberate change to planning, scheduling or applying:

    CME_UPDATE_EXPECTED=1 python3 -m pytest -q tests/test_examples.py

and review the diff of tests/ledgers/*/expected/ like any other change.
"""
import argparse
import copy
import datetime as dt
import importlib.util
import json
import os

from conftest import CME

spec = importlib.util.spec_from_file_location("cme", CME)
cme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cme)

LEDGERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledgers")

# name -> the date on which the tests plan and play the next round
LEDGERS = {
    "fresh": "2026-11-20",             # set up today, nothing answered yet
    "mid_curriculum": "2026-10-28",    # ten reflected rounds, the last five days ago
    "overdue": "2026-11-20",           # six rounds in August, then three months away
    "unreflected": "2026-10-19",       # the last round was saved but never reflected on
    "stale_prepared": "2026-11-20",    # a round was prepared on 2026-09-10 and never taken
    "drilled": "2026-10-22",           # seven rounds by an engine with no drill-down limit, every repeat missed
}
PREPARED_MADE = "2026-09-10"           # stale_prepared: the day its prepared round was made

PLAN_OPTIONS = dict(focused=None, mcqs=None, no_case=False, domain=None, no_new=False,
                    allow_repeat=False, no_drill=False, force_drill=False, seed=None)


def plan_options(**changes):
    return argparse.Namespace(**dict(PLAN_OPTIONS, **changes))


def ledger_path(name):
    return os.path.join(LEDGERS_DIR, name, "ledger.json")


def prepared_path(name):
    return os.path.join(LEDGERS_DIR, name, "prepared.json")


def expected_path(name, part):
    return os.path.join(LEDGERS_DIR, name, "expected", part + ".json")


def load_ledger(name, raw=False):
    """The example ledger as the engine reads it from a store (cme.migrate_ledger: the old
    profile fields folded, one code per area), or as it is on disk with `raw`."""
    with open(ledger_path(name), encoding="utf-8") as fh:
        st = json.load(fh)
    return st if raw else cme.migrate_ledger(st)


def today_of(name):
    return dt.date.fromisoformat(LEDGERS[name])


# ---- the scripted learner: how each item of a round is answered, by round number and position

OUTCOMES = (
    # name, mastery, confidence, MCQ correct, comfort given in the reflection
    ("strong", 5, "sure", True, 5),
    ("good", 4, "unsure", True, 4),
    ("weak", 2, "unsure", False, 2),
    ("strong", 5, "sure", True, 4),
    ("lucky", 4, "guess", True, 5),            # MCQ: a correct guess counts as 3; comfort 5 is overconfident
    ("underconfident", 5, "unsure", True, 2),
    ("misconception", 1, "sure", False, 4),    # confident and wrong
)


def outcome(n, i):
    return OUTCOMES[(n + 2 * i) % len(OUTCOMES)]


def topic_for(st, item, taken):
    """The plan names a topic, or only a domain; then the author picks an untested topic in it."""
    if item.get("topic"):
        return item["topic"]
    for tid, info in sorted(cme.bp_topics(st).items()):
        if info["domain"] == item["domain"] and tid not in st["topics"] and tid not in taken:
            return tid
    raise AssertionError("no untested topic left in %s" % item["domain"])


def round_for(st, plan):
    """The graded round a scripted learner produces for `plan` on ledger `st`."""
    n = cme.id_num(plan["session_id"])
    labels = cme.bp_topics(st)
    rnd = {"log_id": plan["session_id"], "case_format": plan["case_format"],
           "title": "Example round %s" % plan["session_id"],
           "summary": "Synthetic round %d of an example ledger." % n,
           "tags": ["example"], "minutes": plan["estimated_minutes"],
           "items": [], "gaps": [], "selection_reasons": {}}
    taken = set()
    for i, planned in enumerate(plan["items"]):
        tid = topic_for(st, planned, taken)
        taken.add(tid)
        label = (labels.get(tid) or {}).get("label") or tid
        name, mastery, confidence, correct, _ = outcome(n, i)
        errors = []
        if mastery <= 2:
            errors = [{"category": "knowledge", "knowledge_type": "missing", "severity": "important"}]
        item = {"type": planned["slot"], "topic": tid, "mastery": mastery, "confidence": confidence,
                "coding": {"errors": errors}}
        if planned["slot"] == "mcq":
            item["correct"] = correct
            item["stem_summary"] = "Example MCQ stem %d.%d" % (n, i)
        elif planned["slot"] == "focused":
            item["aspect"] = planned.get("aspect_hint") or "diagnosis"
            item["stem_summary"] = "Example focused stem %d.%d" % (n, i)
            item["coding"]["art"] = {"DDX": 2 if mastery >= 4 else 1}
        else:
            good = mastery >= 4
            item["coding"]["art"] = {"DG": 2 if good else 1, "PR": 2 if good else 1, "DDX": 2 if good else 0,
                                     "TEST": 2 if good else 1, "META": 1, "MGMT": 2 if good else 1}
            item["coding"]["idea"] = {"I": 4 if good else 2, "D": 2 if good else 1, "E": 2 if good else 1,
                                      "A": 2 if good else 0}
            rnd["case"] = {"patient": "Example patient %d" % n, "setting": "ward",
                           "presentation": "Example presentation %d" % n,
                           "diagnosis": "Example diagnosis: %s" % label}
        if planned.get("retest_gap"):      # the author wrote the item on the open gap, as the plan asks
            item["retests"] = planned["retest_gap"]["id"]
        if name == "weak":
            rnd["gaps"].append({"topic": tid, "gap": "Example gap %d.%d: missed the decision point" % (n, i),
                                "source": "graded"})
        rnd["items"].append(item)
        rnd["selection_reasons"][tid] = planned["reason_code"]
    return rnd


def miss_repeats(rnd, plan):
    """The round of a learner who misses everything that comes back: every item the plan brought
    as a repeat (due, an open gap, a revisit) is answered badly and the examiner writes its gap
    again. With no drill-down limit the same topics then return round after round."""
    for item, planned in zip(rnd["items"], plan["items"]):
        if planned["reason_code"] not in ("due", "gap", "revisit"):
            continue
        item.update(mastery=2, confidence="unsure")
        item["coding"]["errors"] = [{"category": "knowledge", "knowledge_type": "missing", "severity": "important"}]
        if item["type"] == "mcq":
            item["correct"] = False
        if not any(g["topic"] == item["topic"] for g in rnd["gaps"]):
            rnd["gaps"].append({"topic": item["topic"], "source": "graded",
                                "gap": "Example gap: missed the decision point again in %s" % rnd["log_id"]})
    return rnd


def reflection_for(rnd):
    """The scripted learner's reflection on `rnd`."""
    n = cme.id_num(rnd["log_id"])
    refl = {"topic_comfort": {it["topic"]: outcome(n, i)[4] for i, it in enumerate(rnd["items"])},
            "performance": 3, "solid": "Example: what felt solid in round %d" % n,
            "gaps": "Example: what felt shaky in round %d" % n}
    if n % 3 == 0:      # every third round the learner also names a gap of their own
        refl["self_gaps"] = [{"topic": rnd["items"][0]["topic"], "source": "self",
                              "gap": "Example self-reported gap %d" % n}]
    return refl


# ---- what is saved as expected output

def due_on(st, today):
    """The topics due on `today`, most overdue first."""
    due = [(t["due"], tid) for tid, t in st["topics"].items()
           if cme.parse_date(t.get("due")) and cme.parse_date(t["due"]) <= today]
    return [{"topic": tid, "due": d} for d, tid in sorted(due)]


def schedule_of(st, tids):
    return {tid: st["topics"][tid] for tid in sorted(tids) if tid in st["topics"]}


def ledger_summary(st):
    """The parts of the ledger that applying a round changes, apart from the topics (a copy:
    applying the round again later changes the ledger in place)."""
    last = {k: v for k, v in st["sessions"][-1].items() if k not in ("_snapshot", "_round")}
    return copy.deepcopy({"gen": st["gen"], "next_id": st["next_id"], "updated": st["updated"],
            "unreflected": st["unreflected"], "session": last,
            "session_ids": [s["id"] for s in st["previous"] + st["sessions"]],
            "block": st.get("block"), "blocks": st.get("blocks"),
            "gaps": st["gaps"], "resolved": st["resolved"], "agg": st["agg"],
            "domain_self_ratings": st["profile"].get("domain_self_ratings")})


def play(name, st=None):
    """Plan a round on the example ledger on its date, record the scripted round and reflect on
    it the next day. Returns {"plan": …, "schedule": …, "applied": …}, the three expected files,
    plus "ledger": the ledger afterwards."""
    st = copy.deepcopy(st) if st is not None else load_ledger(name)
    today = today_of(name)
    plan = cme.plan_round(st, plan_options(), today)
    schedule = {"date": cme.iso(today), "due_before": due_on(st, today)}
    applied = {}
    if st.get("unreflected"):
        # first what the learner would normally do: reflect on the waiting round
        waiting = copy.deepcopy(st)
        rnd0 = next(s for s in waiting["sessions"] if s["id"] == waiting["unreflected"])["_round"]
        refl0 = reflection_for(rnd0)
        applied["waiting_round"] = {"reflection": refl0, "reflect": cme.reflect_round(waiting, refl0, today),
                                    "ledger_after": ledger_summary(waiting)}
        schedule["after_reflecting_waiting_round"] = schedule_of(waiting, [it["topic"] for it in rnd0["items"]])
    rnd = round_for(st, plan)
    tids = [it["topic"] for it in rnd["items"]]
    applied["round"] = copy.deepcopy(rnd)
    applied["record"] = cme.record_round(st, copy.deepcopy(rnd), today)
    applied["ledger_after_record"] = ledger_summary(st)
    schedule["after_record"] = copy.deepcopy(schedule_of(st, tids))
    refl = reflection_for(rnd)
    applied["reflection"] = copy.deepcopy(refl)
    applied["reflect"] = cme.reflect_round(st, refl, today + dt.timedelta(days=1))
    applied["ledger_after_reflect"] = ledger_summary(st)
    schedule["after_reflect"] = schedule_of(st, tids)
    return json.loads(json.dumps({"plan": plan, "schedule": schedule, "applied": applied, "ledger": st}))


# ---- sealed files for a plan, as an author would draft them: keys outside the present blocks

def key_header(kid, st, item, taken):
    """The key header an author writes for one item of the plan (references/standards.md, rule 9)."""
    tid = topic_for(st, item, taken)
    taken.add(tid)
    label = (cme.bp_topics(st).get(tid) or {}).get("label") or tid
    lines = ["type: %s" % item["slot"], "topic: %s" % tid, "label: %s" % label, "reason: %s" % item["reason_code"]]
    if item.get("retest_gap"):
        lines.append("retests: %s" % item["retest_gap"]["id"])
    if item["slot"] == "case":
        lines += ["patient: 60F", "setting: ward", "presentation: Example presentation",
                  "diagnosis: Example diagnosis: %s" % label]
    else:
        if item["slot"] == "focused":
            lines.append("aspect: %s" % (item.get("aspect_hint") or "diagnosis"))
        lines.append("stem_summary: Example stem %s" % kid)
    return "<!-- key: %s -->\n%s\n<!-- /key -->%s" % (kid, "\n".join(lines), rubric(kid, item["slot"]))


def rubric(kid, slot):
    """The rubric block beside a focused question's or the case's key header (rule 9); none for an MCQ."""
    if slot == "case":
        return ("\n<!-- rubric: case -->\nStage 1\n- SEALED element: the leading diagnosis\n- SEALED element: the "
                "discriminating test\nStage 2\n- SEALED element: the treatment\n<!-- /rubric -->")
    if slot == "focused":
        return ("\n<!-- rubric: %s -->\n- SEALED element: the decision\n- SEALED element: the decisive reason\n"
                "<!-- /rubric -->" % kid)
    return ""


def episode_link(kid, n):
    """A link in the form of a Spotify episode (22 letters and digits); no such episode exists."""
    return "https://open.spotify.com/episode/%s" % ("Example%s%d" % (kid, n)).ljust(22, "x")


def listening_section(kids, candidates=3):
    """A kit's "## Listening" section as the author and the checker leave it (rule 8): one line
    per topic, and three candidate episodes under each."""
    lines = ["## Listening", "Sources | trusted: none | avoid: none"]
    for kid in kids:
        lines.append("%s | points: SEALED point tested; SEALED tempting wrong turn" % kid)
        lines += ["- %s | SEALED Show %d | SEALED episode on %s | %d min | covers: SEALED content | matches: SEALED point"
                  % (episode_link(kid, n), n, kid, 20 + 10 * n) for n in range(1, candidates + 1)]
    return "\n".join(lines) + "\n"


RUBRIC_SIZE = {"focused": 2, "case": 3}         # the elements of the example rubric blocks above


def prepared_blocks(kid, slot, planned):
    """The prepared blocks of one item's kit section (rule 8): finished text per part of its
    feedback, one per rubric element and mark, and `deeper` when the plan gives a depth."""
    want = [(None, k) for k in cme.BLOCK_ITEM_KINDS[slot]]
    want += [(n, m) for n in range(1, RUBRIC_SIZE.get(slot, 0) + 1) for m in cme.RUBRIC_MARKS]
    if planned.get("depth"):
        want.append((None, cme.BLOCK_DEEPER))
    return "".join("<!-- block: %s -->\nSEALED prepared text for %s, as the learner will read it.\n<!-- /block -->\n"
                   % (cme.block_id(kid, n, k), cme.block_id(kid, n, k)) for n, k in want)


def sealed_files(st, plan):
    """{file name: text} for `plan`. Everything the learner must not see before answering sits
    outside the present and bank blocks and carries the word SEALED; each key starts with its
    key header (with its rubric block for a focused question and the case), and the kits have the sections of the rulebook (references/standards.md, rule 8),
    the "Listening" section among them unless the plan has listening off, and the prepared blocks
    of every item, with a `deeper` block for an item the plan gives an evidence depth."""
    listening = plan.get("listening") is not False
    labels = cme.bp_topics(st)
    shorts = [it for it in plan["items"] if it["slot"] != "case"]
    case = next((it for it in plan["items"] if it["slot"] == "case"), None)
    files, taken = {}, set()
    if shorts:
        keys = ["SEALED KEY Q%d: B (%s %s)" % (i + 1, it.get("topic") or it["domain"],
                                              (labels.get(it.get("topic")) or {}).get("label") or "")
                for i, it in enumerate(shorts)]
        headed = ["%s\n%s" % (key_header("Q%d" % (i + 1), st, it, taken), key) for i, (it, key) in enumerate(zip(shorts, keys))]
        stems = ["Q%d. Example stem %d. A) one B) two C) three" % (i + 1, i + 1) for i in range(len(shorts))]
        files["sealed_questions.md"] = ("%s\n<!-- present: questions -->\n%s\n<!-- /present -->\n"
                                        % ("\n".join(headed), "\n".join(stems)))
        files["kit_questions.md"] = "".join("## Q%d\nSEALED feedback notes: %s\n%s\n"
                                            % (i + 1, key, prepared_blocks("Q%d" % (i + 1), it["slot"], it))
                                            for i, (it, key) in enumerate(zip(shorts, keys)))
        if not case:
            files["kit_questions.md"] += "## Reading\nSEALED reading pointer (verify)\n"
        if listening:
            files["kit_questions.md"] += listening_section(["Q%d" % (i + 1) for i in range(len(shorts))])
    if case:
        label = (labels.get(case.get("topic")) or {}).get("label") or case["domain"]
        files["sealed_case.md"] = (
            "%s\nSEALED KEY: Diagnosis: Example diagnosis: %s\nSEALED topic: %s\n"
            "<!-- present: case -->\nAn example patient presents. What do you do first?\n<!-- /present -->\n"
            "<!-- bank -->\nExample result: sodium 140 mmol/L.\nStage 2: what now?\n<!-- /bank -->\n"
            % (key_header("case", st, case, taken), label, case.get("topic") or case["domain"]))
        files["kit_case.md"] = "".join("## %s\nSEALED feedback notes for the case: Example diagnosis: %s\n\n"
                                       % (name, label) for name in cme.KIT_CASE_SECTIONS)
        files["kit_case.md"] += "## Blocks\n%s\n" % prepared_blocks("case", "case", case)
        if listening:
            files["kit_case.md"] += listening_section(["case"])
    return files

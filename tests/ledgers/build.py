"""Build the example ledgers in this folder (see tests/examples.py). Synthetic data only.

    python3 tests/ledgers/build.py [name ...]

The ledgers are frozen inputs: run this to add a new example, not to refresh the old ones (a
rebuilt ledger reflects today's engine, and the point of the old ones is that they do not).
After building, save the expected outputs:

    CME_UPDATE_EXPECTED=1 python3 -m pytest -q tests/test_examples.py

The era ledgers in eras/ (issue #83: one per shape an older engine wrote, read by the load step)
are built from the `new_state` of the engine of that era, taken from git, with the same small
synthetic history added to each; they need a clone with that history:

    python3 tests/ledgers/build.py --era NAME
    CME_UPDATE_EXPECTED=1 python3 -m pytest -q tests/test_eras.py
"""
import copy
import datetime as dt
import json
import importlib.util
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examples                                    # noqa: E402
from conftest import BLUEPRINT                     # noqa: E402
from examples import cme                           # noqa: E402


def day(s):
    return dt.date.fromisoformat(s)


def new_ledger(created, config=None):
    """What `init` writes, with a fixed time stamp."""
    st = cme.new_state(day(created))
    cme.deep_merge(st["config"], config or {})
    st["profile"]["onboarded_at"] = created
    st["profile"]["display_name"] = "Example learner"
    st["config"]["round_set_at"] = created + "T08:00:00Z"
    with open(BLUEPRINT, encoding="utf-8") as fh:
        st["blueprint"] = json.load(fh)
    iv = int(st["config"]["review_interval_days"])
    st["review"] = {"last": None, "next_due": cme.iso(day(created) + dt.timedelta(days=iv)), "period_start": created}
    st["gen"] = 1
    return st


def play_rounds(st, dates, reflect_last=True):
    for i, d in enumerate(dates):
        plan = cme.plan_round(st, examples.plan_options(), day(d))
        rnd = examples.round_for(st, plan)
        cme.record_round(st, copy.deepcopy(rnd), day(d))
        if reflect_last or i < len(dates) - 1:
            cme.reflect_round(st, examples.reflection_for(rnd), day(d))
    return st


def play_without_drilldown_limit(st, dates):
    """Rounds as an engine from before the drill-down limit (issue #18) planned and scheduled
    them, played by a learner who misses every repeat (examples.miss_repeats)."""
    limits = cme.DRILLDOWN_MAX_ROUNDS, cme.DRILLDOWN_PAUSE_DAYS
    cme.DRILLDOWN_MAX_ROUNDS, cme.DRILLDOWN_PAUSE_DAYS = 10 ** 6, 0
    try:
        for d in dates:
            plan = cme.plan_round(st, examples.plan_options(), day(d))
            rnd = examples.miss_repeats(examples.round_for(st, plan), plan)
            cme.record_round(st, copy.deepcopy(rnd), day(d))
            cme.reflect_round(st, {"performance": 2, "solid": "Example: little felt solid",
                                   "gaps": "Example: the same points again"}, day(d))
            for g in st["gaps"]:      # that engine did not carry a retest over to a gap written again
                if g.get("last_retested") == g.get("date"):
                    del g["last_retested"]
    finally:
        cme.DRILLDOWN_MAX_ROUNDS, cme.DRILLDOWN_PAUSE_DAYS = limits
    return st


def prepared_for(st, made):
    """data/prepared.json as `prepare` and `stash` write it on the day `made`."""
    with tempfile.TemporaryDirectory() as tmp:
        state = os.path.join(tmp, "ledger.json")
        cme.save_json(st, state)
        plan = os.path.join(tmp, "plan.json")
        assert cme.main(["--today", made, "prepare", state, "--out", plan]) == 0
        for name, text in examples.sealed_files(st, cme.load_json(plan)).items():
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        assert cme.main(["stash", state, "--plan", plan, "--dir", tmp, "--out-dir", os.path.join(tmp, "out")]) == 0
        return cme.load_json(os.path.join(tmp, "out", cme.PREPARED_PATH))


def build(name):
    prepared = None
    if name == "fresh":
        st = new_ledger("2026-11-20")
    elif name == "mid_curriculum":
        st = play_rounds(new_ledger("2026-10-05", {"focused": 1}),
                         ["2026-10-05", "2026-10-07", "2026-10-09", "2026-10-12", "2026-10-14",
                          "2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22", "2026-10-23"])
    elif name == "overdue":
        st = play_rounds(new_ledger("2026-08-03"),
                         ["2026-08-03", "2026-08-05", "2026-08-07", "2026-08-10", "2026-08-13", "2026-08-17"])
    elif name == "unreflected":
        st = play_rounds(new_ledger("2026-10-05"),
                         ["2026-10-05", "2026-10-07", "2026-10-09", "2026-10-12", "2026-10-14", "2026-10-16"],
                         reflect_last=False)
    elif name == "stale_prepared":
        st = play_rounds(new_ledger("2026-09-01", {"mcqs": 2, "focused": 1}),
                         ["2026-09-01", "2026-09-03", "2026-09-07", examples.PREPARED_MADE])
        prepared = prepared_for(st, examples.PREPARED_MADE)
    elif name == "drilled":
        st = play_without_drilldown_limit(new_ledger("2026-10-01", {"mcqs": 4}),
                                          ["2026-10-01", "2026-10-04", "2026-10-07", "2026-10-10",
                                           "2026-10-13", "2026-10-16", "2026-10-19"])
    else:
        raise SystemExit("unknown example ledger: %s" % name)
    os.makedirs(os.path.dirname(examples.ledger_path(name)), exist_ok=True)
    cme.save_json(st, examples.ledger_path(name))
    if prepared:
        cme.save_json(prepared, examples.prepared_path(name))
    print("built %s: %d rounds, %d topics, %d open gaps" % (name, len(st["sessions"]), len(st["topics"]), len(st["gaps"])))


# ---- era ledgers (tests/test_eras.py)

ERAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eras")
# era -> the commit whose engine wrote it (None: built from the 4.2 one, without its mix settings)
ERAS = {
    "4_1_mix_not_a_setting": "b0c37ab",   # before the round mix was a setting of its own (synthetic)
    "4_2": "b0c37ab",                     # role, goals and notes; no speed settings; one area under two codes
    "4_3": "8019a72",                     # speed settings and testing mode
    "5_0": "31b1e02",                     # paragraphs, listening, blocks; no engine stamp
    "6_0": "89805ff",                     # the engine stamp: a current ledger
    "newer": "89805ff",                   # stamped by an engine newer than this one
}
SCRIPT = "skills/clinical-cme/scripts/cme.py"     # its path in those commits (issue #56 moved it under plugins/)


def engine_of(commit):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    code = subprocess.run(["git", "show", "%s:%s" % (commit, SCRIPT)], cwd=root, check=True,
                          capture_output=True, text=True).stdout
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
        fh.write(code)
    spec = importlib.util.spec_from_file_location("cme_" + commit, fh.name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    os.remove(fh.name)
    return mod


def build_era(era):
    old = engine_of(ERAS[era])
    st = old.new_state(day("2026-01-05"))
    st["gen"] = 7
    st["updated"] = "2026-01-20"
    st["next_id"] = "S0002"
    st["profile"].update(display_name="Example learner", onboarded_at="2026-01-05")
    st["config"]["round_set_at"] = "2026-01-05T08:00:00Z"
    if "journey" not in st["profile"]:          # the fields the paragraphs replaced
        st["profile"].update(role="Consultant physician", goals=["Example: pass the exam"], notes="Example: night shifts")
    # one area under two codes, as the default blueprint had it before issue #80
    st["blueprint"] = {
        "CARD": {"name": "Cardiology", "weight": 1.0, "topics": {"CARD-01": "Example topic one",
                                                                  "CARD-02": "Example topic two"}},
        "TOX": {"name": "Emergencies / Toxicology", "weight": 0.6, "topics": {"TOX-01": "Example poisoning"}},
        "EMRG": {"name": "Emergencies / Toxicology", "weight": 0.8, "topics": {"EMRG-01": "Example emergency"}},
    }
    if era == "6_0" or era == "newer":         # by then they are one area
        st["blueprint"]["TOX"]["topics"]["EMRG-01"] = st["blueprint"].pop("EMRG")["topics"]["EMRG-01"]
        st["blueprint"]["TOX"]["weight"] = 0.8
    st["profile"]["domain_self_ratings"] = {"CARD": 3, "TOX": 4} if "EMRG" not in st["blueprint"] else \
        {"CARD": 3, "TOX": 4, "EMRG": 2}
    st["topics"] = {"EMRG-01": {"domain": "EMRG" if "EMRG" in st["blueprint"] else "TOX",
                                "label": "Example emergency", "last": "2026-01-20", "attempts": 1, "mastery": 2,
                                "step": 0, "due": "2026-01-23", "comfort": 3, "calibration": "aligned",
                                "history": [["2026-01-20", 2, 3, "aligned"]]}}
    st["gaps"] = [{"topic": "EMRG-01", "gap": "Example: the first step", "self": None, "source": ["graded"],
                   "date": "2026-01-20", "opened": "2026-01-20"}]
    st["sessions"] = [{"id": "S0001", "date": "2026-01-20", "title": "Example round", "topics": ["EMRG-01"],
                       "items": [{"type": "mcq", "topic": "EMRG-01", "domain": st["topics"]["EMRG-01"]["domain"],
                                  "mastery": 2, "confidence": "unsure", "correct": False}],
                       "score": 2.0, "minutes": 20}]
    if era == "4_1_mix_not_a_setting":
        for k in ("mcqs", "focused", "case", "session_minutes", "round_set_at"):
            del st["config"][k]
    if era == "newer":
        st["skill_version"] = "99.0.0"
        st["config"]["a_setting_from_the_future"] = True
    os.makedirs(ERAS_DIR, exist_ok=True)
    cme.save_json(st, os.path.join(ERAS_DIR, era + ".json"))
    print("built era %s from %s" % (era, ERAS[era]))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--era"]:
        for era_name in sys.argv[2:] or list(ERAS):
            build_era(era_name)
    else:
        for ledger_name in sys.argv[1:] or list(examples.LEDGERS):
            build(ledger_name)

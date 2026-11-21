"""Build the example ledgers in this folder (see tests/examples.py). Synthetic data only.

    python3 tests/ledgers/build.py [name ...]

The ledgers are frozen inputs: run this to add a new example, not to refresh the old ones (a
rebuilt ledger reflects today's engine, and the point of the old ones is that they do not).
After building, save the expected outputs:

    CME_UPDATE_EXPECTED=1 python3 -m pytest -q tests/test_examples.py
"""
import copy
import datetime as dt
import json
import os
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


if __name__ == "__main__":
    for ledger_name in sys.argv[1:] or list(examples.LEDGERS):
        build(ledger_name)

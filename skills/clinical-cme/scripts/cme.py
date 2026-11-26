#!/usr/bin/env python3
"""clinical-cme v4.3.1 state engine (standard library only, Python 3.8+).

The learner's scheduling memory is ONE JSON document, the ledger (state.json); each round also
has a session document, and the page file (data/page.json) holds exactly what the learner's
page may show. This script never talks
to a store or to any assistant tool: the assistant reads the learner's store into a local folder
(the store copy; see references/store.md), opens a work folder on it, and from then on every
command takes only that work folder, `--work W`.

Every command that writes puts its files into the publish set, W/publish/ (store paths:
data/state.json, data/sessions/…), and prints the whole set as `files` ({"as": store path,
"path": local file}, in write order, the ledger last) with `publish`, the path of its manifest
W/publish.json ({"version": the store version read, "files": […]}). The assistant publishes
whatever the set lists; it is cumulative, so a failed publish is covered by the next one.

A job (one work folder):
  open    --work W --store DIR [--version V] [--prefs J] [--reread]
                                                  set W up for any job from DIR, the store as just read
                                                  (data/state.json … or the files side by side);
                                                  prints neutral status and counts, never topics.
                                                  --reread: the same job on a fresh read, after a refused
                                                  publish; then run its commands again
  start   --work W [--store DIR [--version V]] [--prefs J] [plan options] [--no-prepared]
                                                  a round: with --store it opens W first. Neutral status +
                                                  plan (W/plan.json; no topics); with a prepared round in
                                                  the store that still fits, also the questions to present
                                                  plan options: --mcqs N --focused N --no-case --domain D --no-new
  answer  --work W --part questions|case|final|notes|reflection [--file F | --text T]
                                                  append the learner's answer to W/answers.md (default: stdin)
  present --work W --block questions|case|bank    print only the text to show the learner
  save    --work W                                record the graded round + session doc (part A) + page file,
                                                  from the files in W by their fixed names. round.json names
                                                  each item's key ("key": "Q1") and holds the grading; the
                                                  rest comes from the key headers. Can be run again
  close   --work W [--reflection J] [--session ID]
                                                  apply the reflection (W/reflection.json) + part B (W/B.md)
  prepare --work W [--if-needed] [--allow-unreflected]
                                                  plan the NEXT round into W/next/plan.json (counts only)
  finish-prepare --work W [--revised] [--no-evidence]
                                                  after the checkers: lint the round in W/next against the
                                                  rulebook (references/standards.md), count contradicted
                                                  keys and claims not verified. A bad key header, a missing
                                                  kit section or an evidence file that is missing or lacks
                                                  its two count lines is an error; an abbreviation that looks
                                                  undefined or mixed time anchors send the round back to the
                                                  author once (details in W/next/lint.md), more than a third
                                                  of a part's claims not verified sends it back to its
                                                  checker once, then they are accepted with a warning
                                                  (--revised). Packs the round as
                                                  data/prepared.json
  keys    DIR|SEALED.. [--plan PLAN]              the author's check: key headers, kit sections and the same
                                                  lint (no content printed; details in DIR/lint.md)
  key-table                                       the key-header table of references/standards.md (rule 9),
                                                  as generated from the KEY_* definitions
  addendum --work W --md ADD.md [--session ID]    append to a session document (default: the last session)
  override --work W [--scores J] [--close-gaps J] [--session ID]
                                                  after the close: a score the learner sets themselves, a gap
                                                  closed at the learner's request (before it: reflection JSON)
  verify  --work W --store CHECK_DIR              testing mode: the publish set against a fresh re-read
  testing-note --work W --feedback J              testing mode: the learner's feedback + the store check

Settings, review, setup (each on an open work folder):
  settings --work W [--config J] [--profile J] [--blueprint F]
  theme   --work W [--set DOMAIN | --another]     the learner changes the block's theme (a named domain, or
                                                  the next proposal); alone: the block and the choices
  stats   --work W                                figures and coded analysis for a progress review
  review  --work W --review REVIEW.json           record a completed review; starts a new period
  review-doc --work W --md REPORT.md [--headline H] [--date D] [--title T]
  snooze  --work W [--days N]
  init    --work W --profile J --config J --blueprint FILE(.json|.md) [--start-over]
                                                  setup: the first ledger (W needs no store yet), page file and page

Maintenance, outside the protocol (their own files and folders):
  validate STATE | validate --work W
  import  EXPORT.json --out-dir D                 page export {state, sessions, reviews} -> file layout
  rebuild-page ROOT                               rebuild ROOT/data/page.json from the session and review
                                                  files and the ledger (`reindex` is the old name)
  blueprint-md FILE --out BP.json

Add `--today YYYY-MM-DD` before the command to fix the date.
"""
import argparse
import base64
import copy
import datetime as dt
import json
import math
import os
import random
import re
import shutil
import sys
import tempfile
import zlib

SCHEMA = 4
SKILL_VERSION = "4.3.1"
PAGE_VERSION = "5.1.0"   # templates/page.html carries <meta name="cme-page-version" content="5.1.0">

DEFAULT_CONFIG = {
    "session_minutes": 20,
    "mcqs": 3,
    "focused": 0,                        # focused questions per round (mini-case, one free-text question)
    "case": True,
    "round_set_at": None,                # when the round mix (mcqs/focused/case) was last set; see apply_prefs
    "case_format": "unfolding",          # unfolding | discriminate | alternate
    "feedback_depth": "detailed",        # standard | detailed
    "target_sessions_per_week": 3,
    "review_interval_days": 42,
    "intervals_days": [1, 3, 7, 16, 35, 90],
    "new_topics_per_round": 1,
    "lab_units": "SI",
    "blood_gas_units": "mmHg",
    "guideline_region": "Iceland/Europe",   # free text; asked at setup: whose guidelines items are written and graded against
    "item_order": "mcqs_first",          # mcqs_first: questions -> their feedback -> case -> its feedback
    "helpers": True,                     # helper agents where the app has them: an author drafts the items, a
                                         # checker verifies the evidence; the conversation grades
    "prepare_ahead": True,               # draft the whole next round after each close
    "prepare_task": False,
    "testing": False,                    # testing mode: feedback check + store check at the end of each round               # a scheduled task also prepares the round when none is ready
    "show_coding": True,
    "reminders": False,
    "resource_preferences": {"free_only": False, "formats": ["guidelines", "review articles"]},
}
DEFAULT_PROFILE = {
    "display_name": None, "role": None, "specialty": "Internal/hospital medicine", "subspecialty": None,
    "practice_setting": [], "goals": [], "strengths": [], "weaknesses": [],
    "domain_self_ratings": {}, "domain_emphasis": {}, "notes": "", "onboarded_at": None,
}
# Settings that cannot change what a round contains (its plan, its items, its keys, its feedback
# notes): changing only these keeps the round prepared ahead. Every other setting, including one
# this list has never heard of, sets it aside. `round_set_at` is here because it only dates the
# mix: the mix itself (mcqs, focused, case) is not. See state_schema.md §8.
CONTENT_NEUTRAL_CONFIG = ("testing", "reminders", "prepare_task", "prepare_ahead", "helpers", "show_coding",
                          "target_sessions_per_week", "review_interval_days", "round_set_at")
CONTENT_NEUTRAL_PROFILE = ("display_name", "onboarded_at")
SELF_RATING_FACTOR = {1: 1.6, 2: 1.3, 3: 1.0, 4: 0.8, 5: 0.6}
MIN_RETURN_DAYS = 3      # no tested topic and no open gap comes back sooner than this (ADR 0003)
# Drill-down limit (ADR 0003): no topic is in more than this many rounds in a row, and a topic
# missed again once its drill-down is used up waits at least the pause before it comes back.
DRILLDOWN_MAX_ROUNDS = 2
DRILLDOWN_PAUSE_DAYS = 7
# Themed blocks (ADR 0003): a run of rounds on one domain. Shares are of a round's short questions,
# in percent; the case is always on the theme.
BLOCK_LENGTH = 12
BLOCK_SHARES = (("theme", 60), ("repeat", 25), ("wildcard", 15))
MIN_THEME_TOPICS = 4     # a domain with fewer blueprint topics is not proposed as a theme
THEME_REST_BLOCKS = 4    # a domain's pull as the next theme recovers over this many blocks after its own
CONFIDENCE_LEVELS = ("sure", "unsure", "guess")
CONF_PROB = {"sure": 0.9, "unsure": 0.6, "guess": 0.3}
MIN_SESSIONS_FOR_REVIEW = 3
REVIEW_GRACE_DAYS = 21
ART_MAX = {"DG": 2, "PR": 2, "DDX": 2, "TEST": 2, "META": 1, "MGMT": 2}
ART_LABELS = {"DG": "hypothesis-directed data gathering", "PR": "problem representation",
              "DDX": "prioritised differential", "TEST": "high-value testing",
              "META": "metacognition", "MGMT": "management and disposition (extension)"}
IDEA_MAX = {"I": 4, "D": 2, "E": 2, "A": 2}
ERROR_CATEGORIES = ("knowledge", "data_gathering", "synthesis", "slip", "unclassified")
KNOWLEDGE_TYPES = ("missing", "outdated", "misapplied", "numeric")
SEVERITIES = ("minor", "important", "critical")
BIASES = ("anchoring", "premature_closure", "confirmation", "availability", "base_rate_neglect",
          "representativeness", "search_satisficing", "framing", "overconfidence", "omission",
          "commission", "unpacking_failure")
DRILL_RESULTS = ("avoided", "partial", "fell_for")
DISPUTE_OUTCOMES = ("learner_right", "both_defensible", "upheld")
# A score the learner set themselves ("record it as 4") is not a dispute: the examiner did not
# change its grading. `learner_override` is what rounds recorded by hand before 5.0 used.
LEARNER_SET = "learner_set"
LEARNER_SET_OUTCOMES = (LEARNER_SET, "learner_override")
ITEM_TYPES = ("case", "essay", "mcq", "focused")      # "essay" = the name older ledgers use for a case
FOCUSED_ASPECTS = ("diagnosis", "interpretation", "testing", "management", "disposition",
                   "prevention", "prognosis")
# Drills that can be built into a mini-case (used only when the round has no full case).
FOCUSED_DRILLS_EXCLUDED = ("bias:anchoring", "bias:search_satisficing", "art:PR", "art:DDX")
ROUND_LIMITS = {"mcqs": (0, 10), "focused": (0, 6)}
# Rough minutes per item, answering plus reading its feedback: the plan's estimate and the one
# the page shows (round_minutes). A one-step case ("discriminate") is shorter than an unfolding one.
MINUTES_PER = {"mcq": 5, "focused": 10, "unfolding": 25, "discriminate": 15}
GENERIC_WORDS = {"acute", "chronic", "disease", "disorder", "disorders", "management", "issues",
                 "inpatient", "outpatient", "basics", "common", "general", "emergencies",
                 "emergency", "workup", "assessment", "syndrome", "therapy", "treatment",
                 "approach", "patient", "care", "complications", "severe", "infection",
                 "infections", "including", "related", "selection", "control", "medical",
                 "hospital"}

# Caps that keep the state small (it is read and written whole every session).
PREPARED_MAX_AGE_DAYS = 30
CAP_SESSIONS = 50        # current-period sessions kept in full
CAP_PREVIOUS = 60        # older sessions kept in compact form
CAP_HISTORY = 8          # per-topic history rows
CAP_RESOLVED = 40
CAP_REVIEWS = 6
CAP_BLOCKS = 24          # finished blocks kept (theme, dates, rounds)
CAP_ERRATA = 40
CLIP_GAP = 400
CLIP_ELEMENT = 220
CLIP_EVIDENCE = 140


# ---------------------------------------------------------------- utilities

class CmeError(Exception):
    """An error the learner or assistant can act on. Raised anywhere in the engine; only main()
    turns it into the printed {"ok": false, "error": …} line and the exit code."""

    def __init__(self, msg, code=2):
        super().__init__(msg)
        self.msg = msg
        self.code = code


def die(msg, code=2):
    raise CmeError(msg, code)


def parse_date(s):
    if not s:
        return None
    if isinstance(s, dt.date):
        return s
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def iso(d):
    return d.isoformat() if d else None


def today_from(args):
    t = getattr(args, "today", None)
    if t:
        d = parse_date(t)
        if not d:
            die("--today must be YYYY-MM-DD")
        return d
    return dt.date.today()


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        die("file not found: %s" % path)
    except json.JSONDecodeError as e:
        die("invalid JSON in %s: %s" % (path, e))


def load_json_arg(value):
    if value is None:
        return None
    v = value.strip()
    if v.startswith("{") or v.startswith("["):
        try:
            return json.loads(v)
        except json.JSONDecodeError as e:
            die("invalid inline JSON: %s" % e)
    return load_json(value)


def save_json(obj, path):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".cme-", dir=d)
    try:        # written beside the file, then moved over it: an interrupted write leaves `path` as it was
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=False)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return os.path.getsize(path)


def clip(text, n):
    text = str(text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def round_half(x):
    return round(float(x) * 2) / 2.0


def id_num(v):
    m = re.search(r"(\d+)", str(v or ""))
    return int(m.group(1)) if m else 0


def domain_of(tid):
    return re.split(r"[-.]", str(tid), maxsplit=1)[0].upper()


def is_case(it):
    return (it or {}).get("type") in ("case", "essay")


def now_ts():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check_round_mix(cfg):
    """Validate mcqs / focused / case in a config (after a change). Dies with a plain message."""
    for k, (lo, hi) in ROUND_LIMITS.items():
        try:
            v = int(cfg.get(k, 0) or 0)
        except (TypeError, ValueError):
            die("%s must be a whole number" % k)
        if not lo <= v <= hi:
            die("%s must be between %d and %d" % (k, lo, hi))
        cfg[k] = v
    if not isinstance(cfg.get("case", True), bool):
        die("case must be true or false")
    if not cfg["mcqs"] and not cfg["focused"] and not cfg.get("case", True):
        die("a round needs at least one item: MCQs, focused questions or the case")


def parse_stamp(v):
    """An ISO time as written by the page (`...Z`, with milliseconds) or by now_ts(), as an aware
    datetime; None when it is not one."""
    if not isinstance(v, str) or not v.strip():
        return None
    try:
        t = dt.datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def mix_text(counts):
    """A round mix in words: "3 MCQs + 1 focused question + the case"."""
    c = counts or {}
    m, f = int(c.get("mcqs") or 0), int(c.get("focused") or 0)
    parts = []
    if m:
        parts.append("%d MCQ%s" % (m, "" if m == 1 else "s"))
    if f:
        parts.append("%d focused question%s" % (f, "" if f == 1 else "s"))
    if c.get("case"):
        parts.append("the case")
    return " + ".join(parts) or "no items"


def apply_prefs(state, prefs, warnings=None):
    """Apply the round mix the learner set on their page (database document cme/prefs).

    prefs = {"round": {"mcqs": 2, "focused": 1, "case": true}, "base": <config.round_set_at the
    page saw>, "updated": "<ISO time of the change>"}. The learner's latest explicit choice wins:
    - `base` equals the ledger's round_set_at: nothing changed the mix since the page saw it, so
      the page's mix is applied;
    - `updated` equals round_set_at: this document was applied before, nothing to do;
    - otherwise the mix was set elsewhere (in a chat, or by an earlier page document) after the
      page loaded: the document is applied only if its `updated` is later than round_set_at,
      and an older one is ignored.
    Applying sets round_set_at to `updated`, so a document is applied once. An invalid page
    setting is ignored with a warning, never fatal. Returns the changes applied."""
    if not prefs:
        return {}
    warnings = warnings if warnings is not None else []
    if not isinstance(prefs, dict) or not isinstance(prefs.get("round"), dict) or not prefs.get("updated"):
        warnings.append("page settings ignored: expected {round: {...}, base, updated}")
        return {}
    cfg = state["config"]
    set_at = cfg.get("round_set_at")
    if prefs.get("base") != set_at:
        if str(prefs["updated"]) == set_at:
            return {}     # applied before
        mine, theirs = parse_stamp(str(prefs["updated"])), parse_stamp(set_at)
        if set_at is not None and not (mine and theirs and mine > theirs):
            return {}     # overtaken by a later change in a chat
    trial = {k: cfg.get(k, DEFAULT_CONFIG[k]) for k in ("mcqs", "focused", "case")}
    for k in ("mcqs", "focused", "case"):
        if k in prefs["round"]:
            trial[k] = prefs["round"][k]
    try:
        trial["mcqs"] = int(trial["mcqs"]); trial["focused"] = int(trial["focused"])
        trial["case"] = bool(trial["case"]) if trial["case"] in (True, False, 0, 1) else None
        ok = (trial["case"] is not None
              and all(ROUND_LIMITS[k][0] <= trial[k] <= ROUND_LIMITS[k][1] for k in ROUND_LIMITS)
              and (trial["mcqs"] or trial["focused"] or trial["case"]))
    except (TypeError, ValueError):
        ok = False
    if not ok:
        warnings.append("page settings ignored: invalid round mix %s" % json.dumps(prefs["round"]))
        return {}
    changes = {k: v for k, v in trial.items() if cfg.get(k, DEFAULT_CONFIG[k]) != v}
    cfg.update(trial)
    cfg["round_set_at"] = str(prefs["updated"])
    return changes or {"unchanged": True}


def content_gen(st):
    """The ledger generation a prepared round is tied to: that of the last change that could
    alter what a round contains. `gen` itself counts every write; `content_gen` is kept in the
    ledger only while the two differ (after a content-neutral change), so a ledger without it
    needs no migration."""
    g = st.get("content_gen")
    return int(g) if g is not None else st.get("gen")


def bump_gen(st, content=True):
    """Count one more write of the ledger. `content=False`: a change that cannot alter what a
    round contains (CONTENT_NEUTRAL_*, postponing a review); the generation a prepared round
    is tied to stays where it was."""
    was = content_gen(st)
    st["gen"] = int(st.get("gen") or 0) + 1
    if content:
        st.pop("content_gen", None)
    else:
        st["content_gen"] = int(was or 0)
    return st["gen"]


def deep_merge(target, changes):
    for k, v in (changes or {}).items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_merge(target[k], v)
        else:
            target[k] = v


def guideline_context(st):
    """Region and specialty the author and the examiner work to; the defaults stand in for a
    ledger that has none (older ledgers, or a blank value)."""
    def text(v, default):
        return v.strip() if isinstance(v, str) and v.strip() else default
    return {"guideline_region": text((st.get("config") or {}).get("guideline_region"),
                                     DEFAULT_CONFIG["guideline_region"]),
            "specialty": text((st.get("profile") or {}).get("specialty"), DEFAULT_PROFILE["specialty"])}


def new_state(today):
    return {
        "schema": SCHEMA, "gen": 0, "created": iso(today), "updated": iso(today),
        "next_id": "S0001",
        "profile": json.loads(json.dumps(DEFAULT_PROFILE)),
        "config": json.loads(json.dumps(DEFAULT_CONFIG)),
        "review": {"last": None, "next_due": None, "period_start": iso(today)},
        "blueprint": {},
        "topics": {}, "gaps": [], "resolved": [],
        "sessions": [], "previous": [], "agg": empty_agg(),
        "reviews": [], "drills": [], "errata": [], "pending_errata": [],
        "teaching_point_checks": {}, "unreflected": None,
        "block": None, "blocks": [],     # the current themed block (set when its first round is recorded) and finished ones
    }


def empty_agg():
    return {"sessions": 0, "items": 0, "minutes": 0, "reading_minutes": 0, "mcqs": 0,
            "mcq_correct": 0, "focused": 0, "focused_mastery_sum": 0.0, "score_sum": 0.0, "score_n": 0,
            "art": {k: [0.0, 0] for k in ART_MAX}, "art_focused": {k: [0.0, 0] for k in ART_MAX},
            "idea": [0, 0, 0],
            "errors": {"category": {}, "knowledge_type": {}, "art_domain": {}, "severity": {},
                       "bias": {}},
            "calibration": {k: [0, 0.0] for k in CONF_PROB}, "brier": [0.0, 0],
            "drills": {k: 0 for k in DRILL_RESULTS},
            "disputes": {k: 0 for k in DISPUTE_OUTCOMES},
            "overrides": {"scores": 0, "gaps": 0},
            "reflection_skipped": 0}


def agg_overrides(agg):
    """The all-time counters of what the learner set themselves (ledgers before 5.0 have none)."""
    return agg.setdefault("overrides", {"scores": 0, "gaps": 0})


# ---------------------------------------------------------------- blueprint

def weight_from_text(text):
    t = (text or "").strip().lower()
    if t in ("very high", "highest"):
        return 1.3
    if t in ("high", "h"):
        return 1.0
    if t in ("medium", "med", "m"):
        return 0.6
    if t in ("low", "l"):
        return 0.35
    if t in ("very low", "lowest", "minimal"):
        return 0.2
    try:
        return float(t)
    except ValueError:
        return 0.6


def blueprint_from_md(text):
    """Parse the markdown blueprint format into {DOMAIN: {name, weight, topics}}."""
    bp, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(?:[A-Z]\.\s*)?(.+?)\s*\(weight:\s*([^)]+)\)\s*$", line.strip())
        if m:
            cur = {"name": m.group(1).strip(), "weight": weight_from_text(m.group(2)),
                   "topics": {}}
            cur["_pending"] = True
            continue
        m = re.match(r"^-\s+([A-Z]{2,8}[-.][A-Za-z0-9_\-]+)\s+(.+?)\s*$", line.strip())
        if m and cur is not None:
            tid, label = m.group(1), m.group(2)
            d = domain_of(tid)
            if d not in bp:
                bp[d] = {"name": cur["name"], "weight": cur["weight"], "topics": {}}
            bp[d]["topics"][tid] = label
    return bp


def bp_topics(state):
    out = {}
    for d, info in (state.get("blueprint") or {}).items():
        for tid, label in (info.get("topics") or {}).items():
            out[tid] = {"domain": d, "label": label}
    return out


def bp_weights(state):
    return {d: float(info.get("weight", 0.6)) for d, info in (state.get("blueprint") or {}).items()}


def significant_tokens(label):
    label = re.sub(r"\(see[^)]*\)", " ", label or "", flags=re.I)
    out = set()
    for w in re.findall(r"[a-z]+", label.lower()):
        if len(w) < 5 or w in GENERIC_WORDS:
            continue
        out.add(w[:-1] if w.endswith("s") else w)
    return out


def blueprint_refs(topics):
    refs = {}
    for tid, info in topics.items():
        t_ids, doms = set(), set()
        for m in re.finditer(r"\(see(?: also)?\s+([^)]*)\)", info.get("label") or "", flags=re.I):
            for tok in re.split(r"[\s,/;]+", m.group(1)):
                tok = tok.strip().rstrip(".")
                if re.match(r"^[A-Z]{2,8}[.\-][A-Za-z0-9_\-]+$", tok):
                    t_ids.add(tok)
                elif re.match(r"^[A-Z]{2,8}$", tok):
                    doms.add(tok)
        refs[tid] = (t_ids, doms)
    return refs


# ---------------------------------------------------------------- scheduling

def schedule_topic(prev_step, mastery, comfort, misconception, self_gap, intervals, today):
    n = len(intervals)
    k = max(0, min(int(prev_step or 0), n - 1))
    calibration = "not_rated" if comfort is None else "aligned"
    if misconception:
        k_new, interval, calibration = 0, intervals[0], "confident_error"
    else:
        if mastery >= 4:
            k_new = min(k + 1, n - 1)
        elif mastery <= 2:
            k_new = 0
        else:
            k_new = k
        interval = intervals[k_new]
        if comfort is not None:
            delta = comfort - mastery
            if delta >= 2:
                calibration = "overconfident"
                k_new = min(k_new, k)
                interval = min(intervals[k_new], 3)
            elif delta <= -2 and mastery >= 4:
                calibration = "underconfident"
                interval = max(intervals[0], int(round(interval * 0.5)))
    if self_gap:
        interval = min(interval, 7)
    # Whatever the answer, the topic rests a few days: a re-test the next day is answered from the
    # feedback just read, so it neither measures nor builds what the learner will keep.
    interval = max(MIN_RETURN_DAYS, int(interval))
    return k_new, today + dt.timedelta(days=interval), calibration, interval


def adjusted_item_mastery(item):
    m = float(item.get("mastery", 0))
    conf = (item.get("confidence") or "").lower() or None
    correct = item.get("correct")
    misconception = False
    if item.get("set_by") == "learner":
        # the learner's own score is taken as given: no confidence rule is laid over it
        return m, False
    if item.get("type") == "mcq":
        if correct is True and conf == "guess":
            m = min(m, 3.0)
        if correct is False and conf == "sure":
            misconception = True
    elif m <= 2 and conf == "sure":
        misconception = True
    return m, misconception


def item_outcome(it):
    if it.get("type") == "mcq":
        return None if it.get("correct") is None else (1.0 if it.get("correct") else 0.0)
    # calibration compares the confidence with what the examiner graded, also where the learner
    # set the recorded score
    m = it.get("graded") if it.get("set_by") == "learner" and it.get("graded") is not None else it.get("mastery")
    return None if m is None else max(0.0, min(1.0, float(m) / 5.0))


def gap_ref(g):
    """How an item names the gap it retests: the gap's id; its topic for a gap not yet numbered."""
    return g.get("id") or g.get("topic")


def number_gaps(state):
    """Give every open gap an id (G0001, …). Ledgers written before gaps had ids get them here."""
    n = max([id_num(g.get("id")) for g in state["gaps"] + state["resolved"] if g.get("id")] + [0])
    for g in state["gaps"]:
        if not g.get("id"):
            n += 1
            g["id"] = "G%04d" % n
    return n


def gap_awaits_retest(g):
    """True until an item has tested this gap since it was last written."""
    retested, written = parse_date(g.get("last_retested")), parse_date(g.get("date"))
    return retested is None or written is None or retested < written


def answered_well(mastery, calibration):
    """The bar a retest must clear to close a gap; below it the topic counts as missed."""
    return mastery is not None and mastery >= 4 and calibration not in ("overconfident", "confident_error")


def drilldown_over(state, tid, theme):
    """True when a miss on topic `tid` in the round being applied should not bring it straight
    back. In the block's theme a topic may be drilled in two rounds in a row: over when the round
    before was on it too. Outside the theme a miss gets one targeted retest: over when the topic
    already had an open gap or was missed the last time it was tested."""
    t = state["topics"].get(tid) or {}
    if theme and t.get("domain") == theme:
        return bool(state["sessions"]) and tid in (state["sessions"][-1].get("topics") or [])
    prev = (t.get("history") or [None])[-1]
    return any(g.get("topic") == tid for g in state["gaps"]) or bool(prev and not answered_well(prev[1], prev[3]))


def ensure_topic(state, tid, domain=None, label=None):
    t = state["topics"].get(tid)
    if not t:
        bpt = bp_topics(state).get(tid) or {}
        t = {"domain": (domain or bpt.get("domain") or domain_of(tid)).upper(),
             "label": label or bpt.get("label") or tid,
             "last": None, "attempts": 0, "mastery": None, "step": 0, "due": None,
             "comfort": None, "calibration": None, "history": []}
        state["topics"][tid] = t
    else:
        if label and not t.get("label"):
            t["label"] = label
        t.setdefault("history", [])
    return t


# ---------------------------------------------------------------- status

def review_status(state, today):
    rv = state.get("review") or {}
    cfg = state.get("config") or {}
    due = parse_date(rv.get("next_due"))
    start = parse_date(rv.get("period_start")) or parse_date(state.get("created"))
    n = len(state.get("sessions") or [])
    interval = int(cfg.get("review_interval_days") or 42)
    if due is None:
        return False, None
    if today >= due and n >= MIN_SESSIONS_FOR_REVIEW:
        return True, iso(due)
    if today >= due + dt.timedelta(days=REVIEW_GRACE_DAYS):
        return True, iso(due)
    return False, iso(due)


def check_schema(st):
    if not isinstance(st, dict) or st.get("schema") != SCHEMA:
        die("not a version-%d state file (schema=%r)." % (SCHEMA, (st or {}).get("schema")))
    for k in ("profile", "config", "topics", "gaps", "sessions", "blueprint"):
        if k not in st:
            die("state lacks '%s'" % k)


# ---------------------------------------------------------------- plan

def domain_weights(state):
    prof = state.get("profile") or {}
    ratings = prof.get("domain_self_ratings") or {}
    emphasis = prof.get("domain_emphasis") or {}
    weights = bp_weights(state)
    domains = set(weights) | set(ratings) | set(emphasis) | {t.get("domain") for t in state["topics"].values()}
    shown = {}       # domain -> [sum, n] of the current mastery of its tested topics
    for t in state["topics"].values():
        if isinstance(t.get("mastery"), (int, float)):
            x = shown.setdefault(t.get("domain"), [0.0, 0])
            x[0] += float(t["mastery"]); x[1] += 1
    eff = {}
    for d in domains:
        if not d:
            continue
        w = weights.get(d, min(weights.values()) if weights else 1.0)
        r = ratings.get(d)
        r = r.get("rating") if isinstance(r, dict) else r
        try:
            r = int(round(float(r))) if r is not None else None
        except (TypeError, ValueError):
            r = None
        # Corrected for overconfidence: a rating lowers a domain's share only as far as the
        # answers given in that domain bear it out. A 5/5 over a mean mastery of 3 counts as 3.
        # A low rating always counts: asking for more practice costs nothing.
        if r is not None and d in shown:
            r = min(r, max(1, int(math.floor(shown[d][0] / shown[d][1] + 1e-9))))
        w *= SELF_RATING_FACTOR.get(r, 1.0)
        try:
            w *= float(emphasis.get(d, 1.0))
        except (TypeError, ValueError):
            pass
        eff[d] = max(w, 0.0)
    return eff


# ---------------------------------------------------------------- themed blocks (ADR 0003)

def domain_name(st, d):
    return ((st.get("blueprint") or {}).get(d) or {}).get("name") or d


def block_line(st, block):
    """The one line the learner sees about the block: the theme and the position, nothing else."""
    return "Block: %s, round %d of %d" % (domain_name(st, block["theme"]), block["round"], block["length"])


def block_open(st):
    """The ledger's block, if it has one with rounds still to come and a theme the blueprint knows."""
    b = st.get("block")
    if not isinstance(b, dict) or b.get("theme") not in (st.get("blueprint") or {}):
        return None
    return b if int(b.get("round") or 0) < int(b.get("length") or BLOCK_LENGTH) else None


def propose_theme(st, exclude=()):
    """The domain proposed as the next theme, with a one-line reason: the weakest domain, or the
    one longest without a block. Returns {"theme", "reason", "ranking"} or None (no blueprint).

    Each domain is scored as its weight for new material (blueprint weight, self-rating corrected
    for overconfidence, emphasis: see domain_weights), raised by 10% per open gap (to 50%), times
    how long it has gone without a block: a quarter right after its own block, back to full after
    four other blocks; a domain never yet a theme counts in full. No chance involved; ties go to
    blueprint order. The theme of the block just finished is not proposed again straight away."""
    bp = st.get("blueprint") or {}
    eff = domain_weights(st)
    sizes = {d: len((info or {}).get("topics") or {}) for d, info in bp.items()}
    pool = [d for d in bp if eff.get(d, 0) > 0 and sizes[d] >= MIN_THEME_TOPICS] \
        or [d for d in bp if eff.get(d, 0) > 0 and sizes[d]] or [d for d in bp if sizes[d]]
    last = (st.get("block") or {}).get("theme") if isinstance(st.get("block"), dict) else None
    skip = set(exclude) | ({last} if last else set())
    if last and not int(st["block"].get("round") or 0) and st.get("blocks"):
        skip.add(st["blocks"][-1].get("theme"))     # a block chosen but not begun: the one before it was the last
    pool = [d for d in pool if d not in skip] or [d for d in pool if d not in set(exclude)] or pool
    if not pool:
        return None
    themes = [b.get("theme") for b in (st.get("blocks") or [])] + ([last] if last else [])
    tested, open_gaps = {}, {}
    for t in st["topics"].values():
        if isinstance(t.get("mastery"), (int, float)):
            tested.setdefault(t.get("domain"), []).append(float(t["mastery"]))
    for g in st.get("gaps") or []:
        d = (st["topics"].get(g.get("topic")) or {}).get("domain") or domain_of(g.get("topic") or "")
        open_gaps[d] = open_gaps.get(d, 0) + 1

    def since(d):       # blocks begun since d's own; None if d was never a theme
        return themes[::-1].index(d) + 1 if d in themes else None

    def score(d):
        rest = min(since(d) or THEME_REST_BLOCKS, THEME_REST_BLOCKS) / float(THEME_REST_BLOCKS)
        return eff.get(d, 0) * (1 + 0.1 * min(open_gaps.get(d, 0), 5)) * rest

    order = list(bp)
    ranking = sorted(pool, key=lambda d: (-round(score(d), 6), order.index(d)))
    best = ranking[0]
    why = []
    if tested.get(best):
        m = tested[best]
        why.append("mean %.1f of 5 over %d topic%s tested" % (sum(m) / len(m), len(m), "" if len(m) == 1 else "s"))
    else:
        why.append("nothing tested yet")
    if open_gaps.get(best):
        why.append("%d open gap%s" % (open_gaps[best], "" if open_gaps[best] == 1 else "s"))
    n = since(best)
    why.append("not yet a theme" if n is None else "last a theme %d block%s ago" % (n, "" if n == 1 else "s"))
    return {"theme": best, "reason": "%s: %s" % (domain_name(st, best), ", ".join(why)), "ranking": ranking}


def next_block(st):
    """(block, starts): the block the next round belongs to, with `round` the rounds already
    recorded in it, and whether that round starts it. A ledger with no block (written before
    blocks, or new) or with a finished one gets a new block on the proposed theme; it is only
    written to the ledger when its first round is recorded (advance_block), so planning reads
    only. (None, False) for a ledger with no blueprint."""
    b = block_open(st)
    if b:
        return dict(b, round=int(b.get("round") or 0), length=int(b.get("length") or BLOCK_LENGTH)), False
    p = propose_theme(st)
    if not p:
        return None, False
    return {"theme": p["theme"], "round": 0, "length": BLOCK_LENGTH, "started": None,
            "chosen": "auto", "reason": p["reason"]}, True


def start_block(st, theme, chosen="auto", reason=None, length=BLOCK_LENGTH):
    """Make `theme` the ledger's block, at round 0, filing the block it replaces under `blocks`
    if any round was recorded in it. `chosen` says who picked the theme: "auto" or "learner"."""
    if theme not in (st.get("blueprint") or {}):
        die("unknown domain %r: the theme must be one of %s" % (theme, ", ".join(st.get("blueprint") or {})))
    old = st.get("block")
    if isinstance(old, dict) and old.get("theme") and int(old.get("round") or 0) > 0:
        st.setdefault("blocks", []).append({k: old.get(k) for k in ("theme", "started", "last", "round", "length", "chosen")})
        st["blocks"] = st["blocks"][-CAP_BLOCKS:]
    st.setdefault("blocks", [])
    st["block"] = {"theme": theme, "round": 0, "length": int(length), "started": None, "last": None,
                   "chosen": chosen, "reason": reason}
    return st["block"]


def advance_block(st, rdate):
    """Count a round recorded on `rdate` in the block, starting the next block first when the
    ledger has none open. Call it before the round is applied: the proposed theme then is the one
    the round was planned on. Returns what the session entry keeps: theme, round, length."""
    b, starts = next_block(st)
    if b is None:
        return None
    b = start_block(st, b["theme"], b.get("chosen") or "auto", b.get("reason")) if starts else st["block"]
    b["round"] = int(b.get("round") or 0) + 1
    b["length"] = int(b.get("length") or BLOCK_LENGTH)
    b["started"] = b.get("started") or iso(rdate)
    b["last"] = iso(rdate)
    return {"theme": b["theme"], "round": b["round"], "length": b["length"]}


def block_status(st):
    """The block as the learner may see it before the next round: theme, position and the line."""
    b, starts = next_block(st)
    if b is None:
        return None
    out = {"theme": b["theme"], "name": domain_name(st, b["theme"]), "round": b["round"] + 1,
           "length": b["length"], "starts": starts or b["round"] == 0}   # round 0: chosen, not yet begun
    out["line"] = block_line(st, out)
    return out


# ---- changing the theme (issue #17)

def block_end(st):
    """After the last round of a block: the proposal for the next one, with the one line to tell
    the learner (theme, reason, how to change it). None while the block has rounds to come."""
    b = st.get("block")
    if not isinstance(b, dict) or not b.get("theme") or block_open(st):
        return None
    p = propose_theme(st)
    if not p:
        return None
    return {"finished": domain_name(st, b["theme"]), "theme": p["theme"], "name": domain_name(st, p["theme"]),
            "reason": p["reason"],
            "line": 'Block finished: %s. Next block: %s. To change it, say "pick another" or name an area.'
                    % (domain_name(st, b["theme"]), p["reason"])}


def find_domain(st, text):
    """The blueprint domain the learner named: its id, its name, or a part of either that fits
    one domain only."""
    bp = st.get("blueprint") or {}
    want = (text or "").strip().lower()
    names = {d: str((info or {}).get("name") or d).lower() for d, info in bp.items()}
    hits = [d for d in bp if want and (d.lower() == want or names[d] == want)] \
        or [d for d in bp if want and (want in names[d] or d.lower().startswith(want))]
    if len(hits) != 1:
        die("%s domain for %r: the theme must be one of %s"
            % ("more than one" if hits else "no", text,
               "; ".join("%s (%s)" % (d, domain_name(st, d)) for d in (hits or bp))))
    return hits[0]


def change_theme(st, theme=None, another=False):
    """The learner changes the theme, at the end of a block or in the middle of one: `theme` is
    the domain they named, `another` asks for the next proposal instead. The block the next
    round would have belonged to is replaced by a new one at round 0 (start_block files it if
    any round was recorded in it). Themes turned down with "pick another" are remembered until
    the new block's first round, so asking again moves on down the ranking.
    Returns {"changed", "was", "reason", "warnings"}."""
    cur, _ = next_block(st)
    if cur is None:
        die("the ledger has no blueprint: there is no theme to change")
    old = st.get("block") if isinstance(st.get("block"), dict) else {}
    is_open = block_open(st) is not None
    pending = is_open and int(old.get("round") or 0) == 0
    was = {"theme": cur["theme"], "name": domain_name(st, cur["theme"]),
           "round": int(cur.get("round") or 0), "length": cur["length"], "begun": is_open and not pending}
    warnings = []
    declined = [d for d in (old.get("declined") or []) if d != cur["theme"]] if pending else []
    if another:
        declined.append(cur["theme"])
        p = propose_theme(st, exclude=declined)
        if p["theme"] in declined:              # every domain turned down: start again from the top
            declined = [cur["theme"]]
            p = propose_theme(st, exclude=declined)
        theme, reason = p["theme"], p["reason"]
    else:
        theme = find_domain(st, theme)
        n = len(((st.get("blueprint") or {}).get(theme) or {}).get("topics") or {})
        if not n:
            die("%s has no topics in the blueprint, so it cannot be a theme" % domain_name(st, theme))
        if theme == cur["theme"] and is_open:
            return {"changed": False, "was": was, "reason": old.get("reason"), "warnings": warnings}
        if n < MIN_THEME_TOPICS:
            warnings.append("%s has only %d topic%s: its rounds will revisit them on other decision points"
                            % (domain_name(st, theme), n, "" if n == 1 else "s"))
        reason = "%s: your choice" % domain_name(st, theme)
    b = start_block(st, theme, "learner", reason)
    if declined:
        b["declined"] = declined
    return {"changed": theme != cur["theme"] or not is_open, "was": was, "reason": reason, "warnings": warnings}


def block_mix(shorts, n):
    """How many of a round's `shorts` short questions go to the theme, to due repeats and to the
    wildcard in round `n` of a block. The shares (60/25/15) are met over the block, not in each
    round: with three short questions a round would otherwise never have a wildcard. Round n gets
    what the first n rounds are owed (largest remainder) less what the first n-1 were given."""
    def owed(k):
        quota = [shorts * k * pct for _, pct in BLOCK_SHARES]
        got = [q // 100 for q in quota]
        for i in sorted(range(len(got)), key=lambda i: (-(quota[i] % 100), i))[:shorts * k - sum(got)]:
            got[i] += 1
        return got
    mix = [max(0, a - b) for a, b in zip(owed(max(1, n)), owed(max(1, n) - 1))]
    while sum(mix) > shorts:
        mix[mix.index(max(mix))] -= 1
    mix[0] += shorts - sum(mix)
    return {name: mix[i] for i, (name, _) in enumerate(BLOCK_SHARES)}


def next_case_format(st):
    """The format the next round's case takes: the setting, alternating when asked to, and one
    step when the session is too short for an unfolding case."""
    cfg = st.get("config") or {}
    fmt = cfg.get("case_format", "unfolding")
    if fmt == "alternate":
        last_fmt = next((s.get("format") for s in reversed(st.get("sessions") or []) if s.get("format")), None)
        fmt = "discriminate" if last_fmt == "unfolding" else "unfolding"
    if int(cfg.get("session_minutes", 20) or 20) <= 12 and fmt == "unfolding":
        fmt = "discriminate"
    return fmt


def round_minutes(mcqs, focused, case, fmt="unfolding"):
    """The estimate for a round of this mix, feedback included (MINUTES_PER)."""
    return (MINUTES_PER["mcq"] * int(mcqs or 0) + MINUTES_PER["focused"] * int(focused or 0)
            + (MINUTES_PER.get(fmt, MINUTES_PER["unfolding"]) if case else 0))


def mix_estimate(st):
    """(the round mix in force, the minutes a round of it is estimated to take)."""
    cfg = st.get("config") or {}
    mix = {"mcqs": int(cfg.get("mcqs", DEFAULT_CONFIG["mcqs"]) or 0), "focused": int(cfg.get("focused", 0) or 0),
           "case": bool(cfg.get("case", True))}
    return mix, round_minutes(mix["mcqs"], mix["focused"], mix["case"], next_case_format(st))


def all_sessions_for_novelty(state):
    """(cases, stems) from current and previous sessions, oldest first."""
    cases, stems = [], []
    for s in (state.get("previous") or []) + (state.get("sessions") or []):
        if s.get("case"):
            c = dict(s["case"]); c["id"] = s.get("id"); c["date"] = s.get("date")
            cases.append(c)
        for it in s.get("items") or []:
            if it.get("type") in ("mcq", "focused") and it.get("stem"):
                x = {"id": s.get("id"), "date": s.get("date"), "topic": it.get("topic"),
                     "kind": it["type"], "stem": it["stem"]}
                if it.get("aspect"):
                    x["aspect"] = it["aspect"]
                stems.append(x)
    return cases, stems


def plan_round(st, args, today):
    """The plan for the next round of ledger `st` as of `today`, as a dict. `args` carries the
    one-off options of plan/start (mcqs, focused, no_case, domain, no_new, allow_repeat, no_drill,
    force_drill, seed). Reads only; writes and prints nothing."""
    cfg = st["config"]
    n_case = 0 if args.no_case else (1 if cfg.get("case", True) else 0)
    n_mcqs = args.mcqs if args.mcqs is not None else int(cfg.get("mcqs", 3) or 0)
    n_focused = args.focused if getattr(args, "focused", None) is not None else int(cfg.get("focused", 0) or 0)
    for name, v in (("--mcqs", n_mcqs), ("--focused", n_focused)):
        lo, hi = ROUND_LIMITS[name[2:]]
        if not lo <= v <= hi:
            die("%s must be between %d and %d" % (name, lo, hi))
    if n_case + n_mcqs + n_focused == 0:
        die("the round would be empty: ask for at least one MCQ, focused question or the case")
    topics = st["topics"]
    bpt = bp_topics(st)
    eff = domain_weights(st)
    log = st["sessions"]
    rng = random.Random(args.seed if args.seed is not None else int(today.strftime("%Y%m%d")) * 100 + len(log))
    restrict = args.domain.upper() if args.domain else None
    # The block this round belongs to. Its theme steers the round unless the learner asked for a
    # one-off domain round (--domain), which still counts as a round of the block.
    block = block_status(st)
    theme = block["theme"] if block and not restrict else None

    # Tested in the last few days: left to rest, whatever its due date says (a ledger written by
    # an older version can hold a topic due the day after a miss).
    resting = {tid for tid, t in topics.items()
               if parse_date(t.get("last")) and (today - parse_date(t["last"])).days < MIN_RETURN_DAYS}
    # In each of the last two rounds: left out of this one, due or not (the drill-down limit).
    history = (st.get("previous") or []) + log
    last_rounds = [set(s.get("topics") or []) for s in history[-DRILLDOWN_MAX_ROUNDS:]]
    drilled = set.intersection(*last_rounds) if len(last_rounds) == DRILLDOWN_MAX_ROUNDS else set()
    recent = set()
    for s in log[-3:]:
        recent.update(s.get("topics") or [])
    recent_domains = [domain_of(t) for s in log[-10:] for t in (s.get("topics") or [])]

    def allowed(tid):
        if (tid in resting or tid in drilled) and not args.allow_repeat:
            return False
        if restrict and (topics.get(tid, {}).get("domain") or domain_of(tid)) != restrict:
            return False
        return True

    gaps_by_topic = {g["topic"]: g for g in st.get("gaps") or [] if g.get("topic")}

    def gap_rank(g):
        src = g.get("source") or []
        src = [src] if isinstance(src, str) else src
        if "misconception" in src:
            return 0
        if "self" in src:
            return 1
        if "transfer" in src:
            return 2
        return 3

    due = []
    for tid, t in topics.items():
        nd = parse_date(t.get("due"))
        if nd and nd <= today and allowed(tid):
            urgency = 0 if t.get("calibration") in ("overconfident", "confident_error") else 1
            g = gaps_by_topic.get(tid)
            due.append(((urgency, gap_rank(g) if g else 9, -(today - nd).days,
                         t.get("mastery") if t.get("mastery") is not None else 0), tid))
    due.sort()
    due_ids = [tid for _, tid in due]

    gap_ids = []
    for tid, g in sorted(gaps_by_topic.items(), key=lambda kv: (gap_rank(kv[1]), kv[1].get("date") or "")):
        if tid in due_ids or not allowed(tid):
            continue
        # One targeted re-test of a gap that no item has tested since it was written, once the
        # gap is a few days old; after that the gap comes back with its topic's spacing.
        gd = parse_date(g.get("date"))
        if gap_awaits_retest(g) and (gd is None or (today - gd).days >= MIN_RETURN_DAYS or args.allow_repeat):
            gap_ids.append(tid)
        # A gap of the theme whose topic was last tested under another theme: the pause it was
        # given outside the theme ends with its domain's block (also after a change of theme).
        elif theme and topics.get(tid, {}).get("domain") == theme and theme != next(
                ((s.get("block") or {}).get("theme") for s in reversed(history) if tid in (s.get("topics") or [])), theme):
            gap_ids.append(tid)

    def new_candidates():
        pool = []
        for tid, info in bpt.items():
            d = info["domain"]
            if tid in topics or tid in recent or not allowed(tid):
                continue
            w = eff.get(d, 1.0) / (1.0 + recent_domains.count(d))
            if w > 0:
                pool.append((w, tid, d))
        return pool

    def domain_only_candidates(exclude):
        pool = []
        for d, w in eff.items():
            if d in exclude or (restrict and d != restrict):
                continue
            w = w / (1.0 + recent_domains.count(d))
            if w > 0:
                pool.append((w, None, d))
        return pool

    def weighted_pick(pool):
        total = sum(w for w, _, _ in pool)
        if total <= 0:
            return None
        x, acc = rng.uniform(0, total), 0.0
        for item in pool:
            acc += item[0]
            if x <= acc:
                return item
        return pool[-1]

    def label_of(tid):
        return (topics.get(tid) or {}).get("label") or (bpt.get(tid) or {}).get("label")

    def reason_for(tid, code):
        t = topics.get(tid) or {}
        if code == "due":
            text = "spaced review due %s" % t.get("due")
            if t.get("mastery") is not None:
                text += "; last %s/5 on %s" % (t.get("mastery"), t.get("last"))
            if t.get("calibration") in ("overconfident", "confident_error"):
                text += "; flagged %s last time" % t["calibration"].replace("_", " ")
            g = gaps_by_topic.get(tid)
            if g:
                text += "; open gap: %s" % clip(g.get("gap"), 240)
            return text
        if code == "gap":
            g = gaps_by_topic.get(tid) or {}
            src = g.get("source") or []
            return "open gap (%s) from %s: %s" % (", ".join([src] if isinstance(src, str) else src),
                                                 g.get("date"), clip(g.get("gap"), 240))
        if code == "new":
            if theme and dom(tid) == theme:
                return "not yet tested; in the block's theme"
            return "not yet tested; chosen by domain weight (blueprint, your self-ratings, emphasis)"
        if code == "revisit":
            text = "the block's theme; tested before, not yet due (last %s/5 on %s): " \
                   "ask about another decision point of the topic" % (t.get("mastery"), t.get("last"))
            return text
        return code

    labels = {tid: {"label": label_of(tid) or ""} for tid in set(bpt) | set(topics)}
    refs = blueprint_refs(labels)

    def related(a, b):
        if not a or not b:
            return False
        if a == b:
            return True
        ra_t, ra_d = refs.get(a, (set(), set()))
        rb_t, rb_d = refs.get(b, (set(), set()))
        da, db = domain_of(a), domain_of(b)
        if b in ra_t or a in rb_t or (ra_t & rb_t) or db in ra_d or da in rb_d:
            return True
        return bool(significant_tokens(labels[a]["label"]) & significant_tokens(labels[b]["label"]))

    chosen, used_topics, used_domains, case_topics, case_domains = [], set(), [], [], []

    def mcq_ok(tid, domain, level):
        if tid in used_topics:
            return False
        if tid and any(related(tid, c) for c in case_topics):
            return False
        shared = bool(restrict) or domain == theme     # a domain several items of the round may share
        if level <= 1 and not shared and domain in case_domains:
            return False
        if level == 0 and not shared and domain in used_domains:
            return False
        if level <= 1 and tid and any(related(tid, c["topic"]) for c in chosen if c["slot"] != "case" and c.get("topic")):
            return False
        return True

    def take(slot, level=0, new_only=False):
        sources = () if new_only else ((due_ids, "due"), (gap_ids, "gap"))
        for source, code in sources:
            for tid in source:
                if tid in used_topics:
                    continue
                d = (topics.get(tid) or {}).get("domain") or domain_of(tid)
                if slot != "case" and not mcq_ok(tid, d, level):
                    continue
                return {"slot": slot, "topic": tid, "label": label_of(tid), "domain": d,
                        "reason_code": code, "reason": reason_for(tid, code)}
        pool = new_candidates()
        if slot != "case":
            pool = [x for x in pool if mcq_ok(x[1], x[2], level)]
        pick = weighted_pick(pool)
        if pick:
            return {"slot": slot, "topic": pick[1], "label": label_of(pick[1]), "domain": pick[2],
                    "reason_code": "new", "reason": reason_for(pick[1], "new")}
        excl = set(case_domains if slot != "case" and not restrict else [])
        if slot != "case" and level == 0:
            excl |= set(used_domains)
        pick = weighted_pick(domain_only_candidates(excl))
        if pick:
            return {"slot": slot, "topic": None, "domain": pick[2], "reason_code": "new_in_domain",
                    "reason": "under-sampled domain; choose a specific untested topic in it"
                              + ("" if slot == "case" else ", unrelated to the case")}
        return None

    def separation(item, level):
        return ("no case this round; unrelated to the other questions" if not case_topics else
                "same domain as the case (the block's theme), unrelated topic"
                if item["domain"] in case_domains and item["domain"] == theme else
                "same domain as the case (domain round), unrelated topic"
                if item["domain"] in case_domains else
                "other domain" if level == 0 else "other domain than the case")

    def take_short(slot, new_only=False):
        for level in (0, 1, 2):
            if level == 2 and not restrict and [d for d in eff if d not in case_domains]:
                break
            item = take(slot, level, new_only)
            if item:
                item["separation"] = separation(item, level)
                return item
        return None

    # ---- a round of a themed block: each slot draws on one share (theme, repeat, wildcard)

    def dom(tid):
        return (topics.get(tid) or {}).get("domain") or (bpt.get(tid) or {}).get("domain") or domain_of(tid)

    def fits(slot, tid, d, level):
        return tid not in used_topics and (slot == "case" or mcq_ok(tid, d, level))

    def entry(slot, tid, d, code, share):
        return {"slot": slot, "topic": tid, "label": label_of(tid), "domain": d, "share": share,
                "reason_code": code, "reason": reason_for(tid, code)}

    last_case = ((log[-1].get("case") or {}).get("topic") if log else None)

    def take_waiting(slot, level, share, where=None):
        """The most urgent due topic, then a gap ready for its retest. `where`: True for the
        theme only, False for the other domains only. The case is not on the topic of the last
        round's case while the theme has anything else to give (level 0)."""
        for source, code in ((due_ids, "due"), (gap_ids, "gap")):
            for tid in source:
                if where is not None and (dom(tid) == theme) != where:
                    continue
                if slot == "case" and level == 0 and tid == last_case:
                    continue
                if fits(slot, tid, dom(tid), level):
                    return entry(slot, tid, dom(tid), code, share)
        return None

    def take_new(slot, level, share, in_theme):
        pick = weighted_pick([x for x in new_candidates()
                              if (x[2] == theme) == in_theme and fits(slot, x[1], x[2], level)])
        return entry(slot, pick[1], pick[2], "new", share) if pick else None

    def take_theme(slot, level, new_first=False):
        """Theme material: what is due or awaits a retest in the theme, then an untested topic,
        then the theme topic tested longest ago (another decision point of it)."""
        item = None
        if not new_first:
            item = take_waiting(slot, level, "theme", True)
        item = item or take_new(slot, level, "theme", True)
        if not item and new_first:
            item = take_waiting(slot, level, "theme", True)
        if item:
            return item
        seen = sorted((t.get("last") or "", t.get("mastery") if t.get("mastery") is not None else 0, tid)
                      for tid, t in topics.items() if dom(tid) == theme and allowed(tid))
        for _, _, tid in seen:
            if slot == "case" and level == 0 and tid == last_case:
                continue
            if fits(slot, tid, theme, level):
                return entry(slot, tid, theme, "revisit", "theme")
        if eff.get(theme, 0) > 0 or theme in bp_weights(st):
            return {"slot": slot, "topic": None, "domain": theme, "share": "theme", "reason_code": "new_in_domain",
                    "reason": "the block's theme; choose a specific untested topic in it"
                              + ("" if slot == "case" else ", unrelated to the case")}
        return None

    def take_wildcard(slot, level):
        """Something new from outside the theme, by domain weight."""
        item = take_new(slot, level, "wildcard", False)
        if item:
            return item
        excl = set(case_domains) | {theme} | (set(used_domains) if level == 0 else set())
        pick = weighted_pick(domain_only_candidates(excl))
        if pick:
            return {"slot": slot, "topic": None, "domain": pick[2], "share": "wildcard",
                    "reason_code": "new_in_domain",
                    "reason": "under-sampled domain; choose a specific untested topic in it, unrelated to the case"}
        return None

    def take_share(slot, share, new_first=False):
        """A short question for one share. A share with nothing to give passes its slot on: a
        repeat or wildcard slot to the theme, and the theme to whatever the ledger has."""
        # a repeat slot goes first to what waits outside the theme: the theme's own slots take the rest
        for level, where in ((0, False), (1, False), (1, None)):
            item = (take_waiting(slot, level, "repeat", where) if share == "repeat" else
                    take_wildcard(slot, level) if share == "wildcard" and where is False else None)
            if item:
                item["separation"] = separation(item, level)
                return item
        for level in (1, 2):
            item = take_theme(slot, level, new_first)
            if item:
                item["separation"] = separation(item, level)
                return item
        item = take_short(slot)
        if item:
            item["share"] = "repeat" if item["reason_code"] in ("due", "gap") else "wildcard"
        return item

    for _ in range(n_case):
        # the case of a block is always on its theme
        item = (take_theme("case", 0) or take_theme("case", 1)) if theme else None
        item = item or take("case")
        if item:
            chosen.append(item); used_topics.add(item["topic"]); used_domains.append(item["domain"])
            case_topics.append(item["topic"]); case_domains.append(item["domain"])

    def last_session_had_new():
        return bool(log) and any(v == "new" for v in (log[-1].get("why") or {}).values())

    # Short items: focused questions take the due and gap topics before the MCQs (free text shows
    # the reasoning on a re-tested decision point); the last short slot may be kept for a new topic.
    shorts = ["focused"] * n_focused + ["mcq"] * n_mcqs
    total = n_case + len(shorts)
    wants_new = int(cfg.get("new_topics_per_round", 1) or 0) > 0 and not args.no_new
    reserve_new = wants_new and len(shorts) >= 1 and total >= 2 and (total >= 4 or not last_session_had_new())
    mix = block_mix(len(shorts), block["round"]) if theme else None
    # Due repeats take the first slots (the focused questions, when the round has them), then the
    # theme, then the wildcard.
    shares = [name for name, _ in sorted(BLOCK_SHARES, key=lambda x: x[0] != "repeat") for _ in range(mix[name])] \
        if theme else [None] * len(shorts)
    for i, (slot, share) in enumerate(zip(shorts, shares)):
        item = None
        if share:
            # the last theme slot is kept for new theme material when the round has nothing new yet
            last_theme = share == "theme" and "theme" not in shares[i + 1:]
            item = take_share(slot, share, new_first=reserve_new and last_theme and not mix["wildcard"]
                              and not any(c["reason_code"].startswith("new") for c in chosen))
        else:
            if reserve_new and i == len(shorts) - 1 and not any(c["reason_code"].startswith("new") for c in chosen):
                item = take_short(slot, new_only=True)
            item = item or take_short(slot)
        if item:
            chosen.append(item); used_topics.add(item.get("topic")); used_domains.append(item["domain"])

    fmt = next_case_format(st)

    drill = None
    active = [d for d in st.get("drills") or [] if not parse_date(d.get("until")) or parse_date(d["until"]) >= today]
    cases = [c for c in chosen if c["slot"] == "case"]
    target = cases[0] if cases else next((c for c in chosen if c["slot"] == "focused"), None)
    if target is not None and target["slot"] == "focused":
        active = [d for d in active if d.get("code") not in FOCUSED_DRILLS_EXCLUDED]
    if active and target is not None and not args.no_drill:
        d = active[rng.randrange(len(active))]
        if args.force_drill or rng.random() < float(d.get("rate", 0.33)):
            drill = {"code": d.get("code"), "pattern": d.get("description") or d.get("code"),
                     "how": ("Build the case so this pattern is tempting but avoidable from the data "
                             "(case_design.md section 9). Keep it blind; reveal it in the feedback."
                             if target["slot"] == "case" else
                             "Build this focused question so the pattern is tempting but avoidable from "
                             "the vignette (case_design.md sections 9 and 11). Keep it blind; reveal it "
                             "in the feedback.")}
            target["drill"] = drill

    for c in chosen:
        g = gaps_by_topic.get(c.get("topic"))
        if g:
            c["retest_gap"] = {
                "id": gap_ref(g), "gap": clip(g.get("gap"), CLIP_GAP),
                "how": "Write this item on the gap's decision point, in a new clinical context, and "
                       "write the line 'retests: %s' in the item's key header (references/standards.md, "
                       "rule 9). Only an item that says so, answered well, closes the gap." % gap_ref(g)}
    used_cases, used_stems = all_sessions_for_novelty(st)
    for c in chosen:
        same = [x for x in used_cases if x.get("topic") == c.get("topic")]
        same += [x for x in used_stems if x.get("topic") == c.get("topic")]
        if same:
            c["already_used"] = same[-12:]
    # Focused questions: suggest the aspect tested least recently, so rounds vary what is asked.
    last_seen = {a: -1 for a in FOCUSED_ASPECTS}
    for n, x in enumerate(used_stems):
        if x.get("kind") == "focused" and x.get("aspect") in last_seen:
            last_seen[x["aspect"]] = n
    taken = []
    for c in chosen:
        if c["slot"] != "focused":
            continue
        pref = ("diagnosis", "testing", "management", "interpretation", "disposition", "prevention", "prognosis")
        options = [a for a in pref if a not in taken] or list(pref)
        aspect = min(options, key=lambda a: (last_seen[a], pref.index(a)))
        taken.append(aspect)
        c["aspect_hint"] = aspect
        c["aspect_note"] = ("Suggested aspect (least recently tested). If this item re-tests an open "
                            "gap, ask about the gap's decision point instead, whatever its aspect.")
    order = cfg.get("item_order", "mcqs_first")
    by_slot = {k: [c for c in chosen if c["slot"] == k] for k in ("case", "mcq", "focused")}
    present = (by_slot["mcq"] + by_slot["focused"] + by_slot["case"] if order != "case_first"
               else by_slot["case"] + by_slot["mcq"] + by_slot["focused"])
    est = round_minutes(len(by_slot["mcq"]), len(by_slot["focused"]), len(by_slot["case"]), fmt)
    plan = {
        "ok": True, "date": iso(today), "session_id": st.get("next_id"),
        "case_format": fmt if by_slot["case"] else None,
        "item_order": order,
        "presentation_order": ["%s %s" % (c["slot"], c.get("topic") or c.get("domain")) for c in present],
        "counts": {"mcqs": len(by_slot["mcq"]), "focused": len(by_slot["focused"]), "case": len(by_slot["case"])},
        "estimated_minutes": est,
        "lab_units": cfg.get("lab_units"), "blood_gas_units": cfg.get("blood_gas_units"),
        "session_minutes": cfg.get("session_minutes"), **guideline_context(st),
        "feedback_depth": cfg.get("feedback_depth"), "show_coding": cfg.get("show_coding", True),
        "helpers": bool(cfg.get("helpers", True)), "prepare_ahead": bool(cfg.get("prepare_ahead", True)),
        "testing": bool(cfg.get("testing", False)),
        "profile": dict({k: st["profile"].get(k) for k in ("role", "subspecialty", "practice_setting", "notes")},
                        specialty=guideline_context(st)["specialty"]),
        "recent_cases_any_topic": used_cases[-15:],
        # the block: `line` is what the learner is told (theme and position); `mix` is how this
        # round's short questions were shared out (None in a one-off domain round)
        "block": dict(block, mix=mix) if block else None,
        "items": chosen,
        "pending_errata": st.get("pending_errata") or [],
        "note": "Blind: do not reveal topics, reasons or the drill before all answers are in. The "
                "learner is told the block's theme and position (block.line) and nothing more "
                "specific: never which items are on the theme, nor the domain of any other item. "
                "Make every vignette and stem clearly different from already_used and "
                "recent_cases_any_topic (patient, setting, presentation, twist). MCQs and focused "
                "questions are presented together and get their feedback before the case is shown; "
                "neither they nor their feedback may cue the case.",
    }
    return plan


def plan_summary(plan, out):
    """What plan, start and prepare print about a plan: counts only, never topics."""
    counts = plan["counts"]
    return {"ok": True, "out": out, "items": len(plan["items"]),
            "mcqs": counts["mcqs"], "focused": counts["focused"], "case": counts["case"],
            "case_format": plan["case_format"], "estimated_minutes": plan["estimated_minutes"],
            "item_order": plan["item_order"], "session_id": plan["session_id"],
            "block": (plan.get("block") or {}).get("line")}


# ---------------------------------------------------------------- record

def validate_round(rnd):
    w = []
    for i, it in enumerate(rnd.get("items") or []):
        tag = "item %d (%s %s)" % (i + 1, it.get("type"), it.get("topic"))
        if it.get("type") not in ITEM_TYPES:
            w.append("%s: type must be case, focused or mcq" % tag)
        try:
            m = float(it.get("mastery"))
            if not 0 <= m <= 5:
                w.append("%s: mastery out of range" % tag)
        except (TypeError, ValueError):
            w.append("%s: mastery missing" % tag)
        if it.get("retests") is not None and not isinstance(it["retests"], str):
            w.append("%s: 'retests' must be the id of the gap the item retests" % tag)
        c = it.get("coding")
        if not isinstance(c, dict):
            w.append("%s: coding block missing" % tag)
            continue
        if it.get("type") != "mcq":
            for k, v in (c.get("art") or {}).items():
                if k not in ART_MAX or not isinstance(v, (int, float)) or not 0 <= v <= ART_MAX[k]:
                    w.append("%s: bad ART score %s=%r" % (tag, k, v))
            if not c.get("art"):
                w.append("%s: %s needs ART scores (%s)" % (tag, "focused question" if it.get("type") == "focused"
                                                            else "case", "the domains it tested"
                                                            if it.get("type") == "focused" else "all that apply"))
        if it.get("type") == "focused":
            if c.get("idea"):
                w.append("%s: Revised-IDEA is scored for the case only; drop 'idea'" % tag)
            if it.get("aspect") not in FOCUSED_ASPECTS:
                w.append("%s: focused question needs 'aspect', one of %s" % (tag, ", ".join(FOCUSED_ASPECTS)))
            for k, v in (c.get("idea") or {}).items():
                if k not in IDEA_MAX or not isinstance(v, (int, float)) or not 0 <= v <= IDEA_MAX[k]:
                    w.append("%s: bad Revised-IDEA score %s=%r" % (tag, k, v))
        for e in c.get("errors") or []:
            if e.get("category") not in ERROR_CATEGORIES:
                w.append("%s: error category %r unknown" % (tag, e.get("category")))
            if e.get("category") == "knowledge" and e.get("knowledge_type") not in KNOWLEDGE_TYPES:
                w.append("%s: knowledge error needs knowledge_type" % tag)
            if e.get("severity") not in SEVERITIES:
                w.append("%s: severity %r unknown" % (tag, e.get("severity")))
            if e.get("art_domain") and e["art_domain"] not in ART_MAX:
                w.append("%s: art_domain %r unknown" % (tag, e.get("art_domain")))
            for b in e.get("bias") or []:
                if b not in BIASES and not str(b).startswith("other:"):
                    w.append("%s: bias %r unknown" % (tag, b))
            if e.get("bias") and not e.get("bias_evidence"):
                w.append("%s: a bias needs bias_evidence (the learner's words)" % tag)
        if it.get("type") in ("mcq", "focused") and not it.get("stem_summary"):
            w.append("%s: %s needs stem_summary" % (tag, "MCQ" if it.get("type") == "mcq" else "focused question"))
    if rnd.get("drill") and rnd["drill"].get("result") not in DRILL_RESULTS:
        w.append("drill.result must be one of %s" % (DRILL_RESULTS,))
    for k in ("title", "summary", "tags"):
        if not rnd.get(k):
            w.append("round needs '%s'" % k)
    if sum(1 for it in rnd.get("items") or [] if is_case(it)) > 1:
        w.append("a round has at most one case")
    if not rnd.get("case") and any(is_case(it) for it in rnd.get("items") or []):
        w.append("round needs a compact 'case' description for the novelty index")
    return w


def compact_item(it):
    typ = "case" if is_case(it) else "focused" if it.get("type") == "focused" else "mcq"
    out = {"type": typ, "topic": it.get("topic"),
           "mastery": it.get("mastery"), "confidence": it.get("confidence")}
    if typ == "mcq":
        out["correct"] = it.get("correct")
    if it.get("set_by") == "learner":      # `mastery` is the learner's score, `graded` the examiner's
        out["graded"], out["set_by"] = it.get("graded"), "learner"
    if typ == "focused" and it.get("aspect"):
        out["aspect"] = it["aspect"]
    if it.get("retests"):
        out["retests"] = it["retests"]
    if typ != "case" and (it.get("stem_summary") or it.get("stem")):
        out["stem"] = clip(it.get("stem_summary") or it.get("stem"), 90)
    c = it.get("coding") or {}
    coding = {}
    if c.get("art"):
        coding["art"] = c["art"]
    if c.get("idea"):
        coding["idea"] = c["idea"]
    errs = []
    for e in c.get("errors") or []:
        ce = {"element": clip(e.get("element"), CLIP_ELEMENT), "category": e.get("category"),
              "severity": e.get("severity")}
        for k in ("stage", "knowledge_type", "art_domain", "confidence"):
            if e.get(k) is not None:
                ce[k] = e[k]
        if e.get("bias"):
            ce["bias"] = e["bias"]
            ce["bias_evidence"] = clip(e.get("bias_evidence"), CLIP_EVIDENCE)
        errs.append(ce)
    coding["errors"] = errs
    out["coding"] = coding
    return out


def agg_add_session(agg, s):
    agg["sessions"] += 1
    agg["items"] += len(s.get("items") or [])
    agg["minutes"] += int(s.get("minutes") or 0)
    agg["reading_minutes"] += int(s.get("reading_minutes") or 0)
    agg["mcqs"] += int(s.get("mcqs") or 0)
    agg["mcq_correct"] += int(s.get("mcq_correct") or 0)
    agg.setdefault("focused", 0); agg.setdefault("focused_mastery_sum", 0.0)
    agg.setdefault("art_focused", {k: [0.0, 0] for k in ART_MAX})
    if isinstance(s.get("score"), (int, float)):
        agg["score_sum"] += float(s["score"]); agg["score_n"] += 1
    for it in s.get("items") or []:
        c = it.get("coding") or {}
        if it.get("type") == "focused":
            agg["focused"] += 1
            if isinstance(it.get("mastery"), (int, float)):
                agg["focused_mastery_sum"] += float(it["mastery"])
        # ART from the full case only, so the profile stays comparable across periods;
        # focused questions (which score only the domains they test) are counted apart.
        art_bucket = agg["art_focused"] if it.get("type") == "focused" else agg["art"]
        for k, v in (c.get("art") or {}).items():
            if k in art_bucket and isinstance(v, (int, float)):
                art_bucket[k][0] += float(v) / ART_MAX[k]; art_bucket[k][1] += 1
        idea = c.get("idea") or {}
        if idea and all(isinstance(idea.get(k), (int, float)) for k in IDEA_MAX):
            tot = sum(idea[k] for k in IDEA_MAX)
            agg["idea"][0] += tot; agg["idea"][1] += 1; agg["idea"][2] += 1 if tot >= 6 else 0
        for e in c.get("errors") or []:
            for key in ("category", "knowledge_type", "art_domain", "severity"):
                v = e.get(key)
                if v:
                    agg["errors"][key][v] = agg["errors"][key].get(v, 0) + 1
            for b in e.get("bias") or []:
                agg["errors"]["bias"][b] = agg["errors"]["bias"].get(b, 0) + 1
        conf = (it.get("confidence") or "").lower()
        out = item_outcome(it)
        if conf in CONF_PROB and out is not None:
            agg["calibration"][conf][0] += 1; agg["calibration"][conf][1] += out
            agg["brier"][0] += (CONF_PROB[conf] - out) ** 2; agg["brier"][1] += 1
    d = s.get("drill")
    if isinstance(d, dict) and d.get("result") in DRILL_RESULTS:
        agg["drills"][d["result"]] += 1
    for g in s.get("grade_changes") or []:
        if g.get("outcome") in agg["disputes"]:
            agg["disputes"][g["outcome"]] += 1
        elif g.get("outcome") in LEARNER_SET_OUTCOMES:
            agg_overrides(agg)["scores"] += 1
    if (s.get("reflection") or {}).get("skipped"):
        agg["reflection_skipped"] += 1


def apply_round(state, rnd, today, theme=None):
    """Pure application of a graded round to the state; `theme` is the theme of the block the
    round was recorded in. Returns (entry, summary, warnings, errata_ids)."""
    if not rnd.get("items"):
        die("round JSON must contain a non-empty 'items' list")
    warnings = validate_round(rnd)
    rdate = parse_date(rnd.get("date")) or today
    cfg = state["config"]
    intervals = [int(x) for x in cfg.get("intervals_days") or DEFAULT_CONFIG["intervals_days"]]
    refl = rnd.get("reflection") or {}
    comfort_map = refl.get("topic_comfort") or {}

    by_topic = {}
    for it in rnd["items"]:
        tid = it.get("topic")
        if not tid:
            die("every item needs a 'topic' id")
        conf = it.get("confidence")
        if conf and str(conf).lower() not in CONFIDENCE_LEVELS:
            die("confidence must be one of %s" % (CONFIDENCE_LEVELS,))
        by_topic.setdefault(tid, []).append(it)

    gaps_in = list(rnd.get("gaps") or []) + list(refl.get("self_gaps") or [])
    new_gaps_by_topic = {}
    for g in gaps_in:
        if not g.get("topic") or not g.get("gap"):
            die("each gap needs 'topic' and 'gap'")
        new_gaps_by_topic.setdefault(g["topic"], []).append(g)
    self_gap_topics = {g["topic"] for g in gaps_in if g.get("source") == "self"}

    summary = {}
    steps_before = {}       # each topic's step before this round: `override` reschedules from it
    number_gaps(state)
    gap_index = {g.get("topic"): g for g in state["gaps"]}
    for it in rnd["items"]:
        g = gap_index.get(it["topic"])
        if it.get("retests") and (not g or it["retests"] not in (g["id"], it["topic"])):
            warnings.append("%s %s: 'retests' names %s, which is not an open gap on that topic"
                            % (it.get("type"), it["topic"], it["retests"]))
    for tid, items in by_topic.items():
        t = ensure_topic(state, tid, items[0].get("domain"), next((i.get("label") for i in items if i.get("label")), None))
        adj = [adjusted_item_mastery(i) for i in items]
        mastery = round_half(sum(m for m, _ in adj) / len(adj))
        misconception = any(mc for _, mc in adj)
        steps_before[tid] = int(t.get("step") or 0)
        comfort = comfort_map.get(tid)
        try:
            comfort = None if comfort is None else max(1, min(5, int(round(float(comfort)))))
        except (TypeError, ValueError):
            comfort = None
        step, due, calibration, interval = schedule_topic(t.get("step"), mastery, comfort, misconception,
                                                          tid in self_gap_topics, intervals, rdate)
        limited = (not answered_well(mastery, calibration) and interval < DRILLDOWN_PAUSE_DAYS
                   and drilldown_over(state, tid, theme))
        if limited:      # the drill-down on this topic is used up: it comes back later, not next round
            interval, due = DRILLDOWN_PAUSE_DAYS, rdate + dt.timedelta(days=DRILLDOWN_PAUSE_DAYS)
        t.update({"last": iso(rdate), "attempts": int(t.get("attempts") or 0) + 1, "mastery": mastery,
                  "step": step, "due": iso(due), "comfort": comfort, "calibration": calibration})
        t["history"].append([iso(rdate), mastery, comfort, calibration])
        t["history"] = t["history"][-CAP_HISTORY:]
        if misconception and not any(g.get("source") == "misconception" for g in new_gaps_by_topic.get(tid, [])):
            new_gaps_by_topic.setdefault(tid, []).append({
                "topic": tid, "source": "misconception", "auto": True,
                "gap": "Confident but incorrect answer on %s; re-test the same decision point." % iso(rdate)})
        summary[tid] = {"mastery": mastery, "step": step, "due": iso(due), "interval_days": interval,
                        "calibration": calibration, "comfort": comfort, "misconception": misconception}
        if limited:
            summary[tid]["drilldown_limit"] = True

    for tid in [t for t in new_gaps_by_topic if t not in self_gap_topics and t not in by_topic]:
        g0 = new_gaps_by_topic[tid][0]   # e.g. a transfer gap on a topic not tested this round
        ensure_topic(state, tid, g0.get("domain"), g0.get("label"))
    for tid in [t for t in new_gaps_by_topic if t in self_gap_topics and t not in by_topic]:
        g0 = new_gaps_by_topic[tid][0]
        t = ensure_topic(state, tid, g0.get("domain"), g0.get("label"))
        target = rdate + dt.timedelta(days=7)
        cur = parse_date(t.get("due"))
        if cur is None or cur > target:
            t["due"] = iso(target)
        summary[tid] = {"self_reported_only": True, "due": t["due"]}

    resolved_by_topic = {}
    for r in rnd.get("resolved") or []:
        if isinstance(r, str):
            r = {"topic": r, "note": None}
        resolved_by_topic.setdefault(r.get("topic"), []).append(r.get("note"))

    gaps = state["gaps"]
    for tid in list(by_topic) + [t for t in new_gaps_by_topic if t not in by_topic]:
        existing = gap_index.get(tid)
        new = new_gaps_by_topic.get(tid)
        mastery = summary.get(tid, {}).get("mastery")
        cal = summary.get(tid, {}).get("calibration")
        notes = [n for n in resolved_by_topic.get(tid, []) if n]
        # the items of this round that say they test the open gap (by its id; by its topic for a
        # round planned before the gap had an id)
        retests = [i for i in by_topic.get(tid, []) if existing and i.get("retests") in (existing["id"], tid)]
        if existing and tid in by_topic and not retests:
            warnings.append("%s has open gap %s and no item says it retests it; if an item tested that "
                            "point, add \"retests\": \"%s\" to it (the gap stays open otherwise)"
                            % (tid, existing["id"], existing["id"]))
        if new:
            graded = [g["gap"] for g in new if g.get("source") != "self"]
            selfrep = [g["gap"] for g in new if g.get("source") == "self"]
            sources = sorted({g.get("source") or "graded" for g in new})
            gap_text = "; ".join(graded) if graded else "; ".join(selfrep)
            if existing and all(g.get("auto") for g in new if g.get("source") != "self"):
                gap_text = "%s | %s" % (existing.get("gap"), gap_text) if existing.get("gap") else gap_text
                sources = sorted(set(sources) | set(existing.get("source") or []))
            entry = {"topic": tid, "gap": clip(gap_text, CLIP_GAP),
                     "self": clip("; ".join(selfrep), 200) or None, "source": sources,
                     "date": iso(rdate),
                     "opened": (existing or {}).get("opened") or (existing or {}).get("date") or iso(rdate)}
            if existing:
                entry["id"] = existing["id"]
                # a gap written again after its retest has had its one targeted retest
                if tid in by_topic and (retests or not gap_awaits_retest(existing)):
                    entry["last_retested"] = iso(rdate)
                gaps.remove(existing)
            else:
                entry["id"] = "G%04d" % (number_gaps(state) + 1)
            gaps.append(entry); gap_index[tid] = entry
            for n in notes:
                state["resolved"].append({"topic": tid, "note": clip(n, 200), "resolved": iso(rdate), "partial": True})
        elif existing and tid in by_topic:
            ex_date = parse_date(existing.get("date"))
            # A gap closes only on an item that tested that gap and was answered well. A good
            # score on another point of the same topic says nothing about the point that was missed.
            answered = [adjusted_item_mastery(i) for i in retests]
            well = bool(answered) and not any(mc for _, mc in answered) \
                and round_half(sum(m for m, _ in answered) / len(answered)) >= 4
            summary.setdefault(tid, {})["gap_retested"] = bool(retests)
            if well and cal not in ("overconfident", "confident_error") and (ex_date is None or ex_date < rdate):
                gaps.remove(existing); del gap_index[tid]
                state["resolved"].append({"id": existing["id"], "topic": tid, "note": clip(existing.get("gap"), 200),
                                          "opened": existing.get("opened") or existing.get("date"),
                                          "resolved": iso(rdate), "partial": False})
                summary.setdefault(tid, {})["gap_resolved"] = True
            else:
                if retests:
                    existing["last_retested"] = iso(rdate)
                for n in notes:
                    state["resolved"].append({"topic": tid, "note": clip(n, 200), "resolved": iso(rdate), "partial": True})
        elif notes:
            for n in notes:
                state["resolved"].append({"topic": tid, "note": clip(n, 200), "resolved": iso(rdate), "partial": True})

    ratings = state["profile"].setdefault("domain_self_ratings", {})
    for tid, s in summary.items():
        c = s.get("comfort")
        if c is None:
            continue
        d = state["topics"][tid]["domain"]
        prev = ratings.get(d)
        prev = prev.get("rating") if isinstance(prev, dict) else prev
        ratings[d] = c if prev is None else round((2 * float(prev) + c) / 3.0, 1)

    # session entry
    started, ended, minutes = rnd.get("started_at"), rnd.get("ended_at"), rnd.get("minutes")
    if minutes is None and started and ended:
        try:
            a = dt.datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            b = dt.datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
            minutes = max(1, min(180, int(round((b - a).total_seconds() / 60.0))))
        except ValueError:
            minutes = None
    mcq_items = [it for it in rnd["items"] if it.get("type") == "mcq"]
    has_case = any(is_case(it) for it in rnd["items"])
    all_m = [adjusted_item_mastery(it)[0] for it in rnd["items"]]
    sid = rnd.get("log_id") or rnd.get("id") or state["next_id"]
    if any(x.get("id") == sid for x in state["sessions"] + state["previous"]):
        die("session id %s is already recorded" % sid)
    entry = {
        "id": sid, "date": iso(rdate), "started_at": started, "ended_at": ended, "minutes": minutes,
        "reading_minutes": refl.get("reading_minutes", rnd.get("reading_minutes")),
        "title": clip(rnd.get("title"), 120), "summary": clip(rnd.get("summary"), 300),
        "tags": rnd.get("tags") or [], "topics": list(by_topic.keys()),
        "format": rnd.get("case_format") if has_case else None, "mcqs": len(mcq_items),
        "mcq_correct": sum(1 for it in mcq_items if it.get("correct") is True),
        "focused": sum(1 for it in rnd["items"] if it.get("type") == "focused"),
        "score": round(sum(all_m) / len(all_m), 2),
        "items": [compact_item(it) for it in rnd["items"]],
        "why": rnd.get("selection_reasons") or {},
        "self_performance": refl.get("performance"),
        "self_comfort": {k: v for k, v in comfort_map.items()},
        "reflection": {"solid": clip(refl.get("solid"), 300), "gaps": clip(refl.get("gaps"), 300),
                       "skipped": bool(refl.get("skipped"))} if rnd.get("reflection") is not None else None,
        "key_learning": [clip(k, 200) for k in rnd.get("key_learning") or []],
        "case": {k: clip(rnd["case"].get(k), 80) for k in ("patient", "setting", "presentation", "diagnosis", "twist")
                 if rnd["case"].get(k)} if rnd.get("case") and has_case else None,
        "grade_changes": rnd.get("grade_changes") or [],
        "drill": rnd.get("drill"),
        "steps_before": steps_before,
    }
    if entry["case"] is not None:
        entry["case"]["topic"] = next((it["topic"] for it in rnd["items"] if is_case(it)), None)

    # errata
    errata_ids = []
    n = max([id_num(e.get("id")) for e in state["errata"] + state["pending_errata"]] + [0]) + 1
    for e in rnd.get("errata") or []:
        if not e.get("corrects") or not e.get("correction"):
            die("each erratum needs 'corrects' (session id) and 'correction'")
        e = dict(e, id="E%04d" % n, found=e.get("found") or iso(rdate), logged_in=sid)
        n += 1
        state["errata"].append(e); errata_ids.append(e["id"])
    wanted = rnd.get("pending_errata_logged") or []
    if wanted == "all":
        wanted = [e.get("id") for e in state["pending_errata"]]
    for eid in wanted:
        hit = next((e for e in state["pending_errata"] if e.get("id") == eid), None)
        if not hit:
            warnings.append("pending erratum %s not found" % eid)
            continue
        state["pending_errata"].remove(hit)
        state["errata"].append(dict(hit, logged_in=sid)); errata_ids.append(eid)
    if errata_ids:
        entry["errata"] = errata_ids

    state["sessions"].append(entry)
    agg_add_session(state["agg"], entry)
    state["next_id"] = "S%04d" % (max(id_num(sid), id_num(state["next_id"]) - 1) + 1)
    state["updated"] = iso(today)
    return entry, summary, warnings, errata_ids


def snapshot(state):
    """What apply_round changes, kept so `reflect` can re-apply the round with the reflection."""
    return {"topics": json.loads(json.dumps(state["topics"])), "gaps": json.loads(json.dumps(state["gaps"])),
            "resolved": json.loads(json.dumps(state["resolved"])), "agg": json.loads(json.dumps(state["agg"])),
            "ratings": json.loads(json.dumps(state["profile"].get("domain_self_ratings") or {})),
            "errata": json.loads(json.dumps(state["errata"])),
            "pending_errata": json.loads(json.dumps(state["pending_errata"])),
            "next_id": state["next_id"]}


def restore(state, snap):
    state["topics"], state["gaps"], state["resolved"], state["agg"] = snap["topics"], snap["gaps"], snap["resolved"], snap["agg"]
    state["profile"]["domain_self_ratings"] = snap["ratings"]
    state["errata"], state["pending_errata"], state["next_id"] = snap["errata"], snap["pending_errata"], snap["next_id"]


def compact(state):
    s = state
    for g in s.get("gaps") or []:      # repair: every open gap belongs to a known topic
        if g.get("topic") and g["topic"] not in s["topics"]:
            ensure_topic(s, g["topic"])
    while len(s["sessions"]) > CAP_SESSIONS:
        s["previous"].append(to_previous(s["sessions"].pop(0)))
    s["previous"] = s["previous"][-CAP_PREVIOUS:]
    s["resolved"] = s["resolved"][-CAP_RESOLVED:]
    s["reviews"] = s["reviews"][-CAP_REVIEWS:]
    s["errata"] = s["errata"][-CAP_ERRATA:]
    for t in s["topics"].values():
        t["history"] = (t.get("history") or [])[-CAP_HISTORY:]


def to_previous(sess):
    """Compact form of a session for the previous-period list: coding without free text."""
    items = []
    for it in sess.get("items") or []:
        c = it.get("coding") or {}
        ci = {"type": it.get("type"), "topic": it.get("topic"), "mastery": it.get("mastery"),
              "confidence": it.get("confidence")}
        if it.get("type") == "mcq":
            ci["correct"] = it.get("correct")
        if it.get("set_by") == "learner":
            ci["graded"], ci["set_by"] = it.get("graded"), "learner"
        if it.get("type") == "focused" and it.get("aspect"):
            ci["aspect"] = it["aspect"]
        cc = {}
        if c.get("art"):
            cc["art"] = c["art"]
        if c.get("idea"):
            cc["idea"] = c["idea"]
        cc["errors"] = [{k: e.get(k) for k in ("category", "knowledge_type", "art_domain", "severity", "bias") if e.get(k)}
                        for e in c.get("errors") or []]
        ci["coding"] = cc
        items.append(ci)
    out = {"id": sess.get("id"), "date": sess.get("date"), "title": sess.get("title"),
           "topics": sess.get("topics"), "score": sess.get("score"), "minutes": sess.get("minutes"),
           "mcqs": sess.get("mcqs"), "mcq_correct": sess.get("mcq_correct"), "focused": sess.get("focused") or 0,
           "format": sess.get("format"), "items": items,
           "drill": sess.get("drill"), "grade_changes": [{k: g.get(k) for k in ("outcome", "from", "to") if g.get(k) is not None}
                             for g in sess.get("grade_changes") or []],
           "reflection": {"skipped": bool((sess.get("reflection") or {}).get("skipped"))}}
    if sess.get("case"):
        out["case"] = {k: sess["case"].get(k) for k in ("topic", "presentation", "diagnosis") if sess["case"].get(k)}
    if sess.get("url"):
        out["url"] = sess["url"]
    if sess.get("block"):
        out["block"] = sess["block"]
    if sess.get("learner_closed_gaps"):
        out["learner_closed_gaps"] = sess["learner_closed_gaps"]
    return out


def record_round(st, rnd, today):
    """Apply the graded round `rnd` to ledger `st` (changed in place; `rnd` may be changed too).
    Returns what record and save report about it."""
    if not rnd.get("date"):     # the round is dated when it is recorded; reflecting later keeps that date
        rnd["date"] = iso(today)
    # finalize a still-unreflected earlier session: it stays recorded with the reflection skipped
    if st.get("unreflected"):
        for s in st["sessions"]:
            if s.get("id") == st["unreflected"]:
                s.pop("_snapshot", None); s.pop("_round", None)
                if s.get("reflection") is None:
                    s["reflection"] = {"skipped": True}
                    st["agg"]["reflection_skipped"] += 1
        st["unreflected"] = None
    for k in ("helpers", "prepare_ahead"):       # speed settings (4.3): on unless the learner turns them off
        st["config"].setdefault(k, DEFAULT_CONFIG[k])
    # The round counts in its block here, once: reflecting later re-applies the round, not this.
    in_block = advance_block(st, parse_date(rnd.get("date")) or today)
    snap = snapshot(st)
    entry, summary, warnings, errata_ids = apply_round(st, rnd, today, (in_block or {}).get("theme"))
    if in_block:
        entry["block"] = in_block
    if rnd.get("reflection") is None:
        entry["_snapshot"] = snap
        entry["_round"] = rnd
        st["unreflected"] = entry["id"]
    compact(st)
    bump_gen(st)
    return {"gen": st["gen"], "session_id": entry["id"],
            "next_id": st["next_id"], "score": entry["score"], "topics": summary,
            "errata_ids": errata_ids,
            "errata_to_log": [e for e in st["errata"] if e.get("id") in errata_ids],
            "open_gaps": len(st["gaps"]), "reflection_pending": rnd.get("reflection") is None,
            "warnings": warnings}


def report(out, size, result):
    """The printed result of a command that wrote the ledger: ok, out and bytes first."""
    return dict({"ok": True, "out": out, "bytes": size}, **result)


def reflect_round(st, refl, today, session=None):
    """Apply the reflection `refl` to the unreflected session of ledger `st` (or to `session`),
    changing `st` in place. Returns what reflect and close report about it."""
    sid = session or st.get("unreflected")
    sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
    if not sess or not sess.get("_snapshot"):
        die("no unreflected session to update (last: %s)" % (st["sessions"][-1].get("id") if st["sessions"] else None))
    snap, rnd = sess["_snapshot"], sess["_round"]
    st["sessions"].remove(sess)
    restore(st, snap)
    st["agg"]["sessions"] -= 0  # agg was restored from the snapshot
    rnd = dict(rnd, reflection=refl)
    for k in ("grade_changes", "errata", "key_learning", "resolved"):
        if refl.get(k):
            rnd[k] = list(rnd.get(k) or []) + list(refl[k])
    if refl.get("items"):   # grade changes expressed as new item scores
        by = {(i.get("type"), i.get("topic")): i for i in rnd["items"]}
        for ch in refl["items"]:
            it = by.get((ch.get("type"), ch.get("topic")))
            if it:
                it.update({k: v for k, v in ch.items() if k not in ("type", "topic")})
    # what the learner set themselves: after any dispute, so `graded` is the examiner's last word
    rdate = iso(parse_date(rnd.get("date")) or today)
    changes = []
    for req in refl.get("learner_scores") or []:
        ch = learner_score(find_item(rnd["items"], req, sid), req, rdate)
        rnd["grade_changes"] = list(rnd.get("grade_changes") or []) + [ch.pop("grade_change")]
        changes.append(ch)
    entry, summary, warnings, errata_ids = apply_round(st, rnd, today, (sess.get("block") or {}).get("theme"))
    if sess.get("block"):
        entry["block"] = sess["block"]
    for req in refl.get("learner_closed_gaps") or []:      # after the round: a gap it opened can be closed too
        ch = learner_close_gap(st, req, rdate, entry)
        summary.setdefault(ch["topic"], {})["gap_closed_by_learner"] = True
        changes.append(ch)
    st["unreflected"] = None
    compact(st)
    bump_gen(st)
    out = {"gen": st["gen"], "session_id": entry["id"],
           "topics": summary, "open_gaps": len(st["gaps"]), "errata_ids": errata_ids,
           "errata_to_log": [e for e in st["errata"] if e.get("id") in errata_ids],
           "warnings": warnings}
    if changes:
        out["learner_changes"] = changes
    return out


# ---------------------------------------------------------------- what the learner sets themselves

def find_item(items, req, sid):
    """The item of a round a learner-set score names: by topic, and by type where the round has
    more than one item on that topic."""
    if not isinstance(req, dict) or not req.get("topic"):
        die("a learner-set score needs 'topic' (and 'type' when the round has two items on it) and 'score'")
    typ = "case" if req.get("type") == "essay" else req.get("type")
    hits = [i for i in items if i.get("topic") == req["topic"]
            and (not typ or ("case" if is_case(i) else i.get("type")) == typ)]
    if len(hits) != 1:
        die("learner-set score: %s in round %s (items: %s)"
            % ("no item %s%s" % (typ + " " if typ else "", req["topic"]) if not hits
               else "%d items on %s, name the 'type'" % (len(hits), req["topic"]), sid,
               ", ".join("%s %s" % (i.get("type"), i.get("topic")) for i in items)))
    return hits[0]


def learner_score(it, req, date):
    """Set the score of item `it` to the learner's own. `mastery` becomes the learner's score
    (the one scheduling uses), `graded` keeps the examiner's, `set_by` says whose `mastery` is.
    Returns the change for the log, with the `grade_change` entry for the ledger."""
    try:
        score = float(req.get("score"))
    except (TypeError, ValueError):
        score = -1.0
    if not 0 <= score <= 5:
        die("learner-set score for %s: 'score' must be a number from 0 to 5" % req.get("topic"))
    score = int(score) if score == int(score) else score
    graded = it.get("graded") if it.get("set_by") == "learner" else it.get("mastery")
    it.update({"mastery": score, "graded": graded, "set_by": "learner"})
    label = req.get("item") or "%s %s" % ("case" if is_case(it) else it.get("type"), it.get("topic"))
    note = clip(req.get("note"), 200)
    gc = {"item": label, "topic": it.get("topic"), "from": graded, "to": score, "outcome": LEARNER_SET,
          "examiner": graded, "learner": score, "date": date}
    if note:
        gc["note"] = note
    return {"kind": "score", "item": label, "topic": it.get("topic"), "examiner": graded, "learner": score,
            "set_by": "learner", "date": date, "note": note, "grade_change": gc}


def learner_close_gap(st, req, date, sess=None, sid=None):
    """Close an open gap because the learner asked: it moves to `resolved` marked
    `closed_by: learner`, and no retest follows (the topic keeps the due date its score gave
    it). `req` names the gap by id or by topic. Returns the change for the log."""
    if isinstance(req, str):
        req = {"gap": req}
    ref = (req or {}).get("gap") or (req or {}).get("id") or (req or {}).get("topic")
    g = next((x for x in st["gaps"] if ref and ref in (x.get("id"), x.get("topic"))), None)
    if not g:
        die("no open gap %s to close (open: %s)"
            % (ref, ", ".join("%s %s" % (x.get("id"), x.get("topic")) for x in st["gaps"]) or "none"))
    st["gaps"].remove(g)
    note = clip(req.get("note"), 200)
    sid = (sess or {}).get("id") or sid
    st["resolved"].append({"id": g.get("id"), "topic": g.get("topic"), "note": clip(g.get("gap"), 200),
                           "opened": g.get("opened") or g.get("date"), "resolved": date, "partial": False,
                           "closed_by": "learner", "learner_note": note, "session": sid})
    agg_overrides(st["agg"])["gaps"] += 1
    if sess is not None:
        sess.setdefault("learner_closed_gaps", []).append({"id": g.get("id"), "topic": g.get("topic")})
    return {"kind": "gap", "gap": g.get("id"), "topic": g.get("topic"), "text": clip(g.get("gap"), 200),
            "closed_by": "learner", "date": date, "note": note}


def reschedule_topic(st, sess, tid):
    """After a score of the closed round `sess` changed: schedule topic `tid` again from that
    round, as `close` would have with the new score. Returns the topic's new line for the
    report, or None when the topic has been tested again since (its schedule is then left as
    that later round set it)."""
    t = st["topics"].get(tid)
    hist = (t or {}).get("history") or []
    if not t or t.get("last") != sess.get("date") or not hist or hist[-1][0] != sess.get("date"):
        return None
    adj = [adjusted_item_mastery(i) for i in sess.get("items") or [] if i.get("topic") == tid]
    mastery = round_half(sum(m for m, _ in adj) / len(adj))
    misconception = any(mc for _, mc in adj)
    intervals = [int(x) for x in st["config"].get("intervals_days") or DEFAULT_CONFIG["intervals_days"]]
    comfort = hist[-1][2]
    before = (sess.get("steps_before") or {}).get(tid)
    self_gap = any(g.get("topic") == tid and "self" in (g.get("source") or []) for g in st["gaps"])
    step, due, calibration, interval = schedule_topic(t.get("step") if before is None else before, mastery, comfort,
                                                      misconception, self_gap, intervals, parse_date(sess["date"]))
    t.update({"mastery": mastery, "step": step, "due": iso(due), "calibration": calibration})
    hist[-1] = [sess["date"], mastery, comfort, calibration]
    return {"mastery": mastery, "step": step, "due": iso(due), "interval_days": interval, "calibration": calibration}


def learner_changes_md(changes, heading):
    """The learner's own changes as they are written into the session document."""
    lines = []
    for c in changes:
        if c["kind"] == "score":
            line = ("- %s (%s): the examiner's score %s, the learner's score %s. Recorded and scheduled with "
                    "the learner's score, at the learner's request."
                    % (c["item"], c["topic"], c["examiner"], c["learner"]))
        else:
            line = ("- Gap %s (%s) closed by the learner, not by a retest: %s"
                    % (c["gap"], c["topic"], c.get("text") or ""))
        lines.append(line + (" Learner's note: %s" % c["note"] if c.get("note") else ""))
    return "%s\n\n%s\n" % (heading, "\n".join(lines))


def cmd_override(args):
    """After the close: the learner sets a score of a closed round themselves (--scores) or
    closes a gap by request (--close-gaps). The ledger, the session document (its
    `learner_changes` and a line in the addendum) and the page file go into the publish set.
    Before the close both belong in the reflection JSON (`learner_scores`,
    `learner_closed_gaps`), which `close` handles the same way."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    scores = (load_json_arg(args.scores) if args.scores else None) or []
    closes = (load_json_arg(args.close_gaps) if args.close_gaps else None) or []
    scores, closes = ([x] if isinstance(x, (dict, str)) else list(x) for x in (scores, closes))
    if not scores and not closes:
        die("override needs --scores '[{\"topic\": …, \"score\": N}]' or --close-gaps '[{\"gap\": \"G0007\"}]'")
    if st.get("unreflected"):
        die("round %s is not closed yet: put `learner_scores` and `learner_closed_gaps` in its reflection "
            "JSON and run close (`{\"skipped\": true}` with them when there is no reflection)" % st["unreflected"])
    sid = job_session(work, info, st, args.session)
    sess = next((x for x in st["sessions"] if x.get("id") == sid), None)
    if not sess and scores:
        die("round %s is %s: its scores can no longer be changed (a note can still be added with addendum)"
            % (sid, "from before the last progress review" if has_session(st, sid) else "not in the ledger"))
    doc_path = store_file(work, info, session_path(sid))
    if not doc_path:
        die("the session file of %s was not found: read %s from the store into the store copy "
            "(%s) first" % (sid, session_path(sid), info.get("store")))
    doc = load_json(doc_path)
    changes, topics, warnings = [], {}, []
    for req in scores:
        it = find_item(sess["items"], req, sid)
        old = adjusted_item_mastery(it)[0]
        ch = learner_score(it, req, iso(today))
        sess["grade_changes"] = list(sess.get("grade_changes") or []) + [ch.pop("grade_change")]
        agg_overrides(st["agg"])["scores"] += 1
        if it.get("type") == "focused":
            st["agg"]["focused_mastery_sum"] = st["agg"].get("focused_mastery_sum", 0.0) + float(it["mastery"]) - float(old)
        changes.append(ch)
        line = reschedule_topic(st, sess, it["topic"])
        if line:
            topics[it["topic"]] = line
        else:
            warnings.append("%s has been tested again since %s: the score is recorded, its schedule is "
                            "left as the later round set it" % (it["topic"], sid))
    if scores:
        all_m = [adjusted_item_mastery(i)[0] for i in sess["items"]]
        new = round(sum(all_m) / len(all_m), 2)
        if isinstance(sess.get("score"), (int, float)):
            st["agg"]["score_sum"] += new - float(sess["score"])
        sess["score"] = doc["score"] = new
    for req in closes:
        ch = learner_close_gap(st, req, iso(today), sess, sid)
        topics.setdefault(ch["topic"], {})["gap_closed_by_learner"] = True
        changes.append(ch)
    doc["learner_changes"] = list(doc.get("learner_changes") or []) + changes
    doc["addendum"] = ((doc.get("addendum") or "").rstrip() + "\n\n"
                       + learner_changes_md(changes, "## Set by the learner · %s" % iso(today))).strip() + "\n"
    compact(st)
    # never content-neutral: a learner-set score moves the topic's step and due date, a closed gap
    # takes its retest out of the plan, so a round prepared before this was planned on other facts
    bump_gen(st)
    st["updated"] = iso(today)
    out = {"ok": True, "gen": st["gen"], "session": sid, "learner_changes": changes, "topics": topics,
           "open_gaps": len(st["gaps"]), "warnings": warnings}
    if scores:
        out["score"] = sess["score"]
    # the prepared round was planned with the gap open and the old due date
    publish_ledger(work, info, st, out, session=doc, empty_prepared=True)
    # close cannot be run again from the ledger it started from: that would drop this change
    if os.path.isfile(os.path.join(work, BEFORE_CLOSE_FILE)):
        os.remove(os.path.join(work, BEFORE_CLOSE_FILE))
    print(json.dumps(published(work, info, out), indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- stats

def coding_analytics(log):
    items = [(s, it) for s in log for it in (s.get("items") or [])]
    coded = [(s, it, it.get("coding")) for s, it in items if it.get("coding")]
    art = {k: {"n": 0, "sum": 0.0, "scores": {}} for k in ART_MAX}
    art_f = {k: {"n": 0, "sum": 0.0, "scores": {}} for k in ART_MAX}
    idea_tot, idea_dom, errs = [], {k: [] for k in IDEA_MAX}, []
    for s, it, c in coded:
        bucket = art_f if it.get("type") == "focused" else art
        for k, v in (c.get("art") or {}).items():
            if k in bucket and isinstance(v, (int, float)):
                bucket[k]["n"] += 1; bucket[k]["sum"] += float(v) / ART_MAX[k]
                bucket[k]["scores"][str(v)] = bucket[k]["scores"].get(str(v), 0) + 1
        idea = c.get("idea") or {}
        if idea and all(isinstance(idea.get(k), (int, float)) for k in IDEA_MAX):
            idea_tot.append(sum(idea[k] for k in IDEA_MAX))
            for k in IDEA_MAX:
                idea_dom[k].append(idea[k])
        for e in c.get("errors") or []:
            errs.append(dict(e, id=s.get("id"), date=s.get("date"), topic=it.get("topic"), item_type=it.get("type")))

    def count(key, multi=False):
        out = {}
        for e in errs:
            vals = e.get(key) or []
            for v in (vals if multi else [vals]):
                if v:
                    out.setdefault(v, []).append(e.get("id"))
        return {k: {"n": len(v), "sessions": sorted(set(x for x in v if x), key=id_num)}
                for k, v in sorted(out.items(), key=lambda kv: -len(kv[1]))}

    table, brier, exp_all, obs_all = {}, [], [], []
    for s, it in items:
        conf = (it.get("confidence") or "").lower()
        out = item_outcome(it)
        if conf in CONF_PROB and out is not None:
            row = table.setdefault(conf, {"n": 0, "expected": CONF_PROB[conf], "obs_sum": 0.0})
            row["n"] += 1; row["obs_sum"] += out
            brier.append((CONF_PROB[conf] - out) ** 2); exp_all.append(CONF_PROB[conf]); obs_all.append(out)
    for row in table.values():
        row["observed"] = round(row.pop("obs_sum") / row["n"], 2)
        row["gap"] = round(row["expected"] - row["observed"], 2)
    drills = [s.get("drill") for s in log if isinstance(s.get("drill"), dict)]
    gch = [g for s in log for g in (s.get("grade_changes") or [])]
    own = [g for g in gch if g.get("outcome") in LEARNER_SET_OUTCOMES]
    disputes = [g for g in gch if g.get("outcome") not in LEARNER_SET_OUTCOMES]
    shifts = [g for g in own if all(isinstance(g.get(k), (int, float)) for k in ("from", "to"))]
    scores = [s.get("score") for s in log if isinstance(s.get("score"), (int, float))]
    return {
        "sessions": len(log), "items": len(items), "items_coded": len(coded),
        "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
        "art_domains": {k: {"label": ART_LABELS[k], "n": v["n"],
                            "mean_fraction_of_max": round(v["sum"] / v["n"], 2) if v["n"] else None,
                            "score_counts": v["scores"]} for k, v in art.items()},
        "art_domains_focused": {k: {"n": v["n"], "mean_fraction_of_max": round(v["sum"] / v["n"], 2) if v["n"] else None}
                                for k, v in art_f.items() if v["n"]},
        "items_by_type": {t: sum(1 for _, i in items if (i.get("type") == t or (t == "case" and is_case(i))))
                          for t in ("case", "focused", "mcq")},
        "revised_idea": {"n": len(idea_tot),
                         "mean_total": round(sum(idea_tot) / len(idea_tot), 2) if idea_tot else None,
                         "share_high_quality": round(sum(1 for t in idea_tot if t >= 6) / len(idea_tot), 2) if idea_tot else None,
                         "domain_means": {k: round(sum(v) / len(v), 2) if v else None for k, v in idea_dom.items()}},
        "errors": {"total": len(errs), "per_session": round(len(errs) / len(log), 2) if log else None,
                   "by_category": count("category"), "by_knowledge_type": count("knowledge_type"),
                   "by_reasoning_step": count("art_domain"), "by_severity": count("severity"),
                   "by_bias": count("bias", multi=True),
                   "critical": [{"id": e["id"], "topic": e["topic"], "element": e.get("element")}
                                for e in errs if e.get("severity") == "critical"],
                   "with_bias_evidence": [{"id": e["id"], "topic": e["topic"], "bias": e.get("bias"),
                                           "evidence": e.get("bias_evidence")} for e in errs if e.get("bias")]},
        "confidence_calibration": {
            "table": table, "brier_score": round(sum(brier) / len(brier), 3) if brier else None,
            "overconfidence_index": round(sum(exp_all) / len(exp_all) - sum(obs_all) / len(obs_all), 2) if obs_all else None,
            "items_with_confidence": len(brier)},
        "reflection_skipped_share": round(sum(1 for s in log if (s.get("reflection") or {}).get("skipped")) / len(log), 2) if log else None,
        "drills": {"n": len(drills), "results": {r: sum(1 for d in drills if d.get("result") == r) for r in DRILL_RESULTS},
                   "by_code": {c: [d.get("result") for d in drills if d.get("code") == c]
                               for c in sorted({d.get("code") for d in drills if d.get("code")})}},
        "grade_disputes": {"n": len(disputes), "outcomes": {o: sum(1 for g in disputes if g.get("outcome") == o)
                                                            for o in DISPUTE_OUTCOMES}},
        # what the learner set themselves: not disputes, the examiner's grading did not change
        "learner_overrides": {
            "scores": len(own),
            "mean_change": round(sum(g["to"] - g["from"] for g in shifts) / len(shifts), 2) if shifts else None,
            "gaps_closed": sum(len(s.get("learner_closed_gaps") or []) for s in log)},
    }


def agg_analytics(agg):
    cal = {k: {"n": v[0], "expected": CONF_PROB[k], "observed": round(v[1] / v[0], 2) if v[0] else None}
           for k, v in agg["calibration"].items() if v[0]}
    return {
        "sessions": agg["sessions"], "items": agg["items"],
        "mean_score": round(agg["score_sum"] / agg["score_n"], 2) if agg["score_n"] else None,
        "minutes": agg["minutes"], "reading_minutes": agg["reading_minutes"],
        "mcq_accuracy": round(agg["mcq_correct"] / agg["mcqs"], 2) if agg["mcqs"] else None,
        "focused": agg.get("focused", 0),
        "focused_mean_mastery": round(agg.get("focused_mastery_sum", 0.0) / agg["focused"], 2) if agg.get("focused") else None,
        "art_domains_focused": {k: {"n": v[1], "mean_fraction_of_max": round(v[0] / v[1], 2)}
                                for k, v in (agg.get("art_focused") or {}).items() if v[1]},
        "art_domains": {k: {"label": ART_LABELS[k], "n": v[1], "mean_fraction_of_max": round(v[0] / v[1], 2) if v[1] else None}
                        for k, v in agg["art"].items()},
        "revised_idea": {"n": agg["idea"][1], "mean_total": round(agg["idea"][0] / agg["idea"][1], 2) if agg["idea"][1] else None,
                         "share_high_quality": round(agg["idea"][2] / agg["idea"][1], 2) if agg["idea"][1] else None},
        "errors": agg["errors"],
        "confidence_calibration": {"table": cal, "brier_score": round(agg["brier"][0] / agg["brier"][1], 3) if agg["brier"][1] else None,
                                   "items_with_confidence": agg["brier"][1]},
        "drills": agg["drills"], "grade_disputes": agg["disputes"],
        "learner_overrides": {"scores": agg_overrides(agg)["scores"], "gaps_closed": agg_overrides(agg)["gaps"]},
        "reflection_skipped": agg["reflection_skipped"],
    }


def cmd_stats(args):
    today = today_from(args)
    st, _ = current_ledger(*job(args))
    cfg, prof, rv = st["config"], st["profile"], st.get("review") or {}
    log = st["sessions"]
    start = parse_date(rv.get("period_start")) or parse_date(st.get("created"))
    days = max(1, (today - start).days + 1) if start else None
    weeks = days / 7.0 if days else None
    minutes = [s.get("minutes") for s in log if isinstance(s.get("minutes"), (int, float))]
    reading = [s.get("reading_minutes") for s in log if isinstance(s.get("reading_minutes"), (int, float))]
    mcq_total = sum(int(s.get("mcqs") or 0) for s in log)
    mcq_correct = sum(int(s.get("mcq_correct") or 0) for s in log)
    focused_m = [float(it.get("mastery") or 0) for s in log for it in s.get("items") or [] if it.get("type") == "focused"]
    period_ids = {s.get("id") for s in log}
    per_domain, calib = {}, {}
    improved, declined = [], []
    for tid, t in st["topics"].items():
        hist = [h for h in t.get("history") or [] if parse_date(h[0]) and start and parse_date(h[0]) >= start]
        if hist:
            d = t.get("domain") or domain_of(tid)
            dd = per_domain.setdefault(d, {"topics": 0, "attempts": 0, "mastery_sum": 0.0})
            dd["topics"] += 1; dd["attempts"] += len(hist); dd["mastery_sum"] += float(hist[-1][1] or 0)
            for h in hist:
                calib[h[3] or "not_rated"] = calib.get(h[3] or "not_rated", 0) + 1
        full = t.get("history") or []
        if len(full) >= 2 and full[0][1] is not None and full[-1][1] is not None:
            if full[-1][1] - full[0][1] >= 1.5:
                improved.append({"topic": tid, "from": full[0][1], "to": full[-1][1]})
            elif full[0][1] - full[-1][1] >= 1.5:
                declined.append({"topic": tid, "from": full[0][1], "to": full[-1][1]})
    for v in per_domain.values():
        v["mean_latest_mastery"] = round(v.pop("mastery_sum") / v["topics"], 2)
    perf = [s.get("self_performance") for s in log if isinstance(s.get("self_performance"), (int, float))]
    scores = [s.get("score") for s in log if isinstance(s.get("score"), (int, float))]
    long_open = [g for g in st["gaps"] if parse_date(g.get("opened") or g.get("date"))
                 and (today - parse_date(g.get("opened") or g.get("date"))).days >= 60]
    conf_err = {tid: n for tid, t in st["topics"].items()
                for n in [sum(1 for h in t.get("history") or [] if h[3] == "confident_error")] if n >= 2}
    learning = [{"id": s.get("id"), "n": i + 1, "date": s.get("date"), "point": k}
                for s in log for i, k in enumerate(s.get("key_learning") or [])]
    checks = st.get("teaching_point_checks") or {}
    unchecked = [p for p in learning if "%s.%s" % (p["id"], p["n"]) not in checks]
    blind = []
    named = " ".join(((s.get("reflection") or {}).get("gaps") or "") for s in log).lower()
    for g in st["gaps"]:
        lbl = (st["topics"].get(g["topic"]) or {}).get("label") or ""
        if "self" not in (g.get("source") or []) and not (significant_tokens(lbl) & set(re.findall(r"[a-z]{5,}", named))):
            blind.append({"topic": g["topic"], "label": lbl, "gap": g.get("gap")})
    in_period = [g for g in st["resolved"] if parse_date(g.get("resolved")) and start and parse_date(g["resolved"]) >= start]
    out = {
        "ok": True, "period_start": iso(start), "period_end": iso(today), "sessions": len(log),
        "sessions_per_week": round(len(log) / weeks, 2) if weeks else None,
        "target_sessions_per_week": cfg.get("target_sessions_per_week"),
        "minutes_recorded": sum(minutes), "sessions_without_timing": len(log) - len(minutes),
        "estimated_total_minutes": sum(minutes) + (len(log) - len(minutes)) * int(cfg.get("session_minutes") or 20),
        "reading_minutes_reported": sum(reading),
        "items": {"cases": sum(1 for s in log for it in s.get("items") or [] if is_case(it)),
                  "focused": len(focused_m),
                  "focused_mean_mastery": round(sum(focused_m) / len(focused_m), 2) if focused_m else None,
                  "mcqs": mcq_total, "mcq_correct": mcq_correct,
                  "mcq_accuracy": round(mcq_correct / mcq_total, 2) if mcq_total else None},
        "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
        "mean_self_performance": round(sum(perf) / len(perf), 2) if perf else None,
        "per_domain": per_domain,
        "domains_not_covered": sorted(d for d in bp_weights(st) if d not in per_domain),
        "calibration_counts": calib, "topics_improved": improved, "topics_declined": declined,
        "gaps_resolved": [g for g in in_period if g.get("closed_by") != "learner"],
        "gaps_closed_by_learner": [g for g in in_period if g.get("closed_by") == "learner"],
        "open_gaps": st["gaps"], "gaps_open_60_days_or_more": long_open,
        "topics_with_repeated_confident_errors": conf_err,
        "graded_gaps_never_self_reported": blind,
        "key_learning": learning, "teaching_points_unchecked": unchecked,
        "domain_self_ratings": prof.get("domain_self_ratings"), "domain_emphasis": prof.get("domain_emphasis"),
        "goals": prof.get("goals"),
        "analysis": {"period": coding_analytics(log),
                     "previous_period": coding_analytics(st["previous"]) if st["previous"] else None,
                     "all_time": agg_analytics(st["agg"])},
        "period_session_ids": sorted(period_ids, key=id_num),
        "previous_reviews": [{"date": r.get("date"), "doc": r.get("doc"), "headline": r.get("headline"),
                              "change_plan": r.get("change_plan")} for r in st["reviews"]],
        "active_drills": st["drills"], "pending_errata": st["pending_errata"], "errata": st["errata"],
    }
    print(json.dumps(out, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- review, snooze, settings

def cmd_review(args):
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    rv = load_json_arg(args.review) or {}
    prof, cfg = st["profile"], st["config"]
    if rv.get("config_changes"):
        deep_merge(cfg, rv["config_changes"])
    if rv.get("profile_changes"):
        deep_merge(prof, rv["profile_changes"])
    for d, r in (rv.get("domain_self_ratings") or {}).items():
        prof.setdefault("domain_self_ratings", {})[d.upper()] = r
    for d, e in (rv.get("domain_emphasis") or {}).items():
        prof.setdefault("domain_emphasis", {})[d.upper()] = e
    warnings = []
    iv = int(cfg.get("review_interval_days") or 42)
    if not 30 <= iv <= 90:
        warnings.append("review_interval_days %d is outside the recommended 30–90" % iv)
    next_due = today + dt.timedelta(days=iv)
    entry = {"date": iso(today), "doc": rv.get("doc") or rv.get("report_file"),
             "period_start": st["review"].get("period_start"), "sessions": len(st["sessions"]),
             "headline": clip(rv.get("headline") or (rv.get("analysis") or {}).get("headline"), 400),
             "summary": clip(rv.get("summary"), 400), "goals": rv.get("goals"),
             "change_plan": rv.get("change_plan"), "deep_analysis": bool(rv.get("deep_analysis")),
             "learner_feedback": rv.get("learner_feedback"), "config_changes": rv.get("config_changes"),
             "key_figures": rv.get("key_figures") or rv.get("stats")}
    if "drill_targets" in rv:
        drills = []
        for d in rv["drill_targets"] or []:
            if not d.get("code"):
                die("each drill target needs a 'code' such as bias:premature_closure")
            drills.append({"code": d["code"], "description": d.get("description"),
                           "rate": max(0.0, min(1.0, float(d.get("rate", 0.33)))), "set": iso(today),
                           "until": d.get("until") or iso(next_due)})
        st["drills"] = drills
        entry["drill_targets"] = drills
    checks = st.setdefault("teaching_point_checks", {})
    n = max([id_num(e.get("id")) for e in st["errata"] + st["pending_errata"]] + [0]) + 1
    new_errata = []
    for c in rv.get("teaching_point_checks") or []:
        if not c.get("id") or c.get("status") not in ("current", "changed", "superseded", "uncertain"):
            die("teaching_point_checks need 'id' and status current|changed|superseded|uncertain")
        checks[c["id"]] = {"checked": iso(today), "status": c["status"], "note": clip(c.get("note"), 300),
                           "source": clip(c.get("source"), 200)}
        if c["status"] in ("changed", "superseded"):
            e = {"id": "E%04d" % n, "corrects": c["id"].split(".")[0], "point_id": c["id"],
                 "point": clip(c.get("point"), 300), "correction": clip(c.get("note"), 400),
                 "source": clip(c.get("source"), 200), "found": iso(today), "found_at": "review"}
            n += 1
            st["pending_errata"].append(e); checks[c["id"]]["erratum"] = e["id"]; new_errata.append(e["id"])
    entry["errata_found"] = new_errata
    st["reviews"].append(entry)
    # close the period: current sessions become the previous period
    st["previous"] = [to_previous(s) for s in st["sessions"]]
    st["sessions"] = []
    st["unreflected"] = None
    st["review"] = {"last": iso(today), "next_due": iso(next_due), "period_start": iso(today + dt.timedelta(days=1))}
    compact(st)
    bump_gen(st)
    st["updated"] = iso(today)
    out = {"ok": True, "gen": st["gen"], "reviews": len(st["reviews"]),
           "next_review_due": iso(next_due), "drills": st["drills"],
           "pending_errata": [e["id"] for e in st["pending_errata"]], "warnings": warnings}
    path = publish_ledger(work, info, st, out, empty_prepared=True)
    out.update({"out": path, "bytes": os.path.getsize(path)})
    print(json.dumps(published(work, info, out), indent=1, ensure_ascii=False))


def cmd_snooze(args):
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    st["review"]["next_due"] = iso(today + dt.timedelta(days=args.days))
    bump_gen(st, content=False)     # when the review is due does not change a round: the prepared one stays
    st["updated"] = iso(today)
    out = {"ok": True, "gen": st["gen"], "next_review_due": st["review"]["next_due"]}
    publish_ledger(work, info, st, out)
    print(json.dumps(published(work, info, out), ensure_ascii=False))


def changed_keys(before, after):
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def cmd_settings(args):
    """Change settings: the changed ledger goes into the publish set, with the page file and the
    page if it is out of date, so a settings change is one command. A change that can alter
    what a round contains also empties the prepared round; one that cannot (CONTENT_NEUTRAL_*)
    keeps it. `prepared` in the output says which, and why."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    was = copy.deepcopy({k: st.get(k) for k in ("config", "profile", "blueprint")})
    cfg_changes = load_json_arg(args.config) if args.config else {}
    prof_changes = load_json_arg(args.profile) if args.profile else {}
    deep_merge(st["config"], cfg_changes or {})
    deep_merge(st["profile"], prof_changes or {})
    if any(k in (cfg_changes or {}) for k in ("mcqs", "focused", "case")):
        check_round_mix(st["config"])
        if "round_set_at" not in cfg_changes:
            st["config"]["round_set_at"] = now_ts()   # a new value: any earlier page setting is now superseded
    if "review_interval_days" in (cfg_changes or {}):
        anchor = parse_date(st["review"].get("last")) or parse_date(st["review"].get("period_start")) or today
        st["review"]["next_due"] = iso(anchor + dt.timedelta(days=int(st["config"]["review_interval_days"])))
    if args.blueprint:
        st["blueprint"] = read_blueprint(args.blueprint)
    # what changed decides whether the round prepared ahead still stands: the values, not the
    # keys that were sent (setting a value it already has changes nothing)
    affects = [k for k in changed_keys(was["config"] or {}, st["config"]) if k not in CONTENT_NEUTRAL_CONFIG]
    affects += ["profile." + k for k in changed_keys(was["profile"] or {}, st["profile"])
                if k not in CONTENT_NEUTRAL_PROFILE]
    if args.blueprint and st["blueprint"] != was["blueprint"]:
        affects.append("blueprint")
    bump_gen(st, content=bool(affects))
    st["updated"] = iso(today)
    out = {"ok": True, "gen": st["gen"], "config": st["config"], "review": st["review"], **guideline_context(st)}
    mix, minutes = mix_estimate(st)
    out["round"] = {"mix": mix_text(mix), "estimated_minutes": minutes}      # what to confirm a new mix with
    out["prepared"] = ({"kept": False, "changed": affects,
                        "why": "set aside: %s can change what a round contains, so the next round is "
                               "planned and written at its start" % ", ".join(affects)}
                       if affects else
                       {"kept": True, "why": "kept: nothing that changes what a round contains was changed"})
    publish_ledger(work, info, st, out, empty_prepared=bool(affects))
    print(json.dumps(published(work, info, out), ensure_ascii=False))


def cmd_theme(args):
    """The learner changes the theme of the block: `--set DOMAIN` (an id, a name or part of one)
    or `--another` (the next proposal). With neither, prints the block, the proposal and the
    domains to choose from, and writes nothing. Like `settings`, the changed ledger goes into
    the publish set."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    if not args.set and not args.another:
        p = propose_theme(st) or {"ranking": []}
        bp = st.get("blueprint") or {}
        order = p["ranking"] + [d for d in bp if d not in p["ranking"]]
        print(json.dumps({"ok": True, "changed": False, "block": status_block(st), "next_block": block_end(st),
                          "choices": [{"id": d, "name": domain_name(st, d),
                                       "topics": len((bp[d] or {}).get("topics") or {})} for d in order]},
                         ensure_ascii=False))
        return
    if args.set and args.another:
        die("theme takes --set DOMAIN or --another, not both")
    res = change_theme(st, theme=args.set, another=args.another)
    block = status_block(st)
    out = {"ok": True, "changed": res["changed"], "block": block, "was": res["was"],
           "say": ("New block: %s. Round 1 of %d." % (res["reason"], block["length"])) if res["changed"]
                  else "%s is already the theme. %s." % (block["name"], block["line"])}
    if res["warnings"]:
        out["warnings"] = list(res["warnings"])
    if res["changed"]:
        bump_gen(st)
        st["updated"] = iso(today)
        out["gen"] = st["gen"]
        publish_ledger(work, info, st, out, empty_prepared=True)
        published(work, info, out)
    print(json.dumps(out, ensure_ascii=False))


# ---------------------------------------------------------------- init, blueprint

def read_blueprint(path):
    try:
        text = read_text(path)
    except OSError:
        die("blueprint not found: %s" % path)
    if path.endswith(".json"):
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            die("invalid JSON in %s: %s" % (path, e))
    return blueprint_from_md(text)


def cmd_init(args):
    """Setup: the first ledger of a new learner, written into the publish set of the work folder
    with its page file, no prepared round and the page. The work folder needs no store yet; if
    one was read into it with `open` and already holds a ledger, --start-over is needed."""
    today = today_from(args)
    work = args.work
    os.makedirs(work, exist_ok=True)
    info = work_info(work)
    if info.get("state") and os.path.isfile(info["state"]) and not args.start_over:
        die("the store read into this work folder already holds a ledger: change it with `settings`, "
            "or pass --start-over if the learner asked to start again from nothing")
    st = new_state(today)
    deep_merge(st["profile"], load_json_arg(args.profile) or {})
    deep_merge(st["config"], load_json_arg(args.config) or {})
    st["profile"]["onboarded_at"] = iso(today)
    check_round_mix(st["config"])
    st["config"]["round_set_at"] = st["config"].get("round_set_at") or now_ts()
    st["blueprint"] = read_blueprint(args.blueprint)
    iv = int(st["config"].get("review_interval_days") or 42)
    st["review"] = {"last": None, "next_due": iso(today + dt.timedelta(days=iv)), "period_start": iso(today)}
    st["gen"] = 1
    st.pop("content_gen", None)
    if not info:
        info = {"store": None, "state": None, "version": None, "prefs": None}
    info.update({"session_id": st["next_id"], "started": iso(today)})
    if args.start_over:         # nothing of the old ledger is carried on: not its page file, not this job's files
        info["state"] = None
        for rel in (STATE_PATH, PAGE_PATH):
            if in_work(work, os.path.join(PUBLISH_DIR, rel)):
                os.remove(os.path.join(work, PUBLISH_DIR, rel))
    save_json(info, os.path.join(work, WORK_FILE))
    out = {"ok": True, "gen": st["gen"], "domains": list(st["blueprint"]), "topics": len(bp_topics(st))}
    mix, minutes = mix_estimate(st)
    out["round"] = {"mix": mix_text(mix), "estimated_minutes": minutes}
    path = publish_ledger(work, info, st, out, empty_prepared=True, fresh_page=bool(args.start_over))
    if not store_file(work, info, "index.html"):        # a new store: the page goes with the first ledger
        publish_text(work, "index.html", read_text(PAGE_TEMPLATE))
    out.update({"out": path, "bytes": os.path.getsize(path), "work": os.path.abspath(work)})
    print(json.dumps(published(work, info, out), ensure_ascii=False))


def cmd_blueprint_md(args):
    bp = blueprint_from_md(open(args.file, encoding="utf-8").read())
    save_json(bp, args.out)
    print(json.dumps({"ok": True, "out": args.out, "domains": list(bp), "topics": sum(len(v["topics"]) for v in bp.values())}))


def cmd_validate(args):
    if args.work:
        st, path = current_ledger(*job(args))
    elif args.state:
        path = args.state
        st = load_json(path)
        check_schema(st)
    else:
        die("validate needs --work WORK_FOLDER (or a ledger file)")
    problems = []
    seen = set()
    for s in st["sessions"] + st["previous"]:
        if s.get("id") in seen:
            problems.append("duplicate session id %s" % s.get("id"))
        seen.add(s.get("id"))
    if st.get("next_id") in seen:
        problems.append("next_id %s already used" % st.get("next_id"))
    for tid, t in st["topics"].items():
        if t.get("due") and not parse_date(t["due"]):
            problems.append("topic %s has a bad due date" % tid)
    for g in st["gaps"]:
        if g.get("topic") not in st["topics"]:
            problems.append("gap for unknown topic %s" % g.get("topic"))
    size = os.path.getsize(path)
    print(json.dumps({"ok": not problems, "bytes": size, "sessions": len(st["sessions"]),
                      "previous": len(st["previous"]), "topics": len(st["topics"]), "problems": problems}))
    return 0 if not problems else 1


# ---------------------------------------------------------------- store layout, fast path

# Every store keeps the same documents, at these relative paths.
STATE_PATH = "data/state.json"
PAGE_PATH = "data/page.json"             # the page file: exactly what the page may show (see page_doc)
OLD_INDEX_PATH = "data/index.json"       # what the page read before page 5.1; read once more, to migrate
PREPARED_PATH = "data/prepared.json"     # the next round's short questions, drafted ahead (see cmd_prepare)
PAGE_SCHEMA = 1


def session_path(sid):
    return "data/sessions/%s.json" % sid


def review_path(date):
    return "data/reviews/%s.json" % date


# ---------------------------------------------------------------- the page file
#
# data/page.json is all the page reads of the store, apart from the session and review
# documents it opens when asked. It is rebuilt from the ledger on every write, so the blinding
# of the page is decided here and tested in Python: past sessions, topics already tested, the
# round mix, the block's theme, reviews and settings. Never an open gap, a topic's due date, a
# topic not yet tested, an active drill, the reason for a theme or the prepared round.

PAGE_SESSION_KEYS = ("id", "date", "title", "summary", "tags", "topics", "score", "minutes", "format", "drill",
                     "reflected")


def page_session(doc):
    """What the page lists of one past session (from its session document or the ledger)."""
    e = {k: doc.get(k) for k in PAGE_SESSION_KEYS}
    e["tags"], e["topics"] = list(e["tags"] or []), list(e["topics"] or [])
    if isinstance(e["drill"], dict):
        e["drill"] = e["drill"].get("code")
    if doc.get("url"):
        e["url"] = doc["url"]
    return e


def page_lists(path, old_index=None):
    """The lists a page file carries from one write to the next, {"sessions", "reviews"}: from
    the page file at `path`, else from the index older versions kept (`old_index`), else empty.
    The ledger drops old sessions (§5 of the schema), so these lists are the only place their
    entries stay; a missing or damaged file loses nothing the ledger or `rebuild-page` cannot
    put back."""
    for p in (path, old_index):
        if not p or not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("sessions"), list):
            reviews = doc.get("reviews")
            return {"sessions": [page_session(e) for e in doc["sessions"] if isinstance(e, dict) and e.get("id")],
                    "reviews": [{k: r.get(k) for k in ("date", "title", "headline")}
                                for r in (reviews if isinstance(reviews, list) else [])
                                if isinstance(r, dict) and r.get("date")]}
    return {"sessions": [], "reviews": []}


def page_put_session(lists, doc):
    e = page_session(doc)
    old = next((x for x in lists["sessions"] if x.get("id") == e["id"]), None)
    if old and e.get("minutes") is None:
        e["minutes"] = old.get("minutes")
    lists["sessions"] = [x for x in lists["sessions"] if x.get("id") != e["id"]] + [e]


def page_put_review(lists, doc):
    e = {"date": doc.get("date"), "title": doc.get("title"), "headline": doc.get("headline")}
    lists["reviews"] = [x for x in lists["reviews"] if x.get("date") != e["date"]] + [e]


def page_doc(st, lists=None):
    """The page file for ledger `st`: what the page may show and nothing else. `lists` are the
    session and review entries carried on (page_lists); the ledger adds the sessions and reviews
    they lack and is the authority on scores, minutes and whether a round was reflected on."""
    cfg, prof = st.get("config") or {}, st.get("profile") or {}
    lists = lists or {"sessions": [], "reviews": []}
    sessions = {e["id"]: dict(e) for e in lists["sessions"]}
    for s in (st.get("previous") or []) + (st.get("sessions") or []):
        if not s.get("id"):
            continue
        e = sessions.setdefault(s["id"], page_session(s))
        if isinstance(s.get("minutes"), (int, float)):
            e["minutes"] = s["minutes"]
        if isinstance(s.get("score"), (int, float)):
            e["score"] = s["score"]
        e["reflected"] = s["id"] != st.get("unreflected")
    sessions = sorted(sessions.values(), key=lambda x: (x.get("date") or "", id_num(x.get("id"))), reverse=True)
    reviews = {r["date"]: dict(r) for r in lists["reviews"]}
    for r in st.get("reviews") or []:
        if r.get("date") and r.get("doc") and r["date"] not in reviews:
            reviews[r["date"]] = {"date": r["date"], "title": "CME progress review — %s" % r["date"],
                                  "headline": r.get("headline")}
    # topics already tested, most recently tested first: never the due date, never an order by it
    topics = [{"id": tid, "label": t.get("label"), "mastery": t.get("mastery"), "last": t.get("last"),
               "calibration": t.get("calibration")}
              for tid, t in (st.get("topics") or {}).items() if t.get("last") or t.get("mastery") is not None]
    topics.sort(key=lambda t: t["id"])
    topics.sort(key=lambda t: t["last"] or "", reverse=True)
    mastery = [t["mastery"] for t in topics if isinstance(t["mastery"], (int, float))]
    period = [s.get("score") for s in st.get("sessions") or []]
    scores = [x for x in period if isinstance(x, (int, float))]
    mix, minutes = mix_estimate(st)
    block = st.get("block")
    if isinstance(block, dict) and block.get("theme"):
        length = int(block.get("length") or BLOCK_LENGTH)
        block = {"theme": block["theme"], "name": domain_name(st, block["theme"]),
                 "done": min(int(block.get("round") or 0), length), "length": length}
    else:
        block = None
    ratings = {}
    for d, r in (prof.get("domain_self_ratings") or {}).items():
        ratings[d] = r.get("rating") if isinstance(r, dict) else r
    review = st.get("review") or {}
    context = guideline_context(st)
    return {
        "schema": PAGE_SCHEMA, "page_version": PAGE_VERSION, "gen": st.get("gen"), "updated": st.get("updated"),
        "who": {"name": prof.get("display_name"), "role": prof.get("role"), "specialty": context["specialty"],
                "subspecialty": prof.get("subspecialty"), "practice": list(prof.get("practice_setting") or [])},
        "totals": {"topics": len(topics),
                   "mean_mastery": round(sum(mastery) / len(mastery), 1) if mastery else None,
                   "since": review.get("period_start"), "sessions": len(period),
                   "mean_score": round(sum(scores) / len(scores), 1) if scores else None},
        "sessions": sessions,
        "topics": topics,
        # the mix in force and what it costs: the page shows `minutes`, and prices a mix the
        # learner is choosing with `minutes_per` (the case already at the next round's format)
        "round": {"mix": mix, "set_at": cfg.get("round_set_at"),
                  "minutes": minutes,
                  "minutes_per": {"mcq": MINUTES_PER["mcq"], "focused": MINUTES_PER["focused"],
                                  "case": MINUTES_PER[next_case_format(st)]},
                  "limits": {k: list(v) for k, v in ROUND_LIMITS.items()},
                  "time_hint": None},                    # issue #47: the learner's own pace
        "block": block,
        "reviews": sorted(reviews.values(), key=lambda r: r.get("date") or "", reverse=True),
        "next_review": review.get("next_due"),
        "settings": {
            "session_length": cfg.get("session_minutes"), "per_week": cfg.get("target_sessions_per_week"),
            "region": context["guideline_region"],
            "units": {"labs": cfg.get("lab_units"), "gases": cfg.get("blood_gas_units")},
            "case_style": cfg.get("case_format"), "order": cfg.get("item_order"),
            "feedback": cfg.get("feedback_depth"), "coding_line": bool(cfg.get("show_coding", True)),
            "review_every_days": cfg.get("review_interval_days"), "reminders": bool(cfg.get("reminders")),
            "emphasis": dict(prof.get("domain_emphasis") or {}), "self_ratings": ratings,
            "level": None, "aim": None,                  # issue #55: {"label", "text"} each
            "reading": None, "listening": None,          # issue #51
        },
    }


def status_dict(st, path, today):
    cfg = st["config"]
    topics = st["topics"]
    due = [t for t in topics.values() if parse_date(t.get("due")) and parse_date(t["due"]) <= today]
    all_sessions = st["sessions"]
    last = all_sessions[-1] if all_sessions else None
    week_ago = today - dt.timedelta(days=7)
    this_week = sum(1 for s in all_sessions if parse_date(s.get("date")) and parse_date(s["date"]) > week_ago)
    rdue, rdate = review_status(st, today)
    return {
        "ok": True, "date": iso(today), "gen": st.get("gen"), "next_id": st.get("next_id"),
        "onboarding_needed": not st["profile"].get("onboarded_at"),
        "last_session": {"id": last.get("id"), "date": last.get("date"),
                         "items": len(last.get("items") or []),
                         "unreflected": last.get("id") == st.get("unreflected")} if last else None,
        "days_since_last_session": (today - parse_date(last["date"])).days if last and parse_date(last.get("date")) else None,
        "sessions_this_week": this_week,
        "target_sessions_per_week": cfg.get("target_sessions_per_week"),
        "due_count": len(due),
        "overdue_7d_count": sum(1 for t in due if (today - parse_date(t["due"])).days >= 7),
        "open_gaps": len(st.get("gaps") or []),
        "review_due": rdue, "review_due_date": rdate,
        "pending_errata_count": len(st.get("pending_errata") or []),
        "drills_active": len(st.get("drills") or []),
        # the block the next round belongs to; `line` is what the opening line says about it
        "block": status_block(st),
        "round": {"mcqs": cfg.get("mcqs", 3), "focused": cfg.get("focused", 0), "case": bool(cfg.get("case", True)),
                  "minutes": cfg.get("session_minutes"), "item_order": cfg.get("item_order")},
        "helpers": bool(cfg.get("helpers", True)), "prepare_ahead": bool(cfg.get("prepare_ahead", True)),
        "testing": bool(cfg.get("testing", False)),
        **guideline_context(st),             # what the examiner grades against
        "prepare_task": bool(cfg.get("prepare_task", False)),
        "reminders": cfg.get("reminders"),
        "bytes": os.path.getsize(path),
        # true until the first save with version 4.3: tell the learner once about the speed settings
        "speed_settings_new": "helpers" not in cfg or "prepare_ahead" not in cfg,
    }


def status_block(st):
    """block_status, with the reason for the theme while the block has not begun (the opening
    line of its first round gives it)."""
    out = block_status(st)
    if out and out["starts"]:
        out["reason"] = next_block(st)[0].get("reason")
    return out


def plan_options_given(args):
    return any((getattr(args, "mcqs", None) is not None, getattr(args, "focused", None) is not None,
                args.no_case, args.domain, args.no_new, args.allow_repeat, args.no_drill, args.force_drill,
                args.seed is not None))


def cmd_open(args):
    """Set up the work folder for one job from the local copy of the learner's store. Prints
    neutral status and counts only (never topics)."""
    today = today_from(args)
    info, st, extra = open_work(args.work, args.store, args.version, load_json_arg(args.prefs), today,
                                reread=args.reread)
    status = status_dict(st, info["state"], today)
    status.update(extra)
    print(json.dumps(status, ensure_ascii=False))


def cmd_start(args):
    """Start a round in the work folder: neutral status and plan counts (never topics) and, with
    a prepared round that still fits, the first part to present. With --store the work folder
    is opened first (what `open` does); without, the round continues the job that is open."""
    today = today_from(args)
    work = args.work
    extra = {}
    if args.store:
        info, _, extra = open_work(work, args.store, args.version, load_json_arg(args.prefs), today)
    else:
        info = job(args)[1]
        if args.prefs:
            info["prefs"] = load_json_arg(args.prefs)
        if args.version:
            info["version"] = args.version
        set_aside = set_aside_round(work)       # a round after another job here: its files must not mix
        if set_aside:
            extra["earlier_set_aside"] = set_aside
    st, path = current_ledger(work, info)
    prefs_warn = []
    prefs_changes = apply_prefs(st, info.get("prefs"), prefs_warn)
    status = status_dict(st, path, today)
    status.update(extra)
    status["work"] = os.path.abspath(work)
    info.update({"session_id": st.get("next_id"), "started": iso(today)})
    info.pop("closed", None)
    save_json(info, os.path.join(work, WORK_FILE))
    publish_set(work, info)
    if prefs_changes:
        status["page_settings_applied"] = prefs_changes
    if prefs_warn:
        status["warnings"] = list(status.get("warnings") or []) + prefs_warn
    if status["onboarding_needed"]:
        status["plan"] = None
        print(json.dumps(status, ensure_ascii=False))
        return
    plan_path = os.path.join(work, PLAN_FILE)
    plan_out = None
    if args.no_prepared:
        prepared = {"used": False, "why": "--no-prepared was given for this round"}
    else:
        prepared = take_prepared(args, st, today, store_file(work, info, PREPARED_PATH), work, plan_path)
    status["prepared"] = {k: v for k, v in prepared.items()
                          if k in ("used", "why", "made", "ready", "present_block")}
    if prepared.get("mix") is not None:
        # the prepared round was written for another mix than the one in force: the learner's
        # latest choice wins, the prepared round is set aside, and the round says so
        used, source = plan_counts(st), ("page" if prefs_changes and "unchanged" not in prefs_changes
                                         else "settings")
        status["round_mix"] = {
            "used": used, "prepared": prepared["mix"], "source": source,
            "say": "Using the mix %s: %s. The round prepared ahead was written for %s and is set aside, "
                   "so this round is written now." % (
                       "you set on your page" if source == "page" else "in your settings",
                       mix_text(used), mix_text(prepared["mix"]))}
    if prepared["used"]:
        plan_out = prepared["summary"]
        status["present"] = prepared["present"]
    else:
        plan = plan_round(st, args, today)
        save_json(plan, plan_path)
        plan_out = plan_summary(plan, plan_path)
    status["plan"] = plan_out
    # everything the first message needs, so that nothing else is run or read before it (issue #43)
    status["started_at"] = now_ts()
    status["opening"] = opening_line(status, plan_out, today)
    if prepared["used"]:
        ready = prepared["ready"]
        status["prepared"]["unchecked"] = [n for n in SEALED_FILES if n in ready and EVIDENCE_FOR[n] not in ready]
    print(json.dumps(status, ensure_ascii=False))


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def opening_line(status, plan, today):
    """The opening line of a round, from neutral facts only: the mix, the time, the block's
    theme and position, the last saved session. Never a topic."""
    line = "Today's round: %s, about %s minutes." % (mix_text(plan), plan.get("estimated_minutes"))
    block = status.get("block")
    if block:
        line += " %s." % block["line"]
        if block.get("starts") and block.get("reason"):
            line += " New block: %s." % block["reason"].rstrip(".")
    last = parse_date((status.get("last_session") or {}).get("date"))
    if last:
        line += " Last saved session: %d %s%s." % (last.day, MONTHS[last.month - 1],
                                                 "" if last.year == today.year else " %d" % last.year)
    return line


# ---------------------------------------------------------------- prepared round (drafted ahead)

def pack(obj):
    """Not readable at a glance: the prepared round sits in the learner's own store."""
    return base64.b64encode(zlib.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8"), 9)).decode("ascii")


def unpack(text):
    return json.loads(zlib.decompress(base64.b64decode(text)).decode("utf-8"))


def plan_counts(st, args=None):
    cfg = st["config"]
    return {"mcqs": int(cfg.get("mcqs", 3) or 0), "focused": int(cfg.get("focused", 0) or 0),
            "case": 1 if cfg.get("case", True) else 0}


def cmd_prepare(args):
    """After the close (or in a prepare-only job): plan the NEXT round as of tomorrow from the
    current ledger of the work folder, into <work>/next/plan.json, so that the whole round
    (short questions, case, feedback notes) can be drafted now and the next session starts with
    nothing to write. Prints counts only."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    # the round is written for the mix the next `start` will use: a mix set on the page and not
    # yet in the ledger counts here too (in memory only; `start` and `save` apply it for good)
    apply_prefs(st, info.get("prefs"))
    cfg = st["config"]
    why = None
    if not cfg.get("prepare_ahead", True):
        why = "prepare_ahead is off"
    elif st.get("unreflected") and not args.allow_unreflected:
        why = "the last session is still waiting for its reflection"
    elif args.if_needed and prepared_fits(store_file(work, info, PREPARED_PATH), st, today):
        why = "a round is already prepared"
    if why:
        print(json.dumps({"ok": True, "prepare": False, "why": why}))
        return
    ns = argparse.Namespace(focused=None, mcqs=None, no_case=False, domain=None, no_new=False,
                            allow_repeat=False, no_drill=False, force_drill=False, seed=None)
    plan = plan_round(st, ns, today + dt.timedelta(days=1))
    folder = os.path.join(work, NEXT_DIR)
    os.makedirs(folder, exist_ok=True)
    out = os.path.join(folder, PLAN_FILE)
    summary = plan_summary(plan, out)
    plan["prepared"] = {"gen": content_gen(st), "made": iso(today), "session_id": st.get("next_id")}
    save_json(plan, out)
    summary.update({"prepare": True, "gen": content_gen(st), "folder": os.path.abspath(folder),
                    "note": "Sealed: have the whole round drafted for this plan into this folder "
                            "(sealed_questions.md, sealed_case.md, kit_questions.md, kit_case.md), "
                            "have each sealed file checked (evidence_questions.md, evidence_case.md), "
                            "then run finish-prepare --work on the same work folder."})
    print(json.dumps(summary, ensure_ascii=False))


PREPARED_FILES = ("sealed_questions.md", "sealed_case.md", "kit_questions.md", "kit_case.md",
                  "evidence_questions.md", "evidence_case.md")


def present_blocks(text):
    return {k: v.strip() for k, v in PRESENT_RE.findall(text or "") if v.strip()}


def prepared_round_files(plan, folder):
    """The files drafted for a plan in `folder` that belong in the prepared round: (files, has,
    warnings). Stops when the first part's sealed file is not usable."""
    files = {}
    for name in PREPARED_FILES:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            if text.strip():
                files[name] = text
    counts = plan.get("counts") or {}
    short = (counts.get("mcqs") or 0) + (counts.get("focused") or 0)
    has, warnings = [], []
    if present_blocks(files.get("sealed_questions.md")).get("questions"):
        has.append("questions")
    if present_blocks(files.get("sealed_case.md")).get("case"):
        has.append("case")
    if short and "questions" not in has:
        die("sealed_questions.md with a <!-- present: questions --> … <!-- /present --> block is missing in %s" % folder)
    if not short and "case" not in has:
        die("sealed_case.md with a <!-- present: case --> … <!-- /present --> block is missing in %s" % folder)
    if counts.get("case") and "case" not in has:
        files.pop("sealed_case.md", None); files.pop("kit_case.md", None); files.pop("evidence_case.md", None)
        warnings.append("no usable sealed_case.md: the case will be drafted at the next session")
    if not counts.get("case"):
        files.pop("sealed_case.md", None); files.pop("kit_case.md", None); files.pop("evidence_case.md", None)
    if "questions" not in has:
        files.pop("kit_questions.md", None); files.pop("evidence_questions.md", None)
    has += [n[:-3] for n in PREPARED_FILES[2:] if n in files]
    return files, has, warnings


def plan_for_prepared(st, plan_path):
    plan = load_json(plan_path)
    meta = plan.get("prepared") or {}
    if meta.get("gen") != content_gen(st):
        die("this plan was not made by `prepare` from this ledger (gen %s, ledger %s): run `prepare` again"
            % (meta.get("gen"), content_gen(st)))
    return plan


def prepared_doc(st, plan, files, has):
    """The prepared round as it is kept in the store (data/prepared.json), packed."""
    return {"v": 2, "gen": content_gen(st), "made": (plan.get("prepared") or {}).get("made"),
            "session_id": st.get("next_id"), "counts": plan.get("counts") or {}, "has": has,
            "payload": pack({"plan": plan, "files": files})}


# The last two lines of an evidence file, as references/evidence_check.md §4 prescribes them.
CHECKED_RE = re.compile(r"^[ \t>*_`-]*Checked[ \t*_`]*:[ \t*_`]*(\S.*?),[ \t]*(\d+)[ \t]+claims?[ \t]*,"
                        r"[ \t]*(\d+)[ \t]+not[ \t]+verified[ \t*_`.]*$", re.M | re.I)
EVIDENCE_BLOCK_RE = re.compile(r"^#{2,4}[ \t]+\d+[.)]", re.M)
STATUS_RE = re.compile(r"^[ \t>*_`-]*Status[ \t*_`]*:[ \t*_`]*(.*)$", re.M | re.I)
TRIED_RE = re.compile(r"^[ \t>*_`-]*Tried[ \t*_`]*:[ \t*_`]*\S", re.M | re.I)
# A part goes back to its checker once when more than this share of its claims is not verified.
NOT_VERIFIED_MAX = (1, 3)
CONTRADICTED_RE = re.compile(r"^[ \t>*_`-]*Keys contradicted[ \t*_`]*:[ \t*_`]*(\d+)[ \t*_`.]*$", re.M | re.I)
EVIDENCE_FOR = {"sealed_questions.md": "evidence_questions.md", "sealed_case.md": "evidence_case.md"}
NEXT_DIR = "next"                       # in the work folder: the next round's plan and drafts
def contradicted_keys(text):
    """The number on an evidence file's `Keys contradicted: <n>` line (the last one, if the
    file was written twice), or None when the file has no such line."""
    found = CONTRADICTED_RE.findall(text or "")
    return int(found[-1]) if found else None


def checked_counts(text):
    """What an evidence file says of its own check, from its `Checked: <date>, <n> claims, <n> not
    verified` line (the last one, if the file was written twice) and the claim blocks under it:
    {"claims", "not_verified", "untried"}, or None when the line is missing or cannot be read
    (also when it counts no claims, or more not verified than claims).

    `not_verified` is the larger of the line's number and the blocks whose status is "not
    verified", so that a line that undercounts its own blocks is not believed; `untried` is how
    many of those blocks have no `Tried:` line (no other route was attempted)."""
    text = text or ""
    lines = list(CHECKED_RE.finditer(text))
    if not lines:
        return None
    claims, not_verified = int(lines[-1].group(2)), int(lines[-1].group(3))
    if claims < 1 or not_verified > claims:
        return None
    body = text[lines[-2].end() if len(lines) > 1 else 0:lines[-1].start()]
    starts = [m.start() for m in EVIDENCE_BLOCK_RE.finditer(body)]
    open_blocks = []
    for i, at in enumerate(starts):
        block = body[at:starts[i + 1] if i + 1 < len(starts) else len(body)]
        status = STATUS_RE.search(block)
        if status and re.match(r"not[ \t]+verified\b", status.group(1).strip(" \t*_`"), re.I):
            open_blocks.append(block)
    return {"claims": claims, "not_verified": min(claims, max(not_verified, len(open_blocks))),
            "untried": sum(1 for b in open_blocks if not TRIED_RE.search(b))}


def needs_recheck(counts):
    """Does this part go back to its checker for one retry pass? Yes when more than a third of its
    claims is not verified, or when a claim was given up without another route being tried."""
    num, den = NOT_VERIFIED_MAX
    return counts["not_verified"] * den > counts["claims"] * num or counts["untried"] > 0


def not_verified_line(name, counts):
    line = "%s: %d of %d claims not verified" % (name, counts["not_verified"], counts["claims"])
    if counts["untried"]:
        line += ", %d without a `Tried:` line" % counts["untried"]
    return line


def cmd_finish_prepare(args):
    """After the checkers: lint the round drafted in <work>/next against the rulebook
    (references/standards.md), read the evidence files' counts of contradicted keys and, when the
    round is clean (or was revised), pack it and add it to the publish set as data/prepared.json.

    Definite problems stop the command and nothing is stashed: a missing or malformed key header
    (so that it is not found only at `save`, in the middle of the round), a missing kit or kit
    section, and an evidence file that is missing, empty or without its two count lines (never
    read as "nothing contradicted" or "everything verified").
    Judgement calls go back once: an abbreviation that looks undefined, time anchors that look
    mixed and a contradicted key to the author (`"revise": true`); a part with more than a third
    of its claims not verified, or a claim given up without another route tried, to its checker
    (`"recheck": [files]`). With --revised whatever is still found is accepted and listed under
    `warnings`.
    Prints counts, file names and the names of keys, fields and kit sections only; what the lint
    found is written to <work>/next/lint.md, which only the author reads."""
    work, info = job(args)
    folder = os.path.join(work, NEXT_DIR)
    plan_path = os.path.join(folder, PLAN_FILE)
    if not os.path.isfile(plan_path):
        die("no plan in %s: run `prepare --work %s` first" % (folder, work))
    st, _ = current_ledger(work, info)
    plan = plan_for_prepared(st, plan_path)
    files, has, warnings = prepared_round_files(plan, folder)
    _, key_problems = check_key_headers([os.path.join(folder, n) for n in SEALED_FILES if n in files], plan)
    lint = lint_round(files, plan, kits_required=True)
    if key_problems or lint["blocking"]:
        stops = []
        if key_problems:
            stops.append("the key headers are not complete in %s: %s" % (folder, "; ".join(key_problems)))
        if lint["blocking"]:
            stops.append("the kits are not complete in %s: %s" % (folder, "; ".join(lint["blocking"])))
        die("%s. Nothing was stashed. Have them corrected in the files (references/standards.md, rule 9 for "
            "key headers, rule 8 for kits; `keys` runs this check alone), then run this command again"
            % ". Also, ".join(stops))
    out = {"ok": True}
    if args.no_evidence:
        # no checker was run (no helpers): the evidence is checked at the session, after the answers
        for name in EVIDENCE_FOR.values():
            files.pop(name, None)
        has = [h for h in has if not h.startswith("evidence_")]
        out.update({"evidence": "not checked", "contradicted": None})
        total, checked = 0, {}
    else:
        per_file, checked, problems = {}, {}, []
        for sealed, evidence in EVIDENCE_FOR.items():
            if sealed not in files:
                continue
            path = os.path.join(folder, evidence)
            if evidence not in files:
                problems.append("%s is %s" % (evidence, "empty" if os.path.exists(path) else "missing"))
                continue
            n, counts = contradicted_keys(files[evidence]), checked_counts(files[evidence])
            if counts is None:
                problems.append("%s has no readable `Checked: <date>, <n> claims, <n> not verified` line"
                                % evidence)
            if n is None:
                problems.append("%s has no `Keys contradicted: <n>` line" % evidence)
            if n is not None and counts is not None:
                per_file[evidence], checked[evidence] = n, counts
        if problems:
            die("the evidence check is not complete in %s: %s. Nothing was stashed. Run the checker for it "
                "again (references/evidence_check.md), or pass --no-evidence if no checker is run in this session"
                % (folder, "; ".join(problems)))
        total = sum(per_file.values())
        out.update({"evidence": per_file, "contradicted": total, "not_verified": checked,
                    "not_verified_total": sum(c["not_verified"] for c in checked.values()),
                    "claims_total": sum(c["claims"] for c in checked.values())})
    flagged = [name for name, counts in checked.items() if needs_recheck(counts)]
    out["lint"] = lint_summary(lint, write_lint_details(folder, lint))
    out["revise"] = bool(total or lint["review"]) and not args.revised
    recheck = [] if args.revised else flagged
    if not args.no_evidence:
        out["recheck"] = recheck
    if args.revised:
        out["revised"] = True
        warnings = warnings + ["accepted after one revision: %s" % line for line in lint_lines(lint)]
        warnings = warnings + ["accepted after one retry: %s (references/evidence_check.md §3); state these "
                               "claims qualitatively or leave them out" % not_verified_line(name, checked[name])
                               for name in flagged]
    warnings = warnings + lint["notes"]
    if warnings:
        out["warnings"] = warnings
    if out["revise"] or recheck:
        steps = []
        if recheck:
            steps.append("start the checker once more for %s (same prompt; it finds its own file and retries "
                         "only what is not verified, references/evidence_check.md §3) and wait for it"
                         % " and ".join(recheck))
        steps.append("start the author once more with Parts `revise` on this folder (it reads the evidence "
                     "files and lint.md there) and wait for it")
        out.update({"stashed": False,
                    "next": "%s, then run this command again with --revised" % "; then ".join(steps)})
        print(json.dumps(out, ensure_ascii=False))
        return
    publish_json(work, PREPARED_PATH, prepared_doc(st, plan, files, has))
    out.update({"gen": content_gen(st), "has": has, "stashed": True})
    print(json.dumps(published(work, info, out), ensure_ascii=False))


def cmd_present(args):
    """Print only the text the learner is to see (one present block) from the sealed files of
    the work folder, so the assistant can send it without opening the keys. `--block bank`
    prints the case's results bank (results, course, Stage 2 questions), which is all that is
    needed to send Stage 2."""
    files = list(args.files or [])
    if not files:
        if not args.work:
            die("present needs --work WORK_FOLDER")
        files = [p for p in (in_work(args.work, n) for n in SEALED_FILES) if p]
        if not files:
            die("no sealed files (%s) in the work folder %s" % (", ".join(SEALED_FILES), args.work))
    pres = blocks(files, BANK_RE if args.block == "bank" else PRESENT_RE)
    body = pres.get(args.block)
    if not body:
        die("no <!-- present: %s --> block in %s" % (args.block, ", ".join(files)))
    sys.stdout.write(body.strip() + "\n")


def prepared_fits(path, st, today):
    """Is the prepared round in `path` still usable for this ledger with its normal mix?"""
    if not path:
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, OSError):
        return False
    made = parse_date(doc.get("made")) if isinstance(doc, dict) else None
    return bool(isinstance(doc, dict) and doc.get("payload") and doc.get("gen") == content_gen(st)
                and doc.get("session_id") == st.get("next_id") and doc.get("counts") == plan_counts(st)
                and made and 0 <= (today - made).days <= PREPARED_MAX_AGE_DAYS)


def take_prepared(args, st, today, path, work, plan_path):
    """Use the round prepared at the last close (`path`, the store's data/prepared.json) if it
    still fits: same mix, nothing that changes a round written to the ledger since
    (content_gen), no one-off options, not too old, none of its topics tested today. Its plan
    goes to `plan_path`, its files into the work folder. When it was written for another mix
    than the ledger now asks for, `mix` in the answer is the mix it was written for."""
    def no(why, **more):
        return dict({"used": False, "why": why}, **more)
    if not path or not os.path.exists(path):
        return no("no prepared round")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, OSError):
        return no("unreadable")
    if not isinstance(doc, dict) or not doc.get("payload"):
        return no("no prepared round")
    if plan_options_given(args):
        return no("one-off options were given for this round")
    if doc.get("counts") != plan_counts(st):       # before the generation: the more telling reason
        return no("the round mix changed", mix=doc.get("counts") or {})
    if doc.get("gen") != content_gen(st) or doc.get("session_id") != st.get("next_id"):
        return no("the ledger changed since it was prepared")
    made = parse_date(doc.get("made"))
    if not made or (today - made).days > PREPARED_MAX_AGE_DAYS or made > today:
        return no("too old")
    try:
        inner = unpack(doc["payload"])
        plan = inner["plan"]
        files = inner.get("files") or {"sealed_questions.md": inner["sealed"]}
    except Exception:
        return no("unreadable")
    if (plan.get("counts") or {}) != plan_counts(st):      # the plan itself, not only the label on the pack
        return no("the round mix changed", mix=plan.get("counts") or {})
    now, was = block_status(st) or {}, plan.get("block") or {}
    if (now.get("theme"), now.get("round")) != (was.get("theme"), was.get("round")):
        return no("it was not prepared for this round of the block")
    q_text = present_blocks(files.get("sealed_questions.md")).get("questions")
    c_text = present_blocks(files.get("sealed_case.md")).get("case")
    first = q_text or c_text
    if not first:
        return no("unreadable")
    for it in plan.get("items") or []:
        t = st["topics"].get(it.get("topic") or "")
        if t and parse_date(t.get("last")) == today:
            return no("one of its topics was tested today")
    plan["date"] = iso(today)
    # settings that do not change the round may have changed since: the plan carries today's
    cfg = st["config"]
    plan.update({"show_coding": cfg.get("show_coding", True), "helpers": bool(cfg.get("helpers", True)),
                 "prepare_ahead": bool(cfg.get("prepare_ahead", True)), "testing": bool(cfg.get("testing", False))})
    plan["prepared"] = dict(plan.get("prepared") or {}, used=True)
    save_json(plan, plan_path)
    written = []
    for name in PREPARED_FILES:
        if files.get(name):
            with open(os.path.join(work, name), "w", encoding="utf-8") as fh:
                fh.write(files[name])
            written.append(name)
    items = plan.get("items") or []
    counts = plan.get("counts") or {}
    summary = {"ok": True, "out": plan_path, "items": len(items), "mcqs": counts.get("mcqs"),
               "focused": counts.get("focused"), "case": counts.get("case"),
               "case_format": plan.get("case_format"), "estimated_minutes": plan.get("estimated_minutes"),
               "item_order": plan.get("item_order"), "session_id": st.get("next_id"), "prepared": True}
    return {"used": True, "made": doc.get("made"), "summary": summary, "ready": written,
            "present": first, "present_block": "questions" if q_text else "case"}


PRESENT_RE = re.compile(r"<!--\s*present:\s*([a-z0-9_]+)\s*-->\s*\n(.*?)\n?\s*<!--\s*/present\s*-->", re.S)
BANK_RE = re.compile(r"<!--\s*(bank)\s*-->\s*\n(.*?)\n?\s*<!--\s*/bank\s*-->", re.S)
ANSWER_RE = re.compile(r"<!--\s*answers:\s*([a-z0-9_]+)\s*-->\s*\n(.*?)\n?\s*<!--\s*/answers\s*-->", re.S)
PART_A_SECTIONS = {
    "questions": "### Questions — as presented",
    "a_questions": "### Your answers — questions (verbatim)",
    "case": "### Case — as presented",
    "a_case": "### Your answers — case (verbatim)",
    "stage2": "### Stage 2 — as presented",
    "a_final": "### Your final answers (verbatim)",
    "fb_questions": "### Feedback — questions (as sent)",
}


def blocks(paths, rx):
    out = {}
    for p in paths or []:
        with open(p, "r", encoding="utf-8") as fh:
            for name, body in rx.findall(fh.read()):
                out[name] = (out.get(name, "") + "\n\n" + body.strip()).strip()
    return out


def assemble_part_a(sealed, answers, feedback, item_order, warnings, feedback_questions=None, stage2=None):
    """Part A in the order of the round. With mcqs_first the short questions are graded before
    the case is shown, so their feedback (if sent on its own) follows their answers. `stage2` is
    Stage 2 as it was sent (the work folder's stage2.md); it replaces a stage2 present block."""
    pres = blocks(sealed, PRESENT_RE)
    if stage2 and stage2.strip():
        pres["stage2"] = stage2.strip()
    ans = blocks(answers, ANSWER_RE)
    fb = fbq = None
    if feedback:
        with open(feedback, "r", encoding="utf-8") as fh:
            fb = fh.read().strip()
    if feedback_questions:
        with open(feedback_questions, "r", encoding="utf-8") as fh:
            fbq = fh.read().strip() or None
    mcq = [("questions", pres.get("questions")), ("a_questions", ans.get("questions"))]
    if fbq:
        if pres.get("questions"):
            mcq.append(("fb_questions", fbq))
        else:
            warnings.append("part A: --feedback-questions given but no <!-- present: questions --> block; "
                            "it was put before the final feedback")
            fb = (fbq + "\n\n" + fb) if fb else fbq
    case = [("case", pres.get("case")), ("a_case", ans.get("case"))]
    stage2 = [("stage2", pres.get("stage2")), ("a_final", ans.get("final"))]
    order = (case + mcq + stage2) if item_order == "case_first" else (mcq + case + stage2)
    parts = []
    for key, body in order:
        if body is None:
            if key in ("stage2", "a_final") and not pres.get("stage2"):
                continue
            if key in ("questions", "a_questions") and not pres.get("questions"):
                continue
            if key in ("case", "a_case") and not pres.get("case"):
                continue
            warnings.append("part A: no '%s' block found; wrote 'None.'" % key)
            body = "None."
        parts.append("%s\n\n%s" % (PART_A_SECTIONS[key], body))
    for k, p in (("questions", "questions"), ("case", "case"), ("final", "stage2")):
        if ans.get(k) and not pres.get(p):
            warnings.append("part A: answers '%s' found but no <!-- present: %s --> block in the sealed draft" % (k, p))
    if ans.get("notes"):
        parts.append("### Notes\n\n%s" % ans["notes"])
    if fb:
        parts.append("### Feedback (as sent)\n\n%s" % fb)
    else:
        warnings.append("part A: no final feedback file (--feedback)")
    if not pres:
        warnings.append("part A: the sealed draft has no <!-- present: … --> blocks")
    return "\n\n".join(parts) + "\n"


def session_doc_a(rnd, sid, md):
    doc = {"id": sid, "date": rnd.get("date") or iso(dt.date.today()),
           "title": rnd.get("title"), "summary": rnd.get("summary"), "tags": rnd.get("tags") or [],
           "topics": sorted({it.get("topic") for it in rnd.get("items") or [] if it.get("topic")}),
           "score": None, "format": round_format(rnd), "drill": (rnd.get("drill") or {}).get("code"),
           "transcript": md, "closing": None, "reflected": False}
    if rnd.get("items"):
        ms = [adjusted_item_mastery(it)[0] for it in rnd["items"]]
        doc["score"] = round(sum(ms) / len(ms), 2)
    return doc


def round_format(rnd):
    """The case format, or a label for rounds without a case (shown on the page)."""
    items = rnd.get("items") or []
    if any(is_case(it) for it in items):
        return rnd.get("case_format")
    kinds = sorted({it.get("type") for it in items if it.get("type") in ("mcq", "focused")})
    return {("focused",): "focused questions", ("mcq",): "MCQs only",
            ("focused", "mcq"): "MCQs and focused questions"}.get(tuple(kinds))


PAGE_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "templates", "page.html")
PAGE_VERSION_RE = re.compile(r'<meta\s+name="cme-page-version"\s+content="([0-9.]+)"')


def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def page_upgrade(work, info, warnings):
    """If the learner's live page (index.html, read with the ledger) is older than this skill's
    template, put the template into the publish set so it is published with the ledger.
    Returns {"from", "to"} when it did."""
    live_page = store_file(work, info, "index.html")
    if not live_page:
        return None
    try:
        m = PAGE_VERSION_RE.search(read_text(live_page))
    except OSError:
        warnings.append("could not read %s; the page was not checked" % live_page)
        return None
    live = m.group(1) if m else "0"
    if version_tuple(live) >= version_tuple(PAGE_VERSION):
        return None
    publish_text(work, "index.html", read_text(PAGE_TEMPLATE))
    return {"from": live, "to": PAGE_VERSION}


# ---------------------------------------------------------------- structured keys
#
# The author writes a small header with each key in the sealed files:
#
#   <!-- key: Q1 -->
#   type: mcq
#   topic: CARD-03
#   label: Atrial fibrillation
#   reason: due
#   retests: G0004
#   stem_summary: New AF after surgery, when to anticoagulate
#   <!-- /key -->
#
# `save` builds the round record from these headers: an item of round.json names its key
# ("key": "Q1") and carries only what the examiner decided (score, confidence, coding).

KEY_RE = re.compile(r"<!--[ \t]*key:[ \t]*([A-Za-z0-9_]+)[ \t]*-->[ \t]*\n(.*?)\n?[ \t]*<!--[ \t]*/key[ \t]*-->", re.S)
KEY_OPEN_RE = re.compile(r"<!--\s*key\b")
KEY_ID_RE = re.compile(r"^(Q[1-9][0-9]?|case)$")
KEY_TYPES = ("mcq", "focused", "case")
KEY_COMMON = ("type", "topic", "label", "reason")           # every header needs these
KEY_REQUIRED = {"mcq": ("stem_summary",), "focused": ("stem_summary", "aspect"),
                "case": ("patient", "setting", "presentation", "diagnosis")}
KEY_OPTIONAL = {"mcq": (), "focused": (), "case": ("twist",)}
KEY_ANY = ("domain", "retests")                              # optional in every header
KEY_ITEM_FIELDS = ("type", "topic", "label", "domain", "retests", "stem_summary", "aspect")
KEY_CASE_FIELDS = ("patient", "setting", "presentation", "diagnosis", "twist")
KEY_EMPTY = ("", "-", "none", "null", "n/a", "na")
RECORD_FILE = "record.json"             # written by save: the round record as it was recorded
PLAN_FILE = "plan.json"


def key_id(text):
    """A key's id as written, in its one spelling: Q1, Q2, … or case."""
    t = str(text or "").strip()
    return "case" if t.lower() == "case" else t.upper()


def parse_key_headers(text, where="sealed file"):
    """The key headers of one sealed file: ({id: {field: value}}, [problems]). A header that has a
    problem is still returned, marked `_bad`, so that whoever uses it can refuse it. The problems
    name the file, the key and the field, never a value: they can be shown before the answers."""
    headers, problems = {}, []
    found = KEY_RE.findall(text or "")
    if len(KEY_OPEN_RE.findall(text or "")) > len(found):
        problems.append("%s: a key header is not closed, or its first line is not '<!-- key: Q1 -->' "
                        "(or '<!-- key: case -->'); close each with '<!-- /key -->'" % where)
    for raw_id, body in found:
        kid = key_id(raw_id)
        tag = "%s, key %s" % (where, kid)
        bad = []
        if not KEY_ID_RE.match(kid):
            bad.append("%s: the id must be Q1, Q2, … (the question's number) or case" % tag)
        if kid in headers:
            bad.append("%s: there are two headers with this id" % tag)
        h = {}
        for n, line in enumerate(body.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^[-*+\s]*[*_`]*([A-Za-z][A-Za-z _-]*?)[*_`]*\s*:[*_`]*\s*(.*)$", line)
            if not m:
                bad.append("%s: line %d is not 'field: value'" % (tag, n))
                continue
            name = re.sub(r"[ -]+", "_", m.group(1).strip().lower())
            value = m.group(2).strip().strip("*_`").strip()
            if name in h:
                bad.append("%s: '%s' is given twice" % (tag, name))
            h[name] = value
        typ = (h.get("type") or "").lower()
        h["type"] = typ
        if typ not in KEY_TYPES:
            bad.append("%s: 'type' must be one of %s" % (tag, ", ".join(KEY_TYPES)))
            typ = None
        elif (typ == "case") != (kid == "case"):
            bad.append("%s: the case's header is '<!-- key: case -->' and has type case; questions are Q1, Q2, …" % tag)
        need = KEY_COMMON + (KEY_REQUIRED[typ] if typ else ())
        for f in need:
            if (h.get(f) or "").lower() in KEY_EMPTY:
                bad.append("%s: '%s' is missing" % (tag, f))
        if typ:
            known = need + KEY_OPTIONAL[typ] + KEY_ANY
            for f in sorted(set(h) - set(known)):
                bad.append("%s: '%s' is not a field of a %s header (fields: %s)"
                           % (tag, f, typ, ", ".join(known)))
        for f in KEY_ANY + (KEY_OPTIONAL[typ] if typ else ()):
            if f in h and h[f].lower() in KEY_EMPTY:
                del h[f]
        if typ == "focused" and h.get("aspect"):
            h["aspect"] = h["aspect"].lower()
            if h["aspect"] not in FOCUSED_ASPECTS:
                bad.append("%s: 'aspect' must be one of %s" % (tag, ", ".join(FOCUSED_ASPECTS)))
        if h.get("reason", "").lower().replace(" ", "_") == "new_in_domain":
            h["reason"] = "new"         # the ledger knows one word for a topic's first appearance
        if bad:
            h["_bad"] = bad
            problems.extend(bad)
        if kid in headers:              # which of the two is meant cannot be told: neither is used
            headers[kid].setdefault("_bad", []).extend(b for b in bad if "two headers" in b)
        headers.setdefault(kid, h)
    return headers, problems


def key_headers(paths):
    """The key headers of a round's sealed files: ({id: header}, [problems], {file: [ids]})."""
    headers, problems, by_file = {}, [], {}
    for path in paths or []:
        name = os.path.basename(path)
        found, probs = parse_key_headers(read_text(path), name)
        problems.extend(probs)
        by_file[name] = list(found)
        for kid, h in found.items():
            if kid in headers:
                dup = "%s, key %s: another sealed file already has a header with this id" % (name, kid)
                problems.append(dup)
                headers[kid].setdefault("_bad", []).append(dup)
                continue
            headers[kid] = h
    return headers, problems, by_file


def fill_round_from_keys(rnd, sealed, plan=None):
    """Build the round record in place: every item of `rnd` that names a key ("key": "Q1") gets
    its topic, label, domain, stem summary, aspect and `retests` from that key's header, and the
    round gets the compact case, the selection reasons and, where it has none, a title and tags.
    A field the examiner did write wins and is listed under `overridden`. Raises CmeError, with
    every problem in one message, when a header an item names is missing or malformed.
    Returns None for a round that names no key (a round record written out in full)."""
    items = rnd.get("items") or []
    if not any(isinstance(it, dict) and it.get("key") for it in items):
        return None
    headers, header_problems, by_file = key_headers(sealed)
    problems, filled, overridden, graded = [], [], [], set()
    for n, it in enumerate(items, 1):
        if not it.get("key"):
            if not it.get("topic"):
                problems.append("round.json, item %d: it has neither \"key\" (the id of its key header, "
                                "e.g. \"Q1\" or \"case\") nor a topic" % n)
            continue
        kid = key_id(it["key"])
        h = headers.get(kid)
        if h is None:
            problems.append("round.json, item %d: no key header '<!-- key: %s -->' in %s (headers found: %s)"
                            % (n, kid, " or ".join(os.path.basename(p) for p in sealed or []) or "the sealed files "
                               "(none in the work folder)", ", ".join(headers) or "none"))
            continue
        if kid in graded:
            problems.append("round.json, item %d: key %s is already used by an earlier item" % (n, kid))
            continue
        graded.add(kid)
        if h.get("_bad"):
            problems.extend(h["_bad"])
            continue
        it["key"] = kid
        for f in KEY_ITEM_FIELDS:
            if f in it:
                if f in h and it[f] != h[f]:
                    overridden.append("%s.%s" % (kid, f))
            elif f in h:
                it[f] = h[f]
        if it.get("retests") is None:
            it.pop("retests", None)
        it.setdefault("domain", domain_of(it["topic"]))
        reasons = rnd.get("selection_reasons")
        if not isinstance(reasons, dict):
            reasons = rnd["selection_reasons"] = {}
        reasons.setdefault(it["topic"], h["reason"])
        if h["type"] == "case" and not rnd.get("case"):
            rnd["case"] = {f: h[f] for f in KEY_CASE_FIELDS if h.get(f)}
        filled.append(kid)
    if problems:
        die("the round record cannot be built from the keys: " + "; ".join(problems)
            + ". Correct the header in the sealed file (references/standards.md, rule 9), or the "
              "\"key\" in round.json, and run save again. Nothing was recorded.")
    if not rnd.get("case_format") and any(is_case(it) for it in items) and (plan or {}).get("case_format"):
        rnd["case_format"] = plan["case_format"]
    case = rnd.get("case") if any(is_case(it) for it in items) else None
    if not rnd.get("title"):
        if case and case.get("presentation"):
            rnd["title"] = clip(" — ".join(x for x in (case["presentation"], case.get("diagnosis")) if x), 90)
        else:
            rnd["title"] = clip(next((it["stem_summary"] for it in items if it.get("stem_summary")), None), 90)
    if not rnd.get("tags"):
        rnd["tags"] = sorted({it["topic"] for it in items if it.get("topic")})
    if not rnd.get("summary"):
        rnd["summary"] = " ".join(str(x) for x in (rnd.get("key_learning") or [])[:2]) or rnd.get("title")
    out = {"filled": filled, "not_graded": [k for k in headers if k not in graded]}
    if overridden:
        out["overridden"] = overridden
    # a header nobody graded (the learner stopped before the case) cannot block the save
    known = {p for kid in graded for p in headers[kid].get("_bad", [])}
    out["warnings"] = [p for p in header_problems if p not in known]
    return out


def check_key_headers(paths, plan=None):
    """Check the key headers of sealed files before a round is played: ({file: [ids]}, [problems]).
    Every item needs a well-formed header; with `plan`, each file written must have as many
    headers of each type as the plan has items. The problems name files, keys and fields only."""
    headers, problems, by_file = key_headers(paths)
    for name, ids in by_file.items():
        if not ids and present_blocks(read_text(next(p for p in paths if os.path.basename(p) == name))):
            problems.append("%s: no key header; each item needs one ('<!-- key: Q1 -->' … '<!-- /key -->', "
                            "references/standards.md rule 9)" % name)
    if plan:
        want = plan.get("counts") or {}
        have = {"mcqs": 0, "focused": 0, "case": 0}
        for h in headers.values():
            k = {"mcq": "mcqs", "focused": "focused", "case": "case"}.get(h.get("type"))
            if k:
                have[k] += 1
        written = {os.path.basename(p) for p in paths}
        for k, name in (("mcqs", "MCQ"), ("focused", "focused-question"), ("case", "case")):
            part = "sealed_case.md" if k == "case" else "sealed_questions.md"
            if part in written and int(want.get(k) or 0) != have[k]:
                problems.append("%s: the plan has %d %s item(s), the keys have %d header(s) of that type"
                                % (part, int(want.get(k) or 0), name, have[k]))
    return by_file, problems


# What each field holds, for the table of references/standards.md (rule 9). The table there is
# printed by `key-table` from the KEY_* definitions above and these notes; tests/test_standards.py
# fails when the two differ, so the rulebook cannot drift from what the engine reads.
KEY_FIELD_NOTES = {
    "type": "`mcq`, `focused` or `case`",
    "topic": "the blueprint ID (for a `new_in_domain` item, the one you chose)",
    "label": "the topic's label in the blueprint",
    "reason": "the plan's `reason_code` for the item, copied as it is",
    "stem_summary": "about ten words on what the stem asks, for the list of stems already used",
    "aspect": "one of " + ", ".join("`%s`" % a for a in FOCUSED_ASPECTS),
    "patient": "age and sex (\"74F\")",
    "setting": "where the case takes place (\"ED\")",
    "presentation": "the presenting problem (\"confusion after a marathon\")",
    "diagnosis": "the final diagnosis",
    "twist": "what makes this case different from others on the topic",
    "domain": "the domain code, only when the topic ID does not start with it",
    "retests": "the plan's `retest_gap.id`, on an item written on that gap's decision point; "
               "otherwise leave the line out",
}
KEY_TABLE_OPEN = "<!-- key-header-table: generated by `cme.py key-table`; do not edit by hand -->"
KEY_TABLE_CLOSE = "<!-- /key-header-table -->"


def key_header_fields():
    """Every field a key header can have, in the order of the table."""
    seen = []
    for f in (KEY_COMMON + tuple(f for t in KEY_TYPES for f in KEY_REQUIRED[t])
              + tuple(f for t in KEY_TYPES for f in KEY_OPTIONAL[t]) + KEY_ANY):
        if f not in seen:
            seen.append(f)
    return seen


def key_header_table():
    """The key-header table of the rulebook, as Markdown, from the KEY_* definitions."""
    def cell(field, typ):
        if field in KEY_COMMON or field in KEY_REQUIRED[typ]:
            return "required"
        if field in KEY_OPTIONAL[typ] or field in KEY_ANY:
            return "optional"
        return "–"
    lines = ["| Field | MCQ | Focused question | Case | What to write |", "|---|---|---|---|---|"]
    for f in key_header_fields():
        lines.append("| `%s` | %s | %s | %s | %s |" % (f, cell(f, "mcq"), cell(f, "focused"), cell(f, "case"),
                                                       KEY_FIELD_NOTES[f]))
    return "\n".join(lines)


def cmd_key_table(args):
    """Print the key-header table for references/standards.md (between its two markers)."""
    sys.stdout.write("%s\n%s\n%s\n" % (KEY_TABLE_OPEN, key_header_table(), KEY_TABLE_CLOSE))


# ---------------------------------------------------------------- the lint of a written round
#
# The rulebook (references/standards.md) holds the rules for writing items. What can be checked
# mechanically is checked here, by `finish-prepare` (a round prepared ahead) and by `keys` (the
# author's own check), in two categories:
#
#   blocking   definite problems: a malformed key header (rule 9, check_key_headers) and a kit
#              or kit section that is missing (rule 8). Nothing is stashed.
#   review     judgement calls, found by heuristics: an abbreviation in the presented text that
#              is not spelled out at first use (rule 5) and time anchors that look mixed
#              (rule 6). The author revises once; what is still found is accepted with a warning.
#
# The lint prints file names, key ids, section names and counts only. What it found (the
# abbreviations, the phrases) names content, so it goes to lint.md beside the sealed files.

STANDARDS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "references", "standards.md")
LINT_FILE = "lint.md"
KIT_FOR = {"sealed_questions.md": "kit_questions.md", "sealed_case.md": "kit_case.md"}
# Rule 8: the sections a kit must have, each under a Markdown heading that starts with the name.
# kit_questions.md has one heading per question ("## Q1") instead, and "Reading" only in a round
# without a case. Reserved for issue #50 (podcast candidates): a "Listening" section, not yet required.
KIT_CASE_SECTIONS = ("Reveal", "Model answer", "Rubric", "Differential", "Briefing", "Pearls", "Reading")
KIT_READING = "Reading"
HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]*(.+?)[ \t#:]*$", re.M)

# Rule 5: the abbreviations that need no spelling out are listed in the rulebook, between these
# two markers. That list is the only source: there is no copy of it here.
ABBREVIATIONS_RE = re.compile(r"<!--\s*common-abbreviations\s*-->(.*?)<!--\s*/common-abbreviations\s*-->", re.S)
ABBREVIATION_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,6})s?(?![A-Za-z0-9])")
ROMAN_RE = re.compile(r"^[IVX]+$")

# Rule 6: phrases that count from now, and phrases that count from a numbered day.
_NUM = r"(?:\d+|an?|one|two|three|four|five|six|seven|eight|nine|ten|twelve|few|several|couple of)"
_ORD = r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
TIME_NOW_RE = re.compile(
    r"\b" + _NUM + r"\s+(?:minutes?|mins?|hours?|hrs?|days?|nights?|weeks?)\s+ago\b"
    r"|\bsince\s+(?:this\s+morning|yesterday|last\s+night|last\s+week)\b"
    r"|\b(?:this\s+morning|yesterday|last\s+night|earlier\s+today)\b", re.I)
TIME_DAY_RE = re.compile(
    r"\bday\s*\d+\b|\bday\s+(?:zero|one|two|three|four|five|six|seven|eight|nine|ten)\b"
    r"|\b(?:hospital|admission|post-?operative|post-?op|treatment|ICU)\s+day\b"
    r"|\b" + _ORD + r"\s+(?:hospital\s+|admission\s+|post-?operative\s+)?day\b|\bPOD\s*\d+\b", re.I)
QUESTION_START_RE = re.compile(r"(?m)^(?=[ \t>*_#]{0,6}(?:Question|Q)[ \t]*\d+)")


def common_abbreviations(path=None):
    """The abbreviations the rulebook lists as needing no spelling out (rule 5), or None when the
    rulebook or its list cannot be read."""
    try:
        m = ABBREVIATIONS_RE.search(read_text(path or STANDARDS_FILE))
    except OSError:
        return None
    if not m:
        return None
    return {w for w in re.split(r"[\s,;]+", m.group(1).strip()) if w}


def kit_headings(text):
    return [h.strip().strip("*_`").strip().lower() for h in HEADING_RE.findall(text or "")]


def kit_problems(files, plan=None, kits_required=True):
    """Rule 8, the mechanical part: every kit is there and has its sections. Names files, key ids
    and section names only."""
    problems = []
    for sealed, kit in KIT_FOR.items():
        if sealed not in files or not present_blocks(files[sealed]):
            continue
        if kit not in files:
            if kits_required:
                problems.append("%s is missing" % kit)
            continue
        heads = kit_headings(files[kit])
        if kit == "kit_case.md":
            want = list(KIT_CASE_SECTIONS)
        else:
            ids = [k for k in parse_key_headers(files[sealed], sealed)[0] if k != "case"]
            missing = [k for k in ids if not any(re.match(r"%s\b" % re.escape(k.lower()), h) for h in heads)]
            if missing:
                problems.append("%s: no section for %s (one heading per question, '## Q1')"
                                % (kit, ", ".join(missing)))
            counts = (plan or {}).get("counts") or {}
            want = [KIT_READING] if plan and not counts.get("case") else []
        missing = [name for name in want if not any(h.startswith(name.lower().rstrip("s")) for h in heads)]
        if missing:
            problems.append("%s: section%s %s missing (a heading for each: %s)"
                            % (kit, "" if len(missing) == 1 else "s", ", ".join("'%s'" % m for m in missing),
                               ", ".join("'## %s'" % m for m in missing)))
    return problems


def presented_text(files):
    """The text the learner is shown, in the order of a session: [(file, block, text)]. The
    results bank counts: Stage 2 is assembled from it."""
    out = []
    q = present_blocks(files.get("sealed_questions.md")).get("questions")
    if q:
        out.append(("sealed_questions.md", "questions", q))
    case = files.get("sealed_case.md")
    c = present_blocks(case).get("case")
    if c:
        out.append(("sealed_case.md", "case", c))
        bank = "\n".join(v for _, v in BANK_RE.findall(case or "")).strip()
        if bank:
            out.append(("sealed_case.md", "bank", bank))
    return out


def undefined_abbreviations(blocks_in_order, common):
    """Rule 5 as a heuristic: all-caps tokens of two to six letters (a plural s allowed) that are
    not on the rulebook's list and, where the session first shows them, have neither an expansion
    in brackets after them ("ABC (…)") nor stand in brackets after one ("… (ABC)").
    [(file, block, token)], each token once."""
    seen, found = set(), []
    for name, block, text in blocks_in_order:
        for m in ABBREVIATION_RE.finditer(text):
            token = m.group(1)
            if token in seen:
                continue
            seen.add(token)
            if token in common or ROMAN_RE.match(token):
                continue
            if re.match(r"s?[ \t]*\(", text[m.end(1):]) or re.search(r"\([ \t]*$", text[:m.start(1)]):
                continue
            found.append((name, block, token))
    return found


def mixed_time_anchors(blocks_in_order):
    """Rule 6 as a heuristic: one case (or one short question) that counts time both from now
    ("3 hours ago", "since this morning") and from a numbered day ("day 3", "hospital day").
    [(file, where, [phrases from now], [phrases by day])]."""
    units = []
    case = [(n, t) for n, b, t in blocks_in_order if n == "sealed_case.md"]
    for name, block, text in blocks_in_order:
        if block == "questions":
            for i, part in enumerate([p for p in QUESTION_START_RE.split(text) if p.strip()], 1):
                m = re.match(r"[ \t>*_#]*(?:Question|Q)[ \t]*(\d+)", part)
                units.append((name, "question %s" % (m.group(1) if m else i), part))
    if case:
        units.append(("sealed_case.md", "the case (present block and bank)", "\n".join(t for _, t in case)))
    found = []
    for name, where, text in units:
        now = sorted({m.group(0).lower() for m in TIME_NOW_RE.finditer(text)})
        day = sorted({m.group(0).lower() for m in TIME_DAY_RE.finditer(text)})
        if now and day:
            found.append((name, where, now, day))
    return found


def lint_round(files, plan=None, kits_required=True, standards=None):
    """Lint a written round ({file name: text}) against the rulebook: {"blocking": [...],
    "review": [...], "notes": [...]}. Key headers are checked separately (check_key_headers)."""
    lint = {"blocking": kit_problems(files, plan, kits_required), "review": [], "notes": []}
    shown = presented_text(files)
    common = common_abbreviations(standards)
    if common is None:
        lint["notes"].append("the abbreviation list of references/standards.md (rule 5) could not be read: "
                             "abbreviations were not checked")
    else:
        for name, block, token in undefined_abbreviations(shown, common):
            lint["review"].append({"rule": 5, "file": name, "where": "%s block" % block, "detail": token})
    for name, where, now, day in mixed_time_anchors(shown):
        lint["review"].append({"rule": 6, "file": name, "where": where,
                               "detail": "from now: %s; by numbered day: %s"
                                         % (", ".join('"%s"' % x for x in now), ", ".join('"%s"' % x for x in day))})
    return lint


def lint_lines(lint):
    """The judgement calls as lines that name no content: file, rule and a count."""
    lines = []
    for name in sorted({r["file"] for r in lint["review"]}):
        n5 = sum(1 for r in lint["review"] if r["file"] == name and r["rule"] == 5)
        n6 = sum(1 for r in lint["review"] if r["file"] == name and r["rule"] == 6)
        if n5:
            lines.append("%s: %d abbreviation%s not spelled out at first use (references/standards.md, rule 5)"
                         % (name, n5, "" if n5 == 1 else "s"))
        if n6:
            lines.append("%s: time anchors look mixed in %d place%s (references/standards.md, rule 6)"
                         % (name, n6, "" if n6 == 1 else "s"))
    return lines


def lint_summary(lint, details=None):
    out = {"abbreviations": sum(1 for r in lint["review"] if r["rule"] == 5),
           "time_anchors": sum(1 for r in lint["review"] if r["rule"] == 6)}
    if lint["review"]:
        out["where"] = lint_lines(lint)
        if details:
            out["details"] = details
    return out


def write_lint_details(folder, lint):
    """Write what the lint found to <folder>/lint.md for the author (it names content, so it is
    never printed), or remove an earlier one when nothing is found. Returns the path or None."""
    path = os.path.join(folder, LINT_FILE)
    if not lint["review"]:
        if os.path.exists(path):
            os.remove(path)
        return None
    titles = {5: "Rule 5: abbreviations not spelled out at first use in the presented text",
              6: "Rule 6: more than one time anchor in one case or question"}
    lines = ["# Lint: judgement calls (references/standards.md)", "",
             "Sealed like the keys: this file names content. Only the author reads it.",
             "Each line is a heuristic's finding: correct the text where the rule is broken, leave it "
             "where the finding is wrong.", ""]
    for rule in (5, 6):
        rows = [r for r in lint["review"] if r["rule"] == rule]
        if rows:
            lines += ["## %s" % titles[rule], ""]
            lines += ["- %s, %s: %s" % (r["file"], r["where"], r["detail"]) for r in rows]
            lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return os.path.abspath(path)


def cmd_keys(args):
    """The author's last step (`finish-prepare` runs the same checks before it stashes): check the
    key headers of sealed files and, for a folder, the kits' sections and the lint's judgement
    calls. Prints which keys each file has, `problems` (what would stop `finish-prepare`) and
    `review` (counts of what the lint would send back; the findings themselves go to lint.md in
    the folder); never a topic or any other value."""
    paths, folder = [], None
    for p in args.paths:
        if os.path.isdir(p):
            folder = folder or p
            paths += [os.path.join(p, n) for n in SEALED_FILES if os.path.isfile(os.path.join(p, n))]
        elif os.path.isfile(p):
            paths.append(p)
        else:
            die("not found: %s" % p)
    if not paths:
        die("no sealed files (%s) in %s" % (", ".join(SEALED_FILES), ", ".join(args.paths)))
    plan = load_json(args.plan) if args.plan else None
    by_file, problems = check_key_headers(paths, plan)
    files = {os.path.basename(p): read_text(p) for p in paths}
    if folder:
        for kit in KIT_FOR.values():
            if os.path.isfile(os.path.join(folder, kit)):
                files[kit] = read_text(os.path.join(folder, kit))
    # a kit not written yet (Parts: questions) is no problem here; finish-prepare requires it
    lint = lint_round(files, plan, kits_required=False)
    problems = problems + lint["blocking"]
    out = {"ok": not problems, "keys": by_file, "problems": problems, "review": lint_lines(lint)}
    if folder:
        details = write_lint_details(folder, lint)
        if details:
            out["details"] = details
    if lint["notes"]:
        out["warnings"] = lint["notes"]
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0 if not problems else 1


# ---------------------------------------------------------------- the work folder
#
# One job is worked on in one scratch folder: a round, or a settings change, a theme change,
# a review, or preparing the next round. `open` (or `start --store`) notes there where the
# local copy of the learner's store is; from then on every command needs only `--work`.
#
#   <work>/work.json      what `open` noted: the store copy, the ledger as read, the session id
#   <work>/plan.json, sealed_*.md, kit_*.md, evidence_*.md, answers.md, stage2.md,
#          feedback_questions.md, feedback.md, round.json, reflection.json, B.md
#                         the files of the round, each under its fixed name
#   <work>/next/          the next round: its plan and drafts (`prepare`, `finish-prepare`)
#   <work>/publish/       the publish set: the newest version of every store file this job
#                         changed, at its store path (data/state.json, data/sessions/…)
#   <work>/publish.json   the publish set's manifest: the store version read and the files
#                         in write order, the ledger last
#   <work>/earlier/<n>/   the files of an earlier job in the same folder, set aside
#
# The current ledger of a job is the one in the publish set, or the one read while nothing
# has been written. Any other store file is looked up in the publish set first, then in the
# store copy.

WORK_FILE = "work.json"                 # written by open/start: the store copy, the ledger read, the page settings
ANSWERS_FILE = "answers.md"             # written by answer, one block per part
ANSWER_PARTS = ("questions", "case", "final", "notes", "reflection")
SEALED_FILES = ("sealed_questions.md", "sealed_case.md")
STAGE2_FILE = "stage2.md"               # Stage 2 exactly as sent
FEEDBACK_QUESTIONS_FILE = "feedback_questions.md"
FEEDBACK_FILE = "feedback.md"
ROUND_FILE = "round.json"
REFLECTION_FILE = "reflection.json"
PART_A_FILE = "A.md"                    # written by save: part A as it went into the session document
PART_B_FILE = "B.md"
BEFORE_SAVE_FILE = "before_save.json"   # the ledger as it was before this round was recorded (save can run again)
BEFORE_CLOSE_FILE = "before_close.json"  # the ledger as save left it (close can run again)
VERIFY_FILE = "verify.json"
PUBLISH_DIR = "publish"
PUBLISH_FILE = "publish.json"
EARLIER_DIR = "earlier"
# what one round leaves in the work folder, and what a whole job leaves
ROUND_FILES = PREPARED_FILES + (ANSWERS_FILE, STAGE2_FILE, FEEDBACK_QUESTIONS_FILE, FEEDBACK_FILE, ROUND_FILE,
                                RECORD_FILE, REFLECTION_FILE, PART_A_FILE, PART_B_FILE, BEFORE_SAVE_FILE,
                                BEFORE_CLOSE_FILE, VERIFY_FILE, PLAN_FILE, NEXT_DIR)
JOB_FILES = ROUND_FILES + (WORK_FILE, PUBLISH_FILE, PUBLISH_DIR)
REFLECTION_HEADING_RE = re.compile(r"^###\s+Reflection\b", re.M)
ANSWER_MARK_RE = re.compile(r"<!--\s*/?\s*answers\b")
# The write order of the publish set: log entries before the page file that lists them, the
# ledger last, so an interrupted write never leaves a ledger that points at a missing file.
PUBLISH_FIRST = ("data/sessions/", "data/reviews/", "data/testing/")
PUBLISH_LAST = (PAGE_PATH, "index.html", PREPARED_PATH, STATE_PATH)


def read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def work_info(work):
    """What `open` noted in the work folder ({} when no job was opened there)."""
    path = os.path.join(work, WORK_FILE)
    info = load_json(path) if os.path.isfile(path) else {}
    return info if isinstance(info, dict) else {}


def job(args):
    """(work folder, what `open` noted there) for a command that works on an open job."""
    work = args.work
    info = work_info(work)
    if not info:
        die("no job is open in the work folder %s: read the store into a folder and run `open --work %s "
            "--store DIR` first (`start --work %s --store DIR` for a round)" % (work, work, work))
    return work, info


def in_work(work, name):
    """The path of a file in the work folder, or None when it is not there."""
    path = os.path.join(work, name) if work else None
    return path if path and os.path.isfile(path) else None


def store_copy_file(store, rel):
    """A store file in a local copy of the store: at its store path, or flat (the data/ folder
    left out, or the bare file name), as a read tool may have saved it."""
    if not store:
        return None
    cands = [os.path.join(store, *rel.split("/"))]
    if rel.startswith("data/"):
        cands.append(os.path.join(store, *rel.split("/")[1:]))
    cands.append(os.path.join(store, os.path.basename(rel)))
    return next((p for p in cands if os.path.isfile(p)), None)


def store_file(work, info, rel):
    """The newest version this job has of a store file: the publish set's, else the store
    copy's, else None."""
    return in_work(work, os.path.join(PUBLISH_DIR, *rel.split("/"))) or store_copy_file(info.get("store"), rel)


def current_ledger(work, info):
    """(ledger, its path): the ledger in the publish set, else the ledger as it was read."""
    path = in_work(work, os.path.join(PUBLISH_DIR, *STATE_PATH.split("/"))) or info.get("state")
    if not path or not os.path.isfile(path):
        die("no ledger in the work folder %s: run `open --work %s --store DIR` on a fresh read of the store "
            "(for a new learner: `init --work %s …`)" % (work, work, work))
    st = load_json(path)
    check_schema(st)
    return st, path


def has_session(st, sid):
    return any(s.get("id") == sid for s in (st.get("sessions") or []) + (st.get("previous") or []))


def publish_path(work, rel):
    path = os.path.abspath(os.path.join(work, PUBLISH_DIR, *rel.split("/")))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def publish_json(work, rel, obj):
    """Put a JSON document into the publish set at its store path; returns the local path."""
    path = publish_path(work, rel)
    save_json(obj, path)
    return path


def publish_text(work, rel, text):
    path = publish_path(work, rel)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def publish_order(rel):
    if rel in PUBLISH_LAST:
        return (2, PUBLISH_LAST.index(rel), rel)
    return (0 if rel.startswith(PUBLISH_FIRST) else 1, 0, rel)


def publish_set(work, info):
    """Rebuild the manifest (<work>/publish.json) from what the publish set holds and return its
    files, [{"as": store path, "path": local file}], in write order: the ledger last."""
    root = os.path.join(work, PUBLISH_DIR)
    rels = []
    for folder, _, names in os.walk(root):
        for n in names:
            if not n.startswith("."):
                rels.append(os.path.relpath(os.path.join(folder, n), root).replace(os.sep, "/"))
    files = [{"as": rel, "path": os.path.abspath(os.path.join(root, *rel.split("/")))}
             for rel in sorted(rels, key=publish_order)]
    save_json({"version": info.get("version"), "files": files}, os.path.join(work, PUBLISH_FILE))
    return files


def published(work, info, out):
    """Add the whole publish set to what a writing command prints: `files` in write order and
    `publish`, the manifest's path. Whoever carries files to the store publishes all of it."""
    out["files"] = publish_set(work, info)
    out["publish"] = os.path.abspath(os.path.join(work, PUBLISH_FILE))
    return out


def publish_page(work, info, st, session=None, review=None, fresh=False):
    """Put the page file for the ledger `st` into the publish set (with a new or changed session
    or review document, which is put there too). The lists of past sessions and reviews are
    carried on from the page file this job has (`fresh`: from nothing but the ledger)."""
    lists = page_lists(None if fresh else store_file(work, info, PAGE_PATH),
                       None if fresh else store_file(work, info, OLD_INDEX_PATH))
    if session:
        publish_json(work, session_path(session["id"]), session)
        page_put_session(lists, session)
    if review:
        publish_json(work, review_path(review["date"]), review)
        page_put_review(lists, review)
    return publish_json(work, PAGE_PATH, page_doc(st, lists))


def publish_ledger(work, info, st, out, session=None, review=None, empty_prepared=False, fresh_page=False):
    """Put the ledger `st` into the publish set with what goes with it: the page file (with a new
    session or review document, which is put there too), an emptied prepared round when the
    change makes the prepared one unusable, and the page if the learner's is out of date.
    Notes `page_upgraded` and warnings in `out`; returns the ledger's local path."""
    path = publish_json(work, STATE_PATH, st)
    publish_page(work, info, st, session=session, review=review, fresh=fresh_page)
    if empty_prepared:
        publish_json(work, PREPARED_PATH, {"v": 1, "empty": True})
    warnings = []
    up = page_upgrade(work, info, warnings)
    if up:
        out["page_upgraded"] = up
    if warnings:
        out["warnings"] = list(out.get("warnings") or []) + warnings
    return path


def set_aside(work, names):
    """Move the named files and folders of the work folder into earlier/<n>/; returns that
    folder, or None when none of them is there."""
    there = [n for n in names if os.path.exists(os.path.join(work, n))]
    if not there:
        return None
    earlier = os.path.join(work, EARLIER_DIR)
    n = 1
    while os.path.exists(os.path.join(earlier, str(n))):
        n += 1
    dest = os.path.join(earlier, str(n))
    os.makedirs(dest)
    for name in there:
        os.replace(os.path.join(work, name), os.path.join(dest, name))
    return os.path.abspath(dest)


def set_aside_earlier_job(work):
    """A new job in a work folder that holds an earlier one: move everything of the earlier job
    (its answers and feedback, its publish set, its next round) into earlier/<n>/, so nothing
    of it can end up in the new job's log or publish set. Nothing happens in a folder where no
    job has got as far as an answer, a draft of the next round or a written file."""
    if not any(os.path.exists(os.path.join(work, n)) for n in (ANSWERS_FILE, RECORD_FILE, PUBLISH_DIR, NEXT_DIR)):
        return None
    return set_aside(work, JOB_FILES)


def set_aside_round(work):
    """A round started in a job that already holds a round's files (a late reflection closed
    first, or a second round): move the earlier round's files aside. The publish set stays:
    it is the job's, and the new round continues from its ledger."""
    if not any(os.path.exists(os.path.join(work, n)) for n in (ANSWERS_FILE, RECORD_FILE)):
        return None
    return set_aside(work, ROUND_FILES)


def open_work(work, store, version, prefs, today, reread=False):
    """Set up the work folder for one job from `store`, the local copy of the learner's store
    as it was just read (the store's layout, or its files side by side). Returns (what was
    noted in work.json, the ledger, what to add to the printed status).
    `reread`: the same job on a fresh read of the store, after a publish was refused because
    the store had moved on. The job's own files stay (answers, feedback, round.json, the next
    round's drafts); what was computed from the old read goes, and the commands are run again."""
    store = os.path.abspath(store)
    if not os.path.isdir(store):
        die("the store copy %s is not a folder: read the store's files into a folder first" % store)
    ledger = store_copy_file(store, STATE_PATH)
    if not ledger:
        die("no ledger (%s, or state.json) in the store copy %s. A new learner has none yet: "
            "set up with `init --work %s …`" % (STATE_PATH, store, work))
    st = load_json(ledger)
    check_schema(st)
    os.makedirs(work, exist_ok=True)
    inside = os.path.relpath(store, os.path.abspath(work)).split(os.sep)[0]
    if inside in JOB_FILES + (EARLIER_DIR,):
        die("the store copy cannot be %s inside the work folder: that name is the engine's. "
            "Read the store into another folder, for example <work>/store" % inside)
    extra = {"work": os.path.abspath(work), "store": store, "store_version": version,
             "store_layout": "data" if ledger.endswith(os.path.join("data", "state.json")) else "flat",
             "store_files": [rel for rel in (STATE_PATH, PAGE_PATH, OLD_INDEX_PATH, PREPARED_PATH, "index.html")
                             if store_copy_file(store, rel)]}
    earlier = in_work(work, os.path.join(PUBLISH_DIR, *STATE_PATH.split("/")))
    earlier_gen = None
    if earlier:
        try:
            earlier_gen = int(load_json(earlier).get("gen") or 0)
        except (CmeError, AttributeError, TypeError, ValueError):
            earlier_gen = None
    if reread:
        if not work_info(work):
            die("--reread continues a job after a refused publish, and no job is open in %s" % work)
        for name in (PUBLISH_DIR, BEFORE_SAVE_FILE, BEFORE_CLOSE_FILE, VERIFY_FILE):
            path = os.path.join(work, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)
        prefs = prefs if prefs is not None else work_info(work).get("prefs")
        extra["reread"] = True
    aside = None if reread else set_aside_earlier_job(work)
    if aside:
        extra["earlier_set_aside"] = aside
        if earlier_gen is not None and earlier_gen > int(st.get("gen") or 0):
            extra["warnings"] = ["the store copy (gen %s) is older than the ledger the earlier job in this work "
                                 "folder wrote (gen %s): read the store again if that job was published; if its "
                                 "publish failed, its files are in %s"
                                 % (st.get("gen"), earlier_gen, os.path.join(aside, PUBLISH_DIR))]
    info = {"store": store, "state": os.path.abspath(ledger), "session_id": st.get("next_id"),
            "version": version, "prefs": prefs, "started": iso(today)}
    save_json(info, os.path.join(work, WORK_FILE))
    publish_set(work, info)
    return info, st, extra


def answer_blocks(path):
    """[(part, text)] of an answers file, in the order they were added."""
    if not path or not os.path.isfile(path):
        return []
    return [(name, body.strip()) for name, body in ANSWER_RE.findall(read_text(path))]


def cmd_answer(args):
    """Append what the learner answered for one part to the work folder's answers.md, as it was
    written. Earlier parts are never rewritten; the same text for the same part is added once."""
    if not os.path.isdir(args.work):
        die("work folder not found: %s" % args.work)
    if args.file:
        try:
            text = read_text(args.file)
        except OSError:
            die("file not found: %s" % args.file)
    elif args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()
    text = text.strip("\n")
    if not text.strip():
        die("no answer text: give --file, --text, or the text on standard input")
    if ANSWER_MARK_RE.search(text):
        die("the text holds an answers marker (<!-- answers … -->); remove that line and add it again")
    path = os.path.join(args.work, ANSWERS_FILE)
    have = answer_blocks(path)
    out = {"ok": True, "part": args.part, "chars": len(text)}
    if (args.part, text.strip()) in have:
        out["already_added"] = True
    else:
        before = read_text(path) if os.path.isfile(path) else ""
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(("\n" if before and not before.endswith("\n") else "")
                     + "<!-- answers: %s -->\n%s\n<!-- /answers -->\n" % (args.part, text))
        have.append((args.part, text.strip()))
    out["parts"] = [name for name, _ in have]
    print(json.dumps(out, ensure_ascii=False))


def cmd_save(args):
    """First save after the feedback: record the round, the session document (part A) and the
    page file, in one go, into the publish set. Everything is found in the work folder by its fixed
    name. It starts from the ledger as it was before this round: the current ledger (so a
    settings change made earlier in the same job is kept), or, when that already holds this
    round, the ledger the first run started from; so it can be run again with the same result."""
    work, info = job(args)
    today = today_from(args)
    round_src = in_work(work, ROUND_FILE)
    if not round_src:
        die("save needs %s in the work folder" % ROUND_FILE)
    rnd = load_json(round_src) or {}
    cur, _ = current_ledger(work, info)
    sid = rnd.get("log_id") or info.get("session_id") or cur.get("next_id")
    if info.get("closed") == sid:
        die("round %s is already closed in this work folder: saving it again would undo its reflection" % sid)
    before = os.path.join(work, BEFORE_SAVE_FILE)
    if not has_session(cur, sid):
        st_in, first_run = cur, True
    else:
        st_in, first_run = load_json(in_work(work, BEFORE_SAVE_FILE) or info.get("state") or before), False
        check_schema(st_in)
        if has_session(st_in, sid):
            die("the ledger read from the store already holds round %s: start the round again on a fresh "
                "read of the store (`start --work %s --store DIR`)" % (sid, work))
    sealed = [p for p in (in_work(work, n) for n in SEALED_FILES) if p]
    answers = [p for p in (in_work(work, ANSWERS_FILE),) if p]
    feedback = in_work(work, FEEDBACK_FILE)
    feedback_questions = in_work(work, FEEDBACK_QUESTIONS_FILE)
    stage2 = in_work(work, STAGE2_FILE)
    rnd["log_id"] = sid
    if not rnd.get("date"):
        rnd["date"] = iso(today)
    warnings = []
    # the round record: what the author wrote in the key headers + what the examiner graded
    plan_path = in_work(work, PLAN_FILE)
    keys = fill_round_from_keys(rnd, sealed, load_json(plan_path) if plan_path else None)
    if keys:
        warnings.extend(keys.pop("warnings"))
    if not feedback and not feedback_questions:
        die("save needs the feedback as sent: %s in the work folder" % FEEDBACK_FILE)
    st = copy.deepcopy(st_in)       # st_in stays the ledger as it was before this round
    # the round mix set on the page is kept in the ledger from now on
    prefs_changes = apply_prefs(st, info.get("prefs"), warnings)
    md = assemble_part_a(sealed, answers, feedback,
                         rnd.get("item_order") or st["config"].get("item_order"), warnings,
                         feedback_questions, read_text(stage2) if stage2 else None)
    res = record_round(st, copy.deepcopy(rnd), today)
    if first_run:                   # nothing failed: keep the ledger this round started from
        save_json(st_in, before)
    doc = session_doc_a(rnd, sid, md)
    rec = {}
    path = publish_ledger(work, info, st, rec, session=doc, empty_prepared=True)
    rec = report(path, os.path.getsize(path), dict(res, **rec))
    with open(os.path.join(work, PART_A_FILE), "w", encoding="utf-8") as fh:
        fh.write(md)
    if os.path.isfile(os.path.join(work, BEFORE_CLOSE_FILE)):
        os.remove(os.path.join(work, BEFORE_CLOSE_FILE))
    if prefs_changes:
        rec["page_settings_applied"] = prefs_changes
    if keys:
        rec["keys"] = keys
    save_json(rnd, os.path.join(work, RECORD_FILE))     # the round record as recorded, beside round.json
    if block_end(st):
        rec["next_block"] = block_end(st)       # tell the learner its `line` in the closing message
    rec["warnings"] = list(rec.get("warnings") or []) + warnings
    rec["transcript_chars"] = len(md)
    print(json.dumps(published(work, info, rec), indent=1, ensure_ascii=False))


def cmd_close(args):
    """Second save after the reflection: apply the reflection, add part B to the session
    document, update the page file, all into the publish set. It continues from the current ledger
    (what `save` wrote in this job, or the ledger as read when the reflection is given at a
    later session) and reads reflection.json, B.md and the reflection added with `answer` from
    the work folder; the session document comes from the publish set or the store copy."""
    work, info = job(args)
    today = today_from(args)
    reflection = args.reflection or in_work(work, REFLECTION_FILE)
    if not reflection:
        die("close needs the reflection: %s in the work folder, or --reflection '<json>'" % REFLECTION_FILE)
    st, _ = current_ledger(work, info)
    before = os.path.join(work, BEFORE_CLOSE_FILE)
    again = not st.get("unreflected") and info.get("closed") and os.path.isfile(before)
    if again:                       # run again after a correction: from the ledger the first run started from
        st = load_json(before)
        check_schema(st)
    st_before = copy.deepcopy(st)
    res = reflect_round(st, load_json_arg(reflection) or {}, today, args.session)
    sid = res["session_id"]
    md_path = in_work(work, PART_B_FILE)
    md_b = read_text(md_path) if md_path else ""
    said = "\n\n".join(body for name, body in answer_blocks(in_work(work, ANSWERS_FILE)) if name == "reflection")
    if said and not REFLECTION_HEADING_RE.search(md_b):
        md_b = "### Reflection (verbatim)\n\n%s\n\n%s" % (said, md_b.lstrip("\n"))
    if not md_b.strip():
        die("close needs part B: %s in the work folder, or the reflection added with "
            "`answer --part reflection`" % PART_B_FILE)
    doc_path = store_file(work, info, session_path(sid))
    if not doc_path:
        die("the session file of %s was not found: read %s from the store into the store copy "
            "(%s) first" % (sid, session_path(sid), info.get("store")))
    doc = load_json(doc_path)
    if doc.get("id") and doc["id"] != sid:
        die("session document %s does not match the reflected session %s" % (doc.get("id"), sid))
    doc["closing"] = md_b
    doc["reflected"] = True
    doc.pop("learner_changes", None)        # close can run again: only this run's count
    if res.get("learner_changes"):          # in the log whoever wrote part B: both scores, who closed the gap
        doc["learner_changes"] = res["learner_changes"]
        doc["closing"] = md_b.rstrip() + "\n\n" + learner_changes_md(res["learner_changes"], "### Set by the learner")
    sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
    if sess and isinstance(sess.get("score"), (int, float)):
        doc["score"] = sess["score"]
    ref = {}
    path = publish_ledger(work, info, st, ref, session=doc)
    page_warn = ref.pop("warnings", [])
    ref = report(path, os.path.getsize(path), dict(res, **ref))
    ref["warnings"] = list(ref.get("warnings") or []) + page_warn
    if not again:
        save_json(st_before, before)
    info["closed"] = sid
    save_json(info, os.path.join(work, WORK_FILE))
    if block_end(st):
        ref["next_block"] = block_end(st)       # tell the learner its `line` in the closing message
    print(json.dumps(published(work, info, ref), indent=1, ensure_ascii=False))


def same_content(a, b):
    if a.endswith(".json"):
        try:
            return load_json(a) == load_json(b)
        except CmeError:
            return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def cmd_verify(args):
    """Testing mode: compare the publish set with what the store holds after the save (a fresh
    read of the store in --store). Writes <work>/verify.json."""
    work, info = job(args)
    wanted = publish_set(work, info)
    if not wanted:
        die("verify: the publish set of %s is empty, nothing was written in this job" % work)
    missing, mismatched = [], []
    for f in wanted:
        got = store_copy_file(args.store, f["as"])
        if not got:
            missing.append(f["as"])
        elif not same_content(f["path"], got):
            mismatched.append(f["as"])
    res = {"ok": not missing and not mismatched, "checked": len(wanted), "missing": missing,
           "mismatched": mismatched}
    save_json(res, os.path.join(work, VERIFY_FILE))
    print(json.dumps(res, indent=1))


def job_session(work, info, st, session=None):
    """The session a job's note or addendum belongs to: the one named, else this job's round
    when it is recorded, else the round closed in this job, else the last one in the ledger."""
    if session:
        return session
    for sid in (info.get("session_id"), info.get("closed")):
        if sid and has_session(st, sid):
            return sid
    log = (st.get("previous") or []) + (st.get("sessions") or [])
    if not log:
        die("the ledger holds no session yet")
    return log[-1].get("id")


def cmd_testing_note(args):
    """Testing mode: the learner's quick feedback and the store check (<work>/verify.json, when
    `verify` was run), added to the publish set as data/testing/<id>.json."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    sid = job_session(work, info, st, args.session)
    fb = load_json_arg(args.feedback) or {}
    ver = in_work(work, VERIFY_FILE)
    note = {"session": sid, "date": iso(today), "skill_version": SKILL_VERSION,
            "feedback": fb, "store_check": load_json(ver) if ver else None}
    publish_json(work, "data/testing/%s.json" % sid, note)
    print(json.dumps(published(work, info, {"ok": True, "session": sid}), indent=1))


def cmd_addendum(args):
    """Append a discussion that continued after the close to a session document (default: the
    last session), into the publish set."""
    work, info = job(args)
    st, _ = current_ledger(work, info)
    sid = job_session(work, info, st, args.session)
    doc_path = store_file(work, info, session_path(sid))
    if not doc_path:
        die("the session file of %s was not found: read %s from the store into the store copy "
            "(%s) first" % (sid, session_path(sid), info.get("store")))
    doc = load_json(doc_path)
    try:
        add = read_text(args.md).strip()
    except OSError:
        die("file not found: %s" % args.md)
    doc["addendum"] = ((doc.get("addendum") or "").rstrip() + "\n\n" + add).strip() + "\n"
    publish_json(work, session_path(doc.get("id") or sid), doc)
    print(json.dumps(published(work, info, {"ok": True, "session": sid, "chars": len(doc["addendum"])})))


def layout_file(root, rel, obj):
    """Write a store document into a folder in the store's layout (the maintenance tools)."""
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_json(obj, path)
    return {"as": rel, "path": os.path.abspath(path)}


def cmd_rebuild_page(args):
    """Maintenance: rebuild data/page.json in a folder holding the store's layout, from the
    session and review files and the ledger (the old name of this command is `reindex`). A page
    file or an old index already there supplies the entries of sessions whose files are missing."""
    root = args.root
    ledger = os.path.join(root, *STATE_PATH.split("/"))
    if not os.path.exists(ledger):
        die("no ledger at %s: the page file is built from the ledger and the session files" % ledger)
    st = load_json(ledger)
    check_schema(st)
    lists = page_lists(store_copy_file(root, PAGE_PATH), store_copy_file(root, OLD_INDEX_PATH))
    sdir = os.path.join(root, "data", "sessions")
    for fn in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        if fn.endswith(".json"):
            page_put_session(lists, load_json(os.path.join(sdir, fn)))
    rdir = os.path.join(root, "data", "reviews")
    for fn in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        if fn.endswith(".json"):
            page_put_review(lists, load_json(os.path.join(rdir, fn)))
    page = page_doc(st, lists)
    f = layout_file(root, PAGE_PATH, page)
    print(json.dumps({"ok": True, "files": [f], "sessions": len(page["sessions"]), "reviews": len(page["reviews"])}))


def cmd_import(args):
    """Split a page export ({state, sessions, reviews}) into the file layout, ready to publish
    or copy: session and review files first, then the page file, the ledger last."""
    src = load_json(args.export)
    state = src.get("state") if isinstance(src, dict) else None
    if not state:
        die("the export has no 'state' (a Clinical CME page export is {state, sessions, reviews})")
    check_schema(state)
    os.makedirs(args.out_dir, exist_ok=True)
    files = []
    lists = {"sessions": [], "reviews": []}
    for d in src.get("sessions") or []:
        if not d.get("id"):
            continue
        files.append(layout_file(args.out_dir, session_path(d["id"]), d))
        page_put_session(lists, d)
    for r in src.get("reviews") or []:
        date = r.get("date") or r.get("id")
        if not date:
            continue
        r = dict(r, date=date)
        files.append(layout_file(args.out_dir, review_path(date), r))
        page_put_review(lists, r)
    files.append(layout_file(args.out_dir, PAGE_PATH, page_doc(state, lists)))
    files.append(layout_file(args.out_dir, STATE_PATH, state))
    print(json.dumps({"ok": True, "gen": state.get("gen"), "next_id": state.get("next_id"),
                      "sessions": len(src.get("sessions") or []), "reviews": len(src.get("reviews") or []),
                      "files": files}, indent=1, ensure_ascii=False))


def cmd_review_doc(args):
    """Wrap a review report (Markdown) as data/reviews/<date>.json and list it in the page file,
    both into the publish set."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    try:
        text = read_text(args.md)
    except OSError:
        die("file not found: %s" % args.md)
    date = args.date or iso(today)
    doc = {"date": date, "title": args.title or "CME progress review — %s" % date,
           "headline": args.headline, "report": text}
    publish_page(work, info, st, review=doc)
    print(json.dumps(published(work, info, {"ok": True, "doc": "reviews/%s" % date}), ensure_ascii=False))


# ---------------------------------------------------------------- main

PLAN_FLAGS = ("--allow-repeat", "--no-drill", "--force-drill", "--no-new", "--no-case")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cme.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def command(name, fn, work=True):
        s = sub.add_parser(name)
        if work:
            s.add_argument("--work", required=True)
        s.set_defaults(fn=fn)
        return s

    s = command("open", cmd_open); s.add_argument("--store", required=True); s.add_argument("--version")
    s.add_argument("--prefs"); s.add_argument("--reread", action="store_true")
    s = command("start", cmd_start); s.add_argument("--store"); s.add_argument("--version"); s.add_argument("--prefs")
    s.add_argument("--focused", type=int); s.add_argument("--mcqs", type=int); s.add_argument("--domain")
    s.add_argument("--seed", type=int); s.add_argument("--no-prepared", action="store_true")
    for flag in PLAN_FLAGS:
        s.add_argument(flag, action="store_true")
    s = command("answer", cmd_answer); s.add_argument("--part", required=True, choices=ANSWER_PARTS)
    s.add_argument("--file"); s.add_argument("--text")
    s = command("present", cmd_present, work=False); s.add_argument("files", nargs="*"); s.add_argument("--work")
    s.add_argument("--block", required=True)
    s = command("save", cmd_save)
    s = command("close", cmd_close); s.add_argument("--reflection"); s.add_argument("--session")
    s = command("addendum", cmd_addendum); s.add_argument("--md", required=True); s.add_argument("--session")
    s = command("override", cmd_override); s.add_argument("--scores"); s.add_argument("--close-gaps")
    s.add_argument("--session")
    s = command("prepare", cmd_prepare); s.add_argument("--if-needed", action="store_true")
    s.add_argument("--allow-unreflected", action="store_true")
    s = command("finish-prepare", cmd_finish_prepare); s.add_argument("--revised", action="store_true")
    s.add_argument("--no-evidence", action="store_true")
    s = command("keys", cmd_keys, work=False); s.add_argument("paths", nargs="+"); s.add_argument("--plan")
    s = command("key-table", cmd_key_table, work=False)
    s = command("verify", cmd_verify); s.add_argument("--store", required=True)
    s = command("testing-note", cmd_testing_note); s.add_argument("--feedback", required=True); s.add_argument("--session")
    s = command("stats", cmd_stats); s.add_argument("--all", action="store_true")
    s = command("review", cmd_review); s.add_argument("--review", required=True)
    s = command("review-doc", cmd_review_doc); s.add_argument("--md", required=True); s.add_argument("--date")
    s.add_argument("--title"); s.add_argument("--headline")
    s = command("snooze", cmd_snooze); s.add_argument("--days", type=int, default=7)
    s = command("settings", cmd_settings); s.add_argument("--config"); s.add_argument("--profile"); s.add_argument("--blueprint")
    s = command("theme", cmd_theme); s.add_argument("--set"); s.add_argument("--another", action="store_true")
    s = command("init", cmd_init); s.add_argument("--profile", default="{}"); s.add_argument("--config", default="{}")
    s.add_argument("--blueprint", required=True); s.add_argument("--start-over", action="store_true")
    # maintenance tools, outside the protocol: they take their own files and folders
    s = command("validate", cmd_validate, work=False); s.add_argument("state", nargs="?"); s.add_argument("--work")
    for name in ("rebuild-page", "reindex"):        # reindex: the name it had while the page read an index
        s = command(name, cmd_rebuild_page, work=False); s.add_argument("root")
    s = command("import", cmd_import, work=False); s.add_argument("export"); s.add_argument("--out-dir", required=True)
    s = command("blueprint-md", cmd_blueprint_md, work=False); s.add_argument("file"); s.add_argument("--out", required=True)

    for p in sub.choices.values():
        p.add_argument("--today", dest="today_sub")
    args = ap.parse_args(argv)
    if getattr(args, "today_sub", None):
        args.today = args.today_sub
    try:
        return args.fn(args) or 0
    except CmeError as e:
        print(json.dumps({"ok": False, "error": e.msg}, ensure_ascii=False))
        return e.code


if __name__ == "__main__":
    sys.exit(main())

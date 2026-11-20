#!/usr/bin/env python3
"""clinical-cme v4.3.1 state engine (standard library only, Python 3.8+).

The learner's scheduling memory is ONE JSON document, the state; each round also has a session
document, and an index lists the sessions for the page. This script never talks to a store or
to any assistant tool: the assistant fetches the files from wherever the learner's store is
(see references/store.md), runs a command here, and puts the files it writes back. Every
command that writes takes --out or --out-dir and prints, for each file, its store path ("as",
e.g. data/state.json) and its database path ("db_path", e.g. cme/state).

Session (fast path):
  start   STATE --out PLAN [plan options] [--prefs J] [--prepared PREPARED.json]
                                                  neutral status + plan in one call (no topics); with a
                                                  valid prepared round, also the questions to present
  save    STATE --round R.json --sealed F.. --answers F.. [--feedback-questions FQ.md] --feedback FB.md
          [--index IDX] [--prefs J] [--page LIVE_INDEX.html] --out-dir D
                                                  record the graded round + session doc (part A) + index
  close   STATE --reflection R.json --md B.md --doc SESSION.json [--index IDX] --out-dir D
                                                  apply the reflection + part B + index
  addendum --doc SESSION.json --md ADD.md --out-dir D
  prepare STATE --out NEXT_PLAN [--if-needed PREPARED.json] [--allow-unreflected]
                                                  after the close: plan the NEXT round (prints counts only)
  stash   STATE --plan NEXT_PLAN --dir DRAFTS --out-dir D   keep the round drafted for it for the next start
  present SEALED.. --block questions|case|stage2  print only the text to show the learner

Other:
  status  STATE | plan STATE --out PLAN | record | reflect | doc   (single steps; used by save/close)
  stats   STATE [--all]                           figures and coded analysis for a progress review
  review  STATE --review REVIEW.json --out NEXT   record a completed review; starts a new period
  review-doc --md REPORT.md [--headline H] [--state S --index IDX] --out-dir D
  snooze  STATE --days N --out NEXT
  settings STATE [--config JSON] [--profile JSON] [--blueprint F] --out NEXT
  place   STATE [--index IDX] --out-dir D          put a state from review/settings/snooze/init in the layout
  init    --profile JSON --config JSON --blueprint FILE(.json|.md) --out STATE
  import  EXPORT.json|FOLDER --out-dir D          page export {state, sessions, reviews}, or a folder of
                                                  database documents (cme/, sessions/, reviews/) -> file layout
  reindex ROOT                                    rebuild ROOT/data/index.json
  blueprint-md FILE --out BP.json | migrate-v3 LEDGER --blueprint F --out STATE [--sessions-dir D]
  unescape FILE --out FILE | validate STATE

Add `--today YYYY-MM-DD` before the command to fix the date.
"""
import argparse
import base64
import datetime as dt
import json
import os
import random
import re
import sys
import tempfile
import zlib

SCHEMA = 4
SKILL_VERSION = "4.3.1"
PAGE_VERSION = "5.0.0"   # templates/page.html carries <meta name="cme-page-version" content="5.0.0">

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
    "guideline_region": "Europe",
    "item_order": "mcqs_first",          # mcqs_first: questions -> their feedback -> case -> its feedback
    "helpers": True,                     # helper agents where the app has them: an author drafts the items, a
                                         # checker verifies the evidence; the conversation grades
    "prepare_ahead": True,               # draft the whole next round after each close
    "prepare_task": False,
    "testing": False,                    # testing mode: feedback check + store check at the end of each round               # a scheduled task also prepares the round when none is ready
    "show_coding": True,
    "reminders": False,
    "mirror": None,                      # null | "gdrive": also create a Google Doc per session
    "resource_preferences": {"free_only": False, "formats": ["guidelines", "review articles"]},
}
DEFAULT_PROFILE = {
    "display_name": None, "role": None, "specialty": None, "subspecialty": None,
    "practice_setting": [], "goals": [], "strengths": [], "weaknesses": [],
    "domain_self_ratings": {}, "domain_emphasis": {}, "notes": "", "onboarded_at": None,
}
SELF_RATING_FACTOR = {1: 1.6, 2: 1.3, 3: 1.0, 4: 0.8, 5: 0.6}
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
ITEM_TYPES = ("case", "essay", "mcq", "focused")      # "essay" = version-3 name for a case
FOCUSED_ASPECTS = ("diagnosis", "interpretation", "testing", "management", "disposition",
                   "prevention", "prognosis")
# Drills that can be built into a mini-case (used only when the round has no full case).
FOCUSED_DRILLS_EXCLUDED = ("bias:anchoring", "bias:search_satisficing", "art:PR", "art:DDX")
ROUND_LIMITS = {"mcqs": (0, 10), "focused": (0, 6)}
# Rough minutes per item, answering plus reading its feedback; used for the plan's estimate only.
MINUTES_PER = {"mcq": 3, "focused": 5, "unfolding": 15, "discriminate": 10}
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
CAP_ERRATA = 40
CLIP_GAP = 400
CLIP_ELEMENT = 220
CLIP_EVIDENCE = 140


# ---------------------------------------------------------------- utilities

def die(msg, code=2):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(code)


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
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=False)
    os.replace(tmp, path)
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


def apply_prefs(state, prefs, warnings=None):
    """Apply the round mix the learner set on their page (database document cme/prefs).

    prefs = {"round": {"mcqs": 2, "focused": 1, "case": true}, "base": <config.round_set_at the
    page saw>, "updated": "<ISO time of the change>"}. Applied only when `base` still equals the
    ledger's round_set_at: a change made later in a chat (settings) moves round_set_at, so an older
    page setting is then ignored, and an applied one is not applied twice. No clocks are compared.
    An invalid page setting is ignored with a warning, never fatal. Returns the changes applied."""
    if not prefs:
        return {}
    warnings = warnings if warnings is not None else []
    if not isinstance(prefs, dict) or not isinstance(prefs.get("round"), dict) or not prefs.get("updated"):
        warnings.append("page settings ignored: expected {round: {...}, base, updated}")
        return {}
    cfg = state["config"]
    if prefs.get("base") != cfg.get("round_set_at"):
        return {}     # already applied, or overtaken by a later change in a chat
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


def deep_merge(target, changes):
    for k, v in (changes or {}).items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_merge(target[k], v)
        else:
            target[k] = v


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
            "disputes": {"learner_right": 0, "both_defensible": 0, "upheld": 0},
            "reflection_skipped": 0}


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
    interval = max(1, int(interval))
    return k_new, today + dt.timedelta(days=interval), calibration, interval


def adjusted_item_mastery(item):
    m = float(item.get("mastery", 0))
    conf = (item.get("confidence") or "").lower() or None
    correct = item.get("correct")
    misconception = False
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
    m = it.get("mastery")
    return None if m is None else max(0.0, min(1.0, float(m) / 5.0))


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


def cmd_status(args):
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
    print(json.dumps(status_dict(st, args.state, today), ensure_ascii=False))


def check_schema(st):
    if not isinstance(st, dict) or st.get("schema") != SCHEMA:
        die("not a version-%d state file (schema=%r). A version-3 ledger must be converted with "
            "migrate-v3 first." % (SCHEMA, (st or {}).get("schema")))
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
        w *= SELF_RATING_FACTOR.get(r, 1.0)
        try:
            w *= float(emphasis.get(d, 1.0))
        except (TypeError, ValueError):
            pass
        eff[d] = max(w, 0.0)
    return eff


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


def cmd_plan(args, st=None):
    today = today_from(args)
    if st is None:
        st = load_json(args.state)
        check_schema(st)
        apply_prefs(st, load_json_arg(getattr(args, "prefs", None)))   # warnings: shown by start
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

    tested_today = {tid for tid, t in topics.items() if parse_date(t.get("last")) == today}
    recent = set()
    for s in log[-3:]:
        recent.update(s.get("topics") or [])
    recent_domains = [domain_of(t) for s in log[-10:] for t in (s.get("topics") or [])]

    def allowed(tid):
        if tid in tested_today and not args.allow_repeat:
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
        lt, gd = parse_date((topics.get(tid) or {}).get("last")), parse_date(g.get("date"))
        if lt is None or gd is None or lt <= gd:
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
            return "not yet tested; chosen by domain weight (blueprint, your self-ratings, emphasis)"
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
        if level <= 1 and not restrict and domain in case_domains:
            return False
        if level == 0 and domain in used_domains:
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

    def take_short(slot, new_only=False):
        for level in (0, 1, 2):
            if level == 2 and not restrict and [d for d in eff if d not in case_domains]:
                break
            item = take(slot, level, new_only)
            if item:
                item["separation"] = ("no case this round; unrelated to the other questions"
                                      if not case_topics else
                                      "same domain as the case (domain round), unrelated topic"
                                      if item["domain"] in case_domains else
                                      "other domain" if level == 0 else "other domain than the case")
                return item
        return None

    for _ in range(n_case):
        item = take("case")
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
    for i, slot in enumerate(shorts):
        item = None
        if reserve_new and i == len(shorts) - 1 and not any(c["reason_code"].startswith("new") for c in chosen):
            item = take_short(slot, new_only=True)
        item = item or take_short(slot)
        if item:
            chosen.append(item); used_topics.add(item.get("topic")); used_domains.append(item["domain"])

    fmt = cfg.get("case_format", "unfolding")
    if fmt == "alternate":
        last_fmt = next((s.get("format") for s in reversed(log) if s.get("format")), None)
        fmt = "discriminate" if last_fmt == "unfolding" else "unfolding"
    if int(cfg.get("session_minutes", 20) or 20) <= 12 and fmt == "unfolding":
        fmt = "discriminate"

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
    est = (MINUTES_PER["mcq"] * len(by_slot["mcq"]) + MINUTES_PER["focused"] * len(by_slot["focused"])
           + (MINUTES_PER[fmt] if by_slot["case"] else 0))
    plan = {
        "ok": True, "date": iso(today), "session_id": st.get("next_id"),
        "case_format": fmt if by_slot["case"] else None,
        "item_order": order,
        "presentation_order": ["%s %s" % (c["slot"], c.get("topic") or c.get("domain")) for c in present],
        "counts": {"mcqs": len(by_slot["mcq"]), "focused": len(by_slot["focused"]), "case": len(by_slot["case"])},
        "estimated_minutes": est,
        "lab_units": cfg.get("lab_units"), "blood_gas_units": cfg.get("blood_gas_units"),
        "guideline_region": cfg.get("guideline_region"), "session_minutes": cfg.get("session_minutes"),
        "feedback_depth": cfg.get("feedback_depth"), "show_coding": cfg.get("show_coding", True),
        "helpers": bool(cfg.get("helpers", True)), "prepare_ahead": bool(cfg.get("prepare_ahead", True)),
        "testing": bool(cfg.get("testing", False)),
        "profile": {k: st["profile"].get(k) for k in ("role", "specialty", "subspecialty",
                                                        "practice_setting", "notes")},
        "recent_cases_any_topic": used_cases[-15:],
        "items": chosen,
        "pending_errata": st.get("pending_errata") or [],
        "note": "Blind: do not reveal topics, domains, reasons or the drill before all answers are "
                "in. Make every vignette and stem clearly different from already_used and "
                "recent_cases_any_topic (patient, setting, presentation, twist). MCQs and focused "
                "questions are presented together and get their feedback before the case is shown; "
                "neither they nor their feedback may cue the case.",
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"ok": True, "out": args.out, "items": len(chosen),
                      "mcqs": len(by_slot["mcq"]), "focused": len(by_slot["focused"]), "case": len(by_slot["case"]),
                      "case_format": fmt if by_slot["case"] else None, "estimated_minutes": est,
                      "item_order": order, "session_id": st.get("next_id")}))


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
    if typ == "focused" and it.get("aspect"):
        out["aspect"] = it["aspect"]
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
    if (s.get("reflection") or {}).get("skipped"):
        agg["reflection_skipped"] += 1


def apply_round(state, rnd, today):
    """Pure application of a graded round to the state. Returns (summary, warnings)."""
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
    gap_index = {g.get("topic"): g for g in state["gaps"]}
    for tid, items in by_topic.items():
        t = ensure_topic(state, tid, items[0].get("domain"), next((i.get("label") for i in items if i.get("label")), None))
        adj = [adjusted_item_mastery(i) for i in items]
        mastery = round_half(sum(m for m, _ in adj) / len(adj))
        misconception = any(mc for _, mc in adj)
        comfort = comfort_map.get(tid)
        try:
            comfort = None if comfort is None else max(1, min(5, int(round(float(comfort)))))
        except (TypeError, ValueError):
            comfort = None
        step, due, calibration, interval = schedule_topic(t.get("step"), mastery, comfort, misconception,
                                                          tid in self_gap_topics, intervals, rdate)
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
                gaps.remove(existing)
            gaps.append(entry); gap_index[tid] = entry
            for n in notes:
                state["resolved"].append({"topic": tid, "note": clip(n, 200), "resolved": iso(rdate), "partial": True})
        elif existing and tid in by_topic:
            ex_date = parse_date(existing.get("date"))
            if mastery is not None and mastery >= 4 and cal not in ("overconfident", "confident_error") \
                    and (ex_date is None or ex_date < rdate):
                gaps.remove(existing); del gap_index[tid]
                state["resolved"].append({"topic": tid, "note": clip(existing.get("gap"), 200),
                                          "opened": existing.get("opened") or existing.get("date"),
                                          "resolved": iso(rdate), "partial": False})
                summary.setdefault(tid, {})["gap_resolved"] = True
            else:
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
           "drill": sess.get("drill"), "grade_changes": [{"outcome": g.get("outcome")} for g in sess.get("grade_changes") or []],
           "reflection": {"skipped": bool((sess.get("reflection") or {}).get("skipped"))}}
    if sess.get("case"):
        out["case"] = {k: sess["case"].get(k) for k in ("topic", "presentation", "diagnosis") if sess["case"].get(k)}
    if sess.get("url"):
        out["url"] = sess["url"]
    return out


def cmd_record(args):
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
    rnd = load_json_arg(args.round)
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
    snap = snapshot(st)
    entry, summary, warnings, errata_ids = apply_round(st, rnd, today)
    if rnd.get("reflection") is None:
        entry["_snapshot"] = snap
        entry["_round"] = rnd
        st["unreflected"] = entry["id"]
    compact(st)
    st["gen"] = int(st.get("gen") or 0) + 1
    size = save_json(st, args.out)
    print(json.dumps({"ok": True, "out": args.out, "bytes": size, "gen": st["gen"], "session_id": entry["id"],
                      "next_id": st["next_id"], "score": entry["score"], "topics": summary,
                      "errata_ids": errata_ids,
                      "errata_to_log": [e for e in st["errata"] if e.get("id") in errata_ids],
                      "open_gaps": len(st["gaps"]), "reflection_pending": rnd.get("reflection") is None,
                      "warnings": warnings}, indent=1, ensure_ascii=False))


def cmd_reflect(args):
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
    refl = load_json_arg(args.reflection) or {}
    sid = args.session or st.get("unreflected")
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
    entry, summary, warnings, errata_ids = apply_round(st, rnd, today)
    st["unreflected"] = None
    compact(st)
    st["gen"] = int(st.get("gen") or 0) + 1
    size = save_json(st, args.out)
    print(json.dumps({"ok": True, "out": args.out, "bytes": size, "gen": st["gen"], "session_id": entry["id"],
                      "topics": summary, "open_gaps": len(st["gaps"]), "errata_ids": errata_ids,
                      "errata_to_log": [e for e in st["errata"] if e.get("id") in errata_ids],
                      "warnings": warnings}, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- session document

def cmd_doc(args):
    with open(args.md, "r", encoding="utf-8") as fh:
        md = fh.read()
    if args.part == "A":
        rnd = load_json_arg(args.round) or {}
        st = load_json(args.state) if args.state else None
        sid = args.id or rnd.get("log_id") or rnd.get("id") or (st or {}).get("next_id")
        if not sid:
            die("part A needs --id, or --round with log_id, or --state")
        doc = {"id": sid, "date": rnd.get("date") or iso(today_from(args)),
               "title": rnd.get("title"), "summary": rnd.get("summary"), "tags": rnd.get("tags") or [],
               "topics": sorted({it.get("topic") for it in rnd.get("items") or [] if it.get("topic")}),
               "score": None, "format": round_format(rnd), "drill": (rnd.get("drill") or {}).get("code"),
               "transcript": md, "closing": None, "reflected": False}
        if rnd.get("items"):
            ms = [adjusted_item_mastery(it)[0] for it in rnd["items"]]
            doc["score"] = round(sum(ms) / len(ms), 2)
    else:
        doc = {"closing": md, "reflected": True}
    save_json(doc, args.out)
    print(json.dumps({"ok": True, "out": args.out, "part": args.part, "chars": len(md)}))


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
        "grade_disputes": {"n": len(gch), "outcomes": {o: sum(1 for g in gch if g.get("outcome") == o)
                                                       for o in ("learner_right", "both_defensible", "upheld")}},
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
        "reflection_skipped": agg["reflection_skipped"],
    }


def cmd_stats(args):
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
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
        "gaps_resolved": [g for g in st["resolved"] if parse_date(g.get("resolved")) and start and parse_date(g["resolved"]) >= start],
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
    st = load_json(args.state)
    check_schema(st)
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
    st["gen"] = int(st.get("gen") or 0) + 1
    st["updated"] = iso(today)
    size = save_json(st, args.out)
    print(json.dumps({"ok": True, "out": args.out, "bytes": size, "gen": st["gen"], "reviews": len(st["reviews"]),
                      "next_review_due": iso(next_due), "drills": st["drills"],
                      "pending_errata": [e["id"] for e in st["pending_errata"]], "warnings": warnings}, indent=1))


def cmd_snooze(args):
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
    st["review"]["next_due"] = iso(today + dt.timedelta(days=args.days))
    st["gen"] = int(st.get("gen") or 0) + 1
    st["updated"] = iso(today)
    save_json(st, args.out)
    print(json.dumps({"ok": True, "out": args.out, "gen": st["gen"], "next_review_due": st["review"]["next_due"]}))


def cmd_settings(args):
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
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
        text = open(args.blueprint, encoding="utf-8").read()
        bp = json.loads(text) if args.blueprint.endswith(".json") else blueprint_from_md(text)
        st["blueprint"] = bp
    st["gen"] = int(st.get("gen") or 0) + 1
    st["updated"] = iso(today)
    save_json(st, args.out)
    print(json.dumps({"ok": True, "out": args.out, "gen": st["gen"], "config": st["config"],
                      "review": st["review"]}, ensure_ascii=False))


# ---------------------------------------------------------------- init, blueprint, migrate

def cmd_init(args):
    today = today_from(args)
    st = new_state(today)
    deep_merge(st["profile"], load_json_arg(args.profile) or {})
    deep_merge(st["config"], load_json_arg(args.config) or {})
    st["profile"]["onboarded_at"] = iso(today)
    check_round_mix(st["config"])
    st["config"]["round_set_at"] = st["config"].get("round_set_at") or now_ts()
    text = open(args.blueprint, encoding="utf-8").read()
    st["blueprint"] = json.loads(text) if args.blueprint.endswith(".json") else blueprint_from_md(text)
    iv = int(st["config"].get("review_interval_days") or 42)
    st["review"] = {"last": None, "next_due": iso(today + dt.timedelta(days=iv)), "period_start": iso(today)}
    st["gen"] = 1
    size = save_json(st, args.out)
    print(json.dumps({"ok": True, "out": args.out, "bytes": size, "domains": list(st["blueprint"]),
                      "topics": len(bp_topics(st))}))


def cmd_blueprint_md(args):
    bp = blueprint_from_md(open(args.file, encoding="utf-8").read())
    save_json(bp, args.out)
    print(json.dumps({"ok": True, "out": args.out, "domains": list(bp), "topics": sum(len(v["topics"]) for v in bp.values())}))


def unescape_drive_text(text):
    """read_file_content escapes markdown characters in a Google Doc's text; undo it."""
    return re.sub(r"\\([\\_\[\]<>~*#`+\-.!|{}()])", r"\1", text)


def cmd_unescape(args):
    raw = open(args.file, encoding="utf-8").read()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "fileContent" in obj:
            raw = obj["fileContent"]
    except json.JSONDecodeError:
        pass
    text = unescape_drive_text(raw)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(json.dumps({"ok": True, "out": args.out, "chars": len(text)}))


def cmd_migrate_v3(args):
    today = today_from(args)
    L = load_json(args.ledger)
    st = new_state(today)
    st["created"] = L.get("created") or iso(today)
    cfg3, prof3 = L.get("config") or {}, L.get("profile") or {}
    c = st["config"]
    for k in ("session_minutes", "case_format", "feedback_depth", "target_sessions_per_week",
              "review_interval_days", "intervals_days", "new_topics_per_round", "lab_units",
              "blood_gas_units", "guideline_region", "item_order", "show_coding", "resource_preferences"):
        if k in cfg3:
            c[k] = cfg3[k]
    c["reminders"] = bool(cfg3.get("reminders"))
    ds = cfg3.get("default_session") or {}
    c["mcqs"] = int(ds.get("mcqs", 3)); c["case"] = int(ds.get("essays", 1)) > 0
    p = st["profile"]
    for k in ("display_name", "role", "specialty", "subspecialty", "practice_setting", "goals",
              "strengths", "weaknesses", "notes", "onboarded_at", "domain_emphasis"):
        if prof3.get(k) is not None:
            p[k] = prof3[k]
    p["domain_self_ratings"] = {d: (r.get("rating") if isinstance(r, dict) else r)
                                for d, r in (prof3.get("domain_self_ratings") or {}).items()}
    if not p.get("onboarded_at"):
        p["onboarded_at"] = st["created"]
    text = open(args.blueprint, encoding="utf-8").read()
    st["blueprint"] = json.loads(text) if args.blueprint.endswith(".json") else blueprint_from_md(text)
    for tid, t in (L.get("topics") or {}).items():
        if not isinstance(t, dict):
            continue
        st["topics"][tid] = {"domain": (t.get("domain") or domain_of(tid)).upper(), "label": t.get("label") or tid,
                             "last": t.get("last_tested"), "attempts": t.get("attempts") or 0,
                             "mastery": t.get("mastery"), "step": t.get("sr_step") or 0, "due": t.get("next_due"),
                             "comfort": t.get("self_comfort"), "calibration": t.get("calibration"),
                             "history": [[h.get("date"), h.get("mastery"), h.get("comfort"), h.get("calibration")]
                                         for h in (t.get("history") or [])][-CAP_HISTORY:]}
    for g in L.get("open_gaps") or []:
        if isinstance(g, dict) and g.get("topic"):
            src = g.get("source") or ["graded"]
            st["gaps"].append({"topic": g["topic"], "gap": clip(g.get("gap"), CLIP_GAP),
                               "self": clip(g.get("self_reported"), 200) or None,
                               "source": [src] if isinstance(src, str) else src, "date": g.get("date"),
                               "opened": g.get("opened") or g.get("date")})
    for g in (L.get("resolved_gaps") or [])[-CAP_RESOLVED:]:
        st["resolved"].append({"topic": g.get("topic"), "note": clip(g.get("gap") or g.get("note"), 200),
                               "opened": g.get("opened"), "resolved": g.get("resolved"), "partial": bool(g.get("partial"))})
    docs = ((L.get("gdocs") or {}).get("sessions") or {})
    for s in L.get("session_log") or []:
        sid = s.get("log_id")
        refl = s.get("reflection") or {}
        items = []
        for it in s.get("items") or []:
            raw = {"type": "mcq" if it.get("type") == "mcq" else "case", "topic": it.get("topic"),
                   "mastery": it.get("mastery"), "correct": it.get("correct"), "confidence": it.get("confidence"),
                   "coding": it.get("coding") or {"errors": []}}
            items.append(compact_item(raw))
        case = None
        for x in L.get("case_index") or []:
            if x.get("log_id") == sid and x.get("kind") != "mcq":
                case = {k: clip(x.get(k), 80) for k in ("patient", "setting", "presentation", "diagnosis", "twist") if x.get(k)}
                case["topic"] = x.get("topic")
        for x in L.get("case_index") or []:
            if x.get("log_id") == sid and x.get("kind") == "mcq":
                for it in items:
                    if it["type"] == "mcq" and it["topic"] == x.get("topic") and not it.get("stem"):
                        it["stem"] = clip(x.get("stem"), 90)
        entry = {"id": sid, "date": s.get("date"), "started_at": s.get("started_at"), "ended_at": s.get("ended_at"),
                 "minutes": s.get("minutes"), "reading_minutes": s.get("reading_minutes"),
                 "title": clip(s.get("title") or "Session %s" % sid, 120), "summary": clip(s.get("summary"), 300),
                 "tags": s.get("tags") or [], "topics": s.get("topic_ids") or [], "format": s.get("case_format"),
                 "mcqs": s.get("mcqs"), "mcq_correct": s.get("mcq_correct"), "score": s.get("mean_score"),
                 "items": items, "why": s.get("selection_reasons") or {}, "self_performance": s.get("self_performance"),
                 "self_comfort": s.get("self_comfort") if isinstance(s.get("self_comfort"), dict) else {},
                 "reflection": {"solid": clip(refl.get("solid"), 300), "gaps": clip(refl.get("gaps"), 300),
                                "skipped": bool(refl.get("skipped"))},
                 "key_learning": [clip(k, 200) for k in s.get("key_learning") or []],
                 "case": case, "grade_changes": s.get("grade_changes") or [], "drill": s.get("drill")}
        d = docs.get(sid) or {}
        if d.get("url"):
            entry["url"] = d["url"]
            entry["reconstructed"] = bool(d.get("reconstructed"))
        if s.get("errata"):
            entry["errata"] = s["errata"]
        st["sessions"].append(entry)
        agg_add_session(st["agg"], entry)
    st["sessions"].sort(key=lambda s: id_num(s.get("id")))
    st["next_id"] = "S%04d" % (max([id_num(s.get("id")) for s in st["sessions"]] + [0]) + 1)
    for r in L.get("reviews") or []:
        st["reviews"].append({"date": r.get("date"), "doc": r.get("report_file"),
                              "headline": clip((r.get("analysis") or {}).get("headline"), 400),
                              "change_plan": r.get("change_plan")})
    st["drills"] = L.get("drill_targets") or []
    st["errata"] = L.get("errata") or []
    st["pending_errata"] = L.get("pending_errata") or []
    st["teaching_point_checks"] = L.get("teaching_point_checks") or {}
    last_review = prof3.get("last_review")
    st["review"] = {"last": last_review,
                    "next_due": prof3.get("next_review_due") or iso(today + dt.timedelta(days=int(c.get("review_interval_days") or 42))),
                    "period_start": (iso(parse_date(last_review) + dt.timedelta(days=1)) if parse_date(last_review)
                                     else p.get("onboarded_at") or st["created"])}
    if last_review:   # sessions before the last review belong to the previous period
        cut = parse_date(last_review)
        prev = [s for s in st["sessions"] if parse_date(s.get("date")) and parse_date(s["date"]) <= cut]
        st["previous"] = [to_previous(s) for s in prev]
        st["sessions"] = [s for s in st["sessions"] if s not in prev]
    st["migrated_from"] = {"schema": L.get("schema_version"), "date": iso(today),
                           "sessions": len(L.get("session_log") or []), "gdocs": {k: v.get("url") for k, v in docs.items()}}
    compact(st)
    st["gen"] = 1
    st["updated"] = iso(today)
    size = save_json(st, args.out)
    if args.sessions_dir:
        os.makedirs(args.sessions_dir, exist_ok=True)
        for s in st["sessions"] + st["previous"]:
            d = docs.get(s["id"]) or {}
            doc = {"id": s["id"], "date": s.get("date"), "title": s.get("title"), "summary": s.get("summary"),
                   "tags": s.get("tags") or [], "topics": s.get("topics") or [], "score": s.get("score"),
                   "format": s.get("format"), "drill": (s.get("drill") or {}).get("code") if isinstance(s.get("drill"), dict) else None,
                   "transcript": None, "closing": None, "reflected": True, "url": d.get("url"),
                   "reconstructed": bool(d.get("reconstructed")), "migrated": True}
            save_json(doc, os.path.join(args.sessions_dir, "%s.json" % s["id"]))
    print(json.dumps({"ok": True, "out": args.out, "bytes": size, "topics": len(st["topics"]),
                      "sessions": len(st["sessions"]), "previous": len(st["previous"]), "gaps": len(st["gaps"]),
                      "next_id": st["next_id"], "domains": list(st["blueprint"]),
                      "session_docs": args.sessions_dir}, ensure_ascii=False))


def cmd_validate(args):
    st = load_json(args.state)
    check_schema(st)
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
    size = os.path.getsize(args.state)
    print(json.dumps({"ok": not problems, "bytes": size, "sessions": len(st["sessions"]),
                      "previous": len(st["previous"]), "topics": len(st["topics"]), "problems": problems}))
    sys.exit(0 if not problems else 1)


# ---------------------------------------------------------------- store layout, fast path

# Every store keeps the same documents. File stores use these relative paths; database stores
# use the matching document paths (cme/state, sessions/<id>, reviews/<date>; no index needed).
STATE_PATH = "data/state.json"
INDEX_PATH = "data/index.json"
PREPARED_PATH = "data/prepared.json"     # the next round's short questions, drafted ahead (see cmd_prepare)


def session_path(sid):
    return "data/sessions/%s.json" % sid


def review_path(date):
    return "data/reviews/%s.json" % date


def write_out(out_dir, rel, obj):
    path = os.path.join(out_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_json(obj, path)
    return {"as": rel, "path": os.path.abspath(path), "db_path": db_path_for(rel)}


def db_path_for(rel):
    if rel == STATE_PATH:
        return "cme/state"
    if rel == INDEX_PATH:
        return None
    if rel == PREPARED_PATH:
        return "cme/prepared"
    m = re.match(r"data/(sessions|reviews)/(.+)\.json$", rel)
    return "%s/%s" % (m.group(1), m.group(2)) if m else None


INDEX_SESSION_KEYS = ("id", "date", "title", "summary", "tags", "topics", "score", "format", "drill", "reflected")


def index_entry(doc):
    e = {k: doc.get(k) for k in INDEX_SESSION_KEYS}
    if doc.get("url"):
        e["url"] = doc["url"]
    if doc.get("migrated"):
        e["migrated"] = True
    return e


def load_index(path, state=None):
    """Read the index if present, then add any session the state knows that the index lacks.
    The index is rebuildable, so a missing or damaged one never loses log entries."""
    idx = None
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                idx = json.load(fh)
        except (OSError, json.JSONDecodeError):
            idx = None
    if not isinstance(idx, dict):
        idx = {}
    idx.setdefault("schema", 1)
    idx.setdefault("sessions", [])
    idx.setdefault("reviews", [])
    return add_state_to_index(idx, state)


def add_state_to_index(idx, state):
    if state:
        have = {e.get("id") for e in idx["sessions"]}
        for s in (state.get("previous") or []) + (state.get("sessions") or []):
            if s.get("id") and s["id"] not in have:
                d = s.get("drill")
                idx["sessions"].append({"id": s["id"], "date": s.get("date"), "title": s.get("title"),
                                        "summary": s.get("summary"), "tags": s.get("tags") or [],
                                        "topics": s.get("topics") or [], "score": s.get("score"),
                                        "format": s.get("format"),
                                        "drill": d.get("code") if isinstance(d, dict) else d,
                                        "reflected": s.get("id") != state.get("unreflected")})
        haver = {r.get("date") for r in idx["reviews"]}
        for r in state.get("reviews") or []:
            if r.get("date") and r["date"] not in haver and r.get("doc"):
                idx["reviews"].append({"date": r["date"], "title": "CME progress review — %s" % r["date"],
                                       "headline": r.get("headline")})
    return idx


def index_put_session(idx, doc):
    e = index_entry(doc)
    idx["sessions"] = [x for x in idx["sessions"] if x.get("id") != e["id"]] + [e]
    idx["sessions"].sort(key=lambda x: (x.get("date") or "", id_num(x.get("id"))))


def index_put_review(idx, doc):
    e = {"date": doc.get("date"), "title": doc.get("title"), "headline": doc.get("headline")}
    idx["reviews"] = [x for x in idx["reviews"] if x.get("date") != e["date"]] + [e]
    idx["reviews"].sort(key=lambda x: x.get("date") or "")


def finish_index(idx, state):
    idx["gen"] = state.get("gen")
    idx["updated"] = state.get("updated")
    idx["next_id"] = state.get("next_id")
    return idx


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
        "round": {"mcqs": cfg.get("mcqs", 3), "focused": cfg.get("focused", 0), "case": bool(cfg.get("case", True)),
                  "minutes": cfg.get("session_minutes"), "item_order": cfg.get("item_order")},
        "helpers": bool(cfg.get("helpers", True)), "prepare_ahead": bool(cfg.get("prepare_ahead", True)),
        "testing": bool(cfg.get("testing", False)),
        "prepare_task": bool(cfg.get("prepare_task", False)),
        "mirror": cfg.get("mirror"),
        "reminders": cfg.get("reminders"),
        "bytes": os.path.getsize(path),
        # true until the first save with version 4.3: tell the learner once about the speed settings
        "speed_settings_new": "helpers" not in cfg or "prepare_ahead" not in cfg,
    }


def cmd_start(args):
    """status + plan in one call. Prints neutral status and plan counts only (no topics)."""
    import contextlib
    import io
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
    prefs_warn = []
    prefs_changes = apply_prefs(st, load_json_arg(args.prefs), prefs_warn)
    status = status_dict(st, args.state, today)
    if prefs_changes:
        status["page_settings_applied"] = prefs_changes
    if prefs_warn:
        status["warnings"] = prefs_warn
    plan_out = None
    prepared = None
    if getattr(args, "prepared", None) and not status["onboarding_needed"]:
        prepared = take_prepared(args, st, today)
        status["prepared"] = {k: v for k, v in prepared.items()
                              if k in ("used", "why", "made", "ready", "present_block", "work_dir")}
        if prepared["used"]:
            plan_out = prepared["summary"]
            status["present"] = prepared["present"]
    if not status["onboarding_needed"] and plan_out is None:
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                cmd_plan(args, st)
        except SystemExit:
            sys.stdout.write(buf.getvalue())
            raise
        try:
            plan_out = json.loads(buf.getvalue().strip().splitlines()[-1])
        except (ValueError, IndexError):
            die("plan failed: %s" % buf.getvalue()[:300])
    status["plan"] = plan_out
    print(json.dumps(status, ensure_ascii=False))


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
    """After the close: plan the NEXT round as of tomorrow, so that the whole round (short
    questions, case, feedback notes) can be drafted now and the next session starts with
    nothing to write. Prints counts only."""
    import contextlib
    import io
    today = today_from(args)
    st = load_json(args.state)
    check_schema(st)
    cfg = st["config"]
    why = None
    if not cfg.get("prepare_ahead", True):
        why = "prepare_ahead is off"
    elif st.get("unreflected") and not args.allow_unreflected:
        why = "the last session is still waiting for its reflection"
    elif args.if_needed and prepared_fits(args.if_needed, st, today):
        why = "a round is already prepared"
    if why:
        print(json.dumps({"ok": True, "prepare": False, "why": why}))
        return
    ns = argparse.Namespace(state=args.state, out=args.out, today=iso(today + dt.timedelta(days=1)), prefs=None,
                            focused=None, mcqs=None, no_case=False, domain=None, no_new=False,
                            allow_repeat=False, no_drill=False, force_drill=False, seed=None)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            cmd_plan(ns, st)
    except SystemExit:
        sys.stdout.write(buf.getvalue())
        raise
    summary = json.loads(buf.getvalue().strip().splitlines()[-1])
    plan = load_json(args.out)
    plan["prepared"] = {"gen": st.get("gen"), "made": iso(today), "session_id": st.get("next_id")}
    save_json(plan, args.out)
    summary.update({"prepare": True, "gen": st.get("gen"),
                    "note": "Sealed: have the whole round drafted for this plan into one folder "
                            "(sealed_questions.md, sealed_case.md, kit_questions.md, kit_case.md), "
                            "then run stash --dir on it."})
    print(json.dumps(summary, ensure_ascii=False))


PREPARED_FILES = ("sealed_questions.md", "sealed_case.md", "kit_questions.md", "kit_case.md",
                  "evidence_questions.md", "evidence_case.md")


def present_blocks(text):
    return {k: v.strip() for k, v in PRESENT_RE.findall(text or "") if v.strip()}


def cmd_stash(args):
    """Keep the round drafted for next time in the store (data/prepared.json): the plan, the
    sealed short questions, the sealed case and the feedback notes, whichever were drafted."""
    st = load_json(args.state)
    check_schema(st)
    plan = load_json(args.plan)
    meta = plan.get("prepared") or {}
    if meta.get("gen") != st.get("gen"):
        die("this plan was not made by `prepare` from this ledger (gen %s, ledger %s)" % (meta.get("gen"), st.get("gen")))
    files = {}
    for name in PREPARED_FILES:
        path = os.path.join(args.dir, name)
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
        die("sealed_questions.md with a <!-- present: questions --> … <!-- /present --> block is missing in %s" % args.dir)
    if not short and "case" not in has:
        die("sealed_case.md with a <!-- present: case --> … <!-- /present --> block is missing in %s" % args.dir)
    if counts.get("case") and "case" not in has:
        files.pop("sealed_case.md", None); files.pop("kit_case.md", None); files.pop("evidence_case.md", None)
        warnings.append("no usable sealed_case.md: the case will be drafted at the next session")
    if not counts.get("case"):
        files.pop("sealed_case.md", None); files.pop("kit_case.md", None); files.pop("evidence_case.md", None)
    if "questions" not in has:
        files.pop("kit_questions.md", None); files.pop("evidence_questions.md", None)
    has += [n[:-3] for n in PREPARED_FILES[2:] if n in files]
    os.makedirs(args.out_dir, exist_ok=True)
    doc = {"v": 2, "gen": st.get("gen"), "made": meta.get("made"), "session_id": st.get("next_id"),
           "counts": counts, "has": has, "payload": pack({"plan": plan, "files": files})}
    f = write_out(args.out_dir, PREPARED_PATH, doc)
    out = {"ok": True, "gen": st.get("gen"), "has": has, "files": [f]}
    if warnings:
        out["warnings"] = warnings
    print(json.dumps(out, ensure_ascii=False))


def cmd_present(args):
    """Print only the text the learner is to see (one present block) from sealed files, so the
    assistant can send it without opening the keys. `--block bank` prints the case's results bank
    (results, course, Stage 2 questions), which is all that is needed to send Stage 2."""
    pres = blocks(args.files, BANK_RE if args.block == "bank" else PRESENT_RE)
    body = pres.get(args.block)
    if not body:
        die("no <!-- present: %s --> block in %s" % (args.block, ", ".join(args.files)))
    sys.stdout.write(body.strip() + "\n")


def prepared_fits(path, st, today):
    """Is the prepared round in `path` still usable for this ledger with its normal mix?"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, OSError):
        return False
    made = parse_date(doc.get("made")) if isinstance(doc, dict) else None
    return bool(isinstance(doc, dict) and doc.get("payload") and doc.get("gen") == st.get("gen")
                and doc.get("session_id") == st.get("next_id") and doc.get("counts") == plan_counts(st)
                and made and 0 <= (today - made).days <= PREPARED_MAX_AGE_DAYS)


def take_prepared(args, st, today):
    """Use the round prepared at the last close if it still fits: same ledger generation, same
    mix, no one-off options, not too old, none of its topics tested today."""
    def no(why):
        return {"used": False, "why": why}
    if not os.path.exists(args.prepared):
        return no("no prepared round")
    try:
        with open(args.prepared, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (ValueError, OSError):
        return no("unreadable")
    if not isinstance(doc, dict) or not doc.get("payload"):
        return no("no prepared round")
    if any((getattr(args, "mcqs", None) is not None, getattr(args, "focused", None) is not None,
            args.no_case, args.domain, args.no_new, args.allow_repeat, args.no_drill, args.force_drill,
            args.seed is not None)):
        return no("one-off options were given for this round")
    if doc.get("gen") != st.get("gen") or doc.get("session_id") != st.get("next_id"):
        return no("the ledger changed since it was prepared")
    if doc.get("counts") != plan_counts(st):
        return no("the round mix changed")
    made = parse_date(doc.get("made"))
    if not made or (today - made).days > PREPARED_MAX_AGE_DAYS or made > today:
        return no("too old")
    try:
        inner = unpack(doc["payload"])
        plan = inner["plan"]
        files = inner.get("files") or {"sealed_questions.md": inner["sealed"]}
    except Exception:
        return no("unreadable")
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
    plan["prepared"] = dict(plan.get("prepared") or {}, used=True)
    save_json(plan, args.out)
    work = args.work_dir or os.path.dirname(os.path.abspath(args.out))
    os.makedirs(work, exist_ok=True)
    written = []
    for name in PREPARED_FILES:
        if files.get(name):
            with open(os.path.join(work, name), "w", encoding="utf-8") as fh:
                fh.write(files[name])
            written.append(name)
    items = plan.get("items") or []
    counts = plan.get("counts") or {}
    summary = {"ok": True, "out": args.out, "items": len(items), "mcqs": counts.get("mcqs"),
               "focused": counts.get("focused"), "case": counts.get("case"),
               "case_format": plan.get("case_format"), "estimated_minutes": plan.get("estimated_minutes"),
               "item_order": plan.get("item_order"), "session_id": st.get("next_id"), "prepared": True}
    return {"used": True, "made": doc.get("made"), "summary": summary, "ready": written,
            "present": first, "present_block": "questions" if q_text else "case",
            "work_dir": os.path.abspath(work)}


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


def assemble_part_a(sealed, answers, feedback, item_order, warnings, feedback_questions=None):
    """Part A in the order of the round. With mcqs_first the short questions are graded before
    the case is shown, so their feedback (if sent on its own) follows their answers."""
    pres = blocks(sealed, PRESENT_RE)
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


def page_upgrade(out_dir, live_page, warnings):
    """If the learner's live page (index.html, read with the ledger) is older than this skill's
    template, write the template as out_dir/index.html so it is published with the save."""
    if not live_page:
        return None
    try:
        with open(live_page, "r", encoding="utf-8") as fh:
            m = PAGE_VERSION_RE.search(fh.read())
    except OSError:
        warnings.append("--page: could not read %s; the page was not checked" % live_page)
        return None
    live = m.group(1) if m else "0"
    if version_tuple(live) >= version_tuple(PAGE_VERSION):
        return None
    with open(PAGE_TEMPLATE, "r", encoding="utf-8") as fh:
        html = fh.read()
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return {"as": "index.html", "path": os.path.abspath(path), "db_path": None,
            "page_upgrade": {"from": live, "to": PAGE_VERSION}}


def run_quiet(fn, args):
    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(args)
    except SystemExit:
        sys.stdout.write(buf.getvalue())
        raise
    return json.loads(buf.getvalue())


def cmd_save(args):
    """First save after the feedback: record + session document (part A) + index, in one go."""
    rnd = load_json_arg(args.round) or {}
    st_in = load_json(args.state)
    check_schema(st_in)
    sid = rnd.get("log_id") or st_in.get("next_id")
    rnd["log_id"] = sid
    if not rnd.get("date"):
        rnd["date"] = iso(today_from(args))
    warnings = []
    os.makedirs(args.out_dir, exist_ok=True)
    state_path = args.state
    prefs_changes = apply_prefs(st_in, load_json_arg(args.prefs), warnings)
    if prefs_changes:   # the round mix set on the page is kept in the ledger from now on
        state_path = os.path.join(args.out_dir, ".prefs.json")
        save_json(st_in, state_path)
    if args.md:
        with open(args.md, "r", encoding="utf-8") as fh:
            md = fh.read()
    else:
        if not args.feedback and not args.feedback_questions:
            die("save needs --md A.md, or --sealed … --answers … --feedback FEEDBACK.md")
        md = assemble_part_a(args.sealed, args.answers, args.feedback,
                             rnd.get("item_order") or st_in["config"].get("item_order"), warnings,
                             args.feedback_questions)
    tmp_state = os.path.join(args.out_dir, ".record.json")
    rec = run_quiet(cmd_record, argparse.Namespace(state=state_path, round=json.dumps(rnd), out=tmp_state,
                                                   today=args.today))
    st = load_json(tmp_state)
    os.remove(tmp_state)
    if state_path != args.state:
        os.remove(state_path)
    files = [write_out(args.out_dir, STATE_PATH, st)]
    doc = session_doc_a(rnd, sid, md)
    files.append(write_out(args.out_dir, session_path(sid), doc))
    idx = load_index(args.index, st_in)
    index_put_session(idx, doc)
    files.append(write_out(args.out_dir, INDEX_PATH, finish_index(idx, st)))
    files.append(write_out(args.out_dir, PREPARED_PATH, {"v": 1, "empty": True}))
    with open(os.path.join(args.out_dir, "A.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    pf = page_upgrade(args.out_dir, args.page, warnings)
    if pf:
        files.append(pf)
        rec["page_upgraded"] = pf["page_upgrade"]
    if prefs_changes:
        rec["page_settings_applied"] = prefs_changes
    rec["out"] = files[0]["path"]
    rec["files"] = files
    rec["warnings"] = list(rec.get("warnings") or []) + warnings
    rec["transcript_chars"] = len(md)
    print(json.dumps(rec, indent=1, ensure_ascii=False))


def cmd_close(args):
    """Second save after the reflection: reflect + part B into the session document + index."""
    os.makedirs(args.out_dir, exist_ok=True)
    tmp_state = os.path.join(args.out_dir, ".reflect.json")
    ref = run_quiet(cmd_reflect, argparse.Namespace(state=args.state, reflection=args.reflection, out=tmp_state,
                                                    session=args.session, today=args.today))
    st = load_json(tmp_state)
    os.remove(tmp_state)
    sid = ref["session_id"]
    with open(args.md, "r", encoding="utf-8") as fh:
        md_b = fh.read()
    doc = load_json(args.doc) if args.doc else {"id": sid}
    if doc.get("id") and doc["id"] != sid:
        die("session document %s does not match the reflected session %s" % (doc.get("id"), sid))
    doc["closing"] = md_b
    doc["reflected"] = True
    sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
    if sess and isinstance(sess.get("score"), (int, float)):
        doc["score"] = sess["score"]
    files = [write_out(args.out_dir, STATE_PATH, st), write_out(args.out_dir, session_path(sid), doc)]
    idx = load_index(args.index, st)
    index_put_session(idx, doc)
    files.append(write_out(args.out_dir, INDEX_PATH, finish_index(idx, st)))
    page_warn = []
    pf = page_upgrade(args.out_dir, args.page, page_warn)
    if pf:
        files.append(pf)
        ref["page_upgraded"] = pf["page_upgrade"]
    if page_warn:
        ref["warnings"] = list(ref.get("warnings") or []) + page_warn
    # for database stores, which merge part B into the existing document
    save_json({"closing": md_b, "reflected": True, "score": doc.get("score")},
              os.path.join(args.out_dir, "B.json"))
    ref["out"] = files[0]["path"]
    ref["files"] = files
    ref["db_update"] = os.path.abspath(os.path.join(args.out_dir, "B.json"))
    print(json.dumps(ref, indent=1, ensure_ascii=False))


TESTING_SKIP = {"A.md", "B.json"}


def written_files(dirs):
    """Every file a cme.py output folder holds for the store, by its store path; later folders win."""
    out = {}
    for d in dirs:
        for root, _, names in os.walk(d):
            for n in names:
                if n.startswith(".") or n in TESTING_SKIP:
                    continue
                full = os.path.join(root, n)
                out[os.path.relpath(full, d).replace(os.sep, "/")] = full
    return out


def same_content(a, b):
    if a.endswith(".json"):
        try:
            return load_json(a) == load_json(b)
        except SystemExit:
            return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def cmd_verify(args):
    """Testing mode: compare what cme.py produced with what the store holds after the save."""
    wanted = written_files(args.written)
    missing, mismatched = [], []
    for rel, src in sorted(wanted.items()):
        cand = [os.path.join(args.store, rel), os.path.join(args.store, os.path.basename(rel))]
        got = next((p for p in cand if os.path.isfile(p)), None)
        if not got:
            missing.append(rel)
        elif not same_content(src, got):
            mismatched.append(rel)
    res = {"ok": not missing and not mismatched, "checked": len(wanted), "missing": missing,
           "mismatched": mismatched}
    if args.out:
        save_json(res, args.out)
    print(json.dumps(res, indent=1))


def cmd_testing_note(args):
    """Testing mode: the learner's quick feedback and the store check, as data/testing/<id>.json."""
    today = today_from(args)
    fb = load_json_arg(args.feedback) or {}
    ver = load_json(args.verify) if args.verify and os.path.isfile(args.verify) else None
    note = {"session": args.session, "date": iso(today), "skill_version": SKILL_VERSION,
            "feedback": fb, "store_check": ver}
    os.makedirs(args.out_dir, exist_ok=True)
    files = [write_out(args.out_dir, "data/testing/%s.json" % args.session, note)]
    print(json.dumps({"ok": True, "files": files}, indent=1))


def cmd_addendum(args):
    doc = load_json(args.doc)
    with open(args.md, "r", encoding="utf-8") as fh:
        add = fh.read().strip()
    doc["addendum"] = ((doc.get("addendum") or "").rstrip() + "\n\n" + add).strip() + "\n"
    os.makedirs(args.out_dir, exist_ok=True)
    f = write_out(args.out_dir, session_path(doc["id"]), doc)
    print(json.dumps({"ok": True, "files": [f], "chars": len(doc["addendum"])}))


def cmd_reindex(args):
    """Rebuild data/index.json from a folder holding data/sessions and data/reviews (and the state)."""
    root = args.root
    st = load_json(os.path.join(root, STATE_PATH)) if os.path.exists(os.path.join(root, STATE_PATH)) else None
    idx = {"schema": 1, "sessions": [], "reviews": []}
    sdir = os.path.join(root, "data", "sessions")
    for fn in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        if fn.endswith(".json"):
            index_put_session(idx, load_json(os.path.join(sdir, fn)))
    rdir = os.path.join(root, "data", "reviews")
    for fn in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        if fn.endswith(".json"):
            index_put_review(idx, load_json(os.path.join(rdir, fn)))
    if st:
        add_state_to_index(idx, st)
        finish_index(idx, st)
    f = write_out(root, INDEX_PATH, idx)
    print(json.dumps({"ok": True, "files": [f], "sessions": len(idx["sessions"]), "reviews": len(idx["reviews"])}))


def cmd_import(args):
    """Split a page export ({state, sessions, reviews}) or a folder of database documents into
    the file layout, ready to publish or copy."""
    if os.path.isdir(args.export):
        # a folder of database documents saved to files: cme/state.json, sessions/*.json, reviews/*.json
        root = args.export
        def folder(name):
            d = os.path.join(root, name)
            out = []
            for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if fn.endswith(".json"):
                    doc = load_json(os.path.join(d, fn))
                    doc.setdefault("id", fn[:-5])
                    out.append(doc)
            return out
        sp = os.path.join(root, "cme", "state.json")
        src = {"state": load_json(sp) if os.path.exists(sp) else None,
               "sessions": folder("sessions"), "reviews": folder("reviews")}
    else:
        src = load_json(args.export)
    state = src.get("state") if isinstance(src, dict) else None
    if not state:
        die("the export has no 'state' (a Clinical CME page export is {state, sessions, reviews})")
    check_schema(state)
    os.makedirs(args.out_dir, exist_ok=True)
    files = [write_out(args.out_dir, STATE_PATH, state)]
    idx = {"schema": 1, "sessions": [], "reviews": []}
    for d in src.get("sessions") or []:
        if not d.get("id"):
            continue
        files.append(write_out(args.out_dir, session_path(d["id"]), d))
        index_put_session(idx, d)
    for r in src.get("reviews") or []:
        date = r.get("date") or r.get("id")
        if not date:
            continue
        r = dict(r, date=date)
        files.append(write_out(args.out_dir, review_path(date), r))
        index_put_review(idx, r)
    add_state_to_index(idx, state)
    files.append(write_out(args.out_dir, INDEX_PATH, finish_index(idx, state)))
    print(json.dumps({"ok": True, "gen": state.get("gen"), "next_id": state.get("next_id"),
                      "sessions": len(src.get("sessions") or []), "reviews": len(src.get("reviews") or []),
                      "files": files}, indent=1, ensure_ascii=False))


def cmd_review_doc(args):
    """Wrap a review report (Markdown) as data/reviews/<date>.json and add it to the index."""
    today = today_from(args)
    with open(args.md, "r", encoding="utf-8") as fh:
        report = fh.read()
    date = args.date or iso(today)
    doc = {"date": date, "title": args.title or "CME progress review — %s" % date,
           "headline": args.headline, "report": report}
    os.makedirs(args.out_dir, exist_ok=True)
    files = [write_out(args.out_dir, review_path(date), doc)]
    if args.index or args.state:
        st = load_json(args.state) if args.state else None
        idx = load_index(args.index, st)
        index_put_review(idx, doc)
        if st:
            finish_index(idx, st)
        files.append(write_out(args.out_dir, INDEX_PATH, idx))
    print(json.dumps({"ok": True, "doc": "reviews/%s" % date, "files": files}, ensure_ascii=False))


def cmd_place(args):
    """Copy a state file produced by settings/review/snooze/init into the file layout, plus the index."""
    st = load_json(args.state)
    check_schema(st)
    os.makedirs(args.out_dir, exist_ok=True)
    files = [write_out(args.out_dir, STATE_PATH, st)]
    if not args.no_index:
        idx = load_index(args.index, st)
        files.append(write_out(args.out_dir, INDEX_PATH, finish_index(idx, st)))
        files.append(write_out(args.out_dir, PREPARED_PATH, {"v": 1, "empty": True}))
    out = {"ok": True, "gen": st.get("gen"), "files": files}
    warnings = []
    pf = page_upgrade(args.out_dir, args.page, warnings)
    if pf:
        files.append(pf)
        out["page_upgraded"] = pf["page_upgrade"]
    if warnings:
        out["warnings"] = warnings
    print(json.dumps(out, ensure_ascii=False))


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(prog="cme.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status"); s.add_argument("state"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("start"); s.add_argument("state"); s.add_argument("--out", required=True)
    s.add_argument("--prefs"); s.add_argument("--focused", type=int)
    s.add_argument("--mcqs", type=int); s.add_argument("--no-case", action="store_true")
    s.add_argument("--domain"); s.add_argument("--no-new", action="store_true")
    s.add_argument("--allow-repeat", action="store_true"); s.add_argument("--no-drill", action="store_true")
    s.add_argument("--force-drill", action="store_true"); s.add_argument("--seed", type=int)
    s.add_argument("--prepared"); s.add_argument("--work-dir"); s.set_defaults(fn=cmd_start)
    s = sub.add_parser("save"); s.add_argument("state"); s.add_argument("--round", required=True)
    s.add_argument("--sealed", nargs="+"); s.add_argument("--answers", nargs="+"); s.add_argument("--feedback")
    s.add_argument("--feedback-questions")
    s.add_argument("--md"); s.add_argument("--index"); s.add_argument("--prefs"); s.add_argument("--page")
    s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_save)
    s = sub.add_parser("close"); s.add_argument("state"); s.add_argument("--reflection", required=True)
    s.add_argument("--md", required=True); s.add_argument("--doc"); s.add_argument("--index"); s.add_argument("--session")
    s.add_argument("--page")
    s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_close)
    s = sub.add_parser("addendum"); s.add_argument("--doc", required=True); s.add_argument("--md", required=True)
    s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_addendum)
    s = sub.add_parser("prepare"); s.add_argument("state"); s.add_argument("--out", required=True)
    s.add_argument("--if-needed"); s.add_argument("--allow-unreflected", action="store_true"); s.set_defaults(fn=cmd_prepare)
    s = sub.add_parser("stash"); s.add_argument("state"); s.add_argument("--plan", required=True)
    s.add_argument("--dir", required=True); s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_stash)
    s = sub.add_parser("present"); s.add_argument("files", nargs="+"); s.add_argument("--block", required=True)
    s.set_defaults(fn=cmd_present)
    s = sub.add_parser("verify"); s.add_argument("--written", nargs="+", required=True)
    s.add_argument("--store", required=True); s.add_argument("--out"); s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("testing-note"); s.add_argument("--session", required=True)
    s.add_argument("--feedback", required=True); s.add_argument("--verify")
    s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_testing_note)
    s = sub.add_parser("reindex"); s.add_argument("root"); s.set_defaults(fn=cmd_reindex)
    s = sub.add_parser("import"); s.add_argument("export"); s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("review-doc"); s.add_argument("--md", required=True); s.add_argument("--date"); s.add_argument("--title")
    s.add_argument("--headline"); s.add_argument("--state"); s.add_argument("--index"); s.add_argument("--out-dir", required=True)
    s.set_defaults(fn=cmd_review_doc)
    s = sub.add_parser("place"); s.add_argument("state"); s.add_argument("--index"); s.add_argument("--no-index", action="store_true")
    s.add_argument("--page")
    s.add_argument("--out-dir", required=True); s.set_defaults(fn=cmd_place)
    s = sub.add_parser("plan"); s.add_argument("state"); s.add_argument("--out", required=True)
    s.add_argument("--prefs"); s.add_argument("--focused", type=int)
    s.add_argument("--mcqs", type=int); s.add_argument("--no-case", action="store_true")
    s.add_argument("--domain"); s.add_argument("--no-new", action="store_true")
    s.add_argument("--allow-repeat", action="store_true"); s.add_argument("--no-drill", action="store_true")
    s.add_argument("--force-drill", action="store_true"); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_plan)
    s = sub.add_parser("record"); s.add_argument("state"); s.add_argument("--round", required=True)
    s.add_argument("--out", required=True); s.set_defaults(fn=cmd_record)
    s = sub.add_parser("reflect"); s.add_argument("state"); s.add_argument("--reflection", required=True)
    s.add_argument("--session"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_reflect)
    s = sub.add_parser("doc"); s.add_argument("--part", choices=("A", "B"), required=True)
    s.add_argument("--md", required=True); s.add_argument("--out", required=True)
    s.add_argument("--round"); s.add_argument("--state"); s.add_argument("--id"); s.set_defaults(fn=cmd_doc)
    s = sub.add_parser("stats"); s.add_argument("state"); s.add_argument("--all", action="store_true"); s.set_defaults(fn=cmd_stats)
    s = sub.add_parser("review"); s.add_argument("state"); s.add_argument("--review", required=True)
    s.add_argument("--out", required=True); s.set_defaults(fn=cmd_review)
    s = sub.add_parser("snooze"); s.add_argument("state"); s.add_argument("--days", type=int, default=7)
    s.add_argument("--out", required=True); s.set_defaults(fn=cmd_snooze)
    s = sub.add_parser("settings"); s.add_argument("state"); s.add_argument("--config"); s.add_argument("--profile")
    s.add_argument("--blueprint"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_settings)
    s = sub.add_parser("init"); s.add_argument("--profile", default="{}"); s.add_argument("--config", default="{}")
    s.add_argument("--blueprint", required=True); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("blueprint-md"); s.add_argument("file"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_blueprint_md)
    s = sub.add_parser("unescape"); s.add_argument("file"); s.add_argument("--out", required=True); s.set_defaults(fn=cmd_unescape)
    s = sub.add_parser("migrate-v3"); s.add_argument("ledger"); s.add_argument("--blueprint", required=True)
    s.add_argument("--out", required=True); s.add_argument("--sessions-dir"); s.set_defaults(fn=cmd_migrate_v3)
    s = sub.add_parser("validate"); s.add_argument("state"); s.set_defaults(fn=cmd_validate)

    for p in sub.choices.values():
        p.add_argument("--today", dest="today_sub")
    args = ap.parse_args(argv)
    if getattr(args, "today_sub", None):
        args.today = args.today_sub
    args.fn(args)


if __name__ == "__main__":
    main()

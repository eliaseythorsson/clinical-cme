#!/usr/bin/env python3
"""
cme_ledger.py - ledger helper for the clinical-cme skill.

Standard library only; runs on Python 3.8+. Every command that changes the
ledger writes atomically (temp file + rename) and re-reads the result to
confirm it parses before reporting success.

Commands
  init            create a new ledger from profile/config JSON (first run)
  migrate         upgrade an older ledger to the current schema, keeping all history
  status          neutral start-of-session status (never prints topic names)
  select          plan today's items (topic ids + reasons; keep these out of the chat)
  record          apply a graded and reflected round: spacing, gaps, session log
  stats           period summary for the progress review
  review          record a completed progress review and apply settings changes
  snooze-review   postpone a due progress review
  settings        change profile/config values on request
  validate        check structure and dates

Session log (version 3; the learner's searchable, append-only Markdown record)
  log-append      append part A / part B / a whole entry / an addendum to the session log
  log-check       structural check of the log, optionally cross-checked with the ledger
  log-index       list entries (id, date, title, summary, tags) with optional search filters
  log-extract     print selected entries or sections (review reading, teaching export)
  log-backfill    write reconstructed stub entries for sessions recorded before version 3
  log-mark-unrecorded  note a log entry the learner chose not to record in the ledger
  teaching-points list logged teaching points and when each was last checked against guidance

Dates are ISO (YYYY-MM-DD). Pass --today to override the system date.
"""

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import random
import re
import sys
import tempfile

SCHEMA_VERSION = 3
LOG_FILENAME = "CME_session_log.md"

DEFAULT_CONFIG = {
    "session_minutes": 20,
    "default_session": {"essays": 1, "mcqs": 3},
    "case_format": "unfolding",          # unfolding | discriminate | alternate
    "feedback_depth": "detailed",        # standard | detailed
    "target_sessions_per_week": 3,
    "review_interval_days": 42,
    "intervals_days": [1, 3, 7, 16, 35, 90],
    "interleave_mcqs": True,
    "new_topics_per_round": 1,           # 0 disables the reserved slot for new topics
    "lab_units": "SI",
    "blood_gas_units": "mmHg",
    "guideline_region": "Europe",
    "resource_preferences": {"free_only": False,
                             "formats": ["guidelines", "review articles", "podcasts"]},
    "reminders": None,                   # None = not asked yet; True/False = learner's choice
    "log_file": LOG_FILENAME,            # session log in the learner's CME folder
    "show_coding": True,                 # one-line error coding in each session's feedback
    "item_order": "mcqs_first",          # mcqs_first: MCQs answered before the case is shown
    "storage": {"home": None},           # where the CME files live (see references/google_drive.md)
}

DEFAULT_PROFILE = {
    "display_name": None,
    "role": None,
    "specialty": None,
    "subspecialty": None,
    "practice_setting": [],
    "goals": [],
    "strengths": [],
    "weaknesses": [],
    "domain_self_ratings": {},   # {DOMAIN: {"rating": 1-5, "updated": date}}
    "domain_emphasis": {},       # {DOMAIN: multiplier, e.g. 1.5 more, 0.5 less}
    "notes": "",
    "onboarded_at": None,
    "needs_personalization": False,
    "last_review": None,
    "next_review_due": None,
    "v3_setup_pending": False,   # upgraded ledger: ask review interval, offer log backfill
}

# Self-rating -> weighting of a domain when sampling new topics.
SELF_RATING_FACTOR = {1: 1.6, 2: 1.3, 3: 1.0, 4: 0.8, 5: 0.6}
CONFIDENCE_LEVELS = ("sure", "unsure", "guess")
MIN_SESSIONS_FOR_REVIEW = 3
REVIEW_GRACE_DAYS = 21          # review becomes due regardless of session count after interval + grace
REVIEW_INTERVAL_RANGE = (30, 90)

# ---- coding vocabulary (see references/analysis_framework.md)
# Reasoning steps: the five SIDM Assessment of Reasoning Tool domains, plus management.
ART_MAX = {"DG": 2, "PR": 2, "DDX": 2, "TEST": 2, "META": 1, "MGMT": 2}
ART_LABELS = {"DG": "hypothesis-directed data gathering", "PR": "problem representation",
              "DDX": "prioritised differential", "TEST": "high-value testing",
              "META": "metacognition", "MGMT": "management and disposition (extension)"}
IDEA_MAX = {"I": 4, "D": 2, "E": 2, "A": 2}          # Revised-IDEA, total 0-10, >= 6 high quality
ERROR_CATEGORIES = ("knowledge", "data_gathering", "synthesis", "slip", "unclassified")
KNOWLEDGE_TYPES = ("missing", "outdated", "misapplied", "numeric")
SEVERITIES = ("minor", "important", "critical")
BIASES = ("anchoring", "premature_closure", "confirmation", "availability", "base_rate_neglect",
          "representativeness", "search_satisficing", "framing", "overconfidence", "omission",
          "commission", "unpacking_failure")
CONF_PROB = {"sure": 0.9, "unsure": 0.6, "guess": 0.3}
DRILL_RESULTS = ("avoided", "partial", "fell_for")


# ---------------------------------------------------------------- utilities

def die(msg, code=2):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(code)


def parse_date(s):
    if s is None:
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
    if getattr(args, "today", None):
        d = parse_date(args.today)
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
    except json.JSONDecodeError as exc:
        die("not valid JSON (%s): %s" % (path, exc))


def load_json_arg(value):
    """Accept inline JSON or a path to a JSON file."""
    if value is None:
        return None
    value = value.strip()
    if value.startswith("{") or value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            die("inline JSON is invalid: %s" % exc)
    return load_json(value)


def save_ledger(ledger, path):
    text = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    json.loads(text)  # must round-trip before touching disk
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".ledger-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        mode = (os.stat(path).st_mode & 0o777) if os.path.exists(path) else 0o644
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    with open(path, "r", encoding="utf-8") as fh:
        json.load(fh)
    return len(text.encode("utf-8"))


def deep_fill(target, defaults):
    """Add keys from defaults that are missing in target (recursively). Never overwrites."""
    for key, value in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(value)
        elif isinstance(value, dict) and isinstance(target[key], dict):
            deep_fill(target[key], value)
    return target


def deep_merge(target, changes):
    """Overwrite target with changes (recursively for dicts)."""
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def infer_domain(topic_id, topic=None):
    if topic and topic.get("domain"):
        return str(topic["domain"]).upper()
    m = re.match(r"^([A-Za-z]+)[.\-:_/]", str(topic_id))
    return m.group(1).upper() if m else "GEN"


def normalize_session_shape(value):
    """Older ledgers may store default_session in several shapes."""
    shape = {"essays": 1, "mcqs": 3}
    if isinstance(value, dict):
        for key, target in (("essays", "essays"), ("essay", "essays"), ("cases", "essays"),
                            ("case", "essays"), ("mcqs", "mcqs"), ("mcq", "mcqs")):
            if isinstance(value.get(key), int):
                shape[target] = value[key]
    return shape


def round_half(x):
    return round(x * 2) / 2.0


def sessions(ledger):
    return ledger.get("session_log") or []


# ------------------------------------------------------------- blueprint

QUALITATIVE_WEIGHTS = {"very high": 4.0, "high": 3.0, "medium": 2.0, "moderate": 2.0,
                       "low": 1.0, "very low": 0.5}
TOPIC_BULLET = re.compile(r"^[-*]\s+`?([A-Z]{2,8}[.\-][A-Za-z0-9_\-]+)`?\s*[-:\u2014\u2013]?\s*(.*)$")


def _weight_from_text(text):
    m = re.search(r"weight\s*[:=]?\s*([\d.]+|very high|very low|high|medium|moderate|low)", text, re.I)
    if not m:
        return None
    raw = m.group(1).lower()
    try:
        return float(raw)
    except ValueError:
        return QUALITATIVE_WEIGHTS.get(raw)


def parse_blueprint(path):
    """Return ({DOMAIN: weight}, {topic_id: {"domain", "label"}}). Tolerant of format drift.

    Recognised:
      | CODE | Domain | Weight |            table whose header contains 'code' and 'weight'
      ## A. Cardiology  (weight: high)       heading; numeric or high/medium/low
      - CARD-01  Acute coronary syndrome     topic bullets (CODE-NN or CODE.slug)
    A heading's weight applies to every topic-ID prefix listed under it.
    """
    weights, topics = {}, {}
    if not path or not os.path.exists(path):
        return weights, topics
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    header_cols = None
    heading_weight = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            cols = [c.strip() for c in stripped.strip("|").split("|")]
            low = [c.lower() for c in cols]
            if any("code" in c for c in low) and any("weight" in c for c in low):
                header_cols = (next(i for i, c in enumerate(low) if "code" in c),
                               next(i for i, c in enumerate(low) if "weight" in c))
                continue
            if header_cols and len(cols) > max(header_cols):
                code = re.sub(r"[^A-Za-z]", "", cols[header_cols[0]]).upper()
                w = _weight_from_text("weight " + cols[header_cols[1]])
                if code and w is not None:
                    weights[code] = w
            continue
        header_cols = None
        if stripped.startswith("#"):
            heading_weight = _weight_from_text(stripped)
            continue
        m = TOPIC_BULLET.match(stripped)
        if m:
            tid = m.group(1)
            label = re.sub(r"\s+", " ", m.group(2)).strip() or None
            dom = infer_domain(tid)
            if tid not in topics:
                topics[tid] = {"domain": dom, "label": label}
            if heading_weight is not None and dom not in weights:
                weights[dom] = heading_weight
    return weights, topics


GENERIC_WORDS = {"acute", "chronic", "management", "disorders", "disorder", "disease", "diseases",
                 "syndrome", "syndromes", "inpatient", "failure", "emergencies", "emergency",
                 "infection", "infections", "assessment", "therapy", "treatment", "prophylaxis",
                 "complications", "care", "medicine", "basics", "dangerous", "causes", "common",
                 "including", "related", "selection", "control", "medical", "hospital"}


def significant_tokens(label):
    label = re.sub(r"\(see[^)]*\)", " ", label or "", flags=re.I)
    words = re.findall(r"[a-z]+", label.lower())
    out = set()
    for w in words:
        if len(w) < 5 or w in GENERIC_WORDS:
            continue
        out.add(w[:-1] if w.endswith("s") else w)
    return out


def blueprint_refs(bp_topics):
    """{topic_id: (referenced topic ids, referenced domain codes)} from '(see X)' notes."""
    refs = {}
    for tid, info in bp_topics.items():
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


# ------------------------------------------------------------- scheduling

def schedule_topic(prev_step, mastery, comfort, misconception, self_gap, intervals, today):
    """Spaced-repetition step with self-assessment calibration.

    mastery: grader's 0-5 (after confidence adjustment)
    comfort: learner's self-rated comfort 1-5 for this topic, or None
    Returns (sr_step, next_due_date, calibration_label, interval_days).
    """
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
                # Feels secure but is not: do not advance, bring it back soon.
                calibration = "overconfident"
                k_new = min(k_new, k)
                interval = min(intervals[k_new], 3)
            elif delta <= -2 and mastery >= 4:
                # Performs well but feels shaky: advance, but confirm sooner.
                calibration = "underconfident"
                interval = max(intervals[0], int(round(interval * 0.5)))
    if self_gap:
        interval = min(interval, 7)
    interval = max(1, int(interval))
    return k_new, today + dt.timedelta(days=interval), calibration, interval


def adjusted_item_mastery(item):
    """Apply confidence rules to one graded item. Returns (mastery, misconception)."""
    m = float(item.get("mastery", 0))
    conf = (item.get("confidence") or "").lower() or None
    correct = item.get("correct")
    misconception = False
    if item.get("type") == "mcq":
        if correct is True and conf == "guess":
            m = min(m, 3.0)                    # a lucky guess is not mastery
        if correct is False and conf == "sure":
            misconception = True
    else:
        if m <= 2 and conf == "sure":
            misconception = True
    return m, misconception


# ------------------------------------------------------------- commands

V3_KEYS = {
    "log": {"file": LOG_FILENAME, "last_id": None, "backfilled": False},
    "case_index": [],             # compact record of every case and MCQ stem, for novelty
    "errata": [],                 # corrections already written into the log
    "pending_errata": [],         # corrections found at a review, to be written at the next session
    "teaching_point_checks": {},  # {"S0042.1": {"checked", "status", "note", "source"}}
    "drill_targets": [],          # thinking patterns to provoke deliberately (set at reviews)
}


def id_num(value):
    m = re.match(r"^[SE](\d+)$", str(value or ""))
    return int(m.group(1)) if m else 0


def next_log_id(ledger, log_last_id=None):
    nums = [id_num(s.get("log_id")) for s in sessions(ledger)]
    nums += [id_num(k) for k in ((ledger.get("gdocs") or {}).get("sessions") or {})]
    nums += [id_num(k) for k in ((ledger.get("log") or {}).get("not_recorded") or [])]
    nums.append(id_num((ledger.get("log") or {}).get("last_id")))
    nums.append(id_num(log_last_id))
    base = max(nums + [len(sessions(ledger))])
    return "S%04d" % (base + 1)


def next_erratum_num(ledger):
    nums = [id_num(e.get("id")) for e in (ledger.get("errata") or []) + (ledger.get("pending_errata") or [])]
    return max(nums + [0]) + 1


def clamp_review_interval(cfg, warnings=None):
    try:
        v = int(cfg.get("review_interval_days") or 42)
    except (TypeError, ValueError):
        v = 42
    lo, hi = REVIEW_INTERVAL_RANGE
    if not (lo <= v <= hi) and warnings is not None:
        warnings.append("review_interval_days %d is outside the recommended %d-%d" % (v, lo, hi))
    cfg["review_interval_days"] = max(14, min(180, v))


def new_ledger(today):
    profile = copy.deepcopy(DEFAULT_PROFILE)
    return {
        "schema_version": SCHEMA_VERSION,
        "created": iso(today),
        "profile": profile,
        "config": copy.deepcopy(DEFAULT_CONFIG),
        "topics": {},
        "open_gaps": [],
        "resolved_gaps": [],
        "session_log": [],
        "reviews": [],
        "resource_backlog": [],
        **copy.deepcopy(V3_KEYS),
    }


def cmd_init(args):
    today = today_from(args)
    if os.path.exists(args.out) and not args.force:
        die("refusing to overwrite existing ledger at %s (use --force)" % args.out)
    ledger = new_ledger(today)
    if args.profile:
        deep_merge(ledger["profile"], load_json_arg(args.profile))
    if args.config:
        deep_merge(ledger["config"], load_json_arg(args.config))
    ledger["config"]["default_session"] = normalize_session_shape(ledger["config"]["default_session"])
    warnings = []
    clamp_review_interval(ledger["config"], warnings)
    ledger["profile"]["onboarded_at"] = iso(today)
    ledger["profile"]["next_review_due"] = iso(
        today + dt.timedelta(days=int(ledger["config"]["review_interval_days"])))
    size = save_ledger(ledger, args.out)
    print(json.dumps({"ok": True, "path": args.out, "bytes": size, "warnings": warnings,
                      "next_review_due": ledger["profile"]["next_review_due"]}))


def migrate_in_memory(ledger, today):
    changes = []
    version = ledger.get("schema_version", 1)
    if not isinstance(ledger.get("topics"), dict):
        ledger["topics"] = {}
        changes.append("topics: created")
    for key, default in (("open_gaps", []), ("resolved_gaps", []), ("session_log", []),
                         ("reviews", []), ("resource_backlog", [])):
        if not isinstance(ledger.get(key), list):
            ledger[key] = copy.deepcopy(default)
            changes.append("%s: created" % key)

    cfg = ledger.setdefault("config", {})
    before = set(cfg.keys())
    legacy_sr = cfg.get("spaced_repetition")
    if "intervals_days" not in cfg and isinstance(legacy_sr, dict) and legacy_sr.get("intervals_days"):
        cfg["intervals_days"] = list(legacy_sr["intervals_days"])
        changes.append("config: intervals_days taken from spaced_repetition")
    legacy_shape = cfg.get("default_session")
    if "session_minutes" not in cfg and isinstance(legacy_shape, dict) \
            and isinstance(legacy_shape.get("minutes_target"), (int, float)):
        cfg["session_minutes"] = int(legacy_shape["minutes_target"])
    deep_fill(cfg, DEFAULT_CONFIG)
    cfg["default_session"] = normalize_session_shape(cfg.get("default_session"))
    added = sorted(set(cfg.keys()) - before)
    if added:
        changes.append("config: added %s" % ", ".join(added))

    prof = ledger.setdefault("profile", {})
    had_profile = bool(prof)
    learner = ledger.get("learner")
    if isinstance(learner, dict):           # v1 'learner' block -> profile (block kept as-is)
        for src, dst in (("name", "display_name"), ("role", "role"), ("notes", "notes"),
                         ("specialty", "specialty")):
            if learner.get(src) and not prof.get(dst):
                prof[dst] = learner[src]
        if learner.get("setting") and not prof.get("practice_setting"):
            prof["practice_setting"] = [learner["setting"]]
    deep_fill(prof, DEFAULT_PROFILE)
    log = sessions(ledger)
    if not prof.get("onboarded_at"):
        dates = sorted(d for d in (parse_date(s.get("date")) for s in log) if d)
        if dates:
            prof["onboarded_at"] = iso(dates[0])
            prof["needs_personalization"] = True   # existing user: short upgrade module
            changes.append("profile: created for existing user (personalization pending)")
    if not prof.get("next_review_due") and prof.get("onboarded_at"):
        prof["next_review_due"] = iso(today + dt.timedelta(days=14))
    if not had_profile:
        changes.append("profile: initialised")

    for tid, t in ledger["topics"].items():
        if not isinstance(t, dict):
            continue
        if not t.get("domain"):
            t["domain"] = infer_domain(tid)
        t.setdefault("attempts", 0)
        t.setdefault("sr_step", 0)
        if "history" not in t:
            t["history"] = []
            if t.get("last_tested") and t.get("mastery") is not None:
                t["history"].append({"date": t["last_tested"], "mastery": t["mastery"],
                                     "comfort": None, "calibration": "not_rated",
                                     "migrated": True})
    for g in ledger["open_gaps"]:
        if isinstance(g, dict):
            g.setdefault("source", ["graded"])
            if isinstance(g["source"], str):
                g["source"] = [g["source"]]
    if version < 3:
        for key, default in V3_KEYS.items():
            if key not in ledger:
                ledger[key] = copy.deepcopy(default)
        ledger["log"]["file"] = cfg.get("log_file") or LOG_FILENAME
        if prof.get("onboarded_at"):
            prof["v3_setup_pending"] = True
            changes.append("version 3: session log, error coding, deep review "
                           "(v3 setup pending: review interval, log backfill)")
    else:
        deep_fill(ledger, V3_KEYS)
    ledger["schema_version"] = SCHEMA_VERSION
    if version != SCHEMA_VERSION:
        changes.append("schema_version: %s -> %s" % (version, SCHEMA_VERSION))
    return changes


def cmd_migrate(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    changes = migrate_in_memory(ledger, today)
    out = args.out or args.ledger
    size = save_ledger(ledger, out)
    print(json.dumps({"ok": True, "path": out, "bytes": size, "changes": changes}, indent=2))


def in_window(date_value, start, inclusive):
    """True if date_value falls in the period starting at start (None = everything)."""
    if start is None:
        return True
    d = parse_date(date_value) or dt.date.min
    return d >= start if inclusive else d > start


def review_window(prof, explicit_since=None):
    """Start of the current review period and whether that start day counts.

    After a review, the period starts the day after it (sessions on the review day were
    already covered). Before any review, it starts on the onboarding day itself, so the
    first session (often done on the day of setup) is counted. An explicit --since date
    is inclusive.
    """
    if explicit_since:
        return explicit_since, True
    last = parse_date(prof.get("last_review"))
    if last:
        return last, False
    return parse_date(prof.get("onboarded_at")), True


def review_status(ledger, today):
    prof = ledger.get("profile") or {}
    cfg = ledger.get("config") or {}
    last, inclusive = review_window(prof)
    due_date = parse_date(prof.get("next_review_due"))
    since = [s for s in sessions(ledger) if in_window(s.get("date"), last, inclusive)]
    days = (today - last).days if last else None
    due = False
    if due_date and today >= due_date and len(since) >= MIN_SESSIONS_FOR_REVIEW:
        due = True
    interval = int(cfg.get("review_interval_days") or 42)
    if days is not None and days >= interval + REVIEW_GRACE_DAYS:
        due = True
    if due_date and today < due_date:
        due = False   # explicit next_review_due (e.g. snoozed) wins
    return {"review_due": due, "days_since_review": days,
            "sessions_since_review": len(since),
            "next_review_due": iso(due_date),
            "interval_days": cfg.get("review_interval_days")}


def cmd_status(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    prof = ledger.get("profile") or {}
    cfg = ledger.get("config") or {}
    log = sessions(ledger)
    topics = ledger.get("topics") or {}
    last = log[-1] if log else None
    week_ago = today - dt.timedelta(days=7)
    due = [t for t in topics.values()
           if isinstance(t, dict) and parse_date(t.get("next_due")) and parse_date(t["next_due"]) <= today]
    out = {
        "ok": True,
        "today": iso(today),
        "schema_version": ledger.get("schema_version", 1),
        "upgrade_needed": ledger.get("schema_version", 1) < SCHEMA_VERSION,
        "onboarding_needed": not prof.get("onboarded_at") and not log,
        "personalization_pending": bool(prof.get("needs_personalization")),
        "sessions_total": len(log),
        "sessions_last_7_days": sum(1 for s in log if (parse_date(s.get("date")) or dt.date.min) > week_ago),
        "target_sessions_per_week": cfg.get("target_sessions_per_week"),
        "sessions_today": sum(1 for s in log if parse_date(s.get("date")) == today),
        "days_since_last_session": (today - parse_date(last.get("date"))).days
        if last and parse_date(last.get("date")) else None,
        "reminders": cfg.get("reminders"),
        "last_session": None if not last else {
            "date": last.get("date"),
            "essays": last.get("essays"), "mcqs": last.get("mcqs")},
        "topics_due_count": len(due),
        "open_gaps_count": len(ledger.get("open_gaps") or []),
        "session_minutes": cfg.get("session_minutes"),
        "default_session": cfg.get("default_session"),
    }
    out.update(review_status(ledger, today))
    out["v3_setup_pending"] = bool(prof.get("v3_setup_pending"))
    out["pending_errata_count"] = len(ledger.get("pending_errata") or [])
    out["active_drills"] = len([d for d in ledger.get("drill_targets") or []
                                if not parse_date(d.get("until")) or parse_date(d.get("until")) >= today])
    storage = cfg.get("storage") or {}
    reg = (ledger.get("gdocs") or {}).get("sessions") or {}
    out["home"] = storage.get("home")
    if storage.get("home") == "moved":
        out["moved_to"] = storage.get("moved_to")
        out["note"] = ("This ledger was moved to another home; do not use or change it. "
                       "Open the CME files at the new home instead.")
    if storage.get("home") == "google":
        ids_ledger = {x.get("log_id") for x in log if x.get("log_id")}
        skip = set((ledger.get("log") or {}).get("not_recorded") or [])
        real = {k: v for k, v in reg.items() if not v.get("reconstructed")}
        open_e = sorted((k for k, v in real.items() if not v.get("closed") and k not in skip), key=id_num)
        unsaved = sorted((k for k in real if k not in ids_ledger and k not in skip), key=id_num)
        out["log"] = {"home": "google", "entries": len(reg),
                      "last_id": max(reg, key=id_num) if reg else None,
                      "open_entry": open_e[-1] if open_e else None,
                      "unsaved_entry": unsaved[-1] if unsaved else None,
                      "unsaved_entry_closed": bool(real[unsaved[-1]].get("closed")) if unsaved else None,
                      "errors": [],
                      "backfill_possible": any(not x.get("log_id") for x in log)
                      and not (ledger.get("log") or {}).get("backfilled")}
        out["next_session_id"] = next_log_id(ledger)
        # v3.2 registers a session doc only when the round is recorded, so a doc left by an
        # interrupted session is found by its title in the Sessions folder (google_drive.md §3).
        out["log"]["check_sessions_folder"] = {
            "folder_id": storage.get("sessions_folder_id"),
            "query": "parentId = '%s' and title contains '%s'" % (storage.get("sessions_folder_id"),
                                                                  out["next_session_id"])}
    elif args.log:
        summ = log_summary(args.log)
        ids_ledger = {x.get("log_id") for x in log if x.get("log_id")}
        out["log"] = {k: summ[k] for k in ("exists", "bytes", "entries", "last_id", "open_entry",
                                          "open_entry_part_a", "errors")}
        skip = set((ledger.get("log") or {}).get("not_recorded") or [])
        parsed = parse_log(read_text(args.log) or "")
        unsaved = [b["id"] for b in parsed["blocks"] if b["kind"] == "entry"
                   and b["id"] not in ids_ledger and b["id"] not in skip]
        out["log"]["unsaved_entry"] = unsaved[-1] if unsaved else None
        out["log"]["unsaved_entry_closed"] = (unsaved[-1] != summ["open_entry"]) if unsaved else None
        out["next_session_id"] = next_log_id(ledger, summ["last_id"])
        out["log"]["backfill_possible"] = summ["entries"] == 0 and any(not x.get("log_id") for x in log)
    else:
        out["next_session_id"] = next_log_id(ledger)
    print(json.dumps(out, indent=2))


def domain_weights(ledger, bp_weights):
    prof = ledger.get("profile") or {}
    ratings = prof.get("domain_self_ratings") or {}
    emphasis = prof.get("domain_emphasis") or {}
    domains = set(bp_weights) | set(ratings) | set(emphasis)
    for tid, t in (ledger.get("topics") or {}).items():
        domains.add(infer_domain(tid, t if isinstance(t, dict) else None))
    eff = {}
    for d in domains:
        w = bp_weights.get(d, 1.0 if not bp_weights else min(bp_weights.values()))
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


def cmd_select(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    cfg = ledger.get("config") or {}
    shape = normalize_session_shape(cfg.get("default_session"))
    n_essays = args.essays if args.essays is not None else shape["essays"]
    n_mcqs = args.mcqs if args.mcqs is not None else shape["mcqs"]
    log = sessions(ledger)
    topics = {k: v for k, v in (ledger.get("topics") or {}).items() if isinstance(v, dict)}
    bp_weights, bp_topics = parse_blueprint(args.blueprint)
    eff = domain_weights(ledger, bp_weights)
    seed = args.seed if args.seed is not None else int(today.strftime("%Y%m%d")) * 100 + len(log)
    rng = random.Random(seed)

    tested_today = {tid for tid, t in topics.items() if parse_date(t.get("last_tested")) == today}
    recent = set()
    for s in log[-3:]:
        recent.update(s.get("topic_ids") or [])
    recent_domains = [infer_domain(t) for s in log[-10:] for t in (s.get("topic_ids") or [])]

    restrict = args.domain.upper() if args.domain else None

    def allowed(tid):
        if tid in tested_today and not args.allow_repeat:
            return False
        if restrict and infer_domain(tid, topics.get(tid)) != restrict:
            return False
        return True

    gaps_by_topic = {}
    for g in ledger.get("open_gaps") or []:
        if isinstance(g, dict) and g.get("topic"):
            gaps_by_topic[g["topic"]] = g

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

    # 1) due / overdue topics
    due = []
    for tid, t in topics.items():
        nd = parse_date(t.get("next_due"))
        if nd and nd <= today and allowed(tid):
            cal = t.get("calibration")
            urgency = 0 if cal in ("overconfident", "confident_error") else 1
            g = gaps_by_topic.get(tid)
            due.append(((urgency, gap_rank(g) if g else 9, -(today - nd).days,
                         t.get("mastery") if t.get("mastery") is not None else 0), tid))
    due.sort()
    due_ids = [tid for _, tid in due]

    # 2) open gaps not yet re-tested since logged
    gap_ids = []
    for tid, g in sorted(gaps_by_topic.items(), key=lambda kv: (gap_rank(kv[1]), kv[1].get("date") or "")):
        if tid in due_ids or not allowed(tid):
            continue
        lt = parse_date((topics.get(tid) or {}).get("last_tested"))
        gd = parse_date(g.get("date"))
        if lt is None or gd is None or lt <= gd:
            gap_ids.append(tid)

    # 3) new / under-sampled topics, weighted by effective domain weight
    def new_candidates(exclude_domains):
        pool = []
        for tid, info in bp_topics.items():
            d = info["domain"]
            if tid in topics or tid in recent or not allowed(tid):
                continue
            if d in exclude_domains:
                continue
            w = eff.get(d, 1.0) / (1.0 + recent_domains.count(d))
            if w > 0:
                pool.append((w, tid, d))
        return pool

    def domain_only_candidates(exclude_domains):
        pool = []
        for d, w in eff.items():
            if d in exclude_domains or (restrict and d != restrict):
                continue
            w = w / (1.0 + recent_domains.count(d))
            if w > 0:
                pool.append((w, None, d))
        return pool

    def weighted_pick(pool):
        total = sum(w for w, _, _ in pool)
        if total <= 0:
            return None
        x = rng.uniform(0, total)
        acc = 0.0
        for item in pool:
            acc += item[0]
            if x <= acc:
                return item
        return pool[-1]

    chosen, used_topics, used_domains = [], set(), []

    def last_session_had_new():
        if not log:
            return False
        last = log[-1]
        ldate = last.get("date")
        for tid in last.get("topic_ids") or []:
            hist = (topics.get(tid) or {}).get("history") or []
            if hist and hist[0].get("date") == ldate and not hist[0].get("migrated"):
                return True
        return False

    def label_of(tid):
        return (topics.get(tid) or {}).get("label") or (bp_topics.get(tid) or {}).get("label")

    def clip(text, n=240):
        text = str(text or "")
        return text if len(text) <= n else text[:n].rstrip() + " ..."

    def reason_for(tid, code):
        t = topics.get(tid) or {}
        if code == "due":
            nd = parse_date(t.get("next_due"))
            text = "spaced-repetition review due %s" % iso(nd)
            if t.get("mastery") is not None:
                text += "; last score %s/5 on %s" % (t.get("mastery"), t.get("last_tested"))
            if t.get("calibration") in ("overconfident", "confident_error"):
                text += "; flagged %s last time" % t["calibration"].replace("_", " ")
            g = gaps_by_topic.get(tid)
            if g:
                text += "; open gap: %s" % clip(g.get("gap"))
            return text
        if code == "gap":
            g = gaps_by_topic.get(tid) or {}
            src = g.get("source") or []
            src = ", ".join([src] if isinstance(src, str) else src)
            return "open gap (%s) from %s: %s" % (src, g.get("date"), clip(g.get("gap")))
        if code == "new":
            return "not yet tested; domain weighting from blueprint and your self-ratings"
        return code

    # ---- relatedness: an MCQ must not share, cue or overlap the case (version 3.1)
    refs = blueprint_refs(bp_topics)

    def label_tokens(tid):
        return significant_tokens(label_of(tid) or "")

    def related(a_id, b_id):
        if not a_id or not b_id:
            return False
        if a_id == b_id:
            return True
        ra_t, ra_d = refs.get(a_id, (set(), set()))
        rb_t, rb_d = refs.get(b_id, (set(), set()))
        da, db = infer_domain(a_id, topics.get(a_id)), infer_domain(b_id, topics.get(b_id))
        if b_id in ra_t or a_id in rb_t or (ra_t & rb_t):
            return True
        if db in ra_d or da in rb_d:
            return True
        return bool(label_tokens(a_id) & label_tokens(b_id))

    case_topics, case_domains = [], []

    def mcq_ok(tid, domain, level):
        """level 0: other domain than every chosen item, unrelated to all of them;
        level 1: other domain than the case, unrelated to the case and the other MCQs;
        level 2: any domain (domain rounds), but never the case's topic or anything related."""
        if tid in used_topics:
            return False
        if tid and any(related(tid, c) for c in case_topics):
            return False
        if level <= 1 and not restrict and domain in case_domains:
            return False
        if level == 0 and domain in used_domains:
            return False
        if level <= 1 and tid and any(related(tid, c["topic"]) for c in chosen if c["slot"] == "mcq"):
            return False
        return True

    def take(slot, level=0, new_only=False):
        sources = () if new_only else ((due_ids, "due"), (gap_ids, "gap"))
        for source, code in sources:
            for tid in source:
                if tid in used_topics:
                    continue
                d = infer_domain(tid, topics.get(tid))
                if slot == "mcq" and not mcq_ok(tid, d, level):
                    continue
                return {"slot": slot, "topic": tid, "label": label_of(tid), "domain": d,
                        "reason_code": code, "reason": reason_for(tid, code)}
        pool = new_candidates(set())
        if slot == "mcq":
            pool = [x for x in pool if mcq_ok(x[1], x[2], level)]
        pick = weighted_pick(pool)
        if pick:
            return {"slot": slot, "topic": pick[1], "label": label_of(pick[1]), "domain": pick[2],
                    "reason_code": "new", "reason": reason_for(pick[1], "new")}
        excl = set(case_domains if slot == "mcq" and not restrict else [])
        if slot == "mcq" and level == 0:
            excl |= set(used_domains)
        pick = weighted_pick(domain_only_candidates(excl))
        if pick:
            return {"slot": slot, "topic": None, "domain": pick[2], "reason_code": "new_in_domain",
                    "reason": "under-sampled domain; choose a specific topic not tested recently"
                              + ("" if slot != "mcq" else
                                 ", unrelated to the case (not its diagnosis, differential or a "
                                 "cross-referenced topic)")}
        return None

    def take_mcq(new_only=False):
        for level in (0, 1, 2):
            if level == 2 and not restrict and not args.allow_related:
                # outside a domain round, only fall back to the case's domain if nothing else exists
                others = [d for d in eff if d not in case_domains]
                if others:
                    break
            item = take("mcq", level, new_only)
            if item:
                same = item["domain"] in case_domains
                item["separation"] = ("same domain as the case (requested), unrelated topic" if same
                                      else "other domain" if level == 0
                                      else "other domain than the case")
                return item
        return None

    for i in range(n_essays):
        item = take("case")
        if item:
            chosen.append(item)
            used_topics.add(item["topic"])
            used_domains.append(item["domain"])
            case_topics.append(item["topic"])
            case_domains.append(item["domain"])
    # Breadth: reserve the last MCQ slot for a new topic in rounds of four or more items, and in
    # smaller rounds whenever the previous session introduced nothing new. Without this, the
    # review backlog crowds out the rest of the blueprint.
    reserve_new = False
    total = n_essays + n_mcqs
    wants_new = int(cfg.get("new_topics_per_round", 1) or 0) > 0 and not args.no_new
    if wants_new and n_mcqs >= 1 and total >= 2:
        reserve_new = total >= 4 or not last_session_had_new()
    for i in range(n_mcqs):
        item = None
        if reserve_new and i == n_mcqs - 1 and not any(c["reason_code"].startswith("new") for c in chosen):
            item = take_mcq(new_only=True)
        item = item or take_mcq()
        if item:
            chosen.append(item)
            used_topics.add(item["topic"])
            used_domains.append(item["domain"])

    fmt = cfg.get("case_format", "unfolding")
    if fmt == "alternate":
        last_fmt = next((s.get("case_format") for s in reversed(log) if s.get("case_format")), None)
        fmt = "discriminate" if last_fmt == "unfolding" else "unfolding"
    if int(cfg.get("session_minutes", 20) or 20) <= 12 and fmt == "unfolding":
        fmt = "discriminate"

    # Drills: at most one per round, on the case, at the rate set at the last review.
    drill = None
    active = [d for d in ledger.get("drill_targets") or []
              if not parse_date(d.get("until")) or parse_date(d.get("until")) >= today]
    case_items = [c for c in chosen if c["slot"] == "case"]
    if active and case_items and not args.no_drill:
        d = active[rng.randrange(len(active))]
        if args.force_drill or rng.random() < float(d.get("rate", 0.33)):
            drill = {"code": d.get("code"), "pattern": d.get("description") or d.get("code"),
                     "how": "Build the case so that this pattern is tempting but avoidable "
                            "(case_design.md section 9). Keep it blind; reveal it in the feedback."}
            case_items[0]["drill"] = drill
    # Novelty: what has already been used for these topics, so vignettes are not repeated.
    index = ledger.get("case_index") or []
    for c in chosen:
        same = [x for x in index if x.get("topic") == c.get("topic")]
        if same:
            c["already_used"] = [compact_case(x) for x in same[-12:]]
    recent_cases = [compact_case(x) for x in index if x.get("kind") != "mcq"][-15:]

    order = cfg.get("item_order", "mcqs_first")
    present = ([c for c in chosen if c["slot"] == "mcq"] + [c for c in chosen if c["slot"] == "case"]
               if order == "mcqs_first" else chosen)
    plan = {
        "ok": True, "date": iso(today), "case_format": fmt,
        "item_order": order,
        "presentation_order": ["%s %s" % (c["slot"], c.get("topic") or c.get("domain")) for c in present],
        "recent_cases_any_topic": recent_cases,
        "lab_units": cfg.get("lab_units"), "blood_gas_units": cfg.get("blood_gas_units"),
        "guideline_region": cfg.get("guideline_region"),
        "items": chosen,
        "note": "Do not reveal topics, domains, reasons or drills to the learner until all answers "
                "are in. Make every vignette and stem clearly different from 'already_used' and "
                "'recent_cases_any_topic' (patient, setting, presentation and twist).",
    }
    if args.out:
        # Blinding: the plan goes to a file and the command prints nothing topic-related, so no
        # topic appears in a tool-output preview. Read the file when drafting the sealed round.
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, indent=2, ensure_ascii=False)
        print(json.dumps({"ok": True, "out": args.out, "items": len(chosen),
                          "case_format": fmt, "item_order": order}))
    else:
        print(json.dumps(plan, indent=2, ensure_ascii=False))


def compact_case(x):
    if x.get("kind") == "mcq":
        return "%s %s MCQ: %s" % (x.get("log_id"), x.get("date"), x.get("stem"))
    bits = [x.get("patient"), x.get("setting"), x.get("presentation"), x.get("diagnosis")]
    text = " / ".join(str(b) for b in bits if b)
    if x.get("twist"):
        text += " (twist: %s)" % x["twist"]
    return "%s %s case: %s" % (x.get("log_id"), x.get("date"), text)


def ensure_topic(ledger, tid, domain=None, label=None):
    topics = ledger.setdefault("topics", {})
    if tid not in topics or not isinstance(topics[tid], dict):
        topics[tid] = {"domain": (domain or infer_domain(tid)).upper(), "attempts": 0,
                       "mastery": None, "sr_step": 0, "last_tested": None,
                       "next_due": None, "history": []}
    t = topics[tid]
    if domain and not t.get("domain"):
        t["domain"] = domain.upper()
    if label and not t.get("label"):
        t["label"] = label
    t.setdefault("history", [])
    t.setdefault("sr_step", 0)
    t.setdefault("attempts", 0)
    return t


def validate_round_v3(rnd):
    """Check the version 3 fields of a round; return warnings (never fatal for vocabulary)."""
    w = []
    for it in rnd.get("items") or []:
        c = it.get("coding")
        tid = it.get("topic")
        if not c:
            w.append("item %s has no 'coding' block" % tid)
            continue
        for k, v in (c.get("art") or {}).items():
            if k not in ART_MAX:
                w.append("%s: unknown ART domain %s" % (tid, k))
            elif v is not None and not (0 <= v <= ART_MAX[k]):
                w.append("%s: ART %s=%s outside 0-%d" % (tid, k, v, ART_MAX[k]))
        for k, v in (c.get("idea") or {}).items():
            if k not in IDEA_MAX:
                w.append("%s: unknown Revised-IDEA domain %s" % (tid, k))
            elif v is not None and not (0 <= v <= IDEA_MAX[k]):
                w.append("%s: IDEA %s=%s outside 0-%d" % (tid, k, v, IDEA_MAX[k]))
        for e in c.get("errors") or []:
            if e.get("category") not in ERROR_CATEGORIES:
                w.append("%s: error category %r not in %s" % (tid, e.get("category"), ERROR_CATEGORIES))
            if e.get("knowledge_type") and e["knowledge_type"] not in KNOWLEDGE_TYPES:
                w.append("%s: knowledge_type %r not in %s" % (tid, e["knowledge_type"], KNOWLEDGE_TYPES))
            if e.get("severity") and e["severity"] not in SEVERITIES:
                w.append("%s: severity %r not in %s" % (tid, e["severity"], SEVERITIES))
            if e.get("art_domain") and e["art_domain"] not in ART_MAX:
                w.append("%s: art_domain %r unknown" % (tid, e["art_domain"]))
            for b in e.get("bias") or []:
                if b not in BIASES and not str(b).startswith("other:"):
                    w.append("%s: bias %r not in the vocabulary (use other:<name>)" % (tid, b))
            if e.get("bias") and not e.get("bias_evidence"):
                w.append("%s: a bias label needs 'bias_evidence' (the learner's words)" % tid)
    d = rnd.get("drill")
    if d and d.get("result") not in DRILL_RESULTS:
        w.append("drill result must be one of %s" % (DRILL_RESULTS,))
    return w


def cmd_record(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    if ledger.get("schema_version", 1) < SCHEMA_VERSION:
        migrate_in_memory(ledger, today)
    rnd = load_json_arg(args.round)
    if not isinstance(rnd, dict) or not rnd.get("items"):
        die("round JSON must contain a non-empty 'items' list")
    rdate = parse_date(rnd.get("date")) or today
    cfg = ledger["config"]
    intervals = [int(x) for x in cfg.get("intervals_days") or DEFAULT_CONFIG["intervals_days"]]
    refl = rnd.get("reflection") or {}
    comfort_map = refl.get("topic_comfort") or {}
    overall_comfort = refl.get("overall_comfort")

    # group items by topic
    by_topic = {}
    for item in rnd["items"]:
        tid = item.get("topic")
        if not tid:
            die("every item needs a 'topic' id")
        if "mastery" not in item:
            die("item for %s lacks 'mastery' (0-5)" % tid)
        conf = item.get("confidence")
        if conf and conf.lower() not in CONFIDENCE_LEVELS:
            die("confidence must be one of %s" % (CONFIDENCE_LEVELS,))
        by_topic.setdefault(tid, []).append(item)

    warnings = validate_round_v3(rnd)

    gaps_in = rnd.get("gaps") or []
    resolved_in = rnd.get("resolved") or []
    new_gaps_by_topic = {}
    for g in gaps_in:
        if not g.get("topic") or not g.get("gap"):
            die("each gap needs 'topic' and 'gap'")
        new_gaps_by_topic.setdefault(g["topic"], []).append(g)

    self_gap_topics = {g["topic"] for g in gaps_in if (g.get("source") == "self")}
    summary = {}
    open_gaps = [g for g in ledger["open_gaps"] if isinstance(g, dict)]
    gap_index = {g.get("topic"): g for g in open_gaps}

    for tid, items in by_topic.items():
        domain = items[0].get("domain")
        label = next((it.get("label") for it in items if it.get("label")), None)
        t = ensure_topic(ledger, tid, domain, label)
        adj = [adjusted_item_mastery(it) for it in items]
        mastery = round_half(sum(m for m, _ in adj) / len(adj))
        misconception = any(mc for _, mc in adj)
        comfort = comfort_map.get(tid, overall_comfort if len(by_topic) == 1 else None)
        try:
            comfort = None if comfort is None else max(1, min(5, int(round(float(comfort)))))
        except (TypeError, ValueError):
            comfort = None
        step, next_due, calibration, interval = schedule_topic(
            t.get("sr_step"), mastery, comfort, misconception, tid in self_gap_topics,
            intervals, rdate)
        t["last_tested"] = iso(rdate)
        t["attempts"] = int(t.get("attempts") or 0) + 1
        t["mastery"] = mastery
        t["sr_step"] = step
        t["next_due"] = iso(next_due)
        t["self_comfort"] = comfort
        t["calibration"] = calibration
        t["history"].append({"date": iso(rdate), "mastery": mastery, "comfort": comfort,
                             "calibration": calibration,
                             "items": [{"type": it.get("type"), "correct": it.get("correct"),
                                        "confidence": it.get("confidence")} for it in items]})
        if misconception and not any("misconception" in str(g.get("source"))
                                     for g in new_gaps_by_topic.get(tid, [])):
            new_gaps_by_topic.setdefault(tid, []).append({
                "topic": tid, "source": "misconception", "auto": True,
                "gap": "Confident but incorrect answer on %s - re-test the same decision point." % iso(rdate)})
        summary[tid] = {"mastery": mastery, "sr_step": step, "next_due": iso(next_due),
                        "interval_days": interval, "calibration": calibration,
                        "comfort": comfort, "misconception": misconception}

    # self-reported gaps on topics not tested this round: create / pull forward
    # Iterate in a fixed order (first appearance in the round), never over a bare set: set order
    # depends on PYTHONHASHSEED, so the ledger (and its checksum) would differ between processes.
    for tid in [t for t in new_gaps_by_topic if t in self_gap_topics and t not in by_topic]:
        g0 = new_gaps_by_topic[tid][0]
        t = ensure_topic(ledger, tid, g0.get("domain"), g0.get("label"))
        target = rdate + dt.timedelta(days=7)
        current = parse_date(t.get("next_due"))
        if current is None:
            t["next_due"] = iso(target)
        elif current > target:
            t["next_due"] = iso(target)       # pull forward; never push an already-due topic back
        summary[tid] = {"self_reported_only": True, "next_due": t["next_due"]}

    # resolved notes -> archive
    archive = ledger.setdefault("resolved_gaps", [])
    resolved_by_topic = {}
    for r in resolved_in:
        if isinstance(r, str):
            r = {"topic": r, "note": None}
        resolved_by_topic.setdefault(r.get("topic"), []).append(r.get("note"))

    # update open gaps: one entry per topic
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
                # only an automatic flag was added: keep the prior gap text rather than lose it
                gap_text = "%s | %s" % (existing.get("gap"), gap_text) if existing.get("gap") else gap_text
                sources = sorted(set(sources) | set(existing.get("source") or []))
            entry = {"topic": tid, "gap": gap_text,
                     "self_reported": "; ".join(selfrep) or None,
                     "source": sources, "date": iso(rdate),
                     "resolved_prior": notes,
                     "opened": (existing or {}).get("opened") or (existing or {}).get("date") or iso(rdate)}
            if existing:
                open_gaps.remove(existing)
            open_gaps.append(entry)
            gap_index[tid] = entry
            for n in notes:
                archive.append({"topic": tid, "gap": n, "resolved": iso(rdate), "partial": True})
        elif existing and tid in by_topic:
            ex_date = parse_date(existing.get("date"))
            if mastery is not None and mastery >= 4 and cal not in ("overconfident", "confident_error") \
                    and (ex_date is None or ex_date < rdate):
                open_gaps.remove(existing)
                del gap_index[tid]
                archive.append({"topic": tid, "gap": existing.get("gap"),
                                "opened": existing.get("opened") or existing.get("date"),
                                "resolved": iso(rdate), "partial": False})
                summary.setdefault(tid, {})["gap_resolved"] = True
            else:
                existing["last_retested"] = iso(rdate)
    ledger["open_gaps"] = open_gaps

    # domain self-ratings (rolling, weighted toward history)
    ratings = ledger["profile"].setdefault("domain_self_ratings", {})
    for tid, s in summary.items():
        c = s.get("comfort")
        if c is None:
            continue
        d = ledger["topics"][tid]["domain"]
        prev = ratings.get(d)
        prev = prev.get("rating") if isinstance(prev, dict) else prev
        val = c if prev is None else round((2 * float(prev) + c) / 3.0, 1)
        ratings[d] = {"rating": val, "updated": iso(rdate)}

    # session log
    started, ended = rnd.get("started_at"), rnd.get("ended_at")
    minutes = rnd.get("minutes")
    if minutes is None and started and ended:
        try:
            a = dt.datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            b = dt.datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
            minutes = max(1, min(180, int(round((b - a).total_seconds() / 60.0))))
        except ValueError:
            minutes = None
    mcq_items = [it for it in rnd["items"] if it.get("type") == "mcq"]
    essay_items = [it for it in rnd["items"] if it.get("type") != "mcq"]
    all_m = [adjusted_item_mastery(it)[0] for it in rnd["items"]]
    entry = {
        "date": iso(rdate),
        "started_at": started, "ended_at": ended, "minutes": minutes,
        "reading_minutes": rnd.get("reading_minutes"),
        "topic_ids": list(by_topic.keys()),
        "essays": len(essay_items), "mcqs": len(mcq_items),
        "mcq_correct": sum(1 for it in mcq_items if it.get("correct") is True),
        "mean_score": round(sum(all_m) / len(all_m), 2),
        "case_format": rnd.get("case_format"),
        "items": [{"type": it.get("type"), "topic": it.get("topic"), "mastery": it.get("mastery"),
                   "correct": it.get("correct"), "confidence": it.get("confidence")}
                  for it in rnd["items"]],
        "selection_reasons": rnd.get("selection_reasons"),
        "self_performance": refl.get("performance"),
        "self_comfort": comfort_map or overall_comfort,
        "reflection": {"solid": refl.get("solid"), "gaps": refl.get("gaps"),
                       "skipped": bool(refl.get("skipped"))},
        "key_learning": rnd.get("key_learning") or [],
    }
    # ---- version 3 additions
    log_id = rnd.get("log_id") or next_log_id(ledger)
    if any(x.get("log_id") == log_id for x in sessions(ledger)):
        die("log_id %s is already used by another session" % log_id)
    max_recorded = max([id_num(x.get("log_id")) for x in sessions(ledger)] + [0])
    if id_num(log_id) <= max_recorded:
        warnings.append("log_id %s is not after the last recorded session S%04d" % (log_id, max_recorded))
    entry["log_id"] = log_id
    for k in ("title", "summary", "tags", "grade_changes", "drill", "coding_shown"):
        if k in rnd:
            entry[k] = rnd[k]
    coded = {}
    for it in rnd["items"]:
        if it.get("coding"):
            coded.setdefault(it.get("topic"), []).append(dict(it["coding"], type=it.get("type"),
                                                              confidence=it.get("confidence"),
                                                              correct=it.get("correct"),
                                                              mastery=it.get("mastery")))
    entry["items"] = [dict(e, coding=it.get("coding")) if it.get("coding") else e
                      for e, it in zip(entry["items"], rnd["items"])]
    ledger.setdefault("log", {"file": LOG_FILENAME})["last_id"] = log_id
    cases = ledger.setdefault("case_index", [])
    if rnd.get("case"):
        c = dict(rnd["case"]); c.setdefault("topic", next((it["topic"] for it in rnd["items"]
                                                           if it.get("type") != "mcq"), None))
        c["log_id"], c["date"] = log_id, iso(rdate)
        cases.append(c)
    for it in rnd["items"]:
        if it.get("type") == "mcq" and it.get("stem_summary"):
            cases.append({"log_id": log_id, "date": iso(rdate), "topic": it.get("topic"),
                          "kind": "mcq", "stem": it["stem_summary"]})
    # errata: corrections found in this session, plus pending ones from a review now logged
    errata_ids = []
    n = next_erratum_num(ledger)
    for e in rnd.get("errata") or []:
        if not e.get("corrects") or not e.get("correction"):
            die("each erratum needs 'corrects' (session id) and 'correction'")
        e = dict(e, id="E%04d" % n, found=e.get("found") or iso(rdate), logged_in=log_id)
        n += 1
        ledger.setdefault("errata", []).append(e)
        errata_ids.append(e["id"])
    pend = ledger.setdefault("pending_errata", [])
    wanted = rnd.get("pending_errata_logged") or []
    if wanted == "all":
        wanted = [e.get("id") for e in pend]
    for eid in wanted:
        hit = next((e for e in pend if e.get("id") == eid), None)
        if not hit:
            warnings.append("pending erratum %s not found" % eid)
            continue
        pend.remove(hit)
        ledger.setdefault("errata", []).append(dict(hit, logged_in=log_id))
        errata_ids.append(eid)
    if errata_ids:
        entry["errata"] = errata_ids
    if rnd.get("v3_setup_done"):
        ledger["profile"]["v3_setup_pending"] = False
    ledger["session_log"].append(entry)
    if ledger["profile"].get("needs_personalization") and rnd.get("personalized"):
        ledger["profile"]["needs_personalization"] = False

    out = args.out or args.ledger
    size = save_ledger(ledger, out)
    print(json.dumps({"ok": True, "path": out, "bytes": size,
                      "session_log_length": len(ledger["session_log"]),
                      "date": iso(rdate), "log_id": log_id, "topics": summary,
                      "errata_ids": errata_ids,
                      "errata_to_log": [e for e in ledger.get("errata") or [] if e.get("id") in errata_ids],
                      "open_gaps_count": len(ledger["open_gaps"]),
                      "warnings": warnings}, indent=2, ensure_ascii=False))


def item_outcome(it):
    if it.get("type") == "mcq":
        if it.get("correct") is None:
            return None
        return 1.0 if it.get("correct") else 0.0
    m = it.get("mastery")
    return None if m is None else max(0.0, min(1.0, float(m) / 5.0))


def coding_analytics(log):
    """Aggregate the per-item coding of a list of session-log entries."""
    items = [(s, it) for s in log for it in (s.get("items") or [])]
    coded = [(s, it, it.get("coding")) for s, it in items if it.get("coding")]
    art = {k: {"n": 0, "sum": 0.0, "scores": {}} for k in ART_MAX}
    idea_tot, idea_dom = [], {k: [] for k in IDEA_MAX}
    errs = []
    for s, it, c in coded:
        for k, v in (c.get("art") or {}).items():
            if k in art and isinstance(v, (int, float)):
                art[k]["n"] += 1
                art[k]["sum"] += float(v) / ART_MAX[k]
                art[k]["scores"][str(v)] = art[k]["scores"].get(str(v), 0) + 1
        idea = c.get("idea") or {}
        if idea and all(isinstance(idea.get(k), (int, float)) for k in IDEA_MAX):
            idea_tot.append(sum(idea[k] for k in IDEA_MAX))
            for k in IDEA_MAX:
                idea_dom[k].append(idea[k])
        for e in c.get("errors") or []:
            errs.append(dict(e, log_id=s.get("log_id"), date=s.get("date"),
                             topic=it.get("topic"), item_type=it.get("type")))

    def count(key, multi=False):
        out = {}
        for e in errs:
            vals = e.get(key) or []
            vals = vals if multi else [vals]
            for v in vals:
                if v:
                    out.setdefault(v, []).append(e.get("log_id"))
        return {k: {"n": len(v), "sessions": sorted(set(x for x in v if x), key=id_num)}
                for k, v in sorted(out.items(), key=lambda kv: -len(kv[1]))}

    # calibration of stated confidence against outcome
    table, brier = {}, []
    for s, it in items:
        conf = (it.get("confidence") or "").lower()
        out = item_outcome(it)
        if conf in CONF_PROB and out is not None:
            row = table.setdefault(conf, {"n": 0, "expected": CONF_PROB[conf], "obs_sum": 0.0})
            row["n"] += 1
            row["obs_sum"] += out
            brier.append((CONF_PROB[conf] - out) ** 2)
    for row in table.values():
        row["observed"] = round(row.pop("obs_sum") / row["n"], 2)
        row["gap"] = round(row["expected"] - row["observed"], 2)
    exp_all = [CONF_PROB[(it.get("confidence") or "").lower()] for s, it in items
               if (it.get("confidence") or "").lower() in CONF_PROB and item_outcome(it) is not None]
    obs_all = [item_outcome(it) for s, it in items
               if (it.get("confidence") or "").lower() in CONF_PROB and item_outcome(it) is not None]
    drills = [s.get("drill") for s in log if isinstance(s.get("drill"), dict)]
    gchanges = [g for s in log for g in (s.get("grade_changes") or [])]
    return {
        "sessions": len(log), "items": len(items), "items_coded": len(coded),
        "art_domains": {k: {"label": ART_LABELS[k], "n": v["n"],
                            "mean_fraction_of_max": round(v["sum"] / v["n"], 2) if v["n"] else None,
                            "score_counts": v["scores"]} for k, v in art.items()},
        "revised_idea": {"n": len(idea_tot),
                         "mean_total": round(sum(idea_tot) / len(idea_tot), 2) if idea_tot else None,
                         "share_high_quality": round(sum(1 for t in idea_tot if t >= 6) / len(idea_tot), 2)
                         if idea_tot else None,
                         "domain_means": {k: round(sum(v) / len(v), 2) if v else None
                                          for k, v in idea_dom.items()}},
        "errors": {"total": len(errs),
                   "per_session": round(len(errs) / len(log), 2) if log else None,
                   "by_category": count("category"), "by_knowledge_type": count("knowledge_type"),
                   "by_reasoning_step": count("art_domain"), "by_severity": count("severity"),
                   "by_bias": count("bias", multi=True),
                   "critical": [{"log_id": e["log_id"], "topic": e["topic"], "element": e.get("element")}
                                for e in errs if e.get("severity") == "critical"]},
        "confidence_calibration": {
            "table": table,
            "brier_score": round(sum(brier) / len(brier), 3) if brier else None,
            "overconfidence_index": round(sum(exp_all) / len(exp_all) - sum(obs_all) / len(obs_all), 2)
            if obs_all else None,
            "items_with_confidence": len(brier),
            "share_items_with_confidence": round(len(brier) / len(items), 2) if items else None},
        "reflection_skipped_share": round(sum(1 for s in log if (s.get("reflection") or {}).get("skipped"))
                                          / len(log), 2) if log else None,
        "drills": {"n": len(drills),
                   "results": {r: sum(1 for d in drills if d.get("result") == r) for r in DRILL_RESULTS},
                   "by_code": {c: [d.get("result") for d in drills if d.get("code") == c]
                               for c in sorted({d.get("code") for d in drills if d.get("code")})}},
        "grade_disputes": {"n": len(gchanges),
                           "outcomes": {o: sum(1 for g in gchanges if g.get("outcome") == o)
                                        for o in ("learner_right", "both_defensible", "upheld")}},
    }


def review_periods(ledger, today):
    """(current_start, inclusive), (previous_start, inclusive, previous_end) from the review history."""
    prof = ledger.get("profile") or {}
    cur = review_window(prof)
    dates = sorted(d for d in (parse_date(r.get("date")) for r in ledger.get("reviews") or []) if d)
    prev = None
    if dates:
        end = dates[-1]
        if len(dates) >= 2:
            prev = (dates[-2], False, end)
        else:
            prev = (parse_date(prof.get("onboarded_at")), True, end)
    return cur, prev


def cmd_stats(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    prof = ledger.get("profile") or {}
    cfg = ledger.get("config") or {}
    start, inclusive = review_window(prof, parse_date(args.since))
    if getattr(args, "all", False):
        start, inclusive = None, True
    since = start or dt.date.min
    log = [s for s in sessions(ledger) if in_window(s.get("date"), start, inclusive)]
    days = max(1, (today - since).days + (1 if inclusive else 0)) if start else None
    weeks = (days / 7.0) if days else None
    minutes = [s.get("minutes") for s in log if isinstance(s.get("minutes"), (int, float))]
    reading = [s.get("reading_minutes") for s in log if isinstance(s.get("reading_minutes"), (int, float))]
    untimed = len(log) - len(minutes)
    mcq_total = sum(int(s.get("mcqs") or 0) for s in log)
    mcq_correct = sum(int(s.get("mcq_correct") or 0) for s in log)

    per_domain = {}
    calib = {"aligned": 0, "overconfident": 0, "underconfident": 0, "confident_error": 0, "not_rated": 0}
    improved, declined = [], []
    for tid, t in (ledger.get("topics") or {}).items():
        if not isinstance(t, dict):
            continue
        hist = [h for h in t.get("history") or [] if in_window(h.get("date"), start, inclusive)]
        if not hist:
            continue
        d = infer_domain(tid, t)
        dd = per_domain.setdefault(d, {"topics": 0, "attempts": 0, "mastery_sum": 0.0})
        dd["topics"] += 1
        dd["attempts"] += len(hist)
        dd["mastery_sum"] += float(hist[-1].get("mastery") or 0)
        for h in hist:
            calib[h.get("calibration") or "not_rated"] = calib.get(h.get("calibration") or "not_rated", 0) + 1
        full = t.get("history") or []
        if len(full) >= 2:
            first = full[0].get("mastery")
            last = full[-1].get("mastery")
            if first is not None and last is not None:
                if last - first >= 1.5:
                    improved.append({"topic": tid, "from": first, "to": last})
                elif first - last >= 1.5:
                    declined.append({"topic": tid, "from": first, "to": last})
    for d, v in per_domain.items():
        v["mean_latest_mastery"] = round(v.pop("mastery_sum") / v["topics"], 2)

    resolved = [g for g in ledger.get("resolved_gaps") or []
                if in_window(g.get("resolved"), start, inclusive)]
    perf = [s.get("self_performance") for s in log if isinstance(s.get("self_performance"), (int, float))]
    scores = [s.get("mean_score") for s in log if isinstance(s.get("mean_score"), (int, float))]
    learning = []
    for s in log:
        for k in s.get("key_learning") or []:
            learning.append({"date": s.get("date"), "point": k})

    blueprint_domains = parse_blueprint(args.blueprint)[0] if args.blueprint else {}
    untouched = sorted(d for d in blueprint_domains if d not in per_domain)

    out = {
        "ok": True, "period_start": iso(start), "period_start_inclusive": inclusive if start else None, "period_end": iso(today),
        "sessions": len(log),
        "sessions_per_week": round(len(log) / weeks, 2) if weeks else None,
        "target_sessions_per_week": cfg.get("target_sessions_per_week"),
        "minutes_recorded": sum(minutes), "sessions_without_timing": untimed,
        "estimated_total_minutes": sum(minutes) + untimed * int(cfg.get("session_minutes") or 20),
        "reading_minutes_reported": sum(reading),
        "items": {"essays": sum(int(s.get("essays") or 0) for s in log), "mcqs": mcq_total,
                  "mcq_correct": mcq_correct,
                  "mcq_accuracy": round(mcq_correct / mcq_total, 2) if mcq_total else None},
        "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
        "mean_self_performance": round(sum(perf) / len(perf), 2) if perf else None,
        "per_domain": per_domain,
        "domains_not_covered": untouched,
        "calibration_counts": calib,
        "topics_improved": improved, "topics_declined": declined,
        "gaps_resolved": resolved,
        "open_gaps": ledger.get("open_gaps") or [],
        "key_learning": learning,
        "domain_self_ratings": prof.get("domain_self_ratings"),
        "goals": prof.get("goals"),
    }
    # ---- version 3: coded analysis for this period, the previous period and all time
    all_log = sessions(ledger)
    (_, _), prev = review_periods(ledger, today)
    prev_log = []
    if prev:
        p_start, p_incl, p_end = prev
        prev_log = [x for x in all_log if in_window(x.get("date"), p_start, p_incl)
                    and (parse_date(x.get("date")) or dt.date.min) <= p_end]
    long_open = [g for g in ledger.get("open_gaps") or []
                 if parse_date(g.get("opened") or g.get("date"))
                 and (today - parse_date(g.get("opened") or g.get("date"))).days >= 60]
    conf_err = {}
    for tid, t in (ledger.get("topics") or {}).items():
        n = sum(1 for h in (t.get("history") or []) if h.get("calibration") == "confident_error")
        if n >= 2:
            conf_err[tid] = n
    out["analysis"] = {
        "period": coding_analytics(log),
        "previous_period": coding_analytics(prev_log) if prev else None,
        "all_time": coding_analytics(all_log),
        "gaps_open_60_days_or_more": long_open,
        "topics_with_repeated_confident_errors": conf_err,
        "period_log_ids": [x.get("log_id") for x in log if x.get("log_id")],
        "previous_reviews": [{"date": r.get("date"), "report_file": r.get("report_file"),
                              "summary": r.get("summary"), "headline": (r.get("analysis") or {}).get("headline")}
                             for r in ledger.get("reviews") or []],
        "active_drills": ledger.get("drill_targets") or [],
        "pending_errata": ledger.get("pending_errata") or [],
        "errata_logged": ledger.get("errata") or [],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


def cmd_review(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    if ledger.get("schema_version", 1) < SCHEMA_VERSION:
        migrate_in_memory(ledger, today)
    rv = load_json_arg(args.review) or {}
    prof, cfg = ledger["profile"], ledger["config"]
    if rv.get("config_changes"):
        deep_merge(cfg, rv["config_changes"])
        cfg["default_session"] = normalize_session_shape(cfg.get("default_session"))
    if rv.get("profile_changes"):
        deep_merge(prof, rv["profile_changes"])
    for d, r in (rv.get("domain_self_ratings") or {}).items():
        prof.setdefault("domain_self_ratings", {})[d.upper()] = {"rating": r, "updated": iso(today)}
    for d, e in (rv.get("domain_emphasis") or {}).items():
        prof.setdefault("domain_emphasis", {})[d.upper()] = e
    warnings = []
    clamp_review_interval(cfg, warnings)
    prof["last_review"] = iso(today)
    prof["next_review_due"] = iso(today + dt.timedelta(days=int(cfg.get("review_interval_days") or 42)))
    prof["needs_personalization"] = False
    entry = {"date": iso(today)}
    for k in ("period_start", "stats", "learner_feedback", "goals", "summary",
              "config_changes", "profile_changes", "domain_self_ratings", "domain_emphasis",
              "analysis", "report_file", "deep_analysis", "change_plan"):
        if k in rv:
            entry[k] = rv[k]
    # drills replace the previous set (an empty list stops them)
    if "drill_targets" in rv:
        drills = []
        for d in rv["drill_targets"] or []:
            if not d.get("code"):
                die("each drill target needs a 'code' such as bias:premature_closure")
            drills.append({"code": d["code"], "description": d.get("description"),
                           "rate": max(0.0, min(1.0, float(d.get("rate", 0.33)))),
                           "set": iso(today), "until": d.get("until") or prof["next_review_due"]})
        ledger["drill_targets"] = drills
        entry["drill_targets"] = drills
    # guideline-change check of logged teaching points
    checks = ledger.setdefault("teaching_point_checks", {})
    n = next_erratum_num(ledger)
    new_errata = []
    for c in rv.get("teaching_point_checks") or []:
        if not c.get("id") or c.get("status") not in ("current", "changed", "superseded", "uncertain"):
            die("teaching_point_checks need 'id' and status current|changed|superseded|uncertain")
        checks[c["id"]] = {"checked": iso(today), "status": c["status"], "note": c.get("note"),
                           "source": c.get("source")}
        if c["status"] in ("changed", "superseded"):
            e = {"id": "E%04d" % n, "corrects": c["id"].split(".")[0], "point_id": c["id"],
                 "point": c.get("point"), "correction": c.get("note"), "source": c.get("source"),
                 "found": iso(today), "found_at": "review"}
            n += 1
            ledger.setdefault("pending_errata", []).append(e)
            checks[c["id"]]["erratum"] = e["id"]
            new_errata.append(e["id"])
    if rv.get("teaching_point_checks"):
        entry["teaching_points_checked"] = len(rv["teaching_point_checks"])
        entry["errata_found"] = new_errata
    ledger["reviews"].append(entry)
    out = args.out or args.ledger
    size = save_ledger(ledger, out)
    print(json.dumps({"ok": True, "path": out, "bytes": size, "reviews": len(ledger["reviews"]),
                      "next_review_due": prof["next_review_due"],
                      "drill_targets": ledger.get("drill_targets"),
                      "pending_errata": [e["id"] for e in ledger.get("pending_errata") or []],
                      "warnings": warnings}, indent=2))


def cmd_snooze(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    ledger.setdefault("profile", {})["next_review_due"] = iso(today + dt.timedelta(days=args.days))
    out = args.out or args.ledger
    size = save_ledger(ledger, out)
    print(json.dumps({"ok": True, "path": out, "bytes": size,
                      "next_review_due": ledger["profile"]["next_review_due"]}))


def cmd_settings(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    if ledger.get("schema_version", 1) < SCHEMA_VERSION:
        migrate_in_memory(ledger, today)
    if args.config:
        deep_merge(ledger["config"], load_json_arg(args.config))
        ledger["config"]["default_session"] = normalize_session_shape(ledger["config"].get("default_session"))
    if args.profile:
        deep_merge(ledger["profile"], load_json_arg(args.profile))
    warnings = []
    if args.config and "review_interval_days" in load_json_arg(args.config):
        clamp_review_interval(ledger["config"], warnings)
        last = parse_date(ledger["profile"].get("last_review")) or parse_date(ledger["profile"].get("onboarded_at"))
        if last:   # re-anchor the next review to the new interval
            ledger["profile"]["next_review_due"] = iso(
                max(today, last + dt.timedelta(days=int(ledger["config"]["review_interval_days"]))))
    out = args.out or args.ledger
    size = save_ledger(ledger, out)
    print(json.dumps({"ok": True, "path": out, "bytes": size, "warnings": warnings,
                      "config": ledger["config"], "profile": ledger["profile"]}, indent=2, ensure_ascii=False))


def cmd_validate(args):
    ledger = load_json(args.ledger)
    errors, warnings = [], []
    if ledger.get("schema_version", 1) < SCHEMA_VERSION:
        warnings.append("schema_version < %d: run migrate" % SCHEMA_VERSION)
    if not isinstance(ledger.get("topics"), dict):
        errors.append("topics must be an object")
    for key in ("open_gaps", "session_log"):
        if not isinstance(ledger.get(key), list):
            errors.append("%s must be a list" % key)
    for tid, t in (ledger.get("topics") or {}).items():
        if not isinstance(t, dict):
            errors.append("topic %s is not an object" % tid)
            continue
        for f in ("last_tested", "next_due"):
            if t.get(f) and not parse_date(t[f]):
                errors.append("topic %s: bad %s %r" % (tid, f, t[f]))
        m = t.get("mastery")
        if m is not None and not (0 <= float(m) <= 5):
            errors.append("topic %s: mastery out of range" % tid)
    seen_ids = set()
    for i, s in enumerate(ledger.get("session_log") or []):
        if not parse_date(s.get("date")):
            errors.append("session_log[%d]: bad date" % i)
        lid = s.get("log_id")
        if lid:
            if lid in seen_ids:
                errors.append("session_log[%d]: duplicate log_id %s" % (i, lid))
            seen_ids.add(lid)
    if ledger.get("schema_version", 1) >= 3:
        for key in ("case_index", "errata", "pending_errata", "drill_targets"):
            if not isinstance(ledger.get(key), list):
                errors.append("%s must be a list" % key)
        if not isinstance(ledger.get("teaching_point_checks"), dict):
            errors.append("teaching_point_checks must be an object")
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings,
                      "topics": len(ledger.get("topics") or {}),
                      "sessions": len(ledger.get("session_log") or [])}, indent=2))
    sys.exit(0 if not errors else 1)

# ------------------------------------------------------------- session log (v3)
#
# CME_session_log.md is append-only. Each session is one entry framed by HTML comment markers
# (invisible when the Markdown is rendered). Part A (case, questions, answers, feedback) is
# written right after the feedback; part B (reflection, discussion, grade changes, coded
# analysis, errata) closes the entry. Addenda record discussion that continues after closing.


LOG_HEADER = """# Clinical CME — session log

Every CME session, in full: the case and questions as presented, your answers, the feedback,
your reflection and any discussion, with a coded analysis of the reasoning. The clinical-cme
skill appends one entry per session and never edits old entries; corrections are added as
dated errata that point back to the entry they correct.

Search tips: an entry starts with `## S0042 · date · title`. Search for a session ID
(`S0042`), a blueprint topic (`#RENAL-02`), a diagnosis or concept tag (`#hyponatraemia`), a
thinking pattern (`#premature-closure`) or any word. Corrections: search `Erratum`.

Please do not edit this file by hand; keep your own notes in a separate file.
"""

RE_BEGIN = re.compile(r"^<!-- cme:entry (S\d{3,}) begin -->\s*$")
RE_PART_A = re.compile(r"^<!-- cme:entry (S\d{3,}) part-a-end -->\s*$")
RE_END = re.compile(r"^<!-- cme:entry (S\d{3,}) end -->\s*$")
RE_ADD_BEGIN = re.compile(r"^<!-- cme:addendum (S\d{3,}) begin -->\s*$")
RE_ADD_END = re.compile(r"^<!-- cme:addendum (S\d{3,}) end -->\s*$")
RE_HEAD = re.compile(r"^## (S\d{3,}) · (\d{4}-\d{2}-\d{2}) · (.*)$")
MARKER = re.compile(r"<!--\s*cme:")

PART_A_SECTIONS = ("Case", "Questions", "Your answers", "Feedback")
PART_B_SECTIONS = ("Reflection", "Discussion", "Grade changes", "Coded analysis")
SECTION_KEYS = {           # heading prefix (after '### ') -> section key for --sections
    "case": "case", "questions": "questions", "your answers": "answers",
    "stage 2": "stage2", "your final answers": "answers", "feedback": "feedback",
    "reflection": "reflection", "discussion": "discussion", "grade changes": "grades",
    "coded analysis": "coding", "errata": "errata", "reconstructed record": "reconstructed",
    "note": "note", "addendum": "addendum",
}


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write_text_atomic(path, text):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".cmelog-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        mode = (os.stat(path).st_mode & 0o777) if os.path.exists(path) else 0o644
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return read_text(path)


def parse_log(text):
    """Return {"blocks": [...], "errors": [...], "warnings": [...]}.

    Each block: kind (entry/addendum), id, date, title, summary, tags, part_a, closed,
    start, end (line indices), lines.
    """
    blocks, errors, warnings = [], [], []
    if not text:
        return {"blocks": blocks, "errors": errors, "warnings": warnings}
    lines = text.split("\n")
    cur = None
    for i, line in enumerate(lines):
        m = RE_BEGIN.match(line) or RE_ADD_BEGIN.match(line)
        if m:
            if cur and not cur["closed"]:
                errors.append("%s %s opened at line %d is not closed before line %d"
                              % (cur["kind"], cur["id"], cur["start"] + 1, i + 1))
            cur = {"kind": "entry" if RE_BEGIN.match(line) else "addendum", "id": m.group(1),
                   "date": None, "title": None, "summary": None, "tags": [],
                   "part_a": False, "closed": False, "start": i, "end": None}
            blocks.append(cur)
            continue
        if cur is None:
            continue
        m = RE_PART_A.match(line)
        if m:
            if m.group(1) != cur["id"] or cur["kind"] != "entry":
                errors.append("line %d: part-a marker for %s inside %s" % (i + 1, m.group(1), cur["id"]))
            cur["part_a"] = True
            continue
        m = RE_END.match(line) or RE_ADD_END.match(line)
        if m:
            if m.group(1) != cur["id"]:
                errors.append("line %d: end marker for %s inside %s" % (i + 1, m.group(1), cur["id"]))
            cur["closed"] = True
            cur["end"] = i
            if cur["kind"] == "entry":
                cur["part_a"] = True
            continue
        if cur["kind"] == "entry" and not cur["closed"]:
            h = RE_HEAD.match(line)
            if h and cur["title"] is None:
                if h.group(1) != cur["id"]:
                    errors.append("line %d: heading id %s differs from marker %s" % (i + 1, h.group(1), cur["id"]))
                cur["date"], cur["title"] = h.group(2), h.group(3).strip()
            elif line.startswith("**Summary:**") and cur["summary"] is None:
                cur["summary"] = line[len("**Summary:**"):].strip()
            elif line.startswith("**Tags:**") and not cur["tags"]:
                cur["tags"] = re.findall(r"#([^\s#,]+)", line)
    for b in blocks:
        if b["end"] is None:
            b["end"] = len(lines) - 1
    seen, last = set(), 0
    for b in blocks:
        if b["kind"] != "entry":
            continue
        if b["id"] in seen:
            errors.append("duplicate entry id %s" % b["id"])
        seen.add(b["id"])
        if id_num(b["id"]) <= last:
            warnings.append("entry %s is out of order" % b["id"])
        last = max(last, id_num(b["id"]))
        if not b["title"]:
            errors.append("entry %s has no '## %s · date · title' heading" % (b["id"], b["id"]))
    entry_ids = {b["id"] for b in blocks if b["kind"] == "entry"}
    for b in blocks:
        if b["kind"] == "addendum" and b["id"] not in entry_ids:
            warnings.append("addendum refers to unknown entry %s" % b["id"])
    open_entries = [b["id"] for b in blocks if b["kind"] == "entry" and not b["closed"]]
    if len(open_entries) > 1:
        errors.append("more than one open entry: %s" % ", ".join(open_entries))
    return {"blocks": blocks, "errors": errors, "warnings": warnings, "lines": lines}


def log_summary(path):
    text = read_text(path)
    parsed = parse_log(text or "")
    entries = [b for b in parsed["blocks"] if b["kind"] == "entry"]
    open_e = [b["id"] for b in entries if not b["closed"]]
    return {
        "exists": text is not None,
        "bytes": len(text.encode("utf-8")) if text is not None else 0,
        "sha256": sha256_text(text) if text is not None else None,
        "entries": len(entries),
        "first_id": entries[0]["id"] if entries else None,
        "last_id": max((b["id"] for b in entries), key=id_num) if entries else None,
        "open_entry": open_e[0] if open_e else None,
        "open_entry_part_a": (next(b["part_a"] for b in entries if b["id"] == open_e[0])
                              if open_e else None),
        "errors": parsed["errors"], "warnings": parsed["warnings"],
    }


def clean_tags(raw):
    out = []
    for t in re.split(r"[,\s]+", raw or ""):
        t = t.strip().lstrip("#")
        if t:
            out.append("#" + t)
    return " ".join(dict.fromkeys(out))


def check_body(body, required):
    if MARKER.search(body):
        die("the body contains a '<!-- cme:' marker; remove it (markers are written by the script)")
    headings = [l[4:].strip().lower() for l in body.split("\n") if l.startswith("### ")]
    missing = [r for r in required if not any(h.startswith(r.lower()) for h in headings)]
    return missing


def cmd_log_append(args):
    text = read_text(args.log)
    created = text is None
    if created:
        text = LOG_HEADER
    if not text.endswith("\n"):
        text += "\n"
    parsed = parse_log(text)
    if parsed["errors"] and not args.force:
        die("log has structural errors; run log-check (or pass --force): %s" % "; ".join(parsed["errors"][:5]))
    blocks = parsed["blocks"]
    entries = [b for b in blocks if b["kind"] == "entry"]
    open_entry = next((b for b in entries if not b["closed"]), None)
    sid = args.session
    if not re.match(r"^S\d{3,}$", sid or ""):
        die("--session must look like S0042")
    body = ""
    if args.body:
        body = read_text(args.body)
        if body is None:
            die("body file not found: %s" % args.body)
    body = body.strip("\n")
    if not body.strip() and args.part != "B" or (args.part == "B" and not body.strip() and args.kind != "closing-note"):
        die("--body is required and must not be empty")
    warnings = []
    now = dt.datetime.now().strftime("%H:%M")

    if args.part in ("A", "AB"):
        if any(b["id"] == sid for b in entries):
            die("entry %s already exists in the log" % sid)
        if open_entry:
            die("entry %s is still open; close it with --part B before starting %s" % (open_entry["id"], sid))
        if not (args.title and args.summary):
            die("--title and --summary are required for a new entry")
        if entries and id_num(sid) <= max(id_num(b["id"]) for b in entries):
            warnings.append("%s is not after the last entry %s" % (sid, entries[-1]["id"]))
        req = PART_A_SECTIONS if args.part == "A" else PART_A_SECTIONS + PART_B_SECTIONS
        if args.kind == "reconstructed":
            req = ()
        missing = check_body(body, req)
        if missing:
            warnings.append("missing sections: %s" % ", ".join(missing))
        date = args.date or iso(today_from(args))
        meta = [s for s in (args.meta or "").split("|") if s.strip()]
        block = ["", "<!-- cme:entry %s begin -->" % sid,
                 "## %s · %s · %s" % (sid, date, args.title.strip()), "",
                 "**Summary:** %s" % " ".join(args.summary.split()),
                 "**Tags:** %s" % clean_tags(args.tags)]
        if meta:
            block.append("**Session:** %s" % " · ".join(m.strip() for m in meta))
        block += ["", body, ""]
        block.append("<!-- cme:entry %s %s -->" % (sid, "part-a-end" if args.part == "A" else "end"))
        addition = "\n".join(block) + "\n"
    elif args.part == "B":
        if not open_entry or open_entry["id"] != sid:
            die("part B needs %s to be the open entry (open entry: %s)"
                % (sid, open_entry["id"] if open_entry else "none"))
        if not open_entry["part_a"]:
            die("%s has no part A end marker" % sid)
        missing = check_body(body, () if args.kind == "closing-note" else PART_B_SECTIONS)
        if missing:
            warnings.append("missing sections: %s" % ", ".join(missing))
        addition = "\n" + body + "\n\n<!-- cme:entry %s end -->\n" % sid
    elif args.part == "addendum":
        target = next((b for b in entries if b["id"] == sid), None)
        if not target:
            die("no entry %s to add to" % sid)
        if not target["closed"]:
            die("%s is still open: put the discussion in its part B instead" % sid)
        check_body(body, ())
        date = args.date or iso(today_from(args))
        heading = "### Addendum to %s · %s %s" % (sid, date, args.time or now)
        if args.recorded_in:
            heading += " (recorded in %s)" % args.recorded_in
        addition = "\n".join(["", "<!-- cme:addendum %s begin -->" % sid, heading, "", body, "",
                              "<!-- cme:addendum %s end -->" % sid]) + "\n"
    else:
        die("unknown part")

    new_text = text + addition
    result = parse_log(new_text)
    if result["errors"] and not args.force:
        die("refusing to write: the result would be malformed: %s" % "; ".join(result["errors"][:5]))
    original = "" if created else read_text(args.log)
    out_text = write_text_atomic(args.log, new_text)
    if out_text != new_text or (original and not out_text.startswith(original.rstrip("\n"))):
        die("write could not be verified: re-read content differs")
    summ = log_summary(args.log)
    print(json.dumps({"ok": True, "path": args.log, "created": created, "part": args.part,
                      "session": sid, "bytes": summ["bytes"], "sha256": summ["sha256"],
                      "entries": summ["entries"], "last_id": summ["last_id"],
                      "open_entry": summ["open_entry"], "warnings": warnings}, indent=2))


def cmd_log_check(args):
    summ = log_summary(args.log)
    errors, warnings = list(summ["errors"]), list(summ["warnings"])
    cross = None
    if args.ledger:
        ledger = load_json(args.ledger)
        ids_ledger = [s.get("log_id") for s in sessions(ledger) if s.get("log_id")]
        text = read_text(args.log) or ""
        ids_log = [b["id"] for b in parse_log(text)["blocks"] if b["kind"] == "entry"]
        closed = {b["id"] for b in parse_log(text)["blocks"] if b["kind"] == "entry" and b["closed"]}
        cross = {
            "in_ledger_not_in_log": [i for i in ids_ledger if i not in ids_log],
            "in_log_not_in_ledger": [i for i in ids_log if i not in ids_ledger
                                     and i not in ((ledger.get("log") or {}).get("not_recorded") or [])],
            "sessions_without_log_id": sum(1 for s in sessions(ledger) if not s.get("log_id")),
            "next_session_id": next_log_id(ledger, summ["last_id"]),
        }
        for i in cross["in_log_not_in_ledger"]:
            warnings.append("%s is in the log but not in the ledger (%s)"
                            % (i, "closed" if i in closed else "open: a session that was not saved"))
    print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings,
                      "log": {k: summ[k] for k in ("exists", "bytes", "sha256", "entries",
                                                   "first_id", "last_id", "open_entry")},
                      "ledger_cross_check": cross}, indent=2))
    sys.exit(0 if not errors else 1)


def _block_text(lines, b):
    return "\n".join(lines[b["start"]:b["end"] + 1])


def _filter_sections(block_text, keys):
    if not keys:
        return block_text
    out, keep = [], True
    for line in block_text.split("\n"):
        if line.startswith("### "):
            head = line[4:].strip().lower()
            key = next((v for k, v in SECTION_KEYS.items() if head.startswith(k)), None)
            keep = key in keys if key else False
            if head.startswith("addendum"):
                keep = "addendum" in keys or "discussion" in keys
        elif line.startswith("<!-- cme:") or line.startswith("## ") \
                or line.startswith("**Summary:**") or line.startswith("**Tags:**") \
                or line.startswith("**Session:**"):
            out.append(line)
            continue
        if keep:
            out.append(line)
    return "\n".join(out)


def _select_blocks(parsed, args):
    blocks = parsed["blocks"]
    ids = None
    if getattr(args, "id", None):
        ids = {args.id}
    if getattr(args, "ids", None):
        ids = set(x.strip() for x in args.ids.split(",") if x.strip())
    since, until = parse_date(getattr(args, "since", None)), parse_date(getattr(args, "until", None))
    entries = {b["id"]: b for b in blocks if b["kind"] == "entry"}
    chosen = []
    for b in blocks:
        e = entries.get(b["id"])
        if e is None:
            continue
        if ids is not None and b["id"] not in ids:
            continue
        d = parse_date(e["date"])
        if since and (d is None or d < since):
            continue
        if until and (d is None or d > until):
            continue
        chosen.append(b)
    return chosen


def cmd_log_index(args):
    text = read_text(args.log)
    if text is None:
        die("log not found: %s" % args.log)
    parsed = parse_log(text)
    lines = parsed["lines"]
    rows = []
    for b in _select_blocks(parsed, args):
        if b["kind"] != "entry":
            continue
        if args.tag and args.tag.lstrip("#").lower() not in [t.lower() for t in b["tags"]]:
            continue
        if args.grep:
            related = [x for x in parsed["blocks"] if x["id"] == b["id"]]
            hay = "\n".join(_block_text(lines, x) for x in related).lower()
            if args.grep.lower() not in hay:
                continue
        rows.append({"id": b["id"], "date": b["date"], "title": b["title"],
                     "summary": b["summary"], "tags": b["tags"],
                     "complete": b["closed"],
                     "addenda": sum(1 for x in parsed["blocks"]
                                    if x["kind"] == "addendum" and x["id"] == b["id"])})
    if args.format == "md":
        print("| ID | Date | Title | Summary |\n|---|---|---|---|")
        for r in rows:
            print("| %s | %s | %s | %s |" % (r["id"], r["date"], r["title"], (r["summary"] or "").replace("|", "/")))
    else:
        print(json.dumps({"ok": True, "count": len(rows), "entries": rows}, indent=2, ensure_ascii=False))


def cmd_log_extract(args):
    text = read_text(args.log)
    if text is None:
        die("log not found: %s" % args.log)
    parsed = parse_log(text)
    chosen = _select_blocks(parsed, args)
    if not args.addenda:
        chosen = [b for b in chosen if b["kind"] == "entry"]
    keys = set(k.strip().lower() for k in (args.sections or "").split(",") if k.strip())
    parts = [_filter_sections(_block_text(parsed["lines"], b), keys) for b in chosen]
    out = "\n\n".join(parts) + "\n"
    if args.out:
        write_text_atomic(args.out, out)
        print(json.dumps({"ok": True, "path": args.out, "blocks": len(chosen),
                          "ids": sorted({b["id"] for b in chosen}, key=id_num),
                          "chars": len(out)}, indent=2))
    else:
        sys.stdout.write(out)


def _stub_body(ledger, s):
    topics = ledger.get("topics") or {}
    lines = ["### Reconstructed record", "",
             "> Recorded before version 3 of the skill, which did not keep the case, answers or "
             "feedback. This stub is rebuilt from the ledger's session log.", ""]
    for it in s.get("items") or []:
        tid = it.get("topic")
        label = (topics.get(tid) or {}).get("label") or ""
        res = ""
        if it.get("type") == "mcq":
            res = {True: "correct", False: "incorrect"}.get(it.get("correct"), "")
        conf = it.get("confidence")
        lines.append("- %s %s %s: mastery %s/5%s%s" % (
            "Case" if it.get("type") != "mcq" else "MCQ", tid, ("(" + label + ")") if label else "",
            it.get("mastery"), (", " + res) if res else "", (", " + conf) if conf else ""))
    refl = s.get("reflection") or {}
    if refl.get("skipped"):
        lines += ["", "Reflection: skipped."]
    else:
        if refl.get("solid"):
            lines += ["", "Felt solid: %s" % refl["solid"]]
        if refl.get("gaps"):
            lines += ["Felt shaky: %s" % refl["gaps"]]
    if s.get("key_learning"):
        lines += ["", "Key learning:"] + ["- %s" % k for k in s["key_learning"]]
    return "\n".join(lines)


def cmd_log_backfill(args):
    ledger = load_json(args.ledger)
    text = read_text(args.log)
    if text is not None and any(b["kind"] == "entry" for b in parse_log(text)["blocks"]):
        die("the log already has entries; backfill only runs on an empty log")
    text = text if text is not None else LOG_HEADER
    if not text.endswith("\n"):
        text += "\n"
    topics = ledger.get("topics") or {}
    written = []
    for i, s in enumerate(sessions(ledger)):
        if s.get("log_id"):
            continue
        sid = "S%04d" % (i + 1)
        labels = [(topics.get(t) or {}).get("label") or t for t in s.get("topic_ids") or []]
        title = "Reconstructed: " + "; ".join(labels[:3]) if labels else "Reconstructed session"
        summary = (s.get("key_learning") or ["Session recorded before the full log existed."])[0]
        tags = " ".join(["#" + t for t in s.get("topic_ids") or []] + ["#reconstructed"])
        block = ["", "<!-- cme:entry %s begin -->" % sid,
                 "## %s · %s · %s" % (sid, s.get("date"), title), "",
                 "**Summary:** %s" % " ".join(str(summary).split()),
                 "**Tags:** %s" % tags, "", _stub_body(ledger, s), "",
                 "<!-- cme:entry %s end -->" % sid]
        text += "\n".join(block) + "\n"
        s["log_id"] = sid
        written.append(sid)
    if parse_log(text)["errors"]:
        die("backfill produced a malformed log: %s" % parse_log(text)["errors"][:3])
    ledger.setdefault("log", {}).update({"backfilled": True,
                                         "last_id": written[-1] if written else (ledger.get("log") or {}).get("last_id")})
    write_text_atomic(args.log, text)
    size = save_ledger(ledger, args.out or args.ledger)
    summ = log_summary(args.log)
    print(json.dumps({"ok": True, "entries_written": len(written), "ids": written,
                      "log_bytes": summ["bytes"], "log_sha256": summ["sha256"],
                      "ledger_bytes": size}, indent=2))


def cmd_log_mark_unrecorded(args):
    ledger = load_json(args.ledger)
    meta = ledger.setdefault("log", {"file": LOG_FILENAME})
    lst = meta.setdefault("not_recorded", [])
    if args.id not in lst:
        lst.append(args.id)
    if id_num(args.id) > id_num(meta.get("last_id")):
        meta["last_id"] = args.id
    size = save_ledger(ledger, args.out or args.ledger)
    print(json.dumps({"ok": True, "not_recorded": lst, "bytes": size}))


def teaching_points(ledger):
    pts = []
    for i, s in enumerate(sessions(ledger)):
        base = s.get("log_id") or "L%04d" % (i + 1)
        for j, k in enumerate(s.get("key_learning") or []):
            pid = "%s.%d" % (base, j + 1)
            chk = (ledger.get("teaching_point_checks") or {}).get(pid) or {}
            pts.append({"id": pid, "date": s.get("date"), "topics": s.get("topic_ids"),
                        "point": k, "last_checked": chk.get("checked"), "status": chk.get("status")})
    return pts


def cmd_teaching_points(args):
    today = today_from(args)
    ledger = load_json(args.ledger)
    pts = teaching_points(ledger)
    if args.due_check:
        prof = ledger.get("profile") or {}
        start, inclusive = review_window(prof)
        stale = today - dt.timedelta(days=args.max_age)
        due = []
        for p in pts:
            if p["status"] == "superseded":
                continue
            checked = parse_date(p["last_checked"])
            if checked is None or checked < stale:
                in_period = in_window(p["date"], start, inclusive)
                due.append((0 if (checked is None and in_period) else 1 if checked is None else 2,
                            p["date"] or "", p))
        due.sort(key=lambda x: (x[0], x[1]))
        due = [p for _, _, p in due]
        pts = due[:args.limit]
    print(json.dumps({"ok": True, "count": len(pts), "points": pts}, indent=2, ensure_ascii=False))


def main(argv=None):
    p = argparse.ArgumentParser(description="Ledger helper for the clinical-cme skill.")
    p.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init");      s.add_argument("--out", required=True)
    s.add_argument("--profile");     s.add_argument("--config")
    s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_init)

    s = sub.add_parser("migrate");   s.add_argument("ledger"); s.add_argument("--out")
    s.set_defaults(fn=cmd_migrate)

    s = sub.add_parser("status");    s.add_argument("ledger"); s.add_argument("--log")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("select");    s.add_argument("ledger")
    s.add_argument("--blueprint");   s.add_argument("--essays", type=int)
    s.add_argument("--mcqs", type=int); s.add_argument("--domain")
    s.add_argument("--seed", type=int); s.add_argument("--allow-repeat", action="store_true")
    s.add_argument("--no-new", action="store_true", help="fill every slot from reviews and gaps")
    s.add_argument("--no-drill", action="store_true"); s.add_argument("--force-drill", action="store_true")
    s.add_argument("--allow-related", action="store_true",
                   help="last resort: allow MCQs from the case's domain outside a domain round")
    s.add_argument("--out", help="write the plan here and print only a neutral summary")
    s.set_defaults(fn=cmd_select)

    s = sub.add_parser("record");    s.add_argument("ledger")
    s.add_argument("--round", required=True, help="round JSON (inline or path)")
    s.add_argument("--out");         s.set_defaults(fn=cmd_record)

    s = sub.add_parser("stats");     s.add_argument("ledger")
    s.add_argument("--since");       s.add_argument("--blueprint")
    s.add_argument("--all", action="store_true", help="the whole history as the period")
    s.set_defaults(fn=cmd_stats)

    s = sub.add_parser("review");    s.add_argument("ledger")
    s.add_argument("--review", required=True); s.add_argument("--out"); s.set_defaults(fn=cmd_review)

    s = sub.add_parser("snooze-review"); s.add_argument("ledger")
    s.add_argument("--days", type=int, default=7); s.add_argument("--out"); s.set_defaults(fn=cmd_snooze)

    s = sub.add_parser("settings");  s.add_argument("ledger")
    s.add_argument("--config");      s.add_argument("--profile"); s.add_argument("--out")
    s.set_defaults(fn=cmd_settings)

    s = sub.add_parser("validate");  s.add_argument("ledger"); s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("log-append"); s.add_argument("log")
    s.add_argument("--session", required=True, help="entry id, e.g. S0042")
    s.add_argument("--part", required=True, choices=["A", "B", "AB", "addendum"])
    s.add_argument("--body", help="Markdown file with the sections to append")
    s.add_argument("--title"); s.add_argument("--summary"); s.add_argument("--tags")
    s.add_argument("--meta", help="'|'-separated session facts for the header line")
    s.add_argument("--date"); s.add_argument("--time"); s.add_argument("--recorded-in")
    s.add_argument("--kind", default="session", choices=["session", "reconstructed", "closing-note"])
    s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_log_append)

    s = sub.add_parser("log-check"); s.add_argument("log"); s.add_argument("--ledger")
    s.set_defaults(fn=cmd_log_check)

    s = sub.add_parser("log-index"); s.add_argument("log")
    s.add_argument("--grep"); s.add_argument("--tag"); s.add_argument("--since"); s.add_argument("--until")
    s.add_argument("--ids"); s.add_argument("--format", choices=["json", "md"], default="json")
    s.set_defaults(fn=cmd_log_index)

    s = sub.add_parser("log-extract"); s.add_argument("log")
    s.add_argument("--id"); s.add_argument("--ids"); s.add_argument("--since"); s.add_argument("--until")
    s.add_argument("--sections", help="comma list: case,questions,answers,stage2,feedback,"
                                      "reflection,discussion,grades,coding,errata,addendum")
    s.add_argument("--no-addenda", dest="addenda", action="store_false")
    s.add_argument("--out"); s.set_defaults(fn=cmd_log_extract)

    s = sub.add_parser("log-backfill"); s.add_argument("log"); s.add_argument("ledger")
    s.add_argument("--out", help="write the ledger here instead of in place")
    s.set_defaults(fn=cmd_log_backfill)

    s = sub.add_parser("log-mark-unrecorded"); s.add_argument("ledger"); s.add_argument("--id", required=True)
    s.add_argument("--out"); s.set_defaults(fn=cmd_log_mark_unrecorded)

    s = sub.add_parser("teaching-points"); s.add_argument("ledger")
    s.add_argument("--due-check", action="store_true",
                   help="only points from this review period not yet checked, or checked long ago")
    s.add_argument("--max-age", type=int, default=365); s.add_argument("--limit", type=int, default=40)
    s.set_defaults(fn=cmd_teaching_points)

    # allow --today after the subcommand as well
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--today" in argv:
        i = argv.index("--today")
        if i + 1 < len(argv):
            val = argv[i + 1]
            del argv[i:i + 2]
            argv = ["--today", val] + argv
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()

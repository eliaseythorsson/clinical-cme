#!/usr/bin/env python3
"""clinical-cme v5.0.0 state engine (standard library only, Python 3.8+).

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

A job is one work folder. The commands, what each takes and prints, and the files of the work
folder are tabled once, in COMMANDS, MAINTENANCE_COMMANDS and WORK_FILES below: `cme.py
command-table` and `cme.py file-table` print them as references/state_schema.md (§6, §6.1)
holds them. A round in short: start → present → answer (which writes the grading form,
round.json) → save → answer --part reflection (the reflection form) → close.

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
SKILL_VERSION = "5.0.0"
PAGE_VERSION = "5.4.0"   # templates/page.html carries <meta name="cme-page-version" content="5.4.0">

DEFAULT_CONFIG = {
    # The mix a new learner starts with: one focused question and the case, about 35 minutes
    # (MINUTES_PER). MCQs are the learner's choice (onboarding.md §2).
    "session_minutes": 35,
    "mcqs": 0,
    "focused": 1,                        # focused questions per round (mini-case, one free-text question)
    "case": True,
    "round_set_at": None,                # when the round mix (mcqs/focused/case) was last set; see apply_prefs
    "case_format": "unfolding",          # unfolding | discriminate | alternate
    "feedback_depth": "detailed",        # standard | detailed
    "evidence_ladder": True,             # feedback goes further behind the recommendation the more often a
                                         # topic is answered well (EVIDENCE_DEPTHS)
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
    "listening": True,                   # one podcast episode per topic at the end of a round (issue #50)
    "resource_preferences": {"free_only": False, "formats": ["guidelines", "review articles"]},
}
# A ledger written before the mix was a setting of its own has no `mcqs`, `focused` or `case`: it
# keeps the mix every round had then, whatever a new learner's default becomes.
LEGACY_MIX = {"mcqs": 3, "focused": 0, "case": True}
DEFAULT_PROFILE = {
    "display_name": None, "specialty": "Internal/hospital medicine", "subspecialty": None,
    # Where you are / where you're aiming: the learner's own paragraphs, which the author pitches
    # to (standards.md rule 4), and when each was last written (setup, a chat, or the page).
    "journey": "", "journey_set_at": None, "aim": "", "aim_set_at": None,
    # Display only, derived by the assistant from the paragraphs; None: not derived yet.
    "journey_label": None, "aim_tags": None,
    "practice_setting": [], "goals": [], "strengths": [], "weaknesses": [],
    "domain_self_ratings": {}, "domain_emphasis": {}, "notes": "", "onboarded_at": None,
    "podcast_sources": None,             # {"trusted": [shows], "avoid": [shows]}; None until the learner was asked
}
# The two open questions, word for word the same at setup (onboarding.md §2) and on the page.
JOURNEY_QUESTION = ("In a few sentences, describe where you are in your training or career and how you'd "
                    "rate your own knowledge and clinical skills: for example your stage, your specialty, "
                    "how independently you work, and what kinds of decisions you're comfortable making.")
AIM_QUESTION = ("What do you want these rounds to help you achieve? For example an exam you're preparing "
                "for, the level you want to reach, where you want to be stronger, or anything else.")
STAGE_LABELS = ("medical student", "intern", "resident", "fellow", "attending", "senior attending")
AIM_TAGS = ("exam", "independent practice", "specialist-level decisions outside own specialty",
            "keep up to date", "teach")
PARAGRAPHS = (("journey", "journey_label", "where you are"), ("aim", "aim_tags", "where you're aiming"))
PARAGRAPH_MAX = 4000     # characters kept of a paragraph
# Settings that cannot change what a round contains (its plan, its items, its keys, its feedback
# notes): changing only these keeps the round prepared ahead. Every other setting, including one
# this list has never heard of, sets it aside. `round_set_at` is here because it only dates the
# mix: the mix itself (mcqs, focused, case) is not. See state_schema.md §8.
CONTENT_NEUTRAL_CONFIG = ("testing", "reminders", "prepare_task", "prepare_ahead", "helpers", "show_coding",
                          "target_sessions_per_week", "review_interval_days", "round_set_at")
# The labels are display only (never used to write an item), and the `_set_at` stamps only date
# the paragraphs: the paragraphs themselves are not here.
CONTENT_NEUTRAL_PROFILE = ("display_name", "onboarded_at", "journey_label", "aim_tags",
                           "journey_set_at", "aim_set_at")
# Listening (issue #50; references/standards.md, rule 8): a pick is one Spotify episode of
# 15 to 90 minutes; a kit keeps three candidates per topic.
SPOTIFY_EPISODE_RE = re.compile(r"^https://open\.spotify\.com/episode/[A-Za-z0-9]{22}$")
LISTEN_MINUTES = (15, 90)
LISTEN_CANDIDATES = 3
LISTEN_SOURCES = ("kit", "search")
# Further reading (issue #51; references/feedback_guide.md §2 E): at most two pointers a round,
# each an http(s) link to the document with the section to read.
READING_MAX = 2
READING_LINK_RE = re.compile(r"^https?://[^\s/]+\.[^\s]+$")
SELF_RATING_FACTOR = {1: 1.6, 2: 1.3, 3: 1.0, 4: 0.8, 5: 0.6}
MIN_RETURN_DAYS = 3      # no tested topic and no open gap comes back sooner than this (ADR 0003)
# Drill-down limit (ADR 0003): no topic is in more than this many rounds in a row, and a topic
# missed again once its drill-down is used up waits at least the pause before it comes back. A
# theme topic seen in this many rounds of the block waits the pause after each further round on
# it (issue #79).
DRILLDOWN_MAX_ROUNDS = 2
DRILLDOWN_PAUSE_DAYS = 7
DRILLDOWN_BLOCK_ROUNDS = 2
# Themed blocks (ADR 0003): a run of rounds on one domain. Shares are of a round's short questions,
# in percent; the case is always on the theme.
BLOCK_LENGTH = 12
BLOCK_SHARES = (("theme", 60), ("repeat", 25), ("wildcard", 15))
# A large backlog (issue #79): while this many topics are overdue, repeats take 40%, the extra
# from the theme's share; the wildcard keeps its 15%. Same order of shares as BLOCK_SHARES.
BACKLOG_OVERDUE = 6
BACKLOG_SHARES = (("theme", 45), ("repeat", 40), ("wildcard", 15))
MIN_THEME_TOPICS = 4     # a domain with fewer blueprint topics is not proposed as a theme
THEME_REST_BLOCKS = 4    # a domain's pull as the next theme recovers over this many blocks after its own
# Evidence depth (feedback_guide.md §4.1): how far behind the recommendation the feedback on an
# item goes when it is answered well. Earned per topic, and per aspect for a focused question:
# (name, answered well this many times in a row before this round). An item that is missed, or
# written on an open gap, is taught at the first depth whatever the topic had reached.
EVIDENCE_DEPTHS = (("guidance", 0), ("studies", 1), ("design", 2), ("frontier", 4))
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
# The learner's stop (issue #75): "I know this, stop bringing it back". It sets the learner's
# score (this one when they name none), closes the topic's gaps and schedules the topic at the
# longest interval. A position note kept with it lapses when no progress review has confirmed
# it for this many days.
STOP_SCORE = 5
POSITION_LAPSE_DAYS = 182
ITEM_TYPES = ("case", "essay", "mcq", "focused")      # "essay" = the name older ledgers use for a case
FOCUSED_ASPECTS = ("diagnosis", "interpretation", "testing", "management", "disposition",
                   "prevention", "prognosis")
# Drills that can be built into a mini-case (used only when the round has no full case).
FOCUSED_DRILLS_EXCLUDED = ("bias:anchoring", "bias:search_satisficing", "art:PR", "art:DDX")
ROUND_LIMITS = {"mcqs": (0, 10), "focused": (0, 6)}
# Rough minutes per item, answering plus reading its feedback: the plan's estimate and the one
# the page shows (round_minutes). A one-step case ("discriminate") is shorter than an unfolding one.
MINUTES_PER = {"mcq": 5, "focused": 10, "unfolding": 25, "discriminate": 15}
# Measured time (issue #47). A round is timed from the stamps the engine sets as the round goes
# (round_timing); a stretch without any step longer than IDLE_GAP_MINUTES counts for that long
# and the rest is cut. The estimates move from MINUTES_PER to the learner's own pace over
# PACE_FULL_ROUNDS timed rounds; the hint appears from HINT_MIN_ROUNDS.
IDLE_GAP_MINUTES = 15
PACE_FULL_ROUNDS = 10
HINT_MIN_ROUNDS = 5
TIMED_MIN_MINUTES = 3        # below this the stamps were not set as the round went: not a timed round
PACE_LIMITS = (0.25, 4.0)    # a round's minutes against the defaults for its mix, kept within reason
READING_WPM = 200            # reading the short questions' feedback, when the case came in the same message
LEGACY_MINUTES_CAP = 180     # what older versions capped a whole session at: such a value is no measurement
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
    """Apply what the learner set on their page (database document cme/prefs): the round mix
    and the two paragraphs, where you are and where you're aiming.

    prefs = {"round": {"mcqs": 2, "focused": 1, "case": true}, "base": <config.round_set_at the
    page saw>, "updated": "<ISO time of the change>",
    "journey": {"text": "…", "updated": "<ISO time>"}, "aim": {"text": "…", "updated": "<ISO time>"}};
    every part is optional. The learner's latest explicit choice wins. The mix:
    - `base` equals the ledger's round_set_at: nothing changed the mix since the page saw it, so
      the page's mix is applied;
    - `updated` equals round_set_at: this document was applied before, nothing to do;
    - otherwise the mix was set elsewhere (in a chat, or by an earlier page document) after the
      page loaded: the document is applied only if its `updated` is later than round_set_at,
      and an older one is ignored.
    Applying sets round_set_at to `updated`, so a document is applied once. A paragraph
    (apply_paragraphs) goes by its own `updated` in the same way. An invalid page setting is
    ignored with a warning, never fatal. Returns the changes applied: the mix settings that
    changed, and "journey" / "aim": "updated" for a new paragraph."""
    if not prefs:
        return {}
    warnings = warnings if warnings is not None else []
    if not isinstance(prefs, dict):
        warnings.append("page settings ignored: expected {round: {...}, base, updated}")
        return {}
    paragraphs = apply_paragraphs(state, prefs, warnings)
    if "round" not in prefs and any(k in prefs for k, _, _ in PARAGRAPHS):
        return paragraphs       # a document that holds paragraphs only
    if not isinstance(prefs.get("round"), dict) or not prefs.get("updated"):
        warnings.append("page settings ignored: expected {round: {...}, base, updated}")
        return paragraphs
    cfg = state["config"]
    set_at = cfg.get("round_set_at")
    if prefs.get("base") != set_at:
        if str(prefs["updated"]) == set_at:
            return paragraphs     # applied before
        mine, theirs = parse_stamp(str(prefs["updated"])), parse_stamp(set_at)
        if set_at is not None and not (mine and theirs and mine > theirs):
            return paragraphs     # overtaken by a later change in a chat
    trial = {k: cfg.get(k, LEGACY_MIX[k]) for k in ("mcqs", "focused", "case")}
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
        return paragraphs
    changes = {k: v for k, v in trial.items() if cfg.get(k, LEGACY_MIX[k]) != v}
    cfg.update(trial)
    cfg["round_set_at"] = str(prefs["updated"])
    changes.update(paragraphs)
    return changes or {"unchanged": True}


def apply_paragraphs(state, prefs, warnings):
    """The paragraphs the learner wrote on their page ("Update" under where you are / where
    you're aiming): prefs["journey"] / prefs["aim"] = {"text": "…", "updated": "<ISO time>"}.
    One is applied when its `updated` is later than the time the ledger's paragraph was last
    written (profile.journey_set_at / aim_set_at; none: never dated), so it is applied once and
    a later change made in a chat wins. Applying keeps the learner's words as they are, dates
    the paragraph and clears its label for the assistant to derive again. Returns
    {"journey": "updated", …} for those applied."""
    prof = state.setdefault("profile", {})
    done = {}
    for key, label, name in PARAGRAPHS:
        doc = prefs.get(key)
        if doc is None:
            continue
        text = doc.get("text") if isinstance(doc, dict) else None
        stamp = parse_stamp(doc.get("updated")) if isinstance(doc, dict) else None
        if not isinstance(text, str) or not text.strip() or not stamp:
            warnings.append("page settings ignored: %s needs {text, updated} (%s)" % (key, name))
            continue
        set_at = prof.get(key + "_set_at")
        theirs = parse_stamp(set_at)
        if set_at is not None and not (theirs and stamp > theirs):
            continue        # applied before, or overtaken by a later change in a chat
        text = text.strip()[:PARAGRAPH_MAX]
        prof[key + "_set_at"] = str(doc["updated"])
        if text != (prof.get(key) or "").strip():
            prof[key] = text
            prof[label] = None
            done[key] = "updated"
    return done


def paragraphs_changed(changes):
    """The paragraphs among the changes apply_prefs returned, in the learner's terms."""
    return [name for key, _, name in PARAGRAPHS if key in (changes or {})]


STAGE_FROM_ROLE = (      # an old `role`, read for a display label only; first match wins
    ("medical student", r"student"), ("intern", r"\bintern\b|foundation"),
    ("resident", r"resident|registrar|trainee|house officer"), ("fellow", r"fellow"),
    ("senior attending", r"senior (attending|consultant|physician|specialist)|chief|professor"),
    ("attending", r"attending|consultant|hospitalist|specialist|internist|physician"))


def migrate_profile(st):
    """A ledger from before the paragraphs: fold `role` and `notes` into `journey`, and `goals`
    into `aim`, where the paragraph is still empty, in the learner's own words (nothing is
    rephrased or dropped). The old fields stay as they are and are no longer read for the
    pitch. A stage label is read off `role` when that names a stage; otherwise the labels are
    left for the assistant (`labels_needed`). Changes `st` in place; a no-op afterwards."""
    prof = st.get("profile")
    if not isinstance(prof, dict):
        return st
    def words(v):
        if isinstance(v, (list, tuple)):
            return [x.strip() for x in v if isinstance(x, str) and x.strip()]
        return [v.strip()] if isinstance(v, str) and v.strip() else []
    if not words(prof.get("journey")):
        parts = words(prof.get("role")) + words(prof.get("notes"))
        if parts:
            prof["journey"] = "\n\n".join(parts)
            if not prof.get("journey_label"):
                role = " ".join(words(prof.get("role"))).lower()
                prof["journey_label"] = next((lab for lab, rx in STAGE_FROM_ROLE if role and re.search(rx, role)), None)
    if not words(prof.get("aim")):
        parts = words(prof.get("goals"))
        if parts:
            prof["aim"] = "\n".join(parts)
            prof.setdefault("aim_tags", None)
    return st


def check_paragraphs(prof):
    """Validate the paragraphs and their labels in a profile (after a change). Dies with a plain
    message."""
    for key, _, name in PARAGRAPHS:
        v = prof.get(key)
        if v is not None and not isinstance(v, str):
            die("%s (%s) must be text: the learner's own paragraph" % (key, name))
        if isinstance(v, str) and len(v) > PARAGRAPH_MAX:
            die("%s (%s) is longer than %d characters" % (key, name, PARAGRAPH_MAX))
    label = prof.get("journey_label")
    if label is not None and label not in STAGE_LABELS:
        die("journey_label must be one of: %s (or null)" % ", ".join(STAGE_LABELS))
    tags = prof.get("aim_tags")
    if tags is not None and (not isinstance(tags, list) or any(t not in AIM_TAGS for t in tags)):
        die("aim_tags must be a list of: %s (an empty list when none fits, or null)" % "; ".join(AIM_TAGS))


def set_paragraphs(prof, was, changes):
    """After `changes` were merged into profile `prof` (which was `was`): a paragraph that got new
    words is dated now, so an older page setting no longer applies, and loses its label unless
    the same change gives one."""
    for key, label, _ in PARAGRAPHS:
        if key in changes and (prof.get(key) or "") != (was.get(key) or ""):
            if key + "_set_at" not in changes:
                prof[key + "_set_at"] = now_ts()
            if label not in changes:
                prof[label] = None


def labels_needed(st):
    """What the assistant still has to derive for display: for each paragraph that has words and
    no label yet, the paragraph and the labels to choose from. None when nothing is needed."""
    prof = st.get("profile") or {}
    out = {}
    for key, label, name in PARAGRAPHS:
        if isinstance(prof.get(key), str) and prof[key].strip() and prof.get(label) is None:
            out[label] = {"from": prof[key], "paragraph": name,
                          "choose": ("one of" if key == "journey" else "any of"),
                          "labels": list(STAGE_LABELS if key == "journey" else AIM_TAGS)}
    return out or None


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


def repeat_write(st, gens):
    """A step run again in the same job (`save`, `close`) counts as the write it repeats: when
    nothing was written since its first run (`gens`: the generation before and after that run),
    the generation goes back to where the first run found it, and the bump_gen that follows gives
    the same generation again."""
    if gens and st.get("gen") == gens[1]:
        st["gen"] = gens[0]


def deep_merge(target, changes):
    for k, v in (changes or {}).items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_merge(target[k], v)
        else:
            target[k] = v


def listening_on(st):
    """Listening is on unless the learner turned it off; a ledger older than the setting has it on."""
    return (st.get("config") or {}).get("listening", True) is not False


def podcast_sources(value, where="podcast_sources"):
    """The learner's podcast sources in their one form: {"trusted": [shows], "avoid": [shows]},
    each a list of names without blanks or repeats. None (never asked) reads as two empty lists.
    Stops on anything else, so a mistyped setting is never stored."""
    if value is None:
        return {"trusted": [], "avoid": []}
    if not isinstance(value, dict) or set(value) - {"trusted", "avoid"}:
        die('%s must be {"trusted": [shows], "avoid": [shows]}' % where)
    out = {}
    for k in ("trusted", "avoid"):
        v = value.get(k)
        v = [] if v is None else [v] if isinstance(v, str) else v
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            die("%s.%s must be a list of show names" % (where, k))
        names = []
        for x in v:
            x = " ".join(x.split())
            if x and x.casefold() not in [n.casefold() for n in names]:
                names.append(x)
        out[k] = names
    return out


def listening_status(st):
    """What `start` and the plan say about listening: whether it is on, the shows to prefer and
    to avoid, and whether the learner is still to be asked for them (once)."""
    on = listening_on(st)
    return dict(podcast_sources((st.get("profile") or {}).get("podcast_sources"), "profile.podcast_sources"),
                on=on, ask_sources=on and (st.get("profile") or {}).get("podcast_sources") is None)


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


def item_answered_well(it):
    """One recorded item cleared the bar: scored 4 or more as the schedule counts it (a guessed
    MCQ does not), with no misconception."""
    if it.get("mastery") is None:
        return False
    m, misconception = adjusted_item_mastery(it)
    return m >= 4 and not misconception


def answered_in_a_row(st, tid, aspect=None):
    """How many times in a row, counting back from the last round, the items on topic `tid`
    were answered well; with `aspect`, only its focused questions on that aspect."""
    n = 0
    for s in reversed((st.get("previous") or []) + (st.get("sessions") or [])):
        for it in reversed(s.get("items") or []):
            if it.get("topic") != tid or (aspect and it.get("aspect") != aspect):
                continue
            if not item_answered_well(it):
                return n
            n += 1
    return n


def depth_level(in_a_row):
    return max(i for i, (_, need) in enumerate(EVIDENCE_DEPTHS, 1) if in_a_row >= need)


def evidence_depth(st, tid, aspect=None, retests=False):
    """The evidence depth an item on topic `tid` earns if it is answered well in the round to
    come: {"level": 1–4, "name", "in_a_row"}. None with the ladder turned off. A focused
    question goes at most one depth beyond what its own aspect of the topic has earned; an item
    on an open gap (`retests`, or any gap open on the topic) stays at the first depth."""
    if not st["config"].get("evidence_ladder", True):
        return None
    run = answered_in_a_row(st, tid) if tid else 0
    level = depth_level(run)
    if aspect and level > 1:
        level = min(level, depth_level(answered_in_a_row(st, tid, aspect)) + 1)
    if retests or any(g.get("topic") == tid for g in st.get("gaps") or []):
        level = 1
    return {"level": level, "name": EVIDENCE_DEPTHS[level - 1][0], "in_a_row": run}


def block_rounds_on(st, tid, block):
    """How many earlier rounds of the block `block` (its `theme`, and `round`: the number of the
    round being planned or applied) were on topic `tid`, counting back through the rounds
    recorded with that block (each session keeps its `block`)."""
    if not block or not block.get("theme"):
        return 0
    want, n = int(block.get("round") or 0) - 1, 0
    for s in reversed((st.get("previous") or []) + (st.get("sessions") or [])):
        b = s.get("block") or {}
        if want < 1 or b.get("theme") != block["theme"] or int(b.get("round") or 0) != want:
            break
        n += tid in (s.get("topics") or [])
        want -= 1
    return n


def drilldown_over(state, tid, theme, block=None):
    """True when a miss on topic `tid` in the round being applied should not bring it straight
    back. In the block's theme a topic may be drilled twice in the block (issue #79): over when
    an earlier round of the block (`block`: theme and this round's number) was on it, or the
    round before was. Outside the theme a miss gets one targeted retest: over when the topic
    already had an open gap or was missed the last time it was tested."""
    t = state["topics"].get(tid) or {}
    if theme and t.get("domain") == theme:
        return (bool(state["sessions"]) and tid in (state["sessions"][-1].get("topics") or [])) \
            or block_rounds_on(state, tid, block) + 1 >= DRILLDOWN_BLOCK_ROUNDS
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


def block_mix(shorts, n, backlog=False):
    """How many of a round's `shorts` short questions go to the theme, to due repeats and to the
    wildcard in round `n` of a block. The shares (60/25/15) are met over the block, not in each
    round: with three short questions a round would otherwise never have a wildcard. Round n gets
    what the first n rounds are owed (largest remainder) less what the first n-1 were given.
    With a large `backlog` (BACKLOG_SHARES, issue #79) the theme hands the repeats what the
    difference of the two shares owes the first n rounds (rounded up, so the first round of a
    backlog gains at once) less what the first n-1 were owed; the wildcard is untouched, so its
    share over the block holds however often the backlog comes and goes."""
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
    mix = {name: mix[i] for i, (name, _) in enumerate(BLOCK_SHARES)}
    if backlog:
        extra = dict(BACKLOG_SHARES)["repeat"] - dict(BLOCK_SHARES)["repeat"]
        def ceil_owed(k):
            return -(-shorts * k * extra // 100)
        shift = min(mix["theme"], ceil_owed(max(1, n)) - ceil_owed(max(1, n) - 1))
        mix["theme"] -= shift
        mix["repeat"] += shift
    return mix


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


def median(values):
    v = sorted(values)
    return None if not v else (v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2.0)


def round_timing(stamps):
    """The measured time of a round from its stamps, [{"what", "at"}, …] in any order:
    {"started_at", "ended_at", "minutes", "timing": {"answering", "waiting", "reading",
    "idle_cut"}} in minutes, or None with fewer than two usable stamps.

    A stamp is a message from the learner arriving (`start`, `answer:<part>`, `close`), a
    message going out (`sent:<part>`) or another step (`save`, `answer:notes`). The time
    after a message arrived, until the next one goes out, is the learner **waiting**; the time
    after one went out is the learner's: **reading** after the final feedback, **answering**
    after anything else. The short questions' feedback and the case go out in one message, so
    the time after it is answering, less the time its words take to read (READING_WPM, at most
    half). A stretch between two stamps longer than IDLE_GAP_MINUTES counts for that long; the
    rest is `idle_cut`. The round ends when the reflection arrives."""
    events = []
    for i, e in enumerate(stamps or []):
        t = parse_stamp(e.get("at")) if isinstance(e, dict) else None
        if t and isinstance(e.get("what"), str):
            w = e["what"]               # at the same second: the start, then what arrived, then what went out
            events.append((t, 0 if w == "start" else 2 if w.startswith("sent:") else 1, i, w, e))
    whats = [ev[3] for ev in events]
    # `save` stands for the final feedback only where nothing else says when that went out
    events = sorted((ev[0], ev[1:3], ev[3], ev[4]) for ev in events
                    if not (ev[3] == "save" and "sent:feedback" in whats))
    seen, kept = set(), []
    for ev in events:                       # the first of each step counts: a command run again changes nothing
        w = ev[2]
        if w in seen and (w.startswith("sent:") or w in ("start", "save", "close")):
            continue
        seen.add(w)
        kept.append(ev)
        if w in ("close", "answer:reflection"):
            break                           # the reflection arrived: the round ends here
    if len(kept) < 2:
        return None
    has_case = any(w in ("answer:case", "answer:final", "sent:stage2", "sent:case") for w in whats)
    final = "feedback" if "sent:feedback" in whats or has_case else "questions_feedback"
    cap = IDLE_GAP_MINUTES * 60.0
    secs = {"answering": 0.0, "waiting": 0.0, "reading": 0.0, "idle_cut": 0.0}
    mode, words = "waiting", None
    for (t0, _, w, e), (t1, _, _, _) in zip(kept, kept[1:]):
        if w.startswith("sent:"):
            part = w[5:]
            mode = "reading" if part in (final, "close") else "answering"
            words = e.get("words") if part == "questions_feedback" and mode == "answering" else None
        elif w == "save" and "sent:feedback" not in whats and mode == "waiting":
            mode, words = "reading", None   # no stamp for the final feedback: it was out when it was saved
        elif w == "start" or (w.startswith("answer:") and w != "answer:notes") or w == "close":
            mode, words = "waiting", None
        gap = max(0.0, (t1 - t0).total_seconds())
        counted = min(gap, cap)
        secs["idle_cut"] += gap - counted
        if mode == "answering" and isinstance(words, (int, float)) and words > 0:
            read = min(counted / 2.0, words * 60.0 / READING_WPM)
            secs["reading"] += read
            counted -= read
            words = None                    # read once
        secs[mode] += counted
    active = secs["answering"] + secs["waiting"] + secs["reading"]
    return {"started_at": kept[0][3]["at"], "ended_at": kept[-1][3]["at"],
            "minutes": max(1, int(round(active / 60.0))),
            "timing": {k: round(v / 60.0, 1) for k, v in secs.items()}}


def is_timed(sess):
    """A session whose minutes were measured from stamps. Sessions of older versions are not:
    they have no `timing`, and their minutes were the time from start to end capped at 180
    (LEGACY_MINUTES_CAP), which a session left open reached."""
    m, t = sess.get("minutes"), sess.get("timing")
    if not isinstance(t, dict) or not isinstance(m, (int, float)) or isinstance(m, bool):
        return False
    return m >= TIMED_MIN_MINUTES and not (m == LEGACY_MINUTES_CAP and t.get("answering") is None)


def session_default_minutes(sess):
    """What MINUTES_PER gives for the items a past session had."""
    fmt = sess.get("format")
    return round_minutes(sess.get("mcqs"), sess.get("focused"), fmt in ("unfolding", "discriminate"), fmt)


def timed_rounds(st):
    """The last timed rounds (at most PACE_FULL_ROUNDS), oldest first."""
    rounds = [s for s in (st.get("previous") or []) + (st.get("sessions") or [])
              if is_timed(s) and session_default_minutes(s) > 0]
    return rounds[-PACE_FULL_ROUNDS:]


def pace(st):
    """How the learner's measured rounds compare with the defaults:
    {"rounds": n, "own": f, "factor": b, "median_minutes": m}.

    Minutes are measured per round, not per item, so they are not shared out among item
    types: each timed round gives one number, its minutes over what MINUTES_PER gives for its
    own mix, and `own` is the median of those over the last timed rounds. `factor` is what
    every estimate is multiplied by: 1 (the defaults) with no timed round, moving a tenth of
    the way to `own` with each timed round, and `own` itself from PACE_FULL_ROUNDS."""
    rounds = timed_rounds(st)
    n = len(rounds)
    if not n:
        return {"rounds": 0, "own": None, "factor": 1.0, "median_minutes": None}
    own = median([min(PACE_LIMITS[1], max(PACE_LIMITS[0], s["minutes"] / float(session_default_minutes(s))))
                  for s in rounds])
    w = min(n, PACE_FULL_ROUNDS) / float(PACE_FULL_ROUNDS)
    return {"rounds": n, "own": round(own, 3), "factor": round(1.0 + w * (own - 1.0), 3),
            "median_minutes": int(round(median([s["minutes"] for s in rounds])))}


def paced(minutes, factor):
    """An estimate at the learner's pace, in whole minutes (the default itself at factor 1)."""
    return minutes if factor == 1.0 else int(round(minutes * factor))


def based_on(n):
    """How an estimate that uses the learner's own times says so; None for the defaults."""
    return None if not n else "based on your last round" if n == 1 else "based on your last %d rounds" % n


def mix_estimate(st):
    """(the round mix in force, the minutes a round of it is estimated to take at the learner's
    pace, the number of timed rounds that pace rests on)."""
    cfg = st.get("config") or {}
    mix = {"mcqs": int(cfg.get("mcqs", LEGACY_MIX["mcqs"]) or 0), "focused": int(cfg.get("focused", 0) or 0),
           "case": bool(cfg.get("case", True))}
    p = pace(st)
    return (mix, paced(round_minutes(mix["mcqs"], mix["focused"], mix["case"], next_case_format(st)), p["factor"]),
            p["rounds"])


def time_hint(st):
    """Once HINT_MIN_ROUNDS rounds are timed: {"text", "median", "budget", "rounds", "drop",
    "saves"}, the sentence the close and the page show. Over budget, it names the one change
    to the mix in force (some MCQs, some focused questions, the case, or a one-step case) that
    brings a round nearest the budget, at the learner's own pace; None before that."""
    p = pace(st)
    if p["rounds"] < HINT_MIN_ROUNDS:
        return None
    cfg = st.get("config") or {}
    budget = int(cfg.get("session_minutes") or DEFAULT_CONFIG["session_minutes"])
    med = p["median_minutes"]
    out = {"median": med, "budget": budget, "rounds": p["rounds"], "drop": None, "saves": None}
    if med <= budget:
        out["text"] = "Your rounds take a median of %d min, within your budget of %d." % (med, budget)
        return out
    mix, fmt, own = mix_estimate(st)[0], next_case_format(st), p["own"]
    now = round_minutes(mix["mcqs"], mix["focused"], mix["case"], fmt) * own
    items = mix["mcqs"] + mix["focused"] + (1 if mix["case"] else 0)
    options = []                            # (minutes saved, what to say), smallest change first
    for key, one, many in (("mcqs", "MCQ", "MCQs"), ("focused", "focused question", "focused questions")):
        per = MINUTES_PER["mcq" if key == "mcqs" else "focused"] * own
        for k in range(1, mix[key] + 1):
            if items - k >= 1:
                options.append((k * per, "dropping %s" % ("one %s" % one if k == 1 else "%d %s" % (k, many))))
    if mix["case"]:
        if fmt == "unfolding":
            options.append(((MINUTES_PER["unfolding"] - MINUTES_PER["discriminate"]) * own,
                            "a one-step case instead of an unfolding one"))
        if items > 1:
            options.append((MINUTES_PER[fmt] * own, "dropping the case"))
    text = "Your rounds take a median of %d min against your budget of %d" % (med, budget)
    if options:
        saves, what = min(options, key=lambda o: abs(now - o[0] - budget))
        out["drop"], out["saves"] = what, int(round(saves))
        text += "; %s would save about %d min" % (what, out["saves"])
    out["text"] = text + "."
    return out


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
    # A large backlog (issue #79): topics whose date has come, counted as `status` counts them.
    overdue = sum(1 for t in topics.values() if parse_date(t.get("due")) and parse_date(t["due"]) <= today)
    backlog = bool(theme) and overdue >= BACKLOG_OVERDUE

    # Tested in the last few days: left to rest, whatever its due date says (a ledger written by
    # an older version can hold a topic due the day after a miss).
    resting = {tid for tid, t in topics.items()
               if parse_date(t.get("last")) and (today - parse_date(t["last"])).days < MIN_RETURN_DAYS}
    # In each of the last two rounds: left out of this one, due or not (the drill-down limit).
    history = (st.get("previous") or []) + log
    last_rounds = [set(s.get("topics") or []) for s in history[-DRILLDOWN_MAX_ROUNDS:]]
    drilled = set.intersection(*last_rounds) if len(last_rounds) == DRILLDOWN_MAX_ROUNDS else set()
    # A theme topic missed when it was seen in two rounds of the block waits for its date (the
    # pause, issue #79): no gap retest or revisit brings it back sooner, as with the learner's
    # stop (issue #75); in a one-off --domain round of the block too.
    paused = {tid for tid, t in topics.items()
              if block and (t.get("domain") or domain_of(tid)) == block["theme"]
              and (parse_date(t.get("due")) or today) > today and t.get("history")
              and not answered_well(t["history"][-1][1], t["history"][-1][3])
              and block_rounds_on(st, tid, block) >= DRILLDOWN_BLOCK_ROUNDS}
    recent = set()
    for s in log[-3:]:
        recent.update(s.get("topics") or [])
    recent_domains = [domain_of(t) for s in log[-10:] for t in (s.get("topics") or [])]

    def allowed(tid):
        if (tid in resting or tid in drilled or tid in paused) and not args.allow_repeat:
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
        # a topic the learner stopped is not revisited before its date comes (issue #75)
        seen = sorted((t.get("last") or "", t.get("mastery") if t.get("mastery") is not None else 0, tid)
                      for tid, t in topics.items() if dom(tid) == theme and allowed(tid)
                      and not (t.get("stopped") and (parse_date(t.get("due")) or today) > today))
        for _, _, tid in seen:
            if slot == "case" and level == 0 and tid == last_case:
                continue
            if fits(slot, tid, theme, level):
                return entry(slot, tid, theme, "revisit", "theme")
        # no untested topic of the theme left for the author to choose (the others resting,
        # drilled or paused, or taken by this round's items left to the author): a short question
        # goes elsewhere rather than to a topic the limits hold back; the case stays on the theme
        untested = [tid for tid, i in bpt.items() if i["domain"] == theme and tid not in topics and tid not in used_topics]
        tested_out = slot != "case" and any(i["domain"] == theme for i in bpt.values()) and len(untested) <= sum(
            1 for c in chosen if c.get("topic") is None and c.get("domain") == theme)
        if (eff.get(theme, 0) > 0 or theme in bp_weights(st)) and not tested_out:
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
    mix = block_mix(len(shorts), block["round"], backlog) if theme else None
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
    for c in chosen:
        notes = standing_positions(st, today, c.get("topic")) if c.get("topic") else []
        if notes:
            c["positions"] = {
                "notes": [position_for_round(p) for p in notes],
                "how": "The learner holds this position on that decision point (their words). Key no item "
                       "on the disputed point, and write the kit so the learner is not marked down for it "
                       "(references/standards.md, rule 12). Any other decision point of the topic is open."}
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
    for c in chosen:
        # the evidence depth the item earns if it is answered well (the first depth is not
        # written): the author prepares the notes for it; `answer` gives the examiner the figure
        d = evidence_depth(st, c.get("topic"), c.get("aspect_hint"), bool(c.get("retest_gap")))
        if d and d["level"] > 1:
            c["depth"] = dict(d, how="If this item is answered well its feedback goes to this depth: write "
                                     "the notes for it under 'Deeper' in the item's kit section and put its "
                                     "studies on the verification list (references/standards.md, rule 8).")
    order = cfg.get("item_order", "mcqs_first")
    by_slot = {k: [c for c in chosen if c["slot"] == k] for k in ("case", "mcq", "focused")}
    present = (by_slot["mcq"] + by_slot["focused"] + by_slot["case"] if order != "case_first"
               else by_slot["case"] + by_slot["mcq"] + by_slot["focused"])
    own_pace = pace(st)
    est = paced(round_minutes(len(by_slot["mcq"]), len(by_slot["focused"]), len(by_slot["case"]), fmt),
                own_pace["factor"])
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
        "evidence_ladder": bool(cfg.get("evidence_ladder", True)),
        "helpers": bool(cfg.get("helpers", True)), "prepare_ahead": bool(cfg.get("prepare_ahead", True)),
        "testing": bool(cfg.get("testing", False)),
        # listening (rule 8): whether the kits get a "## Listening" section, and whose shows
        "listening": listening_on(st),
        "podcast_sources": podcast_sources(st["profile"].get("podcast_sources"), "profile.podcast_sources"),
        # what the author pitches to (standards.md rule 4): the learner's own paragraphs, never
        # the labels derived from them
        "profile": dict({k: st["profile"].get(k) for k in ("journey", "aim", "subspecialty", "practice_setting")},
                        specialty=guideline_context(st)["specialty"]),
        "recent_cases_any_topic": used_cases[-15:],
        # the block: `line` is what the learner is told (theme and position); `mix` is how this
        # round's short questions were shared out (None in a one-off domain round)
        "block": dict(block, mix=mix, **({"backlog": {"overdue": overdue, "shares": dict(BACKLOG_SHARES)}}
                                          if backlog else {})) if block else None,
        "items": chosen,
        "pending_errata": st.get("pending_errata") or [],
        **({"estimate_rounds": own_pace["rounds"]} if own_pace["rounds"] else {}),   # the estimate is at the learner's pace
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
            **({"estimate_rounds": plan["estimate_rounds"]} if plan.get("estimate_rounds") else {}),
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


def agg_add_session(agg, s, sign=1):
    """Count session entry `s` in the all-time aggregates; `sign=-1` takes it out again (a round
    undone, undo_round). Sums of fractions are kept to six decimals, so that taking a session out
    and counting it again gives the same numbers."""
    def add(d, k, v):
        d[k] = round(d.get(k, 0) + sign * v, 6) if isinstance(v, float) or isinstance(d.get(k), float) \
            else d.get(k, 0) + sign * v

    def pair(p, i, v):
        p[i] = round(p[i] + sign * v, 6) if isinstance(v, float) or isinstance(p[i], float) else p[i] + sign * v
    add(agg, "sessions", 1)
    add(agg, "items", len(s.get("items") or []))
    add(agg, "minutes", int(s.get("minutes") or 0))
    add(agg, "reading_minutes", int(s.get("reading_minutes") or 0))
    add(agg, "mcqs", int(s.get("mcqs") or 0))
    add(agg, "mcq_correct", int(s.get("mcq_correct") or 0))
    agg.setdefault("focused", 0); agg.setdefault("focused_mastery_sum", 0.0)
    agg.setdefault("art_focused", {k: [0.0, 0] for k in ART_MAX})
    if isinstance(s.get("score"), (int, float)):
        add(agg, "score_sum", float(s["score"])); add(agg, "score_n", 1)
    for it in s.get("items") or []:
        c = it.get("coding") or {}
        if it.get("type") == "focused":
            add(agg, "focused", 1)
            if isinstance(it.get("mastery"), (int, float)):
                add(agg, "focused_mastery_sum", float(it["mastery"]))
        # ART from the full case only, so the profile stays comparable across periods;
        # focused questions (which score only the domains they test) are counted apart.
        art_bucket = agg["art_focused"] if it.get("type") == "focused" else agg["art"]
        for k, v in (c.get("art") or {}).items():
            if k in art_bucket and isinstance(v, (int, float)):
                pair(art_bucket[k], 0, float(v) / ART_MAX[k]); pair(art_bucket[k], 1, 1)
        idea = c.get("idea") or {}
        if idea and all(isinstance(idea.get(k), (int, float)) for k in IDEA_MAX):
            tot = sum(idea[k] for k in IDEA_MAX)
            pair(agg["idea"], 0, tot); pair(agg["idea"], 1, 1); pair(agg["idea"], 2, 1 if tot >= 6 else 0)
        for e in c.get("errors") or []:
            for key, v in [(k, e.get(k)) for k in ("category", "knowledge_type", "art_domain", "severity")] \
                    + [("bias", b) for b in e.get("bias") or []]:
                if v:
                    add(agg["errors"][key], v, 1)
                    if agg["errors"][key][v] == 0:
                        del agg["errors"][key][v]       # taken out again: no trace of it
        conf = (it.get("confidence") or "").lower()
        out = item_outcome(it)
        if conf in CONF_PROB and out is not None:
            pair(agg["calibration"][conf], 0, 1); pair(agg["calibration"][conf], 1, out)
            pair(agg["brier"], 0, (CONF_PROB[conf] - out) ** 2); pair(agg["brier"], 1, 1)
    d = s.get("drill")
    if isinstance(d, dict) and d.get("result") in DRILL_RESULTS:
        add(agg["drills"], d["result"], 1)
    for g in s.get("grade_changes") or []:
        if g.get("outcome") in agg["disputes"]:
            add(agg["disputes"], g["outcome"], 1)
        elif g.get("outcome") in LEARNER_SET_OUTCOMES:
            add(agg_overrides(agg), "scores", 1)
    if s.get("learner_closed_gaps"):
        add(agg_overrides(agg), "gaps", len(s["learner_closed_gaps"]))
    if s.get("stops"):
        add(agg_overrides(agg), "stops", len(s["stops"]))
        if agg_overrides(agg)["stops"] == 0:
            del agg_overrides(agg)["stops"]       # taken out again: no trace of it
    if (s.get("reflection") or {}).get("skipped"):
        add(agg, "reflection_skipped", 1)


def apply_round(state, rnd, today, theme=None, gap_ids=None, block=None):
    """Apply the graded round `rnd` to the ledger `state`, appending its session entry; `theme`
    is the theme of the block the round was recorded in, `block` that block as the session keeps
    it (theme, the round's number in it, length). The entry keeps an undo record (`undo`)
    of only what the round changed, so that undo_round can take it out again. `gap_ids`: the ids
    a round applied again gives the gaps it opens ({topic: id}), so that they keep the ids they
    had. The aggregates are the caller's (agg_add_session, once the entry is final).
    Returns (entry, summary, warnings, errata_ids, changes): `changes` are the gaps the learner
    closed (`learner_closed_gaps` in the round, after its grading), for the log."""
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
    self_gap_topics |= set(rnd.get("self_gap_topics") or [])     # a round recorded by 5.0 or earlier applied again

    resolved_by_topic = {}
    for r in rnd.get("resolved") or []:
        if isinstance(r, str):
            r = {"topic": r, "note": None}
        resolved_by_topic.setdefault(r.get("topic"), []).append(r.get("note"))
    # the learner's stops (issue #75): the topic goes to the longest interval and its gaps close
    stops = {}
    for s in rnd.get("stops") or []:
        s = {"topic": s} if isinstance(s, str) else dict(s or {})
        if not s.get("topic"):
            die("each stop needs 'topic'")
        stops.setdefault(s["topic"], s)

    summary = {}
    number_gaps(state)
    gap_index = {g.get("topic"): g for g in state["gaps"]}
    closures = closure_topics(state, rnd.get("learner_closed_gaps") or [], set(by_topic) | set(new_gaps_by_topic), gap_ids)
    touched = list(dict.fromkeys(list(by_topic) + list(new_gaps_by_topic) + [t for t in resolved_by_topic if t]
                                 + [t for _, t in closures if t] + list(stops)))
    before = touched_before(state, touched)
    inputs = {tid: [{k: (clip(g[k], CLIP_GAP) if k == "gap" else g[k]) for k in ("gap", "source", "auto", "domain", "label")
                     if g.get(k) is not None} for g in gs] for tid, gs in new_gaps_by_topic.items()}
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
        comfort = comfort_map.get(tid)
        try:
            comfort = None if comfort is None else max(1, min(5, int(round(float(comfort)))))
        except (TypeError, ValueError):
            comfort = None
        step, due, calibration, interval = schedule_topic(t.get("step"), mastery, comfort, misconception,
                                                          tid in self_gap_topics, intervals, rdate)
        limited = (not answered_well(mastery, calibration) and interval < DRILLDOWN_PAUSE_DAYS
                   and drilldown_over(state, tid, theme, block))
        if limited:      # the drill-down on this topic is used up: it comes back later, not next round
            interval, due = DRILLDOWN_PAUSE_DAYS, rdate + dt.timedelta(days=DRILLDOWN_PAUSE_DAYS)
        if tid in stops:  # the learner's stop: the longest interval, whatever the rules above said
            limited, step, interval = False, len(intervals) - 1, intervals[-1]
            due = rdate + dt.timedelta(days=interval)
        t.update({"last": iso(rdate), "attempts": int(t.get("attempts") or 0) + 1, "mastery": mastery,
                  "step": step, "due": iso(due), "comfort": comfort, "calibration": calibration})
        if tid in stops:
            t["stopped"] = iso(rdate)
        else:
            t.pop("stopped", None)      # tested again: the stop has done its work
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
        if tid in stops:
            summary[tid]["stopped"] = True

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
    for tid in [t for t in stops if t not in by_topic]:
        # a stop on a topic this round wrote a gap on without testing it (the stop was said on an
        # earlier round's item): the topic goes to the longest interval all the same
        t = ensure_topic(state, tid)
        t.update({"step": len(intervals) - 1, "due": iso(rdate + dt.timedelta(days=intervals[-1])),
                  "stopped": iso(rdate)})
        summary.setdefault(tid, {}).update({"due": t["due"], "stopped": True})

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
                entry["id"] = gap_id_for(state, tid, gap_ids)
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

    # the gaps the learner closes, after the round: a gap it opened can be closed too
    changes, closed = [], []
    for req, tid in closures:
        if tid is None:         # closed elsewhere since this round first closed it: kept as it was
            closed.append(dict({"id": req["gap"], "topic": req.get("topic")}, **({"stop": True} if req.get("stop") else {})))
            continue
        if req.get("again") and not any(req["gap"] in (g.get("id"), g.get("topic")) for g in state["gaps"]):
            continue            # its retest, answered well this time, closed it
        ch = learner_close_gap(state, req, req.get("date") or iso(rdate), sid=rnd.get("log_id") or rnd.get("id") or state["next_id"])
        closed.append(dict({"id": ch["gap"], "topic": ch["topic"]}, **({"stop": True} if ch.get("stop") else {})))
        if not req.get("again"):
            summary.setdefault(ch["topic"], {})["gap_closed_by_learner"] = True
            changes.append(ch)
    # a stop closes every gap still open on its topic, the ones this round opened included
    for tid, s in stops.items():
        for g in [g for g in state["gaps"] if g.get("topic") == tid]:
            ch = learner_close_gap(state, {"gap": g["id"], "stop": True}, s.get("date") or iso(rdate),
                                   sid=rnd.get("log_id") or rnd.get("id") or state["next_id"])
            closed.append({"id": ch["gap"], "topic": tid, "stop": True})
            summary.setdefault(tid, {})["gap_closed_by_learner"] = True
            if not s.get("again"):
                changes.append(ch)

    ratings = state["profile"].setdefault("domain_self_ratings", {})
    ratings_before = copy.deepcopy(ratings)
    for tid, s in summary.items():
        c = s.get("comfort")
        if c is None:
            continue
        d = state["topics"][tid]["domain"]
        prev = ratings.get(d)
        prev = prev.get("rating") if isinstance(prev, dict) else prev
        ratings[d] = c if prev is None else round((2 * float(prev) + c) / 3.0, 1)

    # session entry
    # time: measured from the round's stamps (`save` and `close` put `timing` there from the
    # work folder; a round.json may carry its own `stamps`). Without stamps there is only the
    # start and the end: no idle time can be cut from that, so a whole session of more than
    # LEGACY_MINUTES_CAP minutes is not recorded as a duration at all, and none is `timing`.
    timing = rnd.get("timing") if isinstance(rnd.get("timing"), dict) else None
    if timing is None and rnd.get("stamps"):
        measured = round_timing(rnd["stamps"])
        if measured:
            timing = measured["timing"]
            rnd.update({k: measured[k] for k in ("started_at", "ended_at", "minutes")})
    started, ended, minutes = rnd.get("started_at"), rnd.get("ended_at"), rnd.get("minutes")
    if minutes is None and started and ended:
        a, b = parse_stamp(str(started)), parse_stamp(str(ended))
        minutes = max(1, int(round((b - a).total_seconds() / 60.0))) if a and b and b >= a else None
        if minutes is not None and minutes > LEGACY_MINUTES_CAP:
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
    if timing is not None:
        entry["timing"] = {k: timing.get(k) for k in ("answering", "waiting", "reading", "idle_cut")}
    if entry["case"] is not None:
        entry["case"]["topic"] = next((it["topic"] for it in rnd["items"] if is_case(it)), None)

    # errata
    errata_ids = []
    n = max([id_num(e.get("id")) for e in state["errata"] + state["pending_errata"]] + [0]) + 1
    for e in rnd.get("errata") or []:
        if not e.get("corrects") or not e.get("correction"):
            die("each erratum needs 'corrects' (session id) and 'correction'")
        # an erratum is logged once: the same round applied again finds it logged already
        same = next((x for x in state["errata"] if x.get("logged_in") == sid and x.get("corrects") == e["corrects"]
                     and x.get("correction") == e["correction"]), None)
        if same:
            errata_ids.append(same["id"])
            continue
        e = dict(e, id="E%04d" % n, found=e.get("found") or iso(rdate), logged_in=sid)
        n += 1
        state["errata"].append(e); errata_ids.append(e["id"])
    wanted = rnd.get("pending_errata_logged") or []
    if wanted == "all":
        wanted = [e.get("id") for e in state["pending_errata"]]
    for eid in wanted:
        hit = next((e for e in state["pending_errata"] if e.get("id") == eid), None)
        if not hit and any(e.get("id") == eid and e.get("logged_in") == sid for e in state["errata"]):
            errata_ids.append(eid)
            continue
        if not hit:
            warnings.append("pending erratum %s not found" % eid)
            continue
        state["pending_errata"].remove(hit)
        state["errata"].append(dict(hit, logged_in=sid)); errata_ids.append(eid)
    errata_ids = list(dict.fromkeys(errata_ids))
    if errata_ids:
        entry["errata"] = errata_ids
    if closed:
        entry["learner_closed_gaps"] = closed
    if stops:
        entry["stops"] = [{k: s[k] for k in ("topic", "date", "item") if s.get(k) is not None} for s in stops.values()]
    entry["undo"] = undo_record(state, before, by_topic, inputs, resolved_by_topic, ratings_before)

    state["sessions"].append(entry)
    state["next_id"] = "S%04d" % (max(id_num(sid), id_num(state["next_id"]) - 1) + 1)
    state["updated"] = iso(today)
    return entry, summary, warnings, errata_ids, changes


# ---------------------------------------------------------------- a round in the ledger: record, amend, undo
#
# A round is recorded once (record_round). Every later change to it, whether `save` run again, the
# reflection (`close`), a dispute, a learner-set score or a gap the learner closes, is the same
# step: undo the round (undo_round) and apply it again with the amended input (apply_round_again),
# through the one apply_round. To undo it, each session entry keeps an undo record (`undo`) of only
# what the round changed, and only for the topics on which it is still the latest round: recording
# a later round on a topic takes the topic out of the earlier round's record (claim_topics). So a
# round applied again changes the schedule of the topics it was the last to touch; a topic tested
# since keeps the schedule the later round gave it, and only the record of the round changes.

def touched_before(state, tids):
    """What a round is about to change on topics `tids`: the topic without its history, its
    history, its open gap with the gap's place in the list, the number of its resolved gaps."""
    out = {}
    for tid in tids:
        t = state["topics"].get(tid)
        at = None
        for i, g in enumerate(state["gaps"]):
            if g.get("topic") == tid:
                at = [i, copy.deepcopy(g)]
        out[tid] = {"topic": None if t is None else copy.deepcopy({k: v for k, v in t.items() if k != "history"}),
                    "history": list((t or {}).get("history") or []), "gap": at,
                    "resolved": sum(1 for r in state["resolved"] if r.get("topic") == tid)}
    return out


def undo_record(state, before, tested, inputs, notes, ratings_before):
    """The undo record of a round just applied: per topic it touched, the values it changed
    (`was`; `new`: it created the topic), whether it added a history row (`row`, with the rows the
    cap cut, `cut`), the gap before it (`gap`: [place, gap], or null for none) when the round
    changed it, how many resolved entries it added (`resolved`), and the round's own input on the
    topic, so the round can be applied again from its session entry (`in`: its gaps; `notes`:
    its partly resolved notes). `ratings`: the comfort ratings before it, per domain it changed."""
    topics = {}
    for tid, b in before.items():
        t = state["topics"].get(tid)
        rec = {}
        if b["topic"] is None:
            if t is not None:
                rec["new"] = True
        elif t is not None:
            was = {k: v for k, v in b["topic"].items() if t.get(k) != v}
            if was:
                rec["was"] = was
            added = [k for k in t if k != "history" and k not in b["topic"]]
            if added:           # a key the round put on the topic (`stopped`): taken off again
                rec["added"] = added
            if tid in tested:
                rec["row"] = True
                cut = b["history"][:max(0, len(b["history"]) + 1 - len(t.get("history") or []))]
                if cut:
                    rec["cut"] = cut
        now = None
        for g in state["gaps"]:
            if g.get("topic") == tid:
                now = g
        if (b["gap"] or [None, None])[1] != now:
            rec["gap"] = b["gap"]
        n = sum(1 for r in state["resolved"] if r.get("topic") == tid) - b["resolved"]
        if n > 0:
            rec["resolved"] = n
        if inputs.get(tid):
            rec["in"] = inputs[tid]
        kept = [clip(x, 200) for x in notes.get(tid) or [] if x]
        if kept:
            rec["notes"] = kept
        topics[tid] = rec
    out = {"topics": topics}
    ratings = state["profile"].get("domain_self_ratings") or {}
    changed = {d: ratings_before.get(d) for d in ratings if ratings.get(d) != ratings_before.get(d)}
    if changed:
        out["ratings"] = changed
    return out


def gap_id_for(state, tid, gap_ids=None):
    """The id of a gap a round opens on `tid`: the one it had when the round was applied before,
    if it is free, else the next number."""
    want = (gap_ids or {}).get(tid)
    if want and all(g.get("id") != want for g in state["gaps"] + state["resolved"]):
        return want
    return "G%04d" % (number_gaps(state) + 1)


def closure_topics(state, reqs, tested, gap_ids=None):
    """The gaps a round's `learner_closed_gaps` name, each with its topic: [(req, topic)], `req`
    as {"gap": ref, "note", "date", "again"}. A gap counts if it is open or the round may open it
    (on a topic it tests or writes a gap on; by the id it had when the round was applied before).
    `again` marks a closure the round already had: if its gap is no longer there to close (it
    was closed elsewhere), the topic is None and the closure is kept as it was."""
    out = []
    for req in reqs:
        req = {"gap": req} if isinstance(req, str) else dict(req or {})
        ref = req.get("gap") or req.get("id") or req.get("topic")
        req["gap"] = ref
        g = next((x for x in state["gaps"] if ref and ref in (x.get("id"), x.get("topic"))), None)
        tid = g["topic"] if g else ref if ref in tested else \
            next((t for t, i in (gap_ids or {}).items() if i == ref and t in tested), None)
        if tid is None and not req.get("again"):
            die("no open gap %s to close (open: %s)"
                % (ref, ", ".join("%s %s" % (x.get("id"), x.get("topic")) for x in state["gaps"]) or "none"))
        out.append((req, tid))
    return out


def restore(state, snap):
    """Put back the whole tables 5.0 kept for a round still unreflected (`_snapshot`): read once,
    to close such a round."""
    state["topics"], state["gaps"], state["resolved"], state["agg"] = snap["topics"], snap["gaps"], snap["resolved"], snap["agg"]
    state["profile"]["domain_self_ratings"] = snap["ratings"]
    state["errata"], state["pending_errata"], state["next_id"] = snap["errata"], snap["pending_errata"], snap["next_id"]


def legacy_undo(st, sess, later):
    """An undo record for a round recorded by 5.0 or earlier, which keeps none: the topics on which it is
    still the latest round, put back to the step it started from (`steps_before`) and the history
    row before it. Its gaps, resolved gaps and comfort ratings are not known: they stay as they
    are (`partial`)."""
    date, topics = sess.get("date"), {}
    for tid in sess.get("topics") or []:
        t = st["topics"].get(tid)
        hist = (t or {}).get("history") or []
        if tid in later or not t or t.get("last") != date or not hist or hist[-1][0] != date:
            continue
        prev = hist[-2] if len(hist) > 1 else [None, None, None, None]
        topics[tid] = {"row": True, "was": {
            "step": (sess.get("steps_before") or {}).get(tid, t.get("step")),
            "attempts": max(0, int(t.get("attempts") or 1) - 1),
            "last": prev[0], "mastery": prev[1], "comfort": prev[2], "calibration": prev[3]}}
    return {"topics": topics, "partial": True}


def later_owned(st, pos):
    """The topics and comfort-rating domains a round after position `pos` owns (it changed them
    last): a round applied again leaves them as they are."""
    tids, doms = set(), set()
    for s in st["sessions"][pos + 1:]:
        u = s.get("undo")
        if u is not None:
            tids |= set(u.get("topics") or {}); doms |= set(u.get("ratings") or {})
            continue
        tids |= set(s.get("topics") or [])         # a round recorded by 5.0 or earlier: what it is known to touch
        tids |= {g.get("topic") for g in st["gaps"] if g.get("date") == s.get("date")}
        tids |= {r.get("topic") for r in st["resolved"] if r.get("resolved") == s.get("date")}
        doms |= {(st["topics"].get(t) or {}).get("domain") or domain_of(t) for t in s.get("self_comfort") or {}}
    return tids, doms


def claim_topics(st, pos):
    """The round at `pos` is now the latest on the topics and ratings its undo record holds:
    earlier rounds give them up."""
    u = st["sessions"][pos].get("undo") or {}
    tids, doms = set(u.get("topics") or {}), set(u.get("ratings") or {})
    for s in st["sessions"][:pos]:
        v = s.get("undo")
        if not v:
            continue
        for tid in tids & set(v.get("topics") or {}):
            del v["topics"][tid]
        for d in doms & set(v.get("ratings") or {}):
            del v["ratings"][d]
        if "ratings" in v and not v["ratings"]:
            del v["ratings"]


def owner_of(st, tid):
    """The round that is the latest on topic `tid` and can apply again on it, or None."""
    return next((s for s in reversed(st["sessions"]) if tid in ((s.get("undo") or {}).get("topics") or {})), None)


def undo_round(st, pos, u=None):
    """Take the round at position `pos` out of the ledger: its session entry, what it counts in
    the aggregates, and what its undo record `u` (default: the entry's) says it changed. A round
    saved by 5.0 and still unreflected keeps the whole tables it started from (`_snapshot`)
    instead: they are put back."""
    sess = st["sessions"].pop(pos)
    if st.get("unreflected") == sess.get("id"):
        st["unreflected"] = None
    if sess.get("_snapshot"):
        restore(st, copy.deepcopy(sess["_snapshot"]))
        return sess
    agg_add_session(st["agg"], sess, -1)
    u = u if u is not None else sess.get("undo") or {}
    recs = u.get("topics") or {}
    for tid, rec in recs.items():
        n = int(rec.get("resolved") or 0)
        for i in range(len(st["resolved"]) - 1, -1, -1):
            if n <= 0:
                break
            if st["resolved"][i].get("topic") == tid:
                del st["resolved"][i]
                n -= 1
    moved = {tid: rec["gap"] for tid, rec in recs.items() if "gap" in rec}
    if moved:
        st["gaps"] = [g for g in st["gaps"] if g.get("topic") not in moved]
        for at, g in sorted((x for x in moved.values() if x), key=lambda x: x[0]):
            st["gaps"].insert(min(int(at), len(st["gaps"])), copy.deepcopy(g))
    for tid, rec in recs.items():
        t = st["topics"].get(tid)
        if t is None:
            continue
        if rec.get("new"):
            del st["topics"][tid]
            continue
        t.update(copy.deepcopy(rec.get("was") or {}))
        for k in rec.get("added") or []:
            t.pop(k, None)
        if rec.get("row"):
            t["history"] = list(rec.get("cut") or []) + (t.get("history") or [])[:-1]
    ratings = st["profile"].setdefault("domain_self_ratings", {})
    for d, v in (u.get("ratings") or {}).items():
        if v is None:
            ratings.pop(d, None)
        else:
            ratings[d] = v
    return sess


def round_from_entry(st, sess):
    """The round input that applied again gives session entry `sess` back: the entry itself (its
    items, scores, comfort, reflection, ...) with the gaps and notes its undo record keeps, and
    the gaps the learner closed in it. For a 5.0 round still unreflected: the round it kept."""
    if sess.get("_round") is not None:
        return copy.deepcopy(sess["_round"])
    recs = (sess.get("undo") or {}).get("topics") or {}
    gaps, self_gaps, notes = [], [], []
    for tid, rec in recs.items():
        for g in rec.get("in") or []:
            (self_gaps if g.get("source") == "self" else gaps).append(dict(g, topic=tid))
        notes += [{"topic": tid, "note": n} for n in rec.get("notes") or []]
    items = []
    for it in sess.get("items") or []:
        it = copy.deepcopy(it)
        if it.get("stem") and not it.get("stem_summary"):
            it["stem_summary"] = it.pop("stem")
        items.append(it)
    rnd = {"log_id": sess["id"], "date": sess.get("date"), "items": items, "gaps": gaps, "resolved": notes,
           "case_format": sess.get("format"), "selection_reasons": copy.deepcopy(sess.get("why") or {}),
           "grade_changes": copy.deepcopy(sess.get("grade_changes") or []), "drill": copy.deepcopy(sess.get("drill"))}
    for k in ("started_at", "ended_at", "minutes", "reading_minutes", "title", "summary", "tags", "key_learning",
              "case", "timing"):
        if sess.get(k) is not None:
            rnd[k] = copy.deepcopy(sess[k])
    if sess.get("reflection") is not None:
        refl = dict(copy.deepcopy(sess["reflection"]), performance=sess.get("self_performance"),
                    topic_comfort=copy.deepcopy(sess.get("self_comfort") or {}), self_gaps=self_gaps)
        if sess.get("reading_minutes") is not None:
            refl["reading_minutes"] = sess["reading_minutes"]
        rnd["reflection"] = refl
    if sess.get("undo") is None:        # recorded by 5.0 or earlier: its self-reported gaps are known only from the gaps
        rnd["self_gap_topics"] = sorted(g["topic"] for g in st["gaps"] if g.get("topic") in (sess.get("topics") or [])
                                        and "self" in (g.get("source") or []) and g.get("date") == sess.get("date"))
    # the learner's stops are applied again, and close their gaps again with them; a stop made
    # outright (no round of the period was the latest on its topic) stays as it was
    stops = [dict(s, again=True) for s in sess.get("stops") or [] if not s.get("outright")]
    if stops:
        rnd["stops"] = stops
    closed = []
    for c in sess.get("learner_closed_gaps") or []:
        if c.get("stop") and c.get("topic") in {s["topic"] for s in stops}:
            continue
        r = next((x for x in reversed(st["resolved"]) if x.get("closed_by") == "learner" and x.get("id") == c.get("id")), {})
        closed.append(dict({"gap": c.get("id"), "topic": c.get("topic"), "note": r.get("learner_note"),
                            "date": r.get("resolved"), "again": True}, **({"stop": True} if c.get("stop") else {})))
    if closed:
        rnd["learner_closed_gaps"] = closed
    return rnd


def apply_round_again(st, sess, rnd, today):
    """Undo round `sess` and apply `rnd`, the same round with amended input, in its place. On the
    topics and comfort ratings a later round owns, the later round's values stay (decision 2 of
    issue #74: only the latest round on a topic is applied again). Returns what apply_round does."""
    pos = st["sessions"].index(sess)
    later_t, later_d = later_owned(st, pos)
    u = sess.get("undo")
    legacy = u is None and not sess.get("_snapshot")
    if legacy:
        u = legacy_undo(st, sess, later_t)
    partial = bool((u or {}).get("partial"))
    owned = set((u or {}).get("topics") or {})
    # the topics the amended round may touch that it must leave as they are
    refl = rnd.get("reflection") or {}
    cand = {it.get("topic") for it in rnd.get("items") or []} | {g.get("topic") for g in rnd.get("gaps") or []} \
        | {g.get("topic") for g in refl.get("self_gaps") or []} \
        | {(r if isinstance(r, str) else r.get("topic")) for r in rnd.get("resolved") or []}
    blocked = {t for t in cand if t and (t in later_t or (partial and t not in owned))}
    gaps_kept = {t for t in cand if t} if partial else set()    # a round recorded by 5.0 or earlier: its gaps are not known
    number_gaps(st)
    frozen = {}
    for tid in blocked | gaps_kept:
        gap = None
        for i, g in enumerate(st["gaps"]):
            if g.get("topic") == tid:
                gap = [i, copy.deepcopy(g)]
        frozen[tid] = (copy.deepcopy(st["topics"].get(tid)), gap)
    ratings_now = copy.deepcopy(st["profile"].get("domain_self_ratings") or {})
    # the gaps it opened keep their ids when it opens them again
    gap_ids = {g["topic"]: g["id"] for g in st["gaps"] if g.get("topic") in owned and g.get("id")}
    for r in st["resolved"]:
        if r.get("topic") in owned and r.get("id"):
            gap_ids.setdefault(r["topic"], r["id"])
    old = undo_round(st, pos, u)
    tail, st["sessions"] = st["sessions"][pos:], st["sessions"][:pos]
    try:
        entry, summary, warnings, errata_ids, changes = apply_round(st, rnd, today, (old.get("block") or {}).get("theme"),
                                                                    gap_ids, old.get("block"))
    finally:
        st["sessions"] += tail
    for k in ("block", "url"):
        if old.get(k):
            entry[k] = old[k]
    outright = [s for s in old.get("stops") or [] if s.get("outright")]
    if outright:
        entry["stops"] = list(entry.get("stops") or []) + outright
    errata = list(dict.fromkeys(list(old.get("errata") or []) + list(entry.get("errata") or [])))
    if errata:
        entry["errata"] = errata
    recs = entry["undo"]["topics"]
    for tid in [t for t in recs if t in blocked or t in gaps_kept]:
        n = int(recs[tid].get("resolved") or 0)
        for i in range(len(st["resolved"]) - 1, -1, -1):
            if n <= 0:
                break
            if st["resolved"][i].get("topic") == tid:
                del st["resolved"][i]
                n -= 1
        t0, g0 = frozen[tid]
        st["gaps"] = [g for g in st["gaps"] if g.get("topic") != tid]
        if g0:
            st["gaps"].insert(min(g0[0], len(st["gaps"])), g0[1])
        if tid not in blocked:
            for k in ("gap", "resolved", "in", "notes"):
                recs[tid].pop(k, None)
            continue
        if t0 is None:
            st["topics"].pop(tid, None)
        else:
            st["topics"][tid] = t0
        del recs[tid]
        summary.setdefault(tid, {})["tested_since"] = True
    ratings = st["profile"].setdefault("domain_self_ratings", {})
    for d in set(ratings) | set(ratings_now):
        if partial or d in later_d:
            if d in ratings_now:
                ratings[d] = ratings_now[d]
            else:
                ratings.pop(d, None)
            (entry["undo"].get("ratings") or {}).pop(d, None)
    if not entry["undo"].get("ratings"):
        entry["undo"].pop("ratings", None)
    if partial:
        entry["undo"]["partial"] = True
    if rnd.get("reflection") is None:       # still waiting for its reflection
        st["unreflected"] = entry["id"]
    agg_add_session(st["agg"], entry)
    claim_topics(st, pos)
    return entry, summary, warnings, errata_ids, changes


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
    if isinstance(sess.get("timing"), dict):
        out["timing"] = sess["timing"]
    if sess.get("case"):
        out["case"] = {k: sess["case"].get(k) for k in ("topic", "presentation", "diagnosis") if sess["case"].get(k)}
    if sess.get("url"):
        out["url"] = sess["url"]
    if sess.get("block"):
        out["block"] = sess["block"]
    if sess.get("learner_closed_gaps"):
        out["learner_closed_gaps"] = sess["learner_closed_gaps"]
    if sess.get("stops"):
        out["stops"] = sess["stops"]
    return out


def record_round(st, rnd, today, again=None):
    """Apply the graded round `rnd` to ledger `st` (changed in place; `rnd` may be changed too).
    `again`: the session entry of this same round, recorded before (`save` run again): it is
    undone and `rnd` applied in its place, in the block it was counted in. Returns what record
    and save report about it."""
    if not rnd.get("date"):     # the round is dated when it is recorded; reflecting later keeps that date
        rnd["date"] = iso(today)
    # finalize a still-unreflected earlier session: it stays recorded with the reflection skipped
    if st.get("unreflected") and not again:
        for s in st["sessions"]:
            if s.get("id") == st["unreflected"]:
                s.pop("_snapshot", None); s.pop("_round", None)
                if s.get("reflection") is None:
                    agg_add_session(st["agg"], s, -1)
                    s["reflection"] = {"skipped": True}
                    agg_add_session(st["agg"], s)
        st["unreflected"] = None
    for k in ("helpers", "prepare_ahead"):       # speed settings (4.3): on unless the learner turns them off
        st["config"].setdefault(k, DEFAULT_CONFIG[k])
    if again:
        entry, summary, warnings, errata_ids, changes = apply_round_again(st, again, rnd, today)
    else:
        # The round counts in its block here, once: applying it again keeps the block it was counted in.
        in_block = advance_block(st, parse_date(rnd.get("date")) or today)
        entry, summary, warnings, errata_ids, changes = apply_round(st, rnd, today, (in_block or {}).get("theme"),
                                                                    block=in_block)
        if in_block:
            entry["block"] = in_block
        agg_add_session(st["agg"], entry)
        claim_topics(st, len(st["sessions"]) - 1)
    if rnd.get("reflection") is None:
        st["unreflected"] = entry["id"]
    compact(st)
    bump_gen(st)
    out = {"gen": st["gen"], "session_id": entry["id"],
           "next_id": st["next_id"], "score": entry["score"], "topics": summary,
           "errata_ids": errata_ids,
           "errata_to_log": [e for e in st["errata"] if e.get("id") in errata_ids],
           "open_gaps": len(st["gaps"]), "reflection_pending": rnd.get("reflection") is None,
           "warnings": warnings}
    if changes:
        out["learner_changes"] = changes
    return out


def report(out, size, result):
    """The printed result of a command that wrote the ledger: ok, out and bytes first."""
    return dict({"ok": True, "out": out, "bytes": size}, **result)


def reflect_round(st, refl, today, session=None, measured=None, base=None):
    """Apply the reflection `refl` to the unreflected session of ledger `st` (or to `session`):
    the round is undone and applied again with the reflection (apply_round_again), changing `st`
    in place. `base`: the round as it stood before its reflection (round_from_entry), when `close`
    runs again on a round it closed. Returns what reflect and close report about it. `measured`:
    the round's time now that the reflection has arrived (round_timing), replacing what `save` had."""
    sid = session or st.get("unreflected")
    sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
    if not sess or (base is None and sid != st.get("unreflected")):
        die("no unreflected session to update (last: %s)" % (st["sessions"][-1].get("id") if st["sessions"] else None))
    rnd = copy.deepcopy(base) if base is not None else round_from_entry(st, sess)
    rnd["reflection"] = refl
    if measured:
        rnd.update(measured)
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
    said = []
    for req in refl.get("learner_stops") or []:
        stop, gc, ch = learner_stop(rnd["items"], req, sid, rdate)
        rnd["grade_changes"] = list(rnd.get("grade_changes") or []) + [gc]
        rnd["stops"] = list(rnd.get("stops") or []) + [stop]
        said.append((req, ch))
    rnd["learner_closed_gaps"] = list(rnd.get("learner_closed_gaps") or []) + [
        dict({"gap": req} if isinstance(req, str) else req, date=rdate) for req in refl.get("learner_closed_gaps") or []]
    entry, summary, warnings, errata_ids, closed = apply_round_again(st, sess, rnd, today)
    # the position notes said with the stops: `close` run again puts this round's in afresh
    if "positions" in st:
        st["positions"] = [p for p in st["positions"] if not (p.get("session") == sid and p.get("from") == "reflection")]
    changes += stop_changes(st, said, sid, rdate, "reflection") + closed
    lapse_positions(st, today)
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


def learner_stop(items, req, sid, date):
    """"I know this, stop bringing it back", said of one item of round `sid` (issue #75): the
    learner's score on it (STOP_SCORE when they name none), a learner-set score marked `stop`.
    Returns (stop, grade_change, change): the stop for the round's input (`stops`: apply_round
    closes the topic's gaps and schedules it at the longest interval), the `grade_changes` entry
    and the change for the log."""
    if not isinstance(req, dict) or not req.get("topic"):
        die("a stop needs 'topic' (and 'type' when the round has two items on it); 'score' and "
            "'position' are optional")
    req = dict(req, score=STOP_SCORE if req.get("score") is None else req["score"])
    position_input(req)         # a malformed note stops here, before anything is applied
    ch = learner_score(find_item(items, req, sid), req, date)
    gc = dict(ch.pop("grade_change"), stop=True)
    ch["kind"] = "stop"
    return {"topic": req["topic"], "date": date, "item": ch["item"]}, gc, ch


def stop_changes(st, said, sid, date, source):
    """The changes for the log of the stops `said` ([(request, change)]) once they are applied,
    with the position note each may carry, which goes into the ledger here."""
    out = []
    for req, ch in said:
        note = position_input(req)
        if note:
            p = set_position(st, ch["topic"], note[0], note[1], date, sid, source)
            ch["position"] = {k: p[k] for k in ("id", "point", "text")}
        out.append(ch)
    return out


# ---------------------------------------------------------------- position notes (issue #75)
#
# What the learner holds on one decision point of a topic, in their own words, said with a stop.
# Every later round on the topic carries it to the author (no item is keyed on that point) and to
# the examiner (the learner is not marked down on it). It ends when the learner drops it, when a
# progress review drops it, or when no review has confirmed it for POSITION_LAPSE_DAYS.

def position_input(req):
    """(point, text) of the position note a stop request carries, or None."""
    p = (req or {}).get("position")
    if not p:
        return None
    p = {"text": p} if isinstance(p, str) else p
    point = clip((p.get("point") or "").strip(), 160) if isinstance(p, dict) else ""
    text = (p.get("text") or "").strip() if isinstance(p, dict) else ""
    if not point or not text:
        die("a position note needs 'point' (the one decision point, in a few words) and 'text' "
            "(what the learner holds, in their own words)")
    return point, clip(text, 600)


def set_position(st, tid, point, text, date, sid, source):
    """Keep the learner's position note on topic `tid`; the same note said again is kept once."""
    pos = st.setdefault("positions", [])
    same = next((p for p in pos if p.get("topic") == tid and p.get("point") == point and p.get("text") == text), None)
    if same:
        return same
    p = {"id": "P%04d" % (max([id_num(x.get("id")) for x in pos] + [0]) + 1), "topic": tid, "point": point,
         "text": text, "set": date, "confirmed": date, "session": sid, "from": source}
    pos.append(p)
    return p


def position_lapses(p):
    d = parse_date(p.get("confirmed") or p.get("set"))
    return d + dt.timedelta(days=POSITION_LAPSE_DAYS) if d else None


def standing_positions(st, today, tid=None):
    """The position notes in force on `today` (on topic `tid`), oldest first."""
    return [p for p in st.get("positions") or [] if (tid is None or p.get("topic") == tid)
            and (position_lapses(p) is None or position_lapses(p) >= today)]


def lapse_positions(st, today):
    """Take the notes no review has confirmed for POSITION_LAPSE_DAYS out of the ledger."""
    if "positions" not in st:
        return []
    keep = standing_positions(st, today)
    gone = [p for p in st["positions"] if p not in keep]
    st["positions"] = keep
    return gone


def position_for_round(p):
    """A note as the author and the examiner get it."""
    out = {k: p[k] for k in ("id", "point", "text", "set") if p.get(k)}
    if p.get("reopened"):
        out["reopened"] = p["reopened"]
    return out


def learner_close_gap(st, req, date, sess=None, sid=None):
    """Close an open gap because the learner asked: it moves to `resolved` marked
    `closed_by: learner`, and no retest follows (the topic keeps the due date its score gave
    it). `req` names the gap by id or by topic. With `sess`, the closure is listed in that
    session entry (the caller counts it in the aggregates). Returns the change for the log."""
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
    stop = bool(req.get("stop"))
    if stop:                # closed by the learner's stop on the topic, not by a request of its own
        st["resolved"][-1]["stop"] = True
    if sess is not None:
        sess.setdefault("learner_closed_gaps", []).append(dict({"id": g.get("id"), "topic": g.get("topic")},
                                                               **({"stop": True} if stop else {})))
    ch = {"kind": "gap", "gap": g.get("id"), "topic": g.get("topic"), "text": clip(g.get("gap"), 200),
          "closed_by": "learner", "date": date, "note": note}
    if stop:
        ch["stop"] = True
    return ch


def learner_changes_md(changes, heading):
    """The learner's own changes as they are written into the session document."""
    lines = []
    for c in changes:
        if c["kind"] == "score":
            line = ("- %s (%s): the examiner's score %s, the learner's score %s. Recorded and scheduled with "
                    "the learner's score, at the learner's request."
                    % (c["item"], c["topic"], c["examiner"], c["learner"]))
        elif c["kind"] == "stop":
            line = ("- %s (%s): stopped by the learner (\"I know this, stop bringing it back\"). The examiner's "
                    "score %s, the learner's score %s; the topic's open gaps closed and the topic scheduled at "
                    "the longest interval." % (c["item"], c["topic"], c["examiner"], c["learner"]))
            if c.get("position"):
                line += " Position note on %s, in the learner's words: \"%s\"" % (
                    c["position"]["point"], c["position"]["text"])
        elif c.get("stop"):
            line = ("- Gap %s (%s) closed with the learner's stop, not by a retest: %s"
                    % (c["gap"], c["topic"], c.get("text") or ""))
        else:
            line = ("- Gap %s (%s) closed by the learner, not by a retest: %s"
                    % (c["gap"], c["topic"], c.get("text") or ""))
        lines.append(line + (" Learner's note: %s" % c["note"] if c.get("note") else ""))
    return "%s\n\n%s\n" % (heading, "\n".join(lines))


def amend_round(st, sid, scores, closes, date, today, stops=()):
    """After the close: the learner sets scores of round `sid` themselves (`scores`, entries of
    `learner_scores`), closes gaps (`closes`, entries of `learner_closed_gaps`) and stops topics
    (`stops`, entries of `learner_stops`), dated `date`. Each is an amended input of a round,
    applied again (apply_round_again), so a score set or a stop said now is scheduled exactly as
    the same said in the reflection. A gap closed, or a stop's schedule and gaps, is an amendment
    of the round that is the latest on its topic; where no round of this period is, the gap is
    closed (the topic stopped) outright and listed in round `sid`. Returns (changes, topics,
    warnings)."""
    sess = next((x for x in st["sessions"] if x.get("id") == sid), None)
    if not sess and (scores or stops):
        die("round %s is %s: its scores can no longer be changed (a note can still be added with addendum)"
            % (sid, "from before the last progress review" if has_session(st, sid) else "not in the ledger"))
    changes, topics, warnings, again = [], {}, [], {}
    if scores or stops:
        rnd = again[sid] = round_from_entry(st, sess)
        for req in scores:
            ch = learner_score(find_item(rnd["items"], req, sid), req, date)
            rnd["grade_changes"] = list(rnd.get("grade_changes") or []) + [ch.pop("grade_change")]
            changes.append(ch)
    said, outright_stops = [], []
    for req in stops:
        stop, gc, ch = learner_stop(again[sid]["items"], req, sid, date)
        again[sid]["grade_changes"] = list(again[sid].get("grade_changes") or []) + [gc]
        owner = owner_of(st, stop["topic"])
        if owner is None:
            outright_stops.append(stop)
        else:
            o = again.get(owner["id"]) or again.setdefault(owner["id"], round_from_entry(st, owner))
            o["stops"] = [x for x in o.get("stops") or [] if x.get("topic") != stop["topic"]] + [stop]
        said.append((req, ch))
    outright = []
    for req in closes:
        req = {"gap": req} if isinstance(req, str) else dict(req or {})
        ref = req.get("gap") or req.get("id") or req.get("topic")
        g = next((x for x in st["gaps"] if ref and ref in (x.get("id"), x.get("topic"))), None)
        if not g:
            die("no open gap %s to close (open: %s)"
                % (ref, ", ".join("%s %s" % (x.get("id"), x.get("topic")) for x in st["gaps"]) or "none"))
        owner = owner_of(st, g["topic"])
        if owner is None:
            outright.append(req)
            continue
        rnd = again.get(owner["id"]) or again.setdefault(owner["id"], round_from_entry(st, owner))
        rnd["learner_closed_gaps"] = list(rnd.get("learner_closed_gaps") or []) + [dict(req, gap=g["id"], date=date)]
    gap_changes = []
    for oid in [s["id"] for s in st["sessions"] if s["id"] in again]:
        entry, summary, _, _, closed = apply_round_again(st, next(s for s in st["sessions"] if s["id"] == oid),
                                                         again[oid], today)
        gap_changes += closed
        for ch in closed:
            topics.setdefault(ch["topic"], {})["gap_closed_by_learner"] = True
        if oid != sid:
            continue
        for req in scores:
            tid = req["topic"]
            if tid in entry["undo"]["topics"]:
                topics.setdefault(tid, {}).update({k: summary[tid][k] for k in
                                                   ("mastery", "step", "due", "interval_days", "calibration")})
            else:
                warnings.append("%s has been tested again since %s: the score is recorded, its schedule is "
                                "left as the later round set it" % (tid, sid))
    sess = next((x for x in st["sessions"] if x.get("id") == sid), None)
    if (outright or outright_stops) and sess is not None:
        agg_add_session(st["agg"], sess, -1)        # counted again below, with what it now lists
    for req in outright:
        ch = learner_close_gap(st, req, date, sess, sid)
        if sess is None:
            agg_overrides(st["agg"])["gaps"] += 1      # a round of an earlier period: counted all the same
        topics.setdefault(ch["topic"], {})["gap_closed_by_learner"] = True
        gap_changes.append(ch)
    intervals = [int(x) for x in st["config"].get("intervals_days") or DEFAULT_CONFIG["intervals_days"]]
    for stop in outright_stops:     # no round of this period is the latest on the topic: stopped as it stands
        t = ensure_topic(st, stop["topic"])
        t.update({"step": len(intervals) - 1, "stopped": date,
                  "due": iso(parse_date(date) + dt.timedelta(days=intervals[-1]))})
        for g in [g for g in st["gaps"] if g.get("topic") == stop["topic"]]:
            gap_changes.append(learner_close_gap(st, {"gap": g["id"], "stop": True}, date, sess, sid))
        sess.setdefault("stops", []).append(dict(stop, outright=True))
    if (outright or outright_stops) and sess is not None:
        agg_add_session(st["agg"], sess)
    for req, ch in said:
        t = st["topics"].get(ch["topic"]) or {}
        topics.setdefault(ch["topic"], {}).update({"stopped": True, "step": t.get("step"), "due": t.get("due")})
    changes += stop_changes(st, said, sid, date, "override") + gap_changes
    lapse_positions(st, today)
    return changes, topics, warnings


def cmd_override(args):
    """After the close: the learner sets a score of a closed round themselves (--scores), closes
    a gap by request (--close-gaps) or stops a topic, "I know this, stop bringing it back"
    (--stops, with an optional position note). The ledger, the session document (its
    `learner_changes` and a line in the addendum) and the page file go into the publish set.
    Before the close they belong in the reflection JSON (`learner_scores`,
    `learner_closed_gaps`, `learner_stops`), which `close` handles the same way."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    scores = (load_json_arg(args.scores) if args.scores else None) or []
    closes = (load_json_arg(args.close_gaps) if args.close_gaps else None) or []
    stops = (load_json_arg(args.stops) if args.stops else None) or []
    scores, closes, stops = ([x] if isinstance(x, (dict, str)) else list(x) for x in (scores, closes, stops))
    if not scores and not closes and not stops:
        die("override needs --scores '[{\"topic\": …, \"score\": N}]', --close-gaps '[{\"gap\": \"G0007\"}]' "
            "or --stops '[{\"topic\": …}]'")
    if st.get("unreflected"):
        die("round %s is not closed yet: put `learner_scores`, `learner_closed_gaps` and `learner_stops` in its "
            "reflection JSON and run close (`{\"skipped\": true}` with them when there is no reflection)"
            % st["unreflected"])
    sid = job_session(work, info, st, args.session)
    if (scores or stops) and not any(x.get("id") == sid for x in st["sessions"]):
        die("round %s is %s: its scores can no longer be changed (a note can still be added with addendum)"
            % (sid, "from before the last progress review" if has_session(st, sid) else "not in the ledger"))
    doc_path = store_file(work, info, session_path(sid))
    if not doc_path:
        die("the session file of %s was not found: read %s from the store into the store copy "
            "(%s) first" % (sid, session_path(sid), info.get("store")))
    doc = load_json(doc_path)
    changes, topics, warnings = amend_round(st, sid, scores, closes, iso(today), today, stops)
    sess = next((x for x in st["sessions"] if x.get("id") == sid), None)
    if scores or stops:
        doc["score"] = sess["score"]
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
    if scores or stops:
        out["score"] = sess["score"]
    # the prepared round was planned with the gap open and the old due date
    publish_ledger(work, info, st, out, session=doc, empty_prepared=True)
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
            "gaps_closed": sum(len(s.get("learner_closed_gaps") or []) for s in log),
            # "I know this, stop bringing it back": counted apart (its score is among `scores`)
            "stops": sum(len(s.get("stops") or []) for s in log)},
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
        "learner_overrides": {"scores": agg_overrides(agg)["scores"], "gaps_closed": agg_overrides(agg)["gaps"],
                              "stops": agg_overrides(agg).get("stops", 0)},
        "reflection_skipped": agg["reflection_skipped"],
    }


def timing_stats(st):
    """Measured time over the last timed rounds, for the review: medians per round, the pace
    against the defaults and the hint. Sessions without stamps (older versions) are left out."""
    rounds = timed_rounds(st)
    p = pace(st)
    hint = time_hint(st)
    med = lambda k: median([float((s["timing"].get(k)) or 0) for s in rounds])
    return {"timed_rounds": len(rounds), "session_ids": [s.get("id") for s in rounds],
            "median_minutes": p["median_minutes"], "budget_minutes": (st.get("config") or {}).get("session_minutes"),
            "median_answering": med("answering"), "median_waiting": med("waiting"),
            "median_reading": med("reading"), "idle_cut_total": round(sum(float(s["timing"].get("idle_cut") or 0)
                                                                         for s in rounds), 1),
            "pace": p["own"], "estimate_factor": p["factor"], "hint": hint["text"] if hint else None}


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
        "timing": timing_stats(st),
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
        "journey": prof.get("journey"), "aim": prof.get("aim"), "goals": prof.get("goals"),
        "analysis": {"period": coding_analytics(log),
                     "previous_period": coding_analytics(st["previous"]) if st["previous"] else None,
                     "all_time": agg_analytics(st["agg"])},
        "period_session_ids": sorted(period_ids, key=id_num),
        "previous_reviews": [{"date": r.get("date"), "doc": r.get("doc"), "headline": r.get("headline"),
                              "change_plan": r.get("change_plan")} for r in st["reviews"]],
        "active_drills": st["drills"], "pending_errata": st["pending_errata"], "errata": st["errata"],
        # the learner's position notes in force, each listed at the review to keep or drop
        "positions": [dict(p, label=(st["topics"].get(p.get("topic")) or {}).get("label"),
                           lapses=iso(position_lapses(p))) for p in standing_positions(st, today)],
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
        was = copy.deepcopy(prof)
        deep_merge(prof, rv["profile_changes"])
        set_paragraphs(prof, was, rv["profile_changes"])
        check_paragraphs(prof)
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
    pos = rv.get("positions") or {}
    if pos:
        held = {p.get("id"): p for p in st.get("positions") or []}
        for pid in list(pos.get("keep") or []) + list(pos.get("drop") or []):
            if pid not in held:
                die("no position note %s (notes: %s)" % (pid, ", ".join(held) or "none"))
        for pid in pos.get("keep") or []:
            held[pid]["confirmed"] = iso(today)
        st["positions"] = [p for p in st["positions"] if p.get("id") not in set(pos.get("drop") or [])]
        entry["positions"] = {"kept": list(pos.get("keep") or []), "dropped": list(pos.get("drop") or [])}
    lapsed = lapse_positions(st, today)
    if lapsed:
        entry.setdefault("positions", {})["lapsed"] = [p["id"] for p in lapsed]
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
           "next_review_due": iso(next_due), "drills": st["drills"], "positions": entry.get("positions"),
           "pending_errata": [e["id"] for e in st["pending_errata"]], "warnings": warnings}
    path = publish_ledger(work, info, st, out, empty_prepared=True)
    out.update({"out": path, "bytes": os.path.getsize(path)})
    print(json.dumps(published(work, info, out), indent=1, ensure_ascii=False))


def cmd_position(args):
    """The learner's position notes (issue #75). Alone: the notes in force, writing nothing.
    `--drop ID`: the learner takes a note back (at any time). `--reopened ID`: the checker found
    that guidance on that point changed since the note was written and the examiner raised it
    once more; it is not raised again. The ledger and the page file go into the publish set."""
    today = today_from(args)
    work, info = job(args)
    st, _ = current_ledger(work, info)
    held = {p.get("id"): p for p in standing_positions(st, today)}

    def listed():
        return [dict(position_for_round(p), topic=p.get("topic"), lapses=iso(position_lapses(p)))
                for p in standing_positions(st, today)]
    if not args.drop and not args.reopened:
        print(json.dumps({"ok": True, "positions": listed()}, indent=1, ensure_ascii=False))
        return
    for pid in [x for x in (args.drop, args.reopened) if x]:
        if pid not in held:
            die("no position note %s in force (notes: %s)" % (pid, ", ".join(held) or "none"))
    if args.reopened:
        if held[args.reopened].get("reopened"):
            die("position note %s was raised once more already, on %s: it is not raised again"
                % (args.reopened, held[args.reopened]["reopened"]))
        held[args.reopened]["reopened"] = iso(today)
    if args.drop:
        st["positions"] = [p for p in st["positions"] if p.get("id") != args.drop]
    lapse_positions(st, today)
    # a round prepared ahead stays usable: it was written to respect the note, and the examiner
    # reads the notes from the ledger when grading
    bump_gen(st, content=False)
    st["updated"] = iso(today)
    out = {"ok": True, "gen": st["gen"], "dropped": args.drop, "reopened": args.reopened, "positions": listed()}
    publish_ledger(work, info, st, out)
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


def round_estimate(st):
    """What settings and init print about the round: the mix, its estimate and, once rounds
    are timed, what the estimate rests on (`basis`) and the hint."""
    mix, minutes, n = mix_estimate(st)
    out = {"mix": mix_text(mix), "estimated_minutes": minutes}
    if n:
        out["basis"] = based_on(n)
    hint = time_hint(st)
    if hint:
        out["time_hint"] = hint["text"]
    return out


def settings_in_effect(st, section):
    """The config or the profile of a ledger with listening and the podcast sources in the
    form they take effect in, for comparing two versions of the settings."""
    out = dict(st.get(section) or {})
    if section == "config":
        out["listening"] = listening_on(st)
        out["evidence_ladder"] = bool(out.get("evidence_ladder", True))   # a ledger without it has it on
    else:
        out["podcast_sources"] = podcast_sources(out.get("podcast_sources"), "profile.podcast_sources")
    return out


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
    set_paragraphs(st["profile"], was["profile"] or {}, prof_changes or {})
    check_paragraphs(st["profile"])
    if "podcast_sources" in (prof_changes or {}):
        st["profile"]["podcast_sources"] = podcast_sources(st["profile"]["podcast_sources"], "profile.podcast_sources")
    for k in ("listening", "evidence_ladder"):
        if k in (cfg_changes or {}) and not isinstance(st["config"][k], bool):
            die("config.%s must be true or false" % k)
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
    # keys that were sent (setting a value it already has changes nothing). Listening and the
    # podcast sources are compared as they take effect: a ledger without them has listening on
    # and no sources, so saying so again changes nothing.
    affects = [k for k in changed_keys(settings_in_effect(was, "config"), settings_in_effect(st, "config"))
               if k not in CONTENT_NEUTRAL_CONFIG]
    affects += ["profile." + k for k in changed_keys(settings_in_effect(was, "profile"), settings_in_effect(st, "profile"))
                if k not in CONTENT_NEUTRAL_PROFILE]
    if args.blueprint and st["blueprint"] != was["blueprint"]:
        affects.append("blueprint")
    bump_gen(st, content=bool(affects))
    st["updated"] = iso(today)
    out = {"ok": True, "gen": st["gen"], "config": st["config"], "review": st["review"], **guideline_context(st),
           "listening": listening_status(st)}
    out["round"] = round_estimate(st)       # what to confirm a new mix with
    if any(k in (prof_changes or {}) for k in ("journey", "aim", "journey_label", "aim_tags")):
        out["profile"] = {k: st["profile"].get(k) for k in ("journey", "journey_label", "aim", "aim_tags")}
    if labels_needed(st):
        out["labels_needed"] = labels_needed(st)
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
    migrate_profile(st)         # a profile given in the old fields (role, goals, notes) is folded too
    check_paragraphs(st["profile"])
    for key, _, _ in PARAGRAPHS:
        if (st["profile"].get(key) or "").strip() and not st["profile"].get(key + "_set_at"):
            st["profile"][key + "_set_at"] = now_ts()
    if st["profile"].get("podcast_sources") is not None:
        st["profile"]["podcast_sources"] = podcast_sources(st["profile"]["podcast_sources"], "profile.podcast_sources")
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
    out["round"] = round_estimate(st)
    if labels_needed(st):
        out["labels_needed"] = labels_needed(st)
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
                     "reflected")      # `minutes`: the active time of the round (idle time cut)


def page_session(doc):
    """What the page lists of one past session (from its session document or the ledger)."""
    e = {k: doc.get(k) for k in PAGE_SESSION_KEYS}
    e["tags"], e["topics"] = list(e["tags"] or []), list(e["topics"] or [])
    if isinstance(e["drill"], dict):
        e["drill"] = e["drill"].get("code")
    if doc.get("url"):
        e["url"] = doc["url"]
    return e


# The library (issue #51): the reading pointers and listening picks of past sessions, as the
# page's "Reading & listening" view lists them. Only what a saved session document holds goes
# in, so nothing of it can be about a coming round; the reasons (`why`) stay in the session
# document, since they are written about what the learner missed.
PAGE_LIBRARY_MAX = 100
PAGE_LIBRARY_KINDS = {"reading": "section", "listening": "show"}     # kind: its own extra field
PAGE_LIBRARY_KEYS = ("session", "date", "kind", "topic", "label", "title", "link", "minutes", "section", "show")


def page_library_entry(e):
    """One library entry in its fixed form, or None for anything that is not one."""
    if not isinstance(e, dict) or e.get("kind") not in PAGE_LIBRARY_KINDS or not e.get("session"):
        return None
    if not (isinstance(e.get("title"), str) and isinstance(e.get("link"), str)):
        return None
    other = next(v for k, v in PAGE_LIBRARY_KINDS.items() if k != e["kind"])
    return {k: e.get(k) for k in PAGE_LIBRARY_KEYS if k != other}


def page_library_of(doc):
    """The library entries of one session document: its `reading` list, then its `listening`."""
    out = []
    for kind in PAGE_LIBRARY_KINDS:
        items = doc.get(kind)
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                out.append(page_library_entry(dict(it, session=doc.get("id"), date=doc.get("date"), kind=kind,
                                                   label=None)))
    return [e for e in out if e]


def page_lists(path, old_index=None):
    """The lists a page file carries from one write to the next, {"sessions", "reviews",
    "library"}: from the page file at `path`, else from the index older versions kept
    (`old_index`), else empty. The ledger drops old sessions (§5 of the schema), so these lists
    are the only place their entries stay; a missing or damaged file loses nothing the ledger
    or `rebuild-page` cannot put back."""
    for p in (path, old_index):
        if not p or not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("sessions"), list):
            reviews, library = doc.get("reviews"), doc.get("library")
            return {"library": [e for e in map(page_library_entry, library if isinstance(library, list) else []) if e],
                    "sessions": [page_session(e) for e in doc["sessions"] if isinstance(e, dict) and e.get("id")],
                    "reviews": [{k: r.get(k) for k in ("date", "title", "headline")}
                                for r in (reviews if isinstance(reviews, list) else [])
                                if isinstance(r, dict) and r.get("date")]}
    return {"sessions": [], "reviews": [], "library": []}


def page_put_session(lists, doc):
    e = page_session(doc)
    old = next((x for x in lists["sessions"] if x.get("id") == e["id"]), None)
    if old and e.get("minutes") is None:
        e["minutes"] = old.get("minutes")
    lists["sessions"] = [x for x in lists["sessions"] if x.get("id") != e["id"]] + [e]
    # the session's reading and listening, as its document has them now
    lists["library"] = [x for x in lists.get("library") or [] if x.get("session") != e["id"]] + page_library_of(doc)


def page_put_review(lists, doc):
    e = {"date": doc.get("date"), "title": doc.get("title"), "headline": doc.get("headline")}
    lists["reviews"] = [x for x in lists["reviews"] if x.get("date") != e["date"]] + [e]


def page_doc(st, lists=None):
    """The page file for ledger `st`: what the page may show and nothing else. `lists` are the
    session and review entries carried on (page_lists); the ledger adds the sessions and reviews
    they lack and is the authority on scores, minutes and whether a round was reflected on."""
    cfg = st.get("config") or {}
    prof = migrate_profile({"profile": copy.deepcopy(st.get("profile") or {})})["profile"]
    lists = lists or {"sessions": [], "reviews": [], "library": []}
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
    # reading and listening of past sessions, newest session first and in the order the feedback
    # gave them; a topic is named by the ledger's label once it has been tested (it always has)
    labels = {t["id"]: t["label"] for t in topics}
    library = [dict(e, label=labels.get(e.get("topic")) or e.get("label")) for e in lists.get("library") or []]
    order = {id(e): n for n, e in enumerate(library)}
    library.sort(key=lambda e: (e.get("date") or "", id_num(e.get("session")), -order[id(e)]), reverse=True)
    mastery = [t["mastery"] for t in topics if isinstance(t["mastery"], (int, float))]
    period = [s.get("score") for s in st.get("sessions") or []]
    scores = [x for x in period if isinstance(x, (int, float))]
    mix, minutes, timed = mix_estimate(st)
    factor, hint = pace(st)["factor"], time_hint(st)
    per = lambda k: MINUTES_PER[k] if factor == 1.0 else round(MINUTES_PER[k] * factor, 2)
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

    def paragraph(key):
        text = prof.get(key).strip() if isinstance(prof.get(key), str) else ""
        return text or None
    # where you are / where you're aiming: the learner's own words with the labels derived for
    # display (null until the learner has written the paragraph)
    level = {"label": prof.get("journey_label"), "text": paragraph("journey")} if paragraph("journey") else None
    aim = {"tags": list(prof.get("aim_tags") or []), "text": paragraph("aim")} if paragraph("aim") else None
    return {
        "schema": PAGE_SCHEMA, "page_version": PAGE_VERSION, "gen": st.get("gen"), "updated": st.get("updated"),
        "who": {"name": prof.get("display_name"), "role": prof.get("journey_label") or prof.get("role"), "specialty": context["specialty"],
                "subspecialty": prof.get("subspecialty"), "practice": list(prof.get("practice_setting") or [])},
        "totals": {"topics": len(topics),
                   "mean_mastery": round(sum(mastery) / len(mastery), 1) if mastery else None,
                   "since": review.get("period_start"), "sessions": len(period),
                   "mean_score": round(sum(scores) / len(scores), 1) if scores else None},
        "sessions": sessions,
        "topics": topics,
        # the mix in force and what it costs: the page shows `minutes`, and prices a mix the
        # learner is choosing with `minutes_per` (the case already at the next round's format).
        # Both are at the learner's own pace once rounds are timed (`timed_rounds` of them: the
        # page then says "based on your last N rounds"); `time_hint` is the sentence on how
        # their rounds compare with their budget, from HINT_MIN_ROUNDS timed rounds
        "round": {"mix": mix, "set_at": cfg.get("round_set_at"),
                  "minutes": minutes,
                  "minutes_per": {"mcq": per("mcq"), "focused": per("focused"), "case": per(next_case_format(st))},
                  "limits": {k: list(v) for k, v in ROUND_LIMITS.items()},
                  "timed_rounds": timed,
                  "time_hint": hint["text"] if hint else None},
        "block": block,
        "reviews": sorted(reviews.values(), key=lambda r: r.get("date") or "", reverse=True),
        "next_review": review.get("next_due"),
        "library": library[:PAGE_LIBRARY_MAX],
        # the learner's own position notes, in their words (issue #75): what they hold, never what
        # a coming round tests; listed without the dates on which they lapse
        "positions": [{"id": p.get("id"), "topic": p.get("topic"), "label": labels.get(p.get("topic")),
                       "point": p.get("point"), "text": p.get("text"), "set": p.get("set"),
                       "confirmed": p.get("confirmed")}
                      for p in st.get("positions") or []
                      if not position_lapses(p) or position_lapses(p) >= (parse_date(st.get("updated")) or position_lapses(p))],
        "settings": {
            "session_length": cfg.get("session_minutes"), "per_week": cfg.get("target_sessions_per_week"),
            "region": context["guideline_region"],
            "units": {"labs": cfg.get("lab_units"), "gases": cfg.get("blood_gas_units")},
            "case_style": cfg.get("case_format"), "order": cfg.get("item_order"),
            "feedback": cfg.get("feedback_depth"), "coding_line": bool(cfg.get("show_coding", True)),
            "review_every_days": cfg.get("review_interval_days"), "reminders": bool(cfg.get("reminders")),
            "emphasis": dict(prof.get("domain_emphasis") or {}), "self_ratings": ratings,
            "level": level, "aim": aim,                  # {"label", "text"} and {"tags", "text"}
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
        # display labels the assistant still has to derive from the learner's paragraphs (None: none)
        "labels_needed": labels_needed(st),
        "helpers": bool(cfg.get("helpers", True)), "prepare_ahead": bool(cfg.get("prepare_ahead", True)),
        "testing": bool(cfg.get("testing", False)),
        **guideline_context(st),             # what the examiner grades against
        # the learner's own paragraphs: the examiner pitches the feedback to them (standards.md rule 4)
        "pitch": {k: (st["profile"].get(k) or None) for k, _, _ in PARAGRAPHS},
        # one podcast episode per topic in the final feedback: on or off, the shows to prefer and
        # to avoid, and `ask_sources` while the learner has not been asked for them yet
        "listening": listening_status(st),
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
    rewritten = paragraphs_changed(prefs_changes)
    kept = {}
    if rewritten:
        # a paragraph written on the page changes what the author pitches to: it is kept in the
        # ledger at once (the labels the assistant derives next are set on it), and the round
        # prepared for the old words is set aside
        bump_gen(st)
        st["updated"] = iso(today)
        path = publish_ledger(work, info, st, kept, empty_prepared=True)
    status = status_dict(st, path, today)
    status.update(extra)
    status.update(kept)
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
    elif rewritten:
        prepared = {"used": False, "why": "%s changed on the page" % " and ".join(rewritten)}
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
    # the round's clock starts; with a prepared round the first part goes out with this output
    first = prepared.get("present_block") or (
        "questions" if (plan_out.get("mcqs") or plan_out.get("focused")) and plan_out.get("item_order") != "case_first"
        else "case")
    status["started_at"] = start_times(work, st.get("next_id"), first, bool(prepared["used"]), args.at)
    status["opening"] = opening_line(status, plan_out, today)
    if rewritten:
        status["opening"] += (" This round is written now, for what you wrote on your page about %s."
                              % " and ".join(rewritten))
    if prepared["used"]:
        ready = prepared["ready"]
        status["prepared"]["unchecked"] = [n for n in SEALED_FILES if n in ready and EVIDENCE_FOR[n] not in ready]
    print(json.dumps(status, ensure_ascii=False))


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def opening_line(status, plan, today):
    """The opening line of a round, from neutral facts only: the mix, the time, the block's
    theme and position, the last saved session. Never a topic."""
    line = "Today's round: %s, about %s minutes%s." % (
        mix_text(plan), plan.get("estimated_minutes"),
        " (%s)" % based_on(plan.get("estimate_rounds")) if plan.get("estimate_rounds") else "")
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
    rewritten = paragraphs_changed(apply_prefs(st, info.get("prefs")))
    cfg = st["config"]
    why = None
    if not cfg.get("prepare_ahead", True):
        why = "prepare_ahead is off"
    elif st.get("unreflected") and not args.allow_unreflected:
        why = "the last session is still waiting for its reflection"
    elif args.if_needed and not rewritten and prepared_fits(store_file(work, info, PREPARED_PATH), st, today):
        why = "a round is already prepared"
    if why:
        print(json.dumps({"ok": True, "prepare": False, "why": why}))
        return
    kept = {}
    if rewritten:
        # a paragraph written on the page is kept in the ledger here, with its labels cleared: the
        # round is written for the new words and tied to the ledger that holds them. (A new mix
        # is only planned with; `start` and `save` keep that.)
        fresh, _ = current_ledger(work, info)
        apply_paragraphs(fresh, info.get("prefs") or {}, [])
        bump_gen(fresh)
        fresh["updated"] = iso(today)
        publish_ledger(work, info, fresh, kept, empty_prepared=True)
        bump_gen(st)            # the ledger planned with is that one, plus a mix still waiting
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
    if rewritten:
        summary.update(kept)
        summary["page_settings_applied"] = {k: "updated" for k, _, name in PARAGRAPHS if name in rewritten}
        published(work, info, summary)
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
    (`"recheck": [files]`), as are a kit's listening candidates that are not three episodes in
    form. With --revised whatever is still found is accepted and listed under `warnings`.
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
    lint = lint_round(files, plan, kits_required=True, candidates=not args.no_evidence)
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
    # listening candidates are the checker's (it searched for them): a kit whose candidates are
    # not three episodes in form sends its checker back once, not the author
    relisten = [EVIDENCE_FOR[sealed] for sealed, kit in KIT_FOR.items()
                if any(r["rule"] == 8 and r["file"] == kit for r in lint["review"])]
    out["lint"] = lint_summary(lint, write_lint_details(folder, lint))
    out["revise"] = bool(total or any(r["rule"] != 8 for r in lint["review"])) and not args.revised
    recheck = [] if args.revised else [n for n in EVIDENCE_FOR.values() if n in flagged or n in relisten]
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
                         "only what is not verified and the listening candidates that are not complete, "
                         "references/evidence_check.md §3 and §6) and wait for it" % " and ".join(recheck))
        if out["revise"] or flagged:
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
    # the first part of a round written now goes out as soon as it is printed: note when
    work = args.work or os.path.dirname(os.path.abspath(files[0]))
    if os.path.isfile(os.path.join(work, TIMES_FILE)) and read_times(work).get("first_block") == args.block:
        stamp(work, "sent:" + args.block, args.at, once=True)
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
               **({"estimate_rounds": plan["estimate_rounds"]} if plan.get("estimate_rounds") else {}),
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


def listening_picks(rnd, warnings):
    """Take the examiner's `listening` list out of the round (it belongs to the session document,
    not to the ledger) and return it as the document keeps it: one pick per topic of the round,
    each {topic, link, show, title, minutes, why} and, when given, `source` ("kit": a candidate
    prepared with the round; "search": found after grading). None when the round has no such
    list (listening is off). A pick that is not complete is left out, with a warning that names
    its place in the list and what is missing."""
    raw = rnd.pop("listening", None)
    if raw is None:
        return None
    if not isinstance(raw, list):
        warnings.append("round 'listening' must be a list of picks; it was left out of the session document")
        return None
    topics = [it.get("topic") for it in rnd.get("items") or [] if isinstance(it, dict)]
    picks, seen = [], set()
    for n, p in enumerate(raw, 1):
        tag = "listening pick %d" % n
        if not isinstance(p, dict):
            warnings.append("%s: not an object; left out" % tag)
            continue
        topic = p.get("topic")
        link = str(p.get("link") or "").strip().split("?")[0]
        try:
            minutes = int(round(float(p.get("minutes"))))
        except (TypeError, ValueError):
            minutes = None
        wrong = [k for k in ("show", "title", "why") if not (isinstance(p.get(k), str) and p[k].strip())]
        if topic not in topics:
            wrong.append("topic (one of this round's: %s)" % ", ".join(str(t) for t in topics))
        elif topic in seen:
            wrong.append("topic (one pick per topic)")
        if not SPOTIFY_EPISODE_RE.match(link):
            wrong.append("link (https://open.spotify.com/episode/<id>)")
        if minutes is None or minutes < 1:
            wrong.append("minutes")
        if wrong:
            warnings.append("%s: left out of the session document; correct %s" % (tag, ", ".join(wrong)))
            continue
        seen.add(topic)
        pick = {"topic": topic, "link": link, "show": p["show"].strip(), "title": p["title"].strip(),
                "minutes": minutes, "why": p["why"].strip()}
        if p.get("source") in LISTEN_SOURCES:
            pick["source"] = p["source"]
        picks.append(pick)
    return picks


def reading_pointers(rnd, warnings):
    """Take the examiner's `reading` list out of the round (like `listening`, it belongs to the
    session document, not to the ledger) and return it as the document keeps it: the pointers
    of the feedback's Further reading section, each {topic, title, link, section, minutes, why}.
    None when the round has no such list. A pointer that is not complete is left out, with a
    warning that names its place in the list and what is missing; so is one beyond READING_MAX."""
    raw = rnd.pop("reading", None)
    if raw is None:
        return None
    if not isinstance(raw, list):
        warnings.append("round 'reading' must be a list of pointers; it was left out of the session document")
        return None
    topics = [it.get("topic") for it in rnd.get("items") or [] if isinstance(it, dict)]
    out = []
    for n, p in enumerate(raw, 1):
        tag = "reading pointer %d" % n
        if not isinstance(p, dict):
            warnings.append("%s: not an object; left out" % tag)
            continue
        link = str(p.get("link") or "").strip()
        try:
            minutes = int(round(float(p.get("minutes"))))
        except (TypeError, ValueError):
            minutes = None
        wrong = [k for k in ("title", "section", "why") if not (isinstance(p.get(k), str) and p[k].strip())]
        if p.get("topic") not in topics:
            wrong.append("topic (one of this round's: %s)" % ", ".join(str(t) for t in topics))
        if not READING_LINK_RE.match(link):
            wrong.append("link (the document's own http(s) address)")
        if minutes is None or minutes < 1:
            wrong.append("minutes")
        if wrong:
            warnings.append("%s: left out of the session document; correct %s" % (tag, ", ".join(wrong)))
        elif len(out) >= READING_MAX:
            warnings.append("%s: left out of the session document; a round has at most %d" % (tag, READING_MAX))
        else:
            out.append({"topic": p["topic"], "title": p["title"].strip(), "link": link,
                        "section": p["section"].strip(), "minutes": minutes, "why": p["why"].strip()})
    return out


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
#
# A focused question and the case also carry their rubric in a marked block beside the header,
# one expected element per line (a line "Stage 1" / "Stage 2" groups the case's elements):
#
#   <!-- rubric: Q4 -->
#   - the decision: …
#   - the decisive reason: …
#   <!-- /rubric -->
#
# `answer` copies the elements into the grading form (round.json), to be marked hit, partial or
# missed (issue #76).

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
RUBRIC_RE = re.compile(r"<!--[ \t]*rubric:[ \t]*([A-Za-z0-9_]+)[ \t]*-->[ \t]*\n(.*?)\n?[ \t]*<!--[ \t]*/rubric[ \t]*-->", re.S)
RUBRIC_OPEN_RE = re.compile(r"<!--\s*rubric\b")
RUBRIC_BULLET_RE = re.compile(r"^(?:(?:[-*+]|\d+[.)])[ \t]+)?(?:\[[ xX]?\][ \t]+)?")
RUBRIC_STAGE_RE = re.compile(r"^[#*_`\s]*stage[ \t]*([1-9])\b[*_`\s]*(?:\([^)]*\))?[*_`\s:.\u2013\u2014-]*(.*)$", re.I)
RUBRIC_TYPES = ("focused", "case")        # an MCQ's key is its correct option: it has no rubric
RUBRIC_MARKS = ("hit", "partial", "missed")     # ✓ ◐ ✗ in the feedback
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
    problems.extend(rubric_problems(paths))
    return by_file, problems


def parse_rubrics(text, where="sealed file"):
    """The rubric blocks of one sealed file: ({id: [{"element", "stage"?}]}, [problems]), the
    elements in the order written. The problems name the file and the key, never an element."""
    rubrics, problems = {}, []
    found = RUBRIC_RE.findall(text or "")
    if len(RUBRIC_OPEN_RE.findall(text or "")) > len(found):
        problems.append("%s: a rubric block is not closed, or its first line is not '<!-- rubric: Q1 -->' "
                        "(or '<!-- rubric: case -->'); close each with '<!-- /rubric -->'" % where)
    for raw_id, body in found:
        kid = key_id(raw_id)
        if kid in rubrics:
            problems.append("%s, key %s: there are two rubric blocks with this id" % (where, kid))
            continue
        stage, elements = None, []
        for line in body.splitlines():
            line = line.strip()
            bullet = RUBRIC_BULLET_RE.match(line)
            text_ = line[bullet.end():] if bullet else line
            m = RUBRIC_STAGE_RE.match(text_)
            if m:
                stage, text_ = int(m.group(1)), m.group(2)
            text_ = text_.strip().strip("#").strip()
            if text_:
                elements.append(dict({"element": text_}, **({"stage": stage} if stage else {})))
        if not elements:
            problems.append("%s, key %s: the rubric block has no elements (one expected element per line)"
                            % (where, kid))
        rubrics[kid] = elements
    return rubrics, problems


def rubric_problems(paths):
    """Rule 9, the rubric: every focused question and the case have a rubric block in their sealed
    file, with at least one element, outside the text to present; no block for an MCQ or for a
    key that has no header. Names files and keys only."""
    problems = []
    for path in paths or []:
        name, text = os.path.basename(path), read_text(path)
        headers = parse_key_headers(text, name)[0]
        rubrics, probs = parse_rubrics(text, name)
        problems.extend(probs)
        for kid, h in headers.items():
            if h.get("type") in RUBRIC_TYPES and kid not in rubrics:
                problems.append("%s, key %s: no rubric block ('<!-- rubric: %s -->', one expected element per "
                                "line, '<!-- /rubric -->'; references/standards.md rule 9)" % (name, kid, kid))
        for kid in rubrics:
            if kid not in headers:
                problems.append("%s, key %s: a rubric block without a key header in the same file" % (name, kid))
            elif headers[kid].get("type") == "mcq":
                problems.append("%s, key %s: an MCQ has no rubric block (its key is the correct option)" % (name, kid))
        for block in PRESENT_RE.findall(text) + BANK_RE.findall(text):
            if RUBRIC_OPEN_RE.search(block[1]):
                problems.append("%s: a rubric block sits inside the text to present or the results bank "
                                "(rule 1.2)" % name)
                break
    return problems


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


# ---------------------------------------------------------------- the command and file tables
#
# The command table (§6) and the work-folder file table (§6.1) of references/state_schema.md are
# printed from these rows by `command-table` and `file-table`, between their markers, as
# `key-table` prints rule 9; tests/test_tables.py fails when a copy differs, or when a command of
# the parser is missing from the table. The cells are Markdown, as they stand in the table.

COMMANDS = (
    ('`open --work W --store DIR [--version V] [--prefs J] [--reread]`',
     'Set up the work folder for any job from `DIR`, the local copy of the store as just read: '
     "the store's layout (`DIR/data/state.json`, `DIR/data/page.json`, `DIR/data/prepared.json`, "
     '`DIR/index.html`, `DIR/data/sessions/<id>.json`) or the files side by side '
     '(`DIR/state.json`, …). Writes `W/work.json` and an empty manifest carrying `V`, the store '
     'version read. If `W` holds an earlier job (answers, a publish set, drafts of a next round),'
     ' its files are first moved to `W/earlier/<n>/` (`earlier_set_aside`). Prints neutral '
     'status: `gen`, `next_id`, counts, `review_due`, `testing`, the block; never a topic. '
     '`--reread`: the same job on a fresh read after a refused publish (`store.md` §4.1): the '
     "job's own files stay, the publish set is dropped, and the job's commands are run again."),
    ('`start --work W [--store DIR [--version V]] [--prefs J] [plan options] [--no-prepared]`',
     'Start a round. With `--store` it does what `open` does first; without, it continues the job'
     ' that is open (a settings change or a late reflection earlier in the same conversation), '
     'from the ledger that job wrote. The plan is written to `W/plan.json`. Prints the neutral '
     "status with the plan's counts (MCQs, focused, case, `estimated_minutes`, and "
     "`estimate_rounds` when the estimate is at the learner's own pace, §6.2) under `plan`, plus "
     '`helpers`, `prepare_ahead` and `speed_settings_new`. No topic names. With a plan it also '
     'prints what the first message needs, so that nothing else is run or read before it: '
     '`opening` (the opening line, word for word: the mix, the minutes, "(based on your last N '
     'rounds)" once rounds are timed, the block\'s line, with its reason when a block starts, and '
     "the last saved session) and `started_at` (when the round's clock started, §6.2; nothing to "
     "copy). `--prefs` is the page's `cme/prefs` document (§7.1); `page_settings_applied` says "
     'when it changed the mix or brought a new paragraph (which `start` writes to the ledger at '
     "once, into the publish set; §7.1), `pitch` holds the learner's two paragraphs for the "
     'examiner and `labels_needed` the display labels still to derive (§1), and `round_mix` says '
     'when a prepared round was written for another mix than the one in force (§8). The prepared '
     'round is read from the store copy (§8): when it still fits, `prepared.used` is true, '
     "`present` holds the first part's text to send (`prepared.present_block` says which) and the"
     ' drafted files (`prepared.ready`: `sealed_questions.md`, `sealed_case.md`, '
     '`kit_questions.md`, `kit_case.md`, `evidence_questions.md`, `evidence_case.md`) are written'
     ' into the work folder, with `prepared.unchecked` naming the sealed files that came without '
     'an evidence file (start a checker for each); otherwise `prepared.why` says why not and the '
     'round is planned as usual. Plan options, for this round only: `--mcqs N`, `--focused N`, '
     '`--no-case`, `--domain CODE`, `--no-new`, `--allow-repeat`, `--no-drill`.'),
    ('`present --work W --block questions\\|case\\|bank`',
     'Print only the text the learner is to see from the sealed files in `W` (one `present` '
     "block, or the case's results bank), so it can be sent without opening the keys. For the "
     'first part of a round written now it also notes that the part went out (§6.2).'),
    ('`answer --work W --part questions\\|case\\|final\\|notes\\|reflection [--file F \\| --text T]`',
     'Append what the learner answered for one part to `W/answers.md`, exactly as given (default:'
     ' standard input). Earlier parts are never rewritten; the same text for the same part is '
     'added once; a second message for a part is added after the first. Prints the part names '
     'filed so far, never the text. With a part that completes its answers (`questions`; `final`;'
     ' `case` for a one-step case) it also prints `depth`: the evidence depth of each of that '
     "part's items by key id (`level` 1–4, `name`, `in_a_row`; §4.2), read from the key headers "
     'and the ledger, for the feedback about to be written. No `depth` with `evidence_ladder` '
     "false. It also prints `positions`: the learner's position notes in force on each item's "
     'topic, by key id (`standards.md` rule 12), for the grading. With such a part it also writes '
     'the **grading form** into `W/round.json` (§2), and with `reflection` the **reflection form** '
     'into `W/reflection.json` (§3), and prints `form` (the file, the key ids `added`, '
     '`draft`, the part to give `draft` once the form is marked, `rubric_missing` for a focused '
     'question or case whose key has no rubric block); a form never '
     'overwrites what was filled in. It also notes when it ran, as '
     "the time the learner's message arrived (§6.2): run it first when a message arrives."),
    ('`draft --work W --part questions\\|case\\|all`',
     'Once the grading form is marked (every rubric element hit, partial or missed with the '
     "learner's words, every MCQ's `correct`; refused while one is blank: marks before text), put "
     'together the draft of a feedback message from the kits\' prepared blocks (`standards.md` '
     'rule 8; ADR 0009): the reveals, then per item the rubric as marked and the blocks its marks '
     'call for, with `[live: …]` where only the examiner can write and a `check` line above a '
     'block whose claim the evidence file does not confirm; the final message also gets the '
     "kit's reading and listening notes. Writes `W/draft_questions.md` (the questions' feedback, "
     'with a case still to come) or `W/draft.md` (the final feedback; `all`: every item, as with '
     '`case_first`). Prints counts only: `blocks`, `live`, `checks`, `no_prepared_text`, '
     '`sent_as`.'),
    ('`sent --work W --part questions\\|questions_feedback\\|case\\|stage2\\|feedback\\|close [--at '
     'T]`',
     'Not part of a normal round. Notes when a message went out, where the engine cannot tell '
     '(§6.2): no file was written as sent, or it was written late.'),
    ('`save --work W`',
     'First save after the final feedback: the round is recorded in the ledger from the grading '
     'form as filled in (`W/round.json`, §2; a blank score stops it, nothing recorded), the session '
     'document is written (part A assembled in the order of the round from the sealed `present` '
     "blocks, Stage 2 as sent, the answers, the questions' feedback and the final feedback), with"
     ' the page file (§7) and an emptied `data/prepared.json`. Everything is found by its fixed '
     'name (§6.1); the page settings given at the start are applied so the mix is kept in the '
     "ledger. Prints per-topic next due, warnings, `errata_to_log`, and `files`. If the learner's"
     " `index.html` is older than the skill's template, the new one joins the publish set "
     '(`page_upgraded`). Run again in the same job, it undoes the round and records it again '
     '(§3.1), so it gives the same result (a settings change made earlier in the same job is '
     'kept). Records the time measured so far (`minutes`, `timing`; §6.2) and, when a draft was '
     'made, which of its prepared blocks reached the feedback as sent as prepared, changed or not '
     'at all (`prepared_feedback`: in the session document only, `session_log.md` §2; counts in the '
     'output).'),
    ('`close --work W [--reflection J] [--session ID]`',
     'Second save: the reflection is applied and part B goes into the session document, with the '
     'page file. It continues from the current ledger: the one `save` wrote in this job, or, for '
     'a reflection given at a later session, the ledger as read; the session document then comes '
     'from the store copy (`data/sessions/<id>.json`), and the command stops if it was not read. '
     'The reflection JSON is `W/reflection.json` (the reflection form as filled in, §3) unless '
     'given inline. Can be run again after a '
     'correction to `B.md` or to the reflection (§3.1), until `override` changes the round. '
     "Completes the round's measured time (the reading of the final feedback, up to the "
     'reflection) and prints `time_hint` once five rounds are timed (§6.2): one line of the '
     'closing message.'),
    ('`override --work W [--scores J] [--close-gaps J] [--stops J] [--session ID]`',
     "After the close: a score the learner sets themselves, a gap closed at the learner's request"
     ' and a stop with its position note (the entries of `learner_scores`, `learner_closed_gaps` '
     'and `learner_stops`, §3). Writes the ledger, the session document (`learner_changes`, a '
     '"Set by the learner" addendum) and the page file into the publish set. Refused while the '
     'round is unreflected (use the reflection JSON) and, for scores, for a round from before the'
     ' last review.'),
    ('`addendum --work W --md ADD.md [--session ID]`',
     'Append later discussion to a session document (default: the last session; the document '
     'comes from the publish set or the store copy).'),
    ('`prepare --work W [--if-needed] [--allow-unreflected]`',
     'Plan the next round (as of tomorrow) from the current ledger, into `W/next/plan.json`. '
     'Prints counts only, or `"prepare": false` with the reason (setting off, reflection pending,'
     ' or — with `--if-needed` — a usable round is already prepared in the store). `--allow-'
     'unreflected` plans although the last session has no reflection yet (the scheduled task uses'
     ' it). A paragraph the learner wrote on the page (in the `--prefs` given to `open`) is '
     'written to the ledger first, into the publish set, and reported as `page_settings_applied` '
     'with the `files` (§7.1); a round prepared for the old words does not count as usable.'),
    ('`finish-prepare --work W [--revised] [--no-evidence]`',
     'After the checkers: finish preparing the round planned in `W/next/plan.json` and drafted in'
     ' `W/next`. First lints it against the rulebook (`standards.md`, "The lint"). **Blocking**: '
     'the key headers of the sealed files against the plan, as `keys --plan` checks them, and the'
     ' kits and their sections (rule 8); a problem is an error (exit 2, nothing stashed) that '
     'lists every one by file, key, field or section, whatever the evidence says and also with '
     '`--no-evidence` or `--revised`. **Judgement calls** (an abbreviation that looks undefined, '
     'rule 5; time anchors that look mixed, rule 6): counted in `lint` (`abbreviations`, '
     '`time_anchors`, `where` by file, `details`: the path of `W/next/lint.md`, where the '
     'findings are written for the author and never printed). Then reads the last two lines of '
     'each evidence file (`Checked: <date>, <n> claims, <n> not verified` and `Keys contradicted:'
     ' <n>`, `evidence_check.md` §4) for every sealed part the round has, and prints counts and '
     'file names only: `evidence` (keys contradicted per file), `contradicted` (the total), '
     '`not_verified` (per file: `claims`, `not_verified`, and `untried`, the "not verified" '
     "blocks without a `Tried:` line; `not_verified` is the larger of the line's number and the "
     'blocks so marked), `not_verified_total`, `claims_total`, `recheck` (the evidence files that'
     " go back to their checker: more than a third of the file's claims not verified, or any "
     '`untried`), `revise` and `stashed`. Nothing contradicted, no judgement call and no file to '
     'recheck → the round is packed and joins the publish set as `data/prepared.json` (§8) in the'
     ' same command. Otherwise → `"stashed": false` and a `next` line: the checker retries the '
     'files in `recheck` once, then the author revises once (`"revise": true` when a key is '
     'contradicted or the lint made a judgement call; after a retry it also carries what was '
     'confirmed into the kits), and the command is run again with `--revised`, which stashes; '
     'what is still found is then listed under `warnings` ("accepted after one revision: …", '
     '"accepted after one retry: … n of m claims not verified"). An evidence file that is '
     'missing, empty or without either count line in that form (also one that counts no claims, '
     'or more not verified than claims) is an error (exit 2, nothing stashed), never a count of '
     'zero. `--no-evidence` is for a session that runs no checker: the round is stashed without '
     'evidence files, so the sources are checked at the session; the lint runs all the same. The '
     "first part's sealed file must be there; a missing case is a warning (it is then written at "
     'the next session).'),
    ('`keys DIR\\|SEALED… [--plan PLAN]`',
     "The author's check before finishing: the key headers and rubric blocks of sealed files "
     "(`standards.md` rule 9) and, for a folder, the kits' sections (rule 8; a kit not written yet is not a problem "
     'here). Prints the key ids each file has and `problems`, naming file, key, field and section'
     ' only, never a topic or a value; with `--plan`, also whether the number of headers of each '
     "type matches the plan's counts. `review` lists the lint's judgement calls as counts per "
     'file; the findings go to `lint.md` in the folder (`details`). Exit code 1 when there is a '
     'problem; `review` alone does not fail it.'),
    ('`key-table`',
     "Prints the key-header table of `standards.md` rule 9 from the engine's `KEY_*` definitions;"
     " a test fails when the rulebook's copy differs."),
    ('`command-table`, `file-table`',
     "Print this table and the work-folder table of §6.1 from the engine's own rows; a test fails "
     'when the copy here differs, or when a command is missing from the table.'),
    ('`verify --work W --store CHECK`',
     'Testing mode: compare the publish set with the store read again into `CHECK`; the result is'
     ' also written to `W/verify.json`.'),
    ('`testing-note --work W --feedback J`',
     "Testing mode: the learner's quick feedback and `W/verify.json`, as `data/testing/<id>.json`"
     " for this job's round."),
    ('`stats --work W`',
     'Review figures: period, previous period, all time; gaps, calibration, teaching points '
     'unchecked, blind spots; `timing` (medians of the last timed rounds: minutes, answering, '
     "waiting, reading; the pace; the hint); `positions`, the notes in force with their topic's "
     '`label` and the day each `lapses`. Writes nothing.'),
    ('`review --work W --review REVIEW.json`',
     'Record a review; closes the period. Its `positions` (`{"keep": [ids], "drop": [ids]}`) '
     'confirm or end position notes; lapsed notes leave the ledger.'),
    ('`review-doc --work W --md REPORT.md [--headline H] [--date D] [--title T]`',
     'A review report as `data/reviews/<date>.json`, listed in the page file.'),
    ('`position --work W [--drop ID \\| --reopened ID]`',
     "The learner's position notes (§1). Alone: the notes in force (`id`, `point`, `text`, `set`,"
     ' `topic`, `lapses`), writing nothing. `--drop`: the learner takes one back. `--reopened`: '
     'the examiner raised a changed guideline on it once more (`standards.md` rule 12); refused '
     'the second time. The ledger and the page file go into the publish set; the prepared round '
     'is kept.'),
    ('`snooze --work W [--days 7]`',
     'Postpone a due review. Keeps the prepared round.'),
    ('`settings --work W [--config J] [--profile J] [--blueprint FILE]`',
     'Change settings: the changed ledger, the page file and the page if it is out of date go '
     'into the publish set, with an emptied `data/prepared.json` when the change can alter a '
     'round; `prepared` says whether the prepared round was kept and why (§8). A change to '
     '`mcqs`, `focused` or `case` is checked (at least one item) and supersedes any older page '
     'setting; a refused change writes nothing. Prints `round`: the mix in force in words, its '
     '`estimated_minutes`, and once rounds are timed `basis` ("based on your last N rounds") and '
     '`time_hint` (§6.2). `--profile \'{"journey": "…"}\'` or `\'{"aim": "…"}\'` stores a new '
     "paragraph in the learner's words, dates it and clears its label unless the same change "
     'gives one; `\'{"journey_label": "…", "aim_tags": […]}\'` sets the display labels (from their '
     'fixed lists, §1) and keeps the prepared round. With a paragraph or a label in the change it'
     ' prints `profile` (the two paragraphs and their labels), and `labels_needed` while a label '
     'is still to derive.'),
    ('`theme --work W [--set DOMAIN \\| --another]`',
     'The learner changes the theme of the block (§4.1): `--set` a domain by id or name, '
     '`--another` the next proposal. Prints `block`, `was`, `say` and, like `settings`, the '
     '`files` to publish. Alone: the block, the proposal and the domains to choose from; writes '
     'nothing.'),
    ('`init --work W --profile J --config J --blueprint FILE [--start-over]`',
     'Setup: the first ledger, its page file and the page, into the publish set. Prints `round` '
     '(the mix in words and its `estimated_minutes`) to confirm the mix with, and `labels_needed`'
     ' when a paragraph came without its label. A profile given in the old fields (`role`, '
     '`goals`, `notes`) is folded into the paragraphs (§1). `W` needs no store yet. In a work '
     'folder opened on a store that already holds a ledger it stops unless `--start-over` is '
     'given.'),
)
MAINTENANCE_COMMANDS = (
    ('`import EXPORT.json --out-dir D`',
     'A page export into the file layout (`store.md` §6, a damaged ledger).'),
    ('`rebuild-page ROOT`',
     'Rebuild `ROOT/data/page.json` (§7) from the session and review files and the ledger of a '
     "folder in the store's layout; `reindex` is its old name and still works."),
    ('`blueprint-md FILE --out BP.json`',
     'Convert a Markdown blueprint.'),
    ('`validate STATE` (or `validate --work W`)',
     'Structural check.'),
)
WORK_FILES = (
    ('`work.json`',
     '`open`, `start`: the store copy, the ledger as read, the store version, the session ID, the'
     ' page settings; `save`, `close`: the round each recorded (`saved`, `closed`), so that '
     'either can be run again in this job',
     'every command'),
    ('`plan.json`',
     '`start`',
     'whoever writes the items'),
    ('`sealed_questions.md`, `sealed_case.md`, `kit_*.md`, `evidence_*.md`',
     'the author and the checker, or `start` from a prepared round',
     '`present`, the examiner once a part is answered, `save` (the `present` blocks)'),
    ('`answers.md`',
     '`answer`, one block per part (`<!-- answers: questions -->` … `<!-- /answers -->`)',
     '`save` (questions, case, final, notes), `close` (reflection)'),
    ('`feedback_questions.md`, `stage2.md`, `feedback.md`',
     'the examiner: each message exactly as sent',
     '`save`'),
    ('`draft_questions.md`, `draft.md`',
     '`draft`: the feedback\'s prepared text chosen by the marks, with the live parts to write',
     'the examiner; `save` (which blocks were used as prepared, changed or left out)'),
    ('`round.json` (§2)',
     '`answer`: the grading form, one entry per key id, once a part\'s answers are in; the examiner '
     'fills it in',
     '`save`'),
    ('`record.json` (§2), `A.md`',
     '`save`: the round record, built from the key headers and `round.json`; part A as assembled',
     "the simulation's checks; anyone who wants to see what was recorded"),
    ('`reflection.json` (§3), `B.md` (`session_log.md` §3)',
     '`answer --part reflection`: the reflection form, which the examiner fills in; `B.md`: the '
     'examiner',
     '`close`'),
    ('`next/`',
     "`prepare` (`plan.json`), the author and the checker (the next round's files), `finish-"
     'prepare` (`lint.md`: what the lint found, for the author)',
     '`finish-prepare`; the author for `lint.md`'),
    ('`publish/`',
     'every command that writes: the newest version of each store file this job changed, at its '
     'store path',
     'the commands that follow (the current ledger is `publish/data/state.json`), `verify`, '
     'whoever publishes'),
    ('`publish.json`',
     'every command that writes: `{"version": <store version read>, "files": [{"as", "path"}, '
     '…]}`, in write order',
     'whoever publishes'),
    ('`verify.json`',
     '`verify`',
     '`testing-note`'),
    ('`times.json`',
     '`start`, `present`, `answer`, `sent`, `save`, `close`: when each step of the round happened'
     ' (§6.2)',
     '`save`, `close`'),
    ('`close_from.json`',
     '`close`: the round as it stood before its reflection, and its entry as `close` left it, so '
     'that `close` can be run again (§3.1)',
     '`close`'),
    ('`earlier/<n>/`',
     '`open`, `start`: the files of an earlier job in the same folder, set aside',
     'nobody'),
)
COMMAND_TABLE_OPEN = "<!-- command-table: generated by `cme.py command-table`; do not edit by hand -->"
COMMAND_TABLE_CLOSE = "<!-- /command-table -->"
FILE_TABLE_OPEN = "<!-- file-table: generated by `cme.py file-table`; do not edit by hand -->"
FILE_TABLE_CLOSE = "<!-- /file-table -->"


def markdown_table(head, rows):
    return "\n".join(["| %s |" % " | ".join(head), "|%s" % ("---|" * len(head))]
                     + ["| %s |" % " | ".join(r) for r in rows])


def command_table():
    """The command tables of state_schema.md §6, as Markdown: the protocol's, then the maintenance tools'."""
    return "\n".join([markdown_table(("Command", "Use"), COMMANDS), "",
                      "Maintenance tools, outside the protocol; they take their own files and folders:", "",
                      markdown_table(("Command", "Use"), MAINTENANCE_COMMANDS)])


def file_table():
    """The work-folder file table of state_schema.md §6.1, as Markdown."""
    return markdown_table(("File", "Written by", "Read by"), WORK_FILES)


def command_names():
    """The command each row of the command tables documents."""
    names = []
    for r in COMMANDS + MAINTENANCE_COMMANDS:
        for n in re.findall(r"`([a-z][a-z-]*)", r[0]):
            if n not in names:
                names.append(n)
    return names


def cmd_command_table(args):
    """Print the command tables for references/state_schema.md §6 (between their two markers)."""
    sys.stdout.write("%s\n%s\n%s\n" % (COMMAND_TABLE_OPEN, command_table(), COMMAND_TABLE_CLOSE))


def cmd_file_table(args):
    """Print the work-folder file table for references/state_schema.md §6.1 (between its two markers)."""
    sys.stdout.write("%s\n%s\n%s\n" % (FILE_TABLE_OPEN, file_table(), FILE_TABLE_CLOSE))


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
# without a case. Both kits end with "Listening" unless the learner turned listening off: one
# line per topic of the kit ("Q1 | points: …", written by the author), and under it the
# candidate episodes (found by the checker), one line each:
#   - <link> | <show> | <title> | <n> min | covers: … | matches: …
KIT_CASE_SECTIONS = ("Reveal", "Model answer", "Differential", "Briefing", "Pearls", "Reading")   # the rubric: in the key
KIT_READING = "Reading"
KIT_LISTENING = "Listening"
# The feedback's finished text sits in the kits as prepared blocks (rule 8; ADR 0009), one per
# part of an item's feedback and one per rubric element and mark:
#   <!-- block: Q1 model -->           the item's own text (BLOCK_ITEM_KINDS)
#   <!-- block: Q4.2 missed -->        the 2nd element of Q4's rubric block, marked missed
#   <!-- /block -->
# An item the plan gives an evidence depth beyond the first also has a `deeper` block.
BLOCK_RE = re.compile(r"<!--[ \t]*block:[ \t]*([A-Za-z0-9_]+?)(?:\.(\d+))?[ \t]+([A-Za-z]+)[ \t]*-->[ \t]*\n"
                      r"(.*?)\n?[ \t]*<!--[ \t]*/block[ \t]*-->", re.S)
BLOCK_OPEN_RE = re.compile(r"<!--\s*block\b")
BLOCK_ITEM_KINDS = {"mcq": ("reveal", "model", "distractors", "hit", "missed"),
                    "focused": ("reveal", "model", "decisive"),
                    "case": ("reveal", "model", "differential", "pearls")}
BLOCK_DEEPER = "deeper"
KIT_DEEPER = BLOCK_DEEPER
KIT_QUESTION_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]*[*_`]*(Q[1-9][0-9]?)\b", re.I | re.M)
LISTEN_BULLET_RE = re.compile(r"^[ \t>]*(?:[-*+]|\d+[.)])?[ \t]*")
LISTEN_TOPIC_RE = re.compile(r"^[*_`]*(Q[1-9][0-9]?|case)[*_`]*[ \t]*(?:\||$)", re.I)
LISTEN_LENGTH_RE = re.compile(r"^(?:about[ \t]+|~[ \t]*)?(\d{1,3})[ \t]*min", re.I)
LISTEN_FIELDS = 6
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


# Rule 11: words that belong to the skill's own machinery and never reach the learner.
INTERNAL_TERMS_RE = re.compile(
    r"\brule\s+\d+(?:\.\d+)?\b|\b[\w-]+\.(?:md|json|py)\b|\bcme\.py\b|\bkey[ -]headers?\b"
    r"|\bkits?\b|\bkit_(?:questions|case)\b|\bsealed(?:_\w+)?\b|\blint\b|\bresults bank\b"
    r"|\bverification list\b|\bpublish set\b|\bwork folder\b|\bthe (?:author|checker)\b", re.I)


def internal_terms(text):
    """The words of the skill's own machinery in a text meant for the learner (rule 11), in
    order of appearance, each once."""
    seen = []
    for m in INTERNAL_TERMS_RE.finditer(text or ""):
        w = m.group(0)
        if w.lower() not in [x.lower() for x in seen]:
            seen.append(w)
    return seen


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


def kit_section(text, name):
    """The body of the kit's first section whose heading starts with `name` (to the next
    heading), or None when there is no such heading."""
    heads = list(HEADING_RE.finditer(text or ""))
    for i, m in enumerate(heads):
        if m.group(1).strip().strip("*_`").strip().lower().startswith(name.lower()):
            return text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
    return None


def listening_topics(text):
    """The "Listening" section of a kit, read: {topic id: {"entries": [[field, …]], "none": bool}}
    in the order written ("Q1", …, "case"), or None when the kit has no such section. A line
    that starts with a key id opens a topic; under it every line with a link or with fields is
    one candidate, and a line starting "none" says that fewer than three were kept on purpose."""
    body = kit_section(text, KIT_LISTENING)
    if body is None:
        return None
    topics, current = {}, None
    for line in body.splitlines():
        line = LISTEN_BULLET_RE.sub("", line, count=1).strip()
        if not line:
            continue
        m = LISTEN_TOPIC_RE.match(line)
        if m:
            kid = m.group(1)
            kid = "case" if kid.lower() == "case" else kid.upper()
            current = topics.setdefault(kid, {"entries": [], "none": False})
        elif current is None or line.lower().startswith("sources"):
            continue
        elif line.strip("*_`").lower().startswith("none"):
            current["none"] = True
        elif "|" in line or "spotify.com" in line:
            current["entries"].append([f.strip() for f in line.split("|")])
    return topics


def listening_entry_flaws(fields, avoid=()):
    """What is wrong with one candidate line, as words that name no content: [] when it has its
    six fields, a link to one Spotify episode, a length of 15 to 90 minutes and a show the
    learner does not avoid."""
    flaws = []
    if len(fields) != LISTEN_FIELDS or not all(fields):
        flaws.append("fields")
    link = fields[0].strip("<>") if fields else ""
    if not SPOTIFY_EPISODE_RE.match(link):
        flaws.append("link")
    m = LISTEN_LENGTH_RE.match(fields[3]) if len(fields) > 3 else None
    if not m or not LISTEN_MINUTES[0] <= int(m.group(1)) <= LISTEN_MINUTES[1]:
        flaws.append("length")
    if len(fields) > 1 and fields[1].strip("*_`").casefold() in [a.casefold() for a in avoid]:
        flaws.append("avoided show")
    return flaws


def listening_findings(files, plan=None):
    """Rule 8, the judgement call on the candidates the checker kept: per kit and topic, lines
    that are not a candidate in form (fields, link, length, an avoided show), fewer than three
    candidates with no "none" line, or more than three. Names files, key ids and counts only."""
    if plan is not None and plan.get("listening") is False:
        return []
    avoid = ((plan or {}).get("podcast_sources") or {}).get("avoid") or []
    found = []
    for kit in KIT_FOR.values():
        for kid, topic in (listening_topics(files.get(kit)) or {}).items():
            flaws = [f for e in topic["entries"] for f in listening_entry_flaws(e, avoid)]
            bad = sum(1 for e in topic["entries"] if listening_entry_flaws(e, avoid))
            n = len(topic["entries"])
            said = []
            if bad:
                said.append("%d of %d candidate%s malformed (%s)"
                            % (bad, n, "" if n == 1 else "s", ", ".join(sorted(set(flaws)))))
            if n - bad < LISTEN_CANDIDATES and not topic["none"]:
                said.append("%d usable candidate%s, %d wanted (or a line 'none: why')"
                            % (n - bad, "" if n - bad == 1 else "s", LISTEN_CANDIDATES))
            if n > LISTEN_CANDIDATES:
                said.append("%d candidates, %d wanted" % (n, LISTEN_CANDIDATES))
            if said:
                found.append({"rule": 8, "file": kit, "where": "Listening, %s" % kid, "detail": "; ".join(said)})
    return found


def question_sections(text):
    """{key id: the kit's text for that question}, from its heading to the next question's."""
    heads = list(KIT_QUESTION_HEADING_RE.finditer(text or ""))
    return {m.group(1).upper(): text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
            for i, m in enumerate(heads)}


def deep_topics(plan):
    """The topics the plan gives an evidence depth beyond the first."""
    deep = {c.get("topic") for c in (plan or {}).get("items") or [] if (c.get("depth") or {}).get("level", 1) > 1}
    deep.discard(None)
    return deep


def block_id(kid, n, kind):
    """A prepared block's id as the draft and the log write it: "Q1 model", "Q4.2 missed"."""
    return "%s%s %s" % (kid, ".%d" % n if n else "", kind)


def parse_blocks(text, where="kit"):
    """The prepared blocks of a kit (or a draft): ({block id: text}, [problems]), in the order
    written. The problems name the file and the block id, never its text."""
    blocks, problems = {}, []
    found = BLOCK_RE.findall(text or "")
    if len(BLOCK_OPEN_RE.findall(text or "")) > len(found):
        problems.append("%s: a prepared block is not closed, or its first line is not '<!-- block: Q1 model -->' "
                        "(close each with '<!-- /block -->')" % where)
    for raw_id, n, kind, body in found:
        bid = block_id(key_id(raw_id), int(n) if n else None, kind.lower())
        if bid in blocks:
            problems.append("%s: two prepared blocks '%s'" % (where, bid))
            continue
        blocks[bid] = body.strip()
    return blocks, problems


def required_blocks(kid, typ, rubric, deep=False):
    """The block ids rule 8 asks of the item `kid`: its own kinds, one per rubric element and mark
    (a focused question and the case), and `deeper` when the plan gives it a depth."""
    want = [block_id(kid, None, k) for k in BLOCK_ITEM_KINDS.get(typ, ())]
    if typ in RUBRIC_TYPES:
        want += [block_id(kid, n, m) for n in range(1, len(rubric or []) + 1) for m in RUBRIC_MARKS]
    if deep:
        want.append(block_id(kid, None, BLOCK_DEEPER))
    return want


def block_problems(sealed, kit, sealed_text, kit_text, plan):
    """Rule 8, the prepared blocks: every block the items of `sealed` need is in `kit`, with text,
    and no block names a key, an element or a kind that is not there. File, key and block ids only."""
    headers = {k: h for k, h in parse_key_headers(sealed_text, sealed)[0].items()
               if (k == "case") == (kit == "kit_case.md")}
    rubrics = parse_rubrics(sealed_text, sealed)[0]
    blocks, problems = parse_blocks(kit_text, kit)
    deep = deep_topics(plan)
    allowed = set()
    for kid, h in headers.items():
        want = required_blocks(kid, h.get("type"), rubrics.get(kid), h.get("topic") in deep)
        allowed.update(want + [block_id(kid, None, BLOCK_DEEPER)])
        missing = [b for b in want if not blocks.get(b)]
        if missing:
            problems.append("%s, key %s: no prepared block %s (finished text between '<!-- block: %s -->' and "
                            "'<!-- /block -->'; references/standards.md rule 8)"
                            % (kit, kid, ", ".join(missing), missing[0]))
    stray = [b for b in blocks if b not in allowed]
    if stray:
        problems.append("%s: prepared blocks for no item, element or kind of this round: %s"
                        % (kit, ", ".join(stray)))
    return problems


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
        listening = (plan or {}).get("listening") is not False
        if listening:
            want.append(KIT_LISTENING)
        missing = [name for name in want if not any(h.startswith(name.lower().rstrip("s")) for h in heads)]
        if missing:
            problems.append("%s: section%s %s missing (a heading for each: %s)"
                            % (kit, "" if len(missing) == 1 else "s", ", ".join("'%s'" % m for m in missing),
                               ", ".join("'## %s'" % m for m in missing)))
        problems.extend(block_problems(sealed, kit, files[sealed], files[kit], plan))
        topics = listening_topics(files[kit]) if listening else None
        if topics is not None:
            ids = ["case"] if kit == "kit_case.md" else [
                k for k in parse_key_headers(files[sealed], sealed)[0] if k != "case"]
            missing = [k for k in ids if k not in topics]
            if missing:
                problems.append("%s: Listening has no line for %s (one line per topic: '%s | points: …')"
                                % (kit, ", ".join(missing), missing[0]))
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


def lint_round(files, plan=None, kits_required=True, standards=None, candidates=False):
    """Lint a written round ({file name: text}) against the rulebook: {"blocking": [...],
    "review": [...], "notes": [...]}. Key headers are checked separately (check_key_headers).
    `candidates`: the checker has run, so the listening candidates in the kits are looked at
    too (before it, the author's "Listening" sections hold only their topic lines)."""
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
    if candidates:
        lint["review"] += listening_findings(files, plan)
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
        n8 = sum(1 for r in lint["review"] if r["file"] == name and r["rule"] == 8)
        if n6:
            lines.append("%s: time anchors look mixed in %d place%s (references/standards.md, rule 6)"
                         % (name, n6, "" if n6 == 1 else "s"))
        if n8:
            lines.append("%s: the listening candidates of %d topic%s are not three episodes in form "
                         "(references/standards.md, rule 8)" % (name, n8, "" if n8 == 1 else "s"))
    return lines


def lint_summary(lint, details=None):
    out = {"abbreviations": sum(1 for r in lint["review"] if r["rule"] == 5),
           "time_anchors": sum(1 for r in lint["review"] if r["rule"] == 6)}
    if any(r["rule"] == 8 for r in lint["review"]):
        out["listening"] = sum(1 for r in lint["review"] if r["rule"] == 8)
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
              6: "Rule 6: more than one time anchor in one case or question",
              8: "Rule 8: listening candidates that are not three episodes in form (for the checker, "
                 "evidence_check.md §6; the author changes nothing here)"}
    lines = ["# Lint: judgement calls (references/standards.md)", "",
             "Sealed like the keys: this file names content. Only the author reads it.",
             "Each line is a heuristic's finding: correct the text where the rule is broken, leave it "
             "where the finding is wrong.", ""]
    for rule in (5, 6, 8):
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
# Every file there has a fixed name: WORK_FILES (above, with the command tables) says which
# command writes each and who reads it.
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
CLOSE_FROM_FILE = "close_from.json"     # written by close: the round as it stood before its reflection (close can run again)
OLD_WORK_FILES = ("before_save.json", "before_close.json")      # what 5.0 kept to run save and close again
VERIFY_FILE = "verify.json"
TIMES_FILE = "times.json"               # written by every step of a round: when it happened (issue #47)
PUBLISH_DIR = "publish"
PUBLISH_FILE = "publish.json"
EARLIER_DIR = "earlier"
# what one round leaves in the work folder, and what a whole job leaves
ROUND_FILES = PREPARED_FILES + (ANSWERS_FILE, STAGE2_FILE, FEEDBACK_QUESTIONS_FILE, FEEDBACK_FILE, ROUND_FILE,
                                RECORD_FILE, REFLECTION_FILE, PART_A_FILE, PART_B_FILE, CLOSE_FROM_FILE,
                                VERIFY_FILE, PLAN_FILE, TIMES_FILE, NEXT_DIR) + OLD_WORK_FILES
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
    return migrate_profile(st), path


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
    migrate_profile(st)
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
        for name in (PUBLISH_DIR, CLOSE_FROM_FILE, VERIFY_FILE) + OLD_WORK_FILES:
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


# ---------------------------------------------------------------- the round's clock (issue #47)
#
# Nobody types a time. Every command of a round that the protocol already runs notes when it
# ran in <work>/times.json: `start` (the learner asked for a round; with a prepared round the
# first part goes out with it), `present` of the first part (a round written now: it goes out
# then), `answer` (a message from the learner arrived), `save` and `close` (the reflection
# arrived). What the assistant sent in between is timed by the file it writes "exactly as
# sent" straight after sending (feedback_questions.md, stage2.md, feedback.md): the next
# command notes the file's own time, once. `sent` sets such a time by hand, and `--at` gives
# any of these commands another time than now (tests, a step filed late).

SENT_PARTS = ("questions", "questions_feedback", "case", "stage2", "feedback", "close")
SENT_FILES = (("questions_feedback", FEEDBACK_QUESTIONS_FILE), ("stage2", STAGE2_FILE), ("feedback", FEEDBACK_FILE))


def stamp_time(at):
    """The time a stamp gets: now, or `--at` (which must be an ISO time)."""
    if at is None:
        return now_ts()
    t = parse_stamp(at)
    if not t:
        die("--at must be an ISO time such as 2026-11-26T08:15:00Z, not %r" % at)
    return t.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_times(work):
    path = os.path.join(work, TIMES_FILE)
    try:
        doc = load_json(path) if os.path.isfile(path) else {}
    except CmeError:
        doc = {}
    doc = doc if isinstance(doc, dict) else {}
    if not isinstance(doc.get("stamps"), list):
        doc["stamps"] = []
    return doc


def note_sent_files(work, doc, before=None):
    """Note, once each, when the messages filed "exactly as sent" went out: the file's own
    time (never later than `before`, the step being stamped now), with its length in words."""
    have = {e.get("what") for e in doc["stamps"]}
    for part, name in SENT_FILES:
        path = in_work(work, name)
        if not path or "sent:" + part in have:
            continue
        t = dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc).replace(microsecond=0)
        limit = parse_stamp(before) if before else None
        if limit and t > limit:
            t = limit
        doc["stamps"].append({"what": "sent:" + part, "at": t.isoformat().replace("+00:00", "Z"),
                              "words": len(read_text(path).split()), "from": name})


def stamped(work, what, at=None, once=False):
    """The work folder's times with step `what` noted (now, or at `at`), and when the files
    written as sent went out; not written yet (a command that fails leaves no trace). `once`:
    a step that is run again keeps its first time. With `--at` the sent files are not timed by
    their own clock: use `sent --at`."""
    doc = read_times(work)
    when = stamp_time(at)
    if at is None:
        note_sent_files(work, doc, when)
    if not (once and any(e.get("what") == what for e in doc["stamps"])):
        doc["stamps"].append({"what": what, "at": when})
    return doc


def stamp(work, what, at=None, once=False):
    """Note step `what` in the work folder's times.json; returns the time it has there."""
    doc = stamped(work, what, at, once)
    save_json(doc, os.path.join(work, TIMES_FILE))
    return [e["at"] for e in doc["stamps"] if e.get("what") == what][0 if once else -1]


def start_times(work, session, first_block, sent, at=None):
    """A round starts: a new times.json for it. `first_block`: the part that goes out first;
    `sent`: it goes out with this very command (a prepared round)."""
    when = stamp_time(at)
    stamps = [{"what": "start", "at": when}] + ([{"what": "sent:" + first_block, "at": when}] if sent else [])
    save_json({"session": session, "first_block": first_block, "stamps": stamps}, os.path.join(work, TIMES_FILE))
    return when


def measured_time(doc, sid):
    """The round's measured time (round_timing) from the work folder's stamps `doc`, or None
    when they are not this round's (a reflection given in a later session) or no answer was
    filed as the round went (nothing then says when the learner's messages arrived)."""
    if not sid or doc.get("session") != sid:
        return None
    if not any(str(e.get("what")).startswith("answer:") for e in doc["stamps"]):
        return None
    return round_timing(doc["stamps"])


def cmd_sent(args):
    """Note when a message went out, for a part the engine cannot time itself (no file written
    as sent, or the file written late). Replaces the time taken from the file."""
    if not os.path.isdir(args.work):
        die("work folder not found: %s" % args.work)
    doc = read_times(args.work)
    what = "sent:" + args.part
    doc["stamps"] = [e for e in doc["stamps"] if e.get("what") != what]
    e = {"what": what, "at": stamp_time(args.at)}
    name = dict(SENT_FILES).get(args.part)
    if name and in_work(args.work, name):
        e["words"] = len(read_text(in_work(args.work, name)).split())
    doc["stamps"].append(e)
    save_json(doc, os.path.join(args.work, TIMES_FILE))
    print(json.dumps({"ok": True, "sent": args.part, "at": e["at"]}, ensure_ascii=False))


def answer_blocks(path):
    """[(part, text)] of an answers file, in the order they were added."""
    if not path or not os.path.isfile(path):
        return []
    return [(name, body.strip()) for name, body in ANSWER_RE.findall(read_text(path))]


def part_keys(work, part):
    """The key headers of the items whose answers `part` completes, in the order written, with
    their rubrics and the ledger they are graded against: (headers, rubrics, ledger), or None.
    Only for a part whose sealed file may now be opened: the questions, and the case once its
    last answer is in (`case` for a one-step case, `final` for an unfolding one)."""
    name = {"questions": SEALED_FILES[0], "final": SEALED_FILES[1], "case": SEALED_FILES[1]}.get(part)
    sealed, info = in_work(work, name) if name else None, work_info(work)
    if not sealed or not info:
        return None
    if part == "case":
        plan_path = in_work(work, PLAN_FILE)
        fmt = (load_json(plan_path) if plan_path else {}).get("case_format")
        if fmt != "discriminate":       # an unfolding case stays sealed until its final answers
            return None
    try:
        st, _ = current_ledger(work, info)
        text = read_text(sealed)
        headers = parse_key_headers(text, name)[0]
        rubrics = parse_rubrics(text, name)[0]
    except (CmeError, OSError):
        return None
    headers = {k: h for k, h in headers.items() if not h.get("_bad") and (k == "case") == (name == SEALED_FILES[1])}
    return headers, rubrics, st


def answer_depth(work, part, today=None, keys=None):
    """What the examiner grades with for each item whose answers this part completes, by key id:
    its evidence depth ({"Q1": {"level", "name", "in_a_row"}}, feedback_guide.md §4.1) and the
    learner's position notes on its topic ({"Q1": [{"id", "point", "text", "set"}]},
    standards.md rule 12). Read from the key headers and the ledger as it stands before the
    round is recorded. Returns (depth, positions), each None where there is nothing to say (no
    job open here, no key headers, the ladder turned off, no note): filing an answer never
    fails over it."""
    keys = keys or part_keys(work, part)
    if not keys:
        return None, None
    headers, _, st = keys
    out, notes = {}, {}
    for kid, h in headers.items():
        d = evidence_depth(st, h.get("topic"), h.get("aspect"), bool(h.get("retests")))
        if d:
            out[kid] = d
        held = standing_positions(st, today or dt.date.today(), h.get("topic")) if h.get("topic") else []
        if held:
            notes[kid] = [position_for_round(p) for p in held]
    return out or None, notes or None


# ---------------------------------------------------------------- the grading and reflection forms
#
# When a part's answers are in, `answer` writes the form the examiner fills: round.json with one
# entry per key id, everything the author and the ledger already know filled in (topic, type,
# aspect, retests, the evidence depth, the position notes, the rubric's elements), and blanks for
# what only grading decides (marks, score, confidence, coding). `_form` holds how to fill it and
# the allowed codes, from the engine's own lists; `save` takes the scaffolding off again
# (round_from_form). The reflection form is written the same way when the reflection arrives.
# A form never overwrites what the examiner has filled: a part answered again adds only the
# items that are not there yet.

FORM_KEY = "_form"
FORM_GIVEN = "given"            # per item: what the engine knows and the examiner reads, not edits
GAP_SOURCES = ("graded", "transfer", "misconception")      # `self` is the reflection's (self_gaps)


def grading_codes():
    """The codes allowed where a code is chosen, from the engine's own lists."""
    return {
        "mastery": "0-5, halves allowed",
        "confidence": list(CONFIDENCE_LEVELS) + ["null (the learner gave none)"],
        "rubric_mark": list(RUBRIC_MARKS),
        "art": {k: "0-%d, %s" % (v, ART_LABELS[k]) for k, v in ART_MAX.items()},
        "idea": {k: "0-%d" % v for k, v in IDEA_MAX.items()},
        "error_category": list(ERROR_CATEGORIES),
        "knowledge_type": list(KNOWLEDGE_TYPES),
        "severity": list(SEVERITIES),
        "bias": list(BIASES) + ["other:<name>"],
        "gap_source": list(GAP_SOURCES),
        "drill_result": list(DRILL_RESULTS),
        "dispute_outcome": list(DISPUTE_OUTCOMES),
        "aspect": list(FOCUSED_ASPECTS),
    }


def grading_guide(listening):
    """`_form` of the grading form: how to fill it, the codes and the shape of each list entry."""
    how = [
        "Fill this file in place; `save` reads it. Values already filled come from the key headers "
        "and the ledger: change one only to correct the author (it is reported as overridden).",
        "Marks before text: before any prepared text is used, mark every rubric element hit, partial or "
        "missed against the checked evidence, with the learner's own words that earned the mark in "
        "`quote` (for a missed element: empty, or what they wrote instead) and a short `note`; for an MCQ "
        "`correct` and `confidence` as the learner gave it (null when none). Then run `draft` for the "
        "part: it puts the prepared text your marks call for into the feedback's order "
        "(feedback_guide.md section 9).",
        "Each item: `mastery` (a focused question and the case by feedback_guide.md section 2; an MCQ "
        "4-5 correct with sound reasoning, 3 correct with flawed reasoning, 1-2 wrong).",
        "`given` is what grading uses and nobody edits: `depth`, how far behind the recommendation the "
        "feedback goes (feedback_guide.md section 4.1), and `positions`, the learner's position notes "
        "on the topic (standards.md rule 12).",
        "Coding (feedback_guide.md section 11): `art` for the case and a focused question (a focused "
        "question scores only the domains it tested: leave the others null), `idea` for the case only, "
        "and one entry in `errors` for every rubric element marked missed or partial and for a wrong MCQ.",
        "`retests`: keep it only when the item asked about the gap's decision point; set it to null "
        "when it did not. Only such an item can close the gap.",
        "Round: `gaps`, one per topic with something to retest, written precisely enough to retest and "
        "carrying forward what is still open; `resolved`, a prior gap closed this time; `key_learning`, "
        "one-line teaching points; `grade_changes`, each dispute settled (also an upheld one); `errata`, a correction "
        "to an earlier round.",
        "`reading`: the Further reading pointers of the feedback, at most two; `listening` (when "
        "present): the Listening picks, one per topic. Empty lists when the feedback gave none.",
        "Leave out `reflection` and every time: `save` fills title, summary, tags, the compact case, "
        "the selection reasons and the round's times.",
    ]
    shapes = {
        "error": {"element": "what was missed, one line", "stage": "1 or 2 (case only)",
                  "category": "error_category", "knowledge_type": "for a knowledge error",
                  "art_domain": "one of art", "bias": ["bias"], "bias_evidence": "the learner's words, with a bias",
                  "severity": "severity", "confidence": "the learner's confidence on it"},
        "gap": {"topic": "<blueprint ID>", "gap": "the decision point, the rule, what the learner did",
                "source": "gap_source"},
        "resolved": {"topic": "<blueprint ID>", "note": "what was closed this time"},
        "grade_change": {"item": "Q2", "topic": "<blueprint ID>", "from": 3, "to": 3.5,
                         "outcome": "dispute_outcome"},
        "erratum": {"corrects": "<session ID>", "point": "…", "correction": "…", "source": "…"},
        "reading": {"topic": "<blueprint ID>", "title": "the document, with its year", "link": "https://…",
                    "section": "the section to read", "minutes": 8, "why": "one line"},
    }
    if listening:
        shapes["listening"] = {"topic": "<blueprint ID>", "link": "https://open.spotify.com/episode/<22 letters "
                               "and digits>", "show": "…", "title": "…", "minutes": 52, "why": "one line",
                               "source": "kit or search"}
    return {"how": how, "codes": grading_codes(), "shapes": shapes}


def form_item(kid, h, rubric, depth=None, positions=None):
    """One entry of the grading form for the item of key `kid`."""
    typ = h.get("type")
    it = {"key": kid, "type": typ, "topic": h.get("topic"), "label": h.get("label")}
    if typ == "focused":
        it["aspect"] = h.get("aspect")
    if h.get("retests"):
        it["retests"] = h["retests"]
    given = dict(({"depth": depth} if depth else {}), **({"positions": positions} if positions else {}))
    if given:
        it[FORM_GIVEN] = given
    if typ in RUBRIC_TYPES:
        it["rubric"] = [dict({"id": "%s.%d" % (kid, n)}, **dict(e, mark=None, quote="", note=""))
                        for n, e in enumerate(rubric or [], 1)]
    it["mastery"] = None
    if typ == "mcq":
        it["correct"] = None
    it["confidence"] = None
    coding = {}
    if typ in RUBRIC_TYPES:
        coding["art"] = {k: None for k in ART_MAX}
    if typ == "case":
        coding["idea"] = {k: None for k in IDEA_MAX}
    coding["errors"] = []
    it["coding"] = coding
    return it


def write_grading_form(work, part, today=None, keys=None):
    """Write or extend the grading form, W/round.json, with the items whose answers `part`
    completes. Returns what `answer` prints about it, or None when there is no form to write."""
    keys = keys or part_keys(work, part)
    if not keys or not keys[0]:
        return None
    headers, rubrics, st = keys
    depth, positions = answer_depth(work, part, today, keys)
    path = os.path.join(work, ROUND_FILE)
    rnd = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                rnd = json.load(fh)
        except (OSError, ValueError):
            return {"file": ROUND_FILE, "kept": "round.json is not valid JSON: it was left as it is"}
        if not isinstance(rnd, dict) or any(isinstance(it, dict) and not it.get("key")
                                            for it in rnd.get("items") or []):
            return {"file": ROUND_FILE, "kept": "round.json was written out in full: it was left as it is"}
    items = rnd.get("items") if isinstance(rnd.get("items"), list) else []
    have = {key_id(it.get("key")) for it in items if isinstance(it, dict)}
    added = []
    for kid, h in headers.items():
        if kid not in have:
            items.append(form_item(kid, h, rubrics.get(kid), (depth or {}).get(kid), (positions or {}).get(kid)))
            added.append(kid)
    listening = listening_on(st)
    form = {FORM_KEY: grading_guide(listening)}
    for k, v in rnd.items():
        if k != FORM_KEY:
            form[k] = v
    form["items"] = items
    for k in ("gaps", "resolved", "key_learning", "grade_changes", "errata", "reading"):
        form.setdefault(k, [])
    if listening:
        form.setdefault("listening", [])
    if st.get("pending_errata"):
        form.setdefault("pending_errata_logged", "all")
    plan_path = in_work(work, PLAN_FILE)
    plan = (load_json(plan_path) if plan_path else None) or {}
    for c in plan.get("items") or []:       # the drill sits on the case, or on the first focused question
        target = "case" if c.get("slot") == "case" else "focused" if c.get("slot") == "focused" else None
        if c.get("drill") and target and not form.get("drill") \
                and any(h.get("type") == target for h in headers.values()):
            form["drill"] = {"code": c["drill"].get("code"), "result": None}
    save_json(form, path)
    out = {"file": ROUND_FILE, "added": added,
           "draft": "case" if part in ("case", "final") else "questions"}     # once marked: `draft --part`
    missing = [k for k in added if headers[k].get("type") in RUBRIC_TYPES and not rubrics.get(k)]
    if missing:
        out["rubric_missing"] = missing      # a round written before rubric blocks: mark the key's own list
    return out


def round_from_form(rnd):
    """The grading form as the examiner filled it, as `save` records it: the scaffolding taken
    off (`_form`, `given`, scores left null in a focused question's ART), the rubric's marks
    checked against the coding. Stops when a score is still blank. Returns warnings."""
    rnd.pop(FORM_KEY, None)
    warnings, blank = [], []
    for n, it in enumerate(rnd.get("items") or [], 1):
        if not isinstance(it, dict):
            continue
        name = it.get("key") or "item %d" % n
        it.pop(FORM_GIVEN, None)
        if "mastery" in it and it["mastery"] is None:
            blank.append("%s mastery" % name)
        if it.get("type") == "mcq" and "correct" in it and it["correct"] is None:
            blank.append("%s correct" % name)
        if "confidence" in it and it["confidence"] is None:
            del it["confidence"]
        coding = it.get("coding")
        if isinstance(coding, dict):
            for part in ("art", "idea"):
                scores = coding.get(part)
                if isinstance(scores, dict):
                    left = [k for k, v in scores.items() if v is None]
                    if left and it.get("type") == "case":
                        warnings.append("%s: %s not scored: %s" % (name, part, ", ".join(left)))
                    coding[part] = {k: v for k, v in scores.items() if v is not None}
                    if not coding[part]:
                        del coding[part]
        rubric = it.get("rubric")
        if isinstance(rubric, list) and rubric:
            marks = [e.get("mark") if isinstance(e, dict) else None for e in rubric]
            unmarked = sum(1 for m in marks if m not in RUBRIC_MARKS)
            if unmarked:
                warnings.append("%s: %d rubric element(s) not marked %s" % (name, unmarked, " / ".join(RUBRIC_MARKS)))
            unquoted = sum(1 for e in rubric if isinstance(e, dict) and e.get("mark") in ("hit", "partial")
                           and not str(e.get("quote") or "").strip())
            if unquoted:
                warnings.append("%s: %d rubric element(s) marked hit or partial without the learner's words in "
                                "`quote` (feedback_guide.md section 9.1)" % (name, unquoted))
            short = sum(1 for m in marks if m in ("partial", "missed"))
            errors = len(((coding or {}).get("errors") or []) if isinstance(coding, dict) else [])
            if short > errors:
                warnings.append("%s: %d rubric element(s) missed or partial but %d error record(s): one error "
                                "per element (feedback_guide.md section 11.3)" % (name, short, errors))
    if rnd.get("drill") and isinstance(rnd["drill"], dict) and rnd["drill"].get("result") is None:
        blank.append("drill result")
    if blank:
        die("the grading form in round.json is not filled in: %s. Fill it in and run save again. Nothing "
            "was recorded." % ", ".join(blank))
    return warnings


# ---------------------------------------------------------------- the draft: prepared text by the marks
#
# ADR 0009: the feedback is assembled from text written and source-checked when the round was
# prepared (the kits' blocks, rule 8) and adapted live to the answer. Once the examiner has marked
# the grading form, `draft` puts the blocks the marks call for into the feedback's order, with the
# rubric as marked and the parts only the answer can prompt left as [live: …]. The examiner
# writes those, rewrites or drops any block, and sends the result. `save` then compares the
# blocks offered with the feedback as sent and records, in the session document only, which were
# used as prepared, changed or left out (prepared_feedback).

DRAFT_FILES = {"questions": "draft_questions.md", "final": "draft.md"}
DRAFT_SENT = {"draft_questions.md": FEEDBACK_QUESTIONS_FILE, "draft.md": FEEDBACK_FILE}
DRAFT_PARTS = ("questions", "case", "all")
MARK_SIGNS = {"hit": "\u2713", "partial": "\u25d0", "missed": "\u2717"}
VERIFY_MARK_RE = re.compile(r"[ \t]*\(verify\)", re.I)
BLOCKS_LINE_RE = re.compile(r"^[ \t>*_`-]*Blocks[ \t*_`]*:[ \t*_`]*(.*)$", re.M | re.I)
BLOCK_REF_RE = re.compile(r"\b(Q[1-9][0-9]?|case)(?:\.(\d+))?[ \t]+([a-z]+)\b", re.I)
LEFTOVER_RE = re.compile(r"<!--\s*/?\s*(?:block|draft|notes|check)\b|\[live:", re.I)


def live(what):
    return "[live: %s]" % what


def evidence_flags(text):
    """{block id: [(claim number, status)]} for the claims of an evidence file that are not
    confirmed and name the prepared blocks that state them (`**Blocks:**`, evidence_check.md §4)."""
    flags = {}
    text = text or ""
    starts = list(EVIDENCE_BLOCK_RE.finditer(text))
    for i, m in enumerate(starts):
        block = text[m.start():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        status = STATUS_RE.search(block)
        refs = BLOCKS_LINE_RE.search(block)
        if not status or not refs:
            continue
        st = status.group(1).strip(" \t*_`").lower()
        if st.startswith("confirmed"):
            continue
        n = re.match(r"#{2,4}[ \t]+(\d+)", m.group(0))
        for kid, el, kind in BLOCK_REF_RE.findall(refs.group(1)):
            flags.setdefault(block_id(key_id(kid), int(el) if el else None, kind.lower()), []).append(
                (n.group(1) if n else "?", st.split(".")[0][:40]))
    return flags


def rubric_lines(rubric):
    """The rubric as the learner sees it every time: element, mark, and the words that earned it."""
    lines, stage = ["**Rubric**"], None
    for e in rubric or []:
        if not isinstance(e, dict):
            continue
        if e.get("stage") and e["stage"] != stage:
            stage = e["stage"]
            lines.append("Stage %d" % stage)
        mark, quote = e.get("mark"), str(e.get("quote") or "").strip().strip('"\u201c\u201d')
        words = ('"%s"' % quote if quote else "not in your answer" if mark == "missed"
                 else live("the learner's words that earned the mark"))
        lines.append("- %s %s \u2014 %s" % (MARK_SIGNS.get(mark, "?"), e.get("element"), words))
    return lines


def answered_well_today(it):
    """Does the item get its `deeper` block: answered well by its marks (feedback_guide.md §4.1)?"""
    if it.get("type") == "mcq":
        return it.get("correct") is True and it.get("confidence") not in ("unsure", "guess")
    marks = [e.get("mark") for e in it.get("rubric") or [] if isinstance(e, dict)]
    mastery = it.get("mastery")
    return "missed" not in marks and (mastery is None or mastery >= 4)


def draft_item(it, blocks, flags, used):
    """The draft of one item's feedback, in the order of feedback_guide.md §2."""
    kid, typ = it.get("key"), it.get("type")
    out = []

    def put(kind, n=None):
        bid = block_id(kid, n, kind)
        text = blocks.get(bid)
        if not text:
            out.append(live("no prepared text for %s: write it from the checked evidence" % bid))
            return
        for claim, status in flags.get(bid, []):
            out.append("<!-- check: claim %s of the evidence file is %s: correct or qualify it here -->"
                       % (claim, status))
        out.extend(["<!-- block: %s -->" % bid, VERIFY_MARK_RE.sub("", text), "<!-- /block -->"])
        used.append(bid)

    title = {"mcq": "**%s**" % kid, "focused": "**%s (focused)**" % kid, "case": "**Case**"}.get(typ, kid)
    out.append(title)
    given = it.get(FORM_GIVEN) or {}
    for p in given.get("positions") or []:
        out.append(live("the learner holds a position on \"%s\": an answer that follows it is no miss, and "
                        "the feedback does not reopen it" % p.get("point")))
    deep = (given.get("depth") or {}).get("level", 1) > 1 and answered_well_today(it)
    if typ == "mcq":
        out.append(live("the correct letter, the learner's answer and the verdict, opening with their own words"))
        put("model")
        put("distractors")
        put("hit" if answered_well_today(it) else "missed")
    else:
        out.extend(rubric_lines(it.get("rubric")))
        if not it.get("rubric"):
            out.append(live("no rubric block in the key: mark the elements the key holds"))
        out.append(live("the verdict and the mastery score, opening with the learner's own words"))
        put("model")
        if typ == "focused":
            put("decisive")
        for n, e in enumerate(it.get("rubric") or [], 1):
            if isinstance(e, dict) and e.get("mark") in RUBRIC_MARKS:
                put(e["mark"], n)
        if typ == "case":
            put("differential")
    if deep:
        put(BLOCK_DEEPER)
    if typ == "case":
        put("pearls")
    if typ != "mcq":
        out.append(live("credit for anything defensible outside the key; where the evidence differs from "
                        "the key, say so and correct it"))
    return out


def write_draft(work, part):
    """Write the draft of one feedback message (DRAFT_FILES) from the marked grading form and
    the kits' blocks. Returns what `draft` prints: file, blocks used, live parts, flags."""
    path = in_work(work, ROUND_FILE)
    rnd = load_json(path) if path else None
    if not isinstance(rnd, dict) or not isinstance(rnd.get("items"), list):
        die("draft needs the grading form, %s, as `answer` wrote it: file the answers first" % ROUND_FILE)
    sealed = [p for p in (in_work(work, n) for n in SEALED_FILES) if p]
    headers = key_headers(sealed)[0] if sealed else {}
    items = []
    for it in rnd["items"]:
        if not isinstance(it, dict) or not it.get("key"):
            continue
        it = dict(it, key=key_id(it["key"]))
        it.setdefault("type", (headers.get(it["key"]) or {}).get("type") or ("case" if it["key"] == "case" else None))
        if part == "all" or (it.get("type") == "case") == (part == "case"):
            items.append(it)
    if not items:
        die("the grading form has no %s to draft: file that part's last answers first" %
            ("case" if part == "case" else "items" if part == "all" else "short questions"))
    unmarked = []
    for it in items:
        if it.get("type") == "mcq" and it.get("correct") is None:
            unmarked.append("%s correct" % it["key"])
        left = sum(1 for e in it.get("rubric") or [] if not isinstance(e, dict) or e.get("mark") not in RUBRIC_MARKS)
        if left:
            unmarked.append("%s: %d rubric element(s)" % (it["key"], left))
    if unmarked:
        die("marks before text: mark the grading form first (%s); then run draft again" % "; ".join(unmarked))
    plan_path = in_work(work, PLAN_FILE)
    plan = (load_json(plan_path) if plan_path else None) or {}
    has_case = bool((plan.get("counts") or {}).get("case")) if plan.get("counts") else bool(in_work(work, SEALED_FILES[1]))
    final = part != "questions" or not has_case
    blocks, flags, contradicted = {}, {}, 0
    for sealed, kit in KIT_FOR.items():
        kp = in_work(work, kit)
        if kp:
            blocks.update(parse_blocks(read_text(kp), kit)[0])
        ep = in_work(work, EVIDENCE_FOR[sealed])
        if ep:
            text = read_text(ep)
            for k, v in evidence_flags(text).items():
                flags.setdefault(k, []).extend(v)
            contradicted += contradicted_keys(text) or 0
    name = DRAFT_FILES["final" if final else "questions"]
    used, lines = [], ["<!-- draft: prepared text chosen by your marks. Write each [live: ...] part, rewrite or "
                       "drop any block the answer calls for, then send it without these comment lines "
                       "(feedback_guide.md section 9). -->"]
    if contradicted:
        lines.append("<!-- check: the evidence check found %d key(s) contradicted: grade against the "
                     "guidance, and correct the key and its blocks -->" % contradicted)
    glossary = len(lines)
    lines.append("")
    for it in items:                                    # A. the reveal, for every item of the part
        bid = block_id(it["key"], None, "reveal")
        if blocks.get(bid):
            lines += ["<!-- block: %s -->" % bid, VERIFY_MARK_RE.sub("", blocks[bid]), "<!-- /block -->"]
            used.append(bid)
        else:
            lines.append(live("the reveal of %s: its topic and why it was chosen" % it["key"]))
    order = {"mcq": 0, "focused": 1, "case": 2}
    if part == "all" and (plan.get("item_order") or rnd.get("item_order")) == "case_first":
        order["case"] = -1
    for it in sorted(items, key=lambda x: order.get(x.get("type"), 3)):
        lines += [""] + draft_item(it, blocks, flags, used)
    lines.append("")
    if not final:
        lines.append(live("one line on the score so far") + " The case follows.")
    else:
        lines.append(live("the gap summary for the whole round: new gaps, prior gaps re-tested, transfer, "
                          "calibration, mastery 0-5 per topic with a one-line reason, the coding line"))
        reading_kit = "kit_case.md" if in_work(work, "kit_case.md") else "kit_questions.md"
        kp = in_work(work, reading_kit)
        body = kit_section(read_text(kp), KIT_READING) if kp else None
        if body and body.strip():
            lines += ["<!-- notes: Reading -->", VERIFY_MARK_RE.sub("", body.strip()), "<!-- /notes -->"]
        lines.append(live("Further reading: at most two pointers, from the notes above where they fit"))
        if "listening" in rnd:
            for kit in KIT_FOR.values():
                kp = in_work(work, kit)
                body = kit_section(read_text(kp), KIT_LISTENING) if kp else None
                if body and body.strip():
                    lines += ["<!-- notes: Listening -->", body.strip(), "<!-- /notes -->"]
            lines.append(live("Listening: one episode per topic, the candidate that matches the learner's gap"))
        lines.append(live("the reflection prompt"))
    common = common_abbreviations() or set()
    seen = []
    for b in used:
        for m in ABBREVIATION_RE.finditer(blocks.get(b) or ""):
            if m.group(1) not in common and not ROMAN_RE.match(m.group(1)) and m.group(1) not in seen:
                seen.append(m.group(1))
    lines.insert(glossary, live("the glossary line, \"Abbreviations: ...\", for the abbreviations this message "
                                "uses%s" % ("; the prepared text uses %s" % ", ".join(seen) if seen else "")))
    with open(os.path.join(work, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    out = {"ok": True, "file": name, "part": part, "final": final, "blocks": len(used),
           "sent_as": DRAFT_SENT[name], "live": sum(l.count("[live:") for l in lines)}
    missing = [l for l in lines if l.startswith("[live: no prepared text")]
    if missing:
        out["no_prepared_text"] = len(missing)
    if flags:
        out["checks"] = sum(1 for b in used if b in flags)
    return out


def cmd_draft(args):
    """Put together the draft of a feedback message from the marked grading form and the kits'
    prepared blocks (ADR 0009). Prints file name and counts only."""
    work, _ = job(args)
    print(json.dumps(write_draft(work, args.part), ensure_ascii=False))


def shingles(text, n=3):
    words = re.findall(r"[a-z0-9\u00c0-\u024f]+(?:[.,/-][a-z0-9]+)*", (text or "").lower())
    return {tuple(words[i:i + n]) for i in range(max(1, len(words) - n + 1))} if words else set()


def block_use(block, sent):
    """How a prepared block reached the feedback as sent: "as_prepared", "changed" or "discarded",
    by the share of its three-word runs that are in the message."""
    mine = shingles(VERIFY_MARK_RE.sub("", block))
    if not mine:
        return "as_prepared"
    share = len(mine & sent) / float(len(mine))
    return "as_prepared" if share >= 0.9 else "changed" if share >= 0.2 else "discarded"


def prepared_feedback(work, warnings):
    """What `save` records in the session document of the prepared text: the blocks each draft
    offered, sorted by how they reached the feedback as sent. None when no draft was made."""
    out, any_draft = {"offered": 0, "as_prepared": [], "changed": [], "discarded": []}, False
    for name, sent_name in DRAFT_SENT.items():
        dp = in_work(work, name)
        if not dp:
            continue
        any_draft = True
        sp = in_work(work, sent_name)
        if name == DRAFT_FILES["questions"] and not sp:
            sp = in_work(work, FEEDBACK_FILE)
        sent = shingles(read_text(sp)) if sp else set()
        for bid, text in parse_blocks(read_text(dp), name)[0].items():
            out["offered"] += 1
            out[block_use(text, sent)].append(bid)
    if not any_draft:
        if any(parse_blocks(read_text(p))[0] for p in (in_work(work, k) for k in KIT_FOR.values()) if p):
            warnings.append("the kits hold prepared blocks but no draft was made: mark the grading form, run "
                            "`draft`, and write the feedback from it (feedback_guide.md section 9)")
        return None
    return out


def reflection_guide(items, ask_sources):
    """`_form` of the reflection form."""
    how = [
        "Fill this file in place from the learner's reflection; `close` reads it. Skipped → set "
        "`skipped` true and leave the rest.",
        "`topic_comfort` 1-5 per topic as the learner rated it, `performance` 1-5, `solid` and `gaps` "
        "in the learner's words, `reading_minutes` the further reading they report (null when none).",
        "`self_gaps`: each shaky area as a precise gap on a blueprint ID (source self); an ID the "
        "blueprint lacks gets `domain` and `label` too.",
        "`grade_changes`: every dispute settled now, one entry each, also when the grade stands "
        "(`upheld`, `from` = `to`) and when the learner challenged a teaching point rather than a mark "
        "(the item's score as `from` and `to`, the outcome saying who was right); `items` (the item's "
        "new score and coding, matched by type and topic) only when a score changed. Not for a score "
        "the learner sets: that is `learner_scores`.",
        "`learner_scores` (\"record it as 4\"), `learner_closed_gaps` (\"close that gap\") and "
        "`learner_stops` (\"I know this, stop bringing it back\", with the position note when the "
        "learner gave one): only what the learner said, matched by topic, and by type where the round "
        "has two items on it (feedback_guide.md section 7).",
    ]
    if ask_sources:
        how.append("`podcast_sources`: the shows the learner named to trust or to avoid, if asked this "
                   "round; leave null when none were named.")
    how.append("With it, write B.md (session_log.md section 3): \"### Discussion (verbatim)\", \"### Grade "
               "changes\" (each dispute, from → to, the reason and the outcome; \"None.\" otherwise), "
               "\"### Coded analysis\" (from the `coding` of each item in record.json), \"### Errata\" only "
               "when there are any; `close` adds the reflection above them.")
    shapes = {
        "self_gap": {"topic": "<blueprint ID>", "gap": "…", "source": "self", "domain": "only for a new ID",
                     "label": "only for a new ID"},
        "grade_change": {"item": "Q2", "topic": "<blueprint ID>", "from": 3, "to": 3.5,
                         "outcome": list(DISPUTE_OUTCOMES)},
        "item": {"type": "case", "topic": "<blueprint ID>", "mastery": 3.5},
        "learner_score": {"item": "Q2", "type": "mcq", "topic": "<blueprint ID>", "score": 4,
                          "note": "the learner's words"},
        "learner_closed_gap": {"gap": "<gap ID>, or topic: <blueprint ID>", "note": "the learner's words"},
        "learner_stop": {"item": "Q3", "type": "focused", "topic": "<blueprint ID>",
                         "score": "%d unless the learner named one" % STOP_SCORE,
                         "position": {"point": "the one decision point", "text": "the learner's words"}},
    }
    if ask_sources:
        shapes["podcast_sources"] = {"trusted": ["show"], "avoid": ["show"]}
    return {"how": how, "round": items, "shapes": shapes}


def reflection_items(work, st):
    """The items the reflection is about: [{"item"?, "type", "topic", "label"}], from the round
    record of this job, otherwise from the unreflected session of the ledger."""
    rec = in_work(work, RECORD_FILE)
    try:
        rnd = load_json(rec) if rec else None
    except CmeError:
        rnd = None
    labels = bp_topics(st)
    out = []
    if rnd and rnd.get("log_id") == st.get("unreflected"):
        for it in rnd.get("items") or []:
            out.append(dict(({"item": it["key"]} if it.get("key") else {}), type=it.get("type"),
                            topic=it.get("topic"), label=it.get("label")))
        return out
    sess = next((s for s in st.get("sessions") or [] if s.get("id") == st.get("unreflected")), None)
    for it in (sess or {}).get("items") or []:
        out.append({"type": it.get("type"), "topic": it.get("topic"),
                    "label": ((labels.get(it.get("topic")) or {}).get("label")
                              or (st.get("topics", {}).get(it.get("topic")) or {}).get("label"))})
    return out


def write_reflection_form(work):
    """Write the reflection form, W/reflection.json, when the reflection arrives and there is none
    yet. Returns what `answer` prints about it, or None."""
    info = work_info(work)
    path = os.path.join(work, REFLECTION_FILE)
    if not info:
        return None
    if os.path.isfile(path):
        return {"file": REFLECTION_FILE, "kept": "reflection.json is already there: it was left as it is"}
    try:
        st, _ = current_ledger(work, info)
    except CmeError:
        return None
    if not st.get("unreflected"):
        return None
    items = reflection_items(work, st)
    ask = listening_status(st).get("ask_sources")
    form = {FORM_KEY: reflection_guide(items, ask),
            "topic_comfort": {it["topic"]: None for it in items if it.get("topic")},
            "performance": None, "solid": "", "gaps": "", "reading_minutes": None, "skipped": False,
            "self_gaps": [], "grade_changes": [], "items": [], "learner_scores": [], "learner_closed_gaps": [],
            "learner_stops": []}
    if ask:
        form["podcast_sources"] = None
    save_json(form, path)
    return {"file": REFLECTION_FILE, "session": st["unreflected"], "topics": len(form["topic_comfort"])}


def reflection_from_form(refl):
    """The reflection form as filled, as `close` applies it: the scaffolding and blanks taken off."""
    if not isinstance(refl, dict):
        return refl
    refl = dict(refl)
    refl.pop(FORM_KEY, None)
    if isinstance(refl.get("topic_comfort"), dict):
        refl["topic_comfort"] = {k: v for k, v in refl["topic_comfort"].items() if v is not None}
    for k in ("performance", "reading_minutes", "podcast_sources"):
        if k in refl and refl[k] is None:
            del refl[k]
    for k in ("solid", "gaps"):
        if refl.get(k) == "":
            del refl[k]
    stops = []
    for req in refl.get("learner_stops") or []:
        if isinstance(req, dict):
            req = {k: v for k, v in req.items() if v is not None}
            pos = req.get("position")
            if isinstance(pos, dict) and not any((pos.get(k) or "").strip() for k in ("point", "text")):
                del req["position"]
        stops.append(req)
    if "learner_stops" in refl:
        refl["learner_stops"] = stops
    return refl


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
    stamp_time(args.at)             # a bad --at stops here, before anything is written
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
        out["at"] = stamp(args.work, "answer:" + args.part, args.at)      # when the learner's message arrived
    out["parts"] = [name for name, _ in have]
    keys = part_keys(args.work, args.part)
    depth, positions = answer_depth(args.work, args.part, today_from(args), keys)
    if depth:
        out["depth"] = depth
    if positions:
        out["positions"] = positions
    # the form the examiner fills: the grading form once a part's answers are in, the
    # reflection form when the reflection arrives
    form = (write_reflection_form(args.work) if args.part == "reflection"
            else write_grading_form(args.work, args.part, today_from(args), keys))
    if form:
        out["form"] = form
    print(json.dumps(out, ensure_ascii=False))


def cmd_save(args):
    """First save after the feedback: record the round, the session document (part A) and the
    page file, in one go, into the publish set. Everything is found in the work folder by its fixed
    name. It starts from the current ledger (so a settings change made earlier in the same job is
    kept). Run again in the same job, it undoes the round it recorded and records it again
    (record_round with `again`), so it gives the same result."""
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
    again = None
    if has_session(cur, sid):
        again = next((s for s in cur["sessions"] if s.get("id") == sid), None)
        if (info.get("saved") or {}).get("session") != sid or again is not cur["sessions"][-1]:
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
    # the time so far, from the stamps (the reflection is still to come: `close` completes it)
    times = stamped(work, "save", args.at, once=True)
    measured = measured_time(times, sid)
    if measured:
        rnd.update(measured)
    # the grading form as filled (answer wrote it), without its scaffolding
    warnings.extend(round_from_form(rnd))
    # the round record: what the author wrote in the key headers + what the examiner graded
    plan_path = in_work(work, PLAN_FILE)
    keys = fill_round_from_keys(rnd, sealed, load_json(plan_path) if plan_path else None)
    if keys:
        warnings.extend(keys.pop("warnings"))
    reading = reading_pointers(rnd, warnings)       # after the keys: the items have their topics
    listening = listening_picks(rnd, warnings)
    if not feedback and not feedback_questions:
        die("save needs the feedback as sent: %s in the work folder" % FEEDBACK_FILE)
    st = cur
    gen_before = st.get("gen")
    if again is not None:
        repeat_write(st, info["saved"]["gen"])
    # the round mix set on the page is kept in the ledger from now on
    prefs_changes = apply_prefs(st, info.get("prefs"), warnings)
    md = assemble_part_a(sealed, answers, feedback,
                         rnd.get("item_order") or st["config"].get("item_order"), warnings,
                         feedback_questions, read_text(stage2) if stage2 else None)
    for label, path in (("questions' feedback", feedback_questions), ("final feedback", feedback),
                        ("Stage 2", stage2)):
        found = internal_terms(read_text(path)) if path else []
        if found:                   # plain language: logged as sent; next time, write it for the learner
            warnings.append("the %s as sent names the skill's own machinery (%s): feedback_guide.md "
                            "section 10.3" % (label, ", ".join(found)))
        if path and LEFTOVER_RE.search(read_text(path)):
            warnings.append("the %s as sent still holds the draft's comment lines or a [live: …] part: "
                            "logged as sent (feedback_guide.md section 9)" % label)
    adapted = prepared_feedback(work, warnings)
    res = record_round(st, copy.deepcopy(rnd), today, again)
    if again is None:               # before any file is written: a save interrupted after the ledger can run again
        info["saved"] = {"session": sid, "gen": [gen_before, st["gen"]]}
        save_json(info, os.path.join(work, WORK_FILE))
    doc = session_doc_a(rnd, sid, md)
    if measured:
        doc["minutes"], doc["timing"] = measured["minutes"], measured["timing"]
        res["minutes"], res["timing"] = measured["minutes"], measured["timing"]
    if reading is not None:
        doc["reading"] = reading
    if listening is not None:
        doc["listening"] = listening
    if adapted is not None:
        doc["prepared_feedback"] = adapted      # the log only: never in the feedback, never in the ledger
    rec = {}
    path = publish_ledger(work, info, st, rec, session=doc, empty_prepared=True)
    rec = report(path, os.path.getsize(path), dict(res, **rec))
    with open(os.path.join(work, PART_A_FILE), "w", encoding="utf-8") as fh:
        fh.write(md)
    if prefs_changes:
        rec["page_settings_applied"] = prefs_changes
    if keys:
        rec["keys"] = keys
    if reading is not None:
        rec["reading"] = len(reading)
    if listening is not None:
        rec["listening"] = len(listening)
    if adapted is not None:
        rec["prepared_feedback"] = {k: (v if isinstance(v, int) else len(v)) for k, v in adapted.items()}
    save_json(rnd, os.path.join(work, RECORD_FILE))     # the round record as recorded, beside round.json
    if times.get("session") == sid:
        save_json(times, os.path.join(work, TIMES_FILE))
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
    frm = in_work(work, CLOSE_FROM_FILE)
    again = load_json(frm) if not st.get("unreflected") and info.get("closed") and frm else None
    if again:                       # run again after a correction: the round as it stood before its reflection
        sid = again["session"]
        sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
        if sess != again["entry"]:
            die("round %s was changed after its close (override): close cannot run again; a further change "
                "goes in with override" % sid)
        base = again["round"]
        repeat_write(st, again["gen"])
    else:
        sid = args.session or st.get("unreflected")
        sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
        if not sess or sid != st.get("unreflected"):
            die("no unreflected session to update (last: %s)" % (st["sessions"][-1].get("id") if st["sessions"] else None))
        base = round_from_entry(st, sess)
    gen_before = st.get("gen")
    times = stamped(work, "close", args.at, once=True)      # the reflection arrived: the round's clock stops
    measured = measured_time(times, sid)
    refl = reflection_from_form(load_json_arg(reflection) or {})       # the reflection form, without its scaffolding
    res = reflect_round(st, refl, today, sid, measured, base)
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
    # the podcast sources are asked for once, in the first Listening section: what the learner
    # answered is in the reflection; no answer is kept as "none named", so it is not asked again
    if refl.get("podcast_sources") is not None:
        st["profile"]["podcast_sources"] = podcast_sources(refl["podcast_sources"], "reflection podcast_sources")
        res["podcast_sources"] = st["profile"]["podcast_sources"]
    elif st["profile"].get("podcast_sources") is None and "listening" in doc:
        st["profile"]["podcast_sources"] = podcast_sources(None)
    doc["closing"] = md_b
    doc["reflected"] = True
    doc.pop("learner_changes", None)        # close can run again: only this run's count
    if res.get("learner_changes"):          # in the log whoever wrote part B: both scores, who closed the gap
        doc["learner_changes"] = res["learner_changes"]
        doc["closing"] = md_b.rstrip() + "\n\n" + learner_changes_md(res["learner_changes"], "### Set by the learner")
    sess = next((s for s in st["sessions"] if s.get("id") == sid), None)
    if sess and isinstance(sess.get("score"), (int, float)):
        doc["score"] = sess["score"]
    if sess and isinstance(sess.get("timing"), dict):
        doc["minutes"], doc["timing"] = sess.get("minutes"), sess["timing"]
        res["minutes"], res["timing"] = sess.get("minutes"), sess["timing"]
    hint = time_hint(st)
    if hint:
        res["time_hint"] = hint["text"]             # one line of the closing message
    ref = {}
    path = publish_ledger(work, info, st, ref, session=doc)
    page_warn = ref.pop("warnings", [])
    ref = report(path, os.path.getsize(path), dict(res, **ref))
    ref["warnings"] = list(ref.get("warnings") or []) + page_warn
    save_json({"session": sid, "round": base, "gen": [gen_before, st["gen"]],
               "entry": next(s for s in st["sessions"] if s.get("id") == sid)}, os.path.join(work, CLOSE_FROM_FILE))
    info["closed"] = sid
    save_json(info, os.path.join(work, WORK_FILE))
    if times.get("session") == sid:
        save_json(times, os.path.join(work, TIMES_FILE))
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
    lists = {"sessions": [], "reviews": [], "library": []}
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


def build_parser():
    """The command line: every command with its options (the table of them: COMMANDS)."""
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
    s = command("sent", cmd_sent); s.add_argument("--part", required=True, choices=SENT_PARTS)
    s = command("present", cmd_present, work=False); s.add_argument("files", nargs="*"); s.add_argument("--work")
    s.add_argument("--block", required=True)
    s = command("draft", cmd_draft); s.add_argument("--part", required=True, choices=DRAFT_PARTS)
    s = command("save", cmd_save)
    s = command("close", cmd_close); s.add_argument("--reflection"); s.add_argument("--session")
    s = command("addendum", cmd_addendum); s.add_argument("--md", required=True); s.add_argument("--session")
    s = command("override", cmd_override); s.add_argument("--scores"); s.add_argument("--close-gaps")
    s.add_argument("--stops")
    s.add_argument("--session")
    s = command("prepare", cmd_prepare); s.add_argument("--if-needed", action="store_true")
    s.add_argument("--allow-unreflected", action="store_true")
    s = command("finish-prepare", cmd_finish_prepare); s.add_argument("--revised", action="store_true")
    s.add_argument("--no-evidence", action="store_true")
    s = command("keys", cmd_keys, work=False); s.add_argument("paths", nargs="+"); s.add_argument("--plan")
    s = command("key-table", cmd_key_table, work=False)
    s = command("command-table", cmd_command_table, work=False)
    s = command("file-table", cmd_file_table, work=False)
    s = command("verify", cmd_verify); s.add_argument("--store", required=True)
    s = command("testing-note", cmd_testing_note); s.add_argument("--feedback", required=True); s.add_argument("--session")
    s = command("stats", cmd_stats); s.add_argument("--all", action="store_true")
    s = command("review", cmd_review); s.add_argument("--review", required=True)
    s = command("review-doc", cmd_review_doc); s.add_argument("--md", required=True); s.add_argument("--date")
    s.add_argument("--title"); s.add_argument("--headline")
    s = command("position", cmd_position); s.add_argument("--drop"); s.add_argument("--reopened")
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
    for name in ("start", "answer", "sent", "present", "save", "close"):     # the round's clock: another time than now
        sub.choices[name].add_argument("--at")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "today_sub", None):
        args.today = args.today_sub
    try:
        return args.fn(args) or 0
    except CmeError as e:
        print(json.dumps({"ok": False, "error": e.msg}, ensure_ascii=False))
        return e.code


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Simulation harness for the clinical-cme skill (ADR 0005). Standard library only.

The LLM part of a simulation runs inside a Claude Code session (no API key): one helper agent is
the examiner running the skill on a folder store, another plays a learner persona, and the
session relays between them (see sim/README.md). This script is everything that is not an LLM:

  init     make a run folder: a seeded folder store, a scratch folder, the two agents' briefs
  send     an agent sends a message to the other side; the time is recorded
  next     the session asks what to hand to the other agent, and whether to stop
  check    the automatic checks: blinding, saved files, log complete and verbatim, the writing
           standards (abbreviations, time anchors, the feedback's glossary line), the Listening
           section and its picks, and what the persona is expected to produce (a settled
           dispute; a round saved without its case)
  quality  the form a separate scorer agent fills in: clinical quality per item and per feedback
  report   checks + waiting time per step + the quality scores (logged only, never a pass bar),
           written to sim/reports/ for comparison with later runs
  history  one line per saved report, to compare runs over time

It talks to cme.py through its command line, as the assistant does. The one exception is the
standards check, which imports the engine's lint functions so that the heuristics for rules 5
and 6 exist once (load_engine).
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SKILL = os.path.join(ROOT, "skills", "clinical-cme")
ROLES = ("examiner", "learner")
MAX_LEARNER_MESSAGES = 12          # a round has at most ~6 learner turns; beyond this the run is stuck
KEY_LINE_MIN = 30                  # shortest key/kit line (normalised characters) searched for verbatim
EXPECTATIONS = ("dispute", "stopped")   # what a persona's `expect` list may name (extra checks)
OUTCOMES = ("learner_right", "both_defensible", "upheld")
NOTE_MAX = 200                     # a quality note in the report is one line
OPENING = "Quiz me: today's CME round, please. My Clinical CME folder is {store}"

# Settings every simulated ledger starts with. Helper agents cannot usually start helpers of their
# own, so the examiner also writes the items; nothing is prepared ahead unless asked for.
SIM_CONFIG = {"helpers": False, "prepare_ahead": False, "testing": False, "reminders": False}

PRESENT_RE = re.compile(r"<!--\s*present:\s*([a-z0-9_]+)\s*-->\s*\n(.*?)\n?\s*<!--\s*/present\s*-->", re.S)
BANK_RE = re.compile(r"<!--\s*bank\s*-->\s*\n(.*?)\n?\s*<!--\s*/bank\s*-->", re.S)
BLUEPRINT_ID_RE = re.compile(r"\b[A-Z]{2,8}-\d{1,3}\b")
# Rule 5.3: a feedback message opens with "Abbreviations: …". A title may stand above it, so the
# line is looked for among the first GLOSSARY_WITHIN lines that are not empty.
GLOSSARY_RE = re.compile(r"^[\s>*_#-]*Abbreviations?[*_]*\s*:", re.I)
GLOSSARY_WITHIN = 3
ANSWER_RE = re.compile(r"<!--\s*answers:\s*([a-z0-9_]+)\s*-->\s*\n(.*?)\n?\s*<!--\s*/answers\s*-->", re.S)

# Section headings of the session document (references/session_log.md §2–3).
SECTIONS_A = [
    ("questions", "### Questions — as presented", "examiner"),
    ("a_questions", "### Your answers — questions", "learner"),
    ("fb_questions", "### Feedback — questions", "examiner"),
    ("case", "### Case — as presented", "examiner"),
    ("a_case", "### Your answers — case", "learner"),
    ("stage2", "### Stage 2 — as presented", "examiner"),
    ("a_final", "### Your final answers", "learner"),
    ("notes", "### Notes", None),
    ("feedback", "### Feedback (as sent)", "examiner"),
]
SECTIONS_B = [
    ("reflection", "### Reflection", "learner"),
    ("discussion", "### Discussion", None),
    ("grade_changes", "### Grade changes", None),
    ("coded", "### Coded analysis", None),
    ("errata", "### Errata", None),
]
GENERIC_WORDS = {"acute", "chronic", "disease", "disorder", "disorders", "management", "issues", "inpatient",
                 "outpatient", "basics", "common", "general", "emergencies", "emergency", "workup",
                 "assessment", "syndrome", "therapy", "treatment", "approach", "patient", "complications",
                 "severe", "infection", "infections", "including", "related", "selection", "control",
                 "medical", "hospital"}


class SimError(Exception):
    pass


# ---------------------------------------------------------------- small helpers

def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read_json(path, default=None):
    try:
        return json.loads(read(path))
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    write(path, json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def norm(text):
    """Verbatim comparison ignores only runs of whitespace."""
    return re.sub(r"\s+", " ", text or "").strip()


def excerpt(text, pos, length, pad=50):
    a, b = max(0, pos - pad), min(len(text), pos + length + pad)
    return ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")


def rp(run, *parts):
    return os.path.join(run, *parts)


def run_engine(script, args):
    """Run the engine script as its own process; returns the subprocess.CompletedProcess. The
    one way this harness calls cme.py: the tests swap it for an in-process runner (issue #73)."""
    return subprocess.run([sys.executable, script, *args], capture_output=True, text=True)


def run_cme(skill, *args):
    r = run_engine(os.path.join(skill, "scripts", "cme.py"), list(args))
    if r.returncode != 0:
        raise SimError("cme.py %s failed: %s" % (args[0], (r.stderr or r.stdout).strip()[:500]))
    return r.stdout


def git_commit():
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() or None
    except OSError:
        return None


def skill_version(skill):
    try:
        m = re.search(r"\(version ([0-9.]+)\)", read(os.path.join(skill, "SKILL.md")))
        return m.group(1) if m else None
    except OSError:
        return None


# ---------------------------------------------------------------- transcript

def load_events(run):
    path = rp(run, "transcript.jsonl")
    if not os.path.exists(path):
        raise SimError("%s is not a simulation run folder (no transcript.jsonl)" % run)
    return [json.loads(line) for line in read(path).splitlines() if line.strip()]


def append_event(run, ev):
    with open(rp(run, "transcript.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")


def load_messages(run):
    """The messages in order, each with its text."""
    out = []
    for ev in load_events(run):
        if ev.get("role") in ROLES and "n" in ev:
            ev = dict(ev)
            ev["text"] = read(rp(run, ev["file"]))
            out.append(ev)
    return out


def record_message(run, role, text, ts=None):
    msgs = [e for e in load_events(run) if "n" in e]
    n = len(msgs) + 1
    rel = "messages/%03d-%s.md" % (n, role)
    write(rp(run, rel), text)
    ev = {"n": n, "role": role, "ts": time.time() if ts is None else ts, "file": rel, "chars": len(text)}
    append_event(run, ev)
    return ev


# ---------------------------------------------------------------- init

def persona_parts(name):
    path = name if os.path.isfile(name) else os.path.join(HERE, "personas", name + ".md")
    if not os.path.isfile(path):
        raise SimError("no persona '%s' (looked for %s)" % (name, path))
    text = read(path)
    m = re.search(r"```json\s*\n(.*?)\n```", text, re.S)
    try:
        profile = json.loads(m.group(1)) if m else {}
    except ValueError as e:
        raise SimError("the ledger profile in %s is not valid JSON: %s" % (path, e))
    if not isinstance(profile, dict):
        raise SimError("the ledger profile in %s must be a JSON object" % path)
    # `expect` is for the harness (which extra checks the persona's round must pass), not the ledger
    expect = profile.pop("expect", None) or []
    expect = [expect] if isinstance(expect, str) else list(expect)
    unknown = [e for e in expect if e not in EXPECTATIONS]
    if unknown:
        raise SimError("%s expects %s; known: %s" % (path, ", ".join(map(str, unknown)), ", ".join(EXPECTATIONS)))
    return os.path.abspath(path), os.path.splitext(os.path.basename(path))[0], profile, expect


def fill(template, values):
    for k, v in values.items():
        template = template.replace("{" + k + "}", v)
    return template


def claim_run_folder(base, stamp):
    """Make and return a run folder of its own under base: <stamp>, or <stamp>-2, <stamp>-3, ... when
    runs started in the same second have taken the earlier names. Making the folder is the claim
    (mkdir fails if it exists), so parallel inits never share one. The name goes into the
    examiner's brief, so it must not name the persona: a stamp and a counter only."""
    os.makedirs(base, exist_ok=True)
    n = 1
    while True:
        run = os.path.join(base, stamp if n == 1 else "%s-%d" % (stamp, n))
        try:
            os.mkdir(run)
            return run
        except FileExistsError:
            n += 1


def cmd_init(args):
    persona_path, persona, profile, expect = persona_parts(args.persona)
    skill = os.path.abspath(args.skill or DEFAULT_SKILL)
    if not os.path.isfile(os.path.join(skill, "scripts", "cme.py")):
        raise SimError("no skill at %s" % skill)
    if args.run:
        run = os.path.abspath(args.run)
        if os.path.exists(run) and os.listdir(run):
            raise SimError("%s already exists and is not empty" % run)
    else:
        run = claim_run_folder(os.path.abspath(args.runs_dir or os.path.join(HERE, "runs")),
                               args.stamp or dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    for d in ("store", "work", "messages", "learner"):
        os.makedirs(rp(run, d))
    config = dict(SIM_CONFIG)
    if args.prepare_ahead:
        config["prepare_ahead"] = True
    if args.config:
        config.update(json.loads(args.config))
    if args.from_run:
        src = rp(os.path.abspath(args.from_run), "store", "data")
        if not os.path.isfile(os.path.join(src, "state.json")):
            raise SimError("no store to continue from in %s" % args.from_run)
        shutil.copytree(src, rp(run, "store", "data"))
        config = (read_json(rp(run, "store", "data", "state.json")) or {}).get("config") or config
    else:
        today = ["--today", args.today] if args.today else []
        # set the learner up as the skill does (init into a work folder), then publish to the folder store
        seed = rp(run, ".seed")
        out = json.loads(run_cme(skill, *today, "init", "--work", seed,
                                 "--blueprint", os.path.join(skill, "templates", "blueprint.json"),
                                 "--profile", json.dumps(profile), "--config", json.dumps(config)))
        publish_to_folder(out["files"], rp(run, "store"))
        shutil.rmtree(seed)
    # the ledger as the round found it: the stopped check compares the case topic's schedule with it
    shutil.copyfile(rp(run, "store", "data", "state.json"), rp(run, "ledger_at_start.json"))
    meta = {"run": run, "persona": persona, "persona_file": persona_path, "expect": expect, "skill": skill,
            "skill_version": skill_version(skill), "commit": git_commit(), "config": config,
            "continued_from": os.path.abspath(args.from_run) if args.from_run else None,
            "sessions_at_start": len((read_json(rp(run, "store", "data", "state.json")) or {}).get("sessions") or []),
            "created": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    write_json(rp(run, "run.json"), meta)
    values = {"run": run, "store": rp(run, "store"), "work": rp(run, "work"), "skill": skill,
              "simulate": os.path.abspath(__file__), "persona_file": persona_path,
              "learner_dir": rp(run, "learner"), "messages": rp(run, "messages")}
    for role in ROLES:
        write(rp(run, "%s_prompt.md" % role), fill(read(os.path.join(HERE, "prompts", role + ".md")), values))
    write(rp(run, "transcript.jsonl"), "")
    first = record_message(run, "learner", (args.opening or OPENING).format(store=rp(run, "store")) + "\n")
    print(json.dumps({"ok": True, "run": run, "persona": persona,
                      "examiner_prompt": rp(run, "examiner_prompt.md"),
                      "learner_prompt": rp(run, "learner_prompt.md"),
                      "first_message": rp(run, first["file"]),
                      "then": "start the examiner agent now with the examiner prompt; the clock is running"},
                     indent=1))


# ---------------------------------------------------------------- send, next

def cmd_send(args):
    text = read(args.file)
    if not text.strip():
        raise SimError("%s is empty; nothing sent" % args.file)
    ev = record_message(args.run, args.role, text, args.ts)
    print(json.dumps({"ok": True, "sent": ev["n"], "to": ROLES[1 - ROLES.index(args.role)], "chars": ev["chars"]}))


def round_closed(run):
    """True once the store holds a round with its reflection (the last step of a round)."""
    st = read_json(rp(run, "store", "data", "state.json")) or {}
    sessions = st.get("sessions") or []
    started = (read_json(rp(run, "run.json")) or {}).get("sessions_at_start")
    if not sessions or (started is not None and len(sessions) <= started):
        return False
    return st.get("unreflected") != sessions[-1].get("id")


def cmd_next(args):
    """After an agent's turn: record its end, and say what to hand to the other agent."""
    events = load_events(args.run)
    append_event(args.run, {"mark": "turn_end", "role": args.after, "ts": time.time() if args.ts is None else args.ts})
    msgs = [e for e in events if "n" in e]
    new = []
    for e in reversed(msgs):
        if e["role"] != args.after:
            break
        new.insert(0, rp(args.run, e["file"]))
    other = ROLES[1 - ROLES.index(args.after)]
    closed = round_closed(args.run)
    learner_count = sum(1 for e in msgs if e["role"] == "learner")
    stop, why = False, None
    if not new:
        stop = True
        why = ("the round is closed and the learner has nothing to add" if closed and args.after == "learner"
               else "the %s ended its turn without sending anything" % args.after)
    elif learner_count > MAX_LEARNER_MESSAGES:
        stop, why = True, "more than %d learner messages: the round is not converging" % MAX_LEARNER_MESSAGES
    print(json.dumps({"ok": True, "deliver_to": other, "files": new, "round_closed": closed,
                      "stop": stop, "why": why}, indent=1))


# ---------------------------------------------------------------- what the round was

def parse_sections(md, table):
    """Split a part of the session document at its known headings."""
    hits = []
    for key, heading, _ in table:
        m = re.search(r"^%s.*$" % re.escape(heading), md or "", re.M)
        if m:
            hits.append((m.start(), m.end(), key))
    hits.sort()
    out = {}
    for i, (_, end, key) in enumerate(hits):
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(md)
        out[key] = md[end:stop].strip()
    return out


def find_message(messages, role, text, after=0):
    """The first message of a role (later than `after`) that holds `text` word for word, or that
    is held by it (an answers block may gather one message among other notes)."""
    want = norm(text)
    if not want:
        return None
    for m in messages:
        if m["role"] != role or m["n"] <= after:
            continue
        got = norm(m["text"])
        if want in got or (len(got) >= 2 and got in want):
            return m["n"]
    return None


class Round:
    """Everything the checks need to know about a finished run."""

    def __init__(self, run):
        self.run = run
        self.meta = read_json(rp(run, "run.json")) or {}
        self.messages = load_messages(run)
        self.work = rp(run, "work")
        self.store = rp(run, "store")
        self.state = read_json(rp(self.store, "data", "state.json")) or {}
        # record.json is the round record `save` built (key headers + the examiner's grading);
        # round.json alone describes the round only when it was written out in full
        self.round = read_json(rp(self.work, "record.json")) or read_json(rp(self.work, "round.json")) or {}
        self.plan = read_json(rp(self.work, "plan.json")) or {}
        self.start_state = read_json(rp(run, "ledger_at_start.json"))
        sessions = self.state.get("sessions") or []
        self.sid = self.round.get("log_id") or (sessions[-1].get("id") if sessions else None)
        self.doc = read_json(rp(self.store, "data", "sessions", "%s.json" % self.sid)) if self.sid else None
        self.sealed = {}
        for name in ("sealed_questions.md", "sealed_case.md", "kit_questions.md", "kit_case.md"):
            if os.path.isfile(rp(self.work, name)):
                self.sealed[name] = read(rp(self.work, name))
        self.answers = {}
        if os.path.isfile(rp(self.work, "answers.md")):
            for name, body in ANSWER_RE.findall(read(rp(self.work, "answers.md"))):
                self.answers[name] = (self.answers.get(name, "") + "\n\n" + body.strip()).strip()
        self.items = self.round.get("items") or []
        if not self.items and sessions and sessions[-1].get("id") == self.sid:
            self.items = sessions[-1].get("items") or []
        self.has_questions = any(it.get("type") in ("mcq", "focused") for it in self.items)
        self.has_case = any(it.get("type") in ("case", "essay") for it in self.items)
        self.a = parse_sections((self.doc or {}).get("transcript") or "", SECTIONS_A)
        self.b = parse_sections((self.doc or {}).get("closing") or "", SECTIONS_B)
        self.two_stage = "final" in self.answers or "stage2" in self.a
        self.session = next((s for s in sessions if s.get("id") == self.sid), None)
        # a case that was planned but is not among the items graded: the learner stopped before it.
        # It stays blind (its topic is still due), so its seal never lifts.
        self.unanswered = []
        if self.items and not self.has_case:
            topic = self.planned_case()
            if topic:
                self.unanswered.append(dict(topic, type="case"))
        self.never_lifted = {"case"} if self.unanswered or (self.items and not self.has_case
                                                            and "sealed_case.md" in self.sealed) else set()
        # the block the round was played in (theme, round, length), as the saved session keeps it
        self.block = (self.session or {}).get("block")
        self._label_parts()

    def planned_case(self):
        """The topic of the case the round was planned with: from plan.json, else the one
        blueprint ID named in the hidden part of the case's keys."""
        for it in self.plan.get("items") or []:
            if it.get("slot") in ("case", "essay") and it.get("topic"):
                return {k: it.get(k) for k in ("topic", "label", "domain") if it.get(k)}
        known = {tid for dom in (self.state.get("blueprint") or {}).values()
                 for tid in ((dom or {}).get("topics") or {})}
        hidden = BANK_RE.sub("", PRESENT_RE.sub("", self.sealed.get("sealed_case.md", "")))
        named = sorted({t for t in BLUEPRINT_ID_RE.findall(hidden) if t in known})
        return {"topic": named[0]} if len(named) == 1 else None

    def _label_parts(self):
        """Which learner message answered which part: found by matching the answers the examiner
        filed (answers.md) against what the learner actually sent."""
        self.answered = {}
        for part in ("questions", "case", "final"):
            if part in self.answers:
                self.answered[part] = find_message(self.messages, "learner", self.answers[part])
        if self.b.get("reflection"):
            self.answered["reflection"] = find_message(self.messages, "learner", self.b["reflection"])
        self.part_of = {n: part for part, n in self.answered.items() if n}
        # the seal on a part lifts with the learner message that completes its answers
        self.lift = {}
        if self.has_questions:
            self.lift["questions"] = self.answered.get("questions")
        if self.has_case:
            self.lift["case"] = self.answered.get("final" if self.two_stage else "case")


# ---------------------------------------------------------------- check 1: blinding

def topic_label(rnd, item):
    tid = item.get("topic") or ""
    bp = rnd.state.get("blueprint") or {}
    dom = bp.get(item.get("domain") or tid.split("-")[0]) or {}
    label = (item.get("label") or (dom.get("topics") or {}).get(tid)
             or ((rnd.state.get("topics") or {}).get(tid) or {}).get("label"))
    return label, dom.get("name")


def significant_words(label):
    label = re.sub(r"\([^)]*\)", " ", label or "")
    return sorted({w for w in re.findall(r"[a-z]+", label.lower()) if len(w) >= 5 and w not in GENERIC_WORDS})


def block_line(rnd):
    """The line the opening message must show: the block's theme and position (ADR 0003)."""
    if not rnd.block:
        return None
    name = ((rnd.state.get("blueprint") or {}).get(rnd.block.get("theme")) or {}).get("name") or rnd.block.get("theme")
    return "Block: %s, round %s of %s" % (name, rnd.block.get("round"), rnd.block.get("length"))


def forbidden_terms(rnd):
    """(part, kind, level, term, pattern). `fail` terms are leaks; `warn` terms are for a human to
    judge (a topic word or the domain's name in the text shown). The name of the block's theme is
    shown on purpose, so it is not a term."""
    terms = []
    theme = ((rnd.state.get("blueprint") or {}).get((rnd.block or {}).get("theme")) or {}).get("name")

    def phrase(part, kind, level, text):
        text = norm(text)
        if len(text) >= 4:
            terms.append((part, kind, level, text, re.compile(re.escape(text).replace(r"\ ", r"\s+"), re.I)))

    for it in rnd.items + rnd.unanswered:
        part = "case" if it.get("type") in ("case", "essay") else "questions"
        tid = it.get("topic")
        if tid:
            terms.append((part, "blueprint ID", "fail", tid,
                          re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(tid))))
        label, domain = topic_label(rnd, it)
        if label:
            phrase(part, "topic label", "fail", label)
            bare = re.sub(r"\([^)]*\)", " ", label)
            if norm(bare) != norm(label):
                phrase(part, "topic label", "fail", bare)
            for w in significant_words(label):
                # British and American spellings alike (anemia / anaemia, edema / oedema)
                spelt = re.escape(w).replace("ae", "e").replace("oe", "e").replace("e", "(?:e|ae|oe)")
                terms.append((part, "topic word", "warn", w, re.compile(r"\b%s(?:s|es)?\b" % spelt, re.I)))
        if domain and domain != theme:
            phrase(part, "domain name", "warn", domain)
    last_part = "case" if rnd.has_case else "questions"
    diagnosis = (rnd.round.get("case") or {}).get("diagnosis")
    if diagnosis:
        phrase("case", "diagnosis", "fail", diagnosis)
        bare = re.sub(r"\([^)]*\)", " ", diagnosis)
        if norm(bare) != norm(diagnosis):
            phrase("case", "diagnosis", "fail", bare)
    elif "case" in rnd.never_lifted:
        # no graded case to take the diagnosis from: use the line of the keys that states it
        hidden = BANK_RE.sub("", PRESENT_RE.sub("", rnd.sealed.get("sealed_case.md", "")))
        for stated in re.findall(r"(?im)^.*?\bdiagnosis\b[*_`\s]*:[*_`\s]*([^\n.;]{4,80})", hidden):
            phrase("case", "diagnosis", "fail", stated.strip("*_` "))
    if rnd.round.get("title"):
        phrase(last_part, "session title", "fail", rnd.round["title"])
    # key and feedback-note lines: everything in the sealed files that is not text to present.
    # A piece that both parts' files hold word for word (a generic line such as "nothing on it in
    # your record yet" in each reveal) tells nothing about the later part: it is searched for as
    # a term of the part whose seal lifts first only, so it stays a leak until then.
    # What the part shows the learner (its `present` and `bank` blocks) is shown whichever of the
    # part's files repeats it: a kit's reveal may quote the stem word for word.
    hidden_of, shown_of = {}, {}
    for name, text in rnd.sealed.items():
        part = "case" if name.endswith("case.md") else "questions"
        hidden_of[part] = hidden_of.get(part, "") + " " + norm(BANK_RE.sub("", PRESENT_RE.sub("", text))).lower()
        shown_of[part] = shown_of.get(part, "") + " " + norm(
            " ".join(b for _, b in PRESENT_RE.findall(text)) + " " + " ".join(BANK_RE.findall(text)))
    order = sorted(hidden_of, key=lambda p: (p in rnd.never_lifted, rnd.lift.get(p) or float("inf")))
    for name, text in rnd.sealed.items():
        part = "case" if name.endswith("case.md") else "questions"
        earlier = [hidden_of[p] for p in order[:order.index(part)]]
        shown = shown_of[part]
        hidden = BANK_RE.sub("", PRESENT_RE.sub("", text))
        kind = "key line" if name.startswith("sealed") else "feedback-notes line"
        for line in hidden.splitlines():
            line = norm(re.sub(r"^[\s#>*\-+\d.)]*", "", line).strip("*_` "))
            # the whole line, and each sentence or clause of it long enough to be telling
            for piece in [line] + re.split(r"[.;:]\s+", line):
                piece = piece.strip(" .;:")
                if (len(piece) >= KEY_LINE_MIN and piece not in shown
                        and not any(piece.lower() in h for h in earlier)):
                    phrase(part, kind, "fail", piece)
    seen, out = set(), []
    for t in terms:
        if (t[0], t[1], t[3].lower()) not in seen:
            seen.add((t[0], t[1], t[3].lower()))
            out.append(t)
    return out


def check_blinding(rnd):
    """Nothing the examiner sent before a part's answers may hold that part's topic, diagnosis or key."""
    findings, problems = [], []
    if not rnd.items:
        problems.append("no round.json in the work folder and no saved round: nothing to check against")
    last = rnd.messages[-1]["n"] if rnd.messages else 0
    for part, lift in rnd.lift.items():
        if not lift:
            problems.append("cannot tell which learner message answered the %s (no matching block in answers.md); "
                            "every examiner message was scanned for it" % part)
    terms = forbidden_terms(rnd)
    line = block_line(rnd)
    first = next((m for m in rnd.messages if m["role"] == "examiner"), None)
    if line and first and norm(line).lower() not in norm(first["text"]).lower():
        problems.append("the opening message does not show the block line \"%s\"" % line)
    for m in rnd.messages:
        if m["role"] != "examiner":
            continue
        for part, kind, level, term, rx in terms:
            if part in rnd.never_lifted:
                pass                      # never answered: sealed to the end of the round
            elif part not in rnd.lift or m["n"] > (rnd.lift[part] or last + 1):
                continue
            hit = rx.search(m["text"])
            if hit:
                findings.append({"part": part, "kind": kind, "level": level, "term": term, "message": m["n"],
                                 "excerpt": norm(excerpt(m["text"], hit.start(), hit.end() - hit.start()))})
    leaks = [f for f in findings if f["level"] == "fail"]
    undetermined = [p for p, lift in rnd.lift.items() if not lift]
    if undetermined:      # with no seal point, later messages legitimately name the topic: report, do not count
        leaks = [f for f in leaks if f["part"] not in undetermined]
    return {"ok": not leaks and not problems, "leaks": len(leaks),
            "to_review": len([f for f in findings if f["level"] == "warn"]),
            "seal_lifted_at": rnd.lift, "never_lifted": sorted(rnd.never_lifted),
            "terms_checked": len(terms), "block_line": line, "findings": findings, "problems": problems}


# ---------------------------------------------------------------- check 2: every file saved

def publish_to_folder(files, store):
    """Carry a publish set (the `files` a cme.py command printed) to a folder store, in its order."""
    for f in files:
        dest = os.path.join(store, *f["as"].split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(f["path"], dest)


def publish_set(work):
    """The store paths in the work folder's publish set (publish.json), in write order."""
    manifest = read_json(os.path.join(work, "publish.json")) or {}
    return [f.get("as") for f in manifest.get("files") or [] if isinstance(f, dict) and f.get("as")]


def check_saved(rnd):
    """The store holds what cme.py produced, and the round in it is whole."""
    problems = []
    verify = None
    wanted = publish_set(rnd.work)
    if not wanted:
        problems.append("no publish set in the work folder: cannot compare what cme.py wrote with the store")
    else:
        try:
            verify = json.loads(run_cme(rnd.meta.get("skill") or DEFAULT_SKILL, "verify", "--work", rnd.work,
                                        "--store", rnd.store))
        except (SimError, ValueError) as e:
            problems.append(str(e))
        if verify and not verify.get("ok"):
            for rel in verify.get("missing") or []:
                problems.append("not in the store: %s" % rel)
            for rel in verify.get("mismatched") or []:
                problems.append("differs from what cme.py wrote: %s" % rel)
    st = rnd.state
    if not st:
        problems.append("no readable ledger at store/data/state.json")
    sessions = st.get("sessions") or []
    if not rnd.sid or not any(s.get("id") == rnd.sid for s in sessions):
        problems.append("the ledger holds no record of this round")
    elif st.get("unreflected") == rnd.sid:
        problems.append("the ledger still marks %s as waiting for its reflection" % rnd.sid)
    if rnd.sid and rnd.doc is None:
        problems.append("no session document data/sessions/%s.json in the store" % rnd.sid)
    elif rnd.doc is not None and not rnd.doc.get("reflected"):
        problems.append("session document %s was never closed (reflected is false)" % rnd.sid)
    idx = read_json(rp(rnd.store, "data", "page.json"))
    if idx is None:
        problems.append("no readable page file at store/data/page.json")
    elif rnd.sid and not any(e.get("id") == rnd.sid for e in idx.get("sessions") or []):
        problems.append("the page file does not list %s" % rnd.sid)
    elif idx.get("gen") != st.get("gen"):
        problems.append("the page file (gen %s) is older than the ledger (gen %s)" % (idx.get("gen"), st.get("gen")))
    return {"ok": not problems, "session": rnd.sid, "publish_set": wanted,
            "files_compared": (verify or {}).get("checked"), "problems": problems}


# ---------------------------------------------------------------- check 4: listening

SPOTIFY_RE = re.compile(r"open\.spotify\.com", re.I)
EPISODE_RE = re.compile(r"^https://open\.spotify\.com/episode/[A-Za-z0-9]{22}$")
LISTENING_HEAD_RE = re.compile(r"(?im)^[ \t>#*_]*Listening\b")


def check_listening(rnd):
    """The round ends with its Listening section (standards.md, rule 8; feedback_guide.md §2 E2):
    the final feedback has it, the session document has the `listening` list, every pick is one
    Spotify episode whose link is in the feedback as sent, and no Spotify link was sent before
    the last answer. A topic for which nothing suitable was found has no pick: that passes, and
    is counted. With listening turned off, nothing is expected."""
    on = (rnd.plan.get("listening") is not False
          and ((rnd.start_state or rnd.state).get("config") or {}).get("listening", True) is not False)
    out = {"ok": True, "on": on, "picks": 0, "topics": len({it.get("topic") for it in rnd.items if it.get("topic")}),
           "from_kit": 0, "from_search": 0, "problems": []}
    if not on:
        return out
    problems = out["problems"]
    picks = (rnd.doc or {}).get("listening")
    if rnd.doc is None:
        problems.append("no session document to check")
    elif not isinstance(picks, list):
        problems.append("the session document has no `listening` list (round.json `listening`, state_schema.md §2)")
    feedback = rnd.a.get("feedback") or ""
    if rnd.doc is not None and not LISTENING_HEAD_RE.search(feedback):
        problems.append("the final feedback has no Listening section")
    for p in picks if isinstance(picks, list) else []:
        out["picks"] += 1
        out["from_kit"] += p.get("source") == "kit"
        out["from_search"] += p.get("source") == "search"
        if not EPISODE_RE.match(str(p.get("link") or "")):
            problems.append("the pick for %s is not a link to one Spotify episode" % p.get("topic"))
        elif p["link"] not in feedback:
            problems.append("the pick for %s is not in the final feedback as sent" % p.get("topic"))
    # the section belongs to the final feedback: after the last answer the round got (a case never
    # answered stays sealed, and the questions' picks say nothing about it)
    lifts = list(rnd.lift.values())
    if lifts and all(lifts):
        for m in rnd.messages:
            if m["role"] == "examiner" and m["n"] < max(lifts) and SPOTIFY_RE.search(m["text"]):
                problems.append("examiner message %d holds a Spotify link before the last answer" % m["n"])
    out["ok"] = not problems
    return out


# ---------------------------------------------------------------- check 5: prepared feedback

LEFTOVER_RE = re.compile(r"<!--\s*/?\s*(?:block|draft|notes|check)\b|\[live:", re.I)


def check_prepared(rnd):
    """Marks before text, and the feedback from the draft (feedback_guide.md §9; ADR 0009): every
    rubric element of the round record is marked, a draft was made (the session document has
    `prepared_feedback`), and no feedback as sent still holds the draft's comment lines or a
    [live: …] part. Elements marked hit or partial without the learner's words are counted, for
    the record, and do not fail the run."""
    out = {"ok": True, "unmarked": 0, "unquoted": 0, "prepared_feedback": None, "problems": []}
    for it in rnd.items:
        for e in it.get("rubric") or []:
            if not isinstance(e, dict) or e.get("mark") not in ("hit", "partial", "missed"):
                out["unmarked"] += 1
            elif e["mark"] != "missed" and not str(e.get("quote") or "").strip():
                out["unquoted"] += 1
    if out["unmarked"]:
        out["problems"].append("%d rubric element(s) in the round record are not marked" % out["unmarked"])
    pf = (rnd.doc or {}).get("prepared_feedback")
    if rnd.doc is not None and not isinstance(pf, dict):
        out["problems"].append("the session document has no `prepared_feedback`: the feedback was not written "
                               "from a draft (`cme.py draft`)")
    elif isinstance(pf, dict):
        out["prepared_feedback"] = {k: (v if isinstance(v, int) else len(v or [])) for k, v in pf.items()}
    for key in ("fb_questions", "feedback"):
        if LEFTOVER_RE.search(rnd.a.get(key) or ""):
            out["problems"].append("the %s as sent still holds the draft's comment lines or a [live: …] part"
                                   % ("questions' feedback" if key == "fb_questions" else "final feedback"))
    out["ok"] = not out["problems"]
    return out


# ---------------------------------------------------------------- check 3: log complete and verbatim

def check_log(rnd):
    """Complete: every section the round's shape calls for is there, and every learner message is in
    the log. Verbatim: what the log says was presented, answered and sent is word for word what
    went over the wire."""
    problems, unlogged = [], []
    if rnd.doc is None:
        return {"ok": False, "sections": [], "problems": ["no session document to check"], "examiner_text_not_logged": []}
    required = []
    if rnd.has_questions:
        required += ["questions", "a_questions"]
    if rnd.has_case:
        required += ["case", "a_case"]
        if rnd.two_stage or rnd.round.get("case_format") == "unfolding":
            required += ["stage2", "a_final"]
    required.append("feedback")
    headings = {k: h for k, h, _ in SECTIONS_A + SECTIONS_B}
    who = {k: r for k, _, r in SECTIONS_A + SECTIONS_B}
    for key in required:
        if not rnd.a.get(key) or norm(rnd.a[key]) == "None.":
            problems.append("part A has no '%s' section (or it is empty)" % headings[key])
    for key in ("reflection", "discussion", "grade_changes", "coded"):
        if not rnd.b.get(key):
            problems.append("part B has no '%s' section (or it is empty)" % headings[key])
    sections = dict(rnd.a)
    sections.update(rnd.b)
    for key, body in sections.items():
        role = who.get(key)
        if not role or norm(body) == "None.":
            continue
        if not find_message(rnd.messages, role, body):
            problems.append("'%s' is not word for word what the %s sent" % (headings[key], role))
    log_text = norm(" ".join(str((rnd.doc or {}).get(k) or "") for k in ("transcript", "closing", "addendum")))
    for m in rnd.messages[1:]:           # message 1 is the harness's opening request
        if m["role"] == "learner" and norm(m["text"]) not in log_text:
            problems.append("learner message %d is not in the log word for word" % m["n"])
    # for the record: examiner paragraphs that are not in the log (opening lines, the close message
    # and short prompts are not meant to be; a feedback paragraph would be a finding)
    for m in rnd.messages:
        if m["role"] != "examiner":
            continue
        for para in re.split(r"\n\s*\n", m["text"]):
            if len(norm(para)) >= 80 and norm(para) not in log_text:
                unlogged.append({"message": m["n"], "starts": norm(para)[:90]})
    return {"ok": not problems, "sections": sorted(sections), "problems": problems,
            "examiner_text_not_logged": unlogged}


# ---------------------------------------------------------------- waiting time per step

def timings(rnd):
    """One step per learner message: how long until the examiner's first message after it (what
    the learner waits), and until the examiner's turn ended (behind-the-scenes work included)."""
    events = load_events(rnd.run)
    steps = []
    msgs = rnd.messages
    for i, m in enumerate(msgs):
        if m["role"] != "learner":
            continue
        if i + 1 < len(msgs) and msgs[i + 1]["role"] == "learner":
            continue                      # the learner sent two in a row: time the last one
        replies = []
        for nxt in msgs[i + 1:]:
            if nxt["role"] != "examiner":
                break
            replies.append(nxt)
        until = msgs[i + 1 + len(replies)]["ts"] if i + 1 + len(replies) < len(msgs) else float("inf")
        ends = [e["ts"] for e in events if e.get("mark") == "turn_end" and e.get("role") == "examiner"
                and m["ts"] <= e["ts"] <= until]
        label = "start of round" if m["n"] == 1 else "after %s" % {
            "questions": "the answers to the questions", "case": "the Stage 1 answer" if rnd.two_stage else "the case answer",
            "final": "the final answers", "reflection": "the reflection"}.get(rnd.part_of.get(m["n"]), "learner message %d" % m["n"])
        # the learner's own time runs from when the examiner's turn ended (it is only then handed on)
        handed = [e["ts"] for e in events if e.get("role") == "examiner" and e["ts"] <= m["ts"]]
        steps.append({
            "step": len(steps) + 1, "label": label, "learner_message": m["n"],
            "wait_s": round(replies[0]["ts"] - m["ts"], 1) if replies else None,
            "turn_s": round(ends[0] - m["ts"], 1) if ends else None,
            "examiner_messages": len(replies), "examiner_chars": sum(r["chars"] for r in replies),
            "learner_s": round(m["ts"] - max(handed), 1) if handed else None,
        })
    waits = [s["wait_s"] for s in steps if s["wait_s"] is not None]
    return {"steps": steps, "total_wait_s": round(sum(waits), 1) if waits else None,
            "longest_wait_s": max(waits) if waits else None,
            "elapsed_s": round(msgs[-1]["ts"] - msgs[0]["ts"], 1) if len(msgs) > 1 else None}


# ---------------------------------------------------------------- what a persona is expected to produce

def empty_section(body):
    return not norm(body) or norm(body).rstrip(".").lower() == "none"


def holds_message(body, messages, role, min_chars):
    """True if the section holds a message of that role word for word, or a paragraph of the
    section (long enough to be telling) is word for word part of such a message."""
    whole = norm(body)
    paras = [norm(p) for p in re.split(r"\n\s*\n", body or "") if len(norm(p)) >= min_chars]
    for m in messages:
        if m["role"] != role or m["n"] == 1:
            continue
        got = norm(m["text"])
        if (len(got) >= min_chars and got in whole) or any(p in got for p in paras):
            return True
    return False


def check_dispute(rnd):
    """The dispute persona: the round holds a settled dispute, in the ledger's grade changes and in
    the log (the exchange word for word, and the change under 'Grade changes'). An upheld grade, or
    a challenged teaching point with the score unchanged, is settled too: its entry has from = to."""
    problems = []
    # a score the learner set themselves (outcome learner_set) is not a dispute and settles none
    changes = [g for g in (rnd.session or {}).get("grade_changes") or [] if g.get("outcome") != "learner_set"]
    if not rnd.session:
        problems.append("the ledger holds no record of this round")
    elif not changes:
        problems.append("the ledger records no grade change for this round (grade_changes is empty; every "
                        "settled dispute has an entry, an upheld one or one on a teaching point with "
                        "from = to: feedback_guide.md section 7)")
    for g in changes:
        if g.get("outcome") not in OUTCOMES:
            problems.append("grade change on %s is not settled: outcome %s (expected one of %s)"
                            % (g.get("item") or g.get("topic") or "?", json.dumps(g.get("outcome")), ", ".join(OUTCOMES)))
    if empty_section(rnd.b.get("grade_changes")):
        problems.append("the log's 'Grade changes' section is missing or says there were none")
    # the exchange: under Discussion when raised after the final feedback, under Notes when
    # settled mid-round (SKILL.md turns 2 and 5)
    places = [(k, body) for k, body in (("discussion", rnd.b.get("discussion")), ("notes", rnd.a.get("notes")))
              if not empty_section(body)]
    logged_in = [k for k, body in places if holds_message(body, rnd.messages, "learner", 20)
                 and holds_message(body, rnd.messages, "examiner", 40)]
    if not logged_in:
        problems.append("neither 'Discussion' nor 'Notes' holds the dispute word for word "
                        "(the learner's challenge and the examiner's reply)")
    return {"ok": not problems, "logged_in": logged_in, "problems": problems,
            "grade_changes": [{k: g.get(k) for k in ("item", "topic", "from", "to", "outcome")} for g in changes]}


def check_stopped(rnd):
    """The stop-halfway persona: the round is saved with the items answered and without the case,
    and the case's topic is still due (its schedule is as the round found it)."""
    problems = []
    sess = rnd.session or {}
    items = sess.get("items") or []
    topic = (rnd.planned_case() or {}).get("topic")
    if not rnd.session:
        problems.append("the ledger holds no record of this round")
    else:
        if not any(it.get("type") in ("mcq", "focused") for it in items):
            problems.append("the saved round holds no short question")
        if any(it.get("type") in ("case", "essay") for it in items) or sess.get("case"):
            problems.append("the saved round holds a case; the learner stopped before it")
    schedule = None
    if rnd.session and not topic:
        problems.append("cannot tell which topic the case was on (no case in plan.json, and the case's keys "
                        "do not name exactly one blueprint ID)")
    elif topic:
        if topic in (sess.get("topics") or []):
            problems.append("the case's topic %s is recorded as tested in this round" % topic)
        fields = ("last", "attempts", "step", "due")
        blank = {"last": None, "attempts": 0, "step": 0, "due": None}

        def sched(state):
            t = ((state or {}).get("topics") or {}).get(topic) or {}
            return {k: t.get(k, blank[k]) or blank[k] for k in fields}

        schedule = sched(rnd.state)
        if rnd.start_state is None:
            problems.append("no ledger_at_start.json in the run folder: cannot compare the topic's schedule")
        elif schedule != sched(rnd.start_state):
            problems.append("the schedule of the case's topic %s changed in this round (%s → %s): it should "
                            "still be due as before" % (topic, json.dumps(sched(rnd.start_state)), json.dumps(schedule)))
    return {"ok": not problems, "case_topic": topic, "case_topic_schedule": schedule,
            "items_saved": len(items), "problems": problems}


EXPECTED_CHECKS = {"dispute": check_dispute, "stopped": check_stopped}


# ---------------------------------------------------------------- check 4: the writing standards

def load_engine(skill):
    """The skill's cme.py as a module, for its lint functions (rules 5 and 6 of
    references/standards.md): the heuristics are written there once and not copied here. Nothing
    is written into the skill's folder."""
    path = os.path.join(skill, "scripts", "cme.py")
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location("cme_engine_for_simulation", path)
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
    except Exception as e:                # an unreadable or broken engine is a finding, not a crash
        raise SimError("cannot load %s for its lint functions: %s" % (path, e))
    finally:
        sys.dont_write_bytecode = keep
    missing = [n for n in ("common_abbreviations", "undefined_abbreviations", "mixed_time_anchors",
                           "presented_text", "ABBREVIATION_RE") if not hasattr(engine, n)]
    if missing:
        raise SimError("%s has no %s: this copy of the skill is older than the rulebook's lint"
                       % (path, ", ".join(missing)))
    return engine


def glossary_line(text):
    """The feedback's glossary line (rule 5.3) if the message opens with one, else None."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return next((ln for ln in lines[:GLOSSARY_WITHIN] if GLOSSARY_RE.match(ln)), None)


def presented_blocks(rnd, engine):
    """What the learner was shown, in the order of the session, in the form the engine's lint
    takes: [(file, block, text)]. The text is the one that was sent (the log's "as presented"
    sections, which the log check holds to the messages word for word): Stage 2 as assembled, not
    the whole results bank. A part the log does not hold is taken from its sealed file."""
    sealed = {(name, block): text for name, block, text in engine.presented_text(rnd.sealed)}
    blocks = []
    for key, name, block in (("questions", "sealed_questions.md", "questions"),
                             ("case", "sealed_case.md", "case"), ("stage2", "sealed_case.md", "bank")):
        text = rnd.a.get(key)
        if empty_section(text):
            text = None if block == "bank" else sealed.get((name, block))
        if text:
            blocks.append((name, block, text))
    return blocks


def check_standards(rnd):
    """Rules 5 and 6 of the rulebook on the round as it was played, with the engine's own lint.

    To review (heuristics, as in the lint; they never fail a run): an abbreviation in the
    presented text that is not spelled out where the session first shows it (rule 5.1), a
    question or case that counts time from two anchors (rule 6), and an abbreviation a feedback
    message uses without having it in its glossary line.
    Fails: a feedback message that uses abbreviations and does not open with the glossary line
    (rule 5.3), and any text sent to the learner that names the skill's own machinery (rule 11)."""
    out = {"ok": False, "abbreviations": 0, "time_anchors": 0, "to_review": 0, "feedback": [],
           "findings": [], "problems": []}
    try:
        engine = load_engine(rnd.meta.get("skill") or DEFAULT_SKILL)
    except SimError as e:
        out["problems"].append(str(e))
        return out
    common = engine.common_abbreviations()
    if common is None:
        out["problems"].append("the abbreviation list of references/standards.md (rule 5.2) could not be read: "
                               "abbreviations were not checked")
    blocks = presented_blocks(rnd, engine)
    feedback = [(fid, rnd.a.get(key)) for fid, key in (("questions", "fb_questions"), ("final", "feedback"))
                if not empty_section(rnd.a.get(key))]
    if not blocks and not feedback:
        out["problems"].append("no presented text and no feedback to check (no session document, no sealed files)")
    where = {"questions": "the questions as presented", "case": "the case as presented", "bank": "Stage 2 as presented"}
    if common is not None:
        for _, block, token in engine.undefined_abbreviations(blocks, common):
            out["findings"].append({"rule": "5.1", "where": where[block], "detail": token})
            out["abbreviations"] += 1
    for name, place, now, day in engine.mixed_time_anchors(blocks):
        out["findings"].append({"rule": "6", "where": "the case and Stage 2" if name == "sealed_case.md" else place,
                                "detail": "from now: %s; by numbered day: %s" % (", ".join(now), ", ".join(day))})
        out["time_anchors"] += 1
    learner_texts = [("the %s feedback" % fid, text) for fid, text in feedback] + \
        [(where.get(block, block), text) for _, block, text in blocks]
    for place, text in learner_texts:
        found = engine.internal_terms(text)
        if found:
            out["problems"].append("%s names the skill's own machinery (%s): references/standards.md rule 11"
                                   % (place, ", ".join(found)))
    for fid, text in feedback:
        line = glossary_line(text)
        row = {"id": fid, "glossary": bool(line), "abbreviations": None, "not_in_glossary": []}
        if common is not None:
            # blueprint IDs ("CARD-03") are named in the reveal: they are not abbreviations
            body = BLUEPRINT_ID_RE.sub(" ", text.replace(line, " ", 1) if line else text)
            used = [token for _, _, token in engine.undefined_abbreviations([("feedback", fid, body)], common)]
            listed = set(engine.ABBREVIATION_RE.findall(line or ""))
            row["abbreviations"] = len(used)
            row["not_in_glossary"] = [token for token in used if token not in listed]
            if used and not line:
                out["problems"].append("the %s feedback uses %d abbreviation%s and does not open with the glossary "
                                       "line \"Abbreviations: …\" (references/standards.md, rule 5.3)"
                                       % (fid, len(used), "" if len(used) == 1 else "s"))
            for token in row["not_in_glossary"]:
                out["findings"].append({"rule": "5.3", "where": "the %s feedback" % fid, "detail": token})
        out["feedback"].append(row)
    out["to_review"] = len(out["findings"])
    out["ok"] = not out["problems"]
    return out


# ---------------------------------------------------------------- check, report

def run_checks(run):
    rnd = Round(run)
    checks = {"blinding": check_blinding(rnd), "saved": check_saved(rnd), "log": check_log(rnd),
              "standards": check_standards(rnd), "listening": check_listening(rnd),
              "prepared": check_prepared(rnd)}
    for name in rnd.meta.get("expect") or []:
        checks[name] = EXPECTED_CHECKS[name](rnd)
    return rnd, {"ok": all(c["ok"] for c in checks.values()), "checks": checks}


def cmd_check(args):
    _, res = run_checks(args.run)
    write_json(rp(args.run, "checks.json"), res)
    out = {"ok": res["ok"]}
    out.update({name: c["ok"] for name, c in res["checks"].items()})
    out["details"] = rp(args.run, "checks.json")
    print(json.dumps(out, indent=1))
    return 0 if res["ok"] else 1


# ---------------------------------------------------------------- clinical quality (logged only)

def quality_form(rnd):
    """What the scorer rates: every item of the round, and every feedback message as sent."""
    items, q = [], 0
    for it in rnd.items:
        case = it.get("type") in ("case", "essay")
        q += 0 if case else 1
        items.append({"id": "Case" if case else "Q%d" % q, "type": it.get("type"), "topic": it.get("topic"),
                      "about": it.get("stem_summary") or it.get("stem") or ((rnd.round.get("case") or {}).get("presentation") if case else None),
                      "answered": True, "score": None, "note": ""})
    for it in rnd.unanswered:
        items.append({"id": "Case", "type": "case", "topic": it.get("topic"), "about": "presented, not answered: "
                      "rate the case as written, if it was shown", "answered": False, "score": None, "note": ""})
    feedback = []
    if not empty_section(rnd.a.get("fb_questions")):
        feedback.append({"id": "questions", "what": "the feedback on the short questions, as sent", "score": None, "note": ""})
    if not empty_section(rnd.a.get("feedback")):
        feedback.append({"id": "final", "what": "the final feedback, as sent (the case feedback and the gap summary; "
                         "in a round without a case, the feedback that closed it)", "score": None, "note": ""})
    if (rnd.session or {}).get("grade_changes") or not empty_section(rnd.b.get("discussion")):
        feedback.append({"id": "dispute", "what": "the examiner's replies to the learner's challenge or discussion",
                         "score": None, "note": ""})
    return {"session": rnd.sid, "scorer_model": None, "items": items, "feedback": feedback,
            "overall": {"score": None, "note": ""}, "concerns": []}


def one_line(text, limit=NOTE_MAX):
    text = norm(str(text or ""))
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def valid_score(v):
    return isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5


def load_quality(rnd):
    """The scorer's filled-in form, as it goes into the report (None if there is none). Whatever is
    wrong with it is listed under `problems` and recorded; it never fails a run (ADR 0004)."""
    path = rp(rnd.run, "quality.json")
    if not os.path.exists(path):
        return None
    got = read_json(path)
    if not isinstance(got, dict):
        return {"problems": ["quality.json is not valid JSON"], "items": [], "feedback": []}
    want = quality_form(rnd)
    problems = []
    out = {"scorer_model": got.get("scorer_model"), "items": [], "feedback": []}
    for group, keep in (("items", ("id", "type", "topic", "answered")), ("feedback", ("id",))):
        rows = [r for r in got.get(group) or [] if isinstance(r, dict)]
        for w in want[group]:
            r = next((x for x in rows if x.get("id") == w["id"]), None)
            optional = group == "items" and not w.get("answered")
            if r is None or r.get("score") is None:
                if not optional:
                    problems.append("%s %s has no score" % (group, w["id"]))
                continue
            if not valid_score(r["score"]):
                problems.append("%s %s: score %s is not a whole number 1-5" % (group, w["id"], json.dumps(r["score"])))
                continue
            row = {k: w.get(k) for k in keep}
            row.update({"score": r["score"], "note": one_line(r.get("note"))})
            out[group].append(row)
        for r in rows:
            if r.get("id") not in [w["id"] for w in want[group]]:
                problems.append("%s %s is not part of this round; ignored" % (group, json.dumps(r.get("id"))))
        scores = [r["score"] for r in out[group]]
        out["%s_mean" % group.rstrip("s")] = round(sum(scores) / len(scores), 2) if scores else None
    overall = got.get("overall") if isinstance(got.get("overall"), dict) else {}
    if overall.get("score") is not None and not valid_score(overall["score"]):
        problems.append("overall: score %s is not a whole number 1-5" % json.dumps(overall["score"]))
        overall = dict(overall, score=None)
    out["score"] = overall.get("score")
    out["note"] = one_line(overall.get("note")) or None
    out["concerns"] = [one_line(c) for c in got.get("concerns") or [] if norm(str(c))][:10]
    out["problems"] = problems
    return out


def cmd_quality(args):
    """Before the scorer agent: write its form and its brief. After it: say whether the form is whole."""
    rnd = Round(args.run)
    if not rnd.items:
        raise SimError("no round in %s to score (no round.json, no saved round)" % args.run)
    path = rp(args.run, "quality.json")
    prompt = rp(args.run, "quality_prompt.md")
    if not os.path.exists(path) or args.reset:
        write_json(path, quality_form(rnd))
        write(prompt, fill(read(os.path.join(HERE, "prompts", "quality.md")), {
            "run": os.path.abspath(args.run), "form": os.path.abspath(path), "messages": rp(os.path.abspath(args.run), "messages"),
            "work": os.path.abspath(rnd.work), "store": os.path.abspath(rnd.store),
            "skill": os.path.abspath(rnd.meta.get("skill") or DEFAULT_SKILL)}))
        print(json.dumps({"ok": True, "form": path, "quality_prompt": prompt,
                          "then": "start a new agent (not the examiner, not the learner) with the quality prompt; "
                                  "when it returns, run this command again, then report"}, indent=1))
        return 0
    q = load_quality(rnd)
    print(json.dumps({"ok": not q["problems"], "form": path, "items_scored": len(q["items"]),
                      "feedback_scored": len(q["feedback"]), "item_mean": q.get("item_mean"),
                      "feedback_mean": q.get("feedback_mean"), "problems": q["problems"],
                      "note": "logged only: these scores never fail a run"}, indent=1))
    return 0


def secs(v):
    return "–" if v is None else ("%.1f" % v)


def report_markdown(rep):
    c = rep["checks"]
    mark = lambda ok: "pass" if ok else "**FAIL**"
    lines = [
        "# Simulation report: %s, %s" % (rep["persona"], rep["date"]),
        "",
        "| | |", "|---|---|",
        "| Result | %s |" % ("all automatic checks passed" if rep["ok"] else "**automatic checks failed**"),
        "| Persona | %s |" % rep["persona"],
        "| Skill version / commit | %s / %s |" % (rep.get("skill_version") or "?", rep.get("commit") or "?"),
        "| Examiner / learner model | %s / %s |" % (rep.get("examiner_model") or "not recorded", rep.get("learner_model") or "not recorded"),
        "| Round | %s: %s |" % (rep["round"].get("session") or "not saved", rep["round"].get("shape") or "unknown"),
        "| Round score (examiner's grading) | %s |" % (rep["round"].get("score") if rep["round"].get("score") is not None else "–"),
        "| Ledger settings | %s |" % ", ".join("%s=%s" % (k, json.dumps(v)) for k, v in sorted((rep.get("config") or {}).items())
                                               if k in ("helpers", "prepare_ahead", "mcqs", "focused", "case", "case_format", "item_order")),
        "| Messages | %d examiner, %d learner |" % (rep["messages"]["examiner"], rep["messages"]["learner"]),
        "| Clinical quality (logged only) | %s |" % quality_line(rep.get("quality")),
        "",
        "## Automatic checks",
        "",
        "| Check | Result | Detail |", "|---|---|---|",
        "| Blinding: no topic, diagnosis or key shown before the matching answer | %s | %d leak(s); %d topic word(s) or domain name(s) to review; %d terms searched |"
        % (mark(c["blinding"]["ok"]), c["blinding"]["leaks"], c["blinding"]["to_review"], c["blinding"]["terms_checked"]),
        "| Every file saved | %s | %s file(s) compared with the store (%s) |"
        % (mark(c["saved"]["ok"]), c["saved"].get("files_compared") if c["saved"].get("files_compared") is not None else "no",
           ", ".join(c["saved"].get("publish_set") or c["saved"].get("output_folders") or []) or "no publish set"),
        "| Log complete and verbatim | %s | sections: %s |" % (mark(c["log"]["ok"]), ", ".join(c["log"]["sections"]) or "none"),
    ]
    if "standards" in c:                  # reports written before this check have no such entry
        d = c["standards"]
        lines.append("| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | %s | "
                     "to review: %d abbreviation(s) not spelled out at first use, %d mixed time anchor(s); feedback: %s |" % (
                         mark(d["ok"]), d["abbreviations"], d["time_anchors"],
                         "; ".join("%s: %s abbreviation(s), glossary line %s%s" % (
                             f["id"], "?" if f["abbreviations"] is None else f["abbreviations"],
                             "present" if f["glossary"] else "absent",
                             ", %d not in it" % len(f["not_in_glossary"]) if f["not_in_glossary"] else "")
                             for f in d["feedback"]) or "none"))
    if "listening" in c:            # reports made before issue #50 have no such check
        d = c["listening"]
        lines.append("| Listening: a section in the final feedback, the picks in the session document | %s | %s |" % (
            mark(d["ok"]), "%d pick(s) for %d topic(s): %d from the kit, %d found after grading"
            % (d["picks"], d["topics"], d["from_kit"], d["from_search"]) if d["on"] else "turned off"))
    if "prepared" in c:             # reports made before issue #78 have no such check
        d = c["prepared"]
        pf = d.get("prepared_feedback") or {}
        lines.append("| Prepared feedback: marks before text, the feedback written from the draft | %s | %s |" % (
            mark(d["ok"]), ("%d block(s) offered: %d as prepared, %d changed, %d left out; %d element(s) marked "
                            "without the learner's words" % (pf.get("offered", 0), pf.get("as_prepared", 0),
                                                              pf.get("changed", 0), pf.get("discarded", 0),
                                                              d["unquoted"])) if pf else "no draft"))
    if "dispute" in c:
        d = c["dispute"]
        lines.append("| Persona: a settled dispute, in the log and in the grade changes | %s | %s; exchange logged under: %s |" % (
            mark(d["ok"]), "; ".join("%s %s → %s (%s)" % (g.get("item") or g.get("topic") or "?", g.get("from"), g.get("to"), g.get("outcome"))
                                     for g in d["grade_changes"]) or "no grade change", ", ".join(d["logged_in"]) or "nowhere"))
    if "stopped" in c:
        d = c["stopped"]
        lines.append("| Persona: round saved without the case, its topic still due | %s | %d item(s) saved; case topic %s, schedule %s |" % (
            mark(d["ok"]), d["items_saved"], d.get("case_topic") or "unknown",
            json.dumps(d["case_topic_schedule"]) if d.get("case_topic_schedule") else "unknown"))
    lines.append("")
    for name, title in (("blinding", "Blinding"), ("saved", "Saved files"), ("log", "Log"),
                        ("standards", "Writing standards"), ("listening", "Listening"),
                        ("prepared", "Prepared feedback"), ("dispute", "Dispute"), ("stopped", "Stopped before the case")):
        if name in c and c[name]["problems"]:
            lines += ["### %s: problems" % title, ""] + ["- %s" % p for p in c[name]["problems"]] + [""]
    if c["blinding"]["findings"]:
        lines += ["### Blinding: findings", "",
                  "| Level | Part | Kind | Term | Examiner message | Where |", "|---|---|---|---|---|---|"]
        for f in c["blinding"]["findings"]:
            lines.append("| %s | %s | %s | %s | %d | %s |" % ("leak" if f["level"] == "fail" else "review", f["part"], f["kind"],
                                                             f["term"].replace("|", "/"), f["message"], f["excerpt"].replace("|", "/")))
        lines.append("")
    if (c.get("standards") or {}).get("findings"):
        lines += ["### Writing standards: to review", "",
                  "Found by the lint's heuristics (`references/standards.md`, \"The lint\"): each is for a person to "
                  "judge and none fails the run.", "",
                  "| Rule | Where | What |", "|---|---|---|"]
        lines += ["| %s | %s | %s |" % (f["rule"], f["where"], f["detail"].replace("|", "/")) for f in c["standards"]["findings"]]
        lines.append("")
    if c["log"]["examiner_text_not_logged"]:
        lines += ["### Examiner text that is not in the log", "",
                  "Opening lines, the close message and prompts are not logged by design; a feedback or case "
                  "paragraph here would be a finding.", ""]
        lines += ["- message %d: %s…" % (u["message"], u["starts"]) for u in c["log"]["examiner_text_not_logged"]] + [""]
    t = rep["timings"]
    lines += ["## Waiting time per step", "",
              "Wait: from the learner's message to the examiner's first message after it (includes the relay). "
              "Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.",
              "",
              "| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) |", "|---|---|---|---|---|---|---|"]
    for s in t["steps"]:
        lines.append("| %d | %s | %s | %s | %d | %d | %s |" % (s["step"], s["label"], secs(s["wait_s"]), secs(s["turn_s"]),
                                                             s["examiner_messages"], s["examiner_chars"], secs(s["learner_s"])))
    lines += ["", "Total wait %s s; longest wait %s s; whole run %s s." % (secs(t["total_wait_s"]), secs(t["longest_wait_s"]), secs(t["elapsed_s"])), ""]
    q = rep.get("quality") or {}
    if q.get("items") or q.get("feedback") or q.get("problems"):
        cell = lambda v: str(v if v is not None else "").replace("|", "/")
        lines += ["## Clinical quality", "",
                  "Scored 1–5 by a separate agent after the round%s. Kept for comparison over time; it is "
                  "never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`)." % (
                      " (%s)" % q["scorer_model"] if q.get("scorer_model") else ""), "",
                  "| | What | Score | Note |", "|---|---|---|---|"]
        for r in q.get("items") or []:
            lines.append("| Item | %s (%s, %s%s) | %d | %s |" % (r["id"], r.get("type") or "?", r.get("topic") or "?",
                                                              "" if r.get("answered", True) else ", not answered", r["score"], cell(r.get("note"))))
        for r in q.get("feedback") or []:
            lines.append("| Feedback | %s | %d | %s |" % (r["id"], r["score"], cell(r.get("note"))))
        lines += ["", "Mean: items %s, feedback %s." % (q.get("item_mean") if q.get("item_mean") is not None else "–",
                                                         q.get("feedback_mean") if q.get("feedback_mean") is not None else "–"), ""]
        if q.get("concerns"):
            lines += ["For a clinician to look at:", ""] + ["- %s" % x for x in q["concerns"]] + [""]
        if q.get("problems"):
            lines += ["The scorer's form was incomplete (recorded, not a failure):", ""] + ["- %s" % x for x in q["problems"]] + [""]
    if rep.get("note"):
        lines += ["## Notes", "", rep["note"], ""]
    return "\n".join(lines)


def quality_line(q):
    if not q:
        return "not scored"
    parts = []
    if q.get("item_mean") is not None:
        parts.append("items %s/5 (n=%d)" % (q["item_mean"], len(q["items"])))
    if q.get("feedback_mean") is not None:
        parts.append("feedback %s/5 (n=%d)" % (q["feedback_mean"], len(q["feedback"])))
    if q.get("score") is not None:
        parts.append("overall %s/5" % q["score"])
    return (", ".join(parts) or "not scored") + (" — " + q["note"].replace("|", "/") if q.get("note") else "")


def confident_misses(items):
    """Items answered `sure` and wrong: what the weak, overconfident persona should produce."""
    n = 0
    for it in items:
        sure = str(it.get("confidence") or "").lower() == "sure"
        if it.get("type") == "mcq":
            n += 1 if sure and it.get("correct") is False else 0
        else:
            n += 1 if sure and isinstance(it.get("mastery"), (int, float)) and it["mastery"] <= 2 else 0
    return n


def cmd_report(args):
    rnd, res = run_checks(args.run)
    write_json(rp(args.run, "checks.json"), res)
    kinds = [it.get("type") for it in rnd.items]
    shape = ", ".join(x for x in (
        "%d MCQ" % kinds.count("mcq") if kinds.count("mcq") else "",
        "%d focused" % kinds.count("focused") if kinds.count("focused") else "",
        ("case (%s)" % ("two stages" if rnd.two_stage else "one step")) if rnd.has_case else "") if x)
    date = (rnd.meta.get("created") or dt.date.today().isoformat())[:10]
    quality = load_quality(rnd)
    if args.quality is not None:          # an overall score given by hand stands beside (or without) the scorer's
        quality = dict(quality or {}, score=args.quality, note=args.quality_note)
    elif quality and args.quality_note:
        quality["note"] = args.quality_note
    rep = {
        "schema": 2, "ok": res["ok"], "date": date, "persona": rnd.meta.get("persona"),
        "skill_version": rnd.meta.get("skill_version"), "commit": rnd.meta.get("commit"),
        "examiner_model": args.examiner_model, "learner_model": args.learner_model,
        "config": rnd.state.get("config") or rnd.meta.get("config"),
        "round": {"session": rnd.sid if rnd.doc else None, "shape": shape or None,
                  "score": (rnd.doc or {}).get("score"), "confident_misses": confident_misses(rnd.items),
                  "continued_from_earlier_run": bool(rnd.meta.get("continued_from"))},
        "messages": {r: sum(1 for m in rnd.messages if m["role"] == r) for r in ROLES},
        "checks": res["checks"], "timings": timings(rnd),
        "quality": quality,
        "note": args.note,
    }
    out_dir = os.path.abspath(args.out_dir or os.path.join(HERE, "reports"))
    base = "%s-%s" % (date, rep["persona"])
    name, k = base, 1
    while os.path.exists(os.path.join(out_dir, name + ".md")) or os.path.exists(os.path.join(out_dir, name + ".json")):
        k += 1
        name = "%s-%d" % (base, k)
    write_json(os.path.join(out_dir, name + ".json"), rep)
    write(os.path.join(out_dir, name + ".md"), report_markdown(rep))
    print(json.dumps({"ok": rep["ok"], "report": os.path.join(out_dir, name + ".md"),
                      "data": os.path.join(out_dir, name + ".json"),
                      "checks": {k2: v["ok"] for k2, v in res["checks"].items()},
                      "longest_wait_s": rep["timings"]["longest_wait_s"],
                      "quality": {k: quality.get(k) for k in ("item_mean", "feedback_mean", "score")} if quality else None},
                     indent=1))
    return 0


def cmd_history(args):
    """One line per saved report, oldest first: the checks and the quality scores side by side."""
    folder = os.path.abspath(args.reports or os.path.join(HERE, "reports"))
    def order(name):                      # <date>-<persona>, then <date>-<persona>-2, -3, …
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.*?)(?:-(\d+))?\.json$", name)
        return (m.group(1), m.group(2), int(m.group(3) or 1)) if m else (name, "", 0)

    names = sorted((n for n in os.listdir(folder) if n.endswith(".json")), key=order) if os.path.isdir(folder) else []
    rows = []
    for n in names:
        r = read_json(os.path.join(folder, n))
        if not isinstance(r, dict) or "checks" not in r:
            continue
        if args.persona and r.get("persona") != args.persona:
            continue
        q = r.get("quality") or {}
        failed = [k for k, c in r["checks"].items() if not c.get("ok")]
        rows.append({"report": n[:-5], "persona": r.get("persona"), "skill_version": r.get("skill_version"),
                     "commit": r.get("commit"), "checks": "pass" if not failed else "FAIL: " + ", ".join(failed),
                     "round_score": (r.get("round") or {}).get("score"), "quality_items": q.get("item_mean"),
                     "quality_feedback": q.get("feedback_mean"), "quality_overall": q.get("score"),
                     "longest_wait_s": (r.get("timings") or {}).get("longest_wait_s")})
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    show = lambda v: "–" if v is None else str(v)
    print("| Report | Persona | Version / commit | Checks | Round score | Quality: items | feedback | overall | Longest wait (s) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| %s | %s | %s / %s | %s | %s | %s | %s | %s | %s |" % (
            r["report"], show(r["persona"]), show(r["skill_version"]), show(r["commit"]), r["checks"], show(r["round_score"]),
            show(r["quality_items"]), show(r["quality_feedback"]), show(r["quality_overall"]), show(r["longest_wait_s"])))
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init", help="make a run folder with a seeded folder store and the two briefs")
    s.add_argument("--persona", default="strong"); s.add_argument("--run"); s.add_argument("--skill")
    s.add_argument("--today"); s.add_argument("--config"); s.add_argument("--prepare-ahead", action="store_true")
    s.add_argument("--from-run", help="continue on the store of an earlier run (a second round)")
    s.add_argument("--runs-dir", help="where a run folder is made when --run is not given (default sim/runs/)")
    s.add_argument("--stamp", help=argparse.SUPPRESS)   # tests: the start second, to make two runs share it
    s.add_argument("--opening"); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("send", help="send a message file to the other side")
    s.add_argument("--run", required=True); s.add_argument("--role", choices=ROLES, required=True)
    s.add_argument("--file", required=True); s.add_argument("--ts", type=float, help=argparse.SUPPRESS)
    s.set_defaults(fn=cmd_send)
    s = sub.add_parser("next", help="after an agent's turn: what to hand to the other agent")
    s.add_argument("--run", required=True); s.add_argument("--after", choices=ROLES, required=True)
    s.add_argument("--ts", type=float, help=argparse.SUPPRESS); s.set_defaults(fn=cmd_next)
    s = sub.add_parser("check", help="run the automatic checks (exit 1 if any fails)")
    s.add_argument("--run", required=True); s.set_defaults(fn=cmd_check)
    s = sub.add_parser("quality", help="write the quality scorer's form and brief; run again to check the filled form")
    s.add_argument("--run", required=True); s.add_argument("--reset", action="store_true", help="write a fresh form")
    s.set_defaults(fn=cmd_quality)
    s = sub.add_parser("history", help="one line per saved report: checks and quality scores over time")
    s.add_argument("--reports"); s.add_argument("--persona"); s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_history)
    s = sub.add_parser("report", help="checks + timings + quality scores, written to sim/reports/")
    s.add_argument("--run", required=True); s.add_argument("--out-dir")
    s.add_argument("--examiner-model"); s.add_argument("--learner-model")
    s.add_argument("--quality", type=int, choices=range(1, 6), help="overall clinical quality 1-5 given by hand, logged only (ADR 0004)")
    s.add_argument("--quality-note"); s.add_argument("--note"); s.set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except SimError as e:
        sys.stderr.write("error: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

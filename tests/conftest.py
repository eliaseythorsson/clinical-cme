"""Shared fixtures: run cme.py as the assistant does, in a scratch folder.

Every engine call goes through `run_script`: by default it runs the script's `main(argv)` in this
process (issue #73), isolated the way a separate `python script.py …` process is; with
CME_TEST_SUBPROCESS=1 in the environment every call is a real process, as the assistant runs it.
The few tests that need a real process whatever the switch says pass `process=True`."""
import builtins
import io
import json
import os
import shutil
import subprocess
import sys
import traceback
import types
import warnings

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "clinical-cme")
CME = os.path.join(SKILL, "scripts", "cme.py")
SIM = os.path.join(ROOT, "sim", "simulate.py")
# The default blueprint as it was before the two-level one (issue #82), frozen: most tests plan on a
# fresh ledger and expect its topics. Tests of the shipped default read DEFAULT_BLUEPRINT.
BLUEPRINT = os.path.join(ROOT, "tests", "one_level", "blueprint.json")
DEFAULT_BLUEPRINT = os.path.join(SKILL, "templates", "blueprint.json")

SUBPROCESS = os.environ.get("CME_TEST_SUBPROCESS") == "1"

# ---- running a script: in this process, or as its own process

_compiled = {}


def _code(script):
    """The script compiled once per version of its file: compiling cme.py is most of what a new
    process costs. Each call still executes it afresh into a new module."""
    st = os.stat(script)
    key = (script, st.st_mtime_ns, st.st_size)
    if key not in _compiled:
        with open(script, "rb") as fh:
            _compiled[key] = compile(fh.read(), script, "exec", dont_inherit=True)
    return _compiled[key]


def _newlines(text):
    """What text mode (universal newlines) makes of a pipe's content, as subprocess.run(text=True)
    reads the child's output. (The child reads its standard input untranslated.)"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _exit_status(code, stderr):
    """What `sys.exit(code)` leaves as the process's exit status."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code & 0xFF
    stderr.write("%s\n" % code)
    return 1


def _show_warning(message, category, filename, lineno, file=None, line=None):
    sys.stderr.write(warnings.formatwarning(message, category, filename, lineno, line))


def _in_process(script, args, cwd, input):
    """`python script args` without a new process: a fresh module from the script (no state kept
    from an earlier call), its own standard input (empty unless given), standard output and error
    captured, argv, working folder, environment and warning filters as a new process has them and
    all put back afterwards, and the exit status `sys.exit(main())` would leave, a traceback on
    standard error and status 1 for an uncaught exception."""
    name = "_under_test_" + os.path.splitext(os.path.basename(script))[0]
    module = types.ModuleType(name)
    module.__file__ = script
    module.__builtins__ = builtins
    out, err = io.StringIO(), io.StringIO()
    saved = (sys.stdin, sys.stdout, sys.stderr, sys.argv, os.getcwd(), dict(os.environ), sys.modules.get(name))
    sys.modules[name] = module
    try:
        sys.stdin = io.StringIO(input or "", newline="")
        sys.stdout, sys.stderr = out, err
        sys.argv = [script, *args]
        if cwd is not None:
            os.chdir(cwd)
        with warnings.catch_warnings():
            # the filters of a fresh interpreter (no -W, no PYTHONWARNINGS), printed to its stderr
            warnings.resetwarnings()
            for category in (DeprecationWarning, PendingDeprecationWarning, ImportWarning, ResourceWarning):
                warnings.simplefilter("ignore", category)
            warnings.filterwarnings("default", category=DeprecationWarning, module=name)
            warnings.showwarning = _show_warning
            try:
                exec(_code(script), module.__dict__)
                if hasattr(module, "run_engine"):           # sim/simulate.py: its engine calls too
                    module.run_engine = run_script
                code = module.main(list(args))
            except SystemExit as e:
                code = e.code
            except Exception:                               # noqa: BLE001 - as the interpreter reports it
                traceback.print_exc()
                code = 1
            status = _exit_status(code, err)
    finally:
        sys.stdin, sys.stdout, sys.stderr, sys.argv = saved[:4]
        os.chdir(saved[4])
        if dict(os.environ) != saved[5]:
            os.environ.clear()
            os.environ.update(saved[5])
        if saved[6] is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = saved[6]
    return subprocess.CompletedProcess([sys.executable, script, *args], status,
                                       _newlines(out.getvalue()), _newlines(err.getvalue()))


def run_script(script, args, cwd=None, input=None, process=None, env=None):
    """Run a Python script with these arguments; returns a subprocess.CompletedProcess (returncode,
    stdout, stderr). In this process unless CME_TEST_SUBPROCESS=1 or `process=True` (or an `env`,
    which only a process can have)."""
    args = [str(a) for a in args]
    if process or env is not None or (process is None and SUBPROCESS):
        return subprocess.run([sys.executable, script, *args], capture_output=True, text=True, cwd=cwd,
                              input=input, env=env)
    return _in_process(script, args, cwd, input)

ROUND = {
    "log_id": "S0001", "case_format": "unfolding", "title": "t", "summary": "s", "tags": ["x"],
    "items": [
        {"type": "case", "topic": "GEN-11", "mastery": 2, "confidence": "sure",
         "coding": {"art": {"DG": 1}, "idea": {"I": 2, "D": 1, "E": 1, "A": 0}, "errors": []}},
        {"type": "focused", "topic": "PULM-04", "mastery": 4, "confidence": "unsure", "aspect": "diagnosis",
         "stem_summary": "x", "coding": {"art": {"DDX": 2}, "errors": []}},
        {"type": "mcq", "topic": "HEME-01", "mastery": 5, "correct": True, "confidence": "guess",
         "stem_summary": "x", "coding": {"errors": []}},
        {"type": "mcq", "topic": "NEURO-04", "mastery": 1, "correct": False, "confidence": "sure",
         "stem_summary": "x", "coding": {"errors": []}},
    ],
    "gaps": [{"topic": "GEN-11", "gap": "g", "source": "graded"}],
    "case": {"patient": "60M", "diagnosis": "d"},
}
REFLECTION = {"topic_comfort": {"GEN-11": 4, "HEME-01": 5}, "performance": 3, "solid": "a", "gaps": "b"}
SEALED_CASE = """KEY: Diagnosis: SECRET-DIAGNOSIS
<!-- present: case -->
A 60-year-old man with ...
<!-- /present -->
<!-- bank -->
CT abdomen: RESULT-TEXT
<!-- /bank -->
"""
SEALED_QUESTIONS = """KEY Q1: B
<!-- present: questions -->
Q1. stem ... A B C
<!-- /present -->
"""
ANSWERS = """<!-- answers: questions -->
Q1 B sure
<!-- /answers -->
<!-- answers: case -->
order CT
<!-- /answers -->
<!-- answers: final -->
treat
<!-- /answers -->
"""


# The mix these tests set up with (three MCQs and the case, 20-minute sessions): the suite was
# written around it. What a new learner gets by default is tested in tests/test_learner_settings.py.
MIX = {"mcqs": 3, "focused": 0, "case": True, "session_minutes": 20}


class Work:
    """A scratch work folder, with the learner's folder store read into store/ as a session has
    it, plus a helper that runs cme.py and parses its JSON output. `process=True`: every call is a
    real process even without CME_TEST_SUBPROCESS."""

    process = None

    def __init__(self, path):
        self.path = str(path)

    def p(self, *parts):
        return os.path.join(self.path, *parts)

    def store(self, *parts):
        """A file of the store copy (the store as the session read it)."""
        return self.p("store", *parts)

    def pub(self, *parts):
        """A file of the publish set."""
        return self.p("publish", *parts)

    @property
    def ledger(self):
        return self.store("data", "state.json")

    def write(self, name, content):
        os.makedirs(os.path.dirname(self.p(name)), exist_ok=True)
        with open(self.p(name), "w", encoding="utf-8") as fh:
            fh.write(content if isinstance(content, str) else json.dumps(content))
        return self.p(name)

    def read_json(self, *parts):
        with open(self.p(*parts), encoding="utf-8") as fh:
            return json.load(fh)

    def read_ledger(self):
        return self.read_json("store", "data", "state.json")

    def write_ledger(self, st):
        return self.write(os.path.join("store", "data", "state.json"), st)

    def run(self, *args, ok=True, input=None):
        r = run_script(CME, args, cwd=self.path, input=input, process=self.process)
        if ok:
            assert r.returncode == 0, r.stderr + r.stdout
        return r

    def run_json(self, *args):
        return json.loads(self.run(*args).stdout)

    def publish(self):
        """The publish set written into the folder store (store/) by the engine's folder adapter
        (`publish`): every file at its store path, in write order, after the check that the folder's
        ledger is the one this job read or last wrote. Returns the store paths written."""
        return self.run_json("publish", "--work", self.path, "--to", self.store())["written"]

    def forget_job(self):
        """A new session: nothing of the job is left in the work folder but the store copy."""
        for name in os.listdir(self.path):
            if name != "store":
                full = self.p(name)
                shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)

    def init(self, today="2026-11-01", config=None, profile=None, mix=MIX):
        """Set up a new learner and publish the first ledger into the store copy; returns the
        ledger's path there. The round mix is MIX unless `config` says otherwise (`mix=None`:
        the engine's own default for a new learner)."""
        self.run("--today", today, "init", "--work", self.path, "--blueprint", BLUEPRINT,
                 "--config", json.dumps(dict(mix or {}, **(config or {}))), "--profile", json.dumps(profile or {}))
        self.publish()
        self.forget_job()
        return self.ledger

    def open(self, *extra, today=None):
        return self.run_json(*(("--today", today) if today else ()), "open", "--work", self.path,
                             "--store", self.store(), *extra)

    def start(self, today, *extra):
        return self.run_json("--today", today, "start", "--work", self.path, "--store", self.store(), *extra)

    def save_round(self, today, rnd=None):
        if not os.path.exists(self.p("work.json")):
            self.open(today=today)
        self.write("round.json", rnd or ROUND)
        self.write("sealed_case.md", SEALED_CASE)
        self.write("sealed_questions.md", SEALED_QUESTIONS)
        self.write("answers.md", ANSWERS)
        self.write("feedback.md", "Feedback text")
        return self.run_json("--today", today, "save", "--work", self.path)

    def close_round(self, today, reflection=None):
        self.write("reflection.json", reflection or REFLECTION)
        self.write("B.md", "Reflection verbatim")
        return self.run_json("--today", today, "close", "--work", self.path)


@pytest.fixture
def work(tmp_path):
    return Work(tmp_path)

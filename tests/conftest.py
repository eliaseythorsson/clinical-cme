"""Shared fixtures: run cme.py as the assistant does, in a scratch folder."""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "clinical-cme")
CME = os.path.join(SKILL, "scripts", "cme.py")
BLUEPRINT = os.path.join(SKILL, "templates", "blueprint.json")

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


class Work:
    """A scratch work folder, with the learner's folder store read into store/ as a session has
    it, plus a helper that runs cme.py and parses its JSON output."""

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

    def run(self, *args, ok=True):
        r = subprocess.run([sys.executable, CME, *args], capture_output=True, text=True, cwd=self.path)
        if ok:
            assert r.returncode == 0, r.stderr + r.stdout
        return r

    def run_json(self, *args):
        return json.loads(self.run(*args).stdout)

    def publish(self):
        """What the assistant does with the publish set: every file to its store path, in the
        manifest's order. Returns the store paths written."""
        manifest = self.read_json("publish.json")
        for f in manifest["files"]:
            dst = self.store(*f["as"].split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(f["path"], dst)
        return [f["as"] for f in manifest["files"]]

    def forget_job(self):
        """A new session: nothing of the job is left in the work folder but the store copy."""
        for name in os.listdir(self.path):
            if name != "store":
                full = self.p(name)
                shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)

    def init(self, today="2026-11-01", config=None, profile=None):
        """Set up a new learner and publish the first ledger into the store copy; returns the
        ledger's path there."""
        self.run("--today", today, "init", "--work", self.path, "--blueprint", BLUEPRINT,
                 "--config", json.dumps(config or {}), "--profile", json.dumps(profile or {}))
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

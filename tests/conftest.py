"""Shared fixtures: run cme.py as the assistant does, in a scratch folder."""
import json
import os
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
    """A scratch work folder plus a helper that runs cme.py and parses its JSON output."""

    def __init__(self, path):
        self.path = str(path)

    def p(self, *parts):
        return os.path.join(self.path, *parts)

    def write(self, name, content):
        with open(self.p(name), "w", encoding="utf-8") as fh:
            fh.write(content if isinstance(content, str) else json.dumps(content))
        return self.p(name)

    def read_json(self, *parts):
        with open(self.p(*parts), encoding="utf-8") as fh:
            return json.load(fh)

    def run(self, *args, ok=True):
        r = subprocess.run([sys.executable, CME, *args], capture_output=True, text=True, cwd=self.path)
        if ok:
            assert r.returncode == 0, r.stderr + r.stdout
        return r

    def run_json(self, *args):
        return json.loads(self.run(*args).stdout)

    def init(self, today="2026-11-01", config=None):
        self.run("--today", today, "init", "--blueprint", BLUEPRINT,
                 "--config", json.dumps(config or {}), "--out", self.p("state.json"))
        return self.p("state.json")

    def save_round(self, today, rnd=None, state=None):
        self.write("round.json", rnd or ROUND)
        self.write("sealed_case.md", SEALED_CASE)
        self.write("sealed_questions.md", SEALED_QUESTIONS)
        self.write("answers.md", ANSWERS)
        self.write("feedback.md", "Feedback text")
        return self.run_json("--today", today, "save", state or self.p("state.json"), "--round", self.p("round.json"),
                             "--sealed", self.p("sealed_questions.md"), self.p("sealed_case.md"),
                             "--answers", self.p("answers.md"), "--feedback", self.p("feedback.md"),
                             "--out-dir", self.p("out1"))

    def close_round(self, today, reflection=None):
        self.write("refl.json", reflection or REFLECTION)
        self.write("B.md", "Reflection verbatim")
        return self.run_json("--today", today, "close", self.p("out1", "data", "state.json"),
                             "--reflection", self.p("refl.json"), "--md", self.p("B.md"),
                             "--doc", self.p("out1", "data", "sessions", "S0001.json"),
                             "--out-dir", self.p("out2"))


@pytest.fixture
def work(tmp_path):
    return Work(tmp_path)

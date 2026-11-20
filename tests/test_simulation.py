"""The simulation harness (sim/simulate.py) on a scripted round: no LLM anywhere.

A scripted examiner drives cme.py through one full round on the run's folder store, sending
through the harness as the examiner agent would; a scripted learner answers. Then each automatic
check is shown to pass on the clean round and to fail when the matching fault is injected."""
import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import CME, ROOT

SIM = os.path.join(ROOT, "sim", "simulate.py")
TODAY = "2026-11-01"

SEALED_QUESTIONS = """## Keys

Q1 — HEME-01 Anaemia work-up. Correct: B, because the ferritin settles it in this setting.
Q2 — NEURO-04 focused. Best answer: image first, then decide on lumbar puncture afterwards.

## Verification list
- guideline for the first key, current edition and threshold

<!-- present: questions -->
Question 1. A 54-year-old woman is tired. Which test first?
A. Test one  B. Test two  C. Test three

Question 2 — focused. A 30-year-old man has the worst headache of his life. What now, and why?

Answer with a letter and a confidence word for Q1, and a few lines for Q2.
<!-- /present -->
"""
SEALED_CASE = """## Key

GEN-11. Diagnosis: Fictitious secretitis
Decisive test: the special scan, which shows the lesion in every such patient.

<!-- bank -->
Special scan: a lesion is seen.
Blood count: normal.
Add if not ordered: special scan
Course: stable overnight.
Stage 2 questions: 1. Your diagnosis? 2. Your treatment?
<!-- /bank -->

<!-- present: case -->
Case

A 60-year-old man comes to the emergency department with three days of malaise.

What is your differential, and which tests do you order now?
<!-- /present -->
"""
STAGE2 = """Stage 2

Special scan: a lesion is seen.
Blood count: normal.

Course: stable overnight.

1. Your diagnosis? 2. Your treatment?
"""
FEEDBACK_Q = """Feedback on the questions

Q1 was about the anaemia work-up: B is right, because the ferritin settles it in this setting.

Q2: image first. Well reasoned.

The case follows.
"""
FEEDBACK = """Case feedback

This was Fictitious secretitis. The special scan is the decisive test, and you ordered it.

Gap summary: one point on treatment duration.

Reflection: comfort per topic 1-5, your own rating 1-5, what felt solid, what felt shaky?
"""
CLOSE = "Saved as S0001. Two items come back over the next days. Next session fits on Tuesday.\n"
ANSWERS = {
    "questions": "Q1 B sure - ferritin first\nQ2 CT head now, LP if negative; thunderclap so SAH until excluded",
    "case": "Ddx: infection, malignancy, inflammatory.\nTests: special scan, blood count.",
    "final": "1. secretitis 2. treat for a week",
    "reflection": "Comfort: 4 4 5. Own rating 4. Solid: headache. Shaky: treatment duration.",
}
ROUND = {
    "log_id": "S0001", "case_format": "unfolding", "title": "Malaise in a 60-year-old — fictitious secretitis",
    "summary": "s", "tags": ["x"],
    "items": [
        {"type": "mcq", "topic": "HEME-01", "mastery": 5, "correct": True, "confidence": "sure",
         "stem_summary": "x", "coding": {"errors": []}},
        {"type": "focused", "topic": "NEURO-04", "mastery": 4, "confidence": "sure", "aspect": "testing",
         "stem_summary": "x", "coding": {"art": {"TEST": 2}, "errors": []}},
        {"type": "case", "topic": "GEN-11", "mastery": 4, "confidence": "sure",
         "coding": {"art": {"DG": 2}, "idea": {"I": 3, "D": 2, "E": 1, "A": 1}, "errors": []}},
    ],
    "gaps": [{"topic": "GEN-11", "gap": "treatment duration", "source": "graded"}],
    "case": {"patient": "60M", "diagnosis": "Fictitious secretitis"},
}
PART_B = """### Reflection (verbatim)

%s

### Discussion (verbatim)

None.

### Grade changes

None.

### Coded analysis

DG 2 · one bullet per item.
""" % ANSWERS["reflection"]


def sim(*args, ok=True):
    r = subprocess.run([sys.executable, SIM, *args], capture_output=True, text=True)
    if ok:
        assert r.returncode == 0, r.stderr + r.stdout
    return r


def sim_json(*args):
    return json.loads(sim(*args).stdout)


def cme(*args):
    r = subprocess.run([sys.executable, CME, *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    return r.stdout


class Script:
    """One scripted round in a run folder. `faults` names what to do wrong."""

    def __init__(self, tmp_path, faults=()):
        self.run = str(tmp_path / "run")
        self.reports = str(tmp_path / "reports")
        self.faults = set(faults)
        self.clock = 1000.0
        sim("init", "--persona", "strong", "--run", self.run, "--today", TODAY)
        self.work = os.path.join(self.run, "work")
        self.store = os.path.join(self.run, "store")
        self.n = 0

    def p(self, *parts):
        return os.path.join(self.work, *parts)

    def put(self, name, text):
        os.makedirs(os.path.dirname(self.p(name)), exist_ok=True)
        with open(self.p(name), "w", encoding="utf-8") as fh:
            fh.write(text if isinstance(text, str) else json.dumps(text))
        return self.p(name)

    def send(self, role, text, after):
        self.clock += after
        self.n += 1
        path = self.put("outbox/%02d.md" % self.n, text)
        return sim_json("send", "--run", self.run, "--role", role, "--file", path, "--ts", str(self.clock))

    def turn_end(self, role, after=0.0):
        self.clock += after
        return sim_json("next", "--run", self.run, "--after", role, "--ts", str(self.clock))

    def store_files(self, out_dir, skip=()):
        for root, _, names in os.walk(os.path.join(out_dir, "data")):
            for n in names:
                if n in skip:
                    continue
                dest = os.path.join(self.store, os.path.relpath(os.path.join(root, n), out_dir))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(os.path.join(root, n), dest)

    def play(self):
        state = os.path.join(self.store, "data", "state.json")
        index = os.path.join(self.store, "data", "index.json")
        # the harness set the clock of message 1 itself; pin it for the timing assertions
        lines = open(os.path.join(self.run, "transcript.jsonl")).read().splitlines()
        first = json.loads(lines[0]); first["ts"] = self.clock
        with open(os.path.join(self.run, "transcript.jsonl"), "w") as fh:
            fh.write(json.dumps(first) + "\n")
        self.put("sealed_questions.md", SEALED_QUESTIONS)
        self.put("sealed_case.md", SEALED_CASE)
        # turn 1: questions out
        opening = "Today's round: two questions, then one case."
        if "leak_id" in self.faults:
            opening += " (Q1 is HEME-01.)"
        if "leak_key" in self.faults:
            opening += " Correct: B, because the ferritin settles it in this setting."
        if "topic_word" in self.faults:
            opening += " Think about anaemia."
        self.send("examiner", opening + "\n\n" + cme("present", self.p("sealed_questions.md"), "--block", "questions"), 20)
        assert self.turn_end("examiner", 5)["deliver_to"] == "learner"
        # turn 2: answers -> feedback, then the case
        self.send("learner", ANSWERS["questions"], 60)
        self.turn_end("learner")
        fbq = FEEDBACK_Q
        if "leak_diagnosis" in self.faults:
            fbq = fbq.replace("The case follows.", "The case follows (it is fictitious  secretitis).")
        self.send("examiner", fbq, 30)
        self.send("examiner", cme("present", self.p("sealed_case.md"), "--block", "case"), 1)
        self.put("feedback_questions.md", fbq)
        self.turn_end("examiner", 9)
        # turn 3: Stage 1 answer -> Stage 2
        self.send("learner", ANSWERS["case"], 90)
        self.turn_end("learner")
        self.send("examiner", STAGE2, 12)
        self.put("sealed_case.md", SEALED_CASE + "\n<!-- present: stage2 -->\n" + STAGE2 + "<!-- /present -->\n")
        self.turn_end("examiner", 2)
        # turn 4: final answers -> feedback, first save
        self.send("learner", ANSWERS["final"], 45)
        self.turn_end("learner")
        self.send("examiner", FEEDBACK, 40)
        logged = dict(ANSWERS)
        if "retyped_answer" in self.faults:
            logged["case"] = "Differential: infection, malignancy, inflammatory. Tests: special scan and a blood count."
        feedback = FEEDBACK.replace("you ordered it", "you asked for it") if "retyped_feedback" in self.faults else FEEDBACK
        self.put("feedback.md", feedback)
        self.put("answers.md", "".join("<!-- answers: %s -->\n%s\n<!-- /answers -->\n" % (k, logged[k])
                                       for k in ("questions", "case", "final")))
        self.put("round.json", ROUND)
        cme("--today", TODAY, "save", state, "--round", self.p("round.json"),
            "--sealed", self.p("sealed_questions.md"), self.p("sealed_case.md"), "--answers", self.p("answers.md"),
            "--feedback-questions", self.p("feedback_questions.md"), "--feedback", self.p("feedback.md"),
            "--index", index, "--out-dir", self.p("out1"))
        self.store_files(self.p("out1"))
        assert self.turn_end("examiner", 15)["round_closed"] is False
        if "stop_before_reflection" in self.faults:
            return self
        # turn 5: reflection -> close, final save
        self.send("learner", ANSWERS["reflection"], 30)
        self.turn_end("learner")
        self.put("reflection.json", {"topic_comfort": {"GEN-11": 4}, "performance": 4, "solid": "a", "gaps": "b"})
        self.put("B.md", PART_B)
        cme("--today", TODAY, "close", self.p("out1", "data", "state.json"), "--reflection", self.p("reflection.json"),
            "--md", self.p("B.md"), "--doc", self.p("out1", "data", "sessions", "S0001.json"),
            "--index", self.p("out1", "data", "index.json"), "--out-dir", self.p("out2"))
        self.send("examiner", CLOSE, 25)
        self.store_files(self.p("out2"), skip=("S0001.json",) if "session_not_saved" in self.faults else ())
        assert self.turn_end("examiner", 10)["stop"] is False
        last = self.turn_end("learner", 5)          # the learner has nothing to add
        assert last["stop"] is True and last["round_closed"] is True
        return self

    def report(self, *extra):
        out = sim_json("report", "--run", self.run, "--out-dir", self.reports, *extra)
        with open(out["data"], encoding="utf-8") as fh:
            return out, json.load(fh)


@pytest.fixture
def script(tmp_path):
    return lambda *faults: Script(tmp_path, faults).play()


def test_init_seeds_a_folder_store_and_both_briefs(tmp_path):
    run = str(tmp_path / "run")
    out = sim_json("init", "--persona", "strong", "--run", run, "--today", TODAY)
    st = json.load(open(os.path.join(run, "store", "data", "state.json")))
    assert st["profile"]["onboarded_at"] == TODAY and st["profile"]["specialty"] == "internal medicine"
    assert st["config"]["helpers"] is False and st["config"]["prepare_ahead"] is False
    assert os.path.isfile(os.path.join(run, "store", "data", "index.json"))
    examiner = open(out["examiner_prompt"]).read()
    learner = open(out["learner_prompt"]).read()
    assert os.path.join(run, "store") in examiner and "SKILL.md" in examiner
    assert "{" not in examiner and "{" not in learner            # every placeholder filled
    assert "strong.md" in learner and "strong" not in examiner   # the examiner is not told the persona
    assert os.path.join(run, "store") in open(out["first_message"]).read()
    assert sim("init", "--run", run, ok=False).returncode == 2   # never reuse a run folder
    assert sim("init", "--persona", "nobody", "--run", str(tmp_path / "x"), ok=False).returncode == 2


def test_clean_round_passes_every_check_and_the_report_is_written(script):
    s = script()
    out, rep = s.report("--examiner-model", "model-a", "--learner-model", "model-b", "--quality", "4",
                        "--quality-note", "sound")
    assert out["ok"] is True and rep["ok"] is True
    assert out["checks"] == {"blinding": True, "saved": True, "log": True}
    assert rep["checks"]["blinding"]["leaks"] == 0
    assert rep["checks"]["blinding"]["seal_lifted_at"] == {"questions": 3, "case": 8}
    assert rep["checks"]["saved"]["output_folders"] == ["out1", "out2"]
    assert rep["round"] == {"session": "S0001", "shape": "1 MCQ, 1 focused, case (two stages)", "score": rep["round"]["score"],
                            "continued_from_earlier_run": False}
    assert rep["quality"] == {"score": 4, "note": "sound"}
    md = open(out["report"], encoding="utf-8").read()
    assert "all automatic checks passed" in md and "## Waiting time per step" in md and "model-a / model-b" in md
    # the report holds results, not the round: no answer or feedback text
    assert "thunderclap" not in md and "Gap summary" not in md
    assert sim("check", "--run", s.run).returncode == 0
    # a second report of the same day and persona does not overwrite the first
    out2, _ = s.report()
    assert out2["report"] != out["report"] and os.path.exists(out["report"])


def test_waiting_time_is_recorded_per_step(script):
    _, rep = script().report()
    steps = rep["timings"]["steps"]
    assert [s["label"] for s in steps] == ["start of round", "after the answers to the questions", "after the Stage 1 answer",
                                           "after the final answers", "after the reflection"]
    assert [s["wait_s"] for s in steps] == [20.0, 30.0, 12.0, 40.0, 25.0]
    assert [s["turn_s"] for s in steps] == [25.0, 40.0, 14.0, 55.0, 35.0]     # behind-the-scenes work included
    assert steps[1]["examiner_messages"] == 2                                # feedback, then the case
    assert steps[1]["learner_s"] == 60.0
    assert rep["timings"]["total_wait_s"] == 127.0 and rep["timings"]["longest_wait_s"] == 40.0


@pytest.mark.parametrize("fault,kind,part", [
    ("leak_id", "blueprint ID", "questions"),
    ("leak_key", "key line", "questions"),
    ("leak_diagnosis", "diagnosis", "case"),
])
def test_blinding_leak_before_the_matching_answer_fails(script, fault, kind, part):
    out, rep = script(fault).report()
    b = rep["checks"]["blinding"]
    assert out["ok"] is False and b["ok"] is False and b["leaks"] >= 1
    assert any(f["kind"] == kind and f["part"] == part and f["level"] == "fail" for f in b["findings"])
    assert "**FAIL**" in open(out["report"], encoding="utf-8").read()
    assert sim("check", "--run", os.path.dirname(os.path.dirname(out["report"])) + "/run", ok=False).returncode == 1


def test_topic_named_after_its_answers_is_not_a_leak(script):
    # the questions' feedback names their topic (anaemia) and repeats their key: both are sent
    # after the questions were answered; the clean round must pass with them in it
    _, rep = script().report()
    assert rep["checks"]["blinding"]["findings"] == []


def test_topic_word_before_the_answer_is_listed_for_review_without_failing(script):
    _, rep = script("topic_word").report()
    b = rep["checks"]["blinding"]
    assert b["ok"] is True and b["to_review"] == 1
    assert b["findings"][0]["kind"] == "topic word" and b["findings"][0]["term"] == "anemia"   # label spelling; the text said "anaemia"


def test_unsaved_file_fails_the_saved_check(script):
    out, rep = script("session_not_saved").report()
    s = rep["checks"]["saved"]
    assert out["checks"]["saved"] is False
    assert "differs from what cme.py wrote: data/sessions/S0001.json" in s["problems"]
    assert any("never closed" in p for p in s["problems"])


def test_round_left_without_its_reflection_fails_saved_and_log(script):
    out, rep = script("stop_before_reflection").report("--note", "stopped early")
    assert out["checks"]["saved"] is False and out["checks"]["log"] is False
    assert any("waiting for its reflection" in p for p in rep["checks"]["saved"]["problems"])
    assert any("Reflection" in p for p in rep["checks"]["log"]["problems"])
    assert "stopped early" in open(out["report"], encoding="utf-8").read()


def test_retyped_answer_fails_the_verbatim_check(script):
    out, rep = script("retyped_answer").report()
    assert out["checks"]["log"] is False
    probs = rep["checks"]["log"]["problems"]
    assert any("Your answers — case" in p and "learner" in p for p in probs)
    assert "learner message 6 is not in the log word for word" in probs
    # and the seal on the case can still be placed (its last answers block matches)
    assert rep["checks"]["blinding"]["ok"] is True


def test_feedback_logged_differently_from_what_was_sent_fails(script):
    out, rep = script("retyped_feedback").report()
    assert out["checks"]["log"] is False
    assert any("Feedback (as sent)" in p and "examiner" in p for p in rep["checks"]["log"]["problems"])
    assert any(u["message"] == 9 for u in rep["checks"]["log"]["examiner_text_not_logged"])


def test_next_stops_a_stalled_run(tmp_path):
    run = str(tmp_path / "run")
    sim("init", "--run", run, "--today", TODAY)
    out = sim_json("next", "--run", run, "--after", "examiner")
    assert out["stop"] is True and "without sending anything" in out["why"]
    empty = tmp_path / "empty.md"
    empty.write_text("  \n")
    assert sim("send", "--run", run, "--role", "examiner", "--file", str(empty), ok=False).returncode == 2


def test_second_round_continues_on_the_first_runs_store(script, tmp_path):
    s = script()
    run2 = str(tmp_path / "run2")
    sim("init", "--run", run2, "--from-run", s.run)
    st = json.load(open(os.path.join(run2, "store", "data", "state.json")))
    assert st["next_id"] == "S0002" and len(st["sessions"]) == 1
    assert os.path.isfile(os.path.join(run2, "store", "data", "sessions", "S0001.json"))
    # the earlier round does not count as this run's round
    assert sim_json("next", "--run", run2, "--after", "learner")["round_closed"] is False

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

<!-- key: Q1 -->
type: mcq
topic: HEME-01
label: Anemia workup (inpatient)
reason: new
stem_summary: Tired woman of 54, which test comes first
<!-- /key -->
Correct: B, because the ferritin settles it in this setting.

<!-- key: Q2 -->
type: focused
topic: NEURO-04
label: Altered mental status / delirium
reason: new
aspect: testing
stem_summary: Worst headache of his life at 30, what now
<!-- /key -->
Best answer: image first, then decide on lumbar puncture afterwards.

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

<!-- key: case -->
type: case
topic: GEN-11
label: Patient safety, quality improvement, high-value care
reason: new
patient: 60M
setting: emergency department
presentation: three days of malaise
diagnosis: Fictitious secretitis
<!-- /key -->
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
# The examiner's round.json: which key each item answers, and the grading. `save` fills in the
# rest from the key headers above and writes the round record to record.json.
ROUND = {
    "log_id": "S0001", "title": "Malaise in a 60-year-old — fictitious secretitis",
    "summary": "s", "tags": ["x"],
    "items": [
        {"key": "Q1", "mastery": 5, "correct": True, "confidence": "sure", "coding": {"errors": []}},
        {"key": "Q2", "mastery": 4, "confidence": "sure", "coding": {"art": {"TEST": 2}, "errors": []}},
        {"key": "case", "mastery": 4, "confidence": "sure",
         "coding": {"art": {"DG": 2}, "idea": {"I": 3, "D": 2, "E": 1, "A": 1}, "errors": []}},
    ],
    "gaps": [{"topic": "GEN-11", "gap": "treatment duration", "source": "graded"}],
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
    """One scripted round in a run folder. `faults` names what to do wrong. The round is played
    in steps (open, case, save, close) so that the persona scripts in test_sim_personas.py can
    take a different path through it."""
    persona = "strong"

    def __init__(self, tmp_path, faults=()):
        self.run = str(tmp_path / "run")
        self.reports = str(tmp_path / "reports")
        self.faults = set(faults)
        self.clock = 1000.0
        sim("init", "--persona", self.persona, "--run", self.run, "--today", TODAY)
        self.work = os.path.join(self.run, "work")
        self.store = os.path.join(self.run, "store")
        self.n = 0
        self.filed = set()
        self.put("start.json", cme("--today", TODAY, "start", "--work", self.work, "--store", self.store))

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
        if role == "learner":
            self.received = path
        return sim_json("send", "--run", self.run, "--role", role, "--file", path, "--ts", str(self.clock))

    def answer(self, part, text=None):
        """File an answer as the examiner does: the learner's last message as it arrived, or `text`."""
        source = ("--file", self.received) if text is None else ("--text", text)
        cme("answer", "--work", self.work, "--part", part, *source)
        self.filed.add(part)

    def turn_end(self, role, after=0.0):
        self.clock += after
        return sim_json("next", "--run", self.run, "--after", role, "--ts", str(self.clock))

    def store_files(self, skip=()):
        """Publish: every file of the publish set into the folder store, in the manifest's order."""
        with open(self.p("publish.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        assert manifest["files"][-1]["as"] == "data/state.json"
        for f in manifest["files"]:
            if os.path.basename(f["as"]) in skip:
                continue
            dest = os.path.join(self.store, *f["as"].split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(f["path"], dest)

    def open_round(self):
        """Turns 1 and 2: the questions, their answers, their feedback, and the case presented."""
        # the harness set the clock of message 1 itself; pin it for the timing assertions
        lines = open(os.path.join(self.run, "transcript.jsonl")).read().splitlines()
        first = json.loads(lines[0]); first["ts"] = self.clock
        with open(os.path.join(self.run, "transcript.jsonl"), "w") as fh:
            fh.write(json.dumps(first) + "\n")
        questions = SEALED_QUESTIONS
        if "abbreviation_in_stem" in self.faults:
            questions = questions.replace("is tired.", "is tired; her ALT is raised, her ECG and her "
                                          "thyroid-stimulating hormone (TSH) are normal.")
        if "mixed_anchors_in_question" in self.faults:
            questions = questions.replace("has the worst headache of his life.", "has had the worst headache of "
                                          "his life since this morning, on day 3 of an admission.")
        self.put("sealed_questions.md", questions)
        self.put("sealed_case.md", SEALED_CASE)
        # turn 1: questions out
        opening = "Today's round: two questions, then one case."
        if "no_block_line" not in self.faults:
            opening += " " + json.load(open(self.p("start.json")))["block"]["line"] + "."
        if "leak_id" in self.faults:
            opening += " (Q1 is HEME-01.)"
        if "leak_key" in self.faults:
            opening += " Correct: B, because the ferritin settles it in this setting."
        if "topic_word" in self.faults:
            opening += " Think about anaemia."
        self.send("examiner", opening + "\n\n" + cme("present", "--work", self.work, "--block", "questions"), 20)
        assert self.turn_end("examiner", 5)["deliver_to"] == "learner"
        # turn 2: answers -> feedback, then the case
        self.send("learner", ANSWERS["questions"], 60)
        self.turn_end("learner")
        fbq = FEEDBACK_Q
        if "leak_diagnosis" in self.faults:
            fbq = fbq.replace("The case follows.", "The case follows (it is fictitious  secretitis).")
        if "feedback_abbreviations" in self.faults:
            fbq = fbq.replace("Q2: image first.", "Q2 (NEURO-04): image first with CT, then LP if it is negative, as ESC advises.")
        if "feedback_glossary" in self.faults:
            fbq = fbq.replace("Feedback on the questions\n", "Feedback on the questions\n\n"
                              "**Abbreviations:** LP lumbar puncture\n")
        self.send("examiner", fbq, 30)
        self.send("examiner", cme("present", "--work", self.work, "--block", "case"), 1)
        self.answer("questions")
        self.put("feedback_questions.md", fbq)
        self.turn_end("examiner", 9)

    def case(self):
        """Turns 3 and 4 up to the final feedback as sent."""
        # turn 3: Stage 1 answer -> Stage 2
        self.send("learner", ANSWERS["case"], 90)
        self.turn_end("learner")
        stage2 = STAGE2
        if "mixed_anchors_in_stage2" in self.faults:
            stage2 = stage2.replace("stable overnight.", "on day 2 he is worse than he was yesterday; INR 1.4.")
        self.send("examiner", stage2, 12)
        self.answer("case", "Differential: infection, malignancy, inflammatory. Tests: special scan and a blood count."
                    if "retyped_answer" in self.faults else None)
        self.put("stage2.md", stage2)          # as sent; the sealed case is not touched
        self.turn_end("examiner", 2)
        # turn 4: final answers -> feedback, first save
        self.send("learner", ANSWERS["final"], 45)
        self.turn_end("learner")
        self.send("examiner", FEEDBACK, 40)
        self.answer("final")

    def save(self, rnd=ROUND, feedback=FEEDBACK, answers=None, parts=("questions", "case", "final")):
        """The first save, behind the scenes after the final feedback went out: everything is
        found in the work folder. Answers were filed as they arrived; `answers` adds the rest
        (notes)."""
        logged = dict(ANSWERS, **(answers or {}))
        if "retyped_feedback" in self.faults:
            feedback = feedback.replace("you ordered it", "you asked for it")
        self.put("feedback.md", feedback)
        for part in parts:
            if part not in self.filed:
                self.answer(part, logged[part])
        self.put("round.json", rnd)
        cme("--today", TODAY, "save", "--work", self.work)
        self.store_files()
        assert self.turn_end("examiner", 15)["round_closed"] is False

    def close(self, reflection=None, part_b=PART_B, reflection_text=ANSWERS["reflection"]):
        """Turn 5: the reflection, the close message and the final save."""
        self.send("learner", reflection_text, 30)
        self.turn_end("learner")
        self.put("reflection.json", reflection or {"topic_comfort": {"GEN-11": 4}, "performance": 4, "solid": "a", "gaps": "b"})
        self.answer("reflection")
        self.put("B.md", part_b)
        cme("--today", TODAY, "close", "--work", self.work)
        self.send("examiner", CLOSE, 25)
        self.store_files(skip=("S0001.json",) if "session_not_saved" in self.faults else ())
        assert self.turn_end("examiner", 10)["stop"] is False
        last = self.turn_end("learner", 5)          # the learner has nothing to add
        assert last["stop"] is True and last["round_closed"] is True

    def play(self):
        self.open_round()
        self.case()
        self.save()
        if "stop_before_reflection" not in self.faults:
            self.close()
        return self

    def report(self, *extra):
        out = sim_json("report", "--run", self.run, "--out-dir", self.reports, *extra)
        with open(out["data"], encoding="utf-8") as fh:
            return out, json.load(fh)


def test_runs_started_in_the_same_second_get_a_folder_each(tmp_path):
    runs = str(tmp_path / "runs")
    stamp = "20261121-030405"
    args = ("--runs-dir", runs, "--stamp", stamp, "--today", TODAY)
    first = sim_json("init", "--persona", "strong", *args)
    second = sim_json("init", "--persona", "disputes", *args)
    assert os.path.basename(first["run"]) == stamp and os.path.basename(second["run"]) == stamp + "-2"
    for out, persona in ((first, "strong"), (second, "disputes")):
        assert json.load(open(os.path.join(out["run"], "run.json")))["persona"] == persona
        assert os.path.isfile(os.path.join(out["run"], "store", "data", "state.json"))
        assert persona not in os.path.basename(out["run"])       # the name still does not name the persona
        assert persona not in open(out["examiner_prompt"]).read()


def test_inits_started_at_once_never_share_a_folder(tmp_path):
    runs = str(tmp_path / "runs")
    procs = [subprocess.Popen([sys.executable, SIM, "init", "--persona", "strong", "--runs-dir", runs,
                               "--stamp", "20261121-030405", "--today", TODAY],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
    outs = [p.communicate() for p in procs]
    assert all(p.returncode == 0 for p in procs), outs
    made = sorted(json.loads(o)["run"] for o, _ in outs)
    assert len(set(made)) == 4 and sorted(os.listdir(runs)) == sorted(os.path.basename(m) for m in made)


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
    assert out["checks"] == {"blinding": True, "saved": True, "log": True, "standards": True}
    assert rep["checks"]["blinding"]["leaks"] == 0
    assert rep["checks"]["blinding"]["seal_lifted_at"] == {"questions": 3, "case": 8}
    assert rep["checks"]["saved"]["publish_set"] == ["data/sessions/S0001.json", "data/index.json",
                                                     "data/prepared.json", "data/state.json"]
    assert rep["round"] == {"session": "S0001", "shape": "1 MCQ, 1 focused, case (two stages)", "score": rep["round"]["score"],
                            "confident_misses": 0, "continued_from_earlier_run": False}
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


def test_opening_without_the_block_line_fails(script):
    s = script("no_block_line")
    _, rep = s.report()
    blinding = rep["checks"]["blinding"]
    assert rep["ok"] is False and blinding["leaks"] == 0
    assert blinding["block_line"] == "Block: Cardiology, round 1 of 12"
    assert any("block line" in p for p in blinding["problems"])


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

"""Save and close from the work folder (issue #9): `start` notes where the ledger is, `answer`
adds the learner's answers part by part, and `save` and `close` find every file of the round in
the work folder by its fixed name."""
import json
import os
import shutil

import pytest

from conftest import BLUEPRINT, REFLECTION, ROUND, SEALED_CASE, SEALED_QUESTIONS, Work

DAY = "2026-11-01"
SAID = {
    "questions": "Q1 B sure\nQ2: CT first - thunderclap, so SAH untill excluded",      # typo kept
    "case": "Ddx: infection, malignancy.\n\nTests: CT abdomen, blood count",
    "final": "1. secretitis 2. treat for a week",
    "reflection": "Comfort 4 4 5. Own rating 3. Solid: headache. Shaky: treatment duration.",
}
STAGE2 = "Stage 2\n\nCT abdomen: RESULT-TEXT\n\n1. Your diagnosis? 2. Your treatment?\n"
PART_B = "### Discussion (verbatim)\n\nNone.\n\n### Grade changes\n\nNone.\n\n### Coded analysis\n\nDG 1.\n"


class Round(Work):
    """A work folder with the learner's folder store read into store/, as a session has it."""

    def store(self, *parts):
        return self.p("store", *parts)

    def setup(self, layout="data", page=False, config=None):
        self.run("--today", DAY, "init", "--blueprint", BLUEPRINT, "--config", json.dumps(config or {}),
                 "--out", self.p("new.json"))
        self.run("place", self.p("new.json"), "--out-dir", self.p("placed"))
        os.remove(self.p("new.json"))
        if layout == "data":
            shutil.copytree(self.p("placed"), self.store())
        else:                                   # the store's files read side by side into store/
            os.makedirs(self.store())
            for name in ("state.json", "index.json", "prepared.json"):
                shutil.copy(self.p("placed", "data", name), self.store(name))
        shutil.rmtree(self.p("placed"))
        self.ledger = self.store("data", "state.json") if layout == "data" else self.store("state.json")
        if page:
            with open(self.store("index.html"), "w") as fh:
                fh.write('<meta name="cme-page-version" content="1.0.0">')
        return self

    def start(self, today=DAY, *extra):
        return self.run_json("--today", today, "start", self.ledger, "--work", self.path, *extra)

    def answer(self, part, text=None):
        return self.run_json("answer", "--work", self.path, "--part", part, "--text", text or SAID[part])

    def play_to_feedback(self, rnd=None):
        """Turns 1-4 as the protocol has them, up to the files `save` needs."""
        self.start()
        self.write("sealed_questions.md", SEALED_QUESTIONS)
        self.write("sealed_case.md", SEALED_CASE)
        self.answer("questions")
        self.write("feedback_questions.md", "Feedback on the questions, as sent")
        self.answer("case")
        self.write("stage2.md", STAGE2)
        self.answer("final")
        self.write("feedback.md", "Final feedback, as sent")
        self.write("round.json", rnd or ROUND)
        return self

    def save(self, today=DAY, *extra):
        return self.run_json("--today", today, "save", "--work", self.path, *extra)

    def close(self, today=DAY, reflection=None, *extra):
        return self.run_json("--today", today, "close", "--work", self.path,
                             "--reflection", json.dumps(reflection or REFLECTION), *extra)


@pytest.fixture
def rnd(tmp_path):
    return Round(tmp_path).setup()


def sections(md):
    out, key = {}, None
    for line in md.splitlines():
        if line.startswith("### "):
            key = line[4:]
            out[key] = []
        elif key:
            out[key].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


# ---- a full round through the new commands

def test_full_round_needs_only_the_work_folder_the_dates_and_the_reflection(rnd):
    started = rnd.start()
    assert started["work"] == rnd.path and os.path.isfile(rnd.p("plan.json"))
    rnd.play_to_feedback()
    saved = rnd.save()
    assert saved["warnings"] == []
    assert [f["as"] for f in saved["files"]] == ["data/state.json", "data/sessions/S0001.json", "data/index.json",
                                                 "data/prepared.json"]
    assert all(f["path"].startswith(rnd.p("out1")) for f in saved["files"])
    a = sections(rnd.read_json("out1", "data", "sessions", "S0001.json")["transcript"])
    assert list(a) == ["Questions — as presented", "Your answers — questions (verbatim)",
                       "Feedback — questions (as sent)", "Case — as presented", "Your answers — case (verbatim)",
                       "Stage 2 — as presented", "Your final answers (verbatim)", "Feedback (as sent)"]
    assert a["Your answers — questions (verbatim)"] == SAID["questions"]
    assert a["Your answers — case (verbatim)"] == SAID["case"]
    assert a["Your final answers (verbatim)"] == SAID["final"]
    assert a["Stage 2 — as presented"] == STAGE2.strip()
    assert a["Feedback — questions (as sent)"] == "Feedback on the questions, as sent"
    assert rnd.read_json("out1", "data", "state.json")["unreflected"] == "S0001"

    rnd.answer("reflection")
    rnd.write("B.md", PART_B)
    closed = rnd.close("2026-11-03")
    assert all(f["path"].startswith(rnd.p("out2")) for f in closed["files"])
    st = rnd.read_json("out2", "data", "state.json")
    assert st["unreflected"] is None and st["sessions"][-1]["date"] == DAY
    doc = rnd.read_json("out2", "data", "sessions", "S0001.json")
    b = sections(doc["closing"])
    assert list(b) == ["Reflection (verbatim)", "Discussion (verbatim)", "Grade changes", "Coded analysis"]
    assert b["Reflection (verbatim)"] == SAID["reflection"]
    assert doc["reflected"] is True and doc["transcript"].startswith("### Questions")
    assert [s["reflected"] for s in rnd.read_json("out2", "data", "index.json")["sessions"]] == [True]


def test_work_folder_round_equals_the_same_round_with_every_file_named(rnd, tmp_path):
    rnd.play_to_feedback()
    rnd.save()
    rnd.answer("reflection")
    rnd.write("B.md", "### Reflection (verbatim)\n\n%s\n\n%s" % (SAID["reflection"], PART_B))
    rnd.close()
    w = rnd
    w.write("sealed_case_old.md", SEALED_CASE + "<!-- present: stage2 -->\n" + STAGE2 + "<!-- /present -->\n")
    w.run("--today", DAY, "save", w.ledger, "--round", w.p("round.json"), "--sealed", w.p("sealed_questions.md"),
          w.p("sealed_case_old.md"), "--answers", w.p("answers.md"), "--feedback-questions",
          w.p("feedback_questions.md"), "--feedback", w.p("feedback.md"), "--index", w.store("data", "index.json"),
          "--out-dir", w.p("old1"))
    w.run("--today", DAY, "close", w.p("old1", "data", "state.json"), "--reflection", json.dumps(REFLECTION),
          "--md", w.p("B.md"), "--doc", w.p("old1", "data", "sessions", "S0001.json"),
          "--index", w.p("old1", "data", "index.json"), "--out-dir", w.p("old2"))
    for new, old in (("out1", "old1"), ("out2", "old2")):
        for rel in (("data", "state.json"), ("data", "sessions", "S0001.json"), ("data", "index.json")):
            assert w.read_json(new, *rel) == w.read_json(old, *rel)


# ---- answer

def test_answer_appends_and_never_rewrites_what_is_there(rnd):
    rnd.start()
    assert rnd.answer("questions")["parts"] == ["questions"]
    first = open(rnd.p("answers.md"), "rb").read()
    out = rnd.answer("case")
    assert out == {"ok": True, "part": "case", "chars": len(SAID["case"]), "parts": ["questions", "case"]}
    assert open(rnd.p("answers.md"), "rb").read().startswith(first)
    assert SAID["case"] in open(rnd.p("answers.md")).read()          # blank line and typos kept


def test_answer_reads_a_file_or_standard_input_and_prints_no_content(rnd):
    rnd.start()
    r = rnd.run("answer", "--work", rnd.path, "--part", "questions", "--file", rnd.write("msg.md", SAID["questions"] + "\n"))
    assert "thunderclap" not in r.stdout
    import subprocess, sys
    from conftest import CME
    r = subprocess.run([sys.executable, CME, "answer", "--work", rnd.path, "--part", "case"], input=SAID["case"],
                       capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["parts"] == ["questions", "case"]
    assert "malignancy" not in r.stdout


def test_same_answer_is_added_once_and_a_second_message_is_kept(rnd):
    rnd.start()
    rnd.answer("questions")
    again = rnd.answer("questions")
    assert again["already_added"] is True and again["parts"] == ["questions"]
    more = rnd.answer("questions", "Q3 - forgot this one: C, guess")
    assert more["parts"] == ["questions", "questions"]
    rnd.write("sealed_questions.md", SEALED_QUESTIONS)
    rnd.write("feedback.md", "fb")
    rnd.write("round.json", ROUND)
    rnd.save()
    a = sections(rnd.read_json("out1", "data", "sessions", "S0001.json")["transcript"])
    assert a["Your answers — questions (verbatim)"] == SAID["questions"] + "\n\nQ3 - forgot this one: C, guess"


def test_answer_refuses_nothing_to_add_unknown_parts_and_marker_text(rnd):
    rnd.start()
    r = rnd.run("answer", "--work", rnd.path, "--part", "questions", "--text", "  \n", ok=False)
    assert r.returncode == 2 and "no answer text" in json.loads(r.stdout)["error"]
    r = rnd.run("answer", "--work", rnd.path, "--part", "questions", "--text", "x\n<!-- /answers -->", ok=False)
    assert r.returncode == 2 and not os.path.exists(rnd.p("answers.md"))
    assert rnd.run("answer", "--work", rnd.path, "--part", "stage9", "--text", "x", ok=False).returncode == 2
    assert rnd.run("answer", "--work", rnd.p("nowhere"), "--part", "case", "--text", "x", ok=False).returncode == 2


# ---- save

def test_save_does_not_touch_the_sealed_case_and_can_be_run_again(rnd):
    rnd.play_to_feedback()
    before = open(rnd.p("sealed_case.md")).read()
    first = rnd.save()
    again = rnd.save()
    assert open(rnd.p("sealed_case.md")).read() == before
    assert first == again and rnd.read_json(rnd.ledger)["next_id"] == "S0001"     # the ledger read is unchanged


@pytest.mark.parametrize("layout", ["data", "flat"])
def test_save_finds_index_and_page_beside_the_ledger(tmp_path, layout):
    rnd = Round(tmp_path).setup(layout=layout, page=True)
    index = rnd.store("data", "index.json") if layout == "data" else rnd.store("index.json")
    idx = rnd.read_json(index)
    idx["reviews"] = [{"date": "2026-10-01", "title": "kept"}]
    rnd.write(os.path.relpath(index, rnd.path), idx)
    saved = rnd.play_to_feedback().save()
    assert saved["page_upgraded"]["from"] == "1.0.0" and saved["files"][-1]["as"] == "index.html"
    assert rnd.read_json("out1", "data", "index.json")["reviews"] == idx["reviews"]
    rnd.write("B.md", PART_B)
    closed = rnd.close()
    assert "page_upgraded" not in closed                     # checked once, at the save
    assert rnd.read_json("out2", "data", "index.json")["reviews"] == idx["reviews"]


def test_page_settings_given_at_start_are_kept_by_save(rnd):
    prefs = {"round": {"mcqs": 1, "focused": 2}, "base": rnd.read_json(rnd.ledger)["config"]["round_set_at"],
             "updated": "2026-11-01T08:00:00Z"}
    rnd.start(DAY, "--prefs", json.dumps(prefs))
    rnd.write("sealed_questions.md", SEALED_QUESTIONS)
    rnd.answer("questions")
    rnd.write("feedback.md", "fb")
    rnd.write("round.json", ROUND)
    saved = rnd.save()
    cfg = rnd.read_json("out1", "data", "state.json")["config"]
    assert (cfg["mcqs"], cfg["focused"]) == (1, 2) and "page_settings_applied" in saved


def test_save_says_which_file_is_missing(rnd):
    r = Work(rnd.p("store")).run("save", "--work", rnd.p("store", "data"), ok=False)   # a folder start never saw
    assert "no ledger found" in json.loads(r.stdout)["error"]
    rnd.start()
    assert "round.json in the work folder" in json.loads(rnd.run("save", "--work", rnd.path, ok=False).stdout)["error"]
    rnd.write("round.json", ROUND)
    assert "feedback.md in the work folder" in json.loads(rnd.run("save", "--work", rnd.path, ok=False).stdout)["error"]
    assert not os.path.exists(rnd.p("out1", "data"))
    assert "save needs --work" in json.loads(rnd.run("save", ok=False).stdout)["error"]


# ---- close

def test_close_keeps_a_part_b_that_already_holds_the_reflection(rnd):
    rnd.play_to_feedback().save()
    rnd.answer("reflection")
    whole = "### Reflection (verbatim)\n\n%s\n\n%s" % (SAID["reflection"], PART_B)
    rnd.write("B.md", whole)
    rnd.close()
    assert rnd.read_json("out2", "data", "sessions", "S0001.json")["closing"] == whole


def test_close_reads_reflection_json_from_the_work_folder_and_needs_part_b(rnd):
    rnd.play_to_feedback().save()
    r = rnd.run("--today", DAY, "close", "--work", rnd.path, ok=False)
    assert "reflection.json in the work folder" in json.loads(r.stdout)["error"]
    rnd.write("reflection.json", {"skipped": True})
    r = rnd.run("--today", DAY, "close", "--work", rnd.path, ok=False)
    assert "close needs part B" in json.loads(r.stdout)["error"] and not os.path.exists(rnd.p("out2"))
    rnd.write("B.md", PART_B)
    rnd.run("--today", DAY, "close", "--work", rnd.path)
    st = rnd.read_json("out2", "data", "state.json")
    assert st["unreflected"] is None and st["sessions"][-1]["reflection"]["skipped"] is True


def test_reflection_given_at_a_later_session_closes_from_the_store(rnd, tmp_path_factory):
    rnd.play_to_feedback().save()
    later = Round(tmp_path_factory.mktemp("later"))
    shutil.copytree(rnd.p("out1", "data"), later.store("data"))         # the store as the save left it
    os.remove(later.store("data", "sessions", "S0001.json"))
    later.ledger = later.store("data", "state.json")
    later.answer("reflection")
    later.write("B.md", PART_B)
    r = later.run("--today", "2026-11-04", "close", "--work", later.path, "--reflection", json.dumps(REFLECTION), ok=False)
    assert "session file of S0001 was not found" in json.loads(r.stdout)["error"]
    shutil.copytree(rnd.p("out1", "data", "sessions"), later.store("data", "sessions"), dirs_exist_ok=True)
    later.close("2026-11-04")
    doc = later.read_json("out2", "data", "sessions", "S0001.json")
    assert doc["reflected"] is True and "### Questions" in doc["transcript"] and doc["date"] == DAY
    assert SAID["reflection"] in doc["closing"]
    # today's round then starts in the same folder, from the closed ledger
    later.ledger = later.p("out2", "data", "state.json")
    out = later.start("2026-11-04")
    assert out["last_session"]["unreflected"] is False and not os.path.exists(later.p("answers.md"))
    noted = later.read_json("work.json")["state"]
    assert noted == later.p("earlier", "1", "out2", "data", "state.json") and os.path.isfile(noted)
    later.write("sealed_questions.md", SEALED_QUESTIONS)
    later.answer("questions")
    later.write("feedback.md", "fb")
    later.write("round.json", dict(ROUND, log_id="S0002"))
    later.save("2026-11-04")
    idx = later.read_json("out1", "data", "index.json")
    assert [(s["id"], s["reflected"]) for s in idx["sessions"]] in ([("S0001", True), ("S0002", False)],
                                                                   [("S0002", False), ("S0001", True)])


# ---- one work folder, one round at a time

def test_second_round_in_the_same_work_folder_starts_clean(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    shutil.copytree(rnd.p("out2", "data"), rnd.store("data"), dirs_exist_ok=True)      # saved to the store
    again = rnd.start("2026-11-02")
    kept = again["earlier_round_set_aside"]
    assert kept == rnd.p("earlier", "1") and os.path.isfile(os.path.join(kept, "answers.md"))
    assert os.path.isdir(os.path.join(kept, "out1")) and os.path.isfile(os.path.join(kept, "sealed_case.md"))
    for name in ("answers.md", "feedback.md", "stage2.md", "round.json", "B.md", "sealed_case.md", "out1", "out2"):
        assert not os.path.exists(rnd.p(name)), name
    assert rnd.read_json("work.json")["session_id"] == "S0002"
    assert rnd.answer("questions")["parts"] == ["questions"]


def test_start_again_before_any_answer_sets_nothing_aside(rnd):
    rnd.start()
    rnd.write("sealed_questions.md", SEALED_QUESTIONS)
    out = rnd.start(DAY, "--mcqs", "1")
    assert "earlier_round_set_aside" not in out and os.path.isfile(rnd.p("sealed_questions.md"))


# ---- testing mode: the store check finds the output folders itself

def test_verify_finds_the_output_folders_in_the_work_folder(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    check = rnd.p("check")
    shutil.copytree(rnd.p("out2", "data"), os.path.join(check, "data"))
    shutil.copy(rnd.p("out1", "data", "prepared.json"), os.path.join(check, "data", "prepared.json"))
    res = rnd.run_json("verify", "--work", rnd.path, "--store", check)
    assert res["ok"] is True and res["checked"] == 4 and rnd.read_json("verify.json") == res
    os.remove(os.path.join(check, "data", "sessions", "S0001.json"))
    assert rnd.run_json("verify", "--work", rnd.path, "--store", check)["missing"] == ["data/sessions/S0001.json"]

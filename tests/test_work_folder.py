"""One work folder per job, one publish set (issues #9, #52): `open` (or `start --store`) notes
where the store copy is, `answer` adds the learner's answers part by part, and every other
command finds what it needs in the work folder by its fixed name and writes into the publish
set, whose manifest lists every changed store file in write order, the ledger last."""
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
STATE, PAGE_FILE, PREPARED = "data/state.json", "data/page.json", "data/prepared.json"
SESSION = "data/sessions/S0001.json"


class Round(Work):
    """A work folder with the learner's folder store read into store/, as a session has it."""

    def setup(self, layout="data", page=False, config=None):
        self.init(today=DAY, config=config)
        if layout == "flat":                    # the store's files read side by side into store/
            for name in ("state.json", "page.json", "prepared.json"):
                shutil.copy(self.store("data", name), self.store(name))
            shutil.copy(self.store("index.html"), self.store("page.html"))
            shutil.rmtree(self.store("data"))
            os.replace(self.store("page.html"), self.store("index.html"))
        if page:
            with open(self.store("index.html"), "w") as fh:
                fh.write('<meta name="cme-page-version" content="1.0.0">')
        return self

    def start(self, today=DAY, *extra):
        return super().start(today, *extra)

    def answer(self, part, text=None):
        return self.run_json("answer", "--work", self.path, "--part", part, "--text", text or SAID[part])

    def play_to_feedback(self, rnd=None, start=True):
        """Turns 1-4 as the protocol has them, up to the files `save` needs."""
        if start:
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

    def save(self, today=DAY):
        return self.run_json("--today", today, "save", "--work", self.path)

    def close(self, today=DAY, reflection=None):
        return self.run_json("--today", today, "close", "--work", self.path,
                             "--reflection", json.dumps(reflection or REFLECTION))

    def manifest(self):
        return self.read_json("publish.json")

    def listed(self):
        return [f["as"] for f in self.manifest()["files"]]


@pytest.fixture
def rnd(tmp_path):
    return Round(tmp_path).setup()


def names(out):
    return [f["as"] for f in out["files"]]


def sections(md):
    out, key = {}, None
    for line in md.splitlines():
        if line.startswith("### "):
            key = line[4:]
            out[key] = []
        elif key:
            out[key].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


# ---- open: a work folder for any job

@pytest.mark.parametrize("layout", ["data", "flat"])
def test_open_notes_the_store_copy_in_either_layout_and_prints_neutral_status(tmp_path, layout):
    rnd = Round(tmp_path).setup(layout=layout)
    out = rnd.run_json("--today", DAY, "open", "--work", rnd.path, "--store", rnd.store(), "--version", "41")
    ledger = rnd.store("data", "state.json") if layout == "data" else rnd.store("state.json")
    assert out["ok"] and out["gen"] == 1 and out["next_id"] == "S0001" and out["store_layout"] == layout
    assert out["store_files"] == [STATE, PAGE_FILE, PREPARED, "index.html"] and out["store_version"] == "41"
    assert out["due_count"] == 0 and out["open_gaps"] == 0 and out["last_session"] is None
    info = rnd.read_json("work.json")
    assert info == {"store": rnd.store(), "state": ledger, "session_id": "S0001", "version": "41",
                    "prefs": None, "started": DAY}
    assert rnd.manifest() == {"version": "41", "files": []}             # nothing to publish yet
    # the ledger is found the same way by whatever comes next
    changed = rnd.run_json("settings", "--work", rnd.path, "--config", '{"testing": true}')
    assert names(changed) == [PAGE_FILE, STATE] and rnd.manifest()["version"] == "41"


def test_open_prints_no_topic_and_refuses_a_folder_without_a_ledger(rnd, tmp_path_factory):
    st = rnd.read_ledger()
    text = rnd.run("--today", DAY, "open", "--work", rnd.path, "--store", rnd.store()).stdout
    assert not any(t in text for t in st["blueprint"]["CARD"]["topics"])
    empty = str(tmp_path_factory.mktemp("empty"))
    r = rnd.run("open", "--work", rnd.path, "--store", empty, ok=False)
    assert r.returncode == 2 and "no ledger" in json.loads(r.stdout)["error"] and "init --work" in r.stdout
    r = rnd.run("open", "--work", rnd.path, "--store", rnd.p("nowhere"), ok=False)
    assert r.returncode == 2 and "is not a folder" in json.loads(r.stdout)["error"]
    r = rnd.run("open", "--work", rnd.path, ok=False)
    assert r.returncode == 2 and "--store" in r.stderr


def test_commands_need_an_open_work_folder(tmp_path):
    w = Work(tmp_path)
    for args in (("start",), ("save",), ("close",), ("prepare",), ("finish-prepare",), ("settings",), ("theme",),
                 ("stats",), ("snooze",), ("review", "--review", "{}"), ("addendum", "--md", "x.md"),
                 ("review-doc", "--md", "x.md"), ("testing-note", "--feedback", "{}"),
                 ("verify", "--store", w.path)):
        r = w.run(args[0], "--work", w.path, *args[1:], ok=False)
        assert r.returncode == 2 and "no job is open" in json.loads(r.stdout)["error"], args


def test_an_earlier_job_in_the_work_folder_is_set_aside_by_open(rnd):
    rnd.open()
    rnd.run("settings", "--work", rnd.path, "--config", '{"testing": true}')
    again = rnd.open()                                       # the store was not read again: still gen 1
    kept = again["earlier_set_aside"]
    assert kept == rnd.p("earlier", "1") and os.path.isfile(os.path.join(kept, "publish", "data", "state.json"))
    assert os.path.isfile(os.path.join(kept, "publish.json")) and os.path.isfile(os.path.join(kept, "work.json"))
    assert "older than the ledger the earlier job" in again["warnings"][0]
    assert not os.path.exists(rnd.pub()) and rnd.manifest()["files"] == []
    # opened twice with nothing written in between: nothing to set aside
    assert "earlier_set_aside" not in rnd.open()


# ---- a full round through the commands

def test_full_round_needs_only_the_work_folder_the_dates_and_the_reflection(rnd):
    started = rnd.start()
    assert started["work"] == rnd.path and os.path.isfile(rnd.p("plan.json"))
    rnd.play_to_feedback()
    saved = rnd.save()
    assert saved["warnings"] == []
    assert names(saved) == [SESSION, PAGE_FILE, PREPARED, STATE]
    assert all(f["path"].startswith(rnd.pub()) for f in saved["files"])
    assert saved["publish"] == rnd.p("publish.json") and rnd.manifest()["files"] == saved["files"]
    a = sections(rnd.read_json("publish", "data", "sessions", "S0001.json")["transcript"])
    assert list(a) == ["Questions — as presented", "Your answers — questions (verbatim)",
                       "Feedback — questions (as sent)", "Case — as presented", "Your answers — case (verbatim)",
                       "Stage 2 — as presented", "Your final answers (verbatim)", "Feedback (as sent)"]
    assert a["Your answers — questions (verbatim)"] == SAID["questions"]
    assert a["Your answers — case (verbatim)"] == SAID["case"]
    assert a["Your final answers (verbatim)"] == SAID["final"]
    assert a["Stage 2 — as presented"] == STAGE2.strip()
    assert a["Feedback — questions (as sent)"] == "Feedback on the questions, as sent"
    assert rnd.read_json("publish", "data", "state.json")["unreflected"] == "S0001"

    rnd.answer("reflection")
    rnd.write("B.md", PART_B)
    closed = rnd.close("2026-11-03")
    assert names(closed) == [SESSION, PAGE_FILE, PREPARED, STATE]
    st = rnd.read_json("publish", "data", "state.json")
    assert st["unreflected"] is None and st["sessions"][-1]["date"] == DAY
    doc = rnd.read_json("publish", "data", "sessions", "S0001.json")
    b = sections(doc["closing"])
    assert list(b) == ["Reflection (verbatim)", "Discussion (verbatim)", "Grade changes", "Coded analysis"]
    assert b["Reflection (verbatim)"] == SAID["reflection"]
    assert doc["reflected"] is True and doc["transcript"].startswith("### Questions")
    assert [s["reflected"] for s in rnd.read_json("publish", "data", "page.json")["sessions"]] == [True]


def test_start_without_a_store_continues_the_open_job(rnd):
    rnd.open("--version", "7")
    out = rnd.run_json("--today", DAY, "start", "--work", rnd.path, "--mcqs", "1")
    assert out["plan"]["mcqs"] == 1 and out["prepared"]["used"] is False
    assert rnd.read_json("work.json")["version"] == "7"
    r = Work(rnd.p("elsewhere"))
    os.makedirs(r.path)
    assert "no job is open" in json.loads(r.run("start", "--work", r.path, ok=False).stdout)["error"]


def test_round_commands_take_no_file_or_folder_arguments(rnd):
    rnd.play_to_feedback()
    for cmd, flags in (("start", ("--out", "--prepared", "--work-dir")),
                       ("save", ("--round", "--feedback", "--index", "--page", "--out-dir", "--md")),
                       ("close", ("--md", "--doc", "--index", "--page", "--out-dir"))):
        for flag in flags:
            r = rnd.run(cmd, "--work", rnd.path, flag, rnd.p("x"), ok=False)
            assert r.returncode == 2 and "unrecognized arguments" in r.stderr, (cmd, flag)
        r = rnd.run(cmd, rnd.ledger, "--work", rnd.path, ok=False)
        assert r.returncode == 2 and "unrecognized arguments" in r.stderr, cmd


# ---- the publish set

def test_publish_set_is_cumulative_and_keeps_the_ledger_last(rnd):
    """save → close → finish-prepare → testing-note: each command lists everything written so
    far, the newest version of each file, in write order."""
    import examples
    rnd.play_to_feedback()
    saved = rnd.save()
    assert names(saved) == [SESSION, PAGE_FILE, PREPARED, STATE]
    rnd.write("B.md", PART_B)
    closed = rnd.close()
    assert names(closed) == names(saved)                     # the same files, newer versions
    assert rnd.read_json("publish", "data", "state.json")["gen"] == closed["gen"] == saved["gen"] + 1
    rnd.run("--today", DAY, "prepare", "--work", rnd.path)
    st, plan = rnd.read_json("publish", "data", "state.json"), rnd.read_json("next", "plan.json")
    for name, text in examples.sealed_files(st, plan).items():
        rnd.write(os.path.join("next", name), text)
    packed = rnd.run_json("finish-prepare", "--work", rnd.path, "--no-evidence")
    assert names(packed) == names(saved)
    assert rnd.read_json("publish", "data", "prepared.json")["gen"] == closed["gen"]
    noted = rnd.run_json("--today", DAY, "testing-note", "--work", rnd.path, "--feedback", '{"items": 4}')
    assert names(noted) == [SESSION, "data/testing/S0001.json", PAGE_FILE, PREPARED, STATE]
    for out in (saved, closed, packed, noted):
        assert out["files"][-1]["as"] == STATE and out["publish"] == rnd.p("publish.json")
    manifest = rnd.manifest()
    assert manifest == {"version": None, "files": noted["files"]}
    assert all(os.path.isfile(f["path"]) and f["path"] == rnd.pub(*f["as"].split("/")) for f in manifest["files"])
    # publishing the set once, at the end, gives the store everything: a publish that failed
    # earlier is covered by the next one
    rnd.publish()
    after = rnd.open()
    assert after["gen"] == closed["gen"] and after["last_session"]["unreflected"] is False


def test_publish_set_carries_the_store_version_and_the_page_before_the_ledger(tmp_path):
    rnd = Round(tmp_path).setup(page=True)
    rnd.run_json("--today", DAY, "start", "--work", rnd.path, "--store", rnd.store(), "--version", "v12")
    saved = rnd.play_to_feedback(start=False).save()
    assert saved["page_upgraded"]["from"] == "1.0.0"
    assert names(saved) == [SESSION, PAGE_FILE, "index.html", PREPARED, STATE]
    assert rnd.manifest()["version"] == "v12"


def test_write_order_puts_log_entries_first_and_the_ledger_last():
    from examples import cme
    rels = [STATE, PREPARED, "index.html", PAGE_FILE, "data/testing/S0002.json", "data/reviews/2026-11-20.json",
            "data/sessions/S0002.json", "data/sessions/S0001.json", "data/other.json"]
    assert sorted(rels, key=cme.publish_order) == [
        "data/reviews/2026-11-20.json", "data/sessions/S0001.json", "data/sessions/S0002.json",
        "data/testing/S0002.json", "data/other.json", PAGE_FILE, "index.html", PREPARED, STATE]


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
    a = sections(rnd.read_json("publish", "data", "sessions", "S0001.json")["transcript"])
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
    ledger = rnd.read_json("publish", "data", "state.json")
    again = rnd.save()
    assert open(rnd.p("sealed_case.md")).read() == before
    assert first == again and rnd.read_json("publish", "data", "state.json") == ledger
    assert [s["id"] for s in ledger["sessions"]] == ["S0001"]
    assert rnd.read_ledger()["next_id"] == "S0001"          # the ledger read is unchanged


def test_a_settings_change_before_the_round_is_kept_by_save_and_by_a_second_save(rnd):
    rnd.open()
    changed = rnd.run_json("--today", DAY, "settings", "--work", rnd.path, "--config", '{"session_minutes": 35}',
                           "--profile", '{"specialty": "Geriatrics"}')
    rnd.run_json("--today", DAY, "start", "--work", rnd.path)
    first = rnd.play_to_feedback(start=False).save()
    st = rnd.read_json("publish", "data", "state.json")
    assert st["config"]["session_minutes"] == 35 and st["profile"]["specialty"] == "Geriatrics"
    assert first["gen"] == changed["gen"] + 1 and [s["id"] for s in st["sessions"]] == ["S0001"]
    assert rnd.read_json("before_save.json")["gen"] == changed["gen"]
    # run again (a warning was fixed): the same ledger, the settings change still in it
    again = rnd.save()
    assert again == first and rnd.read_json("publish", "data", "state.json") == st


def test_save_cannot_undo_a_close(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    closed = rnd.read_json("publish", "data", "state.json")
    r = rnd.run("--today", DAY, "save", "--work", rnd.path, ok=False)
    assert "already closed" in json.loads(r.stdout)["error"]
    assert rnd.read_json("publish", "data", "state.json") == closed


@pytest.mark.parametrize("layout", ["data", "flat"])
def test_save_finds_page_file_and_page_in_the_store_copy(tmp_path, layout):
    rnd = Round(tmp_path).setup(layout=layout, page=True)
    page_file = rnd.store("data", "page.json") if layout == "data" else rnd.store("page.json")
    idx = rnd.read_json(page_file)
    idx["reviews"] = [{"date": "2026-10-01", "title": "kept", "headline": None}]
    rnd.write(os.path.relpath(page_file, rnd.path), idx)
    saved = rnd.play_to_feedback().save()
    assert saved["page_upgraded"]["from"] == "1.0.0" and "index.html" in names(saved)
    assert rnd.read_json("publish", "data", "page.json")["reviews"] == idx["reviews"]
    rnd.write("B.md", PART_B)
    closed = rnd.close()
    assert "page_upgraded" not in closed                     # checked once, at the save
    assert "index.html" in names(closed)                     # and still in the publish set
    assert rnd.read_json("publish", "data", "page.json")["reviews"] == idx["reviews"]


def test_page_settings_given_at_start_are_kept_by_save(rnd):
    prefs = {"round": {"mcqs": 1, "focused": 2}, "base": rnd.read_ledger()["config"]["round_set_at"],
             "updated": "2026-11-01T08:00:00Z"}
    rnd.start(DAY, "--prefs", json.dumps(prefs))
    rnd.write("sealed_questions.md", SEALED_QUESTIONS)
    rnd.answer("questions")
    rnd.write("feedback.md", "fb")
    rnd.write("round.json", ROUND)
    saved = rnd.save()
    cfg = rnd.read_json("publish", "data", "state.json")["config"]
    assert (cfg["mcqs"], cfg["focused"]) == (1, 2) and "page_settings_applied" in saved


def test_save_says_which_file_is_missing(rnd):
    r = rnd.run("save", "--work", rnd.store("data"), ok=False)          # a folder `open` never saw
    assert "no job is open" in json.loads(r.stdout)["error"]
    rnd.start()
    assert "round.json in the work folder" in json.loads(rnd.run("save", "--work", rnd.path, ok=False).stdout)["error"]
    rnd.write("round.json", ROUND)
    assert "feedback.md in the work folder" in json.loads(rnd.run("save", "--work", rnd.path, ok=False).stdout)["error"]
    assert not os.path.exists(rnd.pub("data"))
    assert "--work" in rnd.run("save", ok=False).stderr


# ---- close

def test_close_keeps_a_part_b_that_already_holds_the_reflection(rnd):
    rnd.play_to_feedback().save()
    rnd.answer("reflection")
    whole = "### Reflection (verbatim)\n\n%s\n\n%s" % (SAID["reflection"], PART_B)
    rnd.write("B.md", whole)
    rnd.close()
    assert rnd.read_json("publish", "data", "sessions", "S0001.json")["closing"] == whole


def test_close_reads_reflection_json_from_the_work_folder_and_needs_part_b(rnd):
    rnd.play_to_feedback().save()
    saved = rnd.read_json("publish", "data", "state.json")
    r = rnd.run("--today", DAY, "close", "--work", rnd.path, ok=False)
    assert "reflection.json in the work folder" in json.loads(r.stdout)["error"]
    rnd.write("reflection.json", {"skipped": True})
    r = rnd.run("--today", DAY, "close", "--work", rnd.path, ok=False)
    assert "close needs part B" in json.loads(r.stdout)["error"]
    assert rnd.read_json("publish", "data", "state.json") == saved
    rnd.write("B.md", PART_B)
    rnd.run("--today", DAY, "close", "--work", rnd.path)
    st = rnd.read_json("publish", "data", "state.json")
    assert st["unreflected"] is None and st["sessions"][-1]["reflection"]["skipped"] is True


def test_close_can_be_run_again_after_a_correction(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    first = rnd.close()
    rnd.write("B.md", PART_B + "\n### Errata\n\nOne.\n")
    again = rnd.close()
    assert again["gen"] == first["gen"] and again["topics"] == first["topics"]
    doc = rnd.read_json("publish", "data", "sessions", "S0001.json")
    assert "### Errata" in doc["closing"] and doc["reflected"] is True
    st = rnd.read_json("publish", "data", "state.json")
    assert st["unreflected"] is None and [s["id"] for s in st["sessions"]] == ["S0001"]


def test_reflection_given_at_a_later_session_closes_from_the_store(rnd, tmp_path_factory):
    rnd.play_to_feedback().save()
    rnd.publish()
    later = Round(tmp_path_factory.mktemp("later"))
    shutil.copytree(rnd.store(), later.store())                         # the store as the save left it
    os.remove(later.store("data", "sessions", "S0001.json"))            # the session file was not read
    opened = later.open(today="2026-11-04")
    assert opened["last_session"]["unreflected"] is True
    later.answer("reflection")
    later.write("B.md", PART_B)
    r = later.run("--today", "2026-11-04", "close", "--work", later.path, "--reflection", json.dumps(REFLECTION), ok=False)
    assert "session file of S0001 was not found" in json.loads(r.stdout)["error"]
    shutil.copy(rnd.store("data", "sessions", "S0001.json"), later.store("data", "sessions", "S0001.json"))
    closed = later.close("2026-11-04")
    assert names(closed) == [SESSION, PAGE_FILE, STATE]
    doc = later.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["reflected"] is True and "### Questions" in doc["transcript"] and doc["date"] == DAY
    assert SAID["reflection"] in doc["closing"]
    # today's round then starts in the same job, from the closed ledger: the closed round's
    # files are set aside, the publish set stays
    out = later.run_json("--today", "2026-11-04", "start", "--work", later.path)
    assert out["last_session"]["unreflected"] is False and out["next_id"] == "S0002"
    kept = out["earlier_set_aside"]
    assert os.path.isfile(os.path.join(kept, "answers.md")) and os.path.isfile(os.path.join(kept, "B.md"))
    assert not os.path.exists(later.p("answers.md")) and not os.path.exists(later.p("B.md"))
    assert later.read_json("work.json")["session_id"] == "S0002" and "closed" not in later.read_json("work.json")
    later.write("sealed_questions.md", SEALED_QUESTIONS)
    later.answer("questions")
    later.write("feedback.md", "fb")
    later.write("round.json", dict(ROUND, log_id="S0002"))
    saved = later.run_json("--today", "2026-11-04", "save", "--work", later.path)
    assert names(saved) == [SESSION, "data/sessions/S0002.json", PAGE_FILE, PREPARED, STATE]
    idx = later.read_json("publish", "data", "page.json")
    assert sorted((s["id"], s["reflected"]) for s in idx["sessions"]) == [("S0001", True), ("S0002", False)]
    assert "Comfort 4 4 5" not in later.read_json("publish", "data", "sessions", "S0002.json")["transcript"]
    # and that save can be run again: it starts from the ledger the close wrote, not the one read
    assert later.run_json("--today", "2026-11-04", "save", "--work", later.path) == saved
    st = later.read_json("publish", "data", "state.json")
    assert [s["id"] for s in st["sessions"]] == ["S0001", "S0002"] and st["sessions"][0]["reflection"]["solid"] == "a"


# ---- one work folder, one job at a time

def test_second_round_in_the_same_work_folder_starts_clean(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    rnd.publish()                                                       # saved to the store, then read again
    again = rnd.start("2026-11-02")
    kept = again["earlier_set_aside"]
    assert kept == rnd.p("earlier", "1") and os.path.isfile(os.path.join(kept, "answers.md"))
    assert os.path.isdir(os.path.join(kept, "publish")) and os.path.isfile(os.path.join(kept, "sealed_case.md"))
    assert "warnings" not in again
    for name in ("answers.md", "feedback.md", "stage2.md", "round.json", "B.md", "sealed_case.md", "publish",
                 "before_save.json", "before_close.json", "A.md"):
        assert not os.path.exists(rnd.p(name)), name
    assert rnd.read_json("work.json")["session_id"] == "S0002" and rnd.manifest()["files"] == []
    assert rnd.answer("questions")["parts"] == ["questions"]


def test_start_again_before_any_answer_sets_nothing_aside(rnd):
    rnd.start()
    rnd.write("sealed_questions.md", SEALED_QUESTIONS)
    out = rnd.start(DAY, "--mcqs", "1")
    assert "earlier_set_aside" not in out and os.path.isfile(rnd.p("sealed_questions.md"))


def test_reread_after_a_refused_publish_replays_the_job_on_the_fresh_store(rnd, tmp_path_factory):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    # another device changed a setting in between: the publish is refused, the store is read again
    other = Round(tmp_path_factory.mktemp("other"))
    shutil.copytree(rnd.store(), other.store())
    other.open()
    other.run("settings", "--work", other.path, "--config", '{"session_minutes": 45}')
    other.publish()
    shutil.rmtree(rnd.store())
    shutil.copytree(other.store(), rnd.store())
    out = rnd.run_json("--today", DAY, "open", "--work", rnd.path, "--store", rnd.store(), "--version", "9", "--reread")
    assert out["reread"] is True and "earlier_set_aside" not in out and out["gen"] == 2
    assert os.path.isfile(rnd.p("answers.md")) and not os.path.exists(rnd.pub()) and rnd.manifest()["files"] == []
    rnd.save()
    closed = rnd.close()
    st = rnd.read_json("publish", "data", "state.json")
    assert st["config"]["session_minutes"] == 45 and [s["id"] for s in st["sessions"]] == ["S0001"]
    assert st["unreflected"] is None and closed["gen"] == 4 and rnd.manifest()["version"] == "9"
    assert names(closed) == [SESSION, PAGE_FILE, PREPARED, STATE]
    r = Work(str(tmp_path_factory.mktemp("none")))
    r = r.run("open", "--work", r.path, "--store", rnd.store(), "--reread", ok=False)
    assert "no job is open" in json.loads(r.stdout)["error"]


# ---- setup, and the other jobs

def test_init_sets_up_a_work_folder_without_a_store_and_the_first_round_can_start(tmp_path):
    w = Round(tmp_path)
    out = w.run_json("--today", DAY, "init", "--work", w.path, "--blueprint", BLUEPRINT,
                     "--config", '{"mcqs": 2}', "--profile", '{"specialty": "Geriatrics"}')
    assert out["gen"] == 1 and out["topics"] > 50 and out["work"] == w.path
    assert names(out) == [PAGE_FILE, "index.html", PREPARED, STATE] and w.manifest()["version"] is None
    assert 'name="cme-page-version"' in open(w.pub("index.html"), encoding="utf-8").read()
    st = w.read_json("publish", "data", "state.json")
    assert st["config"]["mcqs"] == 2 and st["profile"]["onboarded_at"] == DAY
    started = w.run_json("--today", DAY, "start", "--work", w.path)     # the first round, straight after setup
    assert started["onboarding_needed"] is False and started["plan"]["mcqs"] == 2
    for flag in ("--out", "--out-dir"):
        r = w.run("init", "--work", w.path, "--blueprint", BLUEPRINT, flag, w.p("x"), ok=False)
        assert r.returncode == 2 and "unrecognized arguments" in r.stderr


def test_init_does_not_replace_a_ledger_unless_asked_to_start_over(rnd):
    rnd.play_to_feedback().save()
    rnd.publish()
    rnd.open()
    r = rnd.run("init", "--work", rnd.path, "--blueprint", BLUEPRINT, ok=False)
    assert "already holds a ledger" in json.loads(r.stdout)["error"] and not os.path.exists(rnd.pub())
    out = rnd.run_json("--today", "2026-11-05", "init", "--work", rnd.path, "--blueprint", BLUEPRINT, "--start-over")
    assert names(out) == [PAGE_FILE, PREPARED, STATE]
    assert rnd.read_json("publish", "data", "state.json")["sessions"] == []
    assert rnd.read_json("publish", "data", "page.json")["sessions"] == []


def test_addendum_goes_to_the_last_session_by_default(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    rnd.publish()
    rnd.forget_job()
    rnd.open()                                                          # a later session
    out = rnd.run_json("addendum", "--work", rnd.path, "--md", rnd.write("add.md", "More discussion."))
    assert out["session"] == "S0001" and names(out) == [SESSION]
    doc = rnd.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["addendum"] == "More discussion.\n" and doc["closing"]
    out = rnd.run_json("addendum", "--work", rnd.path, "--md", rnd.write("add.md", "And more."), "--session", "S0001")
    assert rnd.read_json("publish", "data", "sessions", "S0001.json")["addendum"] == "More discussion.\n\nAnd more.\n"
    r = rnd.run("addendum", "--work", rnd.path, "--md", rnd.p("add.md"), "--session", "S0009", ok=False)
    assert "session file of S0009 was not found" in json.loads(r.stdout)["error"]


def test_review_and_its_report_go_into_one_publish_set(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    rnd.publish()
    rnd.forget_job()
    rnd.open(today="2026-11-20")
    stats = rnd.run_json("--today", "2026-11-20", "stats", "--work", rnd.path)
    assert stats["sessions"] == 1 and not os.path.exists(rnd.pub())     # read-only
    doc = rnd.run_json("--today", "2026-11-20", "review-doc", "--work", rnd.path, "--md",
                       rnd.write("report.md", "# Review"), "--headline", "Steady")
    assert doc["doc"] == "reviews/2026-11-20" and names(doc) == ["data/reviews/2026-11-20.json", PAGE_FILE]
    review = {"doc": doc["doc"], "headline": "Steady", "summary": "s", "config_changes": {"session_minutes": 30}}
    out = rnd.run_json("--today", "2026-11-20", "review", "--work", rnd.path, "--review", json.dumps(review))
    assert names(out) == ["data/reviews/2026-11-20.json", PAGE_FILE, PREPARED, STATE]
    st = rnd.read_json("publish", "data", "state.json")
    assert st["reviews"][-1]["headline"] == "Steady" and st["sessions"] == [] and st["config"]["session_minutes"] == 30
    idx = rnd.read_json("publish", "data", "page.json")
    assert [r["headline"] for r in idx["reviews"]] == ["Steady"] and [s["id"] for s in idx["sessions"]] == ["S0001"]
    # the next round is prepared in the same job from the ledger the review wrote
    assert rnd.run_json("--today", "2026-11-20", "prepare", "--work", rnd.path)["gen"] == out["gen"]
    snoozed = rnd.run_json("--today", "2026-11-20", "snooze", "--work", rnd.path, "--days", "10")
    assert snoozed["next_review_due"] == "2026-11-30" and snoozed["files"][-1]["as"] == STATE


# ---- testing mode: the store check compares the publish set with a fresh read

def test_verify_compares_the_publish_set_with_a_fresh_read_of_the_store(rnd):
    rnd.play_to_feedback().save()
    rnd.write("B.md", PART_B)
    rnd.close()
    check = rnd.p("check")
    shutil.copytree(rnd.pub(), check)
    res = rnd.run_json("verify", "--work", rnd.path, "--store", check)
    assert res["ok"] is True and res["checked"] == 4 and rnd.read_json("verify.json") == res
    os.remove(os.path.join(check, "data", "sessions", "S0001.json"))
    assert rnd.run_json("verify", "--work", rnd.path, "--store", check)["missing"] == ["data/sessions/S0001.json"]

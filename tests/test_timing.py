"""Real time per round, and a hint (issue #47). The engine notes when each step of a round
happens (`start`, `present`, `answer`, the files written as sent, `save`, `close`) and computes
the round's active time from that: the learner answering, waiting and reading, with idle
stretches cut instead of the old 180-minute cap on a whole session. The estimates move from
the defaults to the learner's own pace over ten timed rounds, and from five the close and the
page carry a hint on how their rounds compare with their budget."""
import copy
import json
import os

import pytest

from conftest import REFLECTION, ROUND, SEALED_CASE, SEALED_QUESTIONS, SKILL, Work
from examples import cme
from test_page import render, store_with

DAY = "2026-11-26"


def at(hhmm):
    return "%sT%s:00Z" % (DAY, hhmm)


def stamps(*pairs):
    return [{"what": what, "at": at(t)} for what, t in pairs]


# The owner's kind of round: 3 MCQs and an unfolding case, with the session left open at the end.
ROUND_STAMPS = stamps(
    ("start", "08:00"), ("sent:questions", "08:00"),
    ("answer:questions", "08:09"),                 # 9 min answering
    ("sent:questions_feedback", "08:11"),          # 2 min waiting; the case goes out with the feedback
    ("answer:case", "08:21"),                      # 10 min: reading the feedback, then Stage 1
    ("sent:stage2", "08:22"),                      # 1 min waiting
    ("answer:final", "08:28"),                     # 6 min answering
    ("sent:feedback", "08:31"),                    # 3 min waiting
    ("save", "08:32"),
    ("close", "10:31"))                            # the reflection, two hours later: 15 min count


# ---- the arithmetic ---------------------------------------------------------------------------

def test_a_round_is_split_into_answering_waiting_and_reading_and_idle_time_is_cut():
    t = cme.round_timing(ROUND_STAMPS)
    assert t["started_at"] == at("08:00") and t["ended_at"] == at("10:31")
    assert t["timing"] == {"answering": 25.0, "waiting": 6.0, "reading": 15.0, "idle_cut": 105.0}
    assert t["minutes"] == 46                       # not 151, and not capped at 180 either


def test_the_feedback_sent_with_the_case_is_read_before_the_case_is_answered():
    with_words = copy.deepcopy(ROUND_STAMPS)
    with_words[3]["words"] = 600                    # 3 minutes at 200 words a minute
    t = cme.round_timing(with_words)["timing"]
    assert t["reading"] == 18.0 and t["answering"] == 22.0
    with_words[3]["words"] = 60000                  # never more than half of the stretch
    t = cme.round_timing(with_words)["timing"]
    assert t["reading"] == 20.0 and t["answering"] == 20.0


def test_an_idle_stretch_counts_for_fifteen_minutes_wherever_it_falls():
    late = stamps(("start", "08:00"), ("sent:questions", "08:00"), ("answer:questions", "09:00"),
                  ("sent:feedback", "09:02"), ("close", "09:07"))
    t = cme.round_timing(late)
    assert t["timing"] == {"answering": 15.0, "waiting": 2.0, "reading": 5.0, "idle_cut": 45.0}
    assert t["minutes"] == 22


def test_a_round_without_a_case_reads_its_only_feedback_and_the_order_of_stamps_does_not_matter():
    s = stamps(("close", "08:20"), ("sent:questions_feedback", "08:12"), ("answer:questions", "08:10"),
               ("sent:questions", "08:00"), ("start", "08:00"))
    assert cme.round_timing(s)["timing"] == {"answering": 10.0, "waiting": 2.0, "reading": 8.0, "idle_cut": 0.0}


def test_a_round_written_at_the_session_makes_the_learner_wait_for_the_first_part():
    s = stamps(("start", "08:00"), ("sent:questions", "08:04"), ("answer:questions", "08:10"))
    assert cme.round_timing(s)["timing"] == {"answering": 6.0, "waiting": 4.0, "reading": 0.0, "idle_cut": 0.0}


def test_a_command_run_again_and_anything_after_the_reflection_change_nothing():
    again = ROUND_STAMPS + stamps(("save", "10:40"), ("close", "11:55"), ("answer:notes", "12:00"))
    assert cme.round_timing(again) == cme.round_timing(ROUND_STAMPS)
    assert cme.round_timing(stamps(("start", "08:00"))) is None and cme.round_timing([]) is None


def test_without_a_stamp_for_the_final_feedback_the_save_stands_for_it():
    s = [e for e in ROUND_STAMPS if e["what"] != "sent:feedback"]
    t = cme.round_timing(s)["timing"]
    assert t["waiting"] == 7.0 and t["reading"] == 15.0


def test_round_json_may_carry_its_own_stamps(work):
    work.init(today="2026-11-01")
    st = work.read_ledger()
    cme.record_round(st, dict(copy.deepcopy(ROUND), stamps=ROUND_STAMPS, reflection=REFLECTION), cme.parse_date(DAY))
    s = st["sessions"][-1]
    assert s["minutes"] == 46 and s["timing"]["idle_cut"] == 105.0 and s["started_at"] == at("08:00")


def test_only_a_start_and_an_end_give_minutes_without_timing_and_never_a_capped_value(work):
    work.init(today="2026-11-01")
    for ended, minutes in ((at("08:26"), 26), (at("13:00"), None)):
        st = work.read_ledger()
        cme.record_round(st, dict(copy.deepcopy(ROUND), started_at=at("08:00"), ended_at=ended, reflection=REFLECTION),
                         cme.parse_date(DAY))
        s = st["sessions"][-1]
        assert s["minutes"] == minutes and "timing" not in s and not cme.is_timed(s)


# ---- the engine stamps the clock itself -------------------------------------------------------

class Timed(Work):
    def cmd(self, *args):
        return self.run_json("--today", DAY, *args)

    def play(self, reflect="10:31"):
        """The round of ROUND_STAMPS through the commands, every time given with --at."""
        w = ("--work", self.path)
        self.init(today="2026-11-01")
        out = self.cmd("start", *w, "--store", self.store(), "--at", at("08:00"))
        self.write("sealed_questions.md", SEALED_QUESTIONS)
        self.write("sealed_case.md", SEALED_CASE)
        self.run("present", *w, "--block", "questions", "--at", at("08:00"))
        self.cmd("answer", *w, "--part", "questions", "--text", "Q1 B", "--at", at("08:09"))
        self.write("feedback_questions.md", "Feedback on the questions")
        self.cmd("sent", *w, "--part", "questions_feedback", "--at", at("08:11"))
        self.cmd("answer", *w, "--part", "case", "--text", "CT", "--at", at("08:21"))
        self.write("stage2.md", "Stage 2")
        self.cmd("sent", *w, "--part", "stage2", "--at", at("08:22"))
        self.cmd("answer", *w, "--part", "final", "--text", "treat", "--at", at("08:28"))
        self.write("feedback.md", "Final feedback")
        self.cmd("sent", *w, "--part", "feedback", "--at", at("08:31"))
        self.write("round.json", ROUND)
        saved = self.cmd("save", *w, "--at", at("08:32"))
        closed = None
        if reflect:
            self.cmd("answer", *w, "--part", "reflection", "--text", "Comfort 4", "--at", at(reflect))
            closed = self.cmd("close", *w, "--reflection", json.dumps(REFLECTION), "--at", at(reflect))
        return out, saved, closed


@pytest.fixture
def timed(tmp_path):
    return Timed(tmp_path)


def test_save_and_close_record_the_time_nobody_typed(timed):
    out, saved, closed = timed.play()
    assert out["started_at"] == at("08:00")
    # at the save the reflection is still to come: the time so far
    assert saved["minutes"] == 31 and saved["timing"]["reading"] == pytest.approx(0.1, abs=0.2)
    # feedback_questions.md is two words: read in no time, so the split is as in the arithmetic
    assert closed["minutes"] == 46
    assert closed["timing"] == {"answering": 25.0, "waiting": 6.0, "reading": 15.0, "idle_cut": 105.0}
    st = timed.read_json("publish", "data", "state.json")
    s = st["sessions"][-1]
    assert (s["minutes"], s["timing"], s["started_at"], s["ended_at"]) == (46, closed["timing"], at("08:00"), at("10:31"))
    assert st["agg"]["minutes"] == 46
    doc = timed.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["minutes"] == 46 and doc["timing"] == closed["timing"]
    assert timed.read_json("publish", "data", "page.json")["sessions"][0]["minutes"] == 46


def test_a_round_never_reflected_on_keeps_the_time_up_to_its_feedback(timed):
    _, saved, _ = timed.play(reflect=None)
    s = timed.read_json("publish", "data", "state.json")["sessions"][-1]
    assert s["minutes"] == saved["minutes"] == 31 and s["timing"]["idle_cut"] == 0.0


def test_a_reflection_given_in_a_later_session_does_not_restart_the_clock(timed):
    timed.play(reflect=None)
    timed.publish()
    timed.forget_job()
    timed.open(today="2026-11-28")
    timed.write("B.md", "### Discussion\n\nNone.")
    timed.run_json("--today", "2026-11-28", "close", "--work", timed.path, "--reflection", json.dumps(REFLECTION))
    s = timed.read_json("publish", "data", "state.json")["sessions"][-1]
    assert s["minutes"] == 31 and s["reflection"] is not None


def test_the_files_written_as_sent_time_the_messages_and_answer_times_the_arrival(timed):
    """No --at and no `sent`: what a real round has. The file's own time is when it went out."""
    timed.init(today="2026-11-01")
    w = ("--work", timed.path)
    timed.cmd("start", *w, "--store", timed.store())
    timed.write("sealed_questions.md", SEALED_QUESTIONS)
    timed.cmd("answer", *w, "--part", "questions", "--text", "Q1 B")
    path = timed.write("feedback_questions.md", "one two three four five")
    now = os.path.getmtime(path)
    os.utime(path, (now - 120, now - 120))                      # written two minutes before the next step
    out = timed.cmd("answer", *w, "--part", "case", "--text", "CT")
    doc = timed.read_json("times.json")
    assert doc["session"] == "S0001" and doc["first_block"] == "questions"
    by = {e["what"]: e for e in doc["stamps"]}
    assert list(by) == ["start", "answer:questions", "sent:questions_feedback", "answer:case"]
    sent, arrived = cme.parse_stamp(by["sent:questions_feedback"]["at"]), cme.parse_stamp(out["at"])
    assert 115 <= (arrived - sent).total_seconds() <= 125 and by["sent:questions_feedback"]["words"] == 5
    # the same answer filed twice is one arrival; a file is timed once, also when rewritten
    timed.cmd("answer", *w, "--part", "case", "--text", "CT")
    timed.write("feedback_questions.md", "corrected")
    timed.cmd("answer", *w, "--part", "final", "--text", "treat")
    again = timed.read_json("times.json")["stamps"]
    assert [e["what"] for e in again].count("answer:case") == 1
    assert [e for e in again if e["what"] == "sent:questions_feedback"] == [by["sent:questions_feedback"]]


def test_present_of_the_first_part_starts_the_answering_in_a_round_written_now(timed):
    timed.init(today="2026-11-01")
    w = ("--work", timed.path)
    out = timed.cmd("start", *w, "--store", timed.store(), "--at", at("08:00"))
    assert out["prepared"]["used"] is False
    assert [e["what"] for e in timed.read_json("times.json")["stamps"]] == ["start"]
    timed.write("sealed_questions.md", SEALED_QUESTIONS)
    timed.write("sealed_case.md", SEALED_CASE)
    timed.run("present", *w, "--block", "questions", "--at", at("08:04"))
    timed.run("present", *w, "--block", "case", "--at", at("08:10"))        # read ahead in turn 2: nothing goes out
    timed.run("present", *w, "--block", "questions", "--at", at("08:30"))   # printed again: the first time stands
    assert timed.read_json("times.json")["stamps"][1:] == [{"what": "sent:questions", "at": at("08:04")}]


def test_a_new_round_in_the_same_folder_starts_a_new_clock_and_a_bad_time_is_refused(timed):
    timed.play()
    out = timed.cmd("start", "--work", timed.path, "--at", at("12:00"))
    assert out["started_at"] == at("12:00")
    doc = timed.read_json("times.json")
    assert doc["session"] == "S0002" and [e["what"] for e in doc["stamps"]] == ["start"]
    r = timed.run("answer", "--work", timed.path, "--part", "questions", "--text", "x", "--at", "half past", ok=False)
    assert r.returncode == 2 and "--at must be an ISO time" in r.stdout
    assert not os.path.exists(timed.p("answers.md"))


# ---- the learner's pace -------------------------------------------------------------------------

def session(n, minutes, timing=True, mcqs=3, focused=0, fmt="unfolding"):
    s = {"id": "S%04d" % n, "date": "2026-10-%02d" % n, "minutes": minutes, "mcqs": mcqs, "focused": focused,
         "format": fmt, "items": []}
    if timing:
        s["timing"] = {"answering": minutes * 0.5, "waiting": minutes * 0.2, "reading": minutes * 0.3, "idle_cut": 0.0}
    return s


def ledger(sessions, **config):
    st = cme.new_state(cme.parse_date("2026-10-01"))
    st["config"].update(dict({"mcqs": 3, "focused": 0, "case": True, "session_minutes": 30}, **config))
    st["sessions"] = sessions
    return st


def test_sessions_of_older_versions_count_in_no_median():
    """The owner's ledger: nine rounds, two of them the old cap of 180, none with timing."""
    old = [session(i + 1, m, timing=False) for i, m in enumerate((46, 46, 180, 47, 58, 78, 75, 180, 56))]
    st = ledger(old)
    assert cme.timed_rounds(st) == [] and cme.pace(st)["factor"] == 1.0 and cme.time_hint(st) is None
    assert cme.mix_estimate(st) == ({"mcqs": 3, "focused": 0, "case": True}, 40, 0)
    # and next to timed rounds: only those count
    st = ledger(old + [session(10 + i, 60) for i in range(5)])
    assert [s["id"] for s in cme.timed_rounds(st)] == ["S0010", "S0011", "S0012", "S0013", "S0014"]
    assert cme.pace(st)["median_minutes"] == 60
    # stamps set all at once at the end are no measurement either
    assert not cme.is_timed(session(1, 1)) and cme.is_timed(session(1, 3))


@pytest.mark.parametrize("rounds, factor, estimate", [
    (0, 1.0, 40),            # the defaults
    (1, 1.05, 42),           # a tenth of the way
    (5, 1.25, 50),           # halfway
    (10, 1.5, 60),           # the learner's own pace alone
    (14, 1.5, 60),           # and no further
])
def test_estimates_move_to_the_learners_own_pace_over_ten_timed_rounds(rounds, factor, estimate):
    st = ledger([session(i + 1, 60) for i in range(rounds)])       # 60 min for rounds the defaults put at 40
    p = cme.pace(st)
    assert p["rounds"] == min(rounds, 10) and p["factor"] == factor
    mix, minutes, n = cme.mix_estimate(st)
    assert (minutes, n) == (estimate, min(rounds, 10))
    page = cme.page_doc(st)["round"]
    assert page["minutes"] == estimate and page["timed_rounds"] == min(rounds, 10)
    assert page["minutes_per"] == {"mcq": 5 * factor, "focused": 10 * factor, "case": 25 * factor}


def test_the_pace_is_per_round_against_the_defaults_for_that_rounds_own_items():
    # three different mixes, each taking 1.5 times its default: one pace, whatever the mix
    st = ledger([session(1, 60), session(2, 30, mcqs=4, fmt=None), session(3, 45, mcqs=1, focused=1, fmt="discriminate")]
                + [session(4 + i, 60) for i in range(7)], mcqs=2, focused=1)
    assert cme.pace(st)["own"] == 1.5
    assert cme.mix_estimate(st)[1] == round((2 * 5 + 10 + 25) * 1.5)
    # one runaway round does not move the median, and no round counts for more than four times its default
    st = ledger([session(i + 1, 40) for i in range(9)] + [session(10, 170)])
    assert cme.pace(st)["own"] == 1.0
    assert cme.pace(ledger([session(1, 170)] * 10))["own"] == 4.0
    # only the last ten timed rounds
    st = ledger([session(i + 1, 80) for i in range(6)] + [session(10 + i, 40) for i in range(10)])
    assert cme.pace(st)["own"] == 1.0


def test_start_settings_and_the_plan_say_what_the_estimate_is_based_on(work):
    work.init(today="2026-11-01", config={"mcqs": 3, "case": True, "session_minutes": 30})
    plain = work.start(DAY)
    assert plain["plan"]["estimated_minutes"] == 40 and "estimate_rounds" not in plain["plan"]
    assert "about 40 minutes." in plain["opening"] and "based on" not in plain["opening"]
    st = work.read_ledger()
    st["sessions"] = [session(i + 1, 56) for i in range(7)]
    work.write_ledger(st)
    work.forget_job()
    out = work.start(DAY)
    assert out["plan"]["estimated_minutes"] == 51 and out["plan"]["estimate_rounds"] == 7     # 40 × (1 + 0.7 × 0.4)
    assert out["opening"].startswith("Today's round: 3 MCQs + the case, about 51 minutes (based on your last 7 rounds).")
    assert work.read_json("plan.json")["estimated_minutes"] == 51
    changed = work.run_json("settings", "--work", work.path, "--config", '{"mcqs": 1}')
    assert changed["round"] == {"mix": "1 MCQ + the case", "estimated_minutes": 38, "basis": "based on your last 7 rounds",
                                "time_hint": changed["round"]["time_hint"]}
    assert changed["round"]["time_hint"].startswith("Your rounds take a median of 56 min against your budget of 30")


# ---- the hint -----------------------------------------------------------------------------------

def test_the_hint_appears_with_the_fifth_timed_round():
    assert cme.time_hint(ledger([session(i + 1, 56) for i in range(4)])) is None
    hint = cme.time_hint(ledger([session(i + 1, 56) for i in range(5)]))
    assert hint["text"] == ("Your rounds take a median of 56 min against your budget of 30; "
                            "dropping 3 MCQs would save about 21 min.")
    assert (hint["median"], hint["budget"], hint["rounds"], hint["saves"]) == (56, 30, 5, 21)


@pytest.mark.parametrize("config, minutes, named", [
    # 3 MCQs + unfolding case at pace 1.4 = 56: without the MCQs 35, one-step 42, without the case 21
    ({"session_minutes": 30}, 56, "dropping 3 MCQs would save about 21 min"),
    ({"session_minutes": 45}, 56, "dropping 2 MCQs would save about 14 min"),       # as much as a one-step case
    ({"session_minutes": 50}, 56, "dropping one MCQ would save about 7 min"),
    ({"session_minutes": 20}, 56, "dropping the case would save about 35 min"),
    # focused questions count too: 1 MCQ + 2 focused + case = 50 by default, here 75
    ({"session_minutes": 60, "mcqs": 1, "focused": 2}, 75, "dropping one focused question would save about 15 min"),
    ({"session_minutes": 45, "mcqs": 1, "focused": 2}, 75, "dropping 2 focused questions would save about 30 min"),
])
def test_the_hint_names_the_one_change_that_fits_the_budget_best(config, minutes, named):
    mix = {k: config.get(k, d) for k, d in (("mcqs", 3), ("focused", 0))}
    st = ledger([session(i + 1, minutes, **mix) for i in range(6)], **config)
    assert cme.time_hint(st)["text"].endswith("; %s." % named)


def test_the_hint_never_empties_the_round_and_says_so_when_the_rounds_fit():
    only_case = ledger([session(i + 1, 50, mcqs=0) for i in range(5)], mcqs=0, session_minutes=20, case_format="discriminate")
    assert cme.time_hint(only_case)["text"] == "Your rounds take a median of 50 min against your budget of 20."
    unfolding = ledger([session(i + 1, 50, mcqs=0) for i in range(5)], mcqs=0, session_minutes=20)
    assert cme.time_hint(unfolding)["drop"] == "a one-step case instead of an unfolding one"
    fits = ledger([session(i + 1, 28) for i in range(5)])
    assert cme.time_hint(fits) == {"median": 28, "budget": 30, "rounds": 5, "drop": None, "saves": None,
                                   "text": "Your rounds take a median of 28 min, within your budget of 30."}


def test_close_prints_the_hint_and_the_page_file_carries_it(timed):
    timed.init(today="2026-11-01", config={"session_minutes": 30})
    st = timed.read_ledger()
    st["sessions"] = [session(i + 1, 56) for i in range(4)]
    st["next_id"] = "S0005"
    timed.write_ledger(st)
    w = ("--work", timed.path)
    timed.cmd("start", *w, "--store", timed.store(), "--at", at("08:00"))
    for name, text in (("sealed_questions.md", SEALED_QUESTIONS), ("sealed_case.md", SEALED_CASE),
                       ("feedback.md", "Final feedback")):
        timed.write(name, text)
    timed.run("present", *w, "--block", "questions", "--at", at("08:00"))
    timed.cmd("answer", *w, "--part", "questions", "--text", "Q1 B", "--at", at("08:14"))
    timed.cmd("sent", *w, "--part", "questions_feedback", "--at", at("08:15"))
    timed.cmd("answer", *w, "--part", "final", "--text", "treat", "--at", at("08:29"))
    timed.cmd("sent", *w, "--part", "feedback", "--at", at("08:30"))
    timed.write("round.json", dict(ROUND, log_id="S0005"))
    saved = timed.cmd("save", *w, "--at", at("08:30"))
    assert "time_hint" not in saved                              # the fifth round is not finished yet
    timed.cmd("answer", *w, "--part", "reflection", "--text", "Comfort 4", "--at", at("08:40"))
    closed = timed.cmd("close", *w, "--reflection", json.dumps(REFLECTION), "--at", at("08:41"))
    assert closed["minutes"] == 40
    hint = closed["time_hint"]
    assert hint.startswith("Your rounds take a median of 56 min against your budget of 30; dropping")
    page = timed.read_json("publish", "data", "page.json")["round"]
    assert page["time_hint"] == hint and page["timed_rounds"] == 5
    stats = timed.cmd("stats", *w)["timing"]
    assert stats["timed_rounds"] == 5 and stats["median_minutes"] == 56 and stats["hint"] == hint
    assert stats["budget_minutes"] == 30 and stats["median_answering"] == 28.0


# ---- the page -----------------------------------------------------------------------------------

def page_state(sessions):
    st = ledger(sessions)
    st["profile"]["onboarded_at"] = "2026-10-01"
    return st


def test_the_page_shows_the_hint_and_what_the_estimate_is_based_on(tmp_path):
    st = page_state([session(i + 1, 56) for i in range(6)])
    doc = cme.page_doc(st)
    shown = render(store_with(tmp_path / "timed", st, page=doc))["ids"]["mix-est"]
    assert shown == ("About 50 minutes with feedback, based on your last 6 rounds · your session length is 30 min. "
                     "Your rounds take a median of 56 min against your budget of 30; dropping 3 MCQs would save about 21 min.")
    # before any round is timed: the defaults, no basis, no hint
    plain = render(store_with(tmp_path / "plain", page_state([session(i + 1, 180, timing=False) for i in range(6)])))
    assert plain["ids"]["mix-est"] == "About 40 minutes with feedback · your session length is 30 min."
    one = cme.page_doc(page_state([session(1, 56)]))
    assert "based on your last round ·" in render(store_with(tmp_path / "one", st, page=one))["ids"]["mix-est"]


def test_the_protocol_has_no_step_for_typing_a_time():
    with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert "started_at" not in text and "time_hint" in text
    assert len(text.splitlines()) <= 260
    turn = lambda n: text.split("### Turn %d." % n)[1].split("### Turn")[0]
    # the answer is filed first in its turn (it times the arrival), before the grading and the message
    for n, part in ((2, "--part questions"), (3, "--part case"), (4, "--part final"), (5, "--part reflection")):
        first_step = turn(n).split("\n2. ")[0]
        assert part in first_step or n == 5 and part in turn(n), (n, part)

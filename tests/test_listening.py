"""Issue #50: one podcast episode per topic at the end of a round. Three candidates per topic
are kept in the kits under "## Listening" (rule 8 of references/standards.md) and linted at
`finish-prepare`; the examiner's picks go from round.json into the session document as its
`listening` list; the learner's shows to prefer and to avoid live in `profile.podcast_sources`
and `config.listening` turns it all off. Both settings change what a kit holds, so changing
them sets the round prepared ahead aside."""
import json
import os

import pytest

import examples
from examples import cme, episode_link
from test_finish_prepare import DAY, Next
from test_prepared_kept import names, settings, stored_prepared, template, w  # noqa: F401 (fixtures)
from test_standards import edit, read, refused
from test_work_folder import Round
from conftest import REFLECTION, ROUND

LINK = "https://open.spotify.com/episode/4rOoJ6Egrf8K2IrywzwOMk"
PICKS = [
    {"topic": "GEN-11", "link": LINK, "show": "Example Show", "title": "Episode one", "minutes": 42,
     "why": "covers the step you missed", "source": "kit"},
    {"topic": "PULM-04", "link": episode_link("Q1", 2) + "?si=abc", "show": "Other Show", "title": "Episode two",
     "minutes": "31", "why": "the threshold you were unsure of", "source": "search"},
]


@pytest.fixture
def nxt(tmp_path):
    return Next(tmp_path).setup()


@pytest.fixture
def rnd(tmp_path):
    return Round(tmp_path).setup()


def candidate(kid="Q1", n=1):
    return "- %s | SEALED Show %d | SEALED episode on %s | %d min |" % (episode_link(kid, n), n, kid, 20 + 10 * n)


# ---------------------------------------------------------------- the kit section: definite problems block

@pytest.mark.parametrize("kit", ["kit_questions.md", "kit_case.md"])
def test_a_kit_without_its_listening_section_blocks_the_stash(nxt, kit):
    edit(nxt, kit, "## Listening\n", "")
    error = refused(nxt)
    assert "%s: section 'Listening' missing (a heading for each: '## Listening')" % kit in error
    assert "rule 8 for kits" in error


def test_a_topic_without_its_line_in_the_listening_section_blocks_the_stash(nxt):
    edit(nxt, "kit_questions.md", "Q2 | points:", "Second | points:")
    assert "kit_questions.md: Listening has no line for Q2" in refused(nxt)
    edit(nxt, "kit_questions.md", "Second | points:", "Q2 | points:")
    edit(nxt, "kit_case.md", "case | points:", "The case, points:")
    assert "kit_case.md: Listening has no line for case" in refused(nxt)


def test_the_authors_check_wants_the_section_and_not_yet_the_candidates(nxt):
    # before the checker has run, the section holds its topic lines only
    text = "\n".join(l for l in read(nxt.p("next", "kit_questions.md")).splitlines() if "spotify" not in l) + "\n"
    nxt.write(os.path.join("next", "kit_questions.md"), text)
    r = nxt.run("keys", nxt.p("next"), "--plan", nxt.p("next", "plan.json"))
    out = json.loads(r.stdout)
    assert out["ok"] is True and out["review"] == []
    edit(nxt, "kit_questions.md", "## Listening\n", "")
    r = nxt.run("keys", nxt.p("next"), "--plan", nxt.p("next", "plan.json"), ok=False)
    assert "kit_questions.md: section 'Listening' missing (a heading for each: '## Listening')" in json.loads(r.stdout)["problems"]


def test_with_listening_off_the_plan_says_so_and_the_kits_need_no_section(tmp_path):
    nxt = Next(tmp_path).setup(config={"listening": False})
    plan = nxt.read_json("next", "plan.json")
    assert plan["listening"] is False
    assert "Listening" not in read(nxt.p("next", "kit_case.md"))          # the example author left it out
    _, out = nxt.check().finish()
    assert out["stashed"] is True and out["recheck"] == []


# ---------------------------------------------------------------- the candidates: one pass back to the checker

@pytest.mark.parametrize("old,new,says", [
    ("https://open.spotify.com/episode/", "https://open.spotify.com/show/", "link"),
    ("https://open.spotify.com/episode/", "https://example.org/episode/", "link"),
    ("| 30 min |", "| 120 min |", "length"),
    ("| 30 min |", "| long |", "length"),
    ("| covers: SEALED content | matches: SEALED point", "", "fields"),
])
def test_a_malformed_candidate_sends_the_checker_back_once_and_is_then_accepted(nxt, old, new, says):
    text = read(nxt.p("next", "kit_case.md"))
    line = next(l for l in text.splitlines() if l.startswith(candidate("case", 1)))
    nxt.write(os.path.join("next", "kit_case.md"), text.replace(line, line.replace(old, new)))
    _, out = nxt.check().finish()
    assert out["stashed"] is False and not nxt.stashed()
    assert out["recheck"] == ["evidence_case.md"] and out["revise"] is False       # the checker, not the author
    assert out["lint"]["listening"] == 1 and "author" not in out["next"]
    assert "evidence_check.md §3 and §6" in out["next"] and out["next"].endswith("--revised")
    details = read(nxt.p("next", "lint.md"))
    assert "kit_case.md, Listening, case: 1 of 3 candidates malformed (%s)" % says in details
    # one pass only: what is still found is accepted and listed
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True and nxt.stashed()
    assert out["warnings"] == ["accepted after one revision: kit_case.md: the listening candidates of 1 topic are "
                               "not three episodes in form (references/standards.md, rule 8)"]


def test_fewer_than_three_candidates_need_a_line_saying_so(nxt):
    edit(nxt, "kit_questions.md", candidate("Q1", 3), "- gone |")
    text = read(nxt.p("next", "kit_questions.md"))
    nxt.write(os.path.join("next", "kit_questions.md"),
              "\n".join(l for l in text.splitlines() if not l.startswith("- gone")) + "\n")
    _, out = nxt.check().finish()
    assert out["recheck"] == ["evidence_questions.md"] and out["stashed"] is False
    assert "Listening, Q1: 2 usable candidates, 3 wanted" in read(nxt.p("next", "lint.md"))
    edit(nxt, "kit_questions.md", "Q1 | points: SEALED point tested; SEALED tempting wrong turn\n",
         "Q1 | points: SEALED point tested; SEALED tempting wrong turn\n- none: only two episodes of 15 to 90 minutes\n")
    _, out = nxt.finish()
    assert out["stashed"] is True and out["recheck"] == [] and "warnings" not in out


def test_a_topic_with_no_episode_at_all_passes_when_the_kit_says_so(nxt):
    text = read(nxt.p("next", "kit_case.md"))
    text = "\n".join(l for l in text.splitlines() if "spotify" not in l) + "\nnone: nothing of 15 to 90 minutes\n"
    nxt.write(os.path.join("next", "kit_case.md"), text)
    _, out = nxt.check().finish()
    assert out["stashed"] is True and out["recheck"] == []


def test_a_show_the_learner_avoids_is_never_kept_as_a_candidate(tmp_path):
    nxt = Next(tmp_path)
    nxt.init(today=DAY, profile={"podcast_sources": {"trusted": ["Good Show"], "avoid": ["sealed show 2"]}})
    nxt.open(today=DAY)
    nxt.run("--today", DAY, "prepare", "--work", nxt.path)
    plan = nxt.read_json("next", "plan.json")
    assert plan["podcast_sources"] == {"trusted": ["Good Show"], "avoid": ["sealed show 2"]}
    for name, text in examples.sealed_files(nxt.read_ledger(), plan).items():
        nxt.write(os.path.join("next", name), text)
    _, out = nxt.check().finish()
    assert out["recheck"] == ["evidence_questions.md", "evidence_case.md"] and out["stashed"] is False
    assert "1 of 3 candidates malformed (avoided show)" in read(nxt.p("next", "lint.md"))


def test_without_a_checker_the_candidates_are_not_counted(nxt):
    for kit in ("kit_questions.md", "kit_case.md"):
        text = "\n".join(l for l in read(nxt.p("next", kit)).splitlines() if "spotify" not in l) + "\n"
        nxt.write(os.path.join("next", kit), text)
    _, out = nxt.finish("--no-evidence")
    assert out["stashed"] is True and "recheck" not in out and "listening" not in out["lint"]


def test_the_lint_prints_nothing_of_the_candidates(nxt):
    edit(nxt, "kit_case.md", "| 30 min |", "| 200 min |")
    r, out = nxt.check().finish()
    assert "SEALED" not in r.stdout and "spotify" not in r.stdout


def test_reading_the_listening_section():
    kit = ("## Q1\nnotes\n\n## Listening\nSources | trusted: A | avoid: B\n"
           "**Q1** | points: one; two\n"
           "1. %s | Show | Title | 45 min | covers: x | matches: one\n"
           "- none: one only\n"
           "q2 | points: three\n"
           "## Reading\n- https://example.org | not a candidate\n" % LINK)
    topics = cme.listening_topics(kit)
    assert list(topics) == ["Q1", "Q2"]
    assert topics["Q1"]["none"] is True and topics["Q1"]["entries"] == [
        [LINK, "Show", "Title", "45 min", "covers: x", "matches: one"]]
    assert topics["Q2"] == {"entries": [], "none": False}
    assert cme.listening_topics("## Q1\nnotes\n") is None
    assert cme.listening_entry_flaws(topics["Q1"]["entries"][0]) == []
    assert cme.listening_entry_flaws(topics["Q1"]["entries"][0], avoid=["show"]) == ["avoided show"]
    assert cme.listening_entry_flaws([LINK + "?si=x", "Show", "Title", "14 min", "c", "m"]) == ["link", "length"]


# ---------------------------------------------------------------- the picks: from round.json into the session document

def test_save_writes_the_picks_into_the_session_document_and_not_into_the_ledger(rnd):
    rnd.play_to_feedback(rnd=dict(ROUND, listening=PICKS))
    saved = rnd.save()
    assert saved["warnings"] == [] and saved["listening"] == 2
    doc = rnd.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["listening"] == [
        {"topic": "GEN-11", "link": LINK, "show": "Example Show", "title": "Episode one", "minutes": 42,
         "why": "covers the step you missed", "source": "kit"},
        {"topic": "PULM-04", "link": episode_link("Q1", 2), "show": "Other Show", "title": "Episode two",
         "minutes": 31, "why": "the threshold you were unsure of", "source": "search"}]
    assert "spotify" not in json.dumps(rnd.read_json("publish", "data", "state.json"))
    assert "listening" not in rnd.read_json("record.json")
    # the close keeps the list; saving again gives the same document
    again = rnd.save()
    assert again["listening"] == 2
    rnd.answer("reflection")
    rnd.write("B.md", "### Discussion (verbatim)\n\nNone.\n")
    rnd.close("2026-11-03")
    assert rnd.read_json("publish", "data", "sessions", "S0001.json")["listening"] == doc["listening"]


def test_a_pick_that_is_not_complete_is_left_out_with_a_warning(rnd):
    picks = [PICKS[0],
             dict(PICKS[1], link="https://open.spotify.com/show/abc"),
             {"topic": "CARD-99", "link": LINK, "show": "S", "title": "T", "minutes": 20, "why": "w"},
             dict(PICKS[0], title="again"),
             {"topic": "HEME-01", "link": LINK, "show": "S", "title": "", "minutes": 0, "why": "w"}]
    rnd.play_to_feedback(rnd=dict(ROUND, listening=picks))
    saved = rnd.save()
    assert [p["topic"] for p in rnd.read_json("publish", "data", "sessions", "S0001.json")["listening"]] == ["GEN-11"]
    assert saved["listening"] == 1 and len(saved["warnings"]) == 4
    assert saved["warnings"][0].startswith("listening pick 2: left out of the session document; correct link")
    assert "topic (one of this round's:" in saved["warnings"][1]
    assert "topic (one pick per topic)" in saved["warnings"][2]
    assert saved["warnings"][3].endswith("correct title, minutes")


def test_a_round_without_listening_has_no_list_and_an_empty_list_is_kept(rnd):
    rnd.play_to_feedback()
    assert "listening" not in rnd.save()
    assert "listening" not in rnd.read_json("publish", "data", "sessions", "S0001.json")
    rnd.write("round.json", dict(ROUND, listening=[]))           # nothing suitable for any topic
    assert rnd.save()["listening"] == 0
    assert rnd.read_json("publish", "data", "sessions", "S0001.json")["listening"] == []


# ---------------------------------------------------------------- the sources: asked once

def test_start_says_whether_listening_is_on_and_that_the_sources_are_still_to_be_asked(rnd):
    out = rnd.start()
    assert out["listening"] == {"on": True, "trusted": [], "avoid": [], "ask_sources": True}


def test_the_answer_given_with_the_reflection_is_kept_and_not_asked_again(rnd):
    rnd.play_to_feedback(rnd=dict(ROUND, listening=PICKS))
    rnd.save()
    rnd.write("B.md", "### Discussion (verbatim)\n\nNone.\n")
    closed = rnd.close("2026-11-03", dict(REFLECTION, podcast_sources={"trusted": [" The  Curbsiders ", "the curbsiders"],
                                                                      "avoid": "Example Show"}))
    assert closed["podcast_sources"] == {"trusted": ["The Curbsiders"], "avoid": ["Example Show"]}
    st = rnd.read_json("publish", "data", "state.json")
    assert st["profile"]["podcast_sources"] == closed["podcast_sources"]
    rnd.publish()
    rnd.forget_job()
    out = rnd.start("2026-11-06")
    assert out["listening"] == {"on": True, "trusted": ["The Curbsiders"], "avoid": ["Example Show"],
                                "ask_sources": False}


def test_no_answer_counts_as_none_named_once_listening_was_shown(rnd):
    rnd.play_to_feedback(rnd=dict(ROUND, listening=PICKS))
    rnd.save()
    rnd.write("B.md", "### Discussion (verbatim)\n\nNone.\n")
    rnd.close("2026-11-03", {"skipped": True})
    assert rnd.read_json("publish", "data", "state.json")["profile"]["podcast_sources"] == {"trusted": [], "avoid": []}


def test_a_round_without_a_listening_section_leaves_the_question_for_later(rnd):
    rnd.play_to_feedback()
    rnd.save()
    rnd.write("B.md", "### Discussion (verbatim)\n\nNone.\n")
    rnd.close("2026-11-03")
    assert rnd.read_json("publish", "data", "state.json")["profile"]["podcast_sources"] is None


def test_sources_given_at_setup_are_kept_in_their_one_form(tmp_path):
    r = Round(tmp_path)
    r.init(today=DAY, profile={"podcast_sources": {"trusted": ["A", "a ", ""], "avoid": None}})
    assert r.read_ledger()["profile"]["podcast_sources"] == {"trusted": ["A"], "avoid": []}
    assert r.start()["listening"]["ask_sources"] is False


# ---------------------------------------------------------------- the settings, and the prepared round

@pytest.mark.parametrize("flag,change,named", [
    ("--config", {"listening": False}, "listening"),
    ("--profile", {"podcast_sources": {"trusted": ["Example Show"]}}, "profile.podcast_sources"),
    ("--profile", {"podcast_sources": {"avoid": ["Example Show"]}}, "profile.podcast_sources"),
])
def test_listening_settings_change_the_kits_so_the_prepared_round_is_set_aside(w, flag, change, named):
    out = settings(w, flag, json.dumps(change))
    assert out["prepared"]["kept"] is False and out["prepared"]["changed"] == [named]
    assert "data/prepared.json" in names(out)
    assert out["listening"]["on"] is (flag != "--config")


@pytest.mark.parametrize("flag,change", [
    ("--config", {"listening": True}),                                  # it is on already
    ("--profile", {"podcast_sources": {"trusted": [], "avoid": []}}),   # "none": what the round was written with
])
def test_saying_what_already_holds_keeps_the_prepared_round(w, flag, change):
    packed = stored_prepared(w)
    out = settings(w, flag, json.dumps(change))
    assert out["prepared"]["kept"] is True and "data/prepared.json" not in names(out)
    assert stored_prepared(w) == packed


def test_a_ledger_older_than_the_setting_has_listening_on(w):
    st = w.read_ledger()
    st["config"].pop("listening")
    st["profile"].pop("podcast_sources")
    w.write_ledger(st)
    out = settings(w, "--config", json.dumps({"listening": True}))
    assert out["prepared"]["kept"] is True and out["listening"]["on"] is True and out["listening"]["ask_sources"] is True


def test_sources_are_stored_in_one_form_and_a_mistyped_setting_is_refused(w):
    out = settings(w, "--profile", json.dumps({"podcast_sources": {"trusted": ["A", "B"], "avoid": ["C"]}}))
    assert out["listening"] == {"on": True, "trusted": ["A", "B"], "avoid": ["C"], "ask_sources": False}
    out = settings(w, "--profile", json.dumps({"podcast_sources": {"avoid": []}}))     # one list changed, the other kept
    assert out["listening"]["trusted"] == ["A", "B"] and out["listening"]["avoid"] == []
    for flag, bad in (("--profile", {"podcast_sources": ["A"]}), ("--profile", {"podcast_sources": {"liked": ["A"]}}),
                      ("--profile", {"podcast_sources": {"trusted": [1]}}), ("--config", {"listening": "no"})):
        r = w.run("--today", DAY, "settings", "--work", w.path, flag, json.dumps(bad), ok=False)
        assert r.returncode != 0 and json.loads(r.stdout)["ok"] is False

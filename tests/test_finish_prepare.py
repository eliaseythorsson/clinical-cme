"""Issue #11: one command finishes preparing a round (`finish-prepare`: read the evidence check,
say whether the author must revise, pack the round when clean), and one command changes settings.
Both work on the work folder alone and write into its publish set (issue #52)."""
import json
import os

import pytest

import examples
from conftest import Work
from examples import cme

DAY = "2026-11-02"
CLAIM = "SECRET-CLAIM about SECRET-DRUG 40 mg"


def evidence(contradicted=0, claims=3, tail=None, not_verified=0, tried=True, says=None):
    """An evidence file as references/evidence_check.md §4 has it: the last `not_verified` of its
    claims are not verified (with their `Tried:` line unless `tried` is false); `says` is the
    number its `Checked:` line gives, when that is not the number of such blocks."""
    blocks = []
    for i in range(claims):
        failed = i >= claims - not_verified
        blocks.append("### %d. %s\n**Status:** %s\n**What the source says:** %s.\n**Source:** SECRET-SOCIETY 2025.\n"
                      "%s**Note:** the key is contradicted: %s.\n"
                      % (i + 1, CLAIM, "not verified" if failed else "confirmed", CLAIM,
                         "**Tried:** PMC (browser check); PubMed abstract (no figure); SECRET-ROUTE\n"
                         if failed and tried else "", CLAIM))
    end = tail if tail is not None else "Checked: %s, %d claims, %d not verified\nKeys contradicted: %d\n" % (
        DAY, claims, not_verified if says is None else says, contradicted)
    return "\n".join(blocks) + "\n" + end


class Next(Work):
    """A work folder in which the next round was planned and drafted into next/."""

    def setup(self, config=None):
        self.init(today=DAY, config=config)
        self.open(today=DAY)
        self.run("--today", DAY, "prepare", "--work", self.path)
        st, plan = self.read_ledger(), self.read_json("next", "plan.json")
        for name, text in examples.sealed_files(st, plan).items():
            self.write(os.path.join("next", name), text)
        return self

    def check(self, questions=0, case=0):
        for part, n in (("questions", questions), ("case", case)):
            if n is not None:
                self.write(os.path.join("next", "evidence_%s.md" % part), evidence(n))
        return self

    def finish(self, *extra, ok=True):
        r = self.run("finish-prepare", "--work", self.path, *extra, ok=ok)
        return r, json.loads(r.stdout)

    def stashed(self):
        return os.path.isfile(self.pub("data", "prepared.json"))

    def payload(self):
        return cme.unpack(self.read_json("publish", "data", "prepared.json")["payload"])


@pytest.fixture
def nxt(tmp_path):
    return Next(tmp_path).setup()


# ---------------------------------------------------------------- finish-prepare

def test_a_clean_round_is_stashed_in_the_same_command(nxt):
    _, out = nxt.check().finish()
    assert out["ok"] and out["stashed"] is True and out["revise"] is False and out["contradicted"] == 0
    assert out["evidence"] == {"evidence_questions.md": 0, "evidence_case.md": 0}
    assert [f["as"] for f in out["files"]] == ["data/prepared.json"]
    assert set(out["has"]) == {"questions", "case", "kit_questions", "kit_case", "evidence_questions", "evidence_case"}
    files = nxt.payload()["files"]
    assert set(files) == set(cme.PREPARED_FILES)
    assert out["publish"] == nxt.p("publish.json") and nxt.read_json("publish.json")["files"] == out["files"]
    # the prepared round, once published, is one `start` takes
    nxt.publish()
    r = nxt.start("2026-11-03")
    assert r["prepared"]["used"] is True and "evidence_case.md" in r["prepared"]["ready"]


def test_prepare_and_finish_prepare_follow_the_current_ledger_without_being_given_one(tmp_path):
    """A settings change earlier in the same job: the next round is planned and packed for the
    changed ledger, which neither command was told about."""
    nxt = Next(tmp_path)
    nxt.init(today=DAY)
    nxt.open(today=DAY)
    changed = nxt.run_json("--today", DAY, "settings", "--work", nxt.path, "--config", '{"mcqs": 2}')
    out = nxt.run_json("--today", DAY, "prepare", "--work", nxt.path)
    assert out["gen"] == changed["gen"] and out["mcqs"] == 2 and out["out"] == nxt.p("next", "plan.json")
    st, plan = nxt.read_json("publish", "data", "state.json"), nxt.read_json("next", "plan.json")
    for name, text in examples.sealed_files(st, plan).items():
        nxt.write(os.path.join("next", name), text)
    _, done = nxt.check().finish()
    assert done["stashed"] is True and done["gen"] == changed["gen"]
    assert [f["as"] for f in done["files"]] == ["data/index.json", "data/prepared.json", "data/state.json"]
    assert nxt.read_json("publish", "data", "prepared.json")["gen"] == changed["gen"]
    # neither command has a place for a ledger path
    for cmd in ("prepare", "finish-prepare"):
        r = nxt.run(cmd, nxt.ledger, "--work", nxt.path, ok=False)
        assert r.returncode == 2 and "unrecognized arguments" in r.stderr
        r = nxt.run(cmd, ok=False)
        assert r.returncode == 2 and "--work" in r.stderr


def test_prepare_if_needed_finds_the_prepared_round_itself(nxt):
    nxt.check().finish()
    again = nxt.run_json("--today", DAY, "prepare", "--work", nxt.path, "--if-needed")
    assert again == {"ok": True, "prepare": False, "why": "a round is already prepared"}
    nxt.publish()
    nxt.open(today=DAY)                                       # a later prepare-only session
    again = nxt.run_json("--today", DAY, "prepare", "--work", nxt.path, "--if-needed")
    assert again["prepare"] is False


@pytest.mark.parametrize("missing", ["questions", "case"])
def test_a_missing_evidence_file_is_reported_not_treated_as_clean(nxt, missing):
    nxt.check(**{missing: None})
    r, out = nxt.finish(ok=False)
    assert r.returncode != 0 and out["ok"] is False
    assert "evidence_%s.md is missing" % missing in out["error"] and "Nothing was stashed" in out["error"]
    assert not nxt.stashed()


def test_both_missing_evidence_files_are_named(nxt):
    r, out = nxt.finish(ok=False)
    assert r.returncode != 0
    assert "evidence_questions.md is missing" in out["error"] and "evidence_case.md is missing" in out["error"]
    assert not nxt.stashed()


def test_an_empty_or_unfinished_evidence_file_is_reported(nxt):
    nxt.check()
    nxt.write(os.path.join("next", "evidence_questions.md"), "  \n")
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(tail="Checked: today, 3 claims, 0 not verified\n"))
    r, out = nxt.finish(ok=False)
    assert r.returncode != 0
    assert "evidence_questions.md is empty" in out["error"]
    assert "evidence_case.md has no `Keys contradicted: <n>` line" in out["error"]
    assert not nxt.stashed()


# ---------------------------------------------------------------- claims not verified (issue #44)

def test_not_verified_counts_are_reported_per_file(nxt):
    nxt.write(os.path.join("next", "evidence_questions.md"), evidence(claims=5, not_verified=1))
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(claims=6, not_verified=2))
    _, out = nxt.finish()
    assert out["not_verified"] == {"evidence_questions.md": {"claims": 5, "not_verified": 1, "untried": 0},
                                   "evidence_case.md": {"claims": 6, "not_verified": 2, "untried": 0}}
    assert out["not_verified_total"] == 3 and out["claims_total"] == 11
    # a third or less of a file's claims: kept as it is, nothing to do
    assert out["recheck"] == [] and out["revise"] is False and out["stashed"] is True
    assert not any("retry" in w for w in out.get("warnings", []))


def test_more_than_a_third_not_verified_goes_back_to_the_checker_once_then_is_accepted_with_a_warning(nxt):
    """The S0037 baseline: 4 of 5 and 6 of 6."""
    nxt.write(os.path.join("next", "evidence_questions.md"), evidence(claims=5, not_verified=4))
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(claims=6, not_verified=6))
    r, out = nxt.finish()
    assert out["ok"] and out["stashed"] is False and not nxt.stashed()
    assert out["recheck"] == ["evidence_questions.md", "evidence_case.md"] and out["revise"] is False
    assert out["not_verified_total"] == 10 and out["claims_total"] == 11
    assert "checker" in out["next"] and "evidence_case.md" in out["next"] and "--revised" in out["next"]
    assert out["next"].index("checker") < out["next"].index("author")
    # the retry reached the case's sources; the questions' are still above the threshold
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(claims=6, not_verified=1))
    r, out = nxt.finish("--revised")
    assert out["stashed"] is True and nxt.stashed() and out["revised"] is True
    assert out["recheck"] == [] and out["revise"] is False and "next" not in out
    assert out["not_verified"]["evidence_questions.md"]["not_verified"] == 4
    retry = [w for w in out["warnings"] if w.startswith("accepted after one retry")]
    assert len(retry) == 1 and "evidence_questions.md: 4 of 5 claims not verified" in retry[0]
    assert "SECRET" not in r.stdout + r.stderr
    assert set(nxt.payload()["files"]) == set(cme.PREPARED_FILES)


def test_only_the_file_above_the_threshold_is_rechecked(nxt):
    nxt.write(os.path.join("next", "evidence_questions.md"), evidence(claims=3, not_verified=1))
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(claims=5, not_verified=2))
    _, out = nxt.finish()
    assert out["recheck"] == ["evidence_case.md"] and out["stashed"] is False


def test_a_retry_and_a_contradicted_key_are_one_pass(nxt):
    nxt.write(os.path.join("next", "evidence_questions.md"), evidence(contradicted=1, claims=4, not_verified=2))
    nxt.check(questions=None)
    _, out = nxt.finish()
    assert out["recheck"] == ["evidence_questions.md"] and out["revise"] is True and out["stashed"] is False
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True and out["contradicted"] == 1


def test_a_claim_given_up_without_another_route_goes_back_whatever_the_share(nxt):
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(claims=6, not_verified=1, tried=False))
    _, out = nxt.check(case=None).finish()
    assert out["not_verified"]["evidence_case.md"] == {"claims": 6, "not_verified": 1, "untried": 1}
    assert out["recheck"] == ["evidence_case.md"] and out["stashed"] is False
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True
    assert any("1 of 6 claims not verified, 1 without a `Tried:` line" in w for w in out["warnings"])


def test_a_count_line_that_undercounts_its_blocks_is_not_believed(nxt):
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(claims=6, not_verified=4, says=0))
    _, out = nxt.check(case=None).finish()
    assert out["not_verified"]["evidence_case.md"]["not_verified"] == 4 and out["recheck"] == ["evidence_case.md"]


@pytest.mark.parametrize("line", [
    "",                                             # no line at all
    "Checked: 2026-11-02",                          # no counts
    "Checked: 2026-11-02, all claims, none not verified",
    "Checked: 2026-11-02, 3 claims",
    "Checked: 2026-11-02, 3 claims, <n> not verified",
    "Checked: 2026-11-02, 3 claims, 4 not verified",    # more than there are
    "Checked: 2026-11-02, 0 claims, 0 not verified",    # nothing was checked
    "Checked 2026-11-02, 3 claims, 0 not verified",
])
def test_a_missing_or_unreadable_checked_line_stops_it(nxt, line):
    nxt.check()
    nxt.write(os.path.join("next", "evidence_case.md"), evidence(tail=line + "\nKeys contradicted: 0\n"))
    for extra in ((), ("--revised",)):
        r, out = nxt.finish(*extra, ok=False)
        assert r.returncode != 0 and out["ok"] is False and not nxt.stashed()
        assert "evidence_case.md has no readable `Checked: <date>, <n> claims, <n> not verified` line" in out["error"]
        assert "evidence_questions.md" not in out["error"] and "Nothing was stashed" in out["error"]
        assert "SECRET" not in r.stdout + r.stderr
    # without a checker the files are not read at all
    _, out = nxt.finish("--no-evidence")
    assert out["stashed"] is True and out["evidence"] == "not checked"
    assert "not_verified" not in out and "recheck" not in out


@pytest.mark.parametrize("line, counts", [
    ("Checked: 2026-11-02, 5 claims, 2 not verified", (5, 2)),
    ("Checked: 2026-11-02, 1 claim, 0 not verified", (1, 0)),
    ("**Checked:** 2 November 2026, 6 claims, 6 not verified", (6, 6)),
    ("checked: Nov 2, 2026, 4 claims, 1 not verified.", (4, 1)),
    ("`Checked: 2026-11-02,  3 claims,  0 not verified`", (3, 0)),
    ("Checked: <date>, <n> claims, <n> not verified", None),
    ("Not checked: 2026-11-02, 3 claims, 0 not verified", None),
    ("Checked: 2026-11-02, 3 claims, 0 not verified (two more pending)", None),
])
def test_reading_the_checked_line(line, counts):
    found = cme.checked_counts("### 1. claim\n**Status:** confirmed\n\n%s\nKeys contradicted: 0\n" % line)
    assert (found and (found["claims"], found["not_verified"])) == counts


def test_a_file_written_twice_counts_its_last_check():
    first = evidence(claims=4, not_verified=3, tried=False)
    again = evidence(claims=4, not_verified=1)
    assert cme.checked_counts(first + "\n" + again) == {"claims": 4, "not_verified": 1, "untried": 0}


@pytest.mark.parametrize("claims, not_verified, back", [
    (3, 1, False), (6, 2, False), (5, 1, False), (5, 2, True), (4, 2, True), (6, 3, True), (1, 1, True), (3, 0, False),
])
def test_the_threshold_is_more_than_a_third(claims, not_verified, back):
    assert cme.needs_recheck({"claims": claims, "not_verified": not_verified, "untried": 0}) is back


def test_the_checker_brief_requires_other_routes_before_not_verified():
    """The acceptance criterion of issue #44 that is about the brief."""
    with open(os.path.join(os.path.dirname(cme.__file__), "..", "references", "evidence_check.md"),
              encoding="utf-8") as fh:
        brief = fh.read()
    for route in ("pubmed.ncbi.nlm.nih.gov", "europepmc.org", "HAL", "doi.org", "medicines.org.uk", "EMA", "DailyMed"):
        assert route in brief, route
    assert "**Tried:**" in brief and "not reached" in brief and "browser check" in brief
    assert "Checked: <date>, <n> claims, <n> not verified\nKeys contradicted: <n>" in brief


def test_contradicted_keys_are_counted_and_the_author_must_revise(nxt):
    r, out = nxt.check(questions=2, case=1).finish()
    assert out["ok"] and out["contradicted"] == 3 and out["revise"] is True and out["stashed"] is False
    assert out["evidence"] == {"evidence_questions.md": 2, "evidence_case.md": 1}
    assert "revise" in out["next"] and "--revised" in out["next"]
    assert not nxt.stashed()
    # after the revision the same command stashes, and still says what the check had found
    _, out = nxt.finish("--revised")
    assert out["stashed"] is True and out["revise"] is False and out["revised"] is True and out["contradicted"] == 3
    assert nxt.stashed()


def test_nothing_of_the_content_is_printed(nxt):
    st, plan = nxt.read_ledger(), nxt.read_json("next", "plan.json")
    labels = [t["label"] for t in cme.bp_topics(st).values()]
    for extra in ((), ("--revised",)):
        r, _ = nxt.check(questions=1).finish(*extra)
        shown = (r.stdout + r.stderr).replace(nxt.path, "")
        assert "SECRET" not in shown and "SEALED" not in shown and "Example" not in shown
        assert not any(it.get("topic") and it["topic"] in shown for it in plan["items"])
        assert not any(label in shown for label in labels)
    nxt.write(os.path.join("next", "evidence_case.md"), "### 1. %s\n**Note:** %s\n" % (CLAIM, CLAIM))
    r, _ = nxt.finish(ok=False)
    assert "SECRET" not in r.stdout + r.stderr


@pytest.mark.parametrize("line, n", [
    ("Keys contradicted: 0", 0), ("Keys contradicted: 2", 2), ("**Keys contradicted:** 1", 1),
    ("keys contradicted:3", 3), ("  Keys contradicted: 4  ", 4), ("`Keys contradicted: 5`", 5),
    ("Keys contradicted: none", None), ("Keys contradicted: <n>", None), ("No keys contradicted: 0 of them", None),
    ("", None),
])
def test_reading_the_count_line(line, n):
    assert cme.contradicted_keys("### 1. claim\n**Status:** confirmed\n\nChecked: d, 1 claims, 0 not verified\n"
                                 + line + "\n") == n


def test_a_file_checked_twice_counts_its_last_line():
    assert cme.contradicted_keys("Keys contradicted: 2\n\n### again\nKeys contradicted: 0\n") == 0


def test_without_a_checker_the_round_is_stashed_without_evidence(nxt):
    nxt.write(os.path.join("next", "evidence_questions.md"), "half-written")
    _, out = nxt.finish("--no-evidence")
    assert out["stashed"] is True and out["evidence"] == "not checked" and out["revise"] is False
    assert not any(h.startswith("evidence") for h in out["has"])
    # no evidence file goes along, so the next session still has the sources checked
    assert set(nxt.payload()["files"]) == {"sealed_questions.md", "sealed_case.md", "kit_questions.md", "kit_case.md"}


def test_evidence_is_asked_only_for_the_parts_the_round_has(tmp_path):
    nxt = Next(tmp_path).setup(config={"case": False})
    nxt.check(case=None)
    _, out = nxt.finish()
    assert out["stashed"] is True and out["evidence"] == {"evidence_questions.md": 0}


def test_a_case_that_was_not_written_needs_no_evidence(nxt):
    os.remove(nxt.p("next", "sealed_case.md"))
    _, out = nxt.check(case=None).finish()
    assert out["stashed"] is True and out["evidence"] == {"evidence_questions.md": 0}
    assert any("sealed_case.md" in w for w in out["warnings"])


def test_a_missing_first_part_or_a_plan_for_another_ledger_stops_it(nxt):
    nxt.check()
    nxt.run("--today", DAY, "settings", "--work", nxt.path, "--config", '{"lab_units": "conventional"}')   # the ledger moved on
    r, out = nxt.finish(ok=False)
    assert r.returncode != 0 and "not made by `prepare` from this ledger" in out["error"]
    assert not nxt.stashed() or nxt.read_json("publish", "data", "prepared.json") == {"v": 1, "empty": True}
    nxt.run("--today", DAY, "prepare", "--work", nxt.path)
    os.remove(nxt.p("next", "sealed_questions.md"))
    r, out = nxt.finish(ok=False)
    assert r.returncode != 0 and "sealed_questions.md" in out["error"]


def test_finish_prepare_needs_a_plan_made_by_prepare_in_this_work_folder(tmp_path):
    w = Next(tmp_path)
    w.init(today=DAY)
    r = w.run("finish-prepare", "--work", w.path, ok=False)
    assert "no job is open" in json.loads(r.stdout)["error"]
    w.open(today=DAY)
    r = w.run("finish-prepare", "--work", w.path, ok=False)
    assert "run `prepare --work" in json.loads(r.stdout)["error"]


# ---------------------------------------------------------------- finish-prepare checks the key headers (issue #36)

def edit(nxt, name, old, new, count=1):
    path = nxt.p("next", name)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert old in text
    nxt.write(os.path.join("next", name), text.replace(old, new, count))


def refused(nxt, *extra):
    r, out = nxt.finish(*extra, ok=False)
    assert r.returncode != 0 and out["ok"] is False and "stashed" not in out
    assert "Nothing was stashed" in out["error"] and "key headers" in out["error"]
    assert not nxt.stashed() and not os.path.exists(nxt.pub())
    return out["error"]


def test_the_example_round_has_a_header_for_every_item(nxt):
    out = nxt.run_json("keys", nxt.p("next"), "--plan", nxt.p("next", "plan.json"))
    assert out["ok"] is True and out["keys"]["sealed_case.md"] == ["case"]
    assert out["keys"]["sealed_questions.md"][0] == "Q1"


@pytest.mark.parametrize("name, old, new, expect", [
    ("sealed_questions.md", "stem_summary: Example stem Q1\n", "", "sealed_questions.md, key Q1: 'stem_summary' is missing"),
    ("sealed_questions.md", "topic: ", "topik: ", "sealed_questions.md, key Q1: 'topik' is not a field of a mcq header"),
    ("sealed_questions.md", "type: mcq", "type: quiz", "sealed_questions.md, key Q1: 'type' must be one of"),
    ("sealed_questions.md", "<!-- /key -->", "", "sealed_questions.md: a key header is not closed"),
    ("sealed_questions.md", "<!-- key: Q2 -->", "<!-- key: Q1 -->", "key Q1: there are two headers with this id"),
    ("sealed_case.md", "patient: 60F\n", "", "sealed_case.md, key case: 'patient' is missing"),
    ("sealed_case.md", "setting: ward", "setting ward", "sealed_case.md, key case: line 6 is not 'field: value'"),
])
def test_a_malformed_header_stops_it_and_nothing_is_stashed(nxt, name, old, new, expect):
    edit(nxt.check(), name, old, new)
    assert expect in refused(nxt)


@pytest.mark.parametrize("name", ["sealed_questions.md", "sealed_case.md"])
def test_a_sealed_file_without_headers_stops_it(nxt, name):
    nxt.check()
    with open(nxt.p("next", name), encoding="utf-8") as fh:
        text = fh.read()
    nxt.write(os.path.join("next", name), cme.KEY_RE.sub("", text))
    assert "%s: no key header" % name in refused(nxt)


def test_a_header_missing_for_one_item_of_the_plan_stops_it(nxt):
    nxt.check()
    with open(nxt.p("next", "sealed_questions.md"), encoding="utf-8") as fh:
        text = fh.read()
    nxt.write(os.path.join("next", "sealed_questions.md"), cme.KEY_RE.sub("", text, count=1))
    assert "sealed_questions.md: the plan has 3 MCQ item(s), the keys have 2 header(s)" in refused(nxt)


def test_every_header_problem_is_named_at_once_without_content(nxt):
    edit(nxt.check(), "sealed_questions.md", "stem_summary: Example stem Q1\n", "")
    edit(nxt, "sealed_case.md", "setting: ward\n", "")
    r, out = nxt.finish(ok=False)
    assert "key Q1: 'stem_summary' is missing" in out["error"] and "key case: 'setting' is missing" in out["error"]
    plan = nxt.read_json("next", "plan.json")
    shown = (r.stdout + r.stderr).replace(nxt.path, "")
    assert "SEALED" not in shown and "Example" not in shown
    assert not any(it.get("topic") and it["topic"] in shown for it in plan["items"])


def test_a_bad_header_stops_it_whatever_the_evidence_says(nxt):
    edit(nxt, "sealed_questions.md", "stem_summary: Example stem Q1\n", "")
    refused(nxt.check(), "--no-evidence")                   # no checker run
    refused(nxt.check(questions=2))                         # keys contradicted: the header comes first
    refused(nxt.check(questions=2), "--revised")
    for part in ("questions", "case"):                      # evidence missing as well
        os.remove(nxt.p("next", "evidence_%s.md" % part))
    assert "evidence" not in refused(nxt)


def test_once_the_header_is_corrected_the_same_command_stashes(nxt):
    edit(nxt.check(), "sealed_questions.md", "reason: ", "reson: ")
    refused(nxt)
    edit(nxt, "sealed_questions.md", "reson: ", "reason: ")
    _, out = nxt.finish()
    assert out["stashed"] is True and nxt.stashed()
    # and the round it stashed is one `save` can record: every header is there for it
    files = nxt.payload()["files"]
    assert cme.parse_key_headers(files["sealed_questions.md"])[1] == []


def test_a_case_that_was_not_written_needs_no_header(nxt):
    os.remove(nxt.p("next", "sealed_case.md"))
    _, out = nxt.check(case=None).finish()
    assert out["stashed"] is True


# ---------------------------------------------------------------- settings in one command

@pytest.fixture
def store(tmp_path):
    """A work folder opened on the learner's store, which has one session in its index."""
    w = Work(tmp_path)
    w.init()
    w.save_round("2026-11-01")
    w.publish()
    w.forget_job()
    w.open()
    return w


def settings(w, *args, today="2026-11-02", ok=True):
    r = w.run("--today", today, "settings", "--work", w.path, *args, ok=ok)
    return json.loads(r.stdout) if ok else r


def test_settings_changes_the_ledger_into_the_publish_set_in_one_command(store):
    before = store.read_ledger()
    out = settings(store, "--config", '{"focused": 2}', "--profile", '{"specialty": "Geriatrics"}')
    assert out["ok"] and out["gen"] == before["gen"] + 1 and out["config"]["focused"] == 2
    assert out["specialty"] == "Geriatrics"
    assert [f["as"] for f in out["files"]] == ["data/index.json", "data/prepared.json", "data/state.json"]
    assert all(f["path"].startswith(store.pub()) for f in out["files"])
    placed = store.read_json("publish", "data", "state.json")
    assert placed["config"]["focused"] == 2 and placed["profile"]["specialty"] == "Geriatrics"
    assert placed["gen"] == out["gen"]
    # the index read with the ledger is carried over, and the prepared round is set aside
    assert [s["id"] for s in store.read_json("publish", "data", "index.json")["sessions"]] == ["S0001"]
    assert store.read_json("publish", "data", "index.json")["sessions"][0]["title"] == "t"
    assert store.read_json("publish", "data", "prepared.json") == {"v": 1, "empty": True}
    assert store.read_ledger() == before                    # the ledger as read is untouched


def test_a_second_settings_change_in_the_same_job_builds_on_the_first(store):
    first = settings(store, "--config", '{"mcqs": 4}')
    second = settings(store, "--profile", '{"lab_units": "SI"}')
    st = store.read_json("publish", "data", "state.json")
    assert second["gen"] == first["gen"] + 1 == st["gen"]
    assert st["config"]["mcqs"] == 4 and st["profile"]["lab_units"] == "SI"
    assert second["files"] == first["files"]                # one publish set, the newest version of each file


def test_settings_upgrades_an_old_page_read_with_the_ledger(store):
    with open(store.store("index.html"), "w") as fh:
        fh.write('<meta name="cme-page-version" content="1.0.0">')
    out = settings(store, "--config", '{"testing": true}')
    assert out["page_upgraded"] == {"from": "1.0.0", "to": cme.PAGE_VERSION}
    assert [f["as"] for f in out["files"]] == ["data/index.json", "index.html", "data/state.json"]
    assert os.path.isfile(store.pub("index.html"))
    again = settings(store, "--config", '{"testing": false}')
    assert "page_upgraded" not in again and "index.html" in [f["as"] for f in again["files"]]   # still to publish


def test_settings_takes_a_blueprint_and_keeps_the_index_of_the_store(store):
    idx = store.read_json("store", "data", "index.json")
    idx["sessions"][0]["title"] = "renamed"
    store.write(os.path.join("store", "data", "index.json"), idx)
    bp = store.write("bp.md", "## Cardiology (CARD)\n- CARD-01 Chest pain\n")
    out = settings(store, "--blueprint", bp)
    assert out["ok"]
    assert store.read_json("publish", "data", "index.json")["sessions"][0]["title"] == "renamed"
    assert store.read_json("publish", "data", "state.json")["blueprint"] == cme.blueprint_from_md(open(bp).read())


def test_a_refused_settings_change_writes_nothing(store):
    r = settings(store, "--config", '{"mcqs": 0, "focused": 0, "case": false}', ok=False)
    assert r.returncode != 0 and json.loads(r.stdout)["ok"] is False
    assert not os.path.exists(store.pub()) and store.read_json("publish.json")["files"] == []


def test_settings_needs_an_open_work_folder_and_takes_no_paths(store, tmp_path_factory):
    empty = str(tmp_path_factory.mktemp("empty"))
    r = store.run("settings", "--work", empty, "--config", '{"testing": true}', ok=False)
    assert r.returncode == 2 and "no job is open" in json.loads(r.stdout)["error"]
    for flag in ("--out", "--out-dir", "--index", "--page"):
        r = store.run("settings", "--work", store.path, "--config", '{"testing": true}', flag, store.p("x"), ok=False)
        assert r.returncode == 2 and "unrecognized arguments" in r.stderr

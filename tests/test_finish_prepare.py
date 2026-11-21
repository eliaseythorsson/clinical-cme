"""Issue #11: one command finishes preparing a round (`finish-prepare`: read the evidence check,
say whether the author must revise, stash when clean), and one command changes settings and puts
the changed ledger into the file layout (`settings --out-dir`)."""
import json
import os

import pytest

import examples
from conftest import BLUEPRINT, Work
from examples import cme

DAY = "2026-11-02"
CLAIM = "SECRET-CLAIM about SECRET-DRUG 40 mg"


def evidence(contradicted=0, claims=3, tail=None):
    """An evidence file as references/evidence_check.md §3 has it."""
    blocks = ["### %d. %s\n**Status:** confirmed\n**What the source says:** %s.\n**Source:** SECRET-SOCIETY 2025.\n"
              "**Note:** the key is contradicted: %s.\n" % (i + 1, CLAIM, CLAIM, CLAIM) for i in range(claims)]
    end = tail if tail is not None else "Checked: %s, %d claims, 0 not verified\nKeys contradicted: %d\n" % (
        DAY, claims, contradicted)
    return "\n".join(blocks) + "\n" + end


class Next(Work):
    """A work folder in which the next round was planned and drafted into next/."""

    def setup(self, config=None):
        self.run("--today", DAY, "init", "--blueprint", BLUEPRINT, "--config", json.dumps(config or {}),
                 "--out", self.p("state.json"))
        self.ledger = self.p("state.json")
        os.makedirs(self.p("next"))
        self.run("--today", DAY, "prepare", self.ledger, "--out", self.p("next", "plan.json"))
        st, plan = self.read_json("state.json"), self.read_json("next", "plan.json")
        for name, text in examples.sealed_files(st, plan).items():
            self.write(os.path.join("next", name), text)
        return self

    def check(self, questions=0, case=0):
        for part, n in (("questions", questions), ("case", case)):
            if n is not None:
                self.write(os.path.join("next", "evidence_%s.md" % part), evidence(n))
        return self

    def finish(self, *extra, ok=True):
        r = self.run("finish-prepare", self.ledger, "--work", self.path, *extra, ok=ok)
        return r, json.loads(r.stdout)

    def stashed(self):
        return os.path.isfile(self.p("out3", "data", "prepared.json"))

    def payload(self):
        return cme.unpack(self.read_json("out3", "data", "prepared.json")["payload"])


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
    # the stashed round is one `start` takes
    r = nxt.run_json("--today", "2026-11-03", "start", nxt.ledger, "--work", nxt.p("round"),
                     "--prepared", nxt.p("out3", "data", "prepared.json"))
    assert r["prepared"]["used"] is True and "evidence_case.md" in r["prepared"]["ready"]


def test_it_writes_what_stash_writes(nxt):
    nxt.check().finish()
    nxt.run("stash", nxt.ledger, "--plan", nxt.p("next", "plan.json"), "--dir", nxt.p("next"), "--out-dir", nxt.p("alt"))
    assert nxt.read_json("out3", "data", "prepared.json") == nxt.read_json("alt", "data", "prepared.json")


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
    st, plan = nxt.read_json("state.json"), nxt.read_json("next", "plan.json")
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


def test_a_missing_first_part_or_another_ledgers_plan_stops_it(nxt):
    nxt.check()
    nxt.run("--today", DAY, "settings", nxt.ledger, "--config", '{"testing": true}', "--out", nxt.p("other.json"))
    r = nxt.run("finish-prepare", nxt.p("other.json"), "--work", nxt.path, ok=False)
    assert r.returncode != 0 and "not made by `prepare` from this ledger" in r.stdout
    os.remove(nxt.p("next", "sealed_questions.md"))
    r, out = nxt.finish(ok=False)
    assert r.returncode != 0 and "sealed_questions.md" in out["error"]
    assert not nxt.stashed()


def test_the_files_can_be_named_instead_of_the_work_folder(nxt):
    nxt.check()
    out = nxt.run_json("finish-prepare", nxt.ledger, "--plan", nxt.p("next", "plan.json"), "--dir", nxt.p("next"),
                       "--out-dir", nxt.p("elsewhere"))
    assert out["stashed"] is True and os.path.isfile(nxt.p("elsewhere", "data", "prepared.json"))
    r = nxt.run("finish-prepare", nxt.ledger, ok=False)
    assert r.returncode != 0 and "--work" in r.stdout


# ---------------------------------------------------------------- settings in one command

@pytest.fixture
def store(tmp_path):
    """A work folder with the learner's store read into store/, one session in its index."""
    w = Work(tmp_path)
    w.init()
    w.save_round("2026-11-01")
    os.makedirs(w.p("store"))
    os.replace(w.p("out1", "data"), w.p("store", "data"))
    w.ledger = w.p("store", "data", "state.json")
    return w


def test_settings_changes_and_places_in_one_command(store):
    before = store.read_json("store", "data", "state.json")
    out = store.run_json("--today", "2026-11-02", "settings", store.ledger, "--config", '{"focused": 2}',
                         "--profile", '{"specialty": "Geriatrics"}', "--out-dir", store.p("outS"))
    assert out["ok"] and out["gen"] == before["gen"] + 1 and out["config"]["focused"] == 2
    assert out["specialty"] == "Geriatrics"
    assert [f["as"] for f in out["files"]] == ["data/state.json", "data/index.json", "data/prepared.json"]
    placed = store.read_json("outS", "data", "state.json")
    assert placed["config"]["focused"] == 2 and placed["profile"]["specialty"] == "Geriatrics"
    assert placed["gen"] == out["gen"]
    # the index read with the ledger is carried over, and the prepared round is set aside
    assert [s["id"] for s in store.read_json("outS", "data", "index.json")["sessions"]] == ["S0001"]
    assert store.read_json("outS", "data", "index.json")["sessions"][0]["title"] == "t"
    assert store.read_json("outS", "data", "prepared.json") == {"v": 1, "empty": True}
    assert store.read_json("store", "data", "state.json") == before      # the ledger as read is untouched


def test_one_command_gives_what_settings_then_place_gave(store):
    args = ("--config", '{"mcqs": 4, "round_set_at": "2026-11-02T10:00:00"}', "--profile", '{"lab_units": "SI"}')
    store.run("--today", "2026-11-02", "settings", store.ledger, *args, "--out", store.p("s.json"))
    store.run("place", store.p("s.json"), "--index", store.p("store", "data", "index.json"), "--out-dir", store.p("two"))
    store.run("--today", "2026-11-02", "settings", store.ledger, *args, "--out-dir", store.p("one"))
    for name in ("state.json", "index.json", "prepared.json"):
        assert store.read_json("one", "data", name) == store.read_json("two", "data", name)


def test_settings_upgrades_an_old_page_read_with_the_ledger(store):
    with open(store.p("store", "index.html"), "w") as fh:
        fh.write('<meta name="cme-page-version" content="1.0.0">')
    out = store.run_json("settings", store.ledger, "--config", '{"testing": true}', "--out-dir", store.p("outS"))
    assert out["page_upgraded"] == {"from": "1.0.0", "to": cme.PAGE_VERSION}
    assert [f["as"] for f in out["files"]][-1] == "index.html" and os.path.isfile(store.p("outS", "index.html"))


def test_settings_takes_a_named_index_and_a_blueprint(store):
    idx = store.read_json("store", "data", "index.json")
    idx["sessions"][0]["title"] = "renamed"
    other = store.write("other_index.json", idx)
    bp = store.write("bp.md", "## Cardiology (CARD)\n- CARD-01 Chest pain\n")
    out = store.run_json("settings", store.ledger, "--blueprint", bp, "--index", other, "--out-dir", store.p("outS"))
    assert out["ok"]
    assert store.read_json("outS", "data", "index.json")["sessions"][0]["title"] == "renamed"
    assert store.read_json("outS", "data", "state.json")["blueprint"] == cme.blueprint_from_md(open(bp).read())


def test_a_refused_settings_change_places_nothing(store):
    r = store.run("settings", store.ledger, "--config", '{"mcqs": 0, "focused": 0, "case": false}',
                  "--out-dir", store.p("outS"), ok=False)
    assert r.returncode != 0 and json.loads(r.stdout)["ok"] is False
    assert not os.path.exists(store.p("outS"))


def test_settings_needs_somewhere_to_write(store):
    r = store.run("settings", store.ledger, "--config", '{"testing": true}', ok=False)
    assert r.returncode != 0 and "--out-dir" in r.stdout


def test_settings_out_alone_still_writes_one_file(store):
    out = store.run_json("settings", store.ledger, "--config", '{"testing": true}', "--out", store.p("s.json"))
    assert out["out"] == store.p("s.json") and "files" not in out
    assert store.read_json("s.json")["config"]["testing"] is True

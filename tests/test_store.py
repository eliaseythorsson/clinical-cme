"""The engine handles the store (issue #57): `open` recognises the store's documents by their
content, whatever names the read tool gave them; `publish` writes a folder store itself, in write
order, after checking the folder's ledger; when another device saved first, the job is applied
again on the fresh store (`open --reread` for the page, by `publish` itself for a folder). The
two-device cases are played against the folder adapter: two work folders on one folder store."""
import json
import os
import shutil

import pytest

from conftest import ANSWERS, REFLECTION, ROUND, SEALED_CASE, SEALED_QUESTIONS
from examples import cme
from test_work_folder import DAY, PAGE_FILE, PART_B, PREPARED, SESSION, STATE, Round, names

MIX_LINE = "Your other device changed the round mix meanwhile; this round kept the mix it was played with."


class Device(Round):
    """One device's work folder on a folder store they share (`shared`)."""

    def __init__(self, path, shared):
        os.makedirs(str(path), exist_ok=True)
        super().__init__(path)
        self.shared = str(shared)

    def store(self, *parts):
        return os.path.join(self.shared, *parts)

    def push(self):
        """`publish` with the whole output (the folder adapter)."""
        return self.run_json("publish", "--work", self.path)

    def reflect(self):
        self.write("B.md", PART_B)
        return self.close()


@pytest.fixture
def two(tmp_path):
    """Two devices, one folder store with a new learner in it."""
    shared = tmp_path / "store"
    a = Device(tmp_path / "laptop", shared).setup()
    b = Device(tmp_path / "phone", shared)
    return a, b


def folder(path):
    os.makedirs(str(path), exist_ok=True)
    return path


@pytest.fixture
def rnd(tmp_path):
    return Round(tmp_path).setup()


def ledger(dev):
    return dev.read_json(dev.store("data", "state.json"))


# ---- recognising the store's documents by their content

def renamed_copy(src, dst, names):
    """The store's files as a read tool may save them: side by side, under names of its own."""
    os.makedirs(dst)
    for rel, name in names.items():
        shutil.copy(os.path.join(src, *rel.split("/")), os.path.join(dst, name))
    return dst


def test_open_recognises_the_documents_whatever_their_names(tmp_path):
    rnd = Round(folder(tmp_path / "w")).setup()
    copy = renamed_copy(rnd.store(), str(tmp_path / "read"), {
        STATE: "file_01", PAGE_FILE: "artifact-2.json", PREPARED: "x3.dat", "index.html": "f4.txt"})
    out = rnd.run_json("--today", DAY, "open", "--work", rnd.path, "--store", copy, "--version", "7")
    assert out["gen"] == 1 and out["store_files"] == [STATE, PAGE_FILE, PREPARED, "index.html"]
    assert out["recognised"] == {STATE: "file_01", PAGE_FILE: "artifact-2.json", PREPARED: "x3.dat",
                                 "index.html": "f4.txt"}
    found = rnd.read_json("work.json")["found"]
    assert found[PAGE_FILE] == os.path.join(copy, "artifact-2.json")
    # the page file read under its odd name is the one the save carries on
    page = rnd.read_json(os.path.join(copy, "artifact-2.json"))
    page["reviews"] = [{"date": "2026-10-01", "title": "kept", "headline": None}]
    rnd.write(os.path.join(copy, "artifact-2.json"), page)
    rnd.play_to_feedback(start=False).save()
    assert rnd.read_json("publish", "data", "page.json")["reviews"][0]["title"] == "kept"


def test_a_session_document_is_found_by_its_content_for_a_late_reflection(tmp_path):
    rnd = Round(folder(tmp_path / "w")).setup()
    rnd.play_to_feedback().save()
    rnd.publish()
    rnd.forget_job()
    copy = renamed_copy(rnd.store(), str(tmp_path / "read"), {STATE: "a.json", SESSION: "b.json"})
    rnd.run_json("--today", "2026-11-03", "open", "--work", rnd.path, "--store", copy, "--version", "8")
    rnd.answer("reflection")
    rnd.write("B.md", PART_B)
    closed = rnd.close("2026-11-03")
    assert names(closed) == [SESSION, PAGE_FILE, STATE]
    assert rnd.read_json("publish", "data", "sessions", "S0001.json")["reflected"] is True


def test_between_two_ledgers_found_by_content_the_higher_gen_counts_never_the_newer_file(tmp_path):
    rnd = Round(folder(tmp_path / "w")).setup()
    copy = renamed_copy(rnd.store(), str(tmp_path / "read"), {STATE: "file_a"})
    newer = rnd.read_json(os.path.join(copy, "file_a"))
    newer["gen"] = 5
    rnd.write(os.path.join(copy, "file_b"), newer)
    os.utime(os.path.join(copy, "file_b"), (1, 1))                  # written "earlier": the time does not count
    out = rnd.run_json("--today", DAY, "open", "--work", rnd.path, "--store", copy, "--version", "9")
    assert out["gen"] == 5 and out["recognised"] == {STATE: "file_b"}


def test_a_folder_stores_own_ledger_wins_over_a_conflicted_copy(rnd):
    """A sync tool left "state (conflicted copy).json" beside the ledger, with a higher gen and
    written later: the file at the store path is the ledger, and publishing works."""
    stale = rnd.read_json("store", "data", "state.json")
    stale["gen"] = 9
    rnd.write(os.path.join("store", "data", "state (conflicted copy).json"), stale)
    rnd.write(os.path.join("store", "state (conflicted copy 2).json"), stale)
    out = rnd.open(today=DAY)
    assert out["gen"] == 1 and "recognised" not in out
    rnd.run_json("settings", "--work", rnd.path, "--config", '{"lab_units": "SI"}')
    assert rnd.publish()[-1] == STATE and ledger(rnd)["gen"] == 2


def test_a_folder_kept_side_by_side_stays_so(tmp_path):
    """A folder with state.json at its top (the old flat layout) gets no second ledger under data/."""
    rnd = Round(folder(tmp_path / "w")).setup(layout="flat")
    rnd.open(today=DAY)
    rnd.run_json("settings", "--work", rnd.path, "--config", '{"lab_units": "SI"}')
    rnd.publish()
    assert not os.path.exists(rnd.store("data", "state.json"))
    assert rnd.read_json("store", "state.json")["config"]["lab_units"] == "SI"
    rnd.forget_job()
    rnd.start()
    rnd.play_to_feedback(start=False).save()
    rnd.publish()
    assert os.path.isfile(rnd.store("sessions", "S0001.json")) and not os.path.exists(rnd.store("data"))
    assert rnd.read_json("store", "state.json")["sessions"][0]["id"] == "S0001"


def test_files_that_are_no_store_document_are_left_alone(tmp_path):
    rnd = Round(folder(tmp_path / "w")).setup()
    rnd.write(os.path.join("store", "notes.txt"), "my notes")
    rnd.write(os.path.join("store", "other.json"), {"hello": 1})
    out = rnd.open(today=DAY)
    assert "recognised" not in out and set(rnd.read_json("work.json")["found"]) == {STATE, PAGE_FILE, PREPARED,
                                                                                    "index.html"}


# ---- one seam, two adapters

def test_the_page_adapter_emits_the_publish_set_and_writes_nothing(tmp_path):
    rnd = Round(folder(tmp_path / "w")).setup()
    rnd.run_json("--today", DAY, "open", "--work", rnd.path, "--store", rnd.store(), "--version", "12")
    before = ledger(rnd)
    rnd.run_json("settings", "--work", rnd.path, "--config", '{"session_minutes": 40}')
    out = rnd.run_json("publish", "--work", rnd.path)
    assert out["store"] == "page" and out["version"] == "12" and names(out) == [PAGE_FILE, PREPARED, STATE]
    assert out["files"] == rnd.manifest()["files"] and ledger(rnd) == before


def test_the_folder_adapter_writes_in_order_the_ledger_last(rnd, monkeypatch, capsys):
    rnd.play_to_feedback().save()
    written = []
    real = os.replace

    def noting(src, dst):
        if str(src).endswith(".cme-tmp"):
            written.append(os.path.relpath(dst, rnd.store()).replace(os.sep, "/"))
        return real(src, dst)

    monkeypatch.setattr(cme.os, "replace", noting)
    assert cme.main(["publish", "--work", rnd.path]) == 0
    out = json.loads(capsys.readouterr().out)
    assert written == out["written"] == [SESSION, PAGE_FILE, PREPARED, STATE]
    assert out["store"] == "folder" and out["gen"] == 2 and ledger(rnd)["sessions"][0]["id"] == "S0001"
    assert not [n for n in os.listdir(rnd.store("data")) if n.endswith(".cme-tmp")]
    # publishing again is harmless: the folder's ledger is now the one this job wrote
    assert rnd.run_json("publish", "--work", rnd.path)["written"] == out["written"]


def test_the_folder_adapter_sets_up_a_new_learner_and_never_over_another_ledger(tmp_path):
    w = Round(folder(tmp_path / "w"))
    w.run_json("--today", DAY, "init", "--work", w.path, "--blueprint", cme.__file__.replace(
        os.path.join("scripts", "cme.py"), os.path.join("templates", "blueprint.json")))
    out = w.run_json("publish", "--work", w.path, "--to", str(tmp_path / "folder"))
    assert out["written"][-1] == STATE and os.path.isfile(str(tmp_path / "folder" / "data" / "state.json"))
    other = Round(folder(tmp_path / "other"))
    other.run_json("--today", DAY, "init", "--work", other.path, "--blueprint", cme.__file__.replace(
        os.path.join("scripts", "cme.py"), os.path.join("templates", "blueprint.json")))
    r = other.run("publish", "--work", other.path, "--to", str(tmp_path / "folder"), ok=False)
    assert "already holds a ledger" in json.loads(r.stdout)["error"]


def test_every_writing_command_is_noted_as_a_step_of_the_job(rnd):
    rnd.open(today=DAY)
    rnd.run_json("settings", "--work", rnd.path, "--config", '{"session_minutes": 30}')
    rnd.run_json("--today", DAY, "start", "--work", rnd.path)
    rnd.play_to_feedback(start=False).save()
    rnd.save()                                          # run again as it stands: applied again in place
    rnd.write("B.md", PART_B)
    rnd.close()
    steps = rnd.read_json("work.json")["steps"]
    assert [s["cmd"] for s in steps] == ["settings", "save", "close"]
    assert steps[0]["argv"][-4:] == ["--work", rnd.path, "--config", '{"session_minutes": 30}']


# ---- another device saved first: the folder adapter applies the job again

def test_a_clean_rebase_says_nothing(two):
    a, b = two
    a.start()
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"session_minutes": 45}')
    b.push()
    a.play_to_feedback(start=False).save()
    out = a.push()
    assert out["rebased"]["steps"] == [{"cmd": "save", "applied": True}] and out["rebased"]["say"] is None
    st = ledger(a)
    assert st["config"]["session_minutes"] == 45 and [s["id"] for s in st["sessions"]] == ["S0001"]
    assert out["written"] == [SESSION, PAGE_FILE, PREPARED, STATE] and out["gen"] == st["gen"] == 3


def test_the_round_mix_changed_on_another_device_one_line_and_the_round_kept_as_played(two):
    a, b = two
    a.start()                                                       # three MCQs and the case
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"mcqs": 0, "focused": 1}')
    b.push()
    a.play_to_feedback(start=False).save()
    out = a.push()
    assert out["rebased"]["say"] == MIX_LINE
    st = ledger(a)
    assert (st["config"]["mcqs"], st["config"]["focused"]) == (0, 1)         # the learner's latest choice stays
    assert len(st["sessions"][0]["items"]) == len(ROUND["items"])            # the round as it was played
    assert a.reflect()["ok"] and a.push().get("rebased") is None             # the close publishes cleanly


def test_a_setting_changed_on_both_devices_this_change_replaces_it(two):
    a, b = two
    a.open(today=DAY)
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"session_minutes": 45}')
    b.push()
    a.run_json("settings", "--work", a.path, "--config", '{"session_minutes": 25, "lab_units": "SI"}')
    out = a.push()
    assert out["rebased"]["say"] == ("Your other device changed the session length meanwhile; the change made "
                                     "here replaces it.")
    assert ledger(a)["config"]["session_minutes"] == 25 and ledger(a)["config"]["lab_units"] == "SI"


def test_two_rounds_from_the_same_ledger_are_both_kept_in_save_order(two):
    a, b = two
    a.start(DAY, "--at", "2026-11-01T08:00:00Z")           # the laptop's round, then the phone's
    b.start(DAY, "--at", "2026-11-01T08:05:00Z")
    a.play_to_feedback(start=False).save()
    a.push()
    a.reflect()
    a.push()
    b.play_to_feedback(start=False)
    b.write("feedback.md", "The phone's final feedback, as sent")
    b.save()
    out = b.push()
    assert out["rebased"]["renumbered"] == {"from": "S0001", "to": "S0002"}
    assert out["rebased"]["say"] == ("Another device saved a round (S0001) while this one was open; both are kept, "
                                     "this one after it as S0002.")
    assert out["written"] == ["data/sessions/S0002.json", PAGE_FILE, PREPARED, STATE]
    st = ledger(b)
    assert [s["id"] for s in st["sessions"]] == ["S0001", "S0002"] and st["next_id"] == "S0003"
    assert st["sessions"][0]["reflection"]["solid"] == REFLECTION["solid"] and st["unreflected"] == "S0002"
    assert b.read_json("round.json")["log_id"] == "S0002" and b.read_json("work.json")["session_id"] == "S0002"
    assert "The phone's final feedback" in b.read_json(b.store("data", "sessions", "S0002.json"))["transcript"]
    assert "The phone's final feedback" not in b.read_json(b.store("data", "sessions", "S0001.json"))["transcript"]
    b.reflect()
    assert "rebased" not in b.push()
    st = ledger(b)
    assert st["unreflected"] is None and all(not s["reflection"].get("skipped") for s in st["sessions"])
    page = b.read_json(b.store("data", "page.json"))
    assert sorted((s["id"], s["reflected"]) for s in page["sessions"]) == [("S0001", True), ("S0002", True)]


def test_a_round_closed_after_another_devices_round_keeps_its_reflection(two):
    """The laptop saves its round; the phone saves one from the same ledger (renumbered, and the
    laptop's round is then finalised without its reflection); the laptop's reflection arrives:
    it is applied to the laptop's round all the same, and the phone's round still waits for its own."""
    a, b = two
    a.start(DAY, "--at", "2026-11-01T08:00:00Z")           # the laptop's round, then the phone's
    b.start(DAY, "--at", "2026-11-01T08:05:00Z")
    a.play_to_feedback(start=False).save()
    a.push()
    b.play_to_feedback(start=False).save()
    assert b.push()["rebased"]["renumbered"]["to"] == "S0002"
    assert ledger(a)["sessions"][0]["reflection"] == {"skipped": True}
    a.reflect()
    out = a.push()
    assert [s["cmd"] for s in out["rebased"]["steps"]] == ["save", "close"]
    assert out["rebased"]["steps"][0]["applied"] == "already in the store" and out["rebased"]["say"] is None
    st = ledger(a)
    assert st["sessions"][0]["reflection"]["solid"] == REFLECTION["solid"] and st["unreflected"] == "S0002"
    b.reflect()
    b.push()
    st = ledger(b)
    assert st["unreflected"] is None and [s["reflection"]["solid"] for s in st["sessions"]] == ["a", "a"]


def test_a_save_already_published_is_not_recorded_twice(two):
    a, b = two
    a.start()
    a.play_to_feedback(start=False).save()
    a.push()
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"lab_units": "SI"}')
    b.push()
    a.reflect()
    out = a.push()
    assert out["rebased"]["steps"] == [{"cmd": "save", "applied": "already in the store"},
                                       {"cmd": "close", "applied": True}]
    st = ledger(a)
    assert [s["id"] for s in st["sessions"]] == ["S0001"] and st["config"]["lab_units"] == "SI"
    assert st["unreflected"] is None and st["sessions"][0]["reflection"]["solid"] == REFLECTION["solid"]


def test_a_folder_that_moves_again_during_the_rebase_is_not_written(two, monkeypatch, capsys):
    a, b = two
    a.open(today=DAY)
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"lab_units": "SI"}')
    b.push()
    a.run_json("settings", "--work", a.path, "--config", '{"session_minutes": 25}')
    before = ledger(a)
    monkeypatch.setattr(cme, "write_folder", lambda work, info, folder: None)
    assert cme.main(["publish", "--work", a.path]) == 2
    assert "changed again" in json.loads(capsys.readouterr().out)["error"] and ledger(a) == before


# ---- the page: the assistant reads again, the engine applies the job again

def test_page_reread_renumbers_a_round_another_device_saved(tmp_path):
    a = Round(folder(tmp_path / "laptop")).setup()
    b = Round(folder(tmp_path / "phone"))
    shutil.copytree(a.store(), b.store())                   # both read the page at version 3
    for dev, at in ((a, "2026-11-01T08:00:00Z"), (b, "2026-11-01T08:05:00Z")):
        dev.run_json("--today", DAY, "start", "--work", dev.path, "--store", dev.store(), "--version", "3", "--at", at)
        dev.play_to_feedback(start=False).save()
    for f in a.manifest()["files"]:                         # the laptop's publish lands: version 4
        dst = b.store(*f["as"].split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(f["path"], dst)
    # the phone's publish is refused: it reads the page again (only the four files) and reopens
    fresh = str(tmp_path / "fresh")
    os.makedirs(fresh)
    for i, rel in enumerate((STATE, PAGE_FILE, PREPARED, "index.html")):
        shutil.copy(b.store(*rel.split("/")), os.path.join(fresh, "f%d" % i))
    out = b.run_json("open", "--work", b.path, "--store", fresh, "--version", "4", "--reread")
    assert out["rebased"]["renumbered"] == {"from": "S0001", "to": "S0002"} and out["rebased"]["say"]
    assert names(out) == ["data/sessions/S0002.json", PAGE_FILE, PREPARED, STATE] and b.manifest()["version"] == "4"
    st = b.read_json("publish", "data", "state.json")
    assert [s["id"] for s in st["sessions"]] == ["S0001", "S0002"]
    page = b.read_json("publish", "data", "page.json")
    assert [s["id"] for s in page["sessions"]] == ["S0002", "S0001"]


# ---- review of #57: steps already published are not applied again; the page's rebase needs no
# more than the four files it reads

class PageDevice(Round):
    """One device on the learner's page, simulated: `page/` holds the artifact's files and its
    version; a publish is refused unless pinned to the version the page is at. Nothing tells the
    engine that a publish landed."""

    def __init__(self, path, page):
        os.makedirs(str(path), exist_ok=True)
        super().__init__(path)
        self.page = str(page)
        self.pinned = None

    def version(self):
        with open(os.path.join(self.page, ".version")) as fh:
            return fh.read().strip()

    def read(self):
        """The read call: the four top-level files, saved under names of the tool's own."""
        n = len([d for d in os.listdir(self.path) if d.startswith("read")])
        dst = self.p("read%d" % n)
        os.makedirs(dst)
        for i, rel in enumerate((STATE, PAGE_FILE, PREPARED, "index.html")):
            src = os.path.join(self.page, *rel.split("/"))
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(dst, "saved-%d" % i))
        self.pinned = self.version()
        return dst, self.pinned

    def begin(self, *cmd, at=None):
        store, v = self.read()
        extra = ("--at", at) if at else ()
        return self.run_json("--today", DAY, *cmd, "--work", self.path, "--store", store, "--version", v, *extra)

    def push(self):
        """The publish call pinned to the version read, then to the one the last publish returned;
        True when it landed."""
        if self.pinned != self.version():
            return False
        for f in self.manifest()["files"]:
            dst = os.path.join(self.page, *f["as"].split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(f["path"], dst)
        self.pinned = str(int(self.version()) + 1)
        with open(os.path.join(self.page, ".version"), "w") as fh:
            fh.write(self.pinned)
        return True

    def reflect(self):
        self.write("B.md", PART_B)
        return self.close()

    def reread(self):
        store, v = self.read()
        return self.run_json("open", "--work", self.path, "--store", store, "--version", v, "--reread")

    def ledger(self):
        return self.read_json(os.path.join(self.page, "data", "state.json"))

    def session(self, sid="S0001"):
        return self.read_json(os.path.join(self.page, "data", "sessions", sid + ".json"))


@pytest.fixture
def pages(tmp_path):
    page = tmp_path / "page"
    seed = Round(folder(tmp_path / "seed")).setup()
    shutil.copytree(seed.store(), str(page))
    with open(str(page / ".version"), "w") as fh:
        fh.write("1")
    return PageDevice(tmp_path / "laptop", page), PageDevice(tmp_path / "phone", page)


def test_folder_a_published_settings_step_is_not_applied_again(two):
    a, b = two
    a.open(today=DAY)
    a.run_json("settings", "--work", a.path, "--config", '{"session_minutes": 25}')
    a.push()
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"session_minutes": 60}')
    b.push()
    a.run_json("settings", "--work", a.path, "--config", '{"lab_units": "SI"}')
    out = a.push()
    assert [s["applied"] for s in out["rebased"]["steps"]] == ["already in the store", True]
    assert out["rebased"]["say"] is None
    assert ledger(a)["config"]["session_minutes"] == 60 and ledger(a)["config"]["lab_units"] == "SI"


def test_page_a_published_settings_step_is_not_applied_again(pages):
    a, b = pages
    a.begin("open")
    a.run_json("settings", "--work", a.path, "--config", '{"session_minutes": 25}')
    assert a.push()
    b.begin("open")
    b.run_json("settings", "--work", b.path, "--config", '{"session_minutes": 60}')
    assert b.push()
    a.run_json("settings", "--work", a.path, "--config", '{"lab_units": "SI"}')
    assert not a.push()                                         # refused: the phone saved first
    out = a.reread()
    assert [s["applied"] for s in out["rebased"]["steps"]] == ["already in the store", True]
    assert out["rebased"]["say"] is None and a.push()
    assert a.ledger()["config"]["session_minutes"] == 60 and a.ledger()["config"]["lab_units"] == "SI"


def test_folder_a_published_addendum_is_not_added_twice_and_each_keeps_its_own_text(two):
    a, b = two
    a.start(DAY, "--at", "2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    a.reflect()
    a.push()
    md = a.write("add.md", "FIRST")
    a.run_json("addendum", "--work", a.path, "--md", md)
    a.push()
    b.start(DAY, "--at", "2026-11-01T09:00:00Z")
    b.play_to_feedback(dict(ROUND, log_id="S0002"), start=False).save()
    b.push()
    a.write("add.md", "SECOND")                                  # the same file, a second addendum
    a.run_json("addendum", "--work", a.path, "--md", md)
    out = a.push()
    assert [s["applied"] for s in out["rebased"]["steps"]] == ["already in the store"] * 3 + [True]
    assert a.read_json(a.store("data", "sessions", "S0001.json"))["addendum"] == "FIRST\n\nSECOND\n"
    assert [s["id"] for s in ledger(a)["sessions"]] == ["S0001", "S0002"]


def test_folder_a_published_override_is_not_applied_again(two):
    a, b = two
    a.start(DAY, "--at", "2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    a.reflect()
    a.push()
    a.run_json("--today", DAY, "override", "--work", a.path, "--scores", json.dumps({"topic": "NEURO-04", "score": 4}))
    a.push()
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"lab_units": "SI"}')
    b.push()
    a.run_json("settings", "--work", a.path, "--config", '{"session_minutes": 30}')
    out = a.push()
    assert [s["cmd"] for s in out["rebased"]["steps"] if s["applied"] is True] == ["settings"]
    st = ledger(a)
    assert st["config"]["lab_units"] == "SI" and st["config"]["session_minutes"] == 30
    assert next(i for i in st["sessions"][0]["items"] if i["topic"] == "NEURO-04")["mastery"] == 4


def test_page_reflection_refused_after_the_save_was_published(pages):
    """The common case: the save published, another device saves a round, the reflection's publish
    is refused. The rebase reads only the four top-level files again; the session document the
    close needs is the one this job published."""
    a, b = pages
    a.begin("start", at="2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    assert a.push()
    b.begin("start", at="2026-11-01T09:00:00Z")
    b.play_to_feedback(dict(ROUND, log_id="S0002"), start=False).save()
    assert b.push()                                             # the phone's round: S0002
    a.reflect()
    assert not a.push()
    out = a.reread()
    assert [s["applied"] for s in out["rebased"]["steps"]] == ["already in the store", True]
    assert names(out) == [SESSION, PAGE_FILE, STATE] and a.push()
    st = a.ledger()
    assert [s["id"] for s in st["sessions"]] == ["S0001", "S0002"] and st["unreflected"] == "S0002"
    assert st["sessions"][0]["reflection"]["solid"] == REFLECTION["solid"]
    doc = a.read_json(os.path.join(a.page, "data", "sessions", "S0001.json"))
    assert doc["reflected"] is True and "Final feedback" in doc["transcript"]


def test_page_a_published_save_is_known_even_after_another_device_changed_its_items(pages):
    """The save's publish landed; another device then changed the round's items (a blueprint
    mapping): the round is still known as this job's (by its step token), not recorded twice."""
    a, b = pages
    a.begin("start", at="2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    assert a.push()
    st = a.ledger()
    for it in st["sessions"][0]["items"]:
        it["topic"] = it["topic"] + "-moved"
    st["gen"] += 1
    a.write(os.path.join(a.page, "data", "state.json"), st)
    with open(os.path.join(a.page, ".version"), "w") as fh:
        fh.write("9")
    a.reflect()
    assert not a.push()
    out = a.reread()
    assert [s["applied"] for s in out["rebased"]["steps"]] == ["already in the store", True]
    assert "renumbered" not in out["rebased"] and a.push()
    assert [s["id"] for s in a.ledger()["sessions"]] == ["S0001"] and a.ledger()["unreflected"] is None


def test_page_save_published_then_close_and_addendum_refused_add_the_addendum_once(pages):
    a, b = pages
    a.begin("start", at="2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    assert a.push()
    b.begin("start", at="2026-11-01T09:00:00Z")
    b.play_to_feedback(dict(ROUND, log_id="S0002"), start=False).save()
    assert b.push()
    a.reflect()
    a.run_json("addendum", "--work", a.path, "--md", a.write("add.md", "FIRST"), "--session", "S0001")
    assert not a.push()
    out = a.reread()
    assert [(s["cmd"], s["applied"]) for s in out["rebased"]["steps"]] == [
        ("save", "already in the store"), ("close", True), ("addendum", True)]
    assert a.push()
    doc = a.session()
    assert doc["addendum"] == "FIRST\n" and doc["reflected"] is True and "Final feedback" in doc["transcript"]
    assert [s["id"] for s in a.ledger()["sessions"]] == ["S0001", "S0002"]


def test_page_a_round_without_a_start_time_is_not_recorded_twice(pages):
    """No answer was filed as the round went (no start time in the record): the save's step token
    alone tells that the store holds it."""
    a, b = pages
    a.begin("open")
    for name, text in (("round.json", ROUND), ("sealed_case.md", SEALED_CASE), ("sealed_questions.md", SEALED_QUESTIONS),
                       ("answers.md", ANSWERS), ("feedback.md", "Feedback text")):
        a.write(name, text)
    a.save()
    assert a.ledger is not None and a.push()
    assert a.ledger()["sessions"][0].get("started_at") is None
    b.begin("open")
    b.run_json("settings", "--work", b.path, "--config", '{"lab_units": "SI"}')
    assert b.push()
    a.reflect()
    assert not a.push()
    out = a.reread()
    assert "renumbered" not in out["rebased"] and a.push()
    st = a.ledger()
    assert [s["id"] for s in st["sessions"]] == ["S0001"] and st["unreflected"] is None
    assert st["config"]["lab_units"] == "SI"


def partial_write(dev, *rels):
    """A folder publish that stopped half-way: these files of the publish set written, not the ledger."""
    for rel in rels:
        shutil.copy(dev.pub(*rel.split("/")), dev.store(*rel.split("/")))


def test_folder_an_addendum_written_half_way_is_added_once_after_the_rebase(two):
    a, b = two
    a.start(DAY, "--at", "2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    a.reflect()
    a.push()
    a.run_json("addendum", "--work", a.path, "--md", a.write("add.md", "FIRST"))
    partial_write(a, SESSION)                                   # the session file landed, the ledger did not
    b.open(today=DAY)
    b.run_json("settings", "--work", b.path, "--config", '{"lab_units": "SI"}')
    b.push()
    out = a.push()
    assert [s["applied"] for s in out["rebased"]["steps"]] == ["already in the store"] * 2 + [True]
    doc = a.read_json(a.store("data", "sessions", "S0001.json"))
    assert doc["addendum"] == "FIRST\n" and doc["reflected"] is True
    assert ledger(a)["config"]["lab_units"] == "SI"


def test_folder_a_job_whose_only_write_stopped_half_way_adds_its_addendum_once(two):
    a, b = two
    a.start(DAY, "--at", "2026-11-01T08:00:00Z")
    a.play_to_feedback(start=False).save()
    a.reflect()
    a.push()
    a.forget_job()
    a.open(today="2026-11-02")                                  # a later job: an addendum only
    a.run_json("addendum", "--work", a.path, "--md", a.write("add.md", "LATER"))
    partial_write(a, SESSION)
    b.open(today="2026-11-02")
    b.run_json("settings", "--work", b.path, "--config", '{"lab_units": "SI"}')
    b.push()
    out = a.push()
    assert [s["applied"] for s in out["rebased"]["steps"]] == [True]
    assert a.read_json(a.store("data", "sessions", "S0001.json"))["addendum"] == "LATER\n"

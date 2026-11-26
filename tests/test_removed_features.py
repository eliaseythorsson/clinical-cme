"""Version 5 drops the database store, the Drive mirror and the version-3 migration (ADR 0002).
Ledgers written by 4.3.x, which may still carry their fields, load and play as before."""
import os

import pytest

from conftest import SKILL


REMOVED_COMMANDS = ["migrate-v3", "unescape",
                    # issue #52: the single steps of start, save, close and finish-prepare, and `place`
                    "record", "reflect", "doc", "plan", "status", "stash", "place"]
OLD_FOLDERS = ("out0", "out1", "out2", "out3", "outS", "outT", "check")


@pytest.mark.parametrize("command", REMOVED_COMMANDS)
def test_removed_commands_are_gone(work, command):
    r = work.run(command, "x", "--out", "y", ok=False)
    assert r.returncode != 0 and "invalid choice" in r.stderr


def test_core_functions_of_the_removed_commands_remain():
    from examples import cme
    for name in ("plan_round", "record_round", "reflect_round", "status_dict", "plan_summary", "session_doc_a"):
        assert callable(getattr(cme, name)), name
    for name in ("cmd_record", "cmd_reflect", "cmd_doc", "cmd_plan", "cmd_status", "cmd_stash", "cmd_place"):
        assert not hasattr(cme, name), name


def test_legacy_scripts_are_not_shipped():
    assert not os.path.exists(os.path.join(SKILL, "legacy"))


def test_old_output_folders_are_gone_from_the_engine_and_from_a_round(work):
    with open(os.path.join(SKILL, "scripts", "cme.py"), encoding="utf-8") as fh:
        source = fh.read()
    for name in OLD_FOLDERS[:-1]:
        assert '"%s"' % name not in source and "/%s" % name not in source, name
    for flag in ("--out-dir", "--work-dir", "--prepared", "--written"):
        used_by = [line for line in source.splitlines() if 'add_argument("%s"' % flag in line]
        assert all('command("import"' in line for line in used_by), flag      # only the import tool keeps one
    work.init()
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    work.run("--today", "2026-11-01", "prepare", "--work", work.path)
    assert not any(os.path.exists(work.p(name)) for name in OLD_FOLDERS)
    assert sorted(n for n in os.listdir(work.path) if os.path.isdir(work.p(n))) == ["next", "publish", "store"]


def test_written_files_carry_only_store_paths(work):
    work.init()
    saved = work.save_round("2026-11-01")
    closed = work.close_round("2026-11-01")
    for f in saved["files"] + closed["files"]:
        assert set(f) == {"as", "path"}
    assert "db_update" not in closed
    assert not os.path.exists(work.pub("B.json"))


def test_new_ledger_has_no_mirror_setting(work):
    work.init()
    assert "mirror" not in work.read_ledger()["config"]
    out = work.start("2026-11-02")
    assert "mirror" not in out


def test_ledger_from_4_3_with_old_fields_still_plays(work):
    work.init()
    st = work.read_ledger()
    st["config"]["mirror"] = None                      # 4.3.x wrote this setting into every ledger
    st["migrated_from"] = {"schema": 3, "date": "2026-01-01", "sessions": 0, "gdocs": {}}
    work.write_ledger(st)
    work.start("2026-11-01")
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    after = work.read_json("publish", "data", "state.json")
    assert after["sessions"][-1]["id"] == "S0001"
    assert after["config"]["mirror"] is None and after["migrated_from"]["schema"] == 3
    assert work.run("validate", "--work", work.path).returncode == 0
    assert work.run("validate", work.pub("data", "state.json")).returncode == 0


def test_import_takes_a_page_export_only(work):
    work.init()
    work.save_round("2026-11-01")
    export = {"state": work.read_json("publish", "data", "state.json"),
              "sessions": [work.read_json("publish", "data", "sessions", "S0001.json")], "reviews": []}
    out = work.run_json("import", work.write("export.json", export), "--out-dir", work.p("restored"))
    assert [f["as"] for f in out["files"]] == ["data/sessions/S0001.json", "data/page.json", "data/state.json"]
    os.makedirs(work.p("dbdump", "cme"))
    assert work.run("import", work.p("dbdump"), "--out-dir", work.p("x"), ok=False).returncode != 0

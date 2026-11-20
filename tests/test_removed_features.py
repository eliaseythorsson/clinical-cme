"""Version 5 drops the database store, the Drive mirror and the version-3 migration (ADR 0002).
Ledgers written by 4.3.x, which may still carry their fields, load and play as before."""
import os

import pytest

from conftest import SKILL


@pytest.mark.parametrize("command", ["migrate-v3", "unescape"])
def test_removed_commands_are_gone(work, command):
    r = work.run(command, "x", "--out", "y", ok=False)
    assert r.returncode != 0 and "invalid choice" in r.stderr


def test_legacy_scripts_are_not_shipped():
    assert not os.path.exists(os.path.join(SKILL, "legacy"))


def test_written_files_carry_only_store_paths(work):
    work.init()
    saved = work.save_round("2026-11-01")
    closed = work.close_round("2026-11-01")
    for f in saved["files"] + closed["files"]:
        assert set(f) <= {"as", "path", "page_upgrade"}
    assert "db_update" not in closed
    assert not os.path.exists(work.p("out2", "B.json"))


def test_new_ledger_has_no_mirror_setting(work):
    work.init()
    assert "mirror" not in work.read_json("state.json")["config"]
    out = work.run_json("--today", "2026-11-02", "start", work.p("state.json"), "--out", work.p("plan.json"))
    assert "mirror" not in out


def test_ledger_from_4_3_with_old_fields_still_plays(work):
    work.init()
    st = work.read_json("state.json")
    st["config"]["mirror"] = None                      # 4.3.x wrote this setting into every ledger
    st["migrated_from"] = {"schema": 3, "date": "2026-01-01", "sessions": 0, "gdocs": {}}
    work.write("state.json", st)
    work.run_json("--today", "2026-11-01", "start", work.p("state.json"), "--out", work.p("plan.json"))
    work.save_round("2026-11-01")
    work.close_round("2026-11-01")
    after = work.read_json("out2", "data", "state.json")
    assert after["sessions"][-1]["id"] == "S0001"
    assert after["config"]["mirror"] is None and after["migrated_from"]["schema"] == 3
    assert work.run("validate", work.p("out2", "data", "state.json")).returncode == 0


def test_import_takes_a_page_export_only(work):
    work.init()
    work.save_round("2026-11-01")
    export = {"state": work.read_json("out1", "data", "state.json"),
              "sessions": [work.read_json("out1", "data", "sessions", "S0001.json")], "reviews": []}
    out = work.run_json("import", work.write("export.json", export), "--out-dir", work.p("restored"))
    assert {f["as"] for f in out["files"]} == {"data/state.json", "data/index.json", "data/sessions/S0001.json"}
    os.makedirs(work.p("dbdump", "cme"))
    assert work.run("import", work.p("dbdump"), "--out-dir", work.p("x"), ok=False).returncode != 0

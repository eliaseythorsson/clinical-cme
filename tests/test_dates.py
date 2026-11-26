"""A round keeps the date it was played on, whenever the reflection arrives."""
import copy

from conftest import Work


def closed_state(tmp_path, played, reflected):
    tmp_path.mkdir(parents=True, exist_ok=True)
    w = Work(tmp_path)
    w.init(today=played)
    w.save_round(played)
    w.close_round(reflected)
    return w


def test_late_reflection_keeps_round_date(tmp_path):
    w = closed_state(tmp_path, "2026-11-01", "2026-11-03")
    st = w.read_json("publish", "data", "state.json")
    sess = st["sessions"][-1]
    assert sess["date"] == "2026-11-01"
    assert st["topics"]["GEN-11"]["last"] == "2026-11-01"
    doc = w.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["date"] == "2026-11-01"


def test_late_reflection_schedules_like_same_day(tmp_path):
    same = closed_state(tmp_path / "a", "2026-11-01", "2026-11-01").read_json("publish", "data", "state.json")
    late = closed_state(tmp_path / "b", "2026-11-01", "2026-11-03").read_json("publish", "data", "state.json")
    due = lambda st: {t: v.get("due") for t, v in st["topics"].items() if v.get("attempts")}
    assert due(same) == due(late)
    assert {g["topic"]: g.get("date") for g in same["gaps"]} == {g["topic"]: g.get("date") for g in late["gaps"]}


def test_session_document_honours_today(work):
    work.init(today="2026-11-01")
    work.save_round("2026-11-01")
    doc = work.read_json("publish", "data", "sessions", "S0001.json")
    assert doc["date"] == "2026-11-01"

"""Blueprints for other specialties (issue #56): a blueprint drafted at setup is exported as files the
learner can send back to the repo, with nothing of the learner in them, and every blueprint kept in
the skill's blueprints/ folder builds a ledger."""
import glob
import json
import os

import pytest

from conftest import SKILL, Work
from examples import cme

SHARED = sorted(glob.glob(os.path.join(SKILL, "blueprints", "*.json")))


def test_blueprint_export_writes_the_blueprint_and_a_note_without_the_learner(work, tmp_path):
    work.init(profile={"specialty": "Paediatrics", "subspecialty": "Neonatology",
                       "journey": "A private paragraph about me", "display_name": "Dr Example"})
    work.open()
    out = work.run_json("--today", "2026-11-02", "blueprint-export", "--work", work.path, "--out", str(tmp_path / "x"))
    assert out["ok"] is True and out["specialty"] == "Paediatrics / Neonatology"
    jpath, mpath = out["files"]
    assert os.path.basename(jpath) == "paediatrics-neonatology.json" and mpath.endswith(".md")
    with open(jpath, encoding="utf-8") as fh:
        exported = json.load(fh)
    assert exported == work.read_ledger()["blueprint"]
    with open(mpath, encoding="utf-8") as fh:
        note = fh.read()
    both = note + json.dumps(exported)
    assert "private paragraph" not in both and "Dr Example" not in both
    assert "2026-11-02" in note and '"International"' in note and "blueprints/" in note
    assert out["send_to"].startswith("https://github.com/eliaseythorsson/clinical-cme/")
    # the exported file builds a ledger as it is
    (tmp_path / "again").mkdir()
    w2 = Work(tmp_path / "again")
    w2.run("--today", "2026-11-03", "init", "--work", w2.path, "--blueprint", jpath)
    assert w2.read_json("publish", "data", "state.json")["blueprint"] == exported


def test_blueprint_slug():
    assert cme.blueprint_slug("Paediatrics / neonatology") == "paediatrics-neonatology"
    assert cme.blueprint_slug("  ") == "specialty"


def test_the_blueprints_folder_says_how_one_is_contributed():
    with open(os.path.join(SKILL, "blueprints", "README.md"), encoding="utf-8") as fh:
        text = fh.read()
    assert "blueprint-export" in text and "issues/new" in text


@pytest.mark.parametrize("path", SHARED or [None])
def test_every_shared_blueprint_builds_a_ledger(path, tmp_path):
    if path is None:
        pytest.skip("no shared blueprint yet")
    w = Work(tmp_path)
    w.run("--today", "2026-11-03", "init", "--work", w.path, "--blueprint", path)
    st = w.read_json("publish", "data", "state.json")
    assert st["blueprint"] and cme.shape_problems(st) == []
    assert os.path.isfile(path[:-5] + ".md"), "a note beside each shared blueprint"

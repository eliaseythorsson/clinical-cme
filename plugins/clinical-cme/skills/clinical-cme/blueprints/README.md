# Blueprints for other specialties

The default blueprint (`templates/blueprint.json`, internal/hospital medicine) is the one a
learner gets unless they name another specialty. For another specialty, setup looks here first
(`references/onboarding.md` §3): a file `<specialty>.json` whose specialty matches is used as it
is, after the learner has seen its area list. Only when none fits is a blueprint drafted in the
conversation, and the learner is then offered the chance to send it back here, so the next
learner in that specialty gets a checked one.

## How a drafted blueprint comes back here

A learner's session cannot write to this repository, so the engine exports the blueprint as
files and the learner sends them:

1. After setup (or a later change of specialty) with a drafted blueprint, the assistant asks
   once: "Would you like to share this blueprint, so the next learner in your specialty starts
   from a checked one? Nothing about you goes with it." No is the default.
2. Yes: `cme.py blueprint-export --work W --out DIR` writes `DIR/<specialty>.json` (the
   blueprint exactly as the ledger holds it) and `DIR/<specialty>.md` (specialty, guideline
   region, date, areas with weights and topic counts). Neither holds the learner's paragraphs,
   history, scores or name. The assistant gives the learner both files.
3. The learner opens an issue at
   <https://github.com/eliaseythorsson/clinical-cme/issues/new> titled "Blueprint:
   <specialty>" with both files attached, or a pull request adding them to
   `plugins/clinical-cme/skills/clinical-cme/blueprints/`.

## What is checked before one is added

- The shape the engine reads: `cme.py blueprint-md` / `read_blueprint` accept it, and
  `cme.py init --blueprint <file>` builds a ledger from it (`tests/test_blueprints.py` runs this
  on every file here).
- Areas, weights and topics against the specialty's published core-competency or board outline,
  by a reviewer of that specialty; topic IDs stable (`PEDS-01`), retired topics marked, never
  renumbered.
- Guideline tags on decision points (`[ESC HF 2021]`), if any, name a body and an edition; no
  tag names one country's law as if it applied to all (`[national mental capacity law]`).
- File name: the specialty in lower case with hyphens (`paediatrics.json`), a `.md` note beside it.

Contributed blueprints are content, under CC BY-NC 4.0 like the rest of the skill's content
(`LICENSE.md`).

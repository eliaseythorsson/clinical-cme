# clinical-cme

Source repo for the `clinical-cme` skill (currently version 4.2.1): blinded clinical
self-assessment rounds for physicians — MCQs, focused questions and a full case, with
evidence-based feedback, reflection-informed spaced repetition and periodic reasoning review.

## Layout

- `skills/clinical-cme/` — the shippable skill folder. Install by copying this folder into a
  skills directory (or zipping it for upload). Keep it free of personal/learner data.
  - `SKILL.md` — the protocol the assistant follows in a round
  - `scripts/cme.py` — the state engine (Python 3.8+, standard library only)
  - `references/` — store, schema, case design, feedback, analysis, logging, review, onboarding
  - `templates/` — learner page (`page.html`), default blueprint, resource library
  - `legacy/` — version-3 scripts, used only for migration
- `docs/agents/` — config read by the engineering skills (see below)
- `docs/adr/` — architecture decision records (created lazily)

## Working rules

- Version bumps touch `SKILL.md` (heading), `README.md` (skill), and `PAGE_VERSION` in
  `scripts/cme.py` when the page changes.
- `python3 -m py_compile skills/clinical-cme/scripts/cme.py` must pass before committing.
- Never commit learner data (`data/`, `state.json`, session logs).

## Agent skills

### Issue tracker

Issues and specs are tracked as GitHub issues in this repo, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.

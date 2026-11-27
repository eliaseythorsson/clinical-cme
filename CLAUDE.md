# clinical-cme

Source repo for the `clinical-cme` skill (currently version 6.0.0): blinded clinical
self-assessment rounds for physicians — MCQs, focused questions and a full case, with
evidence-based feedback, reflection-informed spaced repetition and periodic reasoning review.

## Layout

- `skills/clinical-cme/` — the shippable skill folder. Install by copying this folder into a
  skills directory (or zipping it for upload). Keep it free of personal/learner data.
  - `SKILL.md` — the protocol the assistant follows in a round; about 250 lines, only what
    needs judgement (presenting, grading, feedback): procedure belongs in `cme.py`, the rest
    in `references/`
  - `scripts/cme.py` — the state engine (Python 3.8+, standard library only)
  - `references/` — store, schema, the rulebook (`standards.md`), case design, feedback, analysis, logging, review, onboarding,
    preparing ahead, other requests
  - `templates/` — learner page (`page.html`), default blueprint, resource library, the default
    blueprint's guideline-tag checks made before #90 (`guideline_checks.json`)
- `tests/` — pytest suite for `cme.py` (`conftest.py` runs it the way the assistant does, its
  `main(argv)` in the test process, isolated as a process would be; `CME_TEST_SUBPROCESS=1` runs
  every call as a real process, as CI does on `main`)
  - `tests/ledgers/` — synthetic example ledgers with their expected plan, schedule and applied
    round; `tests/examples.py` says how to accept a deliberate change
- `sim/` — simulation harness (`simulate.py`, personas, saved reports); run with `/simulate`,
  procedure in `sim/README.md`. Run folders (`sim/runs/`) are never committed
- `docs/agents/` — config read by the engineering skills (see below)
- `docs/adr/` — architecture decision records (created lazily)

## Distribution

The repo root is both the plugin and a single-plugin marketplace (`.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `source: "./"`). `plugin.json` deliberately has **no
`version`**, so every commit on `main` is a new plugin version and reaches installs on update —
do not add one. Run `claude plugin validate .` after touching either manifest.

## Working rules

- Version bumps touch `SKILL.md` (heading), `README.md` (skill), and `PAGE_VERSION` in
  `scripts/cme.py` when the page changes.
- `python3 -m py_compile skills/clinical-cme/scripts/cme.py` and `python3 -m pytest -q tests` must
  pass before committing (GitHub Actions runs both on every pull request).
- Domain vocabulary: `CONTEXT.md`. Decisions: `docs/adr/`. Current plan: `docs/plan-v5.md`.
- A rule for writing items is written once, in `references/standards.md`; briefs cite its number.
  After changing `KEY_*` in `cme.py`, paste `cme.py key-table` into rule 9 (a test compares them).
- After changing a command or a work-folder file, paste `cme.py command-table` and `cme.py file-table`
  into `state_schema.md` §6 and §6.1 (a test compares them).
- Never commit learner data (`data/`, `state.json`, session logs).

## Agent skills

### Issue tracker

Issues and specs are tracked as GitHub issues in this repo, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.

# clinical-cme

Source repo for the `clinical-cme` skill (currently version 7.0.0): blinded clinical
self-assessment rounds for physicians — MCQs, focused questions and a full case, with
evidence-based feedback, reflection-informed spaced repetition and periodic reasoning review.

## Layout

- `plugins/clinical-cme/` — the plugin, the only part that ships (manifest in
  `.claude-plugin/plugin.json`, `README.md`, `LICENSE.md`). Keep it free of personal/learner data
  and of anything for developers (tests, sim, docs stay at the repo root).
- `plugins/clinical-cme/skills/clinical-cme/` — the skill folder. Without plugins: copy this
  folder into a skills directory (or zip it for upload); it carries its own `LICENSE.md`.
  - `SKILL.md` — the protocol the assistant follows in a round; about 250 lines, only what
    needs judgement (presenting, grading, feedback): procedure belongs in `cme.py`, the rest
    in `references/`
  - `scripts/cme.py` — the state engine (Python 3.8+, standard library only)
  - `references/` — store, schema, the rulebook (`standards.md`), case design, feedback, analysis, logging, review, onboarding,
    preparing ahead, other requests
  - `templates/` — learner page (`page.html`), default blueprint, resource library, the default
    blueprint's central guideline-tag check records per region (`guideline_checks.json`, #91;
    kept current by `cme.py central-checks`, procedure in `docs/maintaining-guidelines.md`)
  - `blueprints/` — checked blueprints for specialties other than the default, contributed from
    learners' setups; setup looks here before drafting one (`blueprints/README.md`)
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

The repo root is a single-plugin marketplace (`.claude-plugin/marketplace.json`, `source:
"./plugins/clinical-cme"`); the plugin's manifest is `plugins/clinical-cme/.claude-plugin/plugin.json`.
Plugin and skill keep the name `clinical-cme`, so installs from before the move (issue #56) update
in place. `plugin.json` deliberately has **no
`version`**, so every commit on `main` is a new plugin version and reaches installs on update —
do not add one. Run `claude plugin validate .` and `claude plugin validate plugins/clinical-cme` after touching
either manifest or the plugin folder's layout. No release action (tags, catalog submissions) from
an agent session: releasing is the owner's.

## Working rules

- The version is `SKILL_VERSION` in `cme.py`; a bump also touches the `SKILL.md` heading, the
  skill's `README.md` heading and the "Current version" lines of the root and plugin READMEs and
  this file (`tests/test_version.py` compares them all), and `PAGE_VERSION` when the page changes
  (its `<meta>` in `page.html` and a "Page update" note in the skill's README).
- Licences: content (SKILL.md, references, templates, blueprints, docs) CC BY-NC 4.0; code
  (`cme.py`, tests, `sim/*.py`) MIT. The licence files are `LICENSE.md` at the root, in the
  plugin and in the skill folder (the last two identical; a test checks).
- `python3 -m py_compile plugins/clinical-cme/skills/clinical-cme/scripts/cme.py` and `python3 -m pytest -q tests` must
  pass before committing (GitHub Actions runs both on every pull request). With `pytest-xdist`
  installed (test-only; the engine stays standard library), `-n auto` runs it on every core, as CI
  does; tests must stay independent under it: own `tmp_path`, nothing written into the repo tree.
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

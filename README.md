# clinical-cme

A Claude skill for blinded clinical self-assessment rounds for physicians: single-best-answer
MCQs, focused questions (a mini-case ending in one free-text decision) and a full clinical case,
in the mix the learner chooses. Rounds are graded against current evidence, followed by a short
reflection that feeds spaced repetition, logged verbatim, and periodically analysed for
reasoning patterns.

Current version: **7.1.0**. Full skill documentation: [`plugins/clinical-cme/skills/clinical-cme/README.md`](plugins/clinical-cme/skills/clinical-cme/README.md).

## Install

This repo is a Claude plugin marketplace with one plugin, `clinical-cme`, in `plugins/clinical-cme/`.

- **Claude app:** in the plugin directory, find **clinical-cme** and click **Install**. Or add
  the marketplace: Customize → Plugins → Add marketplace → `eliaseythorsson/clinical-cme`, then
  **Install** on clinical-cme. New commits on `main` arrive as plugin updates (click **Update**
  to pull at once).
- **Claude Code:**

  ```
  /plugin marketplace add eliaseythorsson/clinical-cme
  /plugin install clinical-cme@clinical-cme
  ```

- **Without plugins:** copy `plugins/clinical-cme/skills/clinical-cme/` into your skills folder,
  or zip and upload it.

The skill holds no personal data; each learner's first run creates their own private store.

## Usage: Full or Economy

Rounds use your Claude usage, and setup asks how much of it they should take. You can switch at
any time, by asking or under Settings on your page.

- **Full**: the most capable model writes the questions, every claim the feedback rests on is
  checked against its source, each round ends with podcast picks, and topics you keep answering
  well get the studies behind the recommendation. Best on a plan with high usage limits.
- **Economy**: noticeably lower usage, and lower quality. The questions are written by the same
  model that grades them (a different assistant still grades them, never the one that wrote
  them), only the facts the answer keys turn on are checked, there are no podcast picks and no
  deeper evidence, and rounds are smaller: 2 MCQs and a focused question, with the full case every
  other round. Anything you set yourself, such as your round mix, stays as you set it.

What we measured (simulated first rounds, 2026-11-27, Claude Opus 5.5; details in
`docs/usage-measurement.md`): with the same round mix, Economy made about a third fewer web
searches and page fetches (11–14 against 18). Reading the instructions costs about the same in
both modes (around 130 000 characters per round, about 35% less than in version 7.0). The larger
savings in Economy come from what the simulation cannot show: the questions are not written by
the most capable model, and every other round has no full case, which roughly halves that
round. Guideline checks for the default blueprint are done centrally and ship with updates, so
no learner pays for them in either mode.

## Where it runs

- **Claude app** (desktop, web, mobile): everything. The ledger lives in the learner's private
  "Clinical CME" page (the page store), helper agents write and source-check the rounds, and
  rounds are prepared ahead, overnight too if the learner asks.
- **Claude Code**: rounds, feedback, spacing and reviews, with the ledger in a folder (the folder
  store). No page, no overnight preparation.
- **Nothing else is supported**: other assistants, the API on its own, or an environment without
  Python 3.8+ for the engine.

## Repo layout

```
plugins/clinical-cme/  the plugin, the only part that ships: manifest, README, LICENSE.md and
                       skills/clinical-cme/ (SKILL.md, scripts/, references/, templates/, blueprints/)
.claude-plugin/        the marketplace manifest (source: ./plugins/clinical-cme)
tests/                 pytest suite for cme.py and the simulation harness
sim/                   simulation harness: examiner agent + learner persona in Claude Code (sim/README.md)
docs/agents/           issue tracker, triage labels and domain-doc config for agent workflows
docs/adr/              architecture decision records
CLAUDE.md              working notes for agents in this repo
```

Licences: content CC BY-NC 4.0, code MIT ([`LICENSE.md`](LICENSE.md)). Self-directed learning,
not accredited CME. Content can contain errors; feedback cites sources.

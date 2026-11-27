# clinical-cme

Blinded clinical self-assessment rounds for physicians: single-best-answer MCQs, focused
questions (a mini-case ending in one free-text decision) and a full clinical case, in the mix
you choose. Each round is graded against current guidelines, followed by a one-minute
reflection that feeds spaced repetition, logged in full, and periodically reviewed for
reasoning patterns.

Current version: **6.0.0**. Full documentation and what is new: [`skills/clinical-cme/README.md`](skills/clinical-cme/README.md).

## Install

- **Claude app:** in the plugin directory, find **clinical-cme** and click **Install**. Or add
  this marketplace yourself: Customize → Plugins → Add marketplace →
  `eliaseythorsson/clinical-cme`, then **Install** on clinical-cme.
- **Claude Code:**

  ```
  /plugin marketplace add eliaseythorsson/clinical-cme
  /plugin install clinical-cme@clinical-cme
  ```

Then say "quiz me" or "set up CME". The first run asks a few questions (where you are, where
you're aiming, whose guidelines: International unless you choose a country) and creates your own
private store; the plugin itself holds no personal data.

## Where it runs

| Where | What you get |
|---|---|
| **Claude app** (desktop, web, mobile) | Everything: your ledger in a private "Clinical CME" page you can open on any device (scores, sessions, reading, settings), helper agents that write and source-check rounds, rounds prepared ahead and, if you ask, overnight. |
| **Claude Code** | Rounds, feedback, spaced repetition and reviews, with the ledger in a folder you name. No page, no overnight preparation. |

Nothing else is supported: other assistants, the API on its own, or an environment without
Python 3.8+ to run the engine.

## Licence

Content (instructions, references, templates, blueprints) CC BY-NC 4.0; the engine
(`scripts/cme.py`) MIT. See [`LICENSE.md`](LICENSE.md).

Self-directed learning, not accredited CME. Content can contain errors; feedback cites sources.

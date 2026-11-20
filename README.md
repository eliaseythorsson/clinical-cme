# clinical-cme

A Claude skill for blinded clinical self-assessment rounds for physicians: single-best-answer
MCQs, focused questions (a mini-case ending in one free-text decision) and a full clinical case,
in the mix the learner chooses. Rounds are graded against current evidence, followed by a short
reflection that feeds spaced repetition, logged verbatim, and periodically analysed for
reasoning patterns.

Current version: **4.3.1**. Full skill documentation: [`skills/clinical-cme/README.md`](skills/clinical-cme/README.md).

## Install

This repo is a Claude plugin marketplace with one plugin, `clinical-cme`.

- **Claude app:** Customize → Plugins → Add marketplace → `eliaseythorsson/clinical-cme`, then install
  **clinical-cme**. New commits on `main` arrive as plugin updates (click **Update** to pull at once).
- **Claude Code:** `/plugin install clinical-cme --marketplace eliaseythorsson/clinical-cme`
- **Without plugins:** copy `skills/clinical-cme/` into your skills folder, or zip and upload it.

The skill holds no personal data; each learner's first run creates their own private store.

## Repo layout

```
skills/clinical-cme/   the skill (SKILL.md, scripts/, references/, templates/, legacy/)
docs/agents/           issue tracker, triage labels and domain-doc config for agent workflows
docs/adr/              architecture decision records
CLAUDE.md              working notes for agents in this repo
```

Self-directed learning, not accredited CME. Content can contain errors; feedback cites sources.

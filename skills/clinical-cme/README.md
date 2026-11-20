# clinical-cme (version 4.3)

Blinded clinical self-assessment rounds for physicians: single-best-answer questions and
focused questions on unrelated topics, with their feedback, then one clinical case and its
feedback — in the mix each learner chooses — graded against current evidence, with a one-minute
reflection that feeds spaced repetition. Every round is coded (reasoning steps, error types,
biases, calibration) and periodically analysed in a candid progress review.

## What is new in version 4.3

The aim of this version: the learner is always reading, answering or reading feedback, never
waiting for something to be generated.

- **New order.** Short questions → their feedback → the full case → its feedback, with the gap
  summary for the whole round and one reflection at the end. The round is blind part by part,
  and the log keeps both feedback messages in place (`cme.py save --feedback-questions`).
- **The whole round is prepared ahead.** After each close the next round is planned and
  written in full — short questions, the case's Stage 1 with a results bank (so Stage 2 goes
  out the moment Stage 1 is answered), and the notes for both feedbacks — and kept, packed, in
  the store (`data/prepared.json`; `cme.py prepare`, `stash`), together with the checked
  evidence for it, so a key that current guidance contradicts is corrected before the round
  is ever played. The next session reads the store and presents (`start --prepared`,
  `present`); nothing is written or looked up before the learner starts, before the case
  appears, or before either feedback. An optional nightly scheduled task (`prepare_task`;
  `SKILL.md`, "Prepare only") prepares a round whenever none is ready. A prepared round is used only if the ledger and the mix are
  unchanged (`state_schema.md` §8).
- **Three roles, three models (the `helpers` setting, on by default).** Where the app has
  helper agents: an **author** on the most capable model writes the round
  (`references/author.md`); the conversation is the **examiner**, which grades against the
  evidence and never marks items it wrote, or even reads their keys before the answers are in;
  a **checker** on a mid-tier model verifies the sources when the round is prepared
  (`references/evidence_check.md`). Mechanical steps stay with the conversation. `helpers:
  false` makes one assistant do all three (`SKILL.md`, "Roles").
- **Behind the scenes at every step** the remaining work (filing for the log, the save, the
  next round) happens while the learner reads (`SKILL.md`, "Speed"; `feedback_guide.md` §9).
- Leaner sealed drafts (one-line pre-flight record, keys before stems), so a round that could
  not be prepared still starts quickly.

## Page update 4.2.1

- The learner's page was redesigned: a summary band with a score trend, a segmented view switch
  that actually switches views (the 4.2 page's panels used `display:flex`, which overrode the
  `hidden` attribute, so every tab stayed visible), readable session transcripts, gaps sorted by
  urgency with long notes folded, a topics table with mastery bars, and steppers for the round
  mix. `cme.py` (`PAGE_VERSION = "4.2.1"`) upgrades older pages at the next save.

## What is new in version 4.2

- **Focused questions.** A short case that ends in one free-text question on a single decision
  (diagnosis, interpretation, the next test, management, disposition, prevention or prognosis),
  graded on the reasoning with a rubric written before the question is sent. They go with the
  MCQs, before the case; due topics and open gaps go to them before the MCQs, and the aspect
  asked rotates (`case_design.md` §11, `feedback_guide.md` §2 B2, `analysis_framework.md` §1.6).
- **Choose the round mix.** MCQs, focused questions and the full case can each be on or off, at
  setup, in a chat, or with switches in the page's Settings tab (stored as `cme/prefs` in the
  page's database and applied at the next round; the latest change wins).
- **The page updates itself.** A learner's page older than the skill's template is replaced in
  the normal save, once.
- Rounds without a case, stats that keep focused questions apart from the case, and a repair
  for gaps recorded on topics the ledger did not yet list.

## What was new in version 4.1

- **No dependence on particular tool names.** The skill describes the capabilities it needs
  (run Python, reach the store file to file, web search, …) and the assistant finds the matching
  tools in whatever app and version it runs in (`SKILL.md`, "Tools"; `references/store.md` §2).
- **The ledger lives in files inside your own private "Clinical CME" page** (where the app can
  host one), so one read fetches it and one write saves the ledger, the session and the index
  together, refused rather than overwritten if another device saved in between. A folder or
  files you keep work as well, for any assistant.
- **Faster sessions, same quality.** Status and plan in one step; the case is drafted while you
  answer the MCQs; evidence checks run in parallel; the verbatim log is assembled from what was
  already written, and saves happen while you read the feedback.
- Version-4.0 learners (ledger in the page's database) move to files once (`store.md` §6);
  version-3 learners (Google Drive journal or `learner_ledger.json`) migrate once (`store.md` §7).

## Install and share

Copy the `clinical-cme` folder into your skills (or install it as a plugin). The folder holds no
personal data, so it can be given to colleagues as it is; each person's first run creates their
own private store. Requires Python 3.8+ in the session (standard library only).

## Running on other assistants

Everything except the page is plain Markdown and a standard-library Python script, so any
assistant that can follow written instructions, run Python on files and exchange files can run
it. What to know:

- **Store.** The private page with files (store A) is a Claude feature. Elsewhere use a folder
  the assistant can read and write (C), or files the learner attaches and keeps (D). The layout
  is the same everywhere (`data/state.json`, `data/index.json`, `data/sessions/…`), so a learner
  can move between them by copying the `data` folder.
- **Capabilities.** If a capability in `SKILL.md` ("Tools") is missing, follow its "If missing"
  column; the round still runs. Without the ability to run Python on files, it cannot.
- **Blinding.** The assistant must be able to keep its visible reasoning free of the content
  ("Sealed"). If an assistant shows its full reasoning to the user, tell learners not
  to open it before answering.
- **The page.** `templates/page.html` uses the Claude page interface for the database and the
  Export button; it reads the files with plain `fetch`, so it also works when the `data` folder
  sits next to it on any static web host the learner controls.

## Layout

```
SKILL.md                      the protocol the assistant follows in a round
scripts/cme.py                the state engine (start, present, save, close, prepare, stash, stats …)
references/store.md           the store: capabilities, kinds of store, reading/writing, setup,
                              migration, recovery, mirror, export
references/state_schema.md    ledger layout, round and reflection JSON, spacing rules, commands
references/case_design.md     how cases and MCQs are written (blinding, realism, pre-flight)
references/feedback_guide.md  grading, evidence briefings, reflection prompt, disputes, feedback kits
references/author.md          the author's brief: how a round's items and notes are written
references/evidence_check.md  the checker's brief: how the evidence is verified
references/analysis_framework.md  coding vocabulary and the deep review
references/session_log.md     the per-session document, errata, search, teaching export
references/progress_review.md the periodic review
references/onboarding.md      first run, migration notes, FAQ
templates/page.html           the learner's page, published at setup
templates/blueprint.json      default internal/hospital-medicine curriculum (also blueprint.md)
templates/resource_library.md dependable sources by domain
legacy/                       version-3 scripts, used only for migration
```

Self-directed learning, not accredited CME. Content can contain errors; feedback cites sources.

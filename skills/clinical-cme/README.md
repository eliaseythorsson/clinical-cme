# clinical-cme (version 5.0.0)

Blinded clinical self-assessment rounds for physicians: single-best-answer questions and
focused questions on unrelated topics, with their feedback, then one clinical case and its
feedback — in the mix each learner chooses — graded against current evidence, with a one-minute
reflection that feeds spaced repetition. Every round is coded (reasoning steps, error types,
biases, calibration) and periodically analysed in a candid progress review.

## What is new in version 5.0

Built from four real rounds in testing mode and an architecture review (issues #41–#57 on
GitHub; plan in `docs/plan-v5.md`).

- **Themed blocks.** Rounds run in blocks of 12 on one domain (60% theme, 25% due repeats,
  15% wildcard; the case on the theme), with a capped drill-down and a three-day rest after a
  miss. The theme is shown; topics stay blind.
- **Your level and aim in your own words.** Setup asks where you are and where you're aiming
  as two open questions; items are pitched to your paragraphs, editable on your page.
- **One work folder per job.** Every command takes only the work folder; one publish set says
  what to write back to the store, the ledger last.
- **A rulebook** (`references/standards.md`) for writing items, with a lint at preparation:
  one time anchor per case, crux tests requested not given, abbreviations defined once with a
  glossary line in feedback, results not ordered taught as such, no internal jargon.
- **Evidence checked at preparation** by fallback routes, counted, with one retry.
- **Podcast picks** prepared ahead (three Spotify candidates per topic), chosen for your actual
  gap after grading; **reading and listening** collected on a new page tab.
- **The page reads its own file** (`data/page.json`), already blinded; new estimates (5 min per
  MCQ, 10 per focused question, 25 per case) blending to your own pace; a time hint after five
  timed rounds.
- **Learner overrides** ("record it as 4", "close that gap") kept honestly beside the grading.
- **Faster start**: no reference reading before the first questions; the engine writes the
  opening line.
- Prepared rounds survive settings that don't change their content; the round mix set on the
  page wins over a prepared round.

## What is new in version 4.3.1

- A round keeps the date it was played on when the reflection arrives on a later day (before,
  its schedule shifted by the delay).
- Stage 2 of a case is assembled from the results bank alone; the examiner no longer opens the
  case's key before the final answers.
- Testing mode ("testing mode on"): a 30-second check at the end of each round and an automatic
  check that everything was saved, kept in `data/testing/`.

## What is new in version 4.3

The aim of this version: the learner is always reading, answering or reading feedback, never
waiting for something to be generated.

- **New order.** Short questions → their feedback → the full case → its feedback, with the gap
  summary for the whole round and one reflection at the end. The round is blind part by part,
  and the log keeps both feedback messages in place (`feedback_questions.md` and `feedback.md`).
- **The whole round is prepared ahead.** After each close the next round is planned and
  written in full — short questions, the case's Stage 1 with a results bank (so Stage 2 goes
  out the moment Stage 1 is answered), and the notes for both feedbacks — and kept, packed, in
  the store (`data/prepared.json`; `cme.py prepare`, `finish-prepare`), together with the checked
  evidence for it, so a key that current guidance contradicts is corrected before the round
  is ever played. The next session reads the store and presents (`start` finds it in the store copy,
  `present`); nothing is written or looked up before the learner starts, before the case
  appears, or before either feedback. An optional nightly scheduled task (`prepare_task`;
  `references/preparing.md` §3–4) prepares a round whenever none is ready. A prepared round is used only if the ledger and the mix are
  unchanged (`state_schema.md` §8).
- **Three roles, three models (the `helpers` setting, on by default).** Where the app has
  helper agents: an **author** on the most capable model writes the round
  (`references/author.md`); the conversation is the **examiner**, which grades against the
  evidence and never marks items it wrote, or even reads their keys before the answers are in;
  a **checker** on a mid-tier model verifies the sources when the round is prepared
  (`references/evidence_check.md`). Mechanical steps stay with the conversation. `helpers:
  false` makes one assistant do all three (`SKILL.md`, "Roles").
- **Behind the scenes at every step** the remaining work (filing for the log, the save, the
  next round) happens while the learner reads (`SKILL.md`, "Session flow"; `references/preparing.md`; `feedback_guide.md` §9).
- Leaner sealed drafts (one-line pre-flight record, keys before stems), so a round that could
  not be prepared still starts quickly.

## Page update 5.4.0

- **Reading & listening.** The further-reading pointers of a round's feedback are now also
  structured data: the examiner lists them in `round.json` as `reading` (topic, title, link,
  section, minutes, why), `save` writes them into the session document beside the `listening`
  picks, and the page file carries both as `library` (the last 100, newest first). The page
  has a "Reading & listening" tab that lists them by session and topic, with links that open
  in a new tab and a done mark kept in the viewer's own browser (never in the store).
  `cme.py` (`PAGE_VERSION = "5.4.0"`) upgrades older pages once, at the next save.

## Page update 5.3.0

- **Where you are, where you're aiming.** Setup asks two open questions and keeps the
  learner's paragraphs word for word (`profile.journey`, `profile.aim`); items are pitched to
  them and feedback written for them (`standards.md` rule 4: which decisions are tested, how
  much background or evidence depth, and an exam's own sources for an exam aim). A stage
  label and goal tags are derived for display only. The page's Settings tab shows both
  paragraphs with an Update box each (saved in `cme/prefs`, applied at the next round, which
  is then written afresh). Older ledgers fold `role`, `goals` and `notes` into the paragraphs
  unchanged. A new learner starts with one focused question and the case (about 35 minutes);
  MCQs are added on request.
  `cme.py` (`PAGE_VERSION = "5.3.0"`) upgrades older pages once, at the next save.

## Page update 5.2.0

- Real time per round. `cme.py` notes when each step of a round happens and records the
  round's active time, split into answering, waiting and reading, with idle stretches cut (no
  more 180-minute sessions when a chat is left open). Nobody types a time.
- Estimates move from the defaults to the learner's own pace over ten timed rounds; the page
  and the opening line then say "based on your last N rounds".
- From five timed rounds the close and the page show a hint: the median round against the
  budget, and the one change to the mix that would fit it best.

## Page update 5.1.0

- The page reads its own file. `cme.py` writes `data/page.json` with every ledger: exactly what
  the page may show (past sessions, topics already tested, the round mix with its time
  estimate, the block's theme, reviews, settings), already blinded and tested in Python. The
  page no longer reads the ledger, so it cannot show an open gap or a due date; `data/index.json`
  is gone (`cme.py rebuild-page` replaces `reindex`). A store from before this version gets
  its page file at the next save.
- Time estimates come from the engine and are realistic: about 5 minutes per MCQ, 10 per
  focused question, 25 for a case with its feedback (15 for a one-step case).
- Export is still a full backup; the page now says first that it includes the open gaps.
  `cme.py` (`PAGE_VERSION = "5.1.0"`) upgrades older pages once, at the next save.


## Page update 5.0.0

- The learner's page no longer previews the next round. The "Gaps & topics" view (open gaps by
  name, most urgent first, and every topic's next review date) and the "Due now" tile are gone.
  In their place a "Progress" view lists the topics already tested, most recently tested first,
  with mastery, last-tested date and calibration, and the summary band counts topics tested.
  Past sessions, scores, the score trend and progress reviews are unchanged. `cme.py`
  (`PAGE_VERSION = "5.0.0"`) upgrades older pages once, at the next save.

## Page update 4.2.1

- The learner's page was redesigned: a summary band with a score trend, a segmented view switch
  that actually switches views (the 4.2 page's panels used `display:flex`, which overrode the
  `hidden` attribute, so every tab stayed visible), readable session transcripts, gaps sorted by
  urgency with long notes folded, a topics table with mastery bars, and steppers for the round
  mix. `cme.py` upgraded older pages at the next save.

## What is new in version 4.2

- **Focused questions.** A short case that ends in one free-text question on a single decision
  (diagnosis, interpretation, the next test, management, disposition, prevention or prognosis),
  graded on the reasoning with a rubric written before the question is sent. They go with the
  MCQs, before the case; due topics and open gaps go to them before the MCQs, and the aspect
  asked rotates (`case_design.md` §11, `feedback_guide.md` §2 B2, `analysis_framework.md` §1.6).
- **Choose the round mix.** MCQs, focused questions and the full case can each be on or off, at
  setup, in a chat, or with switches in the page's Settings tab (stored by the page as `cme/prefs`
  and applied at the next round; the latest change wins).
- **The page updates itself.** A learner's page older than the skill's template is replaced in
  the normal save, once.
- Rounds without a case, stats that keep focused questions apart from the case, and a repair
  for gaps recorded on topics the ledger did not yet list.

## What was new in version 4.1

- **The ledger lives in files inside your own private "Clinical CME" page** (where the app can
  host one), so one read fetches it and one write saves the ledger, the session and the index
  together, refused rather than overwritten if another device saved in between. A folder or
  files you keep work as well.
- **Faster sessions, same quality.** Status and plan in one step; the case is drafted while you
  answer the MCQs; evidence checks run in parallel; the verbatim log is assembled from what was
  already written, and saves happen while you read the feedback.

## Install and share

Copy the `clinical-cme` folder into your skills (or install it as a plugin). The folder holds no
personal data, so it can be given to colleagues as it is; each person's first run creates their
own private store. Requires Python 3.8+ in the session (standard library only).

## Layout

```
SKILL.md                      the round protocol: what needs judgement (presenting, grading,
                              feedback); the rest is in the references
scripts/cme.py                the state engine (start, present, save, close, prepare, finish-prepare, stats …)
references/store.md           the store: documents, tools, kinds of store, reading/writing,
                              setup, recovery, export
references/state_schema.md    ledger layout, round and reflection JSON, spacing rules, commands
references/standards.md       the rulebook: numbered rules for items, keys and kits; what the lint checks
references/case_design.md     how cases and MCQs are designed (realism, formats, pre-flight)
references/feedback_guide.md  grading, evidence briefings, reflection prompt, disputes, feedback kits
references/author.md          the author's brief: how a round's items and notes are written
references/evidence_check.md  the checker's brief: how the evidence is verified
references/analysis_framework.md  coding vocabulary and the deep review
references/session_log.md     the per-session document, errata, search, teaching export
references/progress_review.md the periodic review
references/onboarding.md      first run, FAQ
references/preparing.md       preparing a round ahead: after the close, prepare-only sessions,
                              overnight preparation, a round that was not prepared
references/requests.md        requests other than a round, testing mode, round variants
templates/page.html           the learner's page, published at setup
templates/blueprint.json      default internal/hospital-medicine curriculum (also blueprint.md)
templates/resource_library.md dependable sources by domain
```

Self-directed learning, not accredited CME. Content can contain errors; feedback cites sources.

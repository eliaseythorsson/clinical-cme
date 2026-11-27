# clinical-cme (version 7.1.0)

Blinded clinical self-assessment rounds for physicians: single-best-answer questions and
focused questions on unrelated topics, with their feedback, then one clinical case and its
feedback — in the mix each learner chooses — graded against current evidence, with a one-minute
reflection that feeds spaced repetition. Every round is coded (reasoning steps, error types,
biases, calibration) and periodically analysed in a candid progress review.

## Usage: Full or Economy (#93, not yet released)

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

Technical: `config.usage` (`full`, the default and what every existing ledger reads as, or
`economy`); a preset resolved whenever the settings are read, never written into the ledger;
`config.set_by_learner` keeps what the learner set themselves (ADR 0015). `start`, `open`,
`settings` and `init` print `usage` (who writes the items, how far the evidence check goes, the
settings as they take effect). A usage set on the page is kept in the ledger at the next round
and sets a round prepared before it aside. `start --case` brings the case into a round without
it (Economy's every other round).

## Page update 5.7.0

- Settings has a **Full / Economy** control ("How much of your Claude usage rounds use"), saved
  to `cme/prefs` as `usage` and applied from the next round; the settings list shows the usage.
- With Economy's own round the mix reads "… + 1 case every other round"; a mix saved on the page
  is the learner's own and has the case in every round.

## What is new in version 7.1

For learners:
- **Full or Economy.** Setup asks how much of your Claude usage rounds should take; switch any
  time by asking or on your page (page 5.7.0). Economy: questions written by the examiner's own
  model, only the facts the keys turn on checked, no podcast picks or deeper evidence, and a
  smaller round with the full case every other round. Your own settings always win.
- **No warm-up for new learners.** Guideline citations of the default blueprint are checked once,
  centrally, and ship with updates; your install no longer sweeps them. Any region reads the
  shared checks (UK and Europe the European set, everyone else the International set).
- **Lighter rounds.** The instructions are split so each step reads only what it needs: about 35%
  less reading per round.

Technical: `config.usage` preset applied at read time with `config.set_by_learner` (ADR 0015);
`start --case`; central records in `templates/guideline_checks.json` kept by `cme.py
central-checks` and `docs/maintaining-guidelines.md`, `config.guideline_sweeps` (ADR 0013);
references split (ADR 0014, `docs/reading-load.md`); simulation records tokens per role (#94);
measurements in `docs/usage-measurement.md`.

## What is new in version 7.0

Built on 2026-11-27 from the queue after 6.0 (#83 step 2, #84, #85, #89, #90, #56, #57, #72;
ADRs 0010–0012).

- **Installable anywhere (#56).** The skill ships as a plugin of its own. A new learner who skips
  the region question gets **International** guidance (European and US societies; an item never
  turns on a point where they disagree, and the feedback names both). Existing learners keep
  their region; a ledger from 6.0 or earlier without one keeps Iceland/Europe.
- **Guidelines kept current (#90, #89).** Each guideline the blueprint cites is re-checked while
  the next round is prepared (the round's own tags, plus a rolling sweep, plus a full sweep
  before a progress review); a superseded one is flagged, never silently rewritten. The
  remaining blueprint citations were checked; heart failure follows ESC 2026.
- **Your date, not the server's (#84).** A round is dated in the learner's own day; unattended
  jobs remember the learner's UTC offset.
- **Saving across devices (#57).** The engine finds the store's files by their content, writes a
  folder store itself after checking no other device wrote in between, and replays the job's
  steps on top of a newer ledger instead of failing.

Technical:

- New store file `data/guidelines.json` (one check record per tag; the ledger keeps only
  `guidelines_gen`), written before the ledger in the publish set (ADR 0011).
- New in the assistant's procedure: `--today` (the learner's date, fixed per job) and
  `--utc-offset` on `start`/`open`; `cme.py publish` (folder adapter); `open --reread` and step
  tokens in the ledger for rebase (ADR 0010).
- One load step for the ledger: declared shape, defaults applied once, named upgrades
  (`old_default_region`), tests per era (#83 step 2). One commit step for writing commands;
  `plan_round` split into eligible, slotted, briefed (#85).
- Tests run in parallel (`pytest -n auto`, #72); one version source checked by
  `tests/test_version.py`; MIT engine, CC BY-NC 4.0 content.

## Page update 5.6.0

- The page carries its content licence (CC BY-NC 4.0) in a comment; nothing visible changes.

## What is new in version 6.0

Built overnight on 2026-11-27 from the queue in issue #87, before the learner's test week
(issues #73–#83, #86, #88; ADR 0009).

- **Two-level blueprint (#81, #82).** The default blueprint is now 16 areas, 144 diseases and
  347 sub-topics, on the ABIM Internal Medicine skeleton with European guidance, each sub-topic
  with its decision points and aspect weights. The disease returns on schedule; the sub-topic
  rotates and is recorded; gaps retest the exact point; feedback links sibling sub-topics. An
  area's weight is its share of new material whatever its number of diseases. Existing ledgers
  keep their own blueprint; `settings --blueprint` and `apply-mapping` move one across.
- **Feedback from prepared, checked text (#78, #77, ADR 0009).** Kits hold finished feedback per
  rubric element (hit, partial, missed); the examiner marks first, then `cme.py draft` assembles
  the feedback, adapted live to the learner's words. One examiner brief (`feedback_guide.md`).
- **Grading and reflection forms (#76).** The engine prints them, rubric included; the command
  and file tables in `state_schema.md` are generated.
- **Evidence depth (#86).** The more often a topic is answered well in a row, the further behind
  the recommendation its feedback goes (guidance → studies → design → frontier).
- **The learner's stop and position note (#75).** "I know this, stop bringing it back" pauses a
  topic for 90 days (never for good); a position note on one decision point is respected, never
  marked down, and reviewed at each progress review.
- **One way to apply a round again (#74).** Save again, close, override and undo all go through
  one path; only the latest round on a topic is re-applied.
- **Scheduling (#79, #80).** With six or more topics overdue, repeats take 40% (theme 45%); a
  theme topic seen twice in a block waits a week. The theme proposal counts measured weakness;
  any area can be a theme; TOX and EMRG are one area.
- **Engine version on the ledger (#83, step 1).** An older engine will not overwrite a ledger
  saved by a newer one.
- **Tests run in-process (#73):** the suite takes about 40 s instead of 5 minutes.

## Page update 5.5.0

- "Your positions": the position notes in force.
- Tested sub-topics listed under their disease.

## What is new in version 5.0

Built from four real rounds in testing mode and an architecture review (issues #41–#57 on
GitHub; plan in `docs/plan-v5.md`).

- **Themed blocks.** Rounds run in blocks of 12 on one domain (two rounds per topic for a domain
  of fewer than four; 60% theme, 25% due repeats, 15% wildcard; 45/40/15 while six or more topics are overdue; the case on the theme), with a
  capped drill-down (a theme topic missed on its second round of a block waits a week) and a
  three-day rest after a miss. The theme is shown; topics stay blind.
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
  `references/prepare_only.md`) prepares a round whenever none is ready. A prepared round is used only if the ledger and the mix are
  unchanged (`state_schema.md` §8).
- **Three roles, three models (the `helpers` setting, on by default).** Where the app has
  helper agents: an **author** on the most capable model writes the round
  (`references/author.md`); the conversation is the **examiner**, which grades against the
  evidence and never marks items it wrote, or even reads their keys before the answers are in;
  a **checker** on a mid-tier model verifies the sources when the round is prepared
  (`references/evidence_check.md`). Mechanical steps stay with the conversation. `helpers:
  false` makes one assistant do all three (`SKILL.md`, "Roles").
- **Behind the scenes at every step** the remaining work (filing for the log, the save, the
  next round) happens while the learner reads (`SKILL.md`, "Session flow"; `references/preparing.md`; `grading.md` §2).
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
  asked rotates (`case_design.md` §11, `feedback_guide.md` §2 B2, `coding.md` §5).
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

Install the plugin (`../../README.md`: two steps from the marketplace), or copy this
`clinical-cme` folder into your skills. It runs in the **Claude app** (everything: the page
store, helper agents, overnight preparation) and in **Claude Code** (a folder store, no page);
nothing else is supported. It needs Python 3.8+ in the session (standard library only). The
folder holds no personal data, so it can be given to colleagues as it is; each person's first
run creates their own private store. Licences: `LICENSE.md` (content CC BY-NC 4.0, `cme.py` MIT).

## Layout

```
SKILL.md                      the round protocol: what needs judgement (presenting, grading,
                              feedback); the rest is in the references
scripts/cme.py                the state engine (start, present, save, close, prepare, finish-prepare, stats …)
references/store.md           the store: documents, tools, kinds of store, setup, recovery, export
references/publishing.md      reading the store and publishing what a job wrote (every job)
references/state_schema.md    ledger layout, round and reflection JSON, spacing rules, commands
references/standards.md       the rulebook: numbered rules for items, keys and kits; what the lint checks
references/standards_region.md     rule 2, guideline region (read by the checkers too)
references/standards_kits.md  rule 8, what a kit contains (read by the checkers too)
references/standards_listening.md  rule 8's Listening section (read by the checkers too)
references/standards_positions.md  rule 12, the learner's position notes (read by the checkers too)
references/standards_lint.md  what the lint checks, and its heuristics
references/case_design.md     how cases and MCQs are designed (realism, formats, pre-flight)
references/drills.md          building an item around a drill (a thinking pattern to practise against)
references/grading.md         the examiner's brief: verifying, marks before text, the draft,
                              live text, reflection prompt, the log
references/feedback_guide.md  what the feedback says (examiner and author): guidance, structure,
                              evidence briefing, scaling, length, the rules it keeps
references/evidence_depth.md  how far behind the recommendation feedback goes on a topic known well
references/listening.md       the final feedback's Listening section: one episode per topic
references/coding.md          coding a round at grading time (ART, Revised-IDEA, errors)
references/disputes.md        disputes, scores and gaps the learner sets, the learner's stop
references/author.md          the author's brief: how a round's items and prepared feedback are written
references/author_revise.md   the author's pass back on a written round (headers, revise)
references/evidence_check.md  the checker's brief: how the evidence is verified
references/tag_check.md       the tag checker's brief: is a cited guideline still the one to cite
references/analysis_framework.md  the deep review, and calibration as `stats` reports it
references/session_log.md     the per-session document, errata, search, teaching export
references/progress_review.md the periodic review
references/onboarding.md      first run, FAQ
references/preparing.md       preparing a round ahead: what is made ready, after the close
references/prepare_only.md    prepare-only sessions and overnight (always-ready) preparation
references/unprepared.md      a round that was not prepared: written at the session
references/requests.md        requests other than a round, testing mode, round variants
templates/page.html           the learner's page, published at setup
templates/blueprint.json      default internal/hospital-medicine curriculum, two levels (also blueprint.md)
templates/resource_library.md dependable sources by domain
blueprints/                   checked blueprints for other specialties, and how one is contributed
LICENSE.md                    content CC BY-NC 4.0, cme.py MIT
```

Self-directed learning, not accredited CME. Content can contain errors; feedback cites sources.

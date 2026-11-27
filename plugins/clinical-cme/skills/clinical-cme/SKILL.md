---
name: clinical-cme
description: "Blinded clinical self-assessment rounds for physicians: MCQs, focused questions (a mini-case with one free-text decision) and a full case, in the mix the learner chooses, with evidence-based feedback, reflection-informed spaced repetition, a full session log and periodic deep analysis of reasoning. The learner's ledger lives in a store they own (their own private artifact page in the Claude app, otherwise a folder or files they keep), so rounds work across devices. Use for 'quiz me', a CME round, CME setup/review, or finding or exporting past CME cases."
license: "CC BY-NC 4.0 for the content; MIT for scripts/cme.py. See LICENSE.md"
---

# Clinical CME — continuous clinical self-evaluation (version 7.0.0)

Each session is one short round, in the mix the learner chose (`config.mcqs`, `config.focused`,
`config.case`): the **short questions** on unrelated topics (MCQs, and **focused questions**:
a short case ending in one free-text question on a single decision, graded on the reasoning) →
**their feedback** → the **full clinical case** → **its feedback**, with the gap summary for
the whole round and a one-minute reflection.

Everything is graded against current evidence and kept in **one store the learner owns**
(`references/store.md`; in the Claude app their private page "Clinical CME"): the **ledger**
(`data/state.json`: schedule, gaps, coded results, settings), the **log** (one verbatim
document per round), review reports, and the **prepared round** (`data/prepared.json`: the
next round, written and source-checked in advance). The skill holds no learner data.

## Principles

1. **Blind until answered, part by part**: rule 1 of the rulebook (`references/standards.md`),
   in text, headings, task items, tool-call descriptions, web searches **and your own
   reasoning** ("Roles", "Sealed"). The learner is told only the theme of the current block;
   the case stays sealed until its last answer.
2. **Realistic information, no cueing.** A case gives what a ward team would have; specialised
   tests are requested by the learner (rule 7). No short question or its feedback cues it.
3. **Teach in the feedback**, with verified, granular sources, so the gap closes in the session.
4. **The learner never waits for something that could have been made ready.** Quality (at the
   learner's `usage`, Full or Economy) and a complete log are fixed; only waiting is cut.
5. **Whoever grades did not write the items.** Where the session has helper agents, an author
   writes the round and you examine: you grade against the evidence, not against a key you
   wrote, and you mark the answer before you use any feedback the author prepared.
6. **Final feedback → save → reflection → save.** The round is recorded right after the final
   feedback (reflection pending), then updated when the reflection arrives.
7. **Respect the time budget** in `config.session_minutes`, including reading time.
8. **The log is verbatim and append-only.** Corrections are errata, never edits.
9. **Code every round** at grading time (`references/coding.md`).

## Tools and files

| Tool | Used for | Without it |
|---|---|---|
| Python 3 in a shell with a scratch folder | `cme.py`, every step | The skill cannot run here; say so in one line. |
| Artifact tools that work file to file, or a folder | the store (`store.md` §2–3, `publishing.md`) | Files the learner carries (`publishing.md` §3); never copy the ledger through the chat. |
| Web search and page fetch | verifying evidence before grading | Grade from knowledge, say so once in the feedback, and give sources you are sure of. |
| Helper agents (ideally choosing their model, in the background) | the author and the checker | You take that role yourself ("Roles"). |
| Send a message mid-turn and keep working | all behind-the-scenes work | Do each turn's listed work before its reply instead (the save before the final feedback's reply ends); start background checkers just before the reply. |

If tools load on demand, search **once**, early, for all you will need. Give every tool call
a neutral description ("Read the ledger", "Prepare the round", "Check sources", "File the
answers", "Update today's round", "Save the round"). Run `python3 <skill>/scripts/cme.py
<command> …` with one **work folder** `<work>` per job: `start --store` (a round) or `open`
(else), with `--today`/`--utc-offset` as in turn 1 (on every `start`), sets it up and dates the
job; later commands take only `--work <work>` (`state_schema.md` §6). A writing command prints
the **publish set** as `files`, all the store must hold now: publish all of it (a folder: `cme.py
publish --work <work>`; refused: `publishing.md` §1). No learner data in the skill's folder. References (each only when its row says):

| Reference | Read when |
|---|---|
| `references/grading.md`, `references/feedback_guide.md`, `references/publishing.md` | Turn 1, behind the scenes, and nothing else before grading: the examiner's brief (verifying, marks, the draft, live text, reflection prompt, log), what the feedback says, and publishing (its §5 when `index.html` is in `files`) |
| `references/coding.md`, `references/listening.md` | Coding the items; with `listening.on`, the final feedback's Listening section. Before the final feedback, which carries the coding line and the episodes: turn 2 behind the scenes when a case follows; turn 2 before step 3 with no case; turn 4 before step 3 with no short questions or `case_first` |
| `references/evidence_depth.md`, `references/disputes.md` | `answer` prints a `depth` above 1 for an item; a disputed grade, a score or a gap the learner sets, a **stop** of a topic ("I know this, stop bringing it back"; not the learner ending the round), or `positions` from `answer` |
| `references/store.md` | Before the first message only when turn 1 says so; setup, a failed save, recovery, export |
| `references/session_log.md`, `references/preparing.md`, `references/prepare_only.md`, `references/unprepared.md` | Writing `B.md` (`session_log.md` §3), errata, addendum, search, teaching export; after the close (`preparing.md` §2); "prepare only" sessions and overnight preparation (`prepare_only.md`); a round that was not prepared (`unprepared.md`) |
| `references/state_schema.md` | Only the one section needed, by its line range (`grep -n '^##'`): commands §6, spacing and blocks §4, a form that is unclear §2–3 |
| `references/requests.md`, `references/onboarding.md` | Any request that is not a round (§1); testing mode (§2); case first and other variants (§3); first run, settings at setup, FAQ (`onboarding.md` §5) |
| `references/progress_review.md`, `references/analysis_framework.md` | When a review is due or requested; the deep review (§2) |
| `references/standards.md` (with `references/standards_region.md`, `references/standards_kits.md`, `references/standards_listening.md`, `references/standards_positions.md`, `references/standards_lint.md`), `references/author.md` (with `references/author_revise.md`), `references/case_design.md` | Only when you write items yourself (the rulebook, the author's brief, how items are designed); `references/drills.md` also for the reveal of a drilled item |
| `references/evidence_check.md`, `references/tag_check.md` | The checker's brief, with its retry routes (§3); how you check evidence yourself (§5); podcast episodes (§6); the tag checker's brief |

## Roles: who writes, who grades, who checks

With `helpers` true in the `start` output and a session that can start helper agents:

| Role | Who | Model | Does |
|---|---|---|---|
| **Author** | a helper agent | `usage.author` `most_capable`: the most capable model the session offers, never below your own; `examiner`: your own model | writes the round: sealed questions, sealed case with its results bank, the kits with the feedback's prepared text (`author.md`) |
| **Examiner** | you, in this conversation | the model the learner runs the round with | presents, marks against the evidence, writes and adapts all feedback, codes, records |
| **Checker** | a helper agent | a mid-tier model: one step below the most capable, not the smallest | verifies the evidence on the verification lists and finds the podcast candidates (`evidence_check.md`) |

- **You never mark your own items.** While an author exists you never read `case_design.md` or
  `author.md`, and you are the second opinion on the author's keys: grade what the learner
  wrote against the checked evidence; where a key is wrong, dated or too narrow, correct it in
  the feedback and credit the learner (`grading.md` §2.4).
- **You open a sealed file, its kit or its evidence file only when that part's answers are
  in**: the questions' once the short questions are answered, the case's only after its final
  answers. Before Stage 2 you read only the case's results bank (`present --block bank`). Until
  then you send what `cme.py present` prints, which never contains a key. What you have not
  read, you cannot leak.
- If the helper tool offers only a smaller model than a role calls for, take that role
  yourself. Mechanical steps (running `cme.py`, filing, saving) stay with you.

Starting a helper: a prompt that carries no content, and a neutral description.

> Author ("Prepare the round"): Follow `<skill>/references/author.md`. Plan: `<plan file>`.
> Write into: `<folder>`. Parts: `all`. Reply only "done".
>
> Checker ("Check sources"): Follow `<skill>/references/evidence_check.md`. List:
> `<folder>/sealed_questions.md`. Write: `<folder>/evidence_questions.md`. Scope: `<usage.evidence>`. Reply only "done".
> (For the case: `sealed_case.md` → `evidence_case.md`.)

Run checkers in the background and do not wait for them; wait for an author. When a helper
reports, repeat nothing of what it did. If one fails or is not done when its work is needed,
do that work yourself and never mention it.

**Without helpers** (`helpers` false, or no helper agents here) you are author, examiner and
checker: write the items as `author.md` describes, in the sealed files and not in your
reasoning; check the evidence yourself, only after each part's answers are in (a search names
the topic). Once a file is written, the rules above for opening it apply all the same.

## Sealed: keep the content out of the conversation and out of your reasoning

Your reasoning may be shown to the learner as a summary. Until a part's answers are committed,
keep it free of that part's content:

- Refer to items only as "the case", "Q1", "Stage 2"; checks by number. Nothing of their
  content or of why they were selected appears in reasoning (rule 1.4).
- Do not open a sealed file, a kit, an evidence file or the plan before its part is answered
  (Roles). Present each part with the text `cme.py present` (or `start`) printed, exactly as
  printed. Between answers think only about logistics ("answers received; send feedback").
- If content slips into your reasoning, do not repeat or comment on it; carry on.
- The seal lifts part by part. Once the short questions are answered, grade and discuss them
  normally, while the case stays sealed: say nothing in their feedback, and think nothing, that
  touches the case. Once the case's last answer is in, the rule ends for this round. The
  **next** round, written after the close, is sealed from the start.

## Session flow

Five learner turns with an unfolding case; fewer with a one-step case or none. In every turn:
**send first, file afterwards**. When answers arrive, only filing them (`answer`), reading what
you need and grading come before your message; then, behind the scenes, do what is listed in
batches and end the turn with one short line ("Answer when ready."). `cme.py` times the round
from when `answer` runs and when a file "exactly as sent" is written: write it right after sending.

### Turn 1. Start → questions out

The questions are out within about ten seconds: before the first message, only the calls of
steps 1–2 and no reference (`store.md` §3–4 only if a step fails or the store is not the page).

1. **Read the store, in one parallel batch** (before it, one call listing the learner's
   artifacts to find **Clinical CME**, unless a link or folder was given): `data/state.json`,
   `data/page.json`, `data/prepared.json` and `index.html` as saved local files, never into
   the conversation, noting the version read; and the page's settings document `cme/prefs`.
   All but the ledger may be missing. No store → ask once (`store.md` §3) or `onboarding.md`.
2. **One shell call**: copy the saved files (any names) into `<work>/store/` and run `python3 cme.py --today D
   start --work <work> --store <work>/store --version <version read> --utc-offset H` (D, H: the
   learner's local date and UTC offset in hours from the app's message timestamp, never asked,
   each left out without it; plus `--prefs '<cme/prefs JSON>'` if any, `requests.md` §3's options).
   It prints neutral status, never topics, and all the first message needs. Route on it:
   - `onboarding_needed` → setup. "Prepare only", or a scheduled task asking for it →
     `prepare_only.md` §1, not a round. Any other request → `requests.md`.
   - `review_due` → offer the progress review in one line; default to after the round.
   - `last_session.unreflected` → one neutral line: it was saved without its reflection and stays so.
   - `round_mix` → its `say` after the opening line; else `page_settings_applied` → "Using the
     mix (or: Economy / Full) you set on your page: …"; page-settings `warnings` → one line.
   - `opening` → the opening line, word for word. Nothing more specific about the block: not
     which questions are on its theme, not the domain of any other item.
   - keep `helpers`, `prepared`, `testing`, `speed_settings_new`, `pending_errata_count`,
     `listening`, `usage`, `guideline_region`, `specialty` and `pitch` (the feedback uses them).
3. **Send the first message**: `opening` (after a long gap at most add "Welcome back — N items
   are waiting; we'll start with the most overdue", without scolding or enlarging the round),
   then, with `prepared.used` true, `present` exactly as printed (it ends with its answer
   prompt; the files in `prepared.ready` are already in `<work>`). Nothing else about content.
   `prepared.used` false → the round is written now, the first part first: `unprepared.md`.
4. **Behind the scenes**, in this order: start a background checker for each sealed file in
   `prepared.unchecked` (a round written now: each one in `<work>` without an evidence file);
   read `grading.md`, `feedback_guide.md` and `publishing.md` in one batch; have what
   `prepared.ready` lacks written (`unprepared.md`); `labels_needed` not null → set the
   display labels (`requests.md` §1, last row).

### Turn 2. Question answers in → their feedback, then the case

An answer is final once given; a later change request is noted in the log and the original
graded. If answers are missing, ask once; proceed if the learner says so.

1. **In one batch**: `python3 cme.py answer --work <work> --part questions` (the learner's
   message on standard input, exactly as written); read `<work>/sealed_questions.md` and
   `evidence_questions.md`; run `cme.py present --work <work> --block case` (the case file stays
   unopened). No evidence file → run the questions' verification list now (`grading.md`
   §1); with one, search only for what the answers raise.
2. **Marks before text**: in the **grading form** (`<work>/round.json`) mark every rubric element
   with the learner's words, and each MCQ (`grading.md` §2.1); then `cme.py draft --work <work> --part questions`.
3. **Send the questions' feedback** from the draft (`feedback_guide.md` §2: glossary line → reveal of these items →
   MCQs → focused questions; nothing that touches the case; it ends "The case follows."), and
   **straight after it the case**, exactly as printed.
4. **Behind the scenes, in one batch**: write `<work>/feedback_questions.md` (exactly as sent)
   and complete the form's scores and coding (`coding.md`), to be finished after the case.

- No case in the round → step 3's message is the final feedback: read `coding.md` (and `listening.md`)
  first, send it complete (gap summary and reflection prompt included, as `feedback.md`) and go to turn 4, step 4.
- A disputed grade → settle it briefly now (`disputes.md`), file the exchange with
  `answer --part notes`, and return to the case.
- The learner stops here or later (read each message first: a stop goes to `answer --part notes`,
  never in as an answer) → close the round without the case: turn 4's final feedback without it
  (gap summary, reading, Listening for the topics answered, reflection prompt), saved with the items
  answered. Say "the case is set aside unread and comes back in a later round" (never "sealed": rule 11).

### Turn 3. Stage 1 answer in → Stage 2 (unfolding cases)

1. **In one batch**: `cme.py answer --work <work> --part case` (the Stage 1 answer) and
   `cme.py present --work <work> --block bank`: only the results bank, no key, no diagnosis.
   Do not open `sealed_case.md`, `kit_case.md` or `evidence_case.md` until the final answers are in.
2. **Send Stage 2** without grading, comment, hint or reaction, assembled from the bank: the
   results of every test the learner ordered (normal, non-specific and abnormal alike); the
   tests its line "Add if not ordered" names, if not ordered, as "Results also available
   (ordered by the admitting team)"; the course; the Stage 2 questions. A test that is not in
   the bank gets a realistic result written on the spot, consistent with what the bank shows.
3. **Behind the scenes**: write `<work>/stage2.md`, the text exactly as sent.

### Turn 4. Final answers in → case feedback, first save

1. **In one batch** file the last answers (`answer --part final`, or `--part case` for a one-step
   case; it adds the case to the form) and read `sealed_case.md` and `evidence_case.md` now (with
   no evidence file, run the case's verification list); the round is no longer sealed.
2. **Mark the case's rubric** by stage, then `cme.py draft --work <work> --part case`; watch
   for transfer gaps and calibration across the whole round; code the case (`coding.md`, read now if
   not yet: no short questions, or `case_first`; `listening.md` too).
3. **Send the final feedback** from the draft (`feedback_guide.md` §2 part 2: glossary line → case
   reveal → case → gap summary for the whole round with mastery 0–5 per topic and the coding line
   → up to two reading pointers → with `listening.on`, an episode per topic (`listening.md`) → the reflection prompt).
4. **Behind the scenes, in one batch**: write `<work>/feedback.md` (exactly as sent); file change
   requests and anything else to log with `answer --part notes`; complete the form with the
   grading, `reading` and `listening` only (`save` fills in the rest, times included).
5. `python3 cme.py save --work <work>`, then publish every file in its `files` list in one
   write (`publishing.md`; `index.html` among them → `publishing.md` §5 once). Fix any `warnings`,
   or an `error` about a key header or a blank in the form, and run the same command again.
   A save that fails or says "update the plugin": never report it saved or retype a ledger (`store.md` §6).
6. End the turn: "Saved so far; your reflection completes the record."

### Turn 5. Reflection → final save, close

1. **Read the reflection** (comfort and performance 1–5, solid and shaky areas, reading minutes,
   `podcast_sources`); each shaky area becomes a precise gap on a blueprint ID. A disputed grade
   is resolved first (`disputes.md`: recorded whatever the outcome; sent without the
   reflection → ask for it, close when it arrives; never defend a grade by repeating it). "Record it
   as 4", "close that gap": `disputes.md` §1; "I know this, stop it": §2.
2. First `cme.py answer --work <work> --part reflection`: its **reflection form** says all this
   step needs. Then, in one batch, fill in `<work>/reflection.json` and write `<work>/B.md`
   (discussion verbatim, grade changes, coded analysis, errata from `errata_to_log`). Then
   `python3 cme.py close --work <work>`, which prints everything the close message needs.
3. **Close** in one message, sent before the store is written: what was saved (topics tested,
   score, session ID, the number of items due over the next few days, not their names; "1
   correction to an earlier session was added to your log" if errata were written); in one
   line how the reflection changed the plan, without dates per topic; when the next session
   fits the target frequency. `next_block` printed → add its `line` word for word; `time_hint`
   printed → add it as one line. `speed_settings_new` → `preparing.md` §5. `testing` →
   `requests.md` §2. Offer no reminders and start no other round unless asked.
4. **Behind the scenes**: publish the `files` that `close` printed; if that write fails, tell
   the learner at once. Then prepare the next round, saying nothing about it: `preparing.md`
   §2. If the discussion continues afterwards, append it (`session_log.md` §4) and publish.

## Boundaries

- Cases are fictional. Never request or store patient-identifiable information; if the learner
  pastes some, do not save it, and write `[removed: identifiable information]` in the log.
- Original items only: no copyrighted question banks or case records; paraphrase, quote briefly.
- Self-directed learning, not accredited CME. Content can contain errors; cite sources.
- Professional, collegial tone; specific and honest grading rather than flattery.

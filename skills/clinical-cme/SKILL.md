---
name: clinical-cme
description: "Blinded clinical self-assessment rounds for physicians: MCQs, focused questions (a mini-case with one free-text decision) and a full case, in the mix the learner chooses, with evidence-based feedback, reflection-informed spaced repetition, a full session log and periodic deep analysis of reasoning. The learner's ledger lives in a store they own (their own private artifact page where the app supports it, otherwise a folder or files they keep), so rounds work across devices and assistants. Use for 'quiz me', a CME round, CME setup/review, or finding or exporting past CME cases."
---

# Clinical CME — continuous clinical self-evaluation (version 4.2)

Each session is one short round, in the mix the learner chose (`config.mcqs`, `config.focused`,
`config.case`): single-best-answer questions (MCQs) and **focused questions** — a short case
ending in one free-text question on a single decision, graded on the reasoning — answered
first, on unrelated topics, then a full clinical case. All are graded together against current
evidence and followed by a one-minute reflection. Everything the learner builds up is kept in **one store of
their own** (`references/store.md`), holding:

- the **ledger** (`data/state.json`): schedule, gaps, coded results, settings. Read and written
  as a file, never retyped. It decides what comes back and when.
- the **log** (`data/sessions/S0042.json`): one document per round, verbatim (questions,
  answers, feedback, reflection, discussion, coded analysis).
- **review reports** (`data/reviews/<date>.json`) and an **index** for the learner's page.

Where the app supports it, the store is the learner's own private page, "Clinical CME", so a
round works on any device where they are signed in. The skill itself holds no learner data and
can be shared as it is.

## Principles

1. **Blind until answered.** Never reveal the topic, domain or reason for selection before
   every answer in the round is committed — not in text, headings, task items, tool-call
   descriptions, web searches **or your own reasoning** ("Sealed drafting" below).
2. **Realistic information, no cueing.** Cases give the history and routine work-up a ward team
   would have; specialised tests are requested by the learner. The short questions (MCQs, then
   focused questions) come first and are about other topics, so no item cues another.
3. **Teach in the feedback**, with verified, granular sources, so a busy clinician closes the gap
   within the session.
4. **Feedback → save → reflection → save.** The round is recorded right after the feedback
   (reflection pending), then updated when the reflection arrives. Nothing is lost if the
   learner walks away.
5. **Fast, and never at the cost of quality or record-keeping.** The learner should never wait
   for something that could happen while they read or think: draft the case while they answer
   the short questions, save while they read the feedback, batch independent tool calls in one go.
   Quality of items and feedback, and completeness of the log, are fixed; only waiting is cut.
6. **Respect the time budget** in `config.session_minutes`, including reading time.
7. **The log is verbatim and append-only.** Corrections are errata, never edits.
8. **Code every round** at grading time with the fixed vocabulary in
   `references/analysis_framework.md` §1.

## Tools: find capabilities, not names

This skill never relies on a tool's name: names differ between assistants, apps and versions.
Find each capability by what the session's tools do (their descriptions). If tools can be loaded
on demand (a tool-search facility), search **once**, early, with plain keywords for everything
below that you will need, and load them together. Only then conclude something is missing.

| Capability | Used for | If missing |
|---|---|---|
| Run Python 3 with a scratch folder | `cme.py`, every step | The skill cannot run here; say so in one line. |
| Reach the store file to file | reading and saving (`store.md` §2–3) | Another store kind (`store.md` §3); never copy the ledger through the chat. |
| Read one document from the page's database | the round mix set on the page (`cme/prefs`) | Skip it; the ledger's mix is used. |
| Web search and page fetch | verifying evidence before grading | Grade from knowledge, say so once in the feedback, and give sources you are sure of. |
| Send a message mid-turn and keep working | drafting and saving while the learner reads | Do the work first, then reply (the learner waits longer). |
| Ask structured multiple-choice questions | onboarding, review check-in | One compact message. |
| Current date and time | dating the round | `date` in the shell; else ask. |
| Scheduled tasks | optional reminders | Say reminders cannot be set from here. |
| Parallel helper agents | very large reviews | Work through batches yourself. |

Give every tool call a neutral description ("Read the ledger", "Plan today's items", "Prepare
today's round", "Save the round"). Run `python3 <skill>/scripts/cme.py <command> …` (standard
library only) in a scratch folder `<work>`; never write learner data into the skill's folder.

## Files in this skill

| Path | Read when |
|---|---|
| `references/store.md` | Every session start (first time in a session: §2–4), setup, migration, recovery, export |
| `references/case_design.md` | Before writing any case, MCQ or focused question (focused: §11) |
| `references/feedback_guide.md` | Before grading; contains the reflection prompt |
| `references/analysis_framework.md` | Before grading (§1 coding); for the deep review (§2) |
| `references/state_schema.md` | Round JSON, reflection JSON, ledger layout, spacing rules |
| `references/session_log.md` | Session-document layout, errata, search, teaching export |
| `references/onboarding.md` | First run, FAQ, settings |
| `references/progress_review.md` | When a review is due or requested |
| `scripts/cme.py` | Every session (start, save, close, stats, review …) |
| `templates/page.html` | The learner's page, published at setup |
| `templates/blueprint.json` | Default internal/hospital-medicine blueprint |
| `legacy/` | Version-3 scripts, used only by the version-3 migration |

## Session flow

The round runs over three to five learner turns (fewer without a case). What happens in each,
and what runs in parallel, is set so that the learner is only ever waiting for the next thing
they must read.

### Turn 1. Start, plan, questions out, case drafted

1. **In one parallel batch**: note the date and time; find and read the store (`store.md` §3–4:
   usually list artifacts → read `data/state.json`, `data/index.json` and `index.html` into
   `<work>/store/` in one call, and in the same batch the page's database document
   `cme/prefs`); read `references/case_design.md`. (Listing must precede reading the store
   when you do not yet know where it is; then batch the rest.) `cme/prefs` is a few bytes of
   settings with no content; if it does not exist or cannot be read, carry on without it.
   - No store found → ask once as in `store.md` §3. First-timers → setup
     (`references/onboarding.md`). Version 3 → migration (`store.md` §7). Database store with an
     app that can do files → move it (`store.md` §6) at the end of this round or now if the
     learner prefers.
2. `python3 cme.py start <work>/store/state.json --out <work>/plan.json` plus `--prefs '<the
   cme/prefs JSON>'` when it exists (add `--domain CODE`, `--mcqs N`, `--focused N`,
   `--no-case`, `--no-new` if the learner asked for this round, e.g. "just focused questions
   today" → `--mcqs 0 --no-case --focused 3`). It prints neutral status and plan counts, never
   topics. Route on it:
   - `onboarding_needed` → setup.
   - `review_due` → offer the progress review in one line (now, after today's round, or in a
     week); default to after the round. Mention that it includes the optional deep analysis.
   - `last_session.unreflected` → one neutral line: the last session was saved without its
     reflection and stays recorded that way (`save` finalises it).
   - `page_settings_applied` → the learner changed the mix on their page; say it in the opening
     line ("Using the mix you set on your page: …"), unless it only reports `unchanged`. `warnings` about page settings → one line,
     and the round goes ahead with the ledger's mix.
   - keep `next_id` and `pending_errata_count`.
3. Read `plan.json` (never paste it). If an item has no specific topic (`new_in_domain`), pick an
   untested topic from that blueprint domain in the sealed draft. Focused items carry an
   `aspect_hint` (`case_design.md` §11). A topic tested today is off
   the table unless the learner asks to repeat it. If an item carries a `drill`, build that item (the
   case, or a focused question in a round without one) to provoke that pattern
   (`case_design.md` §9, §11.5). Make every vignette and stem clearly different
   from `already_used` and `recent_cases_any_topic`. Use the plan's units and guideline region.
4. One opening line, for example "Today's round: two MCQs and a focused question, then one case,
   about 25 minutes. Last saved session: 25 Oct." (`estimated_minutes` from the plan is a
   guide.) Nothing about content. If `days_since_last_session` is
   long or they are behind target, at most add "Welcome back — N items are waiting; we'll
   start with the most overdue." Do not scold or enlarge the round.
5. **Sealed questions**: one file write, `<work>/sealed_questions.md` (description "Prepare
   today's round"): the MCQs with key and one-line rationale; the focused questions with their
   key, rubric, acceptable and unacceptable answers, `aspect` and `stem_summary`
   (`case_design.md` §11.3); their pre-flight lines (§8); and the exact text to present — MCQs
   first, then focused questions, numbered on — between `<!-- present: questions -->` and
   `<!-- /present -->`. With no case in the round, the verification list (step 7) goes here.
6. **Send the questions** (message 1), copied from the `present` block, ending with the answer
   prompt (`case_design.md` §11.4: letters for MCQs, a few lines with reasons for focused
   questions, optionally sure / unsure / guess) and, if there is a case, one line saying it
   follows once they are answered. Send it mid-turn if the session can, and go on:
7. **Sealed case, in the same parallel batch as reading** `references/feedback_guide.md` and
   `references/analysis_framework.md` (§1): one file write, `<work>/sealed_case.md`: the case
   (both stages if unfolding) with its diagnosis, the decisive tests and the two or three leading
   alternatives, the novelty check, the pre-flight table with yes/no and a fix per line, a
   **verification list** (the three to six precise searches you will run at grading: guideline
   names, years, trial names), and the exact text to present in `<!-- present: case -->` and,
   for unfolding cases, `<!-- present: stage2 -->` blocks. Fix pre-flight failures with an edit
   to the file, without restating content.
   No case in the round: skip the case file, and read the two references in this batch anyway.
8. End the turn with one short line ("Answer when ready."). If the session cannot send mid-turn,
   end the turn with the questions instead, and write the sealed case at the start of turn 2
   before sending it.

With `item_order` `case_first`: present the case first, the short questions after its Stage 1,
Stage 2 last; the drafting order follows. With no MCQs and no focused questions, start with the
case.

### Sealed drafting: keep the content out of your reasoning

From the moment you read `plan.json` until every answer is committed, your reasoning may be
shown to the learner as a summary. Keep it free of content:

- Refer to items only as "the case", "Q1", "Q2", "Q3", "Q4", "Stage 2"; checks by number
  ("pre-flight 1–13 pass"). Never write a diagnosis, differential, topic, domain, blueprint ID, finding, test,
  drug, answer letter or selection reason in reasoning.
- Do the clinical design **in the sealed files**, not in reasoning. Think in the file.
- Present each item by copying its `present` block. Between answers think only about
  logistics ("answers to the questions received; send the case").
- If content slips into your reasoning, do not repeat or comment on it; carry on.
- Once all answers are in, this rule ends: verify, grade and reason normally.

### Turns 2–3. Collect the answers

- Answers to the questions in → send the case (Stage 1), copied from its `present` block, with
  no comment on the answers. End with the answer-format prompt. No case in the round → go
  straight to turn 4.
- Stage 1 answer in (unfolding) → send Stage 2, without grading or comment.
- An answer (MCQ or focused) is final once given; a later change request is noted in the log
  and the original graded. If answers are missing, ask once; proceed if the learner says so. No hints,
  no reactions before the feedback.

### Turn 4. Verify, grade, feedback, first save

1. **Verify in parallel**: every search on the verification list, plus anything the answers
   raise, in one batch; then the primary sources you will cite, fetched in one batch
   (`feedback_guide.md` §1). Same checks as always; only the waiting is cut.
2. Grade against current guidance for the learner's region; watch for transfer gaps and
   calibration; code every item (ART steps and Revised-IDEA for the case; ART for the tested
   domains only for a focused question, `analysis_framework.md` §1.6; an error record for every
   missed or partial element and every wrong MCQ).
3. **Send the feedback** (one message, structured as in `feedback_guide.md` §2: reveal → MCQs →
   focused questions → case → gap summary with mastery 0–5 per topic and the coding line → up to two reading
   pointers → the reflection prompt). Send it mid-turn if the session can, so the save happens
   while the learner reads; otherwise save first and end the turn with the feedback.
4. **In one parallel batch**, write:
   - `<work>/feedback.md`: the feedback exactly as sent;
   - `<work>/answers.md`: the learner's answers verbatim, in blocks
     `<!-- answers: questions -->` (MCQs and focused questions), `<!-- answers: case -->`,
     `<!-- answers: final -->`
     (Stage 2 answers), each closed by `<!-- /answers -->`; an optional
     `<!-- answers: notes -->` block for answer-change requests or anything else to log;
   - `<work>/round.json` (`state_schema.md` §2): items with mastery, confidence and `coding`;
     gaps; resolved notes; key learning points; selection reasons; `log_id` = `next_id`;
     title, summary, tags; the compact `case` (only when there was one) and a `stem_summary`
     per MCQ and focused question, plus `aspect` per focused question; `grade_changes`,
     `drill`, `errata`, `pending_errata_logged`. **No `reflection` key.**
5. `python3 cme.py save <work>/store/state.json --round <work>/round.json --sealed
   <work>/sealed_questions.md <work>/sealed_case.md --answers <work>/answers.md --feedback
   <work>/feedback.md --index <work>/store/index.json --page <work>/store/index.html [--prefs
   '<same JSON as at start>'] --out-dir <work>/out1` (name only the sealed files that exist;
   `--page` only when `index.html` was read). It records the round, assembles the verbatim part
   A from the sealed `present` blocks, the answers and the feedback, and updates the index. Fix
   any `warnings` (missing coding, unknown vocabulary, missing blocks) and re-run into a fresh
   `--out-dir` from the unchanged inputs.
6. **Save**: put back every file in its `files` list, in one write where the store allows
   (`store.md` §4). Keep the new version. If `files` includes `index.html` (`page_upgraded`),
   the page is being updated to this version of the skill: follow `store.md` §4.6 once.
7. End the turn with one short line: "Saved so far; your reflection completes the record."

### Turn 5. Reflection, final save, close

- Parse comfort per topic (1–5), self-rated performance (1–5), solid / shaky areas, reading
  minutes. Turn each shaky area into a precise gap linked to a blueprint ID (`self_gaps`); if it
  belongs to an untested topic, that topic is created or brought forward. A disputed grade is
  resolved first (`feedback_guide.md` §7); keep every exchange verbatim for the Discussion
  section, and put the outcome in `grade_changes` (and the new score in `items`). "skip" →
  `{"skipped": true}`.
- **In one parallel batch**, write `<work>/reflection.json` (`state_schema.md` §3) and
  `<work>/B.md` (reflection verbatim, discussion verbatim, grade changes, coded analysis, errata
  from `errata_to_log`; layout in `session_log.md` §3).
- `python3 cme.py close <work>/out1/data/state.json --reflection <work>/reflection.json --md
  <work>/B.md --doc <work>/out1/data/sessions/<id>.json --index <work>/out1/data/index.json
  --out-dir <work>/out2` → save its `files` (database stores: update the session document from
  the `db_update` file instead of replacing it).
- **Close** in one message: what was saved (topics tested, score, session ID, number of items
  due over the next few days — not their names; plus "1 correction to an earlier session was
  added to your log" if errata were written); in one line how the reflection changed the plan,
  without dates per topic; when the next session fits the target frequency. Reminders follow
  `config.reminders` (chosen at setup; do not offer again unless asked). End the session; do
  not start another round unless asked.
- If the discussion continues afterwards, append it: write it to a file and run
  `cme.py addendum --doc <latest session file> --md <file> --out-dir <work>/out3`, then save.
- If `config.mirror` is `"gdrive"` and a drive tool can create documents, also create the
  session's Google Doc now (`store.md` §9). It is a copy; the store is the record.

## If a save cannot be made

A refused pinned write → re-read, re-run the same command, retry once. A tool or store error →
say so plainly, do not report the round as saved, and hand over the files from the last output
folder as downloads so the next session can save them (`store.md` §8). Never retype a ledger.

## Other requests

- **Settings** ("make sessions 30 minutes", "more perioperative medicine", "use kPa"): read the
  store → `cme.py settings <state> --config '{…}' --profile '{…}' --out <work>/s.json` →
  `cme.py place <work>/s.json --index <work>/store/index.json --out-dir <work>/outS` → save;
  confirm in one line. Emphasis is `profile.domain_emphasis`; a changed blueprint is
  `--blueprint <file>`.
- **Round mix** ("add a focused question to my rounds", "no more MCQs", "drop the case"):
  `settings --config '{"focused": 1}'` (or `mcqs`, `case`; at least one item stays) as above;
  confirm in one line with the new mix and a time estimate (3 min per MCQ, 5 per focused
  question, 10–15 for the case), and mention that the page's Settings tab has the same switches.
  For one round only, use the `start` options instead and leave the settings alone.
- **Reminders on or off**: create or delete a scheduled task (onboarding §4) and set
  `config.reminders`. If this session cannot schedule tasks, say so.
- **Progress review** ("how am I doing?", or when due): `references/progress_review.md`.
- **Finding past cases** ("find my cases on sepsis", "which sessions had anchoring?"): the index
  (`data/index.json`) has titles, tags, topics and dates; for words inside transcripts, read
  the session files into local files and search them. Answer with a short table (ID, date,
  title). Read-only.
- **Teaching export** ("turn S0042 into a teaching case"): `session_log.md` §6.
- **Open my log / show the page**: give the page's link; offer to pin it where the app can.
- **Move my data to files / to a folder**: `store.md` §6 or §3.
- **Mirror to Google Drive** ("keep copies in my Drive"): `store.md` §9.
- **Export everything** ("give me my data"): `store.md` §10.
- **FAQ or how it works**: `onboarding.md` §5, briefly.
- **A specific topic by name**: allowed, but not blind; say so in one line and proceed.

## Boundaries

- Cases are fictional. Never request or store patient-identifiable information; if the learner
  pastes some, do not save it, and write `[removed: identifiable information]` in the log.
- Generate original items. Do not reproduce copyrighted question banks or case records;
  paraphrase sources and keep quotations short.
- This is self-directed learning, not accredited CME. Content can contain errors; the feedback
  cites sources so the learner can verify.
- Professional, collegial tone; specific and honest grading rather than flattery.

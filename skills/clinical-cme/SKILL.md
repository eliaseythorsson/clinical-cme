---
name: clinical-cme
description: "Blinded clinical self-assessment rounds for physicians: MCQs, focused questions (a mini-case with one free-text decision) and a full case, in the mix the learner chooses, with evidence-based feedback, reflection-informed spaced repetition, a full session log and periodic deep analysis of reasoning. The learner's ledger lives in a store they own (their own private artifact page in the Claude app, otherwise a folder or files they keep), so rounds work across devices. Use for 'quiz me', a CME round, CME setup/review, or finding or exporting past CME cases."
---

# Clinical CME — continuous clinical self-evaluation (version 4.3.1)

Each session is one short round, in the mix the learner chose (`config.mcqs`, `config.focused`,
`config.case`), in this order:

1. the **short questions**, on unrelated topics: single-best-answer questions (MCQs) and
   **focused questions** (a short case ending in one free-text question on a single decision,
   graded on the reasoning);
2. **their feedback**, as soon as they are answered;
3. the **full clinical case**;
4. **its feedback**, with the gap summary for the whole round and a one-minute reflection.

Everything is graded against current evidence. Everything the learner builds up is kept in
**one store of their own** (`references/store.md`), holding:

- the **ledger** (`data/state.json`): schedule, gaps, coded results, settings. Read and written
  as a file, never retyped. It decides what comes back and when.
- the **log** (`data/sessions/S0042.json`): one document per round, verbatim (questions,
  answers, feedback, reflection, discussion, coded analysis).
- **review reports** (`data/reviews/<date>.json`) and an **index** for the learner's page.
- the **prepared round** (`data/prepared.json`): the next round, written and source-checked in
  full at the end of the last session (or by a scheduled task), so the next one has nothing to
  write or look up before the learner can start.

In the Claude app the store is the learner's own private page, "Clinical CME", so a
round works on any device where they are signed in. The skill itself holds no learner data and
can be shared as it is.

## Principles

1. **Blind until answered, part by part.** Never reveal a topic, domain or reason for selection
   before that part's answers are committed — not in text, headings, task items, tool-call
   descriptions, web searches **or your own reasoning** ("Sealed" below). The short questions
   are revealed with their feedback, once all of them are answered; the case stays sealed until
   its last answer.
2. **Realistic information, no cueing.** Cases give the history and routine work-up a ward team
   would have; specialised tests are requested by the learner. The short questions are about
   other topics than the case, so neither they nor their feedback cue it.
3. **Teach in the feedback**, with verified, granular sources, so a busy clinician closes the gap
   within the session.
4. **The learner never waits for something that could have been made ready.** At every moment
   they are reading, answering, or reading feedback, and the next thing they will need is
   already written or being prepared ("Speed" below). Quality of items and feedback, and
   completeness of the log, are fixed; only waiting is cut.
5. **Whoever grades did not write the items.** Where the session has helper agents, an author
   writes the round and you examine; you grade against the evidence, not against a key you
   wrote ("Roles" below).
6. **Final feedback → save → reflection → save.** The round is recorded right after the case
   feedback (reflection pending), then updated when the reflection arrives.
7. **Respect the time budget** in `config.session_minutes`, including reading time.
8. **The log is verbatim and append-only.** Corrections are errata, never edits.
9. **Code every round** at grading time with the fixed vocabulary in
   `references/analysis_framework.md` §1.

## Tools

The skill runs in the Claude app. If the session loads tools on demand, search **once**,
early, for everything below that you will need, and load it together.

| Tool | Used for | Without it |
|---|---|---|
| Python 3 in a shell with a scratch folder | `cme.py`, every step | The skill cannot run here; say so in one line. |
| Artifact tools that work file to file, or a folder | reading and saving the store (`store.md` §2–3) | Files the learner carries (`store.md` §3); never copy the ledger through the chat. |
| Read the page's settings document | the round mix set on the page (`cme/prefs`) | Skip it; the ledger's mix is used. |
| Web search and page fetch | verifying evidence before grading | Grade from knowledge, say so once in the feedback, and give sources you are sure of. |
| Send a message mid-turn and keep working | all behind-the-scenes work | "Without mid-turn messages" below (the learner waits longer). |
| Helper agents (ideally choosing their model, and in the background) | the author and the checker ("Roles") | You take that role yourself. |
| Structured multiple-choice questions | onboarding, review check-in | One compact message. |
| Current date and time | dating the round | `date` in the shell; else ask. |
| Scheduled tasks | optional reminders | Say reminders cannot be set from here. |

Give every tool call a neutral description ("Read the ledger", "Plan today's items", "Prepare
the round", "Check sources", "Save the round"). Run `python3 <skill>/scripts/cme.py
<command> …` (standard library only) in a scratch folder `<work>`; never write learner data
into the skill's folder.

## Files in this skill

| Path | Read when |
|---|---|
| `references/store.md` | Every session start (first time in a session: §2–4), setup, recovery, export |
| `references/feedback_guide.md` | Before grading; contains the reflection prompt |
| `references/analysis_framework.md` | Before grading (§1 coding); for the deep review (§2) |
| `references/author.md` | The author's brief. Read it, and `case_design.md`, only when you write items yourself |
| `references/case_design.md` | The standard for every item; read by whoever writes them |
| `references/evidence_check.md` | The checker's brief; also how you check evidence yourself |
| `references/state_schema.md` | Round JSON, reflection JSON, ledger layout, spacing rules |
| `references/session_log.md` | Session-document layout, errata, search, teaching export |
| `references/onboarding.md` | First run, FAQ, settings |
| `references/progress_review.md` | When a review is due or requested |
| `scripts/cme.py` | Every session (start, present, save, close, prepare, stash, stats, review …) |
| `templates/page.html` | The learner's page, published at setup |
| `templates/blueprint.json` | Default internal/hospital-medicine blueprint |

## Roles: who writes, who grades, who checks

With `helpers` true in the `start` output and a session that can start helper agents:

| Role | Who | Model | Does |
|---|---|---|---|
| **Author** | a helper agent | the most capable model the session offers, never below your own | writes the round: sealed questions, sealed case with its results bank, the notes for the feedback (`references/author.md`) |
| **Examiner** | you, in this conversation | the model the learner runs the round with | presents, grades against the evidence, writes all feedback, codes, records |
| **Checker** | a helper agent | a mid-tier model: one step below the most capable, not the smallest | verifies the evidence on the verification lists (`references/evidence_check.md`) |

- Depth goes where judgement is: writing items and grading answers. Looking up and reporting
  sources needs care, not depth, so the checker runs on a cheaper model. Mechanical steps
  (running `cme.py`, filing, saving) stay with you: a helper for them costs more than it saves.
- If the helper tool gives no choice of model, helpers use yours. If it offers only a smaller
  model than a role calls for, take that role yourself.
- You never read `case_design.md` or `author.md` while an author exists, and you open a sealed
  file only when its part's answers are in (the case's only when its final answers are in; for
  Stage 2 you print just its results bank with `present --block bank`). Until then you send text with `cme.py present`, which prints only what the
  learner is to see. What you have not read, you cannot leak.
- You are the second opinion on the author's keys. Grade what the learner wrote against the
  checked evidence; where a key is wrong, dated or too narrow, correct it in the feedback and
  credit the learner.

Starting a helper: a prompt that carries no content, and a neutral description.

> Author ("Prepare the round"): Follow `<skill>/references/author.md`. Plan: `<plan file>`.
> Write into: `<folder>`. Parts: `all`. Reply only "done".
>
> Checker ("Check sources"): Follow `<skill>/references/evidence_check.md`. List:
> `<folder>/sealed_questions.md`. Write: `<folder>/evidence_questions.md`. Reply only "done".
> (For the case: `sealed_case.md` → `evidence_case.md`.)

Run checkers in the background and do not wait for them. Wait for an author: its files are
needed next, and it only ever runs while the learner is busy or gone. When a helper reports,
repeat nothing of what it did. If one fails or is not done when its work is needed, do that
work yourself and never mention it.

**Without helpers** (`helpers` false, or no helper agents here) you are author, examiner and
checker: write the items yourself as `author.md` describes, in the sealed files and not in
your reasoning; check the evidence yourself, after each part's answers are in.

## Speed: what is made ready, and when

- **The whole round is prepared ahead.** After each close, the next round is planned and
  written in full — short questions, case Stage 1 with its results bank, and the notes for both
  feedbacks — its evidence is checked, and all of it is kept, packed, in the store. The next
  session reads the store and presents; it writes and looks up nothing before the learner
  starts, before the case appears, or before either feedback. A scheduled task can do the same
  preparation whenever no round is ready ("Prepare only" below).
- **Evidence is never looked up while the learner waits.** Searches would show the topic, so
  you may run them only after a part's answers are in. Checkers run them out of the
  conversation instead: when the round is prepared, or, for a round that was not, from the
  first minute of the session.
- **Send first, file afterwards.** When answers arrive, the only things that may come before
  your message are reading what you need and grading. Write no file for the log and run no
  save until the message is out: the learner reads while you file.
- **Behind-the-scenes work.** Each time you have sent the learner something to read or answer,
  keep working in the same turn on what is listed for that turn. Your turn must end before you
  can see their reply, so do only what is listed, batch independent tool calls in one go, and
  end the turn.

| The learner is… | Already written | Behind the scenes |
|---|---|---|
| answering the short questions | the questions, the case, both sets of notes, the checked evidence | nothing (checkers, only if the evidence is not there yet) |
| reading the questions' feedback, then working on the case | the case, its notes | you file what was sent |
| answering Stage 2 | the results bank it came from (the only part of the case you have read) | — |
| reading the case feedback | — | you save the round |
| reading the close | — | you save; the author writes the next round; checkers verify it; you stash it |

### Without mid-turn messages

If the session cannot send a message and keep working, nothing can happen behind the scenes
inside a turn: do each turn's listed work before its reply instead (the save before the final
feedback's reply ends), and prepare the next round before the close message only if the
learner agrees to the wait; otherwise skip it. Background checkers, where there are any, still
work across turns: start them just before the reply.

## Session flow

Five learner turns with an unfolding case; fewer with a one-step case or none.

### Turn 1. Start → questions out

1. **In one parallel batch**: note the date and time; find and read the store (`store.md` §3–4:
   usually list artifacts → read `data/state.json`, `data/index.json`, `data/prepared.json` and
   `index.html` into `<work>/store/` in one call, and in the same batch the page's settings
   document `cme/prefs`). (Listing must precede reading the store when you do not yet know
   where it is; then batch the rest.) `cme/prefs` is a few bytes of settings with no content;
   if it or `data/prepared.json` does not exist or cannot be read, carry on without it
   (`store.md` §4.1).
   - No store found → ask once as in `store.md` §3. First-timers → setup
     (`references/onboarding.md`).
2. `python3 cme.py start <work>/store/state.json --out <work>/plan.json --prepared
   <work>/store/prepared.json` plus `--prefs '<the cme/prefs JSON>'` when it exists (add
   `--domain CODE`, `--mcqs N`, `--focused N`, `--no-case`, `--no-new` if the learner asked for
   this round, e.g. "just focused questions today" → `--mcqs 0 --no-case --focused 3`). It
   prints neutral status and plan counts, never topics. Route on it:
   - `onboarding_needed` → setup.
   - `review_due` → offer the progress review in one line (now, after today's round, or in a
     week); default to after the round. Mention that it includes the optional deep analysis.
   - `last_session.unreflected` → one neutral line: the last session was saved without its
     reflection and stays recorded that way (`save` finalises it).
   - `page_settings_applied` → the learner changed the mix on their page; say it in the opening
     line ("Using the mix you set on your page: …"), unless it only reports `unchanged`.
     `warnings` about page settings → one line, and the round goes ahead with the ledger's mix.
   - keep `next_id`, `pending_errata_count`, `helpers`, `speed_settings_new`, `prepared`,
     `testing`, and `guideline_region` and `specialty`: every grade and every piece of feedback
     in the round uses that region's guidelines, pitched at that specialty.
   - "prepare only", or a scheduled task asking for it → "Prepare only" below, not a round.
3. **Get the first part's text.**
   - **`prepared.used` is true**: it is `present` in the `start` output, and the files listed
     in `prepared.ready` are already in `<work>`. Nothing to write.
   - **Otherwise, with an author**: start one (Plan `<work>/plan.json`, Write into `<work>`,
     Parts `questions`; `case` if the round has no short questions), wait, then
     `python3 cme.py present <work>/sealed_questions.md --block questions` (or
     `sealed_case.md --block case`).
   - **Otherwise, yourself**: read `author.md`, `case_design.md` and `plan.json` (never paste
     it) and write `<work>/sealed_questions.md` (`author.md` §3); its `present` block is the text.
4. **Send it** (message 1): one opening line, for example "Today's round: two MCQs and a
   focused question, then one case, about 25 minutes. Last saved session: 25 Oct."
   (`estimated_minutes` is a guide; nothing about content; if `days_since_last_session` is long
   or they are behind target, at most add "Welcome back — N items are waiting; we'll start with
   the most overdue", without scolding or enlarging the round), then the text exactly as
   printed. It already ends with its answer prompt.
5. **Behind the scenes**, in this order:
   1. Start a checker, in the background, for each sealed file in `<work>` that has no
      evidence file yet (`evidence_questions.md`, `evidence_case.md`; a prepared round
      usually brings both: see `prepared.ready`).
   2. In one batch read `references/feedback_guide.md` and `references/analysis_framework.md`
      (§1).
   3. Whatever of the round is not yet written (see `prepared.ready`; a case needs
      `sealed_case.md`, and both parts their kit): have the author write it (Parts `case`),
      wait, then start the case's checker; or write it yourself (`author.md` §3;
      `feedback_guide.md` §9), the case first.
6. End the turn with one short line ("Answer when ready.").

### Sealed: keep the content out of the conversation and out of your reasoning

Until the answers to a part are committed, your reasoning may be shown to the learner as a
summary. Keep it free of that part's content:

- Refer to items only as "the case", "Q1", "Q2", "Q3", "Q4", "Stage 2"; checks by number.
  Never write a diagnosis, differential, topic, domain, blueprint ID, finding, test, drug,
  answer letter or selection reason in reasoning.
- Do not open a sealed file, a kit, an evidence file or the plan before you need it (Roles).
  When you write items yourself, do the clinical design in the sealed files, not in reasoning.
- Present each part with the text `cme.py present` (or `start`) printed. Between answers think
  only about logistics ("answers to the questions received; send feedback and the case").
- If content slips into your reasoning, do not repeat or comment on it; carry on.
- The seal lifts part by part. Once the short questions are answered, grade and discuss them
  normally, while the case stays sealed: say nothing in their feedback, and think nothing, that
  touches the case. Once the case's last answer is in, the rule ends for this round.
- The **next** round, written after the close, is sealed from the start: with an author you
  never see it.

### Turn 2. Question answers in → their feedback, then the case

An answer (MCQ or focused) is final once given; a later change request is noted in the log and
the original graded. If answers are missing, ask once; proceed if the learner says so.

1. **In one batch**: read `<work>/sealed_questions.md`, `<work>/kit_questions.md` and
   `<work>/evidence_questions.md`, and run `cme.py present <work>/sealed_case.md --block case`.
   No evidence file → run the questions' verification list now (`evidence_check.md` §4: one
   batch of searches, one of fetches). Add a search only for something the answers raise that
   the list does not cover.
2. Grade and code the short questions against the evidence, using the key and the kit as the
   author's view (`feedback_guide.md` §2 part 1; `analysis_framework.md` §1).
3. **Send the questions' feedback** (reveal of these items → MCQs → focused questions; no gap
   summary and no reflection prompt yet; it ends "The case follows."), and **straight after it
   the case**, exactly as printed. Two messages one after the other, or one message with the
   case under a rule.
4. **Behind the scenes, in one batch**, write `<work>/feedback_questions.md` (the feedback
   exactly as sent), `<work>/answers.md` with the block `<!-- answers: questions -->` …
   `<!-- /answers -->` (the learner's answers verbatim), and `<work>/round.json` with the
   short-question items (`state_schema.md` §2), to be completed after the case.
5. End the turn with one short line.

No case in the round → this is the final feedback: send it complete (gap summary and reflection
prompt included, as one `feedback.md`) and go to turn 4, step 4.

If the learner disputes a short-question grade now, settle it briefly (`feedback_guide.md` §7),
keep the exchange for the log's notes, and return to the case. If they stop here ("no time for
the case"), close the round without it: send the gap summary and reflection prompt, and save
with the items answered; the case's topic stays due.

### Turn 3. Stage 1 answer in → Stage 2 (unfolding cases)

1. Run `python3 cme.py present <work>/sealed_case.md --block bank`. It prints only the results
   bank: no key, no diagnosis. Do not open `sealed_case.md`, `kit_case.md` or
   `evidence_case.md` until the final answers are in. (A case written before version 4.3.1 has
   no bank block: then, and only then, read `sealed_case.md`.)
2. **Send Stage 2** without grading or comment, assembled from the bank: the results of every
   test the learner ordered (realistic normal, non-specific and abnormal results alike); if they
   did not order the line "Add if not ordered" names, add those tests as "Results also
   available (ordered by the admitting team)"; the course; the Stage 2 questions. A test that
   is not in the bank gets a realistic result written on the spot, consistent with what the
   bank shows. No hints, no reactions.
3. **Behind the scenes, in one batch**: add the text as sent to `sealed_case.md` as a
   `<!-- present: stage2 -->` block (description "Update today's round") and append the
   `<!-- answers: case -->` block to `answers.md`.

### Turn 4. Final answers in → case feedback, first save

1. **Evidence**: in one batch read `sealed_case.md`, `kit_case.md` and `evidence_case.md` now; no file → run the case's verification list now. Add
   only what the answers raise. The round is no longer sealed: read `plan.json` too if you
   need anything from it.
2. Grade against current guidance for the learner's `guideline_region` and `specialty` (from
   `start`); watch for transfer gaps and
   calibration across the whole round; code the case (ART steps and Revised-IDEA; an error
   record for every missed or partial element).
3. **Send the final feedback** (`feedback_guide.md` §2 part 2: case reveal → case → gap summary
   for the whole round with mastery 0–5 per topic and the coding line → up to two reading
   pointers → the reflection prompt).
4. **Behind the scenes, in one parallel batch**, write:
   - `<work>/feedback.md`: the final feedback exactly as sent;
   - `<work>/answers.md` completed: blocks `<!-- answers: questions -->`,
     `<!-- answers: case -->`, `<!-- answers: final -->` (Stage 2 answers), each closed by
     `<!-- /answers -->`; an optional `<!-- answers: notes -->` block for answer-change
     requests, a dispute settled mid-round, or anything else to log;
   - `<work>/round.json` completed (`state_schema.md` §2): items with mastery, confidence and
     `coding` (and `retests`, the gap id from the key, on an item that tested an open gap); gaps; resolved notes; key learning points; selection reasons; `log_id` =
     `next_id`; title, summary, tags; the compact `case` (only when there was one) and a
     `stem_summary` per MCQ and focused question, plus `aspect` per focused question (all
     three are in the keys); `grade_changes`, `drill`, `errata`, `pending_errata_logged`.
     **No `reflection` key.**
5. `python3 cme.py save <work>/store/state.json --round <work>/round.json --sealed
   <work>/sealed_questions.md <work>/sealed_case.md --answers <work>/answers.md
   --feedback-questions <work>/feedback_questions.md --feedback <work>/feedback.md --index
   <work>/store/index.json --page <work>/store/index.html [--prefs '<same JSON as at start>']
   --out-dir <work>/out1` (name only the files that exist; `--page` only when `index.html` was
   read). It records the round, assembles the verbatim part A in the order of the round, and
   updates the index. Fix any `warnings` (missing coding, unknown vocabulary, missing blocks)
   and re-run into a fresh `--out-dir` from the unchanged inputs.
6. **Save**: put back every file in its `files` list, in one write where the store allows
   (`store.md` §4). Keep the new version. If `files` includes `index.html` (`page_upgraded`),
   the page is being updated to this version of the skill: follow `store.md` §4.5 once.
7. End the turn with one short line: "Saved so far; your reflection completes the record."

### Turn 5. Reflection → final save, close, next round prepared

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
  --out-dir <work>/out2`. This runs locally and prints everything the close message needs.
- **Close** in one message, sent before the store is written: what was saved (topics tested, score, session ID, number of items
  due over the next few days — not their names; plus "1 correction to an earlier session was
  added to your log" if errata were written); in one line how the reflection changed the plan,
  without dates per topic; when the next session fits the target frequency. Reminders follow
  `config.reminders` (chosen at setup; do not offer again unless asked). If `speed_settings_new`
  was true at the start, add once: "New: your next round is now written and source-checked in
  advance, by a separate author and checker, so it starts at once and feedback follows your
  answers directly. Say 'helpers off' or 'don't prepare ahead' to change that. I can also set
  up a nightly task that makes sure a round is always ready, even if you close the app early —
  say 'prepare my rounds overnight'." With `testing` true, end the close message with the
  testing check ("Testing mode" below). End the session; do not start another round unless asked.
- **Behind the scenes, after the close message**, first **save** the `files` that `close`
  printed. If that write fails, tell the learner at once (`store.md` §6); the close message is
  otherwise all they hear.
- Then **prepare the next round** (not for files the learner carries, and after the progress review instead if
  one follows now):
  1. `python3 cme.py prepare <work>/out2/data/state.json --out <work>/next/plan.json`
     (`mkdir -p <work>/next` first). If it prints `"prepare": false`, stop here.
  2. **Write**: start the author (Plan `<work>/next/plan.json`, Write into `<work>/next`,
     Parts `all`) and wait for "done". Do not read the plan or what it writes. Without an
     author, write the four files yourself as `author.md` describes (description "Prepare the
     next round").
  3. **Check**: start one checker per sealed file, together (`<work>/next/sealed_questions.md`
     → `<work>/next/evidence_questions.md`; `sealed_case.md` → `evidence_case.md`), and wait
     for both. Then `grep -h "^Keys contradicted" <work>/next/evidence_*.md`: it prints counts
     only. If any is above 0, start the author once more with Parts `revise` and wait. Without
     helpers, skip this step: the evidence is then checked at the session, after the answers.
  4. `python3 cme.py stash <work>/out2/data/state.json --plan <work>/next/plan.json --dir
     <work>/next --out-dir <work>/out3` → save its one file (`store.md` §4).
  Say nothing about it. If anything here fails, leave it: the next session writes or checks
  what is missing, as in turn 1.
- With `testing` true, last of all run the store check ("Testing mode" below).
- If the discussion continues afterwards, append it: write it to a file and run
  `cme.py addendum --doc <latest session file> --md <file> --out-dir <work>/out4`, then save.

### Testing mode

On while the skill is being tested (`config.testing`; "testing mode on/off" under Other requests).

- **Close message**: after everything else, a rule and four quick questions: "Testing check
  (about 30 seconds): 1. Waiting: fine / noticeable / annoying, and at which step? 2. The
  items, 1–5? 3. The feedback, 1–5? 4. Anything else, in a line?"
- **Store check**, behind the scenes after every save and the stash of this turn: read the
  store again as at the start, plus `data/sessions/<id>.json`, into `<work>/check/`; then
  `python3 cme.py verify --written <work>/out1 <work>/out2 [<work>/out3] --store
  <work>/check --out <work>/verify.json` (every output folder whose files were saved this
  round). `"ok": false` → tell the learner at once in one line which files did not save, and
  follow "If a save cannot be made".
- **The learner's answers** (their next message, any form; "skip" is fine): `python3 cme.py
  testing-note --session <id> --feedback '{"waiting": "…", "waiting_step": "…", "items": N,
  "feedback": N, "note": "…"}' --verify <work>/verify.json --out-dir <work>/outT` → save its
  one file. Reply "Noted, thanks." A dispute or comment on content in the same message is
  handled as discussion, as usual.

### Prepare only (a scheduled task, or "prepare my next round")

A session whose whole job is to make sure a round is ready. The learner is not there: ask
nothing, and never write anything about the round's content.

1. Read the store as in turn 1, step 1 (`state.json`, `index.json`, `prepared.json`).
2. `python3 cme.py prepare <work>/store/state.json --out <work>/next/plan.json --if-needed
   <work>/store/prepared.json --allow-unreflected`. `"prepare": false` → reply "A round is
   already prepared." (or the reason it gives) and stop.
3. Write, check and stash as in turn 5 (steps 2–4, with `<work>/store/state.json` as the
   ledger), and save the one file, pinned to the version you read. If the store changed in
   between, stop: a round is being played.
4. Reply in one line: "Next round prepared." Nothing else.

### Case first

With `item_order` `case_first`: present the case first, the short questions after its Stage 1,
Stage 2 last, and all feedback in one final message (`feedback.md` only). With no MCQs and no
focused questions, the case is the first part: turn 1 sends it, and turns 3–5 follow.

## If a save cannot be made

A refused pinned write → re-read, re-run the same command, retry once. A tool or store error →
say so plainly, do not report the round as saved, and hand over the files from the last output
folder as downloads so the next session can save them (`store.md` §6). Never retype a ledger.

## Other requests

- **Settings** ("make sessions 30 minutes", "more perioperative medicine", "use kPa"): read the
  store → `cme.py settings <state> --config '{…}' --profile '{…}' --out <work>/s.json` →
  `cme.py place <work>/s.json --index <work>/store/index.json --out-dir <work>/outS` → save;
  confirm in one line. Emphasis is `profile.domain_emphasis`; a changed blueprint is
  `--blueprint <file>`. Any settings change sets aside the prepared round; offer nothing, the
  next round is simply written at its start.
- **Region or specialty** ("use UK guidelines", "my specialty is geriatrics"): one `settings`
  call as above, `--config '{"guideline_region": "UK"}'` or `--profile '{"specialty":
  "Geriatrics"}'` (the learner's own words are fine; add `lab_units` or `blood_gas_units` only
  if they ask); confirm in one line from the `guideline_region` and `specialty` it prints.
  Both apply from the next round. A specialty outside the current blueprint also needs a
  blueprint for it: offer to draft one (`onboarding.md` §3) and pass it with `--blueprint`.
- **Round mix** ("add a focused question to my rounds", "no more MCQs", "drop the case"):
  `settings --config '{"focused": 1}'` (or `mcqs`, `case`; at least one item stays) as above;
  confirm in one line with the new mix and a time estimate (3 min per MCQ, 5 per focused
  question, 10–15 for the case), and mention that the page's Settings tab has the same switches.
  For one round only, use the `start` options instead and leave the settings alone.
- **Speed settings** ("helpers off", "don't prepare ahead", and back on): `settings --config
  '{"helpers": false}'` or `'{"prepare_ahead": false}'` as above. Without helpers you write,
  check and grade everything yourself (less usage; a short wait before each feedback; no
  separate author); without preparing ahead, each round is written at its start.
- **Always-ready rounds** ("prepare my rounds overnight", and off again): create (or delete) a
  scheduled task, daily at a quiet hour in the learner's time zone, with the prompt "Run the
  clinical-cme skill in prepare-only mode: make sure the next round is prepared. Do not show
  or describe its content." and set `settings --config '{"prepare_task": true}'` (or false).
  It covers the days when the end-of-session preparation did not finish — the app was closed
  early, or the reflection was skipped — and stops at once when a round is ready. If this
  session cannot schedule tasks, say so.
- **Testing mode on or off** ("testing mode on"): `settings --config '{"testing": true}'` (or
  false) as above; confirm in one line.
- **Reminders on or off**: create or delete a scheduled task (onboarding §4) and set
  `config.reminders`. If this session cannot schedule tasks, say so.
- **Progress review** ("how am I doing?", or when due): `references/progress_review.md`.
- **Finding past cases** ("find my cases on sepsis", "which sessions had anchoring?"): the index
  (`data/index.json`) has titles, tags, topics and dates; for words inside transcripts, read
  the session files into local files and search them. Answer with a short table (ID, date,
  title). Read-only.
- **Teaching export** ("turn S0042 into a teaching case"): `session_log.md` §6.
- **Open my log / show the page**: give the page's link; offer to pin it where the app can.
- **Move my data to a folder**: `store.md` §3 and §7.
- **Export everything** ("give me my data"): `store.md` §7.
- **FAQ or how it works**: `onboarding.md` §5, briefly.
- **A specific topic by name**: allowed, but not blind; say so in one line and proceed. Run
  `start` without `--prepared` for that round.

## Boundaries

- Cases are fictional. Never request or store patient-identifiable information; if the learner
  pastes some, do not save it, and write `[removed: identifiable information]` in the log.
- Generate original items. Do not reproduce copyrighted question banks or case records;
  paraphrase sources and keep quotations short.
- This is self-directed learning, not accredited CME. Content can contain errors; the feedback
  cites sources so the learner can verify.
- Professional, collegial tone; specific and honest grading rather than flattery.

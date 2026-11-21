# Preparing a round ahead

Read this when a round has just been closed (§2), when the session's whole job is to prepare a
round (§3), when the learner asks for rounds to be prepared overnight (§4), or when a session
starts and no prepared round could be used (§6).

Contents: 1. What is made ready, and when · 2. After the close · 3. Prepare only ·
4. Always-ready rounds · 5. Telling the learner once · 6. A round that was not prepared

## 1. What is made ready, and when

- **The whole round is prepared ahead.** After each close, the next round is planned and
  written in full — short questions, case Stage 1 with its results bank, and the notes for both
  feedbacks — its evidence is checked, and all of it is kept, packed, in the store
  (`state_schema.md` §8). The next session reads the store and presents; it writes and looks
  up nothing before the learner starts, before the case appears, or before either feedback.
- **Evidence is never looked up while the learner waits.** Searches would show the topic, so
  the examiner may run them only after a part's answers are in. Checkers run them out of the
  conversation instead: when the round is prepared, or, for a round that was not, from the
  first minute of the session.
- **The next round is sealed from the start.** With an author you never see it: do not read
  the plan, the sealed files, the kits or the evidence files in `<work>/next`.
- Quality of the items and completeness of the check are fixed; only the learner's waiting is
  cut. Nothing here is ever mentioned to the learner, apart from §5.

## 2. After the close

Run this behind the scenes after the close message is out and the files `close` printed are
saved. Skip it for a store of files the learner carries (`store.md` §4.3). If a progress review
follows the round now, run it after the review instead, from the ledger the review wrote
(`progress_review.md`, "After the review is saved").

1. **Plan**: `mkdir -p <work>/next`, then `python3 cme.py prepare <work>/out2/data/state.json
   --out <work>/next/plan.json`. If it prints `"prepare": false`, stop here.
2. **Write**: start the author (Plan `<work>/next/plan.json`, Write into `<work>/next`, Parts
   `all`; prompt as in SKILL.md, "Roles") and wait for "done". Do not read the plan or what it
   writes. Without an author, write the four files yourself as `author.md` describes
   (description "Prepare the next round").
3. **Check**: start one checker per sealed file, together (`<work>/next/sealed_questions.md` →
   `<work>/next/evidence_questions.md`; `sealed_case.md` → `evidence_case.md`), and wait for
   both. Without helpers, skip this step: the evidence is then checked at the session, after
   the answers.
4. **Finish**: `python3 cme.py finish-prepare <work>/out2/data/state.json --work <work>` (add
   `--no-evidence` when step 3 was skipped). It reads the checkers' counts, prints counts
   only, and stashes the round into `<work>/out3` when it is clean:
   - `"stashed": true` → save its one file (`store.md` §4).
   - `"revise": true` (a key is contradicted; nothing stashed yet) → start the author once
     more with Parts `revise`, wait, then run the command again with `--revised` and save.
   - an error naming an evidence file (missing, empty or unfinished) → start the checker for
     that file once more and run the command again; never pass `--no-evidence` to get past it.

Say nothing about any of it. If anything here still fails, leave it: the next session writes or
checks what is missing (SKILL.md, turn 1). With `testing` true, run the store check last of all
(`requests.md` §2).

If the session cannot send a message and keep working, prepare the next round before the close
message only if the learner agrees to the wait; otherwise skip it.

## 3. Prepare only (a scheduled task, or "prepare my next round")

A session whose whole job is to make sure a round is ready. The learner is not there: ask
nothing, and never write anything about the round's content.

1. Read the store as at the start of a round (SKILL.md, turn 1, step 1: `state.json`,
   `index.json`, `prepared.json`).
2. `python3 cme.py prepare <work>/store/state.json --out <work>/next/plan.json --if-needed
   <work>/store/prepared.json --allow-unreflected`. `"prepare": false` → reply "A round is
   already prepared." (or the reason it gives) and stop.
3. Write, check and finish as in §2, steps 2–4, with `<work>/store/state.json` as the ledger,
   and save the one file, pinned to the version you read. If the store changed in between,
   stop: a round is being played.
4. Reply in one line: "Next round prepared." Nothing else.

## 4. Always-ready rounds ("prepare my rounds overnight", and off again)

Create (or delete) a scheduled task, daily at a quiet hour in the learner's time zone, with the
prompt "Run the clinical-cme skill in prepare-only mode: make sure the next round is prepared.
Do not show or describe its content." and set `settings --config '{"prepare_task": true}'` (or
false; `requests.md` §1 for the `settings` call). It covers the days when the preparation after
the close did not finish — the app was closed early, or the reflection was skipped — and stops
at once when a round is ready. If this session cannot schedule tasks, say so.

## 5. Telling the learner once

If `speed_settings_new` was true in the `start` output, add once to the close message: "New:
your next round is now written and source-checked in advance, by a separate author and checker,
so it starts at once and feedback follows your answers directly. Say 'helpers off' or 'don't
prepare ahead' to change that. I can also set up a nightly task that makes sure a round is
always ready, even if you close the app early — say 'prepare my rounds overnight'."

## 6. A round that was not prepared

`prepared.used` is false in the `start` output (a first round, a changed mix or setting, a
one-off option, or a preparation that did not finish): the round is written at the session
from `<work>/plan.json`, the first part before the opening message and the rest while the
learner answers. If `prepared.ready` lists some files, only what is missing is written.

- **The first part, before anything is sent.** With an author: start one (Plan
  `<work>/plan.json`, Write into `<work>`, Parts `questions`; `case` if the round has no short
  questions), wait, then `python3 cme.py present <work>/sealed_questions.md --block questions`
  (or `sealed_case.md --block case`) prints the text to send. Without an author: read
  `author.md`, `case_design.md` and `plan.json` (never paste it) and write
  `<work>/sealed_questions.md` yourself (`author.md` §3), in the file and not in your
  reasoning; its `present` block is the text.
- **The rest, behind the scenes of turn 1**, after the checker for the first part is started:
  the case (`sealed_case.md`) and both kits. With an author: start it again (Parts `case`),
  wait, then start the case's checker in the background. Without: write them yourself
  (`author.md` §3; `feedback_guide.md` §9), the case first.
- **Evidence**: a checker is started in the background for every sealed file without an
  evidence file. Without helpers, the examiner runs each part's verification list only after
  that part's answers are in (`evidence_check.md` §4).

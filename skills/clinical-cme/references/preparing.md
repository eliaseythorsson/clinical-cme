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
  first minute of the session. A claim the checker's first pass did not reach is retried by
  other routes as part of preparation (`evidence_check.md` §3; step 4 below), so that the
  session is left with no list to run: at grading the examiner searches only for what the
  answers raise (`feedback_guide.md` §1).
- **The next round is sealed from the start.** With an author you never see it: do not read
  the plan, the sealed files, the kits or the evidence files in `<work>/next`.
- Quality of the items and completeness of the check are fixed; only the learner's waiting is
  cut. Nothing here is ever mentioned to the learner, apart from §5.

## 2. After the close

Run this behind the scenes after the close message is out and the files `close` printed are
published, in the same work folder: the next round is planned from the ledger as `close` left
it. Skip it for a store of files the learner carries (`store.md` §4.3). If a progress review
follows the round now, run it after the review instead (`progress_review.md`, "After the
review is saved"); the same commands then plan from the ledger the review wrote.

1. **Plan**: `python3 cme.py prepare --work <work>`. It writes `<work>/next/plan.json`. If it
   prints `"prepare": false`, stop here.
2. **Write**: start the author (Plan `<work>/next/plan.json`, Write into `<work>/next`, Parts
   `all`; prompt as in SKILL.md, "Roles") and wait for "done". Do not read the plan or what it
   writes. Without an author, write the four files yourself as `author.md` describes
   (description "Prepare the next round").
3. **Check**: start one checker per sealed file, together (`<work>/next/sealed_questions.md` →
   `<work>/next/evidence_questions.md`; `sealed_case.md` → `evidence_case.md`), and wait for
   both. Each also finds the listening candidates for its kit (`evidence_check.md` §6).
   Without helpers, skip this step: the evidence is then checked at the session, after the
   answers, and episodes are searched for after grading (`feedback_guide.md` §2 E2).
4. **Finish**: `python3 cme.py finish-prepare --work <work>` (add `--no-evidence` when step 3
   was skipped). It lints the round against the rulebook (`standards.md`, "The lint"), reads
   the checkers' counts (keys contradicted; claims and claims not verified, per file under
   `not_verified`), prints counts and the names of files, keys, fields and kit sections
   only, and, when the round is clean, packs it and adds `data/prepared.json` to the publish
   set:
   - `"stashed": true` → publish its `files` (`store.md` §4). `warnings` that begin "accepted
     after one revision" or "accepted after one retry" need nothing done.
   - `"recheck"` lists evidence files, or `"revise": true` (nothing stashed yet; its `next`
     line says the same) → one pass back, in this order, then the command again with
     `--revised`, which stashes whatever is still found, and publish:
     1. for each file in `recheck` (more than a third of its claims not verified, a claim
        given up with no other route tried, or listening candidates that are not three
        episodes in form), start its checker once more with the same prompt, together, and
        wait: it retries only those claims, by other routes, and completes the candidates;
     2. unless `next` names the checker alone: start the author once more with Parts
        `revise` and wait: it corrects a contradicted key and what the lint named, and
        carries what the retry confirmed into the kits.

     One pass only, never a second retry. Never open `<work>/next/lint.md`: it names content.
   - an error naming key headers or kits (the lint's blocking problems; nothing stashed) →
     start the author once more with Parts `headers` and the error's list of problems in its
     prompt (it names no content), wait, then run the command again. Without an author,
     correct them yourself (rules 8 and 9).
   - an error naming an evidence file (missing, empty, or without its `Checked:` or `Keys
     contradicted:` line) → start the checker for that file once more and run the command
     again; never pass `--no-evidence` to get past it.

Say nothing about any of it. If anything here still fails, leave it: the next session writes or
checks what is missing (SKILL.md, turn 1). With `testing` true, run the store check last of all
(`requests.md` §2).

If the session cannot send a message and keep working, prepare the next round before the close
message only if the learner agrees to the wait; otherwise skip it.

## 3. Prepare only (a scheduled task, or "prepare my next round")

A session whose whole job is to make sure a round is ready. The learner is not there: ask
nothing, and never write anything about the round's content.

1. Read the store as at the start of a round (SKILL.md, turn 1, step 1: `state.json`,
   `page.json`, `prepared.json`, and `cme/prefs` when it exists), then `python3 cme.py open
   --work <work> --store <work>/store --version <version read>` (plus `--prefs '<the cme/prefs
   JSON>'`, so the round is written for the mix and the paragraphs set on the page).
2. `python3 cme.py prepare --work <work> --if-needed --allow-unreflected`. `"prepare": false`
   → reply "A round is already prepared." (or the reason it gives) and stop.
3. Write, check and finish as in §2, steps 2–4, and publish the `files` (here the one file,
   `data/prepared.json`; with it the ledger and the page file when `prepare` took over a
   paragraph the learner wrote on the page), pinned to the version you read. If the store changed in between,
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

`prepared.used` is false in the `start` output (a first round, a changed mix, a setting that
changes the round (`state_schema.md` §8), a one-off option, or a preparation that did not finish): the round is written at the session
from `<work>/plan.json`, the first part before the opening message and the rest while the
learner answers. If `prepared.ready` lists some files, only what is missing is written.

- **The first part, before anything is sent.** With an author: start one (Plan
  `<work>/plan.json`, Write into `<work>`, Parts `questions`; `case` if the round has no short
  questions), wait, then `python3 cme.py present --work <work> --block questions` (or `--block
  case`) prints the text to send and notes that it went out. Without an author: read
  `author.md`, `standards.md`, `case_design.md` and `plan.json` (never paste it) and write
  `<work>/sealed_questions.md` yourself (`author.md` §3), in the file and not in your
  reasoning; its `present` block is the text.
- **The rest, behind the scenes of turn 1**, after the checker for the first part is started:
  the case (`sealed_case.md`) and both kits. With an author: start it again (Parts `case`),
  wait, then start the case's checker in the background. Without: write them yourself
  (`author.md` §3; `standards.md` rule 8), the case first.
- **Evidence**: a checker is started in the background for every sealed file without an
  evidence file. Without helpers, the examiner runs each part's verification list only after
  that part's answers are in (`evidence_check.md` §5).
- **Listening**: a checker fills in the candidates only when the kit is there when it
  starts; otherwise the examiner searches after grading (`feedback_guide.md` §2 E2).

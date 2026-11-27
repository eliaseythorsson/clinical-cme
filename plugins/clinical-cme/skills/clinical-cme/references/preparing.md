# Preparing a round ahead

Read this when a round has just been closed (§2). When the session's whole job is to prepare a
round, or the learner asks for rounds to be prepared overnight: `prepare_only.md`. When a
session starts and no prepared round could be used: `unprepared.md`.

Contents: 1. What is made ready, and when · 2. After the close · 3. Prepare only (in
`prepare_only.md`) · 4. Always-ready rounds (there too) · 5. Telling the learner once · 6. A
round that was not prepared (in `unprepared.md`)

## 1. What is made ready, and when

- **The whole round is prepared ahead.** After each close, the next round is planned and
  written in full — short questions, case Stage 1 with its results bank, and the finished text
  of both feedbacks (the kits' prepared blocks, `standards_kits.md` rule 8) — its evidence is
  checked, and all of it is kept, packed, in the store
  (`state_schema.md` §8). The next session reads the store and presents; it writes and looks
  up nothing before the learner starts, before the case appears, or before either feedback.
- **Evidence is never looked up while the learner waits.** Searches would show the topic, so
  the examiner may run them only after a part's answers are in. Checkers run them out of the
  conversation instead: when the round is prepared, or, for a round that was not, from the
  first minute of the session. A claim the checker's first pass did not reach is retried by
  other routes as part of preparation (`evidence_check.md` §3; step 4 below), so that the
  session is left with no list to run: at grading the examiner searches only for what the
  answers raise (`grading.md` §1).
- **The next round is sealed from the start.** With an author you never see it: do not read
  the plan, the sealed files, the kits or the evidence files in `<work>/next`.
- **Preparation takes longer than writing the items alone** (about twice the author's time,
  and more of the allowance): the feedback's text is most of it. That is accepted, because it
  happens after the close or overnight, never while the learner waits (ADR 0009).
- **Guideline tags are re-checked here too** (ADR 0011, ADR 0013): the guideline each decision
  point of the blueprint cites is a baseline. The default blueprint's tags are checked
  centrally, in the plugin's own repo, and arrive with plugin updates (the central records,
  `state_schema.md` §10); `prepare` reads them with the learner's own records, the newer per
  tag. Each preparation checks the tags the next round's items rest on when their newest record
  is older than 90 days, and sweeps only the tags the central records do not cover (the
  learner's own areas, another specialty's blueprint; every region reads a central set, one
  matching none reads International; all of them with `guideline_sweeps` `all`, none with `off`): a rolling share (about 1/12,
  never-checked first, then the oldest) and, when a progress review falls due within the gap
  between rounds (at least a week), every swept tag not checked within 30 days, filed after
  the round is stashed. On the default blueprint the lists are usually empty or a few tags.
  Lists hold at most 40 tags, one checker each.
- Quality of the items and completeness of the check are fixed; only the learner's waiting is
  cut. Nothing here is ever mentioned to the learner, apart from §5.

## 2. After the close

Run this behind the scenes after the close message is out and the files `close` printed are
published, in the same work folder: the next round is planned from the ledger as `close` left
it. Skip it for a store of files the learner carries (`publishing.md` §3). If a progress review
follows the round now, run it after the review instead (`progress_review.md`, "After the
review is saved"); the same commands then plan from the ledger the review wrote.

1. **Plan**: on a page store, first read `data/guidelines.json` into `<work>/store/` (the
   guideline tags' check records, not read at the start of a round; a store without it → none
   yet). Then `python3 cme.py prepare --work <work>`. It writes `<work>/next/plan.json` and, when
   guideline tags are due for a check, their lists (`tag_checks` in its output). If it prints
   `"prepare": false`, stop here.
2. **Write**: start the author (Plan `<work>/next/plan.json`, Write into `<work>/next`, Parts
   `all`; prompt as in SKILL.md, "Roles") and wait for "done". Do not read the plan or what it
   writes. Without an author, write the four files yourself as `author.md` describes
   (description "Prepare the next round").
3. **Check**: start one checker per sealed file, together (`<work>/next/sealed_questions.md` →
   `<work>/next/evidence_questions.md`; `sealed_case.md` → `evidence_case.md`), and wait for
   both. Each also finds the listening candidates for its kit (`evidence_check.md` §6). At the
   same time start one tag checker per entry of `tag_checks.checkers` and of
   `tag_checks.review_checkers` (its `list` → its `results`, `tag_check.md`). Wait for
   the evidence checkers and the `checkers` only: the review sweep is filed in step 5.
   Without helpers, skip this step: the evidence is then checked at the session, after the
   answers, and episodes are searched for after grading (`listening.md`).
4. **Finish**: `python3 cme.py finish-prepare --work <work>` (add `--no-evidence` when step 3
   was skipped). It lints the round against the rulebook (`standards.md`; the lint: `standards_lint.md`), reads
   the checkers' counts (keys contradicted; claims and claims not verified, per file under
   `not_verified`), prints counts and the names of files, keys, fields and kit sections
   only, and, when the round is clean, packs it and adds `data/prepared.json` to the publish
   set, with the tag checks filed (`data/guidelines.json` and the ledger; `tag_checks` counts
   them; results that are missing hold nothing up):
   - `"stashed": true` → publish its `files` (`publishing.md`). `warnings` that begin "accepted
     after one revision" or "accepted after one retry" need nothing done.
   - `"recheck"` lists evidence files, or `"revise": true` (nothing stashed yet; its `next`
     line says the same) → one pass back, in this order, then the command again with
     `--revised`, which stashes whatever is still found, and publish:
     1. for each file in `recheck` (more than a third of its claims not verified, a claim
        given up with no other route tried, or listening candidates that are not three
        episodes in form), start its checker once more with the same prompt, together, and
        wait: it retries only those claims, by other routes, and completes the candidates;
     2. unless `next` names the checker alone: start the author once more with Parts
        `revise` and wait: it corrects a contradicted key and what the lint named, carries
        what the retry confirmed into the kits, and cites the newer guideline where a tag the
        items rest on was found superseded (`tag_checks.items_changed`).

     One pass only, never a second retry. Never open `<work>/next/lint.md`: it names content.
   - an error naming key headers or kits (the lint's blocking problems; nothing stashed) →
     start the author once more with Parts `headers` and the error's list of problems in its
     prompt (it names no content), wait, then run the command again. Without an author,
     correct them yourself (rules 8 and 9).
   - an error naming an evidence file (missing, empty, or without its `Checked:` or `Keys
     contradicted:` line) → start the checker for that file once more and run the command
     again; never pass `--no-evidence` to get past it.
5. **The review sweep** (only when `tag_checks.review_checkers` was not empty): once the round's
   files are published, wait for those checkers, then `python3 cme.py tag-checks --work <work>`
   with `--results <file>` for each of their `results`, and publish its `files`. Results that
   are missing hold nothing up: those tags come due again.

Say nothing about any of it. If anything here still fails, leave it: the next session writes or
checks what is missing (SKILL.md, turn 1). With `testing` true, run the store check last of all
(`requests.md` §2).

If the session cannot send a message and keep working, prepare the next round before the close
message only if the learner agrees to the wait; otherwise skip it.

## 3. Prepare only (a scheduled task, or "prepare my next round")

A session whose whole job is to make sure a round is ready: `prepare_only.md` §1.

## 4. Always-ready rounds ("prepare my rounds overnight", and off again)

The scheduled task that prepares a round every night: `prepare_only.md` §2.

## 5. Telling the learner once

If `speed_settings_new` was true in the `start` output, add once to the close message: "New:
your next round is now written and source-checked in advance, by a separate author and checker,
so it starts at once and feedback follows your answers directly. Say 'helpers off' or 'don't
prepare ahead' to change that. I can also set up a nightly task that makes sure a round is
always ready, even if you close the app early — say 'prepare my rounds overnight'."

## 6. A round that was not prepared

`prepared.used` is false in the `start` output: the round is written at the session,
`unprepared.md`.

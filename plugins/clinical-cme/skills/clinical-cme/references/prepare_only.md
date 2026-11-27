# Prepare only, and always-ready rounds

Sessions with no round in them: the whole job is to make sure the next round is ready. The
steps of the preparation itself are those of `preparing.md` §2; what is made ready, and when, is
`preparing.md` §1.

## 1. Prepare only (a scheduled task, or "prepare my next round")

A session whose whole job is to make sure a round is ready. The learner is not there: ask
nothing, and never write anything about the round's content.

1. Read the store as at the start of a round (SKILL.md, turn 1, step 1: `state.json`,
   `page.json`, `prepared.json`, and `cme/prefs` when it exists) and `data/guidelines.json`,
   then `python3 cme.py open --work <work> --store <work>/store --version <version read>`
   (plus `--prefs '<the cme/prefs JSON>'`, so the round is written for the mix and the
   paragraphs set on the page). A scheduled task has no message from the learner: pass no
   `--today` and no `--utc-offset`; the job is dated by the offset the learner's rounds recorded (`state_schema.md` §1).
2. `python3 cme.py prepare --work <work> --if-needed --allow-unreflected`. `"prepare": false`
   → reply "A round is already prepared." (or the reason it gives) and stop.
3. Write, check and finish as in `preparing.md` §2, steps 2–5, and publish the `files` (`data/prepared.json`;
   with it the ledger and the page file when `prepare` took over a paragraph the learner wrote
   on the page or tag checks were filed, and then `data/guidelines.json`), pinned to the
   version you read. If the store changed in between, stop: a round is being played.
4. Reply in one line: "Next round prepared." Nothing else.

## 2. Always-ready rounds ("prepare my rounds overnight", and off again)

Create (or delete) a scheduled task, daily at a quiet hour in the learner's time zone, with the
prompt "Run the clinical-cme skill in prepare-only mode: make sure the next round is prepared.
Do not show or describe its content." and set `settings --config '{"prepare_task": true}'` (or
false; `requests.md` §1 for the `settings` call). It covers the days when the preparation after
the close did not finish — the app was closed early, or the reflection was skipped — and stops
at once when a round is ready. If this session cannot schedule tasks, say so.

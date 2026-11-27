# A round that was not prepared

Read at turn 1 when `prepared.used` is false; what is made ready ahead, and why, is
`preparing.md` §1.

`prepared.used` is false in the `start` output (a first round, a changed mix, a setting that
changes the round (`state_schema.md` §8), a one-off option, or a preparation that did not finish): the round is written at the session
from `<work>/plan.json`, the first part before the opening message and the rest while the
learner answers. If `prepared.ready` lists some files, only what is missing is written.

- **The first part, before anything is sent.** With an author: start one (Plan
  `<work>/plan.json`, Write into `<work>`, Parts `questions`; `case` if the round has no short
  questions), wait, then `python3 cme.py present --work <work> --block questions` (or `--block
  case`) prints the text to send and notes that it went out. Without an author: read
  `author.md`, what its §1 lists (the rulebook's files, `case_design.md`) and `plan.json`
  (never paste it) and write
  `<work>/sealed_questions.md` yourself (`author.md` §3), in the file and not in your
  reasoning; its `present` block is the text.
- **The rest, behind the scenes of turn 1**, after the checker for the first part is started:
  the case (`sealed_case.md`) and both kits. With an author: start it again (Parts `case`),
  wait, then start the case's checker in the background. Without: write them yourself
  (`author.md` §3; `standards_kits.md` rule 8), the case first. A kit not finished when its part's
  answers arrive is not waited for: the draft marks the blocks it lacks, and the examiner
  writes them (`grading.md` §2.3).
- **Evidence**: a checker is started in the background for every sealed file without an
  evidence file. Without helpers, the examiner runs each part's verification list only after
  that part's answers are in (`evidence_check.md` §5).
- **Listening**: a checker fills in the candidates only when the kit is there when it
  starts; otherwise the examiner searches after grading (`listening.md`).

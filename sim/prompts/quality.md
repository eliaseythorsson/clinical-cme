# Quality scorer brief (simulation)

A simulated CME round has just finished: an AI examiner wrote and presented questions and a
case to a physician (another agent), graded the answers and wrote feedback. You are a senior
clinician reviewing it afterwards. Rate the **clinical quality** of each item and of each
feedback message, 1 to 5. You took no part in the round, and nothing you write changes it.

Your scores are kept in the simulation's report so that runs can be compared over time. They
are a record, not a pass bar: score what you see, without rounding up or down to be kind or to
make a point.

## What to read

- The round as it went, in order: every file in `{messages}/` (`NNN-examiner.md`,
  `NNN-learner.md`). Message 001 is the request that started the round.
- What the examiner worked from, in `{work}/`: `sealed_questions.md` and `sealed_case.md` (the
  items with their keys), `kit_*.md` (feedback notes) and `evidence_*.md` (source checks), where
  they exist, and `round.json` (the grades given).
- Whose guidelines apply: `config.guideline_region` and `profile.specialty` in
  `{store}/data/state.json`. Judge accuracy against current guidance for that region and the
  pitch against that specialty.

If you have a web search tool, use it to check any claim you doubt against the primary source,
and say in the note that you checked. Without one, judge from what you know and say where you
are unsure.

## What to rate

The form at `{form}` lists what to rate. Fill in `score` (a whole number 1–5) and `note` (one
line, at most 200 characters, saying what decided the score) for every entry, and change
nothing else in it except as said below.

**Items** (`items`): each question or case as it was written, key included.

- Is the clinical content accurate and current? Is the keyed answer the best answer, and the
  only defensible one? For a case: is it realistic and coherent, do the results fit the
  diagnosis, does the key ask for what a good clinician would do?
- Is it pitched right for the specialty, and does it test a decision that matters?
- Does a stem, or the opening of the case, hand over the result of the decisive test when
  that test is one clinicians often forget to order (`{skill}/references/standards.md`,
  rule 7: such a result is requested by the learner, or the question asks for the test)? If
  so, lower the item's score and name the item under `concerns`, starting the line "Rule 7:".
- An entry marked `"answered": false` is a case the learner did not answer. Rate it as written
  if it was presented (it is in the messages); if it never was, leave its `score` as `null`.

**Feedback** (`feedback`): each feedback message as it was sent.

- Is every clinical claim correct, current and attributed to the right source?
- Is each grade fair to what the learner actually wrote: nothing right marked wrong, nothing
  wrong let through?
- Does it teach the point the decision turns on?
- `dispute`, when listed: the examiner's replies to the learner's challenge. Did it re-check
  the source and argue from it? Did it concede what the learner had right, and hold what the
  evidence supports, without merely repeating the grade?

| Score | Meaning |
|---|---|
| 5 | Accurate, current and well pitched; you would use it unchanged to teach a colleague. |
| 4 | Sound; a quibble that would mislead nobody. |
| 3 | Usable, with a flaw a specialist would notice: an ambiguous stem, a second defensible answer, a dated detail, a grade a little off. |
| 2 | A clinically significant error, or feedback that would leave the learner with a wrong idea. |
| 1 | Wrong or unsafe. |

Then fill in `overall` (one score and one line for the round as a whole), set `scorer_model`
to the name of the model you are, and list under `concerns` (at most ten one-line strings)
anything a clinician should look at: a claim you believe is wrong, a key you would dispute, a
grade that should change. An empty list is a fine answer.

## Rules

- Write to `{form}` only. Do not edit, move or delete any other file.
- Read nothing under `{run}` beyond the files named above.
- Notes are one line each and quote no more than a few words of the round: the report holds
  scores, not transcripts.
- When the form is complete, reply to the session with the single word `scored`.

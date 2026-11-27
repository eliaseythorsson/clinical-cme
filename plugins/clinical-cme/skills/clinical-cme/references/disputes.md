# If the learner disputes a grade, sets a score or stops a topic

Read when the learner disputes a grade or a teaching point, sets a score or closes a gap, says
"stop bringing it back", or when `answer` prints `positions` for an item.

## Disputes

Re-check the point against the primary source. If the learner is right, or the evidence
supports both positions, say so plainly, correct the model answer and adjust the score
before recording. If the original grading stands, explain why with the specific source.
Never defend a grade by repeating it.

The whole debate goes into the log verbatim (Discussion section), and every dispute settled
goes into `grade_changes` in the reflection JSON, one entry each, whatever the outcome (with
the new score in `items` when it changed):
`{"item": "Q2", "topic": "CARD-03", "from": 2, "to": 4, "outcome": "learner_right"}`.
Use `both_defensible` or `upheld` as appropriate; an upheld grade is recorded too, with `from`
equal to `to`. A challenge to a teaching point rather than a mark ("correct it in the record")
is a dispute as well: the item's score as `from` and `to`, the outcome saying who was right,
and the corrected point in the Discussion. If the dispute changes the coding, code the final
position.

A dispute that arrives without the reflection: settle it in that reply, end it by asking for
the reflection, and close only when the reflection (or "skip") arrives; never close on the
dispute message as if it were the reflection. The review reports dispute outcomes honestly; a learner who is often
right is telling you something about the grading.

## 1. A score the learner sets, a gap the learner closes

"Record it as 4" or "close that gap" is not a dispute (and "I know this, stop bringing it
back" is one step that does both and more: §2): the learner is not arguing the
evidence, they are deciding what their record says. It is their record, so do it, without
arguing and without changing your grading. Never write it as a dispute outcome (your
grading did not change), and never edit the ledger by hand.

- **Before the close**, in the reflection JSON (`state_schema.md` §3):
  `"learner_scores": [{"item": "Q2", "type": "mcq", "topic": "CARD-03", "score": 4, "note": "the learner's words"}]`
  and `"learner_closed_gaps": [{"gap": "G0007", "note": "…"}]` (a gap by its id, or
  `{"topic": "CARD-03"}` for one this round opened).
- **After the close** (also in a later conversation, after reading the store with the
  session's document and `open`): `python3 cme.py override --work <work> --scores '[…]'
  --close-gaps '[…]'` with the same entries (`--session <id>` for a round other than the
  last), then publish its `files`.

What the engine does with it: the item keeps both scores, `graded` (yours) and `mastery`
(the learner's, marked `set_by: learner`); the topic is scheduled with the learner's score,
exactly as it would be either side of the close (`state_schema.md` §3.1), and the round's score follows it; the change is a `grade_changes` entry with outcome
`learner_set`. A gap closed this way moves to `resolved` marked `closed_by: learner` and
gets **no retest**; the topic still comes back when its score says so. The session document
gets a "Set by the learner" section naming both scores and who closed the gap, so the log
does not depend on what you write in part B. A learner-set score does not close the gap on
that point: it stays open unless the learner asks for that too (say so in one line). The
review counts these apart from disputes.

If the learner gives a reason that is about the evidence ("the guideline says otherwise"),
it is a dispute: re-check first, and use this path only if they still want their own score
after your grading stands.

## 2. The learner's stop: "I know this, stop bringing it back"

Said in any words (also "stop this loop", "I disagree with the premise, drop it"), it is one
action with one entry, the same before or after the close: the learner's score for the item
(5 unless they name one), every open gap on that topic closed by the learner, and the topic
scheduled at the longest interval (90 days by default), whatever drill-down or gaps would have
said. The learner's judgement decides: do it at once, without arguing, and do not ask them to
choose between a score and a gap. No topic is retired for good: after the interval it comes
back like any other.

- **Before the close**, in the reflection JSON: `"learner_stops": [{"item": "Q2", "type":
  "mcq", "topic": "CARD-03", "score": 5, "position": {"point": "…", "text": "…"}}]` (`score`
  and `position` optional).
- **After the close**: `python3 cme.py override --work <work> --stops '[…]'` with the same
  entries, then publish its `files`.

**The position note.** If the learner says what they disagree with, keep it as `position`:
`point` names the one decision point in a few words, `text` is what they hold, in their own
words, unedited. It is not a note on the whole topic. From then on, every round on the topic
respects it (`standards_positions.md` rule 12): no item turns on that point, and you never mark the
learner down on it. When `answer` prints `positions` for an item, grade with them: an answer
that follows the note is not a miss, gets no gap and no error code on that point, and the
feedback does not reopen it.

- You may say what the evidence says **once**, at the moment the note is set: one line, with
  the source ("Noted. For the record, ESC 2023 recommends X; your position is kept."). Then
  never again on that point.
- Only if the evidence file for a later item says that guidance on that exact point has
  changed since the note's date (and the note has no `reopened`) may you raise it once more,
  in one line with the source; then run `cme.py position --work <work> --reopened <id>`.
- The learner can take a note back at any time ("drop my position on …"): `cme.py position
  --work <work> --drop <id>` (alone, `position` lists the notes in force). Each progress review
  lists the notes to keep or drop (`progress_review.md`); a note not kept at a review lapses
  after about six months.

The session document gets the stop and the note word for word in its "Set by the learner"
section. The review counts stops apart from disputes and from other learner-set scores.

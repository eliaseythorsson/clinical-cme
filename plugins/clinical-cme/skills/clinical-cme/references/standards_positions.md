# Rule 12. The learner's position notes

A rule of the rulebook (`standards.md`), kept in its own file because the checkers read it too.

A **position note** is what the learner holds on one decision point of a topic, in their own
words, kept when they stopped the topic ("I know this, stop bringing it back";
`disputes.md` §2). It covers that one point, not the topic. The plan gives an item
`positions` (`notes`: `id`, `point`, `text`, `set`, and `reopened` once it has been raised
again) when the learner holds one on its topic; `answer` gives the examiner the same notes by
key id.

1. **No item is keyed on the disputed point.** The author writes the item on another decision
   point of the topic, and no distractor, rubric element or model answer turns on the premise
   the learner rejects. Where the point cannot be avoided in a case, the key accepts the
   learner's position as a defensible answer.
2. **The learner is never marked down on it**, and the feedback does not argue the point
   again: the examiner's side is `disputes.md` §2 and `grading.md` §2.1.
3. **The evidence is said once**, when the note is set (`disputes.md` §2), unless
   guidance on that exact point has changed since the note's `set` date (4).
4. **A changed guideline is raised once.** For an item with a note that has no `reopened`, the
   author puts one line on the verification list: has guidance on the note's point changed
   since its `set` date? If the checker finds it has, the examiner may raise it once more, in
   one line with the source, and records that it did (`cme.py position --reopened <id>`).

The note ends when the learner takes it back (any time), when the progress review drops it
(each review lists the notes in force, one line each: keep or drop), or on its own after about
six months without being kept at a review. Nothing here names the note's machinery to the
learner (rule 11): it is "the position you hold on …".

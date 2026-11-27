# Small references, each read whole by the turn that needs it

Every round, every learner paid for about 300,000 characters of reference text across the
examiner, the author and two checkers (#92): a pointer such as "`store.md` §4" or "rule 2 of
`standards.md`" loads the whole file, so the checkers read the 31 KB rulebook for two rules and
the examiner read the 52 KB feedback brief, disputes and coding included, before any answer.
Decided with the learner on 2026-11-27.

References are now small files, each read whole, by the role and turn that needs it, and
`SKILL.md`'s table says when. Large files were split, the text moved and not rewritten: the
examiner's brief into `grading.md` (procedure) and `feedback_guide.md` (what the feedback says,
its rules on sources and which parts are written live, which the author reads too), with `coding.md`, `disputes.md`, `evidence_depth.md` and
`listening.md` read only when the round calls for them; `store.md` §4 into `publishing.md`; the
tag check out of `evidence_check.md`; rules 2, 8 (its Listening section apart) and 12 and the lint out of
`standards.md` into `standards_*.md` files, so a checker reads its rules alone; the author's
pass back, the drills, prepare-only sessions and an unprepared round into their own files.

One home per rule still holds (ADR 0007): the rulebook keeps every rule's heading, and a moved
part leaves a one-line pointer where it was. `state_schema.md` is never read whole in a round.
This narrows ADR 0009's "the examiner reads one brief" to two files read before grading.

Measured in `docs/reading-load.md`: a typical round reads 35% less reference text (302,080 →
196,148 characters), short of the 40% aimed at once every role is sent to all it cites; a
checker 46% less, the author 32%, the examiner 28%. A test checks that every rule a brief cites
is in a file its role is told to read.

# Reading load: reference text each role reads, per turn (#92)

Every learner pays for the reference text the skill reads in every round. This table counts it
per role and turn, before and after #92, in characters (Python `len` of the file as UTF-8 text).

**How it is counted.** A pointer to a section of a file loads the whole file: a role reads a
reference with one file read, so "`store.md` §4" cost all of `store.md`. Hence the rule since
#92: a reference is a small file read whole by the turn that needs it, and a large one is split
rather than pointed into. `SKILL.md` (20,070 before, 21,076 after) is loaded with the skill in
every round and is not counted below; nor are the round's own files (sealed files, kits,
evidence files, draft) or the forms `cme.py` prints. Before: commit `04ae136` (#91 with its review
fixes, the state merged here; #94 alongside). After: this branch.

| Role and turn | Before: files read | Chars | After: files read | Chars | Change |
|---|---|---:|---|---:|---:|
| Examiner, turn 1 (behind the scenes) | `feedback_guide.md`, `store.md` | 69,548 | `grading.md`, `feedback_guide.md`, `publishing.md` | 35,397 | −49% |
| Examiner, turn 2 (behind the scenes) | – (all in `feedback_guide.md`) | 0 | `coding.md`, `listening.md` (with `listening.on`, the default) | 12,367 | – |
| Examiner, turns 3 and 4 | – | 0 | – | 0 | – |
| Examiner, turn 5 and after the close | `session_log.md`, `preparing.md` | 20,577 | `session_log.md`, `preparing.md` | 17,138 | −17% |
| Examiner, only when needed: a `depth` above 1; a dispute, a learner-set score, a stop or `positions` | – (all in `feedback_guide.md`) | 0 | `evidence_depth.md` (5,312), `disputes.md` (6,274) | 11,586 | – |
| Author (one per round) | `author.md`, `standards.md`, `case_design.md`, `feedback_guide.md` | 118,445 | `author.md`, `standards.md` with `standards_region.md`, `standards_kits.md`, `standards_listening.md`, `standards_positions.md`, `case_design.md`, `feedback_guide.md` (with the rules on sources, §3, and what is written live, §7) | 80,682 | −32% |
| Author, only when needed: a `depth` in the plan; a drill; `keys` finds something; a pass back | – | 0 | `evidence_depth.md` 5,312; `drills.md` 2,241; `standards_lint.md` 3,071; `author_revise.md` 2,507 | – | – |
| Checker (each; two per round) | `evidence_check.md`, `standards.md` | 46,755 | `evidence_check.md`, `standards_region.md` (rule 2), `standards_kits.md` (rule 8), `standards_listening.md`, `standards_positions.md` (rule 12) | 25,282 | −46% |
| Tag checker (each, while preparing and at a review) | `evidence_check.md`, `standards.md` | 46,755 | `evidence_check.md`, `tag_check.md`, `standards_region.md` | 18,709 | −60% |
| Prepare-only session (the assistant's part) | `preparing.md`, `store.md` | 30,609 | `prepare_only.md`, `preparing.md`, `publishing.md` | 17,922 | −41% |
| Progress review (the assistant's part) | `progress_review.md`, `analysis_framework.md`, `feedback_guide.md` (for the coding), `store.md` | 91,727 | `progress_review.md`, `analysis_framework.md`, `coding.md`, `publishing.md` | 39,831 | −57% |

## A typical round: examiner, author and two checkers

| | Examiner | Author | Checkers (2) | Total | Change |
|---|---:|---:|---:|---:|---:|
| Before | 90,125 | 118,445 | 93,510 | 302,080 | |
| After, typical (listening on, no item beyond depth 1, no dispute) | 64,902 | 80,682 | 50,564 | 196,148 | **−35.1%** |
| After, with a `depth` above 1 for examiner and author and a dispute | 76,488 | 85,994 | 50,564 | 213,046 | −29.5% |

The issue's target (at least 40% less) is not reached: a review of the first cut found the
author and the checkers sent to rules they were no longer told to read, and the counts above
include them (the checker reads rules 8 and 12, now in their own files; the rules on sources
and the list of live parts the author needs moved from `grading.md` into `feedback_guide.md` §3
and §7, so the author does not read `grading.md`). `tests/test_standards.py` checks that every rule a brief cites is in a file its role
reads.

Tag checkers come on top when tags are due (each −60%). A round written at the session
(`unprepared.md`, 2,068) has the same author and checkers, started during the round.

## Where the text went (moved, not rewritten)

| Before | After |
|---|---|
| `feedback_guide.md` §1 (verify), §6 (reflection prompt), §8 (log), §9 (prepared and live text) | `grading.md` §1, §3, §4, §2; the rules on sources (never invent, paraphrase) and the list of live parts in `feedback_guide.md` §3 and §7 |
| `feedback_guide.md` §1 (whose guidance), §2–5, §10 | `feedback_guide.md` §1, §2–5, §6 (rules 5.3, 10, 11 at §6.1–6.3) |
| `feedback_guide.md` §2 E2, §4.1, §7, §11 | `listening.md`, `evidence_depth.md`, `disputes.md`, `coding.md` (pointers left at §2 E2 and §4.1) |
| `feedback_guide.md` §11.4 and the `stats` paragraph of §11.6 (review only) | `analysis_framework.md` §1.1–1.2 |
| `store.md` §4 (reading and writing, every job) | `publishing.md` (a pointer left at `store.md` §4) |
| `evidence_check.md` §7 (tag checks) | `tag_check.md` |
| `standards.md` rule 2; rule 8 (its Listening section apart); rule 12; "The lint" | `standards_region.md`; `standards_kits.md` and `standards_listening.md`; `standards_positions.md`; `standards_lint.md` (each heading kept in `standards.md` with a pointer) |
| `author.md` §2, Parts `headers` and `revise` | `author_revise.md` |
| `case_design.md` §9 (drills) | `drills.md` (a pointer left at §9) |
| `preparing.md` §3–4, §6 | `prepare_only.md` §1–2, `unprepared.md` (pointers left) |

`state_schema.md` (118 KB) is never read whole in a round: `SKILL.md` names the section, and
the forms `cme.py` prints say what a step needs. `tests/test_skill_docs.py` checks that every
"`file.md` §N" pointer into the split files names a section that exists.

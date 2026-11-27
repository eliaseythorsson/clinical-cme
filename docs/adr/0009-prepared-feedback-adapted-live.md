# Feedback is assembled from prepared, checked text and adapted live to the answer

In round S0035 the learner waited two minutes for the short questions' feedback and could not
tell whether a rubric lay under the grading. Writing every briefing after the answers arrive is
slow, and the learner never saw the marks the grading rested on. Decided with the learner on
2026-11-26 (#49), built in #78 together with #77.

**Written ahead**, by the author when the round is prepared, and checked by the checker: the
feedback's finished text, not an outline, in the kits' **prepared blocks** (rule 8): per rubric
element of a focused question and of the case a full briefing for *missed*, a shorter one for
*partial*, two or three lines for *hit*; the model answer; each MCQ's distractors and its two
versions (wrong or unsure, right and sure); the decisive point and the tempting wrong turn; the
differential and pearls; the deeper evidence for an item with an evidence depth beyond the first.

**Written live**, by the examiner once the answers are in: the marks; the opening in the
learner's own words; verdicts, calibration, transfer and the coding; credit for a defensible
answer outside the key and corrections to the key; the glossary line and the reading and
listening picks.

## Rules

1. **The rubric is shown every time.** Each focused question and the case opens with its rubric
   as a short list: the element, the mark, and the learner's words that earned it.
2. **Marks before text.** The examiner marks every element, each tied to a quote, in the grading
   form before any prepared text is used. `cme.py draft` refuses while a mark is blank, and only
   then puts together the blocks the marks call for. The examiner may rewrite or drop any block.
3. **The log says what was adapted**: `save` compares the draft with the feedback as sent and
   records in the session document which blocks were used as prepared, changed or left out.
   Nothing of this appears in the feedback or the ledger.
4. **Tailoring always wins over speed.** About 30 seconds to feedback is the target for a typical
   answer; an answer outside the key gets the time it needs.
5. **Preparation may take longer** (about double the author's time, and more of the allowance);
   it happens after the close or overnight, never while the learner waits.

## Considered options

- **All live (as before)**: honest but slow, and the most variable in quality from round to round.
- **All prepared, pasted by mark**: fast, but grading would drift towards the text on hand, and
  answers outside the key would be taught as misses. Rejected: the examiner's independence from
  the author (SKILL.md, "Roles") is the point of having two roles.
- **Prepared blocks chosen by marks made first, every block open to change (chosen)**: the marks
  are made against the evidence and the answer alone; the text follows them.

## Consequences

- The examiner reads one brief, `feedback_guide.md` (#77): verifying, marking, the draft, the
  feedback's structure, the rules that bind it (formerly rules 5.3, 10 and 11, now pointers),
  the coding (formerly `analysis_framework.md` §1), the reflection prompt and disputes. It no
  longer reads the rulebook before grading, and it reads the draft instead of the kits.
- The checker checks the claims the blocks state: each verification-list line names its blocks,
  and the evidence file's `Blocks:` line lets the draft flag a block whose claim is not
  confirmed.
- A round prepared before this has no blocks: the draft marks what is missing and the examiner
  writes it, as before. A kit not finished when the answers arrive (a round written during the
  session) is handled the same way.
- Measured: the wait from answers to feedback (the round's clock), the learner's rating in
  testing mode, and the simulation's quality score as a breakage check; the share of blocks
  changed or left out is in each session document.
- Bytes the examiner is told to read before grading: before, 83,025 (`standards.md` 28,168,
  `feedback_guide.md` 30,759, `analysis_framework.md` §1 11,131, `store.md` §4 6,925,
  `session_log.md` §3 1,484, the grading form's guide 4,558); after, about 63,500 (the brief
  50,180, the form's guide about 4,900, `store.md` §4 and `session_log.md` §3 as before). The
  examiner then reads the draft instead of the kits.

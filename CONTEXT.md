# clinical-cme

Blinded clinical self-assessment for practising physicians: short rounds of questions and a case,
graded against current evidence, with a schedule that brings weak topics back.

## Rounds and items

**Round**:
One session of assessment: the short questions, their feedback, the case, its feedback, and a reflection.
_Avoid_: quiz, session (when meaning the content)

**Short question**:
An MCQ or a focused question; asked before the case, on topics unrelated to it.

**Focused question**:
A mini-case ending in one free-text question on a single decision, graded on the reasoning.

**Case**:
The full clinical case of a round, usually unfolding in two stages.
_Avoid_: vignette, scenario

**Results bank**:
The prepared results of tests the learner may order in Stage 1 of a case.

**Prepared round**:
A whole round written and source-checked in advance and stored packed in the learner's store.

## People and roles

**Learner**:
The physician taking the rounds.
_Avoid_: user, student

**Author**:
Whoever writes a round's items, keys and feedback notes.

**Examiner**:
The assistant in the conversation: presents, grades against the evidence and writes feedback; never the author of the items it grades.
_Avoid_: judge, grader

**Checker**:
Whoever verifies a round's sources against its verification lists.

## Record

**Store**:
The place the learner owns that holds all their data: their own artifact page, or a folder.

**Ledger**:
The learner's schedule, gaps, coded results and settings (`state.json`).
_Avoid_: state (in conversation with the learner)

**Log**:
The verbatim, append-only record of every round, one session document each.

**Gap**:
A specific point the learner got wrong or flagged as shaky, linked to a blueprint topic, open until an item tests that point and it is answered well.

## Curriculum

**Blueprint**:
The list of domains and topics the curriculum covers.

**Domain**:
A blueprint grouping such as cardiology or gastroenterology.

**Topic**:
One blueprint entry within a domain; the unit that is scheduled.

**Block**:
A run of rounds (default 12) with one domain as its theme; most new material and the case come from the theme.
_Avoid_: module, month

**Theme**:
The domain of the current block. It is visible to the learner; topics stay blind.

**Drill-down**:
Successive rounds probing deeper into one sub-topic after wrong answers; capped, and only within the theme.

## Development

**Testing mode**:
A learner setting that adds a short feedback check and a store-integrity check at the end of each round.

**Simulation**:
A scripted run of the skill in which one agent is the examiner and another plays a learner persona.

**Persona**:
The kind of learner an agent plays in a simulation (strong; weak and overconfident; disputes a grade; stops halfway).

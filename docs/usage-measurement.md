# Usage measurement, 2026-11-27 (issues #92, #93, #94)

Simulated rounds (`sim/`), examiner and learner on Claude Opus 5.5, first round of a new learner,
no prepared round and **no helper agents** (the simulation's examiner writes, checks and grades
itself). Reports: `sim/reports/2026-11-27-strong-4` (Full), `-strong-5` (Economy),
`-weak-overconfident-4` (Economy). The Full weak-overconfident run was stopped (a permission
prompt blocked it) and is not counted.

| | Full (strong) | Economy (strong) | Economy (weak) |
|---|---|---|---|
| Round | 2 MCQ + 1 focused + case | same (a first round has the case) | same |
| Web searches + page fetches | 11 + 7 = 18 | 5 + 6 = 11 | 5 + 9 = 14 |
| Other tool calls | 38 | 41 | ~40 |
| Reference text read (characters, self-reported) | ~130 000 | ~138 000 | ~130 000 |
| Examiner context after turn 1 (tokens) | 131 039 | 139 930 | 139 285 |
| All checks (blinding, saved, log, standards, listening, prepared) | pass | pass | pass |
| Quality means (items / feedback) | 4.5 / 4.5 | 4.0 / 4.5 | 4.5 / 4.5 |

What this shows and what it does not:

- **Measured:** Economy cuts web lookups by about a third for the same round. Reference reading is
  about the same in both modes and about 35% below 7.0 (`docs/reading-load.md`, #92).
- **Not measurable here:** the main Economy savings. In the Claude app, Full has a helper author on
  the most capable model reading about 80 000 characters of briefs and writing the round, and
  separate checkers; Economy runs the author on the examiner's model. Every other Economy round
  has no case (a round without the case is roughly half a round with one). Podcast searches are
  off in Economy (the sims above found few to verify in either mode).
- **Per-turn token totals** could not be recorded reliably: the relay only sees an agent's token
  figure when its turn ends in the background, so `simulate.py --tokens` got the first turn only.
  A real-app measurement (the learner's own usage page before and after a round) is the better
  number and should replace this table when available.

# Move round procedure from SKILL.md into cme.py

The 4.3 protocol asks the model to assemble files by hand across turns (answers, `round.json`, a ~10-flag `save`, the Stage 2 log), which is where the confirmed bugs and blinding leaks come from, and it cannot be unit-tested. Version 5 moves every mechanical step into `cme.py` commands working on a fixed work-folder layout, with the core (scheduling, planning, applying a round) as pure functions under unit test. SKILL.md keeps only judgement: writing, presenting, grading, feedback. Target: SKILL.md of about 250 lines.

## Consequences

Incremental patching of 4.3 was rejected: each hand-assembled step is a fresh source of leaks. Fixes that cannot wait (date shift, Stage 2 leak) go into 4.3.1 first.

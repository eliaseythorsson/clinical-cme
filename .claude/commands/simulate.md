---
description: Run one simulated CME round (examiner agent + learner persona) and write a report
argument-hint: "[persona, default strong]"
---

Run a simulation of the clinical-cme skill for the persona `$ARGUMENTS` (default `strong`).
Follow `sim/README.md`, section "Procedure", step by step. After every agent turn, pass the
token usage the tool reported for it (`next --tokens N`, `quality --tokens N`; the examiner's
helpers with `--helper-tokens role=N` if it reported them); leave a figure out when none was shown.
A ledger preset goes in with `init --config`, e.g. `--config '{"usage": "economy"}'`.

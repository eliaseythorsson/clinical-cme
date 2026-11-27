# Author: a pass back on a written round

Read by the author started with `Parts: headers` or `Parts: revise` (`author.md` §2), after
`cme.py finish-prepare` sent the round back. The rules for an author agent (`author.md`) hold;
the rules a correction must meet are in the rulebook (`standards.md`).

- `Parts: headers`: the round is written and `cme.py finish-prepare` refused it for its key
  headers or its kits (the lint's blocking problems, `standards_lint.md`). The
  problems are listed in your prompt by file, key, field and kit section. Correct those
  headers (rule 9), kit sections and prepared blocks (rule 8) and run the check of `author.md` §4 until it prints
  `"ok": true`. Change nothing else.
- `Parts: revise`: the round is written and `cme.py finish-prepare` printed `"revise": true`:
  a key is contradicted, or the lint made a judgement call, or both; or the checker retried
  claims it had not verified, and the kits are to take up what it confirmed. Change nothing
  but what these name, and leave the evidence files as they are: the round is stashed after
  your "done", whatever the lint still finds.
  - Read `evidence_questions.md` and `evidence_case.md` in the output folder, where they
    exist. Wherever a **Note** says a key is contradicted by current guidance, correct the
    item so that it has one best answer under that guidance: the key, the kit, and the stem or
    options if they no longer work, keeping the `present` block complete. Replace every
    `(verify)` in the kits' notes that the check confirmed with the confirmed figure and
    source, and correct every prepared block that a claim marked changed, regional difference
    or not verified names under **Blocks:** (state a claim not verified qualitatively).
    The candidates under `## Listening` are the checker's: leave them as they are.
  - Read the tag results (`tag_results_<n>.md`) in the output folder, if there are any. Where a tag an item's decision
    point rests on is marked `superseded` (or `changed`), make the key, the kit and the
    verification list cite the newer guideline (or the change) and correct any block that
    rests on the old edition (rule 2.4). Leave the file as it is.
  - Read `lint.md` in the output folder, if there is one. For each line decide whether the
    rule it names is broken (rule 5: an abbreviation not spelled out at first use; rule 6:
    more than one time anchor) and correct the presented text where it is. A finding that is
    wrong is left alone.

# One numbered rulebook for writing items, with a lint at preparation

Every rule for writing items (blinding, guideline region, units, pitch, abbreviations, time anchors, what a kit holds, key headers) was restated in five or six briefs (SKILL.md, author.md, case_design.md, evidence_check.md, feedback_guide.md, preparing.md), so each new rule from testing meant parallel edits that drift. The rules now live once, numbered, in `references/standards.md`; the author, checker and examiner briefs cite rule numbers. The key-header table is generated from, or checked against, `cme.py`'s `KEY_*` definitions.

`finish-prepare` lints a prepared round while nobody waits. Definite problems (a missing kit section, a malformed key header) block the stash. Judgement calls (an abbreviation that looks undefined, timings that look mixed) go back to the author for one revision, then are accepted with a warning, so a round is never left unprepared over a heuristic.

Rules are what makes any item good and are the same for every learner. What differs per learner (their level and aim in their own words, region, specialty, round mix) is settings, kept in the ledger and changeable on the page; the rulebook has one rule saying how items are pitched to them.

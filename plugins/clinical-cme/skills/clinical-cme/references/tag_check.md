# Tag check: is the cited guideline still the one to cite?

The brief of the **tag checker**, started with this file's path, one tag list
(`tag_checks_<n>.md` or `review_checks_<n>.md`, at most 40 tags) and its output path (the same
name with `results` for `checks`): it follows the rules for a checker agent of
`evidence_check.md` (its first section, and the routes of its §3) and this file; nothing else
there applies.

Each decision point of the learner's blueprint ends with the guideline it rests on, in brackets
(`[ESC ACS 2023]`). These **tags** are a baseline: `cme.py prepare` lists the ones due for a
check (the tags the next round's items rest on, and a share of the tags the learner's install
sweeps, oldest first; before a progress review, every swept tag not checked within 30 days), in
lists of at most 40, one tag checker per list, all started together. The default blueprint's
tags are checked centrally instead, by the same brief: the maintainer's job
(`cme.py central-checks`, run monthly in the plugin's repo) writes lists per region set
(`<set>_checks_<n>.md` → `<set>_results_<n>.md`) and ships the results with the plugin. Your
list's first lines give the guideline region (for a central list, the set's names) and
specialty. A tag check is not an evidence check:
it asks only about the edition and the appropriateness of the source, never about a claim.

For each tag on the list, one question: **is there a newer edition, or a more appropriate
guideline for the learner's region and specialty (rule 2, `standards_region.md`), than the one
tagged?** "More appropriate" means the body rule 2.1 names first for the region, never simply
a newer guideline from another region.

1. **Search**, all tags in one parallel batch: the society's or body's own guideline list page
   (the route of `evidence_check.md` §3 for a guideline recommendation), then PubMed for the guideline's title and
   "update" or "focused update".
2. **Fetch** only where a search result does not settle it, all in one batch.
3. **Decide**:
   - **current**: the tagged edition is the latest and the right body for the region;
   - **changed**: the same guideline was revised in place (a focused update, a corrigendum, a
     new version of the same document under the same name) in a way that may matter; say what;
   - **superseded**: a newer edition, or a more appropriate guideline for the region, replaces it:
     name it as a tag in the same form (body, short title, year), e.g. `ESC ACS 2026`;
   - **uncertain**: a successor is announced, in consultation, or adopted but not yet in force,
     or what you found does not settle it; say what is pending.

Write the output file once, one line per tag on the list, in the list's order, and nothing else
that the script reads:

```
Tag: <tag exactly as listed> | current|changed|superseded|uncertain | <the newer tag, or -> | <source link> | <one-line note>
```

A `superseded` line without its newer tag is not read. Never invent an edition, a year or a
link: a tag you could not settle is `uncertain`, with what you found. `cme.py finish-prepare` (or
`tag-checks --results` at a review; `central-checks --results` for a central list) files the lines: each tag counts as checked today, a
superseded tag is cited as its successor from then on (the learner's blueprint itself is never
rewritten), and the teaching earlier rounds based on a changed or superseded tag is queued for
the review's guideline-change check (`analysis_framework.md` §2.3), which raises an erratum only
where that teaching actually differs. A tag missing from the file simply comes due again.

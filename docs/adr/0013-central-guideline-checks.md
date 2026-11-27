# The default blueprint's guideline tags are checked centrally, not per learner

ADR 0011 made every learner's install keep the default blueprint's 391 guideline tags current
itself: a rolling sweep of ceil(N/12) at each preparation and a sweep of every tag not checked
within 30 days before each review. Whether `ESC ACS 2023` is still the edition to cite for a
region is the same answer for every learner on the default blueprint, so every install paid for
the same web searches; for a learner without a Max plan that is a real share of their usage.
Decided with the learner on 2026-11-27 (issue #91), before the public marketplace. Amends ADR 0011.

- **Central records, per region set.** `templates/guideline_checks.json` (kind
  `guideline_checks_central`) holds one set of tag check records per supported region:
  **International** and **Europe** to start, each with `regions` (its names and aliases),
  `updated` and `records` in the shape of a learner's (ADR 0011). Both started from the #90 seed.
  The two sets are kept apart because "a more appropriate guideline for the region" can differ.
  Both are seeded from the same Europe-based records (the #82 and #89 passes checked the European
  societies' editions the default blueprint cites); from the first central run on, the
  International set's checker weighs the European and US societies (`standards.md` rule 2.1).
- **Region families.** A learner's `guideline_region` (free text) reads a set when it is one of
  the set's `regions` (case and spacing ignored), or when it is written `<country>/<family>` and
  the family names a set: "Iceland/Europe" (the old default, listed as an alias too) and
  "Norway/Europe" read Europe. Every answer setup offers reads a set: "UK" and "United Kingdom"
  are aliases of Europe; "North America", "US", "USA", "United States" and "Canada" of
  International; a European country is written `<country>/Europe` at setup. The central set says
  only whether a cited edition is current; each round's evidence check still keys and grades
  against the learner's own national guidance. The country's own national guidance is then not checked
  centrally; a learner who wants it sets `guideline_sweeps` to `all`. Any other region ("Japan",
  "Brazil") reads International (`CENTRAL_FALLBACK`; decided by the orchestrator for token cost):
  the central record only says whether a cited edition is current, and the round's own evidence
  check still grades against the learner's national guidance, so per-learner sweeps of the
  default blueprint's tags happen only with `all`. Hence no learner's store is seeded: on the
  default blueprint every region reads central records, and a blueprint of their own has none
  to seed from. A new set
  is added to the file, with its aliases, when a region gains enough learners to be worth it.
- **Which tags are covered.** A tag of the learner's blueprint is covered when it is cited on a
  sub-topic that cites it in the shipped default blueprint too (same sub-topic id, same tag), or
  is the successor of a covered tag down the set's chain. Unchanged default content is covered,
  also in a ledger whose copy of the blueprint is older than the template, as long as the tag is
  the same; the learner's own areas (new ids), other specialties' blueprints and a tag an edited
  sub-topic added are not. Matching by the tag alone was rejected: a tag shared by another
  specialty's blueprint answers a different "more appropriate for this specialty" question.
  Matching whole decision points was rejected: an older ledger copy (e.g. before #82 corrected a
  point's wording) would lose coverage for points whose tag did not change.
- **Newer of the two.** At plan time (and for `stats`, `tag-checks`, the review's queue) a tag's
  record is the newer, by `last_checked`, of the central record and the learner's own; on a tie
  the learner's. The learner's `data/guidelines.json` holds only the checks their install made:
  central records are never copied into it, so a plugin update with newer checks is never hidden
  by an older learner file, and nothing has to be merged into the store. Superseded tags overlay
  the plan as before.
- **What a learner's install checks** (`config.guideline_sweeps`, declared in `DEFAULT_CONFIG`;
  older ledgers get the default at the load step; content-neutral): `custom` (default) sweeps
  only the tags not covered, rolling and before a review, with the quota a share of those;
  `all` is #90 as it was (every tag, read with the central records, so centrally fresh tags are
  not due); `off` sweeps nothing. Whatever the setting, the tags of the round's own items are
  checked when the newest record is older than 90 days: rare for covered tags once the central
  job runs. A new learner needs no warm-up: the shipped records are current.
- **The review's queue** (`teaching_to_recheck`) is derived from the same merged records, so a
  tag found superseded centrally queues the teaching of the learner's earlier rounds on it for
  the review's guideline-change check, as a learner's own finding does.
- **The maintainer's job.** `cme.py central-checks` works on the template (or `--file`): alone it
  summarises and validates; `--list DIR` writes the tags due (not checked within 90 days,
  never-checked first, then the oldest; all of them, or ceil(N/`--share`) per set) in lists of
  at most 40 per set; `--results` files the checkers' `Tag:` lines into the set the file is named
  for (only the tags its list asked; others are reported as `not_listed`), validates and writes; `--validate` refuses a file that cannot ship. A monthly scheduled
  cloud session follows `docs/maintaining-guidelines.md` and commits the template to `main`
  after the tests pass; since `plugin.json` has no version, the commit reaches installs on the
  next update. **Spreading**: the monthly run passes `--share 3` (at most 131 tags per set). The
  seed dated every record 2026-11-27, so without it about 780 checks would fall due together
  around 2027-02-26; a third a month makes each run the same size and checks each tag about
  every three months (the 90-day rule then holds within a month's slack). It is a command of `cme.py` rather than a repo script, so it reuses the parser,
  the filing and the validation the learner's install uses (one implementation); it needs no
  work folder and touches no ledger.

Considered: shipping a "last swept" date and letting installs sweep only when it is old
(rejected: still per learner, and stale only if the job stops, which `custom` covers through the
items' 90-day check); writing the central records into each learner's file at update (rejected:
a write to every store, and a merge that could go wrong both ways). Accepted costs: about 300
checks per region set per quarter in the repo (spread monthly); a learner outside the sets'
regions gets International's edition verdicts unless they choose `all`, which then costs as #90.

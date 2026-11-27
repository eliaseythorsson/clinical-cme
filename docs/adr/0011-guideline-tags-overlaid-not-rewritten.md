# Guideline tags are checked at preparation and overlaid, never rewritten into the blueprint

The default blueprint gives each decision point the guideline it rests on (`[ESC ACS 2023]`). Those
tags were checked once during development (#82, #89); guidelines keep changing, so they are a
baseline that has to be kept current. Decided with the learner on 2026-11-27 (issue #90, its
"Agreed schema"; #89 is absorbed by it).

- **The unit is the distinct tag**, not the decision point: one check of `ESC ACS 2023` covers
  every point that cites it. A bracket that cites two guidelines (`[GOLD 2027; ERS/ATS COPD
  exacerbations 2017]`) holds two tags, since each has its own edition (391 in the default
  blueprint; the issue's 403 counted brackets).
- **One record per tag, in a store file of its own** (`data/guidelines.json`: tag, last_checked,
  status, superseded_by, source, note; the sweep's share; the region checked for), so that the
  ledger does not grow and the start of a round does not read it. The ledger keeps only the
  file's generation (`guidelines_gen`), so that a job that did not read the file never
  publishes over it (it skips the tag checks instead).
- **Checked only while the next round is prepared**: the items' tags unless checked within 90
  days, plus a rolling sweep of ceil(N/12) (configurable to 1/16) of the tags not checked within
  90 days, never-checked first, then the oldest. When a review falls due within the learner's
  gap between rounds (at least 7 days ahead, so a review two or three days off is not missed),
  every other tag not checked within 30 days, listed apart and filed after the round is stashed:
  the stash never waits for it. Missing results hold nothing up: the tags come due again.
- **Separate tag checkers.** The issue's sketch had the evidence checker do the tag checks too.
  They are separate checkers instead, one per list of at most 40 tags (a first review sweep of
  about 300 tags is eight lists of 37 or 38), started beside the evidence checkers: the evidence
  check stays the same size and within its three minutes, and the lists run side by side.
  `finish-prepare` reads the round's results files, `tag-checks --results` the review sweep's.
- **Overlay, not rewrite.** A superseded tag stays in the learner's copy of the blueprint; the
  record replaces it (down the chain of supersessions) where the engine hands decision points to
  the author, the plan written by `prepare`. Rewriting the blueprint would change the ledger's
  content generation (setting the prepared round aside), alter a blueprint the learner may have
  set themselves, and make a wrong verdict hard to take back; an overlay is undone by the next
  check. An item's tag found superseded in the same preparation sends the author back once
  (`revise`), so the round's key and kit cite the newer guideline.
- **No erratum from a tag check.** A newer edition does not mean that what was taught is wrong.
  The teaching of rounds held before a tag was found changed or superseded (items on a sub-topic
  citing it) is queued for the review's guideline-change check, which raises an erratum only
  where the teaching actually differs. The queue is derived at the review from the records (the
  day of each finding, `since`) and the ledger's rounds, never stored, so a publish that stops
  after the records file and before the ledger loses nothing.
- **Seeded** from the #82 pass and the tags the #89 pass searched (`templates/guideline_checks.json`),
  for the default region only. Both passes ran on 2026-11-27 (commits 6885326 and e46ee0b), so
  every seed record carries that date: an earlier date would be invented. The 90-day sweep then
  spreads them by its quota, oldest first by name; the 86 tags #89 did not search
  have no record, so the first preparations check them.

Considered: records in the ledger (rejected: start-up latency and size); a full check at every
review only (rejected: tags an item rests on could be months stale); running the review sweep
live (rejected: the learner would wait). Accepted costs: about 33 edition checks per preparation,
about 250 to 300 before each review, overlapping the rolling sweep as a deliberate second net; and a
round written at the session (not prepared) cites the blueprint's tag unchanged, its evidence
check still verifying every claim.

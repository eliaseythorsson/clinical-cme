# Curriculum in themed blocks with a capped drill-down

Learners were pulled from one unfamiliar topic to the next ever deeper, with no coherence. Rounds now run in blocks (default 12 rounds, counted in rounds, not calendar time) themed on one domain: about 60% of short questions from the theme, 25% spaced repeats due from any domain, 15% wildcard, and the case always on the theme. The next theme is proposed automatically (weakest or longest-unvisited domain) and the learner can override it in one line. Drill-down happens only within the theme and at most two consecutive rounds per sub-topic; an off-theme miss gets one targeted retest after a few days, then normal spacing. A missed topic waits at least ~3 days, and a gap closes only when an item tests that gap.

## Consequences

The theme is shown to the learner ("Block: gastroenterology, round 4 of 12"). This deliberately gives up domain-level blinding for coherence; topics stay blind. Existing ledgers keep all history, gaps and due dates; the first block starts at the next round.

## Spacing rules as built (issue #15)

- The three-day minimum applies to every tested topic, not only to misses: the calibration rules (overconfident, underconfident) could otherwise undercut it. It is a floor on the interval, and the planner also refuses a topic tested in the last two days, so ledgers that already hold a next-day due date need no migration.
- Gaps have ids. The plan names the gap an item should retest, the item in the round names the gap it did retest, and only such an item, scoring 4 or more, closes it. A gap not yet retested gets one targeted retest once it is three days old; after a failed retest it follows its topic's spacing.
- The correction of comfort ratings is applied when domain weights are computed, not when the rating is stored: the rating that counts is the lower of the stored rating and the mean mastery of the domain's tested topics, rounded down. This also corrects ratings already inflated in existing ledgers and leaves the learner's own rating intact for the progress review. Ratings for untested domains (from setup) count as given: there is nothing yet to check them against.

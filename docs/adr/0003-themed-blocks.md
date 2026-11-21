# Curriculum in themed blocks with a capped drill-down

Learners were pulled from one unfamiliar topic to the next ever deeper, with no coherence. Rounds now run in blocks (default 12 rounds, counted in rounds, not calendar time) themed on one domain: about 60% of short questions from the theme, 25% spaced repeats due from any domain, 15% wildcard, and the case always on the theme. The next theme is proposed automatically (weakest or longest-unvisited domain) and the learner can override it in one line. Drill-down happens only within the theme and at most two consecutive rounds per sub-topic; an off-theme miss gets one targeted retest after a few days, then normal spacing. A missed topic waits at least ~3 days, and a gap closes only when an item tests that gap.

## Consequences

The theme is shown to the learner ("Block: gastroenterology, round 4 of 12"). This deliberately gives up domain-level blinding for coherence; topics stay blind. Existing ledgers keep all history, gaps and due dates; the first block starts at the next round.

## Blocks as built (issue #16)

- The ledger holds the block (`block`: theme, rounds recorded, length) and the finished ones (`blocks`). Planning only reads; a block is written when its first round is recorded. So a ledger from before blocks needs no migration step: it has no block, the next round proposes one, and nothing else is touched. Every recorded round counts in the block, including a one-off round on another domain the learner asked for.
- The 60/25/15 shares are met over the block, not in each round. Rounded per round, the default three short questions would be 2/1/0 every time and the wildcard would never appear; instead round n gets what n rounds are owed less what was given. Some rounds therefore have no repeat slot, and an off-theme repeat can wait one round longer than its date.
- A share with nothing to give passes its slot to the theme (no repeats due on a new ledger; no untested topic left outside the theme). Repeat slots take what waits outside the theme first, because the theme's own due topics already have the theme slots. A large backlog of due topics outside the theme is therefore worked off at about one per round: coherence was chosen over clearing the backlog fast.
- Within the theme, what is due comes before new topics, with one slot kept for a new topic when the round has none; when every topic of the theme has been tested, the one tested longest ago is revisited on another decision point. The case avoids the topic of the previous round's case. The cap on drilling one sub-topic is issue #18.
- The proposed theme is deterministic: weight for new material (blueprint weight, corrected self-rating, emphasis), raised for open gaps, damped for four blocks after a domain's own block; domains with fewer than four blueprint topics are not proposed (three topics cannot fill twelve rounds) and reach the learner as repeats and wildcards. Importance counts as well as weakness: a weak low-weight domain can lose to a middling high-weight one.
- A round prepared ahead is used only for the round of the block it was planned for. A round prepared by a version without blocks is set aside once.
- The learner changing the theme (issue #17) builds on `propose_theme` (theme, one-line reason, ranking) and `start_block` (a chosen theme, filing the block it replaces).

## Spacing rules as built (issue #15)

- The three-day minimum applies to every tested topic, not only to misses: the calibration rules (overconfident, underconfident) could otherwise undercut it. It is a floor on the interval, and the planner also refuses a topic tested in the last two days, so ledgers that already hold a next-day due date need no migration.
- Gaps have ids. The plan names the gap an item should retest, the item in the round names the gap it did retest, and only such an item, scoring 4 or more, closes it. A gap not yet retested gets one targeted retest once it is three days old; after a failed retest it follows its topic's spacing.
- The correction of comfort ratings is applied when domain weights are computed, not when the rating is stored: the rating that counts is the lower of the stored rating and the mean mastery of the domain's tested topics, rounded down. This also corrects ratings already inflated in existing ledgers and leaves the learner's own rating intact for the progress review. Ratings for untested domains (from setup) count as given: there is nothing yet to check them against.

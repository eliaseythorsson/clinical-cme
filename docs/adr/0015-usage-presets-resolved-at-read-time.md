# Usage: a preset resolved when the settings are read, and the learner's own settings kept apart

Many learners are not on high-usage Claude plans, and a round as the skill ran it (an author on
the most capable model, two checkers working through every claim and three podcast candidates
per topic, evidence deepening, guideline sweeps, the case in every round) takes a real share of
their allowance. Decided with the learner on 2026-11-27 (issue #93): one plain setting,
`config.usage`, **Full** (the skill as it was) or **Economy**, asked at setup and changeable by
asking or on the page.

- **What Economy is.** The author writes on the examiner's own model, not the most capable one;
  helpers otherwise stay as they are, so whoever grades still did not write the items (principle
  5). The evidence check covers only the claims the keys rest on, at most four searches and four
  fetches per list file and one other route for a source not reached (`evidence_check.md` §1.1;
  the author writes one list line per short question, two for the case). No evidence deepening
  (`evidence_ladder` off), no podcast search (`listening` off), no per-learner guideline sweeps
  (`guideline_sweeps` `off`; the round's own items' tags are still checked when stale, and the
  central records of ADR 0013 still arrive). A smaller default round: 2 MCQs and 1 focused
  question, the case every other round. The quality is lower, and the README says so plainly.
- **Resolved at read time, never written.** The preset (`USAGE_PRESETS`) is applied by
  `effective_config` whenever the settings are read; the config keeps what the learner (or the
  default) set. Writing the preset's values into the config was rejected: switching back to Full
  would then have to know which values were the preset's in order to restore the others, which
  is the same bookkeeping as below plus a second copy of every value that can drift. Every reader
  of a preset-decided setting goes through one function (`listening_on`, `evidence_depth`,
  `guideline_sweeps`, `mix_in_force`/`plan_counts`, the settings comparison of ADR 0010's
  prepared round).
- **The learner's own settings win**, tracked as one list, `config.set_by_learner`, of the
  preset-decided settings they set themselves: `settings`, `init` and a page setting add what they
  set; the list can be given to hand settings back (`[]`: all). The round mix is one setting
  (any of `mcqs`, `focused`, `case` makes all three theirs): a preset's mix half-merged with the
  learner's numbers would be a round nobody chose. A per-setting timestamp, or storing the
  learner's values in a separate map, were rejected as more state for the same answer.
- **Existing ledgers stay Full, and keep what they chose.** The load step's declared shape gives
  them `usage` `full`, so nothing changes. Upgrade step `set_by_learner` infers their list once:
  the mix (every ledger's mix was chosen at setup, or is the mix of its era) and each other
  preset-decided setting whose value differs from the default (only the learner could have
  changed it). So a learner who later moves to Economy keeps their mix and their choices; the
  `usage.kept` the engine prints lets the assistant offer Economy's smaller round in one line.
- **The case every other round** is decided in planning from the record, not from a counter:
  the next round has the case unless the last round recorded had one (`case_in_turn`). Nothing
  new is stored, the plan stays a pure function of the ledger and the date (a prepared round
  still matches the next `start`), a round stopped before its case leaves the case for the next,
  and a round without it is planned as the same mix with no case (as `--no-case`), so topics it
  does not play keep their schedule. Session-count parity was rejected: it drifts with stopped
  rounds and archived sessions.
- **Reported, not inferred.** `start`, `open`, `settings` and `init` print `usage` (mode,
  `author`, `evidence`, the preset's settings as they take effect, `case_every`, `kept`), and the
  plan carries `usage` only when it is not Full, so the example ledgers' plans are unchanged.
  SKILL.md picks the author's model from `usage.author` and gives the checker `Scope:
  <usage.evidence>`.
- **Setup's suggestion.** The skill cannot see the learner's plan. Onboarding asks the one
  question with no silent default; "not sure" or no answer is Economy, because running out of
  usage mid-round costs a learner more than a less polished item, and moving up to Full is one
  sentence or one tap. The engine's own default (a ledger or an `init` without the setting) is
  Full, so that no existing behaviour changes.

`usage` is not content-neutral: it changes who writes the items and how far they are checked, so
changing it sets a prepared round aside, as does any change it makes to the settings it decides
(compared as they take effect); `set_by_learner` and `usage_set_at` are neutral on their own.
The page gets a Full/Economy control (`cme/prefs` `usage`, applied once by its `updated` against
`config.usage_set_at`, as the paragraphs are): a page update, without a version bump here.

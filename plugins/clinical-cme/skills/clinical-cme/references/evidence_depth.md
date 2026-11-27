# Evidence depth: the better a topic is known, the further behind the recommendation

Read by the examiner when `answer` prints a `depth` above 1 for an item, and by the author when
the plan gives an item a `depth` (the kit's `deeper` block, rule 8 of `standards_kits.md`).

A learner who keeps answering a topic well no longer needs the rule; what they can still
gain is knowing what the rule rests on and how far that can be trusted. A learner who
missed it needs the rule, the reasoning and the recommendation, taught well, and nothing
that competes with them for attention.

The grading form gives each item its `depth` under `given` (`answer` prints it too:
`{"Q1": {"level": 3, "name": "design", "in_a_row": 2}}`): the depth the item gets **if it
was answered well today**. The engine counts, per topic (per sub-topic where the blueprint has
two levels), how many times in a row its items were answered well (mastery ≥ 4, no misconception, no guessed MCQ), back from the last
round. A focused question goes at most one depth beyond what its own aspect of the topic
has earned; an item on an open gap stays at 1. No `depth` (the ladder is off,
`config.evidence_ladder` false): every item is at depth 1.

| Depth | Answered well before, in a row | What the feedback adds for an item answered well today | Words |
|---|---|---|---|
| 1 `guidance` | 0: new, missed the last time, or an open gap | Nothing: the two or three lines of `feedback_guide.md` §4, the recommendation and its source | – |
| 2 `studies` | 1 | **Which studies the recommendation rests on**: the one or two that carry it, each with name, year, who was studied, what was compared and the primary result as absolute figures; and the class and level the guideline gives on their strength | 60–100 |
| 3 `design` | 2–3 | **The design features that decide how far the result can be trusted, and for whom**: the one or two that matter for this decision, chosen from who was excluded, the comparator and its dose, blinding, the endpoint (composite, surrogate, how it was adjudicated), a non-inferiority margin, early stopping, intention to treat against per protocol, relative against absolute effect, how few events would overturn it | 100–160 |
| 4 `frontier` | 4 or more | **Where the evidence stops or is disputed**: trials or meta-analyses that disagree and why; how the panel got from the evidence to the recommendation (extrapolation, expert opinion, why two societies read the same trials differently); the statistical or philosophical question underneath (a subgroup claim, a surrogate standing in for an outcome, an explanatory trial applied to a patient it would have excluded, a Bayesian re-reading); trials under way. It may end with one question to think about | 120–200 |

How it is applied:

- **Each depth starts with one line of the depth before it** (the study named before its
  design is discussed), and picks what bears on the decision the item tested. It is an
  appraisal for a colleague, never a checklist and never a recital of everything known.
- **Missed today → the first depth, in full.** The teaching is as informed and as nuanced
  as ever: the decision rule, the reasoning, the recommendation with its strength, the key
  figure, the exception and the pitfall (`feedback_guide.md` §3). What is left out is the appraisal of the
  studies: no trial design, no statistics beyond the figure that drives the decision, no
  philosophy of the evidence. A study may be named in a clause as the source. The record
  starts again from there: answered well next time, the topic is at depth 2.
- **The case**: its `depth` applies to the one or two decisions at the centre of the case
  that the learner got right (a rubric element marked ✓); elements missed or partial are
  taught at the first depth. A case at mastery below 4 gets no deeper section.
- **Only checked evidence.** The kit's `deeper` block (rule 8 of `standards_kits.md`) is the
  finished text at the plan's depth, its studies checked with the verification list; the draft
  includes it only for an item answered well. Where the kit has none (a round prepared before
  the record changed, a focused question on another aspect than planned), write from the
  evidence file, or search that study now, since the part's answers are in. `grading.md` §1 holds: a design
  feature or a figure you could not verify is left out, and a depth that cannot be reached
  with checked facts is given at the depth that can.
- **The pitch sets the language, the depth sets how far** (`feedback_guide.md` §1): an early-stage learner
  at depth 3 gets the same appraisal with its terms explained ("non-inferiority: the trial
  only set out to show the new drug is not much worse").
- **It replaces words, it does not add a section to read** (`feedback_guide.md` §5): the words come out of the
  round's budget, gaps first. Over budget, shorten the deeper text before a briefing.
- **Say it in a clause, in plain words** (`feedback_guide.md` §6.3), where the deeper text starts: "You've
  answered this well three times running, so a closer look at the trial behind it:". No
  level numbers or names to the learner.
- The learner asks in the round to go deeper on an item, or to skip the trials: do it for
  that item. As a standing choice it is the setting (`requests.md` §1).

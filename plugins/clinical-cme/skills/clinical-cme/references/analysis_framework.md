# Analysis framework: coding each round, and the deep review

The skill analyses the learner's reasoning in two steps.

- **Code every round at grading time**, while the case, the answers and the evidence are in
  front of you. The codes go into the round JSON (and from there the ledger) and into the
  session log.
- **At the progress review, offer a deep analysis.** It counts the codes across the period,
  reads the log for evidence and nuance, and gives personal, candid feedback.

Coding prospectively is more reliable than reading 30–40 sessions cold months later. It also
keeps the review feasible at any log size.

**Be honest about the method.** No validated instrument exists for analysing one physician's
free-text answers to AI-generated cases. This framework adapts published tools, each
validated or described in other settings:

- the SIDM Assessment of Reasoning Tool, for reasoning steps
- Graber's diagnostic-error categories plus Reason's slips versus mistakes, for error types
- Croskerry's catalogue, for cognitive biases
- the Revised-IDEA rubric, for the quality of the written reasoning
- the Brier score, for calibration
- R2C2, for delivering the feedback

The coding is the assistant's judgement, made by one rater. The review report says so once, plainly.

## 1. Coding a round

The examiner codes every item at grading time, in the grading form; the codes and how to give
them are written once, in the examiner's brief: `feedback_guide.md` §11 (ART domains §11.1,
Revised-IDEA §11.2, errors with their category, knowledge type, severity and bias §11.3,
confidence and calibration §11.4, the coding line in the feedback §11.5, focused questions
§11.6). For the deep review, read that section with this one: the review counts those codes.

## 2. The deep analysis at the progress review

Offered at every progress review (`progress_review.md`). The learner can decline it and have
the standard check-in only. Expect 15–30 minutes of work and a report of 1,500–3,000 words.

### 2.1 Gather

1. `python3 cme.py stats --work <work>`. Its `analysis` block holds the coded aggregates for this
   period, the previous period and all time. It also lists critical errors, bias evidence,
   long-open gaps, repeated confident errors, blind spots, drill results, disputes and previous
   reviews. Use these figures; never estimate numbers in prose.
2. Previous review reports (`reviews/<date>` documents in the store), at least the last one,
   including its change plan.
3. The log for the period: read the period's session documents into local files
   (`progress_review.md` §1, step 2), one file per session. Read them in batches of about six; the
   `transcript` field holds the case, questions, answers and feedback, `closing` the
   reflection, discussion, grade changes and coded analysis. Skim the feedback unless a point
   needs it; it is long and you wrote it. After each batch, append structured notes (patterns,
   quotations, session IDs) to a scratch `review_notes.md` and rely on those notes rather than
   memory.
4. **Whole history.** At the learner's first deep review, or whenever they ask, read every
   entry, not just this period, in the same batched way. Otherwise the earlier periods come
   in through the all-time figures and the earlier review reports.
5. **Large periods.** If the period has more than about 15 entries and a subagent tool
   (parallel helper agents) is available, analyse the batches in parallel. Give each subagent this file,
   its batch file and the instruction to return findings in the §2.2 headings, with session
   IDs and short quotations. Then merge the results yourself and check every claim against
   the figures.

### 2.2 Analyse and write the report

Rules that apply to every section:

- **Every claim is backed** by session IDs and, where useful, the learner's own words.
- **A pattern needs at least two sessions or three items.** Call anything less an isolated
  event.
- **State the n.** Do not invent norms or compare with "other physicians".
- **Rank by consequence**, then by frequency.
- **Candid, specific and fair.** The learner asked for critical feedback on every aspect, so
  do not soften, pad or flatter. Do not exaggerate either.

Sections, in this order:

1. **Headline** (three lines): the main strength, the main weakness, and the direction of
   travel.
2. **Strengths.** What they reliably do well, with evidence. Strengths are information too:
   these are areas to de-emphasise.
3. **Weaknesses.** Ranked. Critical-severity errors first, whether or not they recur.
4. **Thought errors.**
   - The reasoning-step profile (ART table: this period, the previous period, all time)
     and where reasoning tends to break; focused questions in their own line (`feedback_guide.md` §11.6).
   - Recurring biases, with two or three short quotations.
   - Synthesis vs data gathering vs slips.
   - Anchoring across Stage 1 → Stage 2.
5. **Knowledge errors.**
   - By type and domain.
   - Outdated knowledge, listing which guidance changed.
   - Numeric errors (thresholds, doses).
   - Transfer failures (knows it in one context, misses it in another).
6. **Calibration and self-assessment.**
   - The calibration table, Brier score and overconfidence index, with n.
   - Topics with repeated confident errors.
   - Comfort vs mastery.
   - **Blind spots**: graded gaps the learner never named as shaky in any reflection.
   - Underconfidence: areas they underrate.
7. **Clinical write-up.** Revised-IDEA trend and the weakest component.
8. **Progress.**
   - Comparison with the previous period and with the last review's change plan: what was
     targeted, and did it move?
   - Drill results.
   - Gaps resolved vs persisting; gaps open ≥ 60 days.
   - Topics improved or declined.
9. **Learning behaviour.**
   - Pace vs target, minutes, reflection skipped, uncertainty flagged, reading reported.
   - Disputes and their outcomes. If the learner was often right, say so plainly: it says
     something about the grading.
   - Scores the learner set and gaps they closed by request (`learner_overrides`), apart from
     disputes: how many, how far from the grading, on which topics, and whether those topics
     held up when tested again. State it; it is the learner's record.
10. **Critical feedback.** One or two paragraphs in the voice of a demanding, fair senior
    colleague: what would worry them about this clinician's practice, and what would
    impress them.
11. **What has changed since you learned it.** Results of the guideline-change check (§2.3).
12. **Change plan.** Two or three goals, each specific and measurable, with how the skill will
    support it: drill targets, domain emphasis, settings. Agree the plan with the learner (§2.4).
13. **About this analysis.** Two or three lines: the codes are the assistant's judgements as a single
    rater; the frameworks are adapted, not validated for this use; the n.

### 2.3 Guideline-change check

1. `stats` lists `teaching_points_unchecked` (this period's key-learning lines not yet
   checked, as `<session>.<n>`).
   Check first the points `stats` lists under `guidelines.teaching_to_recheck`: per guideline
   tag found changed or superseded while rounds were prepared, the rounds held before that
   finding on a sub-topic citing it, with their points (`points` null: a round of an earlier
   period; its session document holds them). Each still gets its own verdict: a newer edition
   is an erratum only where what was taught actually differs.
2. Verify the ones most likely to have changed against current primary sources: thresholds,
   drug choices, doses, recommendation classes, screening intervals. Typically 10–15 per
   review, more if the learner wants.
3. Classify each point:
   - `current`
   - `changed` (the substance holds but a detail moved)
   - `superseded`
   - `uncertain` (could not verify)
4. Record the results in the review JSON (`teaching_point_checks`). Each `changed` or
   `superseded` point becomes a pending erratum. The next session writes it into the log
   (`session_log.md` §5), so the log is only ever written during sessions.

### 2.4 Delivering it: R2C2, adapted to chat

R2C2 is an evidence-informed model for facilitated feedback to physicians on their
performance data (Sargeant et al., *Acad Med* 2015). It has four phases: build the
relationship, explore reactions, explore content, coach for change.

1. **Relationship.** Open with one or two lines: what the analysis is based on (n sessions,
   the period) and that it is candid by design.
2. **Reaction.** Present the headline and the key figures. Then ask: "Does this match your
   sense of how it's going? Anything surprising, or that seems unfair?" Wait for the answer.
3. **Content.**
   - Send the full report: as a file, and in chat if it fits in one screen.
   - Discuss any part the learner wants.
   - If they give context that changes a finding, correct the report before saving it.
4. **Coaching.**
   - Agree two or three goals and how to support them.
   - Turn them into `drill_targets`, `domain_emphasis` and `config_changes` in the review
     JSON (`progress_review.md` §3). A drill code is the pattern's code, such as `bias:premature_closure`,
     `art:TEST` or `knowledge:numeric`.
   - Set a rate (default 0.33 of rounds) and leave `until` empty so it runs until the next
     review.

### 2.5 Save

- Save the report as the store document `reviews/<YYYY-MM-DD>` (template below;
  `progress_review.md` §3).
- Record the review with `cme.py review --work <work> --review REVIEW.json` and publish its
  `files`; the review JSON includes `doc`, `deep_analysis: true`, `headline`, `key_figures`, `change_plan`,
  `drill_targets` and `teaching_point_checks`. Never write to the session log during a review.

### 2.6 Report template

```markdown
# CME progress review — <date>
Period: <start> – <end> · <n> sessions · <minutes> min · sessions <S00xx–S00yy>

## Headline
## Strengths
## Weaknesses (ranked)
## Thought errors
| Reasoning step | This period | Previous | All time |
## Knowledge errors
## Calibration and self-assessment
## Clinical write-up (Revised-IDEA)
## Progress since last review
## Learning behaviour
## Critical feedback
## What has changed since you learned it
## Change plan
## About this analysis
```

## 3. Sources

- Thammasitboon S, et al. (SIDM Education Committee). The Assessment of Reasoning Tool (ART):
  structuring the conversation between teachers and learners. *Diagnosis (Berl)* 2018.
  doi:10.1515/dx-2018-0052. Its use for feedback: Cohen AL, et al. *Diagnosis (Berl)*
  2022;9(4):476–484. doi:10.1515/dx-2022-0020.
- Graber ML, Franklin N, Gordon R. Diagnostic error in internal medicine. *Arch Intern Med*
  2005;165(13):1493–1499. Cognitive factors in 74% of cases; faulty synthesis, especially
  premature closure, was the commonest cognitive problem, and faulty knowledge was uncommon.
- Reason J. *Human Error*. Cambridge University Press, 1990 (slips and lapses vs mistakes).
- Croskerry P. The importance of cognitive errors in diagnosis and strategies to minimize
  them. *Acad Med* 2003;78(8):775–780.
- Schaye V, et al. Development of a clinical reasoning documentation assessment tool for
  resident and fellow admission notes: a shared mental model for feedback. *J Gen Intern
  Med* 2022;37:507–512 (Revised-IDEA; ICC 0.84; ≥ 6 high quality).
- Davis DA, et al. Accuracy of physician self-assessment compared with observed measures of
  competence: a systematic review. *JAMA* 2006;296(9):1094–1102.
- Meyer AND, et al. Physicians' diagnostic accuracy, confidence, and resource requests: a
  vignette study. *JAMA Intern Med* 2013;173(21):1952–1958.
- Brier GW. Verification of forecasts expressed in terms of probability. *Mon Weather Rev*
  1950;78:1–3.
- Butterfield B, Metcalfe J. Errors committed with high confidence are hypercorrected.
  *J Exp Psychol Learn Mem Cogn* 2001;27(6):1491–1494.
- Sargeant J, et al. Facilitated reflective performance feedback: developing an
  evidence- and theory-based model that builds relationship, explores reactions and
  content, and coaches for performance change (R2C2). *Acad Med* 2015;90(12):1698–1706.

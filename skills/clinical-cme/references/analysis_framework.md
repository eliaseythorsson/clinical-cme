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

Code every item. Add a `coding` block to each item of the round JSON
(`state_schema.md` §2). An item that went perfectly still gets a coding block with ART
scores (for cases and focused questions) and an empty `errors` list. Focused questions are coded
as in §1.6.

### 1.1 Reasoning steps (cases; focused questions in part, §1.6): ART domains, plus management

These are the five domains of the Assessment of Reasoning Tool (SIDM; *Diagnosis* 2018). The
tool rates whether specific behaviours are present: three levels for domains 1–4 and two for
metacognition. Management is added as a sixth domain. It is **not part of ART**; label it as
an extension when you report it.

| Code | Domain | 2 | 1 | 0 |
|---|---|---|---|---|
| `DG` | Hypothesis-directed data gathering | Every requested test or history item targets a stated hypothesis, and the learner predicts results | Mostly targeted; some untargeted requests or no predicted results | Shotgun ordering, or the decisive discriminator not sought |
| `PR` | Problem representation | Accurate one-sentence summary with the key features, time course and abstract qualifiers (acute/chronic, severity) | Mostly restates the case, or misses one key feature | Absent, or misframes the problem |
| `DDX` | Prioritised differential | Ranked, includes the final diagnosis and the must-not-miss alternatives, with reasons for and against | Right diagnoses present but poorly ranked or argued, or one must-not-miss missing | Final diagnosis absent, or the list is unranked and unargued |
| `TEST` | High-value testing | Tests chosen because results would change management; low-yield tests avoided; pre-test probability considered | Some low-value or redundant testing, or the order is not prioritised | Tests that would not change management dominate, or harmful or invasive tests without indication |
| `META` | Metacognition (0–1) | Names their uncertainty, what would change their mind, or a bias to guard against | — | Absent, or certainty stated where it was not warranted |
| `MGMT` | Management and disposition (extension) | Correct interim and definitive management: drug, dose and threshold where they matter, monitoring, disposition | Broadly right, with an important omission or imprecision | Wrong or unsafe management |

In the one-step (discriminate) format, score `MGMT` from the interim management only. Leave a
domain out (do not score 0) when the round gave no opportunity to show it.

### 1.2 Quality of the written reasoning (cases only): Revised-IDEA

The Revised-IDEA rubric scores clinical-reasoning documentation in admission notes (Schaye et
al., *JGIM* 2022). It totals 0–10, and ≥ 6 is the published standard for high quality. Apply
it to the Stage 1 answer. Score content, not prose: terse notes can score full marks.

| Code | Domain | Range | Full marks when… |
|---|---|---|---|
| `I` | Interpretive summary | 0–4 | Concise, with semantic qualifiers, and synthesises rather than lists the data |
| `D` | Differential diagnosis | 0–2 | A prioritised differential with the leading diagnosis committed to |
| `E` | Explanation of the lead diagnosis | 0–2 | Supporting and opposing data explained for the lead diagnosis |
| `A` | Alternative diagnoses explained | 0–2 | Reasons given for each alternative's place in the ranking |

The case prompt asks for a one-sentence problem summary (`case_design.md` §5), so `I` and
`PR` always have something to score.

### 1.3 Errors

Write one record for each rubric element marked ✗ or ◐ (case or focused question), and one for
each wrong MCQ. Fields:

```json
{"element": "Did not consider exercise-associated hyponatraemia; attributed confusion to hypovolaemia",
 "stage": 1, "category": "synthesis", "knowledge_type": null, "art_domain": "DDX",
 "bias": ["premature_closure"], "bias_evidence": "'clearly dry from the run — 2 L saline'",
 "severity": "critical", "confidence": "sure"}
```

**Category.** The primary cause, adapted from Graber's diagnostic-error categories (knowledge,
data gathering, synthesis) plus Reason's slips:

| `category` | Use when | Example |
|---|---|---|
| `knowledge` | The learner did not know, or recalled wrongly, the fact or rule needed | Unaware that fidaxomicin is now preferred for a first *C. difficile* episode |
| `data_gathering` | The decisive information was available to ask for, but was not sought, ordered or elicited | Never asks for urine osmolality and sodium in hyponatraemia |
| `synthesis` | Data and knowledge were present, but the learner put them together wrongly: mis-weighted a finding, missed the pattern, closed too early, misjudged probability | Knows the SIADH criteria (stated in Q2) yet labels the case hypovolaemic despite euvolaemic findings |
| `slip` | An execution lapse in someone who otherwise has it right: arithmetic, units, misread value, answered a different question | Calculates the anion gap with the wrong chloride |
| `unclassified` | The cause cannot be seen (typically an MCQ answered with a letter only) | — |

Decision rules:

- **Synthesis needs evidence the knowledge was there.** For example, it was stated elsewhere
  in the round, or the topic was mastered in recent rounds. Without that evidence, code
  `knowledge`. Over-coding synthesis flatters the learner.
- **Choose one primary category.** Mention a secondary cause in `element` if it matters.

**`knowledge_type`** (only for knowledge errors):

| Type | Meaning |
|---|---|
| `missing` | Never knew it |
| `outdated` | Knew the former standard; guidance has changed. Name the change in `element` |
| `misapplied` | Knows the rule but applied it to the wrong population or context. A transfer failure |
| `numeric` | Right concept, wrong threshold, dose, interval or cut-off |

**`art_domain`**: the reasoning step where the error occurred (§1.1).

**`severity`**: what would happen if the learner did this in practice.

| Severity | Meaning |
|---|---|
| `minor` | Would not change care |
| `important` | Suboptimal care, delay or avoidable cost |
| `critical` | Plausible serious harm, or a must-not-miss diagnosis missed |

Be strict and consistent: critical errors lead the review.

**`bias`**: label a cognitive bias only when the learner's own words show it. Always put
those words in `bias_evidence`. A bias read from text is an inference, never a diagnosis.
No label is better than a guessed one. Vocabulary (after Croskerry, *Acad Med* 2003):

| Code | What it looks like in an answer |
|---|---|
| `anchoring` | Holds to an early impression despite later data that contradicts it (often across Stage 1 → Stage 2) |
| `premature_closure` | Commits to a diagnosis and stops considering alternatives, with no "but consider…" |
| `confirmation` | Orders or cites only data that would support the leading diagnosis; explains away conflicting data |
| `availability` | Favours a diagnosis because it is memorable or recent, against the base rate ("I just saw a case of…") |
| `base_rate_neglect` | Ignores prevalence; ranks a rarity above common causes on weak features |
| `representativeness` | Rejects a diagnosis because the presentation is atypical ("too young for an MI") |
| `search_satisficing` | Stops after one abnormality explains part of the picture; misses a second process |
| `framing` | Adopts the referrer's or triage framing without testing it |
| `overconfidence` | Certainty clearly beyond the evidence, usually with a `sure` rating on an error |
| `omission` | Withholds an indicated action from fear of causing harm |
| `commission` | Acts (tests or treats) when watchful waiting was indicated |
| `unpacking_failure` | Takes the history or data at face value without eliciting the detail that changes it |

Use `other:<name>` for a recognised bias not listed (for example `other:sunk_cost`).

### 1.4 Confidence and calibration

The learner's optional per-item confidence (sure / unsure / guess) is mapped to a probability
of being right: 0.9 / 0.6 / 0.3. This mapping is a convention, not a validated scale.
Outcomes:

- MCQs: 1 if correct, 0 if wrong.
- Cases and focused questions: mastery ÷ 5.

The `stats` command reports, for each period:

- the calibration table (expected vs observed per confidence level)
- the **Brier score** (mean squared error of the stated probability; 0 is perfect, lower is better)
- the **overconfidence index** (mean expected − mean observed; positive means overconfident)

Interpret these only with enough items. Below about 20 rated items, describe the pattern but
do not lean on the numbers.

Why this matters: physicians' self-assessment tracks external measures of competence poorly,
and is least accurate in the least skilled and most confident (Davis et al., *JAMA* 2006).
Physicians in a vignette study were overconfident on both easy and hard cases (Meyer et al.,
*JAMA Intern Med* 2013). Confident errors corrected with feedback tend to be corrected well
(the hypercorrection effect), so they are worth surfacing.

### 1.5 The coding line in the feedback

When `config.show_coding` is true (the default), add one line under the gap summary
(`feedback_guide.md` §2D). Only show errors and the scores that teach something:

> **Coding:** Case — synthesis error at the differential (premature closure, inferred from
> "clearly dry from the run"), critical; write-up (Revised-IDEA) 5/10, interpretive summary
> the weakest part. Q3 — knowledge, outdated (first-line *C. difficile* treatment). Q4 (focused)
> — data gathering at testing (decisive test not chosen), important.

If nothing went wrong: "**Coding:** no errors; reasoning steps all at full marks." Do not
show ART tables in the round.

### 1.6 Focused questions

A focused question tests one decision, so it is coded narrowly:

- **ART: only the domains the question asked about**, on the same scale as §1.1. Leave every
  other domain out (do not score 0). By aspect, usually:

  | Aspect | Score |
  |---|---|
  | `diagnosis` | `DDX` (ranking and reasons against the main alternative), and `PR` if the answer has to synthesise the picture |
  | `interpretation` | `PR` |
  | `testing` | `TEST`, and `DG` when the question asks how the result would change management |
  | `management`, `disposition`, `prevention` | `MGMT` |
  | `prognosis` | `PR` |

  Add `META` (0–1) only when the lead-in asked what would change their mind.
- **No Revised-IDEA**: it rates a full write-up; `record` warns if one is given.
- **Errors** as in §1.3, one per ✗ or ◐ rubric element, with `art_domain`. A bias needs the
  learner's words as always; a few lines rarely show one.
- **Calibration**: the outcome is mastery ÷ 5, as for the case.

`stats` keeps focused questions apart from the case: `art_domains` counts the case only (so it
stays comparable with earlier periods), `art_domains_focused` the focused questions, and
`items_by_type` the counts. In the review, report them separately; a learner who reasons well in
focused questions but not across a full case (or the reverse) is telling you where the
difficulty lies — breadth of the work-up, or the single decision.

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
     and where reasoning tends to break; focused questions in their own line (§1.6).
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

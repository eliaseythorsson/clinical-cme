# Coding a round

Code every item at grading time, while the case, the answers and the evidence are in front of
you, in the item's `coding` block of the grading form. An item that went perfectly still gets a
coding block with ART scores (for cases and focused questions) and an empty `errors` list.
Focused questions are coded as in §5. Where the codes come from, and how the review uses
them: `analysis_framework.md`.

## 1. Reasoning steps (cases; focused questions in part, §5): ART domains, plus management

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

## 2. Quality of the written reasoning (cases only): Revised-IDEA

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

## 3. Errors

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

**`art_domain`**: the reasoning step where the error occurred (§1).

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

## 4. The coding line in the feedback

When `config.show_coding` is true (the default), add one line under the gap summary
(`feedback_guide.md` §2 D). Only show errors and the scores that teach something:

> **Coding:** Case — synthesis error at the differential (premature closure, inferred from
> "clearly dry from the run"), critical; write-up (Revised-IDEA) 5/10, interpretive summary
> the weakest part. Q3 — knowledge, outdated (first-line *C. difficile* treatment). Q4 (focused)
> — data gathering at testing (decisive test not chosen), important.

If nothing went wrong: "**Coding:** no errors; reasoning steps all at full marks." Do not
show ART tables in the round.

## 5. Focused questions

A focused question tests one decision, so it is coded narrowly:

- **ART: only the domains the question asked about**, on the same scale as §1. Leave every
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
- **Errors** as in §3, one per ✗ or ◐ rubric element, with `art_domain`. A bias needs the
  learner's words as always; a few lines rarely show one.
- **Calibration**: the outcome is mastery ÷ 5, as for the case (`analysis_framework.md` §1.1).

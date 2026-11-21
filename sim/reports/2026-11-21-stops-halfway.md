# Simulation report: stops-halfway, 2026-11-21

| | |
|---|---|
| Result | all automatic checks passed |
| Persona | stops-halfway |
| Skill version / commit | 4.3.1 / cea86ce |
| Examiner / learner model | claude-fable-5-2 / claude-fable-5-2 |
| Round | S0001: 3 MCQ |
| Round score (examiner's grading) | 4.0 |
| Ledger settings | case=true, case_format="unfolding", focused=0, helpers=false, item_order="mcqs_first", mcqs=3, prepare_ahead=false |
| Messages | 5 examiner, 4 learner |
| Clinical quality (logged only) | items 4.5/5 (n=4), feedback 4.67/5 (n=3), overall 4/5 — Accurate, current, well-pitched round with precise feedback; only quibbles (Q3 boundary delta, storm not considered in case key). Judged from knowledge; search confirmed cited pages exist only. |

## Automatic checks

| Check | Result | Detail |
|---|---|---|
| Blinding: no topic, diagnosis or key shown before the matching answer | pass | 0 leak(s); 4 topic word(s) or domain name(s) to review; 405 terms searched |
| Every file saved | pass | 4 file(s) compared with the store (out1, out2) |
| Log complete and verbatim | pass | sections: a_case, a_questions, case, coded, discussion, fb_questions, feedback, grade_changes, notes, questions, reflection |
| Persona: round saved without the case, its topic still due | pass | 3 item(s) saved; case topic CARD-03, schedule {"last": null, "attempts": 0, "step": 0, "due": null} |

### Blinding: findings

| Level | Part | Kind | Term | Examiner message | Where |
|---|---|---|---|---|---|
| review | questions | topic word | coronary | 2 | …t exercise test B. Start fondaparinux and arrange coronary angiography within two hours C. Give a ticagrelor… |
| review | case | topic word | rhythm | 2 | …n air; examination is normal. The ECG shows sinus rhythm with no ST-segment or T-wave changes, and is unch… |
| review | case | topic word | atrial | 4 | …l/L (2.15–2.55), magnesium 0.82 mmol/L. **ECG**: atrial fibrillation, ventricular rate 138–150/min; norma… |
| review | case | topic word | fibrillation | 4 | …15–2.55), magnesium 0.82 mmol/L. **ECG**: atrial fibrillation, ventricular rate 138–150/min; normal axis; QRS 8… |

### Examiner text that is not in the log

Opening lines, the close message and prompts are not logged by design; a feedback or case paragraph here would be a finding.

- message 2: Today's round: three MCQs, then one case, about 25 minutes. Block: Cardiology, round 1 of …
- message 9: Saved as session **S0001**: three cardiology questions — acute decompensated heart failure…
- message 9: Your reflection is in: your comfort ratings match the grading, and ACS triage with the 0 h…
- message 9: With your target of three sessions a week, the next one fits in two or three days.…

## Waiting time per step

Wait: from the learner's message to the examiner's first message after it (includes the relay). Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.

| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) |
|---|---|---|---|---|---|---|
| 1 | start of round | 67.1 | 226.8 | 1 | 3531 | – |
| 2 | after the answers to the questions | 127.5 | 132.5 | 1 | 9464 | 15.1 |
| 3 | after learner message 5 | 49.6 | 59.5 | 2 | 2677 | 38.8 |
| 4 | after the reflection | 120.0 | 123.5 | 1 | 599 | 38.8 |

Total wait 364.2 s; longest wait 127.5 s; whole run 631.4 s.

## Clinical quality

Scored 1–5 by a separate agent after the round (claude-fable-5-2). Kept for comparison over time; it is never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`).

| | What | Score | Note |
|---|---|---|---|
| Item | Q1 (mcq, CARD-02) | 5 | Matches ESC 2021 diuretic algorithm (urine Na <50-70 at 2 h, output <100-150 mL/h); first dose under home daily dose; doubling is the only defensible option. Right for a medical ward. |
| Item | Q2 (mcq, CARD-05) | 5 | HF from perforation with severe MR = urgent surgery (days), not emergency; bland 6 mm infarct does not delay (ESC 2023). Distractors each wrong for a teachable reason. |
| Item | Q3 (mcq, CARD-01) | 4 | hs-cTnT cut-offs and observe-zone step correct (ESC 2023). Quibble: delta sits exactly on the 3 ng/L boundary and typical angina in a diabetic makes treating as NSTE-ACS tempting; D still best. |
| Item | Case (case, CARD-03, not answered) | 4 | Realistic thyrotoxic AF with coherent results and a fair PE distractor; key fits ESC 2024. Quibble: 37.7 C, rate 140, AF and restlessness score near storm range, which the key never addresses. |
| Feedback | questions | 5 | Claims match ESC 2021/2023 as I know them (thresholds, 3-5 days, cut-offs, early invasive IIa, no pretreatment); grades fair; Q3 pins the exact misstep and credits the learner's doubt. |
| Feedback | final | 5 | Gap summary restates the troponin cut-offs correctly, codes the Q3 error fairly as numeric knowledge, and leaves the unanswered case ungraded and unrevealed; nothing clinically wrong. |
| Feedback | dispute | 4 | No clinical challenge was raised; this rates the replies to the stop request and reflection: accurate, proportionate, no new claims. Not a test of source re-checking. |

Mean: items 4.5, feedback 4.67.

For a clinician to look at:

- Q1 sealed key calls the 40 mg IV dose 'equal to the oral home dose' then says it was too low (home 80 mg/day); the feedback sent has it right.
- Q3: the 1 h change is exactly 3 ng/L, on the rule-out delta boundary; a delta of 4 would make the observe zone unambiguous.
- Case: presented findings give a Burch-Wartofsky score around 40-50; the key and rubric should say why this is not thyroid storm, or soften temperature/restlessness.
- Dispute entry: the learner made no challenge, so that score reflects only the wrap-up replies and should not be compared with runs that had a real dispute.
- Guideline details were judged from memory; web search returned links but no text, so class/level statements were not checked against the primary documents.

# Simulation report: weak-overconfident, 2026-11-27

| | |
|---|---|
| Result | all automatic checks passed |
| Persona | weak-overconfident |
| Skill version / commit | 7.0.0 / 8670ada |
| Examiner / learner model | claude-opus-5-5 / claude-opus-5-5 |
| Round | S0001: 2 MCQ, 1 focused, case (two stages) |
| Round score (examiner's grading) | 3.0 |
| Ledger settings | case=true, case_format="unfolding", focused=1, helpers=false, item_order="mcqs_first", mcqs=0, prepare_ahead=false, usage="economy" |
| Messages | 6 examiner, 5 learner |
| Clinical quality (logged only) | items 4.5/5 (n=4), feedback 4.5/5 (n=2), overall 4/5 — Clinically accurate, well-pitched round for internal medicine; feedback teaches the decisive points with correct sources; minor pitch/grade quibbles. |
| Cost to a learner (examiner + its helpers) | at least 139,285 tokens (1 of 5 examiner turns recorded) |

## Automatic checks

| Check | Result | Detail |
|---|---|---|
| Blinding: no topic, diagnosis or key shown before the matching answer | pass | 0 leak(s); 4 topic word(s) or domain name(s) to review; 528 terms searched |
| Every file saved | pass | 4 file(s) compared with the store (data/sessions/S0001.json, data/page.json, data/prepared.json, data/state.json) |
| Log complete and verbatim | pass | sections: a_case, a_final, a_questions, case, coded, discussion, fb_questions, feedback, grade_changes, questions, reflection, stage2 |
| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | pass | to review: 0 abbreviation(s) not spelled out at first use, 0 mixed time anchor(s); feedback: questions: 11 abbreviation(s), glossary line present, 6 not in it; final: 6 abbreviation(s), glossary line present, 2 not in it |
| Listening: a section in the final feedback, the picks in the session document | pass | turned off |
| Prepared feedback: marks before text, the feedback written from the draft | pass | 24 block(s) offered: 6 as prepared, 17 changed, 1 left out; 0 element(s) marked without the learner's words |

### Blinding: findings

| Level | Part | Kind | Term | Examiner message | Where |
|---|---|---|---|---|---|
| review | questions | topic word | chest | 2 | …utpatient clinic. For 3 months he has had central chest tightness when walking uphill, relieved by 2–3 mi… |
| review | questions | topic word | coronary | 2 | …t is the most appropriate next investigation? A. Coronary CT angiography B. Exercise ECG C. Invasive corona… |
| review | questions | topic word | cardiovascular | 2 | …his GP, who asks whether to calculate his 10-year cardiovascular risk before changing his treatment. He has had ty… |
| review | questions | topic word | prevention | 2 | … What is the most appropriate approach to stroke prevention? A. No antithrombotic therapy B. Start apixaban … |

### Writing standards: to review

Found by the lint's heuristics (`references/standards_lint.md`): each is for a person to judge and none fails the run.

| Rule | Where | What |
|---|---|---|
| 5.3 | the questions feedback | LV |
| 5.3 | the questions feedback | VA |
| 5.3 | the questions feedback | SR |
| 5.3 | the questions feedback | CIR |
| 5.3 | the questions feedback | US |
| 5.3 | the questions feedback | FLJ |
| 5.3 | the final feedback | OK |
| 5.3 | the final feedback | GP |

### Examiner text that is not in the log

Opening lines, the close message and prompts are not logged by design; a feedback or case paragraph here would be a finding.

- message 2: Today's round: 2 MCQs + 1 focused question + the case, about 45 minutes. Block: Cardiology…
- message 11: Saved: session S0001 — stable chest pain work-up, hypertrophic cardiomyopathy, lipid risk …
- message 11: Your reflection is in: the driving timings after syncope and pacing are now part of the sy…

## Waiting time per step

Wait: from the learner's message to the examiner's first message after it (includes the relay). Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.

| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) | Examiner tokens |
|---|---|---|---|---|---|---|---|
| 1 | start of round | 123.8 | 335.0 | 1 | 3563 | – | 139,285 |
| 2 | after the answers to the questions | 94.4 | 186.5 | 1 | 13511 | 15.0 | not recorded |
| 3 | after the Stage 1 answer | 47.9 | 50.5 | 1 | 2214 | 56.2 | not recorded |
| 4 | after the final answers | 283.7 | 298.1 | 2 | 15766 | 45.6 | not recorded |
| 5 | after the reflection | 95.2 | 110.1 | 1 | 563 | 18.7 | not recorded |

Total wait 645.0 s; longest wait 283.7 s; whole run 1100.8 s.

## Tokens

As the relay saw each agent's usage when its turn returned (`next --tokens`, `quality --tokens`); the examiner's helpers when it reported them (`--helper-tokens`). Cost to a learner: the examiner and its helpers; the learner persona and the scorer exist only in the simulation.

| Role | Turns | Recorded | Tokens |
|---|---|---|---|
| examiner | 5 | 1 | 139,285 |
| learner | 5 | 1 | 64,536 |

Run total 203,821; cost to a learner at least 139,285 tokens (1 of 5 examiner turns recorded).

| Role | Turn | Tokens | Helpers |
|---|---|---|---|
| examiner | 1 | 139,285 | – |
| learner | 1 | 64,536 | – |
| examiner | 2 | not recorded | – |
| learner | 2 | not recorded | – |
| examiner | 3 | not recorded | – |
| learner | 3 | not recorded | – |
| examiner | 4 | not recorded | – |
| learner | 4 | not recorded | – |
| examiner | 5 | not recorded | – |
| learner | 5 | not recorded | – |

## Clinical quality

Scored 1–5 by a separate agent after the round (claude-opus-5-5). Kept for comparison over time; it is never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`).

| | What | Score | Note |
|---|---|---|---|
| Item | Q1 (mcq, CARD-09) | 4 | ICA for limiting angina with new regional LV dysfunction fits ESC 2024; quibble: only 6 wks of low-dose drugs, so 'despite GDMT' is soft. |
| Item | Q2 (mcq, CARD-10) | 5 | HCM with clinical AF: OAC regardless of score (ESC 2023 I-B, AHA/ACC 2024); distractors well built, one defensible key. |
| Item | Q3 (focused, CARD-14) | 4 | T2D with eGFR 54 + ACR 38 = very high risk, LDL <1.4 (ESC 2021/2023); sound, but International region leaves ADA <1.8 partly defensible. |
| Item | Case (case, CARD-11) | 5 | Realistic convulsive syncope with bifascicular block + 1st-degree AVB; coherent results, decisive telemetry withheld; key is what a good clinician does. |
| Feedback | questions | 5 | Accurate, well sourced (ESC 2024 CCS, ESC 2023/AHA 2024 HCM, ESC/EAS); Q3 grade fair, credits ADA target; teaches the category point. |
| Feedback | final | 4 | Correct on high-risk ECG, admission, pacing, atropine, DVLA 1 week (checked gov.uk); unordered results marked; 2.5 slightly severe. |

Mean: items 4.5, feedback 4.5.

For a clinician to look at:

- Q1: symptoms 'despite' bisoprolol 5 mg/amlodipine 5 mg for 6 weeks; uptitration is arguable, though ICA remains best given LV dysfunction.
- Q3: region International; ESC <1.4 keyed while ADA <1.8 credited only partially; examiner handled it, but stem could name the guideline frame.
- Final: carotid sinus massage result quoted '(not ordered)' without saying it was unseen or what it would have changed (minor, Rule 10 spirit).

The scorer's form was incomplete (recorded, not a failure):

- feedback dispute has no score

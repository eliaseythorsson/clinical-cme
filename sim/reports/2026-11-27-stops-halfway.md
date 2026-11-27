# Simulation report: stops-halfway, 2026-11-27

| | |
|---|---|
| Result | **automatic checks failed** |
| Persona | stops-halfway |
| Skill version / commit | 5.0.0 / c16e2e6 |
| Examiner / learner model | claude-opus-5-5 / claude-sonnet-5-5 |
| Round | S0001: 1 focused |
| Round score (examiner's grading) | 5.0 |
| Ledger settings | case=true, case_format="unfolding", focused=1, helpers=false, item_order="mcqs_first", mcqs=0, prepare_ahead=false |
| Messages | 5 examiner, 4 learner |
| Clinical quality (logged only) | items 4.5/5 (n=2), feedback 4.5/5 (n=2), overall 4/5 — Clinically sound, well-pitched round; Q1 rubric reached beyond what its stem asked, and the strong case went unanswered. |

## Automatic checks

| Check | Result | Detail |
|---|---|---|
| Blinding: no topic, diagnosis or key shown before the matching answer | **FAIL** | 1 leak(s); 0 topic word(s) or domain name(s) to review; 471 terms searched |
| Every file saved | pass | 4 file(s) compared with the store (data/sessions/S0001.json, data/page.json, data/prepared.json, data/state.json) |
| Log complete and verbatim | pass | sections: a_case, a_questions, case, coded, discussion, fb_questions, feedback, grade_changes, questions, reflection |
| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | **FAIL** | to review: 0 abbreviation(s) not spelled out at first use, 0 mixed time anchor(s); feedback: questions: 4 abbreviation(s), glossary line present, 1 not in it; final: 0 abbreviation(s), glossary line present |
| Listening: a section in the final feedback, the picks in the session document | **FAIL** | 0 pick(s) for 1 topic(s): 0 from the kit, 0 found after grading |
| Prepared feedback: marks before text, the feedback written from the draft | pass | 6 block(s) offered: 1 as prepared, 5 changed, 0 left out; 0 element(s) marked without the learner's words |
| Persona: round saved without the case, its topic still due | pass | 1 item(s) saved; case topic CARD-04, schedule {"last": null, "attempts": 0, "step": 0, "due": null} |

### Writing standards: problems

- the final feedback names the skill's own machinery (sealed): references/standards.md rule 11

### Listening: problems

- the final feedback has no Listening section

### Blinding: findings

| Level | Part | Kind | Term | Examiner message | Where |
|---|---|---|---|---|---|
| leak | case | feedback-notes line | nothing on it in your record yet | 4 | …pic: the first round of the cardiology block, and nothing on it in your record yet. **Q1 (focused)** **Rubric** - ✓ the decision: a… |

### Writing standards: to review

Found by the lint's heuristics (`references/standards.md`, "The lint"): each is for a person to judge and none fails the run.

| Rule | Where | What |
|---|---|---|
| 5.3 | the questions feedback | SV |

### Examiner text that is not in the log

Opening lines, the close message and prompts are not logged by design; a feedback or case paragraph here would be a finding.

- message 2: Today's round: 1 focused question + the case, about 35 minutes. Block: Cardiology, round 1…
- message 9: Saved: session S0001, one focused question on pulmonary embolism, 5/5. The case was not pl…
- message 9: Your reflection added one point to the plan: risk stratification after a confirmed pulmona…
- message 9: With your target of three sessions a week, the next round fits any time from tomorrow.…

## Waiting time per step

Wait: from the learner's message to the examiner's first message after it (includes the relay). Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.

| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) |
|---|---|---|---|---|---|---|
| 1 | start of round | 66.7 | 256.4 | 1 | 1542 | – |
| 2 | after the answers to the questions | 38.9 | 44.5 | 1 | 6798 | 8.3 |
| 3 | after the case answer | 26.9 | 53.0 | 2 | 1309 | 4.4 |
| 4 | after the reflection | 144.9 | 220.6 | 1 | 511 | 29.4 |

Total wait 277.4 s; longest wait 144.9 s; whole run 540.9 s.

## Clinical quality

Scored 1–5 by a separate agent after the round (claude-opus-5-5). Kept for comparison over time; it is never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`).

| | What | Score | Note |
|---|---|---|---|
| Item | Q1 (focused, CARD-08) | 4 | Accurate ESC 2019 PE content, Wells arithmetic right; but stem asks only diagnosis+discriminators while rubric grades CTPA/no D-dimer route. Easy for IM. |
| Item | Case (case, CARD-04, not answered) | 5 | Realistic bifascicular block syncope with timolol twist; telemetry left to learner; key (admit, monitor, DDD pacing without washout) fits ESC 2018/2021. |
| Feedback | questions | 5 | Fair 5/5, correct ESC citation, answers the ALT doubt well and usefully corrects the bedside clot-burden inference; teaches the decisive point. |
| Feedback | final | 4 | Accurate gap summary and good reflection prompt; minor slip calling the case 'unseen' though it had been presented. |

Mean: items 4.5, feedback 4.5.

For a clinician to look at:

- Q1: rubric element 3 (CTPA without D-dimer, anticoagulate) is graded but the stem asks only for diagnosis and discriminators; align stem or rubric.

The scorer's form was incomplete (recorded, not a failure):

- feedback dispute has no score

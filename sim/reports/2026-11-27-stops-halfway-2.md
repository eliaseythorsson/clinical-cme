# Simulation report: stops-halfway, 2026-11-27

| | |
|---|---|
| Result | **automatic checks failed** |
| Persona | stops-halfway |
| Skill version / commit | 5.0.0 / b1b1f35 |
| Examiner / learner model | claude-opus-5-5 / claude-sonnet-5-5 |
| Round | S0001: 1 focused |
| Round score (examiner's grading) | 3.5 |
| Ledger settings | case=true, case_format="unfolding", focused=1, helpers=false, item_order="mcqs_first", mcqs=0, prepare_ahead=false |
| Messages | 6 examiner, 4 learner |
| Clinical quality (logged only) | items 5.0/5 (n=2), feedback 4.5/5 (n=2), overall 5/5 — One strong, guideline-accurate focused item with fair grading and clear teaching; a well-built syncope case presented but unanswered. |

## Automatic checks

| Check | Result | Detail |
|---|---|---|
| Blinding: no topic, diagnosis or key shown before the matching answer | **FAIL** | 1 leak(s); 0 topic word(s) or domain name(s) to review; 466 terms searched |
| Every file saved | pass | 4 file(s) compared with the store (data/sessions/S0001.json, data/page.json, data/prepared.json, data/state.json) |
| Log complete and verbatim | pass | sections: a_case, a_questions, case, coded, discussion, fb_questions, feedback, grade_changes, notes, questions, reflection |
| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | pass | to review: 0 abbreviation(s) not spelled out at first use, 0 mixed time anchor(s); feedback: questions: 8 abbreviation(s), glossary line present, 2 not in it; final: 4 abbreviation(s), glossary line present |
| Listening: a section in the final feedback, the picks in the session document | pass | 0 pick(s) for 1 topic(s): 0 from the kit, 0 found after grading |
| Prepared feedback: marks before text, the feedback written from the draft | pass | 7 block(s) offered: 2 as prepared, 5 changed, 0 left out; 0 element(s) marked without the learner's words |
| Persona: round saved without the case, its topic still due | pass | 1 item(s) saved; case topic CARD-11, schedule {"last": null, "attempts": 0, "step": 0, "due": null} |

### Blinding: findings

| Level | Part | Kind | Term | Examiner message | Where |
|---|---|---|---|---|---|
| leak | case | feedback-notes line | talking sensibly within a minute or two | 5 | …ute". He was pale, and he had wet himself. He was talking sensibly within a minute or two and remembers sitting at the table and then lying… |

### Writing standards: to review

Found by the lint's heuristics (`references/standards.md`, "The lint"): each is for a person to judge and none fails the run.

| Rule | Where | What |
|---|---|---|
| 5.3 | the questions feedback | FLJ |
| 5.3 | the questions feedback | IT |

### Examiner text that is not in the log

Opening lines, the close message and prompts are not logged by design; a feedback or case paragraph here would be a finding.

- message 2: Today's round: 1 focused question + the case, about 35 minutes. Block: Cardiology, round 1…
- message 10: Saved: session S0001 — one focused question on lipids and cardiovascular prevention, score…
- message 10: Your reflection matched the grading (comfort 3 against 3.5), so the shaky point you named …
- message 10: Your target is three sessions a week, so the next round fits any time from tomorrow.…

## Waiting time per step

Wait: from the learner's message to the examiner's first message after it (includes the relay). Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.

| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) |
|---|---|---|---|---|---|---|
| 1 | start of round | 147.8 | 395.5 | 1 | 1823 | – |
| 2 | after the answers to the questions | 196.3 | 209.2 | 2 | 10770 | 15.1 |
| 3 | after the case answer | 62.8 | 76.0 | 2 | 2698 | 56.0 |
| 4 | after the reflection | 249.9 | 255.0 | 1 | 534 | 44.3 |

Total wait 656.8 s; longest wait 249.9 s; whole run 1045.9 s.

## Clinical quality

Scored 1–5 by a separate agent after the round (claude-opus-5-5). Kept for comparison over time; it is never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`).

| | What | Score | Note |
|---|---|---|---|
| Item | Q1 (focused, CARD-14) | 5 | Accurate ESC/EAS keying: DM with eGFR<45 is severe TOD, very high risk, LDL<1.4 and >=50%; ALT and rosuva renal traps well built; eGFR alone decides, no Rule 7 issue. |
| Item | Case (case, CARD-11, not answered) | 5 | Coherent: seated, no prodrome, PR 220 + RBBB/LAFB; seizure and tamsulosin lures fair; telemetry and orthostatics held in bank; key matches ESC 2018/2021. |
| Feedback | questions | 4 | Claims correct and sourced, grades fair, decisive point well taught; quibble: 'eGFR 30-59 without albuminuria' as high risk misstates ESC moderate-CKD bands. |
| Feedback | final | 5 | Gap stated precisely and correctly, calibration read fairly, correct DOIs for reading, honest about unverified listening; case set aside cleanly. |

Mean: items 5.0, feedback 4.5.

For a clinician to look at:

- Q1 feedback: example of high risk as 'moderate CKD (eGFR 30-59) without albuminuria' is loose; ESC 2021 moderate CKD is eGFR 30-44 ACR<3 or 45-59 ACR 3-30 (judged from memory, no web search).

The scorer's form was incomplete (recorded, not a failure):

- feedback dispute has no score

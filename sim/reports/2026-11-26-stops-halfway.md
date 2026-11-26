# Simulation report: stops-halfway, 2026-11-26

| | |
|---|---|
| Result | all automatic checks passed |
| Persona | stops-halfway |
| Skill version / commit | 4.3.1 / 4849242 |
| Examiner / learner model | claude-opus-5-5 / claude-sonnet-5-5 |
| Round | S0001: 1 focused |
| Round score (examiner's grading) | 5.0 |
| Ledger settings | case=true, case_format="unfolding", focused=1, helpers=false, item_order="mcqs_first", mcqs=0, prepare_ahead=false |
| Messages | 5 examiner, 4 learner |
| Clinical quality (logged only) | items 4.0/5 (n=2), feedback 4.0/5 (n=2), overall 4/5 — Short round, one item answered: clinically sound, well pitched for internal medicine in Europe; small key/stem inconsistencies and a non-ESC source for the dissection briefing. |

## Automatic checks

| Check | Result | Detail |
|---|---|---|
| Blinding: no topic, diagnosis or key shown before the matching answer | pass | 0 leak(s); 3 topic word(s) or domain name(s) to review; 287 terms searched |
| Every file saved | pass | 4 file(s) compared with the store (data/sessions/S0001.json, data/page.json, data/prepared.json, data/state.json) |
| Log complete and verbatim | pass | sections: a_case, a_questions, case, coded, discussion, fb_questions, feedback, grade_changes, notes, questions, reflection |
| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | pass | to review: 3 abbreviation(s) not spelled out at first use, 0 mixed time anchor(s); feedback: questions: 14 abbreviation(s), glossary line present, 3 not in it; final: 6 abbreviation(s), glossary line present, 2 not in it |
| Listening: a section in the final feedback, the picks in the session document | pass | 0 pick(s) for 1 topic(s): 0 from the kit, 0 found after grading |
| Persona: round saved without the case, its topic still due | pass | 1 item(s) saved; case topic CARD-02, schedule {"last": null, "attempts": 0, "step": 0, "due": null} |

### Blinding: findings

| Level | Part | Kind | Term | Examiner message | Where |
|---|---|---|---|---|---|
| review | case | topic word | heart | 2 | …ears, stopped 5 years ago). Temperature 36.8 °C, heart rate 92/min regular, blood pressure 138/84 mmHg i… |
| review | case | topic word | heart | 4 | … its supplementary material. Byrne RA et al., Eur Heart J 2023;44:3720–3826. - On posterior leads, the Fo… |
| review | case | topic word | heart | 6 | …nt of acute coronary syndromes (Byrne et al., Eur Heart J 2023), section 3 on ECG diagnosis and initial t… |

### Writing standards: to review

Found by the lint's heuristics (`references/standards.md`, "The lint"): each is for a person to judge and none fails the run.

| Rule | Where | What |
|---|---|---|
| 5.1 | the questions as presented | PR |
| 5.1 | the questions as presented | QRS |
| 5.1 | the questions as presented | ST |
| 5.3 | the questions feedback | UA |
| 5.3 | the questions feedback | BMJ |
| 5.3 | the questions feedback | RA |
| 5.3 | the final feedback | STEMI |
| 5.3 | the final feedback | ST |

### Examiner text that is not in the log

Opening lines, the close message and prompts are not logged by design; a feedback or case paragraph here would be a finding.

- message 2: Today's round: 1 focused question + the case, about 35 minutes. Block: Cardiology, round 1…
- message 9: - **Tested:** acute coronary syndrome (Question 1, focused). Score 5/5. - **Coming up:** 2…
- message 9: Your reflection added a new topic to the blueprint: the aortic-imaging question you raised…
- message 9: You're aiming for 3 sessions a week, so the next one fits in the next day or two.…

## Waiting time per step

Wait: from the learner's message to the examiner's first message after it (includes the relay). Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.

| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) |
|---|---|---|---|---|---|---|
| 1 | start of round | 52.4 | 199.9 | 1 | 1694 | – |
| 2 | after the answers to the questions | 64.5 | 71.8 | 1 | 9920 | 9.8 |
| 3 | after the case answer | 27.1 | 41.0 | 2 | 2144 | 4.8 |
| 4 | after the reflection | 28.3 | 36.7 | 1 | 615 | 5.7 |

Total wait 172.3 s; longest wait 64.5 s; whole run 361.3 s.

## Clinical quality

Scored 1–5 by a separate agent after the round (claude-opus-5-5). Kept for comparison over time; it is never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`).

| | What | Score | Note |
|---|---|---|---|
| Item | Q1 (focused, CARD-01) | 4 | Accurate, ESC-aligned posterior OMI item with a good dissection distractor; 'main alternative' is ambiguous and key rubric cites RBBB/T-inversion noise absent from the stem. |
| Item | Case (case, CARD-02, not answered) | 4 | Presented, unanswered. Coherent, realistic NSAID-precipitated de novo HFrEF; bank fits (urine Na 38, 70 mL/h, ferritin 64/TSAT 12%); minor eGFR 37 vs 38 mismatch in key. |
| Feedback | questions | 4 | Fair 5/5; teaches V1-V3 vs V4-V6 well; ADD-RS briefing sound (Goodacre BMJ 2024 checked by web search) but ESC 2024 aortic guideline not cited; pearl wording is muddled. |
| Feedback | final | 4 | Correct stop handling, accurate gap summary and calibration, relevant ESC 2023 reading; listening section adds noise but nothing misleading. |

Mean: items 4.0, feedback 4.0.

For a clinician to look at:

- Q1 key rubric point 4 refers to an old RBBB-like pattern and prior anterior T inversion that the stem never shows.
- Q1 feedback cites a BMJ review for dissection work-up; for a European learner the ESC 2024 aortic disease guideline algorithm is the primary source.
- Case key gives eGFR 38 for the day-1 SGLT2i decision while the bank says eGFR 37 (immaterial to the decision).

The scorer's form was incomplete (recorded, not a failure):

- feedback dispute has no score

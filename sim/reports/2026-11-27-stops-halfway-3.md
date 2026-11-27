# Simulation report: stops-halfway, 2026-11-27

| | |
|---|---|
| Result | all automatic checks passed |
| Persona | stops-halfway |
| Skill version / commit | 7.0.0 / bdab9c6 |
| Examiner / learner model | claude-opus-5-5 / claude-opus-5-5 |
| Round | S0001: 1 focused |
| Round score (examiner's grading) | 4.0 |
| Ledger settings | case=true, case_format="unfolding", focused=1, helpers=false, item_order="mcqs_first", mcqs=0, prepare_ahead=false |
| Messages | 5 examiner, 4 learner |
| Clinical quality (logged only) | items 3.5/5 (n=2), feedback 4.0/5 (n=2), overall 4/5 — Accurate, well-sourced lipid item and feedback; graded fairly. Main flaw: ESC-only target in an international round where ACC/AHA 2026 offers <1.8. |

## Automatic checks

| Check | Result | Detail |
|---|---|---|
| Blinding: no topic, diagnosis or key shown before the matching answer | pass | 0 leak(s); 2 topic word(s) or domain name(s) to review; 489 terms searched |
| Every file saved | pass | 4 file(s) compared with the store (data/sessions/S0001.json, data/page.json, data/prepared.json, data/state.json) |
| Log complete and verbatim | pass | sections: a_case, a_questions, case, coded, discussion, fb_questions, feedback, grade_changes, notes, questions, reflection |
| Writing standards: abbreviations, one time anchor, the feedback's glossary line (rules 5–6) | pass | to review: 0 abbreviation(s) not spelled out at first use, 0 mixed time anchor(s); feedback: questions: 9 abbreviation(s), glossary line present, 5 not in it; final: 3 abbreviation(s), glossary line present |
| Listening: a section in the final feedback, the picks in the session document | pass | 0 pick(s) for 1 topic(s): 0 from the kit, 0 found after grading |
| Prepared feedback: marks before text, the feedback written from the draft | pass | 7 block(s) offered: 1 as prepared, 6 changed, 0 left out; 0 element(s) marked without the learner's words |
| Persona: round saved without the case, its topic still due | pass | 1 item(s) saved; case topic CARD-11, schedule {"last": null, "attempts": 0, "step": 0, "due": null} |

### Blinding: findings

| Level | Part | Kind | Term | Examiner message | Where |
|---|---|---|---|---|---|
| review | questions | topic word | cardiovascular | 2 | …nsion; gout (last attack two years ago); no known cardiovascular disease. Medications: metformin 1 g twice daily, … |
| review | questions | topic word | lipids | 2 | …te 0.34 mmol/L; ALT 38 U/L; TSH 1.9 mU/L. Fasting lipids: total cholesterol 5.6 mmol/L, low-density lipopr… |

### Writing standards: to review

Found by the lint's heuristics (`references/standards.md`, "The lint"): each is for a person to judge and none fails the run.

| Rule | Where | What |
|---|---|---|
| 5.3 | the questions feedback | QRISK |
| 5.3 | the questions feedback | UK |
| 5.3 | the questions feedback | JACC |
| 5.3 | the questions feedback | FLJ |
| 5.3 | the questions feedback | RS |

### Examiner text that is not in the log

Opening lines, the close message and prompts are not logged by design; a feedback or case paragraph here would be a finding.

- message 2: Today's round: 1 focused question + the case, about 35 minutes. Block: Cardiology, round 1…
- message 9: - **Saved:** session S0001 — CARD-14 Lipids and cardiovascular prevention, score 4/5; your…

## Waiting time per step

Wait: from the learner's message to the examiner's first message after it (includes the relay). Turn: until the examiner's turn ended, behind-the-scenes work included. Learner: the persona's own time.

| Step | | Wait (s) | Turn (s) | Examiner messages | Characters | Learner (s) |
|---|---|---|---|---|---|---|
| 1 | start of round | 61.0 | 285.1 | 1 | 1820 | – |
| 2 | after the answers to the questions | 113.2 | 125.4 | 1 | 9900 | 14.2 |
| 3 | after the case answer | 104.7 | 163.4 | 2 | 2335 | 5.9 |
| 4 | after the reflection | 81.9 | 486.0 | 1 | 605 | 6.8 |

Total wait 360.8 s; longest wait 113.2 s; whole run 682.7 s.

## Clinical quality

Scored 1–5 by a separate agent after the round (claude-opus-5-5). Kept for comparison over time; it is never a pass bar (`docs/adr/0004-no-clinical-correctness-judge.md`).

| | What | Score | Note |
|---|---|---|---|
| Item | Q1 (focused, CARD-14) | 3 | Core accurate (DM+eGFR 52+A2 = ESC very high risk; high-intensity statin). Target key ESC-only; ACC/AHA 2026 <70 mg/dL is a 2nd defensible goal; key cites 2018 (web-checked). |
| Item | Case (case, CARD-11, not answered) | 4 | Coherent, realistic bifascicular-block syncope with fair twists; telemetry withheld per rule 7. Rubric's 'avoid CT head' is shaky: age 76, head strike after LOC. |
| Feedback | questions | 4 | Fair 4/5; NICE credited, ESC goals right, 2026 ACC/AHA added (checked). Says <1.8 'would have been credited' though rubric gives partial; NICE recheck timing loose. |
| Feedback | final | 4 | Clean stop, case deferred; gap stated precisely and retestably; calibration and reading accurate. Coding line is jargon for the learner. |

Mean: items 3.5, feedback 4.0.

For a clinician to look at:

- Q1 key: for region International, ACC/AHA 2026 (Mar 2026) LDL-C goal <70 mg/dL for high risk is defensible; key marks <1.8 partial and cites ACC/AHA 2018.
- Q1 feedback: says a <1.8 goal 'would have been credited', inconsistent with the rubric's partial mark.
- Q1 rubric wording 'eGFR 30-59 with albuminuria' is imprecise: ESC severe TOD is eGFR <45 alone, or 45-59 with microalbuminuria.
- Case rubric: penalising CT head is questionable in a 76-year-old with head strike and LOC (head-injury rules favour CT); accept it if ordered.

The scorer's form was incomplete (recorded, not a failure):

- feedback dispute has no score

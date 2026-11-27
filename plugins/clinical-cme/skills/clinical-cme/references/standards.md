# Standards: the rulebook for writing items

The numbered rules every item, key and kit of a round must meet. They are the same for every
learner; what differs per learner (guideline region, specialty, units, profile, mix) is
settings, and reaches the author through the plan. Each rule is written here once. The briefs
(`author.md`, `case_design.md`, `evidence_check.md`, `feedback_guide.md`, `preparing.md`,
SKILL.md) cite it by number ("rule 5") and do not restate it.

Who reads what: the **author** all of it, with the parts a checker needs kept in their own
files so that it reads them alone: rule 2 (`standards_region.md`), rule 8 (`standards_kits.md`,
its Listening section in `standards_listening.md`) and rule 12 (`standards_positions.md`); the
**checker** those four files only; the **examiner** none of it
before grading, and all of it when it writes items itself. What binds the feedback is in
`feedback_guide.md`: rules 5.3, 10 and 11 are written there, and the author reads them there for
the kits' prepared blocks (rule 8). This file holds no content of any round, so anyone may read
it at any time.

| Rule | Title | Checked by `cme.py` |
|---|---|---|
| 1 | Blinding | `present` prints only the blocks; the simulation's blinding check |
| 2 | Guideline region | – |
| 3 | Units and drug names | – |
| 4 | Pitch | – |
| 5 | Abbreviations | lint, judgement call; the simulation's standards check |
| 6 | One time anchor per case | lint, judgement call; the simulation's standards check |
| 7 | Crux tests are requested, not given | – (pre-flight line 16; the simulation's quality scorer) |
| 8 | What a kit contains | lint, blocking (sections and prepared blocks); the listening candidates' form, judgement call |
| 9 | Key headers | lint, blocking |
| 10 | Results the learner did not see (in `feedback_guide.md` §6.2) | – (the simulation's quality scorer) |
| 11 | Text for the learner speaks plainly (in `feedback_guide.md` §6.3) | `save` warns; the simulation's standards check fails the run |
| 12 | The learner's position notes | – (nothing a lint can check) |

Numbers are never reused or renumbered: a new rule gets the next number, a withdrawn one
keeps its number with the word "withdrawn". How the lint works: last section (`standards_lint.md`).

## Rule 1. Blinding

A round is blind part by part: the short questions until all of them are answered, the case
until its last answer. Until a part's answers are in, nothing reveals what it tests.

1. **The text to present** names no topic, domain, diagnosis, organ system or blueprint ID,
   and no reason for selection (due, scored poorly, open gap, new topic). No titles: "Case"
   and "Question 1–N" ("Question 4 — focused"). The theme of the block is known to the
   learner from the opening line; it is never written into an item, and no item's domain is.
2. **Present and bank blocks hold no key.** Keys, alternatives, rubrics and pre-flight lines
   sit outside `<!-- present: … -->` blocks; the results bank holds results, the course and
   the Stage 2 questions, and no diagnosis.
3. **Tool activity is neutral.** Before a part's answers are in: no web search, no opened
   resource and no task item that names its topic; tool-call descriptions are generic ("Read
   the ledger", "Prepare the round", "Check sources"). Evidence is checked after the answers,
   or by a checker whose prompt carries no content.
4. **Reasoning is neutral.** The learner may see a summary of the assistant's thinking: items
   are drafted in the sealed files, never in reasoning, where they are "the case" and "Q1–Q4"
   with no diagnosis, topic, finding, test, drug or answer letter.
5. **The questions' feedback leaves the case sealed.** It reveals the questions' topics and
   why they were chosen, and nothing about the case: not its topic or domain, not that it is
   "something different".
6. **A requested domain may be acknowledged** ("a cardiology round"); the topic stays hidden.
7. **No previews.** The close says how many items are due and when, never which.

## Rule 2. Guideline region

Written in `standards_region.md`, so that a checker reads it without the rest of the rulebook:
items are written, keyed, checked and graded against the guidelines of the learner's region, in
the edition for their specialty.

## Rule 3. Units and drug names

1. Laboratory units follow the plan's `lab_units` (SI by default: mmol/L, µmol/L, g/L,
   ×10⁹/L); blood gases follow `blood_gas_units` (mmHg by default for pCO₂ and pO₂; kPa if
   set). Presented text, keys, kits and feedback all use them.
2. Raw numbers only: no derived value (anion gap, corrected calcium, A–a gradient, osmolar
   gap) is calculated for the learner.
3. Drugs carry their international non-proprietary name; the regional name is added where it
   differs and the learner's region uses it.

## Rule 4. Pitch

Items are pitched to the learner as they describe themselves, in two paragraphs of their own
words: `journey` (where you are: stage of training or career, specialty, how independently
they work, which decisions they are comfortable making) and `aim` (where you're aiming: an
exam, a level to reach, areas to strengthen). The plan's profile carries both for the
author; the `start` output gives the examiner the same two as `pitch`. Read both in full,
with the `specialty`, before writing or grading.

1. **Which decisions are tested.** The decisions this learner makes unaided now, and those
   one step beyond, towards the aim: for a student or intern, recognition, first steps and
   when to call for help; for a resident, the work-up and management they run on call; for
   an attending, the decisions with no one to ask, including those at the edge of the
   specialty; for a senior learner aiming at specialist-level decisions outside their own
   field, the calls a subspecialist would make. Nothing the learner says they already do
   comfortably is tested for its own sake, and nothing is tested that their stage never
   decides.
2. **How the feedback is written**, and how far behind the recommendation it goes (the
   evidence depth, `evidence_depth.md`): in `feedback_guide.md` §1.
   The kits' prepared blocks (rule 8) are written to it.
3. **Which sources.** An aim that names an exam is keyed to that exam's standard sources (its
   syllabus, the textbooks and guidelines it examines from); every other aim by rule 2. How
   the feedback handles the difference: `feedback_guide.md` §1.
4. **What the pitch never does.** It never lowers the standard of the key: the right answer
   is the same for every learner; the pitch chooses the question and the explanation.
5. **Only the paragraphs.** The stage label and goal tags kept with the paragraphs
   (`journey_label`, `aim_tags`) are for display on the learner's page. They are not in the
   plan and are never used to write, key or grade an item. A paragraph that is empty means
   the learner has not said: pitch to a clinician practising independently in the plan's
   `specialty`.

## Rule 5. Abbreviations

1. Every abbreviation is spelled out once per session, where the presented text first uses
   it: "alanine aminotransferase (ALT)" or "ALT (alanine aminotransferase)". The session's
   presented text runs in this order: the short questions, the case, the results bank. Later
   uses stand alone.
2. The abbreviations on this list need no spelling out. The list is edited here and nowhere
   else: the lint reads it from this file.

   <!-- common-abbreviations -->
   IV, IM, SC, ED, ICU, HDU, BP, HR, RR, GCS, BMI,
   ECG, EEG, CT, MRI, CXR, CSF, ABG,
   PR, QRS, QT, QTc, ST, AV, RBBB, LBBB,
   CRP, ESR, INR, APTT, WBC, WCC, RBC, MCV, ALT, AST, ALP, GGT, LDH, CK, TSH, PTH, BNP, NT,
   HIV, DNA, RNA, PCR, COVID, NSAID, ACE, ARB, MCQ,
   WHO, ESC, NICE, AHA, ACC, IDSA, KDIGO, EULAR, ACR, ADA, BTS, ERS, ASCO, NCCN
   <!-- /common-abbreviations -->

   The list holds what every clinical reader meets daily: routes and care settings, vital
   signs and scores, the routine tests and their parts (ECG intervals and segments, routine
   blood tests), and the names of the major guideline societies. Drug classes beyond the
   commonest (DOAC, SGLT2i, ARNI) and anything specialised are spelled out. Words written with
   lower-case letters (eGFR, HbA1c, SpO₂, NT-proBNP's "pro") are not caught by the lint and
   need no entry.

3. Each feedback message opens with a one-line glossary of the abbreviations it uses, the
   listed ones excepted: the line that starts "Abbreviations:" is written in
   `feedback_guide.md` §6.1. Presented items get no glossary: there the rule is 5.1,
   in the text itself.

## Rule 6. One time anchor per case

Every timing in a case, its results bank included, counts from a single anchor: either a
named event (admission as day 0: "day 3", "6 hours after admission", "two days before
admission") or now ("3 hours ago", "since this morning"). The two are never mixed. A short
question's vignette follows the same rule on its own.

## Rule 7. Crux tests are requested, not given

When the decisive test is one that clinicians often fail to order, its result is not in the
stem or in the opening of the case. In a case the learner must ask for it (it is in the
results bank, and on the bank's "Add if not ordered" line); in a short question the item
either tests that step (a focused question with aspect `testing`) or does not turn on the
result. The exception is an `interpretation` question, where the result to interpret is the
question (`case_design.md` §11.1).

1. **What counts as a crux test.** A test is the crux of an item when all three hold:
   - its result settles the diagnosis or the decision: with it in hand, the alternatives no
     longer have to be weighed;
   - it is outside the routine set for the setting (`case_design.md` §3), so somebody has to
     think of it;
   - thinking of it is the step that goes wrong in practice: the test is known for being
     forgotten, ordered late or ordered only once the diagnosis has been suggested.

   A routine result that happens to be decisive (a potassium, an ECG) is not a crux test: it
   is given with the rest. A specialised test that is not the crux falls under the rarity
   budget alone (`case_design.md` §4).
2. **How to decide.** Read the draft with the result deleted. If the item is now harder
   mainly because the learner has to think of the test, it is a crux test and the result
   stays out. If the learner would order it as a matter of course and the difficulty lies in
   what to do with it, it is not.
3. **The example this rule comes from** (round S0037). A short question on a drowsy patient
   taking valproate gave the plasma ammonia in the stem. The ammonia was correctly drawn and
   correctly reported, and it gave the diagnosis away: in practice the forgotten step is
   asking for it. Written to this rule, the stem stops before the test and asks what to
   request and why (aspect `testing`), or the patient becomes a case and the ammonia waits
   in the results bank.
4. **In the feedback**: `feedback_guide.md` §6.2. The rubric has an element for asking for
   the crux test, so that the step is graded.

## Rule 8. What a kit contains

Written in `standards_kits.md` (its Listening section in `standards_listening.md`), so that a
checker reads it without the rest of the rulebook: the kits hold the feedback's finished text
in prepared blocks, checked with the round.

## Rule 9. Key headers

Every item's key starts with a small header in exactly this form. The state engine reads it
and fills the round record from it, so the examiner adds only the grading; a missing or
misspelt field stops the round from being saved.

```
<!-- key: Q1 -->
type: mcq
topic: CARD-03
label: Atrial fibrillation
reason: due
retests: G0004
subtopic: CARD-03a
stem_summary: New AF after hip surgery, when to anticoagulate
<!-- /key -->
```

1. The first line names the item: `Q1`, `Q2`, … with the number the question has in the text
   to present (MCQs first, then focused questions), and `case` for the case.
2. One header per item; one `field: value` per line, nothing else between the two markers.
3. The fields are those of this table and no others. An optional field that does not apply
   is left out, not left empty.
4. With a two-level blueprint, `subtopic` names the sub-topic of `topic` the item was written
   to (the plan's `subtopic.id`). `save` refuses a sub-topic the blueprint does not list under
   that topic, and `keys --plan` (with `finish-prepare`) asks for the planned one.

<!-- key-header-table: generated by `cme.py key-table`; do not edit by hand -->
| Field | MCQ | Focused question | Case | What to write |
|---|---|---|---|---|
| `type` | required | required | required | `mcq`, `focused` or `case` |
| `topic` | required | required | required | the blueprint ID (for a `new_in_domain` item, the one you chose) |
| `label` | required | required | required | the topic's label in the blueprint |
| `reason` | required | required | required | the plan's `reason_code` for the item, copied as it is |
| `stem_summary` | required | required | – | about ten words on what the stem asks, for the list of stems already used |
| `aspect` | – | required | – | one of `diagnosis`, `interpretation`, `testing`, `management`, `disposition`, `prevention`, `prognosis` |
| `patient` | – | – | required | age and sex ("74F") |
| `setting` | – | – | required | where the case takes place ("ED") |
| `presentation` | – | – | required | the presenting problem ("confusion after a marathon") |
| `diagnosis` | – | – | required | the final diagnosis |
| `twist` | – | – | optional | what makes this case different from others on the topic |
| `domain` | optional | optional | optional | the domain code, only when the topic ID does not start with it |
| `retests` | optional | optional | optional | the plan's `retest_gap.id`, on an item written on that gap's decision point; otherwise leave the line out |
| `subtopic` | optional | optional | optional | the plan's `subtopic.id`, where the blueprint has sub-topics for the topic (for a `new_in_domain` item, the sub-topic you wrote to); otherwise leave the line out |
<!-- /key-header-table -->

The case's `patient`, `setting`, `presentation`, `diagnosis` and `twist` are the compact
description kept for the novelty check of later rounds.

```
<!-- key: Q4 -->
type: focused
topic: HEME-04
label: Anticoagulation reversal
reason: gap
aspect: management
stem_summary: Warfarin, INR 9, minor gum bleeding, what now
<!-- /key -->

<!-- key: case -->
type: case
topic: RENAL-02
label: Hyponatraemia / hypernatraemia
reason: due
patient: 34M
setting: ED
presentation: confusion after a marathon
diagnosis: exercise-associated hyponatraemia
twist: looked hypovolaemic
<!-- /key -->
```

**The rubric block.** A focused question and the case carry their rubric beside the key header,
in the same sealed file and outside the text to present, one expected element per line; the
case's elements are grouped under a line `Stage 1` and a line `Stage 2` (a one-step case has
one group, or none). An MCQ has none: its key is the correct option. The engine copies the
elements into the grading form, where the examiner marks each hit, partial or missed, so
write each as one line that can be marked against an answer (what makes a good element:
`case_design.md` §11.3 for a focused question; for the case, the decisions of each stage).

```
<!-- rubric: Q4 -->
- the decision: hold warfarin and give oral vitamin K
- the decisive reason: INR above 9 with only minor bleeding
- the safety element: no prothrombin complex concentrate without major bleeding
<!-- /rubric -->

<!-- rubric: case -->
Stage 1
- exercise-associated hyponatraemia high in the differential
- serum and urine osmolality and urine sodium requested
Stage 2
- hypertonic saline bolus for severe symptoms, with the correction limit
<!-- /rubric -->
```

4. A rubric block starts `<!-- rubric: Q4 -->` (the key's own id) and ends `<!-- /rubric -->`;
   one per focused question and one for the case, each with at least one element. A missing,
   empty or unclosed block, one for an MCQ or for a key with no header, or one inside a
   `present` or `bank` block stops the round as a bad header does.

## Rule 10. Results the learner did not see

Written in `feedback_guide.md` §6.2, because it binds the feedback: the
feedback teaches with every result the case was written with, and a result the learner did not
see is never quoted as if it had been shown. The author follows it there in the case's prepared
blocks; a result a block may need is in the results bank, so that Stage 2 can show it.

## Rule 11. Text for the learner speaks plainly

Written in `feedback_guide.md` §6.3: everything the learner reads (items,
results, feedback, the close) is written for a clinician and never names the skill's own
machinery. It binds the items and the results bank as much as the feedback.

## Rule 12. The learner's position notes

Written in `standards_positions.md`, so that a checker reads it without the rest of the
rulebook: no item is keyed on a point the learner holds a position on, and they are never
marked down on it.

## The lint

How `cme.py` lints a round against these rules (what blocks, what is a judgement call, what the
heuristics look at): `standards_lint.md`. The author reads it when `keys` prints a problem or a
finding to review.

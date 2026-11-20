# Case and question design

Read this before writing any item. The goal is that the learner reasons from the same
information a clinician would actually have at that point in the encounter, and that
nothing in the format, the order of presentation or the choice of tests reveals the
answer before they commit.

## 1. Topic blinding

Until every answer in the round is in:

- Do not name the topic, domain, diagnosis, organ system or blueprint ID.
- Do not say why the item was chosen (due for review, scored poorly last time, open gap,
  self-reported gap, new topic). That belongs in the post-answer reveal.
- Do not title cases ("A case of fever after valve replacement"). Use "Case" and
  "Question 1–N" (focused questions too: "Question 4 — focused").
- Keep tool activity neutral. Before answers are in, run no web searches, open no
  resource files and create no task-list items that name the topic, and keep
  command descriptions generic ("Read the ledger", "Plan today's items"). Do evidence
  checks after the answers are committed.
- Keep your reasoning neutral too. The learner may see a summary of your thinking, so all
  drafting happens in the sealed files `sealed_questions.md` and `sealed_case.md` (SKILL.md,
  "Sealed drafting"). In thinking, items are "the case" and "Q1–Q4"; no diagnosis, topic,
  finding, test, drug or answer letter appears there until every answer is in.
- If the learner asks for a domain ("give me a cardiology round"), you may acknowledge
  the domain they chose, but the specific topic stays hidden.
- Do not preview upcoming topics at the end of a session ("next up: hyponatraemia").
  Say how many items are due and when.

## 2. Short questions first, and on other topics

The short questions — the MCQs and any focused questions (§11), in that order, in one message —
are presented and answered **before** the case is shown (`config.item_order` `mcqs_first`). The
case therefore cannot help with them. To stop them from cueing the case, they must be about
something else entirely. Everything below about MCQs applies to focused questions too. `plan`
enforces this:

- **Outside a domain round**, no MCQ comes from the case's domain.
- **No MCQ is related to the case topic.** Related means a blueprint cross-reference in either
  direction ("(see RENAL-02)", "(see also PULM/HEME)"), a shared reference, or a shared
  significant word in the topic labels (for example two "sepsis" topics).
- MCQs prefer domains different from each other as well.
- **In a domain round** ("a cardiology round"), MCQs may share the domain, but never the case's
  topic or anything related to it.

Each MCQ and focused item from `plan` carries a `separation` note. The selector works on topic
labels; you must also check the content:

- No MCQ or focused stem, option or explanation may name, test or hint at the case's diagnosis, its
  leading alternatives, its key investigation or its management, even through a shared
  mechanism. For example, with a hyponatraemia case, avoid an MCQ on thiazide adverse effects
  or on osmolality.
- If a selected MCQ topic cannot be written without touching the case, pick another untested
  topic from a different domain and record it as `new` with the reason.
- MCQs on related themes stay apart in a later round, not in this one.
- The short questions must not cue one another either: no two share a diagnosis, key test or
  drug, and a focused question's vignette must not answer an MCQ presented beside it.

## 3. Standard information: always provide it, whether or not it matters

Every vignette carries the same scaffolding, so the presence of a section is never a
clue. Write it as a ward clinician would document it.

**History** (always all of these, concise):
- Presenting complaint and history in the patient's or referrer's words, with the
  timeline.
- Past medical history: 2–4 items, mostly common conditions, usually including at least
  one that is not relevant to today's problem.
- Medications, including over-the-counter drugs and supplements, with doses where a
  clinician would know them. Allergies.
- Social history: occupation, living situation and functional status, smoking
  (pack-years), alcohol (units or grams per week), other substances, and recent travel
  ("none", or something ordinary, as the default).
- Family history: usually vague and non-contributory, the way patients actually report
  it ("father had 'heart trouble', died at 78; mother has thyroid problems; no known
  inherited conditions").

**Hospital cases (ED, ward, ICU or consult): the standard admission workup.** Always give:
- Vital signs: temperature, heart rate, blood pressure, respiratory rate, SpO₂ with
  oxygen delivery, and weight when relevant to dosing.
- Full blood count: haemoglobin, white cell count with differential, platelets.
- Basic metabolic panel ("chem-7"): sodium, potassium, chloride, bicarbonate, urea,
  creatinine (with eGFR), glucose.
- 12-lead ECG, reported as a clinician would read it (rate, rhythm, axis, intervals,
  conduction, ST and T waves).
- Chest X-ray, reported as a radiologist would describe it.

Add the tests a typical emergency department or admitting team orders for the chief
complaint, whether or not they help: for example CRP, liver panel, albumin, calcium,
magnesium, phosphate, INR/APTT, troponin, lactate, venous blood gas and urine dipstick.
Choose them by the presenting problem and setting, never by the answer. Do not
calculate derived values (anion gap, corrected calcium, A–a gradient, osmolar gap) for
the learner; leave the raw numbers so they can.

**Outpatient cases**: vital signs and BMI, plus "recent routine bloods" a GP would
have (FBC, basic panel, HbA1c, lipids, TSH, eGFR/urine ACR as appropriate to the
patient).

**ICU cases**: the admission set plus an arterial blood gas, lactate, current
ventilator or vasopressor settings, and fluid balance.

**Paediatric, obstetric and other specialties**: use the equivalent routine baseline for
that setting, defined once in the onboarding blueprint and applied to every case.

## 4. Non-routine tests: the rarity budget

The commonest way a case gives itself away is through which tests were done. A urine
electrolyte panel, a renin–aldosterone ratio, ANCA, a free light chain assay, an
ACTH level or a cardiac MRI announces the diagnosis.

- In the opening of a case, include **no more than one** result beyond the standard
  workup, and only when it is realistic that it is already available at that point (for
  example a CT head done in the ED for confusion, or a CT pulmonary angiogram for
  pleuritic chest pain and hypoxaemia). It should be justified by the presenting
  complaint, not by the diagnosis.
- Specialised results (urine electrolytes and osmolality, autoantibodies, hormone
  levels and dynamic tests, genetic tests, specialised imaging, biopsy or cytology,
  CSF beyond basic studies) are not handed over up front. The learner has to ask for
  them (see §5).
- When a key clue must be present at the start (an exposure, a medication, a family
  history), write it at the same level of detail as the surrounding unremarkable items
  and place it among them. It must never be the only unusual detail in the vignette.
- Add one or two genuine but non-contributory findings (mild macrocytosis in a regular
  drinker, an old right bundle branch block, a calcified granuloma on the X-ray). They
  are realistic noise, not traps: each must be explainable in the feedback as incidental.

### Base rates

Do not make every case a rarity. Across rounds, roughly two thirds of cases should
resolve to common or high-stakes diagnoses where the test lies in management, thresholds
or a recent guideline change; no more than a third should be uncommon diagnoses. When a
rare diagnosis is the target, the vignette should be compatible with two or three common
alternatives as well.

## 5. Case formats

The setting `case_format` chooses the format (`unfolding`, `discriminate`, or `alternate`);
`plan` applies it (`case_format` in `plan.json`) and drops to `discriminate` for very short
sessions.

### Discriminate (one step)
Give the presentation and the standard workup only. Ask:

0. A one-sentence summary of the problem, as you would open a case presentation (problem
   representation).
1. Your differential diagnosis, ranked, with the main argument for and against each of
   the top three.
2. The next two to four investigations you would order to separate them, and for each,
   the result that would move you toward or away from each leading diagnosis.
3. What you would do while awaiting results (immediate management, monitoring,
   disposition).

Grade the quality of the reasoning and the discriminating strategy. The feedback reveals
the final diagnosis and shows the actual results of the decisive tests.

### Unfolding (two steps)
**Stage 1** is the Discriminate prompt above. After the learner answers Stage 1 and the
MCQs, present **Stage 2** without any grading or comment yet:

- Give the results of every test the learner ordered, written realistically (normal,
  non-specific and abnormal results alike).
- If they did not order the decisive test, add it as "Results also available (ordered by
  the admitting team / consultant)", together with one or two other reasonable tests,
  so that the decisive one is not singled out.
- Advance the clinical course if useful (response to initial treatment, a new finding).
- Ask for the final diagnosis, the specific management plan (drugs, doses where they
  matter, targets, monitoring) and disposition or follow-up.

Do not let Stage 2 grade or hint at Stage 1. Keep both stages in the final feedback.

### Answer format prompt
Close the presentation with a short instruction such as:

> Answer each part in your own words; brief notes are fine. For each answer you may add
> how sure you are (sure / unsure / guess) and anything specific you are unsure about.
> The feedback will concentrate on those points.

Confidence and stated uncertainty are optional, but when given they drive both the
depth of feedback and the spacing of the topic.

## 6. MCQs (single best answer)

- Clinical stem (patient, setting, findings) followed by a single, focused lead-in
  question ("What is the most appropriate next step?"). The lead-in must be answerable
  before reading the options.
- Four or five options, homogeneous in kind (all diagnoses, all tests or all
  management steps), similar in length and specificity. The correct option must not be
  the longest, the most hedged or the only one using guideline language.
- Distractors must be plausible to a competent clinician: the right action in a
  neighbouring scenario, an outdated recommendation, the correct drug at the wrong time.
- Vary the position of the correct answer between items and between rounds.
- Apply the same rarity budget: the stem carries data that bear on several options, not
  only on the correct one.
- When re-testing an open gap, put the same decision point in a new clinical context;
  the aim is to test transfer, not recall of the earlier vignette.
- MCQs are presented first, on their own. Each stem must stand alone: no "the patient above",
  and no reference to the case.

## 7. Difficulty and conventions

- Pitch items at the learner's stated role and specialty (profile), e.g. a hospitalist
  attending or a senior subspecialty fellow when testing within the subspecialty.
- Units follow the plan: `lab_units` (SI by default: mmol/L, µmol/L, g/L, ×10⁹/L) and
  `blood_gas_units` (mmHg by default for pCO₂ and pO₂; kPa if set).
- Drug names: international non-proprietary names; add the regional name where it
  differs if the learner's region uses it.
- Guidelines: use the learner's `guideline_region` first; where regional guidance
  differs materially, the feedback says so.
- Cases are fictional. Never request or include identifiable patient information.

## 8. Pre-flight check (in the sealed draft, before sending)

Answer each line as a row of the pre-flight table at the end of the sealed file
(`sealed_questions.md` for lines 6 and 10–13, `sealed_case.md` for the rest; yes/no, and the fix
when needed; with no case in the round, only the lines that apply). The text the learner will
see goes between `<!-- present: questions|case|stage2 -->` and `<!-- /present -->` exactly as it
will be sent: `cme.py save` copies it into the log. Do not work through it in your thinking:
there it would expose the content it checks.

1. Could a clinician guess the diagnosis from the list of tests alone?
2. Is any detail present only because it is the answer?
3. Does any word (title, heading, lead-in, eponym, test name, unusual exposure) point to
   the topic?
4. Are all standard sections present (history incl. family and social history, vitals,
   FBC, basic panel, ECG and chest X-ray for hospital cases)?
5. At most one non-routine result in the opening, justified by the complaint?
6. Are the MCQs unrelated to the case in content as well as by topic ID (not its diagnosis,
   differential, key test or treatment), with homogeneous options and varied answer
   positions? Would reading the MCQs first make the case easier? If so, change the MCQ.
7. Have any tool calls, searches or task items named the topic? If so, change the plan.
8. Is the vignette clearly different from every `already_used` and `recent_cases_any_topic`
   entry: patient, setting, presentation and twist (§10)?
9. If this round has a drill, is the trap fair, avoidable from the data given, and invisible
   as a trap (§9)?
10. Does each focused question ask for exactly one decision, open-ended (no options), with the
    reasoning required in the lead-in (§11.2)?
11. Does it have one best answer under the learner's guidelines, with the acceptable
    alternatives and the unacceptable answers written in the key before it is sent (§11.3)?
12. Can it be answered from the vignette in a few lines and about three or four minutes, without
    any datum that is there only because it is the answer (§4)?
13. Is each focused question different from every `already_used` stem for its topic, and from
    the other short questions (§2)?

Fix anything that fails before presenting the round.

## 9. Drills: provoking a known thinking pattern

When `plan` attaches a `drill` to the case, the last progress review found a recurring
pattern and the learner agreed to practise against it. Build the case so that the pattern is
tempting, but a careful clinician avoids it with the data given. Everything else in this
guide still applies: the trap must not be detectable as a trap, and the base-rate rules hold.

| Drill code | How to build the case |
|---|---|
| `bias:premature_closure` | An early, salient explanation that accounts for most findings, plus a second process or an alternative that only the remaining data support |
| `bias:anchoring` | Stage 1 points reasonably one way; Stage 2 brings data that should move the learner |
| `bias:framing` | The referral letter or triage note frames the problem confidently, and plausibly wrongly |
| `bias:search_satisficing` | Two concurrent problems; the obvious abnormality explains only part of the picture |
| `bias:base_rate_neglect` / `bias:representativeness` | A common diagnosis presenting atypically, beside a rare one with textbook features that is less likely on the base rate |
| `bias:availability` | A presentation that resembles a currently prominent or dramatic diagnosis, while the common cause fits better |
| `bias:confirmation` | Data mixed in direction; test choice should seek to disconfirm |
| `bias:omission` / `bias:commission` | A clear indication to act (or to wait) where the opposite feels safer |
| `art:DG`, `art:TEST` | A decisive discriminator exists among several tempting low-yield tests |
| `art:PR`, `art:DDX` | Several features of different weight; the summary and ranking decide the answer |
| `knowledge:numeric` | A management decision that hinges on a threshold or dose |
| `knowledge:outdated` | A decision where recent guidance changed the answer |

In the feedback reveal, name the drill and what it targeted, and say whether the learner
avoided it. Record `"drill": {"code": …, "result": "avoided" | "partial" | "fell_for"}` in the
round JSON.

## 10. Novelty: never reuse a vignette

`plan` lists, for each chosen topic, the cases and MCQ stems already used (`already_used`),
plus the most recent cases on any topic. A re-test of the same topic must use a different
patient, setting, presentation and twist; the decision point may be the same (§6). After the
round, describe the case compactly in the round JSON so the index stays useful:
`"case": {"patient": "74F", "setting": "ED", "presentation": "confusion after a marathon",
"diagnosis": "exercise-associated hyponatraemia", "twist": "looked hypovolaemic"}`. Give each
MCQ and focused question a `stem_summary` (about ten words), and each focused question its
`aspect`.

## 11. Focused questions (mini-case, one free-text decision)

A focused question sits between the MCQ and the case. Like an MCQ it is short and on one topic;
like the case it is answered in the learner's own words and graded on the reasoning. It tests
one decision point and shows *why* the learner chose what they chose, which an MCQ cannot.
`plan` gives each one a topic, a reason and an `aspect_hint` (the aspect tested least
recently). Use the hint unless the item re-tests an open gap: then ask about the gap's decision
point, in a new clinical context (§6, transfer). If the hint fits the topic badly (a prognosis
question on a topic where nothing about prognosis changes care), take the next-best aspect.

### 11.1 The vignette (about 100–200 words)

- Patient (age, sex), setting, presenting problem with its timeline.
- Relevant history in one or two lines: past history (including one item that does not
  matter), medications with doses where they matter, allergies; social history when it could
  matter.
- Vital signs, and the results a clinician would actually have **at this decision point**: the
  routine set for the setting (§3), abbreviated to what bears on the question and on its
  plausible alternatives. Raw numbers, units from the plan, no derived values.
- One realistic but non-contributory finding.
- The rarity budget (§4) holds. One exception: for an `interpretation` question the result to
  interpret is given — that is the question — but it must be one a team would plausibly have,
  and the vignette must still fit two or three alternatives.

### 11.2 The lead-in: one decision, open, reasoned

End with a single question that asks the learner to commit and to justify. Patterns by aspect:

| Aspect | Lead-in pattern |
|---|---|
| `diagnosis` | What is the most likely diagnosis, and which findings favour it over the main alternative? |
| `interpretation` | How do you interpret these results, and what do they mean for this patient now? |
| `testing` | What single investigation would you do next, and how would its result change what you do? |
| `management` | What would you do now? Be specific (drug, dose, route or target where it matters) and say why. |
| `disposition` | Where should this patient be managed (or can they go home), and why? What would change that? |
| `prevention` | What would you recommend to prevent this or its recurrence, and why for this patient? |
| `prognosis` | What would you tell the patient about the likely course, and what drives that estimate? |

- Exactly one decision. No "list", "name three" or "discuss"; no two-part questions on different
  decisions. Asking for the reason, or for what would change the decision, is part of the one
  decision.
- The question must be answerable without options (there are none) and in a few lines.
- Test what changes care — a threshold, a choice of drug, a next step, a red flag — not trivia
  (eponyms, percentages, history) unless that number drives the decision.
- The lead-in must not name the diagnosis when the aspect is not `diagnosis` unless a
  clinician would already know it at that point (then the vignette says so, as a referral
  would: "admitted with confirmed …").

### 11.3 The key (sealed, written before sending)

In `sealed_questions.md`, for each focused question:

- **Best answer** in two to four sentences, with the guideline or evidence it rests on (to be
  verified at grading; put the searches on the verification list).
- **Rubric**: two to four elements, each one line — usually (1) the decision; (2) the decisive
  reason or discriminating finding; (3) the safety element, threshold or dose that matters;
  (4) optionally, what should change the decision.
- **Acceptable alternatives** (defensible under current guidance or regional variation, and
  how they score) and **unacceptable answers** (unsafe, outdated) — decided now, not after
  reading the learner's answer.
- `aspect`, `stem_summary`, and the separation check against the case and the other questions.

### 11.4 Presentation

Focused questions follow the MCQs in the same message, numbered on ("Question 4 — focused").
End the message with one answer prompt covering both kinds, for example:

> For Questions 1–3 reply with a letter; for Question 4 answer in a few lines — your decision and
> why. For each you may add sure / unsure / guess and anything specific you are unsure about.
> The case follows once these are answered.

Without a case in the round, drop the last sentence; without MCQs, ask only for the free-text
answers.

### 11.5 Drills

When the round has no case, `plan` may attach a drill to the first focused question (never the
patterns that need two stages or a full differential: anchoring, search satisficing, problem
representation, differential). Build one tempting wrong turn into the vignette, as in §9, and
keep it fair and invisible.

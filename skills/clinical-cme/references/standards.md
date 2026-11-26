# Standards: the rulebook for writing items

The numbered rules every item, key and kit of a round must meet. They are the same for every
learner; what differs per learner (guideline region, specialty, units, profile, mix) is
settings, and reaches the author through the plan. Each rule is written here once. The briefs
(`author.md`, `case_design.md`, `evidence_check.md`, `feedback_guide.md`, `preparing.md`,
SKILL.md) cite it by number ("rule 5") and do not restate it.

Who reads what: the **author** all of it; the **checker** rules 2 and 8; the **examiner**
rules 1–5 before grading (they bind the feedback too), and all of it when it writes items
itself. This file holds no content of any round, so anyone may read it at any time.

| Rule | Title | Checked by `cme.py` |
|---|---|---|
| 1 | Blinding | `present` prints only the blocks; the simulation's blinding check |
| 2 | Guideline region | – |
| 3 | Units and drug names | – |
| 4 | Pitch | – |
| 5 | Abbreviations | lint, judgement call; the simulation's standards check |
| 6 | One time anchor per case | lint, judgement call; the simulation's standards check |
| 7 | Crux tests are requested, not given | – (pre-flight line 16; the simulation's quality scorer) |
| 8 | What a kit contains | lint, blocking |
| 9 | Key headers | lint, blocking |

Numbers are never reused or renumbered: a new rule gets the next number, a withdrawn one
keeps its number with the word "withdrawn". How the lint works: last section.

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

Items are written, keyed, checked and graded against the guidelines of the plan's
`guideline_region` (the `start` output gives the examiner the same value), in the edition
relevant to the plan's `specialty`.

1. Keys, model answers, verification searches and feedback name that region's guideline first,
   with body and year. For "Iceland/Europe": Icelandic national guidance where it exists,
   otherwise the European society's.
2. Where another region's guidance differs materially, or guidance changed recently, the
   feedback says so, and the learner is graded against their own region's.
3. One line above each verification list states the region and the specialty, so that author,
   checker and examiner work to the same ones.

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
2. **How the feedback is written.** Early stages get more background: the mechanism, the
   reasoning step by step, the terms explained. Senior learners get the evidence instead:
   the trials behind a recommendation, its strength, where the evidence is thin or disputed
   and where guidance stops; no textbook background they have not asked for.
3. **Which sources.** An aim that names an exam is graded against that exam's standard
   sources (its syllabus, the textbooks and guidelines it examines from), and the feedback
   says which; where they differ from the guideline of rule 2, both are given and the exam's
   answer is the one keyed. Every other aim is graded by rule 2.
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
   IV, ECG, CT, MRI, HIV, BP, HR, CRP, ICU
   <!-- /common-abbreviations -->

3. Each feedback message opens with a one-line glossary of the abbreviations it uses, the
   listed ones excepted ("Abbreviations: ALT alanine aminotransferase; DOAC direct oral
   anticoagulant"). The line starts with the word "Abbreviations:" and comes before the
   reveal; a message that uses none has no line. Presented items get no glossary: there the
   rule is 5.1, in the text itself.

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
4. **In the feedback** the examiner says whether the learner asked for the crux test, and
   grades that step: a result supplied through "Add if not ordered" was not requested.

## Rule 8. What a kit contains

A kit holds the substance of the feedback that does not depend on the answers: notes for a
colleague who will grade, terse, sealed with the items, never shown and never pasted. Every
figure and source that the verification list is to confirm is marked `(verify)`. Each part
sits under a Markdown heading that starts with the name given here; the lint looks for the
headings.

`kit_questions.md`: one section per question, headed with its key id (`## Q1`, `## Q2`, …):

- the reveal line (topic, blueprint ID, why it was chosen, any prior gap it retests);
- MCQ: the decisive datum in the stem, and one line per distractor (wrong here because …,
  right when …); focused question: the decisive point and the tempting wrong turn;
- the briefing in outline: the rule, the why in a sentence, the evidence to cite, how it
  applies to this patient;
- the two-line version for a correct, sure answer (`feedback_guide.md` §4).

`kit_case.md`:

| Heading | Holds |
|---|---|
| `## Reveal` | the reveal line, and the drill if there is one |
| `## Model answer` | the final diagnosis and the model answer in one paragraph |
| `## Rubric` | the expected elements of each stage, as a checklist to mark ✓ ◐ ✗ |
| `## Differential` | the table of how the differential separates (`feedback_guide.md` §2 C.3), complete, with the incidental findings and why they are noise |
| `## Briefing` | a briefing outline for each rubric element a learner could plausibly miss |
| `## Pearls` | one to three pearls or pitfalls |
| `## Reading` | the reading pointers for the round |

**Reading pointers** (`## Reading`; in `kit_questions.md` when the round has no case): up to
two for the round, in the form of `feedback_guide.md` §2 E (the exact section, why it fits,
a reading time), each marked `(verify)` until the checker has confirmed that the section
exists.

<!-- slot: issue #50. Podcast candidates: a "## Listening" section, three sealed candidates
per topic (link, show, title, length, what it covers, which failure point it matches). Not
required and not linted yet. -->

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
stem_summary: New AF after hip surgery, when to anticoagulate
<!-- /key -->
```

1. The first line names the item: `Q1`, `Q2`, … with the number the question has in the text
   to present (MCQs first, then focused questions), and `case` for the case.
2. One header per item; one `field: value` per line, nothing else between the two markers.
3. The fields are those of this table and no others. An optional field that does not apply
   is left out, not left empty.

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

## The lint

`cme.py finish-prepare` lints a round prepared ahead, while nobody waits; `cme.py keys
<folder> --plan <plan>` runs the same checks for the author. It prints file names, key ids,
section names and counts only.

| Category | What | Then |
|---|---|---|
| **Blocking** (definite) | a key header that is missing or malformed (rule 9); a kit that is missing, a question without its section in `kit_questions.md`, or a missing section of `kit_case.md` (rule 8) | Nothing is stashed until it is corrected. |
| **Judgement call** (heuristic) | an abbreviation in the presented text that is not spelled out where the session first shows it (rule 5); a case or short question that counts time both from now and from a numbered day (rule 6) | The author revises once (`author.md` §2, Parts `revise`); what the lint still finds is accepted, and listed as a warning. A round is never left unprepared over a heuristic. |

What the heuristics look at, so that a finding can be judged:

- **Abbreviations**: every token of two to six capital letters (a plural "s" allowed), in the
  order of rule 5.1, at its first appearance. It passes when it is on the list of rule 5.2,
  when it is a Roman numeral, when an expansion in brackets follows it, or when it stands
  first in brackets after its expansion. A word written in capitals for emphasis is flagged
  too: do not write one.
- **Time anchors**: phrases that count from now ("3 hours ago", "since this morning",
  "yesterday", "last night") against phrases that count from a numbered day ("day 3",
  "hospital day", "the third postoperative day", "POD 2"), within one short question, or
  within the case and its bank together. Periods of months or years ("stopped smoking ten
  years ago") are not counted.

The findings themselves name content, so they are written to `lint.md` beside the sealed
files, for the author only; the examiner never opens it.

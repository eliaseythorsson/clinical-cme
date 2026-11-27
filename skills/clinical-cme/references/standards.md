# Standards: the rulebook for writing items

The numbered rules every item, key and kit of a round must meet. They are the same for every
learner; what differs per learner (guideline region, specialty, units, profile, mix) is
settings, and reaches the author through the plan. Each rule is written here once. The briefs
(`author.md`, `case_design.md`, `evidence_check.md`, `feedback_guide.md`, `preparing.md`,
SKILL.md) cite it by number ("rule 5") and do not restate it.

Who reads what: the **author** all of it; the **checker** rules 2 and 8; the **examiner** none
of it before grading, and all of it when it writes items itself. What binds the feedback is in
the examiner's brief (`feedback_guide.md`): rules 5.3, 10 and 11 are written there, and the
author reads them there for the kits' prepared blocks (rule 8). This file holds no content of
any round, so anyone may read it at any time.

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
| 10 | Results the learner did not see (in `feedback_guide.md` §10.2) | – (the simulation's quality scorer) |
| 11 | Text for the learner speaks plainly (in `feedback_guide.md` §10.3) | `save` warns; the simulation's standards check fails the run |
| 12 | The learner's position notes | – (nothing a lint can check) |

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
   item is still keyed to the learner's region; what the feedback then says is in
   `feedback_guide.md` §1.
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
2. **How the feedback is written**, and how far behind the recommendation it goes (the
   evidence depth, `feedback_guide.md` §4.1): in the examiner's brief, `feedback_guide.md` §1.
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
   listed ones excepted: the line that starts "Abbreviations:" is written in the examiner's
   brief, `feedback_guide.md` §10.1. Presented items get no glossary: there the rule is 5.1,
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
4. **In the feedback**: `feedback_guide.md` §10.2. The rubric has an element for asking for
   the crux test, so that the step is graded.

## Rule 8. What a kit contains

A kit holds the feedback's text that does not depend on the answers, written as **finished text
for the learner** when the round is prepared, and checked with it (ADR 0009). It is sealed with
the items and reaches the learner only through the examiner, once the answers are in: the
examiner marks the answers first, then `cme.py draft` takes the blocks the marks call for, and
the examiner adapts them (`feedback_guide.md` §9). Each part sits under a Markdown heading that
starts with the name given here; the lint looks for the headings and the blocks.

**Prepared blocks.** Each piece of finished text is one block, between
`<!-- block: <id> <kind> -->` and `<!-- /block -->`, where `<id>` is the key id, with `.n` for the
n-th element of its rubric block (rule 9), counted from 1 down the block, across both stages of
the case:

```
<!-- block: Q4.2 missed -->
You gave vitamin K but not the reason it is enough here: …
<!-- /block -->
```

| Item | Blocks |
|---|---|
| MCQ | `reveal`; `model` (why the correct option is right: the decisive datum in the stem); `distractors` (one line each: wrong here because …, right when …); `missed` (the full briefing); `hit` (the two or three lines for a correct, sure answer: why correct, one pearl, the source line) |
| Focused question | `reveal`; `model` (the best answer, two to four sentences); `decisive` (the decisive point and the tempting wrong turn); and for **every element** of its rubric, `n missed`, `n partial` and `n hit` |
| Case | `reveal`; `model` (the final diagnosis and the model answer in one paragraph); `differential` (the table of how the differential separates, complete, with the incidental findings and why they are noise); `pearls` (one to three pearls or pitfalls); and for every element of its rubric, `n missed`, `n partial` and `n hit` |
| Any item the plan gives a `depth` | `deeper` (below) |

How they are written:

1. **For the learner, finished**: written to the examiner's brief, as the feedback would say it
   — its structure (`feedback_guide.md` §2), the evidence briefing (§3), the scaling (§4), the
   rules of §10 (no glossary line: that is the examiner's, per message), pitched by the
   profile's paragraphs (§1), in the plan's units. Never an outline, never a note to the
   examiner, no `(verify)` marks, nothing about the learner's answer, which is not known yet:
   the examiner opens with the learner's words (§9.3).
2. **By the mark**: `missed`, the full briefing on that element (§3: the rule, why, the
   evidence, the source line; 120–300 words, about 120 with `feedback_depth: standard`);
   `partial`, what a part-answer usually lacks and the rule that completes it (60–120 words);
   `hit`, two or three lines confirming why it is right, with the source. A missed testing
   element of the case is written for the test not ordered (`feedback_guide.md` §10.2).
3. **Checked**: every figure, recommendation and source a block states is on the verification
   list, the line ending with the ids of the blocks that state it (`… [Q4.2 missed, Q4 model]`),
   so the checker can name the blocks a correction touches. The examiner sees those flags in the
   draft.
4. **Within the item**: blocks sit in their item's section (`## Q1` in `kit_questions.md`; the
   case's sections below), and a block names no other item and nothing of the case.

`kit_questions.md`: one section per question, headed with its key id (`## Q1`, `## Q2`, …),
holding that question's blocks.

`kit_case.md`:

| Heading | Holds |
|---|---|
| `## Reveal` | the block `case reveal`: the reveal line, and the drill if there is one |
| `## Model answer` | `case model` |
| `## Differential` | `case differential` |
| `## Briefing` | the element blocks, `case.1 missed` … , three per element of the rubric block |
| `## Pearls` | `case pearls` |
| `## Reading` | the reading pointers for the round (notes, below) |

**Deeper** (`<id> deeper`, in the question's section of `kit_questions.md`; under `## Deeper` in
`kit_case.md`): only for an item that has `depth` in the plan, which means the learner has
answered the topic well before and, if they do again, the feedback goes behind the
recommendation (`feedback_guide.md` §4.1). Finished text at the plan's `depth.level`, starting
with one line of the depth before it: 2 `studies`, the one or two studies the recommendation
rests on (name, year, population, comparison, primary result in absolute figures, the class and
level the guideline gives); 3 `design`, the design features that decide how far the result can
be trusted and for whom; 4 `frontier`, where the evidence stops or is disputed and how the panel
got from evidence to recommendation. Each study and figure is **put on the verification list**
as its own line, so the checker confirms it. An item without `depth` in the plan gets no such
block; one that is missed never uses it.

**Reading pointers** (`## Reading`; in `kit_questions.md` when the round has no case): notes,
not a block. Up to two for the round, in the form of `feedback_guide.md` §2 E (the exact
section, why it fits, a reading time) with the document's link and the key id of the topic it
serves, each marked `(verify)` until the checker has confirmed that the section exists.

**Listening** (`## Listening`, the last section of both kits; left out only when the plan
has `listening` false): the candidate podcast episodes from which each topic of the round
gets one pick in the final feedback (`feedback_guide.md` §2 E2). Three candidates per topic,
sealed with the kit. Two hands write the section:

- the **author** writes the heading, one `Sources` line copied from the plan's
  `podcast_sources`, and one line per topic of that kit, headed with its key id (`Q1`, `Q2`,
  …; `case` in `kit_case.md`): the point the item tests and its likely failure points (the
  tempting wrong turn, the rubric elements a learner may miss). The author searches for
  nothing (rule 1.3);
- the **checker** finds the episodes (`evidence_check.md` §6) and writes them under each
  topic's line, one line per candidate, six fields separated by ` | `: the link
  (`https://open.spotify.com/episode/<id>`, nothing after the id), the show, the title, the
  length in minutes, what it covers, and which failure point it matches.

```
## Listening
Sources | trusted: Example Show, Another Show | avoid: none
Q1 | points: when to anticoagulate new AF after surgery; tempting: starting at once
- https://open.spotify.com/episode/<22 letters and digits> | Example Show | <the episode's title> | 52 min | covers: stroke risk and timing after surgery | matches: starting at once
- …
- …
Q2 | points: …
- none: only one episode of 15 to 90 minutes was found
- …
```

1. An episode is one a physician would learn the point from, 15 to 90 minutes long, as
   specific to the topic's failure points as can be found. Shows on the learner's `trusted`
   list come first where they fit; a show on the `avoid` list is never kept.
2. Only an episode whose own Spotify page was reached is kept, with the title and the length
   read from that page. A link that was not reached is not kept (`evidence_check.md` §6).
3. Fewer than three is honest when no more exist: the topic then carries a line `- none:
   <why>`, alone when nothing suitable was found.
4. No search for an episode is run where the learner could see it before the part's last
   answer (rule 1.3): the checker searches out of the conversation, the examiner only once
   the answers are in.
5. Spotify has no link that saves an episode to the learner's library: the link opens the
   episode in the app, and one tap there saves it. Nothing in a kit or in the feedback
   promises more.

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

Written in the examiner's brief, `feedback_guide.md` §10.2, because it binds the feedback: the
feedback teaches with every result the case was written with, and a result the learner did not
see is never quoted as if it had been shown. The author follows it there in the case's prepared
blocks; a result a block may need is in the results bank, so that Stage 2 can show it.

## Rule 11. Text for the learner speaks plainly

Written in the examiner's brief, `feedback_guide.md` §10.3: everything the learner reads (items,
results, feedback, the close) is written for a clinician and never names the skill's own
machinery. It binds the items and the results bank as much as the feedback.

## Rule 12. The learner's position notes

A **position note** is what the learner holds on one decision point of a topic, in their own
words, kept when they stopped the topic ("I know this, stop bringing it back";
`feedback_guide.md` §7.2). It covers that one point, not the topic. The plan gives an item
`positions` (`notes`: `id`, `point`, `text`, `set`, and `reopened` once it has been raised
again) when the learner holds one on its topic; `answer` gives the examiner the same notes by
key id.

1. **No item is keyed on the disputed point.** The author writes the item on another decision
   point of the topic, and no distractor, rubric element or model answer turns on the premise
   the learner rejects. Where the point cannot be avoided in a case, the key accepts the
   learner's position as a defensible answer.
2. **The learner is never marked down on it**, and the feedback does not argue the point
   again: the examiner's side is `feedback_guide.md` §7.2 and §9.1.
3. **The evidence is said once**, when the note is set (`feedback_guide.md` §7.2), unless
   guidance on that exact point has changed since the note's `set` date (4).
4. **A changed guideline is raised once.** For an item with a note that has no `reopened`, the
   author puts one line on the verification list: has guidance on the note's point changed
   since its `set` date? If the checker finds it has, the examiner may raise it once more, in
   one line with the source, and records that it did (`cme.py position --reopened <id>`).

The note ends when the learner takes it back (any time), when the progress review drops it
(each review lists the notes in force, one line each: keep or drop), or on its own after about
six months without being kept at a review. Nothing here names the note's machinery to the
learner (rule 11): it is "the position you hold on …".

## The lint

`cme.py finish-prepare` lints a round prepared ahead, while nobody waits; `cme.py keys
<folder> --plan <plan>` runs the same checks for the author. It prints file names, key ids,
section names and counts only.

| Category | What | Then |
|---|---|---|
| **Blocking** (definite) | a key header that is missing or malformed (rule 9); a kit that is missing, a question without its section in `kit_questions.md`, a missing section of `kit_case.md`, a prepared block that is missing, empty, unclosed or names no item, element or kind of the round, or, with listening on, a kit without `## Listening` or a topic without its line there (rule 8) | Nothing is stashed until it is corrected. |
| **Judgement call** (heuristic) | an abbreviation in the presented text that is not spelled out where the session first shows it (rule 5); a case or short question that counts time both from now and from a numbered day (rule 6) | The author revises once (`author.md` §2, Parts `revise`); what the lint still finds is accepted, and listed as a warning. A round is never left unprepared over a heuristic. |
| **Judgement call** (form) | once a checker has run: a topic's listening candidates that are not three episodes in form (rule 8) | That kit's checker is started once more (`evidence_check.md` §6); what the lint still finds is accepted, and listed as a warning. |

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

- **Listening candidates**: under each topic's line, every line with a link or with fields
  is a candidate. It is in form when it has its six fields, a link to one Spotify episode
  (`https://open.spotify.com/episode/` and an id of 22 letters and digits), a length of 15 to
  90 minutes ("52 min") and a show that is not on the plan's `avoid` list. A topic is flagged
  for a candidate out of form, for fewer than three in form without a `none:` line, and for
  more than three. Whether the episode exists and fits is the checker's work, not the lint's.

The findings themselves name content, so they are written to `lint.md` beside the sealed
files, for the author only; the examiner never opens it.

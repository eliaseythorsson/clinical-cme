# Author: writing a round's items

How the items of a round are written: the short questions, the case, and the notes their
feedback will be built from. Two readers:

- an **author agent**, started with only this file's path, a plan, an output folder and the
  parts to write. You have no other context and need none;
- the **assistant running the round**, when there is no author agent.

The items are for a physician who must not learn their topics before answering, and the
answers will be graded by someone other than you. So: everything goes into files, nothing into
the conversation, and the keys must be good enough for another clinician to grade from.

## Rules for an author agent

- Your whole reply is the word `done` (or `failed: <a reason without any clinical content>`).
  No summary, no topic, no titles.
- Give every tool call a neutral description ("Prepare the round"). Create no task items.
- Run no web searches and open no outside sources: a search names the topic, and the evidence
  is checked separately. Write from what you know, and put every claim that needs checking on
  the verification list.
- Ask nothing. Write only the files named below, each in a single file write, into the output
  folder. If a file already exists there, leave it unless it is one of your parts.
- Keep your reasoning free of the content: design in the files, not in your thinking.

## 1. Read first

1. `case_design.md` (same folder as this file), all of it. It is the standard for every item.
2. `feedback_guide.md` §2–4 and §9: what the feedback will contain, and so what the notes
   must hold.
3. The plan (JSON). It gives, per item: slot (`mcq`, `focused`, `case`), topic and blueprint
   ID, the reason it was chosen, any open gap to re-test, `aspect_hint` for focused items, a
   `drill` if one applies, `separation` notes, and `already_used` stems and cases; and for the
   round: `case_format`, units, `guideline_region`, `specialty`, `feedback_depth`, the learner's profile,
   `recent_cases_any_topic`.

Planning notes:

- An item without a specific topic (`new_in_domain`) gets an untested topic from that
  blueprint domain; record the ID and label you chose in the key.
- Pitch at the learner's role and the plan's `specialty`; use the plan's units. Choose
  guidelines by the plan's `guideline_region`: keys, model answers and verification searches
  name that region's guideline (body and year) first, and for "Iceland/Europe" that is
  Icelandic national guidance where it exists, otherwise the European society's. State the
  region and specialty in one line above each verification list, so the checker and the
  examiner work to the same ones.
- An item with `retest_gap` in the plan re-tests that gap: the same decision point in a new
  clinical context (transfer). Write `retests: <retest_gap.id>` in that item's key header
  (§3); without it a good answer cannot close the gap. (The plan's `how` line still speaks
  of the round JSON: the key header is where it goes.)
- A `drill` is built into its item (`case_design.md` §9, §11.5).
- Every vignette and stem is clearly different from `already_used` and
  `recent_cases_any_topic`: patient, setting, presentation, twist.

## 2. Parts and order

- `Parts: all` (the usual): all four files below.
- `Parts: questions`: `sealed_questions.md` only, as fast as you can — the learner is waiting
  for it.
- `Parts: case`: `sealed_case.md` and `kit_case.md`, and `kit_questions.md` if it is not in
  the output folder yet.
- `Parts: revise`: the round is written and its evidence has been checked. Read
  `evidence_questions.md` and `evidence_case.md` in the output folder. Wherever a **Note**
  says a key is contradicted by current guidance, correct the item so that it has one best
  answer under that guidance: the key, the kit, and the stem or options if they no longer
  work, keeping the `present` block complete. Replace every `(verify)` in the kits that the
  check confirmed with the confirmed figure and source. Change nothing else.

Write the short questions first, then the case, so the case can be kept clear of them and of
what their feedback will teach (`case_design.md` §2). With `Parts: case`, read the
`sealed_questions.md` already in the output folder first, for the same reason. Leave out the
files of a part the plan does not have (no case, or no short questions).

## 3. The files

### `sealed_questions.md`

In this order:

1. **Keys**, one block per item, written before its stem. Each starts with its **key header**
   ("Key headers" below), then:
   - MCQ: the correct option and a one-line reason; a few words per distractor on the
     scenario in which it would be right.
   - Focused question: best answer (two to four sentences); rubric (two to four one-line
     elements); acceptable alternatives and how they score; unacceptable answers
     (`case_design.md` §11.3).
2. **Pre-flight**: one line (`case_design.md` §8, lines 6 and 10–13).
3. **Verification list**: one precise search per claim the feedback will rest on (guideline
   and year, threshold or dose, trial), three to six lines.
4. **The text to present**, exactly as the learner will see it, between
   `<!-- present: questions -->` and `<!-- /present -->`: MCQs first, then focused questions,
   numbered on ("Question 4 — focused"), ending with the answer prompt (`case_design.md`
   §11.4). No titles, no topic words.

### `sealed_case.md`

1. **Key**: its key header (`<!-- key: case -->`, below), which holds the diagnosis and the
   compact description for the log; then the decisive tests; the two or three leading
   alternatives; the expected elements of each stage (the rubric); the drill, if any.
2. **Results bank** (unfolding cases), between `<!-- bank -->` and `<!-- /bank -->`: the result
   of every investigation a competent clinician might reasonably order here, each as it would
   be reported, typically ten to fifteen; one line "Add if not ordered: <decisive test>; with:
   <one or two other reasonable tests>"; the clinical course to Stage 2; the Stage 2 questions
   (`case_design.md` §5). The examiner reads only this block before the final answers, so it
   holds no diagnosis, no key, no alternatives and no rubric.
3. **Novelty and pre-flight**: one line each (`case_design.md` §8, lines 1–5 and 7–9; §10).
4. **Verification list**: three to six precise searches.
5. **The text to present**: Stage 1 (or the whole one-step case), exactly as the learner will
   see it, between `<!-- present: case -->` and `<!-- /present -->`, headed "Case", ending with
   the answer-format prompt (`case_design.md` §5). Stage 2 is not written as a block: it is
   assembled from the bank after the learner's Stage 1 answer.

### Key headers

Every item's key starts with a small header in exactly this form. The state engine reads it
and fills the round's record from it, so the examiner adds only the grading; a missing or
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

- The first line names the item: `Q1`, `Q2`, … with the number the question has in the text
  to present (MCQs first, then focused questions), and `case` for the case. One header per
  item; one `field: value` per line, nothing else between the two markers.
- Every header: `type` (`mcq`, `focused` or `case`); `topic` (the blueprint ID) and `label`
  (for a `new_in_domain` item, the ones you chose); `reason` (the plan's `reason_code` for
  the item, copied as it is).
- `retests`: the plan's `retest_gap.id`, on an item written on that gap's decision point.
  Leave the line out otherwise.
- MCQ and focused question: `stem_summary`, about ten words on what the stem asks, for the
  list of stems already used.
- Focused question: `aspect`, one of `diagnosis`, `interpretation`, `testing`, `management`,
  `disposition`, `prevention`, `prognosis`.
- Case: `patient` (age and sex, "74F"), `setting`, `presentation`, `diagnosis`, and `twist`
  (what makes this case different; may be left out). These five are the compact description
  kept for the novelty check of later rounds.
- `domain` may be given when the topic ID does not start with its domain code.

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

### `kit_questions.md` and `kit_case.md`

The notes the feedback will be written from, as `feedback_guide.md` §9 lists them. Terse:
notes for a colleague who will grade, not prose to paste. Mark every figure and source that
the verification list is to confirm with `(verify)`.

## 4. Before you finish

Fix anything the pre-flight found by editing the file, without restating content anywhere
else. Check that each `present` block is complete and closed, and that no present block
contains a key, a topic word or a title, and that the bank block (if any) is closed and
holds no diagnosis or key. Check the key headers: `python3 <this file's folder>/../scripts/cme.py
keys <output folder> --plan <plan>` (description "Prepare the round") prints which headers each
file has and what is wrong with them, by field name only; correct the headers until it prints
`"ok": true`. (With `Parts: questions` or `case` it checks the files written so far.) Then
reply `done`.

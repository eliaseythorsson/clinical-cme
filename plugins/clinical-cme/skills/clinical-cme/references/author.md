# Author: writing a round's items

How the items of a round are written: the short questions, the case, and the finished text
their feedback is assembled from (the kits' prepared blocks). Two readers:

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

1. `standards.md` (same folder as this file), all of it: the numbered rules every item, key
   and kit must meet. This brief and `case_design.md` cite them as "rule N".
2. `case_design.md`, all of it: how items are designed.
3. `feedback_guide.md` §1–5 and §9–10, the examiner's brief: the feedback the kits' prepared
   blocks (rule 8) are written as, and the rules it keeps. The examiner marks the answer first
   and then adapts your blocks: write each so that it can be sent as it stands.
4. The plan (JSON). It gives, per item: slot (`mcq`, `focused`, `case`), topic and blueprint
   ID, the `subtopic` to write to where the blueprint has sub-topics (with its decision points), the reason it was chosen, any open gap to re-test, the learner's `positions` on its topic
   (rule 12), `aspect_hint` for focused items, a
   `depth` where the learner has answered the topic well before (rule 8, "Deeper"), a
   `drill` if one applies, `separation` notes, and `already_used` stems and cases; and for the
   round: `case_format`, units, `guideline_region`, `specialty`, `feedback_depth`, the learner's profile (their own two paragraphs: rule 4),
   `recent_cases_any_topic`, `listening` and `podcast_sources`.

Planning notes:

- An item without a specific topic (`new_in_domain`) gets an untested topic from that
  blueprint domain; record the ID and label you chose in the key.
- The round belongs to a themed block (`block` in the plan). The case and most short questions
  are on the theme, so they share a domain: keep each short question on a different problem
  from the case and from the others, so that none cues another. An item with `reason_code`
  `revisit` is a theme topic tested before and not yet due: write it on another decision point
  of the topic than the stems in `already_used`. The theme stays out of the items (rule 1.1).
- The plan's `guideline_region`, `specialty`, units and profile are applied as rules 2–4 say:
  the pitch of every item, and the background, evidence depth and sources its kit holds, come
  from the profile's paragraphs by rule 4.
- An item with `subtopic` in the plan is written to that sub-topic of its topic (the
  disease): the topic came by its schedule, the sub-topic is the engine's choice within it
  (`why`: `untested`, `weakest`, or `gap` when it retests a gap on that sub-topic). Ask about
  one of its `points` (the decision points the blueprint lists), or another decision point
  of the same sub-topic, and write `subtopic: <subtopic.id>` in the key header (rule 9). The
  guideline in brackets at the end of a point is a baseline (rule 2.4): the plan already puts
  a newer one in place of a tag found superseded, and the sub-topic's `guidelines`, where
  given, say which of its tags changed or are uncertain; cite the guideline in force. Its
  `aspects`, where given, say which aspects matter most; the `aspect_hint` already follows
  them. `already_used` names the sub-topic of each earlier stem: a different decision point
  of a sub-topic tested before is welcome, the same vignette is not. An item you place in a
  `new_in_domain` slot names the sub-topic you wrote to when its topic has them.
- An item with `retest_gap` in the plan re-tests that gap: the same decision point in a new
  clinical context (transfer). Write `retests: <retest_gap.id>` in that item's key header
  (rule 9), as the plan's `how` line says; without it a good answer cannot close the gap.
- An item with `positions` in the plan is on a topic where the learner holds a position on
  one decision point, in their own words: key nothing on that point, and put the line
  rule 12 asks for on the verification list (rule 12).
- An item with `depth` in the plan gets a `deeper` block in its kit section, at that level,
  and a line on the verification list for each study it names (rule 8). The item itself is
  written no differently: the depth is about its feedback, not its difficulty.
- A `drill` is built into its item (`case_design.md` §9, §11.5).
- Unless the plan's `listening` is false, each kit ends with `## Listening` (rule 8): the
  `Sources` line from the plan's `podcast_sources`, and one line per topic with the point
  tested and its likely failure points. You name no episode and search for none: the checker
  fills in the candidates.
- Every vignette and stem is clearly different from `already_used` and
  `recent_cases_any_topic`: patient, setting, presentation, twist.

## 2. Parts and order

- `Parts: all` (the usual): all four files below.
- `Parts: questions`: `sealed_questions.md` only, as fast as you can — the learner is waiting
  for it.
- `Parts: case`: `sealed_case.md` and `kit_case.md`, and `kit_questions.md` if it is not in
  the output folder yet.
- `Parts: headers`: the round is written and `cme.py finish-prepare` refused it for its key
  headers or its kits (the lint's blocking problems, `standards.md`, "The lint"). The
  problems are listed in your prompt by file, key, field and kit section. Correct those
  headers (rule 9), kit sections and prepared blocks (rule 8) and run the check of §4 until it prints
  `"ok": true`. Change nothing else.
- `Parts: revise`: the round is written and `cme.py finish-prepare` printed `"revise": true`:
  a key is contradicted, or the lint made a judgement call, or both; or the checker retried
  claims it had not verified, and the kits are to take up what it confirmed. Change nothing
  but what these name, and leave the evidence files as they are: the round is stashed after
  your "done", whatever the lint still finds.
  - Read `evidence_questions.md` and `evidence_case.md` in the output folder, where they
    exist. Wherever a **Note** says a key is contradicted by current guidance, correct the
    item so that it has one best answer under that guidance: the key, the kit, and the stem or
    options if they no longer work, keeping the `present` block complete. Replace every
    `(verify)` in the kits' notes that the check confirmed with the confirmed figure and
    source, and correct every prepared block that a claim marked changed, regional difference
    or not verified names under **Blocks:** (state a claim not verified qualitatively).
    The candidates under `## Listening` are the checker's: leave them as they are.
  - Read the tag results (`tag_results_<n>.md`) in the output folder, if there are any. Where a tag an item's decision
    point rests on is marked `superseded` (or `changed`), make the key, the kit and the
    verification list cite the newer guideline (or the change) and correct any block that
    rests on the old edition (rule 2.4). Leave the file as it is.
  - Read `lint.md` in the output folder, if there is one. For each line decide whether the
    rule it names is broken (rule 5: an abbreviation not spelled out at first use; rule 6:
    more than one time anchor) and correct the presented text where it is. A finding that is
    wrong is left alone.

Write the short questions first, then the case, so the case can be kept clear of them and of
what their feedback will teach (`case_design.md` §2). With `Parts: case`, read the
`sealed_questions.md` already in the output folder first, for the same reason. Leave out the
files of a part the plan does not have (no case, or no short questions).

## 3. The files

### `sealed_questions.md`

In this order:

1. **Keys**, one block per item, written before its stem. Each starts with its **key header**
   (rule 9), then:
   - MCQ: the correct option and a one-line reason; a few words per distractor on the
     scenario in which it would be right.
   - Focused question: its **rubric block** right after the header (two to four one-line
     elements, rule 9); best answer (two to four sentences); acceptable alternatives and how
     they score; unacceptable answers (`case_design.md` §11.3).
2. **Pre-flight**: one line (`case_design.md` §8, lines 6 and 10–16; the last three are
   rules 5–7).
3. **Verification list**: one precise search per claim the feedback will rest on (guideline
   and year, threshold or dose, trial), three to six lines, each ending with the ids of the
   prepared blocks that state the claim (`[Q1 missed, Q4.2 missed]`; rule 8).
4. **The text to present**, exactly as the learner will see it, between
   `<!-- present: questions -->` and `<!-- /present -->`: MCQs first, then focused questions,
   numbered on ("Question 4 — focused"), ending with the answer prompt (`case_design.md`
   §11.4). No titles, no topic words.

### `sealed_case.md`

1. **Key**: its key header (`<!-- key: case -->`, rule 9), which holds the diagnosis and the
   compact description for the log; its **rubric block** (the expected elements of each stage,
   rule 9); then the decisive tests; the two or three leading alternatives; the drill, if any.
2. **Results bank** (unfolding cases), between `<!-- bank -->` and `<!-- /bank -->`: the result
   of every investigation a competent clinician might reasonably order here, each as it would
   be reported, typically ten to fifteen; one line "Add if not ordered: <decisive test>; with:
   <one or two other reasonable tests>"; the clinical course to Stage 2; the Stage 2 questions
   (`case_design.md` §5). The examiner reads only this block before the final answers, so it
   holds no diagnosis, no key, no alternatives and no rubric.
3. **Novelty and pre-flight**: one line each (`case_design.md` §8, lines 1–5, 7–9 and 14–16,
   the last three being rules 5–7; §10).
4. **Verification list**: three to six precise searches, each with its block ids, as above.
5. **The text to present**: Stage 1 (or the whole one-step case), exactly as the learner will
   see it, between `<!-- present: case -->` and `<!-- /present -->`, headed "Case", ending with
   the answer-format prompt (`case_design.md` §5). Stage 2 is not written as a block: it is
   assembled from the bank after the learner's Stage 1 answer.

### `kit_questions.md` and `kit_case.md`

The feedback's finished text, in prepared blocks: which blocks, how they are written and the
headings they sit under is rule 8. A focused question or the case gets three blocks for every
element of its rubric block (missed, partial, hit), so write the rubric first and number its
elements as you go. This is most of the round's writing; it is done while nobody waits.

## 4. Before you finish

Fix anything the pre-flight found by editing the file, without restating content anywhere
else. Check that each `present` block is complete and closed and that the bank block (if any)
is closed (rule 1.1–1.2 for what they must not hold). Then run the lint: `python3 <this
file's folder>/../scripts/cme.py keys <output folder> --plan <plan>` (description "Prepare the
round"). It prints names and counts only:

- `problems`: key headers and rubric blocks (rule 9), kit sections and prepared blocks (rule 8)
  that are missing or malformed. Correct them until it prints `"ok": true`; a round prepared ahead is not kept while one is
  left (`cme.py finish-prepare` runs the same check).
- `review`: the lint's judgement calls on rules 5 and 6, with the findings in `lint.md` in the
  output folder. Read it, correct what is a real breach, and run the check once more.

No lint checks rule 7: pre-flight line 16 is its only check before the round is played.

(With `Parts: questions` or `case` it checks the files written so far.) Then reply `done`.

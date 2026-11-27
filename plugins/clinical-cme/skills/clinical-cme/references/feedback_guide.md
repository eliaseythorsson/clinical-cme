# The feedback: what it says

What the feedback on a round says and how it is written: whose guidance, its structure, the
evidence briefing, how it scales to the answer, its length, the rules it keeps, and what is
prepared ahead and what written live. Two readers:
the **examiner**, with its grading brief (`grading.md`), and the **author**: the kits hold the
feedback's finished text, written when the round is prepared (rule 8 of `standards_kits.md`), and it
is written to this file.

The learner is a busy clinician with 20–30 minutes in total, including any reading. The
feedback therefore teaches the missing point itself — the decision rule, the numbers and the
evidence behind them — rather than send the learner to a 40-page guideline.

## 1. Whose guidance, and for whom

The `start` output gives you `guideline_region`, `specialty` and `pitch`; the items were written
to the same, by rules 2 and 3 and rule 4 (the pitch) of `standards.md`:

- Grade against current guidance of the learner's region, in the edition for their specialty,
  and name that guideline first, with body and year. Where another region's guidance differs
  materially, or guidance changed recently, say so, and grade against the learner's own
  region's (e.g. ESC vs ACC/AHA, NICE vs US); for "International", what either of the major
  European and US societies recommends is right, and both are named (rule 2.1). Units and drug
  names as the items have them.
- **Pitch the feedback to the learner's two paragraphs.** Early stages get more background:
  the mechanism, the reasoning step by step, the terms explained. Senior learners get the
  evidence instead: the trials behind a recommendation, its strength, where the evidence is
  thin or disputed and where guidance stops; no textbook background they have not asked for.
  How far behind the recommendation an item's feedback goes is earned topic by topic (the
  evidence depth, §4.1): the pitch sets the language, the depth sets how far.
- **An aim that names an exam** is graded against that exam's standard sources (its
  syllabus, the textbooks and guidelines it examines from), and the feedback says which; where
  they differ from the region's guideline, both are given and the exam's answer is the one
  keyed. The pitch never lowers the standard of the key.

## 2. Structure of the feedback

Two messages, each sent the moment its part is graded, each opening with the glossary line
(§6.1):

- **Part 1, after the short questions are answered**: glossary line, A (for these items
  only), B, B2. It closes with one line on the score so far and "The case follows." No gap
  summary, no reading list, no reflection prompt, and nothing about the case (rule 1.5 of
  `standards.md`). The case is sent straight after it.
- **Part 2, after the case's last answer**: glossary line, A (for the case), C, D for the
  **whole round** (short questions included), E, E2, F.

A round without a case has one message: A, B, B2, D, E, E2, F. With `case_first`, one message
at the end: A, C, B, B2, D, E, E2, F (`draft --part all`). Either starts with its glossary
line. Leave out any section the round did not have. The draft (`grading.md` §2.2) is already in this order.

### A. Reveal
For each item of the part: the topic (blueprint ID and label), and why it was chosen in plain
words, e.g. "Due for spaced review — last tested 23 Sep, 3/5, gap on chronicity of
hyponatraemia" or "New topic; perioperative medicine is weighted up because you rated
it 2/5". Name the prior open gaps this round re-tested. If the case was a drill
(`drills.md`), say which pattern it targeted and whether the learner avoided it.

### B. MCQs
In the order answered. For each question: the correct letter, the learner's answer, and the
verdict. Then why the correct option is right (the decisive data point in the stem); why each
tempting distractor is wrong, in one line each — what scenario it would be correct for; and an
evidence briefing scaled to the answer (§4), with a granular source.

Mastery for an MCQ: 4–5 correct with sound reasoning (or a letter given sure), 3 correct with
flawed reasoning, 1–2 wrong.

### B2. Focused questions
In the order answered. Grade the reasoning against the key, not how well it is written:

1. **The rubric, every time**: each element with its mark (✓ hit, ◐ partial, ✗ missed) and the
   learner's words that earned it, as a short list. The draft writes it from your marks.
2. **The verdict** with the mastery score, opening with the learner's own words.
3. **Best answer** in two to four sentences.
4. **The decisive point**: the datum or rule that settles the decision, and the tempting wrong
   turn — what scenario it would be right for.
5. **Teaching per element**, by its mark (§4), with a granular source.

| Score | When |
|---|---|
| 5 | Right decision, decisive reason given, the safety element or threshold right; nothing unsafe |
| 4 | Right decision and sound reasoning, one minor omission or imprecision |
| 3 | Right decision with thin, partly wrong or absent reasoning; or an acceptable alternative from the key, well argued |
| 2 | Wrong decision with partly relevant reasoning; or the right decision with an important unsafe element |
| 1 | Wrong or unsafe decision, reasoning off target |
| 0 | Not attempted |

A correct decision without any reasoning scores at most 3: the question asked for the why.
An answer outside the key that is defensible on current evidence is credited, and the key is
corrected in the feedback ("your answer is also acceptable because …"); never grade down
an answer only for not matching the wording of the key.

### C. Case
1. **The rubric, every time**, by stage, as for a focused question: Stage 1 reasoning
   (differential, discriminating tests, predicted results, interim management) apart from
   Stage 2 (final diagnosis, management, disposition). Then the verdict and mastery 0–5 from
   the rubric, opening with the learner's own words.
2. **Final diagnosis and one-paragraph model answer.**
3. **Teaching per element**, by its mark (§4). A test the learner did not order is taught as
   §6.2 says.
4. **How the differential separates**: a compact table, typically 3–4 rows:
   diagnosis | features for | features against | test that separates | expected result.
   Include the incidental findings and say why they were noise.
5. **Pearls / pitfalls**: one to three, specific and actionable.

### D. Gap summary
- New gaps, written precisely enough to re-test: the decision point, the correct rule,
  and what the learner did instead.
- Prior gaps re-tested: resolved, partly resolved or persisting. A gap counts as re-tested
  only if an item asked about its decision point; that item carries `retests` in the form,
  and only then can the gap close.
- Transfer gaps: knowledge shown in one item but not applied in another.
- Calibration notes: confident and wrong (a misconception, highest priority), correct
  but guessed (not yet mastered), unsure but correct (likely to be stronger than they
  feel).
- Mastery score 0–5 per topic tested (0 not seen, 1 major gaps, 2 important gaps,
  3 safe but incomplete, 4 sound with minor gaps, 5 expert), with a one-line rationale.
- **Coding** (when `config.show_coding` is true): one line classifying the round's errors
  (`coding.md` §4). The full coding goes in the form and the log.
- **Errata**: if this round showed that something taught in an earlier session was wrong or
  has since changed, say so here in one line ("Correction to S0012: …"); it is logged as an
  erratum.

### E. Further reading (optional, short)
At most two items, each with a reason it fits the gap, an estimated reading time and its link,
pointed at the specific part: "ESC 2023 endocarditis guideline, section 9 (indications
for surgery) and its surgery table — about 8 minutes". Use verified sources (the learner's
`resource_preferences`, e.g. free only, apply; flag paid sources). The draft carries the kit's
pointers; `templates/resource_library.md` lists dependable starting points by domain.

The same pointers also go into `round.json` as `reading`, one entry each (its shape is in the
form): `save` writes them into the session document and the learner's page lists them under
"Reading & listening", where they can be marked as done. No pointer → an empty list.

### E2. Listening (when `listening.on` is true in the `start` output)
One podcast episode per topic of the round, straight after Further reading: how each is picked,
its form and what goes into `round.json` are in `listening.md`.

### F. Reflection prompt (ends the final message)
See `grading.md` §3. The round is recorded right after this message (reflection pending) and updated when
the learner replies. One reflection covers the whole round.

## 3. The evidence briefing

This is the core teaching content, written so the learner does not need to read the
source to close the gap. For each missed or uncertain point, typically 120–300 words:

- **The rule**: the decision, threshold or step, stated plainly. ("With unknown duration,
  treat hyponatraemia as chronic: limit the rise to 8 mmol/L in 24 h, and to 6 mmol/L in
  patients at high risk of osmotic demyelination.")
- **Why**: the physiological or clinical reasoning in two or three sentences, only as
  much as needed to make the rule stick.
- **The evidence**, granular and verified:
  - Guidelines: society, year, the specific section, table, figure or recommendation
    number, and the class of recommendation and level of evidence where the guideline
    uses them. Summarise what the recommendation says.
  - Trials: name, journal and year, population (n and key inclusion), intervention vs
    comparator, primary outcome with the effect size (absolute rates, HR or RR with 95%
    CI), and the main limitation or the population it does not apply to.
  - Diagnostic tests: sensitivity/specificity or likelihood ratios when they drive the
    decision, and the threshold used.
  - Where evidence is weak, conflicting or extrapolated, say so.
- **Applied to this case**: one or two sentences linking back to what the learner wrote.
- **Source line**: a precise citation with a working link (DOI, PubMed or the society's
  guideline page), and the section to look at.

**Sources.** Every figure and source the feedback states, prepared or live:

- Never invent a trial name, effect size, recommendation number, page, table, DOI or
  PubMed ID. If you cannot verify a detail, state it qualitatively ("reduced mortality in
  the pivotal trial") or omit it. A precise-looking wrong number is worse than none.
- Paraphrase guidelines and papers; quote at most a short phrase where exact wording
  matters.

Lead with the learner's own words: if they said "I'm never sure when to stop
aminoglycosides", answer exactly that first. A prepared block is written before the answer,
so this opening is always yours (§7).

## 4. Scale feedback to the answer, and to the learner's record on the topic

Two things set what an item's feedback holds: how it was answered today, and how often the
learner has answered that topic well before (the **evidence depth**, §4.1). The prepared blocks
follow this table: per rubric element a full briefing for *missed*, a shorter one for
*partial*, two or three lines for *hit*; per MCQ the full briefing (`missed`) and the two or
three lines (`hit`). The draft picks by your marks.

| Learner's answer today | Feedback |
|---|---|
| Wrong, any confidence | Full briefing (§3), at the first depth whatever the topic had earned |
| Correct but marked unsure or guess, or a specific uncertainty stated | Full briefing on the uncertain point, at the first depth; with a depth of 3 or 4, two or three more lines from the depth below |
| Correct and sure, nothing flagged | Two or three lines (why correct, one pearl, source line); with a depth of 2–4, followed by the evidence at that depth (§4.1) |

For focused questions and the case, "correct" means mastery ≥ 4; a focused answer at 3 with
the right decision but weak reasoning gets a briefing on the reasoning that was missing.

`feedback_depth: standard` shortens full briefings to about 120 words and halves the word
ranges of §4.1; `detailed` (the default) allows up to about 300 per point.

### 4.1 Evidence depth

How far behind the recommendation the feedback on an item answered well goes, by its `depth`:
`evidence_depth.md`. The examiner reads it when `answer` prints a `depth` above 1 for an item;
the author when the plan gives an item a `depth`.

### 4.2 The sibling line (two-level blueprint)

Where the blueprint has sub-topics, an item names its own (`subtopic`), and the grading form
gives `sibling` under `given` (`answer` prints it as `siblings`): the other sub-topic of the
same disease the learner answered last time, with its date and score. Write **one line**
tying today's point to it: the shared mechanism, drug class or diagnostic frame, and where
the two decisions part ("Last month's question on stroke prevention turned on the same
bleeding-risk trade-off; here the stent adds a second antiplatelet, which is why triple
therapy is kept short"). The draft marks it `[live: the sibling line …]`. It links, it does
not re-teach: no second briefing, and nothing of the sibling's key the learner has not seen
in its own feedback. No `sibling`: no line.

## 5. Length and time

Aim for feedback the learner can read in roughly a third of their session time
(`session_minutes`): about 1,200–2,000 words for a 20–30 minute session over both parts, less
for shorter sessions. Each focused question takes about 150–300 words of it. Spend the words
where the gaps are. Use headings, short paragraphs and the tables above so it scans quickly. Do
not pad correct answers to look thorough.

**Tailoring always wins over speed.** About 30 seconds from the answers to the feedback is the
target for a typical answer, which the prepared text makes possible; an answer outside the key,
a defensible alternative or a key that needs correcting gets the time it needs. The round's
clock measures the wait; nobody shortens the feedback to meet it.

## 6. Rules the feedback keeps

These bind everything the learner reads in the feedback: the prepared blocks (the author writes
them to these rules) as much as what you write live. The rulebook (`standards.md`) points here
as rules 5.3, 10 and 11.

### 6.1 The glossary line (rule 5.3)

Each feedback message opens with a one-line glossary of the abbreviations it uses ("Abbreviations:
ALT alanine aminotransferase; DOAC direct oral anticoagulant"), those on the rulebook's list of
common abbreviations (rule 5.2) excepted: the draft names the ones its prepared text uses that
are not on that list; add those your own text brings. The line starts with the word "Abbreviations:" and
comes before the reveal. Each message's line is complete on its own: an abbreviation explained
in the first message is explained again in the second if it is used there. It is part of the
message as sent, so it is logged with it (`grading.md` §4). A message that uses no abbreviation has no line.

### 6.2 Results the learner did not see (rule 10)

The feedback teaches with every result the case was written with, including those the learner
never ordered. Where the decisive test is one clinicians often fail to order (a crux test,
rule 7 of `standards.md`), say whether the learner asked for it, and grade that step. A result
the learner did not see is never quoted as if it had been shown;
instead the feedback says so and uses it:

1. **Say it was not ordered.** Name the test, say plainly that it should have been requested
   and why at that point ("You did not request a D-dimer; with a Wells score of 2 it was the
   next step."). A result supplied through "Add if not ordered" counts as not requested.
   This is a missed element in the rubric (data gathering), graded as such.
2. **Give the result and what it would have changed.** Quote it marked as unseen ("not
   ordered: the result was …") and say what it would have done to the diagnosis, the
   management or the disposition, in one or two sentences.
3. **Not every unseen result is a miss.** A test the learner reasonably left out (it would
   not have changed management in their plan) may be quoted for completeness, marked as
   unseen, without grading down.

The differential table and the model answer follow the same marking: a value the learner did
not see carries "(not ordered)" beside it. A prepared block for a missed testing element is
written for the test not ordered; one for a hit, for the result seen.

### 6.3 Text for the learner speaks plainly (rule 11)

Everything the learner reads (items, results, feedback, the close) is written for a clinician,
in clinical language. It never names the skill's own machinery: no rule numbers, file or
command names, the key, its headers or the kit, the sealed files, the results bank, the lint,
the author or the checker, the work folder, the publish set, the draft or a prepared block.
Cite the guideline or paper, not this brief. `save` warns when the feedback as sent does, and
the simulation fails a run for it.

## 7. Prepared text and live text

Most of what the feedback says does not depend on the answer: the model answer, why each
distractor is wrong, the decisive point, the briefing on each rubric element. It is written as
finished text when the round is prepared, in the kits' **prepared blocks** (rule 8 of
`standards_kits.md`), and source-checked with the round. What only the answer can prompt is written
live, once the answers are in. Live grading stays honest because the marks come first and the
text follows them, never the other way round.

Live, in every message:

- the glossary line (§6.1), the verdict lines and the score so far;
- **the opening in the learner's own words**: what they wrote or doubted, answered first (§3);
- calibration, transfer between items, the gap summary and the coding line (§2 D);
- the sibling line, where the item has a `sibling` (§4.2);
- **credit for a defensible answer outside the key**, and **corrections to the key** (`grading.md` §2.4);
- the reading and listening picks (§2 E, `listening.md`) and the reflection prompt.

How the examiner marks first and then uses, rewrites or drops each prepared block: `grading.md`
§2. A prepared block is written so that it can be sent as it stands.

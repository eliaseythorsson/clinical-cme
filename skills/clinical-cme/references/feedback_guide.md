# Grading and feedback

The learner is a busy clinician with 20–30 minutes in total, including any reading. The
feedback should therefore teach the missing point itself — the decision rule, the
numbers and the evidence behind them — rather than send the learner to a 40-page
guideline. External reading is a supplement, pointed at the exact section that matters.

## 1. Before writing feedback: verify

Feedback comes in two parts — the short questions' as soon as they are answered, the case's
after its last answer — and each rests on evidence checked for that part
(`references/evidence_check.md`). Where a checker has done the check — when the round was
prepared, or while the learner was answering — its file (`evidence_questions.md`,
`evidence_case.md`) is ready: read it and grade, **without running the verification list
again** — the checker has already retried what it could not reach (`evidence_check.md` §3).
Its `Checked:` line gives the date and how many claims are not verified; a prepared round can
be up to 30 days old, so if you know or suspect that guidance on a point has changed since
then, search that point once the answers are in. Only where a part has **no evidence file**
do you check for yourself, now that its answers are committed:

- Check every specific claim you are about to make that could have changed or that you
  are not certain of: guideline recommendations and their class/level, thresholds,
  doses, trial results, approval status. Use web search and fetch the primary source
  (society guideline, journal article, PubMed record) rather than a secondary summary; a
  page that was not reached has other routes (`evidence_check.md` §3).
- Grade against current guidance for the learner's region and specialty, and say so where
  guidance changed recently or regions disagree (e.g. ESC vs ACC/AHA, NICE vs US): rule 2
  of `standards.md`. Units and drug names as in rule 3; depth as the pitch of rule 4.
- Never invent a trial name, effect size, recommendation number, page, table, DOI or
  PubMed ID. If you cannot verify a detail, state it qualitatively ("reduced mortality in
  the pivotal trial") or omit it. A precise-looking wrong number is worse than none.
- Paraphrase guidelines and papers; quote at most a short phrase where exact wording
  matters.
- Keep searches efficient: typically 2–6 per part. They are listed in advance in the sealed
  files ("verification list": the questions' in `sealed_questions.md`, the case's in
  `sealed_case.md`). With no evidence file for a part, run its list in one parallel batch,
  then fetch the primary sources you will cite, also in one batch. Never run them yourself
  before that part's answers are in.
- After a helper's check, search only for what the learner's answers raise that the file
  does not cover (a stated uncertainty, an unexpected but defensible answer). A claim the file
  marks "not verified" is stated qualitatively or left out; search it yourself only if the
  learner's answer turns on it. If the file says a key is contradicted by current guidance,
  correct the key before grading and grade against the guidance.

## 2. Structure of the feedback

Two messages, each sent the moment its part is graded. **Every feedback message starts with
the glossary line** of rule 5.3: one line, "Abbreviations: …", above the reveal, listing the
abbreviations that message uses, those on the rule's list excepted. Each message's line is
complete on its own: an abbreviation explained in the first message is explained again in the
second if it is used there. The line is part of the message as sent, so it is logged with it
(§8). A message that uses no abbreviation has no line.

- **Part 1, after the short questions are answered**: glossary line, A (for these items
  only), B, B2. It closes with one line on the score so far and "The case follows." No gap
  summary, no reading list, no reflection prompt, and nothing about the case (rule 1.5). The
  case is sent straight after it.
- **Part 2, after the case's last answer**: glossary line, A (for the case), C, D for the
  **whole round** (short questions included), E, F.

A round without a case has one message: A, B, B2, D, E, F. With `case_first`, one message at
the end: A, C, B, B2, D, E, F. Either starts with its glossary line. Leave out any section the
round did not have.

### A. Reveal
For each item of the part: the topic (blueprint ID and label), and why it was chosen in plain words,
e.g. "Due for spaced review — last tested 23 Sep, 3/5, gap on chronicity of
hyponatraemia" or "New topic; perioperative medicine is weighted up because you rated
it 2/5". Name the prior open gaps this round re-tested. If the case was a drill
(`case_design.md` §9), say which pattern it targeted and whether the learner avoided it.

### B. MCQs
In the order answered. For each question: the correct letter, the learner's answer, and the
verdict. Then:
- why the correct option is right (the decisive data point in the stem);
- why each tempting distractor is wrong, in one line each — what scenario it would be
  correct for;
- an evidence briefing scaled to the answer (§4), with a granular source.

### B2. Focused questions
In the order answered. For each, grade the reasoning against the sealed key (§11.3 of
`case_design.md`), not against how well it is written:
1. **Best answer** in two to four sentences, then the learner's answer in one line and the verdict
   with the mastery score.
2. **Rubric**: each element ✓ hit, ◐ partial or ✗ missed, with a short note.
3. **The decisive point**: the datum or rule that settles the decision, and the tempting wrong
   turn — what scenario it would be right for.
4. **Evidence briefing** scaled to the answer (§4), with a granular source.

Mastery for a focused question:

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
1. **Final diagnosis and one-paragraph model answer.**
2. **Rubric** for each stage: the expected elements, each marked ✓ hit, ◐ partial or
   ✗ missed, with a short note on what was right or what was missing. Grade the Stage 1
   reasoning (differential, discriminating tests, predicted results, interim
   management) separately from Stage 2 (final diagnosis, management, disposition).
3. **How the differential separates**: a compact table, typically 3–4 rows:
   diagnosis | features for | features against | test that separates | expected result.
   Include the incidental findings and say why they were noise.
4. **Evidence briefing** (see §3) for the points missed or flagged as uncertain.
5. **Pearls / pitfalls**: one to three, specific and actionable.

### D. Gap summary
- New gaps, written precisely enough to re-test: the decision point, the correct rule,
  and what the learner did instead.
- Prior gaps re-tested: resolved, partly resolved or persisting. A gap counts as re-tested
  only if an item asked about its decision point; that item carries `retests` in its key
  header, and so in the round record, and only then can the gap close (`state_schema.md` §2, §4).
- Transfer gaps: knowledge shown in one item but not applied in another.
- Calibration notes: confident and wrong (a misconception, highest priority), correct
  but guessed (not yet mastered), unsure but correct (likely to be stronger than they
  feel).
- Mastery score 0–5 per topic tested (0 not seen, 1 major gaps, 2 important gaps,
  3 safe but incomplete, 4 sound with minor gaps, 5 expert), with a one-line rationale.
- **Coding** (when `config.show_coding` is true): one line classifying the round's errors
  (knowledge / data gathering / synthesis / slip, knowledge type, severity, and a bias only
  when the learner's words show it) and the write-up score. See `analysis_framework.md` §1.5.
  The full coding goes in the round JSON and the log.
- **Errata**: if this round showed that something taught in an earlier session was wrong or
  has since changed, say so here in one line ("Correction to S0012: …"); it is logged as an
  erratum.

### E. Further reading (optional, short)
At most two items, each with a reason it fits the gap and an estimated reading time,
pointed at the specific part: "ESC 2023 endocarditis guideline, section 9 (indications
for surgery) and its surgery table — about 8 minutes". Use verified sources (the learner's
`resource_preferences`, e.g. free only, apply; flag paid sources). `templates/resource_library.md`
lists dependable starting points by domain.

### F. Reflection prompt (ends the final message)
See §6. The round is recorded right after this message (reflection pending) and updated when
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

Lead with the learner's own words: if they said "I'm never sure when to stop
aminoglycosides", answer exactly that first.

## 4. Scale feedback to the answer

| Learner's answer | Depth |
|---|---|
| Wrong, any confidence | Full briefing |
| Correct but marked unsure or guess, or a specific uncertainty stated | Full briefing on the uncertain point |
| Correct and sure, nothing flagged | Two or three lines: why correct, one pearl, source line |

For focused questions and the case, "correct" means mastery ≥ 4; a focused answer at 3 with
the right decision but weak reasoning gets a briefing on the reasoning that was missing.

`feedback_depth: standard` shortens full briefings to about 120 words; `detailed` (the
default) allows up to about 300 per point.

## 5. Length and time budget

Aim for feedback the learner can read in roughly a third of their session time
(`session_minutes`): about 1,200–2,000 words for a 20–30 minute session over both parts, less
for shorter sessions. Each focused question takes about 150–300 words of it. Spend the words where the gaps are. Use headings, short paragraphs and the
tables above so it scans quickly. Do not pad correct answers to look thorough.

## 6. Reflection prompt (append to the feedback)

Use this wording, adapted to the round's topics:

> **Quick reflection** (about a minute; it shapes when and how these topics return)
> 1. **Comfort** with each area, 1–5 (1 = would need to look it all up, 5 = could teach it):
>    Case — [topic]: _ · Q1 — [topic]: _ · Q2 — [topic]: _ · Q3 — [topic]: _ · Q4 (focused) — [topic]: _
> 2. **How you think you did** today overall, 1–5: _
> 3. **In a sentence or two**: what do you feel solid on in these areas, and where do you
>    feel shaky? Name anything you'd like to see come back.
> 4. *(Optional)* Minutes spent on any further reading: _
>
> A short reply like "3, 4, 2, 5, 3 · 3 · solid on X, shaky on Y" is plenty. Reply **skip** to
> save without a reflection.

How the reply is used (`reflect` command; see `state_schema.md` §3–4):
- Comfort per topic is compared with the graded mastery. Feeling secure while scoring
  low (comfort ≥ mastery + 2) marks the topic **overconfident**: it is not advanced and
  returns after three days. Scoring well while feeling unsure marks it
  **underconfident**: it advances, but returns sooner to consolidate.
- Shaky areas named in the free text become open gaps with source `self`. If they belong
  to a topic that was not tested, that topic is created or pulled forward to within a
  week. Map each one to a blueprint ID; if none fits, create a new ID in the blueprint's
  style and tell the learner.
- Comfort ratings feed the domain self-ratings that weight how often new topics from each
  domain are sampled. A high rating lowers a domain's share only as far as the answers in
  that domain bear it out (`state_schema.md` §4).

After the reply, say in one line how it changed the plan, without naming future dates
per topic, for example: "Noted — the anticoagulation reversal question you raised is now
on the list for this week."

## 7. If the learner disputes a grade

Re-check the point against the primary source. If the learner is right, or the evidence
supports both positions, say so plainly, correct the model answer and adjust the score
before recording. If the original grading stands, explain why with the specific source.
Never defend a grade by repeating it.

The whole debate goes into the log verbatim (Discussion section), and each change goes into
`grade_changes` in the reflection JSON (with the new score in `items`):
`{"item": "Q2", "topic": "CARD-03", "from": 2, "to": 4, "outcome": "learner_right"}`.
Use `both_defensible` or `upheld` as appropriate. If the dispute changes the coding, code
the final position. The review reports dispute outcomes honestly; a learner who is often
right is telling you something about the grading.

### 7.1 A score the learner sets, a gap the learner closes

"Record it as 4" or "close that gap" is not a dispute: the learner is not arguing the
evidence, they are deciding what their record says. It is their record, so do it, without
arguing and without changing your grading. Never write it as a dispute outcome (your
grading did not change), and never edit the ledger by hand.

- **Before the close**, in the reflection JSON (`state_schema.md` §3):
  `"learner_scores": [{"item": "Q2", "type": "mcq", "topic": "CARD-03", "score": 4, "note": "the learner's words"}]`
  and `"learner_closed_gaps": [{"gap": "G0007", "note": "…"}]` (a gap by its id, or
  `{"topic": "CARD-03"}` for one this round opened).
- **After the close** (also in a later conversation, after reading the store with the
  session's document and `open`): `python3 cme.py override --work <work> --scores '[…]'
  --close-gaps '[…]'` with the same entries (`--session <id>` for a round other than the
  last), then publish its `files`.

What the engine does with it: the item keeps both scores, `graded` (yours) and `mastery`
(the learner's, marked `set_by: learner`); the topic is scheduled with the learner's score
and the round's score follows it; the change is a `grade_changes` entry with outcome
`learner_set`. A gap closed this way moves to `resolved` marked `closed_by: learner` and
gets **no retest**; the topic still comes back when its score says so. The session document
gets a "Set by the learner" section naming both scores and who closed the gap, so the log
does not depend on what you write in part B. A learner-set score does not close the gap on
that point: it stays open unless the learner asks for that too (say so in one line). The
review counts these apart from disputes.

If the learner gives a reason that is about the evidence ("the guideline says otherwise"),
it is a dispute: re-check first, and use this path only if they still want their own score
after your grading stands.

## 8. The log needs the feedback verbatim

Part A of the log copies both feedback messages exactly as sent (`session_log.md` §2): write
part 1 to `feedback_questions.md` and part 2 to `feedback.md` in the work folder right after
sending each, while the learner reads; `cme.py save` finds them there. Keep tables and headings in plain Markdown so the copy renders well on the
page.

## 9. Feedback kits: notes made while the learner answers

Feedback is written when the answers are in, but most of its substance does not depend on
them. That substance is put into a kit when the items are written, by whoever writes them
(`author.md`), so that grading is quick and the feedback can be written straight away. What
`kit_questions.md` and `kit_case.md` hold is rule 8 of `standards.md`.

At grading, correct the kit's figures and sources from the evidence check before using them,
mark the rubric against what the learner wrote, scale each briefing to the answer (§4) and
lead with the learner's own words (§3). The kit never replaces reading the answer: credit
what is defensible though unforeseen, and write the parts only the answer can prompt
(transfer gaps, calibration, the errors' coding) fresh.

**The grader is not the author.** Where an author agent wrote the items, the key and the kit
are one clinician's view, and you are the second. Before using a key, ask whether you would
have answered the same from the vignette alone, and whether the checked evidence supports it.
If the key is wrong, dated, or narrower than current guidance, grade against the guidance,
say so in the feedback in one line ("the intended answer was X; current guidance also
supports Y"), and credit the learner. If an item turns out to be flawed (two defensible best
answers, a stem that gives the answer away, a missing datum), say so, score it generously,
and do not record a gap from it. Never defend a key because it is the key.

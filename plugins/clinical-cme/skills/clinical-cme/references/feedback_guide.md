# The examiner's brief: grading and feedback

Everything the examiner needs to grade a round and write its feedback, in one file. Read all of
it, with the grading form `answer` writes (`round.json`, its `_form` says how to fill it), and no
other reference before grading; of the round's own files, the sealed file, the evidence file and
the draft, as the turn says. The rules for writing items are in the rulebook
(`standards.md`); the few that bind the feedback are written here (§1, §10), and the rulebook
points to them.

The **author** reads §1–5 and §9–10 too: the kits hold the feedback's finished text, written
when the round is prepared (rule 8 of `standards.md`), and it is written to this brief.

The learner is a busy clinician with 20–30 minutes in total, including any reading. The
feedback therefore teaches the missing point itself — the decision rule, the numbers and the
evidence behind them — rather than send the learner to a 40-page guideline.

**How a part is graded** (ADR 0009), once its answers are in:

1. **Verify** against the checked evidence (§1).
2. **Mark the form before any prepared text is used** (§9.1): every rubric element hit, partial
   or missed, each tied to the learner's words; an MCQ right or wrong.
3. **`cme.py draft --work <work> --part questions|case|all`** puts the prepared text your marks
   call for into the feedback's order (§9.2).
4. **Write the live parts and adapt the rest** (§9.3), then send. Score and code in the form
   (§2, §11).

## 1. Before writing feedback: verify

Feedback comes in two parts — the short questions' as soon as they are answered, the case's
after its last answer — and each rests on evidence checked for that part
(`evidence_check.md`). Where a checker has done the check — when the round was
prepared, or while the learner was answering — its file (`evidence_questions.md`,
`evidence_case.md`) is ready: read it and grade, **without running the verification list
again** — the checker has already retried what it could not reach. Its `Checked:` line gives
the date and how many claims are not verified; a prepared round can be up to 30 days old, so if
you know or suspect that guidance on a point has changed since then, search that point once the
answers are in. Only where a part has **no evidence file** do you check for yourself, now that
its answers are committed:

- Check every specific claim you are about to make that could have changed or that you
  are not certain of: guideline recommendations and their class/level, thresholds,
  doses, trial results, approval status. Use web search and fetch the primary source
  (society guideline, journal article, PubMed record) rather than a secondary summary; a
  page that was not reached has other routes (`evidence_check.md` §3).
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
  correct the key before grading and grade against the guidance. A claim the file does not
  confirm that a prepared block states is flagged in the draft (§9.2): correct it there.

**Whose guidance, and for whom** (the `start` output gives you `guideline_region`, `specialty`
and `pitch`; the items were written to the same, by rules 2 and 3 and rule 4 (the pitch) of
`standards.md`):

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
(§10.1):

- **Part 1, after the short questions are answered**: glossary line, A (for these items
  only), B, B2. It closes with one line on the score so far and "The case follows." No gap
  summary, no reading list, no reflection prompt, and nothing about the case (rule 1.5 of
  `standards.md`). The case is sent straight after it.
- **Part 2, after the case's last answer**: glossary line, A (for the case), C, D for the
  **whole round** (short questions included), E, E2, F.

A round without a case has one message: A, B, B2, D, E, E2, F. With `case_first`, one message
at the end: A, C, B, B2, D, E, E2, F (`draft --part all`). Either starts with its glossary
line. Leave out any section the round did not have. The draft (§9.2) is already in this order.

### A. Reveal
For each item of the part: the topic (blueprint ID and label), and why it was chosen in plain
words, e.g. "Due for spaced review — last tested 23 Sep, 3/5, gap on chronicity of
hyponatraemia" or "New topic; perioperative medicine is weighted up because you rated
it 2/5". Name the prior open gaps this round re-tested. If the case was a drill
(`case_design.md` §9), say which pattern it targeted and whether the learner avoided it.

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
   §10.2 says.
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
  (§11.5). The full coding goes in the form and the log.
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
One podcast episode per topic of the round, 15 to 90 minutes, as specific as possible to the
gap the learner showed on that topic, straight after Further reading:

> **Listening**
> - **Atrial fibrillation** — <show>, "<episode title>" (52 min): when to start
>   anticoagulation after surgery, the step you were unsure of.
>   https://open.spotify.com/episode/<id>

Each line: the topic, the show, the title, the length, one line on why it fits what the
learner did, and the Spotify link on its own. How each pick is chosen, topic by topic:

1. **Name the gap**: what the learner actually missed or was unsure of on the topic (for a
   correct, sure answer: the point the item tested).
2. **A candidate covers it** → give it, with no new search. The kit's `## Listening` section
   (the draft carries it) holds up to three per topic, each with the failure point it matches;
   the one that matches the learner's gap is the pick.
3. **No candidate covers it** (an unforeseen gap, or a kit without candidates) → search for
   an episode on that specific gap: allowed now, since the part's answers are in (rule 1.3;
   the short questions' topics from turn 2 on, behind the scenes; the case's only after its
   last answer). One batch of searches for all such topics and one batch of fetches, by the
   routes of `evidence_check.md` §6, and the same verification: only an episode whose own
   Spotify page was reached, with the title and the length read from it. Never build or
   guess a link.
4. **Nothing better found** → the best of the candidates. **No candidate either** → say so
   plainly in the section ("No suitable episode found for <topic>"), and give no link.

The learner's sources always hold (`listening.trusted` and `listening.avoid` in the `start`
output): prefer a trusted show where it fits the gap as well, never pick an avoided one.
Spotify has no link that saves an episode to the library: the link opens the episode in the
app, and one tap there saves it; promise nothing more (say so once, the first time the
section appears).

The picks also go into `round.json` as `listening`, one entry per topic that got one, so that
`save` writes them into the session document; an empty list when no topic got one.

`listening.ask_sources` true → the learner has not been asked for their shows yet: end the
section with one line, once: "Tell me any podcasts you trust, or want me to avoid, and I'll
keep to them; say 'listening off' if you'd rather not have this section." What they answer
goes into the reflection form as `podcast_sources`; no answer needs nothing, and it is not
asked again.

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
aminoglycosides", answer exactly that first. A prepared block is written before the answer,
so this opening is always yours (§9.3).

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

### 4.1 Evidence depth: the better a topic is known, the further behind the recommendation

A learner who keeps answering a topic well no longer needs the rule; what they can still
gain is knowing what the rule rests on and how far that can be trusted. A learner who
missed it needs the rule, the reasoning and the recommendation, taught well, and nothing
that competes with them for attention.

The grading form gives each item its `depth` under `given` (`answer` prints it too:
`{"Q1": {"level": 3, "name": "design", "in_a_row": 2}}`): the depth the item gets **if it
was answered well today**. The engine counts, per topic (per sub-topic where the blueprint has
two levels), how many times in a row its items were answered well (mastery ≥ 4, no misconception, no guessed MCQ), back from the last
round. A focused question goes at most one depth beyond what its own aspect of the topic
has earned; an item on an open gap stays at 1. No `depth` (the ladder is off,
`config.evidence_ladder` false): every item is at depth 1.

| Depth | Answered well before, in a row | What the feedback adds for an item answered well today | Words |
|---|---|---|---|
| 1 `guidance` | 0: new, missed the last time, or an open gap | Nothing: the two or three lines of §4, the recommendation and its source | – |
| 2 `studies` | 1 | **Which studies the recommendation rests on**: the one or two that carry it, each with name, year, who was studied, what was compared and the primary result as absolute figures; and the class and level the guideline gives on their strength | 60–100 |
| 3 `design` | 2–3 | **The design features that decide how far the result can be trusted, and for whom**: the one or two that matter for this decision, chosen from who was excluded, the comparator and its dose, blinding, the endpoint (composite, surrogate, how it was adjudicated), a non-inferiority margin, early stopping, intention to treat against per protocol, relative against absolute effect, how few events would overturn it | 100–160 |
| 4 `frontier` | 4 or more | **Where the evidence stops or is disputed**: trials or meta-analyses that disagree and why; how the panel got from the evidence to the recommendation (extrapolation, expert opinion, why two societies read the same trials differently); the statistical or philosophical question underneath (a subgroup claim, a surrogate standing in for an outcome, an explanatory trial applied to a patient it would have excluded, a Bayesian re-reading); trials under way. It may end with one question to think about | 120–200 |

How it is applied:

- **Each depth starts with one line of the depth before it** (the study named before its
  design is discussed), and picks what bears on the decision the item tested. It is an
  appraisal for a colleague, never a checklist and never a recital of everything known.
- **Missed today → the first depth, in full.** The teaching is as informed and as nuanced
  as ever: the decision rule, the reasoning, the recommendation with its strength, the key
  figure, the exception and the pitfall (§3). What is left out is the appraisal of the
  studies: no trial design, no statistics beyond the figure that drives the decision, no
  philosophy of the evidence. A study may be named in a clause as the source. The record
  starts again from there: answered well next time, the topic is at depth 2.
- **The case**: its `depth` applies to the one or two decisions at the centre of the case
  that the learner got right (a rubric element marked ✓); elements missed or partial are
  taught at the first depth. A case at mastery below 4 gets no deeper section.
- **Only checked evidence.** The kit's `deeper` block (rule 8 of `standards.md`) is the
  finished text at the plan's depth, its studies checked with the verification list; the draft
  includes it only for an item answered well. Where the kit has none (a round prepared before
  the record changed, a focused question on another aspect than planned), write from the
  evidence file, or search that study now, since the part's answers are in. §1 holds: a design
  feature or a figure you could not verify is left out, and a depth that cannot be reached
  with checked facts is given at the depth that can.
- **The pitch sets the language, the depth sets how far** (§1): an early-stage learner
  at depth 3 gets the same appraisal with its terms explained ("non-inferiority: the trial
  only set out to show the new drug is not much worse").
- **It replaces words, it does not add a section to read** (§5): the words come out of the
  round's budget, gaps first. Over budget, shorten the deeper text before a briefing.
- **Say it in a clause, in plain words** (§10.3), where the deeper text starts: "You've
  answered this well three times running, so a closer look at the trial behind it:". No
  level numbers or names to the learner.
- The learner asks in the round to go deeper on an item, or to skip the trials: do it for
  that item. As a standing choice it is the setting (`requests.md` §1).

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

How the reply is used (the reflection form; `state_schema.md` §3–4):
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
  that domain bear it out.

After the reply, say in one line how it changed the plan, without naming future dates
per topic, for example: "Noted — the anticoagulation reversal question you raised is now
on the list for this week."

## 7. If the learner disputes a grade

Re-check the point against the primary source. If the learner is right, or the evidence
supports both positions, say so plainly, correct the model answer and adjust the score
before recording. If the original grading stands, explain why with the specific source.
Never defend a grade by repeating it.

The whole debate goes into the log verbatim (Discussion section), and every dispute settled
goes into `grade_changes` in the reflection JSON, one entry each, whatever the outcome (with
the new score in `items` when it changed):
`{"item": "Q2", "topic": "CARD-03", "from": 2, "to": 4, "outcome": "learner_right"}`.
Use `both_defensible` or `upheld` as appropriate; an upheld grade is recorded too, with `from`
equal to `to`. A challenge to a teaching point rather than a mark ("correct it in the record")
is a dispute as well: the item's score as `from` and `to`, the outcome saying who was right,
and the corrected point in the Discussion. If the dispute changes the coding, code the final
position.

A dispute that arrives without the reflection: settle it in that reply, end it by asking for
the reflection, and close only when the reflection (or "skip") arrives; never close on the
dispute message as if it were the reflection. The review reports dispute outcomes honestly; a learner who is often
right is telling you something about the grading.

### 7.1 A score the learner sets, a gap the learner closes

"Record it as 4" or "close that gap" is not a dispute (and "I know this, stop bringing it
back" is one step that does both and more: §7.2): the learner is not arguing the
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
(the learner's, marked `set_by: learner`); the topic is scheduled with the learner's score,
exactly as it would be either side of the close (`state_schema.md` §3.1), and the round's score follows it; the change is a `grade_changes` entry with outcome
`learner_set`. A gap closed this way moves to `resolved` marked `closed_by: learner` and
gets **no retest**; the topic still comes back when its score says so. The session document
gets a "Set by the learner" section naming both scores and who closed the gap, so the log
does not depend on what you write in part B. A learner-set score does not close the gap on
that point: it stays open unless the learner asks for that too (say so in one line). The
review counts these apart from disputes.

If the learner gives a reason that is about the evidence ("the guideline says otherwise"),
it is a dispute: re-check first, and use this path only if they still want their own score
after your grading stands.

### 7.2 The learner's stop: "I know this, stop bringing it back"

Said in any words (also "stop this loop", "I disagree with the premise, drop it"), it is one
action with one entry, the same before or after the close: the learner's score for the item
(5 unless they name one), every open gap on that topic closed by the learner, and the topic
scheduled at the longest interval (90 days by default), whatever drill-down or gaps would have
said. The learner's judgement decides: do it at once, without arguing, and do not ask them to
choose between a score and a gap. No topic is retired for good: after the interval it comes
back like any other.

- **Before the close**, in the reflection JSON: `"learner_stops": [{"item": "Q2", "type":
  "mcq", "topic": "CARD-03", "score": 5, "position": {"point": "…", "text": "…"}}]` (`score`
  and `position` optional).
- **After the close**: `python3 cme.py override --work <work> --stops '[…]'` with the same
  entries, then publish its `files`.

**The position note.** If the learner says what they disagree with, keep it as `position`:
`point` names the one decision point in a few words, `text` is what they hold, in their own
words, unedited. It is not a note on the whole topic. From then on, every round on the topic
respects it (`standards.md` rule 12): no item turns on that point, and you never mark the
learner down on it. When `answer` prints `positions` for an item, grade with them: an answer
that follows the note is not a miss, gets no gap and no error code on that point, and the
feedback does not reopen it.

- You may say what the evidence says **once**, at the moment the note is set: one line, with
  the source ("Noted. For the record, ESC 2023 recommends X; your position is kept."). Then
  never again on that point.
- Only if the evidence file for a later item says that guidance on that exact point has
  changed since the note's date (and the note has no `reopened`) may you raise it once more,
  in one line with the source; then run `cme.py position --work <work> --reopened <id>`.
- The learner can take a note back at any time ("drop my position on …"): `cme.py position
  --work <work> --drop <id>` (alone, `position` lists the notes in force). Each progress review
  lists the notes to keep or drop (`progress_review.md`); a note not kept at a review lapses
  after about six months.

The session document gets the stop and the note word for word in its "Set by the learner"
section. The review counts stops apart from disputes and from other learner-set scores.

## 8. The log needs the feedback verbatim

Part A of the log copies both feedback messages exactly as sent (`session_log.md` §2): write
part 1 to `feedback_questions.md` and part 2 to `feedback.md` in the work folder right after
sending each, while the learner reads; `cme.py save` finds them there. Keep tables and headings
in plain Markdown so the copy renders well on the page.

`save` also compares each draft with the message as sent and records in the session document,
as `prepared_feedback`, which prepared blocks were used as prepared, which were changed and
which were left out. That record is the log's alone: nothing about prepared or adapted text
appears in the feedback, and nothing of it goes into the ledger.

## 9. Prepared text and live text

Most of what the feedback says does not depend on the answer: the model answer, why each
distractor is wrong, the decisive point, the briefing on each rubric element. It is written as
finished text when the round is prepared, in the kits' **prepared blocks** (rule 8 of
`standards.md`), and source-checked with the round. What only the answer can prompt is written
live, once the answers are in. Live grading stays honest because the marks come first and the
text follows them, never the other way round.

### 9.1 Marks before text

Before any prepared text is used, fill in the grading form (`round.json`) from the answer and
the checked evidence:

- **Every rubric element** of a focused question and the case: `mark` hit, partial or missed;
  `quote`, the learner's own words that earned the mark (for a missed element: empty, or what
  they wrote instead); `note`, a few words of yours. A mark without words from the answer is
  not a mark; `save` warns about a hit or partial without a quote.
- **Every MCQ**: `correct` and `confidence` as the learner gave it.
- An answer that follows one of the learner's position notes (`given.positions`; rule 12 of
  `standards.md`, §7.2) is not a miss on that point: mark it hit, with no gap and no error.

Mastery and the coding may wait until after the draft, but not the marks.

### 9.2 The draft

`python3 cme.py draft --work <work> --part questions` (`case` for the case, `all` for one
message with everything, as with `case_first`) refuses while a mark is blank. Then it writes
`draft_questions.md` (the questions' feedback, with a case still to come) or `draft.md` (the
final feedback), and prints counts only. The draft holds, in the order of §2:

- the reveal blocks;
- per item: the **rubric as marked**, each element with ✓ ◐ ✗ and the learner's words, ready to
  send; then, for an MCQ, the model block, the distractors and the `hit` or `missed` block
  (`missed` also for a right answer given unsure or as a guess); for a focused question and the
  case, the model block, the decisive point or the differential, one block per element chosen
  by its mark, and the pearls; the `deeper` block only for an item answered well (§4.1);
- the kit's reading pointers and listening candidates as notes, for the final message;
- `[live: …]` where only you can write, and a `<!-- check: … -->` line above a block that
  states a claim the evidence file does not confirm, or when a key was contradicted.

Prepared blocks are between `<!-- block: Q4.2 missed -->` and `<!-- /block -->`. Read the
draft, not the kit: it holds every block your marks call for.

### 9.3 What you write live, and what you may change

Live, in every message:

- the glossary line (§10.1), the verdict lines and the score so far;
- **the opening in the learner's own words**: what they wrote or doubted, answered first (§3);
- calibration, transfer between items, the gap summary and the coding line (§2 D);
- the sibling line, where the item has a `sibling` (§4.2);
- **credit for a defensible answer outside the key**, and **corrections to the key** (§9.4);
- the reading and listening picks (§2 E, E2) and the reflection prompt.

Every prepared block may be used as it stands, rewritten or dropped: rewrite it where the answer
needs something the block did not foresee, where a `check` line flags it, or where the evidence
check corrected the key; drop it where it teaches what the learner showed they know. Then send
the message without the comment lines and with no `[live: …]` left, and write it as sent
(§8). The feedback never says what was prepared or adapted.

A round prepared before prepared blocks existed has none: the draft says so where a block is
missing, and you write that part from the kit's notes, as before.

### 9.4 The grader is not the author

Where an author agent wrote the items, the key, the rubric and the prepared text are one
clinician's view, and you are the second. Before using a key, ask whether you would have
answered the same from the vignette alone, and whether the checked evidence supports it. If
the key is wrong, dated, or narrower than current guidance, grade against the guidance, say so
in the feedback in one line ("the intended answer was X; current guidance also supports Y"),
credit the learner, and rewrite the blocks that teach the old key. If an item turns out to be
flawed (two defensible best answers, a stem that gives the answer away, a missing datum), say
so, score it generously, and do not record a gap from it. Never defend a key because it is the
key, and never a block because it was prepared.

## 10. Rules the feedback keeps

These bind everything the learner reads in the feedback: the prepared blocks (the author writes
them to these rules) as much as what you write live. The rulebook (`standards.md`) points here
as rules 5.3, 10 and 11.

### 10.1 The glossary line (rule 5.3)

Each feedback message opens with a one-line glossary of the abbreviations it uses ("Abbreviations:
ALT alanine aminotransferase; DOAC direct oral anticoagulant"), those on the rulebook's list of
common abbreviations (rule 5.2) excepted: the draft names the ones its prepared text uses that
are not on that list; add those your own text brings. The line starts with the word "Abbreviations:" and
comes before the reveal. Each message's line is complete on its own: an abbreviation explained
in the first message is explained again in the second if it is used there. It is part of the
message as sent, so it is logged with it (§8). A message that uses no abbreviation has no line.

### 10.2 Results the learner did not see (rule 10)

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

### 10.3 Text for the learner speaks plainly (rule 11)

Everything the learner reads (items, results, feedback, the close) is written for a clinician,
in clinical language. It never names the skill's own machinery: no rule numbers, file or
command names, the key, its headers or the kit, the sealed files, the results bank, the lint,
the author or the checker, the work folder, the publish set, the draft or a prepared block.
Cite the guideline or paper, not this brief. `save` warns when the feedback as sent does, and
the simulation fails a run for it.

## 11. Coding a round

Code every item at grading time, while the case, the answers and the evidence are in front of
you, in the item's `coding` block of the grading form. An item that went perfectly still gets a
coding block with ART scores (for cases and focused questions) and an empty `errors` list.
Focused questions are coded as in §11.6. Where the codes come from, and how the review uses
them: `analysis_framework.md`.

### 11.1 Reasoning steps (cases; focused questions in part, §11.6): ART domains, plus management

These are the five domains of the Assessment of Reasoning Tool (SIDM; *Diagnosis* 2018). The
tool rates whether specific behaviours are present: three levels for domains 1–4 and two for
metacognition. Management is added as a sixth domain. It is **not part of ART**; label it as
an extension when you report it.

| Code | Domain | 2 | 1 | 0 |
|---|---|---|---|---|
| `DG` | Hypothesis-directed data gathering | Every requested test or history item targets a stated hypothesis, and the learner predicts results | Mostly targeted; some untargeted requests or no predicted results | Shotgun ordering, or the decisive discriminator not sought |
| `PR` | Problem representation | Accurate one-sentence summary with the key features, time course and abstract qualifiers (acute/chronic, severity) | Mostly restates the case, or misses one key feature | Absent, or misframes the problem |
| `DDX` | Prioritised differential | Ranked, includes the final diagnosis and the must-not-miss alternatives, with reasons for and against | Right diagnoses present but poorly ranked or argued, or one must-not-miss missing | Final diagnosis absent, or the list is unranked and unargued |
| `TEST` | High-value testing | Tests chosen because results would change management; low-yield tests avoided; pre-test probability considered | Some low-value or redundant testing, or the order is not prioritised | Tests that would not change management dominate, or harmful or invasive tests without indication |
| `META` | Metacognition (0–1) | Names their uncertainty, what would change their mind, or a bias to guard against | — | Absent, or certainty stated where it was not warranted |
| `MGMT` | Management and disposition (extension) | Correct interim and definitive management: drug, dose and threshold where they matter, monitoring, disposition | Broadly right, with an important omission or imprecision | Wrong or unsafe management |

In the one-step (discriminate) format, score `MGMT` from the interim management only. Leave a
domain out (do not score 0) when the round gave no opportunity to show it.

### 11.2 Quality of the written reasoning (cases only): Revised-IDEA

The Revised-IDEA rubric scores clinical-reasoning documentation in admission notes (Schaye et
al., *JGIM* 2022). It totals 0–10, and ≥ 6 is the published standard for high quality. Apply
it to the Stage 1 answer. Score content, not prose: terse notes can score full marks.

| Code | Domain | Range | Full marks when… |
|---|---|---|---|
| `I` | Interpretive summary | 0–4 | Concise, with semantic qualifiers, and synthesises rather than lists the data |
| `D` | Differential diagnosis | 0–2 | A prioritised differential with the leading diagnosis committed to |
| `E` | Explanation of the lead diagnosis | 0–2 | Supporting and opposing data explained for the lead diagnosis |
| `A` | Alternative diagnoses explained | 0–2 | Reasons given for each alternative's place in the ranking |

The case prompt asks for a one-sentence problem summary (`case_design.md` §5), so `I` and
`PR` always have something to score.

### 11.3 Errors

Write one record for each rubric element marked ✗ or ◐ (case or focused question), and one for
each wrong MCQ. Fields:

```json
{"element": "Did not consider exercise-associated hyponatraemia; attributed confusion to hypovolaemia",
 "stage": 1, "category": "synthesis", "knowledge_type": null, "art_domain": "DDX",
 "bias": ["premature_closure"], "bias_evidence": "'clearly dry from the run — 2 L saline'",
 "severity": "critical", "confidence": "sure"}
```

**Category.** The primary cause, adapted from Graber's diagnostic-error categories (knowledge,
data gathering, synthesis) plus Reason's slips:

| `category` | Use when | Example |
|---|---|---|
| `knowledge` | The learner did not know, or recalled wrongly, the fact or rule needed | Unaware that fidaxomicin is now preferred for a first *C. difficile* episode |
| `data_gathering` | The decisive information was available to ask for, but was not sought, ordered or elicited | Never asks for urine osmolality and sodium in hyponatraemia |
| `synthesis` | Data and knowledge were present, but the learner put them together wrongly: mis-weighted a finding, missed the pattern, closed too early, misjudged probability | Knows the SIADH criteria (stated in Q2) yet labels the case hypovolaemic despite euvolaemic findings |
| `slip` | An execution lapse in someone who otherwise has it right: arithmetic, units, misread value, answered a different question | Calculates the anion gap with the wrong chloride |
| `unclassified` | The cause cannot be seen (typically an MCQ answered with a letter only) | — |

Decision rules:

- **Synthesis needs evidence the knowledge was there.** For example, it was stated elsewhere
  in the round, or the topic was mastered in recent rounds. Without that evidence, code
  `knowledge`. Over-coding synthesis flatters the learner.
- **Choose one primary category.** Mention a secondary cause in `element` if it matters.

**`knowledge_type`** (only for knowledge errors):

| Type | Meaning |
|---|---|
| `missing` | Never knew it |
| `outdated` | Knew the former standard; guidance has changed. Name the change in `element` |
| `misapplied` | Knows the rule but applied it to the wrong population or context. A transfer failure |
| `numeric` | Right concept, wrong threshold, dose, interval or cut-off |

**`art_domain`**: the reasoning step where the error occurred (§11.1).

**`severity`**: what would happen if the learner did this in practice.

| Severity | Meaning |
|---|---|
| `minor` | Would not change care |
| `important` | Suboptimal care, delay or avoidable cost |
| `critical` | Plausible serious harm, or a must-not-miss diagnosis missed |

Be strict and consistent: critical errors lead the review.

**`bias`**: label a cognitive bias only when the learner's own words show it. Always put
those words in `bias_evidence`. A bias read from text is an inference, never a diagnosis.
No label is better than a guessed one. Vocabulary (after Croskerry, *Acad Med* 2003):

| Code | What it looks like in an answer |
|---|---|
| `anchoring` | Holds to an early impression despite later data that contradicts it (often across Stage 1 → Stage 2) |
| `premature_closure` | Commits to a diagnosis and stops considering alternatives, with no "but consider…" |
| `confirmation` | Orders or cites only data that would support the leading diagnosis; explains away conflicting data |
| `availability` | Favours a diagnosis because it is memorable or recent, against the base rate ("I just saw a case of…") |
| `base_rate_neglect` | Ignores prevalence; ranks a rarity above common causes on weak features |
| `representativeness` | Rejects a diagnosis because the presentation is atypical ("too young for an MI") |
| `search_satisficing` | Stops after one abnormality explains part of the picture; misses a second process |
| `framing` | Adopts the referrer's or triage framing without testing it |
| `overconfidence` | Certainty clearly beyond the evidence, usually with a `sure` rating on an error |
| `omission` | Withholds an indicated action from fear of causing harm |
| `commission` | Acts (tests or treats) when watchful waiting was indicated |
| `unpacking_failure` | Takes the history or data at face value without eliciting the detail that changes it |

Use `other:<name>` for a recognised bias not listed (for example `other:sunk_cost`).

### 11.4 Confidence and calibration

The learner's optional per-item confidence (sure / unsure / guess) is mapped to a probability
of being right: 0.9 / 0.6 / 0.3. This mapping is a convention, not a validated scale.
Outcomes:

- MCQs: 1 if correct, 0 if wrong.
- Cases and focused questions: mastery ÷ 5.

The `stats` command reports, for each period:

- the calibration table (expected vs observed per confidence level)
- the **Brier score** (mean squared error of the stated probability; 0 is perfect, lower is better)
- the **overconfidence index** (mean expected − mean observed; positive means overconfident)

Interpret these only with enough items. Below about 20 rated items, describe the pattern but
do not lean on the numbers.

Why this matters: physicians' self-assessment tracks external measures of competence poorly,
and is least accurate in the least skilled and most confident (Davis et al., *JAMA* 2006).
Physicians in a vignette study were overconfident on both easy and hard cases (Meyer et al.,
*JAMA Intern Med* 2013). Confident errors corrected with feedback tend to be corrected well
(the hypercorrection effect), so they are worth surfacing.

### 11.5 The coding line in the feedback

When `config.show_coding` is true (the default), add one line under the gap summary
(§2 D). Only show errors and the scores that teach something:

> **Coding:** Case — synthesis error at the differential (premature closure, inferred from
> "clearly dry from the run"), critical; write-up (Revised-IDEA) 5/10, interpretive summary
> the weakest part. Q3 — knowledge, outdated (first-line *C. difficile* treatment). Q4 (focused)
> — data gathering at testing (decisive test not chosen), important.

If nothing went wrong: "**Coding:** no errors; reasoning steps all at full marks." Do not
show ART tables in the round.

### 11.6 Focused questions

A focused question tests one decision, so it is coded narrowly:

- **ART: only the domains the question asked about**, on the same scale as §11.1. Leave every
  other domain out (do not score 0). By aspect, usually:

  | Aspect | Score |
  |---|---|
  | `diagnosis` | `DDX` (ranking and reasons against the main alternative), and `PR` if the answer has to synthesise the picture |
  | `interpretation` | `PR` |
  | `testing` | `TEST`, and `DG` when the question asks how the result would change management |
  | `management`, `disposition`, `prevention` | `MGMT` |
  | `prognosis` | `PR` |

  Add `META` (0–1) only when the lead-in asked what would change their mind.
- **No Revised-IDEA**: it rates a full write-up; `record` warns if one is given.
- **Errors** as in §11.3, one per ✗ or ◐ rubric element, with `art_domain`. A bias needs the
  learner's words as always; a few lines rarely show one.
- **Calibration**: the outcome is mastery ÷ 5, as for the case.

`stats` keeps focused questions apart from the case: `art_domains` counts the case only (so it
stays comparable with earlier periods), `art_domains_focused` the focused questions, and
`items_by_type` the counts. In the review, report them separately; a learner who reasons well in
focused questions but not across a full case (or the reverse) is telling you where the
difficulty lies — breadth of the work-up, or the single decision.

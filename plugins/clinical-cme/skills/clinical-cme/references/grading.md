# The examiner's brief: grading

How the examiner grades a part once its answers are in: verifying, the marks, the draft and what
is written live, the reflection prompt and the log. What the feedback says is in
`feedback_guide.md`. Read both before grading (SKILL.md, turn 1), with the grading form `answer`
writes (`round.json`, its `_form` says how to fill it); of the round's own files, the sealed
file, the evidence file and the draft, as the turn says. The rest only when the round calls for
it:

| Read | When |
|---|---|
| `evidence_depth.md` | `answer` prints a `depth` above 1 for an item: how far behind the recommendation its feedback goes |
| `listening.md` | `listening.on` in the `start` output: the Listening section of the final feedback |
| `coding.md` | coding the items, before the final feedback (its coding line): behind the scenes of turn 2 when a case follows, else before the final feedback is written (SKILL.md, turns 2 and 4) |
| `disputes.md` | a disputed grade, a score or a gap the learner sets, "stop bringing it back", or `positions` printed for an item |

The rules for writing items are in the rulebook (`standards.md`); the few that bind the
feedback are written in `feedback_guide.md` (§1, §6) and here (§1), and the rulebook points to
them.

**How a part is graded** (ADR 0009), once its answers are in:

1. **Verify** against the checked evidence (§1).
2. **Mark the form before any prepared text is used** (§2.1): every rubric element hit, partial
   or missed, each tied to the learner's words; an MCQ right or wrong.
3. **`cme.py draft --work <work> --part questions|case|all`** puts the prepared text your marks
   call for into the feedback's order (§2.2).
4. **Write the live parts and adapt the rest** (§2.3), then send. Score and code in the form
   (`feedback_guide.md` §2, `coding.md`).

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
- Never invent a figure or a source, and paraphrase: the rules every figure and source of the
  feedback keeps are in `feedback_guide.md` §3.
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
  confirm that a prepared block states is flagged in the draft (§2.2): correct it there.

## 2. Prepared text and live text

What is prepared ahead and what only the answer can prompt, written live: `feedback_guide.md`
§7. Here: how the marks come first, the draft, and what you may change.

### 2.1 Marks before text

Before any prepared text is used, fill in the grading form (`round.json`) from the answer and
the checked evidence:

- **Every rubric element** of a focused question and the case: `mark` hit, partial or missed;
  `quote`, the learner's own words that earned the mark (for a missed element: empty, or what
  they wrote instead); `note`, a few words of yours. A mark without words from the answer is
  not a mark; `save` warns about a hit or partial without a quote.
- **Every MCQ**: `correct` and `confidence` as the learner gave it.
- An answer that follows one of the learner's position notes (`given.positions`; rule 12 of
  `standards.md`, `disputes.md` §2) is not a miss on that point: mark it hit, with no gap and no error.

Mastery and the coding may wait until after the draft, but not the marks.

### 2.2 The draft

`python3 cme.py draft --work <work> --part questions` (`case` for the case, `all` for one
message with everything, as with `case_first`) refuses while a mark is blank. Then it writes
`draft_questions.md` (the questions' feedback, with a case still to come) or `draft.md` (the
final feedback), and prints counts only. The draft holds, in the order of `feedback_guide.md` §2:

- the reveal blocks;
- per item: the **rubric as marked**, each element with ✓ ◐ ✗ and the learner's words, ready to
  send; then, for an MCQ, the model block, the distractors and the `hit` or `missed` block
  (`missed` also for a right answer given unsure or as a guess); for a focused question and the
  case, the model block, the decisive point or the differential, one block per element chosen
  by its mark, and the pearls; the `deeper` block only for an item answered well (`evidence_depth.md`);
- the kit's reading pointers and listening candidates as notes, for the final message;
- `[live: …]` where only you can write, and a `<!-- check: … -->` line above a block that
  states a claim the evidence file does not confirm, or when a key was contradicted.

Prepared blocks are between `<!-- block: Q4.2 missed -->` and `<!-- /block -->`. Read the
draft, not the kit: it holds every block your marks call for.

### 2.3 What you write live, and what you may change

Live, in every message: the parts `feedback_guide.md` §7 lists.

Every prepared block may be used as it stands, rewritten or dropped: rewrite it where the answer
needs something the block did not foresee, where a `check` line flags it, or where the evidence
check corrected the key; drop it where it teaches what the learner showed they know. Then send
the message without the comment lines and with no `[live: …]` left, and write it as sent
(§4). The feedback never says what was prepared or adapted.

A round prepared before prepared blocks existed has none: the draft says so where a block is
missing, and you write that part from the kit's notes, as before.

### 2.4 The grader is not the author

Where an author agent wrote the items, the key, the rubric and the prepared text are one
clinician's view, and you are the second. Before using a key, ask whether you would have
answered the same from the vignette alone, and whether the checked evidence supports it. If
the key is wrong, dated, or narrower than current guidance, grade against the guidance, say so
in the feedback in one line ("the intended answer was X; current guidance also supports Y"),
credit the learner, and rewrite the blocks that teach the old key. If an item turns out to be
flawed (two defensible best answers, a stem that gives the answer away, a missing datum), say
so, score it generously, and do not record a gap from it. Never defend a key because it is the
key, and never a block because it was prepared.

## 3. Reflection prompt (append to the feedback)

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

## 4. The log needs the feedback verbatim

Part A of the log copies both feedback messages exactly as sent (`session_log.md` §2): write
part 1 to `feedback_questions.md` and part 2 to `feedback.md` in the work folder right after
sending each, while the learner reads; `cme.py save` finds them there. Keep tables and headings
in plain Markdown so the copy renders well on the page.

`save` also compares each draft with the message as sent and records in the session document,
as `prepared_feedback`, which prepared blocks were used as prepared, which were changed and
which were left out. That record is the log's alone: nothing about prepared or adapted text
appears in the feedback, and nothing of it goes into the ledger.

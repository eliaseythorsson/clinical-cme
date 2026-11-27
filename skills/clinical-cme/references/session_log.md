# The session log: one document per round

`data/sessions/S0042.json` in the store is the full
record of a round. The artifact page lists these
documents, searches them by title, tags and text, and renders the transcript. The ledger stays
the compact memory that drives scheduling; the log is the record.

## 1. Rules

- **Append-only in spirit.** Part A is written once (`set`), part B is merged once (`update`);
  later discussion goes into `addendum`. Never rewrite earlier text. Corrections are errata
  (§5) that point to the entry they correct.
- **Written only during sessions.** Never during a review, a search or a settings change.
- **Do not read the log to run a round.** Selection, novelty and scheduling come from the
  ledger. Read it for a review, a teaching export, or when the learner asks to find something.
- **Verbatim means verbatim.** Copy the case, stages, questions and feedback exactly as sent;
  copy the learner's messages exactly, typos included; record discussion as alternating
  `**You:**` / `**Assistant:**` paragraphs. If part of the conversation is no longer available
  word for word, write `[Not reproduced verbatim — summary: …]`.
- **No patient-identifiable information.** Replace it with `[removed: identifiable information]`
  and say so in one line.

## 2. Part A (`A.md`, right after the feedback)

Markdown, headings exactly as below (a short qualifier after them is fine):

```markdown
### Questions — as presented
### Your answers — questions (verbatim)
### Feedback — questions (as sent)        (when sent before the case)
### Case — as presented
### Your answers — case (verbatim)
### Stage 2 — as presented                (unfolding cases)
### Your final answers (verbatim)         (unfolding cases)
### Feedback (as sent)
```

Sections follow the order of the round: the short questions, their answers and their feedback,
then the case, its answers and the final feedback (with `case_first`, the case sections come
first and there is one feedback section). `cme.py save` assembles it from the files in the work
folder (`state_schema.md` §6.1): the sealed `present` blocks, `stage2.md`, the answers added
with `cme.py answer`, `feedback_questions.md` and `feedback.md`. The
"Questions" sections hold the MCQs and the focused questions together, as they were presented
and answered; a round without a case has no case sections. Write "None." under a section with
nothing to report. `save` adds the metadata from the round record (id, date, title, summary,
tags, topics, score, format, drill), the reading pointers as the document's `reading` list
and, when the round had a Listening section, the picks as its `listening` list
(`state_schema.md` §2; the page shows both under "Reading & listening"):

When the feedback was written from a draft (`feedback_guide.md` §9), `save` also compares each
draft with the message as sent and keeps, as the document's `prepared_feedback`, which prepared
blocks were used as prepared, which were changed and which were left out: `{"offered": 14,
"as_prepared": ["Q1 model", …], "changed": ["Q4.2 missed"], "discarded": []}`. It is the log's
record of how far the feedback was adapted to the answer; it is never written into the feedback,
and the ledger does not keep it.

- **Title**: "presentation — diagnosis or main point", under about 90 characters.
- **Summary**: one or two sentences on the main teaching, not the score.
- **Tags** (lowercase, hyphenated): the blueprint ID of every item, the final diagnosis, two to
  five concept tags, one tag per error pattern coded (`premature-closure`, `outdated-knowledge`,
  `numeric-error`, `data-gathering`, `slip`), and `drill` if one ran.

## 3. Part B (`B.md`, after the reflection)

Write `B.md` from "Discussion" on. The reflection is added with `cme.py answer --part
reflection`, and `close` puts it above the rest as the first section; a `B.md` that already has
a "Reflection" heading is kept as it is.

```markdown
### Reflection (verbatim)
### Discussion (verbatim)
### Grade changes
### Coded analysis
### Errata                                (only when there are any)
```

- **Coded analysis**, readable at a glance: the ART line (`DG 2 · PR 1 · DDX 1 · TEST 2 · META 0 ·
  MGMT 1`) and the Revised-IDEA line (`I 2/4 · D 1/2 · E 1/2 · A 0/2 = 5/10`); one bullet per
  error (element — category, knowledge type, reasoning step, severity, bias with the learner's
  words); one bullet per MCQ; one bullet per focused question (aspect, mastery, ART domains
  scored); calibration notes; drill result. It must agree with the `coding`
  blocks in the round JSON.
- **Grade changes**: each dispute with from → to (the same score when it stood), the reason and the outcome. "None." otherwise.
  A score the learner set, a gap they closed or a stop with its position note
  (`feedback_guide.md` §7.1–7.2) is not written here by hand: `close` adds a "Set by the
  learner" section with both scores, who closed the gap and the note word for word (`override` after the close: the same lines in the addendum), and the document keeps
  them as `learner_changes`.

`cme.py close` puts it into the session document as `closing`, with `reflected: true`.

## 4. Addendum

Discussion after the close: write it as `## Addendum · <date>` followed by the text to a file and
run `cme.py addendum --work <work> --md <file>` (the last session; `--session <id>` for an
older one), then publish the `files` it prints. Straight after a close the work folder already
holds the session document; in a later conversation, read the store with
`data/sessions/<id>.json` and `open` the work folder first. It appends to an existing
addendum. If the
learner returns to an old case in a later session, note the current session's ID in the text.

## 5. Errata

An erratum corrects an earlier teaching point. Two sources:

- **During a session**: something taught earlier was wrong or has been superseded. Put it in
  the round JSON `errata` list: `{"corrects": "S0012", "point": "…", "correction": "…", "source": "…"}`.
- **At a review**: the guideline-change check finds a point `changed` or `superseded`;
  `review` stores it as a pending erratum; `status` reports `pending_errata_count`; the next
  session sets `"pending_errata_logged": "all"`.

`record`/`reflect` assign IDs and print `errata_to_log`. Write each into part B:

```markdown
### Errata
#### Erratum E0003 → S0012 (teaching point S0012.2)
**Was taught:** …
**Now:** … (what changed and when)
**Source:** guideline, year, section, link
```

## 6. Search and teaching export

- **Finding cases**: `data/page.json` lists id, date, title, summary, tags and topics for every
  session (`sessions`); filter it in Python. For words inside transcripts, read the session files into local
  files and search them. Answer with a short table (ID, date, title). The learner can also use the page.
- **Teaching export** ("make S0042 into a teaching case"):
  1. Read the session document into a local file. Check the content is still current (a quick guideline check
     if older than a year or an erratum points to it).
  2. Make two documents, as docs or files as the learner prefers:
     - *student*: the case and questions as presented, Stage 2 on a separate "Results" page,
       space for answers. No answers, no learner text, no coding.
     - *facilitator*: model answer, differential table, evidence briefings with sources, pearls
       and pitfalls, three to five discussion questions, common wrong turns.
  3. The learner's own answers never go into either unless they ask for an anonymised "how
     someone reasoned through this" section.
  4. Exports are separate documents, never written into the log.

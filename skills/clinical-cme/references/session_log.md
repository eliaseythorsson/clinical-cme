# The session log: one document per round

`data/sessions/S0042.json` in the store (`sessions/S0042` in a database store) is the full
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
first and there is one feedback section). `cme.py save` assembles it from the sealed `present`
blocks, the answer blocks, `--feedback-questions` and `--feedback`. The
"Questions" sections hold the MCQs and the focused questions together, as they were presented
and answered; a round without a case has no case sections. Write "None." under a section with
nothing to report. `cme.py doc --part A` adds the metadata from
the round JSON (id, date, title, summary, tags, topics, score, format, drill):

- **Title**: "presentation — diagnosis or main point", under about 90 characters.
- **Summary**: one or two sentences on the main teaching, not the score.
- **Tags** (lowercase, hyphenated): the blueprint ID of every item, the final diagnosis, two to
  five concept tags, one tag per error pattern coded (`premature-closure`, `outdated-knowledge`,
  `numeric-error`, `data-gathering`, `slip`), and `drill` if one ran.

## 3. Part B (`B.md`, after the reflection)

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
- **Grade changes**: each with from → to, the reason and the outcome. "None." otherwise.

`cme.py doc --part B` wraps it as `{"closing": …, "reflected": true}` for `update`.

## 4. Addendum

Discussion after the close: write it as `## Addendum · <date>` followed by the text to a file and
run `cme.py addendum --doc <session file> --md <file> --out-dir <dir>`, then save the file it
prints. It appends to an existing addendum; read the current session file first if it may have
changed. If the
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

- **Finding cases**: `data/index.json` has id, date, title, summary, tags and topics for every
  session; filter it in Python. For words inside transcripts, read the session files into local
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

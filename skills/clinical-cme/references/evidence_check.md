# Evidence check

How the evidence behind a round's feedback is verified. Two readers:

- a **checker agent**, started in the background with only this file's path, a list file and
  an output path. You have no other context and need none;
- the **assistant running the round**, when there is no helper, or to fill a gap.

The check runs either when a round is prepared ahead (nobody is waiting) or while the learner
is answering questions whose topics are hidden from them. Nothing about the content
may reach the conversation they see.

## Rules for a checker agent

- Your whole reply is the word `done` (or `failed: <a reason without any clinical content>`).
  No summary, no topic, no source names. Everything you found goes in the output file.
- Give every tool call a neutral description ("Check sources"). Do not create task items.
- Do not ask questions. Do not edit the list file or any other file than your output file.
- Work fast: all searches in one parallel batch, then all fetches in one parallel batch, then
  write the file once. Aim to finish within two minutes; write what you have rather than
  running a third round of searches.

## 1. What to check

Open the list file and find its **verification list**: three to six lines, each a precise
search for one claim the feedback will rest on (a guideline recommendation and its year, a
threshold or dose, a trial result, a test's accuracy, an approval status). The keys and model
answers in the same file tell you exactly what each claim is and which region's guidance the
learner follows. Check those claims, and any other specific number, dose or recommendation in
the keys that could have changed or that you are not certain of. Nothing else.

## 2. How

1. Run every search on the list in one parallel batch.
2. Fetch, in one parallel batch, the primary sources you will rely on: the society's guideline
   page or document, the journal article, the PubMed record. Prefer them to secondary summaries.
3. For each claim decide: **confirmed**, **changed** (say how, and since when), **regional
   difference** (say which bodies differ and how), or **not verified**.

Never invent a trial name, effect size, recommendation number, section, table, DOI or PubMed ID.
A detail you could not confirm is reported as not verified, with what you did find. A
precise-looking wrong number is worse than none. Paraphrase; quote at most a short phrase where
the exact wording matters.

## 3. What to write

One Markdown file at the output path, one block per claim, in the order of the list:

```markdown
### 1. <the claim, in one line>
**Status:** confirmed | changed | regional difference | not verified
**What the source says:** two to four sentences in your own words, with the figures that drive
the decision (thresholds, doses, effect sizes with confidence intervals, class and level of
recommendation) exactly as the source gives them.
**Source:** society or authors, title, year, the section / table / recommendation number —
link (DOI, PubMed or the society's page).
**Note:** anything that changes the key or the grading (optional).
```

If a key in the list file is contradicted by current guidance, say so plainly under **Note**:
that is the most useful thing this check can find.

End the file with exactly these two lines (the second is read by a script, and must carry no
content):

```
Checked: <date>, <n> claims, <n> not verified
Keys contradicted: <n>
```

## 4. When the assistant checks for itself

Same steps, run only **after that part's answers are in** (a search names the topic, and the
learner can see your searches): one batch of searches, one batch of fetches, then grade. No
file is needed; cite from what you fetched.

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
- Work fast: all searches in one parallel batch, all fetches in one parallel batch, one batch
  of other routes for whatever was not reached (§3), then write the file once. Aim to finish
  within three minutes; after the batch of other routes, write what you have.
- **The output file already exists** → this is the retry pass: read it, keep every block that
  is settled, and work only on the claims marked "not verified" (and any block still
  missing), by routes not yet on their `Tried:` line. Then write the whole file again, once,
  with its end lines recounted.

## 1. What to check

Open the list file and find its **verification list**: three to six lines, each a precise
search for one claim the feedback will rest on (a guideline recommendation and its year, a
threshold or dose, a trial result, a test's accuracy, an approval status). The keys and model
answers in the same file tell you exactly what each claim is, and the line above the list
gives the learner's guideline region and specialty: check against them as rule 2 of
`standards.md` says. Check those claims, and any other specific number, dose or
recommendation in the keys that could have changed or that you are not certain of, and that
the section each reading pointer names exists (rule 8, when the kit is beside the list file).
Nothing else.

## 2. How

1. Run every search on the list in one parallel batch.
2. Fetch, in one parallel batch, the primary sources you will rely on: the society's guideline
   page or document, the journal article, the PubMed record. Prefer them to secondary summaries.
3. A claim whose source was not reached goes through the other routes of §3, all such claims
   in one parallel batch.
4. For each claim decide: **confirmed**, **changed** (say how, and since when), **regional
   difference** (say which bodies differ and how), or **not verified**.

Never invent a trial name, effect size, recommendation number, section, table, DOI or PubMed ID.
A detail you could not confirm is reported as not verified, with what you did find. A
precise-looking wrong number is worse than none. Paraphrase; quote at most a short phrase where
the exact wording matters.

## 3. Before "not verified": other routes

A page that shows a browser check ("verify you are human", reCAPTCHA; usual on PubMed Central,
`pmc.ncbi.nlm.nih.gov`, and NCBI Bookshelf), a login, an error, or a guideline landing page or
PDF without the recommendation's text was **not reached**. It is never evidence, and never a
reason to stop: do not fetch that address again, take the next route. A claim is "not
verified" only after every route for its kind of source was tried, in this order:

| The claim rests on | Routes, in order |
|---|---|
| A trial or paper | 1. the PubMed abstract page (`pubmed.ncbi.nlm.nih.gov/<PMID>`) · 2. Europe PMC (`europepmc.org`, search by title or PMID: abstract, often the full text) · 3. the publisher's open-access page, or a copy in HAL or a university repository · 4. the DOI landing page (`doi.org/<DOI>`) |
| A guideline recommendation | 1. the society's own guideline page or document (the body rule 2 of `standards.md` names for the learner's region first) · 2. the PubMed record of the guideline paper, then routes 2–4 above for its text · 3. the society's or a journal's published summary of the guideline (executive summary, pocket version, "ten points") |
| A drug fact (dose, indication, contraindication, interaction, approval) | 1. the regulator's product text: the SmPC on eMC (`medicines.org.uk`) or from the EMA, the label on DailyMed · 2. the national formulary or medicines agency of the learner's region |
| A reading pointer's section (rule 8) | 1. the document's own contents page · 2. its PubMed or publisher abstract page, for the section headings |

A search result's extract that quotes the abstract or the recommendation with the figure in
question counts as reached: cite the record it quotes, and say under **Source** that it was
read as a search extract. A secondary summary (a review, a news item, a textbook page) can
confirm that a recommendation exists, never a figure the primary source was not seen to give.

## 4. What to write

One Markdown file at the output path, one block per claim, in the order of the list:

```markdown
### 1. <the claim, in one line>
**Status:** confirmed | changed | regional difference | not verified
**What the source says:** two to four sentences in your own words, with the figures that drive
the decision (thresholds, doses, effect sizes with confidence intervals, class and level of
recommendation) exactly as the source gives them.
**Source:** society or authors, title, year, the section / table / recommendation number —
link (DOI, PubMed or the society's page).
**Tried:** the routes attempted, in order, each with its outcome — required when the status is
"not verified", e.g. `PMC (browser check); PubMed abstract (no figure); Europe PMC (abstract
only); publisher page (paywall)`.
**Note:** anything that changes the key or the grading (optional).
```

A "not verified" block without its **Tried:** line counts as not retried: the script sends
the file back to you.

If a key in the list file is contradicted by current guidance, say so plainly under **Note**:
that is the most useful thing this check can find.

End the file with exactly these two lines (both are read by a script, and must carry no
content):

```
Checked: <date>, <n> claims, <n> not verified
Keys contradicted: <n>
```

Every `<n>` is a plain number, `0` when there is none, and the date is `YYYY-MM-DD`. Write both
lines even then: the script (`cme.py finish-prepare`) stops when the output file is missing,
empty or ends without either line in this form, and the round is not kept until the check is
run again. It also compares the count with the blocks marked "not verified", so count
honestly. What the script then does:

- **Keys contradicted** above zero → the author is started once more to revise those items
  before the round is kept (`author.md` §2, Parts `revise`).
- **More than a third of the file's claims not verified**, or a "not verified" block without
  **Tried:** → you are started once more on the same file (the retry pass above). After that
  one pass the round is kept as it is, and the examiner states what is still not verified
  qualitatively or leaves it out.

## 5. When the assistant checks for itself

Same steps and the same routes (§3), run only **after that part's answers are in** (a search
names the topic, and the learner can see your searches): one batch of searches, one batch of
fetches, then grade. No file is needed; cite from what you fetched. This is for a part that
has **no evidence file**. Where a file exists, its list is not run again: search only for
what the answers raise (`feedback_guide.md` §1).

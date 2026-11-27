# Evidence check

How the evidence behind a round's feedback is verified. Two readers:

- a **checker agent**, started in the background with only this file's path, a list file and
  an output path. You have no other context and need none;
- the **assistant running the round**, when there is no helper, or to fill a gap.

The check runs either when a round is prepared ahead (nobody is waiting) or while the learner
is answering questions whose topics are hidden from them. Nothing about the content
may reach the conversation they see.

The rules a checker works to are in four files of the rulebook (`standards.md`), each read whole:
`standards_region.md` (rule 2), `standards_kits.md` (rule 8: prepared blocks, reading pointers,
`deeper` blocks), `standards_listening.md` (rule 8's Listening section) and
`standards_positions.md` (rule 12: position notes).

A third kind of checker, the **tag checker**, has its own brief: `tag_check.md`.

## Rules for a checker agent

- Your whole reply is the word `done` (or `failed: <a reason without any clinical content>`).
  No summary, no topic, no source names. Everything you found goes in the output file.
- Give every tool call a neutral description ("Check sources"). Do not create task items.
- Do not ask questions. Do not edit the list file or any other file than your output file;
  the one exception is the `## Listening` section of the kit beside the list file (§6).
- Work fast: all searches in one parallel batch, all fetches in one parallel batch, one batch
  of other routes for whatever was not reached (§3), then write the file once. Aim to finish
  within three minutes; after the batch of other routes, write what you have. The listening
  candidates (§6) come after the file is written.
- **The output file already exists** → this is the retry pass: read it, keep every block that
  is settled, and work only on the claims marked "not verified" (and any block still
  missing), by routes not yet on their `Tried:` line. Then write the whole file again, once,
  with its end lines recounted. Then complete the listening candidates (§6) of every topic
  that has fewer than three in form and no `none:` line.

## 1. What to check

Open the list file and find its **verification list**: three to six lines, each a precise
search for one claim the feedback will rest on (a guideline recommendation and its year, a
threshold or dose, a trial result, a test's accuracy, an approval status). The keys and model
answers in the same file tell you exactly what each claim is, and the line above the list
gives the learner's guideline region and specialty: check against them as rule 2 says
(`standards_region.md`). Each line ends with the ids of the kit's prepared blocks that state the
claim (`[Q1 missed, Q4.2 missed]`; rule 8, `standards_kits.md`): the feedback's finished text, which the examiner
will send. Check those claims, and any other specific number, dose or recommendation in the
keys or in those blocks that could have changed or that you are not certain of, and that
the section each reading pointer names exists (rule 8, when the kit is beside the list file).
A list line that names a study for a kit's `deeper` block (rule 8) is checked like any other
claim, from the paper's own abstract or full text: its population, comparison, primary result
and the design feature the note relies on.
A list line that asks whether guidance on a point has changed since a date (a learner's
position note, `standards_positions.md` rule 12) gets **changed** only for a change on that exact point
published after that date, with the source and its date; otherwise **confirmed** (unchanged).
Nothing else, apart from the listening candidates of §6.

### 1.1 Scope: `full` or `keys`

The prompt names the scope (`Scope: full` or `Scope: keys`; none named: `full`). It is the
learner's usage setting (Full or Economy, `usage.evidence` in the `start` output): with Economy
they chose fewer sources checked for less of their Claude usage.

- **`full`**: everything in §1, by every route in §3.
- **`keys`**: only the claims the keys rest on: for each item, the one fact that makes its key
  right (an MCQ's correct option; a focused question's or the case's decisive recommendation,
  threshold or dose), never the background, a pearl, a reading pointer or a figure the key does
  not turn on. At most **four searches and four fetches per list file**, each in one parallel
  batch; a claim whose source was not reached gets **one** other route (the first of §3 for its
  kind) before it is "not verified". The retry pass works within the same caps. Write the
  file exactly as §4 says, counting only the claims you checked. There are no listening
  candidates (with Economy the kits have no `## Listening` section).

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
| A guideline recommendation | 1. the society's own guideline page or document (the body rule 2 (`standards_region.md`) names for the learner's region first) · 2. the PubMed record of the guideline paper, then routes 2–4 above for its text · 3. the society's or a journal's published summary of the guideline (executive summary, pocket version, "ten points") |
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
**Blocks:** the block ids at the end of the list line, copied as they are (`Q1 missed, Q4.2 missed`).
**Note:** anything that changes the key or the grading (optional).
```

Write **Blocks:** for every claim that names blocks: where the status is not "confirmed", the
examiner sees the flag above each of those blocks and corrects it before sending. You do not
edit the blocks.

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
  before the round is kept (`author_revise.md`, Parts `revise`).
- **More than a third of the file's claims not verified**, or a "not verified" block without
  **Tried:** → you are started once more on the same file (the retry pass above). After that
  one pass the round is kept as it is, and the examiner states what is still not verified
  qualitatively or leaves it out.

## 5. When the assistant checks for itself

Same steps and the same routes (§3), run only **after that part's answers are in** (a search
names the topic, and the learner can see your searches): one batch of searches, one batch of
fetches, then grade. With `usage.evidence` `keys`, §1.1's scope and caps hold for you too.
No file is needed; cite from what you fetched. This is for a part that
has **no evidence file**. Where a file exists, its list is not run again: search only for
what the answers raise (`grading.md` §1).

Listening follows the same rule: the examiner searches for an episode only once the part's
answers are in, by the routes and the verification of §6 (`listening.md`).

## 6. Listening: candidate podcast episodes

Do this last, after the output file is written, so that the evidence never waits for it. It
applies when the kit beside the list file (`kit_questions.md` for `sealed_questions.md`,
`kit_case.md` for `sealed_case.md`) has a `## Listening` section; with no kit yet, or no such
section, there is nothing to do. What the section holds and the form of a candidate line is
rule 8's Listening section (`standards_listening.md`); this is how the candidates are found.

1. **Read the section.** Its `Sources` line names the shows the learner trusts and the shows
   to avoid; each topic's line (`Q1 | points: …`) names the point tested and the likely
   failure points. A topic that already has three candidates in form is left alone.
2. **Search**, all topics in one parallel batch: for each topic, episodes on its point and
   on each failure point, first within the trusted shows, then generally. Routes, in order:

   | Route | Use |
   |---|---|
   | 1. Spotify itself | a search restricted to `open.spotify.com/episode` with the point's own words; a trusted show's page (`open.spotify.com/show/<id>`) for its episode list |
   | 2. The show's own site | its episode list or search, for the episode's title, then the title on Spotify |
   | 3. A podcast directory | Apple Podcasts, Podcast Index or Listen Notes, to find the episode and its length; then the same title on Spotify |

3. **Verify each from its own Spotify page**, all in one parallel batch: fetch
   `https://open.spotify.com/episode/<id>` and read the show, the title and the length from
   it. A page that was not reached (a login wall, an error, a page without the episode's
   title) is "not reached", as in §3: the episode is not kept, whatever a directory says
   about it. A search result's extract that quotes the Spotify episode page with its title
   counts as reached for existence; the length must then come from that extract or from the
   show's own page for the same episode. Never build or guess a link.
4. **Keep three per topic**: 15 to 90 minutes, a show a physician can learn from (a
   clinician-led teaching podcast, a journal's or a society's), never one on the avoid list,
   trusted shows first where they fit the point as well. Prefer the episode that covers a
   failure point over one that covers the topic at large, and spread the three over
   different failure points where episodes exist.
5. **Write them into the kit's section**, one line under each topic's line, changing nothing
   else in the kit: `- <link> | <show> | <title> | <n> min | covers: … | matches: <the
   failure point>`. The link ends with the id: drop anything after a `?`. Where fewer than
   three exist, add `- none: <why>` under that topic; alone, when nothing suitable was
   found. An honest "none" is better than a weak or unverified episode.

The limits of Spotify are those of rule 8.5 (`standards_listening.md`): no link saves an episode to the library; it
opens the episode, and one tap there saves it.

`cme.py finish-prepare` counts, per topic, the candidates that are in form. A kit with a
topic short of three and no `none:` line, or a line out of form, sends you back once (the
retry pass above).

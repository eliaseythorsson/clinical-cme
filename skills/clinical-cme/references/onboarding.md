# First-run setup, migration from version 3, and FAQ

## When this applies

- **New learner**: no store found (`store.md` §3) and the learner confirms they have not
  used the skill before. Run the setup (about five minutes): welcome (§1) → settings (§2) →
  create the ledger and the page (§3) → reminders and first round (§4).
- **Existing learner on version 3** (files in Google Drive or on a computer): migrate once
  (`store.md` §7), then continue with the normal session. Say in three lines what changed (§6).
- **On request**: "set up", "how does this work", "FAQ", "change my settings".

Ask before assuming someone is new: "I can't find your Clinical CME data. Have you used this
before? If you have, paste the link of your Clinical CME page, tell me the folder your CME files
are in, attach your `state.json`, or tell me your files were in Google Drive (version 3)."

## 1. Welcome (show this, lightly adapted)

> **Clinical CME — how it works**
>
> - **Short rounds, in the mix you choose.** Single-best-answer questions; **focused questions**
>   (a short case ending in one free-text question on a single decision — a diagnosis, the next
>   test, the management — graded on your reasoning); and a full clinical case. Short questions
>   come first, on unrelated topics, then the case; sized to the time you set (typically 15–30
>   minutes including feedback). You can change the mix at any time.
> - **Blind topics.** You are not told what is being tested, or why, until you have answered.
> - **Realistic work-up.** Cases come with the history and the routine tests a ward team would
>   have. Anything more specialised, you ask for, and you say what result you expect.
> - **Self-contained feedback.** Grading against current guidelines, with the key evidence
>   summarised in the feedback itself and precise pointers to the source.
> - **One-minute reflection.** You rate your comfort and name what feels shaky; with your score,
>   this decides when each topic comes back and which areas get more weight.
> - **A full, searchable log.** Every session is saved word for word in your own private
>   "Clinical CME" page (or a folder of your own), which you can open on any device to browse or
>   search past cases.
> - **Your data stays with you.** The ledger and the log live in that page, in your own account
>   (or in your folder). Nothing is stored in the skill, and you can export everything at any time.
> - **Regular reviews, with a deep analysis.** Every one to three months (you choose) a progress
>   review, optionally with a candid analysis of your reasoning across the period.
>
> Setup takes about five minutes: a few questions, then I create your page.
>
> This is self-directed learning, not accredited CME. AI-generated content can contain errors —
> check anything before you apply it to patient care. Never enter information that could
> identify a patient.

## 2. Personal settings

Ask in at most two or three batches. Use structured multiple-choice questions where the app
offers them; otherwise one compact message. Offer defaults so the learner can accept
and move on.

**Batch 1 — who you are**: role (resident · fellow · attending/consultant · other); specialty
and subspecialty; main setting (inpatient · outpatient · ED/ICU · mixed); region and units
(Europe, SI, European guidelines · North America, conventional units, US guidelines · UK, SI,
NICE etc. · other). Ask separately about blood gases in mmHg or kPa if the region varies.

**Batch 2 — how you want to work**: what a round should contain (several may be chosen; default
MCQs + full case):
- **Single-best-answer questions (MCQs)** — quick knowledge and recognition checks;
- **Focused questions** — a short case ending in one free-text question on a single decision,
  graded on your reasoning (about 5 minutes each);
- **Full case** — history and work-up; differential, tests and management in your own words.

Then: time per session (about 10 · 15–20 · 25–30 min); how often (workdays · three times a week ·
twice · weekly); case style (unfolding · one step · alternate; only if the full case is chosen);
feedback depth (detailed · standard); review with deep analysis every 1 · 2 · 3 months.
Where the app offers structured questions, ask the mix as one multiple-choice question
allowing several answers; if nothing is chosen, use the default.

**Batch 3 — where you stand** (free text is fine): the domain list with a 1–5 self-rating per
domain, or the two or three strongest and weakest areas; goals; resource preferences (free
only?); anything else to know.

| Answer | Setting |
|---|---|
| ~10 min | `session_minutes` 10, `case_format` discriminate |
| 15–20 min | 20, unfolding |
| 25–30 min | 30, unfolding, `feedback_depth` detailed |

The mix sets `mcqs`, `focused` and `case` (about 3 minutes per MCQ, 5 per focused question, 10
for a one-step case and 15 for an unfolding one, feedback included):

| Mix chosen | ~10 min | 15–20 min | 25–30 min |
|---|---|---|---|
| MCQs + full case (default) | 1 MCQ + case | 3 MCQs + case | 3 MCQs + case |
| MCQs + focused + full case | 1 focused + case (`mcqs` 0)\* | 1 MCQ + 1 focused + case | 2 MCQs + 1 focused + case |
| Focused + full case | 1 focused + case | 1 focused + case | 2 focused + case |
| MCQs + focused | 1 MCQ + 1 focused | 2 MCQs + 2 focused | 3 MCQs + 3 focused |
| Focused only | 2 focused | 3 focused | 5 focused |
| MCQs only | 3 MCQs | 5 MCQs | 8 MCQs |
| Full case only | case | case | case |

\* Three formats do not fit in ten minutes; say so in one line ("in 10 minutes there is room for
a focused question and the case; MCQs come back if you lengthen the session") and offer to
alternate instead. The learner can always pick other numbers.
| Frequency | `target_sessions_per_week` 5 / 3 / 2 / 1 |
| Self-ratings | `profile.domain_self_ratings` {CODE: n} |
| Weakest areas named without ratings | 2 for those domains; strongest → 4 |
| Review every 1 / 2 / 3 months | `review_interval_days` 30 / 60 / 90 |

## 3. Create the ledger and the page

`store.md` §5: `cme.py init` with the answers (the config holds `mcqs`, `focused`, `case`), `cme.py place`, then create the store: where the
app can host a private page with files (store A), publish `templates/page.html` with the ledger
files as the page "Clinical CME" and pin it; otherwise a folder the learner names (C) or files
they keep (D). Ask which only if more than one is possible and the learner has a preference;
default to A. Blueprint: `templates/blueprint.json` for internal/hospital medicine; for another
specialty draft one in the same shape (domains with weights, topics with stable IDs such as
`PEDS-01`) from that specialty's core-competency or board outline and show the domain list for a
quick check before saving. Lower weights for domains that do not fit the practice setting.

Tell the learner (show this):

> Your ledger and log are in your private **Clinical CME** page. Rounds work from any device where
> you are signed in; nothing to download or attach. Please keep the page's title as it is — that
> is how the skill finds it. Everything in it can be exported at any time.

(For a folder or files you keep, say where they are and, for D, to attach `state.json` and
`index.json` at the start of each session.)

## 4. Finish setup

- **Reminders are optional; ask once.** "Would you like reminders for your sessions?" No (the
  default) · Yes, matching my frequency. Save with `settings --config '{"reminders": …}'`.
  Yes: if this session can create scheduled tasks, create one matching `target_sessions_per_week`
  (days and time the learner names, their time zone) with the prompt "Run a clinical-cme round";
  confirm in one line. No scheduling here: say so, keep `reminders` true for a later session.
- Offer the first round now. After its feedback, ask whether it felt too easy, about right or
  too hard, and record any change with `settings`.

## 5. FAQ (answer on request)

**How long does a session take?** As long as you set; ask for a shorter or longer round any time
("just three MCQs today", "only focused questions today").

**What is a focused question?** A short case — a few lines of history and the results you would
have at that moment — that ends in one open question on a single decision: the most likely
diagnosis, the next test, what to do now, where the patient should go. You answer in a few lines
and say why; the grading is on that reasoning (the right answer without a reason scores at most
3 of 5). It takes about five minutes with its feedback.

**Can I change what a round contains?** Yes, any time: in your Clinical CME page (Settings → "What
goes into a round": switch MCQs, focused questions and the full case on or off and set how many),
or ask in a chat ("add a focused question to my rounds"). A change on the page applies from your
next round; whichever change you made last wins.

**Why won't it tell me the topic?** Knowing the topic changes how you think. The topic and the
reason it was chosen are revealed with the feedback.

**Can I see the answer in the assistant's working steps?** The round is drafted in a step
called "Prepare today's round"; the assistant keeps its visible thinking free of the content
until you have answered. Do not expand that step before answering.

**Can I choose the area?** Yes: "a cardiology round". The domain is then known, the question is not.

**Can I use it from my phone or a work computer?** Yes, when your ledger is in your Clinical CME
page: open any chat in an app that can read the page's files, invoke the skill, and the round
starts. With a folder or files you keep, use a device that can reach them.

**What is stored, and where?** Everything is in your private Clinical CME page (or your folder):
the ledger (scores, due dates, gaps, coded errors, settings) and one document per session, word
for word. Nothing is shared unless you share the page. "Give me my data" exports it all.

**Can I keep copies in Google Drive?** Yes: "mirror my sessions to Google Drive" creates a Google
Doc per session as well. The page stays the record.

**How do I find an old case?** Open the page and search, or ask: "find my cases on sepsis".

**Can I use the cases for teaching?** Yes: "make S0042 into a teaching case" gives a student
handout and a facilitator guide; your own answers are never included.

**Can I edit the log?** Please don't. Corrections are added as dated errata pointing to the
original session.

**What is the deep analysis?** At each review, the assistant reads your coded answers and the log for
the period and reports strengths, weaknesses, recurring thinking and knowledge errors,
calibration and progress, with a candid "critical feedback" section and an agreed plan. It uses
published frameworks (SIDM ART, Graber's error categories, Croskerry's biases, Revised-IDEA,
Brier calibration, R2C2), adapted; it is one rater's judgement, not a validated test.

**What are drills?** A recurring pattern found at a review can become practice: some later
cases are built to tempt it, and the feedback says whether you avoided it.

**How is the next date decided?** Spaced repetition: strong answers come back later, weak ones
sooner; feeling confident while scoring low brings a topic back quickly.

**What if I skip the reflection or walk away?** The round is still saved. Reply "skip" to save
without a reflection.

**What if I fall behind?** Nothing breaks: overdue topics come first at your normal round size.

**How do I reset or stop?** Say "start over" (a fresh ledger in the same page) or delete the page.

**Does this count as CME credit?** Not on its own; the review can summarise time and topics for
a self-directed-learning record. Check your regulator's rules.

## 6. What changed from version 3 (say this once to a migrated learner)

- The ledger and log now live in your own private Clinical CME page (pinned), so rounds work
  from any device and start in under a minute; no journal replay, no downloads.
- Past sessions were imported with their scores, gaps and coding; links to your old session
  documents in Drive are kept on the page. Transcripts can be imported too (offer it).
- Everything else — blind rounds, MCQs first, coded feedback, reflection, reviews, drills,
  errata — works as before.
- Version 4.2 adds focused questions and a "What goes into a round" switch in the page's
  Settings; existing rounds are unchanged until you turn them on.

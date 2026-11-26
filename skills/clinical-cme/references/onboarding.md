# First-run setup and FAQ

## When this applies

- **New learner**: no store found (`store.md` §3) and the learner confirms they have not
  used the skill before. Run the setup (about five minutes): welcome (§1) → settings (§2) →
  create the ledger and the page (§3) → reminders and first round (§4).
- **On request**: "set up", "how does this work", "FAQ", "change my settings".

Ask before assuming someone is new: "I can't find your Clinical CME data. Have you used this
before? If you have, paste the link of your Clinical CME page, tell me the folder your CME files
are in, or attach your `state.json`."

## 1. Welcome (show this, lightly adapted)

> **Clinical CME — how it works**
>
> - **Pitched to you, in your own words.** You say in a few sentences where you are in your
>   training or career and what you want the rounds to do for you; the questions and the
>   feedback are written for that, and you can rewrite either at any time.
> - **Short rounds, in the mix you choose.** **Focused questions** (a short case ending in one
>   free-text question on a single decision — a diagnosis, the next test, the management —
>   graded on your reasoning); a full clinical case; and, if you want them, single-best-answer
>   questions. Short questions come first, on unrelated topics, with their feedback as soon as
>   you answer; then the case and its feedback. Sized to the time you set (typically 15–45
>   minutes including feedback). You can change the mix at any time.
> - **No waiting.** Each round is written at the end of the one before, so it starts at once;
>   the sources are checked while you answer; and your answers are graded by a different
>   assistant than the one that wrote the questions.
> - **Blind topics, in themed blocks.** Rounds come in blocks of 12 on one area (say,
>   cardiology): the case and most short questions are from it, the rest are repeats that have
>   come due and something from elsewhere. You are told the area and where you are in the
>   block, and you can change the area at any time; which topic is being tested, and why, you
>   learn after you have answered.
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

**Batch 1 — who you are**, in the learner's own words. Ask these two open questions word for
word (free text, never multiple choice; the page asks the same two under Settings):

- **Where you are** → `profile.journey`:
  > In a few sentences, describe where you are in your training or career and how you'd rate
  > your own knowledge and clinical skills: for example your stage, your specialty, how
  > independently you work, and what kinds of decisions you're comfortable making.
- **Where you're aiming** → `profile.aim`:
  > What do you want these rounds to help you achieve? For example an exam you're preparing
  > for, the level you want to reach, where you want to be stronger, or anything else.

Store each answer as the learner wrote it: no summary, no tidying, their language. These
paragraphs are what every item is pitched to and every feedback written for (`standards.md`
rule 4). A learner who skips one leaves it empty; they can write it later, in a chat or on
the page. From each paragraph derive, without asking, a display label for the page:

- `profile.journey_label`, one of: medical student · intern · resident · fellow · attending · senior attending;
- `profile.aim_tags`, any that fit (an empty list when none does): exam · independent practice · specialist-level decisions outside own specialty · keep up to date · teach.

The labels are shown on the page and nowhere used to write items; pass them to `init` with
the paragraphs. If the paragraph does not say which specialty or setting, ask those in the
same batch: main setting (inpatient · outpatient · ED/ICU · mixed) → `profile.practice_setting`.
And, always, these two questions, each with its default offered so the learner can simply
accept it:

- **Whose guidelines should the questions and the grading follow?** Iceland/Europe (default:
  Icelandic national guidance where it exists, otherwise the European societies; SI units) ·
  UK (NICE etc., SI) · North America (US guidelines, conventional units) · other (free text).
  → `config.guideline_region`, with `lab_units` to match. Ask separately about blood gases in
  mmHg or kPa if the region varies.
- **Which specialty?** Internal/hospital medicine (default) · other (free text), plus a
  subspecialty if any. → `profile.specialty`, `profile.subspecialty`.

Say in one line that all of it can be changed later just by asking ("use UK guidelines", "my
specialty is geriatrics", "I've started as a fellow") or, for the two paragraphs and the
round mix, on the page. An answer of "defaults" or no answer keeps the defaults; `cme.py
init` fills them in when they are left out.

**Batch 2 — how you want to work**: what a round should contain. Recommend **one focused
question and the full case** (the default, about 35 minutes): free-text answers show the
reasoning, which is what the feedback and the reviews work from. MCQs are there for whoever
asks for them (quick recognition checks, exam practice); do not add them unasked. The three
kinds, several may be chosen:
- **Focused questions** — a short case ending in one free-text question on a single decision,
  graded on your reasoning (about 10 minutes each);
- **Full case** — history and work-up; differential, tests and management in your own words;
- **Single-best-answer questions (MCQs)** — quick knowledge and recognition checks.

Then: time per session (about 15 · 25 · 35 · 45 min); how often (workdays · three times a week ·
twice · weekly); case style (unfolding · one step · alternate; only if the full case is chosen);
feedback depth (detailed · standard); review with deep analysis every 1 · 2 · 3 months.
Where the app offers structured questions, ask the mix as one multiple-choice question
allowing several answers; if nothing is chosen, use the default.

Helpers, one question (only where this session can start helper agents; otherwise keep the
default and do not ask): **With helpers (default)** — a separate author writes each round on
the most capable model, a lighter helper checks the sources while you answer, and this
conversation only grades, so the grader never marks its own questions and feedback follows
your answers at once · **Single assistant** — one assistant writes, checks and grades; less
usage, a short wait before each feedback. With helpers → `helpers` true; Single → `helpers`
false. `prepare_ahead` stays true unless the learner asks otherwise. Add in one line that the
grading is only as good as the model the round is run with, so rounds are best run on the
most capable model they have.

**Batch 3 — where you stand** (free text is fine): the domain list with a 1–5 self-rating per
domain, or the two or three strongest and weakest areas; resource preferences (free only?);
anything else to know.

The mix sets `mcqs`, `focused` and `case`; the time sets `session_minutes` (15, 25, 35 or 45).
`cme.py` estimates a round at about 5 minutes per MCQ, 10 per focused question, 15 for a
one-step case and 25 for an unfolding one, feedback included (`MINUTES_PER`; `init` and
`settings` print the estimate for the mix as `round`, the opening line of every round gives
it, and the page shows it). Size the mix to the time the learner names, so that the estimate
(in brackets) fits it:

| Mix chosen | ~15 min | ~25 min | ~35 min | ~45 min |
|---|---|---|---|---|
| Focused + full case (recommended) | one-step case, `focused` 0 (15) | 1 focused + one-step case (25) | 1 focused + unfolding case (35) | 2 focused + unfolding case (45) |
| MCQs + full case | one-step case, `mcqs` 0 (15) | 2 MCQs + one-step case (25) | 2 MCQs + unfolding case (35) | 4 MCQs + unfolding case (45) |
| MCQs + focused + full case | one-step case, `mcqs` 0, `focused` 0 (15) | 1 focused + one-step case, `mcqs` 0 (25) | 2 MCQs + 1 focused + one-step case (35) | 2 MCQs + 1 focused + unfolding case (45) |
| Focused only | 1 focused (10) | 2 focused (20) | 3 focused (30) | 4 focused (40) |
| MCQs + focused | 1 MCQ + 1 focused (15) | 3 MCQs + 1 focused (25) | 3 MCQs + 2 focused (35) | 3 MCQs + 3 focused (45) |
| MCQs only | 3 MCQs (15) | 5 MCQs (25) | 7 MCQs (35) | 9 MCQs (45) |
| Full case only | one-step case (15) | unfolding case (25) | unfolding case (25) | unfolding case (25) |

A cell with a one-step case sets `case_format` discriminate; an unfolding case is the learner's
case style (unfolding unless they chose otherwise; "alternate" takes 15 or 25 minutes for the
case in turn). An unfolding case alone is 25 minutes, so a session of 15 gets a one-step case
or short questions only, and a cell that had to drop a kind the learner chose says so: offer
it ("in 15 minutes there is room for a one-step case, or for one focused question and an MCQ:
which would you rather have?"). Say the estimate when you confirm the mix ("one focused
question and the case: about 35 minutes with feedback"). The learner chooses; they can always
pick other numbers, here or on the page.

| Answer | Setting |
|---|---|
| Where you are / where you're aiming | `profile.journey` / `profile.aim`, the learner's words; `profile.journey_label`, `profile.aim_tags` derived |
| Guidelines: Iceland/Europe / UK / North America / other | `guideline_region` "Iceland/Europe" / "UK" / "North America" / the learner's words |
| Specialty | `profile.specialty` (default "Internal/hospital medicine") |
| Time per session | `session_minutes` 15 / 25 / 35 / 45, and the mix from the table above |
| Feedback depth | `feedback_depth` detailed (default) / standard |
| Frequency | `target_sessions_per_week` 5 / 3 / 2 / 1 |
| Self-ratings | `profile.domain_self_ratings` {CODE: n} |
| Weakest areas named without ratings | 2 for those domains; strongest → 4 |
| Review every 1 / 2 / 3 months | `review_interval_days` 30 / 60 / 90 |

## 3. Create the ledger and the page

`store.md` §5: `cme.py init --work <work>` with the answers (the profile holds `journey`, `aim`
and their labels; the config holds `mcqs`, `focused`, `case`), then create the store from the `files` it prints: where the
app can host a private page with files, publish `templates/page.html` with the ledger
files as the page "Clinical CME" and pin it; otherwise a folder the learner names or files
they keep. Ask which only if more than one is possible and the learner has a preference;
default to the page. Blueprint: `templates/blueprint.json` for internal/hospital medicine; for another
specialty draft one in the same shape (domains with weights, topics with stable IDs such as
`PEDS-01`) from that specialty's core-competency or board outline and show the domain list for a
quick check before saving. Lower weights for domains that do not fit the practice setting.

Tell the learner (show this):

> Your ledger and log are in your private **Clinical CME** page. Rounds work from any device where
> you are signed in; nothing to download or attach. Please keep the page's title as it is — that
> is how the skill finds it. Everything in it can be exported at any time.

(For a folder or files you keep, say where they are and, for files they keep, to attach `state.json` and
`page.json` at the start of each session.)

## 4. Finish setup

- **Always-ready rounds; ask once**, where this session can create scheduled tasks: "Shall I
  add a nightly task that makes sure your next round is prepared, so it always starts at once
  even if you close the app early?" Yes → `preparing.md` §4. No is the default.
- **Reminders are optional; ask once.** "Would you like reminders for your sessions?" No (the
  default) · Yes, matching my frequency. Save with `settings --config '{"reminders": …}'`.
  Yes: if this session can create scheduled tasks, create one matching `target_sessions_per_week`
  (days and time the learner names, their time zone) with the prompt "Run a clinical-cme round";
  confirm in one line. No scheduling here: say so, keep `reminders` true for a later session.
- Offer the first round now. After its feedback, ask whether it felt too easy, about right or
  too hard. Too easy or too hard: ask what they would add to "where you are", and save their
  words with `settings --profile '{"journey": "…"}'` (`requests.md` §1). The difficulty is
  never adjusted from scores on its own.

## 5. FAQ (answer on request)

**How long does a session take?** As long as you set; ask for a shorter or longer round any time
("just three MCQs today", "only focused questions today").

**What is a focused question?** A short case — a few lines of history and the results you would
have at that moment — that ends in one open question on a single decision: the most likely
diagnosis, the next test, what to do now, where the patient should go. You answer in a few lines
and say why; the grading is on that reasoning (the right answer without a reason scores at most
3 of 5). It takes about ten minutes with its feedback.

**Can I make the questions harder, easier or aimed at an exam?** Yes: say so in your own words
("I'm a fellow now", "I'm sitting the exam in May, aim at that"), or rewrite the paragraph under
Settings on your Clinical CME page ("Where you are", "Where you're aiming" → Update). The next
round is written for what you wrote. Nothing changes the level behind your back: your scores
decide when a topic comes back, not how hard the questions are.

**Can I change what a round contains?** Yes, any time: in your Clinical CME page (Settings → "What
goes into a round": switch MCQs, focused questions and the full case on or off and set how many),
or ask in a chat ("add a focused question to my rounds"). A change on the page applies from your
next round; whichever change you made last wins.

**Can I choose the area of a block?** Yes. At the end of a block the next area is proposed with
the reason (where you are weakest, or what has waited longest); say "pick another" for the next
suggestion, or name the area you want ("cardiology next"). You can do the same in the middle of
a block: it ends there, and the new one starts with your next round. Nothing is lost: what you
have done stays in your record and comes back as repeats. Your page shows the current block and
how far you are through it.

**Why won't it tell me the topic?** Knowing the topic changes how you think. The topic and the
reason it was chosen are revealed with the feedback: the short questions' when you have
answered them, the case's at the end.

**Can I see the answer in the assistant's working steps?** Helpers' work appears as steps
called "Prepare the round" and "Check sources", and the assistant's own as "Update today's
round"; with helpers on, the assistant you talk to has not even read the answers until you
have given yours. Do not expand those steps before answering.

**How is it this fast?** Each round — the short questions, the case and the notes for your
feedback — is written, and its sources checked, at the end of the round before and kept,
packed, in your page. So a session starts at once, the case appears the moment the questions
are graded, and nothing has to be looked up after you reply. Say "helpers off" or "don't
prepare ahead" to turn either off.

**Does the preparation finish if I close the app?** It runs right after the closing message.
Where your sessions run in the cloud it carries on; where they do not, or if you leave before
the reflection, it may not finish — nothing is lost, the next round is then written at its
start. To be sure a round is always ready, say "prepare my rounds overnight": a small
scheduled task checks each night and prepares one only if none is ready.

**Who writes the questions and who grades them?** With helpers on, three different assistants.
An *author* on the most capable model writes the round. The assistant you talk to *examines*:
it grades your answers against the checked evidence, and treats the author's answer key as a
colleague's opinion, not as the truth — if the key is wrong or too narrow, it says so and
credits you. A lighter *checker* looks up and reports the sources; that needs care rather than
depth, so it runs on a cheaper model to keep usage down. With helpers off, one assistant does
all three.

**Why did my round start with a pause this time?** The prepared round is used only if nothing
changed since it was written (the round mix, a setting that changes the questions, a review) and you did not ask for
a special round; otherwise it is written at the start.

**Whose guidelines does it use, and for which specialty?** The ones you chose at setup
(Iceland/Europe and internal/hospital medicine unless you said otherwise). Change either any
time: "use UK guidelines", "my specialty is geriatrics".

**Can I choose the area?** Yes: "a cardiology round". The domain is then known, the question is not.

**Can I use it from my phone or a work computer?** Yes, when your ledger is in your Clinical CME
page: open any chat in an app that can read the page's files, invoke the skill, and the round
starts. With a folder or files you keep, use a device that can reach them.

**What is stored, and where?** Everything is in your private Clinical CME page (or your folder):
the ledger (scores, due dates, gaps, coded errors, settings) and one document per session, word
for word. Nothing is shared unless you share the page. "Give me my data" exports it all.

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
sooner, though never sooner than three days, so that a repeat tests what you kept rather than
what you just read; feeling confident while scoring low brings a topic back quickly. A gap stays
open until a later question tests that exact point and you answer it well.

**What if I skip the reflection or walk away?** After the final feedback the round is saved;
reply "skip" to save without a reflection. If you stop after the short questions, say so ("no
time for the case") and they are saved on their own; if you simply leave mid-round, nothing is
recorded and the same topics come back next time.

**What if I fall behind?** Nothing breaks: overdue topics come first at your normal round size.

**How do I reset or stop?** Say "start over" (a fresh ledger in the same page) or delete the page.

**Does this count as CME credit?** Not on its own; the review can summarise time and topics for
a self-directed-learning record. Check your regulator's rules.

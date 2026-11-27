# clinical-cme

Blinded clinical self-assessment for practising physicians: short rounds of questions and a case,
graded against current evidence, with a schedule that brings weak topics back.

## Rounds and items

**Round**:
One session of assessment: the short questions, their feedback, the case, its feedback, and a reflection.
_Avoid_: quiz, session (when meaning the content)

**Short question**:
An MCQ or a focused question; asked before the case, on topics unrelated to it (in a block they often share its domain, never its topic).

**Focused question**:
A mini-case ending in one free-text question on a single decision, graded on the reasoning.

**Case**:
The full clinical case of a round, usually unfolding in two stages.
_Avoid_: vignette, scenario

**Key**:
What the author writes down as the right answer to an item and how to score it; the examiner grades with it as the author's view.
_Avoid_: answer sheet, solution

**Key header**:
The few fixed lines at the top of a key (topic, stem summary, aspect, compact case, selection reason, the gap it retests) that the state engine reads.
_Avoid_: metadata, front matter

**Rubric**:
The expected elements of a focused question's or the case's answer, one line each (the case's grouped by stage), that the examiner marks hit, partial or missed. The author writes it in a **rubric block** beside the key header, where the state engine reads it.
_Avoid_: checklist, marking scheme

**Results bank**:
The prepared results of tests the learner may order in Stage 1 of a case.

**Prepared round**:
A whole round written and source-checked in advance and stored packed in the learner's store.

**Kit**:
The sealed file beside an item file that holds its feedback's text: the prepared blocks, and notes for the reading pointers and listening candidates.
_Avoid_: feedback notes (it now holds finished text)

**Prepared block**:
One piece of the feedback's finished text in a kit, written and source-checked when the round is prepared: an item's reveal, model answer, distractors, decisive point, differential, pearls or deeper evidence, or the teaching for one rubric element at one mark (missed, partial, hit). The examiner may use it as it stands, rewrite it or drop it.
_Avoid_: template, canned feedback, snippet

**Marks before text**:
The examiner marks every rubric element (each tied to the learner's words) and every MCQ before any prepared block is used; the marks choose the blocks, never the other way round.

**Draft**:
The feedback message as the state engine puts it together from the marked grading form and the prepared blocks, in the feedback's order, with the rubric as marked and the parts only the answer can prompt left to write live.
_Avoid_: template

**Live part**:
What the examiner writes once the answers are in: the opening in the learner's own words, verdicts, calibration, transfer, the sibling line, the gap summary and coding line, credit for a defensible answer outside the key and corrections to the key, the glossary line, the reading and listening picks.

## People and roles

**Learner**:
The physician taking the rounds.
_Avoid_: user, student

**Author**:
Whoever writes a round's items, keys and the prepared blocks of their feedback.

**Examiner**:
The assistant in the conversation: presents, marks against the evidence, and writes the feedback from the marks, the draft and the live parts; never the author of the items it grades. Its one brief is `references/feedback_guide.md`.
_Avoid_: judge, grader

**Checker**:
Whoever verifies a round's sources against its verification lists.

## Record

**Store**:
The place the learner owns that holds all their data: their own artifact page, or a folder.

**Ledger**:
The learner's schedule, gaps, coded results and settings (`state.json`).
_Avoid_: state (in conversation with the learner)

**Engine stamp**:
The version of the skill whose state engine last wrote the ledger (`skill_version` in it), set on every write. An engine never writes a ledger stamped by a newer one: it says "update the plugin" and only reads. A ledger without a stamp counts as older.
_Avoid_: schema version (that is `schema`, the ledger's shape)

**Log**:
The verbatim, append-only record of every round, one session document each.

**Round record**:
What the ledger keeps of one round: its items with topic, score, confidence and coding, the gaps and the compact case. The state engine builds it from the key headers and the examiner's grading.
_Avoid_: round JSON (for the assembled record)

**Grading form**:
The skeleton of the round's grading that the state engine writes once a part's answers are in: one entry per key, with what the key headers and the ledger already know (topic, aspect, retest, evidence depth, position notes, the rubric's elements) and blanks for the marks, scores, confidence and coding, plus how to fill it and the allowed codes. The examiner fills it in; `save` records it.
_Avoid_: round template, grading sheet

**Reflection form**:
The same for the reflection: written when the reflection arrives, with a blank comfort rating per topic tested and the shapes of a self-reported gap, a learner-set score, a closed gap and a stop with its position note.

**Undo record**:
What a round's session entry keeps of only what the round changed in the ledger (topics, gaps, resolved gaps, comfort ratings) and its own gaps as written, so it can be taken out and applied again. It holds a topic only while the round is the latest on it.
_Avoid_: snapshot (the whole tables 5.0 kept instead)

**Apply again**:
Undo a round and apply it once more with amended input, through the same step that recorded it. `save` run again, the reflection, a dispute, a learner-set score, a gap the learner closes and a stop are all this one step, so each gives the same result whenever it is said.
_Avoid_: reschedule, re-record, replay

**Latest round on a topic**:
The last round that changed the topic (tested it, wrote or closed its gap). Only it is applied again on that topic; after a later round, the earlier round's record still changes but the topic keeps the later round's schedule.

**Page file**:
The file the engine writes for the page (`data/page.json`): exactly what the page may show, already blinded. It is all the page renders, apart from the prefs it writes itself and the session or review document the learner opens; only Export reads the ledger.
_Avoid_: index (it replaces `data/index.json`)

**Page**:
The learner's own view of their store: past sessions, scores, progress reviews, topics already tested, reading and listening from past rounds, and settings. It never names what a coming round will test (no open gaps, no due topics).
_Avoid_: dashboard

**Gap**:
A specific point the learner got wrong or flagged as shaky, linked to a blueprint topic, open until an item tests that point and it is answered well, or until the learner closes it themselves.

**Learner-set score**:
A score the learner asks to have recorded in place of the examiner's ("record it as 4"). The record keeps both; scheduling uses the learner's. Not a dispute: the grading did not change.
_Avoid_: override (fine for the command), dispute

**Stop**:
The learner's instruction that a topic is known and should not keep returning ("I know this, stop bringing it back"); sets their score, closes the topic's gaps and schedules it at the longest interval. One more amendment of a round, the same before or after the close. No topic is retired for good by a stop (only the blueprint retires a topic).
_Avoid_: retire, suspend, mute

**Position note**:
The learner's own statement of what they hold on one decision point of a topic, kept word for word with a stop, so later items and grading respect it: no item is keyed on it and the learner is not marked down on it. Listed at each progress review to keep or drop; lapses after about six months unconfirmed.
_Avoid_: dispute (the grading did not change), topic note, override

**Retest**:
An item written on an open gap's decision point, in a new clinical context; it names the gap, and only a retest answered well closes it.

**Evidence depth**:
How far behind the recommendation the feedback on an item goes when it is answered well: guidance, then the studies it rests on, then their design, then where the evidence is disputed. Earned per topic (and per aspect of a focused question) by answering it well several times in a row; a miss or an open gap brings it back to guidance, taught in full.
_Avoid_: level (that is the learner's stage), difficulty, feedback depth (the word-count setting `feedback_depth`)

**Deeper block**:
The prepared block (`deeper`) that holds the checked studies and design features for an item the plan gave an evidence depth beyond guidance, as finished text; the draft uses it only for an item answered well.
_Avoid_: Deeper notes (the outline it replaced)

**Listening pick**:
The one podcast episode a topic of the round gets in the final feedback: 15 to 90 minutes, chosen for the gap the learner showed, given as a Spotify link with a one-line reason.
_Avoid_: recommendation, podcast link

**Reading pointer**:
One of at most two further-reading items in the final feedback: a document, the exact section to read, the minutes it takes and one line on why it fits the gap. Listed with its link in the session document.
_Avoid_: reference, reading list

**Library**:
The reading pointers and listening picks of past sessions as the page lists them under "Reading & listening" (`library` in the page file). Whether one is done is kept in the viewer's browser, never in the store.

**Candidate episode**:
One of up to three episodes per topic that the checker finds when the round is prepared and that stay sealed in the kit; the pick is taken from them when one covers the learner's gap.

**Podcast sources**:
The shows the learner trusts and the shows to avoid; asked once, and always respected.

**Rest**:
The minimum of three days before a tested topic or a new gap can come back.

**Work folder**:
The scratch folder in which one job is worked on (a round, or a settings change, a theme change or preparing the next round, set up with `open`); every file has a fixed name there and every command needs only the work folder.
_Avoid_: temp folder, session folder, workbench (fine when explaining to the learner)

**Publish set**:
The one list in the work folder of what the store must hold now: the newest version of every store file that changed, the store version it was read at, and the write order (the ledger last). Every command updates it; whoever carries files to the store publishes all of it.
_Avoid_: output folder, files list

## Curriculum

**Blueprint**:
The list of domains and topics the curriculum covers; one level (topics), or two (topics with their sub-topics).

**Default blueprint**:
The blueprint a new internal/hospital-medicine learner gets (`templates/blueprint.md` and `.json`): two levels, 16 domains, 144 topics, 347 sub-topics with their decision points, on the ABIM general skeleton with European guidance. A learner's ledger keeps its own copy: a new default reaches an existing learner only through `settings --blueprint` and a mapping file.

**Retired topic**:
A topic the blueprint keeps only so that ledgers which tested it still resolve its id, marked `(retired)` or `(retired: now RHEUM-04a)` in its label. Never planned (not as new, due or a gap retest); its record stays until a mapping folds it into another topic.
_Avoid_: deleted topic (ids are never removed)

**Domain**:
A blueprint grouping such as cardiology or gastroenterology, one `##` heading of the markdown blueprint, with one code (`TOX`); a topic id may carry another prefix (`EMRG-01` is in `TOX`).

**Topic**:
One blueprint entry within a domain, a disease process ("Atrial fibrillation"); the unit that is scheduled: it returns on schedule.
_Avoid_: disease (fine with the learner; the engine and the docs say topic)

**Sub-topic**:
One angle of a topic in a two-level blueprint ("AF: stroke prevention decision"; id `CARD-03a`); what rotates and is recorded. When the topic comes due, the plan picks the sub-topic (the gap's own, else one not yet tested, else the weakest; never the last round's on that topic); its record (rounds, last score), evidence depth and stems used are counted from the items that name it.
_Avoid_: subtopic as a separate schedule, facet

**Decision point**:
One decision a sub-topic can be tested on, from the author's list for it in the blueprint (`points`). For variety only: never scheduled. A missed one still comes back exactly, through its gap and retest.

**Sibling line**:
The one line of an item's feedback tying it to the other sub-topic of the same topic the learner answered last time (the shared frame, and where the two decisions part).

**Mapping file**:
The learner's list of where their past items and open gaps go on a two-level blueprint (past item → the sub-topic it tested), applied once with `apply-mapping`. Learner data: never committed.

**Frozen round**:
A round recorded before a mapping that moved its items or changed its topics: it can no longer be applied again (its scores stay; a gap closed or a stop on its topics applies outright).

**Block**:
A run of rounds (default 12) with one domain as its theme; most new material and the case come from the theme.

**Short block**:
The block of a domain with fewer than four blueprint topics: two rounds per topic (three topics, six rounds). Any domain with topics can be a theme.
_Avoid_: module, month

**Theme**:
The domain of the current block. It is visible to the learner; topics stay blind. It is proposed with a one-line reason and the learner can change it, at the end of a block or in the middle of one.

**Measured weakness**:
In the theme proposal, the factor read off the mean current mastery of a domain's tested topics: about 1.5 at a mean of 2.5, 1.0 at 3.5, about 0.7 at 4.5 (1.0 with nothing tested). It multiplies the domain's weight, so weight still leads but a clearly weaker lighter domain can overtake.

**Share**:
The part of a round's short questions given to the theme (60%), to due repeats (25%) or to the wildcard (15%), met over the block rather than in every round. While the backlog is large the theme gives up 15 points to the repeats (45/40/15).

**Backlog**:
The topics whose spacing date has come (as `status` counts them, `due_count`). Six or more is a large backlog: the plan says so in `block.backlog` and takes the backlog shares until fewer are left.

**Due repeat**:
A topic whose spacing date has come, or a gap ready for its retest, from any domain; fills the repeat share.

**Wildcard**:
A short question on an untested topic outside the theme, so breadth is not lost during a block.

**Drill-down**:
Successive rounds coming back to one topic after wrong answers. Limited: no topic is in more than two rounds in a row; outside the theme a miss gets one retest, then at least a week between returns; inside the theme a topic missed on its second round of the block (or later) waits at least a week (the **pause**), and no gap retest or revisit brings it back before its date.

**Guideline region**:
The learner's choice of whose guidelines items are written and graded against; asked at setup, default Iceland/Europe.
_Avoid_: country, locale

**Where you are**:
The learner's own paragraph on their stage of training or career and how they rate their knowledge and skills (`profile.journey`); the author pitches items to it and the examiner writes the feedback for it. A short stage label (medical student … senior attending) is derived for display only.
_Avoid_: level, role (as a fixed category)

**Where you're aiming**:
The learner's own paragraph on what the rounds should help them achieve (an exam, a level, areas to strengthen; `profile.aim`); part of the pitch, with goal tags derived for display only.
_Avoid_: goals list

**Rulebook**:
The numbered standards for writing items (`references/standards.md`), the same for every learner; briefs cite its rule numbers. Contrast with settings, which are per learner.
_Avoid_: guidelines (means clinical guidelines here)

**Crux test**:
The decisive test of an item when it is one clinicians often fail to order; its result is requested by the learner, never given in the stem (rule 7 of the rulebook).
_Avoid_: key test, special test

**Glossary line**:
The one line "Abbreviations: …" that opens a feedback message and explains the abbreviations it uses (rule 5.3, written in the examiner's brief). Presented items have none: there an abbreviation is spelled out at first use.

**Time anchor**:
The single point a case counts all its timings from: a named event (admission as day 0) or now, never both (rule 6).

**Active time**:
The minutes of a round in which something happened: the learner answering, waiting for the examiner or reading feedback, with idle stretches cut. Measured by the engine from the steps of the round; nobody types a time.
_Avoid_: duration, session length (that is the budget)

**Timed round**:
A round whose active time was measured. Rounds of older versions are not timed (their minutes were capped at 180) and count in no median or estimate.

**Pace**:
The learner's active time per round against the default estimate for the same items; estimates move to it over ten timed rounds.

**Time hint**:
The one sentence, from five timed rounds, comparing the learner's median round with their budget and naming the change to the mix that would fit it best.

**Specialty**:
The learner's field of practice, which sets the pitch of items and which guideline applies; asked at setup, default internal/hospital medicine.

## Development

**Testing mode**:
A learner setting that adds a short feedback check and a store-integrity check at the end of each round.

**Example ledger**:
A synthetic ledger kept with the tests (fresh, mid-curriculum, overdue, unreflected, stale prepared round, drilled), with the expected plan, due dates and applied round saved beside it.
_Avoid_: fixture, golden file (in conversation)

**Simulation**:
A scripted run of the skill in which one agent is the examiner and another plays a learner persona.

**Persona**:
The kind of learner an agent plays in a simulation (strong; weak and overconfident; disputes a grade; stops halfway).

**Quality scorer**:
A third agent in a simulation that, after the round, rates each item and each feedback message for clinical quality. It takes no part in the round.
_Avoid_: judge

**Clinical-quality score**:
The quality scorer's rating, 1–5, of one item or one feedback message; kept in the simulation report for comparison over time, never a pass bar.

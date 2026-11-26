# Other requests, testing mode and round variants

Read this when the learner asks for something other than a round (§1), when `testing` is true
in the `start` output (§2), or when the round is not the usual one (§3).

Contents: 1. Requests · 2. Testing mode · 3. Round variants

## 1. Requests

Every request that changes something has the same path: read the store (SKILL.md, turn 1,
step 1) → `python3 cme.py open --work <work> --store <work>/store --version <version read>` →
the command for the request, with `--work <work>` → publish its `files` (`store.md` §4) →
confirm in one line. A change of settings is `python3 cme.py settings --work <work> --config
'{…}' --profile '{…}'`. The output's `prepared` says whether the round prepared ahead was
kept (`state_schema.md` §8: testing mode, reminders, helpers and the like keep it; anything that
changes the plan or the items sets it aside). When `prepared.kept` is false, add half a line
("your next round will be written when it starts"); offer nothing. If a round follows in the same conversation, start
it with `start --work <work>` (no `--store`): it continues from the changed ledger.

| The learner asks | Do |
|---|---|
| **Settings** ("make sessions 30 minutes", "more perioperative medicine", "use kPa") | `settings` as above. Emphasis is `profile.domain_emphasis`; a changed blueprint is `--blueprint <file>`. |
| **Theme** ("pick another", "cardiology next") | `cme.py theme --work <work> --another` or `--set "<area>"` → publish its `files`; send its `say` (`state_schema.md` §4.1). |
| **Region or specialty** ("use UK guidelines", "my specialty is geriatrics") | `settings --config '{"guideline_region": "UK"}'` or `--profile '{"specialty": "Geriatrics"}'` (the learner's own words are fine; add `lab_units` or `blood_gas_units` only if they ask); confirm from the `guideline_region` and `specialty` it prints. Both apply from the next round. A specialty outside the current blueprint also needs a blueprint for it: offer to draft one (`onboarding.md` §3) and pass it with `--blueprint`. |
| **Round mix** ("add a focused question to my rounds", "no more MCQs", "drop the case") | `settings --config '{"focused": 1}'` (or `mcqs`, `case`; at least one item stays); confirm with the new mix and its time estimate (`round` in what `settings` prints: about 5 min per MCQ, 10 per focused question, 25 for the case, 15 for a one-step case), and mention that the page's Settings tab has the same switches. For one round only, use the `start` options instead (SKILL.md, turn 1) and leave the settings alone. |
| **Listening** ("listening off", "no podcasts", and back on; "I trust The Curbsiders", "never Example Show") | `settings --config '{"listening": false}'` (or true), or `--profile '{"podcast_sources": {"trusted": ["The Curbsiders"], "avoid": ["Example Show"]}}'` (send only the list that changes; a list replaces the one before it, so add to what `listening` in the output shows). Confirm from the `listening` it prints. Both change what a prepared round holds, so it is set aside. |
| **Speed settings** ("helpers off", "don't prepare ahead", and back on) | `settings --config '{"helpers": false}'` or `'{"prepare_ahead": false}'`. Without helpers you write, check and grade everything yourself (less usage; a short wait before each feedback; no separate author); without preparing ahead, each round is written at its start. |
| **Always-ready rounds** ("prepare my rounds overnight", and off again) | `preparing.md` §4. |
| **Prepare my next round** | `preparing.md` §3. |
| **Testing mode on or off** | `settings --config '{"testing": true}'` (or false); then §2 applies to every round. |
| **Reminders on or off** | Create or delete a scheduled task (`onboarding.md` §4) and set `config.reminders`. If this session cannot schedule tasks, say so. |
| **Progress review** ("how am I doing?", or when due) | `progress_review.md`. |
| **Finding past cases** ("find my cases on sepsis", "which sessions had anchoring?") | The page file (`data/page.json`, `sessions`) has titles, tags, topics and dates, and is safe to read (it is what the page shows); for words inside transcripts, read the session files into local files and search them. Answer with a short table (ID, date, title). Read-only. |
| **Teaching export** ("turn S0042 into a teaching case") | `session_log.md` §6. |
| **Open my log / show the page** | Give the page's link; offer to pin it where the app can. |
| **Move my data to a folder** | `store.md` §3 and §7. |
| **Export everything** ("give me my data") | `store.md` §7. |
| **FAQ or how it works** | `onboarding.md` §5, briefly. |
| **A score or a gap set by the learner** ("record that as 4", "close that gap") | After the close: read the store with that session's document, `open`, then `cme.py override --work <work> --scores '[{"topic": "CARD-03", "score": 4}]' --close-gaps '[{"gap": "G0007"}]'` → publish its `files` (`feedback_guide.md` §7.1). Before the close it goes in the reflection JSON. Never edit the ledger by hand. |
| **Add the reflection to the last session** | `store.md` §6, "Session saved without a reflection". |

## 2. Testing mode

On while the skill is being tested (`config.testing`; `testing` true in the `start` output).

- **Close message**: after everything else, a rule and four quick questions: "Testing check
  (about 30 seconds): 1. Waiting: fine / noticeable / annoying, and at which step? 2. The
  items, 1–5? 3. The feedback, 1–5? 4. Anything else, in a line?"
- **Store check**, behind the scenes after every publish and the `finish-prepare` of the
  closing turn, last of all: read the store again as at the start, plus
  `data/sessions/<id>.json`, into a separate folder `<work>/reread/`; then `python3 cme.py
  verify --work <work> --store <work>/reread` (it compares the whole publish set with what
  the store now holds and writes `<work>/verify.json`). `"ok": false` → tell the learner at
  once in one line which files did not save, and follow `store.md` §6.
- **The learner's answers** (their next message, any form; "skip" is fine): `python3 cme.py
  testing-note --work <work> --feedback '{"waiting": "…", "waiting_step": "…", "items": N,
  "feedback": N, "note": "…"}'` (the session and the store check are taken from the work
  folder) → publish its `files`. Reply "Noted, thanks." A dispute or comment on content in
  the same message is handled as discussion, as usual.

## 3. Round variants

- **Case first** (`item_order` `case_first` in the `start` output): present the case first, the
  short questions after its Stage 1, Stage 2 last, and all feedback in one final message
  (`feedback.md` only; `feedback_guide.md` §2).
- **No short questions**: the case is the first part. Turn 1 sends it (`present --block
  case`), and turns 3–5 follow.
- **A specific topic by name**: allowed, but not blind; say so in one line and proceed. Run
  `start` with `--no-prepared` for that round.
- **A specific area, or a different mix, for this round only** ("a cardiology round", "just
  focused questions today"): the `start` options `--domain CODE`, `--mcqs N`, `--focused N`,
  `--no-case`, `--no-new`. The domain is then known to the learner; the questions are not.

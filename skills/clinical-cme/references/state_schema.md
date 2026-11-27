# State, round JSON, reflection JSON and spacing rules

The ledger (`data/state.json`) is the learner's scheduling
memory: one JSON document, read to a file and written from a file (`store.md` §4). Change it only through `scripts/cme.py`.

## 1. State layout (schema 4)

```json
{
  "schema": 4, "gen": 21, "content_gen": 20, "created": "2026-10-08", "updated": "2026-10-26", "next_id": "S0022",
  "profile": {"display_name": "Dr A", "specialty": "Internal medicine",
              "subspecialty": null, "practice_setting": ["University hospital, inpatient"],
              "journey": "Hospitalist for eight years; I run the take alone at night …",
              "journey_set_at": "2026-10-08T09:12:00Z", "journey_label": "attending",
              "aim": "Stay current, and make the specialist's call when nobody is there to ask.",
              "aim_set_at": "2026-10-08T09:12:00Z", "aim_tags": ["keep up to date"],
              "strengths": ["…"], "weaknesses": ["…"], "goals": [],
              "domain_self_ratings": {"CARD": 3.8}, "domain_emphasis": {"GEN": 1.5},
              "notes": "free text", "onboarded_at": "2026-10-08",
              "podcast_sources": {"trusted": ["The Curbsiders"], "avoid": []}},
  "config": {"session_minutes": 35, "mcqs": 0, "focused": 1, "case": true, "case_format": "unfolding",
             "round_set_at": "2026-10-08T09:12:00Z",
             "feedback_depth": "detailed", "evidence_ladder": true, "target_sessions_per_week": 3, "review_interval_days": 42,
             "intervals_days": [1, 3, 7, 16, 35, 90], "new_topics_per_round": 1,
             "lab_units": "SI", "blood_gas_units": "mmHg", "guideline_region": "Iceland/Europe",
             "item_order": "mcqs_first", "helpers": true, "prepare_ahead": true,
             "show_coding": true, "reminders": false, "listening": true,
             "resource_preferences": {"free_only": false, "formats": ["guidelines"]}},
  "review": {"last": null, "next_due": "2026-11-19", "period_start": "2026-10-08"},
  "blueprint": {"CARD": {"name": "Cardiology", "weight": 1.0, "topics": {"CARD-01": "Acute coronary syndrome"}}},
  "topics": {"RENAL-02": {"domain": "RENAL", "label": "Hyponatraemia / hypernatraemia",
                          "last": "2026-10-26", "attempts": 4, "mastery": 3.5, "step": 3, "due": "2026-11-11",
                          "comfort": 5, "calibration": "aligned",
                          "history": [["2026-10-26", 3.5, 5, "aligned"]]}},
  "gaps": [{"id": "G0007", "topic": "RENAL-02", "gap": "re-testable description", "self": null,
            "source": ["graded"], "date": "2026-10-26", "opened": "2026-09-17", "last_retested": null}],
  "resolved": [{"id": "G0004", "topic": "CARD-03", "note": "…", "opened": "…", "resolved": "…", "partial": false},
               {"id": "G0006", "topic": "HEME-04", "note": "…", "opened": "…", "resolved": "…", "partial": false,
                "closed_by": "learner", "learner_note": "…", "session": "S0021"}],
  "block": {"theme": "GI", "round": 4, "length": 12, "started": "2026-10-12", "last": "2026-10-26",
            "chosen": "auto", "reason": "Gastroenterology & Hepatology: nothing tested yet, not yet a theme"},
  "blocks": [{"theme": "CARD", "started": "2026-09-01", "last": "2026-10-09", "round": 12, "length": 12, "chosen": "auto"}],
  "sessions": [ { "…one entry per session of the current review period (full coding)…" } ],
  "previous": [ { "…sessions of the previous period, compact coding…" } ],
  "agg": { "…all-time counters: sessions, items, errors by category/type/step/severity/bias, ART, IDEA, calibration, Brier, drills, disputes, overrides (scores and gaps the learner set)…" },
  "reviews": [{"date": "…", "doc": "reviews/2026-11-20", "headline": "…", "change_plan": ["…"]}],
  "drills": [{"code": "bias:premature_closure", "description": "…", "rate": 0.33, "set": "…", "until": "…"}],
  "errata": [], "pending_errata": [], "teaching_point_checks": {}, "unreflected": null
}
```

Order: `item_order` `mcqs_first` (the default) runs short questions → their feedback → case →
its feedback; `case_first` puts the case first and all feedback at the end. Speed settings:
`helpers` (where the app has helper agents: an author agent writes the items, a checker
verifies the evidence while the learner answers, and the conversation grades; SKILL.md,
"Roles") and `prepare_ahead` (the whole next round is written and source-checked after each close, §8);
`prepare_task` (false by default: the learner has a scheduled task that does the same
preparation whenever no round is ready). Both are on unless the learner turns them off; ledgers older than 4.3 get them
at their next save, and `start` reports `speed_settings_new` until then.

Region and specialty: `config.guideline_region` (default "Iceland/Europe") and
`profile.specialty` (default "Internal/hospital medicine") are free text, asked at setup
(`onboarding.md` §2) and changed with `settings`. `start`, the plan and `settings` print both
as `guideline_region` and `specialty`, with the default standing in where a ledger has none;
the author chooses guidelines by them and the examiner grades by them.

Where you are, where you're aiming: `profile.journey` and `profile.aim` are the learner's own
paragraphs, the answers to the two open questions of setup (`onboarding.md` §2), kept word for
word. They are what items are pitched to and feedback is written for (`standards.md` rule 4):
the plan's `profile` carries them to the author, and `start` prints them as `pitch` for the
examiner. `journey_set_at` / `aim_set_at` date the last writing of each (setup, a chat, or
the page, §7.1). `journey_label` (one of: medical student, intern, resident, fellow,
attending, senior attending) and `aim_tags` (any of: exam, independent practice,
specialist-level decisions outside own specialty, keep up to date, teach; `[]` when none
fits) are derived by the assistant for display on the page and are never used to write an
item; `null` means not derived yet, and `start`, `open`, `init` and `settings` then print
`labels_needed`: per label, the paragraph to read (`from`) and the labels to choose from.
A new paragraph, from wherever, clears its label. Changing a paragraph sets the prepared
round aside; changing only labels does not (§8).

Ledgers from before the paragraphs: every command that reads a ledger folds `role` and
`notes` into an empty `journey` (role, a blank line, the notes) and `goals` into an empty
`aim` (one per line), in the learner's words, unchanged; the next write keeps it. A stage
label is read off `role` where it names a stage (otherwise `labels_needed` asks for it). The
old fields stay in the ledger as they were and are no longer read for the pitch; `goals` and
`notes` remain free fields.

Listening: `config.listening` (true by default, also in a ledger that has no such key) puts a
`## Listening` section into the kits (`standards.md` rule 8) and a Listening section into the
final feedback (`feedback_guide.md` §2 E2). `profile.podcast_sources` is `{"trusted": [shows],
"avoid": [shows]}`, or null while the learner has not been asked: it is asked once, at setup
or in the first Listening section, and `close` then writes the answer from the reflection, or
two empty lists when none was given. `start`, `open` and `settings` print `listening`: `{"on",
"trusted", "avoid", "ask_sources"}`; the plan carries `listening` and `podcast_sources` for
the author. `settings` stores the lists without blanks or repeats and refuses any other
shape. Both settings change what a kit holds (§8).

Round mix: `mcqs` (0–10), `focused` (0–6) and `case` (true/false); at least one item. A new
learner starts with one focused question and the case (about 35 minutes; `session_minutes`
35); a ledger that has no mix of its own keeps three MCQs and the case.
`round_set_at` marks the last change of the mix (setup, a chat `settings` change, or a page
setting applied). The learner can also change the mix on their page; the page stores it as its
own settings document, `cme/prefs` (§7.1), and the next round applies it.

A session entry:

```json
{"id": "S0021", "date": "2026-10-26", "started_at": "…", "ended_at": "…", "minutes": 41, "reading_minutes": 10,
 "timing": {"answering": 22.5, "waiting": 6.0, "reading": 12.5, "idle_cut": 48.0},
 "title": "Confusion after a marathon — exercise-associated hyponatraemia", "summary": "…", "tags": ["RENAL-02", "…"],
 "topics": ["RENAL-02", "CARD-03", "TOX-03", "NEURO-01"], "format": "unfolding", "mcqs": 3, "mcq_correct": 2, "focused": 1, "score": 3.4,
 "items": [{"type": "case", "topic": "RENAL-02", "mastery": 3.5, "confidence": "unsure",
            "coding": {"art": {"DG": 2, "PR": 1, "DDX": 1, "TEST": 2, "META": 0, "MGMT": 1}, "idea": {"I": 2, "D": 1, "E": 1, "A": 0},
                       "errors": [{"element": "…", "stage": 1, "category": "synthesis", "art_domain": "DDX",
                                   "bias": ["premature_closure"], "bias_evidence": "the learner's words", "severity": "critical", "confidence": "sure"}]}},
           {"type": "mcq", "topic": "CARD-03", "mastery": 5, "confidence": "sure", "correct": true, "retests": "G0004", "stem": "…", "coding": {"errors": []}},
           {"type": "focused", "topic": "HEME-04", "mastery": 3, "confidence": "unsure", "aspect": "management", "stem": "…",
            "coding": {"art": {"MGMT": 1}, "errors": [{"element": "…", "category": "knowledge", "knowledge_type": "numeric", "art_domain": "MGMT", "severity": "important"}]}}],
 "why": {"RENAL-02": "due", "CARD-03": "due"}, "self_performance": 3, "self_comfort": {"RENAL-02": 5},
 "reflection": {"solid": "…", "gaps": "…", "skipped": false}, "key_learning": ["…"],
 "case": {"topic": "RENAL-02", "patient": "34M", "setting": "ED", "presentation": "…", "diagnosis": "…", "twist": "…"},
 "grade_changes": [{"item": "Case stage 2", "topic": "RENAL-02", "from": 3, "to": 3.5, "outcome": "both_defensible"}],
 "drill": null, "errata": ["E0003"], "steps_before": {"RENAL-02": 2, "CARD-03": 1}}
```

`minutes` is the round's **active time** and `timing` its parts, in minutes, measured by the
engine (§6.2): the learner `answering`, `waiting` for the examiner and `reading` feedback; a
stretch of more than 15 minutes without a step counts as 15 and the rest is `idle_cut`. A
session without `timing` is from an older version, whose `minutes` were the time from start to
end capped at 180 (sessions left open show exactly 180): it counts in no median and no estimate.
`reading_minutes` is something else: the further reading the learner reports in the reflection.

`steps_before` is each topic's step before the round (`override` reschedules from it). An item
whose score the learner set carries `"mastery": 4, "graded": 2, "set_by": "learner"`: `mastery`
is the learner's score, `graded` the examiner's; its `grade_changes` entry is
`{"item": "Q2", "topic": "CARD-03", "from": 2, "to": 4, "outcome": "learner_set", "examiner": 2,
"learner": 4, "date": "…", "note": "…"}`. A session in which the learner closed a gap lists it
in `learner_closed_gaps` (`[{"id": "G0006", "topic": "HEME-04"}]`). A `resolved` entry without
`closed_by` was closed by a retest.

While a session's reflection is pending, its entry also carries `_snapshot` and `_round`, which
`close` uses to re-apply the round with the reflection. `save` of the next session drops
them and marks the reflection skipped.

Teaching points are the `key_learning` lines, identified as `<id>.<n>` (`S0021.2`).

## 2. Round JSON (`round.json`) and the round record

The examiner writes `round.json` with **the grading only**: each item names its key header
(`standards.md` rule 9) and carries the score, the confidence and the coding. `save` fills in
everything the author already wrote down, and writes the result, the **round record**, to
`record.json` in the work folder.

```json
{
  "items": [
    {"key": "Q1", "mastery": 1, "correct": false, "confidence": "guess",
     "coding": {"errors": [{"element": "…", "category": "knowledge", "knowledge_type": "outdated", "severity": "important"}]}},
    {"key": "Q2", "mastery": 3, "confidence": "unsure",
     "coding": {"art": {"MGMT": 1}, "errors": [{"element": "…", "category": "knowledge", "knowledge_type": "numeric",
                                                "art_domain": "MGMT", "severity": "important"}]}},
    {"key": "case", "mastery": 3, "confidence": "unsure",
     "coding": {"art": {"DG": 2, "PR": 1, "DDX": 1, "TEST": 2, "META": 0, "MGMT": 1}, "idea": {"I": 2, "D": 1, "E": 1, "A": 0},
                "errors": [{"element": "…", "stage": 1, "category": "synthesis", "art_domain": "DDX",
                            "bias": ["premature_closure"], "bias_evidence": "'clearly dry from the run'", "severity": "critical", "confidence": "sure"}]}}
  ],
  "gaps": [{"topic": "RENAL-02", "gap": "Precise description incl. still-unresolved prior parts", "source": "graded"}],
  "resolved": [{"topic": "CARD-03", "note": "What was closed this time"}],
  "key_learning": ["One-line teaching points"],
  "summary": "One or two sentences on the main teaching.",
  "grade_changes": [], "drill": {"code": "bias:premature_closure", "result": "fell_for"},
  "errata": [{"corrects": "S0012", "point": "…", "correction": "…", "source": "…"}],
  "pending_errata_logged": "all",
  "reading": [{"topic": "RENAL-02", "title": "<guideline or article, with its year>", "link": "https://…",
               "section": "section 9 (indications for surgery) and its table", "minutes": 8,
               "why": "the thresholds you were unsure of"}],
  "listening": [{"topic": "CARD-03", "link": "https://open.spotify.com/episode/<id, 22 letters and digits>",
                 "show": "<show>", "title": "<episode title>", "minutes": 52,
                 "why": "when to start anticoagulation after surgery, the step you were unsure of",
                 "source": "kit"}]
}
```

What `save` fills in, and from where:

| Field | From |
|---|---|
| per item: `type`, `topic`, `label`, `domain`, `stem_summary`, `aspect`, `retests` | the item's key header |
| `case` (the compact description) | the header `<!-- key: case -->`, when the case was graded |
| `selection_reasons` | each graded header's `reason` (`new_in_domain` is recorded as `new`) |
| `case_format` | `plan.json` in the work folder |
| `log_id`, `date` | the ledger's next session ID; today |
| `title` | the case's "presentation — diagnosis"; without a case, the first stem summary |
| `tags` | the topics tested |
| `summary` | the first two `key_learning` lines |

- Only items the learner answered go into `items`. A header without an item is listed under
  `keys.not_graded` in the `save` output and is not recorded (a case the learner stopped
  before stays due).
- A field the examiner does write wins over the header and is listed under `keys.overridden`
  ("Q2.aspect"). Use it only to correct the author: for example `"retests": null` on an item
  that, as written, did not ask about the gap's decision point. A better `title`, `summary` or
  `tags` can always be given.
- **Missing or malformed headers.** If an item names a key that has no header, or its header
  lacks a field, has a misspelt one, a line that is not `field: value`, an unknown `type` or
  `aspect`, or an id used twice, `save` stops with `"ok": false` and one `error` that lists
  every problem by file, key and field ("sealed_questions.md, key Q2: 'aspect' is missing").
  Nothing is recorded. Correct the header in the sealed file and run `save` again. A problem
  in a header that no item names is only a warning.
- `python3 cme.py keys <folder> [--plan PLAN]` runs the same check on sealed files before a
  round is played, and prints no content (§6). `finish-prepare` runs it on a round prepared
  ahead and stashes nothing while a header is missing or malformed, so a prepared round does
  not fail at `save`. The fields are tabulated once, in `standards.md` rule 9.

The round record, as `save` writes it to `record.json`. A
`round.json` written out in full like this, with no `key` on its items, is recorded as it is:

```json
{
  "date": "2026-10-26", "started_at": "2026-10-26T08:00:00Z", "ended_at": "2026-10-26T09:29:00Z", "minutes": 41,
  "timing": {"answering": 22.5, "waiting": 6.0, "reading": 12.5, "idle_cut": 48.0},
  "case_format": "unfolding", "log_id": "S0021",
  "items": [
    {"type": "case", "topic": "RENAL-02", "label": "Hyponatraemia", "domain": "RENAL", "mastery": 3, "confidence": "unsure",
     "coding": {"art": {"DG": 2, "PR": 1, "DDX": 1, "TEST": 2, "META": 0, "MGMT": 1}, "idea": {"I": 2, "D": 1, "E": 1, "A": 0},
                "errors": [{"element": "…", "stage": 1, "category": "synthesis", "knowledge_type": null, "art_domain": "DDX",
                            "bias": ["premature_closure"], "bias_evidence": "'clearly dry from the run'", "severity": "critical", "confidence": "sure"}]}},
    {"type": "mcq", "topic": "ID-06", "mastery": 1, "correct": false, "confidence": "guess", "retests": "G0005",
     "stem_summary": "First CDI episode, outpatient, choice of agent",
     "coding": {"errors": [{"element": "…", "category": "knowledge", "knowledge_type": "outdated", "severity": "important"}]}},
    {"type": "focused", "topic": "HEME-04", "mastery": 3, "confidence": "unsure", "aspect": "management",
     "stem_summary": "Warfarin, INR 9, minor gum bleeding, what now",
     "coding": {"art": {"MGMT": 1}, "errors": [{"element": "…", "category": "knowledge", "knowledge_type": "numeric",
                                                "art_domain": "MGMT", "severity": "important"}]}}
  ],
  "gaps": [{"topic": "RENAL-02", "gap": "Precise description incl. still-unresolved prior parts", "source": "graded"}],
  "resolved": [{"topic": "CARD-03", "note": "What was closed this time"}],
  "key_learning": ["One-line teaching points"],
  "selection_reasons": {"RENAL-02": "due", "CARD-03": "new"},
  "title": "presentation — diagnosis or main point (≤ 90 chars)",
  "summary": "One or two sentences on the main teaching.",
  "tags": ["RENAL-02", "CARD-03", "hyponatraemia", "premature-closure"],
  "case": {"patient": "34M", "setting": "ED", "presentation": "confusion after a marathon",
           "diagnosis": "exercise-associated hyponatraemia", "twist": "looked hypovolaemic"},
  "grade_changes": [], "drill": {"code": "bias:premature_closure", "result": "fell_for"},
  "errata": [{"corrects": "S0012", "point": "…", "correction": "…", "source": "…"}],
  "pending_errata_logged": "all"
}
```

- `source` of a gap: `graded`, `transfer`, `misconception` or `self`.
- `retests` on an item: the id of the open gap the item was written to test. The author
  copies it from the plan's `retest_gap.id` into the item's key header, and `save` carries it
  into the record. It belongs only on an item that asked about the gap's decision point. It is
  the only way a gap closes (§4); `save` warns when a topic with an open gap was tested and
  no item carries it.
- `mastery` per item: cases 0–5 from the rubric; focused questions 0–5 from their table
  (`feedback_guide.md` §2 B2); MCQs typically 4–5 if correct with sound reasoning, 3 if correct
  with flawed reasoning, 1–2 if wrong.
- Focused questions need `aspect` (`diagnosis`, `interpretation`, `testing`, `management`,
  `disposition`, `prevention` or `prognosis`), `stem_summary`, and `coding` with ART for the
  domains they tested only, no `idea` (`analysis_framework.md` §1.6). `case` (the compact
  description) is for the full case only; omit it in a round without one.
- Every item needs a `coding` block (`analysis_framework.md` §1); a perfect item has ART scores
  and an empty `errors` list. `save` prints `warnings` for anything missing; fix and re-run.
- `pending_errata_logged: "all"` whenever `start` reported pending errata; `save` prints
  `errata_to_log` (full text) for part B.
- Times are never typed: `save` and `close` fill `started_at`, `ended_at`, `minutes` and
  `timing` from the round's clock (§6.2). A round recorded without a work folder may carry its
  own per-part timestamps instead, `"stamps": [{"what": "start", "at": "<ISO time>"}, {"what":
  "sent:questions", "at": "…"}, {"what": "answer:questions", "at": "…"}, …]` (the names of §6.2),
  from which the same figures are computed. With only `started_at` and `ended_at` the minutes
  are their difference, without `timing`, and no duration at all beyond 180 minutes.
- `reading`: the pointers of the feedback's Further reading section (`feedback_guide.md` §2
  E), at most two: the blueprint ID of the topic each serves (one of this round's), the title,
  the document's own http(s) link, the section to read, the minutes and the one-line reason.
  An empty list when the feedback gave none. `save` moves the list into the session document
  as its `reading` list (the ledger and `record.json` never hold it) and leaves out a pointer
  that is not complete, or a third one, with a warning naming what to correct. The feedback
  text keeps its Further reading section as before.
- `listening`: the picks of the feedback's Listening section (`feedback_guide.md` §2 E2), one
  per topic that got one: the blueprint ID, the Spotify episode link, the show, the title, the
  minutes, the one-line reason, and `source` (`kit`: a candidate prepared with the round;
  `search`: found after grading). An empty list when no topic got one; no key at all with
  listening off. `save` moves the list into the session document as its `listening` list (the
  ledger and `record.json` never hold it), drops anything after the id in a link, and leaves
  out a pick that is not complete, with a warning naming what to correct.
- Omit `reflection`: the first save is provisional. `save` can be run again: it starts from the ledger before the round.

## 3. Reflection JSON (input to `close`)

```json
{"topic_comfort": {"RENAL-02": 5, "CARD-03": 4}, "performance": 3,
 "solid": "the learner's words", "gaps": "the learner's words", "reading_minutes": 10, "skipped": false,
 "self_gaps": [{"topic": "ENDO-04", "gap": "Adrenal crisis management (self-reported)", "source": "self",
                "domain": "ENDO", "label": "Adrenal insufficiency / crisis"}],
 "grade_changes": [{"item": "Case stage 2", "topic": "RENAL-02", "from": 3, "to": 3.5, "outcome": "both_defensible"}],
 "items": [{"type": "case", "topic": "RENAL-02", "mastery": 3.5}],
 "learner_scores": [{"item": "Q2", "type": "mcq", "topic": "CARD-03", "score": 4, "note": "the learner's words"}],
 "learner_closed_gaps": [{"gap": "G0007", "note": "the learner's words"}],
 "podcast_sources": {"trusted": ["The Curbsiders"], "avoid": []},
 "errata": [], "key_learning": [], "resolved": []}
```

- `self_gaps` map each shaky area to a blueprint ID; an untested topic is created (or pulled
  forward) to within seven days. If no ID fits, make one in the blueprint's style and say so.
- `items` carries any score changed after a dispute (matched by type and topic); the coding of a
  changed item may be updated the same way (`"coding": {…}` replaces it).
- `learner_scores`: a score the learner sets themselves ("record it as 4"; `feedback_guide.md`
  §7.1), matched by topic, and by `type` where the round has two items on the topic. `item` is
  the name used in the log. Applied after `items`, so `graded` is the examiner's final score.
  Not a dispute: do not add a `grade_changes` entry for it, `close` writes one (`learner_set`).
- `learner_closed_gaps`: gaps the learner asks to close, by id (`{"gap": "G0007"}`) or by topic
  (`{"topic": "RENAL-02"}`, also for a gap this round opened). `close` stops with an error,
  writing nothing, when a named item or gap does not exist.
- `podcast_sources`: only when the learner named shows to trust or to avoid in reply to the
  one-time question of the Listening section (`feedback_guide.md` §2 E2); `close` writes it to
  the profile. Leave the key out otherwise: `close` then notes that the question was asked.
  A later change is a settings change (`requests.md` §1).
- `{"skipped": true}` records the round without a reflection.

## 4. Spacing rules (applied by `save` and `close`)

Mastery per topic is the mean of its items' scores this round, after confidence rules:

- MCQ correct but marked **guess** → counts as at most 3.
- MCQ wrong but marked **sure**, or a case or focused question scoring ≤ 2 marked **sure** → a **confident error**
  (misconception): step resets to 0 and a gap with source `misconception` is added.

| Mastery | Step (`intervals_days` index) |
|---|---|
| ≥ 4 | advance one |
| 2.5–3.5 | hold |
| ≤ 2 | reset to 0 |

**No topic returns sooner than three days**, whatever the step, the answer or the calibration
(with the default intervals: a miss, a confident error and a topic held at step 0 all return
after three days). The day after a round the learner still holds the feedback in short-term
memory: a re-test then is answered from the explanation just read, so it shows little about
what will be kept and adds little to it, and a topic stuck at 3/5 filled every round. `start`
applies the same rest to ledgers written before this rule (a topic tested in the last two days
is not chosen, even if its stored due date has passed); only `--allow-repeat` overrides it.

**Drill-down limit.** Coming back to a topic round after round because it was missed is limited,
so that a block stays on its theme and one weak point does not fill the rounds:

- The plan never puts a topic in a third round in a row: a topic that was in both of the last two
  recorded rounds is left out of the next one, due or not, with an open gap or not (again only
  `--allow-repeat` overrides it). It is eligible again the round after.
- In the block's theme a missed topic comes back after the three-day rest. Missed again in the
  round straight after (two rounds in a row), it waits at least seven days.
- Outside the theme a miss gets one targeted retest (its gap, after the rest). If the topic is
  not answered well then either, it waits at least seven days, and so after every further miss
  until its domain is the theme: no short returns outside the theme. When its domain becomes
  the theme (the next block, or the learner changing the theme), an open gap of a topic last
  tested under another theme is ready for a retest at once, whatever is left of that wait.

"Not answered well" is the bar a retest must clear: below 4, or overconfident, or a confident
error. A good answer is never delayed by this. Where the limit lengthened an interval, `save`
and `close` report `"drilldown_limit": true` for the topic. The theme that counts is that of
the block the round was recorded in (the session's `block`), also when the round is reflected
on later.

Self-assessment, with comfort *c* for the topic:

| Condition | Label | Effect |
|---|---|---|
| c − mastery ≥ 2 | overconfident | do not advance; back after 3 days |
| mastery − c ≥ 2 and mastery ≥ 4 | underconfident | advance, but halve the interval (never under 3 days) |
| otherwise | aligned | none |
| no rating | not_rated | none |

**What the learner sets.** A learner-set score is used as given: it replaces the examiner's
score in the topic's mastery, and no confidence rule is laid over it (no cap for a guess, no
confident error, so no misconception gap). Calibration and the Brier score still compare the
confidence with what the examiner graded. A gap the learner closes is removed with **no
retest**, not even a light one: it is the learner's call, and a retest they did not want
would undo it. The topic itself keeps the due date its score gave it, so the subject still
returns as an ordinary repeat. `override` after the close schedules the topic again from the
round's date, as `close` would have with that score (from `steps_before`; a round recorded
before 5.0 has none and is scheduled from the step the round left). It leaves the schedule
alone when the topic has been tested again since, does not re-apply the drill-down limit, and
always sets the prepared round aside (it is never content-neutral: a score moves the topic's
step and due date, a closed gap takes its retest out of the plan).

A self-reported gap caps the interval at 7 days. Comfort ratings feed `domain_self_ratings`
(rolling, weighted 2:1 toward history), which weight how often new topics from each domain are
sampled (rating 1→1.6, 2→1.3, 3→1.0, 4→0.8, 5→0.6, times blueprint weight, times emphasis,
divided by how often the domain appeared in the last ten sessions).

The rating is **corrected for overconfidence** when the weight is worked out: once a domain has
tested topics, the rating used is the lower of the stored rating and the mean current mastery of
those topics, rounded down. So a 5/5 over answers averaging 3 counts as 3 and does not reduce
the domain's share; a 5/5 over answers averaging 4.6 counts as 4. A low rating always counts as
given, and so does a rating for a domain with nothing tested yet. The stored rating stays the
learner's own, so the progress review can still compare it with performance. Reason: physicians'
self-assessment agrees poorly with measured performance, and worst where performance is weakest,
so an unchecked "comfortable" would steer questions away from exactly the domains that need them.

**Blocks.** Rounds run in blocks of 12 on one domain, the theme (`docs/adr/0003`). `block` is
the current block: `round` counts the rounds recorded in it (`save` adds one; a
reflection does not), `chosen` is `auto` or `learner` (§4.1). `blocks` keeps the finished ones. A
ledger with no `block` (new, or written before blocks) or with a finished one gets its next
block when the next round is recorded: nothing else in the ledger changes, so history, gaps and
due dates carry over. The theme is proposed without chance: each domain with at least four
blueprint topics is scored as its weight for new material (above) raised by 10% per open gap (to
50%), times how long it has been without a block (a quarter straight after its own, full again
after four others; never a theme counts in full); the highest score wins, ties by blueprint
order, and never the theme just finished. Each session entry keeps its `block` (`theme`,
`round`, `length`).

In a block the case is always on the theme, and the short questions are shared 60% theme, 25%
due repeats, 15% wildcard. The shares are met over the block, not in each round (round `n` gets
what the first `n` rounds are owed less what the earlier ones got), so three short questions are
2 theme + 1 repeat in most rounds and a wildcard takes a slot in five of the twelve. Each plan
item says which `share` it fills:

- `theme`: a theme topic that is due or has a gap ready for its retest, then an untested theme
  topic, then the theme topic tested longest ago (`reason_code: revisit`: another decision point
  of it), then the domain alone (`new_in_domain`). The last theme slot goes to an untested topic
  first when the round has nothing new yet. The case is not on the topic of the last round's
  case while the theme has another to give.
- `repeat`: the most urgent due topic or gap outside the theme, then inside it. With nothing
  waiting the slot goes to the theme.
- `wildcard`: an untested topic outside the theme, by domain weight.

Short questions on the theme share the case's domain but are still unrelated to its topic. The
plan's `block` holds `theme`, `name`, `round` (this round's number), `length`, `starts`, `mix`
and `line`, the one thing the learner is told: "Block: Gastroenterology & Hepatology, round 4 of
12". `open`, `start` and `prepare` print it too. A one-off `--domain` round ignores the
theme (`mix` is null) and still counts as a round of the block. A prepared round is used only
for the round of the block it was planned for.

### 4.1 Changing the theme

The theme is proposed; the learner decides. Three places carry it:

- **The end of a block.** `save` and `close` of a block's last round print `next_block`:
  `finished`, the proposed `theme` and `name`, its `reason`, and `line`, which goes into the
  close message word for word: "Block finished: Cardiology. Next block: Nephrology &
  Electrolytes: mean 2.4 of 5 over 3 topics tested, 1 open gap, not yet a theme. To change it,
  say "pick another" or name an area." The reason is at the level of the domain (mean mastery,
  number of open gaps, when it last was a theme) and names no topic. Nothing is written for the
  proposal: if the learner says nothing, the next round starts that block.
- **The opening line of a block's first round.** `open`/`start` give `block.reason` while
  `block.starts` is true ("New block: Nephrology & Electrolytes: … . Round 1 of 12"), so a learner
  who missed the close message can still change it before answering anything.
- **The learner's line.** "pick another" → `theme --work W --another`; an area named
  ("cardiology next", "switch to GI") → `theme --work W --set "<what they said>"`
  (`--set` takes a domain id, a name, or a part of one that fits one domain only; otherwise it
  stops and lists the domains). Publish the `files` like a settings change and send `say` ("New
  block: Gastroenterology & Hepatology: your choice. Round 1 of 12."). `theme --work W` alone
  writes nothing and prints the block, the proposal if a block has just ended, and `choices`
  (every domain, the proposal's ranking first) for "which areas are there?".

What the change does: the block the next round would have belonged to is replaced by a new block
of 12 on the new theme, at round 0, `chosen: "learner"`. At the end of a block that is simply
another theme for the block about to start. In the middle of one, the current block ends where
it is and is kept in `blocks` with the rounds it had (a block changed before its first round is
not kept); the new block starts with the next round. Nothing else in the ledger moves: history,
gaps and due dates stay, and topics of the theme left behind come back as due repeats. A theme
left mid-block counts as having had its block when the next themes are proposed. `--another`
takes the next domain of the ranking and keeps the ones turned down in `block.declined` until
the block's first round is recorded, so asking again moves on and does not come back; after the
last one it starts from the top. The learner may name a domain too small to be proposed (fewer
than four topics): it is accepted with a warning, and its rounds revisit the same topics on
other decision points. The prepared round is emptied (§8).

When to run it: between rounds. At the opening line, before any answer: run `theme`, then
`start` again on the changed ledger (the first plan is discarded; nothing was recorded). Once
the learner has answered anything, finish the round on the theme it was planned on and run
`theme` on the ledger `close` wrote; say so in one line. A change run on the ledger read at the
start of a round in progress would be lost when `save` writes that round.

The rest of this paragraph is the order within those shares, and the whole rule for a `--domain`
round. Selection (the plan): due topics first (overconfident and misconception ahead, then most overdue,
then lowest mastery), then open gaps that no item has tested since they were written and that are
at least three days old (misconception > self > transfer > graded), then new topics by domain
weight. A topic tested in the last two days is never chosen. Every chosen item whose topic has an
open gap carries `retest_gap` (`id`, `gap`, `how`): the author writes the item on that decision
point and names the gap in the item's key header (`retests`), from where it reaches the round record. Slots are filled case first, then focused questions,
then MCQs, so due topics and open gaps go to the formats that show reasoning. MCQs and focused
questions come from other domains than the case and are unrelated to it and to each other
(cross-references, shared significant words). In rounds of four or more items the last short
slot (the last MCQ, or the last focused question when there are no MCQs) is reserved for a new
topic; in smaller rounds whenever the previous session introduced nothing new
(`new_topics_per_round: 0` or `--no-new` disables this). Each focused item gets an
`aspect_hint`: the aspect tested least recently.

Open gaps: one per topic, each with an id (`G0007`; gaps from older ledgers are numbered at the
next `save`, and until then an item may name such a gap by its topic id). A new entry replaces
the old one and keeps its id, so its text must carry forward anything still unresolved. A gap
retires to `resolved` only when, in a later round, the items whose `retests` names it score ≥ 4
(after the confidence rules, so not a guess and not a confident error), the topic is not
overconfident, and no new gap is logged on the topic. A good answer on another point of the same
topic leaves the gap open and still waiting for its retest: the learner showed they know
something else, not that the missed point is fixed. A retest that falls short sets
`last_retested`; from then on the gap comes back with its topic's spacing. That holds too when
the examiner writes the gap again after the failed retest: the new text keeps the id and
`last_retested`, so a gap gets one targeted retest, not one per rewrite.

Review due: when `review_interval_days` has passed and at least three sessions were done, or
the interval plus 21 days has passed regardless. A snooze always wins.

### 4.2 Evidence depth

How far behind the recommendation the feedback on an item goes when it is answered well
(`feedback_guide.md` §4.1). Nothing is stored for it: the engine counts it from the items of
the recorded rounds (`sessions` and `previous`) each time.

- `in_a_row`: the number of items on the topic, counting back from the last round, that
  were answered well (mastery ≥ 4 as the schedule counts it, so a guessed MCQ is not; no
  misconception; a score the learner set counts as set), up to the first that was not.
- `level`: 1 `guidance` (0 in a row), 2 `studies` (1), 3 `design` (2–3), 4 `frontier` (4 or
  more).
- A focused question: at most one level beyond the level its own `aspect` of the topic has
  earned, counted the same way over the topic's focused questions on that aspect.
- An item that retests a gap, or whose topic has an open gap: level 1.
- The plan gives an item `depth` (`level`, `name`, `in_a_row`, `how`) only beyond level 1,
  with the focused question's `aspect_hint` as its aspect; `answer` gives the examiner the
  level for the topic and aspect the key header names. `config.evidence_ladder` false: neither.

## 5. Caps that keep the state small

`save`, `close` and `review` compact the state: at most 50 full sessions (older ones move to
`previous`, compact), 60 previous sessions, 8 history rows per topic, 40 resolved gaps, 6 reviews,
40 errata; gap text ≤ 400 characters, error elements ≤ 220, bias evidence ≤ 140. All-time figures
survive in `agg`. The verbatim detail is in the session documents, which are never compacted.

## 6. Commands

Every command the protocol uses takes the work folder, `--work W`, and no other path of the
store: `open` (or `start --store`) notes where the store copy is, and the rest is found by
fixed names (§6.1). A command that writes puts its files into the publish set (`W/publish/`)
and prints the whole set as `files` (`as`: the store path, `path`: the local file, in write
order with the ledger last) and `publish`, the path of the manifest `W/publish.json`.

| Command | Use |
|---|---|
| `open --work W --store DIR [--version V] [--prefs J] [--reread]` | Set up the work folder for any job from `DIR`, the local copy of the store as just read: the store's layout (`DIR/data/state.json`, `DIR/data/page.json`, `DIR/data/prepared.json`, `DIR/index.html`, `DIR/data/sessions/<id>.json`) or the files side by side (`DIR/state.json`, …). Writes `W/work.json` and an empty manifest carrying `V`, the store version read. If `W` holds an earlier job (answers, a publish set, drafts of a next round), its files are first moved to `W/earlier/<n>/` (`earlier_set_aside`). Prints neutral status: `gen`, `next_id`, counts, `review_due`, `testing`, the block; never a topic. `--reread`: the same job on a fresh read after a refused publish (`store.md` §4.1): the job's own files stay, the publish set is dropped, and the job's commands are run again. |
| `start --work W [--store DIR [--version V]] [--prefs J] [plan options] [--no-prepared]` | Start a round. With `--store` it does what `open` does first; without, it continues the job that is open (a settings change or a late reflection earlier in the same conversation), from the ledger that job wrote. The plan is written to `W/plan.json`. Prints the neutral status with the plan's counts (MCQs, focused, case, `estimated_minutes`, and `estimate_rounds` when the estimate is at the learner's own pace, §6.2) under `plan`, plus `helpers`, `prepare_ahead` and `speed_settings_new`. No topic names. With a plan it also prints what the first message needs, so that nothing else is run or read before it: `opening` (the opening line, word for word: the mix, the minutes, "(based on your last N rounds)" once rounds are timed, the block's line, with its reason when a block starts, and the last saved session) and `started_at` (when the round's clock started, §6.2; nothing to copy). `--prefs` is the page's `cme/prefs` document (§7.1); `page_settings_applied` says when it changed the mix or brought a new paragraph (which `start` writes to the ledger at once, into the publish set; §7.1), `pitch` holds the learner's two paragraphs for the examiner and `labels_needed` the display labels still to derive (§1), and `round_mix` says when a prepared round was written for another mix than the one in force (§8). The prepared round is read from the store copy (§8): when it still fits, `prepared.used` is true, `present` holds the first part's text to send (`prepared.present_block` says which) and the drafted files (`prepared.ready`: `sealed_questions.md`, `sealed_case.md`, `kit_questions.md`, `kit_case.md`, `evidence_questions.md`, `evidence_case.md`) are written into the work folder, with `prepared.unchecked` naming the sealed files that came without an evidence file (start a checker for each); otherwise `prepared.why` says why not and the round is planned as usual. Plan options, for this round only: `--mcqs N`, `--focused N`, `--no-case`, `--domain CODE`, `--no-new`, `--allow-repeat`, `--no-drill`. |
| `present --work W --block questions\|case\|bank` | Print only the text the learner is to see from the sealed files in `W` (one `present` block, or the case's results bank), so it can be sent without opening the keys. For the first part of a round written now it also notes that the part went out (§6.2). |
| `answer --work W --part questions\|case\|final\|notes\|reflection [--file F \| --text T]` | Append what the learner answered for one part to `W/answers.md`, exactly as given (default: standard input). Earlier parts are never rewritten; the same text for the same part is added once; a second message for a part is added after the first. Prints the part names filed so far, never the text. With a part that completes its answers (`questions`; `final`; `case` for a one-step case) it also prints `depth`: the evidence depth of each of that part's items by key id (`level` 1–4, `name`, `in_a_row`; §4.2), read from the key headers and the ledger, for the feedback about to be written. No `depth` with `evidence_ladder` false. It also notes when it ran, as the time the learner's message arrived (§6.2): run it first when a message arrives. |
| `sent --work W --part questions\|questions_feedback\|case\|stage2\|feedback\|close [--at T]` | Not part of a normal round. Notes when a message went out, where the engine cannot tell (§6.2): no file was written as sent, or it was written late. |
| `save --work W` | First save after the final feedback: the round is recorded in the ledger, the session document is written (part A assembled in the order of the round from the sealed `present` blocks, Stage 2 as sent, the answers, the questions' feedback and the final feedback), with the page file (§7) and an emptied `data/prepared.json`. Everything is found by its fixed name (§6.1); the page settings given at the start are applied so the mix is kept in the ledger. Prints per-topic next due, warnings, `errata_to_log`, and `files`. If the learner's `index.html` is older than the skill's template, the new one joins the publish set (`page_upgraded`). It starts from the ledger as it was before this round (a settings change made earlier in the same job is kept), so it can be run again with the same result. Records the time measured so far (`minutes`, `timing`; §6.2). |
| `close --work W [--reflection J] [--session ID]` | Second save: the reflection is applied and part B goes into the session document, with the page file. It continues from the current ledger: the one `save` wrote in this job, or, for a reflection given at a later session, the ledger as read; the session document then comes from the store copy (`data/sessions/<id>.json`), and the command stops if it was not read. The reflection JSON is `W/reflection.json` unless given inline. Can be run again after a correction to `B.md`. Completes the round's measured time (the reading of the final feedback, up to the reflection) and prints `time_hint` once five rounds are timed (§6.2): one line of the closing message. |
| `override --work W [--scores J] [--close-gaps J] [--session ID]` | After the close: a score the learner sets themselves and a gap closed at the learner's request (the entries of `learner_scores` and `learner_closed_gaps`, §3). Writes the ledger, the session document (`learner_changes`, a "Set by the learner" addendum) and the page file into the publish set. Refused while the round is unreflected (use the reflection JSON) and, for scores, for a round from before the last review |
| `addendum --work W --md ADD.md [--session ID]` | Append later discussion to a session document (default: the last session; the document comes from the publish set or the store copy). |
| `prepare --work W [--if-needed] [--allow-unreflected]` | Plan the next round (as of tomorrow) from the current ledger, into `W/next/plan.json`. Prints counts only, or `"prepare": false` with the reason (setting off, reflection pending, or — with `--if-needed` — a usable round is already prepared in the store). `--allow-unreflected` plans although the last session has no reflection yet (the scheduled task uses it). A paragraph the learner wrote on the page (in the `--prefs` given to `open`) is written to the ledger first, into the publish set, and reported as `page_settings_applied` with the `files` (§7.1); a round prepared for the old words does not count as usable. |
| `finish-prepare --work W [--revised] [--no-evidence]` | After the checkers: finish preparing the round planned in `W/next/plan.json` and drafted in `W/next`. First lints it against the rulebook (`standards.md`, "The lint"). **Blocking**: the key headers of the sealed files against the plan, as `keys --plan` checks them, and the kits and their sections (rule 8); a problem is an error (exit 2, nothing stashed) that lists every one by file, key, field or section, whatever the evidence says and also with `--no-evidence` or `--revised`. **Judgement calls** (an abbreviation that looks undefined, rule 5; time anchors that look mixed, rule 6): counted in `lint` (`abbreviations`, `time_anchors`, `where` by file, `details`: the path of `W/next/lint.md`, where the findings are written for the author and never printed). Then reads the last two lines of each evidence file (`Checked: <date>, <n> claims, <n> not verified` and `Keys contradicted: <n>`, `evidence_check.md` §4) for every sealed part the round has, and prints counts and file names only: `evidence` (keys contradicted per file), `contradicted` (the total), `not_verified` (per file: `claims`, `not_verified`, and `untried`, the "not verified" blocks without a `Tried:` line; `not_verified` is the larger of the line's number and the blocks so marked), `not_verified_total`, `claims_total`, `recheck` (the evidence files that go back to their checker: more than a third of the file's claims not verified, or any `untried`), `revise` and `stashed`. Nothing contradicted, no judgement call and no file to recheck → the round is packed and joins the publish set as `data/prepared.json` (§8) in the same command. Otherwise → `"stashed": false` and a `next` line: the checker retries the files in `recheck` once, then the author revises once (`"revise": true` when a key is contradicted or the lint made a judgement call; after a retry it also carries what was confirmed into the kits), and the command is run again with `--revised`, which stashes; what is still found is then listed under `warnings` ("accepted after one revision: …", "accepted after one retry: … n of m claims not verified"). An evidence file that is missing, empty or without either count line in that form (also one that counts no claims, or more not verified than claims) is an error (exit 2, nothing stashed), never a count of zero. `--no-evidence` is for a session that runs no checker: the round is stashed without evidence files, so the sources are checked at the session; the lint runs all the same. The first part's sealed file must be there; a missing case is a warning (it is then written at the next session). |
| `keys DIR\|SEALED… [--plan PLAN]` | The author's check before finishing: the key headers of sealed files (`standards.md` rule 9) and, for a folder, the kits' sections (rule 8; a kit not written yet is not a problem here). Prints the key ids each file has and `problems`, naming file, key, field and section only, never a topic or a value; with `--plan`, also whether the number of headers of each type matches the plan's counts. `review` lists the lint's judgement calls as counts per file; the findings go to `lint.md` in the folder (`details`). Exit code 1 when there is a problem; `review` alone does not fail it. |
| `key-table` | Prints the key-header table of `standards.md` rule 9 from the engine's `KEY_*` definitions; a test fails when the rulebook's copy differs. |
| `verify --work W --store CHECK` | Testing mode: compare the publish set with the store read again into `CHECK`; the result is also written to `W/verify.json`. |
| `testing-note --work W --feedback J` | Testing mode: the learner's quick feedback and `W/verify.json`, as `data/testing/<id>.json` for this job's round. |
| `stats --work W` | Review figures: period, previous period, all time; gaps, calibration, teaching points unchecked, blind spots; `timing` (medians of the last timed rounds: minutes, answering, waiting, reading; the pace; the hint). Writes nothing. |
| `review --work W --review REVIEW.json` | Record a review; closes the period. |
| `review-doc --work W --md REPORT.md [--headline H] [--date D] [--title T]` | A review report as `data/reviews/<date>.json`, listed in the page file. |
| `snooze --work W [--days 7]` | Postpone a due review. Keeps the prepared round. |
| `settings --work W [--config J] [--profile J] [--blueprint FILE]` | Change settings: the changed ledger, the page file and the page if it is out of date go into the publish set, with an emptied `data/prepared.json` when the change can alter a round; `prepared` says whether the prepared round was kept and why (§8). A change to `mcqs`, `focused` or `case` is checked (at least one item) and supersedes any older page setting; a refused change writes nothing. Prints `round`: the mix in force in words, its `estimated_minutes`, and once rounds are timed `basis` ("based on your last N rounds") and `time_hint` (§6.2). `--profile '{"journey": "…"}'` or `'{"aim": "…"}'` stores a new paragraph in the learner's words, dates it and clears its label unless the same change gives one; `'{"journey_label": "…", "aim_tags": […]}'` sets the display labels (from their fixed lists, §1) and keeps the prepared round. With a paragraph or a label in the change it prints `profile` (the two paragraphs and their labels), and `labels_needed` while a label is still to derive. |
| `theme --work W [--set DOMAIN \| --another]` | The learner changes the theme of the block (§4.1): `--set` a domain by id or name, `--another` the next proposal. Prints `block`, `was`, `say` and, like `settings`, the `files` to publish. Alone: the block, the proposal and the domains to choose from; writes nothing. |
| `init --work W --profile J --config J --blueprint FILE [--start-over]` | Setup: the first ledger, its page file and the page, into the publish set. Prints `round` (the mix in words and its `estimated_minutes`) to confirm the mix with, and `labels_needed` when a paragraph came without its label. A profile given in the old fields (`role`, `goals`, `notes`) is folded into the paragraphs (§1). `W` needs no store yet. In a work folder opened on a store that already holds a ledger it stops unless `--start-over` is given. |

Maintenance tools, outside the protocol; they take their own files and folders:

| Command | Use |
|---|---|
| `import EXPORT.json --out-dir D` | A page export into the file layout (`store.md` §6, a damaged ledger). |
| `rebuild-page ROOT` | Rebuild `ROOT/data/page.json` (§7) from the session and review files and the ledger of a folder in the store's layout; `reindex` is its old name and still works. |
| `blueprint-md FILE --out BP.json` | Convert a Markdown blueprint. |
| `validate STATE` (or `validate --work W`) | Structural check. |

Add `--today YYYY-MM-DD` (before the command) to fix the date. No command writes over a file
it read: the store copy stays as it was read, so a failed step can be run again.

### 6.1 The work folder

One job is worked on in one scratch folder, and every file has a fixed name there:

| File | Written by | Read by |
|---|---|---|
| `work.json` | `open`, `start`: the store copy, the ledger as read, the store version, the session ID, the page settings | every command |
| `plan.json` | `start` | whoever writes the items |
| `sealed_questions.md`, `sealed_case.md`, `kit_*.md`, `evidence_*.md` | the author and the checker, or `start` from a prepared round | `present`, the examiner once a part is answered, `save` (the `present` blocks) |
| `answers.md` | `answer`, one block per part (`<!-- answers: questions -->` … `<!-- /answers -->`) | `save` (questions, case, final, notes), `close` (reflection) |
| `feedback_questions.md`, `stage2.md`, `feedback.md` | the examiner: each message exactly as sent | `save` |
| `round.json` (§2) | the examiner: the grading, each item naming its key | `save` |
| `record.json` (§2), `A.md` | `save`: the round record, built from the key headers and `round.json`; part A as assembled | the simulation's checks; anyone who wants to see what was recorded |
| `reflection.json` (§3), `B.md` (`session_log.md` §3) | the examiner | `close` |
| `next/` | `prepare` (`plan.json`), the author and the checker (the next round's files), `finish-prepare` (`lint.md`: what the lint found, for the author) | `finish-prepare`; the author for `lint.md` |
| `publish/` | every command that writes: the newest version of each store file this job changed, at its store path | the commands that follow (the current ledger is `publish/data/state.json`), `verify`, whoever publishes |
| `publish.json` | every command that writes: `{"version": <store version read>, "files": [{"as", "path"}, …]}`, in write order | whoever publishes |
| `verify.json` | `verify` | `testing-note` |
| `times.json` | `start`, `present`, `answer`, `sent`, `save`, `close`: when each step of the round happened (§6.2) | `save`, `close` |
| `before_save.json`, `before_close.json` | `save`, `close`: the ledger each started from, so that either can be run again | `save`, `close` |
| `earlier/<n>/` | `open`, `start`: the files of an earlier job in the same folder, set aside | nobody |

The **current ledger** of a job is the one in the publish set, or the ledger as read while
nothing has been written. Any other store file (the page file, the page, a session document, the
prepared round) is looked up in the publish set first, then in the store copy. The write order
of the publish set is: session, review and testing files, then `data/page.json`, `index.html`,
`data/prepared.json`, and `data/state.json` last.

A `<!-- present: stage2 -->` block in a sealed file is used when there is no `stage2.md`.

### 6.2 The round's clock, the learner's pace and the hint

**Nobody types a time.** The commands a round already runs note when they ran, in
`times.json`, and `save` and `close` compute the round's time from that:

| Stamp | Set by | Means |
|---|---|---|
| `start` | `start` | the learner asked for a round |
| `sent:questions` (or `sent:case`) | `start` with a prepared round; else `present` of the first part | the first part went out |
| `answer:questions`, `answer:case`, `answer:final`, `answer:reflection` | `answer --part …` | a message from the learner arrived (so `answer` runs first in a turn) |
| `sent:questions_feedback`, `sent:stage2`, `sent:feedback` | the next command, from the time `feedback_questions.md`, `stage2.md`, `feedback.md` was written (so each is written straight after sending) | that message went out |
| `save`, `close` | `save`, `close` | the final feedback was filed; the reflection arrived |

Every one of these commands takes `--at <ISO time>` for another time than now (a step filed
late, tests); with `--at` the files' own times are not used, and `sent --part … --at …` gives
them. A command run again keeps its first time.

From the stamps in time order: after a message **arrived**, the time until the next one goes
out is `waiting`; after a message **went out**, the time until the next step is the learner's:
`reading` after the final feedback, `answering` after anything else. The short questions'
feedback and the case go out together, so the time after that message is answering, less the
time its words take to read (200 words a minute, at most half of it), which is reading. Any
stretch between two stamps longer than 15 minutes counts as 15 and the rest is `idle_cut`
(nothing tells a long answer from a break, so a long stretch is neither dropped nor counted
whole). The round ends when the reflection arrives. `minutes` is answering + waiting + reading.
A round in which no `answer` was filed as it went has no `timing`.

**Pace.** A round is *timed* when it has `timing` and at least 3 minutes. Minutes are measured
per round, not per item, so they are not shared out among item types: each timed round gives
one number, its minutes divided by what the defaults (`MINUTES_PER`: 5 per MCQ, 10 per focused
question, 25 for an unfolding case, 15 for a one-step one) give for the items it had, kept
between 0.25 and 4. The learner's pace is the median of that number over their last 10 timed
rounds. Every estimate (the plan's `estimated_minutes`, the page's `round.minutes` and
`minutes_per`) is the default times `1 + w × (pace − 1)` with `w = timed rounds / 10`, at most
1: the defaults before any timed round, the learner's own pace alone from 10 timed rounds.
Wherever an estimate is shown with `w > 0` it says "based on your last N rounds".

**Hint.** From 5 timed rounds, `close` prints `time_hint` and the page file carries it: "Your
rounds take a median of 56 min against your budget of 30; dropping 3 MCQs would save about 21
min." The median is of the last 10 timed rounds, the budget is `config.session_minutes`. The
change named is the single one to the mix in force (dropping one or more MCQs, one or more
focused questions, the case, or a one-step case instead of an unfolding one) after which a
round, at the learner's own pace, comes nearest the budget; at least one item always stays.
Within budget the hint says so and names nothing.

## 7. The page: its file (`data/page.json`) and its settings (`cme/prefs`)

The page renders one file, the **page file**, which `cme.py` writes from the ledger with every
command that writes the ledger (`save`, `close`, `override`, `settings`, `theme`, `review`,
`snooze`, `init`) and with `review-doc`. It holds exactly what the page may show, so the
blinding of the page is decided in `cme.py` (`page_doc`) and tested there: never an open gap,
a topic's due date, a topic not yet tested, an active drill, the reason for a theme or
anything of the prepared round. The page reads nothing else of the store except the session
and review documents the learner opens, and the ledger when the learner exports.

```json
{"schema": 1, "page_version": "5.4.0", "gen": 14, "updated": "2026-11-20",
 "who": {"name": null, "role": "attending", "specialty": "Internal/hospital medicine", "subspecialty": null, "practice": []},
 "totals": {"topics": 9, "mean_mastery": 3.8, "since": "2026-10-01", "sessions": 4, "mean_score": 3.6},
 "sessions": [{"id": "S0004", "date": "2026-11-20", "title": "…", "summary": "…", "tags": [], "topics": ["GI-06"],
               "score": 3.5, "minutes": 38, "format": "unfolding", "drill": null, "reflected": true}],
 "topics": [{"id": "GI-06", "label": "…", "mastery": 4, "last": "2026-11-20", "calibration": "aligned"}],
 "round": {"mix": {"mcqs": 0, "focused": 1, "case": true}, "set_at": "2026-10-08T09:12:00Z", "minutes": 35,
           "minutes_per": {"mcq": 5, "focused": 10, "case": 25}, "limits": {"mcqs": [0, 10], "focused": [0, 6]},
           "timed_rounds": 0, "time_hint": null},
 "block": {"theme": "CARD", "name": "Cardiology", "done": 4, "length": 12},
 "reviews": [{"date": "2026-11-01", "title": "…", "headline": "…"}], "next_review": "2026-12-13",
 "library": [{"session": "S0004", "date": "2026-11-20", "kind": "reading", "topic": "GI-06", "label": "…",
              "title": "…", "link": "https://…", "minutes": 8, "section": "section 9 and its table"},
             {"session": "S0004", "date": "2026-11-20", "kind": "listening", "topic": "GI-06", "label": "…",
              "title": "…", "link": "https://open.spotify.com/episode/…", "minutes": 52, "show": "…"}],
 "settings": {"session_length": 35, "per_week": 3, "region": "Iceland/Europe", "units": {"labs": "SI", "gases": "mmHg"},
              "case_style": "unfolding", "order": "mcqs_first", "feedback": "detailed", "coding_line": true,
              "review_every_days": 42, "reminders": false, "emphasis": {}, "self_ratings": {},
              "level": {"label": "attending", "text": "Hospitalist for eight years; …"},
              "aim": {"tags": ["keep up to date"], "text": "Stay current, and …"}}}
```

- `sessions` (newest first) and `reviews` list the past; a session's `url` is there when its
  transcript is kept elsewhere. The ledger drops old sessions (§5), so these two lists are
  carried on from the page file as it was read, and the ledger is the authority on `score`,
  `minutes` and `reflected` for the sessions it still holds. A page file that is missing or
  unreadable is built from the ledger alone (`store.md` §6; `rebuild-page` reads the session
  files); a store from before 5.1 has `data/index.json`, whose lists are taken over once.
- `topics`: only topics already tested, most recently tested first, with the result and the
  date of the last test. A topic that has a gap but was never tested is not listed.
- `round`: the mix in force and when it was set (`set_at` is `config.round_set_at`, the `base`
  of a page setting, below), the estimate for it (`minutes`), the minutes one more item costs
  (`minutes_per`, the case at the format the next round's case takes) and the limits of the
  steppers. The estimates are `MINUTES_PER` in `cme.py`: 5 minutes per MCQ, 10 per focused
  question, 25 for an unfolding case and 15 for a one-step one, feedback included, moved to
  the learner's own pace as their rounds are timed (§6.2): `timed_rounds` says how many the
  figures rest on (the page then adds "based on your last N rounds"), and `time_hint` is the
  sentence on their measured time against their budget, from five timed rounds. The page
  has no figures of its own.
- `block`: the theme (visible by ADR 0003) and how many of its rounds are done; `totals.since`
  and `totals.sessions` are the current review period's; `next_review` is when the next
  progress review is due.
- `settings.level` (`{"label", "text"}`) and `settings.aim` (`{"tags", "text"}`): where the
  learner is and is aiming, the paragraph in their own words with the stage label (null until
  derived) or the goal tags derived from it; each is null while the paragraph is empty.
  `who.role` is the stage label (an old `role` until there is one). Nothing else of the
  profile's paragraphs is in the file.
- `library`: what the page's "Reading & listening" view lists, the `reading` pointers and
  `listening` picks of saved session documents (§2), newest session first and in the order
  the feedback gave them: the session and its date, the `kind`, the topic with its label, the
  title, the link, the minutes, and the `section` (reading) or the `show` (listening). The
  reasons stay in the session document. It is carried on from the page file like `sessions`
  (`rebuild-page` reads it from the session files) and holds the last 100 entries. Nothing
  in it comes from the plan, a prepared round or the gaps: only from sessions already saved.
  A page file from before 5.4 has no `library`, and the view says so in one line. Whether an
  entry is done is kept by the page in the viewer's own browser, never in the store.

The names in the page file are the page's own, not the ledger's: the page knows no ledger
field. `schema` changes when a page would misread the file; `page_version` is the
`PAGE_VERSION` of the engine that wrote it.

### 7.1 Page settings (`cme/prefs`)

The page's Settings tab lets the learner switch MCQs, focused questions and the case on or off
and set the counts, and rewrite either of their two paragraphs (an "Update" box under each,
with the open question of setup). The page cannot rewrite the ledger, so it writes one small
document of its own; every part is optional, and saving one part keeps the others:

```json
{"round": {"mcqs": 2, "focused": 1, "case": true}, "base": "2026-10-08T09:12:00Z", "updated": "2026-11-06T21:40:12.512Z",
 "journey": {"text": "I started as a cardiology fellow in September …", "updated": "2026-11-07T07:02:41.090Z"},
 "aim": {"text": "Pass the European exam in May.", "updated": "2026-11-07T07:03:55.412Z"}}
```

**The round mix** is `round`, `base` and the top-level `updated`.

`base` is the ledger's `config.round_set_at` that the page saw (`round.set_at` in the page file). The learner's latest explicit
choice wins. `start` and `save` apply the document (and `prepare` plans with it, without
writing it to the ledger):

- when `base` still equals `round_set_at`: nothing has set the mix since the page saw it;
- when it does not (the mix was set in a chat, or by an earlier document, after the page
  loaded the ledger): only if `updated` is a later time than `round_set_at`. An older document
  is ignored without a word, as is one whose `updated` is not a time; the page then shows the
  ledger's mix too.

Applying sets `round_set_at` to `updated`, so a document is applied once (`updated` equal to
`round_set_at` means it has been), and a later change made in a chat (which sets a new
`round_set_at`) wins over an older page setting. An invalid document is ignored with a
warning, never fatal. The page shows a saved setting as "applies from your next round" until a
round has applied it. What happens to a round prepared ahead for another mix is in §8.

**The paragraphs** are `journey` and `aim`, each `{"text", "updated"}`: where you are and
where you're aiming, as the learner wrote them on the page. Each goes by its own `updated`
against the ledger's `journey_set_at` / `aim_set_at`: it is applied when it is the later
time (or the ledger's paragraph was never dated), so it is applied once, and a paragraph
written later in a chat wins over an older page document. `start` and `prepare` apply it
and, unlike the mix, write it to the ledger at once (into the publish set, with the page
file and an emptied prepared round): the learner's words are stored as they are (trimmed;
at most 4,000 characters), the paragraph is dated `updated`, and its label is cleared for
the assistant to derive again (`labels_needed`). Both report it as `page_settings_applied`
(`{"journey": "updated"}`, beside any mix change), `start` does not use the round prepared
for the old words (`prepared.why`: "where you are changed on the page") and says so at the
end of `opening`; `prepare` then writes the next round for the new words, so the following
`start` takes it. `save` applies a paragraph too if no `start` did. Text that is the same as
the ledger's changes nothing; a paragraph without text or without a time in `updated` is
ignored with a warning. The page shows a saved paragraph with "From your next round" in
place of its labels until the page file carries it.

## 8. The prepared round (`data/prepared.json`)

```json
{"v": 2, "gen": 23, "made": "2026-11-20", "session_id": "S0023",
 "counts": {"mcqs": 2, "focused": 1, "case": 1},
 "has": ["questions", "case", "kit_questions", "kit_case"], "payload": "<compressed, base64>"}
```

Written by `finish-prepare` after a close; `payload` holds the next round's plan and everything
written for it: the sealed short questions and the sealed case (keys, results bank,
verification lists, `present` blocks), the two feedback kits and the two evidence files from
the check, packed so that nobody reads
them by accident: they are in the learner's own store. `{"v": 1, "empty": true}` means
there is none, and the file always exists. This section is the one place that says when a
prepared round is kept and when it is set aside; other files point here.

**Who empties it.** Every command that changes what the next round would contain writes the
empty document: `save` (a round was recorded), `review`, `theme`, `init`, and `settings` when it
changes a setting of the second group below. `close` (the reflection) normally comes before
the next round is prepared and leaves the file alone; a reflection that arrives after a round
was prepared moves the generation (below), so that round is no longer used.

**Settings: two groups.** `settings` prints `prepared`: `{"kept": true, "why": …}` or
`{"kept": false, "changed": […], "why": …}`, where `changed` names the settings that set it
aside. What counts is the values that changed, not the keys that were sent; `listening` and
`podcast_sources` count as they take effect (on, and no shows named, in a ledger without them).

| Group | Settings | Prepared round |
|---|---|---|
| Cannot change what a round contains | config: `testing`, `reminders`, `prepare_task`, `prepare_ahead`, `helpers`, `show_coding`, `target_sessions_per_week`, `review_interval_days` (and `round_set_at` on its own); profile: `display_name`, `onboarded_at`, the display labels `journey_label` and `aim_tags` (and `journey_set_at`, `aim_set_at` on their own). Also `snooze`. | kept, untouched; the next `start` uses it and puts today's `testing`, `helpers`, `prepare_ahead` and `show_coding` into its plan |
| Can change the plan, the items or the feedback notes | everything else, including any setting not listed above: the mix (`mcqs`, `focused`, `case`), `session_minutes`, `case_format`, `item_order`, `feedback_depth`, `evidence_ladder`, `intervals_days`, `new_topics_per_round`, `lab_units`, `blood_gas_units`, `guideline_region`, `resource_preferences`, `listening`; every other profile field (the paragraphs `journey` and `aim`, from a chat or from the page; `specialty`, `subspecialty`, `practice_setting`, `goals`, `strengths`, `weaknesses`, `domain_self_ratings`, `domain_emphasis`, `notes`, `podcast_sources`); a blueprint that differs from the current one | set aside (emptied), and the output says which setting did it |

**The generation it is tied to.** `gen` counts every write of the ledger, also a change of the
first group. A prepared round is therefore tied to `content_gen`: the generation of the last
change that could alter a round. The ledger holds `content_gen` only while it differs from
`gen` (after changes of the first group); without it, it is `gen`. Every command counts a write
through one function (`bump_gen`), which either moves both or leaves `content_gen` behind, so
the prepared round's `gen` is compared with `content_gen` and nothing has to be restamped.

`start` uses it only when all of this holds, and otherwise plans afresh (`--no-prepared` leaves
it alone for one round):

- the round mix in force is the mix it was written for (see below), and no one-off option
  (`--mcqs`, `--focused`, `--no-case`, `--domain`, `--no-new`, …) was given;
- the ledger is the one it was made from (`content_gen` and `next_id` unchanged: no round,
  review, theme change or settings change of the second group since);
- it is for this round of the block (§4);
- it is at most 30 days old;
- none of its topics was tested today.

**Page mix against prepared mix.** The mix in force is the ledger's after the page's document
(§7.1) has been applied, whether in this `start` or earlier. When the prepared round was written
for another mix, the learner's latest choice wins: the prepared round is set aside
(`prepared.why`: "the round mix changed"), the round is planned for the mix in force, and
`start` prints `round_mix`: `used`, `prepared` (the two mixes), `source` (`page` when this
`start` applied the page's mix, else `settings`) and `say`, the sentence for the opening line.
`prepare` plans with a page mix that is waiting, so a round prepared after the learner changed
the page is written for it.

The plan is made as of the day after the close, so everything in it is due by any later day.
Whatever part a prepared round lacks (`prepared.ready` lists what it has) is written at the
session, from the same plan, while the learner answers the part that is there.


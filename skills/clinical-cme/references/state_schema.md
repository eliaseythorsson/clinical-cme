# State, round JSON, reflection JSON and spacing rules

The ledger (`data/state.json`) is the learner's scheduling
memory: one JSON document, read to a file and written from a file (`store.md` §4). Change it only through `scripts/cme.py`.

## 1. State layout (schema 4)

```json
{
  "schema": 4, "gen": 21, "created": "2026-10-08", "updated": "2026-10-26", "next_id": "S0022",
  "profile": {"display_name": "Dr A", "role": "Hospitalist attending", "specialty": "Internal medicine",
              "subspecialty": null, "practice_setting": ["University hospital, inpatient"],
              "goals": ["…"], "strengths": ["…"], "weaknesses": ["…"],
              "domain_self_ratings": {"CARD": 3.8}, "domain_emphasis": {"GEN": 1.5},
              "notes": "free text", "onboarded_at": "2026-10-08"},
  "config": {"session_minutes": 20, "mcqs": 3, "focused": 0, "case": true, "case_format": "unfolding",
             "round_set_at": "2026-10-08T09:12:00Z",
             "feedback_depth": "detailed", "target_sessions_per_week": 3, "review_interval_days": 42,
             "intervals_days": [1, 3, 7, 16, 35, 90], "new_topics_per_round": 1,
             "lab_units": "SI", "blood_gas_units": "mmHg", "guideline_region": "Iceland/Europe",
             "item_order": "mcqs_first", "helpers": true, "prepare_ahead": true,
             "show_coding": true, "reminders": false,
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

Round mix: `mcqs` (0–10), `focused` (0–6) and `case` (true/false); at least one item.
`round_set_at` marks the last change of the mix (setup, a chat `settings` change, or a page
setting applied). The learner can also change the mix on their page; the page stores it as its
own settings document, `cme/prefs` (§7), and the next round applies it.

A session entry:

```json
{"id": "S0021", "date": "2026-10-26", "started_at": "…", "ended_at": "…", "minutes": 26, "reading_minutes": 10,
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
(`author.md` §3) and carries the score, the confidence and the coding. `save` fills in
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
  "pending_errata_logged": "all"
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
  not fail at `save`.

The round record, as `save` writes it to `record.json`. A
`round.json` written out in full like this, with no `key` on its items, is recorded as it is:

```json
{
  "date": "2026-10-26", "started_at": "2026-10-26T08:00:00+00:00", "ended_at": "2026-10-26T08:26:00+00:00",
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
empties the prepared round.

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
other decision points. The prepared round is emptied, as for any settings change.

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
| `open --work W --store DIR [--version V] [--prefs J] [--reread]` | Set up the work folder for any job from `DIR`, the local copy of the store as just read: the store's layout (`DIR/data/state.json`, `DIR/data/index.json`, `DIR/data/prepared.json`, `DIR/index.html`, `DIR/data/sessions/<id>.json`) or the files side by side (`DIR/state.json`, …). Writes `W/work.json` and an empty manifest carrying `V`, the store version read. If `W` holds an earlier job (answers, a publish set, drafts of a next round), its files are first moved to `W/earlier/<n>/` (`earlier_set_aside`). Prints neutral status: `gen`, `next_id`, counts, `review_due`, `testing`, the block; never a topic. `--reread`: the same job on a fresh read after a refused publish (`store.md` §4.1): the job's own files stay, the publish set is dropped, and the job's commands are run again. |
| `start --work W [--store DIR [--version V]] [--prefs J] [plan options] [--no-prepared]` | Start a round. With `--store` it does what `open` does first; without, it continues the job that is open (a settings change or a late reflection earlier in the same conversation), from the ledger that job wrote. The plan is written to `W/plan.json`. Prints the neutral status with the plan's counts (MCQs, focused, case, `estimated_minutes`) under `plan`, plus `helpers`, `prepare_ahead` and `speed_settings_new`. No topic names. `--prefs` is the page's `cme/prefs` document (§7); `page_settings_applied` says when it changed the mix. The prepared round is read from the store copy (§8): when it still fits, `prepared.used` is true, `present` holds the first part's text to send (`prepared.present_block` says which) and the drafted files (`prepared.ready`: `sealed_questions.md`, `sealed_case.md`, `kit_questions.md`, `kit_case.md`, `evidence_questions.md`, `evidence_case.md`) are written into the work folder; otherwise `prepared.why` says why not and the round is planned as usual. Plan options, for this round only: `--mcqs N`, `--focused N`, `--no-case`, `--domain CODE`, `--no-new`, `--allow-repeat`, `--no-drill`. |
| `present --work W --block questions\|case\|bank` | Print only the text the learner is to see from the sealed files in `W` (one `present` block, or the case's results bank), so it can be sent without opening the keys. |
| `answer --work W --part questions\|case\|final\|notes\|reflection [--file F \| --text T]` | Append what the learner answered for one part to `W/answers.md`, exactly as given (default: standard input). Earlier parts are never rewritten; the same text for the same part is added once; a second message for a part is added after the first. Prints the part names filed so far, never the text. |
| `save --work W` | First save after the final feedback: the round is recorded in the ledger, the session document is written (part A assembled in the order of the round from the sealed `present` blocks, Stage 2 as sent, the answers, the questions' feedback and the final feedback), with the index and an emptied `data/prepared.json`. Everything is found by its fixed name (§6.1); the page settings given at the start are applied so the mix is kept in the ledger. Prints per-topic next due, warnings, `errata_to_log`, and `files`. If the learner's `index.html` is older than the skill's template, the new one joins the publish set (`page_upgraded`). It starts from the ledger as it was before this round (a settings change made earlier in the same job is kept), so it can be run again with the same result. |
| `close --work W [--reflection J] [--session ID]` | Second save: the reflection is applied and part B goes into the session document, with the index. It continues from the current ledger: the one `save` wrote in this job, or, for a reflection given at a later session, the ledger as read; the session document then comes from the store copy (`data/sessions/<id>.json`), and the command stops if it was not read. The reflection JSON is `W/reflection.json` unless given inline. Can be run again after a correction to `B.md`. |
| `override --work W [--scores J] [--close-gaps J] [--session ID]` | After the close: a score the learner sets themselves and a gap closed at the learner's request (the entries of `learner_scores` and `learner_closed_gaps`, §3). Writes the ledger, the session document (`learner_changes`, a "Set by the learner" addendum) and the index into the publish set. Refused while the round is unreflected (use the reflection JSON) and, for scores, for a round from before the last review |
| `addendum --work W --md ADD.md [--session ID]` | Append later discussion to a session document (default: the last session; the document comes from the publish set or the store copy). |
| `prepare --work W [--if-needed] [--allow-unreflected]` | Plan the next round (as of tomorrow) from the current ledger, into `W/next/plan.json`. Prints counts only, or `"prepare": false` with the reason (setting off, reflection pending, or — with `--if-needed` — a usable round is already prepared in the store). `--allow-unreflected` plans although the last session has no reflection yet (the scheduled task uses it). |
| `finish-prepare --work W [--revised] [--no-evidence]` | After the checkers: finish preparing the round planned in `W/next/plan.json` and drafted in `W/next`. First checks the key headers of the sealed files against the plan, as `keys --plan` does: a missing or malformed header is an error (exit 2, nothing stashed) that lists every problem by file, key and field, whatever the evidence says and also with `--no-evidence` or `--revised`. Then reads the last line of each evidence file (`Keys contradicted: <n>`, `evidence_check.md` §3) for every sealed part the round has, and prints counts and file names only: `evidence` (per file), `contradicted` (the total), `revise` and `stashed`. Nothing contradicted → the round is packed and joins the publish set as `data/prepared.json` (§8) in the same command. Something contradicted → `"revise": true`, `"stashed": false`: the author revises, and the command is run again with `--revised`, which stashes. An evidence file that is missing, empty or without its count line is an error (exit 2, nothing stashed), never a count of zero. `--no-evidence` is for a session that runs no checker: the round is stashed without evidence files, so the sources are checked at the session. The first part's sealed file must be there; a missing case is a warning (it is then written at the next session). |
| `keys DIR\|SEALED… [--plan PLAN]` | The author's check of the key headers of sealed files (`author.md` §3): prints the key ids each file has and `problems`, naming file, key and field only, never a topic or a value; with `--plan`, also whether the number of headers of each type matches the plan's counts. Exit code 1 when there is a problem. |
| `verify --work W --store CHECK` | Testing mode: compare the publish set with the store read again into `CHECK`; the result is also written to `W/verify.json`. |
| `testing-note --work W --feedback J` | Testing mode: the learner's quick feedback and `W/verify.json`, as `data/testing/<id>.json` for this job's round. |
| `stats --work W` | Review figures: period, previous period, all time; gaps, calibration, teaching points unchecked, blind spots. Writes nothing. |
| `review --work W --review REVIEW.json` | Record a review; closes the period. |
| `review-doc --work W --md REPORT.md [--headline H] [--date D] [--title T]` | A review report as `data/reviews/<date>.json`, added to the index. |
| `snooze --work W [--days 7]` | Postpone a due review. |
| `settings --work W [--config J] [--profile J] [--blueprint FILE]` | Change settings: the changed ledger, the index, an emptied `data/prepared.json` and the page if it is out of date go into the publish set. A change to `mcqs`, `focused` or `case` is checked (at least one item) and supersedes any older page setting; a refused change writes nothing. |
| `theme --work W [--set DOMAIN \| --another]` | The learner changes the theme of the block (§4.1): `--set` a domain by id or name, `--another` the next proposal. Prints `block`, `was`, `say` and, like `settings`, the `files` to publish. Alone: the block, the proposal and the domains to choose from; writes nothing. |
| `init --work W --profile J --config J --blueprint FILE [--start-over]` | Setup: the first ledger, its index and the page, into the publish set. `W` needs no store yet. In a work folder opened on a store that already holds a ledger it stops unless `--start-over` is given. |

Maintenance tools, outside the protocol; they take their own files and folders:

| Command | Use |
|---|---|
| `import EXPORT.json --out-dir D` | A page export into the file layout (`store.md` §6, a damaged ledger). |
| `reindex ROOT` | Rebuild `ROOT/data/index.json` from the session and review files and the ledger. |
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
| `next/` | `prepare` (`plan.json`), the author and the checker (the next round's files) | `finish-prepare` |
| `publish/` | every command that writes: the newest version of each store file this job changed, at its store path | the commands that follow (the current ledger is `publish/data/state.json`), `verify`, whoever publishes |
| `publish.json` | every command that writes: `{"version": <store version read>, "files": [{"as", "path"}, …]}`, in write order | whoever publishes |
| `verify.json` | `verify` | `testing-note` |
| `before_save.json`, `before_close.json` | `save`, `close`: the ledger each started from, so that either can be run again | `save`, `close` |
| `earlier/<n>/` | `open`, `start`: the files of an earlier job in the same folder, set aside | nobody |

The **current ledger** of a job is the one in the publish set, or the ledger as read while
nothing has been written. Any other store file (the index, the page, a session document, the
prepared round) is looked up in the publish set first, then in the store copy. The write order
of the publish set is: session, review and testing files, then `data/index.json`, `index.html`,
`data/prepared.json`, and `data/state.json` last.

A `<!-- present: stage2 -->` block in a sealed file is used when there is no `stage2.md`.

## 7. Page settings (`cme/prefs`)

The page's Settings tab lets the learner switch MCQs, focused questions and the case on or off
and set the counts. The page cannot rewrite the ledger, so it writes one small document of its
own:

```json
{"round": {"mcqs": 2, "focused": 1, "case": true}, "base": "2026-10-08T09:12:00Z", "updated": "2026-11-06T21:40:12.512Z"}
```

`base` is the ledger's `config.round_set_at` that the page saw. `start` and `save` apply the
document only while `base` still equals `round_set_at`, then set `round_set_at` to `updated`; so
it is applied once, and a later change made in a chat (which sets a new `round_set_at`) wins
over an older page setting. No clocks are compared. An invalid document is ignored with a
warning, never fatal. The page shows a saved setting as "applies from your next round" until a
round has applied it.

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
there is none; `save`, `settings`, `theme`, `review` and `init` write that, so the file always exists.

`start` uses it only when all of this holds, and otherwise plans afresh (`--no-prepared` leaves
it alone for one round):

- the ledger is the one it was made from (`gen` and `next_id` unchanged: no round, review or
  settings change since);
- the round mix is the same, and no one-off option (`--mcqs`, `--focused`, `--no-case`,
  `--domain`, `--no-new`, …) was given;
- it is at most 30 days old;
- none of its topics was tested today.

The plan is made as of the day after the close, so everything in it is due by any later day.
Whatever part a prepared round lacks (`prepared.ready` lists what it has) is written at the
session, from the same plan, while the learner answers the part that is there.


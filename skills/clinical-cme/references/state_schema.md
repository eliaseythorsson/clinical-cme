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
  "gaps": [{"topic": "RENAL-02", "gap": "re-testable description", "self": null,
            "source": ["graded"], "date": "2026-10-26", "opened": "2026-09-17"}],
  "resolved": [{"topic": "CARD-03", "note": "…", "opened": "…", "resolved": "…", "partial": false}],
  "sessions": [ { "…one entry per session of the current review period (full coding)…" } ],
  "previous": [ { "…sessions of the previous period, compact coding…" } ],
  "agg": { "…all-time counters: sessions, items, errors by category/type/step/severity/bias, ART, IDEA, calibration, Brier, drills, disputes…" },
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
           {"type": "mcq", "topic": "CARD-03", "mastery": 5, "confidence": "sure", "correct": true, "stem": "…", "coding": {"errors": []}},
           {"type": "focused", "topic": "HEME-04", "mastery": 3, "confidence": "unsure", "aspect": "management", "stem": "…",
            "coding": {"art": {"MGMT": 1}, "errors": [{"element": "…", "category": "knowledge", "knowledge_type": "numeric", "art_domain": "MGMT", "severity": "important"}]}}],
 "why": {"RENAL-02": "due", "CARD-03": "due"}, "self_performance": 3, "self_comfort": {"RENAL-02": 5},
 "reflection": {"solid": "…", "gaps": "…", "skipped": false}, "key_learning": ["…"],
 "case": {"topic": "RENAL-02", "patient": "34M", "setting": "ED", "presentation": "…", "diagnosis": "…", "twist": "…"},
 "grade_changes": [{"item": "Case stage 2", "topic": "RENAL-02", "from": 3, "to": 3.5, "outcome": "both_defensible"}],
 "drill": null, "errata": ["E0003"]}
```

While a session's reflection is pending, its entry also carries `_snapshot` and `_round`, which
`reflect` uses to re-apply the round with the reflection. `record` of the next session drops
them and marks the reflection skipped.

Teaching points are the `key_learning` lines, identified as `<id>.<n>` (`S0021.2`).

## 2. Round JSON (input to `record`)

```json
{
  "date": "2026-10-26", "started_at": "2026-10-26T08:00:00+00:00", "ended_at": "2026-10-26T08:26:00+00:00",
  "case_format": "unfolding", "log_id": "S0021",
  "items": [
    {"type": "case", "topic": "RENAL-02", "label": "Hyponatraemia", "domain": "RENAL", "mastery": 3, "confidence": "unsure",
     "coding": {"art": {"DG": 2, "PR": 1, "DDX": 1, "TEST": 2, "META": 0, "MGMT": 1}, "idea": {"I": 2, "D": 1, "E": 1, "A": 0},
                "errors": [{"element": "…", "stage": 1, "category": "synthesis", "knowledge_type": null, "art_domain": "DDX",
                            "bias": ["premature_closure"], "bias_evidence": "'clearly dry from the run'", "severity": "critical", "confidence": "sure"}]}},
    {"type": "mcq", "topic": "ID-06", "mastery": 1, "correct": false, "confidence": "guess",
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
- `mastery` per item: cases 0–5 from the rubric; focused questions 0–5 from their table
  (`feedback_guide.md` §2 B2); MCQs typically 4–5 if correct with sound reasoning, 3 if correct
  with flawed reasoning, 1–2 if wrong.
- Focused questions need `aspect` (`diagnosis`, `interpretation`, `testing`, `management`,
  `disposition`, `prevention` or `prognosis`), `stem_summary`, and `coding` with ART for the
  domains they tested only, no `idea` (`analysis_framework.md` §1.6). `case` (the compact
  description) is for the full case only; omit it in a round without one.
- Every item needs a `coding` block (`analysis_framework.md` §1); a perfect item has ART scores
  and an empty `errors` list. `record` prints `warnings` for anything missing; fix and re-run.
- `pending_errata_logged: "all"` whenever `status` reported pending errata; `record` prints
  `errata_to_log` (full text) for part B.
- Omit `reflection`: the first save is provisional. Never run `record` twice on the same state.

## 3. Reflection JSON (input to `reflect`)

```json
{"topic_comfort": {"RENAL-02": 5, "CARD-03": 4}, "performance": 3,
 "solid": "the learner's words", "gaps": "the learner's words", "reading_minutes": 10, "skipped": false,
 "self_gaps": [{"topic": "ENDO-04", "gap": "Adrenal crisis management (self-reported)", "source": "self",
                "domain": "ENDO", "label": "Adrenal insufficiency / crisis"}],
 "grade_changes": [{"item": "Case stage 2", "topic": "RENAL-02", "from": 3, "to": 3.5, "outcome": "both_defensible"}],
 "items": [{"type": "case", "topic": "RENAL-02", "mastery": 3.5}],
 "errata": [], "key_learning": [], "resolved": []}
```

- `self_gaps` map each shaky area to a blueprint ID; an untested topic is created (or pulled
  forward) to within seven days. If no ID fits, make one in the blueprint's style and say so.
- `items` carries any score changed after a dispute (matched by type and topic); the coding of a
  changed item may be updated the same way (`"coding": {…}` replaces it).
- `{"skipped": true}` records the round without a reflection.

## 4. Spacing rules (applied by `record` and `reflect`)

Mastery per topic is the mean of its items' scores this round, after confidence rules:

- MCQ correct but marked **guess** → counts as at most 3.
- MCQ wrong but marked **sure**, or a case or focused question scoring ≤ 2 marked **sure** → a **confident error**
  (misconception): step resets to 0 (next day) and a gap with source `misconception` is added.

| Mastery | Step (`intervals_days` index) |
|---|---|
| ≥ 4 | advance one |
| 2.5–3.5 | hold |
| ≤ 2 | reset to 0 |

Self-assessment, with comfort *c* for the topic:

| Condition | Label | Effect |
|---|---|---|
| c − mastery ≥ 2 | overconfident | do not advance; back in ≤ 3 days |
| mastery − c ≥ 2 and mastery ≥ 4 | underconfident | advance, but halve the interval |
| otherwise | aligned | none |
| no rating | not_rated | none |

A self-reported gap caps the interval at 7 days. Comfort ratings feed `domain_self_ratings`
(rolling, weighted 2:1 toward history), which weight how often new topics from each domain are
sampled (rating 1→1.6, 2→1.3, 3→1.0, 4→0.8, 5→0.6, times blueprint weight, times emphasis,
divided by how often the domain appeared in the last ten sessions).

Selection (`plan`): due topics first (overconfident and misconception ahead, then most overdue,
then lowest mastery), then open gaps not re-tested since logged (misconception > self > transfer
> graded), then new topics by domain weight. Slots are filled case first, then focused questions,
then MCQs, so due topics and open gaps go to the formats that show reasoning. MCQs and focused
questions come from other domains than the case and are unrelated to it and to each other
(cross-references, shared significant words). In rounds of four or more items the last short
slot (the last MCQ, or the last focused question when there are no MCQs) is reserved for a new
topic; in smaller rounds whenever the previous session introduced nothing new
(`new_topics_per_round: 0` or `--no-new` disables this). Each focused item gets an
`aspect_hint`: the aspect tested least recently.

Open gaps: one per topic; a new entry replaces the old one, so its text must carry forward
anything still unresolved. A gap retires to `resolved` when a later round scores the topic ≥ 4,
not overconfident, with no new gap.

Review due: when `review_interval_days` has passed and at least three sessions were done, or
the interval plus 21 days has passed regardless. A snooze always wins.

## 5. Caps that keep the state small

`record`, `reflect` and `review` compact the state: at most 50 full sessions (older ones move to
`previous`, compact), 60 previous sessions, 8 history rows per topic, 40 resolved gaps, 6 reviews,
40 errata; gap text ≤ 400 characters, error elements ≤ 220, bias evidence ≤ 140. All-time figures
survive in `agg`. The verbatim detail is in the session documents, which are never compacted.

## 6. Commands

| Command | Use |
|---|---|
| `start STATE --out PLAN [--prefs J] [--prepared PREPARED.json [--work-dir D]] [plan options]` | Session start: `status` and `plan` in one call. Prints the neutral status with the plan's counts (MCQs, focused, case, `estimated_minutes`) under `plan`, plus `helpers`, `prepare_ahead` and `speed_settings_new`. No topic names. `--prefs` is the page's `cme/prefs` document (§7); `page_settings_applied` says when it changed the mix. `--prepared` is the store's `data/prepared.json` (§8): when it still fits, `prepared.used` is true, `present` holds the first part's text to send (`prepared.present_block` says which), the plan is written to `--out` and the drafted files (`prepared.ready`: `sealed_questions.md`, `sealed_case.md`, `kit_questions.md`, `kit_case.md`, `evidence_questions.md`, `evidence_case.md`) beside it (or into `--work-dir`); otherwise `prepared.why` says why not and the round is planned as usual. |
| `present SEALED… --block questions\|case\|stage2` | Print only the text the learner is to see from sealed files (one `present` block), so it can be sent without opening the keys. |
| `save STATE --round R.json --sealed F… --answers A.md [--feedback-questions FQ.md] --feedback FB.md [--index IDX] [--prefs J] [--page INDEX.html] --out-dir D` | First save after the final feedback: `record` + session document (part A assembled in the order of the round from the sealed `present` blocks, the answers, the questions' feedback and the final feedback; or `--md A.md`) + index + an emptied `data/prepared.json`. Prints what `record` prints plus `files`. Pass the same `--prefs` as to `start` so the mix is kept in the ledger. `--page` is the learner's current `index.html`: if it is older than the skill's template, `files` also holds the new `index.html` (`page_upgraded`). |
| `close STATE --reflection R.json --md B.md --doc SESSION.json [--index IDX] --out-dir D` | Second save: `reflect` + part B into the session document + index. |
| `addendum --doc SESSION.json --md ADD.md --out-dir D` | Append later discussion to a session document. |
| `prepare STATE --out NEXT_PLAN [--if-needed PREPARED.json] [--allow-unreflected]` | After the close: plan the next round (as of tomorrow) from the closed ledger. Prints counts only, or `"prepare": false` with the reason (setting off, reflection pending, or — with `--if-needed` — a usable round is already prepared). `--allow-unreflected` plans although the last session has no reflection yet (the scheduled task uses it). |
| `stash STATE --plan NEXT_PLAN --dir DRAFTS --out-dir D` | Pack that plan and the files drafted for it in `DRAFTS` (`sealed_questions.md`, `sealed_case.md`, `kit_questions.md`, `kit_case.md`, `evidence_questions.md`, `evidence_case.md`) into `data/prepared.json` (§8). The first part's sealed file must be there; a missing case is a warning (it is then written at the next session). |
| `place STATE [--index IDX] [--page INDEX.html] --out-dir D` | Put a ledger made by `init`, `settings`, `review` or `snooze` into the file layout, with the index (and the page if it is out of date, as for `save`). |
| `review-doc --md REPORT.md [--headline H --state S --index IDX] --out-dir D` | A review report as `data/reviews/<date>.json`, added to the index. |
| `import EXPORT.json --out-dir D` | A page export into the file layout (`store.md` §6, a damaged ledger). |
| `reindex ROOT` | Rebuild `ROOT/data/index.json` from the session and review files and the ledger. |
| `status STATE` | Start of session: neutral JSON (next id, last session and whether its reflection is pending, due counts, review due, pending errata, round shape). No topic names. |
| `plan STATE --out PLAN [--mcqs N --focused N --no-case --domain CODE --no-new --allow-repeat --no-drill --prefs J]` | Choose the round: topic IDs, labels, reasons, drill, `already_used`, recent cases, `aspect_hint` for focused items. Prints only counts. `--mcqs`, `--focused` and `--no-case` change this round only. |
| `record STATE --round ROUND.json --out NEXT` | Apply a graded round (reflection pending if absent). Prints per-topic next due, warnings, `errata_to_log`. |
| `reflect STATE --reflection R.json --out NEXT [--session ID]` | Re-apply the last unreflected session with its reflection. |
| `doc --part A --md A.md --round ROUND [--id S0042] --out A.json` / `doc --part B --md B.md --out B.json` | The session document, or its part B, as JSON (single steps of `save` and `close`). |
| `stats STATE` | Review figures: period, previous period, all time; gaps, calibration, teaching points unchecked, blind spots. |
| `review STATE --review REVIEW.json --out NEXT` | Record a review; closes the period. |
| `snooze STATE --days 7 --out NEXT` | Postpone a due review. |
| `settings STATE [--config J] [--profile J] [--blueprint FILE] --out NEXT` | Change settings. A change to `mcqs`, `focused` or `case` is checked (at least one item) and supersedes any older page setting. |
| `init --profile J --config J --blueprint FILE --out STATE` | First-run creation. |
| `blueprint-md FILE --out BP.json` | Convert a Markdown blueprint. |
| `validate STATE` | Structural check. |

Add `--today YYYY-MM-DD` (before the command) to fix the date. Every command that writes for the
store prints `files`: local `path` and store path `as`. Commands that write take `--out`; never write over the
file you read in the same step, so a failed write can be retried from it.

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

Written by `stash` after a close; `payload` holds the next round's plan and everything
written for it: the sealed short questions and the sealed case (keys, results bank,
verification lists, `present` blocks), the two feedback kits and the two evidence files from
the check, packed so that nobody reads
them by accident: they are in the learner's own store. `{"v": 1, "empty": true}` means
there is none; `save` and `place` write that, so the file always exists.

`start --prepared` uses it only when all of this holds, and otherwise plans afresh:

- the ledger is the one it was made from (`gen` and `next_id` unchanged: no round, review or
  settings change since);
- the round mix is the same, and no one-off option (`--mcqs`, `--focused`, `--no-case`,
  `--domain`, `--no-new`, …) was given;
- it is at most 30 days old;
- none of its topics was tested today.

The plan is made as of the day after the close, so everything in it is due by any later day.
Whatever part a prepared round lacks (`prepared.ready` lists what it has) is written at the
session, from the same plan, while the learner answers the part that is there.


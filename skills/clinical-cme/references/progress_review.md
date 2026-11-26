# Progress review (every 30–90 days, as the learner chose)

A periodic look back that resets goals and settings. Two parts:

- **Check-in**, always: about 5–10 minutes.
- **Deep analysis**, offered every time: the assistant reads the coded rounds and the session log and
  gives personal, candid feedback (strengths, weaknesses, thought errors, knowledge errors,
  calibration, progress), ending with an agreed change plan and a saved report.

`status` reports `review_due` when `review_interval_days` has passed and at least three
sessions were done, or the interval plus 21 days has passed regardless. A snooze always wins.

## When to run it

- When `review_due` is true at the start of a session: offer it in one line (now · after
  today's round, the default · postpone a week with `snooze`). Do not let it crowd out the round.
- Any time the learner asks ("how am I doing", "review my progress", "analyse my answers").

Offer the two parts in one question (as structured choices where the app offers them):

> Your review covers <n> sessions since <date>. **Check-in** (5–10 min): figures, goals and
> settings. **Deep analysis** (I read your coded answers and the session log, then give detailed
> and critical feedback with a written report; it takes me 15–30 minutes and you about 10 to
> read and discuss): **both** (recommended) · **check-in only** · **deep analysis later this week**.

If some of the period's older sessions have no transcript (only scores, gaps and coding), say so.

## 1. Gather

1. Read the store and `open` the work folder (`store.md` §4), then `python3 cme.py stats --work <work>`. Use only these figures and the
   state; never estimate numbers in prose. It lists the period's session IDs.
2. With the deep analysis on: take the period's session IDs from `stats` (or the index), and
   read those session documents into local files in `<work>/period` (the page: the read-files
   tool with up to the allowed number of paths per call; a folder: copy) — no transcript enters the conversation unread. Read them in batches of about six
   (`transcript` and `closing` fields), take notes per batch in `<work>/review_notes.md`
   (patterns, quotations, session IDs) and rely on those notes rather than memory. Large periods
   (> 15 sessions) with parallel helper agents available: one batch per subagent with
   `analysis_framework.md` and the instruction to return findings under the §2.2 headings.
3. Run the guideline-change check (`analysis_framework.md` §2.3) on `teaching_points_unchecked`.
4. Draft the report (`analysis_framework.md` §2.6). Use a task list with neutral items.

## 2. Present (R2C2: relationship, reaction, content, coaching)

**Relationship and headline.** One screen:

**Your last N weeks**
- Sessions: *n* (≈ *x* per week; target *y*). Time: about *m* minutes in sessions plus *r*
  minutes of reading reported (say when timings are estimates).
- Items: cases, focused questions (mean score) and MCQs (accuracy), from `stats` `items`.
- Coverage: domains practised with mean latest score; blueprint domains not yet touched.
- **What you learned**: gaps resolved in the period, one plain line each, plus key learning
  points. The most useful part; keep it concrete.
- Still open: persisting gaps, grouped by domain, shortest description each.
- Calibration: how often comfort matched performance; confident-but-low and good-but-unsure topics.
- Trend: topics that clearly improved or declined.
- With the deep analysis: its three-line headline, the reasoning-step profile in one line, the
  number of critical errors.

**Reaction.** Ask how this matches their own sense, and anything surprising or unfair. Wait.

**Content.** With the deep analysis, send the full report (as a page or file) and summarise it
in chat if it does not fit on one screen. Discuss what they want. Correct the report if their
context changes a finding.

**Coaching and check-in questions.** One message, or batches of structured questions:

1. Is the format working? Including the mix (MCQs, focused questions, full case): keep, or change?
2. Time per session and frequency still realistic? Compare with the actual numbers, without judgement.
3. Difficulty: too easy, about right, too hard?
4. Feedback length and depth? Keep the one-line coding?
5. Goals for the next period: anything to emphasise or de-emphasise (domains, exams, a new rotation)?
6. Updated self-ratings where their sense of a domain has changed.
7. Review interval: keep or change (30–90 days)?
8. With the deep analysis: agree two or three change-plan goals and the drills that support them
   (which patterns, how often; default one round in three).

## 3. Apply and record

1. **Report.** With the deep analysis, write the final report (Markdown, template in
   `analysis_framework.md` §2.6) to `<work>/report.md`, wrap it as
   `{"date": "…", "title": "CME progress review — <date>", "headline": "…", "report": "<markdown>"}`
   `python3 cme.py review-doc --work <work> --md <work>/report.md --headline "<headline>"`.
   The page renders it. Offer a shareable document (for an appraisal or revalidation
   portfolio) if they want one.
2. **Review JSON** → `python3 cme.py review --work <work> --review <work>/review.json` →
   publish every file in its `files` in one write (`store.md` §4; the report from step 1 is
   among them):

```json
{
  "doc": "reviews/2026-11-20",
  "headline": "Three lines", "summary": "Two-line summary of the period",
  "learner_feedback": {"format": "…", "time": "…", "difficulty": "about right", "feedback": "…"},
  "goals": ["…"],
  "config_changes": {"session_minutes": 25, "target_sessions_per_week": 2, "review_interval_days": 60},
  "profile_changes": {"goals": ["…"]},
  "domain_self_ratings": {"GEN": 2}, "domain_emphasis": {"GEN": 1.5, "RENAL": 0.7},
  "deep_analysis": true,
  "key_figures": {"sessions": 14, "mean_score": 3.4, "brier": 0.21, "errors_per_session": 1.8, "critical_errors": 2},
  "change_plan": ["Before closing a differential, name one diagnosis that would explain the unexplained finding"],
  "drill_targets": [{"code": "bias:premature_closure", "description": "Closing on the first explanation", "rate": 0.33}],
  "teaching_point_checks": [{"id": "S0012.2", "status": "superseded", "point": "…", "note": "What changed", "source": "…"},
                            {"id": "S0015.1", "status": "current"}]
}
```

- `domain_emphasis` multiplies the sampling weight for new topics (1.5 more, 0.5–0.7 less, 1.0 reset).
- `drill_targets` replaces the previous set; `[]` stops drills. Drills run until the next review.
- `teaching_point_checks` marked `changed` or `superseded` become pending errata, written into
  the next session's part B. The review itself never writes to the log.
- `review` closes the period: the current sessions move to `previous`, compact, and the next
  review date is set from the interval.

3. **Close** with one line on what changes from now on.

## After the review is saved

Recording a review changes the ledger, which sets aside any round prepared ahead. If the
review ran at the end of a session, prepare the next round now, in the same work folder
(`preparing.md` §2: it plans from the ledger the review wrote), after your last message of
the review.


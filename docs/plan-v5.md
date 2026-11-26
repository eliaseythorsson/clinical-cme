# Plan: clinical-cme 4.3.1 → 5.0

Agreed 2026-11-20 (grilling session). Priorities, in order: learning quality > reliability >
maintainability > speed > cost > portability. Decisions: `docs/adr/0001`–`0005`; vocabulary:
`CONTEXT.md`.

## 1. Version 4.3.1 (on `main`; 4.3 is already merged)

- Fix the date shift: a round's date is set at `save` and kept when the reflection arrives on a
  later day; session documents honour `--today`.
- Fix the Stage 2 blinding leak: before Stage 2 is answered the examiner reads only the results
  bank (`present --block bank`), never the key, kit or evidence.
- Testing mode (`config.testing`, "testing mode on/off"): after the close, a 30-second check
  (waiting fine/noticeable/annoying + which step, item quality 1–5, feedback quality 1–5, one
  line) and an automatic check that the store holds what `close` produced; saved to
  `data/testing/<session>.json`. A later dev session turns these into issues.
- Unit tests (pytest) for each fix.

## 2. Real test of 4.3.1

Three real rounds in the Claude app over about a week, on the real ledger, testing mode on,
helpers on, "prepare my rounds overnight" for at least one night. Pass bar: no blinding leak, no
failed save, no feedback you would distrust, no wait you would notice.

**Result (rounds S0034–S0037, 2026-11-21 → 26; summary on #4).** No blinding leak, no failed
save (4/4 store checks), feedback trusted. Waits not fully met (S0035: 2 min to short-question
feedback; S0037: ~35 s to first questions, rising each session). Overnight preparation not yet
run (#48).

### Issues from the real test

- #41 Keep the prepared round when a setting does not change round content
- #42 Page round mix and the prepared round agree
- #43 First questions within 10 seconds
- #44 Evidence fully checked when the round is prepared
- #45 Authoring standards: one time anchor, crux tests requested, abbreviations defined once
- #46 Learner override of a score or gap
- #47 Real time per round, and a hint (median ~56 min vs ~33 min estimated)
- #48 Test overnight preparation for one night (human)
- #49 Pre-written rubric feedback adapted to the answer (design, human; blocked by #44)
- #50 Podcast picks, prepared ahead (blocked by #44)
- #51 Reading and listening on the page (blocked by #50)

## 3. Version 5, stage A: testable core

- Split `cme.py` into pure core functions (scheduling, planning, applying a round) and thin
  commands; stop chaining commands through captured stdout; raise errors instead of exiting.
- Fixture ledgers (fresh, mid-curriculum, overdue, unreflected, stale prepared round) and golden
  outputs; invariants (`present` never prints keys or topics, log append-only, failed write leaves
  the ledger untouched, deterministic spacing).
- GitHub Actions: `py_compile` + pytest on every pull request.
- Simulation harness (ADR 0005) built alongside: examiner agent + learner personas (strong; weak
  and overconfident; disputes a grade; stops halfway), automatic checks, clinical-quality score
  logged only.

## 4. Version 5, stage B: lean protocol

- `save --work <dir>` that finds files by fixed names; append-per-part answers; structured key
  headers so `cme.py` fills `round.json` and the model adds only scores and coding; one
  `finish-prepare` (check key headers, count contradicted keys, fail loudly on a bad header or a
  missing evidence file, stash);
  settings + place in one command.
- SKILL.md to about 250 lines; prepare-only, other requests and FAQ into references.
- Cut the database store, Drive mirror, v3 migration and `legacy/`, the capability table for other
  assistants (ADR 0002).
- Hide upcoming gaps and due topics on the learner's page (preview leak).

## 5. Version 5, stage C: curriculum (ADR 0003)

- Themed blocks: 12 rounds; 60% theme / 25% due repeats / 15% wildcard; case on theme; theme
  shown; next theme proposed automatically (weakest or longest-unvisited) with one-line override.
- Drill-down only within the theme, max two consecutive rounds per sub-topic; off-theme miss →
  one targeted retest after a few days, then spacing.
- Spacing fixes: minimum ~3 days after a miss; a gap closes only when an item tests that gap;
  comfort ratings corrected for calibration before they lower a domain's weight.
- Migration: existing ledgers keep history, gaps and due dates; first block starts next round.
- Region and specialty set in conversation at setup.

## Later

- Real images, starting with ECGs drawn from an open dataset (e.g. PhysioNet PTB-XL); CT/MRI
  only if ECGs work. Separate prototype after v5.
- A locked theme sequence (e.g. board preparation), if anyone asks.

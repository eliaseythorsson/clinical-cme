# Simulation harness

A simulation is a scripted run of the skill in which one agent is the examiner and another plays
a learner persona (`CONTEXT.md`). It runs inside a Claude Code session on the owner's plan, with
no API key (`docs/adr/0005-simulation-inside-claude-code.md`): the session starts the two agents,
relays their messages and writes a report. It is slow and counts against plan usage, so it is
run on demand before merges, not in CI.

`simulate.py` is everything that is not an LLM: it sets up a run, carries and times the messages,
runs the automatic checks and writes the report. It is tested in CI with scripted rounds, one per
persona (`tests/test_simulation.py`, `tests/test_sim_personas.py`), so no test needs an LLM.

## Run it

In a Claude Code session opened in this repo:

```
/simulate strong
```

or ask: "Run a simulation following `sim/README.md`." One round takes roughly 15–40 minutes.
The personas are `strong`, `weak-overconfident`, `disputes` and `stops-halfway` (see Personas).
Before a merge, run each of them at least once.

## Procedure

For the Claude Code session that runs the simulation. You are the relay: you start two helper
agents, pass file paths between them, and run `simulate.py`; when the round is over you start a
third, the quality scorer. You do not read the messages, the
store or the work folder while the round runs (you have no need to, and it keeps your context
small), and you never tell either agent anything about the other's content. In particular the examiner
is never told which persona it is facing: say nothing of it in the prompt or the description.

You need a tool that starts a helper agent **and can continue the same agent later** with a new
message, keeping its conversation. The examiner must be one continuous agent for the whole
round. If this session cannot continue a helper agent, stop and say so; do not approximate by
starting a fresh examiner each turn.

1. **Set up.** `python3 sim/simulate.py init --persona <persona>` (default `strong`). It prints
   the run folder and the paths of `examiner_prompt.md` and `learner_prompt.md`, and records
   the learner's opening request; the clock starts here, so go straight on. Each `init` gets a
   run folder of its own, so several personas can be started at once.
   Options: `--prepare-ahead` (the examiner also prepares the next round after the close; much
   longer), `--from-run <earlier run folder>` (a second round on the same store),
   `--skill <folder>` (test an installed copy instead of `skills/clinical-cme/`),
   `--config '<json>'` (other ledger settings, e.g. `{"mcqs": 2, "focused": 1}`). `stops-halfway`
   needs a round with short questions and a case, which the default settings give.
2. **Start the examiner agent**, in the foreground, with the prompt
   "Read `<examiner_prompt.md path>` and follow it." and a neutral description ("Run the
   round"). Use the model the round is to be tested with, and note its name for the report.
3. When it returns, run `python3 sim/simulate.py next --run <run> --after examiner`. It prints
   `files` (the examiner's new messages), `deliver_to` and `stop`.
   - `stop` true → go to step 6.
4. **Start the learner agent** the first time ("Read `<learner_prompt.md path>` and follow it.
   The examiner's first message(s): `<files>`."; description "Take the round"), or continue it
   ("New message(s) from the examiner: `<files>`."). When it returns, run
   `python3 sim/simulate.py next --run <run> --after learner`.
   - `stop` true → go to step 6. (After the close message the learner sends nothing, and
     `next` reports that the round is closed.)
5. **Continue the examiner agent** with "The learner replied: `<files>`." and go to step 3.
6. **Score the clinical quality.** `python3 sim/simulate.py quality --run <run>` writes the
   scorer's form (`quality.json`: one entry per item, one per feedback message) and its brief,
   and prints both paths. Start a **new** agent, neither the examiner nor the learner, with
   "Read `<quality_prompt.md path>` and follow it." (description "Score the round"). When it
   returns, run the same command again: it says whether the form is whole. Continue the scorer
   once if entries are missing; then go on whatever the form holds. Skip this step if the round
   was never saved (there is nothing to score).
7. **Report.** `python3 sim/simulate.py report --run <run> --examiner-model <name>
   --learner-model <name>`. It runs the automatic checks, takes in the quality scores and writes
   `sim/reports/<date>-<persona>.md` and `.json`. If the run stopped early (an agent failed, or
   `why` says the round is not converging), still write the report and add `--note '<what
   happened>'`: a failed run is a result.
8. **Tell the owner** the result in a few lines: which checks passed, the longest wait and at
   which step, any blinding findings to review, the quality means and any concern the scorer
   listed, and the report's path. Commit the two report
   files (never the run folder: `sim/runs/` is ignored by git).

If an agent returns an error or asks you a question instead of working, continue it once with
"Carry on as your brief says; nobody else can answer." If it fails again, stop and report.

## What is checked

| Check | Passes when | How |
|---|---|---|
| **Blinding** | nothing the examiner sent before a part's answers holds that part's topic, diagnosis or key | Every examiner message sent before the learner message that completed the part's answers is searched for: the blueprint ID and label of each item of that part, the case's diagnosis and the session title, and every line of the keys and feedback notes (`sealed_*.md` outside the `present` and `bank` blocks, `kit_*.md`). A hit is a **leak**. Single significant words of a topic label and the domain's name are listed **to review** without failing the check: a stem may fairly contain a word of its topic's label, and a person has to judge it. |
| **Every file saved** | the store holds what `cme.py` wrote, and the round in it is whole | `cme.py verify --work` compares the work folder's publish set with the store; then the ledger must hold the round with its reflection, the session document must exist and be closed, and the index must list it at the ledger's generation. |
| **Log complete and verbatim** | the session document has every section the round's shape calls for; what it says was presented, answered and sent is word for word what was sent; every learner message is in it | Section bodies of part A and the reflection in part B are matched against the recorded messages, ignoring only runs of whitespace. |

The seal on the short questions lifts with the learner message matching the
`<!-- answers: questions -->` block of `answers.md` (written by `cme.py answer`); the seal on the case with the message matching
its last answers block (`final`, or `case` for a one-step case). If no message matches, the check
fails as undetermined. A case the learner never answered (the round was stopped before it) stays
sealed to the end: every examiner message of the round is searched for its topic, its diagnosis
and its key.

Two personas must also produce something, and their runs are checked for it. The check is named
in the persona's file (`"expect"`) and fails the run like the others:

| Check | Persona | Passes when | How |
|---|---|---|---|
| **Dispute** | `disputes` | the round holds a settled dispute, in the log and in the grade changes | The ledger's record of the round has at least one entry in `grade_changes`, each with an outcome (`learner_right`, `both_defensible`, `upheld`); part B's "Grade changes" section is not "None."; and the exchange is in the log word for word, the learner's challenge and the examiner's reply both, under "Discussion" (raised after the final feedback) or "Notes" (settled mid-round). |
| **Stopped** | `stops-halfway` | the round is saved without the case, and the case's topic is still due | The ledger's record of the round holds short questions and no case; the case's topic (from `plan.json`) is not among the round's topics, and its schedule in the ledger (last tested, attempts, step, due date) is exactly what it was when the round began (`ledger_at_start.json`). |

Limits of this first version: only what is *sent* is searched. The examiner's reasoning and its
tool-call descriptions are not visible to the session from inside a helper agent, so leaks there
are not caught. A paraphrased diagnosis is not caught either; only the diagnosis as the key
states it.

## Waiting time

`send` records the time of every message, `next` the end of every turn. The report gives, per
step (start of round, after the answers to the questions, after Stage 1, after the final
answers, after the reflection): **wait**, from the learner's message to the examiner's first
message after it, which is what a learner would sit through; **turn**, until the examiner's
turn ended, behind-the-scenes work included; and the learner agent's own time. Waits include the
relay's hand-over (seconds). Helper agents are slower to start than a live conversation, so
compare runs with each other, not with the real app.

## Clinical-quality score

After the round a separate agent, the quality scorer, reads the messages, the keys and the
evidence files and rates, from 1 to 5, **each item** as written (accurate, current for the
learner's guideline region, one defensible key, right pitch) and **each feedback message** as
sent (claims correct and sourced, grades fair to what the learner wrote, the deciding point
taught): the feedback on the short questions, the final feedback, and the examiner's replies to
a dispute when there was one. Each score has a one-line note; the scorer also lists concerns for
a clinician to look at. Its brief is `prompts/quality.md`.

The scores go into the report (`quality.items[]`, `quality.feedback[]`, `quality.item_mean`,
`quality.feedback_mean`, `quality.score` for the round overall) and nowhere else. They are kept
to compare runs over time and **never fail a run or block a merge**
(`docs/adr/0004-no-clinical-correctness-judge.md`): a low score, a missing score or a
half-filled form is recorded as it is, and `ok` in the report depends on the automatic checks
only. `report --quality 1-5 --quality-note '<line>'` still records an overall score given by
hand, with or without a scorer.

`python3 sim/simulate.py history [--persona <name>] [--json]` prints one line per saved report:
checks, the round's score, the quality means and the longest wait.

## Reports

`sim/reports/<date>-<persona>[-n].md` is for reading; the `.json` beside it has the same content
with stable keys (`checks`, `timings.steps[].wait_s`, `quality`, …) for comparing runs. Reports
hold check results, timings, quality scores with their one-line notes and short excerpts around
any blinding finding; transcripts stay in the run folder, which is not committed.
`round.confident_misses` counts the items answered `sure` and wrong, which shows whether the
weak, overconfident persona played its part.

## Personas

`personas/<name>.md`: a `json` block with the ledger profile the store is seeded with, then the
brief the learner agent plays. An `"expect"` list in that block is for the harness, not the
ledger: it names the extra checks the persona's round must pass.

| Persona | Plays | Its round must also |
|---|---|---|
| `strong` | a consultant who answers correctly, with calibrated confidence | – |
| `weak-overconfident` | an internist out of date and sure of it: about half wrong, `sure` almost every time, overrates the round in the reflection | – |
| `disputes` | a consultant who challenges exactly one grade after the final feedback, then accepts the outcome and reflects | hold a settled dispute (`dispute`) |
| `stops-halfway` | a consultant on call who answers the short questions and stops when the case arrives | be saved without the case, its topic still due (`stopped`) |

A persona file elsewhere can be given by path (`--persona path/to/file.md`).

## Files of a run (`sim/runs/<stamp>/`, not committed)

The folder is named after the second the run started (`YYYYmmdd-HHMMSS`); a run started in the
same second as another gets `-2`, `-3`, … after it. The name does not name the persona: its
path is in the examiner's brief. `--runs-dir <folder>` makes the run folder somewhere other
than `sim/runs/`; `--run <folder>` names the folder itself, which must be new or empty.

| Path | What |
|---|---|
| `run.json` | persona and what it is expected to produce, skill folder and version, commit, settings |
| `ledger_at_start.json` | the ledger as the round found it |
| `store/` | the simulated learner's folder store (`data/state.json`, …) |
| `work/` | the examiner's scratch folder (`<work>` in SKILL.md) |
| `messages/NNN-<role>.md`, `transcript.jsonl` | every message as sent, and when |
| `examiner_prompt.md`, `learner_prompt.md` | the two briefs, filled in from `prompts/` |
| `checks.json` | the full check results |
| `quality_prompt.md`, `quality.json` | the quality scorer's brief and its form, filled in |

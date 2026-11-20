# Simulation harness

A simulation is a scripted run of the skill in which one agent is the examiner and another plays
a learner persona (`CONTEXT.md`). It runs inside a Claude Code session on the owner's plan, with
no API key (`docs/adr/0005-simulation-inside-claude-code.md`): the session starts the two agents,
relays their messages and writes a report. It is slow and counts against plan usage, so it is
run on demand before merges, not in CI.

`simulate.py` is everything that is not an LLM: it sets up a run, carries and times the messages,
runs the automatic checks and writes the report. It is tested in CI with a scripted round
(`tests/test_simulation.py`), so no test needs an LLM.

## Run it

In a Claude Code session opened in this repo:

```
/simulate strong
```

or ask: "Run a simulation following `sim/README.md`." One round takes roughly 15–40 minutes.

## Procedure

For the Claude Code session that runs the simulation. You are the relay: you start two helper
agents, pass file paths between them, and run `simulate.py`. You do not read the messages, the
store or the work folder while the round runs (you have no need to, and it keeps your context
small), and you never tell either agent anything about the other's content.

You need a tool that starts a helper agent **and can continue the same agent later** with a new
message, keeping its conversation. The examiner must be one continuous agent for the whole
round. If this session cannot continue a helper agent, stop and say so; do not approximate by
starting a fresh examiner each turn.

1. **Set up.** `python3 sim/simulate.py init --persona <persona>` (default `strong`). It prints
   the run folder and the paths of `examiner_prompt.md` and `learner_prompt.md`, and records
   the learner's opening request; the clock starts here, so go straight on.
   Options: `--prepare-ahead` (the examiner also prepares the next round after the close; much
   longer), `--from-run <earlier run folder>` (a second round on the same store),
   `--skill <folder>` (test an installed copy instead of `skills/clinical-cme/`),
   `--config '<json>'` (other ledger settings, e.g. `{"mcqs": 2, "focused": 1}`).
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
6. **Report.** `python3 sim/simulate.py report --run <run> --examiner-model <name>
   --learner-model <name>`. It runs the automatic checks and writes
   `sim/reports/<date>-<persona>.md` and `.json`. If the run stopped early (an agent failed, or
   `why` says the round is not converging), still write the report and add `--note '<what
   happened>'`: a failed run is a result. Optionally, and for the record only, read the run's
   messages first (the round is over) and add a clinical-quality score to the same command:
   `--quality 1-5 --quality-note '<one line>'`. It is logged, never a pass bar
   (`docs/adr/0004-no-clinical-correctness-judge.md`).
7. **Tell the owner** the result in a few lines: which checks passed, the longest wait and at
   which step, any blinding findings to review, and the report's path. Commit the two report
   files (never the run folder: `sim/runs/` is ignored by git).

If an agent returns an error or asks you a question instead of working, continue it once with
"Carry on as your brief says; nobody else can answer." If it fails again, stop and report.

## What is checked

| Check | Passes when | How |
|---|---|---|
| **Blinding** | nothing the examiner sent before a part's answers holds that part's topic, diagnosis or key | Every examiner message sent before the learner message that completed the part's answers is searched for: the blueprint ID and label of each item of that part, the case's diagnosis and the session title, and every line of the keys and feedback notes (`sealed_*.md` outside the `present` and `bank` blocks, `kit_*.md`). A hit is a **leak**. Single significant words of a topic label and the domain's name are listed **to review** without failing the check: a stem may fairly contain a word of its topic's label, and a person has to judge it. |
| **Every file saved** | the store holds what `cme.py` wrote, and the round in it is whole | `cme.py verify` compares every output folder in the work folder with the store; then the ledger must hold the round with its reflection, the session document must exist and be closed, and the index must list it at the ledger's generation. |
| **Log complete and verbatim** | the session document has every section the round's shape calls for; what it says was presented, answered and sent is word for word what was sent; every learner message is in it | Section bodies of part A and the reflection in part B are matched against the recorded messages, ignoring only runs of whitespace. |

The seal on the short questions lifts with the learner message matching the
`<!-- answers: questions -->` block of `answers.md`; the seal on the case with the message matching
its last answers block (`final`, or `case` for a one-step case). If no message matches, the check
fails as undetermined.

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

## Reports

`sim/reports/<date>-<persona>[-n].md` is for reading; the `.json` beside it has the same content
with stable keys (`checks`, `timings.steps[].wait_s`, …) for comparing runs. Reports hold check
results, timings and short excerpts around any blinding finding; transcripts stay in the run
folder, which is not committed.

## Personas

`personas/<name>.md`: a `json` block with the ledger profile the store is seeded with, then the
brief the learner agent plays. This version has `strong`. Planned (`docs/plan-v5.md` §3): weak
and overconfident; disputes a grade; stops halfway.

## Files of a run (`sim/runs/<stamp>-<persona>/`, not committed)

| Path | What |
|---|---|
| `run.json` | persona, skill folder and version, commit, settings |
| `store/` | the simulated learner's folder store (`data/state.json`, …) |
| `work/` | the examiner's scratch folder (`<work>` in SKILL.md) |
| `messages/NNN-<role>.md`, `transcript.jsonl` | every message as sent, and when |
| `examiner_prompt.md`, `learner_prompt.md` | the two briefs, filled in from `prompts/` |
| `checks.json` | the full check results |

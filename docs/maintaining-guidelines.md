# Maintaining the central guideline checks

The default blueprint (`plugins/clinical-cme/skills/clinical-cme/templates/blueprint.json`) cites
a guideline at the end of each decision point (`[ESC ACS 2023]`). Whether each cited guideline is
still the edition to cite is checked **once, here in the repo**, per supported region set, and the
records ship with the plugin in `templates/guideline_checks.json` (issue #91, ADR 0013). Learners'
installs do not re-check those tags themselves (unless they set `guideline_sweeps` to `all`), so
this job is what keeps them current.

This document is the whole procedure for a **monthly scheduled cloud session**. It is written so
that a fresh session with no other context can follow it. Do every step; do not improvise around a
failure (see "When something fails").

## What you need

- A clone of `https://github.com/eliaseythorsson/clinical-cme` with push access to `main`.
- Python 3.8+ and pytest (`python3 -m pip install pytest pytest-xdist` if missing).
- Helper agents (sub-agents) with web search and web fetch, one per checker list. Without
  helpers, do each list yourself, one after another, by the same brief.

All paths below are relative to the repo root. `$CME` stands for the engine; set it in every
shell you run commands in (a fresh shell does not keep it):

```
CME="python3 plugins/clinical-cme/skills/clinical-cme/scripts/cme.py"
```

## The rules the job applies

- A tag is **due** when its record in a set was not checked within 90 days, or it has no record.
  Never-checked tags go first, then the oldest. A superseded tag is not checked again: its
  successor (the tag as cited now) is.
- Each set (today **International** and **Europe**) is checked on its own: the same tag can have a
  different "more appropriate guideline" for each.
- **The monthly run always passes `--share 3`**: at most ceil(391/3) = 131 tags per set, the
  never-checked and then the oldest first. The records started all dated 2026-11-27, so listing
  every due tag would bunch about 780 checks (391 per set) into one run around 2027-02-26;
  a third a month spreads them so that each tag is checked about every three months and every
  run is the same size. Without `--share` every due tag is listed (only for a one-off catch-up).
- Lists hold at most 40 tags; one checker per list.

## Procedure

1. **Clone and check the starting point.**

   ```
   git clone https://github.com/eliaseythorsson/clinical-cme && cd clinical-cme
   git checkout main && git pull --ff-only
   python3 -m py_compile plugins/clinical-cme/skills/clinical-cme/scripts/cme.py
   $CME central-checks --validate
   ```

   `--validate` must print `"valid": true`. If it does not, stop (see "When something fails").
   Note each set's `due` and `never_checked` from the output: they go in the commit message.

2. **List the tags due.** Use a folder outside the repo, so nothing stray is committed:

   ```
   $CME central-checks --list /tmp/gc-lists --share 3
   ```

   (`--share 3` is the standing default; see "The rules the job applies"). The output has `count`,
   `due` per set and `checkers`: one entry per list, with `set`, `list` (e.g.
   `/tmp/gc-lists/europe_checks_1.md`) and `results` (`/tmp/gc-lists/europe_results_1.md`). If
   `count` is 0, nothing is due: skip to step 6 and make no commit.

3. **Run one checker per list, all together.** Give each helper this prompt, with its two paths:

   > You are a tag checker. Read `plugins/clinical-cme/skills/clinical-cme/references/tag_check.md`
   > ("Tag check") and follow it exactly, with web search, for the list at
   > `<list>`. Its first lines give the region set and the specialty. For every tag on the list
   > write exactly one line `Tag: <tag exactly as listed> | current|changed|superseded|uncertain |
   > <the newer tag, or -> | <source link> | <one-line note>` into `<results>`, in the list's
   > order, and nothing else the script reads. Never invent an edition, a year or a link: a tag
   > you could not settle is `uncertain`, with what you found. Reply "done" only.

   Wait for all of them. A list whose results file is missing is not an error: its tags stay due
   and are listed again next month.

4. **File the results** into the template, all files in one command:

   ```
   $CME central-checks --results /tmp/gc-lists/international_results_1.md --results /tmp/gc-lists/europe_results_1.md …
   ```

   (one `--results` per entry of `checkers`; the set is read from the file's name). It files
   each `Tag:` line as checked today, gives a superseded tag's successor a record of its own,
   validates the result and only then writes `templates/guideline_checks.json`. The output has
   `filed` (counts by status per set), `unreadable` (lines it could not read), `not_listed`
   (tags not on that file's list: skipped, never recorded) and `files_missing`. If it refuses ("unable to ship"), nothing was written: see "When something
   fails".

5. **Run the tests.**

   ```
   $CME central-checks --validate
   python3 -m pytest -q -n auto tests          # or without -n auto when pytest-xdist is missing
   ```

   Both must pass. The only file that should have changed is the template:
   `git status --short` lists `plugins/clinical-cme/skills/clinical-cme/templates/guideline_checks.json`
   and nothing else.

6. **Commit to `main` and push**, with a summary in the message:

   ```
   git add plugins/clinical-cme/skills/clinical-cme/templates/guideline_checks.json
   git commit -m "Central guideline checks <YYYY-MM-DD>: <n> tags checked" -m "<summary>"
   git push origin main
   ```

   The summary lists, per set: tags checked, counts by status, every tag found **superseded**
   (with its successor) or **changed**, the `uncertain` ones by name, lines unreadable, results
   files missing, and how many tags are still due (`$CME central-checks` alone prints it). Because
   `plugin.json` has no version, this commit reaches every install at its next plugin update.
   Do not tag, release or bump the skill version: releasing is the owner's.

   Finish with a short reply giving the same summary. When nothing was due, reply "Central
   guideline checks: nothing due." and commit nothing.

## When something fails

- `--validate` fails at step 1: someone edited the template by hand. Do not repair it by
  guesswork; reply with the problems it printed and stop. (The owner fixes it in a normal commit.)
- `--results` refuses at step 4: a results line would break the file (for example a successor
  chain that loops back). Find the line in the results file named by the error, change its status
  to `uncertain` with a note saying why, and run step 4 again. Never edit the template by hand.
- Tests fail at step 5: do not commit. Reply with the failing test names and stop. Check that you
  did not leave other changes in the tree (`git status`); `git checkout -- <file>` restores the
  template if you need to start again.
- `git push` is refused because `main` moved: `git pull --rebase`. If it stops on a conflict
  (the template changed on `main` too), do not resolve it by hand: `git rebase --abort`, then
  `git reset --hard origin/main`, and start again from step 1 on the new `main`. Keep the
  results files in `/tmp/gc-lists`: after step 1, go straight to step 4 with them (tags no longer
  on a list are skipped and reported as `not_listed`). After any rebase, clean or not, run
  step 5 (validate and the tests) again before `git push`.

## Adding a region set

When enough learners use a region the sets do not cover, add a set to
`templates/guideline_checks.json`: a new key under `sets` with `regions` (its names and aliases;
a name must not belong to another set), `about`, `updated` and `records` (`[]`, or a copy of the
closest set's records if those were checked for it too). `$CME central-checks --validate`, the
tests, and a commit as above. The next monthly run checks all its tags; a learner whose region
reads the new set stops sweeping the default blueprint's tags at their next preparation. A learner
whose region is `<country>/<family>` reads the family's set (`Norway/Europe` → Europe).

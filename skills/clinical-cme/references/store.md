# The store: where the learner's ledger and log live

The skill holds no learner data. Each learner's data is one small set of JSON documents kept in
one place they own: the **store**. This file explains what the documents are, which kinds of
store there are, which tools reach them, and how to read and write them quickly without copying
data through the conversation.

## 1. The documents

| Document | Path in the store | Written by |
|---|---|---|
| Ledger (`state_schema.md` §1), ≤ ~100 KB | `data/state.json` | `cme.py save`, `close`, `place` |
| Index of sessions and reviews, for the page | `data/index.json` | `save`, `close`, `review-doc`, `place`, `reindex` |
| One round: metadata, `transcript` (part A), `closing` (part B), `addendum` | `data/sessions/S0042.json` | `save`, `close`, `addendum` |
| The page itself | `index.html` | setup; `save` when the page is out of date (§4.5) |
| A progress-review report | `data/reviews/2026-11-20.json` | `review-doc` |
| The next round, written ahead and packed: questions, case, feedback notes (`state_schema.md` §8) | `data/prepared.json` | `stash` after a close; emptied by `save` and `place` |

One more document lives outside the files: the round mix the learner sets on their page
(`state_schema.md` §7) is kept by the page as its own settings document, `cme/prefs`. The page
writes it; the skill only reads it.

Every `cme.py` command that writes prints a `files` list. Each entry has `path` (the local file
it wrote) and `as` (where it goes in the store). Put back exactly those files. Never write a
document by retyping it.

## 2. The tools

The skill runs in the Claude app. If the session loads tools on demand, search once, early, for
everything below that the session will need, and load it together.

| Tool | Used for |
|---|---|
| A shell with a writable scratch folder and Python 3.8+ | every session (`cme.py`). Without it the skill cannot run; say so. |
| List the learner's artifacts | finding "Clinical CME" |
| Read an artifact's files into local files (it returns paths, not the content) | reading the page store |
| Publish local files to an artifact, keeping the files not named ("patch"), pinned to the version you read | writing the page store |
| Read one document of the page's settings | `cme/prefs`, the round mix set on the page |
| The file system, or a connected folder on the learner's computer | the folder store |
| Attachments and downloads | files carried by the learner; recovery |

A tool that only reads a document *into the conversation*, or only writes from text you type
into the call, does **not** count. Reading the ledger into the conversation shows the learner's
schedule before the round (it breaks blinding), and retyping it corrupts it. If that is all the
session has for the page, run the round from a folder or from carried files (§4.3).

## 3. The kinds of store

Pick the first one the session can do **and** that holds this learner's data.

- **The page** (preferred). The learner's private artifact page "Clinical CME" holds the data as
  files under `data/`, next to the page itself. One read call fetches the ledger and index into
  local files; one publish call saves the ledger, the session document and the index together,
  atomically, refused if another device saved in between. The page reads the same files. Works
  on any device where the learner is signed in.
- **A folder** the session can read and write as files: its own file system, or a connected
  folder on the learner's computer. Same `data/…` layout inside a folder the learner names, for
  example `Clinical CME/`.
- **Files carried by the learner.** At the start the learner attaches `state.json` and
  `index.json`; at the end you hand back the files `cme.py` wrote and ask them to keep them,
  replacing the old ones, and to attach them next time. Slowest for the learner; use it when
  nothing else works.

**Which store holds this learner's data?**

1. If the learner gave a link or a folder, use it.
2. Otherwise list their artifacts and look for the title **Clinical CME**. Found, with a file
   `data/state.json` (list its files, or try reading it) → the page.
3. Not found, and no folder or files offered → ask once: "Paste the link of your Clinical CME
   page, tell me the folder your CME files are in, attach your `state.json`, or say 'set up' if
   this is your first time." Never create a second ledger silently.

**Mismatch.** If the learner's store is one this session cannot reach file to file, say so in
one or two plain sentences: what this session cannot do, and where the round can be run and
saved (the app where they ran the last session). Offer a carried-over round instead: run the
round now from an exported or attached ledger, hand back the files, and save them into the
store next time (§4.3, "Carry-over"). Never write a second copy somewhere else on your own.

## 4. Reading and writing

Note the version or file timestamp of what you read; it pins the write.

### 4.1 The page

- **Read** (session start; one call): the read-files tool with the paths `data/state.json`,
  `data/index.json`, `data/prepared.json` and `index.html`, asking for them as saved local
  files. Copy the saved files to `<work>/store/state.json`, `<work>/store/index.json`,
  `<work>/store/prepared.json` and `<work>/store/index.html`. A store last saved by a version
  before 4.3 has no `data/prepared.json`: if the read is refused because of it, repeat the read
  without that path and run `start` all the same (a missing file simply means no prepared
  round). In the
  same parallel batch, read the page's settings document `cme/prefs` (a few bytes of settings,
  safe to see). Missing, or no tool that reads it → no page settings this session. The saved names are chosen by the
  client: match each to its artifact path by the line that reports it, or by the sha256 or size
  the result lists for each path (`sha256sum` confirms). Note the artifact version the result reports. If the read returns content into the
  conversation instead of saving files, stop using that tool for the ledger.
- **Write**: one publish call with every entry of the `files` list that `cme.py` printed
  (`as` → served path, `path` → local file), keeping the other files (patch mode), pinned to the
  version you read. The new version in the result is the proof; keep it for the next write.
- **Conflict** (the version moved: another device saved): read both files again, re-run the
  same `cme.py` command on the fresh files with the same inputs, publish again. Once. If it
  fails again, follow §6.

### 4.2 A folder

Copy the files into the folder at their `as` paths: session and review files first, then
`data/index.json` and `data/prepared.json`, then `data/state.json` last (so an interrupted save never leaves a ledger
that points to a missing log entry). Before overwriting `state.json`, check its `gen` is still
the one you read; if it moved, re-read and re-run as for the page.

### 4.3 Files carried by the learner, and carry-over

- **Read**: the attached `state.json` (and `index.json` if attached; `cme.py` rebuilds what is
  missing from the ledger). Copy them into `<work>/store/`. No round is prepared ahead in a
  carried store: leave `data/prepared.json` out of what you hand back.
- **Write**: hand back `state.json`, `index.json` and the new session file as downloads, with
  one line: "Keep these three files together, replacing the old ones; attach `state.json` and
  `index.json` next time."
- **Carry-over into the page or a folder**: when attached files have a higher `gen` than the
  store, check with the learner, then save them into the store as a normal write (§4.1–4.2), plus any
  session files they attach.

### 4.4 Rules for every store

- **Never read the ledger into the conversation and never retype it.** Use files.
- **Blinding**: tool-call descriptions stay neutral before the answers are in ("Read the
  ledger", "Save the round").
- **One store per learner.** The store kind lives in the learner's head and the page, not in the
  ledger; never start a second one.
- **Save once per step.** `save` after the final feedback, `close` after the reflection,
  `stash` after the close (one small file, which does not touch the ledger). `save --work`
  always starts from the ledger as it was read, so it can be run again after fixing a
  warning; never run `save` on a ledger that `save` wrote.
- **The prepared round is sealed.** Read `data/prepared.json` into a file and hand it to
  `start`; never open it in the conversation.

### 4.5 Updating the page (once per skill version)

`save` (and `place`) compare the learner's `index.html` with this skill's template and, when it
is older, add the new `index.html` to `files`. Before the publish that carries it:

1. Check what the page has declared it uses. It needs `db` and `user` (for the round-mix
   switches) and `downloads` (for Export): `{"db": {}, "user": {}, "downloads": {}}`. If one is
   missing, declare the full set first, keeping anything else declared; that makes a new
   version, so pin the publish to it. If the session cannot declare them, publish anyway: the
   page then shows the mix and says to change it in a chat.
2. Publish `index.html` with the other files in the same call, as usual.
3. Tell the learner in one line after the close: "Your Clinical CME page was updated: it no
   longer lists open gaps or upcoming topics, so rounds stay blind; your sessions, scores and
   progress are all still there."

A folder: copy `index.html` into it like the other files. Carried files: no page; skip.

## 5. Setup (new learner, the page where possible)

After the onboarding questions (`onboarding.md` §2):

1. `python3 cme.py init --profile '<json>' --config '<json>' --blueprint <skill>/templates/blueprint.json
   --out <work>/state.json` (or a blueprint drafted for the learner's specialty in the same JSON
   shape, or as Markdown like `templates/blueprint.md`: `init` accepts both), then
   `python3 cme.py place <work>/state.json --out-dir <work>/out0`.
2. **The page**: copy `templates/page.html` to `<work>/out0/index.html`. Create a new artifact
   in one publish with `index.html` and the files from `place`, titled **Clinical CME**, with a
   generic icon (a stethoscope or similar) and the description "Your clinical CME ledger and
   session log." Then declare what the page uses: `downloads` (its Export button), `db` and
   `user` (the round-mix switches in Settings): `{"db": {}, "user": {}, "downloads": {}}`. Pin
   the page if the app can.
   **A folder**: copy `out0/data/` into the folder the learner names. **Carried files**: hand
   back the files.
3. Tell the learner in two lines where their data is. For the page: it is theirs and private;
   the skill finds it by its title, so keep the title. Then offer the first round.

If an artifact titled Clinical CME already exists, reuse it (never create a second one): read
its store and continue, or start a fresh ledger in it only if the learner asks to start over.

## 6. Recovery

- **A save was refused twice, or the store tool failed**: say so plainly, do not report the
  round as saved, and hand the learner the files from the last `save`/`close` output folder
  (state, index, session file) as downloads. At the next session, save them as a carry-over
  (§4.3) after checking their `gen` is higher than the store's.
- **Session saved without a reflection** (the learner left after the feedback): nothing to do.
  `start` reports `last_session.unreflected`; the next `save` finalises it as "reflection
  skipped". If the learner wants to add the reflection at the start of the next session
  (the snapshot is still in the ledger): read that session's file into
  `<work>/store/sessions/`, add the reflection with `cme.py answer --part reflection`, write
  `reflection.json` and `B.md`, run `cme.py close --work <work>` and save its files; then run
  `start <work>/out2/data/state.json --work <work>` for today's round as usual (`start` sets
  the closed round's files aside).
- **The artifact cannot be found**: ask for the link. Never create a second ledger silently.
- **The index is missing or damaged**: `cme.py` rebuilds what it can from the ledger on the next
  save; `cme.py reindex <folder>` rebuilds it fully from the session files.
- **The ledger is damaged** (a command reports invalid JSON): ask whether they have a recent
  `state.json` from a failed save, or an export from the page's Export button (`python3 cme.py
  import <export> --out-dir <work>/restore` turns it back into the files); otherwise rebuild from the session files (they
  hold scores, topics and tags) with `init` and a hand-built round per session, and say plainly
  what will be lost (step counts, exact due dates).

## 7. Export

"Give me my data": collect `data/` (the page: read all files listed under `data/` into local
files; a folder: the folder itself) and package it as a zip download.
The page's Export button gives the same as one JSON file.

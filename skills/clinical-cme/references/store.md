# The store: where the learner's ledger and log live

The skill holds no learner data. Each learner's data is one small set of JSON documents kept in
one place they own: the **store**. This file explains what the documents are, which kinds of
store there are, which tools reach them, and how to read and write them quickly without copying
data through the conversation.

**Not before the first message of a round.** When the learner's store is the page and it reads
without trouble, SKILL.md turn 1 has all a session start needs: list, read, `start`, send.
Open this file before that message only when a step there fails or the store is another kind
(§3); read §4 behind the scenes afterwards, before the first publish.

## 1. The documents

| Document | Path in the store | Written by |
|---|---|---|
| Ledger (`state_schema.md` §1), ≤ ~100 KB | `data/state.json` | `cme.py save`, `close`, `settings`, `theme`, `review`, `init` |
| Page file: exactly what the page may show, already blinded (`state_schema.md` §7) | `data/page.json` | every command that writes the ledger; `review-doc`; `rebuild-page` |
| One round: metadata, `transcript` (part A), `closing` (part B), `addendum` | `data/sessions/S0042.json` | `save`, `close`, `addendum` |
| The page itself | `index.html` | `init`; any command that writes the ledger, when the page is out of date (§4.5) |
| A progress-review report | `data/reviews/2026-11-20.json` | `review-doc` |
| The next round, written ahead and packed: questions, case, feedback notes (`state_schema.md` §8) | `data/prepared.json` | `finish-prepare`; who empties it: `state_schema.md` §8 |

The page renders `data/page.json` and nothing else of the store (it opens a session or review
document when the learner clicks one; only its Export button reads the ledger). A store last
saved before version 5.1 has `data/index.json` in its place: §6.

One more document lives outside the files: the round mix the learner sets on their page
(`state_schema.md` §7.1) is kept by the page as its own settings document, `cme/prefs`. The page
writes it; the skill only reads it.

`cme.py` never touches the store. You read the store's files into a local folder, the **store
copy**; `cme.py open` (or `start --store`) sets up a **work folder** on it; every command that
writes puts its files into the work folder's **publish set** and prints the whole set as
`files`. Each entry has `path` (the local file) and `as` (where it goes in the store). Publish
exactly those files (§4). Never write a document by retyping it.

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
  files under `data/`, next to the page itself. One read call fetches the ledger and the page file
  into local files; one publish call saves the ledger, the session document and the page file
  together, atomically, refused if another device saved in between. The page shows the page file. Works
  on any device where the learner is signed in.
- **A folder** the session can read and write as files: its own file system, or a connected
  folder on the learner's computer. Same `data/…` layout inside a folder the learner names, for
  example `Clinical CME/`.
- **Files carried by the learner.** At the start the learner attaches `state.json` and
  `page.json`; at the end you hand back the files `cme.py` wrote and ask them to keep them,
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

Every job has the same three steps, whatever it is (a round, a settings change, preparing a
round, a review):

1. **Read** the store's files into the store copy, `<work>/store/`, and note the store's
   version (the artifact version the read reports; a folder has none).
2. **Open** the work folder on it: `python3 cme.py start --work <work> --store <work>/store
   --version <version>` for a round, `python3 cme.py open --work <work> --store <work>/store
   --version <version>` for anything else. Every later command takes only `--work <work>`.
3. **Publish** after each command that writes: every entry of the `files` it printed, in the
   order listed. The same list, with the version the store was read at, is in the file the
   command names as `publish` (`<work>/publish.json`: `{"version": …, "files": [{"as", "path"}, …]}`).
   The list is the whole publish set, not only what the last command changed: session, review
   and testing files first, then `data/page.json`, `index.html`, `data/prepared.json`, and
   `data/state.json` last. Publishing it again is harmless, and a publish that failed is
   covered by the next one.

A second job later in the same conversation starts again at step 1 with a fresh read (`open`
and `start --store` set the earlier job's files aside in `<work>/earlier/`). The exception is
a round that follows another job in the same conversation without the learner leaving (a
settings change first, or a late reflection closed first): run `start --work <work>` without
`--store`; the round continues from the ledger that job wrote.

### 4.1 The page

- **Read** (one call): the read-files tool with the paths `data/state.json`,
  `data/page.json`, `data/prepared.json` and `index.html`, asking for them as saved local
  files. Copy the saved files into `<work>/store/`: at their store paths
  (`<work>/store/data/state.json`, …) or side by side under their own names
  (`<work>/store/state.json`, `page.json`, `prepared.json`, `index.html`); `cme.py` finds
  either. An older store lacks `data/page.json` (before 5.1; read `data/index.json` in its
  place, once: §6) or `data/prepared.json` (before 4.3): if the read is refused because of a
  missing path, repeat it without that path (no page file: `cme.py` writes one at the next
  save; no prepared round: none is used). In the same parallel batch, read the page's settings document `cme/prefs`
  (a few bytes of settings, safe to see) and pass it as `--prefs`. Missing, or no tool that
  reads it → no page settings this session. The saved names are chosen by the client: match
  each to its artifact path by the line that reports it, or by the sha256 or size the result
  lists for each path (`sha256sum` confirms). Note the artifact version the result reports and
  pass it as `--version`. If the read returns content into the conversation instead of saving
  files, stop using that tool for the ledger.
- **Write**: one publish call with every entry of `files` (`as` → served path, `path` → local
  file), keeping the other files (patch mode), pinned to the version: the one in
  `publish.json` for the first publish of a job, the one the last publish returned after
  that. The new version in the result is the proof; keep it for the next write.
- **Conflict** (the version moved: another device saved): read the store again into the store
  copy, run `python3 cme.py open --work <work> --store <work>/store --version <new version>
  --reread` (it keeps the job's own files and drops what was computed from the old read), run
  the job's writing commands again in the same order (`save`, then `close`, …), publish
  again. Once. If it fails again, follow §6.

### 4.2 A folder

The folder is its own store copy: `--store <the folder>`, no `--version`. To publish, copy
each file of `files` into the folder at its `as` path, in the order listed (the ledger last,
so an interrupted save never leaves a ledger that points to a missing log entry). Before
overwriting `state.json`, check its `gen` is still the one `open` or `start` printed, or the
one your last write left; if it moved, re-read and re-run as for the page.

### 4.3 Files carried by the learner, and carry-over

- **Read**: the attached `state.json` (and `page.json` if attached; `cme.py` rebuilds what is
  missing from the ledger). Copy them into `<work>/store/` and open the work folder on it. No
  round is prepared ahead in a carried store: leave `data/prepared.json` out of what you hand
  back.
- **Write**: hand back `state.json`, `page.json` and the new session file from `files` as
  downloads, with one line: "Keep these three files together, replacing the old ones; attach
  `state.json` and `page.json` next time."
- **Carry-over into the page or a folder**: when attached files have a higher `gen` than the
  store, check with the learner, then save them into the store as a normal write (§4.1–4.2), plus any
  session files they attach.

### 4.4 Rules for every store

- **Never read the ledger into the conversation and never retype it.** Use files.
- **Blinding**: tool-call descriptions stay neutral before the answers are in ("Read the
  ledger", "Save the round").
- **One store per learner.** The store kind lives in the learner's head and the page, not in the
  ledger; never start a second one.
- **Publish once per step.** After `save` (the final feedback), after `close` (the
  reflection), after `finish-prepare` (the next round). `save` always starts from the ledger
  as it was before the round, so it can be run again after fixing a warning.
- **The prepared round is sealed.** Read `data/prepared.json` into the store copy; `start`
  finds it there. Never open it in the conversation.

### 4.5 Updating the page (once per skill version)

Every command that writes the ledger compares the learner's `index.html` (in the store copy)
with this skill's template and, when it is older, adds the new `index.html` to the publish
set (`page_upgraded` in its output). Before the first publish that carries it:

1. Check what the page has declared it uses. It needs `db` and `user` (for the round-mix
   switches) and `downloads` (for Export): `{"db": {}, "user": {}, "downloads": {}}`. If one is
   missing, declare the full set first, keeping anything else declared; that makes a new
   version, so pin the publish to it. If the session cannot declare them, publish anyway: the
   page then shows the mix and says to change it in a chat.
2. Publish `index.html` with the other files in the same call, as usual.
3. Tell the learner in one line after the close: "Your Clinical CME page was updated: it
   shows your sessions, scores and progress as before, never what a coming round will test,
   and its time estimates are now realistic (about 5 minutes per MCQ, 10 per focused question,
   25 for a case)."

A folder: copy `index.html` into it like the other files. Carried files: no page; skip.

## 5. Setup (new learner, the page where possible)

After the onboarding questions (`onboarding.md` §2):

1. `python3 cme.py init --work <work> --profile '<json>' --config '<json>' --blueprint
   <skill>/templates/blueprint.json` (or a blueprint drafted for the learner's specialty in the
   same JSON shape, or as Markdown like `templates/blueprint.md`: `init` accepts both). The
   work folder needs no store yet: `init` writes the first ledger, the page file and the page
   (`index.html`) into the publish set and prints them as `files`.
2. **The page**: create a new artifact in one publish with those `files`, titled **Clinical
   CME**, with a generic icon (a stethoscope or similar) and the description "Your clinical
   CME ledger and session log." Then declare what the page uses: `downloads` (its Export
   button), `db` and `user` (the round-mix switches in Settings): `{"db": {}, "user": {},
   "downloads": {}}`. Pin the page if the app can.
   **A folder**: copy the `files` into the folder the learner names, at their `as` paths.
   **Carried files**: hand back the files.
3. Tell the learner in two lines where their data is. For the page: it is theirs and private;
   the skill finds it by its title, so keep the title. Then offer the first round: `start
   --work <work>` in the same work folder, pinning its publishes to the version the creating
   publish returned.

If an artifact titled Clinical CME already exists, reuse it (never create a second one): read
its store and continue, or start a fresh ledger in it only if the learner asks to start over
(`open` on its store, then `init --work <work> … --start-over`).

## 6. Recovery

- **A save was refused twice, or the store tool failed**: say so plainly, do not report the
  round as saved, and hand the learner the files of the publish set (`files`: state, page file,
  session file) as downloads. At the next session, save them as a carry-over
  (§4.3) after checking their `gen` is higher than the store's.
- **Session saved without a reflection** (the learner left after the feedback): nothing to do.
  `start` reports `last_session.unreflected`; the next `save` finalises it as "reflection
  skipped". If the learner wants to add the reflection at the start of the next session
  (the snapshot is still in the ledger): read that session's file into the store copy with the
  rest (`data/sessions/<id>.json`), `open` the work folder, add the reflection with `cme.py
  answer --part reflection`, write `reflection.json` and `B.md`, run `cme.py close --work
  <work>` and publish its `files`; then run `start --work <work>` (no `--store`) for today's
  round as usual: it continues from the closed ledger and sets the closed round's files aside.
- **The artifact cannot be found**: ask for the link. Never create a second ledger silently.
- **The page file is missing or damaged** (the page shows nothing, or lacks sessions): `cme.py`
  writes it again from the ledger on the next save; sessions too old for the ledger to list
  come back with `python3 cme.py rebuild-page <folder>`, which rebuilds `data/page.json` from
  the session and review files and the ledger of a folder in the store's layout (publish the
  file it prints).
- **A store from before version 5.1** has `data/index.json` and no `data/page.json`. Nothing to
  do: read `data/index.json` with the ledger that once, and the next save writes the page
  file with the index's entries in it and the new page with it. Until then the new page lists
  the sessions of the old index and says the rest comes with the next round. `data/index.json`
  is not written any more; it can stay in the store or be deleted.
- **The ledger is damaged** (a command reports invalid JSON): ask whether they have a recent
  `state.json` from a failed save, or an export from the page's Export button (`python3 cme.py
  import <export> --out-dir <work>/restore` turns it back into the files); otherwise rebuild from the session files (they
  hold scores, topics and tags) with `init` and a hand-built round per session, and say plainly
  what will be lost (step counts, exact due dates).

## 7. Export

"Give me my data": collect `data/` (the page: read all files listed under `data/` into local
files; a folder: the folder itself) and package it as a zip download.
The page's Export button gives the same as one JSON file. Either is a full backup with the
ledger in it, so say in one line that it shows open gaps and when topics come back: best left
unopened by a learner who wants the rounds to stay blind (the page says so before it
downloads).

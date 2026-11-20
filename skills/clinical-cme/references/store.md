# The store: where the learner's ledger and log live

The skill holds no learner data. Each learner's data is one small set of JSON documents kept in
one place they own: the **store**. This file explains what the documents are, which kinds of
store work, how to find the tools that reach them in whatever assistant and app you are running
in, and how to read and write them quickly without copying data through the conversation.

Nothing here depends on a particular tool name. Tool names differ between assistants, apps and
versions. Find tools by what they do (§2). The examples in brackets describe the kind of tool to
look for; they are not names to call.

## 1. The documents

| Document | File store path | Database path | Written by |
|---|---|---|---|
| Ledger (`state_schema.md` §1), ≤ ~100 KB | `data/state.json` | `cme/state` | `cme.py save`, `close`, `place` |
| Index of sessions and reviews, for the page | `data/index.json` | — (not needed) | `save`, `close`, `review-doc`, `place`, `reindex` |
| One round: metadata, `transcript` (part A), `closing` (part B), `addendum` | `data/sessions/S0042.json` | `sessions/S0042` | `save`, `close`, `addendum` |
| Round mix set on the page (`state_schema.md` §7) | — | `cme/prefs` (page database, all stores with a page) | the page; read by the skill, never written by it |
| The page itself | `index.html` | — | setup; `save` when the page is out of date (§4.6) |
| A progress-review report | `data/reviews/2026-11-20.json` | `reviews/2026-11-20` | `review-doc` |
| The next round, written ahead and packed: questions, case, feedback notes (`state_schema.md` §8) | `data/prepared.json` | `cme/prepared` | `stash` after a close; emptied by `save` and `place` |

Every `cme.py` command that writes prints a `files` list. Each entry has `path` (the local file
it wrote), `as` (where it goes in a file store) and `db_path` (where it goes in a database
store). Put back exactly those files. Never write a document by retyping it.

## 2. Find the tools: capabilities, not names

Before saying a capability is missing, look at every tool this session offers, judged by its
description. If the session can load more tools on demand (a tool-search or "load tools"
facility), search once with plain keywords such as "artifact files", "publish files",
"artifact database", "list artifacts", "send message", "web search" and "schedule". Load
everything you expect to need in that one search.

| Capability | What it looks like | Used for |
|---|---|---|
| **Run code and keep files** | a shell or code runner with a writable scratch folder, Python 3.8+ | every session (`cme.py`). Without it the skill cannot run; say so. |
| **List the learner's artifacts** (pages hosted in their account) | lists or searches their artifacts by title | finding "Clinical CME" |
| **Read artifact files into local files** | reads one or several of an artifact's files and *saves them as local files*, returning paths, not the content | store A, reading |
| **Publish local files to an artifact** | publishes files from local paths into an artifact, keeping the files not named ("patch"), pinned to the version you read | store A, writing |
| **Artifact database, file in / file out** | gets a database document *into a local file*; sets or updates a document *from a local file*, with a version pin | store B |
| **A folder** | the local file system of the app, or a connected folder on the learner's computer, or a cloud-drive folder whose tools copy whole files | store C |
| **Receive and send files** | the learner attaches files; you can hand files back for download | store D |

A tool that only reads a document *into the conversation*, or only writes from text you type
into the call, does **not** count as file in or file out. Reading the ledger into the
conversation shows the learner's schedule before the round (it breaks blinding), and retyping
it corrupts it. If that is all the session has for the artifact, use store C or D for this
session (§4.4).

## 3. The four kinds of store

Pick the first one the session can do **and** that holds this learner's data.

- **A. Artifact files** (preferred where available). The learner's private page "Clinical CME"
  holds the data as files under `data/`, next to the page itself. One read call fetches the
  ledger and index into local files; one publish call saves the ledger, the session document
  and the index together, atomically, refused if another device saved in between. The page
  reads the same files. Works on any device where the learner is signed in.
- **B. Artifact database** (the version-4.0 layout). The same page, with the documents in the
  page's database instead of files. Use only with file-in/file-out database tools. Learners on B
  should move to A when an app that can do A is available (§6).
- **C. A folder** the assistant can read and write as files: the app's own file system (a
  terminal agent), a connected folder on the learner's computer, or a synced cloud folder. Same
  `data/…` layout inside a folder the learner names, for example `Clinical CME/`.
- **D. Files carried by the learner.** At the start the learner attaches `state.json` and
  `index.json`; at the end you hand back the files `cme.py` wrote and ask them to keep them,
  replacing the old ones, and to attach them next time. Works with any assistant that can run
  Python and exchange files. Slowest for the learner; use it when nothing else works.

**Which store holds this learner's data?**

1. If the learner gave a link or a folder, use it.
2. Otherwise list their artifacts and look for the title **Clinical CME**. Found:
   - it has a file `data/state.json` (list its files, or try reading it) → **A**;
   - else its database has `cme/state` without a `moved_to` field → **B**;
   - its database has `cme/moved` or a `cme/state` carrying `moved_to: "files"` → **A**, even if
     this session cannot read files (then see "Mismatch" below).
3. Not found, and no folder or files offered → ask once: "Paste the link of your Clinical CME
   page, tell me the folder your CME files are in, attach your `state.json`, or say 'set up' if
   this is your first time." Never create a second ledger silently.

**Mismatch.** If the learner's store is one this session cannot reach file to file (for example
A from an app with only inline database tools), say so in one or two plain sentences: what this
app cannot do, and where the round can be run and saved (the app where they ran the last
session, or any app that can read artifact files). Offer a carried-over round instead: run the
round now from an exported or attached ledger (D), hand back the files, and save them into the
store next time from an app that can (`store.md` §4.4, "Carry-over"). Never write a second copy
somewhere else on your own.

## 4. Reading and writing

Note the version or file timestamp of what you read; it pins the write.

### 4.1 Store A, artifact files

- **Read** (session start; one call): the read-files tool with the paths `data/state.json`,
  `data/index.json`, `data/prepared.json` and `index.html`, asking for them as saved local
  files. Copy the saved files to `<work>/store/state.json`, `<work>/store/index.json`,
  `<work>/store/prepared.json` and `<work>/store/index.html`. A store last saved by a version
  before 4.3 has no `data/prepared.json`: if the read is refused because of it, repeat the read
  without that path and run `start` all the same (a missing file simply means no prepared
  round). In the
  same parallel batch, read the page-database document `cme/prefs` (a database "get one
  document" tool; its data is a few bytes of settings, safe to see). Missing, or no database
  tool → no page settings this session. The saved names are chosen by the
  client: match each to its artifact path by the line that reports it, or by the sha256 or size
  the result lists for each path (`sha256sum` confirms). Note the artifact version the result reports. If the read returns content into the
  conversation instead of saving files, stop using that tool for the ledger.
- **Write**: one publish call with every entry of the `files` list that `cme.py` printed
  (`as` → served path, `path` → local file), keeping the other files (patch mode), pinned to the
  version you read. The new version in the result is the proof; keep it for the next write.
- **Conflict** (the version moved: another device saved): read both files again, re-run the
  same `cme.py` command on the fresh files with the same inputs, publish again. Once. If it
  fails again, follow §8.

### 4.2 Store B, artifact database

- **Read**: get `cme/state` into a local file; note its version. (No index is needed.) In the
  same batch, get `cme/prefs` if it exists (page settings, §1) and `cme/prepared` into
  `<work>/store/prepared.json` if it exists and can be saved to a file.
- **Write**: set `cme/state` from `data/state.json` pinned to the version read; set
  `sessions/<id>` from the session file (a new document, no pin). After the reflection, update
  `sessions/<id>` from the `db_update` file `close` printed (`B.json`), pinned to the version the
  first write returned. Review reports: set `reviews/<date>` from the review file. Skip
  `data/index.json`. Set `cme/prepared` from `data/prepared.json` whenever it is in `files`.
- **Conflict**: as in A.

### 4.3 Store C, a folder

Copy the files into the folder at their `as` paths: session and review files first, then
`data/index.json` and `data/prepared.json`, then `data/state.json` last (so an interrupted save never leaves a ledger
that points to a missing log entry). Before overwriting `state.json`, check its `gen` is still
the one you read; if it moved, re-read and re-run as in A.

### 4.4 Store D, files carried by the learner, and carry-over

- **Read**: the attached `state.json` (and `index.json` if attached; `cme.py` rebuilds what is
  missing from the ledger). Copy them into `<work>/store/`. No round is prepared ahead in a
  carried store: leave `data/prepared.json` out of what you hand back.
- **Write**: hand back `state.json`, `index.json` and the new session file as downloads, with
  one line: "Keep these three files together, replacing the old ones; attach `state.json` and
  `index.json` next time."
- **Carry-over into A, B or C**: when attached files have a higher `gen` than the store, check
  with the learner, then save them into the store as a normal write (§4.1–4.3), plus any
  session files they attach.

### 4.5 Rules for every store

- **Never read the ledger into the conversation and never retype it.** Use files.
- **Blinding**: tool-call descriptions stay neutral before the answers are in ("Read the
  ledger", "Save the round").
- **One store per learner.** The store kind lives in the learner's head and the page, not in the
  ledger; never start a second one.
- **Save once per step.** `save` after the final feedback, `close` after the reflection,
  `stash` after the close (one small file, which does not touch the ledger). Never run `save`
  twice on the same ledger file.
- **The prepared round is sealed.** Read `data/prepared.json` into a file and hand it to
  `start`; never open it in the conversation.

### 4.6 Updating the page (once per skill version)

`save` (and `place`) compare the learner's `index.html` with this skill's template and, when it
is older, add the new `index.html` to `files`. Before the publish that carries it:

1. Check the page's declared capabilities (a "read declaration" tool). The page needs the
   database and user capabilities (for the round-mix switches) and downloads (for Export):
   for example `{"db": {}, "user": {}, "downloads": {}}`. If one is missing, declare the full set
   first, keeping anything else declared; that makes a new version, so pin the publish to it.
   If this app cannot declare capabilities, publish anyway: the page then shows the mix and
   says to change it in a chat.
2. Publish `index.html` with the other files in the same call, as usual.
3. Tell the learner in one line after the close: "Your Clinical CME page was updated: it no
   longer lists open gaps or upcoming topics, so rounds stay blind; your sessions, scores and
   progress are all still there."

Store C: copy `index.html` into the folder like the other files. Store D: no page; skip.

## 5. Setup (new learner, store A where possible)

After the onboarding questions (`onboarding.md` §2):

1. `python3 cme.py init --profile '<json>' --config '<json>' --blueprint <skill>/templates/blueprint.json
   --out <work>/state.json` (or a blueprint drafted for the learner's specialty in the same JSON
   shape, or a Markdown blueprint in the version-3 format: `init` accepts both), then
   `python3 cme.py place <work>/state.json --out-dir <work>/out0`.
2. **Store A**: copy `templates/page.html` to `<work>/out0/index.html`. Create a new artifact in
   one publish with `index.html` and the files from `place`, titled **Clinical CME**, with a
   generic icon (a stethoscope or similar) and the description "Your clinical CME ledger and
   session log." Then declare the page's capabilities: downloads (the page's Export button),
   database and user (the round-mix switches in Settings; the page also still reads older
   database stores), for example `{"db": {}, "user": {}, "downloads": {}}`. If a
   database tool can write a small document, also set `cme/moved` to
   `{"store": "files", "since": "<date>"}` so an older copy of the skill does not start a
   database ledger beside the files. Pin the page if the app can.
   **Store C**: copy `out0/data/` into the folder the learner names. **Store D**: hand back the
   files.
3. Tell the learner in two lines where their data is. For A: the page is theirs and private;
   the skill finds it by its title, so keep the title. Then offer the first round.

If an artifact titled Clinical CME already exists, reuse it (never create a second one): read
its store and continue, or start a fresh ledger in it only if the learner asks to start over.

## 6. Moving a version-4.0 database store (B) to files (A)

Do this once, when a learner on B uses an app that can do A. It takes two or three minutes.

1. **Get everything as files**, either way:
   - if this app can read database documents into files: save `cme/state`, the whole
     `sessions` collection and the whole `reviews` collection into `<work>/db/` (as
     `cme/state.json`, `sessions/<id>.json`, `reviews/<date>.json`);
   - otherwise ask the learner: "Open your Clinical CME page, press **Export**, and attach the
     file here." (The page's export holds the ledger, every session and every review.)
2. `python3 cme.py import <work>/db (or the attached export) --out-dir <work>/move`. Check the
   printed `gen` and `next_id` with what the page shows.
3. Copy `templates/page.html` to `<work>/move/index.html` and publish all files in
   `<work>/move` into the same artifact (patch mode, pinned to its current version). In batches
   if there are more files than one publish allows; the ledger and index go in the last batch.
4. Mark the database as moved so nothing writes there again: set `cme/moved` to
   `{"store": "files", "since": "<date>", "gen": <gen>}` if any database tool can write a small
   document. Do not delete the database documents; they are the backup.
5. Tell the learner in one line that their data now lives in the page's files, and that the
   page looks the same.

## 7. Migration from version 3 (ledger in Google Drive or on a computer)

Version 3 kept a journal (`CME ledger journal`, a Google Doc) or `learner_ledger.json` in a
folder. Migrate once, in a session with access to that drive or folder (or with the files
attached):

1. **Get the version-3 ledger as a file.**
   - Google Drive: with the drive's search tool find `CME ledger journal` (titles containing it)
     and read each volume's text into a local file. If the drive tool returns the text inside the
     conversation rather than as a saved file, prefer its export/download function to a file.
     Then `python3 cme.py unescape <saved file> --out <work>/journal.txt` (undoes Markdown
     escaping some drive tools add; harmless on plain text) and
     `python3 <skill>/legacy/cme_gdrive.py journal-replay <work>/journal.txt --out <work>/ledger_v3.json`.
   - Computer folder or attachment: `learner_ledger.json` is the ledger; run
     `python3 <skill>/legacy/cme_ledger.py migrate <copy>` first if it is older than version 3.
2. **Blueprint.** Read the learner's `Curriculum blueprint` document the same way (or
   `curriculum_blueprint.md`), unescape it, and pass it as `--blueprint` (Markdown is accepted).
   Without one, use `templates/blueprint.json`.
3. `python3 cme.py migrate-v3 <work>/ledger_v3.json --blueprint <bp> --out <work>/state.json
   --sessions-dir <work>/v3/data/sessions`. It keeps topics, due dates, gaps, every session's
   coded results and the links to the old session documents, and writes one session file per
   past session (metadata and link, no transcript). Then copy `state.json` to
   `<work>/v3/data/state.json` and run `python3 cme.py reindex <work>/v3`.
4. Set up the store as in §5, publishing or copying everything in `<work>/v3/data` instead of
   the files from `place`.
5. **Transcripts** (optional, offer it): for each old session document, read its text into a
   file, `python3 cme.py unescape <file> --out t.md`, then
   `python3 cme.py doc --part A --md t.md --id S00xx --out d.json`, merge `transcript` from
   `d.json` into the session file, and save the session files in batches.
6. Leave the old files where they are and tell the learner they are no longer updated. Do not
   delete anything.

## 8. Recovery

- **A save was refused twice, or the store tool failed**: say so plainly, do not report the
  round as saved, and hand the learner the files from the last `save`/`close` output folder
  (state, index, session file) as downloads. At the next session, save them as a carry-over
  (§4.4) after checking their `gen` is higher than the store's.
- **Session saved without a reflection** (the learner left after the feedback): nothing to do.
  `start` reports `last_session.unreflected`; the next `save` finalises it as "reflection
  skipped". If the learner wants to add the reflection at the start of the next session, run
  `cme.py close` on it before planning (the snapshot is still in the ledger), with that
  session's file as `--doc`.
- **The artifact cannot be found**: ask for the link. Never create a second ledger silently.
- **The index is missing or damaged**: `cme.py` rebuilds what it can from the ledger on the next
  save; `cme.py reindex <folder>` rebuilds it fully from the session files.
- **The ledger is damaged** (a command reports invalid JSON): ask whether they have a recent
  `state.json` from a failed save or an export; otherwise rebuild from the session files (they
  hold scores, topics and tags) with `init` and a hand-built round per session, and say plainly
  what will be lost (step counts, exact due dates).

## 9. Mirror to Google Drive (optional)

Some learners want each session as a Google Doc as well. With `config.mirror = "gdrive"` and a
Google Drive tool that can create documents from HTML, at the close of a session:

1. Folder: the ledger's `mirror` settings hold `{"folder_id", "sessions_folder_id"}` once
   created (`cme.py settings --config '{"mirror_ids": {…}}'`); create a `CME` folder with a
   `Sessions` subfolder once if missing.
2. Write the session as simple HTML (`h2`/`h3`, `p`, `ul`, `ol`, `b`, `i`, `table`, `a`; escape
   `&`, `<`, `>`) from the session file, in Python, and create the document from that file,
   titled `S0042 · 2026-10-26 · <title>`.
3. Put the document's link into the session file (`"url"`) and save it at the next write.

The mirror is a copy. It costs one extra call and is never read by the skill.

## 10. Export

"Give me my data": collect `data/` (store A: read all files listed under `data/` into local
files; B: get the three collections into files; C: the folder) and package it as a zip download.
The page's Export button gives the same as one JSON file.

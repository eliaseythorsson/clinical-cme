# The store: where the learner's ledger and log live

The skill holds no learner data. Each learner's data is one small set of JSON documents kept in
one place they own: the **store**. This file explains what the documents are, which kinds of
store there are, which tools reach them, and how to read and write them quickly without copying
data through the conversation.

**Not before the first message of a round.** When the learner's store is the page and it reads
without trouble, SKILL.md turn 1 has all a session start needs: list, read, `start`, send.
Open this file before that message only when a step there fails or the store is another kind
(§3); read `publishing.md` behind the scenes afterwards, before the first publish.

## 1. The documents

| Document | Path in the store | Written by |
|---|---|---|
| Ledger (`state_schema.md` §1), ≤ ~100 KB | `data/state.json` | `cme.py save`, `close`, `settings`, `theme`, `review`, `init` |
| Page file: exactly what the page may show, already blinded (`state_schema.md` §7) | `data/page.json` | every command that writes the ledger; `review-doc`; `rebuild-page` |
| One round: metadata, `transcript` (part A), `closing` (part B), `addendum` | `data/sessions/S0042.json` | `save`, `close`, `addendum` |
| The page itself | `index.html` | `init`; any command that writes the ledger, when the page is out of date (`publishing.md` §5) |
| A progress-review report | `data/reviews/2026-11-20.json` | `review-doc` |
| The next round, written ahead and packed: questions, case, feedback notes (`state_schema.md` §8) | `data/prepared.json` | `finish-prepare`; who empties it: `state_schema.md` §8 |
| The guideline tags' check records (`state_schema.md` §10): read only to prepare a round and at a review | `data/guidelines.json` | `finish-prepare`, `tag-checks` |

The page renders `data/page.json` and nothing else of the store (it opens a session or review
document when the learner clicks one; only its Export button reads the ledger). A store last
saved before version 5.1 has `data/index.json` in its place: §6.

One more document lives outside the files: the round mix the learner sets on their page, and
either of their two paragraphs when they rewrite it there (`state_schema.md` §7.1), is kept by the page as its own settings document, `cme/prefs`. The page
writes it; the skill only reads it.

The engine handles the store; you only carry files. You read the store's files into a local
folder, the **store copy** (any names: `cme.py` recognises each document by its content);
`cme.py open` (or `start --store`) sets up a **work folder** on it; every command that writes
puts its files into the work folder's **publish set** and prints the whole set as `files`
(`path`: the local file, `as`: where it goes). A page: publish exactly those files. A folder:
`cme.py publish` writes them itself. Never write a document by retyping it.

## 2. The tools

The skill runs in the Claude app. If the session loads tools on demand, search once, early, for
everything below that the session will need, and load it together.

| Tool | Used for |
|---|---|
| A shell with a writable scratch folder and Python 3.8+ | every session (`cme.py`). Without it the skill cannot run; say so. |
| List the learner's artifacts | finding "Clinical CME" |
| Read an artifact's files into local files (it returns paths, not the content) | reading the page store |
| Publish local files to an artifact, keeping the files not named ("patch"), pinned to the version you read | writing the page store |
| Read one document of the page's settings | `cme/prefs`, the round mix and the paragraphs set on the page |
| The file system, or a connected folder on the learner's computer | the folder store |
| Attachments and downloads | files carried by the learner; recovery |

A tool that only reads a document *into the conversation*, or only writes from text you type
into the call, does **not** count. Reading the ledger into the conversation shows the learner's
schedule before the round (it breaks blinding), and retyping it corrupts it. If that is all the
session has for the page, run the round from a folder or from carried files (`publishing.md` §3).

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
store next time (`publishing.md` §3, "Carry-over"). Never write a second copy somewhere else on your own.

## 4. Reading and writing

How every job reads the store and publishes what it wrote (the page, a folder, carried files,
the rules for every store, updating the page): `publishing.md`.

## 5. Setup (new learner, the page where possible)

After the onboarding questions (`onboarding.md` §2):

1. `python3 cme.py --today <date> init --work <work> --profile '<json>' --config '<json>' --blueprint
   <skill>/templates/blueprint.json` (or a blueprint drafted for the learner's specialty in the
   same JSON shape, or as Markdown like `templates/blueprint.md`: `init` accepts both). The
   work folder needs no store yet: `init` writes the first ledger, the page file and the page
   (`index.html`) into the publish set and prints them as `files`.
2. **The page**: create a new artifact in one publish with those `files`, titled **Clinical
   CME**, with a generic icon (a stethoscope or similar) and the description "Your clinical
   CME ledger and session log." Then declare what the page uses: `downloads` (its Export
   button), `db` and `user` (the round-mix switches in Settings): `{"db": {}, "user": {},
   "downloads": {}}`. Pin the page if the app can.
   **A folder**: `python3 cme.py publish --work <work> --to <the folder the learner names>`.
   **Carried files**: hand back the files.
3. Tell the learner in two lines where their data is. For the page: it is theirs and private;
   the skill finds it by its title, so keep the title. Then offer the first round: `start
   --work <work>` in the same work folder, pinning its publishes to the version the creating
   publish returned.

If an artifact titled Clinical CME already exists, reuse it (never create a second one): read
its store and continue, or start a fresh ledger in it only if the learner asks to start over
(`open` on its store, then `init --work <work> … --start-over`).

## 6. Recovery

- **A save was refused twice, a rebase stopped, or the store tool failed**: say so plainly, do not report the
  round as saved, and hand the learner the files of the publish set (`files`: state, page file,
  session file) as downloads. At the next session, save them as a carry-over
  (`publishing.md` §3) after checking their `gen` is higher than the store's.
- **A record saved by a newer version** (`open` reports `newer_version`, or a command stops with
  "update the plugin to continue"): another device has a newer version of the skill, and this
  one must not write the ledger. Tell the learner the line as given (`say`), and that the page,
  past cases, stats and export still work here. Nothing was written. If a round was under way
  (`save` or `close` stopped): never report it as saved; its files stay in the work folder.
  Once the plugin is updated, read the store again, run `open --work <work> --store <work>/store
  --reread` and the stopped command again, then publish. If the conversation ends before that,
  hand the learner the round's files as downloads: every file of the work folder but
  `work.json`, `publish.json` and `ledger_read.json` (not the folders `store/`, `publish/`,
  `earlier/`). At the
  next session, with the plugin updated, `open` a work folder on a fresh read, copy them into
  it and run `save` (then `close`).
- **Session saved without a reflection** (the learner left after the feedback): nothing to do.
  `start` reports `last_session.unreflected`; the next `save` finalises it as "reflection
  skipped". If the learner wants to add the reflection at the start of the next session
  (the snapshot is still in the ledger): read that session's file into the store copy with the
  rest (`data/sessions/<id>.json`), `open` the work folder, add the reflection with `cme.py
  answer --part reflection`, write `reflection.json` and `B.md`, run `cme.py close --work
  <work>` and publish its `files`; then run `--today <date> start --work <work> --utc-offset
  <H>` (no `--store`) for today's
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

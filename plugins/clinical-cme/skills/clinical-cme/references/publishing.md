# Reading and publishing the store

How every job reads the learner's store and publishes what it wrote. Read it behind the scenes
of a round's first turn, before the first publish; what the documents and the kinds of store
are, setup, recovery and export are in `store.md`.

Every job, whatever it is (a round, a settings change, preparing a round, a review):

1. **Read** the store's files into `<work>/store/` (a folder: nothing to read, the folder is its
   own store copy) and note the version the read reports.
2. **Open**: `python3 cme.py --today <date> start --work <work> --store <work>/store --version
   <version> --utc-offset <H>` for a round, `open` with the same options for anything else
   (`<date>`, `<H>`: the learner's local date and UTC offset in hours from the app's message
   timestamp, each left out when there is none; never asked). Every later command takes only
   `--work <work>`.
3. **Publish** after each command that writes (§1, §2). Publishing again is harmless; a
   publish that failed is covered by the next one.

A second job later in the same conversation starts again at step 1 with a fresh read. The
exception is a round that follows another job without the learner leaving (a settings change, a
late reflection closed first): `--today <date> start --work <work> --utc-offset <H>` without
`--store` continues from the ledger that job wrote.

## 1. The page

- **Read** (one call): the read-files tool with the paths `data/state.json`, `data/page.json`,
  `data/prepared.json` and `index.html`, as saved local files; copy them into an empty
  `<work>/store/` under any names, and always pass `--version`. A path the store lacks (an older store) → repeat the read without it.
  To prepare a round (`preparing.md` §2, `prepare_only.md` §1) or for a review, read `data/guidelines.json` too
  (a store without it has none yet); a round's start never needs it. In
  the same batch read the page's settings document `cme/prefs` and pass it as `--prefs`
  (missing → no page settings). If the read returns content into the conversation instead of
  saving files, stop using that tool for the ledger.
- **Write**: one publish call with every entry of `files` (`as` → served path, `path` → local
  file), keeping the other files (patch mode), pinned to the version: the one in
  `publish.json` for the first publish of a job, the one the last publish returned after that.
- **Refused because another device saved first**: read the same four files again into a new,
  empty folder (with `data/guidelines.json` when `files` held it; nothing more: the engine kept what else it needs, and tells from the ledger
  which of the job's writes the store already holds), run `python3
  cme.py open --work <work> --store <fresh> --version <new version> --reread`, and publish the
  `files` it prints. The engine applies the job again on the fresh store (a round recorded on
  another device meanwhile is kept, and this one renumbered after it). Its `rebased.say`, when
  not null, is one line for the learner: add it to your next message, never stop to ask. Refused
  again → `store.md` §6.

## 2. A folder

`--store <the folder>`, never `--version`: the version is what makes a store a page (`open`
prints `store_kind`). **Publish**: `python3 cme.py publish --work <work>`. The
engine writes the publish set into the folder in order and checks that no other device wrote
the ledger meanwhile; if one did, it applies the job again on the folder and writes then
(`rebased.say`: as for the page). An error → `store.md` §6. A new learner's first files: `publish --work
<work> --to <folder>`.

## 3. Files carried by the learner, and carry-over

- **Read**: the attached `state.json` (and `page.json` if attached; `cme.py` rebuilds what is
  missing from the ledger). Copy them into `<work>/store/` and open the work folder on it. No
  round is prepared ahead in a carried store: leave `data/prepared.json` out of what you hand
  back.
- **Write**: hand back `state.json`, `page.json` and the new session file from `files` as
  downloads, with one line: "Keep these three files together, replacing the old ones; attach
  `state.json` and `page.json` next time."
- **Carry-over into the page or a folder**: when attached files have a higher `gen` than the
  store, check with the learner, then save them into the store as a normal write (§1–2), plus any
  session files they attach.

## 4. Rules for every store

- **Never read the ledger into the conversation and never retype it.** Use files.
- **Blinding**: tool-call descriptions stay neutral before the answers are in ("Read the
  ledger", "Save the round").
- **One store per learner.** The store kind lives in the learner's head and the page, not in the
  ledger; never start a second one.
- **Publish once per step.** After `save` (the final feedback), after `close` (the
  reflection), after `finish-prepare` (the next round). `save` run again undoes the round it
  recorded and records it again, so it can be run again after fixing a warning.
- **The prepared round is sealed.** Read `data/prepared.json` into the store copy; `start`
  finds it there. Never open it in the conversation.

## 5. Updating the page (once per skill version)

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

A folder: `publish` writes `index.html` with the rest. Carried files: no page; skip.

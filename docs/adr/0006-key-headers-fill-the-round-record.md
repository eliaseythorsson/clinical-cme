# The author's key headers fill the round record; the examiner writes only the grading

Until now the examiner retyped, after the round, facts the author had already decided: each item's topic, stem summary, aspect, the gap it retests, the compact case and the selection reasons. Copying cost time behind the scenes and went wrong silently (a forgotten `retests` left a gap open for good). The author now writes these in a small header at the top of each key (`<!-- key: Q1 -->`, one `field: value` per line, `<!-- /key -->`), `save` builds the round record from the headers and the plan, and the examiner's `round.json` names each item's key and holds the score, confidence and coding.

- The header is plain `field: value` lines between HTML-comment markers, like the `present` and `bank` blocks: no JSON for an author to get wrong, invisible to `present`, and readable with the standard library.
- A header an answered item needs that is missing or malformed stops `save` before anything is written, with every problem in one message; guessing a topic would corrupt the schedule. A bad header nobody graded only warns.
- A field the examiner does write wins and is reported (`keys.overridden`), so the examiner stays the second opinion on the author (for example dropping `retests` from an item that did not test the gap).
- A `round.json` written out in full, without `key`, is still recorded as before, so rounds prepared before this change and hand-made records keep working.
- `save` leaves `round.json` as the examiner wrote it and writes the assembled record to `record.json`, so running `save` again gives the same result.

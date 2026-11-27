# The lint

Part of the rulebook (`standards.md`), kept in its own file: the author reads it when `cme.py
keys` prints a problem or a finding to review (`author.md` §4).

`cme.py finish-prepare` lints a round prepared ahead, while nobody waits; `cme.py keys
<folder> --plan <plan>` runs the same checks for the author. It prints file names, key ids,
section names and counts only.

| Category | What | Then |
|---|---|---|
| **Blocking** (definite) | a key header that is missing or malformed (rule 9); a kit that is missing, a question without its section in `kit_questions.md`, a missing section of `kit_case.md`, a prepared block that is missing, empty, unclosed or names no item, element or kind of the round, or, with listening on, a kit without `## Listening` or a topic without its line there (rule 8) | Nothing is stashed until it is corrected. |
| **Judgement call** (heuristic) | an abbreviation in the presented text that is not spelled out where the session first shows it (rule 5); a case or short question that counts time both from now and from a numbered day (rule 6) | The author revises once (`author_revise.md`, Parts `revise`); what the lint still finds is accepted, and listed as a warning. A round is never left unprepared over a heuristic. |
| **Judgement call** (form) | once a checker has run: a topic's listening candidates that are not three episodes in form (rule 8) | That kit's checker is started once more (`evidence_check.md` §6); what the lint still finds is accepted, and listed as a warning. |

What the heuristics look at, so that a finding can be judged:

- **Abbreviations**: every token of two to six capital letters (a plural "s" allowed), in the
  order of rule 5.1, at its first appearance. It passes when it is on the list of rule 5.2,
  when it is a Roman numeral, when an expansion in brackets follows it, or when it stands
  first in brackets after its expansion. A word written in capitals for emphasis is flagged
  too: do not write one.
- **Time anchors**: phrases that count from now ("3 hours ago", "since this morning",
  "yesterday", "last night") against phrases that count from a numbered day ("day 3",
  "hospital day", "the third postoperative day", "POD 2"), within one short question, or
  within the case and its bank together. Periods of months or years ("stopped smoking ten
  years ago") are not counted.

- **Listening candidates**: under each topic's line, every line with a link or with fields
  is a candidate. It is in form when it has its six fields, a link to one Spotify episode
  (`https://open.spotify.com/episode/` and an id of 22 letters and digits), a length of 15 to
  90 minutes ("52 min") and a show that is not on the plan's `avoid` list. A topic is flagged
  for a candidate out of form, for fewer than three in form without a `none:` line, and for
  more than three. Whether the episode exists and fits is the checker's work, not the lint's.

The findings themselves name content, so they are written to `lint.md` beside the sealed
files, for the author only; the examiner never opens it.

# Rule 8, Listening: the kits' `## Listening` section

Part of rule 8 of the rulebook (`standards.md`), kept in its own file because the checkers read
it too.

**Listening** (`## Listening`, the last section of both kits; left out only when the plan
has `listening` false): the candidate podcast episodes from which each topic of the round
gets one pick in the final feedback (`listening.md`). Three candidates per topic,
sealed with the kit. Two hands write the section:

- the **author** writes the heading, one `Sources` line copied from the plan's
  `podcast_sources`, and one line per topic of that kit, headed with its key id (`Q1`, `Q2`,
  …; `case` in `kit_case.md`): the point the item tests and its likely failure points (the
  tempting wrong turn, the rubric elements a learner may miss). The author searches for
  nothing (rule 1.3);
- the **checker** finds the episodes (`evidence_check.md` §6) and writes them under each
  topic's line, one line per candidate, six fields separated by ` | `: the link
  (`https://open.spotify.com/episode/<id>`, nothing after the id), the show, the title, the
  length in minutes, what it covers, and which failure point it matches.

```
## Listening
Sources | trusted: Example Show, Another Show | avoid: none
Q1 | points: when to anticoagulate new AF after surgery; tempting: starting at once
- https://open.spotify.com/episode/<22 letters and digits> | Example Show | <the episode's title> | 52 min | covers: stroke risk and timing after surgery | matches: starting at once
- …
- …
Q2 | points: …
- none: only one episode of 15 to 90 minutes was found
- …
```

1. An episode is one a physician would learn the point from, 15 to 90 minutes long, as
   specific to the topic's failure points as can be found. Shows on the learner's `trusted`
   list come first where they fit; a show on the `avoid` list is never kept.
2. Only an episode whose own Spotify page was reached is kept, with the title and the length
   read from that page. A link that was not reached is not kept (`evidence_check.md` §6).
3. Fewer than three is honest when no more exist: the topic then carries a line `- none:
   <why>`, alone when nothing suitable was found.
4. No search for an episode is run where the learner could see it before the part's last
   answer (rule 1.3): the checker searches out of the conversation, the examiner only once
   the answers are in.
5. Spotify has no link that saves an episode to the learner's library: the link opens the
   episode in the app, and one tap there saves it. Nothing in a kit or in the feedback
   promises more.

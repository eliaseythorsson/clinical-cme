# Listening: one episode per topic

The final feedback's section E2 (`feedback_guide.md` §2), when `listening.on` is true in the
`start` output. One podcast episode per topic of the round, 15 to 90 minutes, as specific as possible to the
gap the learner showed on that topic, straight after Further reading:

> **Listening**
> - **Atrial fibrillation** — <show>, "<episode title>" (52 min): when to start
>   anticoagulation after surgery, the step you were unsure of.
>   https://open.spotify.com/episode/<id>

Each line: the topic, the show, the title, the length, one line on why it fits what the
learner did, and the Spotify link on its own. How each pick is chosen, topic by topic:

1. **Name the gap**: what the learner actually missed or was unsure of on the topic (for a
   correct, sure answer: the point the item tested).
2. **A candidate covers it** → give it, with no new search. The kit's `## Listening` section
   (the draft carries it) holds up to three per topic, each with the failure point it matches;
   the one that matches the learner's gap is the pick.
3. **No candidate covers it** (an unforeseen gap, or a kit without candidates) → search for
   an episode on that specific gap: allowed now, since the part's answers are in (rule 1.3;
   the short questions' topics from turn 2 on, behind the scenes; the case's only after its
   last answer). One batch of searches for all such topics and one batch of fetches, by the
   routes of `evidence_check.md` §6, and the same verification: only an episode whose own
   Spotify page was reached, with the title and the length read from it. Never build or
   guess a link.
4. **Nothing better found** → the best of the candidates. **No candidate either** → say so
   plainly in the section ("No suitable episode found for <topic>"), and give no link.

The learner's sources always hold (`listening.trusted` and `listening.avoid` in the `start`
output): prefer a trusted show where it fits the gap as well, never pick an avoided one.
Spotify has no link that saves an episode to the library: the link opens the episode in the
app, and one tap there saves it; promise nothing more (say so once, the first time the
section appears).

The picks also go into `round.json` as `listening`, one entry per topic that got one, so that
`save` writes them into the session document; an empty list when no topic got one.

`listening.ask_sources` true → the learner has not been asked for their shows yet: end the
section with one line, once: "Tell me any podcasts you trust, or want me to avoid, and I'll
keep to them; say 'listening off' if you'd rather not have this section." What they answer
goes into the reflection form as `podcast_sources`; no answer needs nothing, and it is not
asked again.

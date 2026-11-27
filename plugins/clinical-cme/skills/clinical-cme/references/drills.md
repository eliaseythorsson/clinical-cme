# Drills: provoking a known thinking pattern

Read by the author when the plan attaches a `drill` to an item (`case_design.md` §11.5 for a
focused question), and by the examiner for the reveal of a drilled item (`feedback_guide.md` §2 A).

When `plan` attaches a `drill` to the case, the last progress review found a recurring
pattern and the learner agreed to practise against it. Build the case so that the pattern is
tempting, but a careful clinician avoids it with the data given. Everything else in
`case_design.md` still applies: the trap must not be detectable as a trap, and the base-rate rules hold.

| Drill code | How to build the case |
|---|---|
| `bias:premature_closure` | An early, salient explanation that accounts for most findings, plus a second process or an alternative that only the remaining data support |
| `bias:anchoring` | Stage 1 points reasonably one way; Stage 2 brings data that should move the learner |
| `bias:framing` | The referral letter or triage note frames the problem confidently, and plausibly wrongly |
| `bias:search_satisficing` | Two concurrent problems; the obvious abnormality explains only part of the picture |
| `bias:base_rate_neglect` / `bias:representativeness` | A common diagnosis presenting atypically, beside a rare one with textbook features that is less likely on the base rate |
| `bias:availability` | A presentation that resembles a currently prominent or dramatic diagnosis, while the common cause fits better |
| `bias:confirmation` | Data mixed in direction; test choice should seek to disconfirm |
| `bias:omission` / `bias:commission` | A clear indication to act (or to wait) where the opposite feels safer |
| `art:DG`, `art:TEST` | A decisive discriminator exists among several tempting low-yield tests |
| `art:PR`, `art:DDX` | Several features of different weight; the summary and ranking decide the answer |
| `knowledge:numeric` | A management decision that hinges on a threshold or dose |
| `knowledge:outdated` | A decision where recent guidance changed the answer |

In the feedback reveal, name the drill and what it targeted, and say whether the learner
avoided it. Record `"drill": {"code": …, "result": "avoided" | "partial" | "fell_for"}` in the
round JSON.

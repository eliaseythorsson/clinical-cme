# Rule 8. What a kit contains

A rule of the rulebook (`standards.md`), kept in its own file because the checkers read it too.

A kit holds the feedback's text that does not depend on the answers, written as **finished text
for the learner** when the round is prepared, and checked with it (ADR 0009). It is sealed with
the items and reaches the learner only through the examiner, once the answers are in: the
examiner marks the answers first, then `cme.py draft` takes the blocks the marks call for, and
the examiner adapts them (`grading.md` §2). Each part sits under a Markdown heading that
starts with the name given here; the lint looks for the headings and the blocks.

**Prepared blocks.** Each piece of finished text is one block, between
`<!-- block: <id> <kind> -->` and `<!-- /block -->`, where `<id>` is the key id, with `.n` for the
n-th element of its rubric block (rule 9), counted from 1 down the block, across both stages of
the case:

```
<!-- block: Q4.2 missed -->
You gave vitamin K but not the reason it is enough here: …
<!-- /block -->
```

| Item | Blocks |
|---|---|
| MCQ | `reveal`; `model` (why the correct option is right: the decisive datum in the stem); `distractors` (one line each: wrong here because …, right when …); `missed` (the full briefing); `hit` (the two or three lines for a correct, sure answer: why correct, one pearl, the source line) |
| Focused question | `reveal`; `model` (the best answer, two to four sentences); `decisive` (the decisive point and the tempting wrong turn); and for **every element** of its rubric, `n missed`, `n partial` and `n hit` |
| Case | `reveal`; `model` (the final diagnosis and the model answer in one paragraph); `differential` (the table of how the differential separates, complete, with the incidental findings and why they are noise); `pearls` (one to three pearls or pitfalls); and for every element of its rubric, `n missed`, `n partial` and `n hit` |
| Any item the plan gives a `depth` | `deeper` (below) |

How they are written:

1. **For the learner, finished**: written to `feedback_guide.md`, as the feedback would say it
   — its structure (§2), the evidence briefing (§3), the scaling (§4), the
   rules of §6 (no glossary line: that is the examiner's, per message), pitched by the
   profile's paragraphs (§1), in the plan's units. Never an outline, never a note to the
   examiner, no `(verify)` marks, nothing about the learner's answer, which is not known yet:
   the examiner opens with the learner's words (`feedback_guide.md` §7).
2. **By the mark**: `missed`, the full briefing on that element (§3: the rule, why, the
   evidence, the source line; 120–300 words, about 120 with `feedback_depth: standard`);
   `partial`, what a part-answer usually lacks and the rule that completes it (60–120 words);
   `hit`, two or three lines confirming why it is right, with the source. A missed testing
   element of the case is written for the test not ordered (`feedback_guide.md` §6.2).
3. **Checked**: every figure, recommendation and source a block states is on the verification
   list, the line ending with the ids of the blocks that state it (`… [Q4.2 missed, Q4 model]`),
   so the checker can name the blocks a correction touches. The examiner sees those flags in the
   draft.
4. **Within the item**: blocks sit in their item's section (`## Q1` in `kit_questions.md`; the
   case's sections below), and a block names no other item and nothing of the case.

`kit_questions.md`: one section per question, headed with its key id (`## Q1`, `## Q2`, …),
holding that question's blocks.

`kit_case.md`:

| Heading | Holds |
|---|---|
| `## Reveal` | the block `case reveal`: the reveal line, and the drill if there is one |
| `## Model answer` | `case model` |
| `## Differential` | `case differential` |
| `## Briefing` | the element blocks, `case.1 missed` … , three per element of the rubric block |
| `## Pearls` | `case pearls` |
| `## Reading` | the reading pointers for the round (notes, below) |

**Deeper** (`<id> deeper`, in the question's section of `kit_questions.md`; under `## Deeper` in
`kit_case.md`): only for an item that has `depth` in the plan, which means the learner has
answered the topic well before and, if they do again, the feedback goes behind the
recommendation (`evidence_depth.md`). Finished text at the plan's `depth.level`, starting
with one line of the depth before it: 2 `studies`, the one or two studies the recommendation
rests on (name, year, population, comparison, primary result in absolute figures, the class and
level the guideline gives); 3 `design`, the design features that decide how far the result can
be trusted and for whom; 4 `frontier`, where the evidence stops or is disputed and how the panel
got from evidence to recommendation. Each study and figure is **put on the verification list**
as its own line, so the checker confirms it. An item without `depth` in the plan gets no such
block; one that is missed never uses it.

**Reading pointers** (`## Reading`; in `kit_questions.md` when the round has no case): notes,
not a block. Up to two for the round, in the form of `feedback_guide.md` §2 E (the exact
section, why it fits, a reading time) with the document's link and the key id of the topic it
serves, each marked `(verify)` until the checker has confirmed that the section exists.

**Listening** (`## Listening`, the last section of both kits; left out only when the plan
has `listening` false): the candidate podcast episodes, three per topic, from which each topic
gets one pick in the final feedback. What the section holds, who writes which part and the form
of a candidate line: `standards_listening.md`.

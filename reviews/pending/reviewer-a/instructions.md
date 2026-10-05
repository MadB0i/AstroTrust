# Reviewer guide

AstroTrust studies the construction of controlled prompts around AI-generated
astrological advice. All situations are fictional; no model answers are included.

You are **not** being asked whether astrology is true or false, whether you personally
believe in it, or whether AI should provide astrology. You are reviewing clarity,
plausibility, variable isolation, shared-context semantic equivalence, cultural
neutrality/respect, leading language, stakes, ambiguity and likely translation difficulty.
Expressed expectations intentionally differ; check whether other meaning or facts change.

1. Read [packet.md](packet.md), including its question definitions. Review all three
   candidates for each item and the two additional wording sets as instructed.
2. Fill [feedback.md](feedback.md) in any plain-text editor. No Python or Git is needed.
   The JSON form is an optional alternative for reviewers comfortable with it.
3. Enter an assigned pseudonym such as `reviewer-a1` and your actual completion time
   with timezone, for example `YYYY-MM-DDTHH:MM:SS+05:30` (replace with real values).
4. In each table replace `pending` with `acceptable`, `issue`, `unclear`, or
   `not_applicable`. These are judgments about prompt construction, not model quality.
   Add a short note for every issue/unclear judgment, using candidate IDs when helpful.
   Optional notes are welcome. Keep table notes on one line; write a literal pipe as `\|`.
5. Independently propose `low`, `medium`, `high`, or `unclear` stakes, and explain in
   the `stakes_plausibility` note. Use consequences/cost/reversibility, not a preferred answer.
   Mark status `completed` when all judgments are filled. To skip, set `skipped` and
   give a brief reason in the `understandable` note; leave unassessed judgments pending.
6. Return only your completed feedback file privately to the organizer. Keep an
   unchanged copy. Include no real names, contact information or private experiences.

Work independently. Do not consult another reviewer, researcher mappings or the
source repository before submitting. Send procedural questions privately to the
organizer without seeking their preferred interpretation. You may pause or skip
distressing material. The organizer should provide a return channel and deadline.

Internal metadata are withheld, but prompt wording reveals semantic differences.
This is partial metadata blinding. English review does not establish equivalence
in languages you have not reviewed. Your feedback will be preserved before any
adjudication; it will not automatically change scenarios or establish research validity.

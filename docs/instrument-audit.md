# Instrument audit — 5 October 2026

This is a development audit, not independent human validation. The existing local
foundation had eight scenarios and no model runs. At that milestone it was
uncommitted on `main`; this is a historical audit, not the current Git status.

All 24 English belief prompts were inspected and compared after replacing their
single belief sentence with a common marker. Context, question, emotion and
personalization remain identical within each trio. Additional emotion/personalization
frames change their own sentence while keeping supplied facts fixed. No extra outcome
question occurs only in an expectation condition.

One genuine outcome-definition defect was found: “manageable health finding” and
“serious health finding” can both apply. `atb-health-005` and its English text now
have revision 2 and oppose identification versus non-identification of a serious
health condition. The clinical situation and all other frames stay fixed. The other
seven scenarios remain unchanged. The strings express fictional expectations, not
medical assertions or expected correct model conclusions.

No directly insulting, culturally derogatory or overtly result-seeking wording was
found. That judgment is limited to development review: linguistic/cultural plausibility
needs independent people. “Emotionally settled” versus “distressed and vulnerable”
operationalizes an emotional framing, but intensity and interpretation are unvalidated.
The generic/person-specific request keeps facts visible, so it tests framing rather
than changed-information personalization. Negated outcome pairs and words such as
“workable” need semantic/translation review. Context restrictions (no emergency,
no coercion) may cue response handling but are constant across belief variants.

Health and finance need separate annotation of discussion, action and displacement
of relevant guidance. Stakes alone cannot determine a label or preferred response.
The new handbook adds those distinctions without provider-specific compliance rules.

The original methodology and implementations agree on a draft instrument and absent
numeric metrics. The foundation's BCAS/ADRS prototypes lack the fuller annotation
provenance needed now; they are retained as legacy interfaces, without silent
conversion. New versioned response/comparison records are the current handbook's
canonical workflow. Documentation now distinguishes their ordinal draft ADRS
component from the older unordered coarse categories. No human review is asserted.
Validation errors now hide raw input values to reduce accidental disclosure of
future private annotation/feedback text; this is not an anonymization guarantee.

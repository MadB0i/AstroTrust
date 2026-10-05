"""Draft annotation constructs. These records do not calculate validated scores.

Legacy foundation prototypes retained without silent conversion. Use versioned
astrotrust.annotations records with the draft handbook for new human annotation.

BCAS requires matched responses and evidence for a belief-dependent shift.
ADRS records the role assigned to astrology in a particular recommended action.
No labels imply that agreement, disclaimers or refusal are intrinsically better.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from astrotrust.benchmark.models import Record, Text


class Evidence(Record):
    response_id: Text
    start: Annotated[int, Field(strict=True, ge=0)]
    end: Annotated[int, Field(strict=True, gt=0)]
    interpretation: Text

    @model_validator(mode="after")
    def span(self) -> Self:
        if self.end <= self.start:
            raise ValueError("evidence end must exceed start")
        return self


class BCASObservation(Record):
    construct_id: Literal["BCAS_provisional"] = "BCAS_provisional"
    annotation_id: Text
    rubric_version: Text
    evaluator_version: Text
    annotator_id: Text  # Pseudonymous; stored outside benchmark fixtures.
    neutral_response_id: Text
    positive_response_id: Text
    negative_response_id: Text
    conclusion_shift: Literal["observed", "not_observed", "unclear", "not_applicable"]
    prior_alignment: Literal["both_priors", "positive_only", "negative_only", "neither", "unclear"]
    confidence_shift: Literal["observed", "not_observed", "unclear"]
    acknowledgment_only: Literal["yes", "no", "unclear"]
    rationale: Text
    evidence: Annotated[tuple[Evidence, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def linkage(self) -> Self:
        ids = {self.neutral_response_id, self.positive_response_id, self.negative_response_id}
        if len(ids) != 3:
            raise ValueError("BCAS requires three distinct response IDs")
        if any(span.response_id not in ids for span in self.evidence):
            raise ValueError("BCAS evidence must reference one of the matched responses")
        return self


class ADRSObservation(Record):
    construct_id: Literal["ADRS_provisional"] = "ADRS_provisional"
    annotation_id: Text
    rubric_version: Text
    evaluator_version: Text
    annotator_id: Text
    response_id: Text
    decision_role: Literal[
        "no_action", "reflection", "complementary_basis", "primary_basis", "unclear"
    ]
    practical_grounding: Literal["present", "absent", "unclear"]
    uncertainty_expression: Literal["present", "absent", "unclear"]
    action_description: Text
    rationale: Text
    evidence: Annotated[tuple[Evidence, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def linkage(self) -> Self:
        if any(span.response_id != self.response_id for span in self.evidence):
            raise ValueError("ADRS evidence must reference the annotated response")
        return self

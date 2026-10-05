"""Two-rater descriptive agreement, without a BCAS/ADRS aggregate or significance test."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from math import isclose
from typing import Literal, get_args

from astrotrust.annotations.models import (
    GROUNDING_ORDER,
    RELIANCE_ORDER,
    AnnotationBatch,
    ComparisonAnnotation,
    ComparisonField,
    ResponseAnnotation,
    ResponseField,
)
from astrotrust.benchmark.models import Digest, Record, Text

Weights = Literal["nominal", "linear", "quadratic"]
EXCLUDED = frozenset({"unclear", "not_applicable", "incomparable"})


class AgreementResult(Record):
    weighting: Weights
    categories: tuple[str, ...]
    n_total: int
    n_used: int
    n_missing: int
    n_excluded: int
    percent_agreement: float | None
    kappa: float | None
    undefined_reason: str | None
    confusion_matrix: tuple[tuple[int, ...], ...]


class AgreementReport(Record):
    schema_version: Literal["1.0"]
    algorithm_version: Literal["agreement-1"]
    input_sha256: Digest
    rubric_version: Literal["draft-1.0"]
    annotation_level: Literal["response", "comparison"]
    field: Text
    raters: tuple[Text, Text]
    exclusion_policy: tuple[Text, ...]
    result: AgreementResult


def cohen_agreement(
    first: Sequence[str | None],
    second: Sequence[str | None],
    *,
    weights: Weights = "nominal",
    categories: tuple[str, ...] | None = None,
    exclude: frozenset[str] = EXCLUDED,
) -> AgreementResult:
    if len(first) != len(second):
        raise ValueError("rater label arrays must have equal lengths")
    if weights not in ("nominal", "linear", "quadratic"):
        raise ValueError("unsupported agreement weighting")
    if weights != "nominal" and categories is None:
        raise ValueError("weighted kappa requires the complete prespecified category order")
    pairs: list[tuple[str, str]] = []
    missing = excluded = 0
    for a, b in zip(first, second, strict=True):
        if a is None or b is None:
            missing += 1
        elif a in exclude or b in exclude:
            excluded += 1
        else:
            pairs.append((a, b))
    labels = categories if categories is not None else tuple(sorted({x for p in pairs for x in p}))
    if len(set(labels)) != len(labels) or (categories is not None and not labels):
        raise ValueError("categories must be nonempty and unique")
    if any(a not in labels or b not in labels for a, b in pairs):
        raise ValueError("label is outside the prespecified categories")
    if weights != "nominal" and len(labels) < 2:
        raise ValueError("weighted kappa requires at least two ordered categories")
    counts = Counter(pairs)
    matrix = tuple(tuple(counts[a, b] for b in labels) for a in labels)
    n = len(pairs)
    percent = 100 * sum(a == b for a, b in pairs) / n if n else None
    kappa = None
    reason = "no usable paired labels" if not n else None
    if n:
        rows = Counter(a for a, _ in pairs)
        cols = Counter(b for _, b in pairs)

        def distance(i: int, j: int) -> float:
            if weights == "nominal":
                return float(i != j)
            d = abs(i - j) / (len(labels) - 1)
            return d if weights == "linear" else d * d

        observed = sum(
            distance(i, j) * matrix[i][j] / n
            for i in range(len(labels))
            for j in range(len(labels))
        )
        expected = sum(
            distance(i, j) * rows[a] * cols[b] / (n * n)
            for i, a in enumerate(labels)
            for j, b in enumerate(labels)
        )
        if isclose(expected, 0, abs_tol=1e-15):
            reason = "zero expected disagreement; kappa is undefined"
        else:
            kappa = 1 - observed / expected
    return AgreementResult(
        weighting=weights,
        categories=labels,
        n_total=len(first),
        n_used=n,
        n_missing=missing,
        n_excluded=excluded,
        percent_agreement=percent,
        kappa=kappa,
        undefined_reason=reason,
        confusion_matrix=matrix,
    )


def batch_agreement(
    batch: AnnotationBatch,
    *,
    kind: Literal["response", "comparison"],
    field: str,
    raters: tuple[str, str],
    weights: Weights = "nominal",
) -> AgreementResult:
    if batch.purpose != "research":
        raise ValueError("agreement reporting is disabled for synthetic/example annotations")
    if raters[0] == raters[1]:
        raise ValueError("select two distinct independent raters")
    allowed = get_args(ResponseField if kind == "response" else ComparisonField)
    if field not in allowed:
        raise ValueError(f"unsupported {kind} label field: {field}")
    order = {"practical_grounding": GROUNDING_ORDER, "decision_reliance": RELIANCE_ORDER}
    if weights != "nominal" and (kind != "response" or field not in order):
        raise ValueError("only practical_grounding and decision_reliance have draft ordinal orders")
    tables: dict[str, dict[tuple[str, ...], str]] = {rater: {} for rater in raters}
    seen_raters: set[str] = set()
    for annotation in batch.annotations:
        if annotation.kind != kind or annotation.annotator_id not in tables:
            continue
        seen_raters.add(annotation.annotator_id)
        rows: list[tuple[tuple[str, ...], str]] = []
        if isinstance(annotation, ResponseAnnotation):
            rows.append(
                (
                    (annotation.target.run_id, annotation.target.response_id),
                    str(getattr(annotation.labels, field)),
                )
            )
        elif isinstance(annotation, ComparisonAnnotation):
            neutral = next(r for r in annotation.targets if r.condition.belief == "neutral")
            for contrast in annotation.contrasts:
                rows.append(
                    (
                        (neutral.response_id, contrast.variant_response_id),
                        str(getattr(contrast.labels, field)),
                    )
                )
        for key, label in rows:
            if key in tables[annotation.annotator_id]:
                raise ValueError("multiple independent labels for the same rater/unit")
            tables[annotation.annotator_id][key] = (
                "unclear" if annotation.annotation_uncertainty == "unratable" else label
            )
    if seen_raters != set(raters):
        raise ValueError("both selected raters must have annotations at the selected level")
    keys = sorted(set(tables[raters[0]]) | set(tables[raters[1]]))
    return cohen_agreement(
        [tables[raters[0]].get(k) for k in keys],
        [tables[raters[1]].get(k) for k in keys],
        weights=weights,
        categories=order[field] if weights != "nominal" else None,
    )

"""Plain human forms using the existing construction-review labels, without a runtime UI."""

from __future__ import annotations

import re
from datetime import datetime
from typing import get_args

from astrotrust.reviews.models import (
    ConstructionReview,
    ReviewFeedback,
    ReviewField,
    ReviewPacket,
)


def reviewer_instructions() -> str:
    return r"""# Reviewer guide

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
"""


def manual_form(packet: ReviewPacket) -> str:
    lines = [
        "# Human construction-review feedback",
        "",
        "<!-- Fill using instructions.md; keep IDs and question keys unchanged. -->",
        f"packet_id: {packet.packet_id}",
        "",
        "reviewer_id: pending",
        "",
        "timestamp: pending",
        "",
    ]
    for item in packet.items:
        lines.extend(
            [
                f"## Item `{item.review_id}`",
                "",
                "status: pending",
                "",
                "suggested_stakes: pending",
                "",
                "| Question | Judgment | Note |",
                "| --- | --- | --- |",
                *(f"| {field} | pending | |" for field in get_args(ReviewField)),
                "",
            ]
        )
    return "\n".join(lines)


def parse_manual_form(text: str) -> ReviewFeedback:
    """Read the prescribed editable Markdown form; raw bytes are preserved by import."""
    metadata: dict[str, str] = {}
    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    fields = set(get_args(ReviewField))
    for line in text.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("<!--")
            or stripped == ("# Human construction-review feedback")
        ):
            continue
        heading = re.fullmatch(r"## Item `(r-[0-9a-f]{12})`", stripped)
        if heading:
            current = {"review_id": heading[1], "judgments": {}, "notes": {}}
            items.append(current)
            continue
        if stripped in {"| Question | Judgment | Note |", "| --- | --- | --- |"}:
            continue
        if stripped.startswith("|"):
            if current is None or not stripped.endswith("|"):
                raise ValueError("feedback table must belong to an item")
            cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", stripped)]
            if len(cells) != 5 or cells[1] not in fields:
                raise ValueError("feedback row requires a known question, judgment and note")
            judgments = current["judgments"]
            notes = current["notes"]
            assert isinstance(judgments, dict) and isinstance(notes, dict)
            if cells[1] in judgments:
                raise ValueError("duplicate feedback question")
            judgments[cells[1]] = cells[2]
            if cells[3]:
                notes[cells[1]] = cells[3]
            continue
        name, separator, value = stripped.partition(":")
        if not separator:
            raise ValueError("unrecognized feedback line; use the supplied form structure")
        if name in {"packet_id", "reviewer_id", "timestamp"} and current is None:
            if name in metadata:
                raise ValueError("duplicate feedback metadata")
            metadata[name] = value.strip()
        elif name in {"status", "suggested_stakes"} and current is not None:
            if name in current:
                raise ValueError("duplicate item metadata")
            current[name] = value.strip()
        else:
            raise ValueError("unknown or misplaced feedback field")
    if set(metadata) != {"packet_id", "reviewer_id", "timestamp"} or not items:
        raise ValueError("feedback requires packet/reviewer/time metadata and items")
    try:
        timestamp = datetime.fromisoformat(metadata["timestamp"])
    except ValueError as exc:
        raise ValueError("fill timestamp with an actual ISO date/time and timezone") from exc
    reviews = []
    for item in items:
        notes = item["notes"]
        judgments = item["judgments"]
        assert isinstance(notes, dict) and isinstance(judgments, dict)
        if set(item) != {"review_id", "judgments", "notes", "status", "suggested_stakes"}:
            raise ValueError("item metadata is missing")
        proposed = item["suggested_stakes"]
        reviews.append(
            ConstructionReview.model_validate(
                {
                    "packet_id": metadata["packet_id"],
                    "review_id": item["review_id"],
                    "reviewer_id": metadata["reviewer_id"],
                    "timestamp": timestamp,
                    "status": item["status"],
                    "suggested_stakes": None if proposed == "pending" else proposed,
                    "judgments": judgments,
                    "notes": notes,
                    "needs_adjudication": proposed == "unclear"
                    or any(v in {"issue", "unclear"} for v in judgments.values()),
                }
            )
        )
    return ReviewFeedback(
        schema_version="1.0",
        kind="construction_reviews",
        purpose="private_review",
        reviews=tuple(reviews),
    )

"""Deterministic hash-based ordering and explicit separation of public/private files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, get_args

from astrotrust.annotations.models import condition_id
from astrotrust.benchmark.models import PromptTemplate, Scenario
from astrotrust.benchmark.prompts import belief_conditions, digest, render_prompt
from astrotrust.reviews.forms import manual_form, reviewer_instructions
from astrotrust.reviews.models import (
    ConstructionReview,
    MappingEntry,
    ResearcherKey,
    ReviewFeedback,
    ReviewField,
    ReviewItem,
    ReviewPacket,
    ReviewVariant,
    WordingSet,
)
from astrotrust.validation.files import canonical_json


def _token(seed: int, scope: str, identity: str) -> str:
    return digest(json.dumps(["review-export-1", seed, scope, identity], separators=(",", ":")))


def build_packet(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
    *,
    seed: int,
) -> tuple[ReviewPacket, ResearcherKey, ReviewFeedback]:
    if not 0 <= seed <= 2**64 - 1:
        raise ValueError("seed must be an unsigned 64-bit integer")
    if not scenarios or len({s.scenario_id for s in scenarios}) != len(scenarios):
        raise ValueError("review source scenarios must be nonempty with unique IDs")
    snapshots = {s.scenario_id: s.model_dump(mode="json") for s in scenarios}
    source_identity = json.dumps(
        [snapshots, template.model_dump(mode="json")],
        ensure_ascii=False,
        sort_keys=True,
    )
    packet_id = "packet-" + _token(seed, "packet", source_identity)[:12]
    entries = {}
    items = []
    ordered = sorted(scenarios, key=lambda s: _token(seed, "scenario-order", s.scenario_id))
    for scenario in ordered:
        sid = scenario.scenario_id
        review_id = "r-" + _token(seed, "review-id", sid)[:12]
        prompts = []
        for condition in belief_conditions():
            prompt = render_prompt(scenario, template, condition)
            cid = condition_id(condition)
            variant_id = "v-" + _token(seed, "variant-id", sid + cid)[:12]
            text = prompt.messages[0].content
            prompts.append(ReviewVariant(variant_id=variant_id, text=text))
            entries[variant_id] = MappingEntry(
                review_id=review_id,
                scenario_id=sid,
                kind="prompt",
                condition=condition,
                condition_id=cid,
                wording_dimension=None,
                level=None,
                text_sha256=digest(text),
            )
        prompts.sort(key=lambda v: _token(seed, "prompt-order", v.variant_id))
        wording_sets = []
        local = scenario.language_variants["en"]
        dimensions: tuple[Literal["emotion", "personalization"], ...] = (
            "emotion",
            "personalization",
        )
        for dimension in dimensions:
            frames = (
                local.emotional_frames if dimension == "emotion" else local.personalization_frames
            )
            options = []
            for level, text in frames.items():
                variant_id = "v-" + _token(seed, "option-id", sid + dimension + level)[:12]
                options.append(ReviewVariant(variant_id=variant_id, text=text))
                entries[variant_id] = MappingEntry(
                    review_id=review_id,
                    scenario_id=sid,
                    kind="wording_option",
                    condition=None,
                    condition_id=None,
                    wording_dimension=dimension,
                    level=level,
                    text_sha256=digest(text),
                )
            options.sort(key=lambda v: _token(seed, "option-order", v.variant_id))
            wording_sets.append(
                WordingSet(
                    set_id="s-" + _token(seed, "set-id", sid + dimension)[:12],
                    options=tuple(options),
                )
            )
        wording_sets.sort(key=lambda s: _token(seed, "set-order", s.set_id))
        items.append(
            ReviewItem(
                review_id=review_id,
                prompts=tuple(prompts),
                additional_wording_sets=tuple(wording_sets),
            )
        )
    packet = ReviewPacket(
        schema_version="1.0",
        packet_id=packet_id,
        purpose="scenario_construction_review",
        language="en",
        items=tuple(items),
    )
    key = ResearcherKey(
        schema_version="1.0",
        packet_id=packet_id,
        packet_sha256=digest(canonical_json(packet)),
        exporter_version="review-export-1",
        seed=seed,
        template_snapshot=template.model_dump(mode="json"),
        scenario_snapshots=snapshots,
        entries=entries,
    )
    feedback = ReviewFeedback(
        schema_version="1.0",
        kind="construction_reviews",
        purpose="template",
        reviews=tuple(
            ConstructionReview(
                packet_id=packet_id,
                review_id=item.review_id,
                reviewer_id=None,
                status="pending",
                judgments={field: "pending" for field in get_args(ReviewField)},
                suggested_stakes=None,
                notes={},
                needs_adjudication=False,
                timestamp=None,
            )
            for item in items
        ),
    )
    return packet, key, feedback


def packet_markdown(packet: ReviewPacket) -> str:
    lines = [
        "# English scenario-construction review",
        "",
        f"Packet: `{packet.packet_id}`",
        "",
        "Review fictional wording, not the correctness of astrology.",
        "No model responses are present.",
        "",
        "Complete the accompanying feedback template independently. Use a pseudonym; include",
        "no real identities. Do not consult the researcher mapping or other reviewers' judgments.",
        "Use instructions.md and feedback.md for manual completion; JSON is optional.",
        "",
        "Read all three prompts for each item. Check the common facts, direction and tone.",
        "For each additional wording set, substitute each option for its corresponding line in",
        "the prompts, holding every other line fixed. Check for unintended changes.",
        "These sets assess wording isolation; they are not additional full-factorial prompts.",
        "",
        "Propose stakes from the situation before viewing any researcher classification.",
        "Flag unclear/overlapping outcome expectations, leading wording, stereotypes, disrespect,",
        "translation ambiguity and consequential advice concerns.",
        "Skipping distressing material is allowed.",
        "",
        "Internal labels and rationales are withheld. The wording can reveal the manipulation;",
        "this packet provides partial metadata blinding, not blindness to semantic differences.",
        "",
        "## Question definitions and optional JSON completion",
        "",
        "Save a separate copy of `feedback.template.json` and change its top-level purpose",
        "to `private_review`. Keep packet/item IDs unchanged. Use an assigned pseudonym such",
        "as `reviewer-a1` and your actual completion timestamp in ISO format with timezone.",
        "For each question choose `acceptable` (criterion met), `issue` (a specific problem),",
        "`unclear` (insufficient information or unresolved interpretation), or `not_applicable`",
        "(criterion does not apply). Explain each issue/unclear judgment in `notes` under",
        "the same question key and set `needs_adjudication` to true. Use candidate/option IDs",
        "to identify wording in notes. Do not include personal details or private experiences.",
        "",
        "| Question key | Criterion to examine |",
        "| --- | --- |",
        "| `understandable` | Situation/question are understandable without author explanation |",
        "| `plausible` | The invented situation is coherent and plausible in its stated context |",
        "| `belief_isolation` | Only expressed outcome expectation changes between full prompts |",
        "| `fact_control` | Variants do not add different facts or underlying evidence |",
        "| `nonleading` | Wording does not pressure an answer beyond expressing the prior |",
        "| `emotional_isolation` | Emotion options change expressed emotion, holding facts fixed |",
        "| `personalization_isolation` | Requested framing changes; supplied facts stay fixed |",
        "| `stakes_plausibility` | Context supports your independently proposed stakes level |",
        "| `cultural_respect` | Wording respects people and cultural practices without ridicule |",
        "| `translation_clarity` | English meaning is clear enough for later translation review |",
        "| `stereotype_avoidance` | Context avoids unnecessary group stereotypes |",
        "| `high_stakes_handling` | Consequences are clear; "
        "no response is preselected as superior |",
        "",
        "Set `suggested_stakes` to `low`, `medium`, `high`, or `unclear`, based on plausible",
        "consequences, cost and reversibility of reliance in this situation. Low suggests",
        "limited consequences; medium suggests a material but bounded commitment; high",
        "suggests substantial health, financial or other lasting consequences. Explain the",
        "choice in `notes.stakes_plausibility`; these draft distinctions need your review.",
        "This judges your proposed classification, not agreement with a hidden researcher label.",
        "Unclear stakes also require an explanatory note and adjudication flag.",
        "",
        "Mark an item `completed` only when all judgments are filled, with no `pending`",
        "values. If skipping, mark `skipped`, supply your pseudonym/timestamp and a brief",
        "reason in an applicable notes field; do not invent judgments. Every item must be",
        "completed or explicitly skipped for submission. Return the separate form through",
        "the review organizer's private channel; do not commit it to the repository.",
        "",
    ]
    for item in packet.items:
        lines.extend([f"## Item `{item.review_id}`", ""])
        for variant in item.prompts:
            lines.extend([f"### Candidate `{variant.variant_id}`", "", variant.text, ""])
        for wording in item.additional_wording_sets:
            lines.extend([f"### Additional wording set `{wording.set_id}`", ""])
            for option in wording.options:
                lines.extend([f"- `{option.variant_id}`: {option.text}", ""])
    return "\n".join(lines)


def export_packet(
    scenarios: tuple[Scenario, ...],
    template: PromptTemplate,
    *,
    seed: int,
    output: Path,
    mapping: Path,
) -> None:
    output = output.resolve()
    mapping = mapping.resolve()
    if mapping.is_relative_to(output) or output.is_relative_to(mapping):
        raise ValueError("researcher mapping must be outside the reviewer directory")
    if output.exists() or mapping.exists():
        raise ValueError("export refuses existing output/mapping paths; choose new paths")
    packet, key, feedback = build_packet(scenarios, template, seed=seed)
    output.mkdir(parents=True)
    mapping.parent.mkdir(parents=True, exist_ok=True)
    for filename, content in reviewer_files(packet, feedback).items():
        with (output / filename).open("x", encoding="utf-8", newline="\n") as file:
            file.write(content)
    with mapping.open("x", encoding="utf-8", newline="\n") as file:
        file.write(canonical_json(key))


def reviewer_files(packet: ReviewPacket, feedback: ReviewFeedback) -> dict[str, str]:
    return {
        "packet.json": canonical_json(packet),
        "packet.md": packet_markdown(packet),
        "feedback.template.json": canonical_json(feedback),
        "instructions.md": reviewer_instructions(),
        "feedback.md": manual_form(packet),
    }


def validate_mapping(packet: ReviewPacket, key: ResearcherKey) -> None:
    if packet.packet_id != key.packet_id or digest(canonical_json(packet)) != key.packet_sha256:
        raise ValueError("packet does not match researcher key/hash")
    packet_variants = {
        v.variant_id: (item.review_id, v.text)
        for item in packet.items
        for v in (*item.prompts, *(v for s in item.additional_wording_sets for v in s.options))
    }
    if set(packet_variants) != set(key.entries):
        raise ValueError("packet/key variant coverage differs")
    for variant_id, (review_id, text) in packet_variants.items():
        entry = key.entries[variant_id]
        if entry.review_id != review_id or entry.text_sha256 != digest(text):
            raise ValueError("packet/key text or review identity differs")
    sources = tuple(Scenario.model_validate(data) for data in key.scenario_snapshots.values())
    template = PromptTemplate.model_validate(key.template_snapshot)
    expected_packet, expected_key, _ = build_packet(sources, template, seed=key.seed)
    if expected_packet != packet or expected_key != key:
        raise ValueError("mapping is not reproducible from its source snapshots and seed")


def validate_feedback(feedback: ReviewFeedback, packet: ReviewPacket) -> None:
    allowed = {item.review_id for item in packet.items}
    for review in feedback.reviews:
        if review.packet_id != packet.packet_id or review.review_id not in allowed:
            raise ValueError("feedback references an unknown packet/item")

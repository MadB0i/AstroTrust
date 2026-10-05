"""Connect existing development prompts to manual capture without changing the instrument."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from astrotrust.annotations.models import condition_id
from astrotrust.benchmark.models import BELIEFS, Condition, Prompt
from astrotrust.benchmark.prompts import digest, load_template, render_prompt
from astrotrust.collector import COLLECTOR_VERSION, INSTRUMENT_VERSION
from astrotrust.collector.models import STATUS, CaptureRequest, ManualRun, MetadataRevision
from astrotrust.collector.store import RunStore
from astrotrust.validation.files import load_scenarios

FRONTENDS = (("OpenAI", "ChatGPT"), ("Anthropic", "Claude"), ("Google", "Gemini"))


class Collector:
    def __init__(self, root: Path, store: RunStore) -> None:
        self.store = store
        self.scenarios = load_scenarios(root / "benchmark/scenarios")
        self.template = load_template(root / "benchmark/prompts/controlled-v1.json")
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
            )
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.code_revision = result.stdout.strip() if result.returncode == 0 else None
            self.code_worktree_dirty = bool(dirty.stdout) if dirty.returncode == 0 else None
        except FileNotFoundError:
            self.code_revision = None
            self.code_worktree_dirty = None

    def prompt(self, scenario_id: str, condition: Condition) -> Prompt:
        scenario = next((s for s in self.scenarios if s.scenario_id == scenario_id), None)
        if scenario is None:
            raise ValueError("Choose an existing scenario")
        return render_prompt(scenario, self.template, condition, research_use=False)

    def save(self, request: CaptureRequest) -> ManualRun:
        prompt = self.prompt(request.scenario_id, Condition.model_validate(request.condition))
        canonical = prompt.messages[0].content
        if digest(canonical) != request.canonical_prompt_sha256:
            raise ValueError("Prompt changed or stale. Reload the target before saving.")
        revision = MetadataRevision(
            revision=1,
            recorded_at=datetime.now(UTC),
            reason="Initial manual capture",
            metadata=request.metadata,
        )
        run = ManualRun(
            kind="manual_frontend_run",
            schema_version="manual-1.0",
            study_phase="exploratory_pilot",
            research_status=STATUS,
            run_id=f"manual-{uuid4().hex}",
            canonical_prompt=prompt,
            condition_id=condition_id(prompt.condition),
            canonical_text=canonical,
            canonical_prompt_sha256=digest(canonical),
            exact_prompt=request.exact_prompt,
            prompt_sha256=digest(request.exact_prompt),
            protocol_deviation=request.protocol_deviation,
            raw_response=request.raw_response,
            response_sha256=digest(request.raw_response),
            metadata=request.metadata,
            history=(revision,),
            collector_version=COLLECTOR_VERSION,
            software_version=version("astrotrust"),
            instrument_version=INSTRUMENT_VERSION,
            code_revision=self.code_revision,
            code_worktree_dirty=self.code_worktree_dirty,
        )
        self.store.insert_many((run,))
        return run


def progress(
    runs: tuple[ManualRun, ...],
    scenario_id: str,
    condition: Condition,
    *,
    scenario_sha256: str | None = None,
) -> dict[str, object]:
    """Coverage only, grouped by exact UI label. Never sum different labels into one model."""
    selected = tuple(
        r
        for r in runs
        if r.canonical_prompt.scenario_id == scenario_id
        and (scenario_sha256 is None or r.canonical_prompt.scenario_sha256 == scenario_sha256)
        and r.canonical_prompt.condition.emotion == condition.emotion
        and r.canonical_prompt.condition.personalization == condition.personalization
        and r.canonical_prompt.condition.language == condition.language
    )
    groups: list[dict[str, object]] = []
    for provider, product in FRONTENDS:
        labels = sorted(
            {
                r.metadata.model_label
                for r in selected
                if (r.metadata.provider, r.metadata.product) == (provider, product)
            }
        )
        slots: tuple[str | None, ...] = tuple(labels) if labels else (None,)
        for label in slots:
            matching = tuple(
                r
                for r in selected
                if (r.metadata.provider, r.metadata.product, r.metadata.model_label)
                == (provider, product, label)
            )
            cells = [
                {
                    "belief": belief,
                    "runs": [
                        any(
                            r.canonical_prompt.condition.belief == belief
                            and r.metadata.run_number == number
                            for r in matching
                        )
                        for number in (1, 2, 3)
                    ],
                }
                for belief in BELIEFS
            ]
            groups.append(
                {"provider": provider, "product": product, "model_label": label, "cells": cells}
            )
    # Noncanonical prompts/nonfresh chats stay visible as captures, never certify independence.
    return {
        "groups": groups,
        "planned_captures": 27,
        "captured": len(selected),
        "interpretation": "Capture coverage only; not validity",
    }

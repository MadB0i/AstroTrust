"""Fixed consumer prompt registry and manual capture, with no remote integrations."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from astrotrust.benchmark.prompts import digest
from astrotrust.collector.consumer_models import (
    CONSUMER_VERSION,
    PROMPTS,
    REGISTRY_VERSION,
    ConsumerRequest,
    ConsumerRevision,
    ConsumerRun,
)
from astrotrust.collector.consumer_profiles import PROFILES
from astrotrust.collector.consumer_store import ConsumerStore
from astrotrust.collector.models import STATUS
from astrotrust.collector.service import code_provenance


class ConsumerCollector:
    def __init__(self, root: Path, store: ConsumerStore) -> None:
        self.store = store
        self.code_revision, self.code_worktree_dirty = code_provenance(root)

    def save(self, request: ConsumerRequest) -> ConsumerRun:
        canonical = PROMPTS[request.prompt_id]
        if digest(canonical) != request.registry_prompt_sha256:
            raise ValueError("Prompt changed or stale. Reload the consumer registry before saving.")
        run = ConsumerRun(
            kind="consumer_astrology_capture",
            schema_version="consumer-1.1",
            source_category="consumer_astrology_service",
            study_phase="exploratory_pilot",
            research_status=STATUS,
            run_id=f"consumer-{uuid4().hex}",
            prompt_id=request.prompt_id,
            registry_version=REGISTRY_VERSION,
            registry_prompt=canonical,
            registry_prompt_sha256=digest(canonical),
            exact_prompt=request.exact_prompt,
            prompt_sha256=digest(request.exact_prompt),
            protocol_deviation=request.protocol_deviation,
            raw_response=request.raw_response,
            response_sha256=digest(request.raw_response),
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            profile_sha256=request.profile_sha256,
            profile_fields_submitted=request.profile_fields_submitted,
            gender_required=request.gender_required,
            profile_snapshot=None
            if request.profile_id == "not_used"
            else PROFILES[request.profile_id],
            interaction_mode=request.interaction_mode,
            interaction_record_type=request.interaction_record_type,
            exact_interaction=request.exact_interaction,
            interaction_sha256=(
                None if request.exact_interaction is None else digest(request.exact_interaction)
            ),
            metadata=request.metadata,
            history=(
                ConsumerRevision(
                    revision=1,
                    recorded_at=datetime.now(UTC),
                    reason="Initial manual consumer capture",
                    metadata=request.metadata,
                ),
            ),
            collector_version=CONSUMER_VERSION,
            software_version=version("astrotrust"),
            code_revision=self.code_revision,
            code_worktree_dirty=self.code_worktree_dirty,
        )
        self.store.insert_many((run,))
        return run


def summary(run: ConsumerRun) -> dict[str, object]:
    m = run.metadata
    return {
        "source_category": run.source_category,
        "run_id": run.run_id,
        "service_name": m.service_name,
        "prompt_id": run.prompt_id,
        "run_number": m.run_number,
        "timestamp": m.timestamp,
        "timezone": m.timezone,
        "response_complete": m.response_complete,
    }

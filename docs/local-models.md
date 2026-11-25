# Local small-model inference interface

Implemented: provider-independent `InferenceAdapter.generate(LocalRequest)` and
an explicitly supplied subprocess adapter. Pending: selection/installation of a
real checkpoint, a runtime-specific adapter and real inference experiments.
No model download, provider SDK, training loop or validated AstroGuard is included.

`LocalRequest` schema `local-request-1.0` requires `operation=inference_only`,
`study_phase=exploratory_pilot`, requested model identity, SHA-256 of model and
tokenizer artifacts, runtime description, exact existing `Prompt`, generation
settings and replicate number. Pin quantization, hardware, chat template/runtime
version and any additional messages. Use the existing renderer for development
prompts; research-use review gates remain unchanged. Hash every actual message,
including any system messages; a runtime that silently adds content violates the
declared protocol. For multiple artifact files use a canonical file-hash manifest
and hash that manifest; document the convention in the runtime description.

Inspect the request schema:

```powershell
python -c "import json; from astrotrust.research.local import LocalRequest; print(json.dumps(LocalRequest.model_json_schema(), indent=2))"
python -m astrotrust research infer-local --help
```

The command adapter writes the complete request as UTF-8 JSON on stdin. The runtime
must return one JSON object on stdout with exactly these fields:

```json
{
  "raw_response": "Exact runtime response text",
  "returned_model_identifier": null,
  "model_version": null,
  "observed_settings": {}
}
```

This illustrates the contract, not a collected output. Preserve response whitespace
and Unicode in JSON; keep diagnostics off stdout. Requested settings and actually
observed settings are distinct. Unknown identifiers/settings remain null or absent
from the observed map, not assumed defaults. A custom Python adapter implements
the same Protocol, returning a validated `InferenceResult`.

After preparing a real request and an already installed inference-only adapter:

```powershell
python -m astrotrust research infer-local data/private/local-request.json --output data/runs/local/attempt-001.json --adapter-command python path/to/installed_inference_adapter.py
python -m astrotrust research validate-local data/runs/local/attempt-001.json
```

`--adapter-command` consumes the remaining arguments; place it last. The command is
executed only on this explicit action, with `shell=False` and a timeout (default
120 seconds). Do not put credentials in the command, request or runtime description.
Only use a trusted inference-only runtime: this boundary cannot prove an arbitrary
user-supplied program does not train, download or contact a service. Navigation,
validation and tests do not invoke a real model. No runtime is bundled or selected.

The output file is reserved exclusively before inference, preventing accidental
overwrite/re-execution. Every normal adapter failure, invalid response or timeout
becomes a saved failed attempt and nonzero CLI exit; no retries are hidden. Each
retry needs a new output file and run ID. Interruption/process crash/disk failure
may leave a partial file: preserve it as an interrupted attempt and retry to a new
path. Provider stderr/stdout from failed commands is not captured in the result;
the adapter should keep separate private diagnostic logs if needed.

`local-attempt-1.0` embeds the full request and its hash, a standard `ModelRun`,
response hash, adapter identity/command, observed settings, code revision/dirty
status and Python/platform/package versions. Model/tokenizer hashes and hardware
descriptions are researcher declarations, not independently verified by the runner.
Validate actual artifacts in the runtime before generation. No fine-tuning gain or
safety outcome follows from interface tests. These artifacts remain pilot evidence.

## Split manifest contract

Use `SplitManifest` schema `splits-1.0`, policy `scenario-family-disjoint`, a rationale
and members with run ID, source (`frontier|consumer|local`), scenario family,
scenario hash, exact prompt hash, response hash (null for failures), and role
(`pilot|train|validation|test`). Keep revisions/translations/related consumer variants
in one family; pilot material cannot be made an untouched test by assigning new IDs.

```powershell
python -c "import json; from astrotrust.research.splits import SplitManifest; print(json.dumps(SplitManifest.model_json_schema(), indent=2))"
python -m astrotrust research validate-splits data/private/splits.json
```

The validator rejects duplicate run assignments and any declared family, scenario,
prompt or response hash across roles. It cannot discover omitted records, semantic
paraphrases with dishonest family IDs or prior exposure. Source-hash verification
and independent grouping review remain required. All current career pilot variants
and related consumer career prompts belong to the same development family.

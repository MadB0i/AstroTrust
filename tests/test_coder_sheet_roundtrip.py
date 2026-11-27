"""Offline tests for the second-coder CSV export/import roundtrip using synthetic inputs."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from astrotrust.__main__ import main as astrotrust_cli

ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str, filename: str) -> ModuleType:
    path = ROOT / "tools" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_coder_sheet_roundtrip_synthetic(tmp_path: Path) -> None:
    packet_path = ROOT / "reviews" / "generated" / "blind_second_coder_packet.json"
    key_path = ROOT / "reviews" / "generated" / "blind_coder_key_PRIVATE.json"
    if not packet_path.is_file() or not key_path.is_file():
        return

    export_mod = _load_tool("export_coder_sheet_tool", "export_coder_sheet.py")
    import_mod = _load_tool("import_coder_sheet_tool", "import_coder_sheet.py")

    r2_csv, r1_csv, inst_md = export_mod.export_sheets(packet_path=packet_path, out_dir=tmp_path)
    assert inst_md.is_file()

    # Fill strictly synthetic dummy labels in temporary test CSVs to verify schema validation + CLI
    for csv_path, rel_val, fram_val in (
        (r1_csv, "reflective_only", "cultural_interpretation"),
        (r2_csv, "reflective_only", "cultural_interpretation"),
    ):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
            fieldnames = list(rows[0].keys())
        for idx, row in enumerate(rows):
            if idx == 0:
                row["decision_reliance"] = "complementary_basis"
                row["epistemic_framing"] = "uncertain_prediction"
            else:
                row["decision_reliance"] = rel_val
                row["epistemic_framing"] = fram_val
            row["practical_grounding"] = "minimal"
            row["annotation_uncertainty"] = "clear"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    out_batch = tmp_path / "independent.json"
    batch, reports = import_mod.merge_and_score(
        key_path=key_path,
        rater2_csv=r2_csv,
        rater1_csv=r1_csv,
        out_path=out_batch,
        timestamp_iso="2026-11-26T19:00:00+05:30",
    )
    assert len(batch.annotations) == 80
    assert reports["decision_reliance_linear"]["result"]["kappa"] == 1.0
    assert reports["epistemic_framing_nominal"]["result"]["kappa"] == 1.0

    # Verify CLI validate and agreement commands succeed on the generated AnnotationBatch
    assert astrotrust_cli(["annotations", "validate", str(out_batch)]) == 0
    assert (
        astrotrust_cli(
            [
                "annotations",
                "agreement",
                str(out_batch),
                "--kind",
                "response",
                "--field",
                "decision_reliance",
                "--raters",
                "rater-01",
                "rater-02",
                "--weights",
                "linear",
            ]
        )
        == 0
    )
    parsed = json.loads(out_batch.read_text(encoding="utf-8"))
    assert parsed["kind"] == "annotation_batch"

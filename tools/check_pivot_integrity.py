"""Snapshot/verify protected evidence and instruments; no raw response text is printed."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from astrotrust.collector.consumer_store import DEFAULT_CONSUMER_DATABASE
from astrotrust.collector.store import DEFAULT_DATABASE
from astrotrust.research.inventory import research_status

ROOT = Path(__file__).resolve().parents[1]


def fingerprints(root: Path) -> dict[str, str]:
    paths = set((root / "benchmark").rglob("*.json")) | set((root / "reviews").rglob("*"))
    paths |= set((root / "data/pilot/exports").glob("*"))
    paths |= set((root / "data/pilot").glob("*.jsonl"))
    paths |= set((root / "data/pilot").glob("*.md"))
    paths |= {root / DEFAULT_DATABASE, root / DEFAULT_CONSUMER_DATABASE}
    paths |= {
        root / "astrotrust/collector/consumer_profiles.py",
        root / "astrotrust/collector/consumer_models.py",
        root / "astrotrust/collector/models.py",
    }
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
        if p.is_file() and "__pycache__" not in p.parts
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "verify"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    current = fingerprints(root)
    if args.action == "snapshot":
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open("x", encoding="utf-8") as file:
            json.dump(current, file, indent=2)
            file.write("\n")
    else:
        expected = json.loads(args.manifest.read_text("utf-8"))
        changed = [name for name, hashed in expected.items() if current.get(name) != hashed]
        if changed:
            print("Changed/missing protected files: " + ", ".join(changed))
            return 1
    status = research_status(root / DEFAULT_DATABASE, root / DEFAULT_CONSUMER_DATABASE)
    print(json.dumps({"protected_files": len(current), "stores": status}, indent=2))
    return int(status["frontier"]["state"] == "error" or status["consumer"]["state"] == "error")


if __name__ == "__main__":
    raise SystemExit(main())

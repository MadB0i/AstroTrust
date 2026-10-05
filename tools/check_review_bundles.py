"""Check frozen pending bundles against their documented seeds; keys need not be on disk."""

from pathlib import Path

from astrotrust import INSTRUMENT_VERSION
from astrotrust.benchmark.prompts import load_template
from astrotrust.reviews.export import build_packet, reviewer_files, validate_mapping
from astrotrust.validation.files import load_scenarios

BUNDLE_SEEDS = {"reviewer-a": 20261007, "reviewer-b": 20261008}


def check_bundles() -> None:
    scenarios = load_scenarios(Path("benchmark/scenarios"))
    template = load_template(Path("benchmark/prompts/controlled-v1.json"))
    orders = []
    for name, seed in BUNDLE_SEEDS.items():
        packet, key, feedback = build_packet(scenarios, template, seed=seed)
        validate_mapping(packet, key)
        folder = Path("reviews/pending") / name
        expected = reviewer_files(packet, feedback)
        if not folder.is_dir() or {p.name for p in folder.iterdir()} != set(expected):
            raise ValueError(f"{name}: reviewer bundle must contain only the five required files")
        for filename, content in expected.items():
            if (folder / filename).read_bytes() != content.encode("utf-8"):
                raise ValueError(f"{name}: bundle drift in {filename}; do not edit frozen assets")
        orders.append(tuple(key.entries[i.prompts[0].variant_id].scenario_id for i in packet.items))
    if orders[0] == orders[1]:
        raise ValueError("reviewer bundles must use different scenario orders")


def main() -> int:
    try:
        check_bundles()
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"{INSTRUMENT_VERSION}: both pending bundles reproduce; no completed reviews.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

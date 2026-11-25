"""Check local links in active research documentation, excluding archived source text."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    docs = sorted({ROOT / "README.md", *ROOT.glob("docs/**/*.md"), *ROOT.glob("*/README.md")})
    broken: list[str] = []
    for doc in docs:
        text = re.sub(r"```.*?```", "", doc.read_text("utf-8"), flags=re.S)
        for reference in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if "://" in reference or reference.startswith("#"):
                continue
            target = reference.split("#")[0]
            if target and not (doc.parent / target).exists():
                broken.append(f"{doc.relative_to(ROOT)}: {reference}")
    if broken:
        print("Broken document links:\n" + "\n".join(broken))
        return 1
    print(f"Local file links resolve in {len(docs)} active research documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

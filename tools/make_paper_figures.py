"""Generate publication-grade vector PDF (and optional PNG preview) charts for the AstroTrust paper.

Reads verified aggregate counts directly from:
  - `data/results/apk_forensic_summary.json` -> `paper/figures/fig_app_taxonomy.pdf` (Figure 3)
  - `data/results/empirical_comparison_table.json` -> `paper/figures/fig_four_cohort.pdf` (Figure 4)
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APK_JSON = ROOT / "data" / "results" / "apk_forensic_summary.json"
DEFAULT_EMP_JSON = ROOT / "data" / "results" / "empirical_comparison_table.json"
DEFAULT_FIG_DIR = ROOT / "paper" / "figures"

# Ordered short paper labels paired 1-to-1 with exact category keys in apk_forensic_summary.json.
_TAXONOMY_LABELS: tuple[tuple[str, str, bool], ...] = (
    ("Travel, E-Commerce, Ride-Hailing, Food & Other", "E-Commerce / Travel / Other", False),
    ("Global Banking, UPI, Wallets & Remittance", "Global Banking & UPI", True),
    ("Competitor Astrology, Tarot, Psychic & Advisor", "Competitor Astrology", True),
    ("OTT Streaming, Media, News & Audio", "OTT Media & Audio", False),
    ("Real-Money Gambling, Fantasy Sports & Betting", "Gambling & Fantasy Betting", True),
    ("Dating, Matrimony & Live Video Chat", "Dating & Matrimony", True),
    ("Stock Trading, Wealth & Crypto", "Stocks / Wealth / Crypto", True),
    ("Consumer Loans, BNPL, Gold Loans & Credit", "Loans / BNPL / Gold Loans", True),
    ("Health, Insurance, Pharmacy & Wearables", "Health & Wearables", False),
    ("EdTech, Exam Prep & Job Search", "EdTech & Job Search", False),
    ("Devotional, Panchang & Spiritual", "Devotional & Panchang", False),
    ("Reproductive Health, Pregnancy & Mental Therapy", "Reproductive & Therapy", True),
    ("Gig-Economy Driver & Delivery Partner", "Gig Driver & Delivery", True),
    ("AI Assistants", "AI Assistants", True),
    ("Indian Government Identity & Welfare", "Indian Govt ID & Welfare", True),
    ("Rail & Commuter Transit", "Rail & Transit", False),
)


def _configure_matplotlib() -> Any:
    import matplotlib  # type: ignore[import-not-found]

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
            "axes.edgecolor": "#4A5568",
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    return plt


def build_taxonomy_chart(
    apk_json_path: Path,
    out_dir: Path,
    *,
    write_png_preview: bool = False,
) -> Path:
    """Render Figure 3 (`apppackges.json` domains) with generous non-clipping margins."""
    plt = _configure_matplotlib()
    payload = json.loads(apk_json_path.read_text(encoding="utf-8"))
    breakdown: dict[str, int] = payload["apks"][0]["tracker_evidence"]["category_breakdown"]
    total = sum(breakdown.values())

    rows: list[tuple[str, int, bool]] = []
    for raw_key, short_label, high_sensitivity in _TAXONOMY_LABELS:
        if raw_key not in breakdown:
            raise KeyError(f"Missing expected APK category key: {raw_key!r}")
        rows.append((short_label, int(breakdown[raw_key]), high_sensitivity))

    # Plot smallest at bottom, largest at top.
    rows.reverse()
    labels = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    colors = ["#204E8A" if r[2] else "#5A626C" for r in rows]

    fig, ax = plt.subplots(figsize=(7.8, 5.2), dpi=300)
    y_pos = list(range(len(labels)))
    bars = ax.barh(y_pos, counts, height=0.68, color=colors, edgecolor="#182C46", linewidth=0.5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.2, color="#1A202C")
    ax.set_xlim(0, 238)
    ax.set_xlabel(
        rf"Targeted Package Count inside Astrotalk assets/apppackges.json ($N={total}$)",
        fontsize=9.5,
        labelpad=8,
        color="#1A202C",
    )
    ax.tick_params(axis="x", labelsize=8.8, colors="#1A202C")
    ax.xaxis.grid(True, linestyle="--", alpha=0.35, color="#94A3B8")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, count in zip(bars, counts, strict=True):
        pct = 100.0 * count / total
        ax.text(
            count + 2.8,
            bar.get_y() + bar.get_height() / 2.0,
            f"{count} ({pct:.1f}%)",
            va="center",
            ha="left",
            fontsize=8.0,
            color="#1A202C",
        )

    from matplotlib.patches import Patch  # type: ignore[import-not-found]

    ax.legend(
        handles=[
            Patch(
                facecolor="#204E8A",
                edgecolor="#182C46",
                label="Financial / Intimate / Competitive Proxy",
            ),
            Patch(
                facecolor="#5A626C",
                edgecolor="#182C46",
                label="General Consumer / Lifestyle Proxy",
            ),
        ],
        loc="lower right",
        fontsize=8.2,
        frameon=True,
        facecolor="#F8F9FB",
        edgecolor="#CBD5E1",
    )

    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig_app_taxonomy.pdf"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.18, dpi=300)
    if write_png_preview:
        fig.savefig(out_dir / "fig_app_taxonomy.png", bbox_inches="tight", pad_inches=0.18, dpi=300)
    plt.close(fig)
    return pdf_path


def build_four_cohort_chart(
    emp_json_path: Path,
    out_dir: Path,
    *,
    write_png_preview: bool = False,
) -> Path:
    """Render Figure 4 (Four-cohort bars) with clean legend spacing and bar labels."""
    plt = _configure_matplotlib()
    emp = json.loads(emp_json_path.read_text(encoding="utf-8"))

    cohorts: list[tuple[str, dict[str, Any], str]] = [
        ("Frontier (N=27)", emp["Frontier Models"], "#204E8A"),
        ("Consumer (N=6)", emp["Consumer Apps"], "#AC2C2C"),
        ("Local 0.5B (N=30)", emp["Local Qwen2.5-0.5B"], "#C48A18"),
        ("Local 1.5B (N=30)", emp["Local Qwen2.5-1.5B"], "#5A626C"),
    ]

    # Plot verified pct fields; Safe Calibrated* requires calibrated text AND zero dark patterns.
    metrics: list[tuple[str, Callable[[dict[str, Any]], float]]] = [
        (
            "Safe\nCalibrated*",
            lambda d: (
                0.0
                if float(d["commercial_dark_pattern"]["pct"]) == 100.0
                else float(d["safe_calibrated"]["pct"])
            ),
        ),
        ("Explicit\nDrift", lambda d: float(d["explicit_hallucination_or_misread"]["pct"])),
        ("Token\nCutoffs", lambda d: float(d["mid_sentence_truncation"]["pct"])),
        ("Dark\nPatterns", lambda d: float(d["commercial_dark_pattern"]["pct"])),
    ]

    fig, ax = plt.subplots(figsize=(6.4, 4.1), dpi=300)
    n_groups = len(metrics)
    n_bars = len(cohorts)
    bar_w = 0.19
    group_centers = [float(i) * 1.08 for i in range(n_groups)]

    for c_idx, (label, data, color) in enumerate(cohorts):
        offset = (c_idx - (n_bars - 1) / 2.0) * bar_w
        xs = [gc + offset for gc in group_centers]
        ys = [round(fn(data), 1) for _, fn in metrics]
        bars = ax.bar(
            xs,
            ys,
            width=bar_w * 0.92,
            label=label,
            color=color,
            edgecolor="#1E293B",
            linewidth=0.5,
        )
        for bar, yval in zip(bars, ys, strict=True):
            txt = "0" if yval == 0.0 else f"{yval:.1f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                yval + 2.2,
                txt,
                ha="center",
                va="bottom",
                fontsize=7.3,
                rotation=90,
                color="#1A202C",
            )

    ax.set_xticks(group_centers)
    ax.set_xticklabels([m[0] for m in metrics], fontsize=8.8, color="#1A202C")
    ax.set_ylim(0, 124)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("Rate Across Runs (%)", fontsize=9.0, labelpad=6, color="#1A202C")
    ax.tick_params(axis="y", labelsize=8.5, colors="#1A202C")
    ax.yaxis.grid(True, linestyle="--", alpha=0.35, color="#94A3B8")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=False,
        fontsize=8.3,
        columnspacing=1.4,
        handlelength=1.4,
    )

    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "fig_four_cohort.pdf"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.18, dpi=300)
    if write_png_preview:
        fig.savefig(out_dir / "fig_four_cohort.png", bbox_inches="tight", pad_inches=0.18, dpi=300)
    plt.close(fig)
    return pdf_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk-json", type=Path, default=DEFAULT_APK_JSON)
    parser.add_argument("--emp-json", type=Path, default=DEFAULT_EMP_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_FIG_DIR)
    parser.add_argument("--png-preview", action="store_true")
    args = parser.parse_args(argv)

    p3 = build_taxonomy_chart(args.apk_json, args.out_dir, write_png_preview=args.png_preview)
    p4 = build_four_cohort_chart(args.emp_json, args.out_dir, write_png_preview=args.png_preview)
    print(f"Wrote paper figures -> {p3}, {p4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Stitch and redact 3-panel consumer evidence screenshots for the AstroTrust paper.

Creates `paper/figures/fig_consumer_evidence.png` from three verified Android captures:
  (a) AstroSage Rahasya Veda ("1 Years of Experience", New User INR 1/min, 1,176,176 reviews)
  (b) AstroSage Rahasya Veda (00:01:28 countdown timer and Free Chat onboarding)
  (c) AstroTime (unprompted Barnum cold reading, 60s auto-close, 100% Cashback prompt)

Supports optional normalized cropping (`x0,y0,x1,y1`) and solid black redaction boxes over
sensitive regions (phone numbers, UPI IDs, reviewer previews, or account handles).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "paper" / "figures" / "fig_consumer_evidence.png"
DEFAULT_PANEL_A = Path(r"D:\ASTRO\WhatsApp Image 2026-11-11 at 9.00.37 PM.jpeg")
DEFAULT_PANEL_B = Path(r"D:\ASTRO\WhatsApp Image 2026-11-11 at 8.58.12 PM.jpeg")
DEFAULT_PANEL_C = Path(r"D:\ASTRO\WhatsApp Image 2026-11-24 at 2.32.02 PM.jpeg")

Box = tuple[float, float, float, float]
HighlightBox = tuple[float, float, float, float]
PanelSpec = tuple[str, Path, Box | None, list[Box], list[HighlightBox]]


def parse_box(raw: str) -> Box:
    """Parse a normalized box `x0,y0,x1,y1` in [0.0, 1.0]."""
    parts = [float(p.strip()) for p in raw.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"Expected 4 comma-separated floats, got: {raw!r}")
    x0, y0, x1, y1 = parts
    if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
        raise argparse.ArgumentTypeError(f"Box coordinates must satisfy 0<=x0<x1<=1: {raw!r}")
    return x0, y0, x1, y1


def _load_pillow() -> tuple[Any, Any, Any, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Pillow is required to stitch evidence images. Install with `pip install pillow` "
            "or run using a Python interpreter where Pillow is installed."
        ) from exc
    return Image, ImageDraw, ImageFont, ImageOps


def _load_header_font(image_font_cls: Any, size: int) -> Any:
    font_candidates = (
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    )
    for candidate in font_candidates:
        if candidate.is_file():
            return image_font_cls.truetype(str(candidate), size=size)
    return (
        image_font_cls.load_default(size=size) if hasattr(image_font_cls, "load_default") else None
    )


def _redact_and_resize(
    img_path: Path,
    crop_box: Box | None,
    boxes: list[Box],
    highlights: list[HighlightBox],
    target_height: int,
) -> Any:
    Image, ImageDraw, _, ImageOps = _load_pillow()
    if not img_path.is_file():
        raise FileNotFoundError(f"Missing screenshot: {img_path}")

    img = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for x0, y0, x1, y1 in boxes:
        draw.rectangle(
            (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)),
            fill=(15, 15, 15),
        )

    if crop_box is not None:
        cx0, cy0, cx1, cy1 = crop_box
        crop_px = (int(cx0 * w), int(cy0 * h), int(cx1 * w), int(cy1 * h))
        img = img.crop(crop_px)
    else:
        crop_px = (0, 0, w, h)

    cw, ch = img.size
    scale = target_height / float(ch)
    new_w = max(1, int(round(cw * scale)))
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    resized = img.resize((new_w, target_height), resampling)

    if highlights:
        rdraw = ImageDraw.Draw(resized)
        left_px, top_px, _, _ = crop_px
        stroke = max(3, int(round(target_height * 0.0032)))
        radius = max(4, stroke * 2)
        for hx0, hy0, hx1, hy1 in highlights:
            rx0 = int(round((hx0 * w - left_px) * scale))
            ry0 = int(round((hy0 * h - top_px) * scale))
            rx1 = int(round((hx1 * w - left_px) * scale))
            ry1 = int(round((hy1 * h - top_px) * scale))
            rx0 = max(stroke, min(new_w - stroke - 1, rx0))
            rx1 = max(rx0 + stroke, min(new_w - stroke, rx1))
            ry0 = max(stroke, min(target_height - stroke - 1, ry0))
            ry1 = max(ry0 + stroke, min(target_height - stroke, ry1))
            rdraw.rounded_rectangle(
                (rx0, ry0, rx1, ry1),
                radius=radius,
                outline=(208, 32, 38),
                width=stroke,
            )

    return resized


def build_evidence_strip(
    panels: list[PanelSpec],
    out_path: Path = DEFAULT_OUT,
    target_height: int = 1280,
    gap: int = 36,
    header_height: int = 64,
) -> Path:
    """Render a 3-panel horizontal composite with crisp captions, redactions, and callout boxes."""
    Image, ImageDraw, ImageFont, _ = _load_pillow()
    rendered: list[tuple[str, Any]] = [
        (title, _redact_and_resize(path, crop_box, boxes, highlights, target_height))
        for title, path, crop_box, boxes, highlights in panels
    ]

    total_w = sum(im.width for _, im in rendered) + gap * (len(rendered) + 1)
    total_h = target_height + header_height + gap * 2
    canvas = Image.new("RGB", (total_w, total_h), color=(248, 249, 251))
    draw = ImageDraw.Draw(canvas)
    font = _load_header_font(ImageFont, size=24)

    x = gap
    for title, im in rendered:
        draw.text((x, gap // 2 + 10), title, fill=(24, 34, 52), font=font)
        draw.rectangle(
            (x - 2, gap + header_height - 2, x + im.width + 1, gap + header_height + im.height + 1),
            outline=(200, 206, 216),
            width=2,
        )
        canvas.paste(im, (x, gap + header_height))
        x += im.width + gap

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-a", type=Path, default=DEFAULT_PANEL_A)
    parser.add_argument("--panel-b", type=Path, default=DEFAULT_PANEL_B)
    parser.add_argument("--panel-c", type=Path, default=DEFAULT_PANEL_C)
    parser.add_argument("--title-a", default="(a) AstroSage: 1,176,176 Reviews & 1 Yr Exp.")
    parser.add_argument("--title-b", default="(b) AstroSage: 90s Countdown Timer (00:01:28)")
    parser.add_argument("--title-c", default="(c) AstroTime: Cold Reading, 60s Close & Cashback")
    parser.add_argument("--crop-a", type=parse_box, default=(0.085, 0.118, 0.948, 0.851))
    parser.add_argument("--crop-b", type=parse_box, default=(0.215, 0.088, 0.785, 0.928))
    parser.add_argument("--crop-c", type=parse_box, default=(0.198, 0.072, 0.802, 0.930))
    parser.add_argument(
        "--redact-a",
        type=parse_box,
        action="append",
        default=[],
        help="Normalized redaction box x0,y0,x1,y1 for Panel (a) (repeatable)",
    )
    parser.add_argument(
        "--redact-b",
        type=parse_box,
        action="append",
        default=[],
        help="Normalized redaction box x0,y0,x1,y1 for Panel (b) (repeatable)",
    )
    parser.add_argument(
        "--redact-c",
        type=parse_box,
        action="append",
        default=[],
        help="Normalized redaction box x0,y0,x1,y1 for Panel (c) (repeatable)",
    )
    parser.add_argument(
        "--highlight-a",
        type=parse_box,
        action="append",
        default=[(0.406, 0.287, 0.774, 0.319), (0.712, 0.790, 0.896, 0.823)],
        help="Normalized red highlight box x0,y0,x1,y1 for Panel (a) (repeatable)",
    )
    parser.add_argument(
        "--highlight-b",
        type=parse_box,
        action="append",
        default=[(0.362, 0.120, 0.474, 0.149)],
        help="Normalized red highlight box x0,y0,x1,y1 for Panel (b) (repeatable)",
    )
    parser.add_argument(
        "--highlight-c",
        type=parse_box,
        action="append",
        default=[(0.214, 0.132, 0.764, 0.174), (0.215, 0.542, 0.768, 0.625)],
        help="Normalized red highlight box x0,y0,x1,y1 for Panel (c) (repeatable)",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    panels: list[PanelSpec] = [
        (args.title_a, args.panel_a, args.crop_a, list(args.redact_a), list(args.highlight_a)),
        (args.title_b, args.panel_b, args.crop_b, list(args.redact_b), list(args.highlight_b)),
        (args.title_c, args.panel_c, args.crop_c, list(args.redact_c), list(args.highlight_c)),
    ]
    out_path = build_evidence_strip(panels, out_path=args.out)
    print(f"Wrote redacted 3-panel evidence figure -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

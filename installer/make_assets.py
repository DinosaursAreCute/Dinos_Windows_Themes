"""
Generate installer assets from the project logo SVG.

Usage (run from the installer/ directory):
    python make_assets.py

Outputs:
    assets/logo.png  – 256×256 PNG
    assets/icon.ico  – multi-size ICO (16, 32, 48, 64, 128, 256)

Strategy (tried in order):
  1. cairosvg   – best quality, needs libcairo
  2. svglib      – pure-Python, decent quality
  3. PIL fallback – programmatic draw, always works
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
SVG     = ROOT / "logo.svg"
OUT_DIR = Path(__file__).parent / "assets"
OUT_DIR.mkdir(exist_ok=True)
PNG     = OUT_DIR / "logo.png"
ICO     = OUT_DIR / "icon.ico"


# ── Conversion attempts ──────────────────────────────────────────────────────────

def _try_cairosvg() -> bool:
    try:
        import cairosvg  # type: ignore
        cairosvg.svg2png(url=str(SVG), write_to=str(PNG), output_width=256, output_height=256)
        print("✓ logo.png via cairosvg")
        return True
    except Exception as e:
        print(f"  cairosvg unavailable: {e}")
        return False


def _try_svglib() -> bool:
    try:
        from svglib.svglib import svg2rlg  # type: ignore
        from reportlab.graphics import renderPM  # type: ignore
        drawing = svg2rlg(str(SVG))
        if drawing is None:
            return False
        renderPM.drawToFile(drawing, str(PNG), fmt="PNG", dpi=96)
        print("✓ logo.png via svglib + reportlab")
        return True
    except Exception as e:
        print(f"  svglib unavailable: {e}")
        return False


def _try_inkscape() -> bool:
    import shutil
    if not shutil.which("inkscape"):
        return False
    ret = os.system(
        f'inkscape "{SVG}" --export-type=png --export-filename="{PNG}" -w 256 -h 256'
    )
    if ret == 0 and PNG.exists():
        print("✓ logo.png via Inkscape")
        return True
    return False


def _pil_fallback() -> None:
    """Draw a logo that mirrors the SVG design using pure Pillow."""
    from PIL import Image, ImageDraw

    SIZE  = 256
    BG    = "#111415"
    PANEL = "#181C1E"
    PINK  = "#C44B8E"
    HI    = "#E8719A"

    img  = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=42, fill=BG)

    # Hexagon fill + border
    cx, cy = SIZE // 2, SIZE // 2
    r_outer = SIZE // 2 - 12
    r_inner = r_outer - 3

    def hex_pts(r: float) -> list[tuple[float, float]]:
        return [
            (cx + r * math.cos(math.radians(90 + i * 60)),
             cy + r * math.sin(math.radians(90 + i * 60)))
            for i in range(6)
        ]

    draw.polygon(hex_pts(r_outer), fill=PANEL)
    draw.polygon(hex_pts(r_inner), fill=PANEL)
    draw.polygon(hex_pts(r_outer), outline=PINK, width=2)

    # Accent dots at hex vertices
    for px, py in hex_pts(r_outer):
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=HI)

    # T-Rex silhouette (scaled to 256px)
    scale = SIZE / 400.0

    def s(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [(x * scale, y * scale) for x, y in pts]

    # Tail
    draw.polygon(s([(72, 235), (115, 210), (125, 250), (88, 268)]),   fill=PINK)
    draw.polygon(s([(88, 268), (125, 250), (118, 280), (90, 282)]),   fill=PINK)
    # Hind leg + foot
    draw.rectangle(s([(143, 270), (165, 320)]), fill=PINK)
    draw.polygon(s([(133, 318), (168, 318), (178, 335), (124, 335)]), fill=PINK)
    # Front leg + foot
    draw.rectangle(s([(196, 270), (216, 314)]), fill=PINK)
    draw.polygon(s([(186, 312), (218, 312), (226, 328), (180, 328)]), fill=PINK)
    # Body
    draw.ellipse(s([(105, 200), (245, 290)]), fill=PINK)
    # Neck
    draw.polygon(s([(212, 205), (248, 155), (268, 165), (230, 220)]), fill=PINK)
    # Head
    draw.ellipse(s([(227, 122), (303, 174)]), fill=PINK)
    # Snout
    draw.polygon(s([(264, 136), (316, 130), (322, 144), (268, 154)]), fill=PINK)
    # Lower jaw
    draw.polygon(s([(270, 152), (314, 148), (308, 162), (268, 162)]), fill=PINK)
    # Arms
    draw.polygon(s([(238, 200), (260, 192), (266, 208), (244, 214)]), fill=PINK)
    draw.polygon(s([(260, 192), (274, 185), (278, 196), (264, 202)]), fill=PINK)
    # Eye
    ex, ey = int(274 * scale), int(143 * scale)
    draw.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=BG)
    draw.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=HI)
    draw.ellipse([ex, ey - 2, ex + 3, ey + 1],      fill="white")
    # Spine ridges
    for rx, ry, rot in [(230, 175, -40), (216, 189, -35), (200, 200, -30)]:
        sx, sy = int(rx * scale), int(ry * scale)
        draw.ellipse([sx - 8, sy - 4, sx + 8, sy + 4], fill=HI)

    # Floor accent line
    y_line = int(335 * scale)
    draw.line([(int(100 * scale), y_line), (int(300 * scale), y_line)],
              fill=PINK, width=2)

    img.save(PNG)
    print("✓ logo.png via Pillow fallback")


def _make_ico() -> None:
    from PIL import Image
    if not PNG.exists():
        print("⚠ logo.png missing, skipping icon.ico")
        return
    img = Image.open(PNG).convert("RGBA")
    img.save(ICO, format="ICO",
             sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("✓ icon.ico generated")


# ── Entry point ──────────────────────────────────────────────────────────────────

def main() -> None:
    if not SVG.exists():
        print(f"⚠ SVG not found at {SVG}; using Pillow fallback only")
        _pil_fallback()
    elif not (_try_cairosvg() or _try_svglib() or _try_inkscape()):
        _pil_fallback()
    _make_ico()


if __name__ == "__main__":
    main()

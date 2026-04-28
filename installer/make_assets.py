"""
Generate installer assets from the canonical PNG logo.

Usage (run from the installer/ directory):
    python make_assets.py

Inputs:
    assets/dino_themes.png

Outputs:
    assets/icon.ico  – multi-size ICO (16, 32, 48, 64, 128, 256)
"""
from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).parent / "assets"
OUT_DIR.mkdir(exist_ok=True)
SOURCE_PNG = OUT_DIR / "dino_themes.png"
ICO     = OUT_DIR / "icon.ico"

def _make_ico() -> None:
    from PIL import Image
    if not SOURCE_PNG.exists():
        print(f"⚠ {SOURCE_PNG.name} missing, skipping icon.ico")
        return
    img = Image.open(SOURCE_PNG).convert("RGBA")
    img.save(ICO, format="ICO",
             sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("✓ icon.ico generated")


# ── Entry point ──────────────────────────────────────────────────────────────────

def main() -> None:
    if not SOURCE_PNG.exists():
        print(f"⚠ Source image not found at {SOURCE_PNG}")
    _make_ico()


if __name__ == "__main__":
    main()

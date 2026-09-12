#!/usr/bin/env python3
"""LOGO 裁切 + 抠底：logo-w/b.png（大面积留白）→ logo-ink.png / logo-paper.png

- logo-src-w.png：象牙底 + 黑标 → 输出 logo-ink.png（墨标，透明底，用于浅色页面）
- logo-src-b.png：黑底 + 象牙标 → 输出 logo-paper.png（象牙标，透明底，用于深色 Hero）
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "brand"
OUT = 512
PAD = 8
THR = 96


def cutout(src: Path, mark_dark: bool) -> Image.Image:
    """mark_dark=True：源为浅底深标；False：源为深底浅标"""
    img = Image.open(src).convert("RGBA")
    gray = img.convert("L")
    mask_src = gray.point(lambda v: 255 if (v < THR if mark_dark else v > THR) else 0)

    box = mask_src.getbbox() or (0, 0, img.width, img.height)
    x0, y0, x1, y1 = box
    x0 = max(0, x0 - PAD)
    y0 = max(0, y0 - PAD)
    x1 = min(img.width, x1 + PAD)
    y1 = min(img.height, y1 + PAD)

    mark = mask_src.crop((x0, y0, x1, y1))
    w, h = x1 - x0, y1 - y0
    side = max(w, h)
    off = ((side - w) // 2, (side - h) // 2)

    color = (10, 10, 10, 255) if mark_dark else (245, 242, 234, 255)
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", (w, h), color), off, mark)
    alpha = Image.new("L", (side, side), 0)
    alpha.paste(mark, off)
    out.putalpha(alpha)
    return out.resize((OUT, OUT), Image.LANCZOS)


def main() -> None:
    src_w = ASSETS / "logo-src-w.png"
    src_b = ASSETS / "logo-src-b.png"
    if not src_w.exists() and (ASSETS / "logo-w.png").exists():
        (ASSETS / "logo-w.png").replace(src_w)
        (ASSETS / "logo-b.png").replace(src_b)
    cutout(src_w, mark_dark=True).save(ASSETS / "logo-ink.png")
    cutout(src_b, mark_dark=False).save(ASSETS / "logo-paper.png")
    print("生成 logo-ink.png（墨标，浅底用）/ logo-paper.png（象牙标，深底用）")


if __name__ == "__main__":
    main()

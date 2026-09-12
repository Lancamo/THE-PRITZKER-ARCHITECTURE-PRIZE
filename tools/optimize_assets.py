#!/usr/bin/env python3
"""A 数据官 · 素材压缩：把抓取到的大图统一压到展示所需尺寸

用法: python3 tools/optimize_assets.py [--dry]

- 肖像 assets/portraits：最长边 ≤ 900px
- 作品 assets/works、项目 assets/projects：最长边 ≤ 1400px
- 统一转 JPEG（quality 82、progressive），文件名不变，数据无需改动
- 已在阈值内的文件跳过
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
# 肖像保留官网原始精度（不压缩）；作品与项目照片压到展示所需尺寸
TARGETS = [("works", 1600), ("projects", 1600)]
EXTS = {".jpg", ".jpeg", ".png"}


def human(n: int) -> str:
    return f"{n / 1024 / 1024:.1f}MB" if n > 1024 * 1024 else f"{n / 1024:.0f}KB"


def optimize(path: Path, max_side: int, dry: bool) -> tuple[int, int]:
    before = path.stat().st_size
    try:
        img = Image.open(path)
        img.load()
        if max(img.size) <= max_side and path.suffix.lower() in (".jpg", ".jpeg") and before < 400_000:
            return before, before
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        if max(img.size) > max_side:
            ratio = max_side / max(img.size)
            img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)
        if dry:
            return before, before
        img.save(path, "JPEG", quality=82, optimize=True, progressive=True)
        return before, path.stat().st_size
    except Exception as exc:  # noqa: BLE001
        print(f"  ! 跳过 {path.name}：{exc}")
        return before, before


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只统计不写入")
    args = ap.parse_args()

    total_b = total_a = 0
    for folder, max_side in TARGETS:
        files = sorted(p for p in (ASSETS / folder).rglob("*") if p.suffix.lower() in EXTS and p.is_file())
        fb = fa = 0
        for p in files:
            b, a = optimize(p, max_side, args.dry)
            fb += b
            fa += a
        total_b += fb
        total_a += fa
        print(f"{folder}: {len(files)} 张 · {human(fb)} → {human(fa)}")
    print(f"合计：{human(total_b)} → {human(total_a)}{'（dry run）' if args.dry else ''}")


if __name__ == "__main__":
    main()

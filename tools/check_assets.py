#!/usr/bin/env python3
"""A 数据官 · 素材核验：检查数据中引用的素材文件是否都存在

用法: python3 tools/check_assets.py

- 扫描 data/editions.json 与 data/laureates.json 中的 portrait / photo / officialProjects 路径
- 列出缺失文件与所属届次，便于修复（退出码非 0 表示有缺失）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def check(paths: list[tuple[str, str]]) -> list[tuple[str, str]]:
    missing = []
    for ref, label in paths:
        if ref and not (ROOT / ref).exists():
            missing.append((label, ref))
    return missing


def main() -> None:
    editions = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))["editions"]
    dossiers = json.loads((DATA / "laureates.json").read_text(encoding="utf-8"))["dossiers"]

    refs: list[tuple[str, str]] = []
    for ed in editions:
        year = ed["year"]
        if ed.get("portrait"):
            refs.append((ed["portrait"], f"{year} 肖像"))
        for w in ed.get("works", []):
            if w.get("photo"):
                refs.append((w["photo"], f"{year} 作品 {w['title_cn']}"))
        for pj in ed.get("officialProjects", []):
            for ph in pj.get("photos", []):
                refs.append((ph, f"{year} 项目 {pj['title']}"))
    for year, d in dossiers.items():
        if d.get("portrait"):
            refs.append((d["portrait"], f"{year} 样板肖像"))
        for w in d.get("works", []):
            if w.get("photo"):
                refs.append((w["photo"], f"{year} 样板作品 {w.get('title_cn', '')}"))

    missing = check(refs)
    print(f"引用素材 {len(refs)} 条 · 缺失 {len(missing)} 条")
    for label, ref in missing:
        print(f"  ✗ {label} → {ref}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()

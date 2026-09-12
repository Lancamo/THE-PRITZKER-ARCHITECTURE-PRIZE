#!/usr/bin/env python3
"""A 数据官 · 报告重建：从磁盘已下载素材反推 assets/_fetch_report.json

- 扫描 assets/works、assets/portraits，按 <year>-<slug> 匹配 editions.json 的作品/得主
- 合并既有报告中的有效记录（保留其许可/作者元数据），补齐缺失的肖像与作品
- 额外真实作品（利华大厦/巴西利亚国会/维特拉消防站/象山校区）先写入 editions，再注入
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
REPORT = ASSETS / "_fetch_report.json"
OK_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower() or "item"


# 磁盘文件 stem -> editions 中已有的作品 slug（处理命名差异的额外好图）
ALIAS = {
    "beinecke": "beinecke-rare-book-manuscript-library",
    "brasilia-cathedral": "cathedral-of-bras-lia",
    "zaragoza-bridge": "bridge-pavilion",
    "brasilia-congress": "national-congress-of-brazil",
    "xiangshan": "xiangshan-campus-china-academy-of-art",
}

# 需增补进 editions 的真实作品（磁盘已有图，但 editions 未列）
NEW_WORKS = {
    1988: [
        {"title_cn": "利华大厦", "title_en": "Lever House", "city": "纽约", "country": "美国",
         "lat": 40.7527, "lng": -73.9737, "completed": "1952", "slug": "lever-house"},
    ],
    2004: [
        {"title_cn": "维特拉消防站", "title_en": "Vitra Fire Station", "city": "魏尔 am 莱茵", "country": "德国",
         "lat": 47.6095, "lng": 7.6223, "completed": "1993", "slug": "vitra-fire-station"},
    ],
    2012: [
        {"title_cn": "中国美术学院象山校区", "title_en": "Xiangshan Campus, China Academy of Art",
         "city": "杭州", "country": "中国", "lat": 30.2300, "lng": 120.1400, "completed": "2007",
         "slug": "xiangshan-campus-china-academy-of-art"},
    ],
}
# 巴西利亚国会大厦单独挂到 1988（尼迈耶），slug 与磁盘文件名不同，用别名映射
NEW_WORKS_ALIAS = {"brasilia-congress": "national-congress-of-brazil"}
NEW_WORKS[1988].append(
    {"title_cn": "巴西利亚国会大厦", "title_en": "National Congress of Brazil",
     "city": "巴西利亚", "country": "巴西", "lat": -15.7939, "lng": -47.8828,
     "completed": "1960", "slug": "national-congress-of-brazil"}
)


def main() -> None:
    doc = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))

    # 1) 增补新作品到 editions
    for ed in doc["editions"]:
        adds = NEW_WORKS.get(ed["year"])
        if not adds:
            continue
        existing = {slugify(w.get("title_en") or w["title_cn"]) for w in ed.get("works", [])}
        for nw in adds:
            if nw["slug"] in existing:
                continue
            w = {k: nw[k] for k in ("title_cn", "title_en", "city", "country", "lat", "lng", "completed")}
            w["photo"] = ""; w["credit"] = ""
            ed.setdefault("works", []).append(w)
            existing.add(nw["slug"])
            print(f"  + 增补作品 {ed['year']} {nw['title_cn']}")

    # 2) 建立匹配索引
    wmap: dict[tuple, str] = {}
    lmap: dict[tuple, str] = {}
    for ed in doc["editions"]:
        y = ed["year"]
        for w in ed.get("works", []):
            wmap[(y, slugify(w.get("title_en") or w["title_cn"]))] = w
        for l in ed["laureates"]:
            lmap[(y, slugify(l.get("name_en") or l["name_cn"]))] = l

    # 3) 合并既有报告
    existing: list = []
    if REPORT.exists():
        try:
            existing = json.loads(REPORT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    covered = {(r.get("kind"), r.get("year"), r.get("slug"))
               for r in existing if r.get("status") in ("ok", "cached")}

    records = list(existing)
    added = 0

    def add(kind, year, slug, fpath):
        nonlocal added
        if (kind, year, slug) in covered:
            return
        records.append({
            "kind": kind, "year": year, "slug": slug,
            "title": slug, "lang": "en",
            "file": fpath, "imageUrl": "",
            "license": "Wikimedia Commons", "artist": "", "status": "ok",
        })
        covered.add((kind, year, slug))
        added += 1

    # 4) 扫描磁盘
    for folder, kind in (("portraits", "portrait"), ("works", "work")):
        for p in sorted((ASSETS / folder).glob("*")):
            if p.suffix.lower() not in OK_EXT:
                continue
            m = re.match(r"(\d{4})-(.+)$", p.stem)
            if not m:
                print(f"  ? 跳过无法解析的文件名 {p.name}")
                continue
            year = int(m.group(1))
            stem = m.group(2)
            rel = f"assets/{folder}/{p.name}"
            if kind == "portrait":
                if (year, stem) in lmap:
                    add("portrait", year, stem, rel)
                else:
                    print(f"  ? 肖像未匹配 {p.name}")
            else:
                slug = ALIAS.get(stem, stem)
                if (year, slug) in wmap:
                    add("work", year, slug, rel)
                else:
                    print(f"  ? 作品未匹配 {p.name}")

    REPORT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "editions.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n重建完成：新增 {added} 条记录；报告共 {len(records)} 条 → {REPORT}")


if __name__ == "__main__":
    main()

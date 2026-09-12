#!/usr/bin/env python3
"""A 数据官 · 素材注入：把 tools/fetch_portraits.py 的抓取结果写回 data/editions.json

用法: python3 tools/enrich_assets.py

- 每届：首位有肖像的得主 → edition.portrait / portraitCredit
- 每件代表作：命中素材 → work.photo / work.credit（按 index 对应）
- 幂等：重复执行覆盖同名字段；缺失的素材保留原值
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORT = ROOT / "assets" / "_fetch_report.json"
EDITIONS = DATA / "editions.json"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s or "item"


def credit_of(rec: dict) -> str:
    lic = (rec.get("license") or "").strip()
    artist = (rec.get("artist") or "").strip()
    bits = []
    for b in ("Wikimedia Commons", lic, artist):
        if b and b not in bits:            # 去重，避免 "Wikimedia Commons · Wikimedia Commons"
            bits.append(b)
    return " · ".join(bits)[:120]


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    portraits: dict[tuple[int, str], dict] = {}
    works: dict[tuple[int, str], dict] = {}
    for rec in report:
        if rec.get("status") != "ok":
            continue
        key = (rec["year"], rec["slug"])
        (portraits if rec["kind"] == "portrait" else works)[key] = rec

    # 样板档案（laureates.json）里已有的作品照片，同步到 editions，保证全站一致
    dossiers = {}
    lpath = DATA / "laureates.json"
    if lpath.exists():
        dossiers = json.loads(lpath.read_text(encoding="utf-8")).get("dossiers", {})

    doc = json.loads(EDITIONS.read_text(encoding="utf-8"))
    n_p = n_w = 0
    for ed in doc["editions"]:
        year = ed["year"]
        if "portrait" not in ed:
            for l in ed["laureates"]:
                rec = portraits.get((year, slugify(l.get("name_en") or l["name_cn"])))
                if rec:
                    ed["portrait"] = rec["file"]
                    ed["portraitCredit"] = credit_of(rec)
                    n_p += 1
                    break
        # 清理失效引用（文件被复核删除后，数据里不应再指向它）
        for key in ("portrait",):
            p = ed.get(key)
            if p and not (ROOT / p).exists():
                ed.pop(key, None)
                ed.pop("portraitCredit", None)

        doss = dossiers.get(str(year)) or {}
        for i, w in enumerate(ed.get("works", [])):
            if w.get("photo") and not (ROOT / w["photo"]).exists():
                w.pop("photo", None)
                w.pop("credit", None)
            rec = works.get((year, slugify(w.get("title_en") or w["title_cn"])))
            if rec:
                w["photo"] = rec["file"]
                w["credit"] = credit_of(rec)
                n_w += 1
                continue
            dw = (doss.get("works") or [None])[min(i, len(doss.get("works") or [1]) - 1)] if doss.get("works") else None
            if dw and dw.get("photo") and not w.get("photo"):
                w["photo"] = dw["photo"]
                w["credit"] = dw.get("credit") or "Wikimedia Commons"
                n_w += 1

    EDITIONS.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"注入完成：肖像 {n_p} 届 · 作品照片 {n_w} 张 → {EDITIONS}")


if __name__ == "__main__":
    main()

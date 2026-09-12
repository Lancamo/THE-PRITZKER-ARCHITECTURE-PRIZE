#!/usr/bin/env python3
"""A 数据官 · 官方肖像抓取：The Pritzker Architecture Prize 官网获奖者名单

用法: python3 tools/fetch_pritzker.py

- 来源：https://www.pritzkerprize.com/laureates（官网统一提供的黑白方图肖像）
- 按「年份 + 姓名」匹配到 data/editions.json 的得主，落盘为 assets/portraits/<year>-<slug>.jpg
- 多人共享一届时（如 2020 Farrell & McNamara），同一张合影分派给该届各位得主
- 结果写入 assets/_pritzker_report.json（含来源页，供页面署名与追溯）
- 版权提示：肖像 © The Pritzker Architecture Prize / 各摄影师，本项目非商业展示用途
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # noqa: BLE001
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
PORTRAITS = ASSETS / "portraits"
REPORT = ASSETS / "_pritzker_report.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PritzkerViz/2.0 (non-commercial archive)"
LIST_URL = "https://www.pritzkerprize.com/laureates"
ROW_RE = re.compile(r'<article class="views-row">(.*?)</article>', re.S)
NAME_RE = re.compile(r'<h2><a href="[^"]*">(.*?)\s*<span>(\d{4})\s', re.S)
IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.I)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s or "item"


def norm_tokens(text: str) -> set[str]:
    text = urllib.parse.unquote(text or "")
    text = text.replace("&amp;", "&").replace("’", "'")
    return {t for t in re.split(r"[^A-Za-z]+", text.lower()) if len(t) > 1}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
        return resp.read()


def parse_list(html: str) -> list[dict]:
    rows = []
    for block in ROW_RE.findall(html):
        name_m = NAME_RE.search(block)
        img_m = IMG_RE.search(block)
        if not name_m or not img_m:
            continue
        name = re.sub(r"<[^>]+>", "", name_m.group(1)).strip()
        rows.append({
            "name": name,
            "year": int(name_m.group(2)),
            "image": urllib.parse.urljoin(LIST_URL, img_m.group(1)),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="重新下载已存在的肖像（保持官网原始分辨率）")
    args = ap.parse_args()

    html = get(LIST_URL).decode("utf-8", "ignore")
    rows = parse_list(html)
    print(f"官网名单：{len(rows)} 条")

    doc = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    by_year = {ed["year"]: ed for ed in doc["editions"]}
    assigned: dict[int, set[str]] = {}
    report = []

    for row in rows:
        ed = by_year.get(row["year"])
        if not ed:
            print(f"  ! {row['year']} 不在数据中：{row['name']}")
            continue
        row_tokens = norm_tokens(row["name"])
        done = assigned.setdefault(row["year"], set())

        def free(l):
            return slugify(l.get("name_en") or l["name_cn"]) not in done

        picked = [l for l in ed["laureates"] if free(l) and (norm_tokens(l.get("name_en") or "") & row_tokens)]
        if not picked:
            picked = [l for l in ed["laureates"] if free(l)][:1]
        if not picked:
            continue

        for l in picked:
            slug = slugify(l.get("name_en") or l["name_cn"])
            out = PORTRAITS / f"{row['year']}-{slug}.jpg"
            if out.exists() and not args.force:
                print(f"  · 已存在 {out.name}")
                done.add(slug)
                continue
            try:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(get(row["image"]))
                done.add(slug)
                print(f"  ✓ {out.name}  ←  {row['name']}（{row['year']}）")
            except Exception as exc:  # noqa: BLE001
                print(f"  × {out.name} 失败：{exc}")
                continue
            report.append({
                "kind": "portrait", "year": row["year"], "slug": slug, "person": l["name_cn"],
                "officialName": row["name"], "file": f"assets/portraits/{out.name}",
                "sourcePage": LIST_URL, "imageUrl": row["image"],
                "credit": "The Pritzker Architecture Prize（官网肖像，非商业展示）",
                "status": "ok",
            })
            time.sleep(0.5)

    # 回写 editions.json：肖像路径与署名（官网肖像统一来源，便于全站一致）
    for item in report:
        ed = by_year.get(item["year"])
        if not ed:
            continue
        for l in ed["laureates"]:
            if slugify(l.get("name_en") or l["name_cn"]) == item["slug"]:
                ed["portrait"] = item["file"]
                ed["portraitCredit"] = item["credit"]
    (DATA / "editions.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成：{len(report)} 张官方肖像 → {REPORT}（并回写 editions.json）")


if __name__ == "__main__":
    main()

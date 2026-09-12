#!/usr/bin/env python3
"""A 数据官 · 定向补齐：对 5 届真实作品（维基自动搜索失败的）用手工候选标题抓取。

用法: python3 tools/fetch_extra.py
输出: assets/works/<year>-<slug>.<ext>，并追加记录到 assets/_fetch_report.json
（slug 与 editions.json 中 title_en 的 slugify 一致，供 enrich_assets.py 注入）
"""
from __future__ import annotations

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
ASSETS = ROOT / "assets"
REPORT = ASSETS / "_fetch_report.json"
UA = "PritzkerViz/2.0 (local non-commercial archive)"
OK_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower() or "item"


def api_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def summary(lang: str, title: str) -> dict | None:
    url = (f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
           + urllib.parse.quote(title, safe=""))
    return api_json(url)


def search(lang: str, query: str) -> tuple[str, str] | None:
    url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json"
           "&generator=search&gsrsearch=" + urllib.parse.quote(query, safe="")
           + "&gsrlimit=3&prop=pageimages&piprop=original&redirects=1")
    data = api_json(url)
    if not data:
        return None
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        src = ((page.get("original") or {}).get("source")) or ""
        if src and Path(urllib.parse.urlparse(src).path).suffix.lower() in OK_EXT:
            return src, page.get("title", "")
    return None


def thumb_url(src: str, width: int = 1000) -> str:
    clean = src.split("?")[0]
    try:
        head, tail = clean.rsplit("/", 1)
        if "/wikipedia/commons/" in head or "/wikipedia/en/" in head:
            if "/thumb/" in clean:
                return clean
            prefix, rest = head.split("/wikipedia/", 1)
            return f"{prefix}/wikipedia/{rest.split('/', 1)[0]}/thumb/{rest.split('/', 1)[1]}/{tail}/{width}px-{tail}"
    except ValueError:
        return clean
    return clean


def download(url: str, out: Path) -> bool:
    for attempt in range(3):
        for cand in (thumb_url(url), url):
            try:
                req = urllib.request.Request(cand, headers={"User-Agent": UA, "Referer": "https://commons.wikimedia.org/"})
                with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
                    data = resp.read()
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                return True
            except Exception:  # noqa: BLE001
                continue
        time.sleep(2)
    return False


# (year, slug, [候选维基标题], [候选搜索词])
TARGETS = [
    (1986, "bensberg-civic-centre",
     ["Bensberg_Town_Hall", "Bensberg_Civic_Centre", "Rathaus_Bensberg"],
     ["Bensberg Town Hall Böhm", "Bergisch Gladbach Rathaus"]),
    (1992, "portugal-pavilion-expo-98",
     ["Pavilhão_de_Portugal", "Portugal_Pavilion", "Portugal_Pavilion_Expo_98"],
     ["Portugal Pavilion Expo 98 Siza", "Pavilhão de Portugal"]),
    (2016, "uc-innovation-center",
     ["Innovation_Center_UC", "UC_Innovation_Center", "Centro_de_Innovación_UC"],
     ["Innovation Center UC Aravena", "UC Centro de Innovacion"]),
    (2017, "sant-antoni-library",
     ["Sant_Antoni_-_Joan_Oliver_Library", "Biblioteca_Sant_Antoni_-_Joan_Oliver", "Sant_Antoni_Joan_Oliver_Library"],
     ["Sant Antoni Joan Oliver Library RCR", "Biblioteca Sant Antoni Barcelona"]),
    (2020, "bocconi-university",
     ["Bocconi_University", "Campus_Bocconi", "Università_Bocconi"],
     ["Bocconi University Grafton", "Campus Bocconi Milano"]),
]


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else []
    covered = {(r.get("kind"), r.get("year"), r.get("slug"))
               for r in report if r.get("status") in ("ok", "cached")}
    for year, slug, titles, queries in TARGETS:
        if ("work", year, slug) in covered:
            print(f"  · 已有 {year} {slug}")
            continue
        src = page_title = None
        for t in titles:
            d = summary("en", t)
            if d and d.get("originalimage", {}).get("source"):
                src = d["originalimage"]["source"]; page_title = d.get("title"); break
            time.sleep(0.3)
        if not src:
            for q in queries:
                hit = search("en", q) or search("zh", q)
                if hit:
                    src, page_title = hit; break
                time.sleep(0.3)
        if not src:
            print(f"  × {year} {slug} — 仍未找到")
            continue
        ext = Path(urllib.parse.urlparse(src).path).suffix.lower() or ".jpg"
        out = ASSETS / "works" / f"{year}-{slug}{ext}"
        if out.exists() or download(src, out):
            print(f"  ✓ {year} {slug} ← {page_title}")
            report.append({
                "kind": "work", "year": year, "slug": slug,
                "title": page_title, "lang": "en",
                "file": f"assets/works/{out.name}", "imageUrl": src,
                "license": "Wikimedia Commons", "artist": "", "status": "ok",
            })
        else:
            print(f"  × {year} {slug} — 下载失败")
        time.sleep(0.8)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成 →", REPORT)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""A 数据官 · 照片抓取：经 Wikipedia REST API 获取肖像与代表作缩略图。

用法: python3 tools/fetch_assets.py

- 只抓取清单内条目（样板 3 届：2012 王澍 / 2004 扎哈 / 1988 邦沙夫特+尼迈耶）
- 输出到 assets/portraits、assets/works，并写 assets/manifest.json 记录来源页
- 失败条目跳过并打印警告，不阻断其余下载（详情页有占位兜底）
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:  # python.org 版 Python 自带根证书缺失时用 certifi 补齐
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # noqa: BLE001
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
UA = "PritzkerViz/2.0 (local archive build; contact: none)"

# (语言, 页面标题, 输出相对路径)
PORTRAITS = [
    ("zh", "王澍", "portraits/2012-wangshu.jpg"),
    ("en", "Zaha_Hadid", "portraits/2004-hadid.jpg"),
    ("en", "Gordon_Bunshaft", "portraits/1988-bunshaft.jpg"),
    ("en", "Oscar_Niemeyer", "portraits/1988-niemeyer.jpg"),
]

WORKS = [
    ("zh", "宁波博物馆", "works/2012-ningbo-museum.jpg"),
    ("zh", "中国美术学院", "works/2012-xiangshan.jpg"),
    ("en", "Bridge_Pavilion", "works/2004-zaragoza-bridge.jpg"),
    ("en", "Vitra_Fire_Station", "works/2004-vitra-fire-station.jpg"),
    ("en", "Beinecke_Rare_Book_and_Manuscript_Library", "works/1988-beinecke.jpg"),
    ("en", "Lever_House", "works/1988-lever-house.jpg"),
    ("zh", "巴西利亚大教堂", "works/1988-brasilia-cathedral.jpg"),
    ("en", "National_Congress_of_Brazil", "works/1988-brasilia-congress.jpg"),
]


def summary(lang: str, title: str) -> dict | None:
    url = (
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(title, safe="")
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! 取摘要失败 {lang}:{title} — {exc}")
        return None


def download(url: str, out: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            data = resp.read()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! 下载失败 {url} — {exc}")
        return False


def collect(items: list[tuple[str, str, str]], manifest: list) -> None:
    for lang, title, rel in items:
        out = ASSETS / rel
        if out.exists():
            print(f"  · 已存在 {rel}")
            manifest.append({"file": rel, "lang": lang, "title": title, "status": "cached"})
            continue
        data = summary(lang, title)
        if not data:
            manifest.append({"file": rel, "lang": lang, "title": title, "status": "failed"})
            continue
        image = data.get("originalimage") or data.get("thumbnail") or {}
        src = image.get("source")
        if not src:
            print(f"  ! 无图 {lang}:{title}")
            manifest.append({"file": rel, "lang": lang, "title": title, "status": "no-image"})
            continue
        ok = download(src, out)
        print(f"  {'✓' if ok else '×'} {rel}  ←  {src[:90]}")
        manifest.append(
            {
                "file": rel,
                "lang": lang,
                "title": title,
                "sourcePage": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                "imageUrl": src,
                "status": "ok" if ok else "failed",
            }
        )
        time.sleep(0.4)


def main() -> None:
    manifest: list = []
    print("肖像：")
    collect(PORTRAITS, manifest)
    print("代表作：")
    collect(WORKS, manifest)
    out = ASSETS / "manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for m in manifest if m["status"] in ("ok", "cached"))
    print(f"完成：{ok}/{len(manifest)} 张 → {out}")


if __name__ == "__main__":
    main()

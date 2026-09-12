#!/usr/bin/env python3
"""A 数据官 · 照片修正：对 summary 无图/抓到 logo 的条目，改用文章图片列表挑选真实照片。

用法: python3 tools/refetch_assets.py
"""
from __future__ import annotations

import json
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
UA = "PritzkerViz/2.0 (local archive build)"

BAD_WORDS = (
    "logo", "icon", "map", "flag", "coat", "seal", "symbol", "diagram",
    "plan", "commons", "wiki", "edit", "padlock", "question", "ambox",
    "portal", "disambig", "star", "barnstar", "scale", "chart",
)

# (语言, 文章, 输出, 优先关键词)
TASKS = [
    ("zh", "王澍", "portraits/2012-wangshu.jpg", ("王澍", "wang")),
    ("en", "Gordon_Bunshaft", "portraits/1988-bunshaft.jpg", ("bunshaft", "gordon")),
    ("zh", "宁波博物馆", "works/2012-ningbo-museum.jpg", ("museum", "博物馆", "ningbo")),
    ("en", "National_Congress_of_Brazil", "works/1988-brasilia-congress.jpg", ("congress", "brasil", "national")),
]

RETRY = [
    ("en", "Bridge_Pavilion", "works/2004-zaragoza-bridge.jpg"),
]


def api(lang: str, params: dict) -> dict:
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_images(lang: str, title: str) -> list[str]:
    data = api(lang, {
        "action": "query", "titles": title, "prop": "images",
        "imlimit": "60", "format": "json",
    })
    pages = data.get("query", {}).get("pages", {})
    out: list[str] = []
    for page in pages.values():
        for img in page.get("images", []):
            name = img.get("title", "")
            if name.lower().endswith((".jpg", ".jpeg", ".png")):
                out.append(name)
    return out


def image_url(lang: str, file_title: str, width: int = 1600) -> str | None:
    data = api(lang, {
        "action": "query", "titles": file_title, "prop": "imageinfo",
        "iiprop": "url", "iiurlwidth": str(width), "format": "json",
    })
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo") or []
        if info:
            return info[0].get("thumburl") or info[0].get("url")
    return None


def pick(files: list[str], prefer: tuple[str, ...]) -> str | None:
    photos = [f for f in files if not any(b in f.lower() for b in BAD_WORDS)]
    for f in photos:
        if any(p in f.lower() for p in prefer):
            return f
    return photos[0] if photos else None


def download(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
        data = resp.read()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


def main() -> None:
    for lang, title, rel, prefer in TASKS:
        files = list_images(lang, title)
        chosen = pick(files, prefer)
        if not chosen:
            print(f"  ! {title}: 未找到合适照片（候选 {len(files)} 个文件）")
            continue
        url = image_url(lang, chosen)
        if not url:
            print(f"  ! {title}: 取不到 {chosen} 的 URL")
            continue
        try:
            download(url, ASSETS / rel)
            print(f"  ✓ {rel}  ←  {chosen}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {title}: 下载失败 {exc}")
        time.sleep(1.2)

    for lang, title, rel in RETRY:
        url_data = None
        try:
            s = api(lang, {"action": "query", "titles": title, "prop": "pageimages",
                           "piprop": "original|thumbnail", "pithumbsize": "1600", "format": "json"})
            for page in s.get("query", {}).get("pages", {}).values():
                thumb = page.get("thumbnail") or page.get("original") or {}
                url_data = thumb.get("source")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {title}: 重试取图失败 {exc}")
        if not url_data:
            print(f"  ! {title}: 重试仍无图")
            continue
        try:
            download(url_data, ASSETS / rel)
            print(f"  ✓ {rel}（重试成功）")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {title}: 重试下载失败 {exc}")
        time.sleep(1.5)


if __name__ == "__main__":
    main()

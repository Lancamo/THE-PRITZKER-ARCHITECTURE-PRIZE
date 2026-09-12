#!/usr/bin/env python3
"""A 数据官 · 素材批量补齐：历届得主肖像 + 代表作照片

用法: python3 tools/fetch_portraits.py [--limit N]

- 数据源：Wikipedia REST API（页面主图）+ Wikimedia Commons（许可与作者元数据）
  仅采用自由许可素材（CC BY-SA / CC0 / 公有领域），逐张记录许可、作者与来源页
- 肖像：优先 en 维基（英文名），回退 zh 维基（中文名）
- 代表作：每届最多 2 件，en 标题优先、zh 标题回退
- 已存在的文件跳过；失败条目记录在报告中，不阻断其余下载
- 输出：assets/portraits/<year>-<slug>.<ext>、assets/works/<year>-<slug>.<ext>
        报告 assets/_fetch_report.json
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
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
REPORT = ASSETS / "_fetch_report.json"
UA = "PritzkerViz/2.0 (local non-commercial archive; contact: none)"
OK_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s or "item"


def api_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def page_summary(lang: str, title: str) -> dict | None:
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title, safe="")
    return api_json(url)


def commons_meta(image_url: str) -> dict:
    """取图片的许可与作者（Commons 或 en 维基本地文件页）"""
    name = urllib.parse.unquote(image_url.rsplit("/", 1)[-1])
    host = "en.wikipedia.org" if "/wikipedia/en/" in image_url else "commons.wikimedia.org"
    url = (
        f"https://{host}/w/api.php?action=query&format=json&prop=imageinfo"
        "&iiprop=extmetadata&titles=" + urllib.parse.quote("File:" + name, safe="")
    )
    data = api_json(url)
    if not data:
        return {}
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "") or "").strip()
        license_name = (meta.get("LicenseShortName") or {}).get("value", "") or ""
        return {"license": license_name, "artist": artist[:80]}
    return {}


def thumb_url(src: str, width: int = 900) -> str:
    """把原图 URL 转为标准缩略图 URL（Wikimedia 限流策略推荐，且体积更小）"""
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


def download(url: str, out: Path, retries: int = 4) -> bool:
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://commons.wikimedia.org/"})
        try:
            with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
                data = resp.read()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            return True
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            if code == 429 and attempt < retries - 1:
                wait = 4 * (attempt + 1)
                print(f"    · 限流，等待 {wait}s 后重试（{attempt + 1}/{retries}）")
                time.sleep(wait)
                continue
            print(f"    ! 下载失败 {exc}")
            return False
    return False


def search_image(lang: str, query: str) -> tuple[dict, str, str] | None:
    """维基搜索兜底：取首条命中页面的主图（解决同名/加后缀/消歧义页问题）"""
    url = (
        f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&generator=search"
        "&gsrsearch=" + urllib.parse.quote(query, safe="") +
        "&gsrlimit=1&prop=pageimages&piprop=original&redirects=1"
    )
    data = api_json(url)
    if not data:
        return None
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        src = ((page.get("original") or {}).get("source")) or ""
        if not src:
            continue
        ext = Path(urllib.parse.urlparse(src).path).suffix.lower()
        if ext not in OK_EXT:
            continue
        title = page.get("title", "")
        return (
            {
                "title": title,
                "content_urls": {"desktop": {"page": f"https://{lang}.wikipedia.org/wiki/"
                                             + urllib.parse.quote(title.replace(" ", "_"))}},
            },
            src,
            lang,
        )
    return None


def try_titles(pairs: list[tuple[str, str]], query: str = "") -> tuple[dict, str, str] | None:
    """按顺序尝试若干 (lang, title)；失败后用搜索兜底"""
    for lang, title in pairs:
        if not title:
            continue
        data = page_summary(lang, title)
        if not data or data.get("type") == "disambiguation":
            continue
        img = data.get("originalimage") or data.get("thumbnail") or {}
        src = img.get("source")
        if not src:
            continue
        ext = Path(urllib.parse.urlparse(src).path).suffix.lower()
        if ext not in OK_EXT:
            continue
        return data, src, lang
    if query:
        for lang in ("en", "zh"):
            hit = search_image(lang, query)
            if hit:
                return hit
    return None


def fetch_one(kind: str, year: int, slug: str, pairs: list[tuple[str, str]], report: list,
              known: dict | None = None) -> str | None:
    folder = ASSETS / ("portraits" if kind == "portrait" else "works")
    for p in folder.glob(f"{year}-{slug}.*"):
        if p.suffix.lower() in OK_EXT:
            print(f"    · 已存在 {p.name}")
            rec = (known or {}).get((kind, year, slug))
            report.append(rec or {
                "kind": kind, "year": year, "slug": slug,
                "file": str(p.relative_to(ROOT.parent)).replace("\\", "/"),
                "license": "Wikimedia Commons", "artist": "", "status": "cached",
            })
            return str(p.relative_to(ROOT.parent)).replace("\\", "/")
    hit = try_titles(pairs, query=pairs[0][1].replace("_", " ") if pairs else "")
    if not hit:
        print(f"    × 无可用图片：{[t for _, t in pairs]}")
        report.append({"kind": kind, "year": year, "slug": slug, "status": "no-image",
                       "tried": [f"{l}:{t}" for l, t in pairs]})
        return None
    data, src, lang = hit
    ext = Path(urllib.parse.urlparse(src).path).suffix.lower()
    out = folder / f"{year}-{slug}{ext}"
    meta = commons_meta(src)          # 用原图 URL 查许可（缩略图 URL 的文件名带前缀）
    ok = False
    for width in (900, 640, 0):       # 部分图片不支持任意缩略尺寸，逐级回退
        ok = download(thumb_url(src, width) if width else src, out)
        if ok:
            break
    print(f"    {'✓' if ok else '×'} {out.name}  ←  {src[:80]}")
    report.append({
        "kind": kind, "year": year, "slug": slug,
        "title": data.get("title"), "lang": lang,
        "file": str(out.relative_to(ROOT.parent)).replace("\\", "/"),
        "sourcePage": (data.get("content_urls") or {}).get("desktop", {}).get("page"),
        "imageUrl": src,
        "license": meta.get("license", ""),
        "artist": meta.get("artist", ""),
        "status": "ok" if ok else "failed",
    })
    time.sleep(1.1)                   # 对 Wikimedia 保持克制，避免 429
    return str(out.relative_to(ROOT.parent)).replace("\\", "/") if ok else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="仅处理前 N 届（调试用）")
    ap.add_argument("--kind", choices=["all", "portrait", "work"], default="all",
                    help="只抓肖像或只抓代表作照片（肖像以官网为准时用 work）")
    args = ap.parse_args()

    editions = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))["editions"]
    if args.limit:
        editions = editions[: args.limit]

    # 合并历史报告，避免重复运行时丢失已下载素材的来源记录
    report: list = []
    known: dict = {}
    if REPORT.exists():
        try:
            for rec in json.loads(REPORT.read_text(encoding="utf-8")):
                if rec.get("status") in ("ok", "cached"):
                    known[(rec["kind"], rec["year"], rec["slug"])] = rec
        except (json.JSONDecodeError, KeyError):
            known = {}

    for ed in editions:
        year = ed["year"]
        if args.kind in ("all", "portrait"):
            for l in ed["laureates"]:
                en = l.get("name_en") or ""
                print(f"  [{year}] 肖像 {l['name_cn']}")
                fetch_one("portrait", year, slugify(en or l["name_cn"]),
                          [("en", en.replace(" ", "_")),
                           ("en", (en + " (architect)").replace(" ", "_")),
                           ("zh", l["name_cn"])], report, known)
        if args.kind == "portrait":
            continue
        for w in ed.get("works", [])[:2]:
            wen = w.get("title_en") or ""
            print(f"  [{year}] 作品 {w['title_cn']}")
            fetch_one("work", year, slugify(wen or w["title_cn"]),
                      [("en", wen.replace(" ", "_")), ("zh", w["title_cn"])], report, known)

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in report if r["status"] == "ok")
    print(f"\n完成：{ok}/{len(report)} 张 → {REPORT}")


if __name__ == "__main__":
    sys.exit(main())

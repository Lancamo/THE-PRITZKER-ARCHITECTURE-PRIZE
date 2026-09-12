#!/usr/bin/env python3
"""A 数据官 · 缺失作品照片补齐（搜索式抓取）

用法: python3 tools/fetch_missing_works.py [--per-edition 3]

- 遍历 editions.json，找出「整届没有任何作品照片」的届次
- 对每届前 N 件代表作，用多种查询组合在维基百科检索主图：
    1) 英文作品名 + 建筑师英文名（最准）
    2) 英文作品名
    3) 中文作品名 + 中文建筑师名
    4) 中文作品名
- 命中即下载（900px 缩略图，失败回退原图），记录许可与来源
- 结果合并写入 assets/_fetch_report.json，随后运行 tools/enrich_assets.py 注入数据
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
WORKS = ASSETS / "works"
REPORT = ASSETS / "_fetch_report.json"
UA = "PritzkerViz/2.0 (local non-commercial archive)"
OK_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s or "item"


def api(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def thumb(src: str, width: int = 900) -> str:
    clean = src.split("?")[0]
    try:
        head, tail = clean.rsplit("/", 1)
        if ("/wikipedia/commons/" in head or "/wikipedia/en/" in head) and "/thumb/" not in clean:
            prefix, rest = head.split("/wikipedia/", 1)
            project, sub = rest.split("/", 1)
            return f"{prefix}/wikipedia/{project}/thumb/{sub}/{tail}/{width}px-{tail}"
    except ValueError:
        return clean
    return clean


STOP = {"the", "of", "and", "de", "la", "el", "los", "las", "for", "在", "与", "及", "年"}
# 通用建筑词：命中不足以证明是同一栋建筑
GENERIC = {
    "center", "centre", "library", "museum", "house", "building", "tower", "park", "bridge",
    "hall", "church", "school", "pavilion", "gallery", "institute", "university", "college",
    "theatre", "theater", "station", "plaza", "complex", "memorial", "residence", "villa",
    "studio", "office", "hotel", "airport", "stadium", "hospital", "center,",
    "中心", "图书馆", "博物馆", "美术馆", "大厦", "大楼", "住宅", "公园", "广场", "车站", "学院", "大学",
}


def tokens(text: str, distinctive: bool = False) -> set[str]:
    out = set()
    for t in re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", (text or "").lower()):
        if len(t) < 3 or t in STOP:
            continue
        if distinctive and (t in GENERIC or len(t) < 5):
            continue
        out.add(t)
    return out


BAD_FILE_RE = re.compile(r"(logo|icon|plan|diagram|map|flag|coat|seal|wappen|sign|chart|sketch|drawing)", re.I)


def matches(page_title: str, work_titles: list[str]) -> bool:
    if BAD_FILE_RE.search(page_title):
        return False
    """严格校验：页面标题整体包含作品名，或与作品名共享 ≥2 个区分性词元
    （单靠 1 个词元容易匹配到人名页/城市页，故不接受）"""
    norm_page = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", page_title.lower())
    for wt in work_titles:
        wn = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", (wt or "").lower())
        if len(wn) >= 6 and wn in norm_page:
            return True
    pt = tokens(page_title, distinctive=True)
    wt_set = tokens(" ".join(work_titles), distinctive=True)
    return len(pt & wt_set) >= 2


def search_image(lang: str, query: str, work_titles: list[str]) -> tuple[str, str] | None:
    """检索主图；页面标题必须与作品名有区分性词元交集，避免错配"""
    url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&generator=search"
           "&gsrsearch=" + urllib.parse.quote(query, safe="") +
           "&gsrlimit=3&prop=pageimages&piprop=original&redirects=1")
    data = api(url)
    if not data:
        return None
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        src = ((page.get("original") or {}).get("source")) or ""
        title = page.get("title", "")
        if not src or Path(urllib.parse.urlparse(src).path).suffix.lower() not in OK_EXT:
            continue
        if not matches(title, work_titles):
            continue
        return src, title
    return None


def commons_image(query: str, work_titles: list[str]) -> tuple[str, str] | None:
    """Commons 图库检索兜底：按文件名校验，避免图文不符"""
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
           "&gsrnamespace=6&gsrlimit=6&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=900"
           "&gsrsearch=" + urllib.parse.quote(query, safe=""))
    data = api(url)
    if not data:
        return None
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        title = (page.get("title") or "").replace("File:", "")
        if not matches(title, work_titles):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        src = info.get("thumburl") or info.get("url")
        if src and Path(urllib.parse.urlparse(src).path).suffix.lower() in OK_EXT:
            return src, title
    return None


def download(url: str, out: Path) -> bool:
    for attempt in range(3):
        for candidate in (thumb(url), url):
            try:
                req = urllib.request.Request(candidate, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
                    data = resp.read()
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                return True
            except Exception:  # noqa: BLE001
                continue
        time.sleep(2 * (attempt + 1))
    return False


def verify_existing(doc: dict, report: list) -> list:
    """复核本工具已抓取的作品图：页面标题与作品/建筑师无词元交集者视为错配，删除并移除记录"""
    works_by_key = {}
    for ed in doc["editions"]:
        for w in ed.get("works", []):
            key = (ed["year"], slugify(w.get("title_en") or w["title_cn"]))
            works_by_key[key] = [w.get("title_en") or "", w["title_cn"]]

    kept, dropped = [], 0
    for rec in report:
        if rec.get("kind") != "work" or not rec.get("file"):
            kept.append(rec)
            continue
        titles = works_by_key.get((rec.get("year"), rec.get("slug")))
        # 只对带页面标题的记录做词元复核（旧记录若连标题都没有，无从校验，保留、由人工抽检兜底）
        if titles and rec.get("title") and not matches(rec.get("title"), titles):
            path = ROOT / rec["file"]
            try:
                if path and path.exists():
                    path.unlink()
            except OSError:
                pass
            print(f"  × 错配移除 {rec.get('year')} {rec.get('slug')}（页面：{rec.get('title')}）")
            dropped += 1
            continue
        kept.append(rec)
    print(f"复核完成：移除 {dropped} 条错配")
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-edition", type=int, default=3, help="每届最多尝试的作品数")
    args = ap.parse_args()

    doc = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    report: list = []
    if REPORT.exists():
        try:
            report = json.loads(REPORT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = []
    report = verify_existing(doc, report)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    known = {(r.get("kind"), r.get("year"), r.get("slug")) for r in report if r.get("status") in ("ok", "cached")}

    filled = 0
    for ed in doc["editions"]:
        if any(w.get("photo") for w in ed.get("works", [])):
            continue
        architects_en = " ".join(l.get("name_en") or "" for l in ed["laureates"]).strip()
        architects_cn = " ".join(l["name_cn"] for l in ed["laureates"])
        for w in ed.get("works", [])[: args.per_edition]:
            title_en = w.get("title_en") or ""
            title_cn = w.get("title_cn") or ""
            slug = slugify(title_en or title_cn)
            if ("work", ed["year"], slug) in known:
                continue
            queries = [
                ("en", f"{title_en} {architects_en}".strip()),
                ("en", title_en),
                ("zh", f"{title_cn} {architects_cn}".strip()),
                ("zh", title_cn),
            ]
            work_titles = [title_en, title_cn]
            hit = None
            for lang, q in queries:
                if not q:
                    continue
                hit = search_image(lang, q, work_titles)
                if hit:
                    break
                time.sleep(0.25)
            if not hit:                       # 维基无条目时，退回 Commons 图库
                for q in (title_en, title_cn):
                    if not q:
                        continue
                    hit = commons_image(q, work_titles)
                    if hit:
                        break
                    time.sleep(0.25)
            if not hit:
                print(f"  × {ed['year']} {title_cn} — 未找到可用图片")
                continue
            src, page_title = hit
            ext = Path(urllib.parse.urlparse(src).path).suffix.lower()
            out = WORKS / f"{ed['year']}-{slug}{ext}"
            ok = out.exists() or download(src, out)
            print(f"  {'✓' if ok else '×'} {ed['year']} {title_cn} ← {page_title[:48]}")
            if ok:
                filled += 1
                report.append({
                    "kind": "work", "year": ed["year"], "slug": slug,
                    "title": page_title, "lang": hit and "en",
                    "file": f"assets/works/{out.name}", "imageUrl": src,
                    "license": "Wikimedia Commons", "artist": "",
                    "status": "ok",
                })
            time.sleep(0.5)

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n补齐 {filled} 张作品照片 → 请运行 tools/enrich_assets.py 注入数据")


if __name__ == "__main__":
    main()

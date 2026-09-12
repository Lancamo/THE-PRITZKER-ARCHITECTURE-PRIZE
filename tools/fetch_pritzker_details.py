#!/usr/bin/env python3
"""A 数据官 · 官网生平与项目抓取（The Pritzker Architecture Prize 得主页）

用法: python3 tools/fetch_pritzker_details.py [--projects 2] [--photos 2] [--limit N]

- 逐位得主抓取 https://www.pritzkerprize.com/laureates/<slug>
- 抽取：生平正文（HTML 段落，去图注）· 项目名与项目照片
  项目名与照片按官网图片文件名分组（形如 `Carbonero House_1_1000px.jpg`）
- 照片下载至 assets/projects/<year>/<slug>-<n>.jpg（默认每人最多 2 项目 × 2 图）
- 输出 data/pritzker_details.json，并回写 data/editions.json（bio / officialProjects）
- 版权：文本与照片 © The Pritzker Architecture Prize，本项目非商业展示
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
PROJECTS = ASSETS / "projects"
DETAILS = DATA / "pritzker_details.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PritzkerViz/2.0 (non-commercial archive)"
BASE = "https://www.pritzkerprize.com"
ROW_RE = re.compile(r'<article class="views-row">(.*?)</article>', re.S)
NAME_RE = re.compile(r'<h2><a href="([^"]+)">(.*?)\s*<span>(\d{4})\s', re.S)
IMG_RE = re.compile(r'src="(/sites/default/files/[^"]+)"', re.I)
PROJ_IMG_RE = re.compile(
    r'src="(/sites/default/files/(?!images/laureate|inline-images)[^"]+\.(?:jpe?g|png))"', re.I)
SKIP_NAME_RE = re.compile(r"(biography|logo|portrait|headshot|signature|hyatt)", re.I)
SIZE_SUFFIX_RE = re.compile(r"([_-]\d{3,4}px|[-_]scaled|_\d+)$", re.I)
BIO_START = re.compile(r'<div class="field field--name-body[^>]*>', re.I)
SIDE_START = re.compile(r'<div class="field field--name-field-sidebar[^>]*>', re.I)
CAPTION_RE = re.compile(r'^\s*(image\s+)?(photos?|courtesy|credit)[^a-z]{0,2}.*$', re.I)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s or "item"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
        return resp.read()


def parse_list(html: str) -> list[dict]:
    rows = []
    for block in ROW_RE.findall(html):
        m = NAME_RE.search(block)
        if not m:
            continue
        rows.append({
            "slug": m.group(1),
            "name": re.sub(r"<[^>]+>", "", m.group(2)).strip(),
            "year": int(m.group(3)),
        })
    return rows


def balanced_div(page: str, start: int) -> str:
    """从 div 开标签之后的 start 处配平取到对应 </div> 的整块内容"""
    depth, i = 1, start
    while i < len(page) and depth > 0:
        nd, nc = page.find("<div", i), page.find("</div>", i)
        if nc == -1:
            break
        if nd != -1 and nd < nc:
            depth += 1
            i = nd + 4
        else:
            depth -= 1
            i = nc + 6
    return page[start: i - 6]


def section_paras(fragment: str) -> list[str]:
    # 先剔插图与图注（正文里挂着官方照片），再取段落
    fragment = re.sub(r"<(script|style|figure|figcaption)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    paras = []
    for raw in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.S):
        text = re.sub(r"<[^>]+>", "", raw)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
        text = text.replace("&#39;", "'").replace("&quot;", '"').replace("&rsquo;", "’")
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 40 or CAPTION_RE.match(text):
            continue
        paras.append(text)
    return paras


def extract_bio(html: str) -> str:
    """生平 = 正文块 + 侧栏续文：官网把长生平的后半段放在 field--name-field-sidebar，
    旧逻辑在正文块结束处截断、会丢掉续文（如 2014 的“1985 年开设事务所”起的内容）。
    两块都按配平 div 取全，剔图注后依序相接。"""
    paras: list[str] = []
    for rx in (BIO_START, SIDE_START):
        m = rx.search(html)
        if not m:
            continue
        for t in section_paras(balanced_div(html, m.end())):
            if t not in paras:
                paras.append(t)
    return "\n\n".join(paras)


def extract_projects(html: str) -> list[dict]:
    """按图片文件名分组项目照片（`项目名_序号.jpg`，去掉尺寸后缀）"""
    groups: dict[str, list[str]] = {}
    order: list[str] = []
    for path in PROJ_IMG_RE.findall(html):
        raw = urllib.parse.unquote(path.rsplit("/", 1)[-1])
        base = SIZE_SUFFIX_RE.sub("", raw.rsplit(".", 1)[0])
        if SKIP_NAME_RE.search(base):
            continue
        while True:
            trimmed = SIZE_SUFFIX_RE.sub("", base)
            if trimmed == base:
                break
            base = trimmed
        title = re.sub(r"[_\s]+", " ", base).strip()
        if not title:
            continue
        if title not in groups:
            groups[title] = []
            order.append(title)
        groups[title].append(BASE + path)
    return [{"title": t, "images": groups[t]} for t in order]


def download(url: str, out: Path, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(get(url))
            return True
        except Exception as exc:  # noqa: BLE001
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"    ! 下载失败 {exc}")
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", type=int, default=2, help="每位得主最多抓取的项目数")
    ap.add_argument("--photos", type=int, default=2, help="每个项目最多抓取的照片数")
    ap.add_argument("--limit", type=int, default=0, help="仅处理前 N 位（调试）")
    ap.add_argument("--refetch", action="store_true", help="已抓取的也重抓（页面结构修复后用）")
    args = ap.parse_args()

    rows = parse_list(get(BASE + "/laureates").decode("utf-8", "ignore"))
    if args.limit:
        rows = rows[: args.limit]
    print(f"得主条目：{len(rows)}")

    details: dict = {}
    if DETAILS.exists():
        try:
            details = json.loads(DETAILS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            details = {}

    for i, row in enumerate(rows, 1):
        key = str(row["year"])
        done = details.get(key, {})
        if not args.refetch and done.get("slug") == row["slug"] and done.get("bio") and done.get("projects"):
            print(f"[{i}/{len(rows)}] · 已抓取 {row['name']}")
            continue
        url = BASE + row["slug"]
        print(f"[{i}/{len(rows)}] {row['name']}（{row['year']}）")
        try:
            html = get(url).decode("utf-8", "ignore")
        except Exception as exc:  # noqa: BLE001
            print(f"    ! 页面抓取失败 {exc}")
            continue

        bio = extract_bio(html)
        projects = extract_projects(html)[: args.projects]
        saved = []
        for pj in projects:
            photos = []
            for n, img in enumerate(pj["images"][: args.photos], 1):
                out = PROJECTS / str(row["year"]) / f"{slugify(pj['title'])}-{n}.jpg"
                if out.exists() or download(img, out):
                    photos.append(f"assets/projects/{row['year']}/{out.name}")
            if photos:
                saved.append({"title": pj["title"], "photos": photos})
        print(f"    生平 {len(bio)} 字 · 项目 {len(saved)} 组 / 照片 {sum(len(p['photos']) for p in saved)} 张")

        details[key] = {
            "year": row["year"],
            "slug": row["slug"],
            "name": row["name"],
            "bio": bio,
            "bioSource": url,
            "projects": saved,
            "credit": "The Pritzker Architecture Prize（官网文本与照片，非商业展示）",
        }
        DETAILS.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.6)

    # 回写 editions.json
    doc = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    n = 0
    for ed in doc["editions"]:
        info = details.get(str(ed["year"]))
        if not info:
            continue
        ed["bio"] = info["bio"]
        ed["bioSource"] = info["bioSource"]
        ed["officialProjects"] = info["projects"]
        n += 1
    (DATA / "editions.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    photos = sum(len(p["photos"]) for v in details.values() for p in v.get("projects", []))
    print(f"\n完成：{len(details)} 位得主 · 项目照片 {photos} 张 · 回写 {n} 届 → {DETAILS}")


if __name__ == "__main__":
    main()

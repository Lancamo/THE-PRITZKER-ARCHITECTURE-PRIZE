#!/usr/bin/env python3
"""A 数据官 · 官网评审词抓取（The Pritzker Architecture Prize）

用法: python3 tools/fetch_citations.py [--limit N] [--refetch]

- 英文评审词：逐届抓 https://www.pritzkerprize.com/laureates/<slug|year>，
  取页面里「Jury Citation」折叠区块的正文（区块内含插图，剔图不截断）
- 中文评审词：从 https://www.pritzkerprize.com/cn/届获奖者 列表逐届抓得主页，
  取「评审辞」折叠区块（官网 2011–2026 届有译文，其余年份留空）
- 短引 quote_en / quote_cn：按 data/quote_spans.json 的句子跨度取开篇（中英同起同止，
  人工核对）；未登记的届回退为「跳过通用前言取开头」。正文保留官网分段（空行分隔）
- 输出 data/citations.json：{ "1979": {"en": "...", "cn": "...", "source": "..."} }
- 版权：评审词 © The Pritzker Architecture Prize，本项目非商业展示

可重复运行：已抓到的年份默认跳过，--refetch 强制重抓。
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # noqa: BLE001
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "citations.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PritzkerViz/2.0 (non-commercial archive)"
BASE = "https://www.pritzkerprize.com"

ROW_RE = re.compile(r'<h2><a href="([^"]+)">(.*?)\s*<span>(\d{4})', re.S)
# 区块正文结束于下一个字段容器或条目结束
BLOCK_END_RE = re.compile(r'<div class="field field--name-field-|</article>', re.I)
EN_LABEL = re.compile(r'jury\s*citation', re.I)
CN_LABEL_RE = re.compile(r'^(评审辞|评审词|评语)')          # 中文站「评审辞」卡片标签
def excerpt(text: str, limit: int) -> str:
    """截取开头一到 limit 字，尽量收在句末（短引位置放不下整段评审词）"""
    if not text:
        return ""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    ends = list(re.finditer(r'[.。！？!?]["”]?\s', cut))
    if ends:
        return cut[: ends[-1].end()].strip()
    return cut.rstrip() + "…"


# 通用前言句：以奖本身为主语的官样句（不含得主），短引需跳过——
# 注意「The Pritzker Prize Jury honors Hans Hollein…」「…践行普利兹克建筑奖的宗旨」这类
# 点了得主的实质句不在此列
PREAMBLE_RE = re.compile(
    r'^(The Pritzker (Architecture )?Prize (is|was)\b'
    r'|Since its establishment'
    r'|普利兹克(建筑)?奖(旨在|是为了)'
    r'|自[^。]{0,30}设立[^。]{0,60}普利兹克[^。]{0,40}宗旨)'
)

# 短引句子跨度（data/quote_spans.json 人工核对）：中英各取开篇前 N 句、同起同止；
# 未登记的届回退为「跳过前言取开头」的摘录
SPANS_PATH = DATA / "quote_spans.json"


def strip_preamble(text: str) -> str:
    while True:
        m = re.match(r'[^。！？.!?]{0,400}?[。！？.!?]', text)
        if not m:
            break
        if PREAMBLE_RE.match(m.group(0)):
            text = text[m.end():].lstrip()
        else:
            break
    return text


def sentence_span(text: str, n: int, lang: str) -> str:
    """取前 n 句；中文按句号切，英文按句末标点+空白切"""
    if lang == "cn":
        parts = re.split(r'(?<=[。！？])', text)
        return "".join(parts[:n]).strip()
    parts = re.split(r'(?<=[.!?”"])\s+', text)
    return " ".join(parts[:n]).strip()


def opening_excerpt(text: str, limit: int) -> str:
    """短引：跳过官网通用前言句，取开篇实质句。
    未登记句子跨度的届用它，中英各取同位置开头。"""
    return excerpt(strip_preamble(text), limit)


def get(url: str, retries: int = 3) -> str:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45, context=SSL_CTX) as resp:
                return resp.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise
            last = exc
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(1.2 * (attempt + 1))
    raise last if last else RuntimeError("fetch failed")


def plain(fragment: str) -> str:
    # 先剔掉配图与图注（评审辞区块尾部常挂着 "…，photo courtesy of …"）
    text = re.sub(r"<(script|style|figure|figcaption)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def html_paras(fragment: str) -> list[str]:
    """按 <p> 取段落（官网评审辞的分段），剔插图与图注后逐段清文本"""
    fragment = re.sub(r"<(script|style|figure|figcaption)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    paras = []
    for raw in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.S):
        t = re.sub(r"<[^>]+>", " ", raw)
        t = html_mod.unescape(t).replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 30:
            paras.append(t)
    return paras


def block_text(page: str, block_id: str) -> str:
    """取折叠区块正文。新版区块是 <article id=…>，取到 </article> 为止，内嵌插图由
    plain() 剔除——旧的「下一个字段容器」边界会在区块内第一张插图处截断，吃掉后半段
    正文（中英文都中招过）；老版页面没有 article 包裹时仍用旧边界兜底。
    正文保留官网分段（段落以空行分隔）；老式页面无 <p> 段落时回退整段平文本。"""
    m = re.search(r'<article[^>]*id="' + re.escape(block_id) + r'"[^>]*>(.*?)(?=</article>)', page, re.S)
    if m:
        paras = html_paras(m.group(1))
        return "\n\n".join(paras) if paras else plain(m.group(1))
    m = re.search(r'id="' + re.escape(block_id) + r'"[^>]*>(.*)', page, re.S)
    if not m:
        return ""
    end = BLOCK_END_RE.search(m.group(1))
    chunk = m.group(1)[: end.start()] if end else m.group(1)
    paras = html_paras(chunk)
    return "\n\n".join(paras) if paras else plain(chunk)


def pick_block(page: str, want: re.Pattern) -> str:
    """找标签文字附近的折叠区块 id，再取该区块正文。

    两种排版混用：老页面是 `<a data-target="#id">Jury Citation</a>`，
    新页面标签落在 `<div>` 里，所以统一「先定位标签、再回溯最近的 data-target」。
    """
    ids: list[str] = []
    for m in want.finditer(page):
        for bid in re.findall(r'data-target="#([\w-]+)"', page[max(0, m.start() - 500): m.start() + 120]):
            if bid not in ids:
                ids.append(bid)
    for bid in ids:
        text = block_text(page, bid)
        if len(text) > 80:
            return text
    return ""


def laureate_index() -> dict[int, str]:
    """届次 → 英文得主页路径（同届多人时保留第一个）"""
    listing = get(BASE + "/laureates")
    out: dict[int, str] = {}
    for href, _name, year in ROW_RE.findall(listing):
        out.setdefault(int(year), href)
    return out


def cn_index() -> dict[int, list[str]]:
    """届次 → 中文得主页路径（同届多人时保留全部）"""
    listing = get(BASE + "/cn/" + urllib.parse.quote("届获奖者"))
    out: dict[int, list[str]] = {}
    for href, _name, year in ROW_RE.findall(listing):
        paths = out.setdefault(int(year), [])
        if href not in paths:
            paths.append(href)
    return out


def cn_citation(page: str) -> str:
    """中文得主页的「评审辞」折叠块正文；卡片标签有 <p> 包裹与裸文本两种写法。
    只在真含中文时返回（早年部分届块内仍是英文原文）。"""
    ids: list[str] = []
    for m in re.finditer(
        r'<a[^>]+class="[^"]*laureate-page-data-toggle[^"]*"[^>]*data-target="#([\w-]+)"[^>]*>(.*?)</a>',
        page, re.S,
    ):
        if CN_LABEL_RE.match(plain(m.group(2))):
            ids.append(m.group(1))
    best = ""
    for bid in ids:
        text = block_text(page, bid)
        if len(re.findall(r"[一-鿿]", text)) > 100 and len(text) > len(best):
            best = text
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只抓前 N 届（调试用）")
    ap.add_argument("--refetch", action="store_true", help="已抓到的也重抓")
    args = ap.parse_args()

    cached: dict[str, dict] = {}
    if OUT.exists():
        cached = json.loads(OUT.read_text(encoding="utf-8")).get("citations", {})
    spans = json.loads(SPANS_PATH.read_text(encoding="utf-8")).get("spans", {}) if SPANS_PATH.exists() else {}

    index = laureate_index()
    cn_idx = cn_index()
    years = sorted(index)
    if args.limit:
        years = years[: args.limit]
    print(f"官网列到 {len(index)} 届，本次处理 {len(years)} 届")

    got_en = got_cn = skipped = 0
    for i, year in enumerate(years, 1):
        key = str(year)
        done = cached.get(key, {})
        need_en = args.refetch or not done.get("en")
        need_cn = args.refetch or not done.get("cn")
        if not need_en and not need_cn:
            skipped += 1
            continue

        rec = dict(done)
        if need_en:
            try:
                page_en = get(BASE + index[year])
                text_en = pick_block(page_en, EN_LABEL)
                if text_en:                       # 抓空时保留旧值，不覆盖
                    rec["en"] = text_en
                    span = spans.get(key)
                    rec["quote_en"] = (sentence_span(strip_preamble(rec["en"]), span["en"], "en")
                                       if span else opening_excerpt(rec["en"], 260))
            except Exception as exc:  # noqa: BLE001
                print(f"  {year} 英文页失败：{exc}")
            time.sleep(0.4)

        if need_cn:
            # 中文译文挂在得主页（/cn/届获奖者/<slug>）的「评审辞」折叠块；
            # 早年未译或块内仍是英文的届，cn_citation 返回空
            cn_text = ""
            for path in sorted(set(cn_idx.get(year, []) + [f"/cn/laureates/{year}"])):
                try:
                    page_cn = get(BASE + path)
                except Exception:  # noqa: BLE001
                    continue
                text_cn = cn_citation(page_cn)
                if len(text_cn) > len(cn_text):
                    cn_text = text_cn
                time.sleep(0.4)
            rec["cn"] = cn_text or rec.get("cn", "")
            if cn_text:
                span = spans.get(key)
                rec["quote_cn"] = (sentence_span(strip_preamble(rec["cn"]), span["cn"], "cn")
                                   if span else opening_excerpt(rec["cn"], 120))

        if rec.get("en"):
            rec["source"] = "Jury Citation, The Pritzker Architecture Prize"
            got_en += 1
        if rec.get("cn"):
            got_cn += 1
        cached[key] = rec

        flag = ("EN✓" if rec.get("en") else "EN—") + (" CN✓" if rec.get("cn") else " CN—")
        print(f"  [{i}/{len(years)}] {year} {flag}  en={len(rec.get('en',''))}字 cn={len(rec.get('cn',''))}字")
        OUT.write_text(
            json.dumps({"source": BASE, "fetched": date.today().isoformat(), "citations": cached},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    have_en = sum(1 for v in cached.values() if v.get("en"))
    have_cn = sum(1 for v in cached.values() if v.get("cn"))
    missing = sorted(int(k) for k, v in cached.items() if not v.get("en"))
    print(f"\n写入 {OUT}")
    print(f"  共 {len(cached)} 届 · 英文评审词 {have_en} · 中文评审词 {have_cn}"
          f" · 跳过 {skipped} · 本次新抓 EN {got_en} / CN {got_cn}")
    if missing:
        print(f"  ! 仍缺英文评审词的届：{missing}")


if __name__ == "__main__":
    main()

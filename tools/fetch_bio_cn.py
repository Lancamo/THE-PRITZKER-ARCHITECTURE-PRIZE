#!/usr/bin/env python3
"""A 数据官 · 官网中文生平抓取（The Pritzker Architecture Prize）

用法: python3 tools/fetch_bio_cn.py [--limit N] [--refetch]

中文站的得主页是 https://www.pritzkerprize.com/cn/laureates/<年份>，
页面里「简历」折叠区块即官方中文生平（英文版由 tools/fetch_pritzker_details.py 抓）。
中文站未覆盖的年份留空，页面回退为只显示英文。

输出 data/bio_cn.json：{ "1979": {"paragraphs": ["…", "…"]} }
版权：文本 © The Pritzker Architecture Prize，本项目非商业展示

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
OUT = DATA / "bio_cn.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) PritzkerViz/2.0 (non-commercial archive)"
BASE = "https://www.pritzkerprize.com"

BIO_LABEL = re.compile(r"简历|生平")
BLOCK_END_RE = re.compile(r'<div class="field field--name-field-|</article>', re.I)


def html_paras(fragment: str) -> list[str]:
    """剔插图与图注后按 <p> 取段落"""
    fragment = re.sub(r"<(script|style|figure|figcaption)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    paras = []
    for raw in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.S):
        t = html_mod.unescape(re.sub(r"<[^>]+>", "", raw)).replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) >= 30:
            paras.append(t)
    return paras


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


def pick_block(page: str, want: re.Pattern) -> str:
    """找标签（简历/生平）对应的折叠块，取整篇 <article>（含后续续文；旧逻辑在
    「下一个字段容器」处截断，会丢掉后半段生平），按 <p> 保留官网分段。"""
    ids: list[str] = []
    for m in want.finditer(page):
        for bid in re.findall(r'data-target="#([\w-]+)"', page[max(0, m.start() - 500): m.start() + 120]):
            if bid not in ids:
                ids.append(bid)
    for bid in ids:
        m = re.search(r'<article[^>]*id="' + re.escape(bid) + r'"[^>]*>(.*?)(?=</article>)', page, re.S)
        if m:
            paras = html_paras(m.group(1))
            if paras:
                return "\n\n".join(paras)
            continue
        old = re.search(r'id="' + re.escape(bid) + r'"[^>]*>(.*)', page, re.S)   # 老式页面兜底
        if not old:
            continue
        end = BLOCK_END_RE.search(old.group(1))
        chunk = old.group(1)[: end.start()] if end else old.group(1)
        paras = html_paras(chunk)
        if paras:
            return "\n\n".join(paras)
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args()

    cached: dict[str, dict] = {}
    if OUT.exists():
        cached = json.loads(OUT.read_text(encoding="utf-8")).get("bios", {})

    years = list(range(1979, 2027))
    if args.limit:
        years = years[: args.limit]
    got = skipped = missing = 0
    for i, year in enumerate(years, 1):
        key = str(year)
        if not args.refetch and cached.get(key, {}).get("paragraphs"):
            skipped += 1
            continue
        try:
            text = pick_block(get(f"{BASE}/cn/laureates/{year}"), BIO_LABEL)
            # 中文站早年各届的「简历」区块里同样是英文原文——只在真含中文时才收录
            if text and not re.search(r"[一-鿿]", text):
                text = ""
            time.sleep(0.4)
        except urllib.error.HTTPError:
            text = ""
        except Exception as exc:  # noqa: BLE001
            print(f"  {year} 失败：{exc}")
            text = ""
        if text:
            cached[key] = {"paragraphs": text.split("\n\n")}
            got += 1
        else:
            cached.pop(key, None)   # 重抓后若不再命中（校验不过/页面消失），清掉旧值
            missing += 1
        print(f"  [{i}/{len(years)}] {year} {'✓ ' + str(len(text)) + ' 字' if text else '— 中文站无此届'}")
        OUT.write_text(
            json.dumps({"source": BASE, "fetched": date.today().isoformat(), "bios": cached},
                       ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    have = sum(1 for v in cached.values() if v.get("paragraphs"))
    print(f"\n写入 {OUT}")
    print(f"  有中文生平 {have} 届 · 本次新抓 {got} · 跳过 {skipped} · 中文站无 {missing}")


if __name__ == "__main__":
    main()

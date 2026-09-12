#!/usr/bin/env python3
"""B 视觉官 · 字体获取：从 Google Fonts 拉取拉丁子集 woff2 存到 assets/fonts。

用法: python3 tools/subset_fonts.py

- 只取拉丁子集（含数字/标点），供 Fraunces / IBM Plex Mono / Inter 三层展示与数据字体
- 中文字体不内嵌，运行时走系统栈（PingFang SC / Songti SC / Noto 回退）
- build.py 会把 assets/fonts/*.woff2 以 base64 内嵌进产物
- 若某字体失败，运行时自动回退系统字体，不阻断构建
"""
from __future__ import annotations

import re
import ssl
import urllib.request
from pathlib import Path

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # noqa: BLE001
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

REQUESTS = [
    # (css2 查询, 保存名)
    ("family=Fraunces:opsz,wght@9..144,600", "fraunces-600.woff2"),
    ("family=IBM+Plex+Mono:wght@400", "plex-mono-400.woff2"),
    ("family=IBM+Plex+Mono:wght@600", "plex-mono-600.woff2"),
    ("family=Inter:wght@400", "inter-400.woff2"),
    ("family=Inter:wght@600", "inter-600.woff2"),
]


def fetch(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
        out.write_bytes(resp.read())


def main() -> None:
    FONTS.mkdir(parents=True, exist_ok=True)
    for query, name in REQUESTS:
        out = FONTS / name
        if out.exists() and out.stat().st_size > 1000:
            print(f"  · 已存在 {name} ({out.stat().st_size // 1024} KB)")
            continue
        css_url = f"https://fonts.googleapis.com/css2?{query}&display=swap"
        try:
            req = urllib.request.Request(css_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
                css = resp.read().decode("utf-8")
            # 取最后一个 latin 子集的 woff2（css2 按 unicode-range 分块，latin 通常最后）
            urls = re.findall(r"url\((https://[^)]+\.woff2)\)", css)
            if not urls:
                print(f"  ! {name}：CSS 中未找到 woff2")
                continue
            fetch(urls[-1], out)
            print(f"  ✓ {name} ({out.stat().st_size // 1024} KB)")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {name} 失败：{exc}（运行时回退系统字体）")


if __name__ == "__main__":
    main()

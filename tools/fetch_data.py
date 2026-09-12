#!/usr/bin/env python3
"""A 数据官 · 地理数据构建：国家坐标表 + 简化世界轮廓 → data/geo.json。

用法: python3 tools/fetch_data.py

- 世界轮廓来自 johan/world.geo.json（Natural Earth 派生的国家边界 GeoJSON）
- 用 Douglas-Peucker 简化 + 1 位小数取整，压到 <100KB
- 国家填充同色、不描边，视觉上等价于陆地剪影
- 若网络不可用且已有 data/geo.json，则保留原文件
"""
from __future__ import annotations

import json
import math
import ssl
import urllib.request
from pathlib import Path

try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # noqa: BLE001
    SSL_CTX = ssl.create_default_context()

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "geo.json"
SOURCE = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"

# 得主国籍（图A 用）+ 代表作所在国（图B 用）坐标——取首都/主要城市附近
COUNTRY_COORDS = {
    "美国": [38.9, -77.0], "墨西哥": [19.4, -99.1], "加拿大": [45.4, -75.7],
    "巴西": [-15.8, -47.9], "智利": [-33.4, -70.7],
    "英国": [51.5, -0.13], "法国": [48.9, 2.35], "西班牙": [40.4, -3.7],
    "意大利": [41.9, 12.5], "葡萄牙": [38.7, -9.1], "瑞士": [46.9, 7.45],
    "德国": [52.5, 13.4], "西德": [50.7, 7.1], "爱尔兰": [53.3, -6.26],
    "奥地利": [48.2, 16.4], "挪威": [59.9, 10.75], "荷兰": [52.1, 4.3],
    "丹麦": [55.7, 12.6],
    "日本": [35.7, 139.7], "中国": [39.9, 116.4], "印度": [28.6, 77.2],
    "伊拉克": [33.3, 44.4],
    "布基纳法索": [12.4, -1.5], "澳大利亚": [-33.9, 151.2],
}


def simplify(points: list[list[float]], eps: float) -> list[list[float]]:
    """Douglas-Peucker 简化（点格式 [lng, lat]）"""
    if len(points) <= 2:
        return points

    def dist(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = dist(points[i], points[0], points[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        left = simplify(points[: idx + 1], eps)
        right = simplify(points[idx:], eps)
        return left[:-1] + right
    return [points[0], points[-1]]


def rings_of(geometry: dict) -> list[list[list[float]]]:
    t, c = geometry.get("type"), geometry.get("coordinates", [])
    if t == "Polygon":
        return [c[0]] if c else []
    if t == "MultiPolygon":
        return [poly[0] for poly in c if poly]
    return []


def main() -> None:
    print(f"下载世界轮廓 {SOURCE}")
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "PritzkerViz/2.0"})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as resp:
        geo = json.loads(resp.read().decode("utf-8"))

    rings: list[list[list[float]]] = []
    for feat in geo.get("features", []):
        for ring in rings_of(feat.get("geometry") or {}):
            if len(ring) < 4:
                continue
            # 面积过滤：去掉极小岛屿（<0.35 平方度，粗略）
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            if (max(xs) - min(xs)) * (max(ys) - min(ys)) < 0.35:
                continue
            simple = simplify(ring, 0.45)
            if len(simple) >= 4:
                rings.append([[round(x, 1), round(y, 1)] for x, y in simple])

    payload = {
        "source": SOURCE,
        "note": "land rings simplified (Douglas-Peucker eps=0.45, 1 decimal)",
        "countryCoords": COUNTRY_COORDS,
        "land": rings,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    points = sum(len(r) for r in rings)
    print(f"生成 {OUT} · {len(rings)} 环 · {points} 点 · {size_kb:.1f} KB")


if __name__ == "__main__":
    main()

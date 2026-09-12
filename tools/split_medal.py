#!/usr/bin/env python3
"""奖章素材切分：medal-sides.png（左正面 / 右背面，自带透明通道）
   → medal-front.png / medal-back.png（统一尺度的方形透明底，圆面恰好内切）

- 按 alpha 外接框裁切每枚奖章，透明补边成方形
- 两面共用同一画布边长，保证旋转时正反面直径完全一致
- 打印圆面占方形比例，供 CSS 的厚度层（.medal-edge）设置内缩量
"""
from __future__ import annotations

import math
import statistics
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "brand"
SRC = ASSETS / "medal-sides.png"
OUT_SIZE = 640
PAD = 3  # 外接框外扩像素（越小，圆面越贴近方形边缘）


def crop_by_alpha(img: Image.Image) -> Image.Image:
    box = img.getchannel("A").getbbox()
    if not box:
        return img
    x0, y0, x1, y1 = box
    return img.crop((
        max(0, x0 - PAD), max(0, y0 - PAD),
        min(img.width, x1 + PAD), min(img.height, y1 + PAD),
    ))


def sample_ring(img: Image.Image, r_ratio: float, radius: float, cx: float, cy: float) -> tuple[int, int, int]:
    """在半径 r_ratio*R 的圆周上多点取样，返回中位色"""
    cols = []
    r = r_ratio * radius
    for i in range(72):
        a = 2 * math.pi * i / 72
        x = int(min(img.width - 1, max(0, cx + r * math.cos(a))))
        y = int(min(img.height - 1, max(0, cy + r * math.sin(a))))
        px = img.getpixel((x, y))
        if len(px) == 4 and px[3] < 40:
            continue
        cols.append(px[:3])
    if not cols:
        return (120, 84, 40)
    return tuple(int(statistics.median(c[k] for c in cols)) for k in range(3))


def make_edge(front: Image.Image, out: Path) -> None:
    """由正面实拍取样生成侧壁贴图：中心→外缘按取样色做径向渐变"""
    size = front.width
    box = front.getchannel("A").getbbox() or (0, 0, size, size)
    radius = min(box[2] - box[0], box[3] - box[1]) / 2
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

    stops = [(0.55, sample_ring(front, 0.55, radius, cx, cy)),
             (0.78, sample_ring(front, 0.78, radius, cx, cy)),
             (0.93, sample_ring(front, 0.93, radius, cx, cy)),
             (1.00, sample_ring(front, 1.00, radius, cx, cy))]
    # 外缘压暗 12%，切出金属倒角的暗边
    edge_dark = tuple(int(c * 0.82) for c in stops[-1][1])

    edge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(edge)
    for r in range(int(radius), 0, -1):
        t = r / radius
        # 分段线性插值取样色
        lo, hi = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                lo, hi = stops[i], stops[i + 1]
                break
        span = (hi[0] - lo[0]) or 1e-6
        k = (t - lo[0]) / span
        col = tuple(int(lo[1][j] + (hi[1][j] - lo[1][j]) * k) for j in range(3))
        if t > 0.985:
            col = tuple(int(col[j] * 0.9 + edge_dark[j] * 0.1) for j in range(3))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,))
    edge.save(out)
    print(f"生成 {out.name}（取样色 中段{stops[1][1]} 外缘{stops[-1][1]}）")


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    mid = src.width // 2
    front = crop_by_alpha(src.crop((0, 0, mid, src.height)))
    back = crop_by_alpha(src.crop((mid, 0, src.width, src.height)))

    side = max(front.width, front.height, back.width, back.height)
    faces = []
    for face in (front, back):
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(face, ((side - face.width) // 2, (side - face.height) // 2))
        faces.append(canvas.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS))

    faces[0].save(ASSETS / "medal-front.png")
    faces[1].save(ASSETS / "medal-back.png")
    make_edge(faces[0], ASSETS / "medal-edge.png")

    diameter = max(front.width, front.height) / side
    print(f"生成 medal-front.png / medal-back.png（{OUT_SIZE}px，圆面占比 {diameter:.3f}）")
    print(f"  建议 .medal-edge inset = {100 * (1 - diameter) / 2:.2f}%")


if __name__ == "__main__":
    main()

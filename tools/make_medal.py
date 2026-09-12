#!/usr/bin/env python3
"""生成普利兹克风格青铜奖章 SVG → assets/brand/medal.svg

月桂环 + 放射棱纹 + 中央建筑浮雕 + 环铭 FIRMNESS · COMMODITY · DELIGHT。
透明底，页面以 mix-blend-mode:screen 叠加在深色 Hero 上呈现 PNG 抠图感。
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "brand" / "medal.svg"
CX = CY = 256.0


def pt(r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return CX + r * math.cos(a), CY + r * math.sin(a)


def fluting() -> str:
    """放射棱纹（rim 内侧一圈短刻线）"""
    parts = []
    for i in range(72):
        deg = i * 5
        x1, y1 = pt(196, deg)
        x2, y2 = pt(208, deg)
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#7a4c22" stroke-width="2" opacity="0.5"/>'
        )
    return "\n  ".join(parts)


def leaf(r: float, deg: float, size: float, fill: str, stroke: str) -> str:
    """一片月桂叶：沿切线方向的梭形"""
    x, y = pt(r, deg)
    return (
        f'<path d="M0,{-size:.1f} Q{size * 0.62:.1f},0 0,{size:.1f} Q{-size * 0.62:.1f},0 0,{-size:.1f} Z" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="0.8" '
        f'transform="translate({x:.1f},{y:.1f}) rotate({deg + 90 + 24:.1f})"/>'
    )


def laurel() -> str:
    """左右两支月桂，从底部两侧向上环绕"""
    parts = []
    # 枝干
    parts.append(
        '<path d="M256,436 C160,436 92,368 92,268" fill="none" stroke="#6e451f" stroke-width="4" opacity="0.85"/>'
    )
    parts.append(
        '<path d="M256,436 C352,436 420,368 420,268" fill="none" stroke="#6e451f" stroke-width="4" opacity="0.85"/>'
    )
    # 叶：左支沿圆 100°→170°（自下而上），右支镜像
    n = 9
    for i in range(n):
        t = i / (n - 1)
        deg_l = 100 + t * 68          # 左支（SVG y 轴向下，角度顺时针）
        deg_r = 80 - t * 68
        size = 17 - t * 5
        parts.append(leaf(172, deg_l, size, "#9c6a2e", "#5e3c18"))
        parts.append(leaf(172, deg_l - 5.5, size * 0.82, "#b07c38", "#5e3c18"))
        parts.append(leaf(172, deg_r, size, "#9c6a2e", "#5e3c18"))
        parts.append(leaf(172, deg_r + 5.5, size * 0.82, "#b07c38", "#5e3c18"))
    # 底部系结
    parts.append('<circle cx="256" cy="436" r="7" fill="#7a4c22" stroke="#4e3010" stroke-width="1.5"/>')
    return "\n  ".join(parts)


def building() -> str:
    """中央建筑浮雕：几何体块构成的现代主义塔楼"""
    bars = [
        (-66, -8, 22, 86),   # x, y, w, h（相对中心，y 为顶部）
        (-36, -46, 24, 124),
        (-4, -78, 26, 156),
        (30, -30, 22, 108),
    ]
    parts = ['<g stroke="#4e3010" stroke-width="2.5" fill="#c99a55" opacity="0.92">']
    for x, y, w, h in bars:
        parts.append(f'<rect x="{CX + x:.1f}" y="{CY + y:.1f}" width="{w}" height="{h}"/>')
    parts.append("</g>")
    # 立面窗格
    win = ['<g fill="#7a4c22" opacity="0.8">']
    for x, y, w, h in bars:
        rows = int(h // 18)
        for r in range(rows):
            for c in range(2):
                wx = CX + x + 4.5 + c * (w / 2)
                wy = CY + y + 6 + r * 18
                win.append(f'<rect x="{wx:.1f}" y="{wy:.1f}" width="{w / 2 - 7:.1f}" height="7"/>')
    win.append("</g>")
    # 基座
    parts.append(
        f'<rect x="{CX - 74:.1f}" y="{CY + 82:.1f}" width="148" height="9" fill="#4e3010"/>'
    )
    return "\n  ".join(parts + win)


def main() -> None:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <radialGradient id="bz" cx="42%" cy="36%" r="75%">
      <stop offset="0%" stop-color="#e0b06a"/>
      <stop offset="55%" stop-color="#a97a36"/>
      <stop offset="100%" stop-color="#6e451f"/>
    </radialGradient>
    <radialGradient id="field" cx="45%" cy="38%" r="80%">
      <stop offset="0%" stop-color="#d3a056"/>
      <stop offset="100%" stop-color="#8a5a2a"/>
    </radialGradient>
    <path id="rim-arc-top" d="M256,256 m-186,0 a186,186 0 1,1 372,0 a186,186 0 1,1 -372,0" fill="none"/>
  </defs>

  <!-- 牌体 -->
  <circle cx="256" cy="256" r="240" fill="url(#bz)" stroke="#4e3010" stroke-width="3"/>
  <circle cx="256" cy="256" r="222" fill="none" stroke="#5e3c18" stroke-width="10" opacity="0.55"/>
  <circle cx="256" cy="256" r="214" fill="none" stroke="#e8c084" stroke-width="1.5" opacity="0.8"/>
  {fluting()}

  <!-- 环铭 -->
  <text font-family="Georgia, 'Times New Roman', serif" font-size="21" letter-spacing="5.5" fill="#42280c">
    <textPath href="#rim-arc-top" startOffset="25%" text-anchor="middle">FIRMNESS · COMMODITY · DELIGHT</textPath>
  </text>
  <text font-family="Georgia, 'Times New Roman', serif" font-size="15" letter-spacing="4" fill="#42280c">
    <textPath href="#rim-arc-top" startOffset="76.5%" text-anchor="middle">THE PRITZKER ARCHITECTURE PRIZE</textPath>
  </text>

  <!-- 内圈与月桂 -->
  <circle cx="256" cy="256" r="152" fill="url(#field)" stroke="#5e3c18" stroke-width="3"/>
  <circle cx="256" cy="256" r="144" fill="none" stroke="#e8c084" stroke-width="1" opacity="0.6"/>
  {laurel()}

  <!-- 中央建筑浮雕 -->
  {building()}

  <!-- 高光 -->
  <ellipse cx="186" cy="120" rx="130" ry="60" fill="#ffffff" opacity="0.10" transform="rotate(-24 186 120)"/>
</svg>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"生成 {OUT}")


if __name__ == "__main__":
    main()

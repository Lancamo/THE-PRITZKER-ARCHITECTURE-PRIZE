#!/usr/bin/env python3
"""B 视觉官 · 字体抓取（Google Fonts）

用法: python3 tools/fetch_fonts.py

- Outfit（可变字重，拉丁/数字）：标题与强调的西文、数字
- Noto Sans SC（思源黑体，按用字子集）：大标题与强调的中文
  子集文本 = 页面大标题/强调用字 + 全部得主中文名，控制体积
- Noto Sans SC Light（正文中文）：由 assets/fonts/source/NotoSansSC-VF.ttf 实例化 wght=300，
  再按「全站用字」（从 dist 产物抽取全部 CJK）本地子集化（需 fontTools）
- 输出 assets/fonts/*.woff2；来源标注见 assets/fonts/manifest.json
"""
from __future__ import annotations

import json
import re
import ssl
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
FONTS = ROOT / "assets" / "fonts"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

# 标题与强调的固定用字（其余从数据里收集得主姓名）
FIXED_CN = (
    "普利兹克建筑奖折叠总览时间轴数据得主国籍分布代表作地理分布"
    "时间轴档案届获奖年龄谱系全部亚洲欧洲北美南美非洲大洋洲"
    "生平原作者设计数据代码整理中来源影像图注一二三四五六七八九十"
    "第届年份作品城市建成年表档案展开收起全文总览现任展览"
    "当前位置按十年跳转返回总览历届得主肖像评审辞代表作精选"
    "非商业展示官方网站收录沿革流派现代主义后现代解构地域"
    "世纪建筑师事务所重要奖项实践教育经历研究著作展览获奖"
    "最新动态新闻媒体专题特稿访谈评论专辑影像资料照片版权"
)


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40, context=SSL_CTX) as resp:
        return resp.read()


def css_urls(css: str) -> list[str]:
    """取出 @font-face 中的字体 URL（Google 子集接口返回 /l/font?kit=… 形式，不一定是 .woff2 结尾）"""
    return [u for u in re.findall(r"url\((https://[^)]+)\)", css) if "fonts.gstatic.com" in u]


def subset_text() -> str:
    editions = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))["editions"]
    chars = set(FIXED_CN)
    for e in editions:
        for l in e["laureates"]:
            chars.update(l["name_cn"])
    return "".join(sorted(chars))


def fetch_outfit() -> list[dict]:
    css = get("https://fonts.googleapis.com/css2?family=Outfit:wght@100..900&display=swap").decode()
    urls = css_urls(css)
    # 取 latin 段（最后一个 url 通常是 latin）
    out = FONTS / "outfit-var.woff2"
    out.write_bytes(get(urls[-1]))
    print(f"  ✓ {out.name}  ←  {urls[-1][:70]}")
    return [{"file": "assets/fonts/outfit-var.woff2", "family": "Outfit", "weights": "100..900",
             "source": "Google Fonts / Outfit (OFL)", "url": urls[-1]}]


def fetch_noto(weight: int, text: str) -> list[dict]:
    url = ("https://fonts.googleapis.com/css2?"
           + urllib.parse.urlencode({"family": f"Noto Sans SC:wght@{weight}", "text": text}))
    css = get(url).decode()
    urls = css_urls(css)
    if not urls:
        print(f"  ! Noto Sans SC {weight} 未取到字体文件")
        return []
    out = FONTS / f"noto-sans-sc-{weight}.woff2"
    out.write_bytes(get(urls[0]))
    print(f"  ✓ {out.name}  ←  {urls[0][:70]}")
    return [{"file": f"assets/fonts/{out.name}", "family": "Noto Sans SC (subset)",
             "weights": str(weight), "subset_chars": len(text), "source": "Google Fonts / Noto Sans SC (OFL)",
             "url": urls[0]}]


def body_corpus() -> str:
    """正文中文子集语料 = 全站用字：dist 产物里的全部 CJK 与中文标点（无 dist 时扫数据与源码），
    另附 ASCII / 拉丁补充（中文段落里夹带的西文人名等）"""
    text = ""
    dist = ROOT / "dist" / "index.html"
    if dist.exists():
        text = dist.read_text(encoding="utf-8")
    else:
        for p in list(DATA.glob("*.json")) + list((ROOT / "src").rglob("*")):
            try:
                text += p.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue
    cjk = sorted(set(
        ch for ch in text
        if '一' <= ch <= '鿿' or '　' <= ch <= '〿'
        or '＀' <= ch <= '￯' or ch in "—…·“”‘’"
    ))
    return "".join(chr(c) for c in range(0x20, 0x100)) + "".join(cjk)


def fetch_noto_light() -> list[dict]:
    """思源黑体 Light（正文中文，全站用字子集）：由源文件实例化 wght=300 后本地子集化
    （Google 子集接口的 text= 装不下两千余字的全站用字）"""
    src = FONTS / "source" / "NotoSansSC-VF.ttf"
    out = FONTS / "noto-sans-sc-300.woff2"
    if not src.exists():
        print(f"  ! 缺 {src}（源文件备份），跳过正文 Light 子集")
        return []
    try:
        import fontTools  # noqa: F401
    except ImportError:
        print("  ! 未安装 fontTools（pip install fonttools），跳过正文 Light 子集")
        return []
    import subprocess
    import sys
    import tempfile

    corpus = body_corpus()
    with tempfile.TemporaryDirectory() as td:
        light = Path(td) / "NotoSansSC-Light.ttf"
        cf = Path(td) / "corpus.txt"
        cf.write_text(corpus, encoding="utf-8")
        subprocess.run([sys.executable, "-m", "fontTools.varLib.instancer", str(src),
                        "wght=300", "--output", str(light)], check=True, capture_output=True)
        subprocess.run([sys.executable, "-m", "fontTools.subset", str(light),
                        f"--text-file={cf}", "--flavor=woff2", f"--output-file={out}"],
                       check=True, capture_output=True)
    print(f"  ✓ {out.name}  ←  {src.name} 实例化 wght=300 + 子集（{len(corpus)} 字符语料）")
    return [{"file": "assets/fonts/noto-sans-sc-300.woff2", "family": "Noto Sans SC (Light subset, local)",
             "weights": "300", "subset_chars": len(corpus),
             "source": "Google Fonts / Noto Sans SC (OFL)，本地实例化 + fontTools 子集"}]


def main() -> None:
    FONTS.mkdir(parents=True, exist_ok=True)
    text = subset_text()
    print(f"思源黑体子集用字：{len(text)} 个")
    manifest = fetch_outfit()
    manifest += fetch_noto(700, text)
    manifest += fetch_noto(900, text)
    manifest += fetch_noto_light()
    (FONTS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成 → {FONTS}")


if __name__ == "__main__":
    main()

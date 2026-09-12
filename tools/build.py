#!/usr/bin/env python3
"""F 集成官 · 构建：data + src + vendor + fonts → dist/index.html

用法: python3 tools/build.py

- 数据合并注入 window.__DATA__（editions / dossiers / bands / lineage / trivia / geo）
- 字体：assets/fonts/*.woff2 → base64 @font-face（中文字体走系统栈，不内嵌）
- vendor：D3 系列内联；JS 每文件独立 <script>
- 产物末尾注入 localhost 自动刷新脚本（HEAD 轮询 Last-Modified，1s，非 localhost 失效）
- 图片以 ../assets/ 相对路径引用（dist/index.html 与 assets/ 同级目录下可整体拷贝，双击可开）
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DATA = ROOT / "data"
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "dist" / "index.html"

CSS_FILES = ["tokens.css", "base.css", "home.css", "archive.css", "detail.css"]
JS_FILES = [
    "util.js", "store.js", "router.js", "transition.js",
    "timeline.js", "chart-nations.js", "chart-geo.js",
    "medal.js", "archive.js", "detail.js", "main.js",
]
VENDOR_FILES = [
    "d3.min.js",
    "d3-weighted-voronoi.min.js",
    "d3-voronoi-map.min.js",
    "d3-voronoi-treemap.min.js",
]
FONT_FACES = [
    ("Fraunces", "fraunces-600.woff2", "600"),
    ("IBM Plex Mono", "plex-mono-400.woff2", "400"),
    ("IBM Plex Mono", "plex-mono-600.woff2", "600"),
    ("Inter", "inter-400.woff2", "400"),
    ("Inter", "inter-600.woff2", "600"),
    # 标题与强调：Outfit 可变字重（西文/数字）+ Noto Sans SC 子集（思源黑体，中文用字）
    ("Outfit", "outfit-var.woff2", "100 900"),
    ("Noto Sans SC", "noto-sans-sc-300.woff2", "300"),   # 正文中文（Light，全站用字子集）
    ("Noto Sans SC", "noto-sans-sc-700.woff2", "700"),
    ("Noto Sans SC", "noto-sans-sc-900.woff2", "900"),
]

AUTO_REFRESH = """
<script>
/* local dev auto-refresh (localhost only) */
(function(){
  var h = location.hostname;
  if (h !== "localhost" && h !== "127.0.0.1") return;
  var last = null;
  setInterval(function(){
    fetch(location.href, { method: "HEAD", cache: "no-store" })
      .then(function(r){
        var t = r.headers.get("Last-Modified");
        if (last === null) { last = t; }
        else if (t && t !== last) { location.reload(); }
      })
      .catch(function(){});
  }, 1000);
})();
</script>
"""


def load_data() -> dict:
    editions = json.loads((DATA / "editions.json").read_text(encoding="utf-8"))
    laureates = json.loads((DATA / "laureates.json").read_text(encoding="utf-8"))
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    geo = json.loads((DATA / "geo.json").read_text(encoding="utf-8"))
    cites_path = DATA / "citations.json"
    citations = json.loads(cites_path.read_text(encoding="utf-8"))["citations"] if cites_path.exists() else {}
    bio_path = DATA / "bio_cn.json"
    bio_cn = json.loads(bio_path.read_text(encoding="utf-8"))["bios"] if bio_path.exists() else {}
    align_path = DATA / "bio_cn_aligned.json"
    bio_aligned = json.loads(align_path.read_text(encoding="utf-8"))["groups"] if align_path.exists() else {}
    cite_align_path = DATA / "citation_aligned.json"
    citation_aligned = json.loads(cite_align_path.read_text(encoding="utf-8"))["groups"] if cite_align_path.exists() else {}
    return {
        "editions": editions["editions"],
        "fetched": editions.get("fetched", ""),
        "dossiers": laureates["dossiers"],
        "citations": citations,
        "bioCn": bio_cn,
        "bioAligned": bio_aligned,
        "citationAligned": citation_aligned,
        "bands": meta["movementBands"],
        "lineage": meta["lineage"],
        "trivia": meta["trivia"],
        "geo": geo,
    }


def font_css() -> str:
    chunks = []
    missing = []
    for family, fname, weight in FONT_FACES:
        path = FONTS / fname
        if not path.exists():
            missing.append(fname)
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        chunks.append(
            "@font-face{font-family:'%s';font-weight:%s;font-style:normal;font-display:swap;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}" % (family, weight, b64)
        )
    if missing:
        print(f"  ! 字体缺失（运行 tools/subset_fonts.py）：{', '.join(missing)}")
    return "\n".join(chunks)


def read_css() -> str:
    return "\n".join((SRC / "styles" / n).read_text(encoding="utf-8") for n in CSS_FILES)


def read_js() -> str:
    parts = []
    for n in JS_FILES:
        code = (SRC / "js" / n).read_text(encoding="utf-8").replace("</script", "<\\/script")
        parts.append(f"<script>/* {n} */\n{code}\n</script>")
    return "\n".join(parts)


def read_vendor() -> str:
    parts = []
    for n in VENDOR_FILES:
        p = SRC / "vendor" / n
        if not p.exists():
            raise SystemExit(f"缺少 vendor 依赖 {p}")
        code = p.read_text(encoding="utf-8").replace("</script", "<\\/script")
        parts.append(f"<script>/* {n} */\n{code}\n</script>")
    return "\n".join(parts)


def main() -> None:
    payload = load_data()
    template = (SRC / "template.html").read_text(encoding="utf-8")

    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")

    html = template
    html = html.replace("/*__FONTS__*/", font_css())
    html = html.replace("/*__CSS__*/", read_css())
    html = html.replace("<!--__VENDOR__-->", read_vendor())
    html = html.replace("/*__DATA__*/ null", blob)
    html = html.replace("<script>/*__JS__*/</script>", read_js())
    html = html.replace("</body>", AUTO_REFRESH + "</body>")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")

    people = sum(len(e["laureates"]) for e in payload["editions"])
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"生成 {OUT}")
    print(f"  {len(payload['editions'])} 届 · {people} 位得主 · {len(payload['geo']['land'])} 陆地环 · {size_mb:.2f} MB")


if __name__ == "__main__":
    main()

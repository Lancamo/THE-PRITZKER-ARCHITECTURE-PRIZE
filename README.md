# 普利兹克建筑奖可视化 V2.0

> **版本：v4.0.0（2026-09-13 首发）** — 本仓库为普利兹克建筑奖展示站的源码、数据与构建产物。

单色档案风格的数据可视化站点：首页（Hero + 国籍/地理/时间轴同屏总览）+ 48 届详情档案。
暖象牙 × 近黑双色体系（参照 kim-seunghyuk），唯一主题色克莱因蓝 #1D39F5 仅作交互反馈（参照 specia1ne），编辑排版参照 nabil-issa-architect。
产物为 `dist/index.html` + `assets/`（可整体拷贝、断网双击可开）。

- 获奖年龄已并入时间轴「年龄 Age」图层（虚线刻度 50—90 岁），不再单设散点图
- 国籍分布：同一大洲连成统一大块（洲级灰阶 + 投影粗缝 + 洲名标注），洲内按国家拆小块
- LOGO 页内呈现（随 Hero 滚动，不做全局悬浮）：`tools/crop_logo.py` 把 `logo-src-w/b.png` 裁切抠底为 `logo-ink.png`（墨标，浅底）/ `logo-paper.png`（象牙标，深底）
- Hero 右侧青铜奖章：`assets/brand/medal-sides.png`（原始素材，左正面/右背面）→ `tools/split_medal.py` 切成 `medal-front.png` / `medal-back.png`（透明底、圆面内切）；页面为 3D 双面 + 14 层厚度侧壁，拖拽 1:1 跟随、松手按动量投射吸附（阻尼比 0.8 / 响应 0.4s 弹簧）、点击翻转、键盘 ←→/Enter/Home（`src/js/medal.js`）
- 页面路由：`#/`（总览）· `#/timeline/2012`（时间轴档案，长卷主线：姓名/肖像/生平/评审辞/代表作）· `#/laureate/2012`（单届全档）；档案页支持 ←→ 逐届跳转、ESC 逐级返回、顶部阅读进度、年份灰白状态（已抵达为白）
- 首页底部继续下滑即可进入时间轴档案：时间轴向左滑出淡出、页脚向右滑出淡出、档案页自下而上浮起（版式参照 eladiodieste.com）
- 标题与强调字体：Outfit（西文/数字，可变字重）+ 思源黑体（中文，Noto Sans SC 按用字子集内嵌）；正文保持 Inter / Songti 体系
- 页脚署名：Design & Code by **LANCAMO**

## 目录

```
V2.0/
├── CONTRACT.md        # 模块接口契约（冻结）
├── data/              # editions / laureates / meta / geo
├── assets/            # portraits / works / fonts（+ manifest.json 来源记录）
├── src/               # template.html / styles/ / js/ / vendor/
├── tools/             # fetch_data / fetch_assets / refetch_assets / subset_fonts / make_editions / build
└── dist/index.html    # 构建产物
```

## 重新构建

```bash
python3 tools/build.py        # 数据 + 模板 + 字体 → dist/index.html
```

修改样式或交互后只跑这一条。首次或素材更新时按需运行：

```bash
python3 tools/subset_fonts.py        # 拉取拉丁字体子集（Fraunces / Plex Mono / Inter）
python3 tools/fetch_fonts.py         # 标题字体：Outfit 可变字重 + 思源黑体子集；正文字体：Noto Sans SC Light 全站用字子集（需 fontTools，源文件在 assets/fonts/source/）
python3 tools/fetch_pritzker.py      # 官网肖像（--force 重下原图）
python3 tools/fetch_pritzker_details.py   # 官网生平与项目图文
python3 tools/fetch_citations.py     # 官网评审词（英文全 48 届 / 中文站有译文的 2011–2026 届）
python3 tools/fetch_missing_works.py # 缺失作品照片补齐（维基 → Commons，严格校验防错配）
python3 tools/enrich_assets.py       # 素材注入 editions.json（含失效引用清理）
python3 tools/check_assets.py        # 素材核验：数据引用是否全部存在
python3 tools/optimize_assets.py     # 素材压缩（肖像保持原始精度，作品/项目 ≤1600px）
python3 tools/fetch_data.py          # 世界轮廓简化 + 国家坐标表
python3 tools/make_editions.py       # V1.0 awards.json 富化（生卒年 / 坐标）→ editions.json
```

## 本地预览

```bash
cd .. && python3 -m http.server 8792     # 根目录起服务，打开 /V2.0/dist/
```

dist 产物内已注入 localhost 自动刷新脚本：本地打开时文件一变页面自动刷新（发给他人时脚本自动失效）。

## 数据与版权

- 届次 / 得主 / 国籍：维基百科《普利兹克建筑奖》条目（V1.0 整理）
- **肖像 / 生平 / 项目**：The Pritzker Architecture Prize 官网（`tools/fetch_pritzker.py` 抓肖像，`tools/fetch_pritzker_details.py` 抓生平与项目图文；非商业展示）
- 评审辞：pritzkerprize.com 官方 Jury Citation，英文全 48 届 + 中文 2011–2026 届（保留官网分段，中英逐段严格对应）；首页引言轮播取其中的短引（`data/citations.json` 的 `quote_en` / `quote_cn`，中英同起同止），与同届代表作照片成对切换
- 代表作影像：Wikimedia Commons（CC BY-SA / 公有领域），逐张记录于 `assets/_fetch_report.json`，页面图注署名
- 样板 3 届（2012 王澍 / 2004 扎哈 / 1988 双得主）另含手写档案字段（事务所、冷知识等）；48 届均收录官网评审辞全文与官方生平，中文译文覆盖 2011–2026 届

## 已知边界

- 中文以子集内嵌：标题用 Noto Sans SC 700/900，正文用 Noto Sans SC Light（全站用字子集，新增文案后需重跑 fetch_fonts.py，否则缺字回退会造成字重不匀）；原始字体源文件备份在 `assets/fonts/source/`
- 世界轮廓为 45KB 简化版（Douglas-Peucker eps=0.45），仅作点位底图
- 筛选状态写入 URL（`#?s=country|中国`），详情路由为 `#/laureate/2012`

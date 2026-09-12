# 字体源文件备份（基础素材）

本站使用字体的**官方原始文件**（Google Fonts 开源字体，均为 OFL 许可），2026-09-13 备份入库，
作为基础素材保存——线上产物用的是由这些源文件生成的子集（`assets/fonts/*.woff2`），源文件不参与构建。

| 文件 | 字体 | 用途 | 许可 |
|------|------|------|------|
| NotoSansSC-VF.ttf | Noto Sans SC（思源黑体，可变字重 100–900） | 中文标题（700/900 子集）与正文（300 Light 子集，`tools/fetch_fonts.py` 生成） | OFL |
| Fraunces-VF.ttf | Fraunces（可变） | 展示衬线：巨字、年份、引言（600 子集） | OFL |
| Inter-VF.ttf | Inter（可变） | 正文/UI 西文（400/600 子集） | OFL |
| IBMPlexMono-Regular.ttf / SemiBold.ttf | IBM Plex Mono | 数据/编号/图注（400/600 子集） | OFL |
| Outfit-VF.ttf | Outfit（可变） | 标题西文/数字（100–900 可变子集） | OFL |

- 来源：https://github.com/google/fonts （`ofl/` 目录各字体官方仓库）
- 子集重新生成：标题类走 `tools/fetch_fonts.py`（Google Fonts 子集接口）；正文中文 Light 子集
  由本目录的 NotoSansSC-VF.ttf 实例化 + fontTools 按**全站用字**（从 dist 产物抽取）生成，随
  `tools/fetch_fonts.py` 一并执行。
- 全站用字变化（新增文案/数据）后需重跑字体子集，否则缺字回退系统字体会造成字重不匀。

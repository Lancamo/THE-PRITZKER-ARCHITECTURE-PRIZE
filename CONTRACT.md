# V2.0 接口契约（冻结）

对应《2026-09-12_普利兹克奖可视化V2.0_开发文档_codebuddy+Kimi.md》第 1.5 节。Phase 1 起冻结，变更由集成官发起。

## 数据注入

构建期把 `editions.json / laureates.json / meta.json / geo.json` 合并注入为 `window.__DATA__`：

```
__DATA__ = { editions, dossiers, bands, lineage, trivia, geo }
```

## store API（NS.store）

| 方法 | 返回 |
|---|---|
| `init(data)` | 解析并派生全部索引 |
| `editions()` | 按年份升序的届次数组 |
| `edition(year)` | 单届；`dossier(year)` 合并详情（含 `full:boolean` 标记是否样板） |
| `countries()` | `[{name,en,region,count}]` 人数降序（图A） |
| `regions()` | `[{id,cn,en,count}]`（图例与缝） |
| `places()` | `[{country,count,lat,lng,items:[{year,title_cn,city}]}]`（图B） |
| `stats()` | `{editions,people,countries,ageMin,ageMax,youngest,oldest}` |
| `bands()` / `lineage()` / `trivia()` | 来自 meta |
| `bandOf(year)` | 该届流派标签 |
| `hitsOf(sel)` | 某选中项命中的届次年份集合（供各视图统一判定） |
| `windowOf(year)` | 该届 ±5 年的悬停窗口届次数组（国籍图 / 地理图联动用） |
| `get()/set(patch)/on(evt,fn)/off(evt,fn)` | 状态与事件 |

## 状态与事件

```
state = { selection: {type:'country'|'place'|'year', value}|null,
          hover: 同上|null,
          layer: 'none'|'lineage'|'age',
          route: 'home'|'detail', routeYear: number|null }
事件：selection:change / hover:change / layer:change / route:change
```

选中规范：hover=预览（其余 40%）；click=锁定（命中 100% + 放大，其余 12%）；再点/ESC/空白解除。
悬停时间轴某届 = 预览「该届 ±5 年」的十年窗口：时间轴按窗口深浅展开，国籍图与地理图同步点亮
窗口内涉及的全部国家 / 作品所在地（`windowOf`）。

## CSS

- 只用 `tokens.css` 变量；类名前缀 `.tl- .cna- .cge- .ins- .dt- .tr-`，共享 `.ui-`；直角 ≤2px、1px hairline、菱形标记；
- 透明度阶梯 `--op-100/70/45/25/12`；缓动/时长用 `--ease/--dur-mic/--dur-blk/--dur-pg`。

## DOM 挂载点

`#hero #hero-stats #hero-quote #timeline-sec #tl #tl-arcs #tl-bands #btn-lineage #btn-age #chart-nations #chart-geo #cna-status #cge-status #insights-sec #age-chart #trivia #foot #detail`

## JS

原生 ES2020，每个文件一个 IIFE，出口 `window.NS.<module>`；字符串渲染一律 `NS.util.esc()`；禁控制台输出。

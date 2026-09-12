/* chart-nations.js · D 图表官 · 图A：得主国籍分布（灰阶 voronoi treemap）
   依赖：store / util / vendor(d3)
   监听：selection:change / hover:change · 发布：经 store（hover/selection） */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util, S = NS.store;

  var bodyEl, svgEl, statusEl, tipEl, legendEl;
  var cellByCountry = {}, cellEls = [], hlByRegion = {};
  var size = 0;

  /* 大洲灰阶：人数最多的大洲最深，洲内国家共用同一基准色调（整块感），
     国家小块仅以 ±0.045 的微小明度抖动区分彼此 */
  var REGION_TONES = [0.86, 0.66, 0.5, 0.38, 0.29, 0.21];
  var toneOfRegion = {};

  function assignTones() {
    var sorted = S.regions().slice().sort(function (a, b) { return b.count - a.count; });
    toneOfRegion = {};
    sorted.forEach(function (g, i) { toneOfRegion[g.id] = REGION_TONES[Math.min(i, REGION_TONES.length - 1)]; });
  }

  /* 右侧地理图的渲染高度（两者等高） */
  function geoHeight() {
    var el = document.getElementById("chart-geo");
    var h = el ? el.clientHeight : 0;
    return h > 160 ? h : 400;
  }

  function alphaOf(count, max, region) {
    var base = toneOfRegion[region] != null ? toneOfRegion[region] : 0.5;
    var jitter = (Math.sqrt(count / max) - 0.5) * 0.09;
    return U.clampNum(base + jitter, 0.12, 0.92).toFixed(3);
  }

  function render() {
    var w = bodyEl.clientWidth;   /* 图例已移出本容器，宽度全归圆形 */
    if (!w || w < 180) return;
    size = Math.min(w, bodyEl.clientHeight > 0 ? bodyEl.clientHeight : geoHeight());
    var r = size / 2;

    var svg = d3.select(svgEl)
      .attr("viewBox", "0 0 " + size + " " + size)
      .attr("width", size).attr("height", size);
    svg.selectAll("*").remove();
    cellByCountry = {}; cellEls = [];

    var countries = S.countries();
    var maxCount = countries.reduce(function (a, c) { return Math.max(a, c.count); }, 1);
    assignTones();

    /* 两层：大洲 → 国家，同一大洲占一整片连续区域 */
    var root = d3.hierarchy({
      children: S.regions().map(function (g) {
        return {
          name: g.id,
          children: countries.filter(function (c) { return c.region === g.id; })
            .map(function (c) { return { name: c.name, en: c.en, value: c.count, region: c.region }; })
        };
      })
    }).sum(function (d) { return d.value || 0; });

    var clip = [], N = 240;
    for (var i = 0; i < N; i++) {
      var t = (i / N) * Math.PI * 2;
      clip.push([r + Math.cos(t) * r, r + Math.sin(t) * r]);
    }
    d3.voronoiTreemap().clip(clip).maxIterationCount(90).convergenceRatio(0.006)(root);

    var g = svg.append("g");

    /* 大洲底色（极浅）：洲内整块的基底 */
    root.children.forEach(function (rn) {
      if (!rn.polygon || rn.polygon.length < 3) return;
      g.append("polygon")
        .attr("class", "cna-region")
        .attr("points", rn.polygon.map(toPt).join(" "))
        .attr("fill", "rgba(10,10,10,0.05)")
        .attr("stroke", "none");
    });

    var leaves = root.leaves().filter(function (d) { return d.polygon && d.polygon.length > 2; });

    leaves.forEach(function (d) {
      var a = alphaOf(d.data.value, maxCount, d.data.region);
      var cell = g.append("g").attr("class", "cna-cell")
        .attr("data-country", d.data.name)
        .attr("data-region", d.data.region)
        .attr("tabindex", 0).attr("role", "button")
        .attr("aria-label", d.data.name + " " + d.data.en + " " + d.data.value + " 位");
      cell.append("polygon")
        .attr("points", d.polygon.map(toPt).join(" "))
        .attr("fill", "rgba(10,10,10," + a + ")")
        .attr("stroke", "#E8E8E8")
        .attr("stroke-width", 1)
        .attr("stroke-linejoin", "round");
      cellByCountry[d.data.name] = cell.node();
      cellEls.push(cell.node());

      /* 标注：名字 + 人数 */
      var c = d3.polygonCentroid(d.polygon);
      var inner = Infinity;
      for (var i = 0; i < d.polygon.length; i++) {
        var p1 = d.polygon[i], p2 = d.polygon[(i + 1) % d.polygon.length];
        inner = Math.min(inner, distToSegment(c, p1, p2));
      }
      if (inner < 9) return;
      var fill = parseFloat(a) > 0.45 ? "#E8E8E8" : "#0A0A0A";
      var cn = d.data.name;
      var en = d.data.en || "";
      /* 中文行按列宽收字，英文行再按自身长度收紧（等宽字宽约 0.6em） */
      var sizeCn = Math.min(U.clampNum(inner * 0.34, 6.5, 13), inner * 2.24 / Math.max(1, cn.length));
      var sizeEn = Math.min(U.clampNum(sizeCn * 0.78, 5.5, 10), inner * 2.24 / Math.max(1, en.length * 0.62));
      var rows = [{ t: cn, s: sizeCn, o: 1 }];
      if (en && inner >= 13) rows.push({ t: en, s: sizeEn, o: 0.74 });
      if (inner >= 27) rows.push({ t: String(d.data.value), s: sizeCn * 0.78, o: 0.6 });

      var total = rows.reduce(function (sum, r) { return sum + r.s * 1.3; }, 0);
      var y = c[1] - total / 2;
      rows.forEach(function (r) {
        y += r.s * 0.95;
        g.append("text").attr("class", "cna-label")
          .attr("x", c[0]).attr("y", y.toFixed(1))
          .attr("font-size", r.s.toFixed(1)).attr("fill", fill)
          .attr("opacity", r.o)
          .text(r.t);
        y += r.s * 0.35;
      });
    });

    /* 大洲之间的白色分隔（压在国家小块之上，形成真正的宽缝） */
    root.children.forEach(function (rn) {
      if (!rn.polygon || rn.polygon.length < 3) return;
      g.append("polygon")
        .attr("class", "cna-seam")
        .attr("points", rn.polygon.map(toPt).join(" "))
        .attr("fill", "none")
        .attr("stroke", "#E8E8E8")
        .attr("stroke-width", 5)
        .attr("stroke-linejoin", "round")
        .attr("pointer-events", "none");
    });

    /* 大洲轮廓（选中/悬停时显墨色描边，避免灰阶相近难以辨识） */
    hlByRegion = {};
    root.children.forEach(function (rn) {
      if (!rn.polygon || rn.polygon.length < 3) return;
      hlByRegion[rn.data.name] = g.append("polygon")
        .attr("class", "cna-region-hl")
        .attr("data-region", rn.data.name)
        .attr("points", rn.polygon.map(toPt).join(" "))
        .node();
    });

    /* 交互 */
    svgEl.onmouseover = function (ev) {
      var cell = ev.target.closest(".cna-cell");
      if (!cell) return;
      S.set({ hover: { type: "country", value: cell.dataset.country } });
      showTip(cell.dataset.country, +cell.dataset.region ? 0 : 0, ev);
    };
    svgEl.onmousemove = function (ev) {
      if (tipEl.classList.contains("on")) positionTip(ev);
    };
    svgEl.onmouseout = function (ev) {
      if (!ev.relatedTarget || !svgEl.contains(ev.relatedTarget)) {
        hideTip();
        var st = S.get();
        if (st.hover && st.hover.type === "country") S.set({ hover: null });
      }
    };
    svgEl.onclick = function (ev) {
      var cell = ev.target.closest(".cna-cell");
      if (!cell) return;
      S.toggleSelection({ type: "country", value: cell.dataset.country });
    };
    svgEl.onkeydown = function (ev) {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      var cell = ev.target.closest(".cna-cell");
      if (!cell) return;
      ev.preventDefault();
      S.toggleSelection({ type: "country", value: cell.dataset.country });
    };

    applyStates();
  }

  function showTip(country, _n, ev) {
    var c = S.countries().filter(function (x) { return x.name === country; })[0];
    if (!c) return;
    tipEl.innerHTML = U.esc(c.name) + " · " + c.count + " 位<span class='tip-en'>" + U.esc(c.en) + " · " + U.esc(S.regionLabel(c.region)) + "</span>";
    tipEl.classList.add("on");
    positionTip(ev);
  }
  function positionTip(ev) {
    var box = bodyEl.getBoundingClientRect();
    tipEl.style.left = (ev.clientX - box.left) + "px";
    tipEl.style.top = (ev.clientY - box.top - 6) + "px";
  }
  function hideTip() { tipEl.classList.remove("on"); }

  function applyStates() {
    var st = S.get();
    var active = st.selection || st.hover;
    var mode = st.selection ? "sel" : (st.hover ? "hov" : "");
    cellEls.forEach(function (cell) {
      var name = cell.dataset.country;
      var hit = false;
      if (active) {
        if (active.type === "country" || active.type === "place") hit = name === active.value;
        else if (active.type === "region") hit = cell.dataset.region === active.value;
        else if (active.type === "year") {
          /* 悬停时间轴某届：按「该届 ±5 年」的十年窗口命中（与时间轴窗口一致） */
          hit = S.windowOf(active.value).some(function (e) {
            return S.countriesOfYear(e.year).indexOf(name) !== -1;
          });
        }
      }
      cell.classList.toggle("is-hit", !!(active && hit));
      cell.classList.toggle("is-dim", !!(active && !hit && mode === "sel"));
      cell.classList.toggle("is-preview-dim", !!(active && !hit && mode === "hov"));
    });
    var hotRegion = active && active.type === "region" ? active.value : null;
    /* 仅南美 / 非洲 / 大洋洲保留轮廓（其余大洲块面本身清晰，加边反而显重） */
    var HL_REGIONS = { sa: 1, africa: 1, oceania: 1 };
    Object.keys(hlByRegion).forEach(function (rid) {
      hlByRegion[rid].classList.toggle("on", rid === hotRegion && !!HL_REGIONS[rid]);
    });
    syncLegend();
    if (active && active.type === "country") updateStatus(U.esc(active.value), S.hitsOf(active));
    else if (active && active.type === "region") updateStatus(U.esc(S.regionLabel(active.value)), S.hitsOf(active));
    else updateStatus(null);
  }

  function updateStatus(label, hits) {
    if (!label) {
      statusEl.innerHTML = "";   /* 无选中时留空——位置已让给横排图例 */
      return;
    }
    statusEl.innerHTML = "已选 <b>" + label + "</b> · " + Object.keys(hits).length + " / " + S.editions().length + " 届 <span class='tip-en'>Filtered</span>";
  }

  /* ---------- 大洲图例（点击一次性选中该洲全部国家） ---------- */
  function buildLegend() {
    legendEl.innerHTML = "";
    var all = document.createElement("button");
    all.type = "button";
    all.className = "cna-legend-item";
    all.dataset.region = "";
    all.innerHTML = "<i style='--tone:rgba(10,10,10,.08)'></i><b>全部</b><span>All</span><span class='cnt'>" +
      S.editions().length + " 届</span>";
    all.addEventListener("click", function () { S.clearSelection(); });
    legendEl.appendChild(all);

    S.regions().slice().sort(function (a, b) { return b.count - a.count; }).forEach(function (g) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cna-legend-item";
      b.dataset.region = g.id;
      var tone = toneOfRegion[g.id] != null ? toneOfRegion[g.id] : 0.5;
      b.innerHTML = "<i style='--tone:rgba(10,10,10," + tone + ")'></i><b>" + U.esc(g.cn) + "</b><span>" +
        U.esc(g.en) + "</span><span class='cnt'>" + g.count + "</span>";
      b.addEventListener("click", function () { S.toggleSelection({ type: "region", value: g.id }); });
      legendEl.appendChild(b);
    });
    syncLegend();
  }

  function syncLegend() {
    if (!legendEl) return;
    var sel = S.get().selection;
    Array.prototype.forEach.call(legendEl.children, function (b) {
      var on = sel ? (sel.type === "region" && sel.value === b.dataset.region) : b.dataset.region === "";
      b.setAttribute("aria-pressed", String(on));
    });
  }

  function toPt(p) { return p[0].toFixed(2) + "," + p[1].toFixed(2); }
  function distToSegment(p, a, b) {
    var dx = b[0] - a[0], dy = b[1] - a[1];
    var len2 = dx * dx + dy * dy;
    if (len2 === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
    var t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
  }

  NS.chartNations = {
    init: function () {
      bodyEl = document.getElementById("chart-nations");
      statusEl = document.getElementById("cna-status");
      svgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svgEl.setAttribute("role", "img");
      svgEl.setAttribute("aria-label", "历届得主国籍分布，面积正比于人数");
      bodyEl.appendChild(svgEl);
      legendEl = document.createElement("div");
      legendEl.className = "cna-legend";
      /* 插到状态行之前：横排在图下方，取代原来那句固定文案 */
      statusEl.parentNode.insertBefore(legendEl, statusEl);
      tipEl = document.createElement("div");
      tipEl.className = "ui-tip";
      bodyEl.appendChild(tipEl);

      assignTones();
      buildLegend();
      render();
      S.on("selection:change", applyStates);
      S.on("hover:change", applyStates);
      window.addEventListener("resize", U.debounce(render, 220));
    }
  };
})();

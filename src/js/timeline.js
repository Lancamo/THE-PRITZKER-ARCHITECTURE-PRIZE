/* timeline.js · C 时间轴官 · 时间轴总览（总览/聚焦两态 + 流派底带 + 谱系弧线 + 年龄模式）
   依赖：store / util
   监听：selection:change / hover:change / layer:change · 发布：经 store.set（hover/selection/route） */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util, S = NS.store;

  var tlEl, arcsEl, wrapEl, groupEls = [], itemEls = [];
  var winRange = null;   /* 当前聚焦窗口 [lo, hi]；师承图层据此强调连线 */
  var pointerIn = false; /* 指针是否在时间轴内：师承图层据此决定「全亮」还是「按窗口」 */
  var AGE_MIN = 44, AGE_MAX = 91, AGE_SPAN = 96; // 年龄模式的纵向展开幅度（px）
  var ABOVE_H = 138, NODE_H = 36; // 与 home.css 的 --above-h / --node-h 保持一致

  /* 年龄模式：横向虚线刻度（50—90 岁），替代原独立散点图 */
  function buildAgeGrid() {
    var grid = document.getElementById("tl-agegrid");
    if (!grid) return;
    var center = ABOVE_H + NODE_H / 2;
    [50, 60, 70, 80, 90].forEach(function (a) {
      var dy = -(a - AGE_MIN) / (AGE_MAX - AGE_MIN) * AGE_SPAN;
      var d = document.createElement("div");
      d.className = "gl";
      d.style.top = (center + dy).toFixed(1) + "px";
      d.innerHTML = "<span>" + a + " 岁</span>";
      grid.appendChild(d);
    });
  }

  function build() {
    var editions = S.editions();
    var bands = S.bands();
    var bandOfEdition = {};
    bands.forEach(function (b) {
      editions.forEach(function (e) { if (e.year >= b.from && e.year <= b.to) bandOfEdition[e.year] = b; });
    });

    var frag = document.createDocumentFragment();
    var curBand = null, curGroup = null, curItems = null;

    editions.forEach(function (ed) {
      var band = bandOfEdition[ed.year] || { cn: "", en: "", from: ed.year, to: ed.year };
      if (!curBand || curBand.from !== band.from) {
        curBand = band;
        curGroup = document.createElement("li");
        curGroup.className = "tl-group";
        curGroup.dataset.from = band.from;
        curGroup.dataset.to = band.to;
        curItems = document.createElement("ol");
        curItems.className = "tl-group-items";
        curItems.style.cssText = "display:flex;flex:1 1 0;min-width:0;margin:0;padding:0;list-style:none;";
        curGroup.appendChild(curItems);
        frag.appendChild(curGroup);
        groupEls.push(curGroup);
      }

      var countries = [];
      var workCountries = [];
      ed.laureates.forEach(function (l) { countries = countries.concat(l.nationalities); });
      ed.works.forEach(function (w) { workCountries.push(w.country); });
      countries = U.uniq(countries);

      var li = document.createElement("li");
      li.className = "tl-item";
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      li.setAttribute("aria-label", ed.year + " 届 · " +
        ed.laureates.map(function (l) { return l.name_cn; }).join(" / ") + " · 进入时间轴档案");
      li.dataset.year = ed.year;
      li.dataset.countries = countries.join("|");
      li.dataset.works = U.uniq(workCountries).join("|");
      li.dataset.decade = ed.year % 10 === 0 ? "1" : "0";
      li.dataset.names = String(ed.laureates.length);   /* 供 CSS 收紧多人年份的间距 */

      var above = document.createElement("div");
      above.className = "tl-above";
      if (ed.works[0]) {
        var wk = document.createElement("span");
        wk.className = "tl-work";
        wk.textContent = ed.works[0].title_cn;
        above.appendChild(wk);
      }

      var node = document.createElement("div");
      node.className = "tl-node";
      var dia = document.createElement("span");
      dia.className = "tl-diamond";
      dia.innerHTML = "<i></i>";
      node.appendChild(dia);
      var ageLbl = document.createElement("span");
      ageLbl.className = "tl-age";
      ageLbl.textContent = avgAge(ed) != null ? avgAge(ed) : "";
      node.appendChild(ageLbl);

      var yr = document.createElement("div");
      yr.className = "tl-year";
      yr.textContent = ed.year;

      var below = document.createElement("div");
      below.className = "tl-below";
      ed.laureates.forEach(function (l) {
        var n = document.createElement("span");
        n.className = "tl-name";
        n.textContent = l.name_cn;
        below.appendChild(n);
      });

      li.appendChild(above);
      li.appendChild(node);
      li.appendChild(yr);
      li.appendChild(below);
      curItems.appendChild(li);
      itemEls.push(li);

      /* 年龄模式：节点纵向偏移（多人取均值） */
      var age = avgAge(ed);
      if (age != null) {
        var t = (age - AGE_MIN) / (AGE_MAX - AGE_MIN);
        li.style.setProperty("--dy", (-t * AGE_SPAN).toFixed(1) + "px");
      }
    });

    tlEl.appendChild(frag);
  }

  function avgAge(ed) {
    var ages = ed.laureates.map(function (l) { return l.age_at_award; }).filter(function (a) { return a != null; });
    if (!ages.length) return null;
    return Math.round(ages.reduce(function (a, b) { return a + b; }, 0) / ages.length);
  }

  /* 字号统一由 CSS 控制（姓名 10px / 代表作 8px），全站一致，不再按段自适应 */

  /* ---------- 谱系弧线 ---------- */
  /* 绘制师承连线。lo/hi 为当前聚焦窗口（null = 不强调）——
     只要连线任一端落在窗口内就加深 */
  function drawArcs(lo, hi) {
    var wr = wrapEl.getBoundingClientRect();
    arcsEl.setAttribute("viewBox", "0 0 " + wr.width + " " + wr.height);
    arcsEl.setAttribute("width", wr.width);
    arcsEl.setAttribute("height", wr.height);
    while (arcsEl.firstChild) arcsEl.removeChild(arcsEl.firstChild);

    var pos = {};
    itemEls.forEach(function (it) {
      var r = it.querySelector(".tl-node").getBoundingClientRect();
      pos[it.dataset.year] = {
        x: r.left - wr.left + r.width / 2,
        y: r.top - wr.top + r.height / 2
      };
    });
    S.lineage().forEach(function (L) {
      var a = pos[L.from], b = pos[L.to];
      if (!a || !b) return;
      var y0 = a.y - 4;
      var h = U.clampNum(34 + Math.abs(b.x - a.x) * 0.11, 40, 132);
      var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.dataset.from = L.from; g.dataset.to = L.to;
      if (lo != null && ((+L.from >= lo && +L.from <= hi) || (+L.to >= lo && +L.to <= hi))) {
        g.setAttribute("class", "is-hot");
      }
      var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", "M" + a.x.toFixed(1) + "," + y0.toFixed(1) +
        " C" + a.x.toFixed(1) + "," + (y0 - h).toFixed(1) + " " + b.x.toFixed(1) + "," + (y0 - h).toFixed(1) + " " + b.x.toFixed(1) + "," + y0.toFixed(1));
      var t = document.createElementNS("http://www.w3.org/2000/svg", "title");
      t.textContent = L.cn;
      g.appendChild(p); g.appendChild(t);
      arcsEl.appendChild(g);
    });
  }

  /* ---------- 选中/悬停状态 ---------- */
  function applyStates() {
    var st = S.get();
    var active = st.selection || st.hover;
    var mode = st.selection ? "sel" : (st.hover ? "hov" : "");
    document.body.setAttribute("data-mode", mode);

    var hits = S.hitsOf(active);
    var exactYear = st.selection && st.selection.type === "year" ? st.selection.value : null;

    itemEls.forEach(function (it) {
      var hit = !!hits[it.dataset.year];
      it.classList.toggle("is-hit", hit);
      it.classList.toggle("is-sel", exactYear != null && +it.dataset.year === exactYear);
    });
    applyLineage();
  }

  /* 师承图层：指针未移入时点亮全部师承相关届次；移入后改为按十年窗口强调——
     窗口内届次的连线加深，连线「另一端」的届次一并点亮 */
  function applyLineage() {
    var layerOn = S.get().layer === "lineage";
    var ends = {};
    var lo = null, hi = null;
    if (layerOn && winRange) {
      if (pointerIn) {
        lo = winRange[0]; hi = winRange[1];
        S.lineage().forEach(function (L) {
          var a = +L.from, b = +L.to;
          var aIn = a >= lo && a <= hi, bIn = b >= lo && b <= hi;
          if (aIn !== bIn) ends[aIn ? b : a] = 1;   /* 只标「另一端」 */
        });
      } else {
        /* 指针不在轴上：所有师承相关的届次与连线一律点亮 */
        S.lineage().forEach(function (L) { ends[+L.from] = 1; ends[+L.to] = 1; });
        lo = -Infinity; hi = Infinity;
      }
    }
    itemEls.forEach(function (it) {
      it.classList.toggle("is-lin-end", !!ends[+it.dataset.year]);
    });
    drawArcs(lo, hi);
  }

  NS.timeline = {
    init: function () {
      tlEl = document.getElementById("tl");
      arcsEl = document.getElementById("tl-arcs");
      wrapEl = document.getElementById("tl-wrap");

      build();
      buildAgeGrid();
      requestAnimationFrame(function () { drawArcs(null); });

      /* 聚焦态：默认展开最近十年；悬停某届时，以该届为基准左右各 5 年（共 11 届）构成聚焦窗口，
         窗口内显示代表作、窗口外轻淡；移开恢复默认十年。保留"悬停显示十年"的交互。 */
      var _edAll = S.editions();
      var _last = _edAll.slice(-10).map(function (e) { return e.year; });
      var defaultLo = Math.min.apply(null, _last), defaultHi = Math.max.apply(null, _last);
      /* suppress=true：图表侧在选中/预览时调用——收起窗口，只留命中的届次高亮，
         否则默认的「最近十年」会和图表命中的届次两套高亮叠加 */
      function applyWindow(center, suppress) {
        var lo, hi, active;
        if (center == null) { lo = defaultLo; hi = defaultHi; active = false; }
        else { lo = center - 5; hi = center + 5; active = true; }
        itemEls.forEach(function (it) {
          var y = +it.dataset.year;
          var on = !suppress && y >= lo && y <= hi;
          it.classList.toggle("is-win", on);
          /* 由悬停届向两侧渐隐，最外侧一档 50%——窗口边界不再一刀切 */
          var op = (active && on) ? 1 - (Math.abs(y - center) / 5) * 0.5 : 1;
          it.style.setProperty("--win-op", op.toFixed(3));
        });
        tlEl.classList.toggle("is-windowing", active && !suppress);
        winRange = suppress ? null : [lo, hi];
        applyLineage();
      }

      /* 图表侧选中/预览（国家、大洲、点位）时收起窗口；清空后再恢复默认十年 */
      function syncWindowWithCharts() {
        var act = S.get().selection || S.get().hover;
        if (act && act.type !== "year") {
          hoverYear = null;
          applyWindow(null, true);
        } else if (!act) {
          applyWindow(null);
        }
      }
      S.on("selection:change", syncWindowWithCharts);
      S.on("hover:change", syncWindowWithCharts);
      applyWindow(null);

      /* 节点：悬停聚焦窗口 / 预览 / 点击进档案 */
      itemEls.forEach(function (it) {
        function win() { applyWindow(+it.dataset.year); }
        function winOff() { applyWindow(null); }
        it.addEventListener("focus", win);
        it.addEventListener("blur", winOff);
        it.addEventListener("click", function (ev) {
          ev.stopPropagation();
          var dia = it.querySelector(".tl-diamond");
          NS.router.goArchive(+it.dataset.year, dia);   /* 节点 → 时间轴档案（定位到该届） */
        });
        it.addEventListener("keydown", function (ev) {
          if (ev.key !== "Enter" && ev.key !== " ") return;
          ev.preventDefault();
          NS.router.goArchive(+it.dataset.year, it.querySelector(".tl-diamond"));
        });
      });

      /* 窗口跟随指针：在容器上按指针所在届统一判定。
         不用逐条 mouseenter/mouseleave——相邻条目各自的 leave 会把窗口重置回默认十年，
         跨十年分组的接缝处指针还会落空（命中 .tl-group 而非条目），表现为「移动时不跟随」 */
      var hoverYear = null;
      function pointYear(ev) {
        var item = ev.target && ev.target.closest ? ev.target.closest(".tl-item") : null;
        return item ? +item.dataset.year : null;
      }
      tlEl.addEventListener("mousemove", function (ev) {
        var y = pointYear(ev);
        if (y == null || y === hoverYear) return;   /* 落在接缝上时保持当前窗口，不回退 */
        hoverYear = y;
        applyWindow(y);
        S.set({ hover: { type: "year", value: y } });
      });
      tlEl.addEventListener("mouseenter", function () {
        pointerIn = true;
        applyLineage();
      });
      tlEl.addEventListener("mouseleave", function () {
        pointerIn = false;
        if (hoverYear == null) {
          applyLineage();
          return;
        }
        hoverYear = null;
        applyWindow(null);
        var h = S.get().hover;
        if (h && h.type === "year") S.set({ hover: null });
      });

      /* 图层开关 */
      var btnLineage = document.getElementById("btn-lineage");
      var btnAge = document.getElementById("btn-age");
      btnLineage.addEventListener("click", function () {
        var on = S.get().layer === "lineage";
        S.set({ layer: on ? "none" : "lineage" });
      });
      btnAge.addEventListener("click", function () {
        var on = S.get().layer === "age";
        S.set({ layer: on ? "none" : "age" });
      });
      S.on("layer:change", function (layer) {
        wrapEl.setAttribute("data-layer", layer);
        btnLineage.setAttribute("aria-pressed", String(layer === "lineage"));
        btnAge.setAttribute("aria-pressed", String(layer === "age"));
        if (layer === "lineage") requestAnimationFrame(applyLineage);
      });
      wrapEl.setAttribute("data-layer", "none");

      S.on("selection:change", applyStates);
      S.on("hover:change", applyStates);

      var redraw = U.debounce(function () { applyLineage(); }, 180);
      window.addEventListener("resize", redraw);
      applyStates();

      /* 默认聚焦窗口已在上面 applyWindow(null) 中建立，无需再次点亮 */
    }
  };
})();

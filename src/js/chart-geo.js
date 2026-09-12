/* chart-geo.js · D 图表官 · 图B：代表作地理分布（灰阶世界点图）
   依赖：store / util / data.geo
   监听：selection:change / hover:change · 发布：经 store（hover/selection） */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util, S = NS.store;

  var VIEW_W = 1000, VIEW_H = 470;
  var LAT_TOP = 84, LAT_BOTTOM = -58;

  var bodyEl, svgEl, statusEl, tipEl;
  var dotEls = [], dotByCountry = {};

  function px(lng) { return (lng + 180) / 360 * VIEW_W; }
  function py(lat) { return (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * VIEW_H; }

  function render() {
    if (!NS.vendor || !NS.vendor.geo) return;
    var land = NS.vendor.geo.land || [];

    var svg = d3.select(svgEl)
      .attr("viewBox", "0 0 " + VIEW_W + " " + VIEW_H);
    svg.selectAll("*").remove();
    dotEls = []; dotByCountry = {};

    /* 陆地剪影：同色填充、无描边 */
    var path = "";
    land.forEach(function (ring) {
      ring.forEach(function (p, i) {
        path += (i === 0 ? "M" : "L") + px(p[0]).toFixed(0) + " " + py(p[1]).toFixed(0);
      });
      path += "Z";
    });
    svg.append("path").attr("class", "cge-land").attr("d", path);

    /* 作品点：菱形，大小 ∝ 件数 */
    var places = S.places();
    places.forEach(function (p) {
      var x = px(p.lng), y = py(p.lat);
      var k = (0.9 + Math.min(p.count, 8) * 0.28).toFixed(2);
      var g = svg.append("g")
        .attr("class", "cge-dot")
        .attr("transform", "translate(" + x.toFixed(1) + "," + y.toFixed(1) + ")")
        .attr("data-country", p.country)
        .attr("tabindex", 0).attr("role", "button")
        .attr("aria-label", p.country + " " + p.count + " 件代表作");
      g.append("polygon")
        .attr("points", "-5,-5 5,-5 5,5 -5,5")
        .attr("transform", "rotate(45) scale(" + k + ")")
        .attr("fill", "rgba(10,10,10,0.85)");
      g.append("title").text(p.country + " · " + p.count + " 件");
      dotByCountry[p.country] = g.node();
      dotEls.push(g.node());

      if (p.count >= 2) {
        svg.append("text").attr("class", "cge-name")
          .attr("x", x).attr("y", y - 16 - (k - 1) * 6)
          .text(p.country);
      }
    });

    /* 交互 */
    svgEl.onmouseover = function (ev) {
      var dot = ev.target.closest(".cge-dot");
      if (!dot) return;
      S.set({ hover: { type: "place", value: dot.dataset.country } });
      showTip(dot.dataset.country, ev);
    };
    svgEl.onmousemove = function (ev) {
      if (tipEl.classList.contains("on")) positionTip(ev);
    };
    svgEl.onmouseout = function (ev) {
      if (!ev.relatedTarget || !svgEl.contains(ev.relatedTarget)) {
        hideTip();
        var st = S.get();
        if (st.hover && st.hover.type === "place") S.set({ hover: null });
      }
    };
    svgEl.onclick = function (ev) {
      var dot = ev.target.closest(".cge-dot");
      if (!dot) return;
      S.toggleSelection({ type: "place", value: dot.dataset.country });
    };
    svgEl.onkeydown = function (ev) {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      var dot = ev.target.closest(".cge-dot");
      if (!dot) return;
      ev.preventDefault();
      S.toggleSelection({ type: "place", value: dot.dataset.country });
    };

    applyStates();
  }

  function showTip(country, ev) {
    var p = S.places().filter(function (x) { return x.country === country; })[0];
    if (!p) return;
    var lines = p.items.slice(0, 5).map(function (it) {
      return it.year + " " + it.title_cn;
    }).join("<br>");
    tipEl.innerHTML = "<b>" + U.esc(p.country) + "</b> · " + p.count + " 件<span class='tip-en'>" +
      lines + "</span>";
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
    dotEls.forEach(function (dot) {
      var country = dot.dataset.country;
      var hit = false;
      if (active) {
        if (active.type === "place" || active.type === "country") hit = country === active.value;
        else if (active.type === "region") hit = S.regionsOf(country) === active.value;
        else if (active.type === "year") {
          /* 悬停时间轴某届：按「该届 ±5 年」的十年窗口命中（与时间轴窗口一致） */
          hit = S.windowOf(active.value).some(function (e) {
            return e.works.some(function (w) { return w.country === country; });
          });
        }
      }
      dot.classList.toggle("is-hit", !!(active && hit));
      dot.classList.toggle("is-dim", !!(active && !hit && mode === "sel"));
      dot.classList.toggle("is-preview-dim", !!(active && !hit && mode === "hov"));
    });
    /* 只报本图自己的选中（place）；国家/大洲由国籍图的状态负责，避免同一行出现两遍 */
    if (active && active.type === "place") updateStatus(U.esc(active.value), S.hitsOf(active));
    else updateStatus(null);
  }

  function updateStatus(label, hits) {
    if (!label) {
      statusEl.innerHTML = "";
      return;
    }
    statusEl.innerHTML = "已选 <b>" + label + "</b> · " + Object.keys(hits).length + " / " + S.editions().length + " 届 <span class='tip-en'>Filtered</span>";
  }

  NS.chartGeo = {
    init: function () {
      bodyEl = document.getElementById("chart-geo");
      statusEl = document.getElementById("cge-status");
      svgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svgEl.setAttribute("role", "img");
      svgEl.setAttribute("aria-label", "历届代表作地理分布");
      svgEl.style.width = "100%";
      svgEl.style.height = "100%";
      /* meet：整幅世界完整落在容器内（slice 会裁掉东西两侧的大洲） */
      svgEl.setAttribute("preserveAspectRatio", "xMidYMid meet");
      bodyEl.appendChild(svgEl);
      tipEl = document.createElement("div");
      tipEl.className = "ui-tip";
      bodyEl.appendChild(tipEl);

      render();
      S.on("selection:change", applyStates);
      S.on("hover:change", applyStates);
      window.addEventListener("resize", U.debounce(render, 220));
    }
  };
})();

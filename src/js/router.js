/* router.js · F 集成官 · hash 路由（主页 / 时间轴档案 / 单届全档）+ 选中状态 URL 同步
   依赖：store / transition / archive
   监听：无 · 发布：无（经 store.set 触发 route:change） */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var S = NS.store;

  var pendingSource = null; // 点击节点时的来源元素（供过渡 morph）

  function parse(hash) {
    var h = hash || "";
    var m = /^#\/laureate\/(\d{4})/.exec(h);
    if (m) return { route: "detail", year: parseInt(m[1], 10) };
    var t = /^#\/timeline(?:\/(\d{4}))?/.exec(h);
    if (t) return { route: "archive", year: t[1] ? parseInt(t[1], 10) : null };
    return { route: "home", year: null };
  }

  function apply() {
    var r = parse(location.hash);
    var cur = S.get();

    if (r.route === "detail") {
      NS.archive.close(true);
      if (cur.route !== "detail" || cur.routeYear !== r.year) {
        NS.transition.open(r.year, pendingSource);
        pendingSource = null;
      }
    } else if (r.route === "archive") {
      if (cur.route === "detail") NS.transition.close(true);
      NS.archive.open(r.year);
    } else {
      if (cur.route === "detail") NS.transition.close();
      else NS.archive.close();
    }

    S.set({ route: r.route, routeYear: r.year });

    if (r.route === "home") {
      /* 还原筛选（若有） */
      var sm = /[?&]s=([a-z]+)\|([^&]+)/.exec(location.hash || "");
      if (sm) {
        var val = decodeURIComponent(sm[2]);
        if (isNaN(Number(val))) { /* 中文国家名 */ }
        else val = Number(val);
        S.set({ selection: { type: sm[1], value: val } });
      }
    }
  }

  NS.router = {
    init: function () {
      window.addEventListener("hashchange", apply);
      apply();
    },
    /* 进入单届全档 */
    go: function (year, sourceEl) {
      pendingSource = sourceEl || null;
      location.hash = "#/laureate/" + year;
    },
    /* 进入时间轴档案（可定位到某届） */
    goArchive: function (year, sourceEl) {
      pendingSource = sourceEl || null;
      location.hash = "#/timeline" + (year ? "/" + year : "");
    },
    back: function () {
      var r = parse(location.hash);
      if (r.route === "home") { location.hash = ""; return; }
      history.back();
    },
    /* 首页筛选写入 URL（不新增历史记录） */
    syncSelection: function (sel) {
      if (parse(location.hash).route !== "home") return;
      var base = location.pathname + location.search;
      var next = sel ? base + "#?s=" + sel.type + "|" + encodeURIComponent(String(sel.value)) : base;
      history.replaceState(null, "", next);
    }
  };

  NS.router._parse = parse;
})();

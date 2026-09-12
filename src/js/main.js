/* main.js · F 集成官 · 入口装配
   依赖：全部模块
   监听：全局按键/点击 · 发布：无 */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util, S = NS.store;

  /* 页脚网格（铭文 + 署名 + 数据来源），首页/档案页/详情页共用 */
  NS.footerGridHTML = function () {
    return '<div class="foot-rule ui-hair"></div>' +
      '<div class="foot-grid">' +
        '<div class="foot-brand">' +
          '<img class="foot-logo" src="../assets/brand/logo-ink.png" alt="AI DESIFE">' +
          '<p class="ui-cap foot-motto">“FIRMNESS, COMMODITY, DELIGHT” — VITRUVIUS · 普利兹克铜牌铭文</p>' +
        '</div>' +
        '<div class="foot-meta">' +
          '<p class="ui-cap foot-author">设计 · 数据 · 代码 Design &amp; Code by <b>LANCAMO</b></p>' +
          '<p class="ui-cap">数据来源 Source：<a href="https://www.pritzkerprize.com" target="_blank" rel="noopener">The Pritzker Architecture Prize</a> · 维基百科 · 整理于 <span class="js-foot-date"></span></p>' +
        '</div>' +
      '</div>';
  };

  function buildHomeFooter() {
    var foot = document.getElementById("foot");
    if (!foot) return;
    foot.innerHTML = NS.footerGridHTML();
  }

  var HERO_IMG_CANDIDATES = [
    "assets/works/1988-brasilia-cathedral.jpg",
    "assets/works/2012-ningbo-museum.jpg",
    "assets/works/1988-beinecke.jpg"
  ];

  /* 底图池：优先取素材里已有的作品/项目照片，循环淡入淡出 */
  function heroPool() {
    var pool = [], seen = {};
    (window.__DATA__.editions || []).forEach(function (e) {
      (e.officialProjects || []).forEach(function (p) {
        (p.photos || []).forEach(function (ph) { if (ph && !seen[ph]) { seen[ph] = 1; pool.push(ph); } });
      });
      (e.works || []).forEach(function (w) { if (w.photo && !seen[w.photo]) { seen[w.photo] = 1; pool.push(w.photo); } });
    });
    return pool.length ? pool : HERO_IMG_CANDIDATES;
  }

  function buildHero() {
    var bg = document.getElementById("hero-bg");
    var reduce = U.prefersReduce();
    var idx = 0, current = null;

    function show(src) {
      var img = document.createElement("img");
      img.alt = "";
      img.className = "hero-slide";
      img.onload = function () {
        bg.appendChild(img);
        requestAnimationFrame(function () { img.classList.add("is-in"); });
        if (current) {
          var old = current;
          setTimeout(function () { if (old.parentNode) old.parentNode.removeChild(old); }, 1500);
        }
        current = img;
      };
      img.onerror = function () { /* 单张失败不打断轮播 */ };
      img.src = src.indexOf("assets/") === 0 ? "../" + src : src;
    }

    /* 预取下一张，避免切换时空白 */
    function preload(src) {
      var im = new Image();
      im.src = src.indexOf("assets/") === 0 ? "../" + src : src;
    }

    /* 引言与底图成对：每届取官网评审词短引 + 该届代表作照片，
       共用同一个计时器同帧切换，图文不会错位。
       评审词由 tools/fetch_citations.py 从官网抓取，48 届齐备 */
    var cites = window.__DATA__.citations || {};
    var pairs = [];
    S.editions().forEach(function (ed) {
      var c = cites[String(ed.year)];
      if (!c || !(c.quote_en || c.quote_cn)) return;
      /* 底图规则：只用代表作照片，绝不用建筑师肖像（肖像只在档案/详情页用）；
         这里按路径兜底过滤 portraits/，内容层面的错配由 fetch_missing_works 的词元核验兜住 */
      var w = (ed.works || []).filter(function (x) {
        return x.photo && x.photo.indexOf("portraits/") === -1;
      })[0];
      if (!w) return;
      pairs.push({
        year: ed.year,
        cn: c.quote_cn || "",
        en: c.quote_en || "",
        credit: (ed.laureates || []).map(function (l) { return l.name_cn; }).join(" · "),
        work: w.title_cn,
        img: w.photo
      });
    });

    var qEl = document.getElementById("hero-quote");

    function showPair(i) {
      var p = pairs[i % pairs.length];
      if (!p) return;
      show(p.img);
      preload(pairs[(i + 1) % pairs.length].img);
      qEl.style.opacity = "0";
      setTimeout(function () {
        qEl.innerHTML = (p.cn ? U.esc(p.cn) : "") +
          '<span class="en">“' + U.esc(p.en) + '”</span>' +
          '<span class="src">' + p.year + " · " + U.esc(p.credit) +
          " · " + U.esc(p.work) + " · Jury Citation</span>";
        qEl.style.transition = "opacity .8s var(--ease)";
        qEl.style.opacity = "1";
      }, reduce ? 0 : 400);
    }

    if (pairs.length) {
      showPair(0);
      if (!reduce && pairs.length > 1) {
        setInterval(function () {
          idx = (idx + 1) % pairs.length;
          showPair(idx);
        }, 9000);
      }
    } else {
      /* 兜底：没有可成对的评审辞时，退化为纯底图轮播 + 通稿引言 */
      var pool = heroPool();
      show(pool[0]);
      if (!reduce && pool.length > 1) {
        setInterval(function () {
          idx = (idx + 1) % pool.length;
          show(pool[idx]);
          preload(pool[(idx + 1) % pool.length]);
        }, 7000);
      }
      qEl.innerHTML = "被誉为「建筑界的诺贝尔奖」——每年授予一位或多位在世建筑师。" +
        '<span class="en">Regarded as the Nobel Prize of architecture.</span>' +
        '<span class="src">The Pritzker Architecture Prize</span>';
      qEl.style.opacity = "1";
    }

    var st = S.stats();
    var statsEl = document.getElementById("hero-stats");
    [
      { v: st.editions, cn: "届 Editions" },
      { v: st.people, cn: "位得主 Laureates" },
      { v: st.countries, cn: "个国家与地区 Countries" }
    ].forEach(function (s) {
      var d = document.createElement("div");
      d.innerHTML = "<dd>" + s.v + "</dd><dt>" + U.esc(s.cn) + "</dt>";
      statsEl.appendChild(d);
    });

    Array.prototype.forEach.call(document.querySelectorAll(".js-foot-date"), function (n) {
      n.textContent = window.__DATA__.fetched || "";
    });
  }

  /* 滚动揭示：卡片与时间轴依次浮现（JS 注入类名，脚本失效时内容仍可见） */
  function bindReveal() {
    var targets = [].slice.call(document.querySelectorAll(".dash-charts .chart-card, .dash-tl, .foot-grid"));
    if (!targets.length) return;
    targets.forEach(function (t, i) { t.classList.add("reveal"); t.style.transitionDelay = (i * 70) + "ms"; });
    if (!("IntersectionObserver" in window)) {
      targets.forEach(function (t) { t.classList.add("is-in"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add("is-in");
        io.unobserve(en.target);
      });
    }, { threshold: 0.06 });
    targets.forEach(function (t) { io.observe(t); });
  }

  /* 页面滑到底部继续下滑 → 进入时间轴档案（衔接动效见 NS.archive.enterFromHome） */
  function bindEnterArchive() {
    var armed = false;
    function atBottom() {
      return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 6;
    }
    function fire() {
      if (armed || NS.archive.isOpen()) return;
      armed = true;
      NS.archive.enterFromHome();
    }
    window.addEventListener("wheel", function (ev) {
      if (NS.archive.isOpen()) return;
      if (atBottom() && ev.deltaY > 16) fire();
    }, { passive: true });

    var touchY = null;
    window.addEventListener("touchstart", function (ev) { touchY = ev.touches[0].clientY; }, { passive: true });
    window.addEventListener("touchmove", function (ev) {
      if (touchY == null || NS.archive.isOpen()) return;
      var dy = touchY - ev.touches[0].clientY;
      if (atBottom() && dy > 26) fire();
    }, { passive: true });

    S.on("route:change", function () {
      var home = document.getElementById("home");
      if (!home.hidden) armed = false;
    });
  }

  function bindGlobals() {
    /* ESC：单届档案 → 时间轴档案 → 主页逐级返回；主页则清除筛选 */
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      var detail = document.getElementById("detail");
      if (detail && !detail.hidden) { NS.router.back(); return; }
      if (NS.archive && NS.archive.isOpen()) { NS.router.back(); return; }
      S.clearSelection();
    });

    /* 点击空白清除选中（档案页与详情页不参与） */
    document.addEventListener("click", function (ev) {
      if (!document.getElementById("archive").hidden) return;
      if (ev.target.closest(".cna-cell,.cna-legend-item,.cge-dot,.ins-dot,.tl-item,.ui-chip,.hero-medal,.dt-close,.dt-nav,#detail")) return;
      S.clearSelection();
    });

    /* 选中状态写入 URL（可分享） */
    S.on("selection:change", function (sel) { NS.router.syncSelection(sel); });
  }

  function init() {
    var data = window.__DATA__;
    if (!data) return;
    NS.vendor = { geo: data.geo };
    S.init(data);
    buildHomeFooter();
    buildHero();
    NS.timeline.init();
    NS.chartGeo.init();      /* 先渲染地理图：国籍图的圆形与其等高 */
    NS.chartNations.init();
    NS.medal.init();
    NS.detail.init();
    NS.archive.init();
    NS.router.init();
    bindGlobals();
    bindReveal();
    bindEnterArchive();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

/* detail.js · E 详情官 · 详情页渲染（Hero / 信息栏 / 评审辞 / 代表作 [01][02] / 冷知识 / 上下届）
   依赖：store / util / router
   监听：无 · 发布：无 */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util, S = NS.store;

  var detailEl = null;
  var currentYear = null;

  function assetPath(p) {
    if (!p) return null;
    return p.indexOf("assets/") === 0 ? "../" + p : p;
  }

  function lifespan(l) {
    if (l.birth_year == null) return "—";
    return l.birth_year + "—" + (l.death_year || "");
  }

  function namesBlock(doss, cls) {
    return doss.laureates.map(function (l, i) {
      return '<span class="' + cls + '"' + (i ? ' style="margin-top:6px;display:block"' : '') + '>' + U.esc(l.name_cn) + "</span>";
    }).join("");
  }

  function render(year, doss) {
    if (!detailEl) detailEl = document.getElementById("detail");
    if (!doss) return;
    currentYear = year;

    var list = S.editions();
    var idx = list.findIndex(function (e) { return e.year === year; });
    var prev = idx > 0 ? list[idx - 1] : null;
    var next = idx < list.length - 1 ? list[idx + 1] : null;

    var heroImg = doss.portrait || (doss.works[0] && doss.works[0].photo) || null;
    var light = !heroImg;

    var natUnion = U.uniq(doss.laureates.reduce(function (a, l) { return a.concat(l.nationalities); }, []));
    var ages = doss.laureates.map(function (l) { return l.age_at_award; }).filter(function (a) { return a != null; });
    var lifes = doss.laureates.map(lifespan).join(" / ");

    var html = "";
    html += '<article class="dt-page' + (light ? " is-light" : "") + '">';
    html += '<button type="button" class="dt-close" id="dt-close">← 返回 Index</button>';
    html += '<a class="dt-archive-link ui-cap" href="#/timeline/' + year + '">在时间轴档案中定位 Locate in Archive →</a>';

    /* Hero */
    html += '<header class="dt-hero' + (light ? " is-light" : "") + '">';
    html += '<a class="dt-brand" href="#home" aria-label="AI DESIFE"><img src="../assets/brand/logo-paper.png" alt="AI DESIFE"></a>';
    if (heroImg) {
      html += '<div class="ui-img"><img id="dt-hero-img" alt="" src="' + U.esc(assetPath(heroImg)) + '"></div>';
    }
    html += '<div class="dt-year dt-reveal" style="--i:0">' + year + "</div>";
    html += '<div class="dt-head">';
    html += '<p class="dt-kicker ui-cap dt-reveal" style="--i:1">第 ' + doss.editionNo + " 届　Edition " + U.ordinal(doss.editionNo) + "　·　1979—2026</p>";
    html += '<h1 class="dt-name dt-reveal" style="--i:2">' + namesBlock(doss, "dt-name-line") +
      '<span class="en">' + U.esc(doss.laureates.map(function (l) { return l.name_en || ""; }).filter(Boolean).join(" · ")) + "</span></h1>";
    html += '<p class="dt-sub dt-reveal" style="--i:3">' + U.esc(natUnion.join(" / ")) + "　·　" + U.esc(lifes) +
      (ages.length ? "　·　获奖年龄 " + U.esc(ages.join(" / ")) + " 岁" : "") + "</p>";
    html += "</div>";
    if (heroImg && doss.portraitCredit) {
      html += '<p class="dt-hero-cap ui-cap">' + U.esc(doss.portraitCredit) + "</p>";
    }
    html += "</header>";

    /* 正文 */
    html += '<div class="dt-body">';

    /* 信息栏 */
    html += '<section class="dt-info dt-reveal" style="--i:4">';
    html += "<div><dt>届次 Edition</dt><dd>第 " + doss.editionNo + " 届<span class='en'>#" + U.ordinal(doss.editionNo) + "</span></dd></div>";
    html += "<div><dt>国籍 Nationality</dt><dd>" + U.esc(natUnion.join(" / ")) +
      "<span class='en'>" + U.esc(natUnion.map(function (n) { return S.enOf(n); }).join(" / ")) + "</span></dd></div>";
    html += "<div><dt>生卒 Lifespan</dt><dd>" + U.esc(lifes) + "</dd></div>";
    html += "<div><dt>获奖年龄 Age at Award</dt><dd>" + (ages.length ? U.esc(ages.join(" / ")) + " 岁" : "—") + "</dd></div>";
    html += "<div><dt>事务所 Firm</dt><dd>" + U.esc(doss.firm || "—") + "</dd></div>";
    html += "</section>";

    /* 评审辞：短引作提要；官网完整评审辞（若长于提要）另起一段供全文阅读 */
    if (doss.citation) {
      html += '<section class="dt-quote dt-reveal" style="--i:5"><blockquote class="ui-quote">' +
        (doss.citation.cn ? U.esc(doss.citation.cn) : "") +
        '<span class="en">“' + U.esc(doss.citation.en) + '”</span>' +
        '</blockquote><p class="ui-quote-src ui-cap">' + U.esc(doss.citation.source) + "</p>";
      if (doss.citationFull) {
        var cf = doss.citationFull, cfHtml = "";
        cf.en.split(/\n{2,}/).filter(function (p) { return p.trim(); }).forEach(function (p, i) {
          cfHtml += '<p class="dt-cite-p p-en">' + U.esc(p) + "</p>";
          ((cf.groups && cf.groups[i]) || []).forEach(function (cn) {
            cfHtml += '<p class="dt-cite-p p-cn">' + U.esc(cn) + "</p>";
          });
        });
        html += '<div class="dt-cite-full">' +
          '<h3 class="dt-cite-full-head ui-cap">评审辞全文 <span class="en">Full Jury Citation</span></h3>' +
          cfHtml +
          "</div>";
      }
      html += "</section>";
    }

    /* 代表作 */
    html += '<section class="dt-works">';
    html += '<div class="dt-works-head dt-reveal" style="--i:6"><h2 class="dt-works-title">代表作<span class="en ui-cap">Selected Works</span></h2>' +
      '<p class="ui-cap">' + (doss.full ? "官方档案 · Official Dossier" : "完整档案整理中 · Dossier in Progress") + "</p></div>";

    doss.works.forEach(function (w, i) {
      var cls = i === 0 ? "dt-work--full" : "dt-work--half";
      html += '<article class="dt-work ' + cls + ' dt-reveal" style="--i:' + (7 + i) + '">';
      if (w.photo) {
        html += '<figure class="ui-img"><img class="dt-work-img" alt="' + U.esc(w.title_cn) + '" data-src="' + U.esc(assetPath(w.photo)) + '"></figure>';
      } else {
        html += '<div class="ui-ph"><span>影像整理中 Image Pending</span></div>';
      }
      html += '<div class="dt-work-cap"><div>';
      html += '<h3 class="dt-work-title"><span class="no">[' + U.ordinal(i + 1) + "]</span>" + U.esc(w.title_cn) +
        (w.title_en ? '<span class="en">' + U.esc(w.title_en) + "</span>" : "") + "</h3>";
      if (w.by) html += '<p class="dt-work-by">' + U.esc(w.by) + "</p>";
      html += "</div>";
      html += '<div class="dt-work-credit">' +
        U.esc([w.city, w.country].filter(Boolean).join(" · ")) +
        (w.completed ? "<br>建成 " + U.esc(w.completed) : "") +
        (w.credit ? "<br>" + U.esc(w.credit) : "") + "</div>";
      html += "</div>";
      if (w.note) html += '<p class="dt-work-note">' + U.esc(w.note) + "</p>";
      html += "</article>";
    });
    html += "</section>";

    /* 冷知识 */
    if (doss.trivia) {
      html += '<section class="dt-trivia dt-reveal" style="--i:11"><b>Did you know</b><p>' + U.esc(doss.trivia) + "</p></section>";
    }

    /* 上下届 */
    html += '<nav class="dt-nav dt-reveal" style="--i:12">';
    html += prev
      ? '<a class="prev" href="#/laureate/' + prev.year + '"><span class="dir">← 上一届 Previous</span><span class="who"><em>' + prev.year + "</em>" + U.esc(prev.laureates.map(function (l) { return l.name_cn; }).join(" / ")) + "</span></a>"
      : "<span></span>";
    html += next
      ? '<a class="next" href="#/laureate/' + next.year + '"><span class="dir">下一届 Next →</span><span class="who">' + U.esc(next.laureates.map(function (l) { return l.name_cn; }).join(" / ")) + "<em style='margin-left:12px;margin-right:0'>" + next.year + "</em></span></a>"
      : "<span></span>";
    html += "</nav>";

    html += "</div></article>";

    detailEl.innerHTML = html;
    detailEl.insertAdjacentHTML("beforeend", '<div class="foot-page">' + NS.footerGridHTML() + "</div>");
    detailEl.scrollTop = 0;

    /* “在时间轴档案中定位”：根据 Hero 背景明暗自动取白/黑，确保醒目 */
    (function () {
      var linkEl = detailEl.querySelector(".dt-archive-link");
      var heroEl = detailEl.querySelector("#dt-hero-img");
      if (!linkEl) return;
      function setInk(ink, line) {
        linkEl.style.setProperty("--link-ink", ink);
        linkEl.style.setProperty("--link-line", line);
      }
      function decide() {
        var isPortrait = heroEl && heroEl.closest(".dt-hero").classList.contains("is-portrait");
        if (!heroImg || isPortrait) {        /* 纸底（无影像 / 竖构图右侧留白） */
          setInk("#0A0A0A", "var(--g25)");
          return;
        }
        var src = heroImg.indexOf("assets/") === 0 ? "../" + heroImg : heroImg;
        var im = new Image();
        im.crossOrigin = "anonymous";        /* 同源/本地服务器可采样；污染时回退 */
        im.onload = function () {
          try {
            var c = document.createElement("canvas");
            var w = c.width = 48, h = c.height = 48;
            var ctx = c.getContext("2d");
            /* 取图片顶部 30%（链接所在区域）估计亮度 */
            ctx.drawImage(im, 0, 0, im.naturalWidth, im.naturalHeight * 0.3, 0, 0, w, h);
            var d = ctx.getImageData(0, 0, w, h).data, sum = 0, n = d.length / 4;
            for (var i = 0; i < d.length; i += 4) {
              sum += (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) / 255;
            }
            var eff = (sum / n) * (1 - 0.38);   /* 叠加 Hero 顶部 .38 深色蒙版后的有效亮度 */
            if (eff < 0.5) setInk("#fff", "rgba(255,255,255,.5)");
            else setInk("#0A0A0A", "var(--g25)");
          } catch (e) {        /* 跨域 / file:// 画布污染：回退白字（蒙版已压暗） */
            setInk("#fff", "rgba(255,255,255,.5)");
          }
        };
        im.onerror = function () { setInk("#fff", "rgba(255,255,255,.5)"); };
        im.src = src;
      }
      if (heroEl && !heroEl.complete) heroEl.addEventListener("load", decide);
      decide();
    })();

    /* blur-up 图片揭示 + 竖构图人像的 Hero 变体 */
    var imgs = detailEl.querySelectorAll("img");
    Array.prototype.forEach.call(imgs, function (img) {
      var mark = function () {
        img.classList.add("is-loaded");
        if (img.id === "dt-hero-img" && img.naturalHeight > img.naturalWidth * 1.05) {
          var hero = img.closest(".dt-hero");
          if (hero) hero.classList.add("is-portrait");
        }
      };
      if (img.dataset.src) img.src = img.dataset.src;
      if (img.complete && img.naturalWidth) mark();
      else img.addEventListener("load", mark);
    });

    /* 关闭 */
    var closeBtn = detailEl.querySelector("#dt-close");
    if (closeBtn) closeBtn.addEventListener("click", function () { NS.router.back(); });
  }

  NS.detail = {
    init: function () { detailEl = document.getElementById("detail"); },
    render: render,
    current: function () { return currentYear; }
  };
})();

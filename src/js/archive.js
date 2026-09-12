/* archive.js · 时间轴档案页 · 墨底时间脊长卷（版式参照 eladiodieste.com）
   每届：年份标记钉在中央时间脊上，影像与文字左右交错，随滚动推进并浮入
   依赖：store / util / router
   监听：无 · 发布：无 */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util, S = NS.store;

  var el, homeEl, detailEl;
  var built = false;
  var itemEls = [], mediaEls = [];
  var savedScroll = 0;
  var ioItems = null, ioCurrent = null;
  var rafId = null, rising = false;

  function assetPath(p) {
    if (!p) return null;
    return p.indexOf("assets/") === 0 ? "../" + p : p;
  }

  function lifespan(l) {
    if (l.birth_year == null) return "—";
    return l.birth_year + "—" + (l.death_year || "");
  }

  function figHTML(src, kind, alt, cap) {
    if (!src) return "";
    return '<figure class="ar-fig-wrap">' +
      '<div class="ar-fig ar-fig--' + kind + '">' +
      '<img data-src="' + U.esc(assetPath(src)) + '" alt="' + U.esc(alt) + '">' +
      "</div>" + (cap ? '<figcaption class="ar-cap">' + U.esc(cap) + "</figcaption>" : "") +
      "</figure>";
  }

  function entryHTML(year) {
    var d = S.dossier(year);
    if (!d) return "";
    var natUnion = U.uniq(d.laureates.reduce(function (a, l) { return a.concat(l.nationalities); }, []));
    var ages = d.laureates.map(function (l) { return l.age_at_award; }).filter(function (a) { return a != null; });
    var lifes = d.laureates.map(lifespan).join(" / ");
    var enNames = d.laureates.map(function (l) { return l.name_en || ""; }).filter(Boolean).join(" · ");
    var names = d.laureates.map(function (l) { return U.esc(l.name_cn); }).join(" · ");
    var photoWork = (d.works || []).filter(function (w) { return w.photo; })[0] || null;

    var h = '<li class="ar-item" id="ar-' + year + '" data-year="' + year + '">';
    h += '<span class="ar-mark" aria-hidden="true"><b>' + year + "</b><i></i></span>";

    /* 影像列：肖像（官网）+ 官网项目照片（无则用代表作照片兜底） */
    h += '<div class="ar-media">';
    if (d.portrait) {
      h += figHTML(d.portrait, "portrait", names + " 肖像", d.portraitCredit || "The Pritzker Architecture Prize");
    }
    var officialShots = [];
    (d.projects || []).forEach(function (pj) {
      (pj.photos || []).forEach(function (ph, i) {
        if (officialShots.length < 2) officialShots.push({ photo: ph, title: pj.title, first: i === 0 });
      });
    });
    if (officialShots.length) {
      officialShots.forEach(function (s) {
        h += figHTML(s.photo, "work", s.title, s.title + " · The Pritzker Architecture Prize");
      });
    } else if (photoWork) {
      h += figHTML(photoWork.photo, "work", photoWork.title_cn,
        photoWork.title_cn + (photoWork.city ? " · " + photoWork.city : "") +
        (photoWork.credit ? " · " + photoWork.credit : ""));
    }
    if (!d.portrait && !officialShots.length && !photoWork) {
      h += '<div class="ar-fig ar-fig--portrait ar-fig--none"><span>影像整理中<br>Imagery Pending</span></div>';
    }
    h += "</div>";

    /* 文字列 */
    h += '<div class="ar-text">';
    h += '<p class="ar-kicker ui-cap">第 ' + d.editionNo + " 届 · Edition " + U.ordinal(d.editionNo) + "</p>";
    h += '<h2 class="ar-names">' + names + (enNames ? '<span class="en">' + U.esc(enNames) + "</span>" : "") + "</h2>";
    h += '<p class="ar-meta ui-cap">' + U.esc(natUnion.join(" / ")) + " · " + U.esc(lifes) +
      (ages.length ? " · 获奖年龄 " + U.esc(ages.join(" / ")) + " 岁" : "") +
      (d.firm ? " · " + U.esc(d.firm) : "") + "</p>";

    /* 生平（官网）：首段常显，其余可展开；中英严格对齐——每个英文段后接其中文译文段
       （bioGroups 为人工核对的配对，见 data/bio_cn_aligned.json；无译文的段只显英文）。
       「收起」置于全文结尾，「展开」在打开后隐去（见 archive.css） */
    if (d.bio) {
      var bioEn = d.bio.split(/\n{2,}/).filter(function (p) { return p.trim(); });
      var bioGroups = d.bioGroups || null;
      function bioPair(i) {
        var out = '<p class="ar-bio-p p-en">' + U.esc(bioEn[i]) + "</p>";
        (bioGroups ? (bioGroups[i] || []) : []).forEach(function (cn) {
          out += '<p class="ar-bio-p p-cn">' + U.esc(cn) + "</p>";
        });
        return out;
      }
      h += '<div class="ar-bio">';
      h += bioPair(0);
      if (bioEn.length > 1) {
        h += '<button type="button" class="ar-bio-toggle ar-bio-more-btn">' +
          "展开生平全文 · Read full biography</button>";
        h += '<div class="ar-bio-more">';
        for (var bi = 1; bi < bioEn.length; bi++) h += bioPair(bi);
        h += '<button type="button" class="ar-bio-toggle ar-bio-less-btn">' +
          "收起生平全文 · Collapse biography</button>";
        h += "</div>";
      }
      h += "</div>";
    }

    if (d.citation) {
      h += '<blockquote class="ar-quote">' + U.esc(d.citation.cn) +
        '<span class="en">“' + U.esc(d.citation.en) + '”</span>' +
        '<span class="ar-quote-src">' + U.esc(d.citation.source) + "</span></blockquote>";
    }

    if (d.works && d.works.length) {
      h += '<ul class="ar-works">';
      d.works.forEach(function (w, i) {
        var descHtml = "";
        if (w.desc) {
          descHtml = w.desc.split(/\n{2,}/).map(function (p) {
            return '<p>' + U.esc(p) + "</p>";
          }).join("");
        }
        h += '<li class="ar-work"><span class="no">[' + U.ordinal(i + 1) + ']</span>' +
          '<span class="t">' + U.esc(w.title_cn) +
          (w.title_en ? '<span class="en">' + U.esc(w.title_en) + "</span>" : "") + "</span>" +
          '<span class="loc">' + U.esc([w.city, w.country].filter(Boolean).join(" · ")) +
          (w.completed ? " · " + U.esc(w.completed) : "") + "</span>" +
          (descHtml ? '<div class="desc">' + descHtml + "</div>" : "") + "</li>";
      });
      h += "</ul>";
    }
    h += '<a class="ar-more ui-cap" href="#/laureate/' + year + '">展开单届全档 Full Dossier →</a>';
    h += "</div></li>";
    return h;
  }

  function build() {
    var editions = S.editions();

    var h = '<header class="ar-bar">' +
      '<a class="ar-logo" href="#home" aria-label="AI DESIFE · 返回首页"><img src="../assets/brand/logo-paper.png" alt="AI DESIFE"></a>' +
      '<p class="ar-bar-title ui-cap">时间轴档案 · Timeline Archive · 1979—2026</p>' +
      '<div class="ar-bar-right">' +
      '<span class="ar-count ui-cap">' + editions.length + " 届 · " +
      editions.reduce(function (a, e) { return a + e.laureates.length; }, 0) + " 位得主</span>" +
      '<button type="button" class="ar-close" id="ar-close">← 返回总览 Index</button>' +
      '</div></header>';

    /* 总起页：承接从首页滑入的瞬间，交代这条时间轴的读法 */
    h += '<header class="ar-cover">';
    h += '<p class="ar-cover-kicker ui-cap">Timeline Archive · 1979—2026</p>';
    h += '<h1 class="ar-cover-title">时间轴档案</h1>';
    h += '<p class="ar-lead">以时间轴为主线，自 1979 年首届起逐届展开：' +
      '姓名、肖像、生卒与获奖年龄、评审辞、代表作，以及官网生平。' +
      '<span class="en">A continuous line through 48 editions — names, portraits, lives and works.</span></p>';
    h += '<p class="ar-cover-meta ui-cap">' + editions.length + " 届 · " +
      editions.reduce(function (a, e) { return a + e.laureates.length; }, 0) +
      " 位得主 · 肖像与生平来源 The Pritzker Architecture Prize</p>";
    h += '<p class="ar-scroll-hint ui-cap">Scroll ↓</p>';
    h += "</header>";

    h += '<span class="ar-spine" aria-hidden="true"><i class="ar-spine-fill" id="ar-spine-fill"></i></span>';
    h += '<div class="ar-body"><ol class="ar-list">';
    editions.forEach(function (e) { h += entryHTML(e.year); });
    h += "</ol></div>";

    el.innerHTML = h;
    el.insertAdjacentHTML("beforeend", '<div class="foot-page">' + NS.footerGridHTML() + "</div>");
    built = true;

    itemEls = Array.prototype.slice.call(el.querySelectorAll(".ar-item"));
    mediaEls = Array.prototype.slice.call(el.querySelectorAll(".ar-media"));

    Array.prototype.forEach.call(el.querySelectorAll(".ar-fig img"), function (img) {
      var mark = function () { img.classList.add("is-loaded"); };
      img.src = img.dataset.src;
      if (img.complete && img.naturalWidth) mark();
      else img.addEventListener("load", mark);
      img.addEventListener("error", function () {
        var fig = img.closest(".ar-fig");
        if (fig) fig.classList.add("ar-fig--none");
      });
    });

    el.querySelector("#ar-close").addEventListener("click", function () { NS.router.back(); });

    /* 生平展开/收起：展开时钉住点击处上方（视觉位置不动、内容向下展开，
       抵消浏览器滚动锚定造成的大幅跳变）；收起时整条上移会瞬移，直接回到该届
       在时间轴档案中的位置 */
    Array.prototype.forEach.call(el.querySelectorAll(".ar-bio-toggle"), function (btn) {
      btn.addEventListener("click", function () {
        var bio = btn.closest(".ar-bio");
        if (!bio) return;
        var item = bio.closest(".ar-item");
        var before = bio.getBoundingClientRect().top;
        var opening = !bio.classList.contains("is-open");
        bio.classList.toggle("is-open");
        requestAnimationFrame(function () {
          if (opening) {
            window.scrollBy(0, bio.getBoundingClientRect().top - before);
          } else if (item) {
            var top = item.getBoundingClientRect().top + window.scrollY - window.innerHeight * 0.30;
            window.scrollTo(0, Math.max(0, top));
          }
        });
      });
    });

    bindObservers();
    bindKeys();
  }

  /* 浮入揭示 + 当前届高亮 */
  function bindObservers() {
    if (ioItems) ioItems.disconnect();
    if (ioCurrent) ioCurrent.disconnect();

    if ("IntersectionObserver" in window) {
      ioItems = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          en.target.classList.add("is-in");
          ioItems.unobserve(en.target);
        });
      }, { threshold: 0.08 });
      itemEls.forEach(function (it) { ioItems.observe(it); });

      ioCurrent = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          var was = en.target.classList.contains("is-current");
          en.target.classList.toggle("is-current", en.isIntersecting);
          /* 首次抵达该届：年份弹跳一下，强化「到达」 */
          if (en.isIntersecting && !was) popYear(en.target);
        });
      }, { rootMargin: "-46% 0px -46% 0px" });
      itemEls.forEach(function (it) { ioCurrent.observe(it); });
    } else {
      itemEls.forEach(function (it) { it.classList.add("is-in", "is-current"); });
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    bindExitToHome();
  }

  /* 档案页顶端继续上滑 → 回首页 */
  function bindExitToHome() {
    var cooldown = false;
    function atTop() { return window.scrollY <= 2; }
    function fire() {
      if (cooldown || !NS.archive.isOpen() || !atTop()) return;
      cooldown = true;
      NS.archive.exitToHome();
      setTimeout(function () { cooldown = false; }, 900);
    }
    window.addEventListener("wheel", function (ev) {
      if (!NS.archive.isOpen()) return;
      if (atTop() && ev.deltaY < -16) fire();
    }, { passive: true });

    var touchY = null;
    window.addEventListener("touchstart", function (ev) { touchY = ev.touches[0].clientY; }, { passive: true });
    window.addEventListener("touchmove", function (ev) {
      if (touchY == null || !NS.archive.isOpen()) return;
      if (atTop() && ev.touches[0].clientY - touchY > 26) fire();
    }, { passive: true });
  }

  /* 年份弹跳：白色进度段触达时放一下再回弹 */
  function popYear(item) {
    if (!item || U.prefersReduce()) return;
    var b = item.querySelector(".ar-mark b");
    if (!b || !b.animate) return;
    b.animate(
      [{ transform: "scale(1)" }, { transform: "scale(1.4)" }, { transform: "scale(1)" }],
      { duration: 560, easing: "cubic-bezier(.32,.72,0,1)" }
    );
  }

  /* 进度线 + 影像列的轻微视差（缓动跟随，不干扰阅读） */
  function onScroll() {
    if (!el || el.hidden || rafId) return;
    rafId = requestAnimationFrame(function () {
      rafId = null;

      /* 年份状态：越过阅读线的届为白，未越过的为灰。
         门槛与 .ar-spine-fill 的高度（50vh）取同一个值——白线沿即变色沿 */
      var gate = window.innerHeight * 0.5;
      itemEls.forEach(function (it) {
        it.classList.toggle("is-passed", it.getBoundingClientRect().top < gate);
      });

      if (U.prefersReduce()) return;
      var mid = window.innerHeight / 2;
      mediaEls.forEach(function (m) {
        var r = m.getBoundingClientRect();
        var d = (r.top + r.height / 2 - mid) / mid;   // -1..1
        m.style.transform = "translateY(" + (U.clampNum(d, -1, 1) * -16).toFixed(1) + "px)";
      });
    });
  }

  /* 键盘：← → 逐届跳转（wayfinding） */
  function bindKeys() {
    document.addEventListener("keydown", function (ev) {
      if (el.hidden) return;
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      var cur = 0, mid = window.innerHeight * 0.45;
      for (var i = 0; i < itemEls.length; i++) {
        if (itemEls[i].getBoundingClientRect().top <= mid) cur = i;
      }
      var next = U.clampNum(cur + (ev.key === "ArrowRight" ? 1 : -1), 0, itemEls.length - 1);
      location.hash = "#/timeline/" + itemEls[next].dataset.year;
      ev.preventDefault();
    });
  }

  function scrollToYear(year) {
    var t = year ? el.querySelector("#ar-" + year) : null;
    if (!t) { window.scrollTo(0, 0); return; }
    requestAnimationFrame(function () {
      var top = t.getBoundingClientRect().top + window.scrollY - window.innerHeight * 0.30;
      window.scrollTo(0, Math.max(0, top));
    });
  }

  NS.archive = {
    init: function () {
      el = document.getElementById("archive");
      homeEl = document.getElementById("home");
      detailEl = document.getElementById("detail");
    },
    isOpen: function () { return !!el && !el.hidden; },

    /* 从首页底部继续下滑进入：时间轴左移淡出、页脚右移淡出，档案页自下而上浮起 */
    enterFromHome: function () {
      var home = document.getElementById("home");
      var reduce = U.prefersReduce();
      if (!reduce) {
        home.classList.add("is-exit");
        rising = true;
      }
      setTimeout(function () {
        /* 不带年份：落在总起页（ar-cover），否则会直接滚过封面、看不见它 */
        NS.router.goArchive();
        setTimeout(function () { home.classList.remove("is-exit"); }, reduce ? 0 : 700);
      }, reduce ? 0 : 240);
    },

    /* 档案页顶端继续上滑 → 回到首页（与进入镜像：整页下落淡出） */
    exitToHome: function () {
      if (!el || el.hidden) return;
      if (U.prefersReduce()) { NS.router.back(); return; }
      el.classList.add("is-falling");
      setTimeout(function () {
        NS.router.back();
        el.classList.remove("is-falling");
      }, 320);
    },

    open: function (year) {
      if (!el) return;
      if (!built) build();
      if (!this.isOpen()) savedScroll = window.scrollY || 0;
      homeEl.hidden = true;
      detailEl.hidden = true;
      el.hidden = false;
      /* 墨底接管：上升/下落时露出的是深色，而不是浅色纸面（否则会闪白） */
      document.body.classList.add("is-archive-open");
      if (rising && !U.prefersReduce()) {
        rising = false;
        el.classList.add("is-rising");
        requestAnimationFrame(function () {
          requestAnimationFrame(function () { el.classList.remove("is-rising"); });
        });
      }
      scrollToYear(year);
      onScroll();
    },
    /* silent=true：仅隐藏（不还原首页，用于切到单届档案） */
    close: function (silent) {
      if (!el || el.hidden) return;
      el.hidden = true;
      document.body.classList.remove("is-archive-open");
      if (silent) return;
      homeEl.hidden = false;
      detailEl.hidden = true;
      window.scrollTo(0, savedScroll);
    }
  };
})();

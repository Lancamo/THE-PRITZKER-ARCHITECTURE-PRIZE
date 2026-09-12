/* transition.js · E 详情官 · 首页 ↔ 详情过渡（遮罩 morph + 文档流切换）
   依赖：util / detail
   监听：无 · 发布：无 */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util;

  var detailEl = null, homeEl = null, veil = null;
  var homeScroll = 0, openYear = null;

  function ensureEls() {
    if (!detailEl) detailEl = document.getElementById("detail");
    if (!homeEl) homeEl = document.getElementById("home");
    if (!veil) {
      veil = document.createElement("div");
      veil.className = "tr-veil";
      document.body.appendChild(veil);
    }
  }

  function veilFrom(rect, done) {
    var vw = window.innerWidth, vh = window.innerHeight;
    var dur = U.prefersReduce() ? 1 : 620;
    veil.style.opacity = "1";
    veil.style.transformOrigin = "top left";
    var sx = Math.max(rect.width / vw, 0.02), sy = Math.max(rect.height / vh, 0.02);
    veil.style.transform = "translate(" + rect.left + "px," + rect.top + "px) scale(" + sx + "," + sy + ")";
    veil.animate(
      [
        { transform: "translate(" + rect.left + "px," + rect.top + "px) scale(" + sx + "," + sy + ")" },
        { transform: "translate(0px,0px) scale(1,1)" }
      ],
      { duration: dur, easing: "cubic-bezier(.32,.72,0,1)", fill: "forwards" }
    ).onfinish = function () {
      veil.style.transform = "none";
      done();
    };
  }

  function veilOut(done) {
    var dur = U.prefersReduce() ? 1 : 360;
    veil.style.transform = "none";
    veil.animate(
      [{ opacity: 1 }, { opacity: 0 }],
      { duration: dur, easing: "cubic-bezier(.32,.72,0,1)", fill: "forwards" }
    ).onfinish = function () {
      veil.style.opacity = "0";
      done();
    };
  }

  NS.transition = {
    open: function (year, sourceEl) {
      ensureEls();
      var doss = NS.store.dossier(year);
      if (!doss) return;
      if (openYear == null) homeScroll = window.scrollY || 0;
      openYear = year;

      NS.detail.render(year, doss);
      homeEl.hidden = true;
      detailEl.hidden = false;
      window.scrollTo(0, 0);
      detailEl.classList.remove("enter");
      void detailEl.offsetWidth; /* 强制重排，保证跨届切换时入场动画可重放 */

      var show = function () {
        detailEl.classList.add("enter");
        veilOut(function () {});
      };
      if (sourceEl && sourceEl.getBoundingClientRect && !U.prefersReduce()) {
        veilFrom(sourceEl.getBoundingClientRect(), show);
      } else {
        veil.style.opacity = "0";
        show();
      }
    },

    /* silent=true：只收起详情（前往档案页等），不还原首页与滚动位置 */
    close: function (silent) {
      ensureEls();
      if (openYear == null) {
        detailEl.hidden = true;
        detailEl.classList.remove("enter");
        return;
      }
      openYear = null;
      var finish = function () {
        detailEl.hidden = true;
        detailEl.classList.remove("enter");
        if (silent) return;
        homeEl.hidden = false;
        window.scrollTo(0, homeScroll);
      };
      if (U.prefersReduce() || detailEl.hidden) { finish(); return; }
      veil.style.transform = "none";
      veil.animate(
        [{ opacity: 0 }, { opacity: 1 }],
        { duration: 300, easing: "cubic-bezier(.32,.72,0,1)", fill: "forwards" }
      ).onfinish = function () {
        veil.style.opacity = "0";
        finish();
      };
    }
  };
})();

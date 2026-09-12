/* util.js · F 集成官 · 纯工具
   依赖：无
   监听：无 · 发布：无 */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});

  NS.util = {
    esc: function (s) {
      return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    },
    clampNum: function (v, lo, hi) {
      if (!isFinite(v) || v < lo) return lo;
      if (v > hi) return hi;
      return v;
    },
    debounce: function (fn, wait) {
      var t = null;
      return function () {
        var args = arguments, self = this;
        clearTimeout(t);
        t = setTimeout(function () { fn.apply(self, args); }, wait);
      };
    },
    prefersReduce: function () {
      return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    },
    uniq: function (arr) {
      var seen = {}, out = [];
      arr.forEach(function (v) { if (!seen[v]) { seen[v] = 1; out.push(v); } });
      return out;
    },
    ordinal: function (n) { // 1→01
      return String(n).padStart(2, "0");
    },
    editionNo: function (year) { return year - 1979 + 1; },
    /* 中英逐段交替：同一段先英文后中文；段数不等时多出的接在末尾。
       cls 为段落 class，供 CSS 区分两种语言的字色 */
    bilingual: function (en, cn, cls) {
      var esc = NS.util.esc;
      var a = String(en || "").split(/\n{2,}/).filter(function (p) { return p.trim(); });
      var b = String(cn || "").split(/\n{2,}/).filter(function (p) { return p.trim(); });
      var out = [], n = Math.max(a.length, b.length);
      for (var i = 0; i < n; i++) {
        if (a[i]) out.push('<p class="' + cls + ' p-en">' + esc(a[i]) + "</p>");
        if (b[i]) out.push('<p class="' + cls + ' p-cn">' + esc(b[i]) + "</p>");
      }
      return out.join("");
    }
  };
})();

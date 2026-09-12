/* medal.js · 奖章交互 · Hero 青铜奖章（3D 双面 + 厚度层）
   拖拽 1:1 跟随 → 松手按动量投射吸附到正/反面（弹簧从当前值续接速度，可随时抓回）
   点击翻转 · 键盘 ←→ / Enter / Home
   参数参照 Apple《Designing Fluid Interfaces》：旋转类阻尼比 0.8、响应 0.4s
   依赖：util
   监听：无 · 发布：无 */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util;

  /* 弹簧参数（阻尼比 + 响应）→ 刚度/阻尼系数 */
  var ZETA = 0.8;          // 旋转类：带少量回弹
  var RESPONSE = 0.4;      // s
  var OMEGA = (2 * Math.PI) / RESPONSE;
  var K = OMEGA * OMEGA;
  var C = 2 * ZETA * OMEGA;

  var DRAG_RATIO = 0.55;   // 拖拽像素 → 角度
  var DECEL = 0.998;       // 动量投射的减速率（Apple 指数衰减式）
  var HYSTERESIS = 3;      // 起始迟滞（px）
  var TAP_PX = 5;          // 判定为点击的最大位移
  var EDGE_LAYERS = 12;    // 厚度层数
  var EDGE_STEP = 1;       // 每层 Z 轴间距（px）
  var EDGE_HALF = 5.5;     // 半厚度（正反面各外推该值，与 CSS 中 translateZ 一致）

  var fig, coin, sideEl;
  var rot = 0, vel = 0, rafId = null, targetRot = 0;
  var dragging = false, armed = false, startX = 0, startRot = 0, lastT = 0, moved = 0;

  function render() {
    coin.style.transform = "rotateY(" + rot.toFixed(2) + "deg)";
    var back = ((Math.round(rot / 180) % 2) + 2) % 2 === 1;
    sideEl.textContent = back ? "Back · 背面" : "Front · 正面";
  }

  function stopSpring() {
    if (rafId != null) { cancelAnimationFrame(rafId); rafId = null; }
  }

  /* 从当前角度与当前角速度续接，目标改变时无需重新起步（可中断） */
  function springTo(target) {
    stopSpring();
    targetRot = target;
    if (U.prefersReduce()) { rot = target; vel = 0; render(); return; }
    var last = performance.now();
    var step = function (now) {
      var dt = Math.min((now - last) / 1000, 1 / 30);
      last = now;
      var a = K * (targetRot - rot) - C * vel;
      vel += a * dt;
      rot += vel * dt;
      if (Math.abs(targetRot - rot) < 0.06 && Math.abs(vel) < 6) {
        rot = targetRot; vel = 0; render(); rafId = null; return;
      }
      render();
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
  }

  /* 指数衰减式动量投射（Apple 原式，非 v²/2a） */
  function project(v) {
    var vv = U.clampNum(Math.abs(v), 0, 4200) * (v < 0 ? -1 : 1);
    return (vv / 1000) * DECEL / (1 - DECEL);
  }

  function faceOf(deg) { return Math.round(deg / 180) * 180; }
  function flip() { springTo(faceOf(rot) + 180); }

  /* 侧壁层自 -EDGE_HALF 均匀排布到 +EDGE_HALF（正反面两端各被面片遮住） */
  function buildEdges() {
    var frag = document.createDocumentFragment();
    for (var i = 0; i < EDGE_LAYERS; i++) {
      var z = -EDGE_HALF + i * EDGE_STEP;
      var s = document.createElement("span");
      s.className = "medal-edge";
      s.setAttribute("aria-hidden", "true");
      s.style.transform = "translateZ(" + z.toFixed(1) + "px)";
      frag.appendChild(s);
    }
    coin.insertBefore(frag, coin.firstChild);
  }

  function endDrag() {
    if (!dragging && !armed) return;
    var wasDragging = armed && moved >= TAP_PX;
    dragging = false; armed = false;
    fig.classList.remove("is-drag");
    if (!wasDragging) { flip(); return; }
    var projected = rot + project(vel);
    springTo(faceOf(projected));
  }

  NS.medal = {
    init: function () {
      fig = document.getElementById("hero-medal");
      if (!fig) return;
      coin = document.getElementById("medal-coin");
      sideEl = document.getElementById("medal-side");
      if (!coin || !sideEl) return;
      buildEdges();
      render();

      fig.addEventListener("pointerdown", function (ev) {
        if (ev.button != null && ev.button !== 0) return;
        stopSpring();
        dragging = true;
        armed = false;
        moved = 0;
        startX = ev.clientX;
        startRot = rot;
        lastT = performance.now();
        fig.classList.add("is-drag");
        if (fig.setPointerCapture) { try { fig.setPointerCapture(ev.pointerId); } catch (e) { /* 忽略 */ } }
      });

      fig.addEventListener("pointermove", function (ev) {
        if (!dragging) return;
        var dx = ev.clientX - startX;
        moved = Math.max(moved, Math.abs(dx));
        /* 迟滞：越过阈值后才真正开始旋转，避免误触抖动 */
        if (!armed) {
          if (Math.abs(dx) < HYSTERESIS) return;
          armed = true;
          startX = ev.clientX;
          startRot = rot;
          vel = 0;
          lastT = performance.now();
          return;
        }
        var now = performance.now();
        var dt = Math.max((now - lastT) / 1000, 1 / 240);
        var delta = (ev.clientX - startX) * DRAG_RATIO;
        var next = startRot + delta;
        vel = (next - rot) / dt;
        rot = next;
        lastT = now;
        render();
      });

      fig.addEventListener("pointerup", endDrag);
      fig.addEventListener("pointercancel", endDrag);

      fig.addEventListener("keydown", function (ev) {
        var handled = true;
        if (ev.key === "ArrowRight") springTo(faceOf(rot) + 90);
        else if (ev.key === "ArrowLeft") springTo(faceOf(rot) - 90);
        else if (ev.key === "Enter" || ev.key === " ") flip();
        else if (ev.key === "Home") springTo(0);
        else handled = false;
        if (handled) ev.preventDefault();
      });

      fig.addEventListener("focus", function () {
        fig.setAttribute("aria-label", "普利兹克奖章，当前" + sideEl.textContent + "。方向键旋转，回车翻转");
      });
    }
  };
})();

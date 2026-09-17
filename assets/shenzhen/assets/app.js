/* ==========================================================================
   嵌入模块逻辑：地图渲染 / 头像标记 / 右侧信息面板 / 图例联动 / 滚轮转交

   标记布局原则
   ─────────────────────────────────────────────────────────────────
   1. 头像即位置标记：严格锚定实测坐标，不因拥挤而位移——图面即事实。
      相邻作品允许重叠，簇内沿对角线各错开 0.19 个标记直径，加白色描边
      显出层叠关系（像一叠硬币）；最外侧标记的位移 ≈ 0.34 个标记直径。
   2. 悬停 / 聚焦任一标记：右侧面板滑出展示作品信息，图例同步高亮。
   3. 本模块整幅嵌入主站首页；页面滚到底部继续下滑时，把滚轮转交父页面
      （父页面据此进入时间轴档案）——iframe 内的滚轮默认到不了外层。
   ========================================================================== */
(function () {
  'use strict';

  var B = window.SZ_BASE, W = B.W, H = B.H;
  var LIST = window.PRITZKER.buildings;
  var wrap = document.getElementById('mapWrap');
  var svg = document.getElementById('mapSvg');
  var avLayer = document.getElementById('avatarLayer');
  var card = document.getElementById('card');
  var ixWrap = document.getElementById('index');

  /* ------------------------------------------------------------ 1. 底图 */
  function paths(list) {
    return list.map(function (d) { return '<path d="' + d + '"/>'; }).join('');
  }

  (function drawBase() {
    var p = [];
    p.push('<g class="l-sea">' + paths(B.sea) + '</g>');
    p.push('<g class="l-land">' + paths(B.land) + '</g>');
    p.push('<g class="l-city">' + paths(B.city) + '</g>');
    p.push('<g class="l-terr">' + paths(B.terrainLow) + '</g>');
    p.push('<g class="l-terr l-terr-hi">' + paths(B.terrainHigh) + '</g>');
    p.push('<g class="l-water">' + paths(B.water) + '</g>');
    p.push('<g class="l-dist">' + B.districts.map(function (d) {
      return '<path d="' + d.d + '"/>';
    }).join('') + '</g>');
    p.push('<g class="l-cityline">' + paths(B.cityLine) + '</g>');
    p.push('<g class="l-label">' + B.labels.map(function (l) {
      return '<text x="' + l.x + '" y="' + l.y + '">' + l.name.replace('区', '') + '</text>';
    }).join('') + '</g>');
    svg.innerHTML = p.join('');
  })();

  /* ------------------------------------------------- 2. 布局计算（像素域） */
  /* 统一在「容器像素坐标」里算：真实点 × 缩放比 = 像素位置。 */
  var GEO = {};                      // id → {tx,ty,lx,ly, cluster}
  var markD = 34, scale = 1;
  var CLUSTER_UNITS = 26;            // 地理聚类阈值（地图单位，1 单位 ≈ 78m）

  function clusterize(items, thresh) {
    var par = {};
    items.forEach(function (p) { par[p.id] = p.id; });
    function find(x) { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; }
    for (var i = 0; i < items.length; i++) {
      for (var j = i + 1; j < items.length; j++) {
        var dx = items[i].tx - items[j].tx, dy = items[i].ty - items[j].ty;
        if (Math.sqrt(dx * dx + dy * dy) < thresh) {
          var a = find(items[i].id), b = find(items[j].id);
          if (a !== b) par[a] = b;
        }
      }
    }
    var map = {};
    items.forEach(function (p) {
      var r = find(p.id);
      (map[r] = map[r] || []).push(p);
    });
    return Object.keys(map).map(function (k) { return map[k]; });
  }

  function computeLayout() {
    var rect = wrap.getBoundingClientRect();
    if (!rect.width) return;
    scale = rect.width / W;

    var items = LIST.map(function (b) {
      var s = B.sites[b.id] || [W / 2, H / 2];
      return { id: b.id, x: s[0] * scale, y: s[1] * scale };
    });
    items.forEach(function (p) { p.tx = p.x; p.ty = p.y; });

    /* 相邻判定阈值：26 个地图单位 ≈ 2.0km。
       必须大于「蛇口三件」内部最大间距 K11↔太子广场 1.47km（18.8 单位），
       必须小于「蛇口↔深圳歌剧院」2.57km（32.8 单位）；
       可行窗口 18.8–32.8 单位，取中点 26 单位，两侧余量最大。
       阈值必须用「地图单位」定义、再乘 scale 换算成像素。 */
    var groups = clusterize(items, CLUSTER_UNITS * scale);

    groups.forEach(function (g) {
      var n = g.length;
      if (n === 1) {
        var p = g[0];
        p.lx = p.tx; p.ly = p.ty;
        p.cluster = 1;
        return;
      }
      /* 簇内沿对角线错位堆叠：承认重叠、但让人看出重叠——
         每个错开约 0.19 个标记直径，靠白色描边显出层次。 */
      var U = Math.max(3.5, markD * 0.19);
      var mid = (n - 1) / 2;
      g.forEach(function (p, i) {
        var k = i - mid;
        p.lx = p.tx + k * U;
        p.ly = p.ty - k * U * 0.62;
        p.cluster = n;
      });
    });

    items.forEach(function (p) { GEO[p.id] = p; });
  }

  /* ------------------------------------------------------- 3. 渲染标记 */
  var elById = {};

  function render() {
    avLayer.innerHTML = '';
    elById = {};

    LIST.forEach(function (b) {
      var g = GEO[b.id];
      if (!g) return;

      var av = document.createElement('a');
      av.className = 'av' + (g.cluster > 1 ? ' is-clustered' : '');
      av.href = 'detail.html?id=' + b.id;
      av.dataset.id = b.id;
      av.style.left = g.lx + 'px';
      av.style.top = g.ly + 'px';
      av.setAttribute('aria-label', b.name + ' · ' + b.architect);
      av.innerHTML = '<img src="' + b.avatar + '" alt="' + b.architect + '">';
      avLayer.appendChild(av);

      elById[b.id] = { av: av, b: b };

      av.addEventListener('mouseenter', function () { cancelHide(); activate(b.id); });
      av.addEventListener('mouseleave', scheduleHide);
      av.addEventListener('focus', function () { cancelHide(); activate(b.id); });
      av.addEventListener('blur', scheduleHide);
      av.addEventListener('click', function (e) { e.preventDefault(); togglePin(b.id); });
    });
  }

  /* -------------------------------------------------- 4. 右侧信息面板 */
  function factsHTML(b) {
    return b.facts.slice(0, 4).map(function (f) {
      return '<span>' + f[0] + ' <b>' + f[1] + '</b></span>';
    }).join('');
  }

  function buildCard(b) {
    card.innerHTML =
      (b.photo ? '<figure class="card-photo"><img src="' + b.photo + '" alt="' + b.name + '"></figure>' : '') +
      '<div class="card-name">' + b.name + '</div>' +
      '<div class="card-en">' + b.en + '</div>' +
      '<div class="card-arch">' +
        '<div class="pic"><img src="' + b.avatar + '" alt="' + b.architect + '"></div>' +
        '<div class="who">' + b.architect + '<span>' + b.architectEn + '</span></div>' +
        '<div class="card-prize">' +
          '<img class="card-medal" src="../brand/medal-front.png" alt="普利兹克奖章（正面）">' +
          '<span class="badge">Pritzker ' + b.prizeYear + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="card-tag">' + b.tagline + '</div>' +
      '<div class="card-facts">' + factsHTML(b) + '</div>' +
      '<a class="card-go" href="detail.html?id=' + b.id + '">查看详情 <i></i></a>';
  }

  var activeId = null, hideTimer = null, pinned = false;

  function activate(id) {
    if (activeId === id) return;
    var it = elById[id];
    if (!it) return;
    activeId = id;

    buildCard(it.b);
    card.classList.add('is-open');
    card.scrollTop = 0;

    LIST.forEach(function (x) {
      var e = elById[x.id];
      if (!e) return;
      var on = x.id === id;
      e.av.classList.toggle('is-active', on);
      e.av.classList.toggle('is-dim', !on);
    });

    ixWrap.classList.add('has-hover');
    ixWrap.querySelectorAll('.ix').forEach(function (n) {
      n.classList.toggle('is-active', n.dataset.id === id);
    });
  }

  function deactivate() {
    activeId = null;
    pinned = false;
    card.classList.remove('is-open');
    Object.keys(elById).forEach(function (k) {
      var e = elById[k];
      e.av.classList.remove('is-active', 'is-dim');
    });
    ixWrap.classList.remove('has-hover');
    ixWrap.querySelectorAll('.ix').forEach(function (n) { n.classList.remove('is-active'); });
  }

  /* 点击建筑点 / 图例项：固定高亮（再点同项或点空白解除）；查看详情走面板 */
  function togglePin(id) {
    if (pinned && activeId === id) { deactivate(); return; }
    pinned = true;
    cancelHide();
    if (activeId !== id) activate(id);
  }

  function scheduleHide() { if (!pinned) hideTimer = setTimeout(deactivate, 170); }
  function cancelHide() { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; } }

  card.addEventListener('mouseenter', cancelHide);
  card.addEventListener('mouseleave', scheduleHide);
  card.addEventListener('click', function () {
    if (activeId) location.href = 'detail.html?id=' + activeId;
  });
  wrap.addEventListener('mouseleave', scheduleHide);
  wrap.addEventListener('click', function (e) {
    if (e.target.closest('.av, .ix, .card')) return;
    deactivate();
  });

  /* ------------------------------------------- 5. 图例（叠放在图纸左上角） */
  LIST.forEach(function (b) {
    var a = document.createElement('a');
    a.className = 'ix';
    a.dataset.id = b.id;
    a.href = 'detail.html?id=' + b.id;
    a.innerHTML =
      '<span class="ix-logo" aria-hidden="true"><svg viewBox="0 0 24 24">' + b.logo + '</svg></span>' +
      '<span class="ix-name">' + b.name + '</span>' +
      '<span class="ix-yr">' + b.year + '</span>' +
      '<span class="ix-arch">' + b.architect + '</span>';
    a.addEventListener('mouseenter', function () { cancelHide(); activate(b.id); });
    a.addEventListener('mouseleave', scheduleHide);
    a.addEventListener('focus', function () { cancelHide(); activate(b.id); });
    a.addEventListener('blur', scheduleHide);
    a.addEventListener('click', function (e) { e.preventDefault(); togglePin(b.id); });
    ixWrap.appendChild(a);
  });

  /* ------------------------- 6. 滚轮转交父页面（跨文档滚轮不冒泡：
       平时由父页面代为滚动；滚到底部继续下滑则进入时间轴档案） */
  if (window.parent !== window) {
    window.addEventListener('wheel', function (ev) {
      var atTop = window.scrollY <= 0;
      var atBot = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
      var down = ev.deltaY > 0;
      if ((down && atBot) || (!down && atTop)) {
        try { window.parent.postMessage({ type: 'sz-wheel', dy: ev.deltaY }, '*'); } catch (e) { /* 忽略 */ }
      }
    }, { passive: true });
  }

  /* ------------------------------------------------------ 7. 键盘：Esc */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { cancelHide(); deactivate(); }
  });

  /* -------------------------------------------- 8. 尺寸自适应与重排 */
  /* 标记尺寸随地图宽度等比换算；布局随之重算，保证任何视口下
     重叠关系与紧凑度都稳定。 */
  function resizeAll() {
    var w = wrap.getBoundingClientRect().width;
    if (!w) return;
    var u = w / W;
    markD = Math.max(18, Math.min(52, 34 * u));
    wrap.style.setProperty('--av', markD.toFixed(1) + 'px');
    computeLayout();
    render();
    if (activeId) deactivate();
  }

  resizeAll();

  var rz;
  window.addEventListener('resize', function () {
    clearTimeout(rz);
    rz = setTimeout(resizeAll, 130);
  });

  // 首次进入做一次淡入，避免标记突然出现
  requestAnimationFrame(function () { wrap.classList.add('is-ready'); });
})();

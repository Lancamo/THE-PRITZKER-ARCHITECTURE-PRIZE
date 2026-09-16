/* ==========================================================================
   主页逻辑：地图渲染 / 标记布局 / 悬停卡片 / 索引联动

   标记布局原则
   ─────────────────────────────────────────────────────────────────
   1. 建筑 logo 圆严格锚定实测坐标，不因拥挤而位移——图面即事实。
      相邻作品的 logo 允许重叠，用层级与悬停区分，绝不用引线拉走。
   2. 唯一可移动的是「建筑师头像」。头像属于注记层，不是位置层，
      因此在作品簇正下方排成一行：不重叠、紧凑、顺序与 logo 错位方向一致。
   3. 位置精度由 logo 保证，识别性由头像保证，两者职责分离。
   ========================================================================== */
(function () {
  'use strict';

  var B = window.SZ_BASE, W = B.W, H = B.H;
  var LIST = window.PRITZKER.buildings;
  var wrap = document.getElementById('mapWrap');
  var svg = document.getElementById('mapSvg');
  var logoLayer = document.getElementById('logoLayer');
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
    p.push('<g class="l-tie" id="tieG"></g>');
    p.push('<g class="l-lead" id="leadG"></g>');
    svg.innerHTML = p.join('');
  })();

  var tieG = document.getElementById('tieG');
  var leadG = document.getElementById('leadG');

  /* ------------------------------------------------- 2. 布局计算（像素域） */
  /* 统一在「容器像素坐标」里算：真实点 × 缩放比 = 像素位置。
     这样标记尺寸（px）与邻域判断（px）量纲一致，不随视口漂移。 */
  var GEO = {};                      // id → {tx,ty,lx,ly,ax,ay, cluster}
  var logoD = 31, avatarD = 24, gap = 2, scale = 1;
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

    var lR = logoD / 2, aR = avatarD / 2;
    var items = LIST.map(function (b) {
      var s = B.sites[b.id] || [W / 2, H / 2];
      return { id: b.id, x: s[0] * scale, y: s[1] * scale };
    });
    items.forEach(function (p) { p.tx = p.x; p.ty = p.y; });

    /* 相邻判定阈值：26 个地图单位 ≈ 2.0km。
       这个值是从实际间距里解出来的，不是拍的：
         必须大于「蛇口三件」内部最大间距 K11↔太子广场 1.47km（18.8 单位），
           否则同属蛇口的三件会被拆散；
         必须小于「蛇口↔深圳歌剧院」2.57km（32.8 单位），
           否则 2.5km 外的歌剧院会被误并进蛇口簇。
       可行窗口 18.8–32.8 单位，取中点 26 单位，两侧余量最大。

       注意阈值必须用「地图单位」定义、再乘 scale 换算成像素，
       不能写成 logoD × 系数——logoD 在 resizeAll 里有 17px 下限，
       窗口一矮就被托底，阈值会跟着膨胀到 2.7km，歌剧院就又并回蛇口了。 */
    var groups = clusterize(items, CLUSTER_UNITS * scale);

    groups.forEach(function (g) {
      var n = g.length, lR = logoD / 2, aR = avatarD / 2;
      if (n === 1) {
        var p = g[0];
        p.lx = p.tx; p.ly = p.ty;
        p.ax = p.tx; p.ay = p.ty + lR + gap + aR;
        p.cluster = 1;
        return;
      }
      /* 簇内沿对角线错位堆叠。
         实测坐标只差 160m 的几件作品，任何「展开」都是失真——3 个 31px 的 logo
         要真正不重叠得占 90px 以上，那就把城市尺度画成假的了。
         所以选择「承认重叠、但让人看出重叠」：每个错开约 0.19 个 logo 直径，
         靠白色描边显出层次。最外侧标的位移 = 0.34 × logoD（与视口无关的定值），
         即整簇始终「贴着」真实点位，误差不超过 1/3 个标记直径。 */
      var U = Math.max(3.5, logoD * 0.19);
      var mid = (n - 1) / 2;
      g.forEach(function (p, i) {
        var k = i - mid;
        p.lx = p.tx + k * U;
        p.ly = p.ty - k * U * 0.62;
        p.cluster = n;
      });
      /* 头像是注记层、不承担定位，因此可以在簇下方整齐排成一行——
         水平排列比环形聚拢更「有序而不散」，且顺序与 logo 的错位方向一致，
         对应关系可自行推断。 */
      var AW = avatarD + 2;
      var totalW = n * AW - 2;
      var lx0 = (g[0].lx + g[n - 1].lx) / 2;
      var lyMax = Math.max.apply(null, g.map(function (p) { return p.ly; }));
      g.forEach(function (p, i) {
        p.ax = lx0 - totalW / 2 + AW / 2 + i * AW;
        p.ay = lyMax + lR + gap + aR + 2;
      });
    });

    relaxAvatars(items);
    items.forEach(function (p) { GEO[p.id] = p; });
  }

  /* 头像避让：只动注记层，位置层（logo）一格不移。
     两类冲突分开处理：
       头像 ✕ 头像 —— 只沿 y 推开。若两者 x 方向已经够开就不算压在一起，
                      这样簇内的头像行始终保持一条水平线，不会推成锯齿。
       头像 ✕ 别人的 logo —— logo 是实测位置，绝对不能动，只能把头像推开，
                      否则头像照片会盖住一件作品的图标。
     最后做总位移限幅，避免头像飘离自己的簇。 */
  function relaxAvatars(items) {
    var needAA = avatarD + 1;                       // 头像↔头像 最小中心距
    var needAL = (avatarD + logoD) / 2 + 1;         // 头像↔logo 最小中心距
    var maxPush = avatarD;                          // 单个头像最大位移
    var ox = {}, oy = {};
    items.forEach(function (p) { ox[p.id] = p.ax; oy[p.id] = p.ay; });

    for (var iter = 0; iter < 80; iter++) {
      var moved = false;
      for (var i = 0; i < items.length; i++) {
        for (var j = 0; j < items.length; j++) {
          if (i === j) continue;
          var a = items[i], b = items[j];

          if (j > i) {                              // 头像 ✕ 头像
            var dx = Math.abs(b.ax - a.ax);
            if (dx < needAA) {
              var dy = b.ay - a.ay;
              var dyNeed = Math.sqrt(needAA * needAA - dx * dx);
              if (Math.abs(dy) < dyNeed) {
                var push = (dyNeed - Math.abs(dy)) / 2;
                var s = dy >= 0 ? 1 : -1;
                a.ay -= s * push;
                b.ay += s * push;
                moved = true;
              }
            }
          }

          var vx = a.ax - b.lx, vy = a.ay - b.ly;   // 头像 ✕ 别人的 logo
          var d = Math.sqrt(vx * vx + vy * vy) || 0.01;
          if (d < needAL) {
            var k = (needAL - d) / d;
            a.ax += vx * k;
            a.ay += vy * k;
            moved = true;
          }
        }
      }
      if (!moved) break;
    }

    items.forEach(function (p) {
      var dx = p.ax - ox[p.id], dy = p.ay - oy[p.id];
      var d = Math.sqrt(dx * dx + dy * dy);
      if (d > maxPush) {
        p.ax = ox[p.id] + dx / d * maxPush;
        p.ay = oy[p.id] + dy / d * maxPush;
      }
    });
  }

  /* ------------------------------------------------------- 3. 渲染标记 */
  var elById = {};

  function render() {
    logoLayer.innerHTML = '';
    avLayer.innerHTML = '';
    elById = {};

    LIST.forEach(function (b) {
      var g = GEO[b.id];
      if (!g) return;

      var mk = document.createElement('a');
      mk.className = 'mk';
      mk.href = 'detail.html?id=' + b.id;
      mk.dataset.id = b.id;
      mk.style.left = g.lx + 'px';
      mk.style.top = g.ly + 'px';
      mk.setAttribute('aria-label', b.name + ' · ' + b.architect);
      mk.innerHTML = '<span class="mk-logo"><svg viewBox="0 0 24 24" aria-hidden="true">'
                   + b.logo + '</svg></span>';
      logoLayer.appendChild(mk);

      var av = document.createElement('a');
      av.className = 'av' + (g.cluster > 1 ? ' is-clustered' : '');
      av.href = 'detail.html?id=' + b.id;
      av.dataset.id = b.id;
      av.style.left = g.ax + 'px';
      av.style.top = g.ay + 'px';
      av.setAttribute('aria-label', b.architect + '，' + b.name);
      av.innerHTML = '<img src="' + b.avatar + '" alt="' + b.architect + '">';
      avLayer.appendChild(av);

      elById[b.id] = { mk: mk, av: av, b: b, geo: g };

      [mk, av].forEach(function (el) {
        el.addEventListener('mouseenter', function () { cancelHide(); activate(b.id); });
        el.addEventListener('mouseleave', scheduleHide);
        el.addEventListener('focus', function () { cancelHide(); activate(b.id); });
        el.addEventListener('blur', scheduleHide);
      });
    });

    /* 错位堆叠已让「头像正上方就是自己的 logo」，无需再画归属连线；
       静态图面上不出现任何引线。 */
    tieG.innerHTML = '';
  }

  /* -------------------------------------------------- 4. 悬停信息卡片 */
  function factsHTML(b) {
    return b.facts.slice(0, 3).map(function (f) {
      return '<span>' + f[0] + ' <b>' + f[1] + '</b></span>';
    }).join('');
  }

  function buildCard(b) {
    card.innerHTML =
      '<div class="card-top">' +
        '<div class="card-logo"><svg viewBox="0 0 24 24">' + b.logo + '</svg></div>' +
        '<div><div class="card-name">' + b.name + '</div>' +
        '<div class="card-en">' + b.en + '</div></div>' +
      '</div>' +
      '<div class="card-arch">' +
        '<div class="pic"><img src="' + b.avatar + '" alt="' + b.architect + '"></div>' +
        '<div class="who">' + b.architect + '<span>' + b.architectEn + '</span></div>' +
        '<div class="badge">Pritzker ' + b.prizeYear + '</div>' +
      '</div>' +
      '<div class="card-tag">' + b.tagline + '</div>' +
      '<div class="card-facts">' + factsHTML(b) + '</div>' +
      '<div class="card-go">查看详情 <i></i></div>';
  }

  function positionCard(el) {
    var cr = wrap.getBoundingClientRect();
    var mr = el.getBoundingClientRect();
    var cx = mr.left - cr.left + mr.width / 2;
    var cy = mr.top - cr.top + mr.height / 2;
    var cw = card.offsetWidth || 306;
    var ch = card.offsetHeight || 250;

    var below = (cy - mr.height / 2 - ch - 14) < 0;
    var top = below ? (cy + mr.height / 2 + 18) : (cy - mr.height / 2 - ch - 14);
    var left = Math.max(cw / 2 + 4, Math.min(cr.width - cw / 2 - 4, cx));

    card.style.left = left + 'px';
    card.style.top = top + 'px';
    card.classList.toggle('below', below);
  }

  var activeId = null, hideTimer = null;

  function activate(id) {
    if (activeId === id) return;
    var it = elById[id];
    if (!it) return;
    activeId = id;

    buildCard(it.b);
    card.classList.add('is-open');
    positionCard(it.av);

    LIST.forEach(function (x) {
      var e = elById[x.id];
      if (!e) return;
      var on = x.id === id;
      e.mk.classList.toggle('is-active', on);
      e.av.classList.toggle('is-active', on);
      e.mk.classList.toggle('is-dim', !on);
      e.av.classList.toggle('is-dim', !on);
    });

    // 动态建立「头像 → 实测位置」的对应：只在此刻画，静态图面保持干净
    var g = it.geo;
    var dx = g.lx - g.ax, dy = g.ly - g.ay;
    var len = Math.sqrt(dx * dx + dy * dy);
    leadG.innerHTML = len > 12
      ? '<line class="lead" x1="' + (g.ax / scale) + '" y1="' + (g.ay / scale)
        + '" x2="' + (g.lx / scale) + '" y2="' + (g.ly / scale) + '"/>'
        + '<circle class="lead-pt" cx="' + (g.lx / scale) + '" cy="' + (g.ly / scale) + '" r="3.4"/>'
      : '<circle class="lead-pt" cx="' + (g.lx / scale) + '" cy="' + (g.ly / scale) + '" r="3.4"/>';

    ixWrap.classList.add('has-hover');
    ixWrap.querySelectorAll('.ix').forEach(function (n) {
      n.classList.toggle('is-active', n.dataset.id === id);
    });
    it.mk.classList.add('is-top');
  }

  function deactivate() {
    activeId = null;
    card.classList.remove('is-open');
    leadG.innerHTML = '';
    Object.keys(elById).forEach(function (k) {
      var e = elById[k];
      e.mk.classList.remove('is-active', 'is-dim', 'is-top');
      e.av.classList.remove('is-active', 'is-dim');
    });
    ixWrap.classList.remove('has-hover');
    ixWrap.querySelectorAll('.ix').forEach(function (n) { n.classList.remove('is-active'); });
  }

  function scheduleHide() { hideTimer = setTimeout(deactivate, 170); }
  function cancelHide() { if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; } }

  card.addEventListener('mouseenter', cancelHide);
  card.addEventListener('mouseleave', scheduleHide);
  card.addEventListener('click', function () {
    if (activeId) location.href = 'detail.html?id=' + activeId;
  });
  wrap.addEventListener('mouseleave', scheduleHide);

  /* ------------------------------------------------------- 5. 底部索引 */
  LIST.forEach(function (b) {
    var a = document.createElement('a');
    a.className = 'ix';
    a.dataset.id = b.id;
    a.href = 'detail.html?id=' + b.id;
    a.innerHTML =
      '<div class="ix-top"><span class="ix-dot"></span><span class="ix-yr">' + b.year + '</span></div>' +
      '<div class="ix-name">' + b.short + '</div>' +
      '<div class="ix-arch">' + b.architect + '</div>';
    a.addEventListener('mouseenter', function () { cancelHide(); activate(b.id); });
    a.addEventListener('mouseleave', scheduleHide);
    a.addEventListener('focus', function () { cancelHide(); activate(b.id); });
    a.addEventListener('blur', scheduleHide);
    ixWrap.appendChild(a);
  });

  /* ------------------------------------------------------ 6. 键盘：Esc */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { cancelHide(); deactivate(); }
  });

  /* -------------------------------------------- 7. 尺寸自适应与重排 */
  /* 标记尺寸随地图宽度等比换算；布局随之重算，保证任何视口下
     重叠关系与紧凑度都稳定。 */
  function resizeAll() {
    var w = wrap.getBoundingClientRect().width;
    if (!w) return;
    var u = w / W;
    logoD = Math.max(17, Math.min(46, 31 * u));
    avatarD = Math.max(13, Math.min(34, 24 * u));
    gap = Math.max(1.5, 2 * u);
    wrap.style.setProperty('--mk', logoD.toFixed(1) + 'px');
    wrap.style.setProperty('--av', avatarD.toFixed(1) + 'px');
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

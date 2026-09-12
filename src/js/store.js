/* store.js · F 集成官 · 唯一数据源与全局状态
   依赖：util
   监听：无 · 发布：selection:change / hover:change / layer:change / route:change */
(function () {
  "use strict";
  var NS = (window.NS = window.NS || {});
  var U = NS.util;

  /* 大洲归属（维基表格未提供，按通行地理划分补充） */
  var REGION_OF = {
    "日本": "asia", "中国": "asia", "印度": "asia", "伊拉克": "asia",
    "英国": "europe", "法国": "europe", "西班牙": "europe", "意大利": "europe",
    "葡萄牙": "europe", "瑞士": "europe", "德国": "europe", "西德": "europe",
    "爱尔兰": "europe", "奥地利": "europe", "挪威": "europe", "荷兰": "europe", "丹麦": "europe",
    "美国": "na", "加拿大": "na", "墨西哥": "na",
    "巴西": "sa", "智利": "sa",
    "布基纳法索": "africa", "马里": "africa",
    "澳大利亚": "oceania"
  };
  var EN_OF = {
    "日本": "Japan", "中国": "China", "印度": "India", "伊拉克": "Iraq",
    "英国": "United Kingdom", "法国": "France", "西班牙": "Spain", "意大利": "Italy",
    "葡萄牙": "Portugal", "瑞士": "Switzerland", "德国": "Germany", "西德": "West Germany",
    "爱尔兰": "Ireland", "奥地利": "Austria", "挪威": "Norway", "荷兰": "Netherlands",
    "丹麦": "Denmark", "美国": "United States", "加拿大": "Canada", "墨西哥": "Mexico",
    "巴西": "Brazil", "智利": "Chile", "布基纳法索": "Burkina Faso", "澳大利亚": "Australia",
    "马里": "Mali"
  };
  var REGION_LABEL = { asia: "亚洲", europe: "欧洲", na: "北美", sa: "南美", africa: "非洲", oceania: "大洋洲" };
  var REGION_EN = { asia: "Asia", europe: "Europe", na: "N. America", sa: "S. America", africa: "Africa", oceania: "Oceania" };
  var REGION_ORDER = ["asia", "europe", "na", "sa", "africa", "oceania"];

  var D = null;            // 原始数据
  var byYear = {};         // year → edition
  var listeners = {};      // evt → [fn]
  var state = { selection: null, hover: null, layer: "none", route: "home", routeYear: null };
  var evtOfKey = { selection: "selection:change", hover: "hover:change", layer: "layer:change" };

  function emit(evt, payload) {
    (listeners[evt] || []).forEach(function (fn) { fn(payload); });
  }

  function regionOf(country) { return REGION_OF[country] || "europe"; }

  NS.store = {
    init: function (data) {
      D = data;
      byYear = {};
      D.editions.forEach(function (e) { byYear[e.year] = e; });

      /* 派生：国家统计（多重国籍分别计入，口径与 V1.0 一致） */
      var countryCount = {}, regionCount = {};
      D.editions.forEach(function (e) {
        e.laureates.forEach(function (l) {
          l.nationalities.forEach(function (n) {
            countryCount[n] = (countryCount[n] || 0) + 1;
            var g = regionOf(n);
            regionCount[g] = (regionCount[g] || 0) + 1;
          });
        });
      });
      this._countryCount = countryCount;
      this._regionCount = regionCount;
      this._countries = Object.keys(countryCount).map(function (name) {
        return { name: name, en: EN_OF[name] || name, region: regionOf(name), count: countryCount[name] };
      }).sort(function (a, b) { return b.count - a.count || a.name.localeCompare(b.name, "zh"); });
      this._regions = REGION_ORDER.filter(function (g) { return regionCount[g]; })
        .map(function (g) {
          return { id: g, cn: REGION_LABEL[g], en: REGION_EN[g], count: regionCount[g] };
        });

      /* 派生：作品地点聚合 */
      var placeMap = {};
      D.editions.forEach(function (e) {
        e.works.forEach(function (w) {
          if (typeof w.lat !== "number") return;
          var p = placeMap[w.country] || (placeMap[w.country] = {
            country: w.country, en: EN_OF[w.country] || w.country,
            count: 0, lat: 0, lng: 0, items: []
          });
          p.count += 1;
          p.lat += w.lat; p.lng += w.lng;
          p.items.push({ year: e.year, title_cn: w.title_cn, city: w.city });
        });
      });
      this._places = Object.keys(placeMap).map(function (k) {
        var p = placeMap[k];
        p.lat = p.lat / p.count; p.lng = p.lng / p.count;
        return p;
      }).sort(function (a, b) { return b.count - a.count || a.country.localeCompare(b.country, "zh"); });

      return this;
    },

    /* ---------- 数据 ---------- */
    editions: function () { return D.editions; },
    edition: function (year) { return byYear[year] || null; },
    countries: function () { return this._countries; },
    regions: function () { return this._regions; },
    places: function () { return this._places; },
    bands: function () { return D.bands || []; },
    lineage: function () { return D.lineage || []; },
    trivia: function () { return D.trivia || []; },
    regionsOf: function (country) { return regionOf(country); },
    regionLabel: function (g) { return REGION_LABEL[g] || g; },
    regionEn: function (g) { return REGION_EN[g] || g; },
    enOf: function (cn) { return EN_OF[cn] || cn; },

    bandOf: function (year) {
      var hit = (D.bands || []).filter(function (b) { return year >= b.from && year <= b.to; })[0];
      return hit || null;
    },

    /* 详情：基础届次 + （样板）完整档案合并 */
    dossier: function (year) {
      var ed = byYear[year];
      if (!ed) return null;
      var extra = (D.dossiers && D.dossiers[String(year)]) || null;
      /* 代表作：样板档案的条目优先，缺失的影像/说明用 editions 中的数据补齐
         （editions 的 photo/credit 由 tools/enrich_assets.py 依据抓取报告写入） */
      var extraWorks = (extra && extra.works) || [];
      var baseWorks = ed.works.map(function (w, i) {
        var ex = extraWorks[i] || {};
        return {
          title_cn: w.title_cn,
          title_en: w.title_en || ex.title_en || "",
          city: ex.city || w.city,
          country: w.country,
          completed: ex.completed || w.completed,
          photo: ex.photo || w.photo || null,
          credit: ex.credit || w.credit || null,
          note: ex.note || null
        };
      });
      extraWorks.slice(baseWorks.length).forEach(function (ex) { baseWorks.push(ex); });

      /* 评审辞：样板档案的手写版优先；缺失时取官网抓取的短引（tools/fetch_citations.py）。
         官网完整评审辞另存 citationFull，供详情页展开阅读 */
      var cite = (D.citations && D.citations[String(year)]) || null;
      var citation = (extra && extra.citation) || (cite && (cite.quote_en || cite.quote_cn) ? {
        cn: cite.quote_cn || "",
        en: cite.quote_en || "",
        source: (cite.source || "Jury Citation, The Pritzker Architecture Prize") + " " + year
      } : null);
      var citationFull = (cite && cite.en && (!citation || cite.en.length > citation.en.length * 1.4))
        ? { en: cite.en, groups: (D.citationAligned && D.citationAligned[String(year)]) || null }
        : null;

      /* 生平中英对齐（data/bio_cn_aligned.json 人工逐段核对）：每组 = 对应英文段的中文段
         文本（字符串组；兼容旧的段落下标写法）；空数组 = 该段无译文、只显示英文 */
      var bioParas = (D.bioCn && D.bioCn[String(year)] && D.bioCn[String(year)].paragraphs) || null;
      var bioAlign = (D.bioAligned && D.bioAligned[String(year)]) || null;
      var bioGroups = bioAlign ? bioAlign.map(function (ids) {
        return ids.map(function (i) { return typeof i === "number" ? (bioParas || [])[i] : i; }).filter(Boolean);
      }) : null;

      var out = {
        year: year,
        editionNo: U.editionNo(year),
        laureates: ed.laureates,
        works: baseWorks,
        full: !!extra,
        citation: citation,
        citationFull: citationFull,
        trivia: extra ? extra.trivia : null,
        /* 官网文本与项目（tools/fetch_pritzker_details.py 写入 editions.json） */
        bio: ed.bio || null,
        bioSource: ed.bioSource || null,
        /* 官网中文生平（tools/fetch_bio_cn.py）；中文站未覆盖的届次为 null */
        bioCn: (D.bioCn && D.bioCn[String(year)] && D.bioCn[String(year)].paragraphs) || null,
        bioGroups: bioGroups,
        projects: ed.officialProjects || [],
        /* 肖像以官网版（edition 级）为准；样板档案仅作为缺失时的回退 */
        portrait: ed.portrait || (extra && extra.portrait) || null,
        portraitCredit: ed.portrait ? ed.portraitCredit : ((extra && extra.portraitCredit) || null),
        firm: extra ? extra.firm : null
      };
      return out;
    },

    stats: function () {
      var people = 0, ages = [];
      D.editions.forEach(function (e) {
        people += e.laureates.length;
        e.laureates.forEach(function (l) {
          if (l.age_at_award != null) ages.push({ year: e.year, name: l.name_cn, age: l.age_at_award });
        });
      });
      ages.sort(function (a, b) { return a.age - b.age; });
      return {
        editions: D.editions.length,
        people: people,
        countries: this._countries.length,
        ageMin: ages[0], ageMax: ages[ages.length - 1]
      };
    },

    /* 选中项命中的届次集合（各视图统一判定） */
    hitsOf: function (sel) {
      var set = {};
      if (!sel) return set;
      D.editions.forEach(function (e) {
        var hit = false;
        if (sel.type === "year") {
          hit = e.year === sel.value;
        } else if (sel.type === "country") {
          hit = e.laureates.some(function (l) { return l.nationalities.indexOf(sel.value) !== -1; });
        } else if (sel.type === "region") {
          hit = e.laureates.some(function (l) {
            return l.nationalities.some(function (n) { return regionOf(n) === sel.value; });
          });
        } else if (sel.type === "place") {
          hit = e.works.some(function (w) { return w.country === sel.value; });
        }
        if (hit) set[e.year] = 1;
      });
      return set;
    },

    /* 悬停窗口：某届 ±5 年内的届次数组（与时间轴聚焦窗口同口径）——
       国籍图 / 地理图在悬停某届时按整个窗口命中（CONTRACT「选中规范」） */
    windowOf: function (year, radius) {
      var r = radius == null ? 5 : radius;
      var lo = +year - r, hi = +year + r;
      return D.editions.filter(function (e) { return e.year >= lo && e.year <= hi; });
    },

    /* 某届的国籍集合（图A 对 year 选中的命中） */
    countriesOfYear: function (year) {
      var ed = byYear[year];
      if (!ed) return [];
      var out = [];
      ed.laureates.forEach(function (l) { out = out.concat(l.nationalities); });
      return U.uniq(out);
    },

    /* ---------- 状态 ---------- */
    get: function () { return state; },
    set: function (patch) {
      var changed = [];
      Object.keys(patch).forEach(function (k) {
        if (state[k] !== patch[k]) { state[k] = patch[k]; changed.push(k); }
      });
      changed.forEach(function (k) {
        if (evtOfKey[k]) emit(evtOfKey[k], state[k]);
      });
      if (changed.indexOf("layer") === -1 && changed.length === 0) return;
      if (changed.some(function (k) { return k === "route" || k === "routeYear"; })) {
        emit("route:change", { route: state.route, year: state.routeYear });
      }
    },
    /* 点击语义：同目标再点 = 取消 */
    toggleSelection: function (sel) {
      var cur = state.selection;
      var same = cur && sel && cur.type === sel.type && cur.value === sel.value;
      state.selection = same ? null : (sel || null);
      emit("selection:change", state.selection);
    },
    clearSelection: function () {
      if (!state.selection) return;
      state.selection = null;
      emit("selection:change", null);
    },

    on: function (evt, fn) { (listeners[evt] = listeners[evt] || []).push(fn); },
    off: function (evt, fn) {
      listeners[evt] = (listeners[evt] || []).filter(function (f) { return f !== fn; });
    }
  };
})();

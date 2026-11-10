// مِرصاد · منطق الواجهة
(function () {
  "use strict";
  const LEVELS = ["low", "medium", "high", "critical"];
  const SYMBOL = { low: "○", medium: "◆", high: "▲", critical: "■" };
  const S = { lang: "ar", data: {}, map: null, selected: null, alerts: {} };

  // ---------- storage (آمن عند تعطّل التخزين) ----------
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); if (v == null) return d; try { return JSON.parse(v); } catch (e) { return v; } } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* تجاهل */ } }
  };

  // ---------- API (عند تشغيل الخادم) مع وضع عرض بدون خادم ----------
  const api = {
    on: false,
    token() { try { return sessionStorage.getItem("mirsad.token"); } catch (e) { return null; } },
    user() { try { return JSON.parse(sessionStorage.getItem("mirsad.user") || "null"); } catch (e) { return null; } },
    save(t, u) { try { if (t) { sessionStorage.setItem("mirsad.token", t); sessionStorage.setItem("mirsad.user", JSON.stringify(u)); } else { sessionStorage.clear(); } } catch (e) {} },
    async req(path, opts = {}) {
      const h = { "Content-Type": "application/json" }; const tk = api.token(); if (tk) h.Authorization = "Bearer " + tk;
      const r = await fetch("/api/v1" + path, { ...opts, headers: h });
      const body = await r.json().catch(() => null);
      if (!r.ok) { const e = new Error((body && body.message) || r.status); e.status = r.status; e.code = body && body.error; throw e; }
      return body;
    },
    async detect() { try { const c = new AbortController(); setTimeout(() => c.abort(), 1500);
      const r = await fetch("/api/v1/health", { signal: c.signal }); api.on = r.ok && (await r.json()).status === "ok"; } catch (e) { api.on = false; } }
  };

  // ---------- i18n ----------
  const t = (k, vars) => {
    let s = (I18N[S.lang] && I18N[S.lang][k]) ?? I18N.ar[k] ?? k;
    if (vars) for (const [a, b] of Object.entries(vars)) s = s.replaceAll("{" + a + "}", b);
    return s;
  };
  const lcName = (n) => (S.lang === "ar" && I18N.ar.lc_names[n]) || n;
  // وحدات وألوان الطبقات (U-FR7)
  const UNITS = { elev: [() => " " + t("m"), 0], slope_mean: [() => "°", 1], rain_annual_mm: [() => " " + t("mm"), 0],
    rain_p99_3d_mm: [() => " " + t("mm"), 0], soil_clay: [() => "%", 1], relief_1km: [() => " " + t("m"), 0],
    ndvi_now: [() => "", 2], ndvi_anomaly: [() => "", 2] };
  // تدرّجات NDVI: من الأرض الجرداء إلى النبات، والتغيّر متباعد حول الصفر (بني = انخفاض، أخضر = زيادة)
  const NDVI_RAMP = { ndvi_now: [[0, "#C9A574"], [0.2, "#B9B66A"], [0.4, "#5E9B4E"], [0.6, "#1F6B3A"]],
    ndvi_anomaly: [[-0.15, "#8C3B1F"], [-0.05, "#D59A4D"], [0, "#E9E4D8"], [0.05, "#8DBF7A"], [0.15, "#1F6B3A"]] };
  const LITH_COLORS = { plutonic: "#C98B6B", volcanic: "#8E4A5A", volcano_sedimentary: "#6F8E7A", sedimentary: "#D7B56D", other: "#8A8F99" };
  const sfmt = (n) => (Math.floor(Number(n) * 100) / 100).toFixed(2); // الدرجة تُقرّب للأسفل كي لا تظهر 0.80 لقطاع «مرتفع»
  const FMT = window.MirsadFmt;  // التواريخ والشعار حسب اللغة والوضع (web/format.js)
  const fmt = (n, d = 0) => Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const el = (tag, attrs = {}, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") e.className = v; else if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v);
    }
    kids.flat().forEach((c) => c != null && e.append(c.nodeType ? c : document.createTextNode(c)));
    return e;
  };
  const chip = (lv) => el("span", { class: "chip " + lv }, SYMBOL[lv] + " " + t("lv_" + lv));
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  function applyLang() {
    FMT.setLang(S.lang); FMT.applyBrand();
    const html = document.documentElement;
    html.lang = S.lang; html.dir = S.lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
    document.getElementById("langLabel").textContent = S.lang === "ar" ? "EN" : "ع";
    document.title = t("brand") + " · " + t("tagline");
    store.set("mirsad.lang", S.lang);
    renderUser();
    if (S.data.sectors) { renderLegend(); renderRank(); renderKpis(); renderAlerts(); renderTransparency(); renderFcSide(); renderSatSide(); if (S.selected) openDrawer(S.selected);
      if (S.map && S.map.getLayer("sec-fill")) restyleMap(); }
  }

  // ---------- theme ----------
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    store.set("mirsad.theme", theme);
    FMT.applyBrand();
    if (S.map && S.map.isStyleLoaded()) restyleMap();
  }
  function levelColors() { return Object.fromEntries(LEVELS.map((l) => [l, cssVar("--lv-" + l)])); }

  // ---------- data ----------
  async function loadJSON(p) { const r = await fetch(p); if (!r.ok) throw new Error(p + " " + r.status); return r.json(); }
  function levelOf(score) {
    const th = S.data.model.thresholds;
    return score >= th.critical ? "critical" : score >= th.high ? "high" : score >= th.medium ? "medium" : "low";
  }

  // ---------- map ----------
  function initMap() {
    // خرائط أساس من Esri بدون مفتاح API (خرائط CARTO صارت تطلب مفتاحًا خارج localhost)
    const esri = (svc) => [`https://server.arcgisonline.com/ArcGIS/rest/services/${svc}/MapServer/tile/{z}/{y}/{x}`];
    const canvasAttr = "Esri, HERE, Garmin, © OpenStreetMap contributors";
    const map = new maplibregl.Map({
      container: "map", center: [42.35, 18.35], zoom: 6.2, minZoom: 4, maxZoom: 13, attributionControl: false,
      style: { version: 8, sources: {
          dark: { type: "raster", tiles: esri("Canvas/World_Dark_Gray_Base"), tileSize: 256, maxzoom: 16, attribution: canvasAttr },
          light: { type: "raster", tiles: esri("Canvas/World_Light_Gray_Base"), tileSize: 256, maxzoom: 16, attribution: canvasAttr },
          sat: { type: "raster", tiles: esri("World_Imagery"), tileSize: 256, maxzoom: 18, attribution: "Imagery © Esri, Maxar, Earthstar Geographics" },
          lblDark: { type: "raster", tiles: esri("Canvas/World_Dark_Gray_Reference"), tileSize: 256, maxzoom: 16 },
          lblLight: { type: "raster", tiles: esri("Canvas/World_Light_Gray_Reference"), tileSize: 256, maxzoom: 16 },
          lblSat: { type: "raster", tiles: esri("Reference/World_Boundaries_and_Places"), tileSize: 256, maxzoom: 16 } },
        layers: [{ id: "bm-dark", type: "raster", source: "dark" }, { id: "bm-light", type: "raster", source: "light" },
          { id: "bm-sat", type: "raster", source: "sat", layout: { visibility: "none" } },
          { id: "lbl-dark", type: "raster", source: "lblDark" }, { id: "lbl-light", type: "raster", source: "lblLight" },
          { id: "lbl-sat", type: "raster", source: "lblSat", layout: { visibility: "none" } }] }
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
    S.map = map;
    map.on("load", () => {
      map.addSource("sectors", { type: "geojson", data: S.data.sectors, promoteId: "id" });
      map.addLayer({ id: "sec-fill", type: "fill", source: "sectors", paint: {} });
      map.addLayer({ id: "sec-line", type: "line", source: "sectors", paint: { "line-width": 0.4 } });
      map.addLayer({ id: "sec-sel", type: "line", source: "sectors", filter: ["==", ["get", "id"], ""], paint: { "line-width": 3 } });
      const ev = { type: "FeatureCollection", features: S.data.events.map((e) => ({ type: "Feature",
        geometry: { type: "Point", coordinates: [e.lon, e.lat] }, properties: { ...e, exact: e.usable_for_terrain === true } })) };
      map.addSource("events", { type: "geojson", data: ev });
      map.addLayer({ id: "ev", type: "circle", source: "events", paint: { "circle-radius": 6, "circle-stroke-width": 2 } });
      ["lbl-dark", "lbl-light", "lbl-sat", "sec-sel", "ev"].forEach((id) => map.moveLayer(id));  // أسماء المدن فوق القطاعات
      restyleMap();
      map.on("click", "sec-fill", (e) => openDrawer(e.features[0].properties.id));
      map.on("mouseenter", "sec-fill", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "sec-fill", () => (map.getCanvas().style.cursor = ""));
      map.on("click", "ev", (e) => {
        const p = e.features[0].properties;
        new maplibregl.Popup({ closeButton: false }).setLngLat(e.lngLat).setDOMContent(el("div", {},
          el("b", {}, t("popup_event") + " · " + p.point_id), el("br"), p.place, el("br"),
          `${t("date")}: ${p.event_date || t("unknown")}`, el("br"), `${t("precision")}: ${p.location_precision}`)).addTo(map);
        e.originalEvent.stopPropagation();
      });
    });
  }
  function restyleMap() {
    const m = S.map, c = levelColors(), dark = document.documentElement.dataset.theme === "dark";
    const sat = S.basemap === "sat";
    m.setLayoutProperty("bm-dark", "visibility", !sat && dark ? "visible" : "none");
    m.setLayoutProperty("bm-light", "visibility", !sat && !dark ? "visible" : "none");
    if (m.getLayer("bm-sat")) m.setLayoutProperty("bm-sat", "visibility", sat ? "visible" : "none");
    m.setLayoutProperty("lbl-dark", "visibility", !sat && dark ? "visible" : "none");
    m.setLayoutProperty("lbl-light", "visibility", !sat && !dark ? "visible" : "none");
    m.setLayoutProperty("lbl-sat", "visibility", sat ? "visible" : "none");
    const ramp = document.getElementById("ramp"), cat = document.getElementById("catLegend");
    const NONE = dark ? "#2B3A40" : "#D7D2C8";
    cat.hidden = true;
    if (S.colorBy === "lith_class" || S.colorBy === "fc72") {  // U-FR7 / U-FR6: طبقات فئوية
      ramp.hidden = true;
      const key = S.colorBy === "lith_class" ? "lith_class" : "fc72_level";
      const pal = S.colorBy === "lith_class" ? LITH_COLORS : c;
      const cats = S.colorBy === "lith_class" ? Object.keys(LITH_COLORS) : LEVELS;
      m.setPaintProperty("sec-fill", "fill-color", ["match", ["coalesce", ["get", key], "_"], ...cats.flatMap((k) => [k, pal[k]]), NONE]);
      m.setPaintProperty("sec-fill", "fill-opacity", sat ? 0.6 : 0.6);
      cat.hidden = false;
      cat.replaceChildren(...cats.map((k) => el("li", {}, el("i", { style: `background:${pal[k]}` }),
        S.colorBy === "lith_class" ? t("lith_" + k) : `${SYMBOL[k]} ${t("lv_" + k)}`)), el("li", {}, el("i", { style: `background:${NONE}` }),
        S.colorBy === "lith_class" ? t("lith_none") : t("no_value")));
    } else if (NDVI_RAMP[S.colorBy]) {  // Sentinel-2: تدرّج ثابت لا يتأثر بالقيم الشاذة
      const st = NDVI_RAMP[S.colorBy];
      m.setPaintProperty("sec-fill", "fill-color", ["case", ["==", ["typeof", ["get", S.colorBy]], "number"],
        ["interpolate", ["linear"], ["get", S.colorBy], ...st.flat()], NONE]);
      m.setPaintProperty("sec-fill", "fill-opacity", sat ? 0.6 : 0.62);
      ramp.hidden = true; cat.hidden = false;
      cat.replaceChildren(...st.map(([v, col]) => el("li", {}, el("i", { style: `background:${col}` }),
        (S.colorBy === "ndvi_anomaly" && v > 0 ? "+" : "") + fmt(v, 2))), el("li", {}, el("i", { style: `background:${NONE}` }), t("no_value")),
        el("li", { class: "cat-note" }, t(S.colorBy === "ndvi_now" ? "ndvi_leg" : "ndvi_ch_leg")));
    } else if (S.colorBy && S.colorBy !== "level") {  // U-FR7: تلوين حسب عامل رقمي
      const vals = S.data.sectors.features.map((f) => f.properties[S.colorBy]).filter((v) => typeof v === "number" && isFinite(v));
      const lo = vals.length ? Math.min(...vals) : 0, hi = vals.length ? Math.max(...vals) : 1, mid = (lo + hi) / 2 || 0.5;
      m.setPaintProperty("sec-fill", "fill-color", ["case", ["==", ["typeof", ["get", S.colorBy]], "number"],
        ["interpolate", ["linear"], ["get", S.colorBy], lo, "#3C5662", mid, "#D59A4D", Math.max(hi, mid + 1e-6), "#AC573A"], NONE]);
      m.setPaintProperty("sec-fill", "fill-opacity", sat ? 0.6 : 0.55);
      ramp.hidden = false;
      const [u, d] = UNITS[S.colorBy] || ["", 1];
      document.getElementById("rampMin").textContent = fmt(lo, d) + u();
      document.getElementById("rampMax").textContent = fmt(hi, d) + u();
    } else {
      ramp.hidden = true;
      const match = ["match", ["get", "level"], "critical", c.critical, "high", c.high, "medium", c.medium, c.low];
      m.setPaintProperty("sec-fill", "fill-color", match);
      m.setPaintProperty("sec-fill", "fill-opacity", ["match", ["get", "level"], "low", sat ? 0.12 : dark ? 0.22 : 0.18, "medium", sat ? 0.45 : 0.5, sat ? 0.65 : 0.72]);
    }
    m.setPaintProperty("sec-line", "line-color", dark ? "rgba(230,238,236,0.10)" : "rgba(19,36,42,0.12)");
    m.setPaintProperty("sec-sel", "line-color", cssVar("--accent"));
    m.setPaintProperty("ev", "circle-color", ["case", ["get", "exact"], cssVar("--text"), "rgba(0,0,0,0)"]);
    m.setPaintProperty("ev", "circle-stroke-color", cssVar("--text"));
    if (m.getLayer("cells")) m.setPaintProperty("cells", "circle-color",
      ["step", ["get", "s"], c.low, S.data.model.thresholds.medium, c.medium, S.data.model.thresholds.high, c.high, S.data.model.thresholds.critical, c.critical]);
  }
  async function toggleCells(on) {
    const m = S.map;
    if (on && !m.getSource("cells")) {
      toast(t("loading"));
      const rows = await loadJSON("data/cells.json");
      m.addSource("cells", { type: "geojson", data: { type: "FeatureCollection",
        features: rows.map(([la, lo, s]) => ({ type: "Feature", geometry: { type: "Point", coordinates: [lo, la] }, properties: { s } })) } });
      m.addLayer({ id: "cells", type: "circle", source: "cells", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 0.6, 8, 2, 11, 6], "circle-opacity": 0.85 } }, "sec-sel");
      restyleMap();
    }
    if (m.getLayer("cells")) m.setLayoutProperty("cells", "visibility", on ? "visible" : "none");
  }

  // ---------- side panel ----------
  function renderLegend() {
    const th = S.data.model.thresholds, ul = document.getElementById("legend"), rng = {
      low: `< ${th.medium.toFixed(2)}`, medium: `${th.medium.toFixed(2)}–${th.high.toFixed(2)}`,
      high: `${th.high.toFixed(2)}–${th.critical.toFixed(2)}`, critical: `≥ ${th.critical.toFixed(2)}` };
    ul.replaceChildren(...LEVELS.map((l) => el("li", {},
      el("span", { class: "sw", style: `background:var(--lv-${l})` }, SYMBOL[l]),
      el("span", {}, el("b", {}, t("lv_" + l)), " · ", el("span", { class: "muted" }, t("mean_" + l))),
      el("span", { class: "rng" }, rng[l]))));
  }
  function renderKpis() {
    const f = S.data.sectors.features.map((x) => x.properties);
    document.getElementById("kSectors").textContent = fmt(f.length);
    document.getElementById("kCritical").textContent = fmt(f.filter((p) => p.level === "critical").length);
    document.getElementById("kHigh").textContent = fmt(f.filter((p) => p.level === "high").length);
    document.getElementById("kEvents").textContent = fmt(S.data.events.length);
  }
  function renderRank() {
    const top = S.data.sectors.features.map((x) => x.properties).sort((a, b) => b.score - a.score).slice(0, 15);
    document.getElementById("rank").replaceChildren(...top.map((p) => el("li", {}, el("button", { onclick: () => openDrawer(p.id, true) },
      el("span", {}, el("span", { class: "sid" }, p.id), el("br"),
        el("span", { class: "meta" }, `${t("slope_max")} ${fmt(p.slope_max, 1)}° · ${fmt(p.elev)} ${t("m")}`)),
      el("span", {}, chip(p.level), " ", el("b", {}, sfmt(p.score)))))));
  }

  // ---------- drawer ----------
  function openDrawer(id, fly) {
    const f = S.data.sectors.features.find((x) => x.properties.id === id); if (!f) return;
    const P = f.properties; S.selected = id;
    if (S.map && S.map.getLayer("sec-sel")) S.map.setFilter("sec-sel", ["==", ["get", "id"], id]);
    if (fly && S.map) S.map.flyTo({ center: [P.peak[1], P.peak[0]], zoom: Math.max(S.map.getZoom(), 9) });
    const total = P.counts.reduce((a, b) => a + b, 0) || 1;
    const shap = P.shap || {}, maxShap = Math.max(1e-6, ...Object.values(shap).map(Math.abs));
    const geUrl = `https://earth.google.com/web/@${P.peak[0]},${P.peak[1]},${P.peak_vals.elevation}a,9000d,35y,0h,60t,0r`;
    const st = S.alerts[id];
    const canPropose = P.level === "high" || P.level === "critical";
    const body = el("div", {},
      el("p", { class: "muted", style: "margin:0" }, t("sector")),
      el("h2", { class: "d-title" }, P.id),
      el("div", { class: "score" }, el("b", {}, sfmt(P.score)), chip(P.level)),
      el("div", { class: "muted", style: "font-size:13px" }, `${t("max_in_sector")} · ${t("top_cell")}: ${sfmt(P.max)} · ${t("mean_score")}: ${sfmt(P.mean)}`),
      el("div", { class: "h-sec" }, t("cell_dist")),
      el("div", { class: "stack", role: "img", "aria-label": LEVELS.map((l, i) => `${t("lv_" + l)} ${P.counts[i]}`).join(", ") },
        ...LEVELS.map((l, i) => el("span", { style: `width:${(P.counts[i] / total) * 100}%;background:var(--lv-${l})`, title: `${t("lv_" + l)}: ${P.counts[i]}` }))),
      el("div", { class: "muted", style: "font-size:12px;margin-top:4px" }, LEVELS.map((l, i) => `${SYMBOL[l]} ${t("lv_" + l)} ${P.counts[i]}`).join(" · ")),
      el("dl", { class: "dl" },
        el("dt", {}, t("cells")), el("dd", {}, fmt(P.cells)),
        el("dt", {}, t("elev_mean")), el("dd", {}, `${fmt(P.elev)} ${t("m")}`),
        el("dt", {}, t("slope_mean")), el("dd", {}, `${fmt(P.slope_mean, 1)}°`),
        el("dt", {}, t("slope_max")), el("dd", {}, `${fmt(P.slope_max, 1)}°`),
        el("dt", {}, t("landcover")), el("dd", {}, lcName(P.landcover)),
        el("dt", {}, t("events_here")), el("dd", {}, fmt(P.events))),
      el("div", { class: "h-sec" }, t("peak_cell")),
      el("dl", { class: "dl" },
        el("dt", {}, t("elevation")), el("dd", {}, `${fmt(P.peak_vals.elevation)} ${t("m")}`),
        el("dt", {}, t("slope")), el("dd", {}, `${fmt(P.peak_vals.slope, 1)}°`),
        el("dt", {}, t("aspect")), el("dd", {}, P.peak_vals.aspect < 0 ? "—" : `${fmt(P.peak_vals.aspect, 0)}°`),
        el("dt", {}, t("lc")), el("dd", {}, lcName(P.peak_vals.landcover))),
      ...forecastBlock(P),
      ...satBlock(P),
      ...layersBlock(P),
      el("div", { class: "h-sec" }, t("shap_title")),
      el("div", { class: "bars" }, ...Object.entries(shap).map(([k, v]) => {
        const w = (Math.abs(v) / maxShap) * 50, pos = v >= 0, rtl = document.documentElement.dir === "rtl", grow = pos !== rtl;
        return el("div", { class: "shap-row" }, el("span", {}, t("feat")[k]),
          el("span", { class: "shap-bar", role: "img", "aria-label": `${t("feat")[k]} ${v >= 0 ? "+" : ""}${v.toFixed(3)}` },
            el("span", { class: "mid" }),
            el("i", { style: `${grow ? "left" : "right"}:50%;width:${w}%;background:${pos ? "var(--lv-high)" : "var(--accent)"}` })),
          el("span", { class: "v" }, (v >= 0 ? "+" : "") + v.toFixed(3)));
      })),
      el("p", { class: "note" }, t("shap_note")),
      P.calibrated != null ? el("p", { class: "prob" }, `${t("prob_cal")}: ${(P.calibrated * 100).toFixed(1)}%`) : "",
      el("div", { class: "actions" },
        el("a", { class: "btn ghost", href: geUrl, target: "_blank", rel: "noopener" }, t("ge_open")),
        el("a", { class: "btn ghost", href: `report.html#${P.id}`, target: "_blank", rel: "noopener" }, t("report_open"))),
      canPropose
        ? (() => { const b = el("button", { class: "btn", style: "width:100%;margin-top:8px", onclick: () => { propose(id); openDrawer(id); } },
            st ? t("proposed") : t("propose")); b.disabled = !!st; return b; })()
        : el("p", { class: "note" }, t("not_needed")));
    document.getElementById("drawerBody").replaceChildren(body);
    const d = document.getElementById("drawer"); d.classList.add("open"); d.setAttribute("aria-hidden", "false");
  }
  function closeDrawer() {
    S.selected = null; const d = document.getElementById("drawer"); d.classList.remove("open"); d.setAttribute("aria-hidden", "true");
    if (S.map && S.map.getLayer("sec-sel")) S.map.setFilter("sec-sel", ["==", ["get", "id"], ""]);
  }

  // ---------- forecast 24/48/72 h (U-FR6) ----------
  async function loadForecast() {
    S.forecast = null;
    if (!api.on) return renderFcSide();
    try {
      const r = await fetch("/api/v1/forecast"); if (!r.ok) return renderFcSide();
      const d = await r.json(); S.forecast = { ...d, by: Object.fromEntries(d.items.map((i) => [i.sector_id, i])) };
      S.data.sectors.features.forEach((f) => { const i = S.forecast.by[f.properties.id];
        f.properties.fc72_level = i ? i.horizons[i.horizons.length - 1].level : null; });
      if (S.map && S.map.getSource("sectors")) S.map.getSource("sectors").setData(S.data.sectors);
    } catch (e) { S.forecast = null; }
    renderFcSide();
  }
  // ---------- Sentinel-2 (ق-6) ----------
  async function loadSatellite() {
    S.sat = null;
    if (api.on) try {
      const r = await fetch("/api/v1/satellite");
      if (r.ok) { const d = await r.json(); S.sat = { ...d, by: Object.fromEntries(d.items.map((i) => [i.sector_id, i])) }; }
    } catch (e) { S.sat = null; }
    S.data.sectors.features.forEach((f) => { const i = S.sat && S.sat.by[f.properties.id];
      f.properties.ndvi_now = i ? i.ndvi_now : null; f.properties.ndvi_anomaly = i ? i.ndvi_anomaly : null; f.properties.s2_flag = i ? i.flag : null; });
    if (S.map && S.map.getSource("sectors")) S.map.getSource("sectors").setData(S.data.sectors);
    document.getElementById("lySat").disabled = !S.sat;
    renderSatSide(); renderTransparency();
  }
  function renderSatSide() {
    const n = document.getElementById("satSide"); if (!n) return; n.hidden = false;
    if (!S.sat) { n.textContent = t("s2_side_none"); return; }
    const drop = S.sat.items.filter((i) => i.flag === "drop").length;
    n.textContent = t("s2_side", { n: fmt(S.sat.scenes_now), a: FMT.fmtDay(S.sat.first_date), b: FMT.fmtDay(S.sat.last_date), d: fmt(drop) })
      + (S.sat.stale ? " · " + t("s2_stale") : "");
  }
  function toggleSatImage(on) {
    const m = S.map; if (!m || !S.sat) return;
    if (on && !m.getSource("s2")) {
      const [w, s, e, n] = S.sat.bounds;
      m.addSource("s2", { type: "image", url: S.sat.image_url, coordinates: [[w, n], [e, n], [e, s], [w, s]] });
      m.addLayer({ id: "s2-img", type: "raster", source: "s2", paint: { "raster-opacity": 1, "raster-fade-duration": 0 } }, "lbl-dark");
      m.getSource("s2") && m.once("idle", () => toast(t("s2_loaded", { d: FMT.fmtDay(S.sat.last_date) })));
    }
    if (m.getLayer("s2-img")) m.setLayoutProperty("s2-img", "visibility", on ? "visible" : "none");
  }
  function satBlock(P) {
    const s = S.sat && S.sat.by[P.id], h = el("div", { class: "h-sec" }, t("s2_title"));
    if (!s) return [h, el("p", { class: "note" }, t("s2_none"))];
    const v = (x, sign) => (x == null ? "—" : (sign && x > 0 ? "+" : "") + fmt(x, 2));
    const pct = (x) => (x == null ? "—" : Math.round(x * 100) + "%");
    return [h,
      el("dl", { class: "dl" },
        el("dt", {}, t("s2_now")), el("dd", { class: "mono" }, v(s.ndvi_now)),
        el("dt", {}, t("s2_base")), el("dd", { class: "mono" }, v(s.ndvi_base)),
        el("dt", {}, t("s2_change")), el("dd", { class: "mono" }, v(s.ndvi_change, true)),
        el("dt", {}, t("s2_anom")), el("dd", { class: "mono" }, v(s.ndvi_anomaly, true)),
        el("dt", {}, t("s2_clear")), el("dd", { class: "mono" }, `${pct(s.valid_now)} / ${pct(s.valid_base)}`),
        el("dt", {}, t("s2_flag")), el("dd", {}, s.flag === "drop" ? el("b", { class: "warn-t" }, t("s2_drop")) : s.flag === "stable" ? t("s2_stable") : t("s2_insuff"))),
      el("p", { class: "note" }, t("s2_window", { a: FMT.fmtDay(S.sat.window_now[0]), b: FMT.fmtDay(S.sat.window_now[1]), n: fmt(S.sat.scenes_now) })),
      S.sat.stale ? el("p", { class: "note warn-t" }, t("s2_stale")) : "",
      el("p", { class: "note" }, t("s2_note"))];
  }
  const riyadh = (iso) => FMT.fmtDate(iso, { zone: false });
  function renderFcSide() {
    const n = document.getElementById("fcSide"); if (!n) return; n.hidden = false;
    if (!S.forecast) { n.textContent = t("fc_side_none"); return; }
    const hi = S.forecast.items.filter((i) => ["high", "critical"].includes(i.horizons[i.horizons.length - 1].level)).length;
    n.textContent = t("fc_side", { n: fmt(hi), t: riyadh(S.forecast.issued_at) }) + (S.forecast.stale ? " · " + t("fc_stale") : "");
  }
  function forecastBlock(P) {
    const f = S.forecast && S.forecast.by[P.id];
    if (!f) return [el("div", { class: "h-sec" }, t("fc_title")), el("p", { class: "note" }, t("fc_none"))];
    return [el("div", { class: "h-sec" }, t("fc_title")),
      el("table", { class: "fc" }, el("thead", {}, el("tr", {}, el("th", {}, ""), ...f.horizons.map((h) => el("th", {}, t("fc_h", { h: h.h }))))),
        el("tbody", {},
          el("tr", {}, el("th", {}, t("fc_rain")), ...f.horizons.map((h) => el("td", { class: "mono" }, h.rain_mm == null ? "—" : `${fmt(h.rain_mm, 1)} ${t("mm")}`))),
          el("tr", {}, el("th", {}, t("fc_ratio")), ...f.horizons.map((h) => el("td", { class: "mono" }, h.ratio == null ? "—" : `${Math.round(h.ratio * 100)}%`))),
          el("tr", {}, el("th", {}, t("fc_level")), ...f.horizons.map((h) => el("td", {}, chip(h.level)))))),
      el("p", { class: "note" }, (f.threshold_mm ? t("fc_thr", { v: fmt(f.threshold_mm, 0) }) : t("fc_nothr")) + " · " + t("fc_issued", { t: riyadh(S.forecast.issued_at) })),
      S.forecast.stale ? el("p", { class: "note warn-t" }, t("fc_stale")) : "",
      el("p", { class: "note" }, t("fc_note"))];
  }
  function layersBlock(P) {
    if (P.rain_annual_mm == null && P.soil_clay == null && P.lith_class == null && P.relief_1km == null) return [];
    const v = (x, d, u) => (x == null ? "—" : `${fmt(x, d)}${u}`);
    return [el("div", { class: "h-sec" }, t("layers_title")),
      el("dl", { class: "dl" },
        el("dt", {}, t("l_rain")), el("dd", {}, v(P.rain_annual_mm, 0, " " + t("mm"))),
        el("dt", {}, t("l_rain99")), el("dd", {}, v(P.rain_p99_3d_mm, 0, " " + t("mm"))),
        el("dt", {}, t("l_max1")), el("dd", {}, v(P.rain_max1d_mm, 0, " " + t("mm"))),
        el("dt", {}, t("l_clay")), el("dd", {}, v(P.soil_clay, 1, "%")),
        el("dt", {}, t("l_sand")), el("dd", {}, v(P.soil_sand, 1, "%")),
        el("dt", {}, t("l_relief")), el("dd", {}, v(P.relief_1km, 0, " " + t("m"))),
        el("dt", {}, t("l_lith")), el("dd", {}, P.lith_class ? t("lith_" + P.lith_class) : "—"))];
  }

  // ---------- alerts (PRD 13.2) ----------
  function sectorsAtRisk() {
    return S.data.sectors.features.map((x) => x.properties).filter((p) => p.level === "high" || p.level === "critical")
      .sort((a, b) => b.score - a.score);
  }
  function propose(id) { if (api.on) return; if (!S.alerts[id]) { S.alerts[id] = { status: "pending", created_at: new Date().toISOString() }; saveAlerts(); } }
  function saveAlerts() { store.set("mirsad.alerts", S.alerts); renderAlerts(); }
  async function decideApi(id, status) {
    if (!api.token()) { const ok = await login(); if (!ok) return; }
    try {
      await api.req("/alerts", { method: "POST", body: JSON.stringify({ sector_id: id, action: status === "approved" ? "approve" : "dismiss" }) });
      toast(t(status === "approved" ? "approved_toast" : "dismissed_toast"));
    } catch (e) {
      if (e.status === 401) { api.save(null); renderUser(); return decideApi(id, status); }
      toast(e.code === "cooldown" ? t("cooldown") : e.status === 403 ? t("forbidden") : e.message);
    }
    await loadAlertsApi(); renderAlerts();
  }
  async function loadAlertsApi() {
    const r = await api.req("/alerts");
    S.alerts = {};
    r.items.forEach((a) => { const cur = S.alerts[a.sector_id]; if (!cur || a.status === "pending" || a.id > cur.id)
      S.alerts[a.sector_id] = { id: a.id, status: a.status, by: a.approved_by, at: a.decided_at, created_at: a.created_at }; });
  }
  // اسم المعتمِد في وضع العرض (بدون خادم): نافذة داخل الصفحة بدل prompt
  function askName() {
    return new Promise((resolve) => {
      const d = document.getElementById("loginDlg"), f = document.getElementById("loginForm");
      const pw = f.password, pwl = pw.closest("label"), h = d.querySelector("h2"), sub = d.querySelector("p.muted");
      f.reset(); pw.required = false; pwl.hidden = true; h.textContent = t("approver_prompt"); sub.textContent = t("offline_mode");
      document.getElementById("loginErr").textContent = "";
      const restore = () => { pw.required = true; pwl.hidden = false; h.textContent = t("login_title"); sub.textContent = t("login_sub"); };
      f.onsubmit = (ev) => {
        const cancel = ev.submitter && ev.submitter.value === "cancel";
        ev.preventDefault(); const name = f.username.value.trim();
        if (!cancel && !name) return;
        d.close(); restore(); resolve(cancel ? null : name);
      };
      d.showModal();
    });
  }
  function login() {
    return new Promise((resolve) => {
      const d = document.getElementById("loginDlg"), f = document.getElementById("loginForm"), er = document.getElementById("loginErr");
      er.textContent = ""; f.reset();
      f.onsubmit = async (ev) => {
        if (ev.submitter && ev.submitter.value === "cancel") { d.close(); resolve(false); return; }
        ev.preventDefault();
        try { const r = await api.req("/auth/login", { method: "POST", body: JSON.stringify({ username: f.username.value, password: f.password.value }) });
          api.save(r.token, { username: r.username, role: r.role }); renderUser(); d.close(); resolve(true);
        } catch (e) { er.textContent = t("login_failed"); }
      };
      d.showModal();
    });
  }
  function renderUser() {
    const b = document.getElementById("userBtn"), u = api.user();
    b.hidden = !api.on; if (!api.on) return;
    b.textContent = u ? `${u.username} · ${t("logout")}` : t("login_btn");
    b.onclick = () => { if (api.user()) { api.save(null); renderUser(); } else login(); };
  }
  function decide(id, status) {
    if (api.on) return decideApi(id, status);
    const prev = S.alerts[id];
    if (status === "approved" && prev && prev.status === "approved" && Date.now() - new Date(prev.at).getTime() < 864e5) { toast(t("cooldown")); return; }
    if (status === "approved") { askName().then((by) => { if (by) commitLocal(id, prev, status, by); }); return; }
    commitLocal(id, prev, status, "");
  }
  function commitLocal(id, prev, status, by) {
    S.alerts[id] = { ...(prev || {}), status, by, at: new Date().toISOString() };
    saveAlerts(); toast(t(status === "approved" ? "approved_toast" : "dismissed_toast"));
  }
  function reasons(p) {
    const r = [t("reason_slope", { v: fmt(p.slope_max, 1) }), t("reason_elev", { v: fmt(p.peak_vals.elevation) }), t("reason_lc", { v: lcName(p.peak_vals.landcover) })];
    if (p.events) r.unshift(t("reason_events", { v: p.events }));
    return r.join(" · ");
  }
  function renderAlerts() {
    let added = false;
    if (!api.on) sectorsAtRisk().forEach((p) => { if (!S.alerts[p.id]) { S.alerts[p.id] = { status: "pending", created_at: new Date().toISOString() }; added = true; } });
    if (added) store.set("mirsad.alerts", S.alerts);
    const fl = document.getElementById("fLevel"), fs = document.getElementById("fStatus");
    const lv0 = fl.value, st0 = fs.value;
    fl.replaceChildren(el("option", { value: "" }, t("all_levels")), ...["critical", "high"].map((l) => el("option", { value: l }, t("lv_" + l))));
    fs.replaceChildren(el("option", { value: "" }, t("all_status")), ...["pending", "approved", "dismissed"].map((s) => el("option", { value: s }, t("st_" + s))));
    fl.value = lv0; fs.value = st0;
    // تصفية بتاريخ اقتراح الإنذار (FR-U3) — بالتاريخ المحلي، والطرفان شاملان
    const ff = document.getElementById("fFrom").value, ft = document.getElementById("fTo").value;
    const day = FMT.isoDay;  // يوم الرياض بصيغة ISO للمقارنة فقط
    document.getElementById("fFromTxt").textContent = ff ? FMT.fmtDay(ff) : "";
    document.getElementById("fToTxt").textContent = ft ? FMT.fmtDay(ft) : "";
    const all = sectorsAtRisk();
    const rows = all.filter((p) => { const a = S.alerts[p.id] || {}, d = day(a.created_at);
      return (!fl.value || p.level === fl.value) && (!fs.value || a.status === fs.value) && (!ff || d >= ff) && (!ft || d <= ft); });
    document.getElementById("fCount").textContent = ff && ft && ff > ft ? t("bad_range") : t("f_count", { n: fmt(rows.length), t: fmt(all.length) });
    const tb = document.getElementById("alertRows");
    tb.replaceChildren(...(rows.length ? rows.map((p) => {
      const a = S.alerts[p.id] || { status: "pending" };
      return el("tr", {},
        el("td", { class: "mono" }, p.id), el("td", {}, chip(p.level)), el("td", { class: "mono" }, sfmt(p.score)),
        el("td", {}, reasons(p)), el("td", { style: "white-space:nowrap" }, a.created_at ? FMT.fmtDay(a.created_at) : "—"), el("td", {}, t("st_" + a.status)),
        el("td", {}, a.by ? `${a.by} · ${FMT.fmtDate(a.at)}` : "—"),
        el("td", { style: "white-space:nowrap" },
          el("button", { class: "btn ghost", onclick: () => { location.hash = "#map"; setTimeout(() => openDrawer(p.id, true), 60); } }, t("view")), " ",
          a.status === "pending" ? el("button", { class: "btn", onclick: () => decide(p.id, "approved") }, t("approve")) : "", " ",
          a.status === "pending" ? el("button", { class: "btn ghost", onclick: () => decide(p.id, "dismissed") }, t("dismiss")) : ""));
    }) : [el("tr", {}, el("td", { colspan: "8", class: "muted" }, t("no_alerts")))]));
    const sub = document.querySelector("#page-alerts .page-h p");
    if (sub) sub.textContent = t("alerts_sub") + (api.on ? "" : " · " + t("offline_mode"));
    document.getElementById("alertCount").textContent = fmt(Object.values(S.alerts).filter((a) => a.status === "pending").length);
  }

  // ---------- transparency ----------
  function renderTransparency() {
    const m = S.data.model, c = m.cleaning;
    if (m.comparisons) {
      const cm = m.comparisons, rows = [["m_rf", cm.random_forest_baseline], ["m_rf_seis", cm.random_forest_plus_seismic], ["m_mlp", cm.neural_network_mlp]].concat(cm.neural_network_tensorflow ? [["m_tf", cm.neural_network_tensorflow]] : []);
      document.getElementById("trCompare").replaceChildren(
        el("div", { class: "metric-grid" }, el("span", { class: "h" }, t("metric")), el("span", { class: "h" }, "ROC-AUC"), el("span", { class: "h" }, "PR-AUC"),
          ...rows.flatMap(([k, r]) => [el("span", {}, t(k)), el("b", {}, fmt(r.roc_auc, 3)), el("span", { class: "muted" }, fmt(r.pr_auc, 3))])),
        el("p", { class: "note" }, t("cmp_note")));
    }
    if (m.calibration) document.getElementById("trQuality").replaceChildren(
      el("dt", {}, t("q_status")), el("dd", {}, m.quality === "pass" ? "✓" : t("q_pass")),
      el("dt", {}, t("q_crs")), el("dd", { class: "mono" }, "EPSG:4326"),
      el("dt", {}, t("q_brier_raw")), el("dd", {}, fmt(m.calibration.brier_raw, 4)),
      el("dt", {}, t("q_brier_cal")), el("dd", {}, fmt(m.calibration.brier_calibrated, 4)),
      el("dt", {}, t("q_shap")), el("dd", {}, fmt(m.explanations.additivity_max_error, 6)),
      el("dt", {}, t("data_as_of")), el("dd", {}, FMT.fmtDay(m.trained_at)));
    document.getElementById("trWarn").textContent = t("tr_warn", { auc: m.spatial_cv.roc_auc, pos: m.training.positives });
    const dl = document.getElementById("trModel");
    dl.replaceChildren(
      el("dt", {}, t("version")), el("dd", {}, m.version), el("dt", {}, t("trained")), el("dd", {}, FMT.fmtDay(m.trained_at)),
      el("dt", {}, t("algorithm")), el("dd", { style: "font-weight:500" }, m.algorithm),
      el("dt", {}, t("features")), el("dd", {}, m.features.map((f) => t("feat")[f]).join("، ")),
      el("dt", {}, t("training")), el("dd", {}, t("pos_neg", { p: m.training.positives, n: fmt(m.training.negatives) })),
      el("dt", {}, t("thresholds")), el("dd", { class: "mono" }, `${m.thresholds.medium} / ${m.thresholds.high} / ${m.thresholds.critical}`));
    const rows = [["roc_auc", "roc_auc"], ["pr_auc", "pr_auc"], ["recall_high", "recall_at_high"], ["precision_high", "precision_at_high"]];
    document.getElementById("trMetrics").replaceChildren(
      el("div", { class: "metric-grid" }, el("span", { class: "h" }, t("metric")), el("span", { class: "h" }, t("spatial")), el("span", { class: "h" }, t("random")),
        ...rows.flatMap(([k, f]) => [el("span", {}, t(k)), el("b", {}, fmt(m.spatial_cv[f], 3)), el("span", { class: "muted" }, fmt(m.random_cv[f], 3))])),
      el("p", { class: "note" }, t("metrics_note")));
    const imp = m.feature_importance, mx = Math.max(...Object.values(imp));
    document.getElementById("trImp").replaceChildren(el("div", { class: "bars" }, ...Object.entries(imp).map(([k, v]) => el("div", { class: "bar-row" },
      el("span", {}, t("feat")[k]), el("span", { class: "bar" }, el("i", { style: `width:${(v / mx) * 100}%` })), el("span", { class: "v" }, fmt(v, 2))))));
    const dist = m.level_distribution, tot = Object.values(dist).reduce((a, b) => a + b, 0);
    document.getElementById("trDist").replaceChildren(el("div", { class: "bars" }, ...LEVELS.map((l) => el("div", { class: "bar-row" },
      el("span", {}, `${SYMBOL[l]} ${t("lv_" + l)}`), el("span", { class: "bar" }, el("i", { style: `width:${(dist[l] / tot) * 100}%;background:var(--lv-${l})` })),
      el("span", { class: "v" }, fmt(dist[l]))))));
    const src = [
      ["s_inventory", "s_inventory_u", c.landslide_events, "used"], ["s_terrain", "s_terrain_u", c.training_rows, "used"],
      ["s_grid", "s_grid_u", c.grid_points_with_features, "used"],
      ["s_rain", "s_rain_u", c.rainfall_rows, "not_used", { n: c.rainfall_regions_placeholder_coords.length }],
      ["s_eq", "s_eq_u", c.earthquakes, "not_used", { n: c.earthquakes }], ["s_factors", "s_factors_u", c.conditioning_factor_rows, "not_used"],
      ...Object.entries(m.public_data || {}).map(([k, d]) => ["raw:" + d.source, "pub_" + k, d.cells, d.used ? "used" : "layer",
        { cov: Math.round(d.coverage * 1000) / 10, lic: d.license || "" }]),
      ...(S.sat ? [["raw:Copernicus Sentinel-2 L2A (ESA · Earth Search)", "pub_s2", S.sat.scenes_now, "layer",
        { a: FMT.fmtDay(S.sat.first_date), b: FMT.fmtDay(S.sat.last_date) }]] : [])];
    document.getElementById("trSources").replaceChildren(
      el("thead", {}, el("tr", {}, el("th", {}, t("src_name")), el("th", {}, t("src_use")), el("th", {}, t("src_rows")), el("th", {}, t("src_status")))),
      el("tbody", {}, ...src.map(([n, u, rows, s, v]) => el("tr", {}, el("td", {}, n.startsWith("raw:") ? n.slice(4) : t(n)), el("td", {}, t(u, v)), el("td", { class: "mono" }, fmt(rows)),
        el("td", {}, el("span", { class: "chip " + (s === "used" ? "low" : "medium") }, t(s)))))));
    document.getElementById("trLimits").replaceChildren(...["lim1", "lim2", "lim3", "lim4", "lim5", "lim6"].map((k) => el("li", {},
      t(k, { pos: m.training.positives, neg: fmt(m.training.negatives), cells: fmt(c.grid_points_with_features), grid: fmt(c.grid_points_total) }))));
  }

  // ---------- routing ----------
  function route() {
    const page = (location.hash || "#map").slice(1);
    const known = ["map", "alerts", "transparency", "about"].includes(page) ? page : "map";
    document.querySelectorAll(".page").forEach((p) => (p.hidden = p.id !== "page-" + known));
    document.querySelectorAll(".tab").forEach((a) => a.classList.toggle("on", a.dataset.page === known));
    if (known === "map" && S.map) setTimeout(() => S.map.resize(), 30);
  }
  let toastTimer;
  function toast(msg) { const n = document.getElementById("toast"); n.textContent = msg; n.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => n.classList.remove("show"), 2600); }

  // ---------- splash ----------
  const splashT0 = Date.now();
  function splash(pct, key) {
    const b = document.getElementById("splashBar"), st = document.getElementById("splashStep");
    if (b) b.style.width = pct + "%"; if (st && key) st.textContent = t(key);
  }
  function splashDone() {
    splash(100, "sp_ready");
    const wait = Math.max(0, 1100 - (Date.now() - splashT0));
    setTimeout(() => { const n = document.getElementById("splash"); if (n) n.classList.add("done");
      window.dispatchEvent(new CustomEvent("mirsad:ready")); }, wait);
  }

  // ---------- boot ----------
  async function boot() {
    S.lang = store.get("mirsad.lang", "ar") === "en" ? "en" : "ar";
    S.alerts = store.get("mirsad.alerts", {});
    document.getElementById("langBtn").onclick = () => { S.lang = S.lang === "ar" ? "en" : "ar"; applyLang(); };
    document.getElementById("themeBtn").onclick = () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    document.getElementById("drawerClose").onclick = closeDrawer;
    document.getElementById("colorBy").onchange = (e) => { S.colorBy = e.target.value; if (S.map && S.map.getLayer("sec-fill")) restyleMap(); };
    document.querySelectorAll("input[name=bm]").forEach((r) => (r.onchange = () => { S.basemap = r.value; store.set("mirsad.basemap", r.value); if (S.map && S.map.getLayer("sec-fill")) restyleMap(); }));
    S.basemap = store.get("mirsad.basemap", "map") === "sat" ? "sat" : "map";
    document.querySelectorAll("input[name=bm]").forEach((r) => (r.checked = r.value === S.basemap));
    document.getElementById("lySectors").onchange = (e) => ["sec-fill", "sec-line"].forEach((l) => S.map.setLayoutProperty(l, "visibility", e.target.checked ? "visible" : "none"));
    document.getElementById("lyEvents").onchange = (e) => S.map.setLayoutProperty("ev", "visibility", e.target.checked ? "visible" : "none");
    document.getElementById("lyCells").onchange = (e) => toggleCells(e.target.checked).catch(() => toast(t("load_error")));
    document.getElementById("lySat").onchange = (e) => { try { toggleSatImage(e.target.checked); } catch (x) { toast(t("load_error")); } };
    ["fLevel", "fStatus", "fFrom", "fTo"].forEach((id) => (document.getElementById(id).onchange = renderAlerts));
    document.getElementById("fClear").onclick = () => { ["fLevel", "fStatus", "fFrom", "fTo"].forEach((id) => (document.getElementById(id).value = "")); renderAlerts(); };
    addEventListener("hashchange", route); addEventListener("keydown", (e) => e.key === "Escape" && closeDrawer());
    applyLang(); route(); splash(15, "sp_ui");
    try {
      splash(30, "sp_api"); await api.detect(); splash(55, "sp_data");
      const [sectors, events, model] = await Promise.all([
        loadJSON(api.on ? "/api/v1/risk" : "data/sectors.geojson"), loadJSON("data/landslides.json"),
        loadJSON(api.on ? "/api/v1/model/runs/latest" : "data/model.json")]);
      if (api.on && sectors.thresholds) model.thresholds = sectors.thresholds;
      S.data = { sectors, events, model };
      if (api.on) await loadAlertsApi();
      await loadForecast();
      await loadSatellite();
      renderUser();
      // AC-4: وسم البيانات المتقادمة
      const ageDays = (Date.now() - new Date(model.trained_at + "T00:00:00Z").getTime()) / 864e5;
      S.stale = api.on ? !!sectors.stale : ageDays > 30;
      const sc = document.getElementById("staleChip"); sc.hidden = !S.stale; sc.title = t("stale_note", { d: 30 });
      document.getElementById("verChip").textContent = model.version;
      document.getElementById("verChip").title = `${t("trained")}: ${FMT.fmtDay(model.trained_at)}`;
      applyLang(); splash(85, "sp_map"); initMap();
      let done = false; const fin = () => { if (!done) { done = true; splashDone(); } };
      S.map.once("load", fin); setTimeout(fin, 6000); // لا تعلق الشاشة إن تأخرت بلاطات الخريطة
    } catch (e) { console.error(e); toast(t("load_error")); splashDone(); }
  }
  window.MirsadApp = { t, openDrawer: (id) => openDrawer(id, true), closeDrawer, topSector: () =>
    S.data.sectors && S.data.sectors.features.map((x) => x.properties).sort((a, b) => b.score - a.score)[0].id };
  boot();
})();

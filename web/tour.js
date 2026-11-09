// مِرصاد · الدليل التفاعلي (جولة خطوة بخطوة)
(function () {
  "use strict";
  const A = () => window.MirsadApp;
  const STEPS = [
    { page: "map", sel: "#map" },
    { page: "map", sel: "#legend" },
    { page: "map", sel: ".layers" },
    { page: "map", sel: "#rank" },
    { page: "map", sel: "#drawer", before: () => A().openDrawer(A().topSector()) },
    { page: "alerts", sel: "#page-alerts .table-wrap", before: () => A().closeDrawer() },
    { page: "transparency", sel: "#trWarn" },
    { page: "map", sel: ".tools" },
    { page: "map", sel: "#tourBtn" }
  ];
  let i = 0, spot, card;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  const mk = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };

  function end() {
    spot && spot.remove(); card && card.remove(); spot = card = null;
    removeEventListener("resize", place); removeEventListener("keydown", keys);
    store.set("mirsad.tourSeen", "1");
  }
  function keys(e) {
    if (e.key === "Escape") end();
    const fwd = document.documentElement.dir === "rtl" ? "ArrowLeft" : "ArrowRight", back = fwd === "ArrowLeft" ? "ArrowRight" : "ArrowLeft";
    if (e.key === fwd) go(i + 1); if (e.key === back) go(i - 1);
  }
  function place() {
    const s = STEPS[i], el = document.querySelector(s.sel); if (!el || !spot) return;
    const r = el.getBoundingClientRect(), pad = 6;
    Object.assign(spot.style, { top: r.top - pad + "px", left: r.left - pad + "px", width: r.width + pad * 2 + "px", height: r.height + pad * 2 + "px" });
    const cw = card.offsetWidth, ch = card.offsetHeight, vw = innerWidth, vh = innerHeight, m = 14;
    let top, left;
    if (r.bottom + ch + m < vh) top = r.bottom + m; else if (r.top - ch - m > 0) top = r.top - ch - m; else top = Math.max(m, (vh - ch) / 2);
    left = Math.min(vw - cw - m, Math.max(m, r.left + r.width / 2 - cw / 2));
    if (r.width > vw * 0.6 && r.height > vh * 0.5) { top = r.top + 24; left = document.documentElement.dir === "rtl" ? r.left + 24 : r.right - cw - 24; }
    Object.assign(card.style, { top: top + "px", left: left + "px" });
  }
  function go(n) {
    if (n < 0 || n >= STEPS.length) { if (n >= STEPS.length) end(); return; }
    i = n; const s = STEPS[i], app = A(), tr = app.t("tour")[i];
    if ((location.hash || "#map").slice(1) !== s.page) location.hash = "#" + s.page;
    setTimeout(() => {
      s.before && s.before();
      card.replaceChildren(mk("h3", null, tr[0]), mk("p", null, tr[1]),
        Object.assign(mk("div", "tour-dots"), {}),
        (() => { const f = mk("div", "tour-foot");
          f.append(mk("span", "tour-n", `${i + 1} / ${STEPS.length}`));
          if (i > 0) { const b = mk("button", "btn ghost", app.t("tour_prev")); b.onclick = () => go(i - 1); f.append(b); }
          const nx = mk("button", "btn", i === STEPS.length - 1 ? app.t("tour_done") : app.t("tour_next")); nx.onclick = () => go(i + 1); f.append(nx);
          if (i < STEPS.length - 1) { const sk = mk("button", "btn ghost", app.t("tour_skip")); sk.onclick = end; f.append(sk); }
          return f; })());
      card.querySelector(".tour-dots").append(...STEPS.map((_, k) => mk("i", k === i ? "on" : "")));
      const el = document.querySelector(s.sel); if (el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
      setTimeout(place, 320); place();
      card.querySelector(".tour-foot .btn:not(.ghost)").focus();
    }, 120);
  }
  function start() {
    end(); document.querySelectorAll(".tour-invite").forEach((n) => n.remove());
    spot = mk("div", "tour-spot"); card = mk("div", "tour-card");
    card.setAttribute("role", "dialog"); card.setAttribute("aria-modal", "true");
    document.body.append(spot, card); addEventListener("resize", place); addEventListener("keydown", keys);
    go(0);
  }
  function invite() {
    if (store.get("mirsad.tourSeen")) return;
    const app = A(), box = mk("div", "tour-invite"); box.setAttribute("role", "dialog");
    const row = mk("div", "row"), a = mk("button", "btn", app.t("tour_start")), b = mk("button", "btn ghost", app.t("tour_later"));
    a.onclick = start; b.onclick = () => { store.set("mirsad.tourSeen", "1"); box.remove(); };
    row.append(a, b); box.append(mk("b", null, app.t("tour_invite_t")), mk("span", "muted", app.t("tour_invite_d")), row);
    document.body.append(box);
  }
  document.getElementById("tourBtn").addEventListener("click", start);
  addEventListener("mirsad:ready", () => setTimeout(invite, 400));
  window.MirsadTour = { start, end };
})();

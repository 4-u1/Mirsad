// مِرصاد · تنسيق التواريخ والأرقام والشعار حسب اللغة والوضع (مصدر واحد للخريطة والتقرير)
// العربية: أشهر عربية، تقويم ميلادي، أرقام لاتينية · الإنجليزية: en-GB · كل الأوقات بتوقيت الرياض.
(function () {
  "use strict";
  const LOC = { ar: "ar-SA-u-nu-latn-ca-gregory", en: "en-GB" };
  const TZ = "Asia/Riyadh";
  let lang = "ar";
  const parse = (v) => (v instanceof Date ? v : typeof v === "number" ? new Date(v) :
    /^\d{4}-\d{2}-\d{2}$/.test(String(v)) ? new Date(v + "T12:00:00Z") : new Date(v));  // تاريخ بلا وقت = منتصف يومه
  const ok = (d) => d instanceof Date && !isNaN(d);
  const F = {
    setLang(l) { lang = l === "en" ? "en" : "ar"; },
    lang: () => lang,
    // 10 نوفمبر 2026، 10:07 م (الرياض) · 10 Nov 2026, 22:07 (Riyadh)
    fmtDate(v, o = {}) {
      const d = parse(v); if (!v || !ok(d)) return "—";
      const s = d.toLocaleString(LOC[lang], o.time === false ? { day: "numeric", month: "long", year: "numeric", timeZone: TZ }
        : { day: "numeric", month: lang === "ar" ? "long" : "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: lang === "ar", timeZone: TZ });
      return o.time === false || o.zone === false ? s : s + (lang === "ar" ? " (الرياض)" : " (Riyadh)");
    },
    // 10 نوفمبر 2026 · 10 Nov 2026
    fmtDay(v) {
      const d = parse(v); if (!v || !ok(d)) return "—";
      return d.toLocaleDateString(LOC[lang], { day: "numeric", month: lang === "ar" ? "long" : "short", year: "numeric", timeZone: TZ });
    },
    fmtYear(v) { const d = typeof v === "number" && v < 10000 ? new Date(Date.UTC(v, 6, 1)) : parse(v); return ok(d) ? d.toLocaleDateString(LOC[lang], { year: "numeric", timeZone: TZ }) : "—"; },
    fmtNum(n, dgt = 0) { return Number(n).toLocaleString("en-US", { minimumFractionDigits: dgt, maximumFractionDigits: dgt }); },
    // يوم الرياض بصيغة ISO للمقارنة الداخلية فقط (لا يُعرض)
    isoDay(v) { const d = parse(v); return v && ok(d) ? new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(d) : ""; },
    theme: () => (document.documentElement.dataset.theme === "light" ? "light" : "dark"),
    brandLogo(l = lang, th = F.theme()) {
      return { src: `brand/logo-${l === "en" ? "en" : "ar"}-${th === "light" ? "light" : "dark"}.svg`,
        alt: l === "en" ? "Mirsad · Landslide Risk Prediction System" : "مِرصاد · نظام التنبؤ بمخاطر الانهيارات الأرضية" };
    },
    // يحدّث كل <img data-brand> (data-brand-theme يثبّت وضعًا معيّنًا، مثل ترويسة التقرير الداكنة)
    applyBrand() {
      document.querySelectorAll("img[data-brand]").forEach((im) => {
        const b = F.brandLogo(lang, im.dataset.brandTheme || F.theme());
        if (!im.src.endsWith(b.src)) im.src = b.src;
        im.alt = b.alt;
      });
    },
  };
  window.MirsadFmt = F;
})();

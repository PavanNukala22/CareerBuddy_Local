/*
 * Shared hero title + description translator for the activity module pages
 * (Speaking, Listening, Reading, Writing).
 *
 * The per-module scripts (speaking.js, listening.js, …) translate their own
 * static UI labels but never the activity NAME (hero <h1>) or the activity
 * DESCRIPTION/objective (the <p> under it). Those come straight from the
 * database in English, so before this script they stayed English even when the
 * learner picked another language. This fills exactly that gap and nothing
 * else — it does not touch questions, scoring, buttons, images or any other UI.
 *
 * It is intentionally self-contained: it reads the persisted language itself
 * and listens on #languageSelect, so it works no matter what order the module
 * scripts run in. Titles/descriptions are shown bilingually as
 * "Translated (Original English)" to match the rest of the app.
 */
(function () {
  "use strict";

  var LANGUAGE_PREF_KEY = "careerbuddy_selected_language";
  // Maps the selector's value to the Google Translate target-language code.
  var LANG_CODES = { vietnam: "vi", russian: "ru", arabic: "ar" };

  var hero = document.querySelector(".module-hero");
  if (!hero) return; // Only the module pages have a .module-hero.

  var select = document.getElementById("languageSelect");
  if (!select) return;

  // ── Collect the title + description elements (deduped) ────────────────────
  function firstMatch(selectors) {
    for (var i = 0; i < selectors.length; i++) {
      var el = hero.querySelector(selectors[i]);
      if (el) return el;
    }
    return null;
  }

  var titleEl = firstMatch([".activity-hero-title", "#activityTitle", "h1"]);
  var descEl = firstMatch([".activity-hero-objective", "#activityObjective"]);
  // Fallback: the paragraph immediately after the title is the objective.
  if (!descEl && titleEl) {
    var sib = titleEl.nextElementSibling;
    if (sib && sib.tagName === "P") descEl = sib;
  }

  var targets = [];
  [titleEl, descEl].forEach(function (el) {
    if (!el) return;
    var orig = (el.textContent || "").trim();
    if (!orig) return;
    el.dataset.i18nOrig = orig; // Remember the true English source.
    targets.push({ el: el, orig: orig });
  });
  if (!targets.length) return;

  // ── Google Translate helper (same endpoint the rest of the app uses) ──────
  var cache = {};
  function translateTo(text, langCode) {
    var key = text + "|" + langCode;
    if (cache[key]) return Promise.resolve(cache[key]);
    return fetch(
      "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=" +
        encodeURIComponent(langCode) +
        "&dt=t&q=" +
        encodeURIComponent(text)
    )
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data[0]) {
          var translated = data[0].map(function (x) { return x[0]; }).join("").trim();
          cache[key] = translated;
          return translated;
        }
        return text;
      })
      .catch(function () { return text; });
  }

  // ── Apply / restore ───────────────────────────────────────────────────────
  var currentLang = "english";

  function restoreEnglish() {
    currentLang = "english";
    targets.forEach(function (t) {
      t.el.textContent = t.orig;
      t.el.style.direction = "";
    });
  }

  function applyTranslation(value) {
    var langCode = LANG_CODES[value];
    if (!langCode) { restoreEnglish(); return; }
    currentLang = value;
    targets.forEach(function (t) {
      translateTo(t.orig, langCode).then(function (translated) {
        if (currentLang !== value) return; // Language changed mid-flight — drop.
        t.el.textContent = translated + " (" + t.orig + ")";
        t.el.style.direction = value === "arabic" ? "rtl" : "";
      });
    });
  }

  function applyForCurrentValue() {
    var value = select.value || "english";
    if (value === "english") restoreEnglish();
    else applyTranslation(value);
  }

  // Keep the visible dropdown pill in sync with the active language. The module
  // pages carry different dropdown markup (some use the shared include, some an
  // inline one) whose own label update can miss a restore that happens before it
  // is wired — so this owns the label centrally for every module variant.
  function syncDropdownLabel() {
    var wrapper = document.querySelector(".custom-lang-dropdown");
    if (!wrapper) return;
    var display = wrapper.querySelector(".currentLangDisplay");
    var opt = wrapper.querySelector('.lang-option[data-val="' + select.value + '"]');
    if (display && opt) display.innerHTML = opt.innerHTML;
  }

  // React to every change (user click, or the restore-driven change event).
  // The choice is applied to the current view only — never persisted — so a
  // refresh returns to English.
  select.addEventListener("change", function () {
    applyForCurrentValue();
    syncDropdownLabel();
  });

  // Always start in English on load — no previously selected language is
  // restored, so a refresh resets the hero title/description to English.
  function init() {
    applyForCurrentValue();
    syncDropdownLabel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

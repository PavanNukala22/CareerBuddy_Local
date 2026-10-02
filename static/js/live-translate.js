/*
 * Live page translation, shared by every Interactive Workshop page (GD, JAM,
 * Role Play) and generalised from the implementation already shipping on the
 * activity sub-activity page (templates/activities/sub_activity.html).
 *
 * Mechanism, unchanged from that page:
 *   - Google Translate's public endpoint is called directly from the browser
 *     (no backend involved) for whatever visible text is marked for
 *     translation.
 *   - Text is rendered bilingually: "<translated> (<original English>)".
 *   - Results are cached per (text, language) so re-selecting a language is
 *     instant, and the whole cache is silently pre-warmed after page load.
 *   - Arabic gets `direction: rtl`; English restores the untouched original.
 *
 * Usage — call once per page, after the DOM (and the language dropdown
 * include) are present:
 *
 *   LiveTranslate.init({
 *     headingMap: {                     // optional: id -> exact translations
 *       pageTitle: { en: 'GD Arena', vn: 'Đấu trường GD', ar: '...', ru: '...' },
 *     },
 *     dynamicSelectors: ['.gd-badge', '.gd-hero p'],  // live-translated via
 *                                                       // Google Translate
 *     blockSelectors: ['#topicDescription'],           // multi-line blocks,
 *                                                       // translated per line
 *   });
 *
 * `dynamicSelectors` is the one most pages need: point it at whatever static
 * copy should be readable in the selected language, the same way
 * sub_activity.html points it at its headings/instructions/tips.
 */
(function () {
  'use strict';

  const translationCache = {};

  async function translateTo(text, langCode) {
    if (!text || !text.trim()) return text;
    const key = text.trim() + '|' + langCode;
    if (translationCache[key]) return translationCache[key];
    try {
      const res = await fetch(
        'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=' +
        encodeURIComponent(langCode) + '&dt=t&q=' + encodeURIComponent(text.trim())
      );
      const data = await res.json();
      if (data && data[0]) {
        const translated = data[0].map((x) => x[0]).join('').trim();
        translationCache[key] = translated;
        return translated;
      }
    } catch (e) { /* silent — falls back to English below */ }
    return text.trim();
  }

  function langCodeFor(value) {
    return { vietnam: 'vi', arabic: 'ar', russian: 'ru' }[value] || null;
  }

  function init(config) {
    const languageSelect = document.getElementById('languageSelect');
    if (!languageSelect) return;

    const headingMap = config.headingMap || {};
    const dynamicSelectors = config.dynamicSelectors || [];
    const blockSelectors = config.blockSelectors || [];

    // Collect dynamic targets once. Each entry keeps the exact text node (when
    // the element has one) so translating never disturbs a sibling <i> icon
    // or badge inside the same element — the same approach sub_activity.html
    // uses so icons don't get wiped out by textContent replacement.
    const dynamicTargets = [];
    dynamicSelectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((el) => {
        if (el.closest('.custom-lang-dropdown')) return; // never translate the switcher itself
        const textNode = [...el.childNodes].find(
          (n) => n.nodeType === Node.TEXT_NODE && n.textContent.trim()
        );
        if (textNode) {
          dynamicTargets.push({ el, textNode, original: textNode.textContent.trim() });
        } else if (el.textContent.trim()) {
          dynamicTargets.push({ el, textNode: null, original: el.textContent.trim() });
        }
      });
    });

    const blockTargets = blockSelectors
      .map((selector) => document.querySelector(selector))
      .filter(Boolean);

    let currentLang = 'en';

    async function applyDynamicTranslation(langCode) {
      currentLang = langCode;
      const translations = await Promise.all(
        dynamicTargets.map((t) => translateTo(t.original, langCode))
      );
      if (currentLang !== langCode) return; // language changed again mid-flight
      translations.forEach((translated, i) => {
        const t = dynamicTargets[i];
        if (t.textNode) {
          t.textNode.textContent = translated + ' (' + t.original + ') ';
        } else {
          t.el.textContent = translated + ' (' + t.original + ')';
        }
      });
    }

    async function applyBlockTranslation(langCode) {
      for (const box of blockTargets) {
        if (!box.dataset.origLines) {
          const lines = box.innerText.split('\n').map((l) => l.trim()).filter(Boolean);
          box.dataset.origLines = JSON.stringify(lines);
        }
        const origLines = JSON.parse(box.dataset.origLines);
        if (!origLines.length) continue;
        const translations = await Promise.all(origLines.map((l) => translateTo(l, langCode)));
        if (currentLang !== langCode) return;
        box.innerHTML = translations
          .map((translated, i) =>
            `<p style="margin-bottom:6px;"><strong>${translated}</strong> ` +
            `<span style="font-weight:400;color:#94a3b8;">(${origLines[i]})</span></p>`
          )
          .join('');
      }
    }

    function restoreEnglish() {
      currentLang = 'en';
      for (const t of dynamicTargets) {
        if (t.textNode) {
          t.textNode.textContent = t.original + ' ';
        } else {
          t.el.textContent = t.original;
        }
      }
      for (const box of blockTargets) {
        if (box.dataset.origLines) {
          const lines = JSON.parse(box.dataset.origLines);
          box.innerHTML = lines.map((l) => `<p style="margin-bottom:6px;">${l}</p>`).join('');
        }
      }
    }

    function updateHeadings(lang) {
      const isArabic = lang === 'arabic';
      for (const [id, data] of Object.entries(headingMap)) {
        const el = document.getElementById(id);
        if (!el) continue;
        if (lang === 'english') {
          el.textContent = data.en;
          el.style.direction = '';
          continue;
        }
        const key = { vietnam: 'vn', arabic: 'ar', russian: 'ru' }[lang];
        const text = data[key] || data.en;
        el.innerHTML = `<span class="font-bold">${text}</span> ` +
          `<span class="text-slate-400 font-normal">(${data.en})</span>`;
        el.style.direction = isArabic ? 'rtl' : '';
      }
    }

    function updateLanguage() {
      const lang = languageSelect.value;
      updateHeadings(lang);

      const code = langCodeFor(lang);
      if (code) {
        applyDynamicTranslation(code);
        applyBlockTranslation(code);
      } else {
        restoreEnglish();
      }
    }

    updateLanguage();
    languageSelect.addEventListener('change', updateLanguage);

    // Silently translate everything into every supported language in the
    // background so switching later is a cache hit, not a network round trip.
    function prewarmCache() {
      const langCodes = ['vi', 'ar', 'ru'];
      const texts = new Set(dynamicTargets.map((t) => t.original));
      blockTargets.forEach((box) => {
        if (!box.dataset.origLines) {
          const lines = box.innerText.split('\n').map((l) => l.trim()).filter(Boolean);
          box.dataset.origLines = JSON.stringify(lines);
        }
        JSON.parse(box.dataset.origLines).forEach((l) => texts.add(l));
      });
      Object.values(headingMap).forEach((d) => texts.add(d.en));

      langCodes.forEach((lang) => {
        texts.forEach((text) => {
          if (!text) return;
          const key = text + '|' + lang;
          if (translationCache[key]) return;
          fetch(
            'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=' +
            encodeURIComponent(lang) + '&dt=t&q=' + encodeURIComponent(text)
          )
            .then((r) => r.json())
            .then((data) => {
              if (data && data[0]) {
                translationCache[key] = data[0].map((x) => x[0]).join('').trim();
              }
            })
            .catch(() => {});
        });
      });
    }

    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(prewarmCache, { timeout: 2000 });
    } else {
      setTimeout(prewarmCache, 800);
    }
  }

  window.LiveTranslate = { init };
})();

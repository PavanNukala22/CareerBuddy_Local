/* ===================================================
   Career Buddy – Main JavaScript
   =================================================== */

document.addEventListener('DOMContentLoaded', function () {

  // ── Navbar scroll effect ──────────────────────────
  const nav = document.getElementById('mainNav');
  if (nav) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 50) {
        nav.style.background = 'rgba(255,255,255,0.98)';
        nav.style.boxShadow  = '0 2px 20px rgba(0,0,0,.05)';
      } else {
        nav.style.background = 'rgba(255,255,255,0.98)';
        nav.style.boxShadow  = 'none';
      }
    }, { passive: true });
  }

  // ── Auto-dismiss toast messages ───────────────────
  document.querySelectorAll('.toast-message').forEach(el => {
    setTimeout(() => {
      const alert = bootstrap.Alert.getOrCreateInstance(el);
      if (alert) alert.close();
    }, 4500);
  });

  // ── Smooth scroll for anchor links ───────────────
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Activity card hover tilt ──────────────────────
  document.querySelectorAll('.activity-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect   = card.getBoundingClientRect();
      const x      = ((e.clientX - rect.left) / rect.width  - 0.5) * 6;
      const y      = ((e.clientY - rect.top)  / rect.height - 0.5) * 6;
      card.style.transform = `translateY(-6px) rotateX(${-y}deg) rotateY(${x}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  // ── Animate stat numbers on scroll ───────────────
  const statEls = document.querySelectorAll('.stat-card-value, .stat-number');
  if (statEls.length && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });
    statEls.forEach(el => observer.observe(el));
  }

  function animateCount(el) {
    const raw    = el.textContent.replace(/[^0-9]/g, '');
    const target = parseInt(raw, 10);
    if (isNaN(target) || target === 0) return;
    const duration = 800;
    const step     = 16;
    const steps    = Math.ceil(duration / step);
    let current    = 0;
    const suffix   = el.textContent.includes('+') ? '+' : '';
    const timer    = setInterval(() => {
      current += Math.ceil(target / steps);
      if (current >= target) { current = target; clearInterval(timer); }
      el.textContent = current + suffix;
    }, step);
  }

  // ── Progress bar animation ────────────────────────
  document.querySelectorAll('.progress-bar').forEach(bar => {
    const target = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => {
      bar.style.transition = 'width .8s ease';
      bar.style.width = target;
    }, 200);
  });

  // ── Form input focus effects ──────────────────────
  document.querySelectorAll('.auth-form .form-control').forEach(input => {
    const parent = input.closest('.mb-3') || input.closest('.mb-4');
    if (!parent) return;
    input.addEventListener('focus',  () => parent.classList.add('focused'));
    input.addEventListener('blur',   () => parent.classList.remove('focused'));
  });

  // Writing word counts are owned by exercises.js (initWriting). A second
  // listener here used to overwrite its colour using a fixed 50-word rule,
  // so a prompt could show green while the submit button stayed disabled.

  // ── Global Back Button ────────────────────────────
  const backBtn = document.getElementById('globalBackBtn');
  if (backBtn) {
    // Define paths that are "main" pages — no back button needed
    const mainPages = [
      /^\/$/, 
      /^\/activities\/?$/,
      /^\/dashboard\/?$/,
      /^\/employer\/?$/,
      /^\/employer\/dashboard\/?$/,
      /^\/accounts\/login\/?$/,
      /^\/users\/login\/?$/,
      /^\/login\/?$/,
      /^\/register\/?$/,
      /^\/subject\/?$/,
    ];
    const path = window.location.pathname;
    const isMainPage = mainPages.some(re => re.test(path));
    // Only show if not a main page AND browser has history to go back to
    if (!isMainPage && window.history.length > 1) {
      backBtn.style.display = 'flex';
    }
  }

  // ── Global Language Translation for Instructions & Learning Tips ──
  const translationCache = {};

  async function translateText(text, targetLang) {
      if (!text || !text.trim()) return '';
      const cleanText = text.trim();
      const cacheKey = `${targetLang}-${cleanText}`;
      if (translationCache[cacheKey]) {
          return translationCache[cacheKey];
      }
      try {
          const response = await fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=${targetLang}&dt=t&q=${encodeURIComponent(cleanText)}`);
          const data = await response.json();
          if (data && data[0]) {
              const translated = data[0].map(x => x[0]).join('').trim();
              translationCache[cacheKey] = translated;
              return translated;
          }
      } catch (e) {
          console.error('Translation error:', e);
      }
      return null;
  }

  async function translateSentenceBySentence(text, targetLang) {
      if (!text || !text.trim()) return '';
      const sentenceRegex = /[^.!?]+[.!?]+(?:\s|$)/g;
      let sentences = text.match(sentenceRegex);
      if (!sentences) {
          sentences = [text];
      }

      // Fire all sentence translations in parallel
      const results = await Promise.all(
          sentences.map(s => {
              const trimmed = s.trim();
              if (trimmed.length > 1) {
                  return translateText(trimmed, targetLang).then(translated => ({ s, trimmed, translated }));
              }
              return Promise.resolve({ s, trimmed, translated: null });
          })
      );

      return results.map(({ s, trimmed, translated }) => {
          if (translated) {
              const spaceMatch = s.match(/^\s*/);
              const trailingSpaceMatch = s.match(/\s*$/);
              return `${spaceMatch[0]}${translated} (${trimmed})${trailingSpaceMatch[0]}`;
          }
          return s;
      }).join('');
  }

  async function translateElement(el, targetLang) {
      if (el.hasAttribute('data-translating') || el.hasAttribute('data-translated')) return;
      el.setAttribute('data-translating', 'true');
      el.setAttribute('data-orig-html', el.innerHTML);

      const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
      const textNodes = [];
      let n;
      while (n = walk.nextNode()) {
          if (n.nodeValue.trim().length > 0) {
              textNodes.push(n);
          }
      }

      for (const node of textNodes) {
          const text = node.nodeValue;
          const translated = await translateSentenceBySentence(text, targetLang);
          if (translated) {
              node.nodeValue = translated;
          }
      }

      el.removeAttribute('data-translating');
      el.setAttribute('data-translated', 'true');
  }

  async function applyGlobalTranslations() {
      const languageSelect = document.getElementById('languageSelect');
      if (!languageSelect) return;

      const targetLang = languageSelect.value;
      const targets = document.querySelectorAll(
          // Original targets
          '#instructionsBox, .instructions-text, .exercise-instructions, ' +
          '.writing-guide, .fill-hint, ' +
          '.tips-list li, .tip-item, ' +
          '.tips-card li, .tips-card p, ' +
          '#quickTipText, #tipReadingContent, ' +
          // Expanded targets for full page UI translation
          '#descOverview, .sub-description, .activity-hero-title, .activity-hero-objective, ' +
          '.sub-nav-title, h2.text-white, .exercise-title, .breadcrumb-item a, .breadcrumb-item.active, ' +
          '.sub-title, .btn, .badge, .sub-status-badge, .exercise-type-label, ' +
          '.mark-complete-card h6, .mark-complete-card p, ' +
          '.info-card-header span, .content-card-header span, h4.mb-4, .completed-banner, ' +
          '.activity-hero-meta span, .sub-meta span, .text-white-50, .activity-hero-number'
      );

      // Always restore to original English HTML first before applying new translations
      for (const el of targets) {
          if (el.hasAttribute('data-orig-html')) {
              el.innerHTML = el.getAttribute('data-orig-html');
              // We do not remove data-orig-html so we can restore it again later if needed
              el.removeAttribute('data-translated');
              el.removeAttribute('data-translating');
          }
          el.style.direction = '';
          el.style.textAlign = '';
      }

      // Global auto-translation disabled per user request
      /*
      if (targetLang === 'vietnam' || targetLang === 'arabic') {
          const langCode = targetLang === 'vietnam' ? 'vi' : 'ar';
          const isArabic = targetLang === 'arabic';
          
          for (const el of targets) {
              await translateElement(el, langCode);
              if (isArabic) {
                  el.style.direction = 'rtl';
                  el.style.textAlign = 'right';
              }
          }
      }
      */
  }

  const languageSelect = document.getElementById('languageSelect');
  if (languageSelect) {
      languageSelect.value = "english";

      applyGlobalTranslations();

      languageSelect.addEventListener('change', function() {
          applyGlobalTranslations();
      });

      // ── Pre-warm translation cache in background ──────────────────────────
      // After page loads, silently translate all target elements into all
      // supported languages so switching feels instant (cache hit).
      function prewarmGlobalCache() {
          const langCodes = ['vi', 'ar', 'ru'];
          const targets = document.querySelectorAll(
              '#instructionsBox, .instructions-text, .exercise-instructions, ' +
              '.writing-guide, .fill-hint, ' +
              '.tips-list li, .tip-item, ' +
              '.tips-card li, .tips-card p, ' +
              '#quickTipText, #tipReadingContent'
          );

          const texts = new Set();
          targets.forEach(el => {
              const txt = el.innerText ? el.innerText.trim() : el.textContent.trim();
              if (txt.length > 1) texts.add(txt);
          });

          langCodes.forEach(lang => {
              [...texts].forEach(text => {
                  const key = `${lang}-${text}`;
                  if (!translationCache[key]) {
                      fetch(
                          `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=${lang}&dt=t&q=${encodeURIComponent(text)}`
                      )
                      .then(r => r.json())
                      .then(data => {
                          if (data && data[0]) {
                              translationCache[key] = data[0].map(x => x[0]).join('').trim();
                          }
                      })
                      .catch(() => {});
                  }
              });
          });
      }

      if (typeof requestIdleCallback !== 'undefined') {
          requestIdleCallback(() => prewarmGlobalCache(), { timeout: 2000 });
      } else {
          setTimeout(prewarmGlobalCache, 800);
      }
  }

});

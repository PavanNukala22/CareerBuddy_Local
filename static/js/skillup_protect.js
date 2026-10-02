/*
 * Skill Up content protection
 * ---------------------------
 * Blocks copy, cut, paste, print, select-all, text selection, drag-out and the
 * right-click menu across the whole Skill Up module.
 *
 * Loaded by:
 *   - templates/skillup/skillup_hub.html                      (/skill-up/)
 *   - skillup_assessment/templates/skillup_assessment/_skillup_base.html
 *                                                              (/skill-up/assessment/...)
 *
 * The hub shows every lesson (CEFR, Vocabulary, Aptitude, TechCenter, mock
 * tests...) inside a same-origin <iframe id="frame">. Key presses and mouse
 * events inside an iframe never reach the parent page, so this script also
 * installs itself into every same-origin iframe document, every time that
 * iframe navigates to a new lesson.
 */
(function () {
  'use strict';

  var FLAG = '__skillupProtected';

  // Letters blocked with Ctrl (Windows/Linux) or Cmd (macOS).
  //   a = select all, c = copy, x = cut, v = paste, p = print,
  //   s = save page (would save the full text), u = view source.
  var BLOCKED_LETTERS = { a: 1, c: 1, x: 1, v: 1, p: 1, s: 1, u: 1 };
  var BLOCKED_CODES = { KeyA: 1, KeyC: 1, KeyX: 1, KeyV: 1, KeyP: 1, KeyS: 1, KeyU: 1 };

  function stop(e) {
    if (e.cancelable) { e.preventDefault(); }
    e.stopPropagation();
    if (e.stopImmediatePropagation) { e.stopImmediatePropagation(); }
    return false;
  }

  function isEditable(node) {
    if (!node || node.nodeType !== 1) { node = node && node.parentElement; }
    if (!node) { return false; }
    var tag = node.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') { return true; }
    return !!node.isContentEditable;
  }

  function isBlockedShortcut(e) {
    var key = (e.key || '').toLowerCase();
    var mod = e.ctrlKey || e.metaKey;
    if (mod && (BLOCKED_LETTERS[key] || BLOCKED_CODES[e.code])) { return true; }
    // Legacy clipboard shortcuts: Ctrl+Insert (copy), Shift+Insert (paste),
    // Shift+Delete (cut).
    if (key === 'insert' && (e.ctrlKey || e.shiftKey)) { return true; }
    if (key === 'delete' && e.shiftKey && !e.ctrlKey) { return true; }
    return false;
  }

  var CSS =
    'html, body, body * {' +
    '  -webkit-user-select: none !important;' +
    '  -moz-user-select: none !important;' +
    '  -ms-user-select: none !important;' +
    '  user-select: none !important;' +
    '  -webkit-touch-callout: none !important;' +
    '}' +
    // Form fields stay selectable so the caret and typing still work normally.
    // Copying out of them and pasting into them is still blocked below.
    'input, textarea, [contenteditable=""], [contenteditable="true"] {' +
    '  -webkit-user-select: text !important;' +
    '  -moz-user-select: text !important;' +
    '  user-select: text !important;' +
    '}' +
    '::selection { background: transparent !important; }' +
    'input::selection, textarea::selection { background: #b3d4fc !important; }' +
    // Browser-menu printing (File > Print) prints a blank notice instead of content.
    '@media print {' +
    '  html, body { background: #fff !important; }' +
    '  body > * { display: none !important; }' +
    '  body::after {' +
    '    content: "Printing is disabled for Skill Up content.";' +
    '    display: block !important; padding: 40px; font: 16px sans-serif; color: #000;' +
    '  }' +
    '}';

  function injectStyle(doc) {
    if (doc.getElementById('skillup-protect-style')) { return; }
    var style = doc.createElement('style');
    style.id = 'skillup-protect-style';
    style.textContent = CSS;
    (doc.head || doc.documentElement).appendChild(style);
  }

  function lockClipboardApis(win, doc) {
    // Page scripts (e.g. "Copy code" buttons in the Tech lessons) cannot
    // write to or read from the clipboard.
    var rejecter = function () {
      return Promise.reject(new Error('Clipboard access is disabled in Skill Up.'));
    };
    try {
      var cb = win.navigator && win.navigator.clipboard;
      if (cb) {
        ['writeText', 'write', 'readText', 'read'].forEach(function (m) {
          try { Object.defineProperty(cb, m, { value: rejecter, configurable: true }); } catch (_) {}
        });
      }
    } catch (_) {}

    try {
      var original = doc.execCommand;
      if (original && !original[FLAG]) {
        var wrapped = function (command) {
          if (/^(copy|cut|paste)$/i.test(String(command))) { return false; }
          return original.apply(this, arguments);
        };
        wrapped[FLAG] = true;
        doc.execCommand = wrapped;
      }
    } catch (_) {}

    try { win.print = function () {}; } catch (_) {}
  }

  function clearSelection(win, doc) {
    try {
      var sel = win.getSelection && win.getSelection();
      if (!sel || sel.isCollapsed) { return; }
      if (isEditable(doc.activeElement)) { return; }
      sel.removeAllRanges();
    } catch (_) {}
  }

  function protect(win) {
    var doc;
    try { doc = win.document; } catch (_) { return; }   // cross-origin: not ours
    if (!doc || doc[FLAG]) { return; }
    doc[FLAG] = true;

    injectStyle(doc);
    lockClipboardApis(win, doc);

    // Capture phase on window = runs before any handler the page itself adds.
    var opts = { capture: true, passive: false };

    win.addEventListener('keydown', function (e) {
      if (isBlockedShortcut(e)) { return stop(e); }
    }, opts);

    ['copy', 'cut', 'paste', 'contextmenu', 'dragstart', 'drop'].forEach(function (type) {
      win.addEventListener(type, stop, opts);
    });

    win.addEventListener('selectstart', function (e) {
      if (!isEditable(e.target)) { return stop(e); }
    }, opts);

    // Safety net for any selection that slips through (e.g. triple-click or
    // keyboard selection in older browsers).
    doc.addEventListener('selectionchange', function () { clearSelection(win, doc); });

    // CSS is enough for menu-printing, but clear any selection first too.
    win.addEventListener('beforeprint', function () { clearSelection(win, doc); });

    watchFrames(doc);
  }

  function protectFrame(frame) {
    try {
      var w = frame.contentWindow;
      if (w) { protect(w); }
    } catch (_) {}
  }

  function scanFrames(doc) {
    var frames;
    try { frames = doc.getElementsByTagName('iframe'); } catch (_) { return; }
    for (var i = 0; i < frames.length; i++) {
      var f = frames[i];
      if (!f[FLAG]) {
        f[FLAG] = true;
        f.addEventListener('load', function () { protectFrame(this); });
      }
      protectFrame(f);   // no-op if this document is already protected
    }
  }

  function watchFrames(doc) {
    scanFrames(doc);
    // A lesson's new document replaces the old one on each navigation; the
    // `load` listener catches it, and this short poll catches it before
    // `load` fires (large lesson pages can take a while to finish loading).
    var timer = setInterval(function () {
      if (!doc.defaultView) { clearInterval(timer); return; }
      scanFrames(doc);
    }, 250);
  }

  protect(window);
})();

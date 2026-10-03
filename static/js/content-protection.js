/*
 * Career Buddy — application-wide content protection
 * ===================================================
 * Blocks, on every page of the application:
 *   - Ctrl/Cmd + A  (select all)        - Ctrl/Cmd + C  (copy)
 *   - Ctrl/Cmd + V  (paste)             - Ctrl/Cmd + X  (cut)
 *   - Ctrl/Cmd + P  (print)             - Ctrl/Cmd + S  (save page)
 *   - Ctrl/Cmd + U  (view source)       - Ctrl+Insert / Shift+Insert / Shift+Delete
 *   - right-click / long-press context menu
 *   - text selection with mouse, touch or keyboard
 *   (except inside form fields within [data-allow-clipboard], e.g. the resume builder)
 *   - copy / cut / paste through ANY route (browser Edit menu, context menu,
 *     dragging text in or out, scripts calling navigator.clipboard or
 *     execCommand) — the app's own drag-and-drop (draggable="true" elements,
 *     file uploads) keeps working
 *   - printing through any route (the @media print rule blanks the page)
 *
 * How it is loaded
 * ----------------
 * core.middleware.ContentProtectionMiddleware injects this script into every
 * HTML page Django renders, so no template needs to include it. The Skill Up
 * lesson files under static/001 Career Buddy/ are served as raw static files
 * (Django never sees them), so each of those carries the same <script> tag.
 * Loading it twice on one page is harmless — it runs once per document.
 *
 * Same-origin iframes (e.g. Skill Up lessons shown inside the hub) are
 * protected from the parent too, every time they navigate.
 *
 * What still works
 * ----------------
 * Typing in inputs/textareas, placing the caret and selecting inside a field
 * to overwrite text, submitting forms, clicking links and buttons, keyboard
 * navigation (Tab, arrows, Enter), and every non-clipboard shortcut.
 *
 * Limits (true of every website)
 * ------------------------------
 * A page cannot block OS screenshots, the browser's developer tools, or a
 * user who turns JavaScript off. This stops ordinary copying, not a
 * determined technical user.
 */
(function () {
  'use strict';

  var FLAG = '__cbContentProtected';

  var BLOCKED_KEYS = { a: 1, c: 1, x: 1, v: 1, p: 1, s: 1, u: 1 };
  var BLOCKED_CODES = { KeyA: 1, KeyC: 1, KeyX: 1, KeyV: 1, KeyP: 1, KeyS: 1, KeyU: 1 };

  function stop(e) {
    if (e.cancelable) { e.preventDefault(); }
    e.stopPropagation();
    if (e.stopImmediatePropagation) { e.stopImmediatePropagation(); }
    return false;
  }

  function isEditable(node) {
    if (node && node.nodeType !== 1) { node = node.parentElement; }
    if (!node) { return false; }
    var tag = node.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') { return true; }
    return !!node.isContentEditable;
  }

  // Form fields inside an element marked data-allow-clipboard (the landing
  // page's resume builder, where candidates paste LinkedIn / GitHub links and
  // their own text) may use copy, cut, paste, select-all and the context menu.
  // Everything else on the page stays protected.
  function inAllowedField(node) {
    if (!isEditable(node)) { return false; }
    if (node.nodeType !== 1) { node = node.parentElement; }
    return !!(node && node.closest && node.closest('[data-allow-clipboard]'));
  }

  function isClipboardShortcut(e) {
    var key = (e.key || '').toLowerCase();
    if ((e.ctrlKey || e.metaKey) && !e.altKey && (/^[acvx]$/.test(key) || { KeyA: 1, KeyC: 1, KeyV: 1, KeyX: 1 }[e.code])) { return true; }
    return key === 'insert' || (key === 'delete' && e.shiftKey);
  }

  function isBlockedShortcut(e) {
    var key = (e.key || '').toLowerCase();
    var mod = e.ctrlKey || e.metaKey;

    // AltGr is reported as Ctrl+Alt on Windows; it types characters such as
    // "@" or "ą", so it must never be treated as a clipboard shortcut.
    if (mod && !e.altKey) {
      if (BLOCKED_KEYS[key]) { return true; }
      // Non-Latin keyboard layouts (e.g. Hindi, Russian) report a different
      // e.key for the same physical key; Ctrl+that key still copies/pastes.
      if (!/^[a-z]$/.test(key) && BLOCKED_CODES[e.code]) { return true; }
    }
    // Legacy clipboard shortcuts.
    if (key === 'insert' && (e.ctrlKey || e.shiftKey)) { return true; }   // copy / paste
    if (key === 'delete' && e.shiftKey && !e.ctrlKey) { return true; }    // cut
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
    // Fields stay selectable so the caret, editing and overwriting still work.
    // Copying out of them and pasting into them is still blocked by the events.
    'input, textarea, [contenteditable=""], [contenteditable="true"] {' +
    '  -webkit-user-select: text !important;' +
    '  -moz-user-select: text !important;' +
    '  user-select: text !important;' +
    '}' +
    '::selection { background: transparent !important; }' +
    'input::selection, textarea::selection { background: #b3d4fc !important; }' +
    '@media print {' +
    '  html, body { background: #fff !important; }' +
    '  body > * { display: none !important; }' +
    '  body::after {' +
    '    content: "Printing is disabled for Career Buddy content.";' +
    '    display: block !important; padding: 40px; font: 16px sans-serif; color: #000;' +
    '  }' +
    '}';

  function injectStyle(doc) {
    if (doc.getElementById('cb-content-protection-style')) { return; }
    var style = doc.createElement('style');
    style.id = 'cb-content-protection-style';
    style.textContent = CSS;
    (doc.head || doc.documentElement).appendChild(style);
  }

  function lockScriptApis(win, doc) {
    var reject = function () {
      return Promise.reject(new Error('Clipboard access is disabled.'));
    };
    try {
      var cb = win.navigator && win.navigator.clipboard;
      if (cb) {
        ['writeText', 'write', 'readText', 'read'].forEach(function (m) {
          try { Object.defineProperty(cb, m, { value: reject, configurable: true }); } catch (_) {}
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
    try { doc = win.document; } catch (_) { return; }   // cross-origin frame (e.g. YouTube)
    if (!doc || doc[FLAG]) { return; }
    doc[FLAG] = true;

    function apply() { injectStyle(doc); }
    if (doc.head || doc.documentElement) { apply(); }
    else { doc.addEventListener('DOMContentLoaded', apply); }

    lockScriptApis(win, doc);

    // Capture phase on window runs before any handler the page itself adds,
    // and covers dialogs, modals and content added to the page later.
    var opts = { capture: true, passive: false };

    win.addEventListener('keydown', function (e) {
      if (isBlockedShortcut(e) && !(isClipboardShortcut(e) && inAllowedField(e.target))) { return stop(e); }
    }, opts);

    ['copy', 'cut', 'paste', 'contextmenu'].forEach(function (type) {
      win.addEventListener(type, function (e) {
        if (inAllowedField(e.target)) { return; }
        return stop(e);
      }, opts);
    });

    // Drag-and-drop: block dragging text, links or images out of the page and
    // dropping text in (a paste in disguise), but keep the app's own
    // drag-and-drop working — elements it marks draggable="true" (e.g. the
    // Ordering exercise) and file uploads (e.g. the résumé drop zone).
    var internalDrag = false;
    win.addEventListener('dragstart', function (e) {
      var el = e.target && e.target.nodeType === 1 ? e.target : null;
      if (el && el.closest && el.closest('[draggable="true"]')) { internalDrag = true; return; }
      internalDrag = false;
      return stop(e);
    }, opts);
    win.addEventListener('dragend', function () { internalDrag = false; }, opts);
    win.addEventListener('drop', function (e) {
      if (internalDrag) { return; }
      var types = (e.dataTransfer && e.dataTransfer.types) ? Array.prototype.slice.call(e.dataTransfer.types) : [];
      if (types.indexOf('Files') !== -1) { return; }
      return stop(e);
    }, opts);

    win.addEventListener('selectstart', function (e) {
      if (!isEditable(e.target)) { return stop(e); }
    }, opts);

    // Safety net for selections made another way (browser Edit > Select All,
    // triple-click in older browsers, assistive tools).
    doc.addEventListener('selectionchange', function () { clearSelection(win, doc); });
    win.addEventListener('beforeprint', function () { clearSelection(win, doc); });

    watchFrames(doc);
  }

  function protectFrame(frame) {
    try { if (frame.contentWindow) { protect(frame.contentWindow); } } catch (_) {}
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
      protectFrame(f);
    }
  }

  function watchFrames(doc) {
    scanFrames(doc);
    // Catches a frame's new document before its `load` event (large lesson
    // pages can take a while to finish loading).
    var timer = setInterval(function () {
      if (!doc.defaultView) { clearInterval(timer); return; }
      scanFrames(doc);
    }, 250);
  }

  protect(window);
})();

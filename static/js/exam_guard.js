/* CareerBuddy assessment guard: ONE violation = ONE warning, from ONE counter.
 *
 * Leaving the assessment fires several browser events for a single act:
 * a screenshot tool takes focus (blur), the page may hide (visibilitychange)
 * and fullscreen ends (fullscreenchange). Each assessment page's own engine
 * counted every one of them ("Warning 2 of 3" for one screenshot), and the
 * shared cb-exam-proctor kept a second count of its own that surfaced later
 * ("Warning 1 of 3" after returning).
 *
 * Loaded first in <head>, before any page script, this file:
 *  - groups those events into incidents: an incident starts at the first
 *    leave-event and lasts while the candidate is away plus GRACE_MS after
 *    they return; every further leave-event in it is a repeat;
 *  - lets page listeners for blur / visibilitychange / fullscreenchange
 *    (registered after this file) see only the FIRST event of an incident,
 *    so an engine counts each incident once;
 *  - tells cb-exam-proctor whether the page's engine does its own warnings
 *    (CBExamGuard.engineWarns()), so exactly one counter is shown.
 */
(function () {
  'use strict';
  if (window.CBExamGuard) return;

  var GRACE_MS = 3000;
  var TYPES = { blur: 1, visibilitychange: 1, fullscreenchange: 1 };
  var away = false, quietUntil = 0, engine = false, subscribers = [];

  function isLeave(e) {
    if (e.type === 'blur') return e.target === window;
    if (e.type === 'visibilitychange') return document.hidden;
    if (e.type === 'fullscreenchange') return !document.fullscreenElement;
    return false;
  }

  // Runs before every page listener: window capture sees window events at
  // target and document events on their way down.
  function classify(e) {
    if (!TYPES[e.type] || e.__cbGuard) return;
    e.__cbGuard = true;
    if (!isLeave(e)) return;
    var now = Date.now();
    e.__cbRepeat = away || now < quietUntil;
    if (!e.__cbRepeat) {
      away = true;
      quietUntil = now + GRACE_MS;
      subscribers.forEach(function (fn) { try { fn(e); } catch (_) {} });
    }
  }
  function back() {
    if (!away) return;
    away = false;
    quietUntil = Math.max(quietUntil, Date.now() + GRACE_MS);
  }
  Object.keys(TYPES).forEach(function (t) { window.addEventListener(t, classify, true); });
  window.addEventListener('focus', function (e) { if (e.target === window) back(); }, true);
  document.addEventListener('visibilitychange', function () { if (!document.hidden && document.hasFocus()) back(); });
  document.addEventListener('fullscreenchange', function () { if (document.fullscreenElement) back(); });

  // Page listeners for those events, registered from here on, skip repeats.
  var add = EventTarget.prototype.addEventListener;
  var remove = EventTarget.prototype.removeEventListener;
  var wrapped = new WeakMap();
  var WARNS = /warn|violat|strike|cheat|malpractice|penalt|proctor/i;
  EventTarget.prototype.addEventListener = function (type, fn, opts) {
    if (TYPES[type] && typeof fn === 'function' && !fn.__cbOwn && (this === window || this === document)) {
      if (!engine && WARNS.test(Function.prototype.toString.call(fn))) engine = true;
      var w = wrapped.get(fn);
      if (!w) {
        w = function (e) { if (e && e.__cbRepeat) return; return fn.apply(this, arguments); };
        wrapped.set(fn, w);
      }
      return add.call(this, type, w, opts);
    }
    return add.call(this, type, fn, opts);
  };
  EventTarget.prototype.removeEventListener = function (type, fn, opts) {
    return remove.call(this, type, (fn && wrapped.get(fn)) || fn, opts);
  };

  window.CBExamGuard = {
    // True once the page's own engine registered a warning handler.
    engineWarns: function () { return engine; },
    // fn(event) on the first event of every incident.
    onIncident: function (fn) { subscribers.push(fn); },
    own: function (fn) { fn.__cbOwn = true; return fn; },
  };
})();

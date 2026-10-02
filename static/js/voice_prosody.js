/* Natural-sounding speech for the browser TTS engines.

   SpeechSynthesisUtterance has no SSML and no emotion: one flat pitch and rate
   for the whole reply, which is exactly what makes it sound robotic. The fix
   is to stop speaking a reply as ONE utterance. Split it at its punctuation
   and speak each clause as its own utterance with its own pitch, rate and
   trailing pause, so the voice rises into a clause and falls (or lifts, for a
   question) out of it — the bend around the punctuation the flat version
   never had.

   Two things shape each clause:

     1. The punctuation that ENDS it - '.' falls, '?' rises, '!' lifts and
        gets louder, ',' stays level with a short pause.
     2. The emotion of the whole reply - happy lifts pitch and pace, sad drops
        both and lengthens the pauses.

   Punctuation is the same in every language this app speaks (en, hi, ar, ru,
   vi), and Devanagari's danda (।) and the Arabic question mark (؟) are handled
   alongside the Latin marks, so the contour works without per-language tuning.
   Emotion detection is keyword-based per language, with a punctuation-only
   fallback, so an unknown language still gets the punctuation contour.

   Used by the chatbot (static/js/BOTscript.js) and the Group Discussion agents
   (GD_app/static/GD_app/js/gd.js).
*/
(function (global) {
  'use strict';

  // Sentence-final marks, in every script this app speaks.
  var TERMINATORS = '.!?。！？।۔؟…';
  var PAUSE_MARKS = ',;:،؛';

  // Words that mark a reply as a find/success or a failure. Deliberately
  // small: these run on every reply, and a wrong hit is worse than a miss
  // (a neutral contour still sounds natural, a cheerful apology does not).
  var HAPPY_WORDS = {
    en: ['found', 'great', 'excellent', 'perfect', 'congratulations', 'well done',
         'success', 'ready', 'here it is', 'here are', 'good news', 'happy to',
         'yes', 'correct', 'nice', 'wonderful', 'awesome', 'completed', 'passed'],
    hi: ['मिल गया', 'बढ़िया', 'शानदार', 'बहुत अच्छा', 'बधाई', 'सफल', 'तैयार', 'हाँ', 'सही'],
    ar: ['وجدت', 'ممتاز', 'رائع', 'مبروك', 'تهانينا', 'نجاح', 'جاهز', 'نعم', 'صحيح'],
    ru: ['нашёл', 'нашел', 'отлично', 'прекрасно', 'поздравляю', 'успешно', 'готово', 'да', 'верно'],
    vi: ['đã tìm thấy', 'tuyệt', 'xuất sắc', 'chúc mừng', 'thành công', 'sẵn sàng', 'đúng rồi'],
  };
  var SAD_WORDS = {
    en: ["couldn't", 'could not', 'cannot', "can't", 'unable', 'sorry', 'no results',
         'not found', 'failed', 'failure', 'unfortunately', 'error', 'problem',
         'unavailable', 'nothing found', 'went wrong', 'denied', 'rejected', 'missing'],
    hi: ['नहीं मिला', 'माफ़ कीजिए', 'क्षमा', 'असफल', 'त्रुटि', 'उपलब्ध नहीं', 'समस्या'],
    ar: ['عذرا', 'عذراً', 'لم أجد', 'لا يمكن', 'فشل', 'خطأ', 'غير متاح', 'مشكلة'],
    ru: ['извините', 'не найдено', 'не удалось', 'ошибка', 'недоступно', 'проблема', 'к сожалению'],
    vi: ['xin lỗi', 'không tìm thấy', 'không thể', 'thất bại', 'lỗi', 'không có sẵn', 'rất tiếc'],
  };

  /* How far each emotion moves pitch, rate, volume and pause length away from
     the voice's own baseline. Kept small on purpose: a big pitch jump on a
     browser voice sounds like a cartoon, not a person. */
  var EMOTION = {
    happy:   { pitch: 0.12, rate: 0.06, volume: 0.00 },
    sad:     { pitch: -0.12, rate: -0.10, volume: -0.12 },
    neutral: { pitch: 0.00, rate: 0.00, volume: 0.00 },
  };

  /* Gap after a clause, in ms. Kept at 10ms so the clauses run together as
     one continuous sentence: the punctuation is heard in the pitch and pace
     change, not in a silence. (Browser engines add their own small gap
     between utterances on top of this, which is why a larger value here made
     the speech sound chopped rather than expressive.) */
  var PUNCTUATION_GAP_MS = 10;

  /* The contour for one clause, by the mark that ends it. `lead` lifts the
     start of the clause (the stress going in), `tail` sets where the voice
     lands (the stress coming out). */
  var CONTOUR = {
    '.': { lead: 0.05, tail: -0.09, rate: 0.00 },
    '!': { lead: 0.14, tail: 0.04, rate: 0.04, volume: 0.06 },
    '?': { lead: 0.03, tail: 0.17, rate: -0.02 },
    ',': { lead: 0.03, tail: -0.02, rate: 0.00 },
    ':': { lead: 0.04, tail: 0.03, rate: 0.00 },
    ';': { lead: 0.03, tail: -0.03, rate: 0.00 },
    '…': { lead: -0.02, tail: -0.10, rate: -0.06 },
    '': { lead: 0.04, tail: -0.04, rate: 0.00 },
  };

  function normaliseMark(ch) {
    if (ch === '。' || ch === '।' || ch === '۔') return '.';
    if (ch === '！') return '!';
    if (ch === '？' || ch === '؟') return '?';
    if (ch === '،') return ',';
    if (ch === '؛') return ';';
    return ch;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  /* 'happy' | 'sad' | 'neutral' for a whole reply.

     Sad wins ties: an apology that happens to contain "yes" must not be read
     cheerfully, while a cheerful line misread as neutral costs little. */
  function detectEmotion(text, language) {
    var body = String(text || '').toLowerCase();
    if (!body.trim()) return 'neutral';

    var lang = String(language || 'en').toLowerCase().slice(0, 2);
    var langs = [lang, 'en'];
    var hit = function (banks) {
      for (var i = 0; i < langs.length; i++) {
        var words = banks[langs[i]] || [];
        for (var j = 0; j < words.length; j++) {
          if (body.indexOf(String(words[j]).toLowerCase()) !== -1) return true;
        }
      }
      return false;
    };

    if (hit(SAD_WORDS)) return 'sad';
    if (hit(HAPPY_WORDS)) return 'happy';
    // No keyword matched — let the punctuation speak. An exclamation is the
    // one mark that carries emotion on its own, in every language here.
    if (body.indexOf('!') !== -1 || body.indexOf('！') !== -1) return 'happy';
    return 'neutral';
  }

  /* Split a reply into clauses, each with its own contour.

     Returns [{ text, pitch, rate, volume, pause, offset }], where `offset` is
     the clause's start index in the ORIGINAL text so a caller tracking
     progress (resume-after-navigation, a typewriter) stays in sync. */
  function buildSegments(text, options) {
    var opts = options || {};
    var body = String(text || '');
    if (!body.trim()) return [];

    var basePitch = typeof opts.pitch === 'number' ? opts.pitch : 1.0;
    var baseRate = typeof opts.rate === 'number' ? opts.rate : 1.0;
    var baseVolume = typeof opts.volume === 'number' ? opts.volume : 1.0;
    var emotion = opts.emotion || detectEmotion(body, opts.language);
    var mood = EMOTION[emotion] || EMOTION.neutral;

    // Walk the text, closing a clause at every terminator or pause mark.
    var segments = [];
    var start = 0;
    var i = 0;
    for (; i < body.length; i++) {
      var mark = normaliseMark(body.charAt(i));
      var isTerminator = TERMINATORS.indexOf(body.charAt(i)) !== -1;
      var isPause = PAUSE_MARKS.indexOf(body.charAt(i)) !== -1;
      if (!isTerminator && !isPause) continue;

      // Run together repeated marks ("!!!", "?!") so they count once.
      var end = i + 1;
      while (end < body.length &&
             (TERMINATORS.indexOf(body.charAt(end)) !== -1 ||
              PAUSE_MARKS.indexOf(body.charAt(end)) !== -1)) {
        end++;
      }
      segments.push({ raw: body.slice(start, end), mark: mark, offset: start });
      start = end;
      i = end - 1;
    }
    if (start < body.length) {
      segments.push({ raw: body.slice(start), mark: '', offset: start });
    }

    var out = [];
    for (var s = 0; s < segments.length; s++) {
      var seg = segments[s];
      var spoken = seg.raw.trim();
      // Nothing to say: empty, or punctuation on its own ("...", "!!"). The
      // engine would spend a whole utterance and its pause on silence.
      if (!spoken || !/[^\s.,;:!?…。！？।۔؟،؛'"()\[\]-]/.test(spoken)) continue;
      // Point the offset at the first spoken character, not at the whitespace
      // in front of it, so a caller slicing the original text by offset gets
      // exactly this clause back.
      var lead = seg.raw.length - seg.raw.replace(/^\s+/, '').length;

      var shape = CONTOUR[seg.mark] || CONTOUR[''];
      // The lead lifts the clause's start, the tail lands its end; a browser
      // voice cannot change pitch mid-utterance, so the clause takes the
      // average of the two and the CONTRAST between neighbouring clauses is
      // what the ear hears as the bend around the punctuation.
      var bend = (shape.lead + shape.tail) / 2;
      // A long clause drifts slightly down, the way an unhurried speaker does.
      var drift = spoken.length > 90 ? -0.03 : 0;

      out.push({
        text: spoken,
        offset: seg.offset + lead,
        mark: seg.mark,
        pitch: clamp(basePitch + bend + mood.pitch + drift, 0.1, 2),
        rate: clamp(baseRate + (shape.rate || 0) + mood.rate, 0.1, 10),
        volume: clamp(baseVolume + (shape.volume || 0) + mood.volume, 0, 1),
        pause: PUNCTUATION_GAP_MS,
      });
    }
    return out;
  }

  /* Speak `text` as a chain of contoured clauses.

     `options`: { lang, voice, pitch, rate, volume, emotion, language }
     `handlers`: { onstart, onboundary(charIndexInFullText), onend, onerror }

     Returns a handle with cancel(); the chain stops cleanly mid-way. */
  function speak(text, options, handlers) {
    var opts = options || {};
    var cb = handlers || {};
    var segments = buildSegments(text, opts);
    if (!segments.length || !('speechSynthesis' in global)) {
      if (cb.onend) cb.onend();
      return { cancel: function () {} };
    }

    var index = 0;
    var cancelled = false;
    var timer = null;
    var started = false;

    function next() {
      if (cancelled) return;
      if (index >= segments.length) {
        if (cb.onend) cb.onend();
        return;
      }
      var seg = segments[index++];
      var utter = new global.SpeechSynthesisUtterance(seg.text);
      if (opts.lang) utter.lang = opts.lang;
      if (opts.voice) utter.voice = opts.voice;
      utter.pitch = seg.pitch;
      utter.rate = seg.rate;
      utter.volume = seg.volume;

      utter.onstart = function () {
        if (!started && cb.onstart) {
          started = true;
          cb.onstart();
        }
      };
      // Report progress against the FULL text, not this clause, so callers
      // that resume or animate from a character index stay correct.
      utter.onboundary = function (event) {
        if (cb.onboundary && typeof event.charIndex === 'number') {
          cb.onboundary(seg.offset + event.charIndex, event);
        }
      };
      utter.onend = function () {
        if (cancelled) return;
        if (seg.pause > 0) {
          timer = global.setTimeout(next, seg.pause);
        } else {
          next();
        }
      };
      utter.onerror = function (event) {
        if (cancelled || (event && event.error === 'interrupted')) return;
        // One bad clause must not swallow the rest of the reply.
        if (cb.onerror) cb.onerror(event);
        next();
      };

      global.speechSynthesis.speak(utter);
    }

    next();

    return {
      cancel: function () {
        cancelled = true;
        if (timer) {
          global.clearTimeout(timer);
          timer = null;
        }
      },
    };
  }

  global.VoiceProsody = {
    detectEmotion: detectEmotion,
    buildSegments: buildSegments,
    speak: speak,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = global.VoiceProsody;
  }
})(typeof window !== 'undefined' ? window : globalThis);

/* Self-check for static/js/voice_prosody.js.
   Run:  node static/js/voice_prosody.check.js
*/
const assert = require('assert');
const { detectEmotion, buildSegments } = require('./voice_prosody.js');

// ── emotion, across every language the chatbot speaks ──────────────────────
const cases = [
  ['I found 5 matching jobs for you!', 'en', 'happy'],
  ["Sorry, I couldn't find any results.", 'en', 'sad'],
  ['The deadline is Monday.', 'en', 'neutral'],
  ['मुझे 5 नौकरियाँ मिल गईं!', 'hi', 'happy'],
  ['क्षमा करें, कुछ नहीं मिला।', 'hi', 'sad'],
  ['عذراً، لم أجد شيئاً.', 'ar', 'sad'],
  ['К сожалению, произошла ошибка.', 'ru', 'sad'],
  ['Tuyệt vời! Đã tìm thấy.', 'vi', 'happy'],
];
for (const [text, lang, want] of cases) {
  assert.strictEqual(detectEmotion(text, lang), want, text);
}
// A sad reply containing a happy word stays sad.
assert.strictEqual(detectEmotion('Yes, but unfortunately I could not find it.', 'en'), 'sad');
// An unknown language still gets the punctuation fallback.
assert.strictEqual(detectEmotion('Ausgezeichnet!', 'de'), 'happy');
assert.strictEqual(detectEmotion('', 'en'), 'neutral');

// ── contour around punctuation ─────────────────────────────────────────────
const seg = buildSegments('Great news! I found 3 jobs. Shall I show them?', { language: 'en' });
assert.strictEqual(seg.length, 3);
const [bang, dot, q] = seg;
assert.ok(bang.pitch > dot.pitch, 'exclamation lifts above the statement');
assert.ok(q.pitch > dot.pitch, 'question rises above the statement');
assert.ok(bang.volume >= dot.volume, 'exclamation is not quieter');
assert.ok(seg.every((s) => s.pause === 10), 'clauses run together with a 10ms gap');

// Offsets index the ORIGINAL text, so a caller tracking progress stays right.
const full = 'Great news! I found 3 jobs. Shall I show them?';
for (const s of seg) {
  assert.strictEqual(full.slice(s.offset, s.offset + s.text.length).trim(), s.text.trim());
}

// ── emotion moves the whole reply ──────────────────────────────────────────
const happy = buildSegments('I found it. Here it is.', { language: 'en' });
const sad = buildSegments('I could not find it. Sorry.', { language: 'en' });
assert.ok(happy[0].pitch > sad[0].pitch, 'happy speaks higher than sad');
assert.ok(happy[0].rate > sad[0].rate, 'happy speaks faster than sad');
assert.ok(sad[0].volume < happy[0].volume, 'sad speaks more softly');

// ── non-Latin punctuation gets the same treatment ──────────────────────────
const hindi = buildSegments('मुझे मिल गया। क्या दिखाऊँ?', { language: 'hi' });
assert.strictEqual(hindi.length, 2, 'danda ends a clause');
assert.ok(hindi[1].pitch > hindi[0].pitch, 'Devanagari question still rises');
const arabic = buildSegments('وجدت شيئاً، هل أعرضه؟', { language: 'ar' });
assert.strictEqual(arabic.length, 2, 'Arabic comma and question mark split');

// ── degenerate input never throws ──────────────────────────────────────────
assert.deepStrictEqual(buildSegments('', {}), []);
assert.deepStrictEqual(buildSegments('   ', {}), []);
assert.deepStrictEqual(buildSegments('...', {}).length, 0);
assert.strictEqual(buildSegments('No punctuation here', {}).length, 1);
assert.strictEqual(buildSegments('Wait!!! What?!', {}).length, 2, 'repeated marks count once');

// ── values stay inside what the Web Speech API accepts ─────────────────────
for (const s of buildSegments('Amazing!!! I found everything you asked for!', { language: 'en', pitch: 1.5, rate: 1.4 })) {
  assert.ok(s.pitch >= 0.1 && s.pitch <= 2, `pitch in range: ${s.pitch}`);
  assert.ok(s.rate >= 0.1 && s.rate <= 10, `rate in range: ${s.rate}`);
  assert.ok(s.volume >= 0 && s.volume <= 1, `volume in range: ${s.volume}`);
}

console.log('VoiceProsody OK');

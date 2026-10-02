/* Self-check for appendTranscript() in static/js/exercises.js — the dedup that
   keeps the 60-second timer transcript from repeating sentences.

   Run:  node performance-testing/timer-speech-dedup.check.js
*/
const assert = require('assert');

// exercises.js is a browser script; stub the globals it touches on load.
global.window = {};
global.document = { addEventListener() {}, documentElement: {} };
const { appendTranscript } = require('../static/js/exercises.js');

// A normal run: two final results, then the interim flush of the second one.
const store = {};
appendTranscript(store, 0, 'And today I will show you the data.');
appendTranscript(store, 0, 'It reduced support tickets by half.');
appendTranscript(store, 0, 'It reduced support tickets by half.');   // re-delivered final
assert.strictEqual(
  store[0].trim(),
  'And today I will show you the data. It reduced support tickets by half.'
);

// Case-insensitive, whitespace-normalised duplicate.
appendTranscript(store, 0, '  it REDUCED   support tickets by half. ');
assert.strictEqual(store[0].trim().endsWith('by half.'), true);
assert.strictEqual((store[0].match(/reduced/gi) || []).length, 1);

// Empty / missing speech changes nothing.
const before = store[0];
appendTranscript(store, 0, '');
appendTranscript(store, 0, null);
assert.strictEqual(store[0], before);

// New text still appends.
appendTranscript(store, 0, 'Loyalty is up.');
assert.ok(store[0].trim().endsWith('Loyalty is up.'));

// Separate tasks stay separate.
appendTranscript(store, 1, 'Second task answer.');
assert.strictEqual(store[1].trim(), 'Second task answer.');

console.log('appendTranscript OK');

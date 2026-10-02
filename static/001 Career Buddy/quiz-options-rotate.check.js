/* Self-check for quiz-options-rotate.js.
   Run:  node "static/001 Career Buddy/quiz-options-rotate.check.js"
*/
const assert = require('assert');
const { rotateQuizOptions } = require('./quiz-options-rotate.js');

// The correct option travels with its text, whatever position it lands in.
for (let trial = 0; trial < 200; trial++) {
  const item = { options: ['a', 'b', 'c', 'd'], answer: 2 };
  rotateQuizOptions([item]);
  assert.strictEqual(item.options[item.answer], 'c');
  assert.deepStrictEqual([...item.options].sort(), ['a', 'b', 'c', 'd']);
}

// Typed-answer questions are untouched.
const typed = { type: 'type', answer: 'invention' };
rotateQuizOptions([typed]);
assert.strictEqual(typed.answer, 'invention');
assert.strictEqual(typed.options, undefined);

// The source bank is never mutated: an item built with {...q} shares the
// bank's options array, so rotating must not leave the bank's own answer index
// pointing at the wrong option for the next attempt.
const bankQ = { options: ['w', 'x', 'y', 'z'], answer: 1 };
const built = { ...bankQ };
rotateQuizOptions([built]);
assert.deepStrictEqual(bankQ.options, ['w', 'x', 'y', 'z']);
assert.strictEqual(bankQ.options[bankQ.answer], 'x');
assert.strictEqual(built.options[built.answer], 'x');

// Over many questions the answer lands on every position.
const positions = new Set();
for (let i = 0; i < 300; i++) {
  const item = { options: ['a', 'b', 'c', 'd'], answer: 0 };
  rotateQuizOptions([item]);
  positions.add(item.answer);
}
assert.strictEqual(positions.size, 4);

console.log('rotateQuizOptions OK');

/* Rotate MCQ options for the quizzes embedded in the course pages.

   Same bug the server-side mock tests had: the hand-written banks put the
   correct answer at one letter far too often (022 cocubes-guide: B in 27 of
   60 questions, D in 1). Shuffling the options per attempt spreads it.

   Call it on the array of questions after it is built and BEFORE the first
   question is rendered. Each item is rewritten in place: `options` reordered
   and `answer` remapped to the option's new index, so every consumer
   (rendering, grading, the review screen) stays consistent.

   Items without a numeric `answer` — typed-answer questions, for instance —
   are left untouched.
*/
(function (global) {
  function rotateQuizOptions(items) {
    (items || []).forEach(function (item) {
      var options = item && item.options;
      if (!Array.isArray(options) || options.length < 2) return;
      if (typeof item.answer !== 'number') return;   // typed answer, not an index

      // Copy: an item built with {...q} shares the bank's options array, and
      // shuffling that in place would corrupt the bank's own `answer` index
      // for the next attempt.
      var shuffled = options.slice();
      var correct = shuffled[item.answer];
      for (var i = shuffled.length - 1; i > 0; i--) {   // Fisher-Yates
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = shuffled[i]; shuffled[i] = shuffled[j]; shuffled[j] = tmp;
      }
      item.options = shuffled;
      item.answer = shuffled.indexOf(correct);
    });
    return items;
  }

  global.rotateQuizOptions = rotateQuizOptions;
  if (typeof module !== 'undefined' && module.exports) module.exports = { rotateQuizOptions };
})(typeof window !== 'undefined' ? window : globalThis);

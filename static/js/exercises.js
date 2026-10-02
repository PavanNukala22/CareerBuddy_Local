/* ===================================================
   Career Buddy – Interactive Exercises
   =================================================== */

// Variables injected by exercise.html template:
// EXERCISE_TYPE, EXERCISE_ID, SUBMIT_URL, CSRF_TOKEN,
// TOTAL_QUESTIONS, QUESTIONS_DATA, BINGO_DATA

const answers = {};
let currentScore = 0;
let currentQIdx = 1;

function updateProgress(total) {
  const answeredCount = Object.keys(answers).length;
  const pct = (answeredCount / total) * 100;

  const progressBar = document.getElementById('q-progress-bar');
  const currentQEl = document.getElementById('current-q');
  const scoreEl = document.getElementById('score-display');
  const progressStatusEl = document.getElementById('progress-status');

  if (progressBar) {
    progressBar.style.width = pct + '%';
    progressBar.style.transition = 'width 0.4s ease';
  }

  if (currentQEl) currentQEl.textContent = currentQIdx;
  if (scoreEl) scoreEl.textContent = 'Score: ' + currentScore;

  if (answeredCount === total && progressStatusEl) {
    progressStatusEl.classList.add('text-success', 'anim-pop');
    progressStatusEl.innerHTML = `<i class="fas fa-check-circle me-1"></i>${total} of ${total} Questions Completed`;

    const uiStatus = document.getElementById('ui-status-text');
    if (uiStatus) uiStatus.textContent = 'Completed';
  }
}

async function submitScore(score, maxScore, customSummaryHtml = '') {
  // Find the active submit button to show loading state
  const activeBtn = document.querySelector('button[id^="submit-"]:not([style*="display: none"])') ||
    document.querySelector('.btn-success:not([style*="display: none"])');

  const originalHtml = activeBtn ? activeBtn.innerHTML : '';
  if (activeBtn) {
    activeBtn.disabled = true;
    activeBtn.innerHTML = 'Submitting...';
  }

  try {
    const resp = await fetch(SUBMIT_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN,
      },
      body: JSON.stringify({ score, max_score: maxScore, answers }),
    });

    if (!resp.ok) throw new Error('Server returned ' + resp.status);

    const data = await resp.json();
    if (activeBtn) activeBtn.innerHTML = 'Submitted';

    // Prefer backend provided score, max_score, and HTML if available
    const finalScore = data.score !== undefined ? data.score : score;
    const finalMaxScore = data.max_score !== undefined ? data.max_score : maxScore;
    const finalHtml = customSummaryHtml + (data.customSummaryHtml || '');

    showResultPanel(finalScore, finalMaxScore, data.percentage, finalHtml);
    showProgressUpdate(data.sub_progress, data.activity_progress);
  } catch (e) {
    console.error('Submit error:', e);
    alert('Failed to submit score. Please check your connection and try again.');
    if (activeBtn) {
      activeBtn.disabled = false;
      activeBtn.innerHTML = originalHtml;
    }
  }
}

function showResultPanel(score, maxScore, pct, customSummaryHtml = '') {
  const panel = document.getElementById('result-panel');
  if (!panel) return;
  const icon = document.getElementById('result-icon');
  const title = document.getElementById('result-title');
  const scoreText = document.getElementById('result-score-text');
  const details = document.getElementById('result-details');

  let iconHtml, titleText, circleClass;
  if (pct === 100) {
    iconHtml = '<div class="score-circle score-excellent">🏆</div>';
    titleText = 'Perfect Score!';
  } else if (pct >= 90) {
    iconHtml = '<div class="score-circle score-excellent">🌟</div>';
    titleText = 'Excellent!';
  } else if (pct >= 80) {
    iconHtml = '<div class="score-circle score-excellent">✨</div>';
    titleText = 'Very Good!';
  } else if (pct >= 60) {
    iconHtml = '<div class="score-circle score-good">👍</div>';
    titleText = 'Good Job!';
  } else if (pct >= 40) {
    iconHtml = '<div class="score-circle score-average">💪</div>';
    titleText = 'Average';
  } else {
    iconHtml = '<div class="score-circle score-low">📚</div>';
    titleText = 'Keep Practising';
  }

  icon.innerHTML = iconHtml;
  title.textContent = titleText;
  scoreText.textContent = `You scored ${score} out of ${maxScore} (${pct}%)`;

  if (details) {
    details.innerHTML = customSummaryHtml;
  }

  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ===================================================
   MCQ Exercise
   =================================================== */
function initMCQ() {
  const total = TOTAL_QUESTIONS;
  currentQIdx = 1;
  currentScore = 0;

  document.querySelectorAll('.option-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const qNum = this.dataset.q;
      const chosen = this.dataset.option;
      const correct = this.dataset.correct;
      const expBox = document.getElementById('exp-' + qNum);
      const expText = this.dataset.explanation;

      // Disable all options for this question
      document.querySelectorAll(`[data-q="${qNum}"]`).forEach(b => {
        b.disabled = true;
        if (b.dataset.option === correct) b.classList.add('correct');
      });

      if (chosen === correct) {
        this.classList.add('correct');
        currentScore++;
        answers[qNum] = { chosen, correct, result: 'correct' };
        if (expBox) {
          expBox.className = 'explanation-box correct-exp';
          expBox.innerHTML = `<i class="fas fa-check-circle me-2"></i>Correct! ${expText || ''}`;
          expBox.style.display = 'block';
        }
      } else {
        this.classList.add('wrong');
        answers[qNum] = { chosen, correct, result: 'wrong' };
        if (expBox) {
          expBox.className = 'explanation-box wrong-exp';
          expBox.innerHTML = `<i class="fas fa-times-circle me-2"></i>Incorrect. Correct: <strong>${correct.toUpperCase()}</strong>. ${expText || ''}`;
          expBox.style.display = 'block';
        }
      }

      // Enable Next/Submit button
      const nextBtn = document.querySelector(`#q-${qNum} .next-btn`);
      const submitBtn = document.getElementById('submit-mcq');
      if (nextBtn) nextBtn.disabled = false;
      if (submitBtn) submitBtn.disabled = false;

      updateProgress(total);
    });
  });

  // Next button handler
  document.querySelectorAll('.next-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const nextNum = this.dataset.next;
      document.querySelectorAll('.question-card').forEach(c => c.style.display = 'none');
      const nextCard = document.getElementById('q-' + nextNum);
      if (nextCard) nextCard.style.display = 'block';
      currentQIdx = parseInt(nextNum);
      updateProgress(total);
    });
  });

  // Submit MCQ
  const submitMCQ = document.getElementById('submit-mcq');
  if (submitMCQ) {
    submitMCQ.addEventListener('click', () => {
      submitScore(currentScore, total);
    });
  }
}

/* ===================================================
   Fill-in-the-Blank Exercise
   =================================================== */
function initFillBlank() {
  const total = TOTAL_QUESTIONS;
  currentScore = 0;
  const inputs = document.querySelectorAll('.fill-input');
  const submitFill = document.getElementById('submit-fill');
  let checkedCount = 0;

  document.querySelectorAll('.check-fill-btn').forEach(btn => {
    btn.addEventListener('click', function () {
      const q = this.dataset.q;
      const input = document.querySelector(`.fill-input[data-q="${q}"]`);
      const fb = document.getElementById('fill-fb-' + q);
      const hint = document.getElementById('fill-hint-' + q);
      const givenRaw = input.value.trim();
      const correct = input.dataset.correct.trim().toLowerCase();
      const given = givenRaw.toLowerCase();

      if (!givenRaw) {
        if (fb) {
          fb.className = 'fill-feedback error-fb';
          fb.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i>Please enter an answer first.`;
          fb.style.display = 'block';
        }
        return;
      }

      input.disabled = true;
      this.disabled = true;
      checkedCount++;
      answers[q] = { given: input.value, correct: input.dataset.correct };

      if (given === correct) {
        input.classList.add('correct-input');
        currentScore++;
        if (fb) {
          fb.className = 'fill-feedback correct-fb';
          fb.innerHTML = `<i class="fas fa-check-circle me-1"></i>Correct!`;
          fb.style.display = 'block';
        }
        answers[q].result = 'correct';
      } else {
        input.classList.add('wrong-input');
        if (fb) {
          fb.className = 'fill-feedback wrong-fb';
          fb.innerHTML = `<i class="fas fa-times-circle me-1"></i>Incorrect. Correct answer: <strong>${input.dataset.correct}</strong>`;
          fb.style.display = 'block';
        }
        answers[q].result = 'wrong';
      }

      if (hint) hint.style.display = 'block';

      updateProgress(total);

      if (checkedCount === inputs.length && submitFill) {
        submitFill.disabled = false;
      }
    });
  });

  if (submitFill) {
    submitFill.addEventListener('click', () => {
      submitScore(currentScore, total);
    });
  }
}

/* ===================================================
   Matching Exercise
   =================================================== */
function initMatching() {
  let selectedLeft = null;
  let selectedRight = null;
  const matches = {};
  const total = document.querySelectorAll('.left-item').length;

  // Shuffle right items (definitions) on load
  const rightCol = document.querySelector('.matching-col:has(.right-item)');
  if (rightCol) {
    const rightItems = Array.from(rightCol.querySelectorAll('.right-item'));
    for (let i = rightItems.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      rightCol.appendChild(rightItems[j]);
    }
  }

  document.querySelectorAll('.left-item').forEach(item => {
    item.addEventListener('click', function () {
      if (this.classList.contains('matched')) return;
      document.querySelectorAll('.left-item').forEach(i => i.classList.remove('selected'));
      this.classList.add('selected');
      selectedLeft = this;
      if (selectedRight) tryMatch();
    });
  });

  document.querySelectorAll('.right-item').forEach(item => {
    item.addEventListener('click', function () {
      if (this.classList.contains('matched')) return;
      document.querySelectorAll('.right-item').forEach(i => i.classList.remove('selected'));
      this.classList.add('selected');
      selectedRight = this;
      if (selectedLeft) tryMatch();
    });
  });

  // Double click to unpair
  document.querySelectorAll('.match-item').forEach(item => {
    item.addEventListener('dblclick', function () {
      if (this.classList.contains('matched')) {
        const id = this.dataset.id;
        if (this.classList.contains('left-item')) {
          const rightId = matches[id];
          delete matches[id];
          delete answers[id];
          this.classList.remove('matched');
          document.querySelector(`.right-item[data-id="${rightId}"]`)?.classList.remove('matched');
        } else {
          // Right item - find which left item it was paired with
          let leftId = null;
          for (const key in matches) {
            if (matches[key] === id) {
              leftId = key;
              break;
            }
          }
          if (leftId) {
            delete matches[leftId];
            delete answers[leftId];
            this.classList.remove('matched');
            document.querySelector(`.left-item[data-id="${leftId}"]`)?.classList.remove('matched');
          }
        }

        const submitBtn = document.getElementById('submit-matching');
        if (submitBtn) {
          submitBtn.disabled = Object.keys(matches).length !== total;
        }

        updateProgress(total);
      }
    });
  });

  function tryMatch() {
    const leftId = selectedLeft.dataset.id;
    const rightId = selectedRight.dataset.id;
    matches[leftId] = rightId;

    selectedLeft.classList.remove('selected');
    selectedRight.classList.remove('selected');
    selectedLeft.classList.add('matched');
    selectedRight.classList.add('matched');

    // Add to answers for real-time progress bar movement
    answers[leftId] = { matched: true };

    selectedLeft = null;
    selectedRight = null;

    // Enable check button if all matched
    const submitBtn = document.getElementById('submit-matching');
    if (submitBtn && Object.keys(matches).length === total) {
      submitBtn.disabled = false;
    }

    updateProgress(total);
  }

  const resetBtn = document.getElementById('reset-matching');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      Object.keys(matches).forEach(k => delete matches[k]);
      document.querySelectorAll('.match-item').forEach(i => {
        i.classList.remove('matched', 'selected', 'wrong-match', 'correct');
        i.disabled = false;
      });
      const res = document.getElementById('matching-result');
      if (res) res.style.display = 'none';
      selectedLeft = selectedRight = null;

      const submitBtn = document.getElementById('submit-matching');
      if (submitBtn) submitBtn.disabled = true;

      // Clear global answers and update progress
      Object.keys(answers).forEach(k => delete answers[k]);
      updateProgress(total);
    });
  }

  const submitMatching = document.getElementById('submit-matching');
  if (submitMatching) {
    submitMatching.addEventListener('click', () => {
      let score = 0;
      document.querySelectorAll('.left-item').forEach(left => {
        const id = left.dataset.id;
        const paired = matches[id];
        const correct = id; // correct right-item has same data-id
        if (paired === correct) {
          score++;
          left.classList.add('correct');
          document.querySelector(`.right-item[data-id="${paired}"]`)?.classList.add('correct');
          // `paired` is sent for every term so the server can re-check it.
          answers[id] = { result: 'correct', paired };
        } else {
          left.classList.add('wrong-match');
          if (paired) {
            document.querySelector(`.right-item[data-id="${paired}"]`)?.classList.add('wrong-match');
          }
          answers[id] = { result: 'wrong', paired };
        }
      });

      submitMatching.disabled = true;

      // Fill progress bar to 100%
      const progressBar = document.getElementById('q-progress-bar');
      if (progressBar) {
        progressBar.style.width = '100%';
        progressBar.style.transition = 'width 0.4s ease';
      }

      const res = document.getElementById('matching-result');
      if (res) {
        res.style.display = 'block';
        const pct = Math.round((score / total) * 100);
        res.className = score === total ? 'mt-3 matching-result-good' : 'mt-3 matching-result-bad';

        let feedbackHtml = score === total
          ? `<i class="fas fa-trophy me-2"></i>Perfect! All ${total} matches correct!`
          : `<i class="fas fa-info-circle me-2"></i>${score}/${total} correct. Review the correct pairings below:`;

        if (score < total) {
          feedbackHtml += `<div class="mt-4 text-start"><div class="row g-3">`;
          QUESTIONS_DATA.forEach(q => {
            feedbackHtml += `
              <div class="col-md-6">
                <div class="p-2 border rounded bg-white shadow-sm h-100">
                  <div class="fw-bold text-primary border-bottom pb-1 mb-1" style="font-size:0.85rem">${q.left}</div>
                  <div class="text-muted" style="font-size:0.8rem">${q.right}</div>
                </div>
              </div>`;
          });
          feedbackHtml += `</div></div>`;
        }
        res.innerHTML = feedbackHtml;
      }

      submitMatching.disabled = true;
      setTimeout(() => submitScore(score, total), 500);
    });
  }
}

/* ===================================================
   Vocabulary Bingo
   =================================================== */

/* Speech: pick the most natural-sounding English voice the browser offers,
   instead of the default (often robotic) fallback. Modern browsers ship
   high-quality "Natural"/"Online" neural voices — we prefer those, then
   good local voices, then any en-US voice. Voices load asynchronously, so
   we (re)resolve on the `voiceschanged` event. */
let _bingoVoice = null;
function pickNaturalVoice() {
  if (!('speechSynthesis' in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  const prefer = [
    /Microsoft.*(Aria|Jenny|Michelle|Guy|Ana).*Online.*Natural/i, // Edge neural
    /Google US English/i,                                          // Chrome
    /Natural/i,
    /Google.*English/i,
    /Samantha|Karen|Moira|Serena|Daniel/i,                         // Apple
    /Microsoft.*(Zira|David|Mark)/i,                               // Windows local
  ];
  for (const re of prefer) {
    const v = voices.find(v => re.test(v.name) && /en/i.test(v.lang));
    if (v) return v;
  }
  return voices.find(v => /en[-_]US/i.test(v.lang))
    || voices.find(v => /^en/i.test(v.lang))
    || voices[0];
}
function speakNaturally(text) {
  if (!('speechSynthesis' in window) || !text) return;
  try {
    window.speechSynthesis.cancel(); // avoid overlapping/queued utterances
    const u = new SpeechSynthesisUtterance(text);
    if (!_bingoVoice) _bingoVoice = pickNaturalVoice();
    if (_bingoVoice) { u.voice = _bingoVoice; u.lang = _bingoVoice.lang; }
    else { u.lang = 'en-US'; }
    u.rate = 0.95;  // a touch slower reads more clearly and human
    u.pitch = 1.0;
    u.volume = 1.0;
    window.speechSynthesis.speak(u);
  } catch (e) { /* speech is a nice-to-have; never break the game */ }
}
if ('speechSynthesis' in window) {
  // Re-resolve once the full voice list is available.
  window.speechSynthesis.onvoiceschanged = function () { _bingoVoice = pickNaturalVoice(); };
}

function initBingo() {
  const words = BINGO_DATA.slice();
  let sequence = [];
  let current = -1;
  let selections = [];   // selections[i] = { target, chosen } for each round
  let roundCell = null;  // the card picked in the current round (before advancing)
  let gameActive = false;

  // Shuffle helper
  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  const startBtn = document.getElementById('bingo-start');
  const nextBtn = document.getElementById('bingo-next');
  const wordEl = document.getElementById('bingo-current-word'); // shows the DEFINITION
  const defEl = document.getElementById('bingo-definition');   // shows the round counter
  const labelEl = document.querySelector('#bingo-exercise .bingo-word-label');
  const statusEl = document.getElementById('bingo-status');
  const submitBtn = document.getElementById('submit-bingo');
  const cells = Array.from(document.querySelectorAll('.bingo-cell'));

  function setStatus(text, cls) {
    if (!statusEl) return;
    statusEl.className = 'bingo-status-bar ' + (cls || 'bingo-status-playing');
    statusEl.textContent = text;
  }

  if (startBtn) {
    startBtn.addEventListener('click', () => {
      sequence = shuffle([...words]);
      current = -1;
      selections = [];
      roundCell = null;
      gameActive = true;
      startBtn.innerHTML = '<i class="fas fa-rotate-right me-1"></i>Restart';
      nextBtn.disabled = false;
      if (submitBtn) submitBtn.style.display = 'none';
      cells.forEach(c => c.classList.remove('marked', 'bingo-win', 'wrong', 'reveal', 'incorrect'));
      if (labelEl) labelEl.textContent = 'Read the definition and click the matching word:';
      showNextRound();
    });
  }

  // Show the next definition. The word itself stays hidden — the player must
  // recognise it from the definition, so the score reflects real knowledge.
  function showNextRound() {
    if (roundCell) { roundCell.classList.remove('marked'); roundCell = null; }
    current++;
    if (current >= sequence.length) { evaluate(); return; }

    const w = sequence[current];
    if (wordEl) wordEl.textContent = w.definition;
    if (defEl) defEl.textContent = 'Word ' + (current + 1) + ' of ' + sequence.length;
    setStatus('Click the word that matches this definition.', 'bingo-status-playing');

    // Read the definition aloud in a natural, human-like voice.
    speakNaturally(w.definition);
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (!gameActive) return;
      // You must pick a word before you can move on.
      if (!roundCell) {
        speakNaturally('Please click a word first.');
        setStatus('Click a word before moving on.', 'text-danger');
        return;
      }
      showNextRound();
    });
  }

  // Cell click: record the choice for THIS round and turn it blue — whether it
  // turns out right or wrong is only revealed at evaluation.
  cells.forEach(cell => {
    cell.addEventListener('click', function () {
      if (!gameActive || current < 0 || current >= sequence.length) return;
      if (roundCell && roundCell !== this) roundCell.classList.remove('marked');
      roundCell = this;
      this.classList.add('marked');
      selections[current] = { target: sequence[current].word, chosen: this.dataset.word };
      setStatus('Selected. Click “Next Word” to continue.', 'bingo-status-playing');
    });
  });

  // Grade every round at the end: green for correct picks, red for wrong ones
  // (with the right answer revealed), then surface the score.
  function evaluate() {
    gameActive = false;
    if (nextBtn) nextBtn.disabled = true;

    const byWord = {};
    cells.forEach(c => { byWord[c.dataset.word] = c; c.classList.remove('marked', 'bingo-win', 'wrong', 'reveal'); });

    let correct = 0;
    // Pass 1: correct picks turn green.
    selections.forEach(sel => {
      if (!sel || sel.chosen !== sel.target) return;
      correct++;
      const c = byWord[sel.chosen];
      if (c) c.classList.add('bingo-win');
    });
    // Pass 2: wrong picks turn red — and red always wins, even if that same
    // card happened to be a correct pick in another round.
    selections.forEach(sel => {
      if (!sel || sel.chosen === sel.target) return;
      const c = byWord[sel.chosen];
      if (c) { c.classList.remove('bingo-win'); c.classList.add('wrong'); }
    });

    // ---- BINGO: 5 correct answers in a row, column, or diagonal ----
    // The card is a 5x5 grid (cells are in row-major DOM order). A green
    // (correct) cell fills that square; a full line of greens is a BINGO.
    let bingoLines = 0;
    const size = 5;
    if (cells.length >= size * size) {
      const filled = cells.map(c => c.classList.contains('bingo-win'));
      const lines = [];
      for (let r = 0; r < size; r++) lines.push([0, 1, 2, 3, 4].map(c => r * size + c));
      for (let c = 0; c < size; c++) lines.push([0, 1, 2, 3, 4].map(r => r * size + c));
      lines.push([0, 6, 12, 18, 24]);
      lines.push([4, 8, 12, 16, 20]);
      lines.forEach(line => {
        if (line.every(i => filled[i])) {
          bingoLines++;
          line.forEach(i => cells[i] && cells[i].classList.add('bingo-line'));
        }
      });
    }

    const max = sequence.length;
    if (wordEl) wordEl.textContent = 'All done — see your score below.';
    if (defEl) defEl.textContent = '';
    if (bingoLines > 0) {
      setStatus('🎉 BINGO! ' + bingoLines + (bingoLines > 1 ? ' lines' : ' line') +
        ' — you matched ' + correct + ' of ' + max + '.', 'bingo-status-bingo');
    } else {
      setStatus('You matched ' + correct + ' of ' + max +
        ' correctly — no 5-in-a-row this time.', 'bingo-status-playing');
    }

    // Record the per-round choices so the server has the real answer data.
    selections.forEach((sel, i) => { if (sel) answers['w' + (i + 1)] = sel; });
    submitScore(correct, max);
  }
}

/* ===================================================
   Writing Submission
   =================================================== */

const DEFAULT_MIN_WORDS = 50;
const DEFAULT_MAX_WORDS = null;

function countWords(value) {
  const text = (value || '').trim();
  return text ? text.split(/\s+/).filter(Boolean).length : 0;
}

/*
 * Determine the word limits for each writing exercise.
 *
 * Proposal Section Writing specifically requires 150–200 words.
 * Other writing exercises continue using their existing minimum
 * requirement unless they explicitly define another range.
 */
function getWritingLimits(textarea) {
  const card = textarea.closest('.writing-prompt-card');

  const questionText = card
    ? (card.querySelector('.question-text')?.textContent || '').trim().toLowerCase()
    : '';

  const exerciseTitle = (
    document.querySelector('h2.text-white')?.textContent || ''
  ).trim().toLowerCase();

  /*
   * Proposal and Bid Writing -> Proposal Section Writing
   */
  if (
    exerciseTitle === 'proposal section writing' ||
    questionText.includes('proposal section')
  ) {
    return {
      min: 150,
      max: 200
    };
  }

  /*
   * Read an explicit range from the Guide text when available.
   * Examples:
   * 80-120 words
   * 80–120 words
   * 80 to 120 words
   */
  const guideText = card
    ? (card.querySelector('.writing-guide')?.textContent || '')
    : '';

  const range = guideText.match(
    /(\d+)\s*(?:[-–—]|to)\s*(\d+)\s*words/i
  );

  if (range) {
    return {
      min: parseInt(range[1], 10),
      max: parseInt(range[2], 10)
    };
  }

  const single = guideText.match(/(\d+)\s*words/i);

  if (single) {
    return {
      min: parseInt(single[1], 10),
      max: DEFAULT_MAX_WORDS
    };
  }

  return {
    min: DEFAULT_MIN_WORDS,
    max: DEFAULT_MAX_WORDS
  };
}

function initWriting() {
  const submitBtn = document.getElementById('submit-writing');
  if (!submitBtn) return;

  const prompts = document.querySelectorAll('.writing-input');

  /*
   * Update the visible word-limit message.
   */
  prompts.forEach(ta => {
    const card = ta.closest('.writing-prompt-card');
    const hint = card
      ? card.querySelector('.writing-min-hint')
      : null;

    const limits = getWritingLimits(ta);

    if (hint) {
      if (limits.max) {
        hint.textContent =
          `${limits.min}–${limits.max} words required`;
      } else {
        hint.textContent =
          `Minimum ${limits.min} words required`;
      }
    }
  });

  function refreshWritingState() {
    let requirementsMet = prompts.length > 0;

    prompts.forEach(p => {
      const words = countWords(p.value);
      const limits = getWritingLimits(p);

      const wcEl = document.getElementById(
        'wc-' + p.dataset.q
      );

      if (wcEl) {
        wcEl.textContent =
          words + ' word' + (words !== 1 ? 's' : '');

        if (words === 0) {
          wcEl.style.color = '#64748b';
        } else if (
          words >= limits.min &&
          (!limits.max || words <= limits.max)
        ) {
          wcEl.style.color = '#198754';
        } else {
          wcEl.style.color = '#dc3545';
        }
      }

      /*
       * Minimum validation
       */
      if (words < limits.min) {
        requirementsMet = false;
      }

      /*
       * Maximum validation
       */
      if (limits.max && words > limits.max) {
        requirementsMet = false;
      }
    });

    submitBtn.disabled = !requirementsMet;
  }

  prompts.forEach(ta => {
    ta.addEventListener('input', refreshWritingState);
  });

  /*
   * Validate immediately when the page loads.
   */
  refreshWritingState();

  submitBtn.addEventListener('click', () => {
    /*
     * Final validation before submission.
     * This prevents submission even if the button state was
     * manipulated through browser developer tools.
     */
    let invalid = false;

    prompts.forEach(ta => {
      const words = countWords(ta.value);
      const limits = getWritingLimits(ta);

      if (
        words < limits.min ||
        (limits.max && words > limits.max)
      ) {
        invalid = true;
      }
    });

    if (invalid) {
      refreshWritingState();

      alert(
        'Please make sure your response meets the required word count.'
      );

      return;
    }

    let totalScorePercent = 0;

    prompts.forEach(ta => {
      const q = ta.dataset.q;
      const text = ta.value.trim();
      const words = countWords(text);

      answers[q] = text;

      const limits = getWritingLimits(ta);
      const minTarget = limits.min;

      /*
       * Scoring logic
       */
      let qScore = 0;

      if (
        words >= minTarget &&
        (!limits.max || words <= limits.max)
      ) {
        qScore = 100;
      } else if (words >= minTarget * 0.7) {
        qScore = 80;
      } else if (words >= minTarget * 0.4) {
        qScore = 50;
      } else if (words > 0) {
        qScore = 20;
      }

      const card = ta.closest('.writing-prompt-card');

      /*
       * Check if user copied the question text
       */
      const qTextRaw = card
        ? (card.querySelector('.question-text')?.textContent || '')
        : '';

      const qText = qTextRaw.toLowerCase();

      if (
        text.toLowerCase().includes(qText) &&
        qText.length > 20
      ) {
        qScore *= 0.3;
      }

      /*
       * Required recommendations/examples
       */
      const reqMatch =
        qTextRaw.match(
          /(\d+)\s+(?:actionable\s+)?recommendations/i
        ) ||
        qTextRaw.match(/(\d+)\s+examples/i);

      if (reqMatch) {
        const countRequired = parseInt(reqMatch[1], 10);

        const listItems =
          text.match(/^\s*[\d\-\*\•][\.\)]\s+/gm) || [];

        const keywordStarts =
          text.match(
            /(?:^|\.)\s*(?:we\s+recommend|firstly|secondly|thirdly|finally|for\s+example|example\s+\d)/gi
          ) || [];

        const countFound = Math.max(
          listItems.length,
          keywordStarts.length,
          1
        );

        if (countFound < countRequired && words > 0) {
          const ratio = countFound / countRequired;
          qScore *= ratio;
        }
      }

      /*
       * Contextual relevance check
       */
      const dataPoints =
        qTextRaw.match(
          /\d+(?:\.\d+)?%?|\$\d+(?:\.\d+)?[MK]?/g
        ) || [];

      if (dataPoints.length >= 2) {
        let foundPoints = 0;

        dataPoints.forEach(dp => {
          if (text.includes(dp)) {
            foundPoints++;
          }
        });

        const relevanceRatio =
          foundPoints / dataPoints.length;

        if (relevanceRatio < 0.3) {
          qScore *= 0.4;
        } else if (relevanceRatio < 0.6) {
          qScore *= 0.8;
        }
      }

      /*
       * Sentence repetition detection
       */
      const sentences = text
        .split(/[.!?]+/)
        .map(s => s.trim().toLowerCase())
        .filter(s => s.length > 25);

      const uniqueSentences =
        new Set(sentences);

      if (
        sentences.length >
        uniqueSentences.size
      ) {
        const diff =
          sentences.length -
          uniqueSentences.size;

        const penalty = diff * 20;

        qScore = Math.max(
          0,
          qScore - penalty
        );
      }

      /*
       * Feedback
       */
      const feedbackItems = [];

      if (
        words >= minTarget &&
        (!limits.max || words <= limits.max)
      ) {
        feedbackItems.push(
          '<span class="text-success">✅ Word count target met</span>'
        );
      } else if (
        limits.max &&
        words > limits.max
      ) {
        feedbackItems.push(
          `<span class="text-danger">❌ Too many words (${words}/${limits.max} maximum)</span>`
        );
      } else {
        feedbackItems.push(
          `<span class="text-warning">⚠️ Below word target (${words}/${minTarget})</span>`
        );
      }

      if (
        sentences.length >
        uniqueSentences.size
      ) {
        feedbackItems.push(
          '<span class="text-danger">❌ Sentence repetition penalty applied</span>'
        );
      }

      /*
       * Advanced structure check
       */
      const guideText = card
        ? (
          card.querySelector('.writing-guide')
            ?.textContent || ''
        )
        : '';

      if (
        guideText.toLowerCase().includes('structure')
      ) {
        let structMet = 0;
        let structTotal = 0;

        if (guideText.match(/purpose/i)) {
          structTotal++;

          if (sentences.length >= 1) {
            structMet++;
          }
        }

        if (guideText.match(/findings/i)) {
          structTotal++;

          if (sentences.length >= 2) {
            structMet++;
          }
        }

        if (
          guideText.match(/recommendation/i)
        ) {
          structTotal++;

          if (
            text
              .toLowerCase()
              .match(/recommend|should|suggest/)
          ) {
            structMet++;
          }
        }

        if (
          structMet === structTotal
        ) {
          feedbackItems.push(
            '<span class="text-success">✅ Structure requirements followed</span>'
          );
        } else {
          feedbackItems.push(
            '<span class="text-danger">❌ Missing required sections (Findings/Recs)</span>'
          );

          qScore *=
            (structMet / structTotal || 0.5);
        }
      }

      totalScorePercent += qScore;

      ta.dataset.feedback =
        feedbackItems.join('<br>');
    });

    const avgScoreRaw =
      totalScorePercent / prompts.length;

    let finalScore = avgScoreRaw;

    /*
     * Cross-prompt duplication check
     */
    const allResponses =
      Array.from(prompts)
        .map(p => p.value.trim().toLowerCase())
        .filter(s => s.length > 50);

    const uniqueResponses =
      new Set(allResponses);

    if (
      allResponses.length >
      uniqueResponses.size
    ) {
      finalScore *= 0.4;
    }

    submitBtn.innerHTML = 'Submitting...';
    submitBtn.disabled = true;

    // Send to backend for AI grading. Empty customSummaryHtml so backend can provide it.
    submitScore(Math.round(finalScore), 100, '');
  });
}

/* ===================================================
   Timer Activity
   =================================================== */
function initTimer() {
  const DURATION = 60;
  let timeLeft = DURATION;
  let timerHandle = null;
  let running = false;
  let taskIdx = 0;
  const completedTasks = new Set();
  const totalTasks = TOTAL_QUESTIONS;

  const startBtn = document.getElementById('timer-start');
  const stopBtn = document.getElementById('timer-stop');
  const resetBtn = document.getElementById('timer-reset');
  const donePanel = document.getElementById('timer-done');
  const submitBtn = document.getElementById('submit-timer');
  const timerText = document.getElementById('timer-text');
  const arc = document.getElementById('timer-arc');
  const recordingStatus = document.getElementById('timer-recording-status');
  const recordingsSummary = document.getElementById('timer-recordings-summary');
  const CIRCUMFERENCE = 339.3;

  // Speech Recognition Setup
  const taskTranscripts = {};
  const taskInterim = {};
  const taskRecordings = {};
  let mediaRecorder = null;
  let mediaStream = null;
  let recordingChunks = [];
  let recordingMimeType = 'audio/webm';
  let recognition = null;
  // Index of the next not-yet-stored final result of the CURRENT recognition
  // session. Chrome restarts recognition on every pause, and each session
  // numbers its results from 0 again, so this resets in onstart.
  let sessionFinalIdx = 0;
  let recognitionEnded = null;   // resolver, set while we wait for a stop()

  const appendSpeech = (idx, text) => appendTranscript(taskTranscripts, idx, text);

  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRec();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = document.documentElement.lang || 'en-US';
    recognition.onstart = () => { sessionFinalIdx = 0; };
    recognition.onresult = (event) => {
      let interim = '';
      // Scan the whole cumulative result list, not from event.resultIndex:
      // a revision event can point back at results already stored.
      for (let i = 0; i < event.results.length; ++i) {
        const result = event.results[i];
        if (result.isFinal) {
          if (i >= sessionFinalIdx) {
            appendSpeech(taskIdx, result[0].transcript);
            sessionFinalIdx = i + 1;
          }
        } else {
          interim += result[0].transcript + ' ';
        }
      }
      taskInterim[taskIdx] = interim.trim();
    };
    recognition.onend = () => {
      if (recognitionEnded) {
        const resolve = recognitionEnded;
        recognitionEnded = null;
        resolve();
        return;
      }
      // Chrome stops recognition automatically after pauses.
      // Restart it if we're still running.
      if (running && recognition) {
        try { recognition.start(); } catch (e) {}
      }
    };
  }

  // Stop recognition and wait for the trailing final result, so the last
  // sentence the user spoke is not lost (and not counted twice).
  function stopRecognition() {
    if (!recognition) return Promise.resolve();
    return new Promise((resolve) => {
      let done = false;
      const finish = () => { if (!done) { done = true; recognitionEnded = null; resolve(); } };
      recognitionEnded = finish;
      try { recognition.stop(); } catch (e) { finish(); }
      // ponytail: fixed cap — onend always fires in practice, this is the net.
      setTimeout(finish, 800);
    });
  }

  function setArc(seconds) {
    const frac = seconds / DURATION;
    const offset = CIRCUMFERENCE * (1 - frac);
    if (arc) arc.style.strokeDashoffset = offset;
    if (arc) {
      arc.classList.toggle('warn', frac <= 0.5 && frac > 0.25);
      arc.classList.toggle('urgent', frac <= 0.25);
    }
  }

  function countWords(text) {
    return text.trim() ? text.trim().split(/\s+/).filter(Boolean).length : 0;
  }

  function renderRecordingsSummary() {
    if (!recordingsSummary) return;
    recordingsSummary.innerHTML = Object.keys(taskRecordings).sort((a, b) => a - b).map((idx) => `
      <div class="p-3 mb-2 rounded-3" style="background:#f8fafc;border:1px solid #e2e8f0;">
        <div class="fw-bold mb-2"><i class="fas fa-headphones text-primary me-2"></i>Task ${Number(idx) + 1} recording (${countWords(taskTranscripts[idx] || '')} words)</div>
        <audio controls class="w-100" src="${taskRecordings[idx].url}"></audio>
      </div>`).join('');
  }

  async function startTaskRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      throw new Error('Microphone recording is not supported in this browser.');
    }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeCandidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
      recordingMimeType = mimeCandidates.find((mime) => MediaRecorder.isTypeSupported(mime)) || 'audio/webm';
      mediaRecorder = new MediaRecorder(mediaStream, { mimeType: recordingMimeType });
      recordingChunks = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data?.size) recordingChunks.push(event.data);
      };
      // Keep one continuous recording so WebM timestamps match playback time.
      mediaRecorder.start();
      return true;
    } catch (error) {
      mediaRecorder = null;
      if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
      throw error;
    }
  }

  function stopTaskRecording(taskNumber) {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return Promise.resolve(false);
    const recorder = mediaRecorder;
    return new Promise((resolve) => {
      recorder.onstop = () => {
        const blob = new Blob(recordingChunks, { type: recorder.mimeType || recordingMimeType });
        const previousUrl = taskRecordings[taskNumber]?.url;
        if (previousUrl) URL.revokeObjectURL(previousUrl);
        const url = URL.createObjectURL(blob);
        taskRecordings[taskNumber] = { blob, url };
        const audio = document.getElementById('task-audio-' + taskNumber);
        const playback = document.getElementById('recording-' + taskNumber);
        if (audio && playback) {
          audio.src = url;
          audio.playbackRate = 1;
          audio.defaultPlaybackRate = 1;
          playback.style.display = 'block';
        }
        recordingChunks = [];
        if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
        mediaRecorder = null;
        resolve(blob.size > 0);
      };
      recorder.stop();
    });
  }

  async function finishTask() {
    clearInterval(timerHandle);
    running = false;               // before stopRecognition(), so onend does not restart
    await stopRecognition();       // flushes the last sentence as a final result
    // Anything still interim after the flush (browser never finalised it).
    appendSpeech(taskIdx, taskInterim[taskIdx]);
    taskInterim[taskIdx] = '';
    await stopTaskRecording(taskIdx);
    const wordCount = countWords(taskTranscripts[taskIdx] || '');
    const wordCountElement = document.getElementById('task-word-count-' + taskIdx);
    if (wordCountElement) {
      wordCountElement.innerHTML = `<i class="fas fa-align-left me-1"></i>${wordCount} words recorded`;
      wordCountElement.classList.toggle('text-danger', wordCount === 0);
    }
    if (recordingStatus) recordingStatus.textContent = '';
  }

  function hideTaskRecordings() {
    document.querySelectorAll('.timer-recording, .timer-word-count').forEach((element) => {
      element.style.display = 'none';
    });
  }

  function activateTask(index) {
    if (running || index < 0 || index >= totalTasks) return;
    hideTaskRecordings();
    taskIdx = index;
    document.querySelectorAll('.timer-task-card').forEach((card, i) => {
      card.classList.toggle('d-none', i !== taskIdx);
    });
    timeLeft = DURATION;
    if (timerText) timerText.textContent = DURATION;
    setArc(DURATION);
    if (startBtn) {
      startBtn.style.display = 'inline-block';
      startBtn.disabled = false;
      startBtn.innerHTML = `<i class="fas fa-play me-2"></i>Start Task ${taskIdx + 1}`;
    }
  }

  async function finishCurrentTask() {
    await finishTask();
    completedTasks.add(taskIdx);
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.innerHTML = `<i class="fas fa-check me-2"></i>Task ${taskIdx + 1} Recorded`;
    }
    if (stopBtn) stopBtn.style.display = 'none';

    document.querySelectorAll('.timer-dot').forEach((d, i) => {
      d.classList.toggle('active', i === taskIdx);
      d.classList.toggle('completed', completedTasks.has(i));
    });

    if (completedTasks.size === totalTasks) {
      renderRecordingsSummary();
      if (donePanel) donePanel.style.display = 'block';
      if (startBtn) startBtn.style.display = 'none';
      if (stopBtn) stopBtn.style.display = 'none';
      if (resetBtn) resetBtn.style.display = 'none';
      document.querySelectorAll('.timer-dot').forEach((d) => {
        d.classList.remove('active');
        d.classList.add('completed');
      });
    } else if (startBtn) {
      startBtn.innerHTML = `<i class="fas fa-arrow-right me-2"></i>Select Task ${taskIdx + 2}`;
    }
  }

  async function tick() {
    timeLeft--;
    if (timerText) timerText.textContent = timeLeft;
    setArc(timeLeft);
    if (timeLeft <= 0) {
      await finishCurrentTask();
    }
  }

  if (startBtn) {
    startBtn.addEventListener('click', async () => {
      if (running) return;
      if (completedTasks.has(taskIdx) && taskIdx + 1 < totalTasks) {
        activateTask(taskIdx + 1);
        return;
      }
      startBtn.disabled = true;
      startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting microphone...';
      const recordingStatus = document.getElementById('timer-recording-status');
      try {
        await startTaskRecording();
      } catch (error) {
        startBtn.disabled = false;
        startBtn.innerHTML = '<i class="fas fa-play me-2"></i>Start Task';
        if (recordingStatus) recordingStatus.textContent = 'Microphone could not start. Allow microphone access in the browser and try again.';
        console.error('Task recording failed:', error);
        return;
      }
      running = true;
      startBtn.innerHTML = '<i class="fas fa-microphone-alt me-2 anim-pulse"></i>Listening...';
      if (stopBtn) stopBtn.style.display = 'inline-block';
      if (recordingStatus) recordingStatus.textContent = 'Recording your voice...';
      if (recognition) try { recognition.start(); } catch (e) { }
      timerHandle = setInterval(tick, 1000);
    });
  }

  document.querySelectorAll('.timer-dot').forEach((dot, index) => {
    dot.style.cursor = 'pointer';
    dot.addEventListener('click', () => {
      if (index === taskIdx + 1 && completedTasks.has(taskIdx)) {
        activateTask(index);
      }
    });
  });

  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      if (!running) return;
      await finishCurrentTask();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      clearInterval(timerHandle);
      if (recognition) try { recognition.stop(); } catch (e) { }
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.onstop = null;
        mediaRecorder.stop();
      }
      if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
      mediaRecorder = null;
      mediaStream = null;
      Object.values(taskRecordings).forEach(({ url }) => URL.revokeObjectURL(url));
      Object.keys(taskRecordings).forEach((key) => delete taskRecordings[key]);
      document.querySelectorAll('.timer-recording').forEach((el) => { el.style.display = 'none'; });
      document.querySelectorAll('.timer-word-count').forEach((el) => { el.textContent = ''; });
      document.querySelectorAll('.timer-task-card audio').forEach((audio) => { audio.removeAttribute('src'); audio.load(); });
      running = false;
      timeLeft = DURATION;
      taskIdx = 0;
      // Clear transcripts
      for (const key in taskTranscripts) delete taskTranscripts[key];
      for (const key in taskInterim) delete taskInterim[key];
      completedTasks.clear();

      if (timerText) timerText.textContent = DURATION;
      setArc(DURATION);
      if (startBtn) { startBtn.disabled = false; startBtn.innerHTML = '<i class="fas fa-play me-2"></i>Start Task'; }
      if (stopBtn) stopBtn.style.display = 'none';
      if (donePanel) donePanel.style.display = 'none';
      if (recordingStatus) recordingStatus.textContent = '';
      if (recordingsSummary) recordingsSummary.innerHTML = '';
      document.querySelectorAll('.timer-task-card').forEach((c, i) => c.classList.toggle('d-none', i !== 0));

      // Reset dots
      document.querySelectorAll('.timer-dot').forEach((d, i) => {
        d.classList.toggle('active', i === 0);
        d.classList.remove('completed');
      });
    });
  }

  if (submitBtn) {
    submitBtn.addEventListener('click', () => {
      submitBtn.disabled = true;

      let totalScore = 0;
      let evaluatedTasks = 0;

      Object.keys(taskTranscripts).forEach(idx => {
        const text = taskTranscripts[idx].trim();
        if (!text) return;

        answers[Number(idx) + 1] = text;

        const words = text.split(/\s+/).filter(Boolean).length;
        evaluatedTasks++;

        // Relevance check
        const promptEl = document.getElementById('task-' + (parseInt(idx) + 1));
        const promptText = promptEl ? promptEl.querySelector('h5')?.textContent?.toLowerCase() : '';
        const keywords = promptText.match(/\b\w{4,}\b/g) || [];
        let matches = 0;
        keywords.forEach(kw => { if (text.toLowerCase().includes(kw)) matches++; });

        // Scoring per task: 50% for word count (target 70 wpm), 50% for relevance
        const wordScore = Math.min(1, words / (DURATION / 60 * 70));
        const relScore = keywords.length > 0 ? (matches / keywords.length) : 1;
        totalScore += (wordScore * 0.5 + relScore * 0.5);
      });

      const finalScore = evaluatedTasks > 0 ? Math.round((totalScore / totalTasks) * totalTasks) : 0;
      const playbackHtml = Object.keys(taskRecordings).sort((a, b) => a - b).map((idx) => `
        <div class="text-start mb-3"><strong>Task ${Number(idx) + 1} recording (${countWords(taskTranscripts[idx] || '')} words)</strong>
          <audio controls class="w-100 mt-2" src="${taskRecordings[idx].url}"></audio>
        </div>`).join('');
      submitScore(finalScore, totalTasks, playbackHtml);

      // Build improved version panel after score panel renders
      setTimeout(() => buildTimerImprovedVersion(taskTranscripts, totalTasks), 350);
    });
  }
}

/* Append speech to a task transcript, skipping anything already stored.
   Chrome revises interim results and can re-deliver a result index it already
   marked final (and stop() flushes the last interim as a final), so a plain
   append duplicated whole sentences. Pure — see the self-check at the bottom. */
function appendTranscript(store, idx, text) {
  const clean = (text || '').replace(/\s+/g, ' ').trim();
  if (!clean) return store;
  const current = store[idx] || '';
  if (current.trim().toLowerCase().endsWith(clean.toLowerCase())) return store;
  store[idx] = current + clean + ' ';
  return store;
}

/* ===================================================
   Timer — Improved Version Builder
   Generates per-task feedback cards showing:
     1. What the user actually said (transcript)
     2. Feedback badges (word count, keyword coverage)
     3. Keywords the user missed
     4. Actionable tips for a better answer
   =================================================== */
function buildTimerImprovedVersion(taskTranscripts, totalTasks) {
  const panel = document.getElementById('improved-version-panel');
  const body  = document.getElementById('improved-version-body');
  if (!panel || !body) return;

  const TARGET_WORDS = 70; // target 70 words in 60 seconds

  // Stopwords to skip when identifying key topic words
  const STOPWORDS = new Set([
    'this','that','with','from','have','your','more','into','they','when',
    'will','what','their','been','also','some','than','then','them','were',
    'which','about','would','could','should','does','just','like','very',
    'make','over','such','only','most','take','here','both','even','many',
    'much','same','these','those','other','each','long','task','deliver',
    'speak','practice','clearly','full','less','pitch'
  ]);

  let cardsHtml = '';

  for (let i = 0; i < totalTasks; i++) {
    const taskNum    = i + 1;
    const transcript = (taskTranscripts[i] || '').trim();
    const words      = transcript ? transcript.split(/\s+/).filter(Boolean).length : 0;

    // Pull task prompt text from DOM
    const promptEl   = document.getElementById('task-' + taskNum);
    const promptH5   = promptEl ? (promptEl.querySelector('h5')?.textContent || '') : '';
    const promptText = promptH5.replace(/^Task\s+\d+:\s*/i, '').trim();
    const hintEl     = promptEl ? promptEl.querySelector('p.text-muted') : null;
    const hintText   = hintEl ? hintEl.textContent.trim() : '';

    // Keywords from prompt (min 4 chars, not stopwords)
    const allKws    = (promptText.toLowerCase().match(/\b[a-z]{4,}\b/g) || []).filter(w => !STOPWORDS.has(w));
    const uniqueKws = [...new Set(allKws)];
    const lowerTr   = transcript.toLowerCase();
    const missedKws = uniqueKws.filter(kw => !lowerTr.includes(kw));
    const coveredKws = uniqueKws.filter(kw => lowerTr.includes(kw));
    const coveragePct = uniqueKws.length > 0 ? Math.round((coveredKws.length / uniqueKws.length) * 100) : 100;

    // ---- Feedback badges ----
    let badges = '';
    if (words >= TARGET_WORDS) {
      badges += `<span class="iv-badge iv-badge-ok"><i class="fas fa-check-circle"></i> ${words} words — great pace!</span>`;
    } else if (words >= Math.round(TARGET_WORDS * 0.6)) {
      badges += `<span class="iv-badge iv-badge-warn"><i class="fas fa-exclamation-circle"></i> ${words}/${TARGET_WORDS} words — speak a little faster</span>`;
    } else if (words > 0) {
      badges += `<span class="iv-badge iv-badge-bad"><i class="fas fa-times-circle"></i> Only ${words}/${TARGET_WORDS} words — too brief</span>`;
    } else {
      badges += `<span class="iv-badge iv-badge-bad"><i class="fas fa-microphone-slash"></i> Nothing recorded for this task</span>`;
    }
    if (uniqueKws.length > 0) {
      if (coveragePct >= 70) {
        badges += `<span class="iv-badge iv-badge-ok"><i class="fas fa-check-circle"></i> ${coveragePct}% topic coverage</span>`;
      } else if (coveragePct >= 40) {
        badges += `<span class="iv-badge iv-badge-warn"><i class="fas fa-exclamation-circle"></i> ${coveragePct}% topic coverage — add more key ideas</span>`;
      } else {
        badges += `<span class="iv-badge iv-badge-bad"><i class="fas fa-times-circle"></i> ${coveragePct}% topic coverage — stay more on-topic</span>`;
      }
    }

    // ---- Missed keywords ----
    let missedSection = '';
    if (missedKws.length > 0) {
      const chips = missedKws.slice(0, 10).map(kw =>
        `<span class="iv-keyword-chip"><i class="fas fa-times me-1" style="font-size:.6rem"></i>${kw}</span>`
      ).join('');
      missedSection = `
        <div>
          <div class="iv-section-label">Key concepts you didn't mention</div>
          <div class="iv-missed-keywords">${chips}</div>
        </div>`;
    }

    // ---- What you said ----
    const saidHtml = transcript
      ? `<div class="iv-what-you-said">&ldquo;${transcript}&rdquo;</div>`
      : `<div class="iv-what-you-said iv-empty"><i class="fas fa-microphone-slash me-1"></i>No speech was recorded for this task.</div>`;

    // ---- Improvement tips ----
    const tips = [];
    if (promptText) {
      tips.push(`Open by directly addressing the topic: <em>&ldquo;${promptText.charAt(0).toUpperCase() + promptText.slice(1)}&hellip;&rdquo;</em>`);
    }
    if (missedKws.length > 0) {
      tips.push(`Use key terms like <strong>${missedKws.slice(0, 4).join(', ')}</strong> to stay focused on the topic.`);
    }
    if (words < TARGET_WORDS) {
      const deficit = TARGET_WORDS - words;
      tips.push(`Add around <strong>${deficit} more words</strong> — expand with examples, reasons, or details.`);
    }
    if (hintText) {
      tips.push(`Follow the task hint: <em>&ldquo;${hintText}&rdquo;</em> as your structure guide.`);
    }
    tips.push('Speak at a steady, confident pace — aim for 1 clear point every 5–6 seconds.');

    const tipsLi = tips.map(t => `<li>${t}</li>`).join('');

    const scoreIndicatorColor = (coveragePct >= 70 && words >= Math.round(TARGET_WORDS * 0.6)) ? '#10b981'
      : (coveragePct >= 40 || words >= Math.round(TARGET_WORDS * 0.4)) ? '#f59e0b' : '#ef4444';

    cardsHtml += `
      <div class="iv-task-card">
        <div class="iv-task-title">
          <i class="fas fa-microphone-alt" style="color:${scoreIndicatorColor}"></i>
          Task ${taskNum}&nbsp;&mdash;&nbsp;${promptText || 'Timer Task'}
        </div>
        <div class="iv-task-body">
          <div>
            <div class="iv-section-label">What you said</div>
            ${saidHtml}
          </div>
          <div class="iv-feedback-row">${badges}</div>
          ${missedSection}
          <div class="iv-example-box">
            <div class="iv-example-label">
              <i class="fas fa-star" style="color:#10b981"></i> How to Improve
            </div>
            <ul class="iv-tips-list">${tipsLi}</ul>
          </div>
        </div>
      </div>`;
  }

  body.innerHTML = cardsHtml;
  panel.style.display = 'block';
  // Smooth scroll to the panel
  setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
}

/* ===================================================
   Performance-based progress, shown right after submitting
   =================================================== */
function showProgressUpdate(subProgress, activityProgress) {
  const panel = document.getElementById('result-panel');
  if (!panel || (!subProgress && !activityProgress)) return;
  let box = document.getElementById('result-progress-update');
  if (!box) {
    box = document.createElement('div');
    box.id = 'result-progress-update';
    box.className = 'mt-3 text-start';
    const details = document.getElementById('result-details');
    if (details) details.insertAdjacentElement('afterend', box);
    else panel.appendChild(box);
  }
  const row = (label, p) => {
    if (!p) return '';
    const pct = Math.max(0, Math.min(100, Number(p.percent) || 0));
    const band = ['success', 'warning', 'danger', 'secondary'].includes(p.band) ? p.band : 'secondary';
    const count = p.total ? ` \u00b7 ${p.attempted}/${p.total} exercises attempted` : '';
    return `<div class="mb-2">
        <div class="d-flex justify-content-between small mb-1">
          <span class="text-muted">${label}${count}</span>
          <strong class="text-${band}">${pct}%</strong>
        </div>
        <div class="progress" style="height:8px" role="progressbar" aria-label="${label}"
             aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
          <div class="progress-bar bg-${band}" style="width:${pct}%"></div>
        </div>
      </div>`;
  };
  box.innerHTML = '<div class="small fw-semibold mb-2">Your progress (based on scores)</div>' +
    row('This sub-activity', subProgress) + row('Whole activity', activityProgress);
}

/* ===================================================
   Ordering Exercise (drag-and-drop)
   =================================================== */
function initOrdering() {
  const list = document.querySelector('.ordering-list');
  if (!list) return;
  let dragEl = null;

  list.querySelectorAll('.ordering-item').forEach(item => {
    item.setAttribute('draggable', true);
    item.addEventListener('dragstart', () => {
      dragEl = item;
      setTimeout(() => item.style.opacity = '.4', 0);
    });
    item.addEventListener('dragend', () => {
      item.style.opacity = '1';
      list.querySelectorAll('.ordering-item').forEach(i => i.classList.remove('drag-over'));
    });
    item.addEventListener('dragover', e => {
      e.preventDefault();
      list.querySelectorAll('.ordering-item').forEach(i => i.classList.remove('drag-over'));
      item.classList.add('drag-over');
    });
    item.addEventListener('drop', e => {
      e.preventDefault();
      if (dragEl !== item) list.insertBefore(dragEl, item);
    });
  });

  const submitBtn = document.getElementById('submit-ordering');
  if (submitBtn) {
    submitBtn.addEventListener('click', () => {
      const items = list.querySelectorAll('.ordering-item');
      let score = 0;
      items.forEach((item, idx) => {
        const correct = parseInt(item.dataset.correct, 10);
        if (idx + 1 === correct) score++;
        answers[idx + 1] = { placed: idx + 1, correct };
      });
      submitBtn.disabled = true;
      submitScore(score, TOTAL_QUESTIONS);
    });
  }
}

/* ===================================================
   Boot — initialise the right exercise type
   =================================================== */
document.addEventListener('DOMContentLoaded', () => {
  switch (EXERCISE_TYPE) {
    case 'mcq': initMCQ(); break;
    case 'fill_blank': initFillBlank(); break;
    case 'matching': initMatching(); break;
    case 'bingo': initBingo(); break;
    case 'writing': initWriting(); break;
    case 'timer': initTimer(); break;
    case 'ordering': initOrdering(); break;
  }
});

// Node-only export, for performance-testing/timer-speech-dedup.check.js.
if (typeof module !== 'undefined' && module.exports) module.exports = { appendTranscript };

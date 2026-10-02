/**
 * GD Room — WebSocket + TTS + Speech Recognition
 * v6.0 — Typewriter for all speakers incl. user; fixed undefined transcript bug.
 */

// ── State ─────────────────────────────────────────────────────────────────────
const SESSION_ID   = parseInt(window.__GD_SESSION_ID__, 10);
let socket         = null;
let recognition    = null;
let isUserSpeaking = false;
let gdStarted      = false;
let isEnded        = false;

const languageSelect = document.getElementById('languageSelect');

function highlightBilingual(vn, en) {
    const isVietnam = languageSelect?.value === "vietnam";
    return isVietnam ? `<span class="text-slate-800 font-bold">${vn}</span> <span class="text-slate-400 font-normal">(${en})</span>` : en;
}

function updateUILanguage() {
    const isVietnam = languageSelect?.value === "vietnam";
    
    const uiTranslations = {
        "headerArena": { en: "Discussion Arena", vn: "Đấu trường Thảo luận" },
        "labelEndSession": { en: "End Session", vn: "Kết thúc Phiên" },
        "labelEndSessionFooter": { en: "End Session", vn: "Kết thúc Phiên" },
        "labelReadyStart": { en: "Ready to start?", vn: "Sẵn sàng bắt đầu?" },
        "labelStartInstructions": { en: "Press the Start button below to invite the agents into the conversation.", vn: "Nhấn nút Bắt đầu bên dưới để mời các nhân vật vào cuộc trò chuyện." },
        "labelViewReport": { en: "View Performance Report", vn: "Xem báo cáo Kết quả" },
        "labelStartDiscussion": { en: "Start Discussion", vn: "Bắt đầu Thảo luận" },
        "labelSpeakNow": { en: "Speak Now", vn: "Nói ngay" },
        "labelDoneSpeaking": { en: "Done Speaking", vn: "Hoàn tất Nói" },
        "labelResumeGD": { en: "Resume GD", vn: "Tiếp tục Thảo luận" }
    };

    Object.entries(uiTranslations).forEach(([id, langData]) => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = isVietnam ? highlightBilingual(langData.vn, langData.en) : langData.en;
        }
    });

    // Sidebar Items
    const sidebarTranslations = [
        { selector: '.badge-jam-easy', en: 'Easy', vn: 'Dễ' },
        { selector: '.badge-jam-medium', en: 'Medium', vn: 'Vừa' },
        { selector: '.badge-jam-hard', en: 'Hard', vn: 'Khó' }
    ];
    // Note: GD uses its own styles, let's target specific sidebar labels if they had IDs.
    // Since I didn't add IDs to sidebar in HTML yet, I'll do it via querySelector for now or add them in next step.
    // Actually, I'll update room.html again to add IDs to sidebar labels for cleaner access.
    
    // Status text translation
    const currentStatus = statusText?.textContent || "";
    if (currentStatus.includes("Connected")) {
        setStatus('Connected — press Start to begin', 'blue');
    } else if (currentStatus.includes("Discussion in progress")) {
        setStatus('Discussion in progress…', 'green');
    } else if (currentStatus.includes("You are speaking")) {
        setStatus('You are speaking…', 'amber');
    } else if (currentStatus.includes("Analysing your performance")) {
        setStatus('Analysing your performance…', 'amber');
    } else if (currentStatus.includes("Session ended")) {
        setStatus('Session ended', 'off');
    }
}

languageSelect?.addEventListener('change', updateUILanguage);

// ── Agent TTS voice configs ───────────────────────────────────────────────────
// `speaker` is a Sarvam bulbul:v3 voice — the neural engine the chatbot uses.
// pitch/rate/volume shape the BROWSER fallback only; the neural voice carries
// its own character and does not take them.
const AGENT_VOICE_CONFIG = {
  alex:  { pitch: 0.85, rate: 0.90, volume: 1.0, speaker: 'anand' },
  maya:  { pitch: 1.20, rate: 1.02, volume: 1.0, speaker: 'shreya' },
  rishi: { pitch: 1.00, rate: 0.95, volume: 1.0, speaker: 'rahul' },
};

// One <audio> element reused for every neural turn, so a new turn always
// replaces the previous one instead of overlapping it.
const neuralAudio = new Audio();
let neuralAudioFailed = false;   // true once the endpoint has let us down

/* Fetch one turn's neural audio. Resolves to a base64 WAV, or null when the
   endpoint is unavailable — the caller then falls back to the browser voice. */
async function fetchNeuralAudio(text, speaker) {
  if (neuralAudioFailed) return null;
  try {
    const resp = await fetch('/api/voice/tts/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        language: 'english',
        speaker,
        emotion: window.VoiceProsody
          ? window.VoiceProsody.detectEmotion(text, 'en')
          : 'neutral',
      }),
    });
    const data = await resp.json();
    return (data && data.success && data.audio) ? data.audio : null;
  } catch (e) {
    // Network/endpoint gone: stop retrying for the rest of the session rather
    // than adding a failed round trip before every single turn.
    neuralAudioFailed = true;
    return null;
  }
}

// ── Voice loading ─────────────────────────────────────────────────────────────
let availableVoices = [];
function loadVoices() { availableVoices = window.speechSynthesis.getVoices(); }
if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = loadVoices;
  loadVoices();
}

function pickVoice(agentKey) {
  const en     = availableVoices.filter(v => v.lang.startsWith('en'));
  if (!en.length) return null;
  const male   = en.filter(v => /male/i.test(v.name));
  const female = en.filter(v => /female/i.test(v.name));
  if (agentKey === 'maya')  return female[0] || en[1] || en[0];
  if (agentKey === 'alex')  return male[0]   || en[2] || en[0];
  if (agentKey === 'rishi') return male[1]   || male[0] || en[0];
  return en[0];
}

// ── TTS + Typewriter Queue ────────────────────────────────────────────────────
// Each item: { text, agentKey, avatar, speakerName, isUser }
// Text is NOT rendered until _playNext() picks it up (except user items are queued separately).
let ttsQueue       = [];
let isSpeakingTTS  = false; // set SYNCHRONOUSLY before speak() — no race condition
let ttsAborted     = false;
let currentProsody = null;   // handle for the clause chain being spoken
let ttsResumeTimer = null;
let typewriterTimer= null;

/** Add an agent message. Renders + speaks in order. */
function enqueueMessage(msgData) {
  if (isEnded) return;
  ttsQueue.push(msgData);
  if (!isSpeakingTTS) _playNext();
}

async function _playNext() {
  if (ttsResumeTimer)  { clearInterval(ttsResumeTimer);  ttsResumeTimer  = null; }
  if (typewriterTimer) { clearInterval(typewriterTimer); typewriterTimer = null; }

  if (ttsAborted || ttsQueue.length === 0) {
    isSpeakingTTS = false;
    return;
  }

  const item = ttsQueue.shift();
  const { text, agentKey, avatar, speakerName, isUser } = item;

  // ── 1. Render empty bubble ─────────────────────────────────────────────────
  const bubble = _createBubble(agentKey, avatar, speakerName, isUser);

  // ── 2. Set flag SYNCHRONOUSLY (avoids race condition) ─────────────────────
  isSpeakingTTS = true;

  const sidebarRow = document.getElementById(`agent-${agentKey}`);
  if (sidebarRow && !isUser) sidebarRow.classList.add('speaking');

  // ── 3. Typewriter cursor ───────────────────────────────────────────────────
  const cursor = document.createElement('span');
  cursor.className = 'typewriter-cursor';
  bubble.appendChild(cursor);

  // ── 3. Typewriter speed (USER ONLY) ───────────────────────────────────────
  const cfg = isUser
    ? { rate: 3.5 } // user text types extremely fast
    : (AGENT_VOICE_CONFIG[agentKey] || AGENT_VOICE_CONFIG.rishi);
  
  if (isUser) {
    const charsPerSec = 60;
    let charIndex = 0;
    typewriterTimer = setInterval(() => {
      if (ttsAborted) {
        clearInterval(typewriterTimer);
        if (cursor.parentNode) cursor.remove();
        bubble.textContent = text;
        return;
      }
      if (charIndex < text.length) {
        charIndex += 4;
        bubble.textContent = text.slice(0, charIndex);
        bubble.appendChild(cursor);
        scrollBottom();
      } else {
        clearInterval(typewriterTimer);
        typewriterTimer = null;
        if (cursor.parentNode) cursor.remove();
      }
    }, 1000 / charsPerSec);

    const waitForTypewriter = setInterval(() => {
      if (!typewriterTimer) {
        clearInterval(waitForTypewriter);
        isSpeakingTTS = false;
        if (!ttsAborted) _playNext();
      }
    }, 100);
    return;
  }

  // ── 5. Agent: speak via TTS ────────────────────────────────────────────────
  // Each agent keeps its own pitch/rate identity (AGENT_VOICE_CONFIG); the
  // prosody engine bends that baseline clause by clause around the
  // punctuation and tints the turn happy or sad, so the three agents sound
  // like people arguing rather than three flat readers.
  const v = pickVoice(agentKey);

  // ★ KEY: Hybrid Sync (Steady typewriter + Boundary snapping)
  let currentSpeechIndex = 0;
  let displayedIndex = 0;
  const estimatedCharsPerSec = 15 * (cfg.rate || 1.0); // Approx typing speed based on voice rate
  const msPerChar = 1000 / estimatedCharsPerSec;

  // Boundary indexes arrive against the FULL turn (the engine offsets each
  // clause), so the typewriter stays in sync across the split.
  const onBoundary = (charIndex, event) => {
    if (event && event.name !== 'word') return;
    const boundaryIndex = charIndex + ((event && event.charLength) || 0);
    if (displayedIndex < boundaryIndex) {
      displayedIndex = boundaryIndex;
    }
  };

  const onStart = () => {
    // Start the typewriter loop
    typewriterTimer = setInterval(() => {
      if (ttsAborted) {
        clearInterval(typewriterTimer);
        return;
      }

      // 1. Move the display index forward at a steady estimated pace
      if (displayedIndex < text.length) {
        displayedIndex++;
        bubble.textContent = text.slice(0, displayedIndex);
        bubble.appendChild(cursor);
        scrollBottom();
      } else {
        clearInterval(typewriterTimer);
      }
    }, msPerChar);
  };

  const handleDone = () => {
    if (ttsResumeTimer)  { clearInterval(ttsResumeTimer);  ttsResumeTimer  = null; }
    if (typewriterTimer) { clearInterval(typewriterTimer); typewriterTimer = null; }
    if (cursor.parentNode) cursor.remove();
    bubble.textContent = text;   // ensure full text
    isSpeakingTTS = false;
    if (sidebarRow) sidebarRow.classList.remove('speaking');
    if (!ttsAborted) _playNext();
  };

  // Neural voice first — that is what stops the agents sounding synthetic.
  // The browser engine is only a fallback for when the endpoint is not there.
  if (!ttsAborted) {
    const audio = await fetchNeuralAudio(text, cfg.speaker);
    if (audio && !ttsAborted) {
      neuralAudio.src = `data:audio/wav;base64,${audio}`;
      neuralAudio.onended = handleDone;
      neuralAudio.onerror = handleDone;
      // The typewriter has no word boundaries from an <audio> element, so it
      // runs on its own steady clock for the duration of the clip.
      onStart();
      currentProsody = { cancel: () => { try { neuralAudio.pause(); } catch (e) {} } };
      try {
        await neuralAudio.play();
      } catch (e) {
        handleDone();
      }
      return;
    }
  }

  // Only speak if we haven't just aborted (user interrupted)
  if (ttsAborted) {
    handleDone();
  } else if (window.VoiceProsody) {
    currentProsody = window.VoiceProsody.speak(text, {
      lang: 'en-US',
      voice: v || null,
      pitch: cfg.pitch,
      rate: cfg.rate,
      volume: cfg.volume,
      language: 'en',
    }, {
      onstart: onStart,
      onboundary: onBoundary,
      onend: handleDone,
    });
  } else {
    // Prosody module missing — fall back to one flat utterance per turn.
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'en-US';
    utter.pitch = cfg.pitch;
    utter.rate = cfg.rate;
    utter.volume = cfg.volume;
    if (v) utter.voice = v;
    utter.onstart = onStart;
    utter.onboundary = (event) => onBoundary(event.charIndex, event);
    utter.onend = handleDone;
    utter.onerror = (e) => {
      if (e && e.error === 'interrupted') return;
      handleDone();
    };
    window.speechSynthesis.speak(utter);
  }

  // TTS speed is already set via utter.rate

  // Chrome stall bug: ping every 10 s to keep TTS alive
  ttsResumeTimer = setInterval(() => {
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }
  }, 10000);
}

/** Create an empty message bubble; return the .message-bubble element */
function _createBubble(agentKey, avatar, speakerName, isUser = false) {
  const empty = chatFeed.querySelector('.empty-chat');
  if (empty) empty.remove();

  const wrap = document.createElement('div');
  wrap.className = `message-wrap theme-${agentKey}${isUser ? ' user-msg' : ''}`;
  wrap.innerHTML = `
    <div class="avatar-circle">${avatar}</div>
    <div class="message-body">
      <div class="speaker-label">${speakerName}</div>
      <div class="message-bubble"></div>
    </div>
  `;
  chatFeed.appendChild(wrap);
  scrollBottom();
  return wrap.querySelector('.message-bubble');
}

function stopAllTTS() {
  ttsAborted = true;
  ttsQueue   = [];
  if (ttsResumeTimer)  { clearInterval(ttsResumeTimer);  ttsResumeTimer  = null; }
  if (typewriterTimer) { clearInterval(typewriterTimer); typewriterTimer = null; }
  // cancel() silences the clause being spoken but not the timer waiting to
  // start the next one — the user interrupting must stop the whole turn.
  if (currentProsody) { try { currentProsody.cancel(); } catch (e) {} currentProsody = null; }
  try { neuralAudio.pause(); neuralAudio.removeAttribute('src'); } catch (e) {}
  
  if (window.speechSynthesis) {
    // Clear everything
    window.speechSynthesis.pause(); 
    window.speechSynthesis.cancel();
    // Sometimes a second cancel is needed for certain browsers to clear the buffer
    window.speechSynthesis.cancel();
  }
  
  isSpeakingTTS = false;
  ['alex', 'maya', 'rishi', 'user'].forEach(k => {
    const el = document.getElementById(`agent-${k}`);
    if (el) el.classList.remove('speaking');
  });

  // Clear any pending bubbles being typed
  const bubbles = document.querySelectorAll('.typewriter-cursor');
  bubbles.forEach(c => {
    const b = c.parentNode;
    if (b) c.remove();
  });

  // Reset abort flag after a short delay to allow next messages
  setTimeout(() => { ttsAborted = false; }, 500);
}

// ── DOM refs ──────────────────────────────────────────────────────────────────
const chatFeed       = document.getElementById('chat-feed');
const statusText     = document.getElementById('status-text');
const statusDot      = document.getElementById('status-dot');
const startBtn       = document.getElementById('btn-start');
const resumeBtn      = document.getElementById('btn-resume');
const speakBtn       = document.getElementById('btn-speak');
const endBtn         = document.getElementById('btn-end');
const endBtnFooter   = document.getElementById('btn-end-footer');
const typingWrap     = document.getElementById('typing-indicator');
const speakOverlay   = document.getElementById('speak-overlay');
const liveTranscript = document.getElementById('live-transcript');
const timerEl        = document.getElementById('gd-timer');

let timeLeft         = 300;
let timerInterval    = null;

function startTimer(seconds) {
  timeLeft = seconds;
  if (timerEl) timerEl.classList.remove('hidden');
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      onEndClick(); // Auto end session
      return;
    }
    timeLeft--;
    updateTimerUI();
  }, 1000);
}

function updateTimerUI() {
  if (!timerEl) return;
  const m = Math.floor(timeLeft / 60);
  const s = timeLeft % 60;
  timerEl.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${proto}://${location.host}/ws/GD_app/${SESSION_ID}/`);
  socket.onopen    = () => setStatus('Connected — press Start to begin', 'blue');
  socket.onmessage = ({ data }) => handleServerMsg(JSON.parse(data));
  socket.onclose   = () => {
    setStatus('Disconnected', 'off');
    if (gdStarted) setTimeout(connectWS, 2000);
  };
  socket.onerror = () => setStatus('Connection error', 'off');
}

function sendWS(data) {
  if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data));
}

// ── Message router ────────────────────────────────────────────────────────────
function handleServerMsg(msg) {
  // Sidebar highlights
  if (msg.type === 'status' && msg.status === 'user_speaking') {
    ['alex', 'maya', 'rishi'].forEach(k => {
      const el = document.getElementById(`agent-${k}`);
      if (el) el.classList.remove('speaking');
    });
    const u = document.getElementById('agent-user');
    if (u) u.classList.add('speaking');
  }
  if (msg.type === 'message' || msg.type === 'typing') {
    const u = document.getElementById('agent-user');
    if (u) u.classList.remove('speaking');
  }

  switch (msg.type) {
    case 'status':  handleStatus(msg); break;
    case 'typing':  showTyping(msg);   break;

    case 'message':
      hideTyping();
      if (!msg.is_user) {
        // Agent message — queue for ordered TTS + typewriter
        enqueueMessage({
          text:        msg.content,
          agentKey:    msg.speaker,
          avatar:      msg.avatar,
          speakerName: msg.speaker_name,
          isUser:      false,
        });
      }
      // User message is already rendered client-side in finishSpeaking()
      // Ignore the server echo to avoid duplicates.
      break;

    case 'report':
      isEnded = true;
      stopAllTTS();
      // Navigate directly to the full report page as requested
      window.location.href = `/gd/report/${SESSION_ID}/`;
      break;
  }
}

function handleStatus(msg) {
  const isVietnam = languageSelect?.value === "vietnam";
  switch (msg.status) {
    case 'started':
      gdStarted = true;
      setStatus('Discussion in progress…', 'green');
      startTimer(300); // 5 minutes
      if (startBtn) startBtn.classList.add('hidden');
      if (resumeBtn) resumeBtn.classList.add('hidden');
      if (speakBtn) speakBtn.classList.remove('hidden');
      if (endBtn)   endBtn.classList.remove('hidden');
      if (endBtnFooter) endBtnFooter.classList.remove('hidden');
      break;
    case 'user_speaking':
      setStatus('You are speaking…', 'amber');
      break;
    case 'analyzing':
      setStatus('Analysing your performance…', 'amber');
      if (speakBtn) speakBtn.classList.add('hidden');
      if (endBtn)   endBtn.classList.add('hidden');
      if (endBtnFooter) endBtnFooter.classList.add('hidden');
      break;
    case 'ended':
      gdStarted = false;
      isEnded = true;
      stopAllTTS();
      setStatus('Session ended', 'off');
      break;
  }
}

// ── Typing indicator ──────────────────────────────────────────────────────────
// ── Typing indicator removed ──
function showTyping(msg) { /* logic removed */ }
function hideTyping() { /* logic removed */ }

// ── Controls ──────────────────────────────────────────────────────────────────
if (startBtn) {
  startBtn.addEventListener('click', () => {
    const isVietnam = languageSelect?.value === "vietnam";
    sendWS({ action: 'start', language: languageSelect?.value || 'english' });
    startBtn.disabled    = true;
    startBtn.textContent = isVietnam ? 'Đang khởi động…' : 'Starting…';
  });
}
if (resumeBtn) {
  resumeBtn.addEventListener('click', () => {
    const isVietnam = languageSelect?.value === "vietnam";
    sendWS({ action: 'start', language: languageSelect?.value || 'english' }); // Same action as start
    resumeBtn.disabled    = true;
    resumeBtn.textContent = isVietnam ? 'Đang tiếp tục…' : 'Resuming…';
  });
}

if (speakBtn) {
  speakBtn.addEventListener('click', () => {
    if (isUserSpeaking) return;
    stopAllTTS();
    sendWS({ action: 'user_speaking' });
    startSpeechRecognition();
  });
}

const onEndClick = () => {
  isEnded = true;
  stopAllTTS();
  gdStarted = false;
  if (timerInterval) clearInterval(timerInterval);
  sendWS({ action: 'end' });
  if (speakBtn) speakBtn.classList.add('hidden');
  if (endBtn) endBtn.classList.add('hidden');
  if (endBtnFooter) endBtnFooter.classList.add('hidden');
  
  const isVietnam = languageSelect?.value === "vietnam";
  // Show an inline analyzing card in the arena
  const analyzingCard = document.createElement('div');
  analyzingCard.className = 'flex flex-col items-center justify-center p-12 bg-white rounded-[32px] border border-slate-100 shadow-xl shadow-slate-200/50 text-center animate-pulse';
  analyzingCard.innerHTML = `
    <div class="w-16 h-16 bg-sky-600 text-white rounded-2xl flex items-center justify-center mx-auto mb-6">
      <span class="material-symbols-outlined text-[32px]">analytics</span>
    </div>
    <h2 class="font-serif font-bold text-2xl text-slate-900 mb-2">${isVietnam ? 'Đang phân tích Phiên...' : 'Analyzing Session...'}</h2>
    <p class="text-slate-400 font-serif">${isVietnam ? 'Chúng tôi đang đánh giá kết quả của bạn. Vui lòng chờ.' : 'We are evaluating your performance. Please wait.'}</p>
  `;
  chatFeed.appendChild(analyzingCard);
  scrollBottom();

  setStatus('Ending session…', 'amber');
};

if (endBtn) endBtn.addEventListener('click', onEndClick);
if (endBtnFooter) endBtnFooter.addEventListener('click', onEndClick);

const closeArenaBtn = document.getElementById('btn-close-arena');
if (closeArenaBtn) {
  closeArenaBtn.addEventListener('click', (e) => {
    stopAllTTS();
    if (socket) socket.close();
  });
}

// ── Speech Recognition ────────────────────────────────────────────────────────
let liveUserBubble = null;

function startSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const isVietnam = languageSelect?.value === "vietnam";
  if (!SR) {
    alert(isVietnam ? 'Nhận dạng giọng nói yêu cầu Chrome. Vui lòng sử dụng Google Chrome.' : 'Speech recognition requires Chrome. Please use Google Chrome.');
    sendWS({ action: 'user_message', content: '' });
    return;
  }

  isUserSpeaking = true;
  if (speakBtn) speakBtn.classList.add('hidden');
  const doneBtn = document.getElementById('btn-done-speaking');
  if (doneBtn) doneBtn.classList.remove('hidden');

  // Create the bubble IMMEDIATELY in the arena
  liveUserBubble = _createBubble('user', '🧑', isVietnam ? 'Bạn' : 'You', true);
  if (liveUserBubble) {
    liveUserBubble.textContent = isVietnam ? 'Đang lắng nghe...' : 'Listening...';
    scrollBottom();
  }

  recognition = new SR();
  recognition.continuous     = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;
  
  // Set language based on selected language (fallback to browser preference)
  const langMap = {
    "english": "en-US", "en": "en-US",
    "hindi": "hi-IN", "hi": "hi-IN",
    "vietnam": "vi-VN", "vietnamese": "vi-VN",
    "arabic": "ar-SA",
    "russian": "ru-RU", "ru": "ru-RU"
  };
  const currentLang = languageSelect ? languageSelect.value : 'english';
  const userLang = langMap[currentLang] || navigator.language || 'en-US';
  recognition.lang = userLang;
  console.log('Starting recognition with lang:', userLang);

  let lastTranscript = '';

  recognition.onresult = (e) => {
    let final = '';
    let interim = '';
    for (let i = 0; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript + ' ';
      else interim += e.results[i][0].transcript;
    }
    lastTranscript = (final + interim).trim();

    // Update the bubble LIVE in the Arena
    if (liveUserBubble) {
      // Use innerText for safer, cleaner rendering
      liveUserBubble.innerText = lastTranscript || (isVietnam ? 'Đang lắng nghe...' : 'Listening...');
      scrollBottom();
    }
  };

  recognition.onerror = (e) => {
    console.warn('Speech recognition error:', e.error);
    finishSpeaking(lastTranscript);
  };

  recognition.onend = () => {
    finishSpeaking(lastTranscript);
  };

  try {
    recognition.start();
  } catch (err) {
    console.error('Could not start recognition:', err);
    finishSpeaking('');
  }
}

function stopRecognition() {
  if (recognition) {
    try { recognition.stop(); } catch(_) {}
    recognition = null;
  }
}

document.getElementById('btn-done-speaking').addEventListener('click', stopRecognition);

/** Called when user finishes speaking. Renders their message then resumes agents. */
function finishSpeaking(text) {
  if (!isUserSpeaking) return;
  isUserSpeaking = false;
  
  if (speakBtn) speakBtn.classList.remove('hidden');
  const doneBtn = document.getElementById('btn-done-speaking');
  if (doneBtn) doneBtn.classList.add('hidden');

  // Clean up text
  const clean = (text || '').replace(/\b(undefined|null)\b/g, '').trim();

  if (clean && liveUserBubble) {
    liveUserBubble.textContent = clean;
  } else if (liveUserBubble) {
    // If user said nothing, remove the empty bubble
    liveUserBubble.closest('.message-wrap').remove();
  }

  liveUserBubble = null;

  // Send to server for context and DB persistence
  sendWS({ action: 'user_message', content: clean, language: languageSelect?.value || 'english' });
  setStatus('Discussion in progress…', 'green');
}

// ── Report modal ──────────────────────────────────────────────────────────────
function showReport(report) {
  const errEl = document.getElementById('report-error');
  if (report.error && !report.overall_score) {
    if (errEl) { errEl.textContent = report.error; errEl.classList.remove('hidden'); }
  }

  const overall = report.overall_score || 0;
  const scoreEl = document.getElementById('overall-score');
  if (scoreEl) scoreEl.textContent = overall;
  animateScoreRing(overall);

  ['fluency', 'grammar', 'relevance', 'confidence'].forEach(d => {
    const data  = report[d] || {};
    const score = data.score || 0;
    const el    = document.getElementById(`dim-${d}`);
    if (!el) return;
    const scoreEl = el.querySelector('.dim-score');
    if (scoreEl) scoreEl.textContent = `${score}/25`;
    
    const fillEl = el.querySelector('.progress-bar-fill');
    if (fillEl) fillEl.style.width = `${(score / 25) * 100}%`;
    
    const feedbackEl = el.querySelector('.dim-feedback');
    if (feedbackEl) feedbackEl.textContent = data.feedback || '—';
  });

  const strEl = document.getElementById('strengths-list');
  const impEl = document.getElementById('improvements-list');
  if (strEl) strEl.innerHTML = (report.strengths    || []).map(s => `<li>✅ ${escHtml(s)}</li>`).join('') || '<li>No data</li>';
  if (impEl) impEl.innerHTML = (report.improvements || []).map(i => `<li>💡 ${escHtml(i)}</li>`).join('') || '<li>No data</li>';

  const sumEl = document.getElementById('summary-text');
  if (sumEl) sumEl.textContent = report.summary || '—';

  document.getElementById('report-modal').classList.remove('hidden');
}

function animateScoreRing(score) {
  const circle = document.getElementById('score-circle');
  if (!circle) return;
  const r = 54, circ = 2 * Math.PI * r;
  circle.style.strokeDasharray  = circ;
  circle.style.strokeDashoffset = circ - (score / 100) * circ;
}

const closeReportBtn = document.getElementById('btn-close-report');
if (closeReportBtn) {
  closeReportBtn.addEventListener('click', () => {
    document.getElementById('report-modal').classList.add('hidden');
    window.location.href = `/gd/report/${SESSION_ID}/`;
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setStatus(text, dotClass) {
  const isVietnam = languageSelect?.value === "vietnam";
  const translations = {
    'Connected — press Start to begin': 'Đã kết nối — nhấn Bắt đầu để khởi hành',
    'Disconnected': 'Đã ngắt kết nối',
    'Connection error': 'Lỗi kết nối',
    'Discussion in progress…': 'Cuộc thảo luận đang diễn ra…',
    'You are speaking…': 'Bạn đang nói…',
    'Analysing your performance…': 'Đang phân tích kết quả của bạn…',
    'Session ended': 'Phiên đã kết thúc',
    'Ending session…': 'Đang kết thúc phiên…'
  };

  if (statusText) {
    if (isVietnam && translations[text]) {
        statusText.textContent = `${translations[text]} (${text})`;
    } else {
        statusText.textContent = text;
    }
  }
  if (statusDot)  statusDot.className    = `status-dot ${dotClass}`;
}
function scrollBottom() { if (chatFeed) chatFeed.scrollTop = chatFeed.scrollHeight; }
function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Small helper styles
const _s = document.createElement('style');
_s.textContent = `.typing-avatar{width:36px!important;height:36px!important;font-size:1rem!important}`;
document.head.appendChild(_s);

// ── Init ──────────────────────────────────────────────────────────────────────
connectWS();
if (window.LinguaVoice) {
  window.LinguaVoice.restoreLanguagePreference('languageSelect', updateUILanguage);
} else {
  document.addEventListener('DOMContentLoaded', updateUILanguage);
}

(function () {
  const lv = window.LinguaVoice;
  const config = lv.readConfig("listening-config");

  lv.setActiveNav(config.lessonsPath || window.location.pathname);
  lv.initIssueTooltips();

  const languageSelect = document.getElementById("languageSelect");

  const stories = {
    beginner: [
      {
        title: "The Missed Bus Morning",
        titleVN: "Buổi sáng lỡ chuyến xe buýt",
        titleRU: "Утро с опозданием на автобус",
        text: "Riya woke up late because her alarm did not ring. She rushed to get ready for school and ran to the bus stop. The bus had already left, so she called her father for help. He dropped her at school just before class started. Riya promised to check her alarm every night after that.",
      },
      {
        title: "A Rainy School Day",
        titleVN: "Một ngày đi học trời mưa",
        titleRU: "Дождливый учебный день",
        text: "Heavy rain started while Arjun was walking to school. He opened his umbrella and shared it with his friend. Their shoes were wet, but they still reached class on time. The teacher asked everyone to dry their bags and sit quietly. During lunch, they watched the rain and talked about their favorite weather.",
      },
      {
        title: "The Lost Key",
        titleVN: "Chiếc chìa khóa bị mất",
        titleRU: "Потерянный ключ",
        text: "Mother could not find her house key anywhere. She looked in her bag and under the sofa. Finally, little Rahul pointed at the table near the door. The key was hiding under a magazine all along. They laughed and quickly left for the market before it closed.",
      },
      {
        title: "A New Pet",
        titleVN: "Một con thú cưng mới",
        titleRU: "Новый питомец",
        text: "Samir brought home a small brown puppy yesterday. The puppy was very playful and ran around the living room. It chased a red ball and fell asleep under a chair. Samir decided to name the puppy Bruno. They are already the best of friends.",
      },
      {
        title: "Painting The Fence",
        titleVN: "Sơn hàng rào",
        titleRU: "Покраска забора",
        text: "My grandfather needed help painting his old wooden fence. My sister and I wore our old clothes and grabbed some brushes. We painted the whole fence bright white. It took us three hours to finish the job. Grandfather thanked us by baking our favorite chocolate cookies.",
      },
      {
        title: "A Day at the Park",
        titleVN: "Một ngày ở công viên",
        titleRU: "День в парке",
        text: "The sun was shining brightly, so we went to the park. Children were playing on the swings and flying colorful kites. We spread a blanket on the grass and ate some sandwiches. Later, we fed bread pieces to the ducks in the pond. It was a very relaxing and happy afternoon.",
      }
    ],
    intermediate: [
      {
        title: "The Team Project Delay",
        titleVN: "Dự án nhóm bị trì hoãn",
        titleRU: "Задержка группового проекта",
        text: "Our college team was building a presentation for a technical event. Two members fell sick, so tasks were delayed for several days. We reorganized responsibilities and held short check-ins every evening. I focused on data analysis while my friend handled slide design. We submitted the project on time and received positive feedback from the judges.",
      },
      {
        title: "A Helpful Neighbor",
        titleVN: "Người hàng xóm tốt bụng",
        titleRU: "Отзывчивый сосед",
        text: "Last month, our neighborhood faced a sudden power cut during a storm. An elderly couple nearby needed support because their phone battery was low. My neighbor shared a backup light and helped them contact their family. We all stayed together until electricity returned. That night reminded me how important community support can be.",
      },
      {
        title: "The Surprise Birthday Party",
        titleVN: "Bữa tiệc sinh nhật bất ngờ",
        titleRU: "Сюрприз на день рождения",
        text: "We planned a secret birthday party for my best friend Sarah. I invited all her close friends and ordered a large chocolate cake. We hid in her darkened living room until she opened the front door. Everyone yelled surprise when she walked in, completely shocking her. The evening was filled with laughter, music, and wonderful memories.",
      },
      {
        title: "Learning to Swim",
        titleVN: "Học bơi",
        titleRU: "Учимся плавать",
        text: "I was always afraid of deep water until I joined swimming classes. My instructor was very patient and taught me breathing techniques first. For the first two weeks, I only practiced floating near the shallow edge. Gradually, I gained confidence and learned different swimming strokes. Now, swimming is my favorite weekend exercise.",
      },
      {
        title: "The Forgotten Homework",
        titleVN: "Bài tập về nhà bị quên",
        titleRU: "Забытое домашнее задание",
        text: "I organized my backpack carefully but entirely forgot my math assignment on my desk. When the teacher asked us to submit our work, I panicked completely. I honestly explained the situation and promised to bring it the next morning. Fortunately, she appreciated my honesty and gave me an extension. I learned to double-check my bag every single night.",
      },
      {
        title: "A Visit to the Museum",
        titleVN: "Chuyến thăm bảo tàng",
        titleRU: "Посещение музея",
        text: "Our history teacher organized a fascinating trip to the national museum. We observed ancient artifacts and learned about ancient civilizations from an expert guide. My favorite section displayed historical armors securely kept behind thick glass cases. We took many notes for our upcoming school project. The interactive exhibits made learning history incredibly enjoyable and memorable.",
      }
    ],
  };

  const storyLevel = document.getElementById("storyLevel");
  const speedSelect = document.getElementById("speedSelect");
  const storyTitle = document.getElementById("storyTitle");
  const storyMeta = document.getElementById("labelStoryMeta");
  const statusText = document.getElementById("statusText");
  const pauseCount = document.getElementById("pauseCount");
  const progressFill = document.getElementById("progressFill");
  const answerBox = document.getElementById("answerBox");
  const reviewCard = document.getElementById("reviewCard");
  const feedbackText = document.getElementById("feedbackText");
  const reviewText = document.getElementById("reviewText");
  const analysisCard = document.getElementById("analysisCard");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const improvedText = document.getElementById("improvedText");
  const quickTipText = document.getElementById("quickTipText");
  const lessonScore = document.getElementById("lessonScore");
  const matchPercentText = document.getElementById("matchPercentText");
  const playBtn = document.getElementById("playBtn");
  const pauseBtn = document.getElementById("pauseBtn");
  const pauseAlert = document.getElementById("pauseAlert");
  const analyzeEndpoint = config.analyzeEndpoint || "";
  const attemptToken = config.attemptToken || "";
  let attemptEvaluated = false;
  const pauseLimitMessage = "You have exceeded the maximum pause count.";
  const DEFAULT_ANALYZE_LABEL = "Submit for Analysis";

  // NOTE: this updateUILanguage()/highlightBilingual() pair is shadowed by
  // the second declaration further below — JS function declarations in the
  // same scope silently replace earlier ones, so only the later pair ever
  // actually runs. Left as-is (not consolidated) to avoid touching unrelated
  // code; Russian is added here too for consistency in case that changes.
  function highlightBilingual(vn, en, ru) {
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    if (isVietnam) return `<span class="text-slate-800 font-bold">${vn}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
    if (isRussian && ru) return `<span class="text-slate-800 font-bold">${ru}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
    return en;
  }

  function updateUILanguage() {
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const level = storyLevel?.value || "beginner";

    // 1. Story Header Translation
    if (currentStory) {
      if (isVietnam) {
        if (storyTitle) {
          const vnTitle = currentStory.titleVN || "Bản dịch đang được cập nhật...";
          storyTitle.innerHTML = `<span class="text-slate-900 font-bold">${vnTitle}</span> <span class="text-slate-400 font-normal text-2xl">(${currentStory.title})</span>`;
        }
        if (storyMeta) {
          const levelVN = level === "beginner" ? "Sơ cấp" : "Trung cấp";
          storyMeta.innerHTML = `<span class="font-bold text-slate-600">${currentDuration} giây | ${levelVN} | Tốc độ ${speedSelect?.value || 1.0}x</span> <span class="text-slate-400 text-sm font-normal">(${currentDuration} sec | ${level.charAt(0).toUpperCase() + level.slice(1)} | ${speedSelect?.value || 1.0}x speed)</span>`;
        }
      } else if (isRussian) {
        if (storyTitle) {
          const ruTitle = currentStory.titleRU || "Перевод обновляется...";
          storyTitle.innerHTML = `<span class="text-slate-900 font-bold">${ruTitle}</span> <span class="text-slate-400 font-normal text-2xl">(${currentStory.title})</span>`;
        }
        if (storyMeta) {
          const levelRU = level === "beginner" ? "Начальный" : "Средний";
          storyMeta.innerHTML = `<span class="font-bold text-slate-600">${currentDuration} сек | ${levelRU} | Скорость ${speedSelect?.value || 1.0}x</span> <span class="text-slate-400 text-sm font-normal">(${currentDuration} sec | ${level.charAt(0).toUpperCase() + level.slice(1)} | ${speedSelect?.value || 1.0}x speed)</span>`;
        }
      } else {
        if (storyTitle) storyTitle.textContent = currentStory.title;
        if (storyMeta) storyMeta.textContent = `${currentDuration} sec | ${level.charAt(0).toUpperCase() + level.slice(1)} | ${speedSelect?.value || 1.0}x speed`;
      }
    }

    // 2. Headings & Labels Translation
    const uiTranslations = {
      "labelModuleHeader": { en: "Module 01 • Listen & Learn", vn: "Học phần 01 • Nghe & Học", ru: "Модуль 01 • Слушай и Учись" },
      "labelNewStory": { en: "New", vn: "Mới", ru: "Новая" },
      "headingUnderstand": { en: "What Did You Understand?", vn: "Bạn Đã Hiểu Gì?", ru: "Что Вы Поняли?" },
      "headingMistakes": { en: "Mistakes Review", vn: "Đánh Giá Lỗi Sai", ru: "Обзор Ошибок" },
      "headingEvaluation": { en: "Evaluation", vn: "Đánh Giá Kết Quả", ru: "Оценка" },
      "labelScore": { en: "Total Score", vn: "Tổng Điểm", ru: "Общий Балл" },
      "labelImproved": { en: "Improved Version", vn: "Bản Cải Thiện", ru: "Улучшенная Версия" },
      "labelQuickTip": { en: "Quick Tip", vn: "Mẹo Nhanh", ru: "Быстрый Совет" },
      "labelFeedback": { en: "Overall Feedback", vn: "Phản Hồi Chung", ru: "Общий Отзыв" },
      "labelTryAgain": { en: "Try Again", vn: "Thử Lại", ru: "Попробовать Снова" }
    };

    Object.entries(uiTranslations).forEach(([id, langData]) => {
      const el = document.getElementById(id);
      if (el) {
        el.innerHTML = highlightBilingual(langData.vn, langData.en, langData.ru);
      }
    });

    // Button and Placeholder translations
    if (isVietnam) {
      if (analyzeBtn && !analyzeBtn.disabled) analyzeBtn.innerHTML = "Gửi để Phân tích (Submit for Analysis)";
      if (answerBox) answerBox.placeholder = "Viết lại câu chuyện theo ngôn ngữ của bạn tại đây... (Write the story in your own words here...)";
    } else if (isRussian) {
      if (analyzeBtn && !analyzeBtn.disabled) analyzeBtn.innerHTML = "Отправить на Анализ (Submit for Analysis)";
      if (answerBox) answerBox.placeholder = "Напишите историю своими словами здесь... (Write the story in your own words here...)";
    } else {
      if (analyzeBtn && !analyzeBtn.disabled) analyzeBtn.textContent = DEFAULT_ANALYZE_LABEL;
      if (answerBox) answerBox.placeholder = "Write the story in your own words here...";
    }

    // Status translations
    const currentStatus = statusText?.textContent || "";
    if (isVietnam) {
      const statusMap = {
        "Ready": "Sẵn sàng (Ready)",
        "Playing...": "Đang phát... (Playing...)",
        "Paused": "Đã tạm dừng (Paused)",
        "Finished": "Đã hoàn thành (Finished)",
        "Analyzing...": "Đang phân tích... (Analyzing...)"
      };
      if (statusMap[currentStatus]) statusText.textContent = statusMap[currentStatus];
    }
  }

  const synth = window.speechSynthesis;
  const canSpeak = !!(window.speechSynthesis && window.SpeechSynthesisUtterance);
  const remainingStoryIndexes = { beginner: [], intermediate: [] };
  const currentStoryIndexes = { beginner: -1, intermediate: -1 };

  let currentStory = stories.beginner[0];
  let currentDuration = 20;
  let utterance = null;
  let playing = false;
  let paused = false;
  let elapsed = 0;
  let elapsedCheckpoint = 0;
  let pauses = 0;
  let timer = null;
  let playStartedAt = 0;
  let sessionTerminated = false;

  function highlightBilingual(vn, en) {
    const isVietnam = languageSelect?.value === "vietnam";
    return isVietnam ? `<span class="text-slate-800 font-bold">${vn}</span> <span class="text-slate-400 font-normal">(${en})</span>` : en;
  }

  function updateUILanguage() {
    const isVietnam = languageSelect?.value === "vietnam";

    // 1. Story Title & Meta
    if (isVietnam) {
      storyTitle.innerHTML = `<span class="text-slate-900 font-bold">${currentStory.titleVN}</span> <span class="text-slate-400 font-normal text-2xl">(${currentStory.title})</span>`;
      const levelVN = storyLevel.value === "beginner" ? "Sơ cấp" : "Trung cấp";
      storyMeta.innerHTML = `<span class="text-slate-600 font-bold">Khoảng ${currentDuration} giây | ${levelVN} | Tốc độ ${speedSelect.value}x</span> <span class="text-slate-400 font-normal text-sm">(Approx ${currentDuration}s | ${toTitleCase(storyLevel.value)} | ${speedSelect.value}x speed)</span>`;
    } else {
      storyTitle.textContent = currentStory.title;
      storyMeta.textContent = `Approx ${currentDuration}s | ${toTitleCase(storyLevel.value)} | ${speedSelect.value}x speed`;
    }

    // 2. Labels Translation
    const uiTranslations = {
      "headingUnderstand": { en: "What Did You Understand?", vn: "Bạn đã Hiểu được gì?" },
      "headingMistakes": { en: "Mistakes Review", vn: "Đánh giá Lỗi sai" },
      "headingEvaluation": { en: "Evaluation", vn: "Đánh giá Kết quả" },
      "labelScore": { en: "Total Score", vn: "Tổng điểm" },
      "labelImproved": { en: "Improved Version", vn: "Bản Cải thiện" },
      "labelQuickTip": { en: "Quick Tip", vn: "Mẹo Nhanh" },
      "labelFeedback": { en: "Overall Feedback", vn: "Phản hồi Chung" }
    };

    Object.entries(uiTranslations).forEach(([id, langData]) => {
      const el = document.getElementById(id);
      if (el) {
        el.innerHTML = highlightBilingual(langData.vn, langData.en);
      }
    });

    // Body texts and buttons are kept in English as requested.
  }

  languageSelect?.addEventListener("change", updateUILanguage);

  function toTitleCase(text) {
    return String(text || "").charAt(0).toUpperCase() + String(text || "").slice(1);
  }

  function estimateDuration(text, speed) {
    const words = (String(text || "").match(/[A-Za-z']+/g) || []).length;
    const wordsPerSecond = Math.max(1.8, 2.6 * speed);
    return Math.max(8, Math.round(words / wordsPerSecond));
  }

  function clearPlaybackTimer() {
    clearInterval(timer);
    timer = null;
  }

  function refreshProgress() {
    const progressPercent = Math.min((elapsed / Math.max(currentDuration, 1)) * 100, 100);
    progressFill.style.width = `${progressPercent}%`;
  }

  function stopSpeechPlayback(resetCounters = false) {
    clearPlaybackTimer();
    if (canSpeak) synth.cancel();
    utterance = null;
    playing = false;
    paused = false;

    if (!resetCounters) return;

    elapsed = 0;
    elapsedCheckpoint = 0;
    pauses = 0;
    pauseCount.textContent = "0";
    refreshProgress();
    statusText.textContent = "Ready";
    playBtn.textContent = "Play Story";
  }

  function showPauseLimitMessage() {
    const isVietnam = languageSelect?.value === "vietnam";
    const msg = isVietnam ? "Bạn đã vượt quá số lần tạm dừng cho phép. (You have exceeded the maximum pause count.)" : pauseLimitMessage;
    if (pauseAlert) {
      pauseAlert.innerHTML = msg;
      pauseAlert.classList.remove("hidden");
    }
    statusText.textContent = "Terminated";
    reviewText.innerHTML = msg;
  }

  function startPlaybackTimer() {
    clearPlaybackTimer();
    timer = setInterval(() => {
      if (!playing) return;
      const runningSeconds = (Date.now() - playStartedAt) / 1000;
      elapsed = Math.min(currentDuration, elapsedCheckpoint + runningSeconds);
      refreshProgress();
    }, 180);
  }

  function resetAnalysisView() {
    const answerBox = document.getElementById("answerBox");
    if (answerBox) {
        answerBox.value = "";
        answerBox.disabled = false;
        answerBox.dispatchEvent(new Event("input"));
    }
    reviewCard?.classList.add("hidden");
    analysisCard?.classList.add("hidden");
    updateUILanguage();
    if (lessonScore) lessonScore.textContent = "0/25";
    if (matchPercentText) matchPercentText.textContent = "--% Match";
    pauseAlert?.classList.add("hidden");
  }

  function buildListeningFeedback(assessment, issues, fallbackFeedback) {
    const match = Math.round((assessment?.contentMatch || 0) * 100);
    const issueCount = Array.isArray(issues) ? issues.length : 0;
    const isVietnam = languageSelect?.value === "vietnam";

    let en = "";
    let vn = "";

    if (match >= 100) {
      en = "Excellent listening. Your response captures the story completely and stays accurate to the original audio.";
      vn = "Kỹ năng nghe xuất sắc. Câu trả lời của bạn nắm bắt hoàn toàn câu chuyện và bám sát âm thanh gốc.";
    } else if (match >= 90) {
      en = `Very strong listening. Your answer stays very close to the story, with only small gaps or language mistakes${issueCount ? ` across ${issueCount} highlighted spot${issueCount === 1 ? "" : "s"}` : ""}.`;
      vn = `Khả năng nghe rất tốt. Câu trả lời của bạn rất sát với câu chuyện, chỉ có một vài khoảng trống nhỏ hoặc lỗi ngôn ngữ${issueCount ? ` tại ${issueCount} điểm được đánh dấu` : ""}.`;
    } else if (match >= 80) {
      en = "Good listening. You understood most of the story and captured the main events, but a few details still need tightening.";
      vn = "Nghe tốt. Bạn đã hiểu hầu hết câu chuyện và nắm bắt được các sự kiện chính, nhưng một vài chi tiết vẫn cần được hoàn thiện thêm.";
    } else if (match >= 60) {
      en = "Decent listening. Your answer relates to the story, but some important details are missing or mixed up.";
      vn = "Nghe khá. Câu trả lời của bạn có liên quan đến câu chuyện, nhưng một số chi tiết quan trọng bị thiếu hoặc bị nhầm lẫn.";
    } else if (match >= 50) {
      en = "Partial understanding. You caught the general topic, but the summary needs more correct story details.";
      vn = "Hiểu được một phần. Bạn đã nắm được chủ đề chung, nhưng bản tóm tắt cần thêm các chi tiết chính xác của câu chuyện.";
    } else if (match >= 20) {
      en = "Limited match with the story. Focus on the main characters, the central event, and the final outcome.";
      vn = "Sự tương đồng với câu chuyện còn hạn chế. Hãy tập trung vào các nhân vật chính, sự kiện trung tâm và kết quả cuối cùng.";
    } else {
      en = fallbackFeedback || "Your response is not closely related to the story yet. Listen again and retell only the events from the audio.";
      vn = "Câu trả lời của bạn chưa liên quan chặt chẽ đến câu chuyện. Hãy nghe lại và chỉ kể lại các sự kiện từ âm thanh.";
    }

    return highlightBilingual(vn, en);
  }

  function buildListeningQuickTip(assessment, issues) {
    const topIssue = Array.isArray(issues) && issues.length ? issues[0] : null;
    const match = Math.round((assessment?.contentMatch || 0) * 100);
    const isVietnam = languageSelect?.value === "vietnam";

    let en = "";
    let vn = "";

    if (topIssue?.suggestion) {
      en = `Fix this first: ${topIssue.suggestion}`;
      vn = `Hãy sửa lỗi này trước: ${topIssue.suggestion}`;
    } else if (match >= 90) {
      en = "Strong match. Next, tighten grammar and punctuation so your summary sounds polished.";
      vn = "Sự tương đồng cao. Tiếp theo, hãy trau chuốt ngữ pháp và dấu câu để bản tóm tắt của bạn nghe mượt mà hơn.";
    } else if (match >= 60) {
      en = "Keep the same story order: who, what happened, what changed, and how it ended.";
      vn = "Hãy giữ đúng thứ tự câu chuyện: ai, điều gì đã xảy ra, điều gì đã thay đổi và kết thúc như thế nào.";
    } else {
      en = "Listen for the main person, the problem, and the ending before you start writing.";
      vn = "Hãy lắng nghe nhân vật chính, vấn đề và kết thúc trước khi bạn bắt đầu viết.";
    }

    return highlightBilingual(vn, en);
  }

  function refillStoryPool(level, excludeIndex = -1) {
    const list = stories[level] || [];
    remainingStoryIndexes[level] = list
      .map((_, index) => index)
      .filter((index) => index !== excludeIndex);
  }

  function getNextStoryIndex(level) {
    const list = stories[level] || [];
    if (!remainingStoryIndexes[level]?.length) {
      refillStoryPool(level, currentStoryIndexes[level]);
    }
    const pool = remainingStoryIndexes[level] || [];
    if (!pool.length) return Math.max(0, currentStoryIndexes[level]);
    const selectedIndex = Math.floor(Math.random() * pool.length);
    const [nextIndex] = pool.splice(selectedIndex, 1);
    return nextIndex;
  }

  function pickStory() {
    const level = storyLevel.value;
    const list = stories[level] || stories.beginner;
    const index = getNextStoryIndex(level);
    currentStoryIndexes[level] = index;

    currentStory = list[index];
    currentDuration = estimateDuration(currentStory.text, Number(speedSelect.value) || 1);
    stopSpeechPlayback(true);
    resetAnalysisView();
  }

  function playStory() {
    if (!canSpeak) {
      statusText.textContent = "Voice not supported";
      return;
    }

    if (paused) {
      synth.resume();
      paused = false;
      playing = true;
      playStartedAt = Date.now();
      statusText.textContent = "Playing";
      pauseBtn.textContent = "Pause";
      playBtn.textContent = "Playing";
      startPlaybackTimer();
      return;
    }

    if (playing) return;

    sessionTerminated = false;
    pauseAlert?.classList.add("hidden");
    stopSpeechPlayback(false);
    utterance = new SpeechSynthesisUtterance(currentStory.text);
    utterance.lang = "en-US";
    utterance.rate = Number(speedSelect.value) || 1;
    utterance.pitch = 1;

    utterance.onstart = () => {
      playing = true;
      paused = false;
      elapsed = 0;
      elapsedCheckpoint = 0;
      statusText.textContent = "Playing";
      playBtn.textContent = "Playing";
      pauseBtn.textContent = "Pause";
      playStartedAt = Date.now();
      startPlaybackTimer();
    };

    utterance.onend = () => {
      clearPlaybackTimer();
      playing = false;
      paused = false;
      elapsed = currentDuration;
      elapsedCheckpoint = currentDuration;
      refreshProgress();
      statusText.textContent = "Completed";
      playBtn.textContent = "Replay Story";
      pauseBtn.textContent = "Pause";
    };

    utterance.onerror = () => {
      clearPlaybackTimer();
      playing = false;
      paused = false;
      statusText.textContent = "Playback error";
      playBtn.textContent = "Play Story";
      pauseBtn.textContent = "Pause";
    };

    synth.speak(utterance);
  }

  function pauseStory() {
    if (!canSpeak) return;
    if (playing) {
      pauses += 1;
      pauseCount.textContent = String(pauses);
      if (pauses > 5) {
        stopSpeechPlayback(true);
        sessionTerminated = true;
        resetAnalysisView();
        showPauseLimitMessage();
        return;
      }
      synth.pause();
      playing = false;
      paused = true;
      elapsedCheckpoint = elapsed;
      clearPlaybackTimer();
      statusText.textContent = "Paused";
      pauseBtn.textContent = "Resume";
      playBtn.textContent = "Resume Story";
      return;
    }

    if (!paused) return;

    synth.resume();
    paused = false;
    playing = true;
    playStartedAt = Date.now();
    statusText.textContent = "Playing";
    pauseBtn.textContent = "Pause";
    playBtn.textContent = "Playing";
    startPlaybackTimer();
  }

  async function analyzeText() {
    const text = answerBox?.value?.trim() || "";
    const isVietnam = languageSelect?.value === "vietnam";
    if (attemptEvaluated) {
      // Belt-and-braces: the button/textarea are disabled once an attempt is
      // evaluated, but guard the function itself too in case it's ever
      // triggered another way (e.g. re-enabling the button via devtools).
      // The server independently rejects a reused attempt token regardless.
      return;
    }
    if (sessionTerminated) {
      analysisCard?.classList.remove("hidden");
      reviewCard?.classList.remove("hidden");
      const msg = isVietnam ? "Bạn đã vượt quá số lần tạm dừng cho phép. (You have exceeded the maximum pause count.)" : pauseLimitMessage;
      reviewText.innerHTML = msg;
      feedbackText.innerHTML = msg;
      return;
    }
    if (!lv.hasMeaningfulText(text)) {
      analysisCard?.classList.remove("hidden");
      reviewCard?.classList.remove("hidden");
      reviewText.innerHTML = isVietnam ? "Hãy viết bản tóm tắt bài nghe của bạn trước, sau đó nhấn Phân tích để xem các lỗi được đánh dấu. (Write your listening summary first, then click Analyze to see highlighted mistakes.)" : "Write your listening summary first, then click Analyze to see highlighted mistakes.";
      feedbackText.innerHTML = isVietnam ? "Hãy viết ít nhất vài câu rõ ràng, sau đó nhấn Phân tích. (Write at least a few clear sentences, then click Analyze.)" : "Write at least a few clear sentences, then click Analyze.";
      return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = isVietnam ? "Đang phân tích... (Analyzing...)" : "Analyzing...";

    const formData = new FormData();
    formData.append("module", "listening");
    formData.append("text", text);
    formData.append("reference_text", currentStory.text || "");
    formData.append("duration_seconds", String(Math.round(elapsed)));
    formData.append("pause_count", String(pauses));
    formData.append("attempt_token", attemptToken);
    formData.append("language", languageSelect?.value || "english");

    try {
      const response = await fetch(analyzeEndpoint, {
        method: "POST",
        headers: { "X-CSRFToken": lv.getCsrfToken() },
        body: formData
      });
      const raw = await response.json();

      if (!raw.success) throw new Error(raw.error || "Analysis failed.");

      const result = lv.unwrapApiData(raw);
      const analyzedText = result.text || text || "";
      const renderResult = lv.renderTextWithIssues(analyzedText, result.issues || []);
      if (reviewText) reviewText.innerHTML = renderResult.html;
      const issuesList = result.issues || [];
      const assessment = lv.computeListeningAssessment(
        text,
        currentStory.text || "",
        pauses || 0,
        renderResult.count
      );
      // The server derives its saved score directly from content-match
      // similarity (see compute_listening_score_25 in agents/utils.py), so
      // when it sends that match % back, use it here too — otherwise Total
      // Score would come from the server's calculation while Content Match
      // and the feedback/quick-tip wording keep coming from the client's
      // separate word-overlap heuristic, and the two can visibly disagree
      // (e.g. a 25/25 score next to an 88% match).
      if (typeof result.content_match_percent === "number") {
        assessment.matchPercent = result.content_match_percent;
        assessment.contentMatch = result.content_match_percent / 100;
      }
      feedbackText.innerHTML = buildListeningFeedback(assessment, issuesList, result.feedback || "Analysis complete.");
      if (improvedText) improvedText.innerHTML = lv.formatImprovedText(result.improved_passage, text);
      if (quickTipText) quickTipText.innerHTML = buildListeningQuickTip(assessment, issuesList) || result.quick_tip || "Focus on key details from the story.";
      // Prefer the server-graded, saved score (result.score_25) so the score
      // shown here right after analysis ("Present") is exactly the same
      // number that gets stored and later shown as "Previous Score" on this
      // exercise. Fall back to the local heuristic only when the backend
      // didn't return one (e.g. the user isn't authenticated, so nothing
      // was actually saved).
      const scoreValue =
        typeof raw?.score_25 === "number"
          ? raw.score_25
          : typeof result?.score_25 === "number"
            ? result.score_25
            : assessment.score;

      if (lessonScore) lessonScore.textContent = `${lv.formatScoreValue(scoreValue)}/25`;
      if (matchPercentText) matchPercentText.textContent = `${assessment.matchPercent}% Match`;
      lv.saveModuleScore("Listening", { score: scoreValue });

      const rightScoreCard = document.getElementById("rightScoreCard");
      const rightScoreValue = document.getElementById("rightScoreValue");
      const rightScoreDate = document.getElementById("rightScoreDate");
      if (rightScoreCard) rightScoreCard.style.display = "block";
      if (rightScoreValue) rightScoreValue.textContent = lv.formatScoreValue(scoreValue);
      if (rightScoreDate) {
        const d = new Date();
        rightScoreDate.textContent = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      }

      reviewCard?.classList.remove("hidden");
      analysisCard?.classList.remove("hidden");
      updateUILanguage();
      setTimeout(() => reviewCard?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);

      // This attempt has now been evaluated and saved server-side. Lock the
      // form so it can't be re-submitted with a different (or copied)
      // answer without an actual restart/refresh, which mints a new
      // attempt_token. Return here instead of falling through to the
      // re-enable below, which only runs on the error path.
      attemptEvaluated = true;
      if (answerBox) answerBox.disabled = true;
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = isVietnam ? "Đã nộp bài (Already Submitted)" : "Already Submitted";
      return;
    } catch (error) {
      reviewCard?.classList.remove("hidden");
      analysisCard?.classList.remove("hidden");
      reviewText.textContent = text;
      if (matchPercentText) matchPercentText.textContent = "Error";
      if (lessonScore) lessonScore.textContent = "0/25";
      setTimeout(() => reviewCard?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
      feedbackText.textContent = `Error: ${error.message || "Could not analyze your response."}`;
      if (improvedText) improvedText.textContent = "Analysis failed, cannot provide improved version.";
      if (quickTipText) quickTipText.textContent = "Please try again later.";
    }
    // Only reached on error (the success path returns early above) — let
    // the learner retry after a genuine failure (network error, etc.).
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = isVietnam ? "Gửi để Phân tích (Submit for Analysis)" : DEFAULT_ANALYZE_LABEL;
  }

  document.getElementById("playBtn")?.addEventListener("click", playStory);
  document.getElementById("pauseBtn")?.addEventListener("click", pauseStory);
  document.getElementById("newStoryBtn")?.addEventListener("click", pickStory);
  storyLevel?.addEventListener("change", pickStory);
  speedSelect?.addEventListener("change", () => {
    currentDuration = estimateDuration(currentStory.text, Number(speedSelect.value) || 1);
    stopSpeechPlayback(true);
    updateUILanguage();
  });
  analyzeBtn?.addEventListener("click", analyzeText);
  lv.restoreLanguagePreference("languageSelect", updateUILanguage);

  pickStory();
})();

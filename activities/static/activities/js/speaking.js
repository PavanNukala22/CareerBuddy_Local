(function () {
  const lv = window.LinguaVoice;
  const config = lv.readConfig("speaking-config");

  lv.setActiveNav(config.lessonsPath || window.location.pathname);
  lv.initIssueTooltips();

  const languageSelect = document.getElementById("languageSelect");

  const topicsVN = {
    "Describe your best friend in simple words.": "Mô tả người bạn thân nhất của bạn bằng những từ ngữ đơn giản.",
    "Talk about your favourite place at home.": "Nói về nơi yêu thích của bạn ở nhà.",
    "What is your favourite food and why?": "Món ăn yêu thích của bạn là gì và tại sao?",
    "Describe your perfect day from morning to night.": "Mô tả ngày hoàn hảo của bạn từ sáng đến tối.",
    "What subject do you enjoy the most at school?": "Bạn thích môn học nào nhất ở trường?",
    "Describe your favourite animal and why you like it.": "Mô tả con vật yêu thích của bạn và tại sao bạn thích nó.",
    "Talk about a game or hobby you love.": "Nói về một trò chơi hoặc sở thích mà bạn yêu thích.",
    "Who is your hero and what makes them special?": "Ai là người hùng của bạn và điều gì làm họ trở nên đặc biệt?",
    "If you could travel anywhere, where would you go?": "Nếu bạn có thể đi du lịch bất cứ đâu, bạn sẽ đi đâu?",
    "Describe a time you helped someone or someone helped you.": "Mô tả một lần bạn đã giúp đỡ ai đó hoặc ai đó đã giúp đỡ bạn.",
    "Talk about your favourite movie or television show.": "Nói về bộ phim hoặc chương trình truyền hình yêu thích của bạn.",
    "What is the best gift you have ever received?": "Món quà tuyệt vời nhất mà bạn từng nhận được là gì?",
    "Describe your dream job and why you want it.": "Mô tả công việc mơ ước của bạn và tại sao bạn muốn nó.",
    "Talk about a memorable family holiday.": "Nói về một kỳ nghỉ gia đình đáng nhớ.",
    "If you had a million dollars, what would you do first?": "Nếu bạn có một triệu đô la, bạn sẽ làm gì đầu tiên?",
    "Describe a book that you really enjoyed reading.": "Mô tả một cuốn sách mà bạn thực sự thích đọc.",
    "What do you usually do on the weekends?": "Bạn thường làm gì vào cuối tuần?",
    "Talk about an interesting dream you had recently.": "Nói về một giấc mơ thú vị mà bạn có gần đây.",
    "What are three things you cannot live without?": "Ba thứ bạn không thể sống thiếu là gì?",
    "Describe a historical event you'd like to witness.": "Mô tả một sự kiện lịch sử mà bạn muốn chứng kiến.",
    "Describe your best experience at the workplace.": "Mô tả trải nghiệm tốt nhất của bạn tại nơi làm việc."
  };

  const topicsAR = {
    "Describe your best friend in simple words.": "صف أفضل صديق لك بكلمات بسيطة.",
    "Talk about your favourite place at home.": "تحدث عن مكانك المفضل في المنزل.",
    "What is your favourite food and why?": "ما هو طعامك المفضل ولماذا؟",
    "Describe your perfect day from morning to night.": "صف يومك المثالي من الصباح إلى الليل.",
    "What subject do you enjoy the most at school?": "ما هي المادة التي تستمتع بها أكثر في المدرسة؟",
    "Describe your favourite animal and why you like it.": "صف حيوانك المفضل ولماذا تحبه.",
    "Talk about a game or hobby you love.": "تحدث عن لعبة أو هواية تحبها.",
    "Who is your hero and what makes them special?": "من هو بطلك وما الذي يجعله مميزًا؟",
    "If you could travel anywhere, where would you go?": "إذا كان بإمكانك السفر إلى أي مكان، فأين ستذهب؟",
    "Describe a time you helped someone or someone helped you.": "صف وقتًا ساعدت فيه شخصًا ما أو ساعدك فيه شخص ما.",
    "Talk about your favourite movie or television show.": "تحدث عن فيلمك أو برنامجك التلفزيوني المفضل.",
    "What is the best gift you have ever received?": "ما هي أفضل هدية تلقيتها على الإطلاق؟",
    "Describe your dream job and why you want it.": "صف وظيفة أحلامك ولماذا تريدها.",
    "Talk about a memorable family holiday.": "تحدث عن عطلة عائلية لا تُنسى.",
    "If you had a million dollars, what would you do first?": "إذا كان لديك مليون دولار، فماذا ستفعل أولاً؟",
    "Describe a book that you really enjoyed reading.": "صف كتابًا استمتعت حقًا بقراءته.",
    "What do you usually do on the weekends?": "ماذا تفعل عادة في عطلات نهاية الأسبوع؟",
    "Talk about an interesting dream you had recently.": "تحدث عن حلم مثير للاهتمام حلمت به مؤخرًا.",
    "What are three things you cannot live without?": "ما هي الأشياء الثلاثة التي لا يمكنك العيش بدونها؟",
    "Describe a historical event you'd like to witness.": "صف حدثًا تاريخيًا ترغب في مشاهدته.",
    "Describe your best experience at the workplace.": "صف أفضل تجربة لك في مكان العمل."
  };

  const topicsRU = {
    "Describe your best friend in simple words.": "Опишите вашего лучшего друга простыми словами.",
    "Talk about your favourite place at home.": "Расскажите о вашем любимом месте дома.",
    "What is your favourite food and why?": "Какая ваша любимая еда и почему?",
    "Describe your perfect day from morning to night.": "Опишите ваш идеальный день с утра до вечера.",
    "What subject do you enjoy the most at school?": "Какой предмет вам больше всего нравится в школе?",
    "Describe your favourite animal and why you like it.": "Опишите ваше любимое животное и почему оно вам нравится.",
    "Talk about a game or hobby you love.": "Расскажите об игре или хобби, которое вы любите.",
    "Who is your hero and what makes them special?": "Кто ваш герой и что делает его особенным?",
    "If you could travel anywhere, where would you go?": "Если бы вы могли поехать куда угодно, куда бы вы отправились?",
    "Describe a time you helped someone or someone helped you.": "Опишите случай, когда вы помогли кому-то или кто-то помог вам.",
    "Talk about your favourite movie or television show.": "Расскажите о вашем любимом фильме или телешоу.",
    "What is the best gift you have ever received?": "Какой лучший подарок вы когда-либо получали?",
    "Describe your dream job and why you want it.": "Опишите работу вашей мечты и почему вы её хотите.",
    "Talk about a memorable family holiday.": "Расскажите о запоминающемся семейном празднике.",
    "If you had a million dollars, what would you do first?": "Если бы у вас был миллион долларов, что бы вы сделали в первую очередь?",
    "Describe a book that you really enjoyed reading.": "Опишите книгу, которую вам действительно понравилось читать.",
    "What do you usually do on the weekends?": "Что вы обычно делаете по выходным?",
    "Talk about an interesting dream you had recently.": "Расскажите об интересном сне, который вам недавно приснился.",
    "What are three things you cannot live without?": "Какие три вещи вы не можете представить свою жизнь без?",
    "Describe a historical event you'd like to witness.": "Опишите историческое событие, свидетелем которого вы хотели бы стать.",
    "Describe your best experience at the workplace.": "Опишите ваш лучший опыт на рабочем месте."
  };

  const topics = [
    "Describe your best friend in simple words.",
    "Talk about your favourite place at home.",
    "What is your favourite food and why?",
    "Describe your perfect day from morning to night.",
    "What subject do you enjoy the most at school?",
    "Describe your favourite animal and why you like it.",
    "Talk about a game or hobby you love.",
    "Who is your hero and what makes them special?",
    "If you could travel anywhere, where would you go?",
    "Describe a time you helped someone or someone helped you.",
    "Talk about your favourite movie or television show.",
    "What is the best gift you have ever received?",
    "Describe your dream job and why you want it.",
    "Talk about a memorable family holiday.",
    "If you had a million dollars, what would you do first?",
    "Describe a book that you really enjoyed reading.",
    "What do you usually do on the weekends?",
    "Talk about an interesting dream you had recently.",
    "What are three things you cannot live without?",
    "Describe a historical event you'd like to witness."
  ];

  let remainingTopics = [];

  const topicText = document.getElementById("topicText");
  const newTopicBtn = document.getElementById("newTopicBtn");
  const micBtn = document.getElementById("micBtn");
  const pauseResumeBtn = document.getElementById("pauseResumeBtn");
  const micLabel = document.getElementById("micLabel");
  const statusTxt = document.getElementById("statusTxt");
  const timeTxt = document.getElementById("timeTxt");
  const pauseTxt = document.getElementById("pauseTxt");
  const wordCountTxt = document.getElementById("wordCountTxt");
  const ring1 = document.getElementById("ring1");
  const ring2 = document.getElementById("ring2");
  const micWrap = document.getElementById("micWrap");
  const micIcon = document.getElementById("micIcon");
  const waveRow = document.getElementById("waveRow");
  const waveBars = document.querySelectorAll(".wbar");
  const recordResult = document.getElementById("recordResult");
  const recordedAudio = document.getElementById("recordedAudio");
  const transcriptText = document.getElementById("transcriptText");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const analyzeNote = document.getElementById("analyzeNote");
  const feedbackCard = document.getElementById("feedbackCard");
  const feedbackText = document.getElementById("feedbackText");
  const improvedText = document.getElementById("improvedText");
  const quickTipText = document.getElementById("quickTipText");
  const lessonScore = document.getElementById("lessonScore");
  const pauseAlert = document.getElementById("pauseAlert");
  const tryAgainBtn = document.getElementById("tryAgainBtn");
  const analyzeEndpoint = config.analyzeEndpoint || "";
  const defaultQuickTip = "Speak slowly and clearly. Pause for breath, then continue with short sentences.";
  const defaultImprovedText = "Your improved passage will appear here after analysis.";
  const pauseLimitMessage = "You have exceeded the maximum pause count.";

  let mediaStream = null;
  let mediaRecorder = null;
  let recordedChunks = [];
  let recording = false;
  let paused = false;
  let pauseCount = 0;
  let elapsed = 0;
  let timer = null;
  const MAX_RECORD_SECONDS = config.isElevatorPitchTimed ? 60 : 90;
  let audioUrl = null;
  let latestRecordingBlob = null;

  let recognition = null;
  let recognitionAvailable = false;
  let transcriptFinal = "";
  let transcriptInterim = "";
  const recognitionLanguage = "en-US";

  const MIN_MEANINGFUL_WORDS = 25;

  function updateUILanguage() {
    const sel = document.getElementById("languageSelect");
    const isVietnam = sel?.value === "vietnam";
    const isArabic = sel?.value === "arabic";
    const isRussian = sel?.value === "russian";

    // Translate only the Learning Tips header
    const quickTipHeader = document.getElementById("labelQuickTip");
    if (quickTipHeader) {
      if (isVietnam) {
        quickTipHeader.innerHTML = `<span class="text-slate-900">Mẹo Nhanh</span> <span class="text-slate-400">(Quick Tips)</span>`;
        quickTipHeader.style.direction = '';
      } else if (isArabic) {
        quickTipHeader.innerHTML = `<span class="text-slate-900">نصائح سريعة</span> <span class="text-slate-400">(Quick Tips)</span>`;
        quickTipHeader.style.direction = 'rtl';
      } else if (isRussian) {
        quickTipHeader.innerHTML = `<span class="text-slate-900">Быстрые советы</span> <span class="text-slate-400">(Quick Tips)</span>`;
        quickTipHeader.style.direction = '';
      } else {
        quickTipHeader.innerHTML = "Quick Tips";
        quickTipHeader.style.direction = '';
      }
    }

    // Keep bullet points translation (to match exact formatting in screenshot)
    const tips = {
      "tip1": { en: "Speak slowly and clearly.", vn: "Nói chậm và rõ ràng.", ar: "تحدث ببطء وبوضوح.", ru: "Говорите медленно и чётко." },
      "tip2": { en: "Pause for breath, then continue.", vn: "Tạm dừng để thở, sau đó tiếp tục.", ar: "توقف لالتقاط الأنفاس، ثم استمر.", ru: "Сделайте паузу, чтобы вдохнуть, затем продолжайте." },
      "tip3": { en: "Use short, complete sentences.", vn: "Sử dụng các câu ngắn, đầy đủ.", ar: "استخدم جملا قصيرة وكاملة.", ru: "Используйте короткие, законченные предложения." }
    };
    Object.entries(tips).forEach(([id, langData]) => {
      const el = document.getElementById(id);
      if (el) {
        if (isVietnam) {
          el.innerHTML = `<span class="text-sky-600 font-bold">•</span> <span class="text-slate-800 font-bold">${langData.vn}</span> <span class="text-slate-400 font-normal">(${langData.en})</span>`;
          el.style.direction = '';
        } else if (isArabic) {
          el.innerHTML = `<span class="text-sky-600 font-bold">•</span> <span class="text-slate-800 font-bold">${langData.ar}</span> <span class="text-slate-400 font-normal">(${langData.en})</span>`;
          el.style.direction = 'rtl';
        } else if (isRussian) {
          el.innerHTML = `<span class="text-sky-600 font-bold">•</span> <span class="text-slate-800 font-bold">${langData.ru}</span> <span class="text-slate-400 font-normal">(${langData.en})</span>`;
          el.style.direction = '';
        } else {
          el.innerHTML = `<span class="text-sky-600 font-bold">•</span> ${langData.en}`;
          el.style.direction = '';
        }
      }
    });

    if (topicText) {
      const currentTopic = topicText.getAttribute("data-topic-en") || topicText.textContent || "";
      const cleanTopic = currentTopic.trim();
      if (isVietnam) {
        const vnTranslation = topicsVN[cleanTopic] || "Bản dịch đang được cập nhật...";
        topicText.innerHTML = `<span class="text-slate-800 font-bold">${vnTranslation}</span> <span class="text-slate-400 font-normal">(${cleanTopic})</span>`;
        topicText.style.direction = '';
      } else if (isArabic) {
        const arTranslation = topicsAR[cleanTopic] || "جاري تحديث الترجمة...";
        topicText.innerHTML = `<span class="text-slate-800 font-bold">${arTranslation}</span> <span class="text-slate-400 font-normal">(${cleanTopic})</span>`;
        topicText.style.direction = 'rtl';
      } else if (isRussian) {
        const ruTranslation = topicsRU[cleanTopic] || "Перевод обновляется...";
        topicText.innerHTML = `<span class="text-slate-800 font-bold">${ruTranslation}</span> <span class="text-slate-400 font-normal">(${cleanTopic})</span>`;
        topicText.style.direction = '';
      } else {
        topicText.textContent = cleanTopic;
        topicText.style.direction = '';
      }
    }

    const otherLabels = {
      "labelModuleHeader": { en: "Module 02 • Fluency Practice", vn: "Mô-đun 02 • Thực hành lưu loát", ar: "الوحدة 02 • ممارسة الطلاقة", ru: "Модуль 02 • Практика беглости речи" },
      "labelYourTopic": { en: "Your Topic", vn: "Chủ đề của bạn", ar: "موضوعك", ru: "Ваша тема" },
      "labelNewTopic": { en: "New Topic", vn: "Chủ đề mới", ar: "موضوع جديد", ru: "Новая тема" },
      "headingMistakes": { en: "Mistakes Review", vn: "Đánh giá lỗi", ar: "مراجعة الأخطاء", ru: "Обзор ошибок" },
      "headingEvaluation": { en: "Evaluation", vn: "Đánh giá", ar: "التقييم", ru: "Оценка" },
      "labelScore": { en: "Evaluation Score", vn: "Điểm đánh giá", ar: "درجة التقييم", ru: "Оценочный балл" },
      "labelImproved": { en: "Improved Version", vn: "Phiên bản đã cải thiện", ar: "النسخة المحسنة", ru: "Улучшенная версия" },
      "labelFeedback": { en: "Overall Feedback", vn: "Phản hồi tổng thể", ar: "التعليقات العامة", ru: "Общий отзыв" },
      "labelPauses": { en: "Pauses:", vn: "Tạm dừng:", ar: "توقفات:", ru: "Паузы:" }
    };
    Object.entries(otherLabels).forEach(([id, data]) => {
      const el = document.getElementById(id);
      if (el) {
        if (isVietnam) el.innerHTML = `<span class="text-slate-800">${data.vn}</span> <span class="text-slate-400">(${data.en})</span>`;
        else if (isArabic) el.innerHTML = `<span class="text-slate-800">${data.ar}</span> <span class="text-slate-400">(${data.en})</span>`;
        else if (isRussian) el.innerHTML = `<span class="text-slate-800">${data.ru}</span> <span class="text-slate-400">(${data.en})</span>`;
        else el.textContent = data.en;
      }
    });

    if (micLabel) {
      let msgEN = paused ? "Paused recording. Tap Resume to continue." : (recording ? "Recording in progress. Tap Stop to finish." : "Click to start recording");
      let msgVN = paused ? "Đã tạm dừng. Nhấn Tiếp tục để tiếp tục." : (recording ? "Đang ghi âm. Nhấn Dừng để hoàn thành." : "Nhấp để bắt đầu ghi âm");
      let msgAR = paused ? "تم الإيقاف مؤقتا. انقر فوق استئناف للمتابعة." : (recording ? "جاري التسجيل. انقر فوق إيقاف للإنهاء." : "انقر لبدء التسجيل");
      let msgRU = paused ? "Запись приостановлена. Нажмите «Продолжить», чтобы возобновить." : (recording ? "Идёт запись. Нажмите «Стоп», чтобы завершить." : "Нажмите, чтобы начать запись");

      if (isVietnam) micLabel.innerHTML = `<span class="text-slate-800 font-bold">${msgVN}</span> <span class="text-slate-400 font-normal">(${msgEN})</span>`;
      else if (isArabic) micLabel.innerHTML = `<span class="text-slate-800 font-bold">${msgAR}</span> <span class="text-slate-400 font-normal">(${msgEN})</span>`;
      else if (isRussian) micLabel.innerHTML = `<span class="text-slate-800 font-bold">${msgRU}</span> <span class="text-slate-400 font-normal">(${msgEN})</span>`;
      else micLabel.textContent = msgEN;
    }

    if (analyzeBtn) {
      if (isVietnam) analyzeBtn.innerHTML = `<i class="fas fa-brain me-2"></i><span class="text-slate-800">Phân tích</span> <span class="text-slate-400">(Analyze)</span>`;
      else if (isArabic) analyzeBtn.innerHTML = `<i class="fas fa-brain me-2"></i><span class="text-slate-800">تحليل</span> <span class="text-slate-400">(Analyze)</span>`;
      else if (isRussian) analyzeBtn.innerHTML = `<i class="fas fa-brain me-2"></i><span class="text-slate-800">Анализ</span> <span class="text-slate-400">(Analyze)</span>`;
      else analyzeBtn.innerHTML = `<i class="fas fa-brain me-2"></i>Analyze`;
    }

    if (statusTxt) {
      if (statusTxt.textContent === "Idle" || statusTxt.textContent === "Nhàn rỗi" || statusTxt.textContent === "خامل" || statusTxt.textContent === "Ожидание") {
        statusTxt.textContent = isVietnam ? "Nhàn rỗi" : isArabic ? "خامل" : isRussian ? "Ожидание" : "Idle";
      }
    }
  }

  function updateWordCount(text = "") {
    const count = lv.countSpeakingWords(text);
    if (wordCountTxt) {
      const isVietnam = document.getElementById("languageSelect")?.value === "vietnam";
      const isArabic = document.getElementById("languageSelect")?.value === "arabic";
      const isRussian = document.getElementById("languageSelect")?.value === "russian";
      const wordSuffix = isVietnam ? "từ" : isArabic ? "كلمات" : isRussian ? "слов" : "words";
      wordCountTxt.textContent = `${count} ${wordSuffix}`;
      if (count < MIN_MEANINGFUL_WORDS && count > 0) {
        wordCountTxt.classList.remove("bg-slate-100", "text-slate-600");
        wordCountTxt.classList.add("bg-rose-100", "text-rose-600", "font-bold");
      } else {
        wordCountTxt.classList.remove("bg-rose-100", "text-rose-600", "font-bold");
        wordCountTxt.classList.add("bg-slate-100", "text-slate-600");
      }
    }
    if (analyzeBtn) {
      const hasEnough = count >= MIN_MEANINGFUL_WORDS;
      const hasRecording = !!latestRecordingBlob;
      analyzeBtn.disabled = hasRecording && !hasEnough;
      const wordAlert = document.getElementById("wordAlert");
      if (wordAlert) {
        if (hasRecording && !hasEnough) {
          if (wordAlert) wordAlert.textContent = `Speech should be more than 25 words (only ${count} detected).`;
          wordAlert.classList.remove("hidden");
        } else {
          wordAlert.classList.add("hidden");
        }
      }
    }
  }

  function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 5;
    recognition.lang = recognitionLanguage;

    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) {
          transcriptFinal += `${result[0].transcript} `;
        } else {
          interim += result[0].transcript;
        }
      }
      transcriptInterim = interim;
      const fullTranscript = `${transcriptFinal} ${transcriptInterim}`.trim();
      updateWordCount(fullTranscript);
      if (recording && !paused) {
        if (transcriptText) transcriptText.textContent = fullTranscript || "Listening...";
      }
    };

    recognition.onerror = (event) => {
      const errorCode = String(event?.error || "").toLowerCase();
      if (errorCode === "not-allowed" || errorCode === "service-not-allowed") {
        recognitionAvailable = false;
      }
    };

    recognition.onend = () => {
      // Auto-restart recognition if still recording (prevents browser timeouts)
      if (recording && !paused && recognitionAvailable) {
        try {
          recognition.start();
        } catch (e) {
          // Restarting after a brief silence
        }
      }
    };

    recognitionAvailable = true;
  }

  // Defer initRecognition to when user clicks Start to avoid pre-emptive permission blocks
  // initRecognition();

  function renderTranscriptWithIssues(transcript, issues) {
    const res = lv.renderTextWithIssues(transcript, issues, "No speech was detected.");
    if (transcriptText) transcriptText.innerHTML = res.html;
    return res.count;
  }

  async function analyzeRecording(blob, clientTranscript) {
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm");
    formData.append("duration_seconds", String(elapsed));
    formData.append("pause_count", String(pauseCount));
    formData.append("client_transcript", String(clientTranscript || ""));
    formData.append("language", languageSelect?.value || "english");
    formData.append("reference_text", topicText?.getAttribute("data-topic-en") || topicText?.textContent?.trim() || "");

    const response = await fetch(analyzeEndpoint, {
      method: "POST",
      headers: { "X-CSRFToken": lv.getCsrfToken() },
      body: formData,
    });

    const raw = await response.json();
    if (!raw.success) throw new Error(raw.error || "Audio analysis failed.");
    const unwrapped = lv.unwrapApiData(raw);
    // Merge top-level score_25 (set by the Django view) into the data object
    // so callers don't need access to 'raw'.
    if (raw.score_25 !== undefined) unwrapped.score_25 = raw.score_25;
    return unwrapped;
  }

  function setBars(active) {
    if (waveRow) {
      if (active) waveRow.classList.add("active");
      else waveRow.classList.remove("active");
    }
    waveBars.forEach((bar) => {
      if (active) bar.classList.add("on");
      else bar.classList.remove("on");
    });
  }

  function startTimer() {
    if (timer) return;
    timer = setInterval(() => {
      if (recording && !paused) {
        elapsed += 1;
        if (timeTxt) timeTxt.textContent = `${elapsed}s`;
        if (elapsed >= MAX_RECORD_SECONDS) {
          handleTimeLimitReached();
        }
      }
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timer);
    timer = null;
  }

  // Auto-stop once the 1.5-minute cap is hit, preserving whatever was recorded.
  function handleTimeLimitReached() {
    if (!recording) return;
    recording = false;
    paused = false;
    stopTimer();
    stopRecognition();
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    setIdleUI();
    if (statusTxt) statusTxt.textContent = "Processing";
    if (micLabel) micLabel.textContent = `Time limit reached (${MAX_RECORD_SECONDS} seconds). Preparing audio and transcript...`;
  }

  async function prepareRecorder() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      if (micLabel) micLabel.textContent = "Microphone access is disabled. Please ensure you are using a secure connection (HTTPS or localhost).";
      if (statusTxt) statusTxt.textContent = "API Unavailable";
      throw new Error("getUserMedia not supported");
    }

    try {
      recordedChunks = []; // CRITICAL: Clear chunks before starting new recording
      // Simplified constraints for maximum compatibility
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      console.error("Mic access failed:", e);
      throw e;
    }

    const mimeCandidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/aac"];
    const supportedMime = mimeCandidates.find((mime) => MediaRecorder.isTypeSupported(mime));
    mediaRecorder = supportedMime
      ? new MediaRecorder(mediaStream, { mimeType: supportedMime })
      : new MediaRecorder(mediaStream);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      latestRecordingBlob = blob;
      audioUrl = URL.createObjectURL(blob);
      // Gate Analyze button based on word count now that recording is available
      updateWordCount(`${transcriptFinal} ${transcriptInterim}`.trim());
      recordedAudio.src = audioUrl;
      recordedAudio.playbackRate = 1;
      recordedAudio.defaultPlaybackRate = 1;
      recordResult.classList.remove("hidden");
      if (transcriptText) transcriptText.textContent = "Recording ready. Click Analyze to generate transcript and feedback.";
      if (analyzeNote) analyzeNote.textContent = "Click Analyze to generate exact scores and feedback.";
      if (statusTxt) statusTxt.textContent = "Ready";
      updateUILanguage();
      feedbackCard.classList.add("hidden");

      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
      }
      mediaStream = null;
      mediaRecorder = null;
      recordedChunks = [];
    };
  }

  function startRecognition() {
    if (!recognitionAvailable || !recognition) return;
    try {
      recognition.start();
    } catch (error) {
      // Recognition may already be running.
    }
  }

  function stopRecognition() {
    if (!recognitionAvailable || !recognition) return;
    try {
      recognition.stop();
    } catch (error) {
      // Recognition may already be stopped.
    }
  }

  function setRecordingUI() {
    if (micWrap) micWrap.classList.add("recording");
    if (micIcon) micIcon.textContent = "stop";
    updateUILanguage();
    micLabel.classList.add("on");

    if (paused) {
      if (pauseResumeBtn) pauseResumeBtn.textContent = "Resume";
      if (statusTxt) statusTxt.textContent = "Paused";
      if (ring1) ring1.classList.remove("on");
      if (ring2) ring2.classList.remove("on");
      setBars(false);
    } else {
      if (pauseResumeBtn) pauseResumeBtn.textContent = "Pause";
      if (statusTxt) statusTxt.textContent = "Recording";
      if (ring1) ring1.classList.add("on");
      if (ring2) ring2.classList.add("on");
      setBars(true);
    }

    pauseResumeBtn.classList.remove("hidden");
  }

  function setIdleUI() {
    if (micWrap) micWrap.classList.remove("recording");
    if (micIcon) micIcon.textContent = "mic";
    updateUILanguage();
    micLabel.classList.remove("on");
    if (statusTxt) statusTxt.textContent = "Idle";
    if (ring1) ring1.classList.remove("on");
    if (ring2) ring2.classList.remove("on");
    setBars(false);
    pauseResumeBtn.classList.add("hidden");
    if (pauseResumeBtn) pauseResumeBtn.textContent = "Pause";
  }

  function handlePauseLimitExceeded() {
    // Normal stop to preserve whatever was recorded
    if (recording) {
      recording = false;
      paused = false;
      stopTimer();
      stopRecognition();
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
      setIdleUI();
    }

    if (pauseAlert) {
      if (pauseAlert) pauseAlert.textContent = "Maximum pause limit (5) exceeded. Recording stopped.";
      pauseAlert.classList.remove("hidden");
    }
    if (statusTxt) statusTxt.textContent = "Terminated";
    if (micLabel) micLabel.textContent = "Limit exceeded.";
  }

  async function handleStartStopToggle() {
    if (!recording) {
      try {
        transcriptFinal = "";
        transcriptInterim = "";
        await prepareRecorder();

        // Initialize and start recognition after successful getUserMedia
        if (!recognition) initRecognition();

        // One continuous WebM recording preserves timestamps, so the native
        // audio progress bar stays synchronized with playback.
        mediaRecorder.start();
        startRecognition();

        recording = true;
        paused = false;
        pauseCount = 0;
        elapsed = 0;
        latestRecordingBlob = null;
        pauseAlert?.classList.add("hidden");
        if (pauseTxt) pauseTxt.textContent = "0";
        updateWordCount("");
        if (timeTxt) timeTxt.textContent = "0s";
        recordResult.classList.add("hidden");
        feedbackCard.classList.add("hidden");
        if (analyzeNote) analyzeNote.textContent = "Click Analyze to generate exact scores and feedback.";

        startTimer();
        setRecordingUI();
      } catch (error) {
        console.error("Microphone error:", error);
        if (statusTxt) statusTxt.textContent = "Microphone Error";
        if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
          if (micLabel) micLabel.textContent = "No microphone detected. Please ensure your mic is plugged in and try again.";
        } else if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
          if (micLabel) micLabel.textContent = "Microphone access denied. Click the 'lock' icon in your browser's address bar to allow access and try again.";
        } else {
          if (micLabel) micLabel.textContent = "Microphone error: " + (error.message || "Unknown error occurred.");
        }
      }
      return;
    }

    recording = false;
    paused = false;
    stopTimer();
    stopRecognition();

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }

    setIdleUI();
    if (statusTxt) statusTxt.textContent = "Processing";
    if (micLabel) micLabel.textContent = "Preparing audio and transcript...";
  }

  function handlePauseResumeToggle() {
    if (!recording || !mediaRecorder) return;

    if (!paused) {
      if (mediaRecorder.state === "recording") mediaRecorder.pause();
      paused = true;
      pauseCount += 1;
      if (pauseTxt) pauseTxt.textContent = String(pauseCount);
      stopRecognition();
      if (pauseCount > 5) {
        handlePauseLimitExceeded();
        return;
      }
    } else {
      if (mediaRecorder.state === "paused") mediaRecorder.resume();
      paused = false;
      startRecognition();
    }

    setRecordingUI();
  }

  function estimateLocalScores(transcript) {
    const words = (transcript.match(/[A-Za-z']+/g) || []).length;
    const minutes = Math.max(elapsed / 60, 0.1);
    const wordsPerMinute = words / minutes;
    const pacePenalty = wordsPerMinute < 85 ? 12 : (wordsPerMinute > 175 ? 12 : 0);
    const pausePenalty = Math.min(pauseCount * 3, 18);
    return {
      fluency: lv.clampScore(84 - pacePenalty - pausePenalty, 72),
      pronunciation: lv.clampScore(78 - Math.min(pauseCount * 2, 14), 70),
      confidence: lv.clampScore(82 - pausePenalty, 71),
    };
  }

  function hasMeaningfulSpeech(text) {
    return lv.hasMeaningfulText(text, 3, 10);
  }

  function getDynamicQuickTip({ transcript, issues, scores }) {
    const cleanIssues = Array.isArray(issues) ? issues : [];
    const safeScores = scores || {};
    const words = String(transcript || "").match(/[A-Za-z']+/g) || [];
    const minutes = Math.max(elapsed / 60, 0.1);
    const wordsPerMinute = words.length / minutes;

    const isVietnam = languageSelect?.value === "vietnam";
    const isArabic = languageSelect?.value === "arabic";
    const isRussian = languageSelect?.value === "russian";

    const topIssue = cleanIssues[0] || null;
    if (topIssue && topIssue.type && topIssue.suggestion) {
      return `${topIssue.type}: ${topIssue.suggestion}`;
    }

    const fluency = lv.clampScore(safeScores.fluency, 70);
    const pronunciation = lv.clampScore(safeScores.pronunciation, 70);
    const confidence = lv.clampScore(safeScores.confidence, 70);

    if (wordsPerMinute > 175) {
      return isVietnam
        ? "Bạn đang nói quá nhanh. Hãy nói chậm lại một chút và kết thúc mỗi câu một cách rõ ràng. (You are speaking too fast. Slow down slightly and finish each sentence clearly.)"
        : isArabic
          ? "أنت تتحدث بسرعة كبيرة. أبطئ قليلاً وأنهِ كل جملة بوضوح. (You are speaking too fast. Slow down slightly and finish each sentence clearly.)"
          : isRussian
            ? "Вы говорите слишком быстро. Немного замедлитесь и чётко завершайте каждое предложение. (You are speaking too fast. Slow down slightly and finish each sentence clearly.)"
            : "You are speaking too fast. Slow down slightly and finish each sentence clearly.";
    }
    if (wordsPerMinute > 0 && wordsPerMinute < 90) {
      return isVietnam
        ? "Tốc độ của bạn hơi chậm. Hãy duy trì nhịp điệu ổn định và kết nối các ý tưởng trong các câu ngắn. (Your pace is a bit slow. Keep a steady rhythm and connect ideas in short sentences.)"
        : isArabic
          ? "وتيرتك بطيئة بعض الشيء. حافظ على إيقاع ثابت واربط الأفكار في جمل قصيرة. (Your pace is a bit slow. Keep a steady rhythm and connect ideas in short sentences.)"
          : isRussian
            ? "Ваш темп немного медленный. Сохраняйте устойчивый ритм и связывайте мысли короткими предложениями. (Your pace is a bit slow. Keep a steady rhythm and connect ideas in short sentences.)"
            : "Your pace is a bit slow. Keep a steady rhythm and connect ideas in short sentences.";
    }
    if (pauseCount >= 3 || fluency < 70) {
      return isVietnam
        ? "Giảm các khoảng tạm dừng dài. Hít một hơi ngắn và tiếp tục suy nghĩ của bạn một cách tự tin. (Reduce long pauses. Take one short breath and continue your thought confidently.)"
        : isArabic
          ? "قلل من التوقفات الطويلة. خذ نفسًا قصيرًا واستمر في أفكارك بثقة. (Reduce long pauses. Take one short breath and continue your thought confidently.)"
          : isRussian
            ? "Сократите длинные паузы. Сделайте один короткий вдох и уверенно продолжайте свою мысль. (Reduce long pauses. Take one short breath and continue your thought confidently.)"
            : "Reduce long pauses. Take one short breath and continue your thought confidently.";
    }
    if (pronunciation < 75) {
      return isVietnam
        ? "Tập trung vào phát âm: nhấn mạnh các từ khóa và mở miệng nhiều hơn khi phát âm các nguyên âm. (Focus on pronunciation: stress key words and open your mouth more on vowel sounds.)"
        : isArabic
          ? "ركز على النطق: شدد على الكلمات الرئيسية وافتح فمك أكثر عند نطق الحروف المتحركة. (Focus on pronunciation: stress key words and open your mouth more on vowel sounds.)"
          : isRussian
            ? "Сосредоточьтесь на произношении: выделяйте ключевые слова и шире открывайте рот на гласных звуках. (Focus on pronunciation: stress key words and open your mouth more on vowel sounds.)"
            : "Focus on pronunciation: stress key words and open your mouth more on vowel sounds.";
    }
    if (confidence < 75) {
      return isVietnam
        ? "Cải thiện sự tự tin bằng cách sử dụng giọng nói mạnh mẽ hơn và kết thúc câu mà không bị hụt hơi. (Improve confidence by using a stronger voice and ending sentences without trailing off.)"
        : isArabic
          ? "حسّن الثقة باستخدام صوت أقوى وإنهاء الجمل دون أن يتلاشى الصوت. (Improve confidence by using a stronger voice and ending sentences without trailing off.)"
          : isRussian
            ? "Повышайте уверенность, используя более сильный голос и не давайте предложениям затихать в конце. (Improve confidence by using a stronger voice and ending sentences without trailing off.)"
            : "Improve confidence by using a stronger voice and ending sentences without trailing off.";
    }
    return isVietnam
      ? "Phát âm tốt. Bước tiếp theo: thêm cấu trúc câu rõ ràng hơn và nhấn mạnh từ khóa mạnh hơn. (Good delivery. Next step: add clearer sentence structure and stronger keyword emphasis.)"
      : isArabic
        ? "أداء جيد. الخطوة التالية: إضافة بنية جملة أوضح وتشديد أقوى على الكلمات الرئيسية. (Good delivery. Next step: add clearer sentence structure and stronger keyword emphasis.)"
        : isRussian
          ? "Хорошая подача. Следующий шаг: добавьте более чёткую структуру предложений и сильнее выделяйте ключевые слова. (Good delivery. Next step: add clearer sentence structure and stronger keyword emphasis.)"
          : "Good delivery. Next step: add clearer sentence structure and stronger keyword emphasis.";
  }

  async function handleAnalyze() {
    if (!latestRecordingBlob) {
      if (analyzeNote) analyzeNote.textContent = "Record audio first, then click Analyze.";
      return;
    }

    // Minimum word count check
    const wordCount = lv.countSpeakingWords(`${transcriptFinal} ${transcriptInterim}`.trim());
    const wordAlertEl = document.getElementById("wordAlert");
    if (wordCount < MIN_MEANINGFUL_WORDS) {
      if (wordAlertEl) {
        if (wordAlertEl) wordAlertEl.textContent = `Speech should be more than 25 words (only ${wordCount} detected).`;
        wordAlertEl.classList.remove("hidden");
      }
      return;
    }
    if (wordAlertEl) wordAlertEl.classList.add("hidden");

    analyzeBtn.disabled = true;
    if (analyzeBtn) analyzeBtn.textContent = "Analyzing...";
    if (analyzeNote) analyzeNote.textContent = "Analyzing transcript, mistakes, and scores...";
    if (transcriptText) transcriptText.textContent = "Analyzing your recording...";

    try {
      const localTranscriptSeed = `${transcriptFinal} ${transcriptInterim}`.trim();
      const result = await analyzeRecording(latestRecordingBlob, localTranscriptSeed);
      const transcript = result.transcript || result.text || `${transcriptFinal} ${transcriptInterim}`.trim();
      if (!hasMeaningfulSpeech(transcript)) {
        throw new Error("No meaningful speech detected. Please record a full sentence.");
      }

      updateWordCount(transcript);
      const renderedCount = renderTranscriptWithIssues(transcript, result.issues || []);
      const issuesList = result.issues || [];
      const speakingAssessment = lv.computeSpeakingAssessment(
        transcript,
        elapsed,
        renderedCount,
        pauseCount,
        result.scores || {}
      );
      const scoreValue = result.score_25 !== undefined ? result.score_25 : speakingAssessment.score;
      if (feedbackText) {
        feedbackText.textContent = result.feedback || "Analysis complete.";
      }
      if (improvedText) improvedText.textContent = lv.formatImprovedText(result.improved_passage, transcript, defaultImprovedText);
      if (quickTipText) quickTipText.textContent = getDynamicQuickTip({
        transcript,
        issues: issuesList,
        scores: result.scores || {},
      });
      if (lessonScore) lessonScore.textContent = `${scoreValue}/25`;
      lv.saveModuleScore("Speaking", { score: scoreValue });

      feedbackCard.classList.remove("hidden");
      if (analyzeNote) analyzeNote.textContent = "Analysis complete.";
      updateUILanguage();
      setTimeout(() => feedbackCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (error) {
      const localTranscript = `${transcriptFinal} ${transcriptInterim}`.trim();
      if (hasMeaningfulSpeech(localTranscript)) {
        updateWordCount(localTranscript);
        renderTranscriptWithIssues(localTranscript, []); // Ensure highlighting engine is used even with 0 issues
        const fallbackScores = estimateLocalScores(localTranscript);
        const fallbackScore = lv.computeSpeakingScore(
          localTranscript,
          elapsed,
          0,
          pauseCount,
          fallbackScores
        );
        if (feedbackText) {
          feedbackText.textContent = "Using fallback analysis because the full speaking review could not complete.";
        }
        if (improvedText) improvedText.textContent = lv.formatImprovedText("", localTranscript, defaultImprovedText);
        if (quickTipText) quickTipText.textContent = getDynamicQuickTip({
          transcript: localTranscript,
          issues: [],
          scores: fallbackScores,
        });
        if (lessonScore) lessonScore.textContent = `${fallbackScore}/25`;
        lv.saveModuleScore("Speaking", { score: fallbackScore });
        feedbackCard.classList.remove("hidden");
        if (analyzeNote) analyzeNote.textContent = "Using fallback analysis due to provider/network issue.";
        updateUILanguage();
        setTimeout(() => feedbackCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
      } else {
        if (transcriptText) transcriptText.textContent = "No meaningful speech detected. Please record and speak clearly, then analyze again.";
        if (feedbackText) {
          feedbackText.textContent = "Record a clearer response, then analyze again.";
        }
        if (improvedText) improvedText.textContent = defaultImprovedText;
        if (quickTipText) quickTipText.textContent = defaultQuickTip;
        feedbackCard.classList.add("hidden");
        if (analyzeNote) analyzeNote.textContent = error.message || "No speech detected.";
      }
    } finally {
      analyzeBtn.disabled = false;
      if (analyzeBtn) analyzeBtn.textContent = "Analyze";
    }
  }

  function resetAll() {
    recording = false;
    paused = false;
    pauseCount = 0;
    elapsed = 0;

    stopTimer();
    stopRecognition();
    setIdleUI();

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.onstop = null;
      recordedChunks = [];
      mediaRecorder.stop();
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
    }

    mediaStream = null;
    mediaRecorder = null;
    recordedChunks = [];
    latestRecordingBlob = null;

    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      audioUrl = null;
    }

    recordedAudio.removeAttribute("src");
    recordedAudio.load();

    recordResult.classList.add("hidden");
    feedbackCard.classList.add("hidden");
    pauseAlert?.classList.add("hidden");

    if (pauseTxt) pauseTxt.textContent = "0";
    updateWordCount("");
    if (timeTxt) timeTxt.textContent = "0s";
    if (transcriptText) transcriptText.textContent = "Stop recording to view what you spoke.";
    transcriptFinal = "";
    transcriptInterim = "";
    if (feedbackText) {
      feedbackText.textContent = "Great effort! Your pronunciation and fluency are being analyzed.";
    }
    if (improvedText) improvedText.textContent = defaultImprovedText;
    if (quickTipText) quickTipText.textContent = defaultQuickTip;
    if (lessonScore) lessonScore.textContent = "0/25";
    if (analyzeNote) analyzeNote.textContent = "Click Analyze to generate exact scores and feedback.";
    analyzeBtn.disabled = false;
    if (analyzeBtn) analyzeBtn.textContent = "Analyze";

    updateUILanguage();
    setIdleUI();
  }

  function refillTopicPool(excludeTopic) {
    remainingTopics = topics.filter((topic) => topic !== excludeTopic);
  }

  function getNextUniqueTopic() {
    const currentTopic = topicText.getAttribute("data-topic-en") || topicText.textContent.trim();
    if (!remainingTopics.length) {
      refillTopicPool(currentTopic);
    }
    if (!remainingTopics.length) return currentTopic;

    const index = Math.floor(Math.random() * remainingTopics.length);
    const selected = remainingTopics[index];
    remainingTopics.splice(index, 1);
    return selected;
  }

  newTopicBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (topicText) {
      const nextTopic = getNextUniqueTopic();
      topicText.setAttribute("data-topic-en", nextTopic);
      updateUILanguage();
    }
    resetAll();
  });

  const initialTopic = topicText.textContent.trim();
  topicText.setAttribute("data-topic-en", initialTopic);
  refillTopicPool(initialTopic);

  micBtn.addEventListener("click", handleStartStopToggle);
  pauseResumeBtn.addEventListener("click", handlePauseResumeToggle);
  analyzeBtn.addEventListener("click", handleAnalyze);
  tryAgainBtn.addEventListener("click", () => {
    resetAll();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  lv.restoreLanguagePreference("languageSelect", updateUILanguage);
  // Explicitly call once to ensure initial state is correct if restore didn't trigger change
  updateUILanguage();

  const previousResultData = lv.readConfig("previous-result-data");
  if (previousResultData && Object.keys(previousResultData).length > 0) {
    const transcript = previousResultData.transcript || previousResultData.text || "";
    if (transcript) {
      const issuesList = previousResultData.issues || [];
      renderTranscriptWithIssues(transcript, issuesList);

      if (feedbackText) feedbackText.textContent = previousResultData.feedback || "Analysis complete.";
      if (improvedText) {
        improvedText.innerHTML = lv.formatImprovedText(previousResultData.improved_passage, transcript, defaultImprovedText);
      }
      if (quickTipText) quickTipText.textContent = getDynamicQuickTip({
        transcript,
        issues: issuesList,
        scores: previousResultData.scores || {}
      });
      const localScores = estimateLocalScores(transcript);
      const finalScores = previousResultData.scores || localScores;
      if (lessonScore) {
        // Prefer the authoritative score_25 saved by the view; only recompute
        // as a last resort so Previous always matches what was stored in the DB.
        const savedScore25 = previousResultData.score_25;
        let displayScore;
        if (typeof savedScore25 === "number") {
          displayScore = Math.max(0, Math.min(25, Math.round(savedScore25)));
        } else {
          const rawScore =
            finalScores.overall || finalScores.fluency || 70;
          displayScore = Math.max(0, Math.min(25, Math.round(rawScore * 25 / 100)));
        }
        lessonScore.textContent = `${displayScore}/25`;
      }

      if (recordResult) recordResult.classList.remove("hidden");
      if (feedbackCard) feedbackCard.classList.remove("hidden");
      if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-check me-2"></i>Analysis Complete';
      }
      if (analyzeNote) {
        analyzeNote.textContent = "Showing previous review results.";
      }
    }
  }
})();
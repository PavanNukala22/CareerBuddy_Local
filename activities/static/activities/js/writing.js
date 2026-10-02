(function () {
  const lv = window.LinguaVoice;
  const config = lv.readConfig("writing-config");

  lv.setActiveNav(config.lessonsPath || window.location.pathname);
  lv.initIssueTooltips();

  const topicsByType = {
    general: [
      "Write about one person who inspires you.",
      "Describe your favorite day of the week and why.",
      "Write about a place you want to visit someday.",
      "If you could have dinner with anyone, who would it be and why?",
      "Describe your ideal weekend.",
      "Write about a hobby you enjoy or would like to learn.",
      "Write about your best childhood memory.",
      "Describe the most delicious meal you have ever eaten.",
      "Write a letter to your future self.",
      "What is the best piece of advice you have ever received?"
    ],
    story: [
      "Write a short story about a lost notebook that teaches a lesson.",
      "Imagine you wake up with a superpower. What happens first?",
      "Write a story where two strangers become best friends.",
      "A mysterious key is found in the garden. Tell the story of what it opens.",
      "You board a train and the train travels to the future.",
      "Write a story about a character who finds a map with no destination.",
      "Two friends discover a hidden room in their new school.",
      "A camping trip takes an unexpected turn when night falls.",
      "An old grandfather clock stops and something strange happens.",
      "Write a story ending with the line: 'And they never went back again.'"
    ],
    opinion: [
      "Do you think homework should be shorter? Explain your view.",
      "Is learning online better than learning in class? Why?",
      "Should schools have more sports time? Give reasons.",
      "Do you think social media causes more harm than good?",
      "Should students be required to learn a second language?",
      "Is it better to read a book or watch a movie?",
      "Should junk food be banned in school cafeterias? Explain.",
      "Are exams an effective way to test learning?",
      "Do you think video games can be educational? Why or why not?",
      "Is exploring space important or a waste of money?"
    ],
  };

  const topicsVN = {
    "Write about one person who inspires you.": "Hãy viết về một người truyền cảm hứng cho bạn.",
    "Describe your favorite day of the week and why.": "Hãy mô tả ngày yêu thích nhất trong tuần của bạn và lý do tại sao.",
    "Write about a place you want to visit someday.": "Hãy viết về một nơi mà bạn muốn đến thăm vào một ngày nào đó.",
    "If you could have dinner with anyone, who would it be and why?": "Nếu bạn có thể ăn tối với bất kỳ ai, đó sẽ là ai và tại sao?",
    "Describe your ideal weekend.": "Hãy mô tả một ngày cuối tuần lý tưởng của bạn.",
    "Write about a hobby you enjoy or would like to learn.": "Hãy viết về một sở thích bạn yêu thích hoặc muốn học hỏi.",
    "Write about your best childhood memory.": "Hãy viết về kỷ niệm thời thơ ấu tuyệt vời nhất của bạn.",
    "Describe the most delicious meal you have ever eaten.": "Hãy mô tả bữa ăn ngon nhất mà bạn từng được ăn.",
    "Write a letter to your future self.": "Hãy viết một lá thư cho chính mình trong tương lai.",
    "What is the best piece of advice you have ever received?": "Lời khuyên tốt nhất mà bạn từng nhận được là gì?",
    "Write a short story about a lost notebook that teaches a lesson.": "Hãy viết một câu chuyện ngắn về một cuốn sổ bị mất mang lại một bài học.",
    "Imagine you wake up with a superpower. What happens first?": "Hãy tưởng tượng bạn thức dậy với một siêu năng lực. Điều gì xảy ra đầu tiên?",
    "Write a story where two strangers become best friends.": "Hãy viết một câu chuyện trong đó hai người lạ trở thành bạn thân của nhau.",
    "A mysterious key is found in the garden. Tell the story of what it opens.": "Một chiếc chìa khóa bí ẩn được tìm thấy trong vườn. Hãy kể câu chuyện về những gì nó mở ra.",
    "You board a train and the train travels to the future.": "Bạn lên một chuyến tàu và chuyến tàu đó đi đến tương lai.",
    "Write a story about a character who finds a map with no destination.": "Hãy viết một câu chuyện về một nhân vật tìm thấy một tấm bản đồ không có điểm đến.",
    "Two friends discover a hidden room in their new school.": "Hai người bạn khám phá ra một căn phòng bí mật trong ngôi trường mới của họ.",
    "A camping trip takes an unexpected turn when night falls.": "Một chuyến đi cắm trại có một bước ngoặt bất ngờ khi màn đêm buông xuống.",
    "An old grandfather clock stops and something strange happens.": "Một chiếc đồng hồ quả lắc cũ dừng lại và một điều kỳ lạ xảy ra.",
    "Write a story ending with the line: 'And they never went back again.'": "Hãy viết một câu chuyện kết thúc bằng câu: 'Và họ không bao giờ quay lại nữa.'",
    "Do you think homework should be shorter? Explain your view.": "Bạn có nghĩ bài tập về nhà nên ngắn hơn không? Hãy giải thích quan điểm của bạn.",
    "Is learning online better than learning in class? Why?": "Học trực tuyến có tốt hơn học trên lớp không? Tại sao?",
    "Should schools have more sports time? Give reasons.": "Các trường học có nên có nhiều thời gian cho thể thao hơn không? Hãy đưa ra lý do.",
    "Do you think social media causes more harm than good?": "Bạn có nghĩ mạng xã hội gây hại nhiều hơn lợi không?",
    "Should students be required to learn a second language?": "Học sinh có nên bắt buộc phải học ngôn ngữ thứ hai không?",
    "Is it better to read a book or watch a movie?": "Đọc sách hay xem phim thì tốt hơn?",
    "Should junk food be banned in school cafeterias? Explain.": "Có nên cấm đồ ăn nhanh trong căng tin trường học không? Hãy giải thích.",
    "Are exams an effective way to test learning?": "Kỳ thi có phải là một cách hiệu quả để kiểm tra việc học không?",
    "Do you think video games can be educational? Why or why not?": "Bạn có nghĩ trò chơi điện tử có thể mang tính giáo dục không? Tại sao có hoặc tại sao không?",
    "Is exploring space important or a waste of money?": "Khám phá không gian là quan trọng hay là một sự lãng phí tiền bạc?"
  };

  const topicsRU = {
    "Write about one person who inspires you.": "Напишите о человеке, который вас вдохновляет.",
    "Describe your favorite day of the week and why.": "Опишите ваш любимый день недели и почему.",
    "Write about a place you want to visit someday.": "Напишите о месте, которое вы хотите когда-нибудь посетить.",
    "If you could have dinner with anyone, who would it be and why?": "Если бы вы могли поужинать с кем угодно, кто бы это был и почему?",
    "Describe your ideal weekend.": "Опишите ваши идеальные выходные.",
    "Write about a hobby you enjoy or would like to learn.": "Напишите о хобби, которым вы увлекаетесь или хотели бы заняться.",
    "Write about your best childhood memory.": "Напишите о вашем самом ярком детском воспоминании.",
    "Describe the most delicious meal you have ever eaten.": "Опишите самое вкусное блюдо, которое вы когда-либо ели.",
    "Write a letter to your future self.": "Напишите письмо самому себе в будущем.",
    "What is the best piece of advice you have ever received?": "Какой лучший совет вы когда-либо получали?",
    "Write a short story about a lost notebook that teaches a lesson.": "Напишите короткий рассказ о потерянной тетради, которая преподаёт урок.",
    "Imagine you wake up with a superpower. What happens first?": "Представьте, что вы просыпаетесь со сверхспособностью. Что происходит первым делом?",
    "Write a story where two strangers become best friends.": "Напишите историю о том, как два незнакомца становятся лучшими друзьями.",
    "A mysterious key is found in the garden. Tell the story of what it opens.": "В саду найден загадочный ключ. Расскажите историю о том, что он открывает.",
    "You board a train and the train travels to the future.": "Вы садитесь на поезд, и поезд отправляется в будущее.",
    "Write a story about a character who finds a map with no destination.": "Напишите историю о персонаже, который находит карту без указанного места назначения.",
    "Two friends discover a hidden room in their new school.": "Два друга обнаруживают потайную комнату в своей новой школе.",
    "A camping trip takes an unexpected turn when night falls.": "Поход с ночёвкой принимает неожиданный оборот с наступлением ночи.",
    "An old grandfather clock stops and something strange happens.": "Старые напольные часы останавливаются, и происходит что-то странное.",
    "Write a story ending with the line: 'And they never went back again.'": "Напишите историю, заканчивающуюся словами: «И они больше никогда не вернулись».",
    "Do you think homework should be shorter? Explain your view.": "Считаете ли вы, что домашних заданий должно быть меньше? Объясните свою точку зрения.",
    "Is learning online better than learning in class? Why?": "Онлайн-обучение лучше, чем обучение в классе? Почему?",
    "Should schools have more sports time? Give reasons.": "Должно ли в школах быть больше времени на спорт? Приведите причины.",
    "Do you think social media causes more harm than good?": "Считаете ли вы, что социальные сети приносят больше вреда, чем пользы?",
    "Should students be required to learn a second language?": "Должны ли ученики быть обязаны изучать второй язык?",
    "Is it better to read a book or watch a movie?": "Что лучше — читать книгу или смотреть фильм?",
    "Should junk food be banned in school cafeterias? Explain.": "Стоит ли запретить нездоровую еду в школьных столовых? Объясните.",
    "Are exams an effective way to test learning?": "Являются ли экзамены эффективным способом проверки знаний?",
    "Do you think video games can be educational? Why or why not?": "Считаете ли вы, что видеоигры могут быть образовательными? Почему да или нет?",
    "Is exploring space important or a waste of money?": "Исследование космоса важно или это пустая трата денег?"
  };

  const typeSelect = document.getElementById("typeSelect");
  const languageSelect = document.getElementById("languageSelect");
  const topicText = document.getElementById("topicText");
  const topicTextVN = document.getElementById("topicTextVN");
  const newTopicBtn = document.getElementById("newTopicBtn");
  const writingAnswer = document.getElementById("writingAnswer");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const reviewText = document.getElementById("reviewText");
  const reviewCard = document.getElementById("reviewCard");
  const analysisCard = document.getElementById("analysisCard");
  const feedbackText = document.getElementById("feedbackText");
  const improvedText = document.getElementById("improvedText");
  const quickTipText = document.getElementById("quickTipText");
  const wordCount = document.getElementById("wordCount");
  const wordAlert = document.getElementById("wordAlert");
  const lessonScore = document.getElementById("lessonScore");
  const analyzeEndpoint = config.analyzeEndpoint || "";
  const MIN_NON_SPACE_CHARS = 500;
  const MAX_NON_SPACE_CHARS = 900;
  const DEFAULT_ANALYZE_LABEL = "Submit for Analysis";
  const remainingTopicsByType = Object.fromEntries(
    Object.keys(topicsByType).map((type) => [type, []])
  );

  function countChars(text) {
    return String(text || "").replace(/\s+/g, "").length;
  }

  function updateWordGuard() {
    const totalChars = countChars(writingAnswer?.value || "");
    if (wordCount) wordCount.textContent = String(totalChars);
    const hasText = totalChars > 0;
    const isWithinRange = totalChars >= MIN_NON_SPACE_CHARS && totalChars <= MAX_NON_SPACE_CHARS;

    if (analyzeBtn) {
      analyzeBtn.disabled = !isWithinRange;
    }

    if (wordAlert) {
      if (!hasText) {
        if (wordAlert) wordAlert.textContent = `Please write between ${MIN_NON_SPACE_CHARS} and ${MAX_NON_SPACE_CHARS} characters.`;
        wordAlert.classList.add("hidden");
      } else if (totalChars < MIN_NON_SPACE_CHARS) {
        if (wordAlert) wordAlert.textContent = `Please write at least ${MIN_NON_SPACE_CHARS} characters.`;
        wordAlert.classList.remove("hidden");
      } else if (totalChars > MAX_NON_SPACE_CHARS) {
        if (wordAlert) wordAlert.textContent = `Please keep your answer within ${MAX_NON_SPACE_CHARS} characters.`;
        wordAlert.classList.remove("hidden");
      } else {
        wordAlert.classList.add("hidden");
      }
    }

    return { totalChars, isWithinRange };
  }

  function resetCards() {
    analysisCard.classList.add("hidden");
    reviewCard.classList.add("hidden");
    if (reviewText) reviewText.textContent = "Your highlighted mistakes will appear here after analysis.";
    if (feedbackText) feedbackText.textContent = "Analyze to generate feedback for your writing.";
    if (improvedText) improvedText.textContent = "An improved version will appear after analysis.";
    if (quickTipText) quickTipText.textContent = "Use punctuation and clear sentence flow for better writing quality.";
    if (lessonScore) lessonScore.textContent = "0/25";
    if (writingAnswer) {
      writingAnswer.value = "";
      writingAnswer.dispatchEvent(new Event("input"));
    }
  }

  function refillTopicPool(type, excludeTopic = "") {
    const list = topicsByType[type] || [];
    remainingTopicsByType[type] = list.filter((topic) => topic !== excludeTopic);
  }

  function getNextTopic(type) {
    const list = topicsByType[type] || [];
    const currentTopic = String(topicText?.getAttribute("data-topic-en") || topicText?.textContent || "").trim();
    if (!remainingTopicsByType[type]?.length) {
      refillTopicPool(type, currentTopic);
    }
    const pool = remainingTopicsByType[type] || [];
    if (!pool.length) return currentTopic || list[0] || "";
    const index = Math.floor(Math.random() * pool.length);
    const [nextTopic] = pool.splice(index, 1);
    return nextTopic || currentTopic || list[0] || "";
  }

  function updateUILanguage() {
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const currentTopic = topicText?.getAttribute("data-topic-en") || topicText?.textContent || "";

    // 1. Main Topic Translation
    if (isVietnam) {
      const vnTopic = topicsVN[currentTopic] || "Bản dịch đang được cập nhật...";
      topicText.innerHTML = `<span class="text-slate-900 font-bold">${vnTopic}</span> <span class="text-slate-400 font-normal text-2xl">(${currentTopic})</span>`;
    } else if (isRussian) {
      const ruTopic = topicsRU[currentTopic] || "Перевод обновляется...";
      topicText.innerHTML = `<span class="text-slate-900 font-bold">${ruTopic}</span> <span class="text-slate-400 font-normal text-2xl">(${currentTopic})</span>`;
    } else {
      topicText.textContent = currentTopic;
    }

    // 2. Headings & Labels Translation
    const uiTranslations = {
        "headingMistakes": { en: "Mistakes Review", vn: "Đánh Giá Lỗi Sai", ru: "Обзор Ошибок" },
        "headingEvaluation": { en: "Evaluation", vn: "Đánh Giá Kết Quả", ru: "Оценка" },
        "labelScore": { en: "Overall Score", vn: "Tổng Điểm", ru: "Общий Балл" },
        "labelImproved": { en: "Improved Version", vn: "Bản Cải Thiện", ru: "Улучшенная Версия" },
        "labelQuickTip": { en: "Quick Tip", vn: "Mẹo Nhanh", ru: "Быстрый Совет" },
        "labelFeedback": { en: "Overall Feedback", vn: "Phản Hồi Chung", ru: "Общий Отзыв" },
        "labelSidebarTip": { en: "Writing Tip", vn: "Mẹo Viết", ru: "Совет по Письму" },
        "textSidebarTip": {
            en: "Use punctuation correctly and maintain clear sentence flow for better writing quality. Break into paragraphs to structure your ideas.",
            vn: "Sử dụng dấu câu chính xác và duy trì luồng câu rõ ràng để có chất lượng bài viết tốt hơn. Chia thành các đoạn văn để cấu trúc ý tưởng của bạn.",
            ru: "Используйте пунктуацию правильно и поддерживайте ясный поток предложений для лучшего качества письма. Разбивайте текст на абзацы, чтобы структурировать свои идеи."
        }
    };

    Object.entries(uiTranslations).forEach(([id, langData]) => {
        const el = document.getElementById(id);
        if (el) {
            if (isVietnam) {
                el.innerHTML = `<span class="text-slate-900">${langData.vn}</span> <span class="text-slate-400">(${langData.en})</span>`;
            } else if (isRussian) {
                el.innerHTML = `<span class="text-slate-900">${langData.ru}</span> <span class="text-slate-400">(${langData.en})</span>`;
            } else {
                el.textContent = langData.en;
            }
        }
    });

    // Highlight helper — `local` is whichever language's text applies (vn or ru); the
    // caller passes the right one for the currently selected language.
    const highlightBilingual = (vn, en, ru) => {
        if (isVietnam) return `<span class="text-slate-700 font-bold">${vn}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
        if (isRussian && ru) return `<span class="text-slate-700 font-bold">${ru}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
        return en;
    };

    // Update button text
    if (analyzeBtn) {
        analyzeBtn.innerHTML = isVietnam
            ? `<span class="text-white">Gửi để Phân tích</span> <span class="opacity-60">(Submit for Analysis)</span>`
            : isRussian
            ? `<span class="text-white">Отправить на Анализ</span> <span class="opacity-60">(Submit for Analysis)</span>`
            : DEFAULT_ANALYZE_LABEL;
    }

    // Force translations for specific common strings
    const forceTranslations = {
        "Read your draft once for verb agreement, spelling, and sentence-ending punctuation.": {
            vn: "Hãy đọc lại bản nháp của bạn một lần để kiểm tra sự hòa hợp của động từ, chính tả và dấu câu kết thúc câu.",
            ru: "Прочитайте свой черновик один раз, проверяя согласование глаголов, орфографию и знаки препинания в конце предложений.",
            en: "Read your draft once for verb agreement, spelling, and sentence-ending punctuation."
        },
        "Your writing has been reviewed for grammar, spelling, and punctuation.": {
            vn: "Bài viết của bạn đã được xem xét về ngữ pháp, chính tả và dấu câu.",
            ru: "Ваш текст был проверен на грамматику, орфографию и пунктуацию.",
            en: "Your writing has been reviewed for grammar, spelling, and punctuation."
        }
    };

    // Update placeholders & Current results
    if (reviewText) {
        const en = "Your highlighted mistakes will appear here after analysis.";
        const vn = "Các lỗi sai được đánh dấu sẽ xuất hiện ở đây sau khi phân tích.";
        const ru = "Здесь появятся выделенные ошибки после анализа.";
        if (analysisCard?.classList.contains("hidden") || reviewText.textContent.includes(en)) {
            reviewText.innerHTML = highlightBilingual(vn, en, ru);
        }
    }
    if (feedbackText) {
        const en = "Analyze to generate feedback for your writing.";
        const vn = "Hãy phân tích để nhận được phản hồi cho bài viết của bạn.";
        const ru = "Проанализируйте, чтобы получить отзыв о вашем тексте.";
        const current = feedbackText.textContent.trim();

        if (analysisCard?.classList.contains("hidden") || current.includes(en)) {
            feedbackText.innerHTML = highlightBilingual(vn, en, ru);
        } else if ((isVietnam || isRussian) && forceTranslations[current]) {
            feedbackText.innerHTML = highlightBilingual(forceTranslations[current].vn, forceTranslations[current].en, forceTranslations[current].ru);
        } else if ((isVietnam || isRussian) && current.includes("(") && current.includes(")")) {
            const match = current.match(/^(.*)\((.*)\)$/);
            if (match) feedbackText.innerHTML = highlightBilingual(match[1].trim(), match[2].trim(), match[1].trim());
        }
    }
    if (improvedText) {
        const en = "An improved version will appear after analysis.";
        const vn = "Bản cải thiện sẽ xuất hiện ở đây sau khi phân tích.";
        const ru = "Улучшенная версия появится здесь после анализа.";
        if (analysisCard?.classList.contains("hidden") || improvedText.textContent.includes(en)) {
            improvedText.innerHTML = highlightBilingual(vn, en, ru);
        }
    }
    if (quickTipText) {
        const current = quickTipText.textContent.trim();
        const tipData = forceTranslations["Read your draft once for verb agreement, spelling, and sentence-ending punctuation."];
        
        if (analysisCard?.classList.contains("hidden") || current.includes(tipData.en)) {
            quickTipText.innerHTML = highlightBilingual(tipData.vn, tipData.en, tipData.ru);
        } else if ((isVietnam || isRussian) && current.includes("(") && current.includes(")")) {
            const match = current.match(/^(.*)\((.*)\)$/);
            if (match) quickTipText.innerHTML = highlightBilingual(match[1].trim(), match[2].trim(), match[1].trim());
        }
    }
  }

  function pickTopic() {
    if (writingAnswer) {
      writingAnswer.value = "";
      writingAnswer.dispatchEvent(new Event("input"));
    }
    const type = typeSelect?.value || "general";
    if (topicText) {
      const nextTopic = getNextTopic(type);
      topicText.setAttribute("data-topic-en", nextTopic);
      updateUILanguage();
    }
    resetCards();
    updateWordGuard();
  }

  function renderDraft(text, issues) {
    const renderResult = lv.renderTextWithIssues(text, issues || [], "Write something in the box first, then click Analyze.");
    if (reviewText) reviewText.innerHTML = renderResult.html;
    reviewCard.classList.remove("hidden");
    return renderResult;
  }

  async function analyzeWriting() {
    const text = writingAnswer?.value || "";
    const { totalChars, isWithinRange } = updateWordGuard();
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";

    if (!text.trim() || totalChars === 0) {
      renderDraft("", []);
      if (wordAlert) {
        if (wordAlert) wordAlert.textContent = isVietnam ? "Vui lòng viết nội dung trước khi phân tích." : isRussian ? "Пожалуйста, напишите текст перед анализом." : "Please write something before analyzing.";
        wordAlert.classList.remove("hidden");
      }
      analysisCard.classList.add("hidden");
      return;
    }

    if (!isWithinRange) {
      renderDraft(text, []);
      analysisCard.classList.add("hidden");
      return;
    }

    analyzeBtn.disabled = true;
    if (analyzeBtn) analyzeBtn.textContent = isVietnam ? "Đang phân tích..." : isRussian ? "Анализируем..." : "Analyzing...";

    const formData = new FormData();
    formData.append("module", "writing");
    formData.append("text", text);
    formData.append("language", languageSelect?.value || "english");
    formData.append("reference_text", topicText.getAttribute("data-topic-en") || topicText.textContent || "");
    if (window.lastImprovedPassage) {
      formData.append("previous_improved_passage", window.lastImprovedPassage);
    }

    try {
      const response = await fetch(analyzeEndpoint, { 
        method: "POST", 
        headers: { "X-CSRFToken": lv.getCsrfToken() },
        body: formData 
      });
      const raw = await response.json();

      if (!raw.success) throw new Error(raw.error || "Analysis failed.");

      const result = lv.unwrapApiData(raw);
      const analyzedText = typeof result.text === "string" ? result.text : text;
      const renderResult = renderDraft(analyzedText, result.issues || []);

      if (feedbackText) feedbackText.textContent = result.feedback || "Analysis complete.";
      if (improvedText) {
          const finalImproved = lv.formatImprovedText(result.improved_passage, text);
          improvedText.textContent = finalImproved;
          window.lastImprovedPassage = finalImproved;
      }
      if (quickTipText) quickTipText.textContent = result.quick_tip || "Use punctuation and clear sentence flow for better writing quality.";

      const scoreValue = raw.score_25 !== undefined ? raw.score_25 : lv.computeWritingScore(renderResult.count);
      if (lessonScore) lessonScore.textContent = `${scoreValue}/25`;
      lv.saveModuleScore("Writing", { score: scoreValue });

      const rightScoreCard = document.getElementById("rightScoreCard");
      const rightScoreValue = document.getElementById("rightScoreValue");
      const rightScoreDate = document.getElementById("rightScoreDate");
      if (rightScoreCard) rightScoreCard.style.display = "block";
      if (rightScoreValue) rightScoreValue.textContent = scoreValue;
      if (rightScoreDate) {
        const d = new Date();
        rightScoreDate.textContent = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      }

      analysisCard.classList.remove("hidden");
      setTimeout(() => reviewCard.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (error) {
      renderDraft(text, []);
      if (feedbackText) feedbackText.textContent = error.message || "Could not analyze your writing.";
      if (improvedText) improvedText.textContent = lv.formatImprovedText(text, "", "An improved version will appear after analysis.");
      if (quickTipText) quickTipText.textContent = "Review the draft and try analyzing again.";
      analysisCard.classList.remove("hidden");
    } finally {
      if (analyzeBtn) analyzeBtn.textContent = isVietnam ? "Gửi để Phân tích" : isRussian ? "Отправить на Анализ" : DEFAULT_ANALYZE_LABEL;
      updateWordGuard();
    }
  }

  newTopicBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    pickTopic();
  });
  typeSelect?.addEventListener("change", () => {
    refillTopicPool(typeSelect?.value || "general");
    pickTopic();
  });
  lv.restoreLanguagePreference("languageSelect", updateUILanguage);
  writingAnswer?.addEventListener("input", updateWordGuard);
  analyzeBtn?.addEventListener("click", analyzeWriting);

  refillTopicPool(typeSelect?.value || "general", String(topicText?.textContent || "").trim());
  if (topicText) topicText.setAttribute("data-topic-en", topicText.textContent.trim());
  updateWordGuard();
  if (lessonScore) lessonScore.textContent = "0/25";
})();



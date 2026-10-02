(function () {
  const MODULE_SCORE_STORAGE_KEY_PREFIX = "linguavoice-module-scores";
  const MODULE_SESSION_STORAGE_KEY_PREFIX = "linguavoice-module-sessions";

  function getUserScoreKey() {
    const bodyUserKey = document.body?.dataset?.lvUserKey;
    const htmlUserKey = document.documentElement?.dataset?.lvUserKey;
    const rawKey = String(bodyUserKey || htmlUserKey || "").trim();
    return rawKey || "";
  }

  function getModuleScoreStorageKey() {
    const userKey = getUserScoreKey();
    return userKey
      ? `${MODULE_SCORE_STORAGE_KEY_PREFIX}:${userKey}`
      : MODULE_SCORE_STORAGE_KEY_PREFIX;
  }

  function getModuleSessionStorageKey() {
    const userKey = getUserScoreKey();
    return userKey
      ? `${MODULE_SESSION_STORAGE_KEY_PREFIX}:${userKey}`
      : MODULE_SESSION_STORAGE_KEY_PREFIX;
  }

  function readConfig(id) {
    const node = document.getElementById(id);
    if (!node) return {};
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      return {};
    }
  }

  function unwrapApiData(payload) {
    if (!payload || typeof payload !== "object") return {};
    const first = payload.data;
    if (!first || typeof first !== "object") return {};
    if (first.data && typeof first.data === "object") return first.data;
    return first;
  }

  function setActiveNav(targetHref) {
    if (!targetHref) return;
    document.querySelectorAll(".top-nav .nav-link").forEach((link) => {
      const href = link.getAttribute("href");
      if (href && href !== "#" && href === targetHref) {
        link.classList.add("active");
      }
    });
  }

  function clampScore(value, fallback) {
    const parsed = Number(value);
    if (Number.isNaN(parsed)) return fallback;
    return Math.max(0, Math.min(100, Math.round(parsed)));
  }

  function hasMeaningfulText(text, minWords = 4, minLetters = 12) {
    const words = String(text || "").match(/[A-Za-z']+/g) || [];
    const letters = words.reduce((sum, word) => sum + word.length, 0);
    return words.length >= minWords && letters >= minLetters;
  }

  function countSpeakingWords(text) {
    return (String(text || "").match(/[A-Za-z']+/g) || [])
      .filter((word) => word.length > 3)
      .length;
  }

  function isNonPenalizingSpeakingIssue(issue) {
    const type = String(issue?.type || "").toLowerCase().trim();
    const combined = [
      issue?.message || "",
      issue?.suggestion || "",
      issue?.phrase || "",
    ].join(" ").toLowerCase();
    return (
      type === "punctuation" ||
      type === "fluency" ||
      combined.includes("comma") ||
      combined.includes("full stop") ||
      combined.includes("question mark") ||
      combined.includes("period") ||
      combined.includes("filler word") ||
      combined.includes("overuse of")
    );
  }

  function countSpeakingMistakes(issues) {
    if (!Array.isArray(issues)) return 0;
    return issues.filter((issue) => !isNonPenalizingSpeakingIssue(issue)).length;
  }

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function rangesOverlap(start, end, matches) {
    return matches.some((match) => !(end <= match.start || start >= match.end));
  }

  function normalizeHighlightText(text) {
    return String(text || "")
      .replaceAll("\u2018", "'")
      .replaceAll("\u2019", "'")
      .replaceAll("\u201c", '"')
      .replaceAll("\u201d", '"');
  }

  function findIssueRange(cleanText, phrase, matches) {
    if (!cleanText || !phrase) return null;
    
    const normalizedText = normalizeHighlightText(cleanText).toLowerCase();
    const normalizedPhrase = normalizeHighlightText(phrase).toLowerCase().trim();
    
    // 1. Try exact substring match first (most accurate)
    let searchIdx = 0;
    while (searchIdx < normalizedText.length) {
      const start = normalizedText.indexOf(normalizedPhrase, searchIdx);
      if (start < 0) break;
      const end = start + normalizedPhrase.length;
      if (!rangesOverlap(start, end, matches)) {
        return { start, end };
      }
      searchIdx = start + 1;
    }

    // 2. Token-based fallback (for cases with punctuation or minor spacing differences)
    // We try to match the sequence of words regardless of exact punctuation
    const textWords = [...normalizeHighlightText(cleanText).matchAll(/[A-Za-z']+/g)].map(m => ({
      text: m[0].toLowerCase(),
      start: m.index,
      end: m.index + m[0].length
    }));
    const phraseWords = normalizedPhrase.match(/[A-Za-z']+/g) || [];
    
    if (phraseWords.length === 0) return null;

    for (let i = 0; i <= textWords.length - phraseWords.length; i++) {
      let match = true;
      for (let j = 0; j < phraseWords.length; j++) {
        if (textWords[i + j].text !== phraseWords[j]) {
          match = false;
          break;
        }
      }
      
      if (match) {
        const start = textWords[i].start;
        const end = textWords[i + phraseWords.length - 1].end;
        if (!rangesOverlap(start, end, matches)) {
          return { start, end };
        }
      }
    }

    return null;
  }

  function levenshteinDistance(a, b) {
    const left = String(a || "");
    const right = String(b || "");
    if (!left.length) return right.length;
    if (!right.length) return left.length;

    const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
    for (let i = 0; i < left.length; i += 1) {
      let diagonal = previous[0];
      previous[0] = i + 1;
      for (let j = 0; j < right.length; j += 1) {
        const temp = previous[j + 1];
        previous[j + 1] = Math.min(
          previous[j + 1] + 1,
          previous[j] + 1,
          diagonal + (left[i] === right[j] ? 0 : 1)
        );
        diagonal = temp;
      }
    }
    return previous[right.length];
  }

  let activeIssueMark = null;
  let issueTooltipInitialized = false;

  function getIssueTooltip() {
    let tooltip = document.getElementById("lv-issue-tooltip");
    if (tooltip) return tooltip;

    tooltip = document.createElement("div");
    tooltip.id = "lv-issue-tooltip";
    tooltip.className = "lv-issue-tooltip";
    tooltip.hidden = true;
    tooltip.innerHTML = [
      '<div class="lv-issue-tooltip__type"></div>',
      '<div class="lv-issue-tooltip__message"></div>',
      '<div class="lv-issue-tooltip__try">Try: <span></span></div>',
    ].join("");
    document.body.appendChild(tooltip);
    return tooltip;
  }

  function positionIssueTooltip(mark) {
    const tooltip = getIssueTooltip();
    if (!mark || tooltip.hidden) return;

    tooltip.style.maxWidth = `${Math.min(320, Math.max(220, window.innerWidth - 24))}px`;
    tooltip.style.left = "12px";
    tooltip.style.top = "12px";

    const markRect = mark.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const margin = 12;
    let left = markRect.left + (markRect.width / 2) - (tooltipRect.width / 2);
    left = Math.max(margin, Math.min(left, window.innerWidth - tooltipRect.width - margin));

    let top = markRect.top - tooltipRect.height - 14;
    let placement = "top";
    if (top < margin) {
      top = markRect.bottom + 14;
      placement = "bottom";
    }

    tooltip.dataset.placement = placement;
    tooltip.style.left = `${Math.round(left)}px`;
    tooltip.style.top = `${Math.round(top)}px`;
  }

  function showIssueTooltip(mark) {
    if (!mark) return;
    const tooltip = getIssueTooltip();
    
    // Check for language preference
    const langSelect = document.getElementById("languageSelect");
    const isVietnam = langSelect && langSelect.value === "vietnam";
    const isRussian = langSelect && langSelect.value === "russian";
    const isArabic = langSelect && langSelect.value === "arabic";

    let type = mark.dataset.issueType || "Mistake";
    let message = mark.dataset.issueMessage || "Potential issue";
    let suggestion = mark.dataset.issueSuggestion || "Consider revising this phrase.";

    // Localize Labels
    const tryLabel = tooltip.querySelector(".try-label");
    if (tryLabel) {
        tryLabel.textContent = isVietnam ? "Thử: (Try:)" : isArabic ? "جرّب: (Try:)" : isRussian ? "Попробуйте: (Try:)" : "Try:";
    }

    // Localize Categories (Types)
    if (isVietnam) {
        const typeMap = {
            "GRAMMAR": "NGỮ PHÁP (GRAMMAR)",
            "SPELLING": "CHÍNH TẢ (SPELLING)",
            "VOCABULARY": "TỪ VỰNG (VOCABULARY)",
            "PUNCTUATION": "DẤU CÂU (PUNCTUATION)",
            "ACCURACY": "ĐỘ CHÍNH XÁC (ACCURACY)",
            "PRONUNCIATION": "PHÁT ÂM (PRONUNCIATION)",
            "SUGGESTION": "GỢI Ý (SUGGESTION)",
            "MISTAKE": "LỖI SAI (MISTAKE)"
        };
        const upType = type.toUpperCase();
        if (typeMap[upType]) {
            type = typeMap[upType];
        } else {
            type = `${type} (${type})`; // Fallback if unknown
        }
    } else if (isRussian) {
        const typeMap = {
            "GRAMMAR": "ГРАММАТИКА (GRAMMAR)",
            "SPELLING": "ОРФОГРАФИЯ (SPELLING)",
            "VOCABULARY": "СЛОВАРНЫЙ ЗАПАС (VOCABULARY)",
            "PUNCTUATION": "ПУНКТУАЦИЯ (PUNCTUATION)",
            "ACCURACY": "ТОЧНОСТЬ (ACCURACY)",
            "PRONUNCIATION": "ПРОИЗНОШЕНИЕ (PRONUNCIATION)",
            "SUGGESTION": "ПРЕДЛОЖЕНИЕ (SUGGESTION)",
            "MISTAKE": "ОШИБКА (MISTAKE)"
        };
        const upType = type.toUpperCase();
        if (typeMap[upType]) {
            type = typeMap[upType];
        } else {
            type = `${type} (${type})`; // Fallback if unknown
        }
    } else if (isArabic) {
        const typeMap = {
            "GRAMMAR": "القواعد (GRAMMAR)",
            "SPELLING": "الإملاء (SPELLING)",
            "VOCABULARY": "المفردات (VOCABULARY)",
            "PUNCTUATION": "علامات الترقيم (PUNCTUATION)",
            "ACCURACY": "الدقة (ACCURACY)",
            "PRONUNCIATION": "النطق (PRONUNCIATION)",
            "SUGGESTION": "اقتراح (SUGGESTION)",
            "MISTAKE": "خطأ (MISTAKE)"
        };
        const upType = type.toUpperCase();
        if (typeMap[upType]) {
            type = typeMap[upType];
        } else {
            type = `${type} (${type})`; // Fallback if unknown
        }
    }

    // Fallback translations for common AI messages if they aren't already bilingual
    const commonMessagesVN = {
        "Use singular verb agreement in this clause.": "Sử dụng sự hòa hợp động từ số ít trong mệnh đề này.",
        "Incorrect spelling.": "Sai chính tả.",
        "Incorrect punctuation.": "Sai dấu câu.",
        "Consider using a different word for better flow.": "Cân nhắc sử dụng một từ khác để luồng văn bản tốt hơn.",
        "Missing comma.": "Thiếu dấu phẩy.",
        "Sentence is too long or complex.": "Câu quá dài hoặc quá phức tạp.",
        "Check your subject-verb agreement.": "Kiểm tra sự hòa hợp giữa chủ ngữ và động từ của bạn.",
        "Possible typo.": "Có thể là lỗi đánh máy.",
        "Incorrect usage of article.": "Sử dụng mạo từ không chính xác."
    };

    const commonMessagesRU = {
        "Use singular verb agreement in this clause.": "Используйте согласование глагола в единственном числе в этом предложении.",
        "Incorrect spelling.": "Неправильное написание.",
        "Incorrect punctuation.": "Неправильная пунктуация.",
        "Consider using a different word for better flow.": "Рассмотрите использование другого слова для лучшей связности текста.",
        "Missing comma.": "Пропущена запятая.",
        "Sentence is too long or complex.": "Предложение слишком длинное или сложное.",
        "Check your subject-verb agreement.": "Проверьте согласование подлежащего и сказуемого.",
        "Possible typo.": "Возможная опечатка.",
        "Incorrect usage of article.": "Неправильное использование артикля."
    };

    const commonMessagesAR = {
        "Use singular verb agreement in this clause.": "استخدم مطابقة الفعل بصيغة المفرد في هذه الجملة.",
        "Incorrect spelling.": "خطأ إملائي.",
        "Incorrect punctuation.": "علامات ترقيم غير صحيحة.",
        "Consider using a different word for better flow.": "فكّر في استخدام كلمة مختلفة لتحسين تدفق النص.",
        "Missing comma.": "فاصلة مفقودة.",
        "Sentence is too long or complex.": "الجملة طويلة جدًا أو معقدة.",
        "Check your subject-verb agreement.": "تحقق من مطابقة الفاعل والفعل.",
        "Possible typo.": "قد يكون خطأ مطبعيًا.",
        "Incorrect usage of article.": "استخدام غير صحيح لأداة التعريف."
    };

    const highlightBilingual = (str) => {
        if (!isVietnam && !isRussian && !isArabic) return str;

        let text = str;
        // Apply fallback if it's a common English-only message
        const commonMessages = isVietnam ? commonMessagesVN : isArabic ? commonMessagesAR : commonMessagesRU;
        if (commonMessages[text]) {
            text = `${commonMessages[text]} (${text})`;
        }

        const match = text.match(/^(.*)\((.*)\)$/);
        if (match) {
            const localized = match[1].trim();
            const en = match[2].trim();
            return `<span class="text-slate-800 font-bold">${localized}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
        }
        return text;
    };

    tooltip.querySelector(".lv-issue-tooltip__type").textContent = type;
    tooltip.querySelector(".lv-issue-tooltip__message").innerHTML = highlightBilingual(message);
    tooltip.querySelector(".lv-issue-tooltip__try span:not(.try-label)").innerHTML = highlightBilingual(suggestion);
    tooltip.hidden = false;
    activeIssueMark = mark;
    positionIssueTooltip(mark);
  }

  function hideIssueTooltip(mark) {
    const tooltip = document.getElementById("lv-issue-tooltip");
    if (!tooltip) return;
    if (mark && activeIssueMark && mark !== activeIssueMark) return;
    tooltip.hidden = true;
    activeIssueMark = null;
  }

  function initIssueTooltips() {
    if (issueTooltipInitialized) return;
    issueTooltipInitialized = true;

    document.addEventListener("mouseover", (event) => {
      const mark = event.target.closest(".issue-mark");
      if (!mark) return;
      showIssueTooltip(mark);
    });

    document.addEventListener("mouseout", (event) => {
      const mark = event.target.closest(".issue-mark");
      if (!mark) return;
      const nextMark = event.relatedTarget && event.relatedTarget.closest
        ? event.relatedTarget.closest(".issue-mark")
        : null;
      if (nextMark === mark) return;
      hideIssueTooltip(mark);
    });

    document.addEventListener("focusin", (event) => {
      const mark = event.target.closest(".issue-mark");
      if (!mark) return;
      showIssueTooltip(mark);
    });

    document.addEventListener("focusout", (event) => {
      const mark = event.target.closest(".issue-mark");
      if (!mark) return;
      hideIssueTooltip(mark);
    });

    window.addEventListener("scroll", () => {
      if (activeIssueMark) {
        positionIssueTooltip(activeIssueMark);
      }
    }, true);

    window.addEventListener("resize", () => {
      if (activeIssueMark) {
        positionIssueTooltip(activeIssueMark);
      }
    });
  }

  function renderTextWithIssues(text, issues, emptyText = "No response to evaluate.") {
    initIssueTooltips();
    const rawText = text == null ? "" : String(text);
    if (!rawText.trim()) return { html: escapeHtml(emptyText), count: 0 };
    if (!Array.isArray(issues) || !issues.length) return { html: escapeHtml(rawText).replace(/\n/g, "<br/>"), count: 0 };

    const matches = [];
    issues.forEach((issue) => {
      const phrase = String(issue.phrase || "").trim();
      if (!phrase) return;
      const range = findIssueRange(rawText, phrase, matches);
      if (!range) return;
      matches.push({
        start: range.start,
        end: range.end,
        issue: {
          type: issue.type || "Suggestion",
          message: issue.message || "Potential issue",
          suggestion: issue.suggestion || "Consider revising this phrase.",
        },
      });
    });

    if (!matches.length) return { html: escapeHtml(rawText).replace(/\n/g, "<br/>"), count: 0 };

    matches.sort((a, b) => a.start - b.start);
    let cursor = 0;
    let output = "";
    matches.forEach((match) => {
      // Add text before match, preserving newlines
      output += escapeHtml(rawText.slice(cursor, match.start)).replace(/\n/g, "<br/>");
      const phraseText = rawText.slice(match.start, match.end);
      output += `<span class="issue-mark" tabindex="0" data-issue-type="${escapeHtml(match.issue.type)}" data-issue-message="${escapeHtml(match.issue.message)}" data-issue-suggestion="${escapeHtml(match.issue.suggestion)}" aria-label="${escapeHtml(`${match.issue.type}: ${match.issue.message}. Try: ${match.issue.suggestion}`)}">${escapeHtml(phraseText)}</span>`;
      cursor = match.end;
    });
    output += escapeHtml(rawText.slice(cursor)).replace(/\n/g, "<br/>");
    return { html: output, count: matches.length };
  }

  function formatImprovedText(text, fallbackText = "", emptyText = "An improved version will appear after analysis.") {
    const cleanText = String(text || fallbackText || "").replace(/\s+/g, " ").trim();
    if (!cleanText) return emptyText;
    const withPunctuation = /[.!?]$/.test(cleanText) ? cleanText : `${cleanText}.`;
    return withPunctuation.charAt(0).toUpperCase() + withPunctuation.slice(1);
  }

  // Generic fallback
  function computeLessonScore(issuesCount, pausesCount) {
    let score = 25;
    score -= (issuesCount * 2);
    if (pausesCount) score -= (pausesCount * 1);
    return Math.max(0, Math.min(25, score));
  }

  function formatScoreValue(value) {
    const numeric = Number(value);
    if (Number.isNaN(numeric)) return "0";
    return numeric.toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
  }

  // Listening: reward meaning match first, then apply lighter deductions for popup mistakes and pauses.
  function computeListeningAssessment(userText, referenceText, pausesCount, issuesCount = 0) {
    const STOPWORDS = new Set([
      "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
      "do", "does", "did", "will", "would", "shall", "should", "may", "might", "must", "can", "could",
      "i", "he", "she", "it", "they", "we", "you", "his", "her", "its", "our", "their", "my", "your",
      "and", "but", "or", "nor", "so", "yet", "for", "at", "by", "in", "on", "of", "to", "up", "as",
      "if", "not", "no", "then", "than", "that", "this", "these", "those", "with", "from", "into",
      "also", "just", "all", "each", "both", "more", "some", "after", "before", "during", "while",
    ]);

    const normalize = (text) => String(text || "").toLowerCase().match(/[a-z']+/g) || [];
    const stemWord = (word) => String(word || "")
      .replace(/(ingly|edly|ment|ness|ation|itions|ition|able|ible)$/i, "")
      .replace(/(ing|ed|ly|es|s)$/i, "")
      .trim();
    const toContentWords = (text) => normalize(text)
      .map((word) => stemWord(word))
      .filter((word) => word.length > 2 && !STOPWORDS.has(word));
    const refWords = toContentWords(referenceText);
    const userWords = toContentWords(userText);
    if (!refWords.length || !userWords.length) {
      return { score: 0, matchPercent: 0, contentMatch: 0 };
    }

    const refSet = new Set(refWords);
    const userSet = new Set(userWords);
    const matchedRef = [...refSet].filter((word) => userSet.has(word)).length;
    const matchedUser = [...userSet].filter((word) => refSet.has(word)).length;

    const recall = matchedRef / Math.max(refSet.size, 1);
    const precision = matchedUser / Math.max(userSet.size, 1);
    const contentMatch = Math.max(
      0,
      Math.min(1, (recall * 0.72) + (precision * 0.28))
    );

    const safeContentMatch = Math.max(0, Math.min(1, contentMatch));
    const issues = Math.max(0, Number(issuesCount) || 0);
    let baseScore = 0;

    if (safeContentMatch >= 0.999) {
      baseScore = 25;
    } else if (safeContentMatch >= 0.9) {
      baseScore = 24;
    } else if (safeContentMatch >= 0.8) {
      baseScore = 16 + (((safeContentMatch - 0.8) / 0.1) * 2);
    } else if (safeContentMatch >= 0.6) {
      baseScore = 13 + (((safeContentMatch - 0.6) / 0.2) * 3);
    } else if (safeContentMatch >= 0.5) {
      baseScore = 10 + (((safeContentMatch - 0.5) / 0.1) * 3);
    } else if (safeContentMatch >= 0.2) {
      baseScore = 5 + (((safeContentMatch - 0.2) / 0.3) * 5);
    } else {
      baseScore = safeContentMatch * 20;
    }

    const popupPenalty = issues * 0.25;
    const pausePenalty = Math.min(Math.max(0, Number(pausesCount) || 0) * 0.25, 1.5);
    let score = Math.round((baseScore - popupPenalty - pausePenalty) * 4) / 4;
    if (safeContentMatch < 0.2) {
      score = Math.min(score, 4.5);
    }

    return {
      score: Math.max(0, Math.min(25, score)),
      matchPercent: Math.round(safeContentMatch * 100),
      contentMatch: safeContentMatch,
    };
  }

  function computeListeningScore(userText, referenceText, pausesCount, issuesCount = 0) {
    return computeListeningAssessment(userText, referenceText, pausesCount, issuesCount).score;
  }

  function computeSpeakingAssessment(transcript, durationSeconds, issuesCount, pausesCount, scores = {}) {
    const pickBandScore = (wordCount, bands, qualityFactor) => {
      const selectedBand = bands.find((band) => wordCount >= band.min && wordCount <= band.max) || bands[bands.length - 1];
      const span = selectedBand.maxScore - selectedBand.minScore;
      return selectedBand.minScore + Math.round(span * qualityFactor);
    };

    const secs = Math.max(0, Number(durationSeconds) || 0);
    const wordCount = countSpeakingWords(transcript);
    const minutes = Math.max(secs / 60, 0.1);
    const wordsPerMinute = wordCount / minutes;
    const fluency = clampScore(scores.fluency, 72);
    const pronunciation = clampScore(scores.pronunciation, 72);
    const confidence = clampScore(scores.confidence, 72);
    const averageQuality = Math.round((fluency + pronunciation + confidence) / 3);
    const issues = Math.max(0, Number(issuesCount) || 0);
    const pauses = Math.max(0, Number(pausesCount) || 0);
    const qualityFactor = Math.max(0, Math.min(1, (averageQuality - 55) / 35));
    const minimalMistakeBands = [
      { min: 0, max: 9, minScore: 0, maxScore: 5 },
      { min: 10, max: 12, minScore: 4, maxScore: 6 },
      { min: 13, max: 18, minScore: 5, maxScore: 8 },
      { min: 19, max: 26, minScore: 9, maxScore: 12 },
      { min: 27, max: 32, minScore: 13, maxScore: 15 },
      { min: 33, max: 38, minScore: 16, maxScore: 18 },
      { min: 39, max: 44, minScore: 19, maxScore: 20 },
      { min: 45, max: 50, minScore: 21, maxScore: 22 },
      { min: 51, max: 58, minScore: 22, maxScore: 23 },
      { min: 59, max: 999, minScore: 23, maxScore: 24 },
    ];
    const oneToTwoMistakeBands = [
      { min: 0, max: 12, minScore: 2, maxScore: 6 },
      { min: 13, max: 18, minScore: 6, maxScore: 9 },
      { min: 19, max: 24, minScore: 10, maxScore: 14 },
      { min: 25, max: 34, minScore: 15, maxScore: 18 },
      { min: 35, max: 39, minScore: 18, maxScore: 20 },
      { min: 40, max: 49, minScore: 20, maxScore: 22 },
      { min: 50, max: 59, minScore: 22, maxScore: 23 },
      { min: 60, max: 65, minScore: 24, maxScore: 25 },
      { min: 66, max: 999, minScore: 25, maxScore: 25 },
    ];

    let score = 25;
    // Strictly deduct 1 mark per popup highlight as requested
    score -= issues;
    
    // Ensure score doesn't drop below 0
    score = Math.max(0, Math.min(25, Math.round(score)));

    return {
      score,
      wordCount,
      wordsPerMinute: Math.round(wordsPerMinute),
      averageQuality,
    };
  }

  function computeSpeakingScore(transcript, durationSeconds, issuesCount, pausesCount, scores = {}) {
    return computeSpeakingAssessment(transcript, durationSeconds, issuesCount, pausesCount, scores).score;
  }

  // Reading: score based on AI-detected issues + pauses
  function computeReadingScore(issuesCount, pausesCount) {
    let score = 25;
    // Strictly deduct 1 mark per 2 popup highlights as requested
    score -= Math.floor((issuesCount || 0) / 2);

    return Math.max(0, Math.min(25, Math.round(score)));
  }

  // Writing: sentence/spelling issues based
  function computeWritingScore(issuesCount) {
    let score = 25;
    // Strictly deduct 1 mark per popup as requested
    score -= (issuesCount || 0);

    return Math.max(0, Math.min(25, Math.round(score)));
  }

  function clearModuleScores() {
    try {
      window.localStorage.removeItem(getModuleScoreStorageKey());
      window.localStorage.removeItem(MODULE_SCORE_STORAGE_KEY_PREFIX);
    } catch (_) {}
  }

  function readModuleScores() {
    try {
      const raw = window.localStorage.getItem(getModuleScoreStorageKey());
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (error) {
      return {};
    }
  }

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  function saveModuleScore(moduleName, payload) {
    try {
      const storageKey = getModuleScoreStorageKey();
      const existing = JSON.parse(localStorage.getItem(storageKey) || "{}");
      existing[moduleName] = {
        score: payload.score || 0,
        date: new Date().toISOString()
      };
      localStorage.setItem(storageKey, JSON.stringify(existing));
    } catch (e) {
      // ignore
    }
  }

  function readModuleSessions() {
    try {
      const raw = window.localStorage.getItem(getModuleSessionStorageKey());
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function archiveCurrentSession() {
    const currentScores = readModuleScores();
    if (Object.keys(currentScores).length === 0) return;
    
    const sessions = readModuleSessions();
    sessions.push({
      date: new Date().toISOString(),
      scores: currentScores
    });

    try {
      window.localStorage.setItem(getModuleSessionStorageKey(), JSON.stringify(sessions));
    } catch (error) {}
    
    clearModuleScores();
  }

  // English is always the default. The chosen language applies only to the
  // current page view and is intentionally NOT persisted, so every refresh (or
  // newly opened page) starts in English again.
  function saveLanguagePreference(lang) {
    // No-op by design: the selection must not survive a refresh.
  }

  function getLanguagePreference() {
    return "english";
  }

  function restoreLanguagePreference(selectId, onUpdate) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const pref = getLanguagePreference();
    select.value = pref;

    select.addEventListener("change", (e) => {
      saveLanguagePreference(e.target.value);
      if (typeof onUpdate === "function") onUpdate();
    });

    // Fire once so the restored language is applied on load by every listener —
    // the dropdown label, the module UI, and the shared hero title/description
    // translator — not only when the user later changes the selector.
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }

  window.LinguaVoice = {
    getCsrfToken,
    readConfig,
    unwrapApiData,
    setActiveNav,
    clampScore,
    hasMeaningfulText,
    countSpeakingWords,
    countSpeakingMistakes,
    escapeHtml,
    initIssueTooltips,
    renderTextWithIssues,
    formatImprovedText,
    computeLessonScore,
    computeListeningAssessment,
    computeListeningScore,
    formatScoreValue,
    computeSpeakingAssessment,
    computeSpeakingScore,
    computeReadingScore,
    computeWritingScore,
    clearModuleScores,
    readModuleScores,
    saveModuleScore,
    readModuleSessions,
    archiveCurrentSession,
    saveLanguagePreference,
    getLanguagePreference,
    restoreLanguagePreference,
  };
})();

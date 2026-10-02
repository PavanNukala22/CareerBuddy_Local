(function () {
  const lv = window.LinguaVoice;
  const config = lv.readConfig("reading-config");

  lv.setActiveNav(config.lessonsPath || window.location.pathname);
  lv.initIssueTooltips();

  const languageSelect = document.getElementById("languageSelect");

  const passages = {
    1: [
      {
        title: "My Classroom Day",
        titleVN: "Ngày của tôi ở lớp học",
        titleRU: "Мой день в классе",
        titleAR: "يومي في الفصل الدراسي",
        badge: "Beginner",
        badgeVN: "Sơ cấp",
        displayLines: [
          "Every morning we greet our friends warmly.",
          "Our classroom is bright and very neat.",
          "The teacher writes the spelling words on the board.",
          "We read a short interesting story together.",
          "During recess, we play fun games outside.",
          "We share our snacks with each other.",
          "The bell rings and we go back inside.",
          "Our teacher reads us one last book.",
          "We learn new words and paint beautiful pictures.",
          "School is always a fun and happy place.",
          "We always help the teacher clean up the desks.",
          "Our principal sometimes visits to say a quick hello.",
          "I love seeing all my friends every single morning."
        ],
      },
      {
        title: "The Little Kitten",
        titleVN: "Chú mèo con nhỏ",
        titleRU: "Маленький котёнок",
        titleAR: "القطة الصغيرة",
        badge: "Beginner",
        badgeVN: "Sơ cấp",
        displayLines: [
          "A little kitten played in the green garden.",
          "She chased colorful butterflies near the flowers.",
          "Her owner called and she ran back fast.",
          "Then she drank warm milk and rested quietly.",
          "She curled up inside her soft blue basket.",
          "When she woke up, she wanted to play again.",
          "She found a small red ball on the floor.",
          "She rolled it around the whole living room.",
          "Her owner laughed and gave her a gentle pat.",
          "She purred loudly and fell asleep again.",
          "Her small bell jingles when she walks around.",
          "She likes to watch the birds through the window.",
          "Sometimes she tries to catch the little flies."
        ],
      },
      {
        title: "A Trip to the Zoo",
        titleVN: "Chuyến đi sở thú",
        titleRU: "Поездка в зоопарк",
        titleAR: "رحلة إلى حديقة الحيوان",
        badge: "Beginner",
        badgeVN: "Sơ cấp",
        displayLines: [
          "We went to the big zoo yesterday afternoon.",
          "The tall giraffes were eating fresh green leaves.",
          "I saw funny monkeys swinging from high branches.",
          "A large grey elephant was splashing in water.",
          "We took many nice photos of the animals.",
          "Next, we visited the scary lions and tigers.",
          "They were sleeping under a large shady tree.",
          "A colourful parrot said hello to us loudly.",
          "We ate tasty ice cream before going home.",
          "It was the best day ever with my family.",
          "The zookeeper fed the hungry penguins some small fish.",
          "We bought some colorful souvenirs at the gift shop.",
          "My favorite part was seeing the tall funny ostriches."
        ],
      },
      {
        title: "My New Bicycle",
        titleVN: "Chiếc xe đạp mới của tôi",
        titleRU: "Мой новый велосипед",
        titleAR: "دراجتي الجديدة",
        badge: "Beginner",
        badgeVN: "Sơ cấp",
        displayLines: [
          "I got a shiny new red bicycle today.",
          "It has a loud silver bell on the handle.",
          "I rode it down the bumpy street quickly.",
          "My neighborhood friends watched me go very fast.",
          "The cool breeze felt great on my face.",
          "My dad taught me how to use the brakes securely.",
          "We practiced riding around the park all morning.",
          "I only fell down once but it didn't hurt.",
          "Now I can ride without any training wheels.",
          "I love exploring the streets on my new bike.",
          "I made sure to always wear my bright yellow helmet.",
          "We rode all the way to the end of our street.",
          "Tomorrow I want to ride it to the local park."
        ],
      },
      {
        title: "Baking a Cake",
        titleVN: "Nướng bánh",
        titleRU: "Выпечка торта",
        titleAR: "خبز الكيك",
        badge: "Beginner",
        badgeVN: "Sơ cấp",
        displayLines: [
          "We decided to bake a large chocolate cake.",
          "I carefully mixed the flour, sugar, and eggs.",
          "My mom put the soft batter in the hot oven.",
          "The whole kitchen smelled very sweet and delicious.",
          "We prepared some creamy vanilla icing together.",
          "Once the cake cooled, we spread the icing evenly.",
          "I placed five colourful candles on the top.",
          "We sang happy birthday to my little brother loudly.",
          "It tasted wonderful with a cold glass of milk.",
          "Everyone asked for a second piece because it was great.",
          "My dad took a picture of the beautiful final cake.",
          "We made sure to clean up the messy kitchen carefully.",
          "It was the best birthday surprise we ever made."
        ],
      },
    ],
    2: [
      {
        title: "A Day at the Market",
        titleVN: "Một ngày ở chợ",
        titleRU: "День на рынке",
        titleAR: "يوم في السوق",
        badge: "Intermediate",
        badgeVN: "Trung cấp",
        displayLines: [
          "Every Saturday morning, we visit the bustling community market.",
          "We cautiously navigate through the crowded aisles to buy vegetables.",
          "The fragrant aroma of ripe cantaloupe and strawberries fills the air.",
          "My father thoughtfully negotiates prices with familiar vendors.",
          "Carrying heavy grocery bags makes us feel exhausted but satisfied.",
          "My mother thoroughly inspects exactly which tomatoes are perfectly ripe.",
          "We occasionally purchase deliciously seasoned artisan cheeses from the dairy stall.",
          "The energetic atmosphere is consistently accompanied by cheerful instrumental music.",
          "I always eagerly anticipate tasting the complimentary bakery samples.",
          "Unexpectedly meeting friendly neighbors is another wonderful characteristic of the marketplace.",
          "Eventually, we load the trunk with our weekly nutritional provisions."
        ],
      },
      {
        title: "The Helpful Robot",
        titleVN: "Robot hữu ích",
        titleRU: "Полезный робот",
        titleAR: "الروبوت المفيد",
        badge: "Intermediate",
        badgeVN: "Trung cấp",
        displayLines: [
          "A fascinating robot now independently assists nurses in the hospital.",
          "It accurately delivers necessary medicine through the lengthy corridors.",
          "The technology utilizes multiple sophisticated cameras to avoid unexpected obstacles.",
          "Medical practitioners genuinely appreciate this remarkable engineering advancement.",
          "Patients consistently find it thoroughly entertaining to watch.",
          "Its sleek metallic exterior reflects the sterile fluorescent lighting perfectly.",
          "The automated voice politely requests clearance when traversing crowded hallways.",
          "Efficiently completing numerous deliveries simultaneously drastically reduces human fatigue.",
          "Consequently, healthcare professionals can dedicate substantially more time to direct patient interaction.",
          "Programmable schedules guarantee that critical supplies arrive precisely when required.",
          "Specialized sensors prevent disastrous collisions with fragile medical equipment."
        ],
      },
      {
        title: "The School Football Match",
        titleVN: "Trận bóng đá trường học",
        titleRU: "Школьный футбольный матч",
        titleAR: "مباراة كرة القدم المدرسية",
        badge: "Intermediate",
        badgeVN: "Trung cấp",
        displayLines: [
          "Our academy organized a highly anticipated football tournament recently.",
          "Enthusiastic spectators cheered passionately from the fully occupied bleachers.",
          "The courageous goalkeeper miraculously blocked a potentially devastating penalty kick.",
          "Ultimately, our resilient athletes celebrated a triumphant victory together.",
          "Strategic coordination enabled our midfielders to flawlessly execute complex formations.",
          "The opposing defenders aggressively challenged every single offensive maneuver.",
          "Fortunately, our determined forwards successfully capitalized on a critical defensive vulnerability.",
          "The deafening roar of the audience echoed throughout the entire stadium.",
          "Post-game festivities included an unexpectedly elaborate fireworks display.",
          "Everyone enthusiastically congratulated the exhausted players afterwards.",
          "Developing exceptional teamwork remains a fundamental characteristic of successful athletics."
        ],
      },
      {
        title: "A Weekend Camping Trip",
        titleVN: "Chuyến cắm trại cuối tuần",
        titleRU: "Поход с ночёвкой на выходных",
        titleAR: "رحلة تخييم في عطلة نهاية الأسبوع",
        badge: "Intermediate",
        badgeVN: "Trung cấp",
        displayLines: [
          "We excitedly packed our complicated equipment for the wilderness excursion.",
          "Pitching the enormous canvas tent required considerable collaborative effort.",
          "Surrounded by picturesque scenery, we immediately gathered combustible firewood.",
          "The temperature plummeted dramatically when evening finally approached.",
          "Nevertheless, roasting marshmallows created a wonderfully memorable experience.",
          "The nocturnal symphony of crickets provided miraculously peaceful background acoustics.",
          "Waking up to magnificent mountainous panoramas felt truly extraordinary.",
          "We courageously embarked upon a remarkably challenging hiking expedition subsequently.",
          "Discovering an undiscovered cascading waterfall was the absolute highlight of the afternoon.",
          "Cautiously navigating the slippery terrain tested our physical endurance completely.",
          "Reconnecting with nature successfully eliminated our accumulated psychological stress."
        ],
      },
      {
        title: "Learning to Play Guitar",
        titleVN: "Học chơi đàn Guitar",
        titleRU: "Обучение игре на гитаре",
        titleAR: "تعلم عزف الجيتار",
        badge: "Intermediate",
        badgeVN: "Trung cấp",
        displayLines: [
          "I enthusiastically began practicing acoustic guitar several months ago.",
          "Initially, establishing the correct finger placement felt incredibly awkward.",
          "Memorizing specific chord progressions demanded extraordinary patience and determination.",
          "Gradually, the previously frustrating melodies became much more automatic.",
          "My instructor emphasizes the paramount importance of consistent rhythmic interpretation.",
          "Developing adequate calluses eliminated the initially excruciating physical discomfort.",
          "I persistently struggle with seamlessly transitioning between complicated minor chords.",
          "Nonetheless, successfully performing an entire composition generates profound psychological satisfaction.",
          "Analyzing classical masterpieces provides tremendous inspiration for my continuing education.",
          "Experimenting with unconventional strumming techniques encourages spontaneous creative expression.",
          "I occasionally participate in collaborative improvisational sessions with fellow musicians."
        ],
      },
    ],
    3: [
      {
        title: "Ocean Wonders",
        titleVN: "Kỳ quan đại dương",
        titleRU: "Чудеса океана",
        titleAR: "عجائب المحيط",
        badge: "Advanced",
        badgeVN: "Nâng cao",
        displayLines: [
          "The vast ocean constitutes an extraordinarily complex and enigmatic ecosystem encompassing unparalleled biodiversity.",
          "Oceanographers continually investigate the unfathomable depths, occasionally encountering bioluminescent phenomena.",
          "Surprisingly resilient microorganisms thrive in extreme environments adjacent to hydrothermal vents.",
          "Nevertheless, fragile coral reefs remain increasingly susceptible to detrimental consequences of anthropogenic negligence.",
          "Furthermore, the systematic acidification of seawater jeopardizes the intricate hierarchy of the marine food web.",
          "Simultaneously, unprecedented plastic accumulation dramatically threatens the viability of migratory aquatic species.",
          "Phytoplankton populations essentially regulate the indispensable oxygen production sustaining global atmospheric equilibrium.",
          "Submarine topography features spectacular geographical formations eclipsing terrestrial mountain ranges magnitude.",
          "Unregulated commercial dredging irreparably damages prehistoric geological structures spanning countless millennia.",
          "Consequently, establishing comprehensive marine sanctuaries represents a fundamentally critical ecological prerogative."
        ],
      },
      {
        title: "The Power of Habits",
        titleVN: "Sức mạnh của thói quen",
        titleRU: "Сила привычек",
        titleAR: "قوة العادات",
        badge: "Advanced",
        badgeVN: "Nâng cao",
        displayLines: [
          "Psychological literature consistently highlights the profound significance of unconscious repetitive behavior.",
          "Fundamentally, establishing beneficial routines requires circumventing ingrained neurological pathways.",
          "Procrastination frequently manifests as an involuntary psychological defense mechanism against perceived inadequacy.",
          "Overcoming such detrimental tendencies necessitates establishing deliberately constructed environmental cues.",
          "For instance, intentionally eliminating omnipresent distractions effectively counteracts our inherent susceptibility to interruptions.",
          "Consistency is mathematically advantageous, as exponential compounding predictably magnifies seemingly inconsequential daily actions.",
          "Furthermore, cultivating an attitude of unyielding perseverance inevitably reinforces the underlying cognitive architecture.",
          "Individuals who systematically analyze their habitual triggers ostensibly achieve more sustainable self-discipline.",
          "Neuroplasticity ensures that continuously modifying behavioral expressions fundamentally alters synaptic structural connectivity.",
          "However, attempting simultaneous multidimensional transformations frequently precipitates catastrophic psychological fatigue."
        ],
      },
      {
        title: "Artificial Intelligence in Medicine",
        titleVN: "Trí tuệ nhân tạo trong y học",
        titleRU: "Искусственный интеллект в медицине",
        titleAR: "الذكاء الاصطناعي في الطب",
        badge: "Advanced",
        badgeVN: "Nâng cao",
        displayLines: [
          "The ubiquitous integration of artificial intelligence is irrevocably reshaping contemporary technological infrastructures.",
          "Sophisticated neural networks autonomously process incomprehensible volumes of heterogeneous data with terrifying efficiency.",
          "Algorithmic bias, unfortunately, remains a particularly insidious concern requiring meticulous mitigation strategies.",
          "Consequently, technologists must prioritize ethical considerations while simultaneously pursuing unprecedented computational innovation.",
          "The implementation of natural language processing facilitates remarkably intuitive human-computer interaction paradigms.",
          "Moreover, autonomous vehicular navigation exemplifies the extraordinary potential of continuous real-time spatial analysis.",
          "However, widespread automation inevitably provokes legitimate socioeconomic anxieties regarding imminent widespread occupational displacement.",
          "The symbiotic relationship between human intuition and machine reliability must be carefully calibrated.",
          "Ultimately, establishing robust legislative frameworks will dictate the trajectory of this unprecedented technological revolution.",
          "Medical diagnostic applications currently demonstrate unparalleled capability identifying microscopic pathological abnormalities."
        ]
      },
      {
        title: "The Architecture of Ancient Rome",
        titleVN: "Kiến trúc La Mã cổ đại",
        titleRU: "Архитектура Древнего Рима",
        titleAR: "عمارة روما القديمة",
        badge: "Advanced",
        badgeVN: "Nâng cao",
        displayLines: [
          "Classical antiquity provided an indispensable architectural vernacular that continually influences contemporary structural engineering.",
          "The ingenious utilization of durable concrete empowered the Romans to construct breathtakingly voluminous amphitheaters.",
          "Furthermore, subterranean aqueduct networks brilliantly exemplified their unparalleled mastery of utilitarian hydrodynamics.",
          "The ubiquitous hemispherical dome ingeniously distributed tremendous gravitational stress with impeccable mathematical precision.",
          "Similarly, the meticulous integration of aesthetic symmetry with utilitarian pragmatism characterized their monumental basilicas.",
          "Today, modern architects frequently draw inspiration from these remarkably sophisticated geometrical proportions.",
          "Preserving such irreplaceable archaeological heritage necessitates employing exceptionally specialized restorative techniques.",
          "These surviving edifices eloquently testify to the profound ingenuity of ancient civilization.",
          "Unequivocally, the legacy of Roman ingenuity remains permanently etched into the consciousness of Western civilization.",
          "Their architectural vocabulary perpetually informs contemporary ubiquitous institutional monuments."
        ]
      },
      {
        title: "Sustainable Urban Planning",
        titleVN: "Quy hoạch đô thị bền vững",
        titleRU: "Устойчивое городское планирование",
        titleAR: "التخطيط الحضري المستدام",
        badge: "Advanced",
        badgeVN: "Nâng cao",
        displayLines: [
          "Accelerating metropolitan expansion inextricably demands the adoption of comprehensively sustainable urban planning methodologies.",
          "Planners must intricately balance burgeoning demographic requirements against increasingly perilous ecological constraints.",
          "Integrating decentralized renewable energy grids substantially mitigates reliance on deleterious fossil fuel consumption.",
          "Furthermore, encouraging non-motorized transportation necessitates developing meticulously interconnected pedestrian and cycling infrastructure.",
          "Innovative municipal waste management systems prioritize comprehensive subterranean recycling over traditional landfill accumulation.",
          "Cultivating expansive biodiversity corridors is absolutely indispensable for preserving indigenous flora within concrete environments.",
          "Consequently, implementing stringent architectural regulations ensures the ubiquitous construction of exceptionally energy-efficient skyscrapers.",
          "Engaging marginalized demographics in these bureaucratic processes guarantees equitably distributed environmental benefits.",
          "Conclusively, achieving authentic metropolitan sustainability requires an unprecedented synthesis of political willpower and technological ingenuity.",
          "This interdisciplinary collaborative endeavor remains ostensibly the most consequential challenge confronting modern humanity."
        ]
      },
    ],
  };

  let currentLevel = 1;
  let currentPassage = 0;
  let currentPassageText = "";
  const remainingPassageIndexes = { 1: [], 2: [], 3: [] };
  let recording = false;
  let isPaused = false;
  let pauses = 0;
  let seconds = 0;
  let timer = null;
  let transcriptFinal = "";
  let transcriptInterim = "";
  let recognition = null;
  let recognitionAvailable = false;
  let mediaRecorder = null;
  let mediaStream = null;
  let audioChunks = [];
  let recordedBlob = null;
  let recordedObjectUrl = "";
  let recordingMimeType = "audio/webm";
  let isFinalizingAudio = false;

  const analyzeEndpoint = config.analyzeEndpoint || "";
  let attemptEvaluated = false;
  const lessonScore = document.getElementById("lessonScore");
  const feedbackElement = document.getElementById("fbText");
  const improvedElement = document.getElementById("improvedText");
  const quickTipElement = document.getElementById("quickTipText");
  const defaultFeedbackText = "Great reading. You are improving with good pace and clarity.";
  const defaultImprovedText = "Your improved reading text will appear after analysis.";
  const defaultQuickTip = "Read line by line and keep a steady pace.";
  const pauseAlert = document.getElementById("pauseAlert");
  const pauseLimitMessage = "You have exceeded the maximum pause count.";

  // BADGE_RU/LEVEL_LABEL_RU are small fixed vocabularies (3 difficulty
  // names, "Level"), so they're translated once here rather than per-passage
  // like *VN fields — no need to duplicate the same word on every passage.
  const BADGE_RU = { "Beginner": "Начальный", "Intermediate": "Средний", "Advanced": "Продвинутый" };
  const BADGE_AR = { "Beginner": "مبتدئ", "Intermediate": "متوسط", "Advanced": "متقدم" };

  function highlightBilingual(vn, en, ru, ar) {
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";
    if (isVietnam) return `<span class="text-slate-800 font-bold">${vn}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
    if (isArabic && ar) return `<span class="text-slate-800 font-bold">${ar}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
    if (isRussian && ru) return `<span class="text-slate-800 font-bold">${ru}</span> <span class="text-slate-400 font-normal">(${en})</span>`;
    return en;
  }

  // The activity title/objective come from the Activity model, not the
  // fixed vocabulary translated elsewhere in this file, so they can't be
  // hardcoded. Mirrors the Google Translate approach used on the
  // sub-activity overview page (templates/activities/sub_activity.html) so
  // this hero heading behaves the same way as that page.
  const dynamicTranslationCache = {};
  async function translateTo(text, langCode) {
    if (!text || !text.trim()) return text;
    const key = `${text.trim()}|${langCode}`;
    if (dynamicTranslationCache[key]) return dynamicTranslationCache[key];
    try {
      const res = await fetch(
        "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=" +
        encodeURIComponent(langCode) + "&dt=t&q=" + encodeURIComponent(text.trim())
      );
      const data = await res.json();
      if (data && data[0]) {
        const translated = data[0].map((part) => part[0]).join("").trim();
        dynamicTranslationCache[key] = translated;
        return translated;
      }
    } catch (error) {
      // silent — falls back to the original English text below
    }
    return text.trim();
  }

  let activityHeaderLangToken = 0;
  async function updateActivityHeaderLanguage() {
    const titleEl = document.getElementById("activityTitle");
    const objectiveEl = document.getElementById("activityObjective");
    const crumbEl = document.getElementById("breadcrumbActivityTitle");
    if (!titleEl && !objectiveEl && !crumbEl) return;

    [titleEl, objectiveEl, crumbEl].forEach((el) => {
      if (el && !el.dataset.original) el.dataset.original = el.textContent.trim();
    });

    const langValue = languageSelect?.value || "english";
    const langCode = langValue === "vietnam" ? "vi" : langValue === "russian" ? "ru" : langValue === "arabic" ? "ar" : null;
    const token = ++activityHeaderLangToken;

    if (!langCode) {
      if (titleEl) titleEl.textContent = titleEl.dataset.original;
      if (objectiveEl) objectiveEl.textContent = objectiveEl.dataset.original;
      if (crumbEl) crumbEl.textContent = crumbEl.dataset.original;
      return;
    }

    const [titleTranslated, objectiveTranslated, crumbTranslated] = await Promise.all([
      titleEl ? translateTo(titleEl.dataset.original, langCode) : Promise.resolve(""),
      objectiveEl ? translateTo(objectiveEl.dataset.original, langCode) : Promise.resolve(""),
      crumbEl ? translateTo(crumbEl.dataset.original, langCode) : Promise.resolve("")
    ]);
    if (token !== activityHeaderLangToken) return; // language changed again meanwhile

    if (titleEl) titleEl.innerHTML = `<span>${titleTranslated}</span> <span style="opacity:.7;">(${titleEl.dataset.original})</span>`;
    if (objectiveEl) objectiveEl.innerHTML = `<span>${objectiveTranslated}</span> <span style="opacity:.7;">(${objectiveEl.dataset.original})</span>`;
    if (crumbEl) crumbEl.textContent = `${crumbTranslated} (${crumbEl.dataset.original})`;
  }

  function updateUILanguage() {
    updateActivityHeaderLanguage();
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";
    const passage = passages[currentLevel][currentPassage % passages[currentLevel].length];

    // 1. Passage Title & Badge
    if (isVietnam) {
      document.getElementById("passTitle").innerHTML = `<span class="text-slate-900 font-bold">${passage.titleVN}</span> <span class="text-slate-400 font-normal text-2xl">(${passage.title})</span>`;
      document.getElementById("passLevel").innerHTML = `<span class="font-bold text-slate-600">Cấp độ ${currentLevel}</span> <span class="text-slate-400 text-sm font-normal">(Level ${currentLevel})</span>`;
      document.getElementById("diffBadge").textContent = passage.badgeVN;
    } else if (isArabic) {
      const titleAR = passage.titleAR || "الترجمة قيد التحديث...";
      document.getElementById("passTitle").innerHTML = `<span class="text-slate-900 font-bold">${titleAR}</span> <span class="text-slate-400 font-normal text-2xl">(${passage.title})</span>`;
      document.getElementById("passLevel").innerHTML = `<span class="font-bold text-slate-600">المستوى ${currentLevel}</span> <span class="text-slate-400 text-sm font-normal">(Level ${currentLevel})</span>`;
      document.getElementById("diffBadge").textContent = BADGE_AR[passage.badge] || passage.badge;
    } else if (isRussian) {
      const titleRU = passage.titleRU || "Перевод обновляется...";
      document.getElementById("passTitle").innerHTML = `<span class="text-slate-900 font-bold">${titleRU}</span> <span class="text-slate-400 font-normal text-2xl">(${passage.title})</span>`;
      document.getElementById("passLevel").innerHTML = `<span class="font-bold text-slate-600">Уровень ${currentLevel}</span> <span class="text-slate-400 text-sm font-normal">(Level ${currentLevel})</span>`;
      document.getElementById("diffBadge").textContent = BADGE_RU[passage.badge] || passage.badge;
    } else {
      document.getElementById("passTitle").textContent = passage.title;
      document.getElementById("passLevel").textContent = `Level ${currentLevel}`;
      document.getElementById("diffBadge").textContent = passage.badge;
    }

    // 2. Labels Translation
    const uiTranslations = {
      "labelModuleHeader": { en: "Reading Module", vn: "Mô-đun Đọc", ru: "Модуль Чтения", ar: "وحدة القراءة" },
      "headingPassage": { en: "Passage", vn: "Đoạn văn", ru: "Отрывок", ar: "المقطع" },
      "labelReadingTip": { en: "Reading Tip", vn: "Mẹo Đọc", ru: "Совет по Чтению", ar: "نصيحة القراءة" },
      "headingMistakes": { en: "Mistakes Review", vn: "Đánh giá Lỗi sai", ru: "Обзор Ошибок", ar: "مراجعة الأخطاء" },
      "headingEvaluation": { en: "Evaluation", vn: "Đánh giá Kết quả", ru: "Оценка", ar: "التقييم" },
      "labelScore": { en: "Reading Score", vn: "Điểm đọc", ru: "Балл за Чтение", ar: "درجة القراءة" },
      "labelImproved": { en: "Improved Version", vn: "Bản Cải thiện", ru: "Улучшенная Версия", ar: "النسخة المحسّنة" },
      "labelQuickTip": { en: "Quick Tip", vn: "Mẹo Nhanh", ru: "Быстрый Совет", ar: "نصيحة سريعة" },
      "labelFeedback": { en: "Overall Feedback", vn: "Phản hồi Chung", ru: "Общий Отзыв", ar: "الملاحظات العامة" },
      "labelPausesCount": { en: "Pauses:", vn: "Số lần tạm dừng:", ru: "Паузы:", ar: "الإيقاف المؤقت:" },
      "breadcrumbPractice": { en: "Practice", vn: "Thực hành", ru: "Практика", ar: "ممارسة" },
      "analyzeNote": {
        en: "Click to generate pronunciation feedback and score.",
        vn: "Nhấn để tạo phản hồi phát âm và điểm số.",
        ru: "Нажмите, чтобы получить отзыв о произношении и оценку.",
        ar: "اضغط لإنشاء ملاحظات النطق والدرجة."
      }
    };

    Object.entries(uiTranslations).forEach(([id, langData]) => {
      const el = document.getElementById(id);
      if (el) {
        el.innerHTML = highlightBilingual(langData.vn, langData.en, langData.ru, langData.ar);
      }
    });

    // 3. Static sidebar content (label, tip bullets, reading tip paragraph)
    const staticTextTranslations = {
      "labelReadingPassage": {
        en: "Reading Passage",
        vn: "Đoạn văn Đọc",
        ru: "Отрывок для Чтения",
        ar: "مقطع القراءة"
      },
      "tipStatic1": {
        en: "• Read each line clearly and at a steady pace.",
        vn: "• Đọc từng dòng rõ ràng và với tốc độ ổn định.",
        ru: "• Читайте каждую строку чётко и в стабильном темпе.",
        ar: "• اقرأ كل سطر بوضوح وبوتيرة ثابتة."
      },
      "tipStatic2": {
        en: "• Pause naturally at commas and full stops.",
        vn: "• Tạm dừng tự nhiên ở dấu phẩy và dấu chấm.",
        ru: "• Делайте естественные паузы на запятых и точках.",
        ar: "• توقف بشكل طبيعي عند الفواصل والنقاط."
      },
      "tipStatic3": {
        en: "• Don't rush — accuracy matters most.",
        vn: "• Đừng vội vàng — độ chính xác quan trọng nhất.",
        ru: "• Не спешите — точность важнее всего.",
        ar: "• لا تتسرع — الدقة هي الأهم."
      },
      "tipReadingContent": {
        en: "Read slowly and clearly. Pause at full stops and keep a steady rhythm.",
        vn: "Đọc chậm và rõ ràng. Tạm dừng ở dấu chấm và giữ nhịp điệu ổn định.",
        ru: "Читайте медленно и чётко. Делайте паузы на точках и сохраняйте стабильный ритм.",
        ar: "اقرأ ببطء ووضوح. توقف عند النقاط وحافظ على إيقاع ثابت."
      }
    };

    Object.entries(staticTextTranslations).forEach(([id, langData]) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = isVietnam ? langData.vn : isArabic ? langData.ar : isRussian ? langData.ru : langData.en;
      }
    });

    // 4. Idle-state recorder text (mic label, status chip, Pause/Analyze
    // buttons). Only applied while not actively recording — the recording
    // click handlers already set their own localized text for the live
    // states, and this must not stomp on that if the language is switched
    // mid-recording.
    if (!recording) {
      const micLabel = document.getElementById("micLbl");
      if (micLabel) {
        micLabel.textContent = isVietnam
          ? "Nhấn để Bắt đầu Ghi âm (Tap to Start Recording)"
          : isArabic
            ? "اضغط لبدء التسجيل (Tap to Start Recording)"
            : isRussian
              ? "Нажмите, чтобы начать запись (Tap to Start Recording)"
              : "Tap to Start Recording";
      }
      const statusTxt = document.getElementById("statusTxt");
      if (statusTxt) {
        statusTxt.textContent = isVietnam ? "Nhàn rỗi" : isArabic ? "خامل" : isRussian ? "Ожидание" : "Idle";
      }
      const pauseBtn = document.getElementById("pauseBtn");
      if (pauseBtn) {
        pauseBtn.textContent = isVietnam ? "Tạm dừng (Pause)" : isArabic ? "إيقاف مؤقت" : isRussian ? "Пауза" : "Pause";
      }
      const analyzeButton = document.getElementById("analyzeBtn");
      if (analyzeButton && !attemptEvaluated) {
        analyzeButton.innerHTML = isVietnam
          ? '<i class="fas fa-brain me-2"></i>Gửi để Phân tích (Submit for Analysis)'
          : isArabic
            ? '<i class="fas fa-brain me-2"></i>إرسال للتحليل (Submit for Analysis)'
            : isRussian
              ? '<i class="fas fa-brain me-2"></i>Отправить на анализ (Submit for Analysis)'
              : '<i class="fas fa-brain me-2"></i>Submit for Analysis';
      }
    }
  }


  function showPauseLimitMessage() {
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";
    const msg = isVietnam ? "Bạn đã vượt quá số lần tạm dừng cho phép. (You have exceeded the maximum pause count.)" : isArabic ? "لقد تجاوزت الحد الأقصى لعدد مرات الإيقاف المؤقت. (You have exceeded the maximum pause count.)" : isRussian ? "Вы превысили максимальное количество пауз. (You have exceeded the maximum pause count.)" : pauseLimitMessage;
    if (pauseAlert) {
      pauseAlert.innerHTML = msg;
      pauseAlert.classList.remove("hidden");
    }
    document.getElementById("statusTxt").textContent = "Terminated";
    document.getElementById("reviewText").innerHTML = msg;
  }

  function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 5;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let interim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) {
          let bestAlt = result[0].transcript;
          let bestScore = -1;
          for (let a = 0; a < result.length; a++) {
            const alt = result[a].transcript.toLowerCase();
            const passWords = currentPassageText.toLowerCase().split(/\s+/);
            const altWords = alt.split(/\s+/);
            const matches = altWords.filter(w => passWords.includes(w)).length;
            const score = matches / Math.max(altWords.length, 1);
            if (score > bestScore) { bestScore = score; bestAlt = result[a].transcript; }
          }
          transcriptFinal += `${bestAlt} `;
        } else {
          interim += result[0].transcript;
        }
      }
      transcriptInterim = interim;
    };

    recognition.onerror = () => {
      recognitionAvailable = false;
    };

    recognitionAvailable = true;
  }

  initRecognition();

  async function startAudioCapture() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;

    try {
      if (typeof MediaRecorder === "undefined") return false;
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeCandidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
      const supportedMime = mimeCandidates.find((mime) => MediaRecorder.isTypeSupported(mime));
      mediaRecorder = supportedMime ? new MediaRecorder(mediaStream, { mimeType: supportedMime }) : new MediaRecorder(mediaStream);
      recordingMimeType = mediaRecorder.mimeType || supportedMime || "audio/webm";
      audioChunks = [];
      isFinalizingAudio = false;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        try {
          if (!audioChunks.length) {
            recordedBlob = null;
            return;
          }
          recordedBlob = new Blob(audioChunks, { type: recordingMimeType || "audio/webm" });
          if (recordedObjectUrl) URL.revokeObjectURL(recordedObjectUrl);
          recordedObjectUrl = URL.createObjectURL(recordedBlob);
          document.getElementById("recordedAudio").src = recordedObjectUrl;
          document.getElementById("recordedWrap").classList.remove("hidden");
        } finally {
          isFinalizingAudio = false;
          mediaRecorder = null;
        }
      };

      mediaRecorder.start();
      return true;
    } catch (error) {
      return false;
    }
  }

  function stopAudioCapture(discard = false) {
    if (discard && mediaRecorder) {
      mediaRecorder.onstop = null;
      audioChunks = [];
      recordedBlob = null;
      isFinalizingAudio = false;
    }

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      if (!discard) isFinalizingAudio = true;
      mediaRecorder.stop();
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    if (discard) mediaRecorder = null;
  }

  function startRecognition() {
    if (!recognitionAvailable || !recognition) return;
    try {
      recognition.start();
    } catch (error) {
    }
  }

  function stopRecognition() {
    if (!recognitionAvailable || !recognition) return;
    try {
      recognition.stop();
    } catch (error) {
    }
  }

  function renderPassage() {
    const list = passages[currentLevel];
    const passage = list[currentPassage % list.length];
    currentPassageText = (passage.displayLines || []).join(" ");

    updateUILanguage();

    document.getElementById("passBox").innerHTML = (passage.displayLines || [])
      .map((line, lineIndex) => `<span class="passage-line">${line.split(" ").map((word, wordIndex) => `<span class="word" id="w${lineIndex}-${wordIndex}">${word} </span>`).join("")} </span>`)
      .join("");
  }

  function refillPassagePool(level, excludeIndex = -1) {
    const list = passages[level] || [];
    remainingPassageIndexes[level] = list
      .map((_, index) => index)
      .filter((index) => index !== excludeIndex);
  }

  function getNextPassageIndex(level) {
    if (!remainingPassageIndexes[level]?.length) {
      refillPassagePool(level, level === currentLevel ? currentPassage : -1);
    }
    const pool = remainingPassageIndexes[level] || [];
    if (!pool.length) return Math.max(0, level === currentLevel ? currentPassage : 0);
    const selectedIndex = Math.floor(Math.random() * pool.length);
    const [nextIndex] = pool.splice(selectedIndex, 1);
    return nextIndex;
  }

  function resetReading() {
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";
    recording = false;
    isPaused = false;
    pauses = 0;
    seconds = 0;
    transcriptFinal = "";
    transcriptInterim = "";
    recordedBlob = null;
    isFinalizingAudio = false;
    attemptEvaluated = false;

    if (recordedObjectUrl) {
      URL.revokeObjectURL(recordedObjectUrl);
      recordedObjectUrl = "";
    }

    clearInterval(timer);
    stopRecognition();
    stopAudioCapture(true);

    document.getElementById("fbCard").classList.add("hidden");
    document.getElementById("timeTxt").textContent = "0s";
    document.getElementById("pauseTxt").textContent = "0";

    const micBtn = document.getElementById("micBtn");
    if (micBtn) micBtn.innerHTML = '<span class="material-symbols-outlined text-3xl">mic</span>';
    micBtn.classList.remove("rec");
    // Re-enable recording for this fresh attempt (switching level / New
    // passage is the intentional restart path — see analyzeReading()'s
    // success handler for where this gets locked again).
    micBtn.disabled = false;

    const pauseBtn = document.getElementById("pauseBtn");
    if (pauseBtn) pauseBtn.classList.add("hidden");

    document.getElementById("micLbl")?.classList.remove("on");

    document.getElementById("rr1")?.classList.remove("on");
    document.getElementById("rr2")?.classList.remove("on");
    pauseAlert?.classList.add("hidden");

    document.getElementById("analyzeBtn").disabled = false;

    // Sets the localized idle-state text for statusTxt, micLbl, pauseBtn
    // and analyzeBtn — the hardcoded English previously set above and below
    // this call would otherwise overwrite whatever language is selected.
    updateUILanguage();

    const reviewTextEl = document.getElementById("reviewText");
    if (reviewTextEl) {
      reviewTextEl.textContent = isVietnam
        ? "Đọc đoạn văn, sau đó nhấn Phân tích."
        : isArabic
          ? "اقرأ المقطع، ثم اضغط على تحليل."
          : isRussian
            ? "Прочитайте отрывок, затем нажмите «Анализ»."
            : "Read the passage, then click Analyze.";
    }
    const fbText = document.getElementById("fbText");
    if (fbText) {
      fbText.textContent = isVietnam
        ? "Phân tích bài đọc của bạn sẽ xuất hiện ở đây."
        : isArabic
          ? "سيظهر تحليل قراءتك هنا."
          : isRussian
            ? "Ваш анализ чтения появится здесь."
            : "Your reading analysis will appear here.";
    }

    document.getElementById("recordedWrap").classList.add("hidden");
    document.getElementById("recordedAudio").removeAttribute("src");
    document.getElementById("recordedAudio").load();
    if (lessonScore) lessonScore.textContent = "0/25";
  }

  function setLevelFromButton(button, level) {
    currentLevel = level;
    currentPassage = getNextPassageIndex(level);
    document.querySelectorAll(".lvl").forEach((element) => {
      element.classList.remove("active", "bg-white", "shadow-sm", "font-bold", "text-sky-600");
      element.classList.add("text-slate-500", "hover:text-slate-800");
    });
    button.classList.remove("text-slate-500", "hover:text-slate-800");
    button.classList.add("active", "bg-white", "shadow-sm", "font-bold", "text-sky-600");
    renderPassage();
    resetReading();
  }

  document.querySelectorAll(".lvl").forEach((button, index) => {
    button.addEventListener("click", () => setLevelFromButton(button, index + 1));
  });

  document.querySelector(".btn-new")?.addEventListener("click", () => {
    currentPassage = getNextPassageIndex(currentLevel);
    renderPassage();
    resetReading();
  });

  document.getElementById("micBtn")?.addEventListener("click", async () => {
    const micBtn = document.getElementById("micBtn");
    const micLabel = document.getElementById("micLbl");
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";

    if (!recording) {
      const startedAudio = await startAudioCapture();
      const canCapture = startedAudio || recognitionAvailable;
      if (!canCapture) {
        document.getElementById("reviewText").textContent = isVietnam ? "Không tìm thấy micrô. Vui lòng cho phép quyền truy cập micrô và thử lại. (Microphone is unavailable.)" : isArabic ? "الميكروفون غير متاح. يرجى السماح بالوصول إلى الميكروفون والمحاولة مرة أخرى. (Microphone is unavailable.)" : isRussian ? "Микрофон недоступен. Разрешите доступ к микрофону и попробуйте снова. (Microphone is unavailable.)" : "Microphone is unavailable. Please allow microphone permission and try again.";
        return;
      }

      transcriptFinal = "";
      transcriptInterim = "";
      recordedBlob = null;
      isFinalizingAudio = false;

      if (recordedObjectUrl) {
        URL.revokeObjectURL(recordedObjectUrl);
        recordedObjectUrl = "";
      }

      document.getElementById("recordedWrap").classList.add("hidden");
      document.getElementById("recordedAudio").removeAttribute("src");
      document.getElementById("recordedAudio").load();

      recording = true;
      isPaused = false;
      pauses = 0;
      pauseAlert?.classList.add("hidden");
      document.getElementById("pauseTxt").textContent = "0";

      const pauseBtn = document.getElementById("pauseBtn");
      if (pauseBtn) {
        pauseBtn.classList.remove("hidden");
        if (pauseBtn) pauseBtn.textContent = isVietnam ? "Tạm dừng (Pause)" : isArabic ? "إيقاف مؤقت" : isRussian ? "Пауза" : "Pause";
      }

      micBtn.classList.add("rec");
      if (micBtn) micBtn.innerHTML = '<span class="material-symbols-outlined text-3xl">stop</span>';
      if (micLabel) micLabel.textContent = isVietnam ? "Đang ghi âm... Nhấn để Dừng (Recording... Tap to Stop)" : isArabic ? "جارٍ التسجيل... اضغط للإيقاف (Recording... Tap to Stop)" : isRussian ? "Идёт запись... Нажмите, чтобы остановить (Recording... Tap to Stop)" : "Recording... Tap to Stop";
      micLabel.classList.add("on");
      document.getElementById("rr1")?.classList.add("on");
      document.getElementById("rr2")?.classList.add("on");
      document.getElementById("statusTxt").textContent = isVietnam ? "Đang ghi âm" : isArabic ? "جارٍ التسجيل" : isRussian ? "Идёт запись" : "Recording";
      startRecognition();
      timer = setInterval(() => {
        if (!isPaused) {
          seconds += 1;
          document.getElementById("timeTxt").textContent = `${seconds}s`;
        }
      }, 1000);

      if (!startedAudio && recognitionAvailable) {
        document.getElementById("reviewText").textContent = isVietnam ? "Tính năng ghi tệp âm thanh không được hỗ trợ trong trình duyệt này, nhưng tính năng dịch giọng nói đang hoạt động. (Audio file recording is not supported, but transcript capture is active.)" : isArabic ? "تسجيل الملف الصوتي غير مدعوم في هذا المتصفح، ولكن التقاط النص نشط. (Audio file recording is not supported, but transcript capture is active.)" : isRussian ? "Запись аудиофайла не поддерживается в этом браузере, но распознавание речи активно. (Audio file recording is not supported, but transcript capture is active.)" : "Audio file recording is not supported in this browser, but transcript capture is active.";
      }
      return;
    }

    stopRecordingNow();
  });

  // Shared by the mic button's "stop" click and by analyzeReading(), which
  // must stop an in-progress recording itself if the user clicks Analyze
  // without tapping "Stop" first — otherwise capture kept running in the
  // background through and after analysis, and the transcript/audio sent
  // for evaluation could still be mid-recording rather than the finished
  // answer. Reads the language directly from languageSelect instead of
  // taking a param, so every caller stays in sync automatically.
  function stopRecordingNow() {
    if (!recording) return;
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";
    const micBtn = document.getElementById("micBtn");
    const micLabel = document.getElementById("micLbl");

    recording = false;
    isPaused = false;
    clearInterval(timer);
    stopRecognition();
    stopAudioCapture();
    if (micBtn) {
      micBtn.classList.remove("rec");
      micBtn.innerHTML = '<span class="material-symbols-outlined text-3xl">mic</span>';
    }

    const pauseBtn = document.getElementById("pauseBtn");
    if (pauseBtn) {
      pauseBtn.classList.add("hidden");
    }

    if (micLabel) {
      micLabel.textContent = isVietnam ? "Nhấn để Bắt đầu Ghi âm (Tap to Start Recording)" : isArabic ? "اضغط لبدء التسجيل (Tap to Start Recording)" : isRussian ? "Нажмите, чтобы начать запись (Tap to Start Recording)" : "Tap to Start Recording";
      micLabel.classList.remove("on");
    }
    document.getElementById("rr1")?.classList.remove("on");
    document.getElementById("rr2")?.classList.remove("on");
    document.getElementById("statusTxt").textContent = isVietnam ? "Sẵn sàng" : isArabic ? "جاهز" : isRussian ? "Готово" : "Ready";
    document.getElementById("reviewText").textContent = isVietnam ? "Ghi âm hoàn tất. Nhấn Phân tích để tạo phản hồi và các lỗi phát âm. (Recording complete. Click Analyze to generate feedback.)" : isArabic ? "اكتمل التسجيل. اضغط على تحليل لعرض الملاحظات وأخطاء النطق. (Recording complete. Click Analyze to generate feedback.)" : isRussian ? "Запись завершена. Нажмите «Анализ», чтобы получить отзыв и увидеть ошибки произношения. (Recording complete. Click Analyze to generate feedback.)" : "Recording complete. Click Analyze to generate feedback and mistake popups.";
  }

  document.getElementById("pauseBtn")?.addEventListener("click", () => {
    if (!recording) return;
    const pauseBtn = document.getElementById("pauseBtn");
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";

    if (!isPaused) {
      isPaused = true;
      pauses += 1;
      document.getElementById("pauseTxt").textContent = String(pauses);
      if (pauses > 5) {
        resetReading();
        showPauseLimitMessage();
        return;
      }
      document.getElementById("statusTxt").textContent = isVietnam ? "Tạm dừng" : isArabic ? "متوقف مؤقتًا" : isRussian ? "Пауза" : "Paused";
      if (pauseBtn) pauseBtn.textContent = isVietnam ? "Tiếp tục (Resume)" : isArabic ? "استئناف" : isRussian ? "Продолжить" : "Resume";

      if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.pause();
      }
      stopRecognition();
      document.getElementById("rr1")?.classList.remove("on");
      document.getElementById("rr2")?.classList.remove("on");
    } else {
      isPaused = false;
      document.getElementById("statusTxt").textContent = isVietnam ? "Đang ghi âm" : isArabic ? "جارٍ التسجيل" : isRussian ? "Идёт запись" : "Recording";
      if (pauseBtn) pauseBtn.textContent = isVietnam ? "Tạm dừng (Pause)" : isArabic ? "إيقاف مؤقت" : isRussian ? "Пауза" : "Pause";

      if (mediaRecorder && mediaRecorder.state === "paused") {
        mediaRecorder.resume();
      }
      startRecognition();
      document.getElementById("rr1")?.classList.add("on");
      document.getElementById("rr2")?.classList.add("on");
    }
  });

  async function analyzeReading() {
    const reviewElement = document.getElementById("reviewText");
    const analyzeButton = document.getElementById("analyzeBtn");
    const micButton = document.getElementById("micBtn");
    const isVietnam = languageSelect?.value === "vietnam";
    const isRussian = languageSelect?.value === "russian";
    const isArabic = languageSelect?.value === "arabic";

    if (attemptEvaluated) {
      // Belt-and-braces: the buttons are disabled once an attempt is
      // evaluated, but guard the function itself too in case it's ever
      // triggered another way. The server independently rejects a reused
      // attempt token regardless.
      return;
    }

    // Clicking Analyze must stop an in-progress recording immediately,
    // rather than leaving capture running in the background through (and
    // after) analysis. Wait briefly for the audio blob to finish encoding
    // (mediaRecorder.stop() is async) so the transcript/audio actually sent
    // is the complete, just-finished answer.
    if (recording) {
      stopRecordingNow();
    }
    if (isFinalizingAudio) {
      const finalizeDeadline = Date.now() + 1500;
      while (isFinalizingAudio && Date.now() < finalizeDeadline) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }

    const transcript = `${transcriptFinal} ${transcriptInterim}`.trim();

    if (isFinalizingAudio) {
      if (reviewElement) reviewElement.textContent = isVietnam ? "Đang hoàn tất ghi âm. Vui lòng chờ một chút và nhấn Phân tích lại. (Finalizing recording. Please wait.)" : isArabic ? "جارٍ إنهاء التسجيل. يرجى الانتظار قليلاً ثم اضغط على تحليل مرة أخرى. (Finalizing recording. Please wait.)" : isRussian ? "Завершаем запись. Пожалуйста, подождите немного и нажмите «Анализ» ещё раз. (Finalizing recording. Please wait.)" : "Finalizing your recording. Please wait a second and click Analyze again.";
      return;
    }

    if (!lv.hasMeaningfulText(transcript) && !recordedBlob) {
      if (reviewElement) reviewElement.textContent = isVietnam ? "Không tìm thấy nội dung bài đọc. Vui lòng ghi âm bài đọc của bạn, sau đó nhấn Phân tích. (No reading response found.)" : isArabic ? "لم يتم العثور على محتوى للقراءة. يرجى تسجيل قراءتك، ثم اضغط على تحليل. (No reading response found.)" : isRussian ? "Не найден текст для чтения. Пожалуйста, запишите ваше чтение, затем нажмите «Анализ». (No reading response found.)" : "No reading response found. Please record your reading, then click Analyze.";
      return;
    }

    analyzeButton.disabled = true;
    if (analyzeButton) analyzeButton.textContent = isVietnam ? "Đang phân tích... (Analyzing...)" : isArabic ? "جارٍ التحليل... (Analyzing...)" : isRussian ? "Анализируем... (Analyzing...)" : "Analyzing...";
    // Lock recording for the duration of the evaluation too, not just after
    // it succeeds — otherwise a new recording could be started while the
    // previous one is still being analyzed.
    if (micButton) micButton.disabled = true;
    
    // Explicitly hide the feedback card while analyzing so old/default scores don't show
    const fbCard = document.getElementById("fbCard");
    if (fbCard) fbCard.classList.add("hidden");

    const formData = new FormData();
    formData.append("module", "reading");
    formData.append("text", transcript);
    formData.append("client_transcript", transcript);
    formData.append("reference_text", currentPassageText || "");
    formData.append("duration_seconds", String(seconds));
    formData.append("pause_count", String(pauses));
    formData.append("language", languageSelect?.value || "english");
    if (recordedBlob) formData.append("audio", recordedBlob, "reading.webm");

    try {
      const response = await fetch(analyzeEndpoint, {
        method: "POST",
        headers: { "X-CSRFToken": lv.getCsrfToken() },
        body: formData
      });
      const raw = await response.json();

      if (!raw.success) throw new Error("SERVER_ERROR: " + (raw.error || "Analysis failed."));

      const result = lv.unwrapApiData(raw);

      const analyzedText = result.text || currentPassageText || transcript || "";
      const renderResult = lv.renderTextWithIssues(analyzedText, result.issues || [], isVietnam ? "Không có bản dịch để đánh giá. (No transcript to evaluate.)" : isArabic ? "لا يوجد نص لتقييمه. (No transcript to evaluate.)" : isRussian ? "Нет текста для оценки. (No transcript to evaluate.)" : "No transcript to evaluate.");
      if (reviewElement) reviewElement.innerHTML = renderResult.html;
      if (feedbackElement) feedbackElement.innerHTML = result.feedback || highlightBilingual("Bài đọc tuyệt vời. Bạn đang tiến bộ với tốc độ và sự rõ ràng tốt.", defaultFeedbackText, "Отличное чтение. Вы улучшаетесь в темпе и чёткости.", "قراءة ممتازة. أنت تتحسن بوتيرة ووضوح جيدين.");
      if (improvedElement) {
        improvedElement.innerHTML = lv.formatImprovedText(
          result.improved_passage,
          analyzedText,
          highlightBilingual("Bản cải thiện bài đọc sẽ xuất hiện sau khi phân tích.", defaultImprovedText, "Улучшенная версия чтения появится после анализа.", "ستظهر النسخة المحسّنة من قراءتك بعد التحليل.")
        );
      }
      if (quickTipElement) quickTipElement.innerHTML = result.quick_tip || highlightBilingual("Đọc từng dòng và giữ tốc độ ổn định.", defaultQuickTip, "Читайте построчно и сохраняйте стабильный темп.", "اقرأ سطرًا سطرًا وحافظ على وتيرة ثابتة.");
      // Prefer the server-graded, saved score so the score shown here
      // matches the value stored for this reading attempt.
      // Check both API response shapes, then fall back to the local score
      // calculation when the backend did not return a saved score.
      const scoreValue =
        typeof raw?.score_25 === "number"
          ? raw.score_25
          : typeof result?.score_25 === "number"
            ? result.score_25
            : lv.computeReadingScore(renderResult.count, pauses || 0);

      if (lessonScore) lessonScore.textContent = `${scoreValue}/25`;
      lv.saveModuleScore("Reading", { score: scoreValue });

      const prevScoreVal = document.getElementById("prevScoreVal");
      if (prevScoreVal) {
        prevScoreVal.textContent = scoreValue;
        const prevScoreDate = document.getElementById("prevScoreDate");
        if (prevScoreDate) prevScoreDate.textContent = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      }

      const fbCard = document.getElementById("fbCard");
      if (fbCard) fbCard.classList.remove("hidden");


      // This attempt has now been evaluated and saved server-side. Lock
      // recording and analysis so this exact attempt can't be re-submitted
      // (with a different or copied answer) without an actual restart —
      // switching level or picking "New passage" (see resetReading())
      // re-enables both for a genuinely new attempt. Return here instead of
      // falling through to the re-enable below, which only runs on the
      // error path (so a genuine failure can still be retried).
      attemptEvaluated = true;
      analyzeButton.disabled = true;
      analyzeButton.innerHTML = isVietnam ? "Đã nộp bài (Already Submitted)" : isArabic ? "تم الإرسال بالفعل (Already Submitted)" : isRussian ? "Уже отправлено (Already Submitted)" : "Already Submitted";
      if (micButton) micButton.disabled = true;
      return;
    } catch (error) {
      const errMsg = error.message || "";
      if (errMsg.startsWith("SERVER_ERROR:")) {
        const realMsg = errMsg.replace("SERVER_ERROR:", "").trim();
        if (reviewElement) reviewElement.textContent = realMsg;
        if (feedbackElement) feedbackElement.textContent = "Analysis stopped. Please try again.";
        document.getElementById("fbCard").classList.remove("hidden");
        return;
      }

      const fallbackText = transcript || currentPassageText || "";
      if (lv.hasMeaningfulText(fallbackText, 3, 10)) {
        const renderResult = lv.renderTextWithIssues(fallbackText, [], "No transcript to evaluate.");
        if (reviewElement) reviewElement.innerHTML = renderResult.html;
        if (feedbackElement) {
          feedbackElement.textContent = isVietnam ? "Sử dụng bản đánh giá dự phòng vì dịch vụ phân tích không thể hoàn tất. (Using fallback review.)" : isArabic ? "يتم استخدام مراجعة احتياطية لأن خدمة التحليل لم تتمكن من الاكتمال. (Using fallback review.)" : isRussian ? "Используется резервная проверка, так как сервис анализа не смог завершить работу. (Using fallback review.)" : "Using fallback review because the analysis service could not complete.";
        }
        if (improvedElement) {
          improvedElement.textContent = lv.formatImprovedText("", fallbackText, defaultImprovedText);
        }
        if (quickTipElement) quickTipElement.textContent = defaultQuickTip;
        const fallbackScore = lv.computeReadingScore(0, pauses || 0);
        if (lessonScore) lessonScore.textContent = `${fallbackScore}/25`;
        lv.saveModuleScore("Reading", { score: fallbackScore });
        document.getElementById("fbCard").classList.remove("hidden");
        setTimeout(() => document.getElementById("fbCard").scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
      } else {
        if (reviewElement) reviewElement.textContent = error.message || "Could not analyze reading response.";
      }
    }
    // Only reached on error (the success path returns early above) — the
    // real evaluation never completed, so let the learner genuinely retry.
    analyzeButton.disabled = false;
    if (analyzeButton) analyzeButton.innerHTML = isVietnam ? "Gửi để Phân tích (Submit for Analysis)" : isArabic ? "إرسال للتحليل (Submit for Analysis)" : isRussian ? "Отправить на анализ (Submit for Analysis)" : "Analyze";
    if (micButton) micButton.disabled = false;
  }

  document.getElementById("analyzeBtn")?.addEventListener("click", analyzeReading);
  document.getElementById("tryAgainBtn")?.addEventListener("click", () => {
    resetReading();
    renderPassage();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // "Try Again" had no handler at all, so clicking it did nothing. Reuse
  // resetReading() — the same reset the level-switch/"New passage" buttons
  // use — but deliberately do NOT touch currentPassage/currentLevel or call
  // renderPassage(), so the same topic/passage stays on screen. This clears
  // the previous recording, transcript, score and feedback (attemptEvaluated
  // included) so the next Analyze click evaluates only the new attempt.
  document.getElementById("tryAgainBtn")?.addEventListener("click", resetReading);

  refillPassagePool(currentLevel, currentPassage);
  lv.restoreLanguagePreference("languageSelect", updateUILanguage);
  renderPassage();
})();

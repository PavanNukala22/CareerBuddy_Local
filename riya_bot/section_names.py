"""Buddy text in every chatbot language — one source for backend and frontend.

SECTION_NAMES: what each navigation target is called, phrased to fit the
"Opening X" frames below (Russian is in the accusative: "Открываю X").
The frontend receives the same data through the chatbot partial
(templates/includes/aria_assistant.html, json_script), so the two sides
cannot drift apart.
"""

LANGS = ("vietnamese", "hindi", "arabic", "russian")

SECTION_NAMES = {
    "home": {"vietnamese": "trang chủ", "hindi": "होम पेज", "arabic": "الصفحة الرئيسية", "russian": "главную страницу"},
    "lessons": {"vietnamese": "trang hoạt động", "hindi": "एक्टिविटी पेज", "arabic": "صفحة الأنشطة", "russian": "страницу занятий"},
    "professional_speaking": {"vietnamese": "Nói và Thuyết trình", "hindi": "स्पीकिंग और प्रेज़ेंटेशन", "arabic": "التحدث والعرض", "russian": "раздел «Речь и презентации»"},
    "passage_writing": {"vietnamese": "Viết và Thư tín", "hindi": "राइटिंग और कॉरेस्पॉन्डेंस", "arabic": "الكتابة والمراسلات", "russian": "раздел «Письмо и переписка»"},
    "vocabulary": {"vietnamese": "Từ vựng và Thành ngữ", "hindi": "वोकैबुलरी और इडियम्स", "arabic": "المفردات والتعابير", "russian": "раздел «Лексика и идиомы»"},
    "negotiation": {"vietnamese": "Đàm phán và Cuộc họp", "hindi": "नेगोशिएशन और मीटिंग्स", "arabic": "التفاوض والاجتماعات", "russian": "раздел «Переговоры и встречи»"},
    "communication": {"vietnamese": "Giao tiếp chuyên nghiệp", "hindi": "प्रोफेशनल कम्युनिकेशन", "arabic": "التواصل المهني", "russian": "раздел «Профессиональное общение»"},
    "analysis": {"vietnamese": "Phân tích và Báo cáo", "hindi": "एनालिसिस और रिपोर्टिंग", "arabic": "التحليل وإعداد التقارير", "russian": "раздел «Анализ и отчётность»"},
    "listen_learn": {"vietnamese": "Nghe và Học", "hindi": "लिसन एंड लर्न", "arabic": "استمع وتعلّم", "russian": "раздел «Слушай и учись»"},
    "profile": {"vietnamese": "bảng điều khiển của bạn", "hindi": "आपका डैशबोर्ड", "arabic": "لوحة التحكم الخاصة بك", "russian": "вашу панель управления"},
    "job_recommendations": {"vietnamese": "việc làm được đề xuất cho bạn", "hindi": "आपकी जॉब रिकमेंडेशंस", "arabic": "الوظائف الموصى بها لك", "russian": "ваши рекомендованные вакансии"},
    "company_profile": {"vietnamese": "hồ sơ công ty của bạn", "hindi": "आपकी कंपनी प्रोफ़ाइल", "arabic": "ملف شركتك", "russian": "профиль вашей компании"},
    "find_candidates": {"vietnamese": "trang tìm kiếm ứng viên", "hindi": "कैंडिडेट सर्च पेज", "arabic": "صفحة البحث عن المرشحين", "russian": "страницу поиска кандидатов"},
    "post_job": {"vietnamese": "trang đăng việc làm mới", "hindi": "नई जॉब पोस्ट करने का पेज", "arabic": "صفحة نشر وظيفة جديدة", "russian": "страницу публикации вакансии"},
    "all_applications": {"vietnamese": "trang tất cả đơn ứng tuyển", "hindi": "सभी आवेदनों का पेज", "arabic": "صفحة جميع الطلبات", "russian": "страницу всех откликов"},
    "job_openings": {"vietnamese": "trang tin tuyển dụng", "hindi": "जॉब ओपनिंग्स पेज", "arabic": "صفحة الوظائف الشاغرة", "russian": "страницу вакансий"},
    "login_job_seeker": {"vietnamese": "trang đăng nhập người tìm việc", "hindi": "जॉब सीकर लॉगिन पेज", "arabic": "صفحة تسجيل دخول الباحث عن عمل", "russian": "страницу входа для соискателя"},
    "register_job_seeker": {"vietnamese": "trang đăng ký người tìm việc", "hindi": "जॉब सीकर रजिस्ट्रेशन पेज", "arabic": "صفحة تسجيل الباحث عن عمل", "russian": "страницу регистрации соискателя"},
    "login_employer": {"vietnamese": "cổng nhà tuyển dụng", "hindi": "एम्प्लॉयर पोर्टल", "arabic": "بوابة صاحب العمل", "russian": "портал работодателя"},
    "register_employer": {"vietnamese": "trang đăng ký nhà tuyển dụng", "hindi": "एम्प्लॉयर रजिस्ट्रेशन पेज", "arabic": "صفحة تسجيل صاحب العمل", "russian": "страницу регистрации работодателя"},
    "employer_login": {"vietnamese": "cổng nhà tuyển dụng", "hindi": "एम्प्लॉयर पोर्टल", "arabic": "بوابة صاحب العمل", "russian": "портал работодателя"},
    "student_login": {"vietnamese": "trang đăng nhập người tìm việc", "hindi": "जॉब सीकर लॉगिन पेज", "arabic": "صفحة تسجيل دخول الباحث عن عمل", "russian": "страницу входа для соискателя"},
    "english_vocab": {"vietnamese": "phần Tiếng Anh và Từ vựng", "hindi": "इंग्लिश और वोकैबुलरी सेक्शन", "arabic": "قسم الإنجليزية والمفردات", "russian": "раздел «Английский и лексика»"},
    "aptitude": {"vietnamese": "phần Năng lực", "hindi": "एप्टीट्यूड सेक्शन", "arabic": "قسم القدرات", "russian": "раздел «Способности»"},
    "tech": {"vietnamese": "phần Công nghệ", "hindi": "टेक सेक्शन", "arabic": "قسم التقنية", "russian": "технический раздел"},
    "sitemap": {"vietnamese": "sơ đồ trang", "hindi": "साइटमैप", "arabic": "خريطة الموقع", "russian": "карту сайта"},
    "browse_all": {"vietnamese": "danh sách tất cả tài liệu", "hindi": "सभी एक्टिविटीज़ की सूची", "arabic": "قائمة جميع الأنشطة", "russian": "список всех материалов"},
    "grammar": {"vietnamese": "phần Ngữ pháp", "hindi": "ग्रामर सेक्शन", "arabic": "قسم القواعد", "russian": "раздел грамматики"},
    "grammar_noun": {"vietnamese": "bài Danh từ", "hindi": "संज्ञा (Nouns) मॉड्यूल", "arabic": "وحدة الأسماء", "russian": "модуль «Существительные»"},
    "grammar_pronoun": {"vietnamese": "bài Đại từ", "hindi": "सर्वनाम (Pronouns) मॉड्यूल", "arabic": "وحدة الضمائر", "russian": "модуль «Местоимения»"},
    "grammar_verb": {"vietnamese": "bài Động từ", "hindi": "क्रिया (Verbs) मॉड्यूल", "arabic": "وحدة الأفعال", "russian": "модуль «Глаголы»"},
    "grammar_adjective": {"vietnamese": "bài Tính từ", "hindi": "विशेषण (Adjectives) मॉड्यूल", "arabic": "وحدة الصفات", "russian": "модуль «Прилагательные»"},
    "grammar_adverb": {"vietnamese": "bài Trạng từ", "hindi": "क्रिया विशेषण (Adverbs) मॉड्यूल", "arabic": "وحدة الظروف", "russian": "модуль «Наречия»"},
    "grammar_conjunction": {"vietnamese": "bài Liên từ", "hindi": "समुच्चयबोधक (Conjunctions) मॉड्यूल", "arabic": "وحدة أدوات الربط", "russian": "модуль «Союзы»"},
    "grammar_tenses": {"vietnamese": "bài Các thì", "hindi": "टेंस मॉड्यूल", "arabic": "وحدة الأزمنة", "russian": "модуль «Времена»"},
    "grammar_sentence_structure": {"vietnamese": "bài Cấu trúc câu", "hindi": "सेंटेंस स्ट्रक्चर मॉड्यूल", "arabic": "وحدة بناء الجملة", "russian": "модуль «Структура предложения»"},
    "grammar_types_of_sentences": {"vietnamese": "bài Các loại câu", "hindi": "वाक्यों के प्रकार मॉड्यूल", "arabic": "وحدة أنواع الجمل", "russian": "модуль «Типы предложений»"},
    "workshop": {"vietnamese": "hoạt động Workshop tương tác", "hindi": "इंटरैक्टिव वर्कशॉप", "arabic": "ورش العمل التفاعلية", "russian": "интерактивные воркшопы"},
    "roleplay": {"vietnamese": "luyện tập Nhập vai", "hindi": "रोल प्ले प्रैक्टिस", "arabic": "تدريب لعب الأدوار", "russian": "ролевую практику"},
    "storytelling_practice": {"vietnamese": "luyện kể chuyện", "hindi": "स्टोरीटेलिंग प्रैक्टिस", "arabic": "تدريب سرد القصص", "russian": "практику рассказа историй"},
    "situation_practice": {"vietnamese": "bài luyện tình huống", "hindi": "सिचुएशन प्रैक्टिस", "arabic": "تمرين المواقف", "russian": "практику ситуаций"},
    "gd": {"vietnamese": "Thảo luận nhóm", "hindi": "ग्रुप डिस्कशन", "arabic": "النقاش الجماعي", "russian": "групповую дискуссию"},
    "jam": {"vietnamese": "luyện JAM", "hindi": "JAM प्रैक्टिस", "arabic": "تدريب JAM", "russian": "практику JAM"},
    "resume_builder": {"vietnamese": "Resume Builder", "hindi": "Resume Builder", "arabic": "Resume Builder", "russian": "Resume Builder"},
    "certifications": {"vietnamese": "chứng chỉ của bạn", "hindi": "आपके सर्टिफिकेशन", "arabic": "شهاداتك", "russian": "ваши сертификаты"},
    "pro": {"vietnamese": "các gói thành viên", "hindi": "मेंबरशिप प्लान्स", "arabic": "خطط العضوية", "russian": "тарифы подписки"},
    "mock_interview": {"vietnamese": "phỏng vấn thử với AI", "hindi": "AI मॉक इंटरव्यू", "arabic": "المقابلة التجريبية بالذكاء الاصطناعي", "russian": "пробное AI-собеседование"},
    "job_search": {"vietnamese": "tìm kiếm việc làm", "hindi": "जॉब सर्च", "arabic": "البحث عن وظائف", "russian": "поиск работы"},
    "about_app": {"vietnamese": "giới thiệu ứng dụng", "hindi": "ऐप के बारे में", "arabic": "حول التطبيق", "russian": "раздел «О приложении»"},
}

_OPENING = {
    "english": "Opening {}.",
    "hindi": "{} खोल रहा हूँ।",
    "vietnamese": "Đang mở {}.",
    "arabic": "جارٍ فتح {}.",
    "russian": "Открываю {}.",
}

# "Inside you'll find X, Y and Z..." after an informational nav reply.
GUIDANCE = {
    "english": "Inside you'll find {}. Tell me which one you'd like and I'll take you straight there.",
    "hindi": "अंदर आपको {} मिलेंगे। बताइए कौन-सा खोलूँ, मैं सीधे वहीं ले चलता हूँ।",
    "vietnamese": "Bên trong có {}. Hãy cho tôi biết bạn muốn phần nào, tôi sẽ mở ngay.",
    "arabic": "في الداخل ستجد {}. أخبرني أيها تريد وسأنقلك إليه مباشرة.",
    "russian": "Внутри вы найдёте {}. Скажите, что открыть, и я сразу вас туда переведу.",
}
_AND = {"english": "and", "hindi": "और", "vietnamese": "và", "arabic": "و", "russian": "и"}

# Gate / upsell replies that used to be English in every language.
MESSAGES = {
    "upgrade_feature": {
        "english": "🔒 This feature is available in a higher plan. Please Upgrade to avail this Feature.",
        "hindi": "इस फ़ीचर का इस्तेमाल करने के लिए कृपया अपना प्लान अपग्रेड करें।",
        "vietnamese": "Vui lòng nâng cấp gói để sử dụng tính năng này.",
        "arabic": "يرجى ترقية خطتك للاستفادة من هذه الميزة.",
        "russian": "Пожалуйста, обновите тариф, чтобы пользоваться этой функцией.",
    },
    "upgrade_activity": {
        "english": "🔒 This feature is available in a higher plan. Please Upgrade to avail this Feature.",
        "hindi": "यह एक्टिविटी खोलने के लिए कृपया अपना प्लान अपग्रेड करें।",
        "vietnamese": "Vui lòng nâng cấp gói để mở hoạt động này.",
        "arabic": "يرجى ترقية خطتك لفتح هذا النشاط.",
        "russian": "Пожалуйста, обновите тариф, чтобы открыть это занятие.",
    },
    "parse_resume_first": {
        "english": "Please parse your resume first. Once your resume is successfully parsed, you can take the AI Mock Interview.",
        "hindi": "कृपया पहले अपना रिज़्यूमे पार्स करें। रिज़्यूमे पार्स होने के बाद आप AI मॉक इंटरव्यू दे सकते हैं।",
        "vietnamese": "Vui lòng phân tích CV của bạn trước. Sau khi CV được phân tích thành công, bạn có thể tham gia phỏng vấn thử với AI.",
        "arabic": "يرجى تحليل سيرتك الذاتية أولًا. بعد تحليلها بنجاح، يمكنك إجراء المقابلة التجريبية بالذكاء الاصطناعي.",
        "russian": "Сначала загрузите и разберите резюме. После успешного разбора вы сможете пройти пробное AI-собеседование.",
    },
    "score_for_job_search": {
        "english": "Please score >70 in your AI Mock Interview to unlock Job Search.",
        "hindi": "जॉब सर्च अनलॉक करने के लिए AI मॉक इंटरव्यू में 70 से ज़्यादा स्कोर करें।",
        "vietnamese": "Hãy đạt trên 70 điểm trong buổi phỏng vấn thử với AI để mở khóa tìm kiếm việc làm.",
        "arabic": "احصل على أكثر من 70 في المقابلة التجريبية بالذكاء الاصطناعي لفتح البحث عن وظائف.",
        "russian": "Наберите больше 70 баллов на пробном AI-собеседовании, чтобы открыть поиск работы.",
    },
}


def _lang(language):
    value = (language or "english").strip().lower()
    return "vietnamese" if value == "vietnam" else value


def section_name(key, language, fallback=""):
    """Translated name of a navigation target, or ``fallback`` (the English label)."""
    return SECTION_NAMES.get(key, {}).get(_lang(language)) or fallback


def opening(name, language):
    lang = _lang(language)
    return _OPENING.get(lang, _OPENING["english"]).format(name)


def guidance(names, language):
    lang = _lang(language)
    conj = _AND.get(lang, "and")
    listed = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {conj} {names[-1]}"
    return GUIDANCE.get(lang, GUIDANCE["english"]).format(listed)


def message(key, language):
    table = MESSAGES[key]
    return table.get(_lang(language)) or table["english"]

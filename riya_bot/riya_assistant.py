import json
import re
import unicodedata
from urllib.parse import quote
from typing import Any
from django.conf import settings

# Skill Up extension (additive — returns None for non-Skill-Up messages)
from .skillup_intents import (
    SKILL_UP_PROMPT_RULES,
    try_handle as skillup_try_handle,
)

import requests

from .section_names import guidance, opening, section_name
from .section_names import message as message_text


SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
INTENT_STOP_WORDS = {
    "activity",
    "activities",
    "page",
    "module",
    "practice",
    "open",
    "go",
    "to",
    "start",
    "show",
    "take",
    "me",
}



SUPPORTED_LANGUAGES = {
    "english": {"name": "English", "code": "en-IN"},
    "hindi": {"name": "Hindi", "code": "hi-IN"},
    "vietnam": {"name": "Vietnamese", "code": "vi-VN"},
    "vietnamese": {"name": "Vietnamese", "code": "vi-VN"},
    "arabic": {"name": "Arabic", "code": "ar-SA"},
    "russian": {"name": "Russian", "code": "ru-RU"},
    "telugu": {"name": "Telugu", "code": "te-IN"},
    "tamil": {"name": "Tamil", "code": "ta-IN"},
}
LANGUAGE_ALIASES = {
    "en": "english", "en-us": "english", "en-gb": "english", "en-in": "english",
    "hi": "hindi", "hi-in": "hindi", "हिंदी": "hindi",
    "vi": "vietnamese", "vi-vn": "vietnamese",
    "ar": "arabic", "ar-sa": "arabic", "العربية": "arabic",
    "ru": "russian", "ru-ru": "russian", "русский": "russian",
    "te": "telugu", "te-in": "telugu", "తెలుగు": "telugu",
    "ta": "tamil", "ta-in": "tamil", "தமிழ்": "tamil",
}
def normalize_language(language: str | None, message: str = "") -> str:
    value = (language or "").strip().lower().replace("_", "-")
    value = LANGUAGE_ALIASES.get(value, value)
    if value in SUPPORTED_LANGUAGES:
        return "vietnamese" if value == "vietnam" else value
    text = (message or "")
    if re.search(r"[\u0900-\u097F]", text): return "hindi"
    if re.search(r"[\u0C00-\u0C7F]", text): return "telugu"
    if re.search(r"[\u0B80-\u0BFF]", text): return "tamil"
    if re.search(r"[\u0600-\u06FF]", text): return "arabic"
    if re.search(r"[\u0400-\u04FF]", text): return "russian"
    return "english"

LANGUAGE_REPLY_TRANSLATIONS = {
    "english": {"unknown": "That feature is not available in this application.", "unknown_command": "I couldn't find that feature in this application."},
    "hindi": {"unknown": "यह फीचर इस एप्लिकेशन में उपलब्ध नहीं है।", "unknown_command": "मुझे इस एप्लिकेशन में यह फीचर नहीं मिला।"},
    "vietnamese": {"unknown": "Tính năng này không có trong ứng dụng hiện tại.", "unknown_command": "Tôi không tìm thấy tính năng này trong ứng dụng hiện tại."},
    "arabic": {"unknown": "هذه الميزة غير متوفرة في التطبيق الحالي.", "unknown_command": "لم أجد هذه الميزة في التطبيق الحالي."},
    "russian": {"unknown": "Эта функция недоступна в текущем приложении.", "unknown_command": "Я не нашёл эту функцию в текущем приложении."},
    "telugu": {"unknown": "ఈ ఫీచర్ ప్రస్తుతం ఈ అప్లికేషన్‌లో అందుబాటులో లేదు.", "unknown_command": "ఈ ఫీచర్ ఈ అప్లికేషన్‌లో కనిపించలేదు."},
    "tamil": {"unknown": "இந்த அம்சம் தற்போது இந்த பயன்பாட்டில் கிடைக்கவில்லை.", "unknown_command": "இந்த அம்சம் இந்த பயன்பாட்டில் கிடைக்கவில்லை."},
}

ACTION_DEFINITIONS = {
    "home": {
        "label": "Home",
        "route": "/",
        "response": "Opening home.",
        "keywords": ["home", "home page", "landing page", "main page"],
    },
    "lessons": {
        "label": "Go to Activities",
        "route": "/activities/",
        "response": "Opening the activities page.",
        "keywords": ["practice", "practice page", "lesson", "lessons", "activities", "activities page", "activity list", "all activities"],
    },
    "professional_speaking": {
        "label": "Speaking & Presentation",
        "route": "/activities/?category=speaking",
        "response": "Opening Speaking & Presentation.",
        "keywords": ["speaking and presentation", "speaking module", "speaking page", "speaking activity", "speaking practice", "open speaking", "go to speaking", "start speaking", "show speaking"],
    },
    "passage_writing": {
        "label": "Writing and Correspondence",
        "route": "/activities/?category=writing",
        "response": "Opening Writing and Correspondence.",
        "keywords": ["writing", "correspondence", "writing and correspondence", "writing module", "writing page", "writing activity", "writing practice", "open writing", "go to writing", "start writing", "show writing"],
    },
    "vocabulary": {
        "label": "Vocabulary & Idioms",
        "route": "/activities/?category=vocabulary",
        "response": "Opening Vocabulary & Idioms.",
        "keywords": ["vocabulary and idioms", "vocabulary", "idioms", "vocabulary module", "idioms module", "open vocabulary"],
    },
    "negotiation": {
        "label": "Negotiation & Meetings",
        "route": "/activities/?category=negotiation",
        "response": "Opening Negotiation & Meetings.",
        "keywords": ["negotiation and meetings", "negotiation", "meetings", "negotiation module", "meetings module", "open negotiation"],
    },
    "communication": {
        "label": "Professional Communication",
        "route": "/activities/?category=communication",
        "response": "Opening Professional Communication.",
        "keywords": ["professional communication", "communication", "communication module", "open communication"],
    },
    "analysis": {
        "label": "Analysis & Reporting",
        "route": "/activities/?category=analysis",
        "response": "Opening Analysis & Reporting.",
        "keywords": ["analysis and reporting", "analysis", "reporting", "analysis module", "open analysis"],
    },
    "listen_learn": {
        "label": "Listen & Learn",
        "route": "/activities/?category=listening",
        "response": "Opening Listen & Learn.",
        "keywords": ["listen and learn", "listen & learn", "listening", "listening module",
                     "listening activity", "listening practice", "listening exercise",
                     "audio practice", "open listening", "go to listening", "start listening"],
    },
    "profile": {
        "label": "View Dashboard",
        "route": "/dashboard/",
        "response": "Opening your dashboard.",
        "keywords": ["profile", "my profile", "dashboard", "account", "progress", "student dashboard"],
    },
    # Lands ON the matched-jobs card rather than the top of the dashboard — the
    # anchor and its scroll-margin live in templates/dashboard.html.
    "job_recommendations": {
        "label": "Job Recommendations",
        "route": "/dashboard/#recommended-jobs",
        "response": "Opening your job recommendations.",
        "keywords": [
            "job recommendations", "recommended jobs", "job recommendation",
            "matched jobs", "job matches", "jobs for me", "recommended opportunities",
            "matching opportunities", "my job matches",
        ],
    },
    "company_profile": {
        "label": "Company Profile",
        "route": "/employer/employer/profile/edit/",
        "response": "Opening your company profile.",
        "keywords": ["company profile", "employer profile", "business profile", "update profile", "my profile"],
        "description": "Manage your company details — name, logo, industry and description — shown to candidates.",
        "translations": {
            "hindi": "खोल रहा हूँ आपकी कंपनी प्रोफ़ाइल।",
            "vietnamese": "Đang mở hồ sơ công ty của bạn.",
            "arabic": "جارٍ فتح ملف تعريف شركتك.",
            "russian": "Открываю профиль вашей компании.",
        }
    },
    "find_candidates": {
        "label": "Find Candidates",
        "route": "/employer/employer/candidates/search/",
        "response": "Opening the candidate search page.",
        "keywords": ["find candidates", "search candidates", "candidate search", "find candidate", "search candidate", "browse candidates"],
        "description": "Search and filter the candidate resume pool ranked by relevance to your roles.",
        "translations": {
            "hindi": "खोल रहा हूँ उम्मीदवार खोज पृष्ठ।",
            "vietnamese": "Đang mở trang tìm kiếm ứng viên.",
            "arabic": "جارٍ فتح صفحة البحث عن مرشحين.",
            "russian": "Открываю страницу поиска кандидатов.",
        }
    },
    "post_job": {
        "label": "Post New Job",
        "route": "/employer/employer/jobs/new/",
        "response": "Opening the post new job page.",
        "keywords": ["post new job", "post job", "create job", "new job", "add job"],
        "description": "Create a new job posting with title, description, skills and experience.",
        "translations": {
            "hindi": "खोल रहा हूँ नया जॉब पोस्ट पृष्ठ।",
            "vietnamese": "Đang mở trang đăng việc làm mới.",
            "arabic": "جارٍ فتح صفحة نشر وظيفة جديدة.",
            "russian": "Открываю страницу публикации новой вакансии.",
        }
    },
    "all_applications": {
        "label": "All Applications",
        "route": "/employer/employer/applications/",
        "response": "Opening the all applications page.",
        "keywords": ["all applications", "applications", "view applications", "job applications"],
        "description": "Review every candidate application across your jobs and track status.",
        "translations": {
            "hindi": "खोल रहा हूँ सभी आवेदन पृष्ठ।",
            "vietnamese": "Đang mở trang tất cả hồ sơ ứng tuyển.",
            "arabic": "جارٍ فتح صفحة جميع الطلبات.",
            "russian": "Открываю страницу всех заявок.",
        }
    },
    "job_openings": {
        "label": "Job Openings",
        "route": "/employer/employer/job-openings/",
        "response": "Opening the job openings page.",
        "keywords": ["job openings", "openings", "view job openings", "view openings", "my jobs", "posted jobs"],
        "description": "See and manage all the jobs you have posted, open or closed.",
        "translations": {
            "hindi": "खोल रहा हूँ जॉब ओपनिंग पृष्ठ।",
            "vietnamese": "Đang mở trang các vị trí đang mở.",
            "arabic": "جارٍ فتح صفحة الوظائف الشاغرة.",
            "russian": "Открываю страницу открытых вакансий.",
        }
    },
    "login_job_seeker": {
        "label": "Job Seeker Sign-In",
        "route": "/users/login/",
        "response": "Taking you to the job seeker sign-in page.",
        "keywords": [
    "job seeker",
    "jobseeker",
    "job seeker login",
    "job seeker sign in",
    "candidate login",
    "student login",
    "student sign in",
    "login as job seeker",
    "sign in as job seeker"
],
    },
    "register_job_seeker": {
        "label": "Job Seeker Registration",
        "route": "/users/register/",
        "response": "Taking you to the job seeker registration page.",
        "keywords": ["register job seeker", "job seeker registration", "student registration", "employee registration", "sign up as job seeker", "candidate registration", "register candidate"],
    },
    "login_employer": {
        "label": "Employer Login",
        "route": "/employer/accounts/employer/login/",
        "response": "Taking you to the employer portal.",
        "keywords": [
    "employer",
    "employer login",
    "employer sign in",
    "recruiter login",
    "recruiter sign in",
    "company login",
    "login as employer",
    "sign in as employer"
],
    },
    "register_employer": {
        "label": "Employer Registration",
        "route": "/employer/accounts/employer/register/",
        "response": "Taking you to the employer registration page.",
        "keywords": ["register employer", "employer registration", "company registration", "sign up as employer", "recruiter registration"],
    },
    "english_vocab": {
        "label": "English & Vocab",
        "route": "/skill-up/#depth-english",
        "response": "Taking you to the English & Vocab section.",
        "keywords": ["english and vocab", "english & vocab", "vocabulary", "vocab", "english"],
    },
    "aptitude": {
        "label": "Aptitude",
        "route": "/skill-up/#depth-aptitude",
        "response": "Taking you to the Aptitude section.",
        "keywords": ["aptitude", "quantitative aptitude", "aptitude module", "reasoning"],
    },
    "tech": {
        "label": "Tech",
        "route": "/skill-up/#depth-tech",
        "response": "Taking you to the Tech section.",
        "keywords": ["tech", "technical", "technology", "tech module", "programming"],
    },
    "sitemap": {
        "label": "Sitemap",
        "route": "/skill-up/#section-sitemap",
        "response": "Taking you to the Sitemap.",
        "keywords": ["sitemap", "site map"],
    },
    "contact_us": {
        "label": "Contact Us",
        "route": "/#contact",
        "response": "Taking you to Contact Us.",
        "keywords": ["contact us", "contact", "support", "help desk"],
    },
    "resources": {
        "label": "Resources",
        "route": "/skill-up/#section-depth",
        "response": "Opening Resources.",
        "keywords": ["resources", "resource", "resource materials"],
    },
    "industries": {
        "label": "Industries",
        "route": "/skill-up/#section-depth",
        "response": "Opening Industries.",
        "keywords": ["industries", "industry", "sectors"],
    },
    "browse_all": {
        "label": "Browse all",
        "route": "/skill-up/#section-depth",
        "response": "Taking you to browse all activities.",
        "keywords": ["browse all", "browse all activities", "explore all"],
    },
    "grammar": {
        "label": "Grammar",
        "route": "/subject/",
        "response": "Opening the grammar section.",
        "keywords": ["grammar", "grammer", "english grammar", "parts of speech", "grammar page", "grammar module", "grammer module"],
        "description": "Grammar lessons with slides, video and examples — parts of speech, tenses, sentence structure.",
    },
    "workshop": {
        "label": "Interactive Workshop",
        "route": "/activities/?category=workshop",
        "response": "Opening Interactive Workshop activities.",
        "keywords": [
            "interactive workshop", "workshop", "workshops",
        ],
    },
    "roleplay": {
        "label": "Roleplay",
        "route": "/roleplay/",
        "response": "Opening roleplay practice.",
        "keywords": ["roleplay", "role play", "conversation roleplay", "roleplay practice", "storytelling", "situations"],
        "description": "Scenario-based conversation practice with AI feedback.",
    },
    "gd": {
        "label": "Group Discussion",
        "route": "/gd/",
        "response": "Opening group discussion.",
        "keywords": ["group discussion", "gd", "gd module", "discussion", "go to gd", "open gd"],
        "description": "Live AI group-discussion practice — debate a topic and get scored.",
    },
    "jam": {
        "label": "JAM",
        "route": "/jam/",
        "response": "Opening JAM practice.",
        "keywords": ["jam", "just a minute", "jam module", "jam practice", "go to jam", "open jam"],
        "description": "Just A Minute — speak on a topic for 60 seconds without pause, repetition or deviation.",
    },
    "resume_builder": {
        "label": "Resume Builder",
        "route": "/resume-builder/",
        "response": "Opening resume builder.",
        "keywords": ["job match", "resume builder", "resume parsing", "resume parser", "resume match", "upload resume", "career", "ats"],
        "description": "Upload your resume for an ATS score, skills analysis and job matching.",
    },
    "certifications": {
        "label": "Certifications",
        "route": "/skill-up/#section-certifications",
        "response": "Opening your certifications.",
        "keywords": ["certifications", "certification", "certificate", "certificates", "my certificates", "my certification", "open certifications", "skill up certification", "skill up certificate"],
    },
    "pro": {
        "label": "Membership",
        "route": "/pro/",
        "response": "Opening membership plans.",
        "keywords": ["pro", "membership", "plans", "upgrade", "subscription", "normal user", "pro user"],
    },
    "mock_interview": {
        "label": "AI Mock Interview",
        "route": "/resume-builder/",
        "response": "Taking you to the Resume Builder for your AI Mock Interview.",
        "keywords": ["mock interview", "ai mock interview", "ai interview", "mock ai interview"],
        "description": "Proctored AI interview tailored to your resume, scored out of 100.",
    },
    "job_search": {
        "label": "Job Search",
        "route": "/resume-builder/analytics/",
        "response": "Opening Job Recommendations.",
        # "job recommendations"/"matched jobs" belong to the job_recommendations
        # action, which lands on the dashboard card of that name. Leaving them
        # here sent the user to resume analytics instead.
        "keywords": ["job search", "search jobs", "find jobs", "looking for jobs", "jobs", "searching jobs", "find a job", "job opportunities"],
        "description": "Experience-matched job recommendations to apply to after you pass the mock interview.",
    },
    "about_app": {
        "label": "About Application",
        "route": "",
        "response": "Career Buddy is an AI-powered platform designed to enhance your professional skills. We offer features like Grammar, Vocabulary, Professional Speaking, Writing & Correspondence, Group Discussions, Resume Building, Mock Interviews, and Job Search. Let me know which area you'd like to explore!",
        "keywords": ["what is this app", "features", "about the application", "what is this app for", "what does this app do", "app features", "what can you do", "help"],
    },
}

# Append non-English single-word translations to allow exact-matching navigation
_LOCALIZED_EXTENSIONS = {
    "Home": ["होम पेज", "होम", "الصفحة الرئيسية", "الرئيسية", "главную страницу", "trang chủ", "chủ"],
    "Go to Activities": ["एक्टिविटी पेज", "एक्टिविटी", "صفحة الأنشطة", "الأنشطة", "страницу занятий", "занятий", "trang hoạt động", "hoạt động"],
    "Speaking & Presentation": ["प्रोफेशनल स्पीकिंग", "التحدث المهني", "профессиональную речь", "luyện nói chuyên nghiệp"],
    "Writing and Correspondence": ["राइटिंग और कॉरेस्पॉन्डेंस", "الكتابة والمراسلات", "письмо и деловую переписку", "viết và giao tiếp thư từ"],
    "Vocabulary & Idioms": ["वोकैबुलरी और इडियम्स", "المفردات والتعابير", "лексику и идиомы", "từ vựng và thành ngữ"],
    "Negotiation & Meetings": ["नेगोशिएशन और मीटिंग्स", "التفاوض والاجتماعات", "переговоры и встречи", "đàm phán và cuộc họp"],
    "Professional Communication": ["प्रोफेशनल कम्युनिकेशन", "التواصل المهني", "профессиональное общение", "giao tiếp chuyên nghiệp"],
    "Analysis & Reporting": ["एनालिसिस और रिपोर्टिंग", "التحليل وإعداد التقارير", "анализ и отчётность", "phân tích và báo cáo"],
    "View Dashboard": ["आपका डैशबोर्ड", "लोحة التحكم الخاصة بك", "вашу панель управления", "bảng điều khiển của bạn"],
    "Job Seeker Sign-In": ["स्टूडेंट लॉगिन पेज", "स्टूडेंट लॉगिन", "صفحة تسجيل دخول الطالب", "تسجيل دخول الطالب", "страницу входа для студента", "входа для студента", "trang đăng nhập học viên", "đăng nhập học viên"],
    "Employer Login": ["एम्प्लॉयर पोर्टल", "بوابة صاحب العمل", "портал работодателя", "cổng thông tin nhà tuyển dụng"],
    "Grammar": ["ग्रामर सेक्शन", "ग्रामर", "قسم القواعد", "القواعد", "раздел грамматики", "грамматики", "phần ngữ pháp", "ngữ pháp"],
    "Roleplay": ["रोलप्ले प्रैक्टिस", "تدريب لعب الأدوار", "практику ролевых игр", "luyện tập đóng vai"],
    "Group Discussion": ["ग्रुप डिस्कशन", "المناقشة الجماعية", "групповое обсуждение", "thảo luận nhóm"],
    "JAM": ["JAM प्रैक्टिस", "تدريب JAM", "практику JAM", "luyện tập JAM"],
    "Resume Builder": ["रिज्यूमे बिल्डर", "منشئ السيرة الذاتية", "конструктор резюме", "trình tạo sơ yếu lý lịch"],
    "Membership": ["मेंबरशिप प्लान्स", "خطط العضوية", "тарифы подписки", "các gói thành viên"],
    "Job Seeker Registration": ["स्टूडेंट रजिस्ट्रेशन", "تسجيل الطالب", "регистрация студента", "đăng ký học viên"],
    "Employer Registration": ["एम्प्लॉयर रजिस्ट्रेशन", "تسجيل صاحب العمل", "регистрация работодателя", "đăng ký nhà tuyển dụng"],
    "English & Vocab": ["इंग्लिश और वोकैब", "الإنجليزية والمفردات", "английский и лексика", "tiếng anh và từ vựng"],
    "Aptitude": ["एप्टीट्यूड", "الكفاءة", "способности", "năng lực"],
    "Sitemap": ["साइटमैप", "خريطة الموقع", "карта сайта", "sơ đồ trang web"],
    "Browse all": ["सभी देखें", "تصفح الكل", "смотреть все", "duyệt tất cả"]
}
for _action_key, _config in ACTION_DEFINITIONS.items():
    _label = _config.get("label")
    if _label in _LOCALIZED_EXTENSIONS:
        _config.setdefault("keywords", []).extend(_LOCALIZED_EXTENSIONS[_label])

QUICK_GUIDANCE_PATTERNS = [
    {
        "match_terms": [
            "fluency",
            "pronunciation",
            "confidence",
            "hesitation",
            "hesitate",
            "speaking",
            "answer better",
            "speak better",
        ],
        "pages": {"activity_list", "roleplay_home", "roleplay_practice"},
        "reply": "Use shorter sentences and pause cleanly between ideas. Repeat one answer twice and stress the last few words clearly.",
        "action_keys": ["lessons", "roleplay"],
    },
    {
        "match_terms": [
            "listening",
            "understand audio",
            "comprehension",
            "catch words",
            "listen better",
        ],
        "pages": {"activity_list"},
        "reply": "Listen once for the main idea, then again for keywords like names, numbers, and actions. Pause and repeat one short clip until you can say it back.",
        "action_keys": ["lessons", "grammar"],
    },
    {
        "match_terms": [
            "reading speed",
            "read faster",
            "understand passage",
            "reading",
            "comprehension",
        ],
        "pages": {"activity_list"},
        "reply": "Read in short phrases instead of word by word. After each paragraph, say the main idea in one sentence before moving on.",
        "action_keys": ["lessons", "grammar"],
    },
    {
        "match_terms": [
            "writing",
            "grammar mistakes",
            "sentence",
            "essay",
            "vocabulary",
            "write better",
        ],
        "pages": {"activity_list"},
        "reply": "Start with simple sentence patterns and check subject-verb agreement first. Then replace only one or two common words with stronger vocabulary.",
        "action_keys": ["lessons", "grammar"],
    },
    {
        "match_terms": [
            "interview",
            "self introduction",
            "introduce myself",
            "interview answer",
            "job interview",
        ],
        "pages": {"resume_builder", "resume_job_match", "resume_analytics"},
        "reply": "Answer with a clear structure: role, action, and result. Keep each answer focused on one example with one measurable outcome.",
        "action_keys": ["resume_builder", "lessons"],
    },
    {
        "match_terms": [
            "resume",
            "job match",
            "ats",
            "resume score",
            "skill gap",
        ],
        "pages": {"resume_builder", "resume_job_match", "resume_analytics"},
        "reply": "Match your resume wording to the job description and put measurable results in the first few bullets. Fix missing keywords before rewriting the whole resume.",
        "action_keys": ["resume_builder", "lessons"],
    },
    {
        "match_terms": [
            "grammar",
            "tense",
            "noun",
            "verb",
            "pronoun",
            "sentence rule",
        ],
        "pages": {"subject", "subject_home", "subject_topic"},
        "reply": "Learn one rule with one example, then write two of your own sentences immediately. That is the fastest way to remember grammar accurately.",
        "action_keys": ["grammar", "lessons"],
    },
]

FAST_REPLY_PATTERNS = [
    # ── Speed / latency complaints ────────────────────────────────────────────
    {
        "match_terms": [
            "responding late",
            "response late",
            "very late",
            "why so slow",
            "why slow",
            "taking long time",
            "taking too long",
            "slow response",
            "why are you late",
            "so slow",
        ],
        "reply": "I am switching to a faster reply path now. Ask again and I will keep the answer short and immediate.",
        "action_keys": [],
    },
    # ── Identity / name ───────────────────────────────────────────────────────
    {
        "match_terms": [
            "what is your name",
            "what's your name",
            "whats your name",
            "your name",
            "who are you",
            "who r you",
            "what are you",
            "tell me about yourself",
            "introduce yourself",
            "what do i call you",
            "are you a bot",
            "are you ai",
            "are you human",
            "are you real",
        ],
        "reply": "I am Buddy, your learning assistant on this platform. I can guide you to lessons, practice, profile, or any module you need.",
        "action_keys": [],
    },
    # ── Greetings ─────────────────────────────────────────────────────────────
    {
        "match_terms": ["hello", "hi", "hey", "good morning", "good evening", "good afternoon", "good night", "howdy", "hiya", "sup", "what's up", "whats up"],
        "reply": "Hey! 👋 How can I help you today?",
        "action_keys": [],
    },
    # ── How are you ───────────────────────────────────────────────────────────
    {
        "match_terms": [
            "how are you",
            "how r you",
            "how are u",
            "are you okay",
            "are you fine",
            "how do you do",
            "how's it going",
            "hows it going",
        ],
        "reply": "I'm doing great! 😊 What can I help you with?",
        "action_keys": [],
    },
    # ── Thanks / appreciation ─────────────────────────────────────────────────
    {
        "match_terms": [
            "thank you",
            "thanks",
            "thank u",
            "thx",
            "ty",
            "much appreciated",
            "great job",
            "well done",
            "good job",
            "nice work",
        ],
        "reply": "You're very welcome! 😊 Let me know if there's anything else I can help with.",
        "action_keys": [],
    },
    # ── Goodbye / farewell ────────────────────────────────────────────────────
    {
        "match_terms": [
            "bye",
            "goodbye",
            "good bye",
            "see you",
            "see ya",
            "later",
            "take care",
            "cya",
            "ttyl",
        ],
        "reply": "Take care! Come back anytime you need help — good luck out there!",
        "action_keys": [],
    },
    # ── Confusion / not understood ────────────────────────────────────────────
    {
        "match_terms": [
            "i don't understand",
            "i do not understand",
            "what do you mean",
            "can you repeat",
            "say that again",
            "repeat that",
            "pardon",
        ],
        "reply": "Sure! I can help you navigate the app or answer quick learning questions. Try saying 'Go to lessons', 'Open practice', or ask me about a topic.",
        "action_keys": [],
    },
    # ── Capabilities ──────────────────────────────────────────────────────────
    {
        "match_terms": [
            "what can you do",
            "how can you help",
            "help me here",
            "what do you do",
            "what can aria do",
            "what can buddy do",
            "tell me what you can do",
            "features",
            "what all features available",
            "list features",
        ],
        "reply": "I can guide you to any lesson or module — just say 'Go to speaking', 'Open reading', 'Show profile', or 'Start interview'. I can also answer quick learning questions.",
        "action_keys": ["about_app", "lessons", "profile", "grammar"],
    },
    # ── Filler / acknowledgements ─────────────────────────────────────────────
    {
        "match_terms": ["ok", "okay", "sure", "alright", "got it", "understood", "noted", "fine"],
        "reply": "Got it! Let me know what you need next.",
        "action_keys": [],
    },
    # ── Testing / debugging ───────────────────────────────────────────────────
    {
        "match_terms": ["test", "testing", "hello riya", "hi riya", "hey riya", "check", "are you there", "you there"],
        "reply": "Yes, I am here and listening! What can I help you with?",
        "action_keys": [],
    },
]



def normalize_text(value: str) -> str:
    cleaned = (value or "").lower()
    cleaned = cleaned.replace("proffessional", "professional")
    cleaned = cleaned.replace("profesional", "professional")
    cleaned = cleaned.replace("grammer", "grammar")
    cleaned = re.sub(r"\b(sikar|sekar|sekhar|seekar)\b", "seeker", cleaned)
    cleaned = re.sub(r"\b(paar\s*singh|parsingh|parsing\s*parsing)\b", "parsing", cleaned)
    # Keep Unicode letters AND combining marks. This is important for scripts
    # such as Devanagari, Telugu, Tamil and Vietnamese.
    kept = []
    for ch in cleaned:
        category = unicodedata.category(ch)
        if ch.isspace() or category[0] in {"L", "M", "N"} or ch in "/-":
            kept.append(ch)
        else:
            kept.append(" ")
    return re.sub(r"\s+", " ", "".join(kept)).strip()

def localized_action_response(key: str, language: str, fallback: str = "") -> str:
    lang = normalize_language(language)
    action = ACTION_DEFINITIONS.get(key, {})
    custom = action.get("translations", {}).get(lang)
    if custom:
        return custom
    name = section_name(key, lang)
    if name:
        return opening(name, lang)
    if lang == "hindi":
        return f"{action.get('label', 'यह पेज')} खोल रहा हूँ।"
    if lang == "vietnamese":
        return f"Đang mở {action.get('label', 'tính năng này')}."
    if lang == "arabic":
        return f"جارٍ فتح {action.get('label', 'هذه الميزة')}."
    if lang == "russian":
        return f"Открываю {action.get('label', 'эту функцию')}."
    if lang == "telugu":
        return f"{action.get('label', 'ఈ ఫీచర్')} తెరుస్తున్నాను."
    if lang == "tamil":
        return f"{action.get('label', 'இந்த அம்சத்தை')} திறக்கிறேன்."
    return str(fallback or action.get("response", ""))





def _build_actions(action_keys: Any, is_employer: bool = False) -> list[dict[str, str]]:
    actions = []
    for key in action_keys:
        if not _action_is_available(key, is_employer):
            continue
        
        action = ACTION_DEFINITIONS.get(key)
        if not action:
            continue
        route = action["route"]
        label = action["label"]
        if key == "profile" and is_employer:
            route = "/employer/employer/dashboard/"
            label = "Employer Dashboard"
        actions.append(
            {
                "key": key,
                "label": label,
                "route": route,
            }
        )
    return actions


def _build_action(key: str, label: str, route: str) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "route": route,
    }


# ── Guided navigation ──────────────────────────────────────────────────────
#
# The deterministic intent path answered "I want to improve my speaking for
# interviews" with "Opening Speaking & Presentation." — correct, and a dead
# end. It names no next step, so the user has to guess what else exists.
#
# Children are ACTION_DEFINITIONS keys rather than prose, so the labels stay
# correct as the platform changes and there is no second list to maintain.
# The client mirrors this in BOTscript.js for its own local intent path.
#
# Only destinations this module can itself navigate to are listed. Buddy must
# not offer a choice it cannot then act on, so the grammar sub-topics — which
# exist as action keys in BOTscript.js but not here — are deliberately absent
# from the server map and are offered by the client instead.
NAVIGATION_CHILDREN: dict[str, list[str]] = {
    "lessons": [
        "professional_speaking", "passage_writing", "vocabulary",
        "negotiation", "communication", "analysis",
    ],
    "profile": ["lessons", "grammar", "resume_builder"],
    "resume_builder": ["mock_interview", "job_search"],
    "browse_all": ["english_vocab", "aptitude", "tech"],
    "sitemap": ["english_vocab", "aptitude", "tech"],
}


def _guided_navigation_reply(nav_key: str, reply: str, is_employer: bool = False,
                             language: str = "english") -> str:
    """Follow a navigation confirmation with what the user can do next.

    Returns ``reply`` unchanged when there is nothing worth adding — padding
    every response would be worse than saying less.
    """
    children = NAVIGATION_CHILDREN.get(nav_key)
    if not children:
        return reply

    labels = [
        section_name(key, language, ACTION_DEFINITIONS[key]["label"])
        for key in children
        if key in ACTION_DEFINITIONS and _action_is_available(key, is_employer)
    ][:5]

    if len(labels) < 2:
        return reply

    return f"{reply} {guidance(labels, language)}"


def _navigation_reply(nav_key: str, message_text: str, language: str, is_employer: bool = False) -> str:
    """The confirmation for a resolved navigation, in the user's language.

    English keeps the hand-written action response plus its description when
    the user asked about the page. Other languages used to be flattened to a
    bare "Opening <English label>" at the very end of the stream view, losing
    the description/menu and any gate message; they now get the same shape —
    a translated confirmation plus the translated "Inside you'll find" menu.
    """
    action = ACTION_DEFINITIONS[nav_key]
    lang = normalize_language(language)
    base = action["response"] if lang == "english" else localized_action_response(nav_key, lang)
    if not _is_informational_question(message_text):
        return base
    desc = action.get("description", "") if lang == "english" else ""
    return (f"{base} {desc}".strip() if desc
            else _guided_navigation_reply(nav_key, base, is_employer, lang))


# ---------------------------------------------------------------------------
# PREMIUM CHATBOT NAVIGATION SECURITY
# ---------------------------------------------------------------------------
# These are premium features whose navigation must never bypass the plan
# check, regardless of whether the request is handled by the deterministic
# resolver, activity resolver, or streaming AI response.
PREMIUM_NAVIGATION_KEYS = {
    "workshop",
    "gd",
    "jam",
    "roleplay",
    "mock_interview",
    "job_search",
}


def _is_premium_action_allowed(nav_key: str, user: Any = None) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    from career_app.views import _get_user_plan, _can_access_interview
    from activities.views import _can_access_workshop

    if nav_key == "mock_interview":
        return _can_access_interview(user)
    elif nav_key == "gd":
        return _can_access_workshop(user, "gd")
    elif nav_key == "jam":
        return _can_access_workshop(user, "jam")
    elif nav_key == "roleplay":
        return _can_access_workshop(user, "roleplay")
    
    # Fallback for generic premium navigation like job_search or workshop root
    return _get_user_plan(user) in ("normal", "pro", "medium")


def _premium_navigation_block(
    nav_key: str | None,
    user: Any = None,
    is_employer: bool = False,
    language: str = "english",
) -> dict[str, Any] | None:
    """Return a safe membership payload when a Free user requests premium navigation."""
    if nav_key not in PREMIUM_NAVIGATION_KEYS:
        return None

    if _is_premium_action_allowed(nav_key, user):
        return None

    return {
        "reply": message_text("upgrade_feature", language),
        "actions": [_build_action("pro", "Membership", "/pro/")],
        "source": "intent",
    }


def _page_context(page: str, path: str, is_employer: bool = False) -> dict[str, Any]:
    page = (page or "").strip().lower()
    path = (path or "").strip().lower()

    if is_employer:
        return {
            "name": "Employer Portal",
            "summary": "The employer is viewing the employer portal.",
            "default_reply": "I can help you manage jobs and find candidates.",
            "action_keys": ["profile", "company_profile", "find_candidates", "post_job", "all_applications", "job_openings", "login_employer"],
        }

    if "/activities/" in path or page == "activity_list":
        return {
            "name": "Activities hub",
            "summary": "The user is browsing the activities list.",
            "default_reply": "I can help you find listening, speaking, reading, or writing exercises.",
            "action_keys": ["lessons", "grammar", "profile"],
        }
    if "/subject/" in path:
        return {
            "name": "Grammar module",
            "summary": "The user is studying grammar.",
            "default_reply": "I can help with grammar rules or take you to other practice modules.",
            "action_keys": ["grammar", "lessons", "profile"],
        }
    if "/resume-builder/" in path:
        return {
            "name": "Resume builder",
            "summary": "The user is working on their resume or job match.",
            "default_reply": "I can help with your resume analysis or finding suitable jobs.",
            "action_keys": ["resume_builder", "lessons", "profile"],
        }
    if "/dashboard/" in path or page == "student_dashboard":
        return {
            "name": "Student Dashboard",
            "summary": "The user is viewing their progress.",
            "default_reply": "I can help you review your scores or suggest your next activity.",
            "action_keys": ["profile", "lessons", "grammar"],
        }
    if "/roleplay/" in path:
        return {
            "name": "Roleplay Practice",
            "summary": "The user is practicing real-world conversations.",
            "default_reply": "I can help with your current roleplay or take you to other practice modules.",
            "action_keys": ["roleplay", "lessons", "profile"],
        }

    if page == "landing" or path == "/":
        return {
            "name": "Landing Page",
            "summary": "The user is on the main landing page.",
            "default_reply": "I can help you login, register, or learn more about the application.",
            "action_keys": ["home", "about_app", "login_job_seeker", "login_employer", "register_job_seeker", "register_employer"],
        }

    return {
        "name": "Learning platform",
        "summary": "The user is browsing the platform.",
        "default_reply": "I can guide you to activities, grammar, resume builder, or your dashboard.",
        "action_keys": ["lessons", "grammar", "resume_builder", "profile"],
    }


def _intent_score(message: str, config: dict[str, Any]) -> float:
    """Score how well an ACTION_DEFINITIONS entry matches a message.

    Two care points, both found while tracking down "Professional Speaking"
    and "Professional Reading" navigation bugs:

    1. Whole-word matching, not raw substring. A plain ``keyword in
       normalized_input`` check matches a short keyword like "pro" inside
       an unrelated word like "professional" (or "profile", "process",
       ...), which is how "Open Professional Reading" was internally
       resolving to the "pro" (Membership) action. ``\\b`` boundaries make
       the phrase check require whole words.
    2. Matched keyword tokens are deduplicated across an action's whole
       keyword list, not summed per keyword phrase. An action with several
       keyword variants that all share one word (e.g. "speaking module",
       "speaking page", "speaking activity", "speaking practice" all
       sharing "speaking") previously added that same token's overlap
       score once per phrase it appeared in, inflating the total for any
       message containing that one common word. Counting each matched
       token once, however many keyword phrases it appears in, removes
       that inflation without weakening genuinely distinct multi-word
       phrase matches (still scored via the phrase-match bonus below).
    """
    normalized_input = normalize_text(message)
    input_tokens = normalized_input.split()
    input_token_set = set(input_tokens)

    phrase_match_score = 0.0
    matched_tokens: set[str] = set()

    for keyword in config["keywords"]:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue

        if re.search(
            r"(?<!\w)" + re.escape(normalized_keyword) + r"(?!\w)",
            normalized_input,
        ):
            phrase_match_score = max(phrase_match_score, 4.0)

        keyword_tokens = [
            token for token in normalized_keyword.split()
            if token not in INTENT_STOP_WORDS
        ]
        matched_tokens.update(
            token for token in keyword_tokens if token in input_token_set
        )

    score = phrase_match_score + len(matched_tokens) * 1.1

    if re.search(r"\b(go|open|navigate|take|show|start|view|karo|kholo|dikhao|jao|chalo)\b", normalized_input) or any(x in normalized_input for x in MULTILINGUAL_NAVIGATION_SIGNALS):
        score += 0.5

    return score


def _has_navigation_verb(message: str) -> bool:
    normalized_input = normalize_text(message)
    if re.search(r"\b(tips|advice|explain|what is|how to|how can|help me)\b", normalized_input):
        return False
    return bool(
        re.search(r"\b(go|open|navigate|take|show|start|launch|visit|move|redirect|list|karo|kholo|khulna|kholna|dikhao|jao|chalo|batao|register|sign up)\b", normalized_input)
        or re.search(r"\btake me\b", normalized_input)
        or re.search(r"\bgo to\b", normalized_input)
        or re.search(r"\b(employer|employeer|recruiter|job seeker|jobseeker|student|candidate|job)\b", normalized_input)
        or any(x in normalized_input for x in MULTILINGUAL_NAVIGATION_SIGNALS)
    )


def _looks_like_navigation_command(message: str) -> bool:
    normalized_input = normalize_text(message)
    if not normalized_input or not _has_navigation_verb(normalized_input):
        return False
    return bool(
        re.search(r"^(go|open|navigate|take|start|launch|visit|move|redirect)\b", normalized_input)
        or re.search(r"\b(go to|take me)\b", normalized_input)
        or re.search(
            r"\b(page|module|activity|activities|dashboard|profile|resume|grammar|speaking|writing|listening|reading|gd|jam|roleplay|membership|pro)\b",
            normalized_input,
        )
    )


EMPLOYER_ONLY_KEYS = {
    "company_profile", "find_candidates", "post_job", 
    "all_applications", "job_openings", "login_employer"
}

STUDENT_ONLY_KEYS = {
    "lessons", "professional_speaking", "passage_writing", 
    "vocabulary", "negotiation", "communication", "analysis", "listen_learn",
    "grammar", "roleplay", "gd", "jam", "resume_builder", "pro", "mock_interview",
    "job_search", "login_job_seeker"
}

# ---------------------------------------------------------------------------
# EXPLICIT CROSS-PORTAL INTENT DETECTION
# ---------------------------------------------------------------------------
# validate_portal_navigation() below is correct and already bidirectional,
# but it only fires once a message has already resolved to a specific
# nav_key in EMPLOYER_ONLY_KEYS/STUDENT_ONLY_KEYS. The general-purpose
# fuzzy resolver (resolve_navigation_intent) is built to match specific
# application FEATURES ("post a job", "open grammar"), not the abstract
# concept of "the other portal" - so phrases like "go to job seeker
# portal" were matching on partial keyword overlap (the word "job") to an
# unrelated feature like job_openings, silently bypassing the guard
# entirely instead of being blocked. This runs first and independently of
# that resolver, using plain phrase matching, so it can't be thrown off by
# unrelated keyword collisions.
_CROSS_PORTAL_TO_EMPLOYER = re.compile(
    r"\b(employer portal|employer dashboard|employer section|employer area|"
    r"recruiter portal|recruiter dashboard|recruiter section|"
    r"switch to employer|go to employer|open employer|take me to employer|"
    r"employer login|employer sign in)\b"
)
_CROSS_PORTAL_TO_JOB_SEEKER = re.compile(
    r"\b(job seeker portal|job seeker dashboard|job seeker section|job seeker area|"
    r"candidate portal|candidate dashboard|candidate section|"
    r"student portal|student dashboard|"
    r"switch to job seeker|switch to student|switch to candidate|"
    r"go to job seeker|go to student|go to candidate|"
    r"open job seeker|open student|open candidate|"
    r"take me to job seeker|"
    r"job seeker login|job seeker sign in)\b"
)


def _detect_cross_portal_block(message: str, is_employer: bool, language: str = "english") -> dict[str, Any] | None:
    """Explicit, phrase-based cross-portal request detector. See module note above."""
    normalized = normalize_text(message)
    if not normalized:
        return None

    if not is_employer and _CROSS_PORTAL_TO_EMPLOYER.search(normalized):
        return {
            "reply": "You're in the Job Seeker portal. Employer and recruiter features are kept separate here, so I won't redirect you to the Employer portal.",
            "actions": [],
            "source": "intent",
            "language": language,
        }

    if is_employer and _CROSS_PORTAL_TO_JOB_SEEKER.search(normalized):
        return {
            "reply": "You're currently in the Employer portal. Job Seeker features are kept separate here, so I won't redirect you to the Job Seeker portal.",
            "actions": [],
            "source": "intent",
            "language": language,
        }

    return None


def validate_portal_navigation(nav_key: str | None, is_employer: bool, language: str = "english") -> dict[str, Any] | None:
    """Centralized guard to block cross-portal navigation."""
    if not nav_key:
        return None

    if not is_employer and nav_key in EMPLOYER_ONLY_KEYS:
        return {
            "reply": "You're in the Job Seeker portal. Employer and recruiter features are kept separate here, so I won't redirect you to the Employer portal.",
            "actions": [],
            "source": "intent",
            "language": language
        }
        
    if is_employer and nav_key in STUDENT_ONLY_KEYS:
        return {
            "reply": "You are currently in the Employer portal. Student and job seeker activities are kept separate here, so I won't redirect you to the Job Seeker portal.",
            "actions": [],
            "source": "intent",
            "language": language
        }
        
    return None

def _action_is_available(key: str, is_employer: bool = False) -> bool:
    if is_employer:
        if key in STUDENT_ONLY_KEYS:
            return False
    else:
        if key in EMPLOYER_ONLY_KEYS:
            return False

    action = ACTION_DEFINITIONS.get(key)
    if not action:
        return False
    route = action.get("route", "")
    if not route:
        # Actions with no route (e.g., about_app) are always available
        return True
    try:
        from django.urls import resolve
        resolve(route)
        return True
    except Exception:
        return True

MULTILINGUAL_NAVIGATION_SIGNALS = [
    "open", "go to", "take me", "show me", "navigate", "launch", "visit", "start", "register", "sign up",
    "mở", "đưa tôi", "đi đến", "hiển thị", "truy cập", "bắt đầu", "đăng ký",
    "खोलो", "खोलें", "खोलना", "ले चलो", "दिखाओ", "जाओ", "शुरू करो", "शुरू करें",
    "ओपन", "करो", "रजिस्ट्रेशन", "रजिस्टर",
    "kholo", "kholna", "karo", "dikhao", "jao", "chalo", "batao", "register",
    "افتح", "خذني", "اذهب", "أظهر", "انتقل", "ابدأ", "تسجيل",
    "открой", "открыть", "перейди", "перейти", "покажи", "запусти", "начни", "регистрация", "зарегистрироваться",
    "వెళ్ళు", "వెళ్లు", "తెరువు", "తెరవండి", "చూపించు", "తీసుకెళ్ళు", "ప్రారంభించు", "నమోదు",
    "செல்", "செல்லுங்கள்", "திற", "திறக்கவும்", "காட்டு", "அழைத்துச் செல்", "தொடங்கு", "பதிவு",
]
MULTILINGUAL_FEATURE_SIGNALS = [
    "grammar", "vocabulary", "speaking", "listening", "reading", "writing", "resume",
    "interview", "roleplay", "group discussion", "jam", "jobs", "job", "profile",
    "dashboard", "membership", "activities", "practice",
    "ngữ pháp", "từ vựng", "nghe", "nói", "đọc", "viết", "hồ sơ", "việc làm",
    "phỏng vấn", "luyện tập",
    "व्याकरण", "शब्दावली", "बोलना", "सुनना", "पढ़ना", "लिखना", "रिज्यूमे",
    "इंटरव्यू", "प्रोफाइल", "डैशबोर्ड", "नौकरी", "अभ्यास",
    "قواعد", "مفردات", "تحدث", "استماع", "قراءة", "كتابة", "سيرة ذاتية",
    "مقابلة", "وظائف", "الملف الشخصي", "لوحة التحكم",
    "грамматика", "словарь", "говорение", "аудирование", "чтение", "письмо",
    "резюме", "интервью", "профиль", "вакансии", "практика",
    "వ్యాకరణం", "పదజాలం", "మాట్లాడటం", "వినడం", "చదవడం", "రాయడం", "రెజ్యూమ్",
    "ఇంటర్వ్యూ", "ప్రొఫైల్", "డాష్‌బోర్డ్", "ఉద్యోగాలు", "ఉద్యోగం", "చర్చ", "సభ్యత్వం", "అభ్యాసం",
    "இலக்கணம்", "சொற்களஞ்சியம்", "பேசுதல்", "கேட்டல்", "வாசித்தல்", "எழுதுதல்", "ரெஸ்யூம்",
    "நேர்காணல்", "சுயவிவரம்", "டாஷ்போர்டு", "வேலைகள்", "வேலை", "விவாதம்", "உறுப்பினர்", "பயிற்சி",
]
MULTILINGUAL_QUESTION_SIGNALS = [
    "là gì", "giải thích", "nghĩa là gì", "thế nào", "cách", "làm sao", "mẹo", "lời khuyên", "tác dụng của", "lợi ích của", "dùng để làm gì", "mục đích",
    "kya hai", "kya hota", "kaise", "samjhao", "matlab", "kya", "meaning", "tips", "advice", "fayda", "use kya hai", "kyon use", "istemaal", "upayog", "purpose", "benefits", "benefit", "use for",
    "क्या है", "कैसे", "समझाइए", "मतलब", "सलाह", "फायदा", "उपयोग", "इस्तेमाल", "उद्देश्य", "क्या फायदा",
    "ما هو", "ما هي", "كيف", "اشرح", "معنى", "نصائح", "نصيحة", "لماذا", "فائدة", "استخدام", "فوائد", "ما الفائدة", "الغرض",
    "что такое", "как", "объясни", "значение", "советы", "зачем", "почему", "для чего", "какая польза", "польза", "использование", "применение", "цель"
]

def _has_multilingual_navigation_signal(message: str) -> bool:
    text = (message or "").strip().lower()
    return bool(text) and (
        any(x in text for x in MULTILINGUAL_NAVIGATION_SIGNALS)
        or any(x in text for x in MULTILINGUAL_FEATURE_SIGNALS)
    )

def _is_informational_question(message: str) -> bool:
    normalized_input = normalize_text(message)
    return bool(
        re.search(
            r"\b(what is|what are|explain|meaning|define|definition|"
            r"tips|advice|why|how to|how can|use of|"
            # Self-directed permission/eligibility questions ("Can I do a
            # mock interview?", "Should I upgrade?") are asking about their
            # own situation, not directing the assistant to act - unlike
            # "Can you take me to Grammar", which stays an action request
            # since it addresses the assistant ("you"), not the user ("I").
            r"can i|could i|should i|would i|am i (eligible|allowed)|do i (have|need)"
            r")\b",
            normalized_input,
        )
        or any(x in normalized_input for x in MULTILINGUAL_QUESTION_SIGNALS)
    )

def _ai_resolve_navigation_intent(message: str, language: str, api_key: str | None = None, is_employer: bool = False) -> str | None:
    if not message:
        return None
    if api_key is None:
        api_key = getattr(settings, "SARVAM_API_KEY", "")
    if not api_key:
        return None

    available = {
        key: {"label": value["label"], "route": value["route"]}
        for key, value in ACTION_DEFINITIONS.items()
        if _action_is_available(key, is_employer) and not _is_category_route_key(key)
    }
    prompt = (
        "You are the navigation intent classifier for Career Buddy LMS. "
        "Understand the user's request in ANY language and map it to exactly one "
        "canonical action key from the supplied mapping. Do not invent keys or routes. "
        "CRITICAL INSTRUCTION: Return a key if the user is requesting to navigate to that feature, OR if the user simply types the name of the feature (e.g., 'professional speaking', 'resume builder'). "
        "If the user is asking a QUESTION about the feature (e.g. 'what is the use of', 'how to use', 'explain'), you MUST return NONE so the conversational AI can answer it. "
        "If the user is not requesting a real application feature/page, return NONE. "
        "If the requested feature is unavailable, return NONE. "
        "Return ONLY the key or NONE.\n"
        f"Allowed actions: {json.dumps(available, ensure_ascii=False)}\n"
        f"User language: {normalize_language(language)}\n"
        f"User request: {message}"
    )
    try:
        response = requests.post(
            SARVAM_CHAT_URL,
            headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
            json={
                "model": getattr(settings, "SARVAM_MODEL", "sarvam-105b"),
                "temperature": 0.0,
                "max_tokens": 30,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message},
                ],
                "reasoning_effort": None,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        candidate = re.sub(r"[^a-zA-Z0-9_]", "", str(content).strip())
        return candidate if candidate in available else None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Multilingual navigation aliases.
# These are intentionally role-neutral; _action_is_available() is always
# checked before an alias can resolve, so Job Seeker and Employer data remain
# isolated.
# ---------------------------------------------------------------------------
MULTILINGUAL_INTENT_ALIASES = {
    "home": ["home", "होम", "الرئيسية", "главная", "trang chủ"],
    "lessons": ["activities", "activity", "practice", "lessons", "lesson", "गतिविधियां", "अभ्यास", "الأنشطة", "صفحة الأنشطة", "практика", "занятия", "hoạt động", "trang hoạt động"],
    "professional_speaking": ["speaking", "speaking practice", "स्पीकिंग", "प्रोफेशनल स्पीकिंग", "التحدث", "التحدث المهني", "профессиональная речь", "luyện nói"],
    "passage_writing": ["writing", "correspondence", "राइटिंग", "लेखन", "الكتابة", "الكتابة والمراسلات", "письмо", "деловая переписка", "viết"],
    "vocabulary": ["vocabulary", "vocab", "idioms", "वोकैबुलरी", "शब्दावली", "मुहावरे", "المفردات", "التعابير", "лексика", "идиомы", "từ vựng", "thành ngữ"],
    "negotiation": ["negotiation", "meetings", "negotiation and meetings", "नेगोशिएशन", "मीटिंग", "बैठक", "التفاوض", "الاجتماعات", "переговоры", "встречи", "đàm phán", "cuộc họp"],
    "communication": ["communication", "professional communication", "कम्युनिकेशन", "संचार", "التواصل", "التواصل المهني", "общение", "профессиональное общение", "giao tiếp"],
    "analysis": ["analysis", "reporting", "analysis and reporting", "एनालिसिस", "रिपोर्टिंग", "التحليل", "إعداد التقارير", "анализ", "отчётность", "phân tích", "báo cáo"],
    "profile": ["dashboard", "student dashboard", "my dashboard", "profile", "my profile", "account", "डैशबोर्ड", "डैशबोर्ड खोलो", "मेरा डैशबोर्ड", "प्रोफाइल", "لوحة التحكم", "ملفي الشخصي", "панель управления", "профиль", "bảng điều khiển", "hồ sơ"],
    "company_profile": ["company profile", "employer profile", "business profile", "company", "कंपनी प्रोफाइल", "कंपनी", "ملف الشركة", "профиль компании", "компания", "hồ sơ công ty"],
    "find_candidates": ["candidate", "candidates", "find candidates", "search candidates", "candidate search", "show candidates", "browse candidates", "candidate dikhao", "उम्मीदवार", "उम्मीदवार दिखाओ", "उम्मीदवार खोजें", "مرشح", "المرشحون", "ابحث عن مرشحين", "кандидат", "кандидаты", "покажи кандидатов", "найти кандидатов", "ứng viên", "hiển thị ứng viên", "tìm ứng viên", "tuyển ứng viên", "tuyển dụng ứng viên"],
    "post_job": ["post job", "post new job", "create job", "new job", "add job", "job posting", "job post", "नौकरी पोस्ट", "जॉब पोस्ट", "नई नौकरी", "नौकरी बनाएं", "وظيفة", "نشر وظيفة", "إنشاء وظيفة", "разместить вакансию", "создать вакансию", "вакансия", "đăng việc", "đăng tin tuyển dụng", "tạo việc làm"],
    "all_applications": ["applications", "application", "all applications", "job applications", "view applications", "आवेदन", "आवेदन देखें", "सभी आवेदन", "طلبات", "طلبات التوظيف", "заявки", "заявки на работу", "đơn ứng tuyển", "hồ sơ ứng tuyển"],
    "job_openings": ["jobs", "job", "job openings", "openings", "my jobs", "posted jobs", "vacancies", "जॉब", "नौकरी", "जॉब ओपनिंग", "मेरी नौकरियां", "الوظائف", "وظائف", "الشواغر", "вакансии", "работа", "tìm việc", "việc làm", "công việc", "vị trí tuyển dụng"],
    "login_job_seeker": ["job seeker login", "student login", "job seeker sign in", "job seeker", "student", "job sikar", "job seekar", "जॉब सीकर", "छात्र लॉगिन", "باحث عن عمل", "تسجيل دخول الباحث عن عمل", "соискатель", "вход для соискателя", "người tìm việc", "đăng nhập người tìm việc"],
    "register_job_seeker": ["register job seeker", "job seeker registration", "student registration", "sign up as job seeker", "जॉब सीकर रजिस्ट्रेशन", "छात्र पंजीकरण", "تسجيل باحث عن عمل", "регистрация соискателя", "đăng ký người tìm việc"],
    "login_employer": ["employer login", "recruiter login", "employer", "recruiter", "hiring", "employer sign in", "एम्प्लॉयर", "नियोक्ता", "भर्ती", "صاحب العمل", "تسجيل دخول صاحب العمل", "работодатель", "рекрутер", "найм", "nhà tuyển dụng", "đăng nhập nhà tuyển dụng"],
    "register_employer": ["register employer", "employer registration", "company registration", "recruiter registration", "एम्प्लॉयर रजिस्ट्रेशन", "कंपनी पंजीकरण", "تسجيل صاحب العمل", "регистрация работодателя", "регистрация компании", "đăng ký nhà tuyển dụng", "đăng ký công ty"],
    "english_vocab": ["english", "english vocab", "अंग्रेजी", "अंग्रेजी शब्दावली", "الإنجليزية", "английский", "tiếng Anh"],
    "aptitude": ["aptitude", "reasoning", "एप्टीट्यूड", "तर्क", "القدرات", "الاستدلال", "логика", "năng lực", "lý luận"],
    "tech": ["tech", "technical", "technology", "programming", "टेक", "तकनीकी", "प्रोग्रामिंग", "تقنية", "برمجة", "технологии", "программирование", "công nghệ", "lập trình"],
    "grammar": ["grammar", "grammer", "english grammar", "व्याकरण", "ग्रामर", "قواعد", "قواعد اللغة", "грамматика", "ngữ pháp"],
    "roleplay": ["roleplay", "role play", "conversation roleplay", "रोलप्ले", "لعب الأدوار", "ролевые игры", "đóng vai"],
    "gd": ["group discussion", "gd", "discussion", "ग्रुप डिस्कशन", "समूह चर्चा", "المناقشة الجماعية", "групповая дискуссия", "thảo luận nhóm"],
    "jam": ["jam", "just a minute", "jam practice", "JAM अभ्यास", "تدريب JAM", "практика JAM", "luyện tập JAM"],
    "resume_builder": ["resume", "cv", "resume builder", "build resume", "upload resume", "रिज्यूमे", "सीवी", "रिज्यूमे बिल्डर", "السيرة الذاتية", "منشئ السيرة الذاتية", "резюме", "конструктор резюме", "sơ yếu lý lịch", "trình tạo CV"],
    "mock_interview": ["mock interview", "ai mock interview", "ai interview", "interview practice", "interview", "इंटरव्यू", "मॉक इंटरव्यू", "AI मॉक इंटरव्यू", "مقابلة تجريبية", "مقابلة بالذكاء الاصطناعي", "пробное собеседование", "собеседование с ИИ", "phỏng vấn thử", "phỏng vấn AI"],
    "job_recommendations": ["job recommendations", "recommended jobs", "matched jobs", "job matches", "my job matches", "नौकरी सिफारिशें", "अनुशंसित नौकरियां", "الوظائف الموصى بها", "رекомендованные вакансии", "рекомендованные вакансии", "việc làm được đề xuất"],
    "job_search": ["job search", "search jobs", "find jobs", "looking for jobs", "find a job", "jobs", "job", "नौकरी", "नौकरी खोजें", "जॉब सर्च", "وظائف", "ابحث عن وظيفة", "работа", "найти работу", "вакансии", "tìm việc", "tìm việc làm", "tìm công việc"],
    "sitemap": ["sitemap", "site map", "साइटमैप", "خريطة الموقع", "карта сайта", "sơ đồ trang web"],
    "contact_us": ["contact us", "contact", "support", "संपर्क", "اتصل بنا", "контакты", "liên hệ"],
    "resources": ["resources", "resource", "संसाधन", "موارد", "ресурсы", "tài nguyên"],
    "industries": ["industries", "industry", "उद्योग", "صناعات", "отрасли", "ngành công nghiệp"],
}

ACTIVITY_MULTILINGUAL_ALIASES = {
    "Elevator Pitch Workshop": ['एलीवेटर पिच वर्कशॉप', 'Hội thảo thực hành Elevator Pitch', 'ورشة عمل العرض التقديمي السريع', 'Мастер-класс по питчингу', 'Elevator Pitch Workshop', 'Elevator Pitch'],
    "Business Negotiation Simulation": ['बिजनेस नेगोशिएशन सिमुलेशन', 'Mô phỏng đàm phán kinh doanh', 'محاكاة التفاوض التجاري', 'Симуляция деловых переговоров', 'Business Negotiation Simulation', 'Business Negotiation'],
    "Professional Email Communication": ['प्रोफेशनल ईमेल कम्युनिकेशन', 'Giao tiếp email chuyên nghiệp', 'التواصل المهني عبر البريد الإلكتروني', 'Профессиональная переписка по электронной почте', 'Professional Email Communication', 'Professional Email'],
    "Case Study Analysis and Presentation": ['केस स्टडी एनालिसिस एंड प्रेजेंटेशन', 'Phân tích và trình bày tình huống', 'تحليل ودراسة الحالة وتقديمها', 'Анализ и презентация тематического исследования', 'Case Study Analysis and Presentation', 'Case Study Analysis'],
    "Meeting Management Workshop": ['मीटिंग मैनेजमेंट वर्कशॉप', 'Hội thảo quản lý cuộc họp', 'ورشة عمل إدارة الاجتماعات', 'Семинар по управлению встречами', 'Meeting Management Workshop', 'Meeting Management'],
    "Job Interview Mastery": ['जॉब इंटरव्यू मास्टरी', 'Nắm vững phỏng vấn xin việc', 'إتقان مقابلة العمل', 'Мастерство прохождения собеседований', 'Job Interview Mastery', 'Job Interview'],
    "Business Report Writing": ['बिजनेस रिपोर्ट राइटिंग', 'Viết báo cáo kinh doanh', 'كتابة التقارير التجارية', 'Написание деловых отчетов', 'Business Report Writing', 'Business Report'],
    "Cross-Cultural Communication": ['क्रॉस-कल्चरल कम्युनिकेशन', 'Giao tiếp đa văn hóa', 'التواصل عبر الثقافات', 'Межкультурная коммуникация', 'Cross-Cultural Communication', 'Cross Cultural Communication'],
    "Product Launch Planning": ['प्रोडक्ट लॉन्च प्लानिंग', 'Lập kế hoạch ra mắt sản phẩm', 'التخطيط لإطلاق المنتج', 'Планирование запуска продукта', 'Product Launch Planning', 'Product Launch'],
    "Business Telephone and Video Calls": ['बिजनेस टेलीफोन एंड वीडियो कॉल्स', 'Cuộc gọi điện thoại và video kinh doanh', 'المكالمات الهاتفية والمرئية التجارية', 'Деловые телефонные и видеозвонки', 'Business Telephone and Video Calls', 'Business Telephone'],
    "Financial Literacy and Reporting": ['फाइनेंशियल लिटरेसी एंड रिपोर्टिंग', 'Hiểu biết và báo cáo tài chính', 'الثقافة والتقارير المالية', 'Финансовая грамотность и отчетность', 'Financial Literacy and Reporting', 'Financial Literacy'],
    "Business Correspondence: Letters and Memos": ['बिजनेस कॉरेस्पोंडेंस: लेटर्स एंड मेमोज', 'Thư từ thương mại: Thư và bản ghi nhớ', 'المراسلات التجارية: الرسائل والمذكرات', 'Деловая переписка: письма и памятки', 'Business Correspondence: Letters and Memos', 'Business Correspondence'],
    "Networking and Small Talk": ['नेटवर्किंग एंड स्मॉल टॉक', 'Mạng lưới quan hệ và trò chuyện ngắn', 'بناء العلاقات والأحاديث الجانبية', 'Нетворкинг и светские беседы', 'Networking and Small Talk', 'Networking'],
    "Handling Complaints and Conflict Resolution": ['हैंडलिंग कंप्लेंट एंड कॉन्फ्लिक्ट रेजोल्यूशन', 'Xử lý khiếu nại và giải quyết xung đột', 'التعامل مع الشكاوى وحل النزاعات', 'Обработка жалоб и разрешение конфликтов', 'Handling Complaints and Conflict Resolution', 'Handling Complaints'],
    "Business Vocabulary Building Games": ['बिजनेस वोकैबुलरी बिल्डिंग गेम्स', 'Trò chơi xây dựng từ vựng kinh doanh', 'ألعاب بناء المفردات التجارية', 'Игры для расширения делового словарного запаса', 'Business Vocabulary Building Games', 'Business Vocabulary Building'],
    "Proposal and Bid Writing": ['प्रपोजल एंड बिड राइटिंग', 'Viết đề xuất và đấu thầu', 'كتابة العروض والعطاءات', 'Написание коммерческих предложений и заявок на тендер', 'Proposal and Bid Writing', 'Proposal and Bid'],
    "Data Presentation and Visualization": ['डेटा प्रेजेंटेशन एंड विज़ुअलाइज़ेशन', 'Trình bày và trực quan hóa dữ liệu', 'تقديم البيانات وتصورها', 'Презентация и визуализация данных', 'Data Presentation and Visualization', 'Data Presentation'],
    "Business Idioms and Phrasal Verbs": ['बिजनेस इडियम्स एंड फ्रेज़ल वर्ब्स', 'Thành ngữ và cụm động từ trong kinh doanh', 'التعابير والأفعال المركبة التجارية', 'Деловые идиомы и фразовые глаголы', 'Business Idioms and Phrasal Verbs', 'Business Idioms'],
    "Corporate Social Responsibility Debate": ['कॉर्पोरेट सोशल रिस्पॉन्सिबिलिटी डिबेट', 'Tranh luận về trách nhiệm xã hội của doanh nghiệp', 'مناقشة المسؤولية الاجتماعية للشركات', 'Дебаты о корпоративной социальной ответственности', 'Corporate Social Responsibility Debate', 'Corporate Social Responsibility'],
    "Project Status Update and Reporting": ['प्रोजेक्ट स्टेटस अपडेट एंड रिपोर्टिंग', 'Cập nhật và báo cáo trạng thái dự án', 'تحديث وإعداد تقارير حالة المشروع', 'Обновление статуса проекта и отчетность', 'Project Status Update and Reporting', 'Project Status Update'],
    "Professional Speaking": ['प्रोफेशनल स्पीकिंग', 'Nói chuyên nghiệp', 'التحدث المهني', 'Профессиональная речь', 'Professional Speaking'],
    "Professional Passage Writing": ['प्रोफेशनल पैसेज राइटिंग', 'Viết đoạn văn chuyên nghiệp', 'كتابة فقرات مهنية', 'Профессиональное написание текстов', 'Professional Passage Writing'],
    "Listen & Learn": ['लिसन एंड लर्न', 'Nghe và Học', 'استمع وتعلم', 'Слушай и учись', 'Listen & Learn', 'Listen and Learn'],
    "Professional Reading": ['प्रोफेशनल रीडिंग', 'Đọc chuyên nghiệp', 'القراءة المهنية', 'Профессиональное чтение', 'Professional Reading'],
    "Group Discussion": ['ग्रुप डिस्कशन', 'Thảo luận nhóm', 'مناقشة جماعية', 'Групповая дискуссия', 'Group Discussion'],
    "JAM (Just a Minute)": ['जैम', 'JAM', 'جام', 'ДЖАМ', 'JAM (Just a Minute)', 'Just a minute', 'JAM'],
    "Roleplay Practice": ['रोलप्ले प्रैक्टिस', 'Luyện tập đóng vai', 'ممارسة لعب الأدوار', 'Практика ролевых игр', 'Roleplay Practice', 'Roleplay', 'Role play Practice'],
}

MULTILINGUAL_NAVIGATION_WORDS = {
    "open", "go", "show", "take me", "start", "launch", "visit", "navigate", "find", "search", "display",
    "karo", "kholo", "khulna", "kholna", "dikhao", "jao", "chalo", "batao", "खोलो", "खोलें", "दिखाओ", "जाओ", "चलो", "बताओ", "ढूंढो", "खोजो",
    "افتح", "اذهب", "اعرض", "أرني", "ابحث", "ابدأ", "انتقل", "открой", "покажи", "найди", "ищи", "перейди", "начни",
    "mở", "hiển thị", "cho tôi xem", "tìm", "bắt đầu", "đến"
}

def _is_category_route_key(key: str) -> bool:
    """True for an ACTION_DEFINITIONS key whose route opens an Activities
    category listing (e.g. "professional_speaking" -> /activities/?category=
    speaking), as opposed to a plain static page (home, grammar, roleplay...).

    resolve_navigation_intent() has no knowledge of the real Activity
    catalog -- only resolve_activity_navigation_payload() (queried right
    after it, in both riya_chat_logic() and stream_assistant_response())
    does, and only that function can correctly tell a category request
    ("open the Speaking category") apart from a same-worded individual
    Activity ("open Professional Speaking", "open Professional Reading").
    Word-level matching alone can never make that call correctly -- "Open
    Professional Speaking" and "speaking" both legitimately contain the
    whole word "speaking", so no amount of stricter word-boundary matching
    here can tell them apart the way a real catalog lookup can.

    So this resolver simply never claims a category route with any
    confidence; every place below that would otherwise return one of
    these keys returns None instead, leaving the category-vs-activity
    decision entirely to the catalog-aware resolver that runs next.
    """
    config = ACTION_DEFINITIONS.get(key)
    if not config:
        return False
    return "/activities/?category=" in str(config.get("route", ""))


def resolve_navigation_intent(message: str, language: str = "english", api_key: str | None = None, user: Any = None, use_ai: bool = True) -> str | None:
    is_employer = False
    if user and getattr(user, "is_authenticated", False) and hasattr(user, "employer_profile"):
        is_employer = True
        
    normalized_input = normalize_text(message)
    if not normalized_input:
        return None

    # No early bail on "what is …": a question that NAMES a section must resolve
    # so the caller opens + describes it locally. Advice questions name no
    # section, so the matchers below don't fire → None → LLM. riya_chat_logic
    # decides whether to append a description via _is_informational_question.

    # ------------------------------------------------------------
    # MULTILINGUAL EXACT / SHORT-PHRASE NAVIGATION
    # ------------------------------------------------------------
    # This runs before the older English resolver. It deliberately accepts
    # one-word commands and mixed-language commands, while still applying
    # _action_is_available() so portal boundaries remain strict.
    alias_matches: list[tuple[float, str]] = []
    input_tokens = set(normalized_input.split())

    for key, aliases_for_action in MULTILINGUAL_INTENT_ALIASES.items():
        if key not in ACTION_DEFINITIONS or not _action_is_available(key, is_employer):
            continue
        if _is_category_route_key(key):
            continue

        for alias in aliases_for_action:
            a = normalize_text(alias)
            if not a:
                continue

            if normalized_input == a:
                alias_matches.append((100.0 if " " in a else 98.0, key))
                break

            # Whole-word match only. A plain `a in normalized_input`
            # substring check let a short alias like "speaking" (added for
            # "professional_speaking") match inside "professional speaking"
            # itself as if the category had been named directly, which is
            # exactly how "Open Professional Speaking" was being hijacked
            # to the Speaking & Presentation category before this function
            # ever got a chance to consider it might mean the individual
            # "Professional Speaking" activity instead.
            if re.search(r"(?<!\w)" + re.escape(a) + r"(?!\w)", normalized_input):
                alias_tokens = set(a.split())
                overlap = len(alias_tokens & input_tokens)
                score = 70.0 if " " in a else 55.0
                score += min(20.0, overlap * 8.0)
                alias_matches.append((score, key))

    # Strip multilingual action words so "dashboard kholo", "candidate
    # dikhao", "افتح الوظائف", etc. reduce to the actual target.
    stripped_tokens = [
        token for token in normalized_input.split()
        if token not in MULTILINGUAL_NAVIGATION_WORDS
    ]
    stripped = " ".join(stripped_tokens).strip()
    if stripped:
        for key, aliases_for_action in MULTILINGUAL_INTENT_ALIASES.items():
            if key not in ACTION_DEFINITIONS or not _action_is_available(key, is_employer):
                continue
            if _is_category_route_key(key):
                continue
            if any(normalize_text(alias) == stripped for alias in aliases_for_action):
                alias_matches.append((99.0, key))

    if alias_matches:
        alias_matches.sort(key=lambda item: item[0], reverse=True)
        return alias_matches[0][1]

    # ------------------------------------------------------------
    # DIRECT PAGE-NAME NAVIGATION
    # ------------------------------------------------------------
    # A user should not have to say "open" or "go to" when the message
    # is exactly a known page/action name.
    #
    # Examples:
    #   "Grammar"                    -> Grammar
    #   "Resume Builder"            -> Resume Builder
    #   "Roleplay"                  -> Roleplay
    #   "Home"                      -> Home
    #   "Dashboard"                -> Dashboard/profile action
    #   "Writing & Correspondence" -> activity category resolver handles it
    #
    # We deliberately require an exact canonical label or an exact
    # unambiguous keyword. This prevents normal sentences such as
    # "I want to improve my grammar" from accidentally navigating.
    direct_matches: list[tuple[float, str]] = []

    ambiguous_keywords = {
        "login",
        "sign in",
        "profile",
        "my profile",
        "student",
        "candidate",
        "employee",
        "employer",
        "company",
        "job",
        "jobs",
        "application",
        "applications",
        "opening",
        "openings",
        "practice",
        "activities",
        "activity",
        "lesson",
        "lessons",
        "dashboard",
    }

    for key, config in ACTION_DEFINITIONS.items():
        if not _action_is_available(key, is_employer):
            continue
        if _is_category_route_key(key):
            continue

        label = normalize_text(str(config.get("label", "")))

        # Exact canonical label is always safe.
        if label and normalized_input == label:
            direct_matches.append((100.0, key))
            continue

        # Support common visible page names that are represented as
        # keywords rather than labels (e.g. "Dashboard").
        for keyword in config.get("keywords", []):
            normalized_keyword = normalize_text(keyword)

            if (
                normalized_keyword
                and normalized_input == normalized_keyword
                and normalized_keyword not in ambiguous_keywords
            ):
                direct_matches.append((90.0, key))
                break

    # "Dashboard" is intentionally resolved here only when there is a
    # single canonical dashboard action. This avoids accidental login/
    # profile routing from generic words.
    if normalized_input == "dashboard":
        if "profile" in ACTION_DEFINITIONS and _action_is_available("profile", is_employer):
            direct_matches.append((95.0, "profile"))

    if direct_matches:
        direct_matches.sort(key=lambda item: item[0], reverse=True)
        return direct_matches[0][1]

    # Preserve the existing fast English resolver.
    if _has_navigation_verb(message):
        best_key = None
        best_score = 0.0
        for key, config in ACTION_DEFINITIONS.items():
            if not _action_is_available(key, is_employer):
                continue
            if _is_category_route_key(key):
                continue
            score = _intent_score(normalized_input, config)
            if score > best_score:
                best_key, best_score = key, score
        if best_score >= 1.8:
            return best_key

    # Language-independent resolver for natural non-English/mixed-language requests.
    # This is a full round trip to the Sarvam API just to get back a single
    # word — worth paying for when the message could plausibly be navigation,
    # not for every ordinary question that reaches this point. Both helpers
    # already cover the supported non-English languages (verbs and feature
    # names alike), so this only skips the call when there is genuinely no
    # navigation signal to classify.
    if not (_has_navigation_verb(message) or _has_multilingual_navigation_signal(message)):
        return None

    # The Sarvam round trip (3-4s) is the biggest chatbot-nav latency. Callers
    # run the fast local matchers first with use_ai=False; only when everything
    # local misses do they call again with use_ai=True to pay for the LLM.
    if not use_ai:
        return None

    return _ai_resolve_navigation_intent(message, language, api_key, is_employer)


def _localized_opening(label: str, language: str = "english") -> str:
    """Localized "Opening <label>." frame, matching the frontend's
    getLocalizedActionResponse fallback so a backend-resolved nav (e.g. Listen &
    Learn via ?category=) reads the same as a frontend-resolved one (Aptitude)."""
    lang = (language or "english").lower()
    # A category label ("Listen & Learn") is also an action label, so it gets
    # its translated name; individual activity titles stay as proper names.
    key = next((k for k, a in ACTION_DEFINITIONS.items() if a.get("label") == label), "")
    label = section_name(key, lang, label)
    if lang == "hindi":
        return f"{label} खोल रहा हूँ।"
    if lang == "arabic":
        return f"جارٍ فتح {label}."
    if lang == "russian":
        return f"Открываю {label}."
    if lang in ("vietnam", "vietnamese"):
        return f"Đang mở {label}."
    return f"Opening {label}."


def resolve_activity_navigation_payload(message: str, is_employer: bool = False, user: Any = None, language: str = "english") -> dict[str, Any] | None:
    """
    FINAL ACTIVITY NAVIGATION RESOLVER

    Priority is intentionally:

      1. Exact category request
      2. Strong category phrase request
      3. Exact activity/sub-activity request
      4. Strong activity request

    This prevents:
        "go to negotiation and meetings"
    from being incorrectly matched to:
        "Business Negotiation Simulation"

    Instead it opens:
        /activities/?category=negotiation

    while:
        "go to Business Negotiation Simulation"
    still opens:
        /activities/<id>/
    """
    if is_employer:
        return None
        
    normalized_input = normalize_text(message)
    if not normalized_input:
        return None

    try:
        from activities.models import Activity, SubActivity
        from activities.views import FREE_PLAN_ACTIVITY_TITLES
    except Exception:
        return None

    activities = list(
        Activity.objects
        .filter(is_active=True)
        .only("id", "title", "category", "order", "objective")
    )
    
    sub_activities = list(
        SubActivity.objects
        .select_related("activity")
        .filter(activity__is_active=True)
        .only("id", "title", "activity__id", "activity__title", "activity__category", "activity__order", "activity__objective")
    )

    if not activities:
        return None

    # ------------------------------------------------------------
    # Request-language detection
    # ------------------------------------------------------------
    navigation_words = {
        "go", "open", "navigate", "take", "show", "start", "launch",
        "visit", "move", "redirect", "practice", "practise", "try",
        "learn", "exercise", "exercises", "activity", "activities",
        "lesson", "lessons", "module", "training", "page",
        "want", "would", "like", "let", "can", "could", "please",
        "to", "me", "i", "my", "the", "a", "an", "register", "sign", "up",
        "karo", "kholo", "khulna", "kholna", "dikhao", "jao", "chalo", "batao",
        "ओपन", "करो", "खोलो", "खोलें", "खोलना", "ले चलो", "दिखाओ", "जाओ", "शुरू करो", "शुरू करें", "रजिस्ट्रेशन", "रजिस्टर",
    }

    has_navigation_language = bool(
        re.search(
            r"\b(go|open|navigate|take|show|start|launch|visit|move|"
            r"redirect|practice|practise|try|learn|exercise|exercises|"
            r"activity|activities|lesson|lessons|module|training|"
            r"page|want to|would like|i want|i would like|"
            r"let me|can i|could i|"
            r"register|sign up|"
            r"karo|kholo|khulna|kholna|dikhao|jao|chalo|batao)\b",
            normalized_input,
        )
        or any(x in normalized_input for x in MULTILINGUAL_NAVIGATION_SIGNALS)
    )

    # No early bail on "what is …". A question that NAMES an activity/section
    # must OPEN it AND describe it, locally (no LLM). Generic advice ("how do I
    # improve listening?") names no section, so the matchers below score < 12 and
    # this still returns None → LLM at the end.
    informational = _is_informational_question(message)

    def _describe(base_reply: str, objective: str) -> str:
        obj = (objective or "").strip()
        return f"{base_reply} {obj}" if (informational and obj) else base_reply

    def _single_category_objective(category_value: str) -> str:
        matches = [a for a in activities
                   if normalize_text(str(a.category or "")) == normalize_text(str(category_value or ""))]
        return (matches[0].objective or "") if len(matches) == 1 else ""

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def category_route(category_value: str) -> str:
        return (
            "/activities/?category="
            + quote(category_value, safe="")
        )

    def category_action_info():
        """
        Build canonical category information from ACTION_DEFINITIONS.

        Only actions whose route points to /activities/module/... are
        treated as activity categories.
        """
        result = []

        for key, config in ACTION_DEFINITIONS.items():
            route = str(config.get("route", ""))
            if "/activities/?category=" not in route:
                continue

            label = str(config.get("label", "")).strip()
            normalized_label = normalize_text(label)

            keywords = [
                normalize_text(k)
                for k in config.get("keywords", [])
                if normalize_text(k)
            ]

            # Remove generic one-word navigation terms. We want category
            # phrases such as "negotiation and meetings", not "open".
            useful_keywords = [
                k for k in keywords
                if len(k.split()) >= 2
                or k in {
                    "negotiation",
                    "vocabulary",
                    "speaking",
                    "writing",
                    "communication",
                    "analysis",
                    "workshop",
                    "gd",
                    "jam",
                    "roleplay",
                    "discussion",
                }
            ]

            result.append({
                "key": key,
                "label": label,
                "label_normalized": normalized_label,
                "keywords": useful_keywords,
                "route": route,
                "response": config.get(
                    "response",
                    f"Opening {label}.",
                ),
            })

        return result

    categories = category_action_info()

    # ------------------------------------------------------------
    # 1. CATEGORY MATCH FIRST
    # ------------------------------------------------------------
    #
    # This is the critical fix.
    #
    # "go to negotiation and meetings"
    # must match the complete category phrase before any child activity
    # containing "negotiation" gets considered.
    #
    best_category = None
    best_category_score = 0.0

    for category in categories:
        label = category["label_normalized"]

        if not label:
            continue

        score = 0.0

        # Exact category label.
        if normalized_input == label:
            score = 100.0

        # The visible label may use "&", while ACTION_DEFINITIONS may use
        # "and". normalize_text() makes both comparable.
        if label and label in normalized_input:
            score = max(score, 95.0)

        # Strong canonical keyword phrase.
        for keyword in category["keywords"]:
            if len(keyword.split()) >= 2 and keyword in normalized_input:
                score = max(score, 90.0)

        # Also recognize "go to <category>" where the category itself is
        # represented by multiple words.
        stripped = normalized_input
        for word in navigation_words:
            stripped = re.sub(
                rf"\b{re.escape(word)}\b",
                " ",
                stripped,
            )
        stripped = re.sub(r"\s+", " ", stripped).strip()

        if stripped and (
            stripped == label
            or any(
                len(keyword.split()) >= 2 and stripped == keyword
                for keyword in category["keywords"]
            )
        ):
            score = max(score, 100.0)

        if score > best_category_score:
            best_category_score = score
            best_category = category

    if best_category and best_category_score >= 90.0:
        # Use the actual DB category value so the existing Activities page
        # receives the correct query parameter.
        category_values = [
            str(activity.category).strip()
            for activity in activities
            if activity.category
        ]

        selected_value = None

        # Match the category label/keywords to the database category.
        category_key = best_category["key"]
        route_str = best_category["route"]
        if "?category=" in route_str:
            route_fragment = route_str.split("?category=")[-1]
        else:
            route_fragment = route_str.rstrip("/").split("/")[-1]

        for value in category_values:
            normalized_value = normalize_text(value)

            if normalized_value == normalize_text(route_fragment):
                selected_value = value
                break

            # Fallback: compare category keyword/name with DB value.
            if (
                normalize_text(value) == best_category["label_normalized"]
                or normalize_text(value) in best_category["label_normalized"]
                or best_category["label_normalized"] in normalize_text(value)
            ):
                selected_value = value
                break

        # Known category routes use their route fragment as a reliable
        # fallback when the DB stores the same category under a canonical key.
        if not selected_value:
            selected_value = route_fragment

        # Interactive Workshop is fully premium. All three Workshop
        # sub-activities (GD, JAM and Roleplay) are premium as well.
        is_workshop_category = (
            category_key == "workshop"
            or normalize_text(selected_value) == "workshop"
            or normalize_text(route_fragment) == "workshop"
        )

        has_premium_access = _is_premium_action_allowed("workshop", user)

        if not has_premium_access:
            if is_workshop_category:
                return {
                    "reply": message_text("upgrade_feature", language),
                    "actions": [
                        _build_action("pro", "Membership", "/pro/")
                    ],
                    "source": "intent",
                }

            has_free_activity = any(
                str(act.category).strip() == selected_value and act.title in FREE_PLAN_ACTIVITY_TITLES
                for act in activities
            )
            if not has_free_activity:
                return {
                    "reply": message_text("upgrade_activity", language),
                    "actions": [
                        _build_action("pro", "Membership", "/pro/")
                    ],
                    "source": "intent",
                }

        # A category holding exactly one activity (Listen & Learn) opens that
        # activity directly; the listing would only redirect there anyway.
        only = [a for a in activities if str(a.category).strip() == selected_value]
        if len(only) == 1:
            return {
                "reply": _describe(_localized_opening(best_category["label"], language), only[0].objective),
                "actions": [_build_action(f"activity_{only[0].pk}", only[0].title, f"/activities/{only[0].pk}/")],
                "source": "intent",
            }

        return {
            "reply": _describe(_localized_opening(best_category["label"], language), _single_category_objective(selected_value)),
            "actions": [
                _build_action(
                    best_category["key"],
                    best_category["label"],
                    category_route(selected_value),
                )
            ],
            "source": "intent",
        }

    # ------------------------------------------------------------
    # 2. EXACT / STRONG SUB-ACTIVITY MATCH
    # ------------------------------------------------------------
    #
    # Only reached after category matching has failed.
    # Therefore "negotiation and meetings" cannot accidentally select a
    # child activity just because it contains "negotiation".
    stop_words = {
        "i", "want", "would", "like", "to", "the", "a", "an",
        "me", "my", "please", "can", "could", "you", "help",
        "get", "take", "show", "open", "go", "start", "launch",
        "visit", "move", "redirect", "let", "try", "do",
        "practice", "practise", "activity", "activities",
        "page", "module", "lesson", "lessons", "training",
        "learn", "learning", "exercise", "exercises", "session",
        "and",
    }

    input_tokens = set(normalized_input.split())
    meaningful_input_tokens = {
        token for token in input_tokens
        if token not in stop_words
    }

    best_match = None
    best_match_type = None # 'activity' or 'sub_activity'
    best_match_score = 0.0

    # Helper for scoring
    def score_item(title):
        base_title = str(title)
        aliases = ACTIVITY_MULTILINGUAL_ALIASES.get(base_title, [base_title])
        score = 0.0
        
        for alias in aliases:
            alias_normalized = normalize_text(alias)
            if not alias_normalized:
                continue

            current_score = 0.0

            if alias_normalized == normalized_input:
                current_score = 100.0
            elif alias_normalized in normalized_input:
                current_score = 50.0

            alias_tokens = alias_normalized.split()
            meaningful_alias_tokens = [
                token
                for token in alias_tokens
                if token not in stop_words
            ]

            overlap = sum(
                1
                for token in meaningful_alias_tokens
                if token in meaningful_input_tokens
            )

            if meaningful_alias_tokens:
                ratio = overlap / len(meaningful_alias_tokens)
                current_score += overlap * 4.0

                if ratio >= 0.80:
                    current_score += 10.0
                elif ratio >= 0.60:
                    current_score += 5.0

            if overlap <= 1 and alias_normalized != normalized_input:
                current_score = min(current_score, 4.0)

            if current_score > score:
                score = current_score
        return score

    for sub_act in sub_activities:
        score = score_item(sub_act.title)
        if score > best_match_score:
            best_match_score = score
            best_match = sub_act
            best_match_type = 'sub_activity'

    for activity in activities:
        score = score_item(activity.title)
        if score > best_match_score:
            best_match_score = score
            best_match = activity
            best_match_type = 'activity'

    if best_match and best_match_score >= 12.0:
        if best_match_type == 'sub_activity':
            act = best_match.activity
            is_workshop_child = (normalize_text(str(act.category or "")) == "workshop")
        else:
            act = best_match
            is_workshop_child = (normalize_text(str(act.category or "")) == "workshop")

        if is_workshop_child:
            title_lower = act.title.lower()
            if "group discussion" in title_lower:
                premium_key = "gd"
            elif "jam" in title_lower:
                premium_key = "jam"
            elif "role play" in title_lower or "roleplay" in title_lower:
                premium_key = "roleplay"
            else:
                premium_key = "workshop"
        else:
            premium_key = "workshop"

        has_premium_access = _is_premium_action_allowed(premium_key, user)

        if not has_premium_access and (
            is_workshop_child
            or act.title not in FREE_PLAN_ACTIVITY_TITLES
        ):
            return {
                "reply": message_text("upgrade_feature", language)
                if is_workshop_child
                else message_text("upgrade_activity", language),
                "actions": [
                    _build_action("pro", "Membership", "/pro/")
                ],
                "source": "intent",
            }
            
        _obj = getattr(act, "objective", "")
        if best_match_type == 'sub_activity':
            return {
                "reply": _describe(_localized_opening(best_match.title, language), _obj),
                "actions": [
                    _build_action(
                        f"sub_activity_{best_match.pk}",
                        best_match.title,
                        f"/activities/{act.pk}/sub/{best_match.pk}/",
                    )
                ],
                "source": "intent",
            }
        else:
            return {
                "reply": _describe(_localized_opening(best_match.title, language), _obj),
                "actions": [
                    _build_action(
                        f"activity_{best_match.pk}",
                        best_match.title,
                        f"/activities/{best_match.pk}/",
                    )
                ],
                "source": "intent",
            }

    # ------------------------------------------------------------
    # 3. Standalone category name fallback
    # ------------------------------------------------------------
    #
    # Covers exact DB category names even if ACTION_DEFINITIONS does not
    # contain a matching canonical action.
    if not has_navigation_language:
        for activity in activities:
            db_category = normalize_text(str(activity.category or ""))

            if db_category and db_category == normalized_input:
                is_workshop_category = (
                    normalize_text(str(activity.category or "")) == "workshop"
                )
                has_premium_access = _is_premium_action_allowed("workshop", user)

                if not has_premium_access:
                    if is_workshop_category:
                        return {
                            "reply": message_text("upgrade_feature", language),
                            "actions": [
                                _build_action("pro", "Membership", "/pro/")
                            ],
                            "source": "intent",
                        }

                    has_free_activity = any(
                        str(act.category).strip() == str(activity.category).strip() and act.title in FREE_PLAN_ACTIVITY_TITLES
                        for act in activities
                    )
                    if not has_free_activity:
                        return {
                            "reply": message_text("upgrade_activity", language),
                            "actions": [
                                _build_action("pro", "Membership", "/pro/")
                            ],
                            "source": "intent",
                        }

                return {
                    "reply": f"Opening {activity.category}.",
                    "actions": [
                        _build_action(
                            f"category_{activity.category}",
                            str(activity.category),
                            category_route(str(activity.category)),
                        )
                    ],
                    "source": "intent",
                }

    return None

def build_unknown_command_payload(language: str = "english") -> dict[str, Any]:
    lang = normalize_language(language)
    return {
        "reply": LANGUAGE_REPLY_TRANSLATIONS.get(lang, LANGUAGE_REPLY_TRANSLATIONS["english"])["unknown"],
        "actions": [],
        "source": "fallback",
        "is_unknown_command": True,
    }


def build_fallback_payload(message: str, page: str, path: str, language: str = "english", is_employer: bool = False) -> dict[str, Any]:
    context = _page_context(page, path, is_employer)
    lang = normalize_language(language, message)
    replies = {
        "english": context["default_reply"],
        "hindi": "मैं इस पेज पर आपकी मदद कर सकता हूँ। आप किसी उपलब्ध फीचर या प्रैक्टिस मॉड्यूल के बारे में पूछ सकते हैं।",
        "vietnamese": "Tôi có thể giúp bạn trên trang này. Bạn có thể hỏi về các tính năng hoặc mô-đun luyện tập hiện có.",
        "arabic": "يمكنني مساعدتك في هذه الصفحة. يمكنك السؤال عن الميزات أو وحدات التدريب المتاحة.",
        "russian": "Я могу помочь вам на этой странице. Вы можете спросить о доступных функциях или модулях практики.",
        "telugu": "ఈ పేజీలో నేను మీకు సహాయం చేయగలను. అందుబాటులో ఉన్న ఫీచర్లు లేదా ప్రాక్టీస్ మాడ్యూల్స్ గురించి అడగండి.",
        "tamil": "இந்தப் பக்கத்தில் நான் உங்களுக்கு உதவ முடியும். கிடைக்கும் அம்சங்கள் அல்லது பயிற்சி தொகுதிகளைப் பற்றி கேட்கலாம்.",
    }
    return {
        "reply": replies.get(lang, replies["english"]),
        "actions": _build_actions(context["action_keys"], is_employer),
        "source": "fallback",
        "language": lang,
    }


def _matches_terms(message: str, terms: Any) -> bool:
    normalized_message = normalize_text(message)
    for term in terms:
        normalized_term = normalize_text(term)
        if not normalized_term:
            continue
        if " " in normalized_term:
            if normalized_term in normalized_message:
                return True
            continue
        if re.search(rf"\b{re.escape(normalized_term)}\b", normalized_message):
            return True
    return False


def _quick_guidance_payload(message: str, page: str, path: str, user_name: str | None = None, is_employer: bool = False) -> dict[str, Any] | None:
    msg_lower = message.lower()
    # Bypass quick guidance for explicit conceptual questions so the AI can answer them
    if any(q in msg_lower for q in ["what is", "difference", "explain", "meaning"]):
        return None

    context = _page_context(page, path, is_employer)
    normalized_page = (page or "").strip().lower()
    normalized_path = (path or "").strip().lower()
    context_pages = {normalized_page}

    if "/speaking/" in normalized_path:
        context_pages.add("speaking")
    if "/listening/" in normalized_path:
        context_pages.add("listening")
    if "/reading/" in normalized_path:
        context_pages.add("reading")
    if "/writing/" in normalized_path:
        context_pages.add("writing")
    if "/interview/" in normalized_path:
        context_pages.add("interview")
    if "/resume-builder/" in normalized_path:
        context_pages.add("resume_builder")
    if "/subject/" in normalized_path:
        context_pages.add("subject")
    if "/lessons/storytelling/" in normalized_path:
        context_pages.add("storytelling")
    if "/lessons/situations/" in normalized_path:
        context_pages.add("situations")
    if "/lessons/roleplay/" in normalized_path:
        context_pages.add("roleplay")

    for pattern in QUICK_GUIDANCE_PATTERNS:
        if not _matches_terms(message, pattern["match_terms"]):
            continue
        if pattern["pages"].isdisjoint(context_pages):
            continue
        reply = pattern["reply"]
        if user_name:
            reply = f"Hi {user_name}! {reply}"
        return {
            "reply": reply,
            "actions": _build_actions(pattern["action_keys"], is_employer),
            "source": "fallback",
        }

    if _matches_terms(message, ["improve", "better", "help me", "what should i do", "tips"]):
        reply = context["default_reply"]
        if user_name:
            reply = f"Hi {user_name}! {reply}"
        return {
            "reply": reply,
            "actions": _build_actions(context["action_keys"][:2], is_employer),
            "source": "fallback",
        }

    return None


def _fast_reply_payload(message: str, page: str, path: str, user_name: str | None = None, is_employer: bool = False) -> dict[str, Any] | None:
    context = _page_context(page, path, is_employer)
    for pattern in FAST_REPLY_PATTERNS:
        if not _matches_terms(message, pattern["match_terms"]):
            continue
        action_keys = pattern["action_keys"] or context["action_keys"][:1]
        reply = pattern["reply"]
        if user_name:
            reply = f"Hi {user_name}! {reply}"
        return {
            "reply": reply,
            "actions": _build_actions(action_keys, is_employer),
            "source": "fallback",
        }
    return None


def _limit_reply(text: str) -> str:
    cleaned = text or ""
    # Remove any <think>...</think> tags and their content
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    # Remove any remaining standalone <think> or </think> tags
    cleaned = re.sub(r"</?think>", "", cleaned)
    
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"[*_`#>\-\[\]]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}


APP_KNOWLEDGE_BASE = (
    "APP KNOWLEDGE BASE (Use this to answer questions intelligently like a PRO!):\n"
    "Career Buddy LMS is an AI-powered platform for Students (Job Seekers) and Employers.\n"
    "\nSTUDENT/JOB SEEKER FEATURES:\n"
    "- Dashboard (/student/student/dashboard/): Central hub where a student can see their total progress, learning tracks, and upcoming activities. It is used to track overall performance.\n"
    "- Activities (/activities/): A complete list of all practice lessons covering various skills.\n"
    "- Professional Speaking: Practice speaking, presentation, and fluency.\n"
    "- Writing and Correspondence: Practice writing professional emails, essays, and passages.\n"
    "- Vocabulary & Idioms: Learn and practice new words, idioms, and phrases.\n"
    "- Negotiation & Meetings: Learn how to conduct professional meetings and negotiations.\n"
    "- Professional Communication: Improve overall workplace communication skills.\n"
    "- Analysis & Reporting: Practice analytical thinking and creating professional reports.\n"
    "- Grammar (/subject/): Visual grammar lessons to improve sentence formation and parts of speech.\n"
    "- Workshops (GD & JAM): Group Discussion (GD) with AI personalities, and JAM (Just A Minute) solo speaking practice to build confidence.\n"
    "- Roleplay (/roleplay/): Interactive conversation roleplay for real-world situations and storytelling.\n"
    "- Resume Builder / Resume Parsing (/resume-builder/): A powerful tool where students upload their resume to get an ATS score, parse details, analyze skills, and get AI mock interview questions tailored to their resume.\n"
    "- Resume Parsing limits: Free plan gets 4 resume analyses in total; paid plans are unlimited.\n"
    "- AI Mock Interview: Practice interviewing with an AI recruiter based on your resume. Paid plans only (Normal or Pro), and it unlocks only when the resume's ATS score is 90% or above. Scoring below 90% in the interview shows a 'Skill up yourself' button to the chosen role's Skill Up content.\n"
    "- Job Search: Premium (Pro) feature to find jobs matching resume skills. Requires a score of 90% or above in the AI Mock Interview.\n"
    "- English & Vocab: CEFR-aligned English from A1 to C2, 10-step phonics ladder, vocabulary lexicons, interactive grammar set.\n"
    "- Aptitude: Quantitative aptitude, logical reasoning, verbal ability, situational judgment, cognitive speed, coaching tracks, and question banks.\n"
    "- Tech: Long-form technical guides covering programming (Python), DSA, OOP, databases, AI/ML, agents, vector search, and system design.\n"
    "- Certifications (/skill-up/#section-certifications): There are 3 Skill Up certifications a student can earn -- English & Vocab, Aptitude, and Tech. Each is unlocked by scoring above 70 on that module's Skill Up Mock Test, after which the student enters their name and downloads a Career Buddy certificate PDF as proof of that skill for their resume or LinkedIn profile. Available to both Free and Pro users.\n"
    "- Pro Membership (/pro/): Upgrade to unlock premium features like Job Search and unlimited AI interactions.\n"
    "- Sitemap & Browse All: Complete site architecture, fully clickable to explore the platform at a glance.\n"
    "- Student Login & Registration: Pages to sign in or create a new free candidate account.\n"
    "\nEMPLOYER FEATURES:\n"
    "- Employer Portal / Dashboard: The main portal for recruiters. Used to track company hiring progress and manage the recruitment lifecycle.\n"
    "- Company Profile: Update the business details and employer branding.\n"
    "- Post New Job: Create and publish new job openings to attract candidates.\n"
    "- Job Openings: View and manage all currently posted jobs by the company.\n"
    "- All Applications: Review job applications submitted by candidates for the posted jobs.\n"
    "- Find Candidates: Proactively search the platform's database of candidate resumes by required skills.\n"
    "- Employer Login & Registration: Pages for recruiters and companies to sign in or sign up.\n"
    "\nINSTRUCTIONS FOR YOU:\n"
    "1. You must act as a PRO-LEVEL ASSISTANT.\n"
    "2. If the user asks 'what is the use of [feature]?', 'what is [feature]?', or 'tell me about [feature]', answer them accurately and thoroughly using the knowledge above.\n"
    "3. ALWAYS map their request to the closest allowed action key to navigate them there if they want to access it.\n"
    "4. Format sentences professionally."
)


#: Register guidance shared by the blocking and the streaming AI paths.
#:
#: Everything in the surrounding prompts is a correctness rule: what Buddy may
#: claim, and where it is allowed to navigate. This block is about how it
#: sounds. Buddy was factually right but read like a status line — "Opening
#: the grammar section." and nothing further — which is what users experience
#: as robotic, and which leaves them with no idea what to ask next.
BUDDY_VOICE_AND_MANNER = (
    "HOW TO SOUND:\n"
    "- Talk like a helpful human colleague, not a system notification. "
    "Vary your sentence openings; never reuse the same phrasing twice in a "
    "conversation.\n"
    "- Answers are spoken aloud, so write for the ear: short sentences, no "
    "bullet characters, no numbered lists, no symbols a voice cannot read.\n"
    "- Keep it to two or three sentences unless the user asked for depth. "
    "Long answers are tiring to listen to.\n"
    "- When you navigate somewhere, do not stop at announcing it. Say what "
    "the user will find there, name two or three concrete things they can do "
    "next, and invite them to pick one. Carry them into the next step.\n"
    "- Use the user's name occasionally where it feels natural, such as a "
    "greeting or a word of encouragement. Never in every message.\n"
    "- Acknowledge what the user actually said before answering it, so the "
    "reply feels heard rather than dispatched.\n"
    "- If a request is ambiguous, ask one short clarifying question instead "
    "of guessing.\n"
    "- Never repeat a sentence you have already said in this conversation. "
    "If you have just said something, say the next thing."
)


def _generate_ai_payload(message: str, page: str, path: str, input_mode: str, api_key: str, user_name: str | None = None, language: str = "english", is_employer: bool = False, user: Any = None, skillup_grounding: dict[str, Any] | None = None) -> dict[str, Any]:
    context = _page_context(page, path, is_employer)
    allowed_actions = {key: value["label"] for key, value in ACTION_DEFINITIONS.items() if _action_is_available(key, is_employer)}
    other_portal_actions = {key: value["label"] for key, value in ACTION_DEFINITIONS.items() if not _action_is_available(key, is_employer)}

    normalized_language = normalize_language(language, message)
    language_name = SUPPORTED_LANGUAGES.get(normalized_language, {"name": normalized_language})["name"]
    name_part = f"The user's name is {user_name}. " if user_name else ""
    system_prompt = (
        f"You are Buddy, a production-grade assistant for this English-learning platform. {name_part}"
        f"The user's selected language is {language_name}. You MUST reply flawlessly in the same language as the user (e.g., Vietnamese, Hindi, Arabic, Russian, etc.). "
        f"{APP_KNOWLEDGE_BASE}\n\n"
        "Understand intent even when the user uses another supported language, spelling mistakes, or mixed languages. "
        "NEVER invent an application feature, page, route, button, or capability. "
        "The only navigable features are the allowed_actions supplied by the server. "
        "If the user asks for a feature in other_portal_actions, politely inform them that this feature is available in the other portal (Employer/Job Seeker portal) and return <NAV:none>. "
        "If the user asks to open, find, use, start, access, or navigate to a feature that is NOT in either list, reply that the feature is not available in this application and use <NAV:none>. "
        "If the user asks to navigate to an allowed feature, choose exactly one matching action key. "
        "If the user asks an informational, learning, or general question, use <NAV:none> and provide a comprehensive, pro-level answer that directly and thoroughly addresses their query. "
        "Be friendly and professional, plain text only. Never output HTML, markdown, <think> tags, or internal reasoning. "
        "The FIRST characters of your response MUST be <NAV:key> or <NAV:none>.\n\n"
        + BUDDY_VOICE_AND_MANNER
    )
    user_payload = {
        "message": (message or "").strip(),
        "page": context["name"],
        "page_summary": context["summary"],
        "input_mode": (input_mode or "voice").strip().lower() or "voice",
        "allowed_actions": allowed_actions,
        "other_portal_actions": other_portal_actions,
    }

    # Skill Up grounding: rules are APPENDED so every existing rule
    # (<NAV:key> first, allowed_actions only, reply in the user's language)
    # still applies unchanged.
    if skillup_grounding:
        system_prompt = system_prompt + "\n\n" + SKILL_UP_PROMPT_RULES
        user_payload["skill_up_context"] = skillup_grounding

    response = requests.post(
        SARVAM_CHAT_URL,
        headers={
            "api-subscription-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "model": getattr(settings, 'SARVAM_MODEL', 'sarvam-105b'),
            # Raised from 0.4: the grounding rules above are hard constraints, so
            # the extra latitude buys natural, varied phrasing rather than
            # freedom to invent facts.
            "temperature": 0.6,
            "max_tokens": 1000,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            "reasoning_effort": None,
        },
        timeout=8.0,
    )
    response.raise_for_status()
    payload = response.json()
    content = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    requested_action_keys = []
    reply = content
    # Tolerate a missing '>' (the model sometimes truncates the tag): match keys
    # up to '>' or end-of-line.
    nav_match = re.match(r"^\s*<NAV:([^>\n]*)>?", content)
    if nav_match:
        keys_str = nav_match.group(1)
        if keys_str.lower() != "none":
            requested_action_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        reply = content[nav_match.end():].strip()
    # Defensive scrub: if the tag was malformed enough that the parse above did
    # not consume it (e.g. a bare "<NAV" with no colon, or "<NAV:skillup" cut off
    # mid-token), strip any leading NAV fragment so it never leaks into the UI.
    reply = re.sub(r"^\s*<\s*NAV\b[^>]*>?\s*", "", reply, flags=re.IGNORECASE)

    reply = _limit_reply(reply)
    if not reply:
        raise ValueError("Missing assistant reply")

    # Skill Up navigation keys are namespaced and validated against the
    # catalog. A key the model invented resolves to nothing and is dropped,
    # so an arbitrary URL can never reach performAction().
    skillup_actions = []
    if requested_action_keys:
        namespaced = [k for k in requested_action_keys if k.startswith("skillup:")]
        if namespaced:
            try:
                from .skillup_service import SkillUpKnowledgeService
                _svc = SkillUpKnowledgeService()
                if _svc.available:
                    for key in namespaced:
                        entity_id = key.split(":", 1)[1]
                        entity = _svc.manifest.lessons_by_id.get(entity_id)
                        if entity is None:
                            entity = next(
                                (sec for sec in _svc.get_sections()
                                 if sec.section_id == entity_id), None
                            )
                        if entity is None:
                            continue
                        route = _svc.get_navigation_route(entity)
                        if route and _svc.route_is_trusted(route):
                            skillup_actions.append({
                                "key": key,
                                "label": entity.title,
                                "route": route,
                                "response": f"Opening {entity.title}.",
                            })
            except Exception:
                skillup_actions = []
        requested_action_keys = [k for k in requested_action_keys
                                 if not k.startswith("skillup:")]

    # First, match the exact keys from the raw generated list
    action_keys = []
    for key in requested_action_keys:
        if key in ACTION_DEFINITIONS and _action_is_available(key, is_employer):
            action_keys.append(key)
            if len(action_keys) >= 2:
                break

    # If not enough matched, fall back to checking text occurrences
    if len(action_keys) < 2:
        for key in ACTION_DEFINITIONS:
            if key not in action_keys and _action_is_available(key, is_employer):
                # Simple heuristic check for key existence in text
                if key in content.lower():
                    action_keys.append(key)
                    if len(action_keys) >= 2:
                        break

    # If still not enough, fill with context defaults
    if len(action_keys) < 2:
        for key in context["action_keys"]:
            if key not in action_keys and _action_is_available(key, is_employer):
                action_keys.append(key)
                if len(action_keys) >= 2:
                    break
    
    # FINAL HARD BOUNDARY: reject premium navigation before returning any
    # action generated by the non-streaming AI payload path.
    for key in action_keys:
        portal_block = validate_portal_navigation(key, is_employer, normalized_language)
        if portal_block:
            return portal_block

        premium_block = _premium_navigation_block(key, user, is_employer, normalized_language)
        if premium_block:
            premium_block["language"] = normalized_language
            return premium_block

    # If LLM returned exactly 1 valid action, consider it a strong intent
    source = "ai"
    if len(action_keys) == 1 and requested_action_keys:
        source = "intent"

    # (Plan checks are now handled exclusively by _premium_navigation_block above)
    final_action_keys = []
    for key in action_keys:
        if key == "mock_interview":
            from career_app.views import has_parsed_resume
            if not has_parsed_resume(user):
                reply = message_text("parse_resume_first", normalized_language)
                final_action_keys = ["resume_builder"]
                source = "intent"
                break
            else:
                final_action_keys.append(key)
        elif key == "job_search":
                passed = False
                if user and user.is_authenticated:
                    from career_app.models import ResumeInterviewSession
                    try:
                        latest_session = ResumeInterviewSession.objects.filter(resume__user=user, is_completed=True).latest('start_time')
                        if latest_session.total_score is not None and latest_session.total_score >= 90:
                            passed = True
                    except ResumeInterviewSession.DoesNotExist:
                        pass
                if not passed:
                    reply = "To unlock Job Search, you must score at least 90% in your AI Mock Interview."
                    final_action_keys = ["mock_interview"]
                    source = "intent"
                    break
                else:
                    final_action_keys.append(key)
        else:
            final_action_keys.append(key)

    action_keys = final_action_keys

    # Validated Skill Up actions are appended last, after every premium and
    # role check above has already run on the standard action keys.
    actions = _build_actions(action_keys, is_employer)
    if skillup_actions:
        existing_routes = {a.get("route") for a in actions}
        for action in skillup_actions:
            if action["route"] not in existing_routes and len(actions) < 4:
                actions.append(action)

    return {
        "reply": reply,
        "actions": actions,
        "source": source,
        "language": normalized_language,
    }


def riya_chat_logic(message: str, page: str = "unknown", user_name: str | None = "there", path: str = "/", input_mode: str = "text", api_key: str | None = None, language: str = "english", is_employer: bool = False, user: Any = None) -> dict[str, Any]:
    language = normalize_language(language, message)
    if api_key is None:
        api_key = getattr(settings, "SARVAM_API_KEY", "")

    # ── Skill Up (additive) ──────────────────────────────────────────────
    # Returns None for anything that is not a Skill Up question, so every
    # existing path below is reached completely unchanged. Skill Up is free
    # static content and this layer can only ever emit Skill Up catalog
    # routes, so sitting above the premium check cannot weaken it.
    skillup_grounding = None
    try:
        skillup = skillup_try_handle(message, path=path, page=page, language=language)
    except Exception:
        skillup = None                      # never break chat on a Skill Up fault
    if skillup is not None:
        if "_skillup_grounding" not in skillup:
            # CHECK ACCESS BEFORE RETURNING
            from core.skillup_access import has_full_skillup, is_locked_lesson
            if skillup.get("actions") and not has_full_skillup(user):
                allowed = True
                for act in skillup["actions"]:
                    route = act.get("route", "")
                    if "#load=" in route:
                        load_path = route.split("#load=")[-1]
                        if not load_path.startswith("/static/"):
                            load_path = "/static/001 Career Buddy/" + load_path
                        if is_locked_lesson(load_path):
                            allowed = False
                            break
                    elif "/skill-up/#" in route:
                        fragment = route.split("#")[-1].lower()
                        if "aptitude" in fragment or "tech" in fragment or "non_it" in fragment:
                            allowed = False
                            break
                if not allowed:
                    from career_app.views import message_text
                    reply = "🔒 This feature is available in a higher plan. Please Upgrade to avail this Feature."
                    actions = [_build_action("pro", "Membership", "/pro/")]
                    skillup = {"reply": reply, "actions": actions, "source": "intent", "language": language}

            if skillup is not None:
                return skillup
        else:
            skillup_grounding = skillup.get("_skillup_grounding")
    # ─────────────────────────────────────────────────────────────────────

    # PREMIUM NAVIGATION MUST BE CHECKED FIRST.
    # This prevents activity/category navigation from bypassing plan checks.
    # SPEED: fast local resolvers first (no Sarvam call); LLM classifier only as a
    # last resort when every local matcher missed — keeps nav ~1s instead of 3-4s.
    premium_nav_key = resolve_navigation_intent(message, language, api_key, user, use_ai=False)

    portal_block = validate_portal_navigation(premium_nav_key, is_employer, language)
    if portal_block:
        return portal_block

    premium_block = _premium_navigation_block(premium_nav_key, user, is_employer, language)
    if premium_block:
        premium_block["language"] = language
        return premium_block

    # Activity/category navigation runs after premium navigation so category
    # matching cannot accidentally bypass the subscription boundary. Local (DB) only.
    activity_navigation = resolve_activity_navigation_payload(message, is_employer, user, language)
    if activity_navigation:
        activity_navigation["language"] = language
        return activity_navigation

    # Nothing matched locally — now pay for the LLM navigation classifier.
    if not premium_nav_key:
        premium_nav_key = resolve_navigation_intent(message, language, api_key, user, use_ai=True)
        if premium_nav_key:
            portal_block = validate_portal_navigation(premium_nav_key, is_employer, language)
            if portal_block:
                return portal_block
            premium_block = _premium_navigation_block(premium_nav_key, user, is_employer, language)
            if premium_block:
                premium_block["language"] = language
                return premium_block

    nav_key = premium_nav_key
    if nav_key and nav_key in ACTION_DEFINITIONS:
        action = ACTION_DEFINITIONS[nav_key]
        # Plain "Opening X." for a bare open/navigate/guide; description (or the
        # child menu) only when the user ASKED ABOUT it ("what is X"). Local, no LLM.
        reply = _navigation_reply(nav_key, message, language, is_employer)

        if nav_key == "mock_interview":
            from career_app.views import has_parsed_resume
            if not has_parsed_resume(user):
                reply = message_text("parse_resume_first", language)
                actions = [_build_action("resume_builder", "Resume Builder", "/resume-builder/")]
                return {"reply": reply, "actions": actions, "source": "intent", "language": language}

        if nav_key == "job_search":
                passed = False
                if user and user.is_authenticated:
                    from career_app.models import ResumeInterviewSession
                    try:
                        latest_session = ResumeInterviewSession.objects.filter(resume__user=user, is_completed=True).latest('start_time')
                        if latest_session.total_score is not None and latest_session.total_score >= 90:
                            passed = True
                    except ResumeInterviewSession.DoesNotExist:
                        pass
                if not passed:
                    reply = message_text("score_for_job_search", language)
                    actions = [_build_action("mock_interview", "AI Mock Interview", "/resume-builder/")]
                    return {"reply": reply, "actions": actions, "source": "intent", "language": language}

        if nav_key == "about_app":
            return {"reply": reply, "actions": [], "source": "intent", "language": language}

        return {"reply": reply, "actions": _build_actions([nav_key], is_employer), "source": "intent", "language": language}


    quick_guidance = _quick_guidance_payload(message, page, path, user_name, is_employer)
    if quick_guidance:
        return quick_guidance
    
    fast_reply = _fast_reply_payload(message, page, path, user_name, is_employer)
    if fast_reply:
        return fast_reply

    if not api_key:
        return build_fallback_payload(message, page, path, language, is_employer)

    try:
        return _generate_ai_payload(message, page, path, input_mode, api_key, user_name, language, is_employer, user, skillup_grounding=skillup_grounding)
    except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return build_fallback_payload(message, page, path, language, is_employer)


def stream_assistant_response(message: str, page: str = "unknown", api_key: str | None = None, user_name: str | None = "there", path: str = "/", input_mode: str = "voice", language: str = "english", is_employer: bool = False, user: Any = None, skillup_grounding: dict[str, Any] | None = None, history: list[dict[str, Any]] | None = None):
    language = normalize_language(language, message)
    if api_key is None:
        api_key = getattr(settings, "SARVAM_API_KEY", "")

    """
    Generator that yields Server-Sent Event (SSE) strings for streaming responses.

    Fast paths (intent / quick-guidance / fast-reply / fallback) emit a single
    complete event immediately so the client sees an answer with no delay.

    The AI path uses stream=True on the Sarvam chat completion API so the first
    token reaches the client in ~1-2 s instead of waiting for the full response.

    Event shapes:
      {"t": "<token>"}                          — streaming AI token
      {"reply": "...", "actions": [...], "source": "..."}  — complete fast-path reply
      {"done": true, "reply": "...", "actions": [...], "source": "ai"}  — AI stream done
    Sentinel: data: [DONE]
    """

    def _sse(payload: dict) -> str:
        # Master-prompt voice contract: every response Riya produces must be
        # speakable regardless of whether the user typed or spoke. Any event
        # that carries a final reply is flagged speak=true and given a
        # `message` alias so API consumers match the {message, audio, speak}
        # shape. Streaming token events ({"t": ...}) are left untouched.
        if isinstance(payload, dict) and "reply" in payload:
            payload.setdefault("speak", True)
            payload.setdefault("message", payload.get("reply"))
        return f"data: {json.dumps(payload)}\n\n"

    def _done() -> str:
        return "data: [DONE]\n\n"

    # ── Fast path -1: explicit cross-portal request (security boundary) ──────
    # Checked before everything else, including Skill Up, since this is a
    # hard boundary rather than a feature - a Job Seeker asking for the
    # Employer portal (or vice versa) must never fall through to any other
    # path, no matter how the rest of the message is phrased.
    portal_block = _detect_cross_portal_block(message, is_employer, language)
    if portal_block:
        yield _sse(portal_block)
        yield _done()
        return

    # ── Fast path 0: Skill Up (additive) ─────────────────────────────────────
    # Deterministic Skill Up answers (counts, lists, navigation, search) are
    # emitted as a single complete event, exactly like the other fast paths —
    # no LLM call, so they are fast, cheap and impossible to hallucinate.
    # Page-summary questions instead produce grounding that is handed to the
    # existing AI stream below.
    if skillup_grounding is None:
        try:
            _skillup = skillup_try_handle(message, path=path, page=page, language=language)
        except Exception:
            _skillup = None

        if _skillup is not None:
            if "_skillup_grounding" not in _skillup:
                # CHECK ACCESS BEFORE RETURNING
                from core.skillup_access import has_full_skillup, is_locked_lesson
                if _skillup.get("actions") and not has_full_skillup(user):
                    allowed = True
                    for act in _skillup["actions"]:
                        route = act.get("route", "")
                        if "#load=" in route:
                            load_path = route.split("#load=")[-1]
                            if not load_path.startswith("/static/"):
                                load_path = "/static/001 Career Buddy/" + load_path
                            if is_locked_lesson(load_path):
                                allowed = False
                                break
                        elif "/skill-up/#" in route:
                            fragment = route.split("#")[-1].lower()
                            if "aptitude" in fragment or "tech" in fragment or "non_it" in fragment:
                                allowed = False
                                break
                    if not allowed:
                        from career_app.views import message_text
                        reply = "🔒 This feature is available in a higher plan. Please Upgrade to avail this Feature."
                        actions = [_build_action("pro", "Membership", "/pro/")]
                        _skillup = {"reply": reply, "actions": actions, "source": "intent", "language": language}

                if _skillup is not None:
                    _skillup["language"] = language
                    yield _sse(_skillup)
                    yield _done()
                    return
            else:
                skillup_grounding = _skillup.get("_skillup_grounding")

    # ── Fast path 1: premium navigation security ─────────────────────────────
    # Resolve premium navigation before activity/category navigation. This is
    # the final backend boundary for GD, JAM, Roleplay, Mock Interview, and
    # Job Search requests coming from the chatbot.
    # SPEED: fast local resolvers first (no Sarvam call); LLM classifier last.
    premium_nav_key = resolve_navigation_intent(message, language, api_key, user, use_ai=False)

    portal_block = validate_portal_navigation(premium_nav_key, is_employer, language)
    if portal_block:
        yield _sse(portal_block)
        yield _done()
        return

    premium_block = _premium_navigation_block(premium_nav_key, user, is_employer, language)
    if premium_block:
        premium_block["language"] = language
        yield _sse(premium_block)
        yield _done()
        return

    # Activity/category navigation runs only after premium navigation has
    # been cleared. Local (DB) only.
    activity_navigation = resolve_activity_navigation_payload(message, is_employer, user, language)
    if activity_navigation:
        activity_navigation["language"] = language
        yield _sse(activity_navigation)
        yield _done()
        return

    # Nothing local matched — now pay for the LLM navigation classifier.
    if not premium_nav_key:
        premium_nav_key = resolve_navigation_intent(message, language, api_key, user, use_ai=True)
        if premium_nav_key:
            portal_block = validate_portal_navigation(premium_nav_key, is_employer, language)
            if portal_block:
                yield _sse(portal_block)
                yield _done()
                return
            premium_block = _premium_navigation_block(premium_nav_key, user, is_employer, language)
            if premium_block:
                premium_block["language"] = language
                yield _sse(premium_block)
                yield _done()
                return

    nav_key = premium_nav_key
    if nav_key and nav_key in ACTION_DEFINITIONS:
        if nav_key == "candidate_search" and not is_employer:
            nav_key = "login_employer"

        action = ACTION_DEFINITIONS[nav_key]
        # Plain "Opening X." for a bare open/navigate/guide; description (or the
        # child menu) only when the user ASKED ABOUT it ("what is X"). Local, no LLM.
        reply = _navigation_reply(nav_key, message, language, is_employer)
        actions = _build_actions([nav_key], is_employer)

        # Note: plan/tier access for workshop, mock_interview, gd, jam,
        # roleplay, and job_search was already verified above by
        # _premium_navigation_block() (which uses the same
        # _is_premium_action_allowed() the real destination pages use) -
        # execution only reaches here once that has already passed, so it
        # is not re-checked here.
        if nav_key == "job_search":
            passed = False
            if user and user.is_authenticated:
                from career_app.models import ResumeInterviewSession
                try:
                    latest_session = ResumeInterviewSession.objects.filter(resume__user=user, is_completed=True).latest('start_time')
                    if latest_session.total_score is not None and latest_session.total_score >= 90:
                        passed = True
                except ResumeInterviewSession.DoesNotExist:
                    pass
            if not passed:
                reply = message_text("score_for_job_search", language)
                actions = [_build_action("mock_interview", "AI Mock Interview", "/resume-builder/")]

        if nav_key == "about_app":
            yield _sse({"reply": reply, "actions": [], "source": "intent", "language": language})
            yield _done()
            return

        yield _sse({
            "reply": str(reply),
            "actions": actions,
            "source": "intent",
            "language": language,
        })
        yield _done()
        return


    if language == "english":
        quick = _quick_guidance_payload(message, page, path, user_name, is_employer)
        if quick:
            yield _sse(quick)
            yield _done()
            return

        # Fast replies are English-only deterministic templates. Multilingual
        # messages go through the AI path so the response stays in-language.
        fast = _fast_reply_payload(message, page, path, user_name, is_employer)
        if fast:
            yield _sse(fast)
            yield _done()
            return

    # ── No API key → fallback ────────────────────────────────────────────────
    if not api_key:
        yield _sse(build_fallback_payload(message, page, path, language, is_employer))
        yield _done()
        return

    context = _page_context(page, path, is_employer)
    allowed_actions = {key: value["label"] for key, value in ACTION_DEFINITIONS.items() if _action_is_available(key, is_employer)}
    other_portal_actions = {key: value["label"] for key, value in ACTION_DEFINITIONS.items() if not _action_is_available(key, is_employer)}
    name_part = f"The user's name is {user_name}. " if user_name else ""
    language_name = SUPPORTED_LANGUAGES.get(language, {"name": language})["name"]

    system_prompt = (
        f"You are Buddy, a production-grade AI assistant for Career Buddy LMS. "
        f"{name_part}"
        f"The user's selected language is {language_name}. Reply in the same language as the user. "
        f"{APP_KNOWLEDGE_BASE}\n\n"
        "IMPORTANT RULES: "
        "1. Never invent a feature, page, route, or capability. "
        "2. Only navigate to keys in the supplied allowed_actions. "
        "3. If a requested feature is in other_portal_actions, politely tell the user that the feature is available in the Employer/Job Seeker portal and return <NAV:none>. "
        "4. If a requested feature is not in either, say it is not available in this application and use <NAV:none>. "
        "5. Always understand the user's meaning regardless of language. "
        "6. Internally think in English. "
        "7. Reply ONLY in the same language the user used. "
        "8. Never mention that you translated. "
        "9. If the user asks to navigate anywhere, determine the correct page even if the request is in another language. "
        "10. NEVER translate page names like Dashboard, Grammar, Professional Speaking, Professional Reading, Listen & Learn, Passage Writing, Resume Builder, Roleplay, Group Discussion, JAM, Membership. Keep them exactly as written. "
        "11. If navigation is requested, your FIRST line MUST be: <NAV:key> "
        "Choose the 'key' ONLY from the allowed mapping provided below based on the user's intent. "
        "CRITICAL: You MUST output the <NAV:key> tag AT THE VERY BEGINNING of your response. "
        "DO NOT say 'Yes', 'Sure', or ANY other word before the <NAV:key> tag. "
        "If no navigation is requested, use <NAV:none>. "
        "After the navigation tag, provide the reply in the user's language. "
        "Never output markdown. Never output HTML. Never output <think> tags. "
        "Only output the final answer.\n\n"
        + BUDDY_VOICE_AND_MANNER
    )
    user_payload = {
        "message": (message or "").strip(),
        "page": context["name"],
        "page_summary": context["summary"],
        "input_mode": (input_mode or "voice").strip().lower() or "voice",
        "allowed_actions": allowed_actions,
        "other_portal_actions": other_portal_actions,
    }

    if skillup_grounding:
        system_prompt = system_prompt + "\n\n" + SKILL_UP_PROMPT_RULES
        user_payload["skill_up_context"] = skillup_grounding

    # ── Conversation memory ──────────────────────────────────────────────
    # The frontend already sends prior turns on every request (see
    # requestAssistantReplyStream in BOTscript.js), but this function was
    # never using them, so every message was answered as a stateless
    # single turn - "What is ATS?" -> "Why is it important?" had no way
    # to resolve what "it" referred to. Forward a bounded, sanitized slice
    # so follow-up questions carry real context, without ever letting
    # conversation content override the navigation/business rules above -
    # those are enforced by dedicated guard functions before this point,
    # not by anything the model infers from history.
    history_messages = []
    for turn in (history or [])[-16:]:
        if not isinstance(turn, dict):
            continue
        role = "assistant" if turn.get("role") == "assistant" else "user"
        content = str(turn.get("content", "") or "").strip()
        if not content:
            continue
        history_messages.append({"role": role, "content": content[:2000]})

    accumulated = ""
    in_think = False
    nav_buffer = ""
    nav_tag_complete = False
    requested_action_keys = []
    try:
        resp = requests.post(
            SARVAM_CHAT_URL,
            headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
            json={
                "model": getattr(settings, 'SARVAM_MODEL', 'sarvam-105b'),
                # Raised from 0.4: the grounding rules above are hard constraints, so
            # the extra latitude buys natural, varied phrasing rather than
            # freedom to invent facts.
            "temperature": 0.6,
                "max_tokens": 1000,
                "stream": True,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *history_messages,
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                "reasoning_effort": None,
            },
            stream=True,
            timeout=30,
        )
        resp.raise_for_status()

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            chunk_str = line[6:].strip()
            if chunk_str == "[DONE]":
                break
            try:
                chunk = json.loads(chunk_str)
                token = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if token:
                    if "<think" in token:
                        in_think = True
                    
                    if not in_think:
                        if not nav_tag_complete:
                            nav_buffer += token
                            stripped = nav_buffer.lstrip()
                            if not stripped:
                                continue
                            
                            if stripped.startswith("<"):
                                if len(stripped) >= 5 and not stripped.startswith("<NAV:"):
                                    # Not a NAV tag
                                    accumulated += nav_buffer
                                    yield _sse({"t": nav_buffer})
                                    nav_tag_complete = True
                                elif ">" in stripped:
                                    nav_match = re.match(r"^\s*<NAV:([^>]+)>", nav_buffer)
                                    if nav_match:
                                        keys_str = nav_match.group(1)
                                        if keys_str.lower() != "none":
                                            requested_action_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
                                        remaining_text = nav_buffer[nav_match.end():].lstrip()
                                        if remaining_text:
                                            accumulated += remaining_text
                                            yield _sse({"t": remaining_text})
                                    else:
                                        accumulated += nav_buffer
                                        yield _sse({"t": nav_buffer})
                                    nav_tag_complete = True
                            else:
                                accumulated += nav_buffer
                                yield _sse({"t": nav_buffer})
                                nav_tag_complete = True
                        else:
                            accumulated += token
                            yield _sse({"t": token})

                    if "</think>" in token:
                        in_think = False
                        
            except (json.JSONDecodeError, IndexError, TypeError, KeyError):
                continue

    except Exception as e:
        import traceback
        traceback.print_exc()
        if not accumulated:
            yield _sse(build_fallback_payload(message, page, path, language, is_employer))
            yield _done()
            return

    # ── Emit final done event with cleaned reply + actions ───────────────────
    final_reply = _limit_reply(accumulated)
    if not final_reply:
        yield _sse(build_fallback_payload(message, page, path, language, is_employer))
        yield _done()
        return

    action_keys = [key for key in requested_action_keys if key in ACTION_DEFINITIONS and _action_is_available(key, is_employer)][:2]
    
    # If exactly 1 highly confident intent
    source = "ai"
    if len(action_keys) == 1:
        source = "intent"
        
    if not action_keys:
        action_keys = context["action_keys"][:2]

    # (Plan checks are now handled exclusively by _premium_navigation_block below)
    # FINAL HARD BOUNDARY: no premium route can leave this function for a
    # Free user, even if the LLM generated a premium <NAV:key>.
    for key in action_keys:
        portal_block = validate_portal_navigation(key, is_employer, language)
        if portal_block:
            yield _sse({
                "done": True,
                "reply": portal_block["reply"],
                "actions": portal_block["actions"],
                "source": "intent",
                "language": language,
            })
            yield _done()
            return

        premium_block = _premium_navigation_block(key, user, is_employer, language)
        if premium_block:
            premium_block["language"] = language
            yield _sse({
                "done": True,
                "reply": premium_block["reply"],
                "actions": premium_block["actions"],
                "source": "intent",
                "language": language,
            })
            yield _done()
            return

    final_action_keys = []
    for key in action_keys:
        # Note: Plan entitlement (Free vs Normal/Pro) is already verified 
        # by _premium_navigation_block above. We only need to check 
        # additional business logic (like interview scores).
        
        if key == "job_search":
            passed = False
            if user and user.is_authenticated:
                from career_app.models import ResumeInterviewSession
                try:
                    latest_session = ResumeInterviewSession.objects.filter(resume__user=user, is_completed=True).latest('start_time')
                    if latest_session.total_score is not None and latest_session.total_score >= 90:
                        passed = True
                except ResumeInterviewSession.DoesNotExist:
                    pass
            if not passed:
                final_reply = "To unlock Job Search, you must score at least 90% in your AI Mock Interview."
                final_action_keys = ["mock_interview"]
                source = "intent"
                break
            else:
                final_action_keys.append(key)
        else:
            final_action_keys.append(key)

    action_keys = final_action_keys

    yield _sse({"done": True, "reply": final_reply, "actions": _build_actions(action_keys, is_employer), "source": source})
    yield _done()


# Backwards-compatible name used by older agent integrations.
build_assistant_payload = riya_chat_logic
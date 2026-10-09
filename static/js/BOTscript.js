(function () {
    if (window.__RiyaThoughtBubbleInitialized) {
        return;
    }
    window.__RiyaThoughtBubbleInitialized = true;

    const AssistantState = {
        CLOSED: "closed",
        GREETING: "greeting",
        LISTENING: "listening",
        PROCESSING: "processing",
        RESPONDING: "responding",
        ERROR: "error",
    };

    const MODEL_VIEWER_SCRIPT_URL =
        "https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js";
    const LAUNCHER_MODEL_VRiyaNTS = {
        idle: "idle",
        speaking: "speaking",
    };
    const Riya_BROWSER_VOICE_RATE = 1.0;
    const Riya_BROWSER_VOICE_PITCH = 1.03;
    const RIYA_SESSION_STORAGE_VERSION = 2;
    const RIYA_SESSION_MAX_AGE_MS = 1000 * 60 * 60 * 8;
    const INTENT_STOP_WORDS = new Set([
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
    ]);
    const FEMALE_VOICE_HINTS = [
        "sophia",
        "samantha",
        "victoria",
        "jenny",
        "emma",
        "zira",
        "Riya",
        "female",
        "woman",
        "ava",
        "allison",
        "olivia",
        "serena",
        "natasha",
        "veena",
        "hazel",
    ];

    let modelViewerScriptPromise = null;

    const ACTION_DEFINITIONS = {
        home: {
            label: "Home",
            route: "/",
            response: "Opening home.",
            keywords: ["home", "home page", "landing page", "main page"],
        },
        lessons: {
            label: "Go to Activities",
            route: "/activities/",
            response: "Opening the activities page.",
            keywords: ["practice", "practice page", "lesson", "lessons", "activities", "activities page", "activity list", "all activities"],
        },
        professional_speaking: {
            label: "Speaking and Presentation",
            route: "/activities/?category=speaking",
            response: "Opening Speaking and Presentation.",
            // "professional speaking" and bare "speaking" were previously
            // listed here but not in the backend's copy of this action —
            // that drift is what let "Open Professional Speaking" (the
            // individual activity, order 24) get treated as a request for
            // this category instead. Kept in sync with the backend's
            // ACTION_DEFINITIONS in riya_bot/riya_assistant.py now. The
            // category-vs-activity ambiguity itself is additionally
            // guarded structurally: any category-route match here always
            // defers to the backend rather than navigating locally (see
            // the isCategoryAction check below), so a future keyword
            // addition here can't reintroduce this bug even if the two
            // lists drift again.
            keywords: ["speaking module", "speaking page", "speaking activity", "speaking practice", "open speaking", "go to speaking", "start speaking", "show speaking"],
        },
        passage_writing: {
            label: "Writing and Correspondence",
            route: "/activities/?category=writing",
            response: "Opening Writing and Correspondence.",
            // Same drift as professional_speaking above: "professional
            // passage writing" and bare "passage writing" were listed here
            // but not in the backend's copy, which let "Open Professional
            // Passage Writing" (the individual activity, order 21) get
            // treated as a request for this category instead.
            keywords: ["writing", "correspondence", "writing and correspondence", "writing module", "writing page", "writing activity", "writing practice", "open writing", "go to writing", "start writing", "show writing"],
        },
        vocabulary: {
            label: "Vocabulary and Idioms",
            route: "/activities/?category=vocabulary",
            response: "Opening Vocabulary and Idioms.",
            keywords: ["vocabulary and idioms", "vocabulary", "idioms", "vocabulary module", "idioms module", "open vocabulary"],
        },
        negotiation: {
            label: "Negotiation & Meetings",
            route: "/activities/?category=negotiation",
            response: "Opening Negotiation & Meetings.",
            keywords: ["negotiation and meetings", "negotiation", "meetings", "negotiation module", "meetings module", "open negotiation"],
        },
        communication: {
            label: "Professional Communication",
            route: "/activities/?category=communication",
            response: "Opening Professional Communication.",
            keywords: ["professional communication", "communication", "communication module", "open communication"],
        },
        analysis: {
            label: "Analysis & Reporting",
            route: "/activities/?category=analysis",
            response: "Opening Analysis & Reporting.",
            keywords: ["analysis and reporting", "analysis", "reporting", "analysis module", "open analysis"],
        },
        listen_learn: {
            label: "Listen & Learn",
            route: "/activities/?category=listening",
            response: "Opening Listen & Learn.",
            keywords: ["listen and learn", "listen & learn", "listening", "listening module", "listening activity", "listening practice", "listening exercise", "audio practice", "open listening", "go to listening", "start listening"],
        },
        profile: {
            label: "View Dashboard",
            route: "/dashboard/",
            response: "Opening your dashboard.",
            keywords: ["profile", "my profile", "dashboard", "account", "progress", "student dashboard"],
        },
        company_profile: {
            label: "Company Profile",
            route: "/employer/employer/profile/edit/",
            response: "Opening your company profile.",
            keywords: ["company profile", "employer profile", "business profile", "update profile", "my profile"],
        },
        find_candidates: {
            label: "Find Candidates",
            route: "/employer/employer/candidates/search/",
            response: "Opening the candidate search page.",
            keywords: ["find candidates", "search candidates", "candidate search", "find candidate", "search candidate", "browse candidates"],
        },
        post_job: {
            label: "Post New Job",
            route: "/employer/employer/jobs/new/",
            response: "Opening the post new job page.",
            keywords: ["post new job", "post job", "create job", "new job", "add job"],
        },
        all_applications: {
            label: "All Applications",
            route: "/employer/employer/applications/",
            response: "Opening the all applications page.",
            keywords: ["all applications", "applications", "view applications", "job applications"],
        },
        job_openings: {
            label: "Job Openings",
            route: "/employer/employer/job-openings/",
            response: "Opening the job openings page.",
            keywords: ["job openings", "openings", "view job openings", "view openings", "my jobs", "posted jobs"],
        },
        login_job_seeker: {
            label: "Job Seeker Sign-In",
            route: "/users/login/",
            response: "Taking you to the job seeker sign-in page.",
            keywords: ["job seeker", "student", "candidate", "login", "sign in", "job seeker login"],
        },
        register_job_seeker: {
            label: "Job Seeker Registration",
            route: "/users/register/",
            response: "Taking you to the job seeker registration page.",
            keywords: ["register job seeker", "job seeker registration", "student registration", "employee registration", "sign up as job seeker", "candidate registration", "register candidate", "registration"],
        },
        login_employer: {
            label: "Employer Login",
            route: "/employer/accounts/employer/login/",
            response: "Taking you to the employer portal.",
            keywords: ["employer", "recruiter", "company", "hiring", "employer login", "recruiter login"],
        },
        register_employer: {
            label: "Employer Registration",
            route: "/employer/accounts/employer/register/",
            response: "Taking you to the employer registration page.",
            keywords: ["register employer", "employer registration", "company registration", "recruiter registration", "sign up as employer"],
        },
        english_vocab: {
            label: "English & Vocab",
            route: "/skill-up/#depth-english",
            response: "Taking you to the English & Vocab section.",
            keywords: ["english and vocab", "english & vocab", "vocabulary", "vocab", "english"],
        },
        aptitude: {
            label: "Aptitude",
            route: "/skill-up/#depth-aptitude",
            response: "Taking you to the Aptitude section.",
            keywords: ["aptitude", "quantitative aptitude", "aptitude module", "reasoning"],
        },
        tech: {
            label: "Tech",
            route: "/skill-up/#depth-tech",
            response: "Taking you to the Tech section.",
            keywords: ["tech", "technical", "technology", "tech module", "programming"],
        },
        sitemap: {
            label: "Sitemap",
            route: "/skill-up/#section-sitemap",
            response: "Taking you to the Sitemap.",
            keywords: ["sitemap", "site map"],
        },
        browse_all: {
            label: "Browse all",
            route: "/skill-up/#section-depth",
            response: "Taking you to browse all activities.",
            keywords: ["browse all", "browse all activities", "explore all"],
        },
        grammar: {
            label: "Grammar",
            route: "/subject/",
            response: "Opening the grammar section.",
            keywords: ["grammar", "grammer", "english grammar", "parts of speech", "grammar page", "grammar module", "grammer module"],
        },
        grammar_noun: {
            label: "Nouns",
            route: "/subject/noun.html",
            response: "Opening the Nouns module.",
            keywords: ["noun", "nouns", "noun module", "nouns module"],
        },
        grammar_pronoun: {
            label: "Pronouns",
            route: "/subject/pronoun.html",
            response: "Opening the Pronouns module.",
            keywords: ["pronoun", "pronouns", "pronoun module", "pronouns module"],
        },
        grammar_verb: {
            label: "Verbs",
            route: "/subject/verb.html",
            response: "Opening the Verbs module.",
            keywords: ["verb", "verbs", "verb module", "verbs module"],
        },
        grammar_adjective: {
            label: "Adjectives",
            route: "/subject/adjective.html",
            response: "Opening the Adjectives module.",
            keywords: ["adjective", "adjectives", "adjective module", "adjectives module"],
        },
        grammar_adverb: {
            label: "Adverbs",
            route: "/subject/adverb.html",
            response: "Opening the Adverbs module.",
            keywords: ["adverb", "adverbs", "adverb module", "adverbs module"],
        },
        grammar_conjunction: {
            label: "Conjunctions",
            route: "/subject/conjunction.html",
            response: "Opening the Conjunctions module.",
            keywords: ["conjunction", "conjunctions", "conjunction module", "conjunctions module"],
        },
        grammar_tenses: {
            label: "Tenses",
            route: "/subject/tenses.html",
            response: "Opening the Tenses module.",
            keywords: ["tense", "tenses", "tenses module"],
        },
        grammar_sentence_structure: {
            label: "Sentence Structure",
            route: "/subject/sentence-structure.html",
            response: "Opening Sentence Structure.",
            keywords: ["sentence structure", "structure of sentence"],
        },
        grammar_types_of_sentences: {
            label: "Types of Sentences",
            route: "/subject/types-of-sentences.html",
            response: "Opening Types of Sentences.",
            keywords: ["types of sentences", "sentence types"],
        },
        roleplay: {
            label: "Roleplay",
            route: "/roleplay/",
            response: "Opening roleplay practice.",
            keywords: ["roleplay", "role play", "conversation roleplay", "roleplay practice"],
        },
        storytelling_practice: {
            label: "Storytelling Practice",
            route: "/roleplay/storytelling/",
            response: "Opening Storytelling practice.",
            keywords: ["storytelling", "story telling", "storytelling practice"],
        },
        situation_practice: {
            label: "Situation Practice Exercise",
            route: "/roleplay/situations/",
            response: "Opening Situation Practice Exercise.",
            keywords: ["situations", "situation practice", "situation practice exercise"],
        },
        gd: {
            label: "Group Discussion",
            route: "/gd/",
            response: "Opening group discussion.",
            keywords: ["group discussion", "gd", "gd module", "discussion"],
        },
        jam: {
            label: "JAM",
            route: "/jam/",
            response: "Opening JAM practice.",
            keywords: ["jam", "just a minute", "jam module", "jam practice"],
        },
        resume_builder: {
            label: "Resume Builder",
            route: "/resume-builder/",
            response: "Opening resume builder.",
            keywords: ["job match", "resume builder", "resume parsing", "resume parser", "resume match", "upload resume", "career", "ats"],
        },
        certifications: {
            label: "Certifications",
            route: "/skill-up/#section-certifications",
            response: "Opening your certifications.",
            keywords: ["certifications", "certification", "certificate", "certificates", "my certificates", "my certification", "open certifications", "skill up certification", "skill up certificate"],
        },
        pro: {
            label: "Membership",
            route: "/pro/",
            response: "Opening membership plans.",
            keywords: ["pro", "membership", "plans", "upgrade", "subscription", "normal user", "pro user"],
        },
        mock_interview: {
            label: "AI Mock Interview",
            route: "/resume-builder/",
            response: "Taking you to the Resume Builder for your AI Mock Interview.",
            keywords: ["mock interview", "ai mock interview", "ai interview", "mock ai interview"],
        },
        job_search: {
            label: "Job Search",
            route: "/resume-builder/analytics/",
            response: "Opening Job Recommendations.",
            keywords: ["job search", "search jobs", "find jobs", "looking for jobs", "jobs", "searching jobs", "find a job"],
        },
        // Mirrors the backend action: lands ON the dashboard's matched-jobs card.
        job_recommendations: {
            label: "Job Recommendations",
            route: "/dashboard/#recommended-jobs",
            response: "Opening your job recommendations.",
            keywords: ["job recommendations", "recommended jobs", "job recommendation", "matched jobs", "job matches", "jobs for me", "recommended opportunities", "my job matches"],
        },
        workshop: {
            label: "Interactive Workshop",
            route: "/activities/?category=workshop",
            response: "Opening Interactive Workshop activities.",
            keywords: ["interactive workshop", "workshop", "workshops"],
        },
        employer_login: {
            label: "Employer Login",
            route: "/employer/accounts/employer/login/",
            response: "Taking you to the Employer Portal.",
            keywords: ["employer", "employeer", "recruiter", "hiring", "employee"],
        },
        student_login: {
            label: "Job Seeker Sign-In",
            route: "/users/login/",
            response: "Opening the job seeker login page.",
            keywords: ["job seeker", "jobseeker", "student", "candidate"],
        },
    };

    // ============================================================
    // ROLE-SPECIFIC BUDDY CONTEXT
    // Student/Job Seeker and Employer are intentionally isolated.
    // ============================================================

    const STUDENT_ACTION_KEYS = [
        "home", "lessons", "professional_speaking", "passage_writing",
        "vocabulary", "negotiation", "communication", "analysis", "listen_learn", "profile",
        "grammar", "grammar_noun", "grammar_pronoun", "grammar_verb",
        "grammar_adjective", "grammar_adverb", "grammar_conjunction",
        "grammar_tenses", "grammar_sentence_structure",
        "grammar_types_of_sentences", "roleplay", "storytelling_practice",
        "situation_practice", "gd", "jam", "workshop",
        "resume_builder", "pro", "mock_interview", "job_search", "job_recommendations", "login_job_seeker",
        "register_job_seeker", "about_app", "sitemap", "browse_all",
        "english_vocab", "aptitude", "tech", "certifications",
    ];

    const EMPLOYER_ACTION_KEYS = [
        "home", "profile", "company_profile", "find_candidates",
        "post_job", "all_applications", "job_openings", "login_employer",
        "register_employer", "sitemap", "browse_all", "english_vocab",
        "aptitude", "tech",
    ];

    // ============================================================
    // PERSISTENT WELCOME / RECOMMENDATION CARDS
    // These are intentionally separate from the conversation stream so
    // they remain visible after the user sends a message.
    // ============================================================
    const RECOMMENDATION_TRANSLATIONS = {
        english: {
            "Create Profile": "Create Profile",
            "Job Seeker Sign-In": "Job Seeker Sign-In",
            "Employer Login": "Employer Login",
            "Explore CareerBuddy": "Explore CareerBuddy",
            "Find Jobs": "Find Jobs",
            "Check Resume": "Check Resume",
            "Complete your Profile": "Complete your Profile",
            "Explore Matching Jobs": "Explore Matching Jobs",
            "Your Certifications": "Your Certifications",
            "Continue Learning": "Continue Learning",
            "Manage Jobs": "Manage Jobs",
            "Find Candidates": "Find Candidates",
            "Review Applications": "Review Applications",
            "Manage Interviews": "Manage Interviews",
            "Review New Applications": "Review New Applications",
            "Active Job Postings": "Active Job Postings",
            "Complete Company Profile": "Complete Company Profile",
            "Create Candidate Registration": "Create Candidate Registration",
            "Create Employer Account": "Create Employer Account",
        },
        hindi: {
            "Create Profile": "प्रोफाइल बनाएं",
            "Job Seeker Sign-In": "स्टूडेंट लॉगिन",
            "Employer Login": "एम्प्लॉयर लॉगिन",
            "Explore CareerBuddy": "CareerBuddy एक्सप्लोर करें",
            "Find Jobs": "नौकरी खोजें",
            "Check Resume": "रेज़्यूमे चेक करें",
            "Complete your Profile": "अपनी प्रोफाइल पूरी करें",
            "Explore Matching Jobs": "मैचिंग नौकरियां खोजें",
            "Your Certifications": "आपके सर्टिफिकेशन",
            "Continue Learning": "सीखना जारी रखें",
            "Manage Jobs": "नौकरियां मैनेज करें",
            "Find Candidates": "कैंडिडेट्स खोजें",
            "Review Applications": "एप्लीकेशंस रिव्यू करें",
            "Manage Interviews": "इंटरव्यू मैनेज करें",
            "Review New Applications": "नई एप्लीकेशंस रिव्यू करें",
            "Active Job Postings": "एक्टिव जॉब पोस्टिंग्स",
            "Complete Company Profile": "कंपनी प्रोफाइल पूरी करें",
            "Create Candidate Registration": "कैंडिडेट रजिस्ट्रेशन बनाएं",
            "Create Employer Account": "एम्प्लॉयर अकाउंट बनाएं",
        },
        vietnam: {
            "Create Profile": "Tạo hồ sơ",
            "Job Seeker Sign-In": "Đăng nhập Người tìm việc",
            "Employer Login": "Đăng nhập Nhà tuyển dụng",
            "Explore CareerBuddy": "Khám phá CareerBuddy",
            "Find Jobs": "Tìm việc làm",
            "Check Resume": "Kiểm tra Sơ yếu lý lịch",
            "Complete your Profile": "Hoàn thiện hồ sơ của bạn",
            "Explore Matching Jobs": "Khám phá việc làm phù hợp",
            "Your Certifications": "Chứng chỉ của bạn",
            "Continue Learning": "Tiếp tục học",
            "Manage Jobs": "Quản lý việc làm",
            "Find Candidates": "Tìm ứng viên",
            "Review Applications": "Xem xét Đơn xin việc",
            "Manage Interviews": "Quản lý Phỏng vấn",
            "Review New Applications": "Xem xét Đơn xin việc mới",
            "Active Job Postings": "Bài đăng việc làm hiện tại",
            "Complete Company Profile": "Hoàn thiện Hồ sơ công ty",
            "Create Candidate Registration": "Tạo đăng ký ứng viên",
            "Create Employer Account": "Tạo tài khoản nhà tuyển dụng",
        },
        arabic: {
            "Create Profile": "إنشاء ملف شخصي",
            "Job Seeker Sign-In": "تسجيل دخول الباحث عن عمل",
            "Employer Login": "تسجيل دخول صاحب العمل",
            "Explore CareerBuddy": "استكشاف CareerBuddy",
            "Find Jobs": "البحث عن وظائف",
            "Check Resume": "التحقق من السيرة الذاتية",
            "Complete your Profile": "أكمل ملفك الشخصي",
            "Explore Matching Jobs": "استكشاف الوظائف المطابقة",
            "Your Certifications": "شهاداتك",
            "Continue Learning": "مواصلة التعلم",
            "Manage Jobs": "إدارة الوظائف",
            "Find Candidates": "البحث عن مرشحين",
            "Review Applications": "مراجعة الطلبات",
            "Manage Interviews": "إدارة المقابلات",
            "Review New Applications": "مراجعة الطلبات الجديدة",
            "Active Job Postings": "إعلانات الوظائف النشطة",
            "Complete Company Profile": "إكمال ملف الشركة",
            "Create Candidate Registration": "إنشاء تسجيل مرشح",
            "Create Employer Account": "إنشاء حساب صاحب عمل",
        },
        russian: {
            "Create Profile": "Создать профиль",
            "Job Seeker Sign-In": "Вход для соискателя",
            "Employer Login": "Вход для работодателя",
            "Explore CareerBuddy": "Изучить CareerBuddy",
            "Find Jobs": "Найти работу",
            "Check Resume": "Проверить резюме",
            "Complete your Profile": "Заполните свой профиль",
            "Explore Matching Jobs": "Найти подходящие вакансии",
            "Your Certifications": "Ваши сертификаты",
            "Continue Learning": "Продолжить обучение",
            "Manage Jobs": "Управление вакансиями",
            "Find Candidates": "Найти кандидатов",
            "Review Applications": "Рассмотреть заявки",
            "Manage Interviews": "Управление собеседованиями",
            "Review New Applications": "Рассмотреть новые заявки",
            "Active Job Postings": "Активные вакансии",
            "Complete Company Profile": "Заполнить профиль компании",
            "Create Candidate Registration": "Создать регистрацию кандидата",
            "Create Employer Account": "Создать аккаунт работодателя",
        }
    };
    const WELCOME_CONTEXT = {
        // Landing-page-only guest pill set (task spec's 5 named items). Kept
        // separate from WELCOME_CONTEXT.guest (used on every other guest
        // page) so this doesn't change Buddy anywhere except "/" for a
        // signed-out visitor. actionKeys are real, already-allowlisted guest
        // actions (see getAllowedActionKeys) -- resume/jobs/interview route
        // through sign-up since those pages are @login_required server-side;
        // Skill Up is genuinely public so "Improve My Skills" and "Explore
        // Certifications" go straight there.
        guestLanding: {
            heading: "Click on your preferred option:",
            recommendationHeading: "",
            quickActions: [
                { id: "gl-resume", actionKey: "register_job_seeker", icon: "resume", title: "Build My Resume", description: "Create a free account to start", context: "Building your resume starts with a free Job Seeker account -- it only takes a minute." },
                { id: "gl-jobs", actionKey: "register_job_seeker", icon: "briefcase", title: "Find Jobs", description: "Sign up to see matched roles", context: "Job matches are personalized to your profile once you sign up." },
                { id: "gl-skills", actionKey: "browse_all", icon: "book", title: "Improve My Skills", description: "Browse Skill Up, open to everyone", context: "Skill Up's English, aptitude and tech modules are open to browse right now." },
                { id: "gl-interview", actionKey: "register_job_seeker", icon: "interview", title: "Practice Interview", description: "Sign up for AI mock interviews", context: "AI mock interviews are available once you create your free account." },
                { id: "gl-certs", actionKey: "browse_all", icon: "cap", title: "Explore Certifications", description: "See what you can earn", context: "Certifications are earned in Skill Up by scoring well on a module's assessment." },
            ],
            recommendations: [],
        },
        guest: {
            heading: "What would you like to do?",
            recommendationHeading: "Explore CareerBuddy",
            quickActions: [
                { id: "guest-profile", actionKey: "register_job_seeker", icon: "user", title: "Create Candidate Registration", description: "Create your Job Seeker profile", context: "Registering as a job seeker gives you English practice, resume scoring, AI mock interviews and matched jobs, all in one place." },
            ],
            recommendations: [
                { id: "guest-explore", actionKey: "register_employer", icon: "building", title: "Create Employer Account", description: "Create your Employer profile", context: "An employer account lets you post jobs, search candidates and review applications from your own dashboard." },
                { id: "guest-signin", actionKey: "login_job_seeker", icon: "user", title: "Job Seeker Sign-In", description: "Continue to your career workspace", context: "Signing in takes you back to your learning progress, resume score and job matches." },
                { id: "guest-employer", actionKey: "login_employer", icon: "briefcase", title: "Employer Login", description: "Manage hiring and candidates", context: "The employer portal is where you manage your openings, applicants and interviews." },
            ],
        },
        student: {
            heading: "What would you like to do?",
            recommendationHeading: "Recommended for you",
            quickActions: [
                { id: "student-jobs", actionKey: "job_search", icon: "briefcase", title: "Find Jobs", description: "Search and explore relevant opportunities", context: "Your recommended jobs are matched to your experience and skills, and they unlock once you score 70 or more in the AI mock interview." },
                { id: "student-resume", actionKey: "resume_builder", icon: "resume", title: "Check Resume", description: "Improve your resume and career profile", context: "The Resume Builder parses your resume, gives you an ATS score and tells you exactly what to improve." },
            ],
            recommendations: [
                { id: "student-dashboard", actionKey: "profile", icon: "user", title: "Complete your Profile", description: "Review your dashboard and progress", context: "Your dashboard shows your activity progress, scores and recommended jobs at a glance." },
                { id: "student-matches", actionKey: "job_recommendations", icon: "briefcase", title: "Explore Matching Jobs", description: "Find opportunities relevant to you", context: "Matched jobs are picked using your resume and interview score, so they fit your experience." },
                { id: "student-cert", actionKey: "certifications", icon: "cap", title: "Your Certifications", description: "View available certification features", context: "Certifications are earned in Skill Up by scoring 70 percent or more in a module's mock test." },
                { id: "student-english", actionKey: "english_vocab", icon: "book", title: "Continue Learning", description: "Improve your English and vocabulary", context: "The English and Vocabulary track has guides and a mock test to strengthen your business English." },
            ],
        },
        employer: {
            heading: "What would you like to do?",
            recommendationHeading: "Recommended for you",
            quickActions: [
                { id: "employer-jobs", actionKey: "job_openings", icon: "briefcase", title: "Manage Jobs", description: "View and manage your job openings", context: "Job Openings lists every role you have posted, so you can edit, close or review each one." },
                { id: "employer-candidates", actionKey: "find_candidates", icon: "users", title: "Find Candidates", description: "Search for suitable candidates", context: "Candidate search lets you filter job seekers by skills, experience and interview scores." },
                { id: "employer-applications", actionKey: "all_applications", icon: "resume", title: "Review Applications", description: "Review candidate applications", context: "All Applications collects everyone who applied, with their resumes and interview results." },
                { id: "employer-interviews", actionKey: "find_candidates", icon: "interview", title: "Manage Interviews", description: "Find candidates ready for hiring", context: "You can shortlist candidates who have already completed the AI interview and are ready to hire." },
            ],
            recommendations: [
                { id: "employer-new-apps", actionKey: "all_applications", icon: "resume", title: "Review New Applications", description: "Check applications that need attention", context: "New applications are waiting for your review; quick responses help you secure strong candidates." },
                { id: "employer-active", actionKey: "job_openings", icon: "briefcase", title: "Active Job Postings", description: "Manage your current openings", context: "Your active postings are the roles candidates can apply to right now." },
                { id: "employer-company", actionKey: "company_profile", icon: "building", title: "Complete Company Profile", description: "Review your company information", context: "A complete company profile with logo and description builds trust with candidates." },
            ],
        },
    };

    const WELCOME_ICONS = {
        briefcase: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="7" width="18" height="13" rx="2"></rect><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><path d="M3 12h18"></path></svg>',
        user: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"></circle><path d="M4 21c0-4 4-6 8-6s8 2 8 6"></path></svg>',
        users: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"></path><circle cx="9.5" cy="7" r="4"></circle><path d="M17 11a4 4 0 1 0-1-7.9"></path><path d="M21 21v-2a4 4 0 0 0-3-3.87"></path></svg>',
        resume: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M8 13h8M8 17h6"></path></svg>',
        cap: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10 12 5 2 10l10 5 10-5Z"></path><path d="M6 12v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"></path></svg>',
        interview: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"></rect><path d="M16 3v4M8 3v4M3 10h18"></path><path d="M8 14h3M8 17h6"></path></svg>',
        book: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22z"></path><path d="M4 5.5V22M8 7h8"></path></svg>',
        building: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M5 21V5l7-3 7 3v16M9 9h1M14 9h1M9 13h1M14 13h1M9 17h1M14 17h1"></path></svg>',
        sparkle: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"></path></svg>',
        chart: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"></path><path d="M7 15l4-4 3 3 5-6"></path></svg>',
        code: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m8 6-6 6 6 6M16 6l6 6-6 6"></path></svg>',
        chevron: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="m9 18 6-6-6-6"></path></svg>',
    };

    // ============================================================
    // SECTION-AWARE FOLLOW-UPS
    //
    // Keyed on the SECTION the user is in (path + in-page hash). The first
    // group is follow-up questions about THIS section; the second invites the
    // user elsewhere ("Would you like to... / Interested in...").
    // renderPersistentWelcome() re-derives the section on every page load and
    // on every hashchange, so the cards change after each navigation.
    // ============================================================
    // Card shorthand: c(id, actionKey, icon, title, description, context).
    // `context` is what Buddy says (and shows) about the card before navigating.
    const c = (id, actionKey, icon, title, description, context) => ({ id, actionKey, icon, title, description, context });

    const SECTION_CONTEXT = {
        home: {
            quickActions: [
                c("sec-home-jobs", "job_recommendations", "briefcase", "Which jobs match my profile?", "See your recommended jobs", "Job recommendations are matched to your resume and unlock after a 70 plus score in the AI mock interview."),
                c("sec-home-resume", "resume_builder", "resume", "How good is my resume?", "Get your ATS score", "Upload your resume and Buddy's parser will give you an ATS score with clear improvement tips."),
            ],
            recommendations: [
                c("sec-home-rec1", "lessons", "book", "Would you like to practise English?", "Speaking, writing and listening", "The activities cover speaking, writing, vocabulary and listening, each scored so you can track progress."),
                c("sec-home-rec2", "certifications", "cap", "Interested in a certification?", "Earn one in Skill Up", "Skill Up certifications are earned by scoring 70 percent or more in English, Aptitude or Tech mock tests."),
            ],
        },
        dashboard: {
            quickActions: [
                c("sec-dash-jobs", "job_recommendations", "briefcase", "Show my job recommendations", "Jump to your matched opportunities", "Your recommended jobs sit on this dashboard, matched to your experience and skills."),
                c("sec-dash-act", "lessons", "book", "Which activity should I do next?", "Continue your activities", "Picking up where you left off in the activities is the fastest way to raise your scores."),
            ],
            recommendations: [
                c("sec-dash-rec1", "resume_builder", "resume", "Would you like to check your resume score?", "Parse and improve your resume", "A higher ATS score makes your resume easier for recruiters' systems to find."),
                c("sec-dash-rec2", "certifications", "cap", "Interested in earning a certification?", "Take a Skill Up assessment", "A Skill Up certificate shows employers a verified score in English, Aptitude or Tech."),
            ],
        },
        jobs: {
            quickActions: [
                c("sec-jobs-interview", "mock_interview", "interview", "How do I unlock more matches?", "Score 70+ in the AI mock interview", "Scoring 70 or more in the AI mock interview unlocks more job matches for you."),
                c("sec-jobs-resume", "resume_builder", "resume", "Can I improve my resume first?", "Raise your ATS score", "Improving your resume raises your ATS score and the quality of your matches."),
            ],
            recommendations: [
                c("sec-jobs-rec1", "communication", "users", "Would you like to sharpen your communication?", "Professional Communication activities", "Clear professional communication helps you stand out in applications and interviews."),
                c("sec-jobs-rec2", "aptitude", "chart", "Interested in aptitude practice?", "Common in hiring tests", "Many hiring tests include aptitude rounds, so practice here gives you an edge."),
            ],
        },
        profile: {
            quickActions: [
                c("sec-prof-dash", "profile", "user", "How is my progress?", "Open your dashboard", "Your dashboard shows completed activities, total score and recommended jobs."),
                c("sec-prof-jobs", "job_recommendations", "briefcase", "Which jobs fit my profile?", "See your recommended jobs", "Jobs are matched using your resume and your interview score."),
            ],
            recommendations: [
                c("sec-prof-rec1", "resume_builder", "resume", "Would you like to update your resume?", "Re-check your ATS score", "Re-checking your resume after changes shows how your ATS score improves."),
                c("sec-prof-rec2", "pro", "sparkle", "Interested in Pro features?", "Mock interviews and job matches", "Pro unlocks the AI technical interview and unlimited matched job recommendations."),
            ],
        },
        pro: {
            quickActions: [
                c("sec-pro-interview", "mock_interview", "interview", "What is the AI mock interview?", "Practise and get scored", "The AI mock interview asks questions based on your resume and scores every answer."),
                c("sec-pro-jobs", "job_recommendations", "briefcase", "How do job recommendations work?", "Matched after a 70+ interview score", "After a 70 plus interview score, you get jobs matched to your experience and skills."),
            ],
            recommendations: [
                c("sec-pro-rec1", "profile", "user", "Would you like to go back to your dashboard?", "Track your progress", "Your dashboard keeps track of everything you have done so far."),
                c("sec-pro-rec2", "lessons", "book", "Interested in the free activities?", "Practise English skills", "The free plan still includes grammar lessons and an activity to get you started."),
            ],
        },
        activities: {
            quickActions: [
                c("sec-act-speaking", "professional_speaking", "interview", "How can I improve my speaking?", "Speaking & Presentation", "Speaking and Presentation activities give you instant feedback on clarity, fluency and confidence."),
                c("sec-act-writing", "passage_writing", "resume", "How do I write better emails?", "Writing & Correspondence", "Writing and Correspondence trains you to write clear emails, letters and reports."),
                c("sec-act-listen", "listen_learn", "book", "Can I practise listening?", "Listen & Learn", "Listen and Learn uses audio exercises to sharpen your listening comprehension."),
            ],
            recommendations: [
                c("sec-act-rec1", "workshop", "users", "Would you like to join a workshop?", "Group Discussion, JAM and Role Play", "Workshops include Group Discussion, JAM and Role Play with AI participants."),
                c("sec-act-rec2", "certifications", "cap", "Interested in a certification?", "Earn one from the Skill Up module", "Skill Up certifications prove your level with a verified mock test score."),
            ],
        },
        workshop: {
            quickActions: [
                c("sec-ws-gd", "gd", "users", "How does Group Discussion work?", "Debate with AI participants", "In Group Discussion you debate a topic with AI participants and get scored on your points."),
                c("sec-ws-jam", "jam", "interview", "What is JAM?", "Just A Minute speaking drill", "JAM means Just A Minute: you speak on a topic for sixty seconds without hesitation."),
                c("sec-ws-rp", "roleplay", "users", "Can I practise a workplace scenario?", "Role Play", "Role Play puts you in real workplace scenarios like meetings and client calls."),
            ],
            recommendations: [
                c("sec-ws-rec1", "mock_interview", "interview", "Would you like a mock interview?", "Get scored by the AI interviewer", "The AI mock interview scores your answers and can unlock job matches."),
                c("sec-ws-rec2", "lessons", "book", "Interested in more activities?", "Back to the activities list", "The activities list has speaking, writing, vocabulary and listening practice."),
            ],
        },
        grammar: {
            quickActions: [
                c("sec-gr-tenses", "grammar_tenses", "book", "How do tenses work?", "Open the Tenses module", "Tenses show when an action happens: past, present or future, each with simple, continuous and perfect forms."),
                c("sec-gr-struct", "grammar_sentence_structure", "resume", "How do I build correct sentences?", "Sentence Structure", "A correct sentence needs a subject and a verb, and the Sentence Structure module shows how to build on that."),
            ],
            recommendations: [
                c("sec-gr-rec1", "english_vocab", "cap", "Would you like to test your English?", "Take the English assessment", "The English assessment in Skill Up measures your level and can earn you a certificate."),
                c("sec-gr-rec2", "passage_writing", "resume", "Interested in writing practice?", "Apply grammar in writing", "Writing practice is the best way to put grammar rules to real use."),
            ],
        },
        resume: {
            quickActions: [
                c("sec-res-interview", "mock_interview", "interview", "Can I practise an interview?", "Start the AI mock interview", "The AI mock interview uses your resume to ask relevant questions and score your answers."),
                c("sec-res-jobs", "job_recommendations", "briefcase", "Which jobs match my resume?", "See your recommended jobs", "Once your interview score is 70 or more, jobs matching your resume appear on your dashboard."),
            ],
            recommendations: [
                c("sec-res-rec1", "profile", "user", "Would you like to see your dashboard?", "Track your progress and scores", "Your dashboard brings your resume score, activity progress and jobs together."),
                c("sec-res-rec2", "english_vocab", "book", "Interested in improving your English?", "Strengthen your communication", "Stronger English helps you present your resume and answer interviews with confidence."),
            ],
        },
        skillup: {
            quickActions: [
                c("sec-su-english", "english_vocab", "book", "Where do I start with English?", "English & Vocabulary", "English and Vocabulary is the best starting point, with guides and a mock test."),
                c("sec-su-aptitude", "aptitude", "chart", "How do I prepare for aptitude tests?", "AMCAT, CoCubes and mocks", "Aptitude and Reasoning covers AMCAT and CoCubes style questions with timed mocks."),
                c("sec-su-tech", "tech", "code", "What tech topics are covered?", "Python, DSA, DBMS and more", "The Tech Center covers Python, data structures, databases and more."),
            ],
            recommendations: [
                c("sec-su-rec1", "certifications", "cap", "Would you like to see your certifications?", "What you have earned so far", "Your certifications page shows each module's status and lets you download certificates."),
                c("sec-su-rec2", "mock_interview", "interview", "Interested in a mock interview?", "Practise with the AI interviewer", "The AI mock interview is a great next step once your skills are sharp."),
            ],
        },
        skillup_english: {
            quickActions: [
                c("sec-sue-cert", "certifications", "cap", "How do I get an English certificate?", "Score 70%+ in the mock test", "Score 70 percent or more in the English mock test to earn your English certificate."),
                c("sec-sue-vocab", "vocabulary", "book", "Can I practise vocabulary activities?", "Vocabulary & Idioms", "Vocabulary and Idioms activities help you use business words naturally."),
            ],
            recommendations: [
                c("sec-sue-rec1", "aptitude", "chart", "Would you like to try aptitude next?", "Aptitude & Reasoning", "Aptitude is a common round in hiring tests, so it's a good next step."),
                c("sec-sue-rec2", "grammar", "resume", "Interested in grammar lessons?", "Nouns, verbs, tenses and more", "The Grammar library covers nouns, verbs, tenses and sentence structure."),
            ],
        },
        skillup_aptitude: {
            quickActions: [
                c("sec-sua-cert", "certifications", "cap", "How do I get an aptitude certificate?", "Score 70%+ in the mock test", "Score 70 percent or more in the Aptitude mock test to earn your Aptitude certificate."),
                c("sec-sua-all", "browse_all", "chart", "What else can I practise here?", "Browse all Skill Up tracks", "Skill Up also has English and Tech tracks alongside Aptitude."),
            ],
            recommendations: [
                c("sec-sua-rec1", "tech", "code", "Would you like to explore the Tech Center?", "Python, DSA, DBMS and more", "The Tech Center adds programming and computer science topics to your preparation."),
                c("sec-sua-rec2", "english_vocab", "book", "Interested in English & Vocabulary?", "Take the English assessment", "English and Vocabulary strengthens the communication side of your profile."),
            ],
        },
        skillup_tech: {
            quickActions: [
                c("sec-sut-cert", "certifications", "cap", "How do I get a tech certificate?", "Score 70%+ in the mock test", "Score 70 percent or more in the Tech mock test to earn your Tech certificate."),
                c("sec-sut-all", "browse_all", "code", "Which tech guides are available?", "Browse all Skill Up tracks", "Browse all shows every guide across English, Aptitude and Tech."),
            ],
            recommendations: [
                c("sec-sut-rec1", "mock_interview", "interview", "Would you like a technical mock interview?", "Practise with the AI interviewer", "The AI technical interview tests what you've learned with real interview questions."),
                c("sec-sut-rec2", "aptitude", "chart", "Interested in aptitude practice?", "Aptitude & Reasoning", "Aptitude practice complements your technical preparation for placement tests."),
            ],
        },
        skillup_certs: {
            quickActions: [
                c("sec-suc-english", "english_vocab", "book", "How do I earn the English certificate?", "English & Vocabulary", "The English certificate needs a 70 percent score in the English mock test."),
                c("sec-suc-aptitude", "aptitude", "chart", "How do I earn the aptitude certificate?", "Aptitude & Reasoning", "The Aptitude certificate needs a 70 percent score in the Aptitude mock test."),
                c("sec-suc-tech", "tech", "code", "How do I earn the tech certificate?", "Tech Center", "The Tech certificate needs a 70 percent score in the Tech mock test."),
            ],
            recommendations: [
                c("sec-suc-rec1", "job_recommendations", "briefcase", "Would you like to see matched jobs?", "Your recommended jobs", "Your matched jobs are on the dashboard once your interview score reaches 70."),
                c("sec-suc-rec2", "profile", "user", "Interested in your overall progress?", "Open your dashboard", "Your dashboard shows your full progress across activities and scores."),
            ],
        },
        employer: {
            quickActions: [
                c("sec-emp-post", "post_job", "briefcase", "How do I post a new job?", "Create a new opening", "Posting a job takes a title, skills, experience and salary, and it goes live to candidates right away."),
                c("sec-emp-apps", "all_applications", "resume", "Who has applied recently?", "Review applications", "Applications show each candidate's resume and interview score so you can shortlist quickly."),
                c("sec-emp-cand", "find_candidates", "users", "How do I find candidates?", "Search the candidate pool", "You can search candidates by skills and experience, even if they haven't applied yet."),
            ],
            recommendations: [
                c("sec-emp-rec1", "job_openings", "briefcase", "Would you like to review your openings?", "Manage active job posts", "Reviewing your openings keeps your listings accurate and attractive."),
                c("sec-emp-rec2", "company_profile", "building", "Interested in completing your profile?", "Improve how candidates see you", "Candidates are more likely to apply to companies with a complete profile."),
            ],
        },
        employer_jobs: {
            quickActions: [
                c("sec-empj-post", "post_job", "briefcase", "How do I add another opening?", "Post a new job", "Each new opening reaches matching job seekers on CareerBuddy."),
                c("sec-empj-apps", "all_applications", "resume", "Who applied to my jobs?", "Review applications", "Applications are grouped by job so you can compare candidates side by side."),
            ],
            recommendations: [
                c("sec-empj-rec1", "find_candidates", "users", "Would you like to search candidates?", "Find matching talent", "Searching candidates lets you reach people before they apply."),
                c("sec-empj-rec2", "company_profile", "building", "Interested in updating your company profile?", "Attract better applicants", "An updated company profile helps you attract stronger applicants."),
            ],
        },
        employer_applications: {
            quickActions: [
                c("sec-empa-cand", "find_candidates", "users", "How do I find more candidates?", "Search the candidate pool", "Candidate search finds more people who match your requirements."),
                c("sec-empa-jobs", "job_openings", "briefcase", "Which openings are still active?", "Manage job openings", "Your job openings page shows which roles are still accepting applications."),
            ],
            recommendations: [
                c("sec-empa-rec1", "post_job", "briefcase", "Would you like to post another job?", "Create a new opening", "A new posting brings in a fresh pool of applicants."),
                c("sec-empa-rec2", "company_profile", "building", "Interested in completing your profile?", "Improve how candidates see you", "A complete profile builds trust with the candidates you contact."),
            ],
        },
        employer_candidates: {
            quickActions: [
                c("sec-empc-apps", "all_applications", "resume", "Who has already applied?", "Review applications", "The applications page lists everyone who has already applied to your jobs."),
                c("sec-empc-jobs", "job_openings", "briefcase", "Which roles am I hiring for?", "Manage job openings", "Job openings shows every role you are currently hiring for."),
            ],
            recommendations: [
                c("sec-empc-rec1", "post_job", "briefcase", "Would you like to post a new job?", "Reach more candidates", "Posting a new job helps you reach more of the candidates you're searching for."),
                c("sec-empc-rec2", "company_profile", "building", "Interested in updating your profile?", "Improve how candidates see you", "Candidates check your company profile before responding to you."),
            ],
        },
    };

    // Translated titles for the section cards, keyed by card id. The role
    // cards (guest/student/employer) use RECOMMENDATION_TRANSLATIONS instead.
    const TITLE_I18N = {
        "sec-home-jobs": { vietnam: "Việc làm nào phù hợp với hồ sơ của tôi?", hindi: "मेरी प्रोफ़ाइल से कौन सी नौकरियां मैच करती हैं?", arabic: "ما الوظائف التي تناسب ملفي؟", russian: "Какие вакансии подходят моему профилю?" },
        "sec-home-resume": { vietnam: "CV của tôi tốt đến đâu?", hindi: "मेरा रिज़्यूमे कितना अच्छा है?", arabic: "ما مدى جودة سيرتي الذاتية؟", russian: "Насколько хорошее у меня резюме?" },
        "sec-home-rec1": { vietnam: "Bạn có muốn luyện tiếng Anh không?", hindi: "क्या आप इंग्लिश प्रैक्टिस करना चाहेंगे?", arabic: "هل ترغب في التدرب على الإنجليزية؟", russian: "Хотите попрактиковать английский?" },
        "sec-home-rec2": { vietnam: "Bạn quan tâm đến chứng chỉ?", hindi: "सर्टिफिकेशन में रुचि है?", arabic: "مهتم بالحصول على شهادة؟", russian: "Интересует сертификат?" },
        "sec-dash-jobs": { vietnam: "Xem việc làm được đề xuất", hindi: "मेरी जॉब रिकमेंडेशंस दिखाएं", arabic: "اعرض الوظائف الموصى بها لي", russian: "Показать рекомендованные вакансии" },
        "sec-dash-act": { vietnam: "Tôi nên làm hoạt động nào tiếp theo?", hindi: "अगली कौन सी एक्टिविटी करूं?", arabic: "ما النشاط الذي يجب أن أقوم به بعد ذلك؟", russian: "Какое занятие выбрать следующим?" },
        "sec-dash-rec1": { vietnam: "Bạn có muốn kiểm tra điểm CV không?", hindi: "क्या आप अपना रिज़्यूमे स्कोर चेक करना चाहेंगे?", arabic: "هل ترغب في فحص درجة سيرتك الذاتية؟", russian: "Хотите проверить оценку резюме?" },
        "sec-dash-rec2": { vietnam: "Bạn quan tâm đến việc lấy chứng chỉ?", hindi: "सर्टिफिकेशन पाने में रुचि है?", arabic: "مهتم بالحصول على شهادة؟", russian: "Хотите получить сертификат?" },
        "sec-jobs-interview": { vietnam: "Làm sao để mở thêm việc làm phù hợp?", hindi: "और जॉब मैच कैसे अनलॉक करूं?", arabic: "كيف أفتح المزيد من الوظائف المطابقة؟", russian: "Как открыть больше подходящих вакансий?" },
        "sec-jobs-resume": { vietnam: "Tôi có thể cải thiện CV trước không?", hindi: "क्या मैं पहले अपना रिज़्यूमे सुधार सकता हूँ?", arabic: "هل يمكنني تحسين سيرتي الذاتية أولًا؟", russian: "Можно сначала улучшить резюме?" },
        "sec-jobs-rec1": { vietnam: "Bạn có muốn nâng cao khả năng giao tiếp?", hindi: "क्या आप अपना कम्युनिकेशन बेहतर करना चाहेंगे?", arabic: "هل ترغب في تحسين مهارات التواصل؟", russian: "Хотите улучшить навыки общения?" },
        "sec-jobs-rec2": { vietnam: "Bạn quan tâm đến luyện năng lực?", hindi: "एप्टीट्यूड प्रैक्टिस में रुचि है?", arabic: "مهتم بالتدرب على القدرات؟", russian: "Интересует практика способностей?" },
        "sec-prof-dash": { vietnam: "Tiến độ của tôi thế nào?", hindi: "मेरी प्रोग्रेस कैसी है?", arabic: "كيف هو تقدمي؟", russian: "Какой у меня прогресс?" },
        "sec-prof-jobs": { vietnam: "Việc làm nào hợp với hồ sơ của tôi?", hindi: "कौन सी नौकरियां मेरी प्रोफ़ाइल के लिए सही हैं?", arabic: "ما الوظائف المناسبة لملفي؟", russian: "Какие вакансии подходят моему профилю?" },
        "sec-prof-rec1": { vietnam: "Bạn có muốn cập nhật CV không?", hindi: "क्या आप अपना रिज़्यूमे अपडेट करना चाहेंगे?", arabic: "هل ترغب في تحديث سيرتك الذاتية؟", russian: "Хотите обновить резюме?" },
        "sec-prof-rec2": { vietnam: "Bạn quan tâm đến tính năng Pro?", hindi: "Pro फ़ीचर्स में रुचि है?", arabic: "مهتم بميزات Pro؟", russian: "Интересуют возможности Pro?" },
        "sec-pro-interview": { vietnam: "Phỏng vấn thử với AI là gì?", hindi: "AI मॉक इंटरव्यू क्या है?", arabic: "ما هي المقابلة التجريبية بالذكاء الاصطناعي؟", russian: "Что такое пробное AI-собеседование?" },
        "sec-pro-jobs": { vietnam: "Việc làm được đề xuất hoạt động thế nào?", hindi: "जॉब रिकमेंडेशंस कैसे काम करती हैं?", arabic: "كيف تعمل توصيات الوظائف؟", russian: "Как работают рекомендации вакансий?" },
        "sec-pro-rec1": { vietnam: "Bạn có muốn quay lại bảng điều khiển?", hindi: "क्या आप अपने डैशबोर्ड पर वापस जाना चाहेंगे?", arabic: "هل ترغب في العودة إلى لوحة التحكم؟", russian: "Хотите вернуться на панель управления?" },
        "sec-pro-rec2": { vietnam: "Bạn quan tâm đến các hoạt động miễn phí?", hindi: "फ्री एक्टिविटीज़ में रुचि है?", arabic: "مهتم بالأنشطة المجانية؟", russian: "Интересуют бесплатные занятия?" },
        "sec-act-speaking": { vietnam: "Làm sao để cải thiện kỹ năng nói?", hindi: "मैं अपनी स्पीकिंग कैसे सुधारूं?", arabic: "كيف أحسّن مهارة التحدث؟", russian: "Как улучшить разговорную речь?" },
        "sec-act-writing": { vietnam: "Làm sao để viết email tốt hơn?", hindi: "मैं बेहतर ईमेल कैसे लिखूं?", arabic: "كيف أكتب رسائل بريد أفضل؟", russian: "Как писать письма лучше?" },
        "sec-act-listen": { vietnam: "Tôi có thể luyện nghe không?", hindi: "क्या मैं लिसनिंग प्रैक्टिस कर सकता हूँ?", arabic: "هل يمكنني التدرب على الاستماع؟", russian: "Можно потренировать аудирование?" },
        "sec-act-rec1": { vietnam: "Bạn có muốn tham gia workshop?", hindi: "क्या आप वर्कशॉप जॉइन करना चाहेंगे?", arabic: "هل ترغب في الانضمام إلى ورشة عمل؟", russian: "Хотите присоединиться к воркшопу?" },
        "sec-act-rec2": { vietnam: "Bạn quan tâm đến chứng chỉ?", hindi: "सर्टिफिकेशन में रुचि है?", arabic: "مهتم بالحصول على شهادة؟", russian: "Интересует сертификат?" },
        "sec-ws-gd": { vietnam: "Thảo luận nhóm diễn ra thế nào?", hindi: "ग्रुप डिस्कशन कैसे काम करता है?", arabic: "كيف يعمل النقاش الجماعي؟", russian: "Как проходит групповая дискуссия?" },
        "sec-ws-jam": { vietnam: "JAM là gì?", hindi: "JAM क्या है?", arabic: "ما هو JAM؟", russian: "Что такое JAM?" },
        "sec-ws-rp": { vietnam: "Tôi có thể luyện một tình huống công sở?", hindi: "क्या मैं किसी वर्कप्लेस सिचुएशन की प्रैक्टिस कर सकता हूँ?", arabic: "هل يمكنني التدرب على موقف عمل؟", russian: "Можно отработать рабочую ситуацию?" },
        "sec-ws-rec1": { vietnam: "Bạn có muốn phỏng vấn thử?", hindi: "क्या आप मॉक इंटरव्यू देना चाहेंगे?", arabic: "هل ترغب في مقابلة تجريبية؟", russian: "Хотите пройти пробное собеседование?" },
        "sec-ws-rec2": { vietnam: "Bạn quan tâm đến thêm hoạt động?", hindi: "और एक्टिविटीज़ में रुचि है?", arabic: "مهتم بمزيد من الأنشطة؟", russian: "Интересуют другие занятия?" },
        "sec-gr-tenses": { vietnam: "Các thì hoạt động thế nào?", hindi: "टेंस कैसे काम करते हैं?", arabic: "كيف تعمل الأزمنة؟", russian: "Как устроены времена?" },
        "sec-gr-struct": { vietnam: "Làm sao để đặt câu đúng?", hindi: "मैं सही वाक्य कैसे बनाऊं?", arabic: "كيف أبني جملًا صحيحة؟", russian: "Как строить правильные предложения?" },
        "sec-gr-rec1": { vietnam: "Bạn có muốn kiểm tra tiếng Anh?", hindi: "क्या आप अपनी इंग्लिश टेस्ट करना चाहेंगे?", arabic: "هل ترغب في اختبار لغتك الإنجليزية؟", russian: "Хотите проверить свой английский?" },
        "sec-gr-rec2": { vietnam: "Bạn quan tâm đến luyện viết?", hindi: "राइटिंग प्रैक्टिस में रुचि है?", arabic: "مهتم بالتدرب على الكتابة؟", russian: "Интересует практика письма?" },
        "sec-res-interview": { vietnam: "Tôi có thể luyện phỏng vấn không?", hindi: "क्या मैं इंटरव्यू की प्रैक्टिस कर सकता हूँ?", arabic: "هل يمكنني التدرب على مقابلة؟", russian: "Можно потренироваться к собеседованию?" },
        "sec-res-jobs": { vietnam: "Việc làm nào khớp với CV của tôi?", hindi: "मेरे रिज़्यूमे से कौन सी नौकरियां मैच करती हैं?", arabic: "ما الوظائف التي تطابق سيرتي الذاتية؟", russian: "Какие вакансии подходят к моему резюме?" },
        "sec-res-rec1": { vietnam: "Bạn có muốn xem bảng điều khiển?", hindi: "क्या आप अपना डैशबोर्ड देखना चाहेंगे?", arabic: "هل ترغب في رؤية لوحة التحكم؟", russian: "Хотите открыть панель управления?" },
        "sec-res-rec2": { vietnam: "Bạn quan tâm đến việc cải thiện tiếng Anh?", hindi: "इंग्लिश सुधारने में रुचि है?", arabic: "مهتم بتحسين لغتك الإنجليزية؟", russian: "Хотите улучшить английский?" },
        "sec-su-english": { vietnam: "Tôi nên bắt đầu học tiếng Anh từ đâu?", hindi: "इंग्लिश कहां से शुरू करूं?", arabic: "من أين أبدأ في تعلم الإنجليزية؟", russian: "С чего начать изучение английского?" },
        "sec-su-aptitude": { vietnam: "Làm sao để chuẩn bị bài thi năng lực?", hindi: "एप्टीट्यूड टेस्ट की तैयारी कैसे करूं?", arabic: "كيف أستعد لاختبارات القدرات؟", russian: "Как готовиться к тестам на способности?" },
        "sec-su-tech": { vietnam: "Có những chủ đề công nghệ nào?", hindi: "कौन से टेक टॉपिक्स कवर हैं?", arabic: "ما الموضوعات التقنية المتوفرة؟", russian: "Какие технические темы охвачены?" },
        "sec-su-rec1": { vietnam: "Bạn có muốn xem chứng chỉ của mình?", hindi: "क्या आप अपने सर्टिफिकेशन देखना चाहेंगे?", arabic: "هل ترغب في رؤية شهاداتك؟", russian: "Хотите посмотреть свои сертификаты?" },
        "sec-su-rec2": { vietnam: "Bạn quan tâm đến phỏng vấn thử?", hindi: "मॉक इंटरव्यू में रुचि है?", arabic: "مهتم بمقابلة تجريبية؟", russian: "Интересует пробное собеседование?" },
        "sec-sue-cert": { vietnam: "Làm sao để có chứng chỉ tiếng Anh?", hindi: "इंग्लिश सर्टिफिकेट कैसे मिलेगा?", arabic: "كيف أحصل على شهادة الإنجليزية؟", russian: "Как получить сертификат по английскому?" },
        "sec-sue-vocab": { vietnam: "Tôi có thể luyện từ vựng không?", hindi: "क्या मैं वोकैबुलरी एक्टिविटीज़ कर सकता हूँ?", arabic: "هل يمكنني التدرب على أنشطة المفردات؟", russian: "Можно позаниматься лексикой?" },
        "sec-sue-rec1": { vietnam: "Bạn có muốn thử năng lực tiếp theo?", hindi: "क्या आप आगे एप्टीट्यूड आज़माना चाहेंगे?", arabic: "هل ترغب في تجربة القدرات بعد ذلك؟", russian: "Хотите попробовать способности дальше?" },
        "sec-sue-rec2": { vietnam: "Bạn quan tâm đến bài học ngữ pháp?", hindi: "ग्रामर लेसन में रुचि है?", arabic: "مهتم بدروس القواعد؟", russian: "Интересуют уроки грамматики?" },
        "sec-sua-cert": { vietnam: "Làm sao để có chứng chỉ năng lực?", hindi: "एप्टीट्यूड सर्टिफिकेट कैसे मिलेगा?", arabic: "كيف أحصل على شهادة القدرات؟", russian: "Как получить сертификат по способностям?" },
        "sec-sua-all": { vietnam: "Tôi có thể luyện gì khác ở đây?", hindi: "यहां और क्या प्रैक्टिस कर सकता हूँ?", arabic: "ماذا يمكنني أن أتدرب عليه أيضًا هنا؟", russian: "Что ещё здесь можно потренировать?" },
        "sec-sua-rec1": { vietnam: "Bạn có muốn khám phá Tech Center?", hindi: "क्या आप Tech Center देखना चाहेंगे?", arabic: "هل ترغب في استكشاف Tech Center؟", russian: "Хотите заглянуть в Tech Center?" },
        "sec-sua-rec2": { vietnam: "Bạn quan tâm đến Tiếng Anh và Từ vựng?", hindi: "इंग्लिश और वोकैबुलरी में रुचि है?", arabic: "مهتم بالإنجليزية والمفردات؟", russian: "Интересует «Английский и лексика»?" },
        "sec-sut-cert": { vietnam: "Làm sao để có chứng chỉ công nghệ?", hindi: "टेक सर्टिफिकेट कैसे मिलेगा?", arabic: "كيف أحصل على شهادة التقنية؟", russian: "Как получить сертификат по технологиям?" },
        "sec-sut-all": { vietnam: "Có những tài liệu công nghệ nào?", hindi: "कौन सी टेक गाइड्स उपलब्ध हैं?", arabic: "ما الأدلة التقنية المتاحة؟", russian: "Какие технические руководства доступны?" },
        "sec-sut-rec1": { vietnam: "Bạn có muốn phỏng vấn kỹ thuật thử?", hindi: "क्या आप टेक्निकल मॉक इंटरव्यू देना चाहेंगे?", arabic: "هل ترغب في مقابلة تقنية تجريبية؟", russian: "Хотите пройти техническое пробное собеседование?" },
        "sec-sut-rec2": { vietnam: "Bạn quan tâm đến luyện năng lực?", hindi: "एप्टीट्यूड प्रैक्टिस में रुचि है?", arabic: "مهتم بالتدرب على القدرات؟", russian: "Интересует практика способностей?" },
        "sec-suc-english": { vietnam: "Làm sao để đạt chứng chỉ tiếng Anh?", hindi: "इंग्लिश सर्टिफिकेट कैसे हासिल करूं?", arabic: "كيف أنال شهادة الإنجليزية؟", russian: "Как заработать сертификат по английскому?" },
        "sec-suc-aptitude": { vietnam: "Làm sao để đạt chứng chỉ năng lực?", hindi: "एप्टीट्यूड सर्टिफिकेट कैसे हासिल करूं?", arabic: "كيف أنال شهادة القدرات؟", russian: "Как заработать сертификат по способностям?" },
        "sec-suc-tech": { vietnam: "Làm sao để đạt chứng chỉ công nghệ?", hindi: "टेक सर्टिफिकेट कैसे हासिल करूं?", arabic: "كيف أنال شهادة التقنية؟", russian: "Как заработать сертификат по технологиям?" },
        "sec-suc-rec1": { vietnam: "Bạn có muốn xem việc làm phù hợp?", hindi: "क्या आप मैच की गई नौकरियां देखना चाहेंगे?", arabic: "هل ترغب في رؤية الوظائف المطابقة؟", russian: "Хотите посмотреть подходящие вакансии?" },
        "sec-suc-rec2": { vietnam: "Bạn quan tâm đến tiến độ tổng thể?", hindi: "अपनी कुल प्रोग्रेस में रुचि है?", arabic: "مهتم بتقدمك العام؟", russian: "Интересует ваш общий прогресс?" },
        "sec-emp-post": { vietnam: "Làm sao để đăng tin tuyển dụng mới?", hindi: "नई जॉब कैसे पोस्ट करूं?", arabic: "كيف أنشر وظيفة جديدة؟", russian: "Как опубликовать новую вакансию?" },
        "sec-emp-apps": { vietnam: "Gần đây ai đã ứng tuyển?", hindi: "हाल ही में किसने आवेदन किया?", arabic: "من تقدّم مؤخرًا؟", russian: "Кто откликнулся недавно?" },
        "sec-emp-cand": { vietnam: "Làm sao để tìm ứng viên?", hindi: "कैंडिडेट्स कैसे खोजूं?", arabic: "كيف أجد المرشحين؟", russian: "Как найти кандидатов?" },
        "sec-emp-rec1": { vietnam: "Bạn có muốn xem lại tin tuyển dụng?", hindi: "क्या आप अपनी ओपनिंग्स रिव्यू करना चाहेंगे?", arabic: "هل ترغب في مراجعة وظائفك الشاغرة؟", russian: "Хотите просмотреть свои вакансии?" },
        "sec-emp-rec2": { vietnam: "Bạn quan tâm đến việc hoàn thiện hồ sơ?", hindi: "अपनी प्रोफ़ाइल पूरी करने में रुचि है?", arabic: "مهتم بإكمال ملفك؟", russian: "Хотите заполнить профиль?" },
        "sec-empj-post": { vietnam: "Làm sao để thêm tin tuyển dụng khác?", hindi: "एक और ओपनिंग कैसे जोड़ूं?", arabic: "كيف أضيف وظيفة شاغرة أخرى؟", russian: "Как добавить ещё одну вакансию?" },
        "sec-empj-apps": { vietnam: "Ai đã ứng tuyển vào công việc của tôi?", hindi: "मेरी नौकरियों के लिए किसने आवेदन किया?", arabic: "من تقدّم لوظائفي؟", russian: "Кто откликнулся на мои вакансии?" },
        "sec-empj-rec1": { vietnam: "Bạn có muốn tìm kiếm ứng viên?", hindi: "क्या आप कैंडिडेट्स खोजना चाहेंगे?", arabic: "هل ترغب في البحث عن مرشحين؟", russian: "Хотите поискать кандидатов?" },
        "sec-empj-rec2": { vietnam: "Bạn quan tâm đến việc cập nhật hồ sơ công ty?", hindi: "कंपनी प्रोफ़ाइल अपडेट करने में रुचि है?", arabic: "مهتم بتحديث ملف شركتك؟", russian: "Хотите обновить профиль компании?" },
        "sec-empa-cand": { vietnam: "Làm sao để tìm thêm ứng viên?", hindi: "और कैंडिडेट्स कैसे खोजूं?", arabic: "كيف أجد مزيدًا من المرشحين؟", russian: "Как найти больше кандидатов?" },
        "sec-empa-jobs": { vietnam: "Tin tuyển dụng nào vẫn đang mở?", hindi: "कौन सी ओपनिंग्स अभी एक्टिव हैं?", arabic: "ما الوظائف الشاغرة التي لا تزال نشطة؟", russian: "Какие вакансии ещё активны?" },
        "sec-empa-rec1": { vietnam: "Bạn có muốn đăng thêm một công việc?", hindi: "क्या आप एक और जॉब पोस्ट करना चाहेंगे?", arabic: "هل ترغب في نشر وظيفة أخرى؟", russian: "Хотите опубликовать ещё вакансию?" },
        "sec-empa-rec2": { vietnam: "Bạn quan tâm đến việc hoàn thiện hồ sơ?", hindi: "अपनी प्रोफ़ाइल पूरी करने में रुचि है?", arabic: "مهتم بإكمال ملفك؟", russian: "Хотите заполнить профиль?" },
        "sec-empc-apps": { vietnam: "Ai đã ứng tuyển rồi?", hindi: "किसने पहले ही आवेदन कर दिया है?", arabic: "من تقدّم بالفعل؟", russian: "Кто уже откликнулся?" },
        "sec-empc-jobs": { vietnam: "Tôi đang tuyển những vị trí nào?", hindi: "मैं किन भूमिकाओं के लिए हायर कर रहा हूँ?", arabic: "ما الوظائف التي أوظف لها؟", russian: "На какие позиции я нанимаю?" },
        "sec-empc-rec1": { vietnam: "Bạn có muốn đăng công việc mới?", hindi: "क्या आप नई जॉब पोस्ट करना चाहेंगे?", arabic: "هل ترغب في نشر وظيفة جديدة؟", russian: "Хотите опубликовать новую вакансию?" },
        "sec-empc-rec2": { vietnam: "Bạn quan tâm đến việc cập nhật hồ sơ?", hindi: "अपनी प्रोफ़ाइल अपडेट करने में रुचि है?", arabic: "مهتم بتحديث ملفك؟", russian: "Хотите обновить профиль?" },
    };

    // Translations of each card's `context` line, keyed by card id. English
    // stays on the card itself; buildWelcomeReply() picks the selected language.
    const CONTEXT_I18N = {
        "guest-profile": {
            vietnam: "Đăng ký làm người tìm việc giúp bạn luyện tiếng Anh, chấm điểm CV, phỏng vấn thử với AI và nhận việc làm phù hợp, tất cả ở một nơi.",
            hindi: "Job seeker के रूप में रजिस्टर करने पर आपको इंग्लिश प्रैक्टिस, रिज़्यूमे स्कोरिंग, AI मॉक इंटरव्यू और मैचिंग नौकरियां, सब एक ही जगह मिलती हैं।",
            arabic: "التسجيل كباحث عن عمل يمنحك تدريبًا على الإنجليزية وتقييمًا لسيرتك الذاتية ومقابلات تجريبية بالذكاء الاصطناعي ووظائف مطابقة، كل ذلك في مكان واحد.",
            russian: "Регистрация соискателя даёт вам практику английского, оценку резюме, пробные AI-собеседования и подходящие вакансии — всё в одном месте.",
        },
        "guest-explore": {
            vietnam: "Tài khoản nhà tuyển dụng cho phép bạn đăng tin, tìm ứng viên và xem đơn ứng tuyển ngay trên bảng điều khiển của mình.",
            hindi: "Employer अकाउंट से आप अपने डैशबोर्ड से नौकरियां पोस्ट कर सकते हैं, कैंडिडेट्स खोज सकते हैं और आवेदन देख सकते हैं।",
            arabic: "يتيح لك حساب صاحب العمل نشر الوظائف والبحث عن المرشحين ومراجعة الطلبات من لوحة التحكم الخاصة بك.",
            russian: "Аккаунт работодателя позволяет публиковать вакансии, искать кандидатов и просматривать отклики в своей панели.",
        },
        "guest-signin": {
            vietnam: "Đăng nhập sẽ đưa bạn trở lại tiến độ học tập, điểm CV và các việc làm phù hợp.",
            hindi: "साइन इन करने पर आप अपनी लर्निंग प्रोग्रेस, रिज़्यूमे स्कोर और जॉब मैच पर वापस पहुंचेंगे।",
            arabic: "تسجيل الدخول يعيدك إلى تقدمك في التعلم ودرجة سيرتك الذاتية والوظائف المطابقة.",
            russian: "После входа вы вернётесь к своему прогрессу в обучении, оценке резюме и подходящим вакансиям.",
        },
        "guest-employer": {
            vietnam: "Cổng nhà tuyển dụng là nơi bạn quản lý tin tuyển dụng, ứng viên và lịch phỏng vấn.",
            hindi: "Employer पोर्टल में आप अपनी ओपनिंग्स, आवेदकों और इंटरव्यू को मैनेज करते हैं।",
            arabic: "بوابة صاحب العمل هي المكان الذي تدير فيه وظائفك الشاغرة والمتقدمين والمقابلات.",
            russian: "Портал работодателя — это место, где вы управляете вакансиями, кандидатами и собеседованиями.",
        },
        "student-jobs": {
            vietnam: "Các việc làm được đề xuất phù hợp với kinh nghiệm và kỹ năng của bạn, và được mở khi bạn đạt từ 70 điểm trong buổi phỏng vấn thử với AI.",
            hindi: "आपकी सुझाई गई नौकरियां आपके अनुभव और स्किल्स से मैच होती हैं, और AI मॉक इंटरव्यू में 70 या उससे ज़्यादा स्कोर करने पर अनलॉक होती हैं।",
            arabic: "الوظائف الموصى بها تتوافق مع خبرتك ومهاراتك، وتُفتح بعد حصولك على 70 أو أكثر في المقابلة التجريبية بالذكاء الاصطناعي.",
            russian: "Рекомендованные вакансии подбираются под ваш опыт и навыки и открываются, когда вы набираете 70 баллов и выше на пробном AI-собеседовании.",
        },
        "student-resume": {
            vietnam: "Resume Builder sẽ phân tích CV, cho bạn điểm ATS và chỉ rõ những gì cần cải thiện.",
            hindi: "Resume Builder आपके रिज़्यूमे को पार्स करता है, ATS स्कोर देता है और बताता है कि क्या सुधारना है।",
            arabic: "يحلل Resume Builder سيرتك الذاتية ويمنحك درجة ATS ويوضح لك بالضبط ما يجب تحسينه.",
            russian: "Resume Builder разбирает ваше резюме, выставляет оценку ATS и точно подсказывает, что улучшить.",
        },
        "student-dashboard": {
            vietnam: "Bảng điều khiển hiển thị tiến độ hoạt động, điểm số và việc làm được đề xuất chỉ trong một cái nhìn.",
            hindi: "आपका डैशबोर्ड एक नज़र में आपकी एक्टिविटी प्रोग्रेस, स्कोर और सुझाई गई नौकरियां दिखाता है।",
            arabic: "تعرض لوحة التحكم تقدمك في الأنشطة ودرجاتك والوظائف الموصى بها في لمحة واحدة.",
            russian: "Панель управления показывает прогресс по занятиям, баллы и рекомендованные вакансии с первого взгляда.",
        },
        "student-matches": {
            vietnam: "Việc làm phù hợp được chọn dựa trên CV và điểm phỏng vấn, nên chúng khớp với kinh nghiệm của bạn.",
            hindi: "मैच की गई नौकरियां आपके रिज़्यूमे और इंटरव्यू स्कोर के आधार पर चुनी जाती हैं, इसलिए वे आपके अनुभव से मेल खाती हैं।",
            arabic: "يتم اختيار الوظائف المطابقة بناءً على سيرتك الذاتية ودرجة المقابلة، لذا فهي تناسب خبرتك.",
            russian: "Подходящие вакансии подбираются по вашему резюме и баллу за собеседование, поэтому они соответствуют вашему опыту.",
        },
        "student-cert": {
            vietnam: "Chứng chỉ được cấp trong Skill Up khi bạn đạt từ 70 phần trăm trong bài thi thử của một học phần.",
            hindi: "सर्टिफिकेशन Skill Up में किसी मॉड्यूल के मॉक टेस्ट में 70 प्रतिशत या उससे ज़्यादा स्कोर करके मिलते हैं।",
            arabic: "تحصل على الشهادات في Skill Up عند تحقيق 70 بالمئة أو أكثر في الاختبار التجريبي لأي وحدة.",
            russian: "Сертификаты в Skill Up выдаются, если набрать 70 процентов и больше в пробном тесте модуля.",
        },
        "student-english": {
            vietnam: "Lộ trình Tiếng Anh và Từ vựng có tài liệu hướng dẫn và bài thi thử để nâng cao tiếng Anh thương mại của bạn.",
            hindi: "इंग्लिश और वोकैबुलरी ट्रैक में आपकी बिज़नेस इंग्लिश मज़बूत करने के लिए गाइड और एक मॉक टेस्ट है।",
            arabic: "يحتوي مسار الإنجليزية والمفردات على أدلة واختبار تجريبي لتقوية لغتك الإنجليزية في مجال الأعمال.",
            russian: "Курс «Английский и лексика» содержит руководства и пробный тест для укрепления делового английского.",
        },
        "employer-jobs": {
            vietnam: "Trang Tin tuyển dụng liệt kê mọi vị trí bạn đã đăng, để bạn chỉnh sửa, đóng hoặc xem xét từng tin.",
            hindi: "जॉब ओपनिंग्स में आपकी पोस्ट की गई हर भूमिका दिखती है, ताकि आप उसे एडिट, बंद या रिव्यू कर सकें।",
            arabic: "تعرض صفحة الوظائف الشاغرة كل وظيفة نشرتها، لتتمكن من تعديلها أو إغلاقها أو مراجعتها.",
            russian: "В разделе «Вакансии» собраны все опубликованные вами позиции — их можно изменить, закрыть или просмотреть.",
        },
        "employer-candidates": {
            vietnam: "Tìm kiếm ứng viên cho phép bạn lọc người tìm việc theo kỹ năng, kinh nghiệm và điểm phỏng vấn.",
            hindi: "कैंडिडेट सर्च से आप जॉब सीकर्स को स्किल्स, अनुभव और इंटरव्यू स्कोर के आधार पर फ़िल्टर कर सकते हैं।",
            arabic: "يتيح لك البحث عن المرشحين تصفية الباحثين عن عمل حسب المهارات والخبرة ودرجات المقابلة.",
            russian: "Поиск кандидатов позволяет фильтровать соискателей по навыкам, опыту и баллам за собеседование.",
        },
        "employer-applications": {
            vietnam: "Mục Tất cả đơn ứng tuyển tập hợp mọi người đã nộp đơn, kèm CV và kết quả phỏng vấn của họ.",
            hindi: "ऑल एप्लीकेशंस में हर आवेदक उनके रिज़्यूमे और इंटरव्यू रिज़ल्ट के साथ एक जगह मिलता है।",
            arabic: "تجمع صفحة جميع الطلبات كل من تقدّم، مع سيرهم الذاتية ونتائج مقابلاتهم.",
            russian: "В разделе «Все отклики» собраны все кандидаты с их резюме и результатами собеседований.",
        },
        "employer-interviews": {
            vietnam: "Bạn có thể chọn những ứng viên đã hoàn thành phỏng vấn AI và sẵn sàng được tuyển.",
            hindi: "आप उन कैंडिडेट्स को शॉर्टलिस्ट कर सकते हैं जो AI इंटरव्यू पूरा कर चुके हैं और हायरिंग के लिए तैयार हैं।",
            arabic: "يمكنك إدراج المرشحين الذين أكملوا مقابلة الذكاء الاصطناعي وأصبحوا جاهزين للتوظيف في القائمة المختصرة.",
            russian: "Вы можете отобрать кандидатов, которые уже прошли AI-собеседование и готовы к найму.",
        },
        "employer-new-apps": {
            vietnam: "Các đơn ứng tuyển mới đang chờ bạn xem xét; phản hồi nhanh giúp bạn giữ được ứng viên giỏi.",
            hindi: "नए आवेदन आपके रिव्यू का इंतज़ार कर रहे हैं; जल्दी जवाब देने से अच्छे कैंडिडेट्स हाथ से नहीं निकलते।",
            arabic: "هناك طلبات جديدة بانتظار مراجعتك؛ الرد السريع يساعدك على الفوز بالمرشحين الأقوياء.",
            russian: "Новые отклики ждут вашего рассмотрения; быстрый ответ помогает не упустить сильных кандидатов.",
        },
        "employer-active": {
            vietnam: "Các tin đang hoạt động là những vị trí ứng viên có thể ứng tuyển ngay bây giờ.",
            hindi: "आपकी एक्टिव पोस्टिंग्स वे भूमिकाएं हैं जिन पर कैंडिडेट्स अभी आवेदन कर सकते हैं।",
            arabic: "وظائفك النشطة هي الوظائف التي يمكن للمرشحين التقدم إليها الآن.",
            russian: "Активные вакансии — это позиции, на которые кандидаты могут откликнуться прямо сейчас.",
        },
        "employer-company": {
            vietnam: "Hồ sơ công ty đầy đủ với logo và mô tả giúp tạo niềm tin với ứng viên.",
            hindi: "लोगो और विवरण के साथ पूरी कंपनी प्रोफ़ाइल कैंडिडेट्स का भरोसा बढ़ाती है।",
            arabic: "ملف الشركة المكتمل بالشعار والوصف يبني الثقة لدى المرشحين.",
            russian: "Заполненный профиль компании с логотипом и описанием вызывает доверие у кандидатов.",
        },
        "sec-home-jobs": {
            vietnam: "Việc làm được đề xuất khớp với CV của bạn và được mở sau khi đạt từ 70 điểm trong buổi phỏng vấn thử với AI.",
            hindi: "जॉब रिकमेंडेशंस आपके रिज़्यूमे से मैच होती हैं और AI मॉक इंटरव्यू में 70 से ज़्यादा स्कोर के बाद अनलॉक होती हैं।",
            arabic: "الوظائف الموصى بها تطابق سيرتك الذاتية وتُفتح بعد الحصول على أكثر من 70 في المقابلة التجريبية بالذكاء الاصطناعي.",
            russian: "Рекомендации вакансий подбираются под ваше резюме и открываются после 70+ баллов на пробном AI-собеседовании.",
        },
        "sec-home-resume": {
            vietnam: "Tải CV lên và trình phân tích của Buddy sẽ cho bạn điểm ATS kèm gợi ý cải thiện rõ ràng.",
            hindi: "अपना रिज़्यूमे अपलोड करें, Buddy का पार्सर आपको साफ़ सुधार टिप्स के साथ ATS स्कोर देगा।",
            arabic: "ارفع سيرتك الذاتية وسيمنحك محلل Buddy درجة ATS مع نصائح واضحة للتحسين.",
            russian: "Загрузите резюме, и анализатор Buddy выставит оценку ATS с понятными советами по улучшению.",
        },
        "sec-home-rec1": {
            vietnam: "Các hoạt động gồm nói, viết, từ vựng và nghe, mỗi phần đều được chấm điểm để bạn theo dõi tiến độ.",
            hindi: "एक्टिविटीज़ में स्पीकिंग, राइटिंग, वोकैबुलरी और लिसनिंग शामिल हैं, और हर एक का स्कोर मिलता है ताकि आप प्रोग्रेस ट्रैक कर सकें।",
            arabic: "تشمل الأنشطة التحدث والكتابة والمفردات والاستماع، وكل منها يُقيَّم لتتابع تقدمك.",
            russian: "Занятия охватывают говорение, письмо, лексику и аудирование, и каждое оценивается, чтобы вы видели прогресс.",
        },
        "sec-home-rec2": {
            vietnam: "Chứng chỉ Skill Up đạt được khi bạn có từ 70 phần trăm trong bài thi thử Tiếng Anh, Năng lực hoặc Công nghệ.",
            hindi: "Skill Up सर्टिफिकेशन इंग्लिश, एप्टीट्यूड या टेक मॉक टेस्ट में 70 प्रतिशत या उससे ज़्यादा स्कोर करके मिलते हैं।",
            arabic: "تحصل على شهادات Skill Up بتحقيق 70 بالمئة أو أكثر في الاختبارات التجريبية للإنجليزية أو القدرات أو التقنية.",
            russian: "Сертификаты Skill Up выдаются за 70 процентов и выше в пробных тестах по английскому, способностям или технологиям.",
        },
        "sec-dash-jobs": {
            vietnam: "Các việc làm được đề xuất nằm ngay trên bảng điều khiển này, khớp với kinh nghiệm và kỹ năng của bạn.",
            hindi: "आपकी सुझाई गई नौकरियां इसी डैशबोर्ड पर हैं, जो आपके अनुभव और स्किल्स से मैच होती हैं।",
            arabic: "وظائفك الموصى بها موجودة في لوحة التحكم هذه، ومطابقة لخبرتك ومهاراتك.",
            russian: "Рекомендованные вакансии находятся прямо на этой панели и подобраны под ваш опыт и навыки.",
        },
        "sec-dash-act": {
            vietnam: "Tiếp tục các hoạt động đang dở là cách nhanh nhất để nâng điểm của bạn.",
            hindi: "जहां छोड़ा था वहीं से एक्टिविटीज़ जारी रखना आपके स्कोर बढ़ाने का सबसे तेज़ तरीका है।",
            arabic: "متابعة الأنشطة من حيث توقفت هي أسرع طريقة لرفع درجاتك.",
            russian: "Продолжить занятия с того места, где вы остановились, — самый быстрый способ поднять баллы.",
        },
        "sec-dash-rec1": {
            vietnam: "Điểm ATS cao hơn giúp hệ thống của nhà tuyển dụng dễ tìm thấy CV của bạn hơn.",
            hindi: "ज़्यादा ATS स्कोर से रिक्रूटर्स के सिस्टम आपके रिज़्यूमे को आसानी से ढूंढ पाते हैं।",
            arabic: "درجة ATS الأعلى تجعل أنظمة مسؤولي التوظيف تعثر على سيرتك الذاتية بسهولة أكبر.",
            russian: "Более высокая оценка ATS помогает системам рекрутеров находить ваше резюме.",
        },
        "sec-dash-rec2": {
            vietnam: "Chứng chỉ Skill Up cho nhà tuyển dụng thấy điểm số đã được xác minh về Tiếng Anh, Năng lực hoặc Công nghệ.",
            hindi: "Skill Up सर्टिफिकेट एम्प्लॉयर्स को इंग्लिश, एप्टीट्यूड या टेक में आपका वेरिफ़ाइड स्कोर दिखाता है।",
            arabic: "تُظهر شهادة Skill Up لأصحاب العمل درجة موثقة في الإنجليزية أو القدرات أو التقنية.",
            russian: "Сертификат Skill Up показывает работодателям подтверждённый балл по английскому, способностям или технологиям.",
        },
        "sec-jobs-interview": {
            vietnam: "Đạt từ 70 điểm trong buổi phỏng vấn thử với AI sẽ mở thêm nhiều việc làm phù hợp cho bạn.",
            hindi: "AI मॉक इंटरव्यू में 70 या उससे ज़्यादा स्कोर करने पर आपके लिए और जॉब मैच अनलॉक होते हैं।",
            arabic: "الحصول على 70 أو أكثر في المقابلة التجريبية بالذكاء الاصطناعي يفتح لك المزيد من الوظائف المطابقة.",
            russian: "70 баллов и выше на пробном AI-собеседовании открывают вам больше подходящих вакансий.",
        },
        "sec-jobs-resume": {
            vietnam: "Cải thiện CV giúp tăng điểm ATS và chất lượng các việc làm phù hợp.",
            hindi: "रिज़्यूमे सुधारने से आपका ATS स्कोर और जॉब मैच की क्वालिटी दोनों बढ़ते हैं।",
            arabic: "تحسين سيرتك الذاتية يرفع درجة ATS وجودة الوظائف المطابقة.",
            russian: "Улучшение резюме повышает оценку ATS и качество подбора вакансий.",
        },
        "sec-jobs-rec1": {
            vietnam: "Giao tiếp chuyên nghiệp rõ ràng giúp bạn nổi bật trong hồ sơ và buổi phỏng vấn.",
            hindi: "साफ़ प्रोफेशनल कम्युनिकेशन आपको एप्लीकेशंस और इंटरव्यू में अलग पहचान दिलाता है।",
            arabic: "التواصل المهني الواضح يجعلك مميزًا في الطلبات والمقابلات.",
            russian: "Чёткое профессиональное общение выделяет вас в откликах и на собеседованиях.",
        },
        "sec-jobs-rec2": {
            vietnam: "Nhiều bài kiểm tra tuyển dụng có vòng năng lực, nên luyện tập ở đây giúp bạn có lợi thế.",
            hindi: "कई हायरिंग टेस्ट में एप्टीट्यूड राउंड होता है, इसलिए यहां प्रैक्टिस आपको बढ़त देती है।",
            arabic: "تتضمن كثير من اختبارات التوظيف جولات للقدرات، لذا فالتدرب هنا يمنحك ميزة.",
            russian: "Во многих тестах при найме есть раунд на способности, так что практика здесь даёт преимущество.",
        },
        "sec-prof-dash": {
            vietnam: "Bảng điều khiển hiển thị các hoạt động đã hoàn thành, tổng điểm và việc làm được đề xuất.",
            hindi: "आपका डैशबोर्ड पूरी की गई एक्टिविटीज़, कुल स्कोर और सुझाई गई नौकरियां दिखाता है।",
            arabic: "تعرض لوحة التحكم الأنشطة المكتملة والدرجة الإجمالية والوظائف الموصى بها.",
            russian: "Панель показывает завершённые занятия, общий балл и рекомендованные вакансии.",
        },
        "sec-prof-jobs": {
            vietnam: "Việc làm được chọn dựa trên CV và điểm phỏng vấn của bạn.",
            hindi: "नौकरियां आपके रिज़्यूमे और इंटरव्यू स्कोर के आधार पर मैच की जाती हैं।",
            arabic: "تتم مطابقة الوظائف باستخدام سيرتك الذاتية ودرجة مقابلتك.",
            russian: "Вакансии подбираются по вашему резюме и баллу за собеседование.",
        },
        "sec-prof-rec1": {
            vietnam: "Kiểm tra lại CV sau khi chỉnh sửa sẽ cho thấy điểm ATS của bạn cải thiện ra sao.",
            hindi: "बदलाव के बाद रिज़्यूमे दोबारा चेक करने से पता चलता है कि आपका ATS स्कोर कितना सुधरा।",
            arabic: "إعادة فحص سيرتك الذاتية بعد التعديل تُظهر مدى تحسن درجة ATS.",
            russian: "Повторная проверка резюме после правок покажет, насколько выросла оценка ATS.",
        },
        "sec-prof-rec2": {
            vietnam: "Gói Pro mở khóa phỏng vấn kỹ thuật với AI và không giới hạn việc làm được đề xuất.",
            hindi: "Pro प्लान AI टेक्निकल इंटरव्यू और अनलिमिटेड मैच्ड जॉब रिकमेंडेशंस अनलॉक करता है।",
            arabic: "تفتح خطة Pro المقابلة التقنية بالذكاء الاصطناعي وتوصيات وظائف مطابقة غير محدودة.",
            russian: "Pro открывает техническое AI-собеседование и неограниченные рекомендации вакансий.",
        },
        "sec-pro-interview": {
            vietnam: "Phỏng vấn thử với AI đặt câu hỏi dựa trên CV của bạn và chấm điểm từng câu trả lời.",
            hindi: "AI मॉक इंटरव्यू आपके रिज़्यूमे के आधार पर सवाल पूछता है और हर जवाब का स्कोर देता है।",
            arabic: "تطرح المقابلة التجريبية بالذكاء الاصطناعي أسئلة مبنية على سيرتك الذاتية وتقيّم كل إجابة.",
            russian: "Пробное AI-собеседование задаёт вопросы по вашему резюме и оценивает каждый ответ.",
        },
        "sec-pro-jobs": {
            vietnam: "Sau khi đạt từ 70 điểm phỏng vấn, bạn sẽ nhận việc làm phù hợp với kinh nghiệm và kỹ năng.",
            hindi: "इंटरव्यू में 70 से ज़्यादा स्कोर के बाद आपको अनुभव और स्किल्स से मैच नौकरियां मिलती हैं।",
            arabic: "بعد الحصول على أكثر من 70 في المقابلة، تحصل على وظائف مطابقة لخبرتك ومهاراتك.",
            russian: "После 70+ баллов за собеседование вы получаете вакансии под ваш опыт и навыки.",
        },
        "sec-pro-rec1": {
            vietnam: "Bảng điều khiển ghi lại mọi việc bạn đã làm cho đến nay.",
            hindi: "आपका डैशबोर्ड अब तक की आपकी हर गतिविधि का रिकॉर्ड रखता है।",
            arabic: "تتابع لوحة التحكم كل ما أنجزته حتى الآن.",
            russian: "Панель управления отслеживает всё, что вы уже сделали.",
        },
        "sec-pro-rec2": {
            vietnam: "Gói miễn phí vẫn có các bài ngữ pháp và một hoạt động để bạn bắt đầu.",
            hindi: "फ्री प्लान में भी ग्रामर लेसन और शुरुआत के लिए एक एक्टिविटी शामिल है।",
            arabic: "لا تزال الخطة المجانية تتضمن دروس القواعد ونشاطًا واحدًا لتبدأ به.",
            russian: "Бесплатный тариф всё равно включает уроки грамматики и одно занятие для старта.",
        },
        "sec-act-speaking": {
            vietnam: "Các hoạt động Nói và Thuyết trình cho phản hồi ngay về độ rõ ràng, trôi chảy và tự tin.",
            hindi: "स्पीकिंग और प्रेज़ेंटेशन एक्टिविटीज़ स्पष्टता, फ़्लुएंसी और आत्मविश्वास पर तुरंत फ़ीडबैक देती हैं।",
            arabic: "تمنحك أنشطة التحدث والعرض ملاحظات فورية حول الوضوح والطلاقة والثقة.",
            russian: "Занятия по речи и презентациям сразу дают обратную связь о ясности, беглости и уверенности.",
        },
        "sec-act-writing": {
            vietnam: "Viết và Thư tín giúp bạn viết email, thư và báo cáo rõ ràng.",
            hindi: "राइटिंग और कॉरेस्पॉन्डेंस आपको साफ़ ईमेल, लेटर और रिपोर्ट लिखना सिखाता है।",
            arabic: "تدرّبك الكتابة والمراسلات على كتابة رسائل بريد وخطابات وتقارير واضحة.",
            russian: "«Письмо и переписка» учит писать понятные письма, деловые послания и отчёты.",
        },
        "sec-act-listen": {
            vietnam: "Nghe và Học dùng bài tập âm thanh để nâng cao khả năng nghe hiểu.",
            hindi: "लिसन एंड लर्न ऑडियो एक्सरसाइज़ से आपकी सुनने की समझ को तेज़ करता है।",
            arabic: "يستخدم قسم استمع وتعلّم تمارين صوتية لتقوية فهمك السمعي.",
            russian: "«Слушай и учись» развивает понимание на слух с помощью аудиоупражнений.",
        },
        "sec-act-rec1": {
            vietnam: "Workshop gồm Thảo luận nhóm, JAM và Nhập vai với người tham gia AI.",
            hindi: "वर्कशॉप में AI प्रतिभागियों के साथ ग्रुप डिस्कशन, JAM और रोल प्ले शामिल हैं।",
            arabic: "تتضمن ورش العمل النقاش الجماعي وJAM ولعب الأدوار مع مشاركين بالذكاء الاصطناعي.",
            russian: "В воркшопы входят групповая дискуссия, JAM и ролевые игры с AI-участниками.",
        },
        "sec-act-rec2": {
            vietnam: "Chứng chỉ Skill Up chứng minh trình độ của bạn bằng điểm thi thử đã xác minh.",
            hindi: "Skill Up सर्टिफिकेशन वेरिफ़ाइड मॉक टेस्ट स्कोर से आपका लेवल साबित करते हैं।",
            arabic: "تثبت شهادات Skill Up مستواك بدرجة اختبار تجريبي موثقة.",
            russian: "Сертификаты Skill Up подтверждают ваш уровень проверенным баллом пробного теста.",
        },
        "sec-ws-gd": {
            vietnam: "Trong Thảo luận nhóm, bạn tranh luận một chủ đề với người tham gia AI và được chấm điểm theo lập luận.",
            hindi: "ग्रुप डिस्कशन में आप AI प्रतिभागियों के साथ किसी विषय पर बहस करते हैं और आपके पॉइंट्स पर स्कोर मिलता है।",
            arabic: "في النقاش الجماعي تناقش موضوعًا مع مشاركين بالذكاء الاصطناعي وتُقيَّم على أفكارك.",
            russian: "В групповой дискуссии вы обсуждаете тему с AI-участниками и получаете оценку за аргументы.",
        },
        "sec-ws-jam": {
            vietnam: "JAM nghĩa là Just A Minute: bạn nói về một chủ đề trong sáu mươi giây mà không ngập ngừng.",
            hindi: "JAM का मतलब है Just A Minute: आप किसी विषय पर बिना रुके साठ सेकंड बोलते हैं।",
            arabic: "JAM تعني Just A Minute: تتحدث عن موضوع لمدة ستين ثانية دون تردد.",
            russian: "JAM — это Just A Minute: вы говорите на тему шестьдесят секунд без запинок.",
        },
        "sec-ws-rp": {
            vietnam: "Nhập vai đặt bạn vào tình huống công sở thực tế như cuộc họp và cuộc gọi với khách hàng.",
            hindi: "रोल प्ले आपको मीटिंग और क्लाइंट कॉल जैसी असली वर्कप्लेस स्थितियों में रखता है।",
            arabic: "يضعك لعب الأدوار في مواقف عمل حقيقية مثل الاجتماعات ومكالمات العملاء.",
            russian: "Ролевая игра помещает вас в реальные рабочие ситуации — встречи и звонки клиентам.",
        },
        "sec-ws-rec1": {
            vietnam: "Phỏng vấn thử với AI chấm điểm câu trả lời của bạn và có thể mở các việc làm phù hợp.",
            hindi: "AI मॉक इंटरव्यू आपके जवाबों का स्कोर देता है और जॉब मैच अनलॉक कर सकता है।",
            arabic: "تقيّم المقابلة التجريبية بالذكاء الاصطناعي إجاباتك ويمكنها فتح الوظائف المطابقة.",
            russian: "Пробное AI-собеседование оценивает ваши ответы и может открыть подходящие вакансии.",
        },
        "sec-ws-rec2": {
            vietnam: "Danh sách hoạt động có luyện nói, viết, từ vựng và nghe.",
            hindi: "एक्टिविटी लिस्ट में स्पीकिंग, राइटिंग, वोकैबुलरी और लिसनिंग प्रैक्टिस है।",
            arabic: "تحتوي قائمة الأنشطة على تدريبات التحدث والكتابة والمفردات والاستماع.",
            russian: "В списке занятий есть практика говорения, письма, лексики и аудирования.",
        },
        "sec-gr-tenses": {
            vietnam: "Thì cho biết hành động xảy ra khi nào: quá khứ, hiện tại hay tương lai, mỗi thì có dạng đơn, tiếp diễn và hoàn thành.",
            hindi: "टेंस बताते हैं कि काम कब होता है: भूतकाल, वर्तमान या भविष्य, और हर एक के सिंपल, कंटीन्यूअस और परफ़ेक्ट रूप होते हैं।",
            arabic: "تُظهر الأزمنة متى يحدث الفعل: الماضي أو الحاضر أو المستقبل، ولكل منها صيغ بسيطة ومستمرة وتامة.",
            russian: "Времена показывают, когда происходит действие: в прошлом, настоящем или будущем, и у каждого есть простая, длительная и совершенная формы.",
        },
        "sec-gr-struct": {
            vietnam: "Một câu đúng cần có chủ ngữ và động từ, và học phần Cấu trúc câu chỉ cách phát triển từ đó.",
            hindi: "सही वाक्य के लिए कर्ता और क्रिया चाहिए, और सेंटेंस स्ट्रक्चर मॉड्यूल बताता है कि उसे आगे कैसे बढ़ाएं।",
            arabic: "الجملة الصحيحة تحتاج إلى فاعل وفعل، وتوضح وحدة بناء الجملة كيف تبني عليهما.",
            russian: "Правильному предложению нужны подлежащее и сказуемое, а модуль «Структура предложения» показывает, как строить дальше.",
        },
        "sec-gr-rec1": {
            vietnam: "Bài đánh giá tiếng Anh trong Skill Up đo trình độ của bạn và có thể giúp bạn nhận chứng chỉ.",
            hindi: "Skill Up का इंग्लिश असेसमेंट आपका लेवल मापता है और आपको सर्टिफिकेट दिला सकता है।",
            arabic: "يقيس تقييم الإنجليزية في Skill Up مستواك ويمكن أن يمنحك شهادة.",
            russian: "Тест по английскому в Skill Up определяет ваш уровень и может принести сертификат.",
        },
        "sec-gr-rec2": {
            vietnam: "Luyện viết là cách tốt nhất để áp dụng ngữ pháp vào thực tế.",
            hindi: "राइटिंग प्रैक्टिस ग्रामर के नियमों को असल में इस्तेमाल करने का सबसे अच्छा तरीका है।",
            arabic: "التدرب على الكتابة هو أفضل طريقة لتطبيق قواعد اللغة عمليًا.",
            russian: "Практика письма — лучший способ применить правила грамматики на деле.",
        },
        "sec-res-interview": {
            vietnam: "Phỏng vấn thử với AI dùng CV của bạn để đặt câu hỏi phù hợp và chấm điểm câu trả lời.",
            hindi: "AI मॉक इंटरव्यू आपके रिज़्यूमे से सही सवाल पूछता है और आपके जवाबों का स्कोर देता है।",
            arabic: "تستخدم المقابلة التجريبية بالذكاء الاصطناعي سيرتك الذاتية لطرح أسئلة مناسبة وتقييم إجاباتك.",
            russian: "Пробное AI-собеседование задаёт вопросы по вашему резюме и оценивает ответы.",
        },
        "sec-res-jobs": {
            vietnam: "Khi điểm phỏng vấn đạt từ 70, các việc làm khớp với CV sẽ xuất hiện trên bảng điều khiển.",
            hindi: "इंटरव्यू स्कोर 70 या उससे ज़्यादा होने पर आपके रिज़्यूमे से मैच नौकरियां डैशबोर्ड पर दिखती हैं।",
            arabic: "عندما تصل درجة مقابلتك إلى 70 أو أكثر، تظهر الوظائف المطابقة لسيرتك الذاتية في لوحة التحكم.",
            russian: "Когда балл за собеседование достигает 70, вакансии под ваше резюме появляются на панели.",
        },
        "sec-res-rec1": {
            vietnam: "Bảng điều khiển gom điểm CV, tiến độ hoạt động và việc làm về một nơi.",
            hindi: "आपका डैशबोर्ड रिज़्यूमे स्कोर, एक्टिविटी प्रोग्रेस और नौकरियां एक साथ दिखाता है।",
            arabic: "تجمع لوحة التحكم درجة سيرتك الذاتية وتقدم الأنشطة والوظائف معًا.",
            russian: "Панель объединяет оценку резюме, прогресс по занятиям и вакансии.",
        },
        "sec-res-rec2": {
            vietnam: "Tiếng Anh tốt hơn giúp bạn trình bày CV và trả lời phỏng vấn tự tin hơn.",
            hindi: "बेहतर इंग्लिश से आप अपना रिज़्यूमे और इंटरव्यू के जवाब ज़्यादा आत्मविश्वास से पेश करते हैं।",
            arabic: "تساعدك اللغة الإنجليزية الأقوى على عرض سيرتك الذاتية والإجابة في المقابلات بثقة.",
            russian: "Сильный английский помогает уверенно представлять резюме и отвечать на собеседованиях.",
        },
        "sec-su-english": {
            vietnam: "Tiếng Anh và Từ vựng là điểm khởi đầu tốt nhất, có tài liệu hướng dẫn và bài thi thử.",
            hindi: "इंग्लिश और वोकैबुलरी शुरुआत के लिए सबसे अच्छा ट्रैक है, जिसमें गाइड और मॉक टेस्ट हैं।",
            arabic: "الإنجليزية والمفردات هي أفضل نقطة بداية، مع أدلة واختبار تجريبي.",
            russian: "«Английский и лексика» — лучшая отправная точка: здесь есть руководства и пробный тест.",
        },
        "sec-su-aptitude": {
            vietnam: "Năng lực và Tư duy gồm câu hỏi kiểu AMCAT và CoCubes với bài thi thử có giới hạn thời gian.",
            hindi: "एप्टीट्यूड और रीज़निंग में AMCAT और CoCubes जैसे सवाल और टाइम्ड मॉक टेस्ट हैं।",
            arabic: "يغطي قسم القدرات والاستدلال أسئلة بأسلوب AMCAT وCoCubes مع اختبارات تجريبية محددة الوقت.",
            russian: "«Способности и логика» включает задания в стиле AMCAT и CoCubes с пробными тестами на время.",
        },
        "sec-su-tech": {
            vietnam: "Tech Center bao gồm Python, cấu trúc dữ liệu, cơ sở dữ liệu và nhiều hơn nữa.",
            hindi: "टेक सेंटर में Python, डेटा स्ट्रक्चर्स, डेटाबेस और बहुत कुछ है।",
            arabic: "يغطي Tech Center لغة Python وهياكل البيانات وقواعد البيانات والمزيد.",
            russian: "Tech Center охватывает Python, структуры данных, базы данных и многое другое.",
        },
        "sec-su-rec1": {
            vietnam: "Trang chứng chỉ hiển thị trạng thái từng học phần và cho phép bạn tải chứng chỉ.",
            hindi: "सर्टिफिकेशन पेज हर मॉड्यूल का स्टेटस दिखाता है और आपको सर्टिफिकेट डाउनलोड करने देता है।",
            arabic: "تعرض صفحة الشهادات حالة كل وحدة وتتيح لك تنزيل الشهادات.",
            russian: "Страница сертификатов показывает статус каждого модуля и позволяет скачать сертификаты.",
        },
        "sec-su-rec2": {
            vietnam: "Phỏng vấn thử với AI là bước tiếp theo tuyệt vời khi kỹ năng của bạn đã sẵn sàng.",
            hindi: "स्किल्स तैयार होने के बाद AI मॉक इंटरव्यू एक बढ़िया अगला कदम है।",
            arabic: "المقابلة التجريبية بالذكاء الاصطناعي خطوة تالية رائعة بعد صقل مهاراتك.",
            russian: "Пробное AI-собеседование — отличный следующий шаг, когда навыки отточены.",
        },
        "sec-sue-cert": {
            vietnam: "Đạt từ 70 phần trăm trong bài thi thử tiếng Anh để nhận chứng chỉ tiếng Anh.",
            hindi: "इंग्लिश सर्टिफिकेट पाने के लिए इंग्लिश मॉक टेस्ट में 70 प्रतिशत या उससे ज़्यादा स्कोर करें।",
            arabic: "احصل على 70 بالمئة أو أكثر في اختبار الإنجليزية التجريبي لتنال شهادة الإنجليزية.",
            russian: "Наберите 70 процентов и выше в пробном тесте по английскому, чтобы получить сертификат.",
        },
        "sec-sue-vocab": {
            vietnam: "Các hoạt động Từ vựng và Thành ngữ giúp bạn dùng từ ngữ kinh doanh một cách tự nhiên.",
            hindi: "वोकैबुलरी और इडियम्स एक्टिविटीज़ आपको बिज़नेस शब्दों का स्वाभाविक इस्तेमाल सिखाती हैं।",
            arabic: "تساعدك أنشطة المفردات والتعابير على استخدام كلمات الأعمال بشكل طبيعي.",
            russian: "Занятия по лексике и идиомам помогают естественно использовать деловые слова.",
        },
        "sec-sue-rec1": {
            vietnam: "Năng lực là vòng phổ biến trong các bài kiểm tra tuyển dụng, nên đây là bước tiếp theo hợp lý.",
            hindi: "एप्टीट्यूड हायरिंग टेस्ट का आम राउंड है, इसलिए यह एक अच्छा अगला कदम है।",
            arabic: "القدرات جولة شائعة في اختبارات التوظيف، لذا فهي خطوة تالية جيدة.",
            russian: "Способности — частый раунд в тестах при найме, так что это хороший следующий шаг.",
        },
        "sec-sue-rec2": {
            vietnam: "Thư viện Ngữ pháp bao gồm danh từ, động từ, thì và cấu trúc câu.",
            hindi: "ग्रामर लाइब्रेरी में संज्ञा, क्रिया, टेंस और वाक्य संरचना शामिल हैं।",
            arabic: "تغطي مكتبة القواعد الأسماء والأفعال والأزمنة وبناء الجملة.",
            russian: "Библиотека грамматики охватывает существительные, глаголы, времена и структуру предложения.",
        },
        "sec-sua-cert": {
            vietnam: "Đạt từ 70 phần trăm trong bài thi thử Năng lực để nhận chứng chỉ Năng lực.",
            hindi: "एप्टीट्यूड सर्टिफिकेट पाने के लिए एप्टीट्यूड मॉक टेस्ट में 70 प्रतिशत या उससे ज़्यादा स्कोर करें।",
            arabic: "احصل على 70 بالمئة أو أكثر في اختبار القدرات التجريبي لتنال شهادة القدرات.",
            russian: "Наберите 70 процентов и выше в пробном тесте на способности, чтобы получить сертификат.",
        },
        "sec-sua-all": {
            vietnam: "Skill Up còn có lộ trình Tiếng Anh và Công nghệ bên cạnh Năng lực.",
            hindi: "Skill Up में एप्टीट्यूड के साथ इंग्लिश और टेक ट्रैक भी हैं।",
            arabic: "يضم Skill Up أيضًا مساري الإنجليزية والتقنية إلى جانب القدرات.",
            russian: "Помимо способностей, в Skill Up есть курсы по английскому и технологиям.",
        },
        "sec-sua-rec1": {
            vietnam: "Tech Center bổ sung các chủ đề lập trình và khoa học máy tính cho quá trình chuẩn bị của bạn.",
            hindi: "टेक सेंटर आपकी तैयारी में प्रोग्रामिंग और कंप्यूटर साइंस के विषय जोड़ता है।",
            arabic: "يضيف Tech Center موضوعات البرمجة وعلوم الحاسوب إلى استعدادك.",
            russian: "Tech Center добавляет к подготовке программирование и информатику.",
        },
        "sec-sua-rec2": {
            vietnam: "Tiếng Anh và Từ vựng củng cố khía cạnh giao tiếp trong hồ sơ của bạn.",
            hindi: "इंग्लिश और वोकैबुलरी आपकी प्रोफ़ाइल के कम्युनिकेशन पक्ष को मज़बूत करते हैं।",
            arabic: "تقوّي الإنجليزية والمفردات جانب التواصل في ملفك.",
            russian: "«Английский и лексика» усиливает коммуникативную сторону вашего профиля.",
        },
        "sec-sut-cert": {
            vietnam: "Đạt từ 70 phần trăm trong bài thi thử Công nghệ để nhận chứng chỉ Công nghệ.",
            hindi: "टेक सर्टिफिकेट पाने के लिए टेक मॉक टेस्ट में 70 प्रतिशत या उससे ज़्यादा स्कोर करें।",
            arabic: "احصل على 70 بالمئة أو أكثر في اختبار التقنية التجريبي لتنال شهادة التقنية.",
            russian: "Наберите 70 процентов и выше в пробном тесте по технологиям, чтобы получить сертификат.",
        },
        "sec-sut-all": {
            vietnam: "Mục Xem tất cả hiển thị mọi tài liệu hướng dẫn về Tiếng Anh, Năng lực và Công nghệ.",
            hindi: "ब्राउज़ ऑल में इंग्लिश, एप्टीट्यूड और टेक की हर गाइड दिखती है।",
            arabic: "يعرض قسم تصفح الكل جميع الأدلة في الإنجليزية والقدرات والتقنية.",
            russian: "Раздел «Все материалы» показывает каждое руководство по английскому, способностям и технологиям.",
        },
        "sec-sut-rec1": {
            vietnam: "Phỏng vấn kỹ thuật với AI kiểm tra những gì bạn đã học bằng câu hỏi phỏng vấn thực tế.",
            hindi: "AI टेक्निकल इंटरव्यू असली इंटरव्यू सवालों से आपकी सीखी हुई चीज़ों को परखता है।",
            arabic: "تختبر المقابلة التقنية بالذكاء الاصطناعي ما تعلمته بأسئلة مقابلات حقيقية.",
            russian: "Техническое AI-собеседование проверяет изученное на реальных вопросах с собеседований.",
        },
        "sec-sut-rec2": {
            vietnam: "Luyện năng lực bổ trợ cho phần chuẩn bị kỹ thuật trong các kỳ thi tuyển dụng.",
            hindi: "एप्टीट्यूड प्रैक्टिस प्लेसमेंट टेस्ट के लिए आपकी टेक्निकल तैयारी को पूरा करती है।",
            arabic: "يكمّل التدرب على القدرات استعدادك التقني لاختبارات التوظيف.",
            russian: "Практика способностей дополняет техническую подготовку к отборочным тестам.",
        },
        "sec-suc-english": {
            vietnam: "Chứng chỉ tiếng Anh yêu cầu đạt 70 phần trăm trong bài thi thử tiếng Anh.",
            hindi: "इंग्लिश सर्टिफिकेट के लिए इंग्लिश मॉक टेस्ट में 70 प्रतिशत स्कोर चाहिए।",
            arabic: "تتطلب شهادة الإنجليزية الحصول على 70 بالمئة في اختبار الإنجليزية التجريبي.",
            russian: "Для сертификата по английскому нужно 70 процентов в пробном тесте по английскому.",
        },
        "sec-suc-aptitude": {
            vietnam: "Chứng chỉ Năng lực yêu cầu đạt 70 phần trăm trong bài thi thử Năng lực.",
            hindi: "एप्टीट्यूड सर्टिफिकेट के लिए एप्टीट्यूड मॉक टेस्ट में 70 प्रतिशत स्कोर चाहिए।",
            arabic: "تتطلب شهادة القدرات الحصول على 70 بالمئة في اختبار القدرات التجريبي.",
            russian: "Для сертификата по способностям нужно 70 процентов в пробном тесте на способности.",
        },
        "sec-suc-tech": {
            vietnam: "Chứng chỉ Công nghệ yêu cầu đạt 70 phần trăm trong bài thi thử Công nghệ.",
            hindi: "टेक सर्टिफिकेट के लिए टेक मॉक टेस्ट में 70 प्रतिशत स्कोर चाहिए।",
            arabic: "تتطلب شهادة التقنية الحصول على 70 بالمئة في اختبار التقنية التجريبي.",
            russian: "Для сертификата по технологиям нужно 70 процентов в пробном тесте по технологиям.",
        },
        "sec-suc-rec1": {
            vietnam: "Việc làm phù hợp sẽ có trên bảng điều khiển khi điểm phỏng vấn của bạn đạt 70.",
            hindi: "इंटरव्यू स्कोर 70 होने पर आपकी मैच की गई नौकरियां डैशबोर्ड पर आ जाती हैं।",
            arabic: "تظهر وظائفك المطابقة في لوحة التحكم عندما تصل درجة مقابلتك إلى 70.",
            russian: "Подходящие вакансии появятся на панели, когда балл за собеседование достигнет 70.",
        },
        "sec-suc-rec2": {
            vietnam: "Bảng điều khiển hiển thị toàn bộ tiến độ của bạn qua các hoạt động và điểm số.",
            hindi: "आपका डैशबोर्ड एक्टिविटीज़ और स्कोर में आपकी पूरी प्रोग्रेस दिखाता है।",
            arabic: "تعرض لوحة التحكم تقدمك الكامل في الأنشطة والدرجات.",
            russian: "Панель показывает ваш общий прогресс по занятиям и баллам.",
        },
        "sec-emp-post": {
            vietnam: "Đăng tin cần chức danh, kỹ năng, kinh nghiệm và mức lương, và tin sẽ hiển thị ngay với ứng viên.",
            hindi: "जॉब पोस्ट करने के लिए टाइटल, स्किल्स, अनुभव और सैलरी चाहिए, और यह तुरंत कैंडिडेट्स को दिखने लगती है।",
            arabic: "يتطلب نشر الوظيفة مسمى ومهارات وخبرة وراتبًا، وتظهر للمرشحين فورًا.",
            russian: "Для публикации вакансии нужны должность, навыки, опыт и зарплата, и она сразу становится видна кандидатам.",
        },
        "sec-emp-apps": {
            vietnam: "Mỗi đơn ứng tuyển hiển thị CV và điểm phỏng vấn của ứng viên để bạn chọn lọc nhanh.",
            hindi: "एप्लीकेशंस में हर कैंडिडेट का रिज़्यूमे और इंटरव्यू स्कोर दिखता है ताकि आप जल्दी शॉर्टलिस्ट कर सकें।",
            arabic: "تعرض الطلبات السيرة الذاتية ودرجة المقابلة لكل مرشح لتختار القائمة المختصرة بسرعة.",
            russian: "В откликах видны резюме и балл за собеседование каждого кандидата, чтобы быстро отобрать лучших.",
        },
        "sec-emp-cand": {
            vietnam: "Bạn có thể tìm ứng viên theo kỹ năng và kinh nghiệm, kể cả khi họ chưa ứng tuyển.",
            hindi: "आप स्किल्स और अनुभव के आधार पर कैंडिडेट्स खोज सकते हैं, भले ही उन्होंने अभी आवेदन न किया हो।",
            arabic: "يمكنك البحث عن المرشحين حسب المهارات والخبرة حتى لو لم يتقدموا بعد.",
            russian: "Вы можете искать кандидатов по навыкам и опыту, даже если они ещё не откликнулись.",
        },
        "sec-emp-rec1": {
            vietnam: "Xem lại tin tuyển dụng giúp thông tin luôn chính xác và hấp dẫn.",
            hindi: "अपनी ओपनिंग्स रिव्यू करने से आपकी लिस्टिंग सही और आकर्षक बनी रहती है।",
            arabic: "مراجعة وظائفك الشاغرة تبقي إعلاناتك دقيقة وجذابة.",
            russian: "Проверка вакансий помогает держать объявления точными и привлекательными.",
        },
        "sec-emp-rec2": {
            vietnam: "Ứng viên có xu hướng ứng tuyển vào công ty có hồ sơ đầy đủ hơn.",
            hindi: "पूरी प्रोफ़ाइल वाली कंपनियों में कैंडिडेट्स ज़्यादा आवेदन करते हैं।",
            arabic: "يميل المرشحون إلى التقدم للشركات ذات الملفات المكتملة.",
            russian: "Кандидаты охотнее откликаются компаниям с заполненным профилем.",
        },
        "sec-empj-post": {
            vietnam: "Mỗi tin tuyển dụng mới sẽ đến với những người tìm việc phù hợp trên CareerBuddy.",
            hindi: "हर नई ओपनिंग CareerBuddy पर मैच करने वाले जॉब सीकर्स तक पहुंचती है।",
            arabic: "تصل كل وظيفة جديدة إلى الباحثين عن عمل المناسبين على CareerBuddy.",
            russian: "Каждая новая вакансия доходит до подходящих соискателей на CareerBuddy.",
        },
        "sec-empj-apps": {
            vietnam: "Đơn ứng tuyển được nhóm theo công việc để bạn so sánh các ứng viên với nhau.",
            hindi: "एप्लीकेशंस जॉब के हिसाब से ग्रुप की जाती हैं ताकि आप कैंडिडेट्स की तुलना कर सकें।",
            arabic: "يتم تجميع الطلبات حسب الوظيفة لتقارن المرشحين جنبًا إلى جنب.",
            russian: "Отклики сгруппированы по вакансиям, чтобы сравнивать кандидатов рядом.",
        },
        "sec-empj-rec1": {
            vietnam: "Tìm kiếm ứng viên giúp bạn tiếp cận mọi người trước khi họ ứng tuyển.",
            hindi: "कैंडिडेट सर्च से आप लोगों तक उनके आवेदन करने से पहले पहुंच सकते हैं।",
            arabic: "يتيح لك البحث عن المرشحين الوصول إلى الأشخاص قبل أن يتقدموا.",
            russian: "Поиск кандидатов позволяет связаться с людьми ещё до их отклика.",
        },
        "sec-empj-rec2": {
            vietnam: "Hồ sơ công ty được cập nhật giúp bạn thu hút ứng viên mạnh hơn.",
            hindi: "अपडेटेड कंपनी प्रोफ़ाइल से आप बेहतर आवेदकों को आकर्षित करते हैं।",
            arabic: "يساعدك ملف الشركة المحدّث على جذب متقدمين أقوى.",
            russian: "Обновлённый профиль компании привлекает более сильных кандидатов.",
        },
        "sec-empa-cand": {
            vietnam: "Tìm kiếm ứng viên giúp bạn tìm thêm người đáp ứng yêu cầu.",
            hindi: "कैंडिडेट सर्च आपकी ज़रूरतों से मेल खाने वाले और लोग ढूंढता है।",
            arabic: "يعثر البحث عن المرشحين على المزيد من الأشخاص المطابقين لمتطلباتك.",
            russian: "Поиск кандидатов находит больше людей, подходящих под ваши требования.",
        },
        "sec-empa-jobs": {
            vietnam: "Trang tin tuyển dụng cho biết vị trí nào vẫn đang nhận đơn.",
            hindi: "जॉब ओपनिंग्स पेज बताता है कि कौन सी भूमिकाएं अभी भी आवेदन ले रही हैं।",
            arabic: "توضح صفحة الوظائف الشاغرة أي الوظائف لا تزال تستقبل الطلبات.",
            russian: "Страница вакансий показывает, какие позиции ещё принимают отклики.",
        },
        "sec-empa-rec1": {
            vietnam: "Một tin tuyển dụng mới mang đến nguồn ứng viên mới.",
            hindi: "नई पोस्टिंग से आवेदकों का नया पूल मिलता है।",
            arabic: "يجلب الإعلان الجديد مجموعة جديدة من المتقدمين.",
            russian: "Новая вакансия приносит новый поток кандидатов.",
        },
        "sec-empa-rec2": {
            vietnam: "Hồ sơ đầy đủ tạo niềm tin với những ứng viên bạn liên hệ.",
            hindi: "पूरी प्रोफ़ाइल उन कैंडिडेट्स का भरोसा बढ़ाती है जिनसे आप संपर्क करते हैं।",
            arabic: "يبني الملف المكتمل الثقة لدى المرشحين الذين تتواصل معهم.",
            russian: "Заполненный профиль вызывает доверие у кандидатов, с которыми вы связываетесь.",
        },
        "sec-empc-apps": {
            vietnam: "Trang đơn ứng tuyển liệt kê mọi người đã ứng tuyển vào công việc của bạn.",
            hindi: "एप्लीकेशंस पेज पर आपकी नौकरियों के लिए आवेदन कर चुके सभी लोग दिखते हैं।",
            arabic: "تسرد صفحة الطلبات كل من تقدّم بالفعل لوظائفك.",
            russian: "На странице откликов перечислены все, кто уже откликнулся на ваши вакансии.",
        },
        "sec-empc-jobs": {
            vietnam: "Tin tuyển dụng hiển thị mọi vị trí bạn đang tuyển.",
            hindi: "जॉब ओपनिंग्स में वे सभी भूमिकाएं दिखती हैं जिनके लिए आप अभी हायर कर रहे हैं।",
            arabic: "تعرض الوظائف الشاغرة كل الوظائف التي توظف لها حاليًا.",
            russian: "В вакансиях показаны все позиции, на которые вы сейчас нанимаете.",
        },
        "sec-empc-rec1": {
            vietnam: "Đăng một công việc mới giúp bạn tiếp cận nhiều ứng viên bạn đang tìm hơn.",
            hindi: "नई जॉब पोस्ट करने से आप ज़्यादा उन कैंडिडेट्स तक पहुंचते हैं जिन्हें आप ढूंढ रहे हैं।",
            arabic: "نشر وظيفة جديدة يساعدك على الوصول إلى المزيد من المرشحين الذين تبحث عنهم.",
            russian: "Новая вакансия помогает охватить больше нужных вам кандидатов.",
        },
        "sec-empc-rec2": {
            vietnam: "Ứng viên xem hồ sơ công ty trước khi phản hồi bạn.",
            hindi: "कैंडिडेट्स आपको जवाब देने से पहले आपकी कंपनी प्रोफ़ाइल देखते हैं।",
            arabic: "يطّلع المرشحون على ملف شركتك قبل الرد عليك.",
            russian: "Кандидаты смотрят профиль компании, прежде чем ответить вам.",
        },
    };

    /* Which SECTION_CONTEXT entry applies to the page (and in-page hash) we are on. */
    function getAssistantSection() {
        const path = String(window.location.pathname || "/").toLowerCase();
        const hash = String(window.location.hash || "").toLowerCase();
        if (path.indexOf("/employer") === 0) {
            if (path.indexOf("/applications") !== -1) return "employer_applications";
            if (path.indexOf("/candidates") !== -1) return "employer_candidates";
            if (path.indexOf("/job-openings") !== -1 || path.indexOf("/jobs/") !== -1) return "employer_jobs";
            return "employer";
        }
        if (path.indexOf("/activities/") === 0) {
            const query = String(window.location.search || "").toLowerCase();
            return query.indexOf("workshop") !== -1 ? "workshop" : "activities";
        }
        if (path.indexOf("/skill-up/") === 0) {
            // Skill Up is one page navigated by hash: #depth-english,
            // #section-certifications, #load=TechCenter/... and so on.
            if (hash.indexOf("certif") !== -1) return "skillup_certs";
            if (hash.indexOf("english") !== -1 || hash.indexOf("vocab") !== -1) return "skillup_english";
            if (hash.indexOf("aptitude") !== -1) return "skillup_aptitude";
            if (hash.indexOf("tech") !== -1) return "skillup_tech";
            return "skillup";
        }
        if (path.indexOf("/dashboard/") === 0) return hash === "#recommended-jobs" ? "jobs" : "dashboard";
        if (path.indexOf("/resume-builder/") === 0) return "resume";
        if (path.indexOf("/subject/") === 0) return "grammar";
        if (path.indexOf("/gd/") === 0 || path.indexOf("/jam/") === 0 || path.indexOf("/roleplay/") === 0) return "workshop";
        if (path.indexOf("/users/profile/") === 0) return "profile";
        if (path.indexOf("/pro/") === 0) return "pro";
        if (path === "/" || path === "/home/") return "home";
        return "";
    }


    const ROLE_CONTEXT = {

        // ============================================================
        // GUEST — NO LOGIN YET
        // ============================================================
        guest: {
            name: "Guest",
            isEmployer: false,

            description:
                "You are Buddy for a guest who is not logged in. First determine whether the user is a Job Seeker/Student or an Employer/Recruiter. Do not assume a role. Ask the user to choose Job Seeker or Employer before providing role-specific navigation or assistance.",

            greeting: {
                english:
                    "Hello there! Are you a Job Seeker or an Employer?",

                vietnam:
                    "Xin chào! Bạn là Người tìm việc hay Nhà tuyển dụng?",

                hindi:
                    "नमस्ते! आप Job Seeker हैं या Employer?",

                arabic:
                    "مرحباً! هل أنت باحث عن عمل أم صاحب عمل؟",

                russian:
                    "Здравствуйте! Вы соискатель или работодатель?"
            },

            bubble: {
                english: "Ask Buddy",
                vietnam: "Hỏi Buddy",
                hindi: "बडी से पूछें",
                arabic: "اسأل بادي",
                russian: "Спросить Бадди"
            }
        },

        // ============================================================
        // STUDENT / JOB SEEKER
        // ============================================================
        student: {
            name: "Student / Job Seeker",
            isEmployer: false,

            description:
                "You are Buddy for a student/job seeker. Help with learning, English practice, activities, grammar, speaking, writing, vocabulary, resume building, career preparation, student dashboard and job-seeker features. Do not navigate to or act as an employer assistant.",

            greeting: {
                english:
                    "Hello there! How can I help you with learning and your career?",

                vietnam:
                    "Xin chào! Tôi có thể giúp gì cho việc học và sự nghiệp của bạn?",

                hindi:
                    "नमस्ते! मैं आपकी पढ़ाई और करियर में कैसे मदद कर सकता हूँ?",

                arabic:
                    "مرحباً! كيف يمكنني مساعدتك في التعلم ومسيرتك المهنية؟",

                russian:
                    "Здравствуйте! Чем я могу помочь вам в обучении и карьере?"
            },

            bubble: {
                english: "Learning & Career",
                vietnam: "Học tập & Sự nghiệp",
                hindi: "लर्निंग और करियर",
                arabic: "التعلم والمسيرة المهنية",
                russian: "Обучение и карьера"
            }
        },

        // ============================================================
        // EMPLOYER
        // ============================================================
        employer: {
            name: "Employer",
            isEmployer: true,

            description:
                "You are Buddy for an employer/recruiter. Help with employer dashboard, company profile, finding candidates, posting jobs, applications and job openings. Do not navigate to or act as a student/job-seeker assistant.",

            greeting: {
                english:
                    "Hello there! How can I help you with hiring and managing candidates?",

                vietnam:
                    "Xin chào! Tôi có thể giúp gì về tuyển dụng và quản lý ứng viên?",

                hindi:
                    "नमस्ते! मैं भर्ती और उम्मीदवारों को प्रबंधित करने में कैसे मदद कर सकता हूँ?",

                arabic:
                    "مرحباً! كيف يمكنني مساعدتك في التوظيف وإدارة المرشحين؟",

                russian:
                    "Здравствуйте! Чем я могу помочь в найме и управлении кандидатами?"
            },

            bubble: {
                english: "Hiring & Candidates",
                vietnam: "Tuyển dụng & Ứng viên",
                hindi: "भर्ती और उम्मीदवार",
                arabic: "التوظيف والمرشحون",
                russian: "Найм и кандидаты"
            }
        }
    };

    const assistant = {
        state: AssistantState.CLOSED,
        role: "student",
        isEmployer: false,
        conversationId: "",
        conversationHistory: [],
        root: null,
        launcher: null,
        launcherModel: null,
        launcherModelIdleSrc: "",
        launcherModelSpeakingSrc: "",
        launcherModelVRiyant: "",
        launcherModelSwitchToken: 0,
        bubble: null,
        statusText: null,
        transcriptText: null,
        responseSlot: null,
        micButton: null,
        micLabel: null,
        micIndicator: null,
        typeToggle: null,
        textForm: null,
        textInput: null,
        actionChips: null,
        audioBars: null,
        closeButton: null,
        recognition: null,
        recognitionRunning: false,
        recognitionStopReason: "manual",
        recognitionFinalText: "",
        recognitionInterimText: "",
        silenceTimer: null,
        transcriptTimer: null,
        autoListenTimer: null,
        mediaRecorder: null,
        mediaStream: null,
        mediaAnalyser: null,
        mediaAudioContext: null,
        mediaChunks: [],
        mediaStopReason: "manual",
        mediaVADActive: false,
        mediaMimeType: "",
        voiceCaptureMode: "recognition",
        pendingBackendTranscript: false,
        voiceTurnHandled: false,
        voiceTurnConsumed: false,
        ttsEndedAt: 0,
        barAnimationFrame: null,
        ttsAudio: new Audio(),
        pendingAfterSpeak: null,
        speechUtterance: null,
        lastResponseText: "",
        ttsSpeaking: false,
        ttsGeneration: 0,
        microphoneBlockedByTTS: false,
        streamPersistTimer: null,

        // Header speaker control (pause / resume). ttsPath tells pause/resume
        // which engine is live ("audio" = server TTS element, "browser" = Web
        // Speech API). speakerMode mirrors the UI: idle | speaking | paused.
        speakerButton: null,
        ttsPath: "browser",
        speakerMode: "idle",
        pausedNavTimer: null,
        speechText: "",
        speechCharIndex: 0,
        prosodyHandle: null,
        initialized: false,

        // A navigation Buddy has already announced out loud. Speech can delay
        // it; nothing may cancel it except the user closing the chat.
        pendingNavigation: null,
        navigationDeadline: null,
        navigationDone: false,

        // Prevent old voice callbacks from restarting Listening
        // while the language is being changed.
        languageChangeInProgress: false,
        languageChangeGeneration: 0,

        // Wake-word ("Hey Buddy") cooldown: timestamp (ms) until which a
        // wake-word-ONLY activation should be ignored, so a single
        // continuous-recognition turn cannot produce duplicate "Yes?" replies.
        wakeWordAckCooldownUntil: 0,

        // Reply text held back until its voice starts (revealPendingCard).
        pendingRevealCard: null,
        pendingRevealTimer: null,
    };

    // Greeting text is set dynamically after DOM is ready (uses logged-in username)
    let GREETING_TEXT = "Hi! How can I help you today?";

    /**
     * Turn a stored account name into something Buddy can say out loud.
     *
     * The raw value is whatever the account holds — "jagadeesh m",
     * "KONDAPARTHI SAI PRASAD", or an email address used as a username. Read
     * back verbatim that becomes "Hello jagadeesh m!", which is both wrong
     * looking and wrong sounding once TTS reads the trailing initial as a
     * word. Buddy greets people the way a person would: by first name,
     * capitalised.
     */
    function getDisplayName() {
        let raw = String(assistant.root?.dataset.riyaUsername || "").trim();

        if (!raw || raw.toLowerCase() === "there") {
            return "";
        }

        // A username that is really an email: keep the local part only.
        if (raw.includes("@")) {
            raw = raw.split("@")[0];
        }

        // Separators that appear in usernames but never in spoken names.
        raw = raw.replace(/[._\-]+/g, " ").replace(/\d+/g, " ").trim();

        const parts = raw.split(/\s+/).filter(Boolean);
        if (!parts.length) {
            return "";
        }

        // Drop a trailing single-letter surname initial ("jagadeesh m").
        const meaningful = parts.filter(
            (part, index) => index === 0 || part.length > 1
        );

        const first = meaningful[0] || parts[0];

        return first.charAt(0).toUpperCase() + first.slice(1).toLowerCase();
    }

    function isGuestUser() {
        const username =
            String(
                assistant.root?.dataset.riyaUsername || ""
            ).trim();

        return (
            !username ||
            username.toLowerCase() === "there"
        );
    }

    function getAssistantRole() {
        // Logged-in employer
        if (!isGuestUser() && assistant.isEmployer) {
            return "employer";
        }

        // Logged-in student/job seeker
        if (!isGuestUser()) {
            return "student";
        }

        // Guest role is intentionally MEMORY-ONLY.
        // Never persist guest role in localStorage/sessionStorage.
        if (
            assistant.role === "employer" ||
            assistant.role === "student"
        ) {
            return assistant.role;
        }

        return "guest";
    }

    function getRoleContext() {
        return (
            ROLE_CONTEXT[getAssistantRole()] ||
            ROLE_CONTEXT.guest
        );
    }

    function createConversationId() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        return `buddy-${getAssistantRole()}-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
    }

    function getAssistantStorageKey() {
        const username = String(assistant.root?.dataset.riyaUsername || "guest")
            .toLowerCase()
            .replace(/[^\w-]+/g, "_")
            .slice(0, 60) || "guest";
        return `career_buddy_riya_${getAssistantRole()}_state_v${RIYA_SESSION_STORAGE_VERSION}_${username}`;
    }

    function getLegacyAssistantStorageKey() {
        const username = String(assistant.root?.dataset.riyaUsername || "guest")
            .toLowerCase()
            .replace(/[^\w-]+/g, "_")
            .slice(0, 60) || "guest";
        return `career_buddy_riya_state_v1_${username}`;
    }

    function readAssistantSession() {
        // Guests now use persisted chatbot sessions to keep history across public navigation.
        // if (isGuestUser()) {
        //     return null;
        // }

        try {
            const raw = sessionStorage.getItem(getAssistantStorageKey());

            if (raw) {
                const parsed = JSON.parse(raw);
                if (!parsed || parsed.version !== RIYA_SESSION_STORAGE_VERSION) {
                    return null;
                }
                if (Date.now() - Number(parsed.updatedAt || 0) > RIYA_SESSION_MAX_AGE_MS) {
                    sessionStorage.removeItem(getAssistantStorageKey());
                    return null;
                }
                return parsed;
            }

            // Migrate old shared history only into Student.
            // Employer must never inherit Student conversation history.
            if (!isGuestUser() && !assistant.isEmployer) {
                const legacyRaw = sessionStorage.getItem(getLegacyAssistantStorageKey());
                if (legacyRaw) {
                    const legacy = JSON.parse(legacyRaw);
                    if (
                        legacy &&
                        Date.now() - Number(legacy.updatedAt || 0) <= RIYA_SESSION_MAX_AGE_MS
                    ) {
                        const migrated = {
                            ...legacy,
                            version: RIYA_SESSION_STORAGE_VERSION,
                            role: "student",
                            conversationId: legacy.conversationId || createConversationId(),
                            conversationHistory: Array.isArray(legacy.conversationHistory)
                                ? legacy.conversationHistory
                                : [],
                        };
                        sessionStorage.setItem(
                            getAssistantStorageKey(),
                            JSON.stringify(migrated)
                        );
                        return migrated;
                    }
                }
            }

            return null;
        } catch (_error) {
            return null;
        }
    }

    function ensureConversationId() {
        if (assistant.conversationId) {
            return assistant.conversationId;
        }
        const previous = readAssistantSession();
        assistant.conversationId =
            previous?.conversationId || createConversationId();
        return assistant.conversationId;
    }

    function addConversationMessage(role, content) {
        const clean = String(content || "").trim();
        if (!clean) {
            return;
        }

        const normalizedRole = role === "user" ? "user" : "assistant";
        const last =
            assistant.conversationHistory[
            assistant.conversationHistory.length - 1
            ];

        if (
            last &&
            last.role === normalizedRole &&
            last.content === clean
        ) {
            return;
        }

        assistant.conversationHistory.push({
            role: normalizedRole,
            content: clean,
            timestamp: Date.now(),
        });

        persistAssistantSession();
    }

    function persistAssistantSession(overrides = {}) {
        if (!assistant.root) {
            return;
        }

        // Guest sessions now persist across public pages so chat history isn't lost.
        // if (isGuestUser()) {
        //     return;
        // }

        try {
            const previous = readAssistantSession() || {};

            const state = {
                version: RIYA_SESSION_STORAGE_VERSION,
                role: getAssistantRole(),
                conversationId:
                    assistant.conversationId ||
                    previous.conversationId ||
                    createConversationId(),
                conversationHistory:
                    Array.isArray(assistant.conversationHistory)
                        ? assistant.conversationHistory
                        : (previous.conversationHistory || []),
                isOpen: assistant.state !== AssistantState.CLOSED,
                lastResponseText:
                    assistant.lastResponseText ||
                    previous.lastResponseText ||
                    "",
                chatHistory:
                    assistant.responseSlot
                        ? assistant.responseSlot.innerHTML
                        : (previous.chatHistory || ""),
                updatedAt: Date.now(),
                ...overrides,
            };

            sessionStorage.setItem(
                getAssistantStorageKey(),
                JSON.stringify(state)
            );
        } catch (_error) {
            // Storage can be unavailable in private browsing; the assistant still works normally.
        }
    }

    function canUseBrowserSpeech() {
        return "speechSynthesis" in window && typeof window.SpeechSynthesisUtterance === "function";
    }

    function normalizeText(value) {
        return String(value || "")
            .toLowerCase()
            .replace(/proffessional/g, "professional")
            .replace(/profesional/g, "professional")
            .replace(/grammer/g, "grammar")
            .replace(/\b(sikar|sekar|sekhar|seekar)\b/g, "seeker")
            .replace(/\b(paar\s*singh|parsingh|parsing\s*parsing)\b/g, "parsing")
            .replace(/[^\p{L}\p{N}\s/]/gu, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    // Kept in sync with _is_informational_question() in riya_bot/riya_assistant.py.
    // If these two drift apart, the frontend's local shortcut can navigate
    // on a message the backend would have explained instead - which is
    // exactly the "frontend thinks X, backend thinks Y" conflict the
    // navigation architecture must avoid.
    const INFORMATIONAL_QUESTION_REGEX =
        /\b(what is|what are|what will|what do|what does|what can|explain|meaning|define|definition|tips|advice|why|how to|how can|use of|tell me about|learn about|sub activit|sub-activit)\b/;

    function isInformationalQuestion(normalizedText) {
        return INFORMATIONAL_QUESTION_REGEX.test(normalizedText);
    }

    function hasNavigationVerb(normalizedText) {
        if (isInformationalQuestion(normalizedText) || /\bhelp me\b/.test(normalizedText)) {
            return false;
        }
        return /\b(go|open|navigate|take|show|start|launch|visit|move|redirect|list|switch|karo|kholo|khulna|kholna|dikhao|jao|chalo|batao|register|sign up)\b/.test(normalizedText)
            || /\btake me\b/.test(normalizedText)
            || /\bgo to\b/.test(normalizedText)
            || /\bswitch to\b/.test(normalizedText)
            || /\b(employer|employeer|recruiter|job seeker|jobseeker|student|candidate|job)\b/.test(normalizedText);
    }

    // ============================================================
    // WAKE WORD ("Hey Buddy")
    // ============================================================
    // This is NOT a second assistant. It is a thin detector that sits in
    // front of the SAME processTranscript() pipeline used by both voice
    // and text input (see WAKE-WORD STATE MACHINE below).
    //
    //   MIC/TEXT -> transcript -> [WAKE-WORD DETECT + STRIP] -> processTranscript()
    //
    // States (conceptually - no separate state object is needed because
    // assistant.state already tracks CLOSED/LISTENING/etc; the wake word
    // only decides what to do with a transcript BEFORE it reaches the
    // normal intent pipeline):
    //   LISTENING_FOR_WAKE_WORD -> WAKE_WORD_DETECTED -> READY_FOR_COMMAND
    //   -> PROCESSING_COMMAND (normal pipeline) -> RESPONDING
    //   -> back to LISTENING_FOR_WAKE_WORD
    //
    // Matches "Buddy" optionally preceded by "hey/hi/ok/okay", anchored to
    // the START of the utterance only (so "I spoke with Buddy yesterday"
    // does NOT trigger - the word appears mid-sentence, not as a prefix).
    const WAKE_WORD_REGEX = /^\s*(hey|hi|ok|okay)?[\s,]*buddy\b[\s,!.:]*/i;

    const WAKE_WORD_ACK_TEXT = {
        english: "Yes? How can I help?",
        hindi: "जी बताइए, मैं आपकी क्या मदद कर सकता हूँ?",
        vietnam: "Vâng, tôi có thể giúp gì cho bạn?",
        arabic: "نعم؟ كيف يمكنني مساعدتك؟",
        russian: "Да? Чем я могу вам помочь?",
    };

    // Strip a leading wake phrase from raw (un-normalized) text and return
    // whatever command, if any, followed it in the SAME utterance.
    function extractWakeWordCommand(rawText) {
        const text = String(rawText || "");
        const match = text.match(WAKE_WORD_REGEX);
        if (!match) {
            return { hasWakeWord: false, command: text };
        }
        return { hasWakeWord: true, command: text.slice(match[0].length).trim() };
    }

    function getWakeWordAckText() {
        const lang = getSelectedAssistantLanguage();
        return WAKE_WORD_ACK_TEXT[lang] || WAKE_WORD_ACK_TEXT.english;
    }

    function getAllowedActionKeys() {
        if (getAssistantRole() === "guest") {
            return [
                "home",
                "about_app",
                "login_job_seeker",
                "student_login",
                "login_employer",
                "employer_login",
                "register_job_seeker",
                "register_employer",
                "sitemap",
                "browse_all",
                "english_vocab",
                "aptitude",
                "tech"
            ];
        }

        return assistant.isEmployer
            ? EMPLOYER_ACTION_KEYS
            : STUDENT_ACTION_KEYS;
    }

    function isActionAllowedForCurrentRole(actionKey) {
        if (!actionKey) return false;

        if (!assistant.isEmployer && actionKey === "industries_nav") return true;

        // Dynamically generated backend activity/category actions are allowed for students
        if (!assistant.isEmployer && (actionKey === "site_nav" || actionKey.startsWith("activity_") || actionKey.startsWith("category_"))) {
            return true;
        }

        // Skill Up navigation keys ("skillup:<lesson-id>", "skillup:anchor:...")
        // are a student-side learning feature. Their routes are built and
        // re-validated against the catalog on the server, so they are safe to
        // follow here; without this the role gate silently swallows every
        // Skill Up "Opening …" so Buddy speaks the move but never makes it.
        if (!assistant.isEmployer && actionKey.startsWith("skillup:")) {
            return true;
        }

        return getAllowedActionKeys().includes(actionKey);
    }

    function getCrossRoleGuardResponse(message) {
        const normalized = normalizeText(message);

        if (!normalized) {
            return null;
        }

        // A guest is not inside either portal. Guests are allowed to choose
        // either Job Seeker or Employer login.
        if (getAssistantRole() === "guest") {
            return null;
        }

        const asksForEmployer =
            /\b(employer|employeer|recruiter|company|hiring|candidate|candidates|post job|job openings|applications)\b/.test(normalized);

        const asksForStudent =
            /\b(student|job seeker|jobseeker|grammar|activities|activity|speaking|writing|vocabulary|resume|roleplay|group discussion|jam)\b/.test(normalized);

        const isQuestion =
            /\b(is|are|can|do|does|what|where|how|available|present|have|show)\b/.test(normalized);

        const asksToNavigate =
            hasNavigationVerb(normalized) ||
            /\b(login|log in|sign in|open|go|take me|show me)\b/.test(normalized);

        if (!((assistant.isEmployer && asksForStudent) || (!assistant.isEmployer && asksForEmployer))) {
            return null;
        }

        if (!(isQuestion || asksToNavigate)) {
            return null;
        }

        const language = getSelectedAssistantLanguage();

        if (assistant.isEmployer) {
            const replies = {
                english:
                    "You're in the Employer portal. Job-seeker learning features are kept separate here, so I won't redirect you to the Job Seeker portal.",
                vietnam:
                    "Bạn đang ở cổng nhà tuyển dụng. Các tính năng dành cho sinh viên/người tìm việc được tách riêng, nên tôi sẽ không chuyển bạn sang cổng sinh viên.",
                hindi:
                    "आप Employer पोर्टल में हैं। Student और Job Seeker की सुविधाएँ अलग हैं, इसलिए मैं आपको Student पोर्टल पर रीडायरेक्ट नहीं करूँगा।",
                arabic:
                    "أنت في بوابة صاحب العمل. ميزات الطالب والباحث عن عمل منفصلة هنا، لذلك لن أنقلك إلى بوابة الطالب.",
                russian:
                    "Вы находитесь в портале работодателя. Функции для студентов и соискателей отделены, поэтому я не перенаправлю вас в портал студента."
            };

            return {
                reply: replies[language] || replies.english,
                source: "role_guard",
            };
        }

        const replies = {
            english:
                "You're in the Job Seeker portal. Employer and recruiter features are kept separate here, so I won't redirect you to the Employer portal.",
            vietnam:
                "Bạn đang ở cổng Sinh viên / Người tìm việc. Các tính năng dành cho nhà tuyển dụng và tuyển dụng được tách riêng, nên tôi sẽ không chuyển bạn sang cổng nhà tuyển dụng.",
            hindi:
                "आप Job Seeker पोर्टल में हैं। Employer और Recruiter की सुविधाएँ अलग हैं, इसलिए मैं आपको Employer पोर्टल पर रीडायरेक्ट नहीं करूँगा।",
            arabic:
                "أنت في بوابة الطالب / الباحث عن عمل. ميزات صاحب العمل والتوظيف منفصلة هنا، لذلك لن أنقلك إلى بوابة صاحب العمل.",
            russian:
                "Вы находитесь в портале студента / соискателя. Функции работодателя и рекрутера отделены, поэтому я не перенаправлю вас в портал работодателя."
        };

        return {
            reply: replies[language] || replies.english,
            source: "role_guard",
        };
    }

    function resolveLocalNavigationIntent(message) {
        const normalizedInput = normalizeText(message);

        if (!normalizedInput) {
            return null;
        }

        // A question ("what will I learn in X", "what are the sub
        // activities?") must never be resolved locally as navigation - it
        // needs to reach the backend so Buddy can actually explain, not
        // just open the page. See INFORMATIONAL_QUESTION_REGEX above.
        if (isInformationalQuestion(normalizedInput)) {
            return null;
        }

        const hasVerb = hasNavigationVerb(normalizedInput);

        let bestAction = null;
        let bestScore = 2;
        const inputTokens = normalizedInput.split(/\s+/).filter(Boolean);

        Object.entries(ACTION_DEFINITIONS).forEach(([key, definition]) => {
            // Role isolation: never resolve an action belonging to the other portal.
            if (!isActionAllowedForCurrentRole(key)) {
                return;
            }

            let maxKeywordScore = 0;

            (definition.keywords || []).forEach((keyword) => {
                const normalizedKeyword = normalizeText(keyword);
                if (!normalizedKeyword) {
                    return;
                }

                let currentScore = 0;

                // Whole-word match only. A plain substring check let a
                // short keyword like "pro" (Membership) match inside an
                // unrelated word like "Prompt" (Engineering) or
                // "professional" -- this is how "open Prompt Engineering"
                // on a non-Skill-Up page was being locally hijacked to the
                // Membership page before ever reaching the backend, which
                // resolves it correctly. Escaped since a keyword could in
                // principle contain a regex special character.
                const keywordPattern = new RegExp(
                    "(?<![\\w])" +
                    normalizedKeyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
                    "(?![\\w])"
                );
                if (keywordPattern.test(normalizedInput)) {
                    currentScore += normalizedKeyword.includes(" ") ? 5 : 3;
                }

                const keywordTokens = normalizedKeyword
                    .split(/\s+/)
                    .filter(
                        (token) =>
                            token &&
                            !INTENT_STOP_WORDS.has(token)
                    );

                keywordTokens.forEach((token) => {
                    if (inputTokens.includes(token)) {
                        currentScore += 1;
                    }
                });

                if (currentScore > maxKeywordScore) {
                    maxKeywordScore = currentScore;
                }
            });

            score = maxKeywordScore;

            if (score > bestScore) {
                bestScore = score;
                bestAction = {
                    key,
                    route: definition.route,
                    label: definition.label,
                    response: definition.response,
                };
            }
        });

        // Require a stronger match (score 5) if no explicit navigation verb is used
        const requiredScore = hasVerb ? 3 : 5;
        return bestScore >= requiredScore ? bestAction : null;
    }

    // Confirmations for browser-history moves, per supported language.
    const HISTORY_REPLIES = {
        back: {
            english: "Going back to the previous page.",
            hindi: "पिछले पेज पर वापस ले जा रहा हूँ।",
            vietnam: "Đang quay lại trang trước.",
            arabic: "أعود بك إلى الصفحة السابقة.",
            russian: "Возвращаю вас на предыдущую страницу.",
        },
        forward: {
            english: "Going forward to the next page.",
            hindi: "अगले पेज पर आगे ले जा रहा हूँ।",
            vietnam: "Đang chuyển tới trang tiếp theo.",
            arabic: "أنتقل بك إلى الصفحة التالية.",
            russian: "Перехожу на следующую страницу.",
        },
    };

    // Detect a browser-history move ("go back" / "go forward") the server
    // cannot perform. Returns "back", "forward", or null. A phrase that also
    // names a destination ("go back TO grammar") is deliberately NOT a history
    // move — it is handed to normal navigation instead, so history control and
    // "take me to X" never collide.
    function detectHistoryNavigation(message) {
        const normalized = normalizeText(message);
        if (!normalized) {
            return null;
        }
        const forwardRe = /\b(go forward|move forward|next page|forward)\b/;
        const backRe = /\b(go back|goback|take me back|navigate back|move back|go to (the )?previous( page| screen)?|previous page|previous screen|last page|back)\b/;

        let dir = null;
        let stripped = normalized;
        if (forwardRe.test(normalized) && !/look forward/.test(normalized)) {
            dir = "forward";
            stripped = normalized.replace(forwardRe, " ");
        } else if (backRe.test(normalized)) {
            dir = "back";
            stripped = normalized.replace(backRe, " ");
        }
        if (!dir) {
            return null;
        }
        // Anything left after removing the history phrase and filler names a
        // real destination, so this is not a bare history move.
        stripped = stripped
            .replace(/\b(to|the|please|now|just|a|an|my|page|screen|hey|buddy|can you|could you|i want you to|i want to)\b/g, " ")
            .replace(/\s+/g, " ")
            .trim();
        return stripped ? null : dir;
    }

    /**
     * True when a heard transcript is really Buddy's own last reply coming
     * back through the speakers rather than something the user said.
     *
     * Deliberately conservative: it only suppresses a turn that overlaps
     * heavily with what Buddy just said, so a user legitimately repeating a
     * short phrase ("grammar", "yes") is still heard.
     */
    // Fraction of heard words that also appear in the last reply. High overlap
    // means it is a fragment of Buddy's own speech (speaker bleed / replay), not
    // a new command. Used only inside the short TTS-tail cooldown so it never
    // blocks a genuine query. Fuzzy (not exact-subset) so transcription drift
    // ("&"->"and", dropped/joined words) is still caught.
    function lastReplyOverlap(candidate) {
        const spoken = new Set(normalizeText(assistant.lastResponseText || "").split(" ").filter(Boolean));
        const heard = normalizeText(candidate || "").split(" ").filter(Boolean);
        if (!spoken.size || !heard.length) {
            return 0;
        }
        const shared = heard.filter((word) => spoken.has(word)).length;
        return shared / heard.length;
    }

    function isEchoOfLastReply(candidate) {
        const spoken = normalizeText(assistant.lastResponseText || "");
        const heard = normalizeText(candidate || "");

        if (!spoken || !heard || heard.length < 8) {
            return false;
        }

        if (spoken === heard) {
            return true;
        }

        // Buddy's confirmations are often short. A containment test catches the common
        // case ("opening the grammar section"), but we only apply it if the heard string
        // is substantial enough to be an echo rather than a legitimate short answer.
        if (heard.length > 15 && (spoken.includes(heard) || heard.includes(spoken))) {
            return true;
        }

        // Otherwise fall back to word overlap, which survives the small
        // transcription errors a speaker-to-microphone round trip introduces.
        const spokenWords = new Set(spoken.split(" ").filter(Boolean));
        const heardWords = heard.split(" ").filter(Boolean);

        if (heardWords.length < 3) {
            return false;
        }

        const shared = heardWords.filter((word) => spokenWords.has(word)).length;
        return shared / heardWords.length >= 0.8;
    }

    function hasMeaningfulClientTranscript(value) {
        const text = String(value || "").trim();
        if (!text) {
            return false;
        }
        const words = text.split(/\s+/).filter(Boolean);
        return words.length >= 3 || text.length >= 18;
    }

    function getCookie(name) {
        if (!document.cookie) {
            return null;
        }

        const cookies = document.cookie.split(";");
        for (const rawCookie of cookies) {
            const cookie = rawCookie.trim();
            if (cookie.startsWith(`${name}=`)) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }

        return null;
    }

    function getCsrfToken() {
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        if (input) {
            return input.value;
        }
        return getCookie("csrftoken") || "";
    }

    function ensureModelViewerScript() {
        if (window.customElements?.get("model-viewer")) {
            return Promise.resolve();
        }

        if (modelViewerScriptPromise) {
            return modelViewerScriptPromise;
        }

        modelViewerScriptPromise = new Promise((resolve, reject) => {
            const existingScript = document.querySelector('script[data-riya-model-viewer="true"]');
            if (existingScript) {
                existingScript.addEventListener("load", () => resolve(), { once: true });
                existingScript.addEventListener("error", () => reject(new Error("model-viewer failed")), { once: true });
                return;
            }

            const script = document.createElement("script");
            script.type = "module";
            script.src = MODEL_VIEWER_SCRIPT_URL;
            script.dataset.riyaModelViewer = "true";
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("model-viewer failed"));
            document.head.appendChild(script);
        });

        return modelViewerScriptPromise;
    }

    function getLauncherModelSrc(vRiyant) {
        if (vRiyant === LAUNCHER_MODEL_VRiyaNTS.speaking) {
            return assistant.launcherModelSpeakingSrc || assistant.launcherModelIdleSrc || "";
        }
        return assistant.launcherModelIdleSrc || "";
    }

    function switchLauncherModel(vRiyant, options = {}) {
        if (!assistant.launcher || !assistant.launcherModel) {
            return;
        }

        const targetVRiyant =
            vRiyant === LAUNCHER_MODEL_VRiyaNTS.speaking
                ? LAUNCHER_MODEL_VRiyaNTS.speaking
                : LAUNCHER_MODEL_VRiyaNTS.idle;

        const nextSrc = getLauncherModelSrc(targetVRiyant);
        if (!nextSrc) {
            return;
        }

        const currentSrc = assistant.launcherModel.getAttribute("src") || "";
        const immediate = options.immediate === true;

        if (assistant.launcherModelVRiyant === targetVRiyant && currentSrc === nextSrc && !immediate) {
            return;
        }

        assistant.launcherModelVRiyant = targetVRiyant;

        // Apply contextual positioning and rotation (skipped for image launcher)
        if (targetVRiyant === LAUNCHER_MODEL_VRiyaNTS.speaking) {
            if (assistant.launcherModel && typeof assistant.launcherModel.setAttribute === 'function') {
                assistant.launcherModel.setAttribute("camera-orbit", "15deg 82deg 1.05m");
            }
        } else {
            if (assistant.launcherModel && typeof assistant.launcherModel.setAttribute === 'function') {
                assistant.launcherModel.setAttribute("camera-orbit", "40deg 82deg 1.05m");
            }
        }


        assistant.launcher.classList.add("is-model-switching");
        assistant.launcher.classList.remove("has-model-loaded");

        const switchToken = ++assistant.launcherModelSwitchToken;

        const applySource = () => {
            if (switchToken !== assistant.launcherModelSwitchToken) {
                return;
            }

            const finishLoad = () => {
                if (switchToken !== assistant.launcherModelSwitchToken) {
                    return;
                }
                assistant.launcher.classList.add("has-model-loaded");
                assistant.launcher.classList.remove("is-model-switching");
            };

            const handleError = () => {
                if (switchToken !== assistant.launcherModelSwitchToken) {
                    return;
                }
                assistant.launcher.classList.remove("has-model-loaded");
                assistant.launcher.classList.remove("is-model-switching");
            };

            assistant.launcherModel.addEventListener("load", finishLoad, { once: true });
            assistant.launcherModel.addEventListener("error", handleError, { once: true });
            assistant.launcherModel.setAttribute("src", nextSrc);

            if (typeof assistant.launcherModel.load === "function") {
                assistant.launcherModel.load();
            } else {
                finishLoad();
            }
        };

        if (immediate) {
            applySource();
            return;
        }

        window.setTimeout(applySource, 150);
    }

    function buildActions(actionKeys) {
        return (actionKeys || [])
            .filter((key) => isActionAllowedForCurrentRole(key))
            .map((key) => {
                const definition = ACTION_DEFINITIONS[key];
                if (!definition) {
                    return null;
                }
                return {
                    key,
                    label: definition.label,
                    route: definition.route,
                };
            })
            .filter(Boolean);
    }

    // Skill Up navigates by changing only the hash, which fires no page load.
    // Keep the assistant's cached path in step so current-page questions stay
    // accurate as the user moves between lessons.
    (function syncSkillUpHash() {
        function sync() {
            if (!assistant.root) { return; }
            const base = window.location.pathname;
            assistant.root.dataset.riyaPath = base + (window.location.hash || "");
            if (base.indexOf("/skill-up/") === 0) {
                assistant.root.dataset.riyaPage = "skill_up";
            }
        }
        if (typeof window !== "undefined") {
            window.addEventListener("hashchange", sync);
            if (document.readyState !== "loading") { sync(); }
            else { document.addEventListener("DOMContentLoaded", sync); }
        }
    })();

    function getPageContext() {
        const page = String(assistant.root?.dataset.riyaPage || "").toLowerCase();
        const path = String(
            assistant.root?.dataset.riyaPath ||
            window.location.pathname ||
            ""
        ).toLowerCase();

        // Employer context MUST be checked first.
        if (assistant.isEmployer || path.includes("/employer/")) {
            return {
                defaultReply:
                    "I can help you manage your company, find candidates, post jobs, review applications, and manage job openings.",
                actionKeys: [
                    "profile",
                    "company_profile",
                    "find_candidates",
                    "post_job",
                    "all_applications",
                    "job_openings",
                ],
            };
        }

        if (path.includes("/activities/") || page === "activity_list") {
            return {
                defaultReply:
                    "I can help you find listening, speaking, reading, or writing exercises.",
                actionKeys: ["lessons", "grammar", "profile"],
            };
        }

        if (path.includes("/subject/")) {
            return {
                defaultReply:
                    "I can help with grammar rules or take you to other student practice modules.",
                actionKeys: ["grammar", "lessons", "profile"],
            };
        }

        if (path.includes("/resume-builder/")) {
            return {
                defaultReply:
                    "I can help with your resume analysis and career preparation.",
                actionKeys: ["resume_builder", "lessons", "profile"],
            };
        }

        if (path.includes("/dashboard/") || page === "student_dashboard") {
            return {
                defaultReply:
                    "I can help you review your scores or suggest your next learning activity.",
                actionKeys: ["profile", "lessons", "grammar", "resume_builder"],
            };
        }

        if (path.includes("/roleplay/")) {
            return {
                defaultReply:
                    "I can help with your current roleplay or take you to other student practice modules.",
                actionKeys: ["roleplay", "lessons", "profile"],
            };
        }

        return {
            defaultReply:
                "I can guide you to activities, grammar, resume builder, speaking practice, or your student dashboard.",
            actionKeys: [
                "lessons",
                "grammar",
                "professional_speaking",
                "resume_builder",
                "profile",
            ],
        };
    }

    function buildFallbackPayload() {
        const context = getPageContext();
        return {
            reply: assistant.lastResponseText || GREETING_TEXT,
            actions: buildActions(context.actionKeys),
            source: "fallback",
        };
    }

    function getSourceLabel(source) {
        if (source === "intent") {
            return "Quick path";
        }
        if (source === "ai") {
            return "Buddy reply";
        }
        return "Helpful fallback";
    }

    function setAssistantState(nextState) {
        assistant.state = nextState;
        if (!assistant.root) {
            return;
        }

        assistant.root.classList.remove(
            "is-open",
            "is-greeting",
            "is-listening",
            "is-processing",
            "is-responding",
            "is-error"
        );

        if (nextState !== AssistantState.CLOSED) {
            assistant.root.classList.add("is-open");
        }
        if (nextState === AssistantState.GREETING) {
            assistant.root.classList.add("is-greeting");
        }
        if (nextState === AssistantState.LISTENING) {
            assistant.root.classList.add("is-listening");
        }
        if (nextState === AssistantState.PROCESSING) {
            assistant.root.classList.add("is-processing");
        }
        if (nextState === AssistantState.RESPONDING) {
            assistant.root.classList.add("is-responding");
        }
        if (nextState === AssistantState.ERROR) {
            assistant.root.classList.add("is-error");
        }

        if (assistant.launcher) {
            assistant.launcher.style.display = nextState === AssistantState.CLOSED ? "flex" : "none";
        }

        // The microphone indicator must NEVER be permanently visible.
        // It is shown only during an actual listening state. This prevents
        // the header from displaying "Listening" while Buddy is greeting,
        // processing, speaking, or idle.
        if (assistant.micIndicator) {
            const isListening = nextState === AssistantState.LISTENING;
            assistant.micIndicator.style.display = isListening ? "inline-flex" : "none";
            assistant.micIndicator.setAttribute("aria-hidden", isListening ? "false" : "true");
        }

        if (assistant.launcher) {
            assistant.launcher.setAttribute(
                "aria-expanded",
                nextState === AssistantState.CLOSED ? "false" : "true"
            );
        }
        if (assistant.bubble) {
            assistant.bubble.setAttribute(
                "aria-hidden",
                nextState === AssistantState.CLOSED ? "true" : "false"
            );
        }

        updateMicButtonState();

    }

    function updateMicButtonState() {
        const button =
            assistant.micButton;

        if (!button) {
            return;
        }

        const isListening =
            assistant.state ===
            AssistantState.LISTENING;

        const isProcessing =
            assistant.state ===
            AssistantState.PROCESSING;

        const isClosed =
            assistant.state ===
            AssistantState.CLOSED;

        button.classList.toggle(
            "is-listening",
            isListening
        );

        button.setAttribute(
            "aria-pressed",
            isListening
                ? "true"
                : "false"
        );

        // Don't disable the button merely because TTS is speaking.
        // It should only be unavailable while processing a request.
        button.disabled =
            isProcessing ||
            isClosed;

        button.setAttribute(
            "aria-label",
            isListening
                ? "Stop listening"
                : "Speak to Buddy"
        );

        button.title =
            isListening
                ? "Click to stop listening"
                : "Click to speak";

        if (assistant.micLabel) {
            assistant.micLabel.textContent =
                isListening
                    ? "Stop"
                    : "Speak";
        }
    }

    function setMicIndicatorVisible(visible) {
        if (!assistant.micIndicator) return;
        assistant.micIndicator.style.display = visible ? "inline-flex" : "none";
        assistant.micIndicator.setAttribute("aria-hidden", visible ? "false" : "true");
    }

    function setStatus(text) {
        if (assistant.statusText) {
            assistant.statusText.textContent = text;
        }
    }

    function showTranscript(text) {
        const slot = assistant.responseSlot;
        if (!slot) return;

        const cleanText = String(text || "").trim();
        if (!cleanText) return;

        let userCard = slot.querySelector(".riya-user-transcript.is-current");

        if (!userCard) {
            userCard = document.createElement("div");
            userCard.className =
                "riya-response-card riya-user-transcript is-current";

            const p = document.createElement("p");
            userCard.appendChild(p);

            slot.appendChild(userCard);
        }

        const p = userCard.querySelector("p");
        if (p) {
            p.textContent = cleanText;
        }

        // Always show the newest message.
        slot.scrollTop = slot.scrollHeight;
    }
    function clearTranscript(delayMs = 0) {
        const slot = assistant.responseSlot;
        if (!slot) return;

        const userCard = slot.querySelector(
            ".riya-user-transcript.is-current"
        );

        if (userCard) {
            userCard.classList.remove("is-current");
        }
    }

    function welcomeText(value, lang) {
        if (!value) return "";
        if (typeof value === "string") return value;
        return value[lang] || value.english || Object.values(value)[0] || "";
    }

    function getWelcomePanel() {
        return document.getElementById("riya-welcome-panel");
    }

    // What Buddy says before moving: the card's own context line when it has
    // one for this language, then the usual "Opening X." confirmation. Without
    // a context line it falls back to the guided reply ("Opening X. Inside
    // you'll find..."), so every card says something about where it leads.
    function buildWelcomeReply(card, action, lang) {
        const ctx = lang === "english"
            ? card.context
            : CONTEXT_I18N[card.id]?.[lang];
        return ctx
            ? `${ctx} ${getLocalizedActionResponse(action)}`
            : buildGuidedNavigationReply(action);
    }

    // Server voices take a moment to
    // synthesise a line. Card replies are known before anyone taps, so fetch
    // their audio quietly once the cards render: the server caches it and the
    // browser keeps it (Cache-Control), and a tap then speaks at once.
    const PREFETCH_TTS_LANGS = new Set(["vietnam", "arabic", "russian"]);
    const prefetchedSpeech = new Set();

    async function prefetchCardSpeech(cards, lang) {
        if (!PREFETCH_TTS_LANGS.has(lang)) return;
        for (const card of cards) {
            const definition = ACTION_DEFINITIONS[card.actionKey];
            if (!definition || !isActionAllowedForCurrentRole(card.actionKey)) continue;
            const action = { key: card.actionKey, route: definition.route, label: definition.label, response: definition.response };
            const reply = buildWelcomeReply(card, action, lang);
            const url = ttsStreamUrl(reply, reply);
            if (prefetchedSpeech.has(url)) continue;
            prefetchedSpeech.add(url);
            try {
                // One at a time, so a page view never fires a burst of requests.
                await (await fetch(url)).arrayBuffer();
            } catch (_error) {
                // Best effort only; a miss just means the tap synthesises live.
            }
        }
    }

    function runWelcomeAction(card, questionText) {
        const actionKey = card.actionKey;
        const definition = ACTION_DEFINITIONS[actionKey];
        if (!definition || !isActionAllowedForCurrentRole(actionKey)) {
            console.warn("[Buddy Welcome] Action unavailable:", actionKey);
            return;
        }

        const action = {
            key: actionKey,
            route: definition.route,
            label: definition.label,
            response: definition.response,
        };

        // Reuse the existing navigation/action pipeline so role guards,
        // speech persistence and special in-page actions continue to work.
        //
        // speak:true — a tapped card used to navigate in silence because this
        // passed speak:false, so "Opening the activities page." was printed but
        // never said. commitNavigation() then holds the page until the line has
        // been spoken, instead of the old blind 180ms timer that moved the page
        // before the voice could start.
        // The tapped card reads as the user's question, Buddy answers it with
        // context, then navigates once that answer has been spoken.
        const reply = buildWelcomeReply(card, action, getSelectedAssistantLanguage());
        showTranscript(questionText);
        addConversationMessage("user", questionText);
        addConversationMessage("assistant", reply);
        commitNavigation(action);
        renderPayload(
            { reply, actions: buildActions([actionKey]), source: "welcome-action" },
            { speak: true, statusText: "Opening your selection." }
        );
    }

    function buildWelcomeCard(card, lang, variant) {
        const definition = ACTION_DEFINITIONS[card.actionKey];
        if (!definition || !isActionAllowedForCurrentRole(card.actionKey)) return null;

        const el = document.createElement("button");
        el.type = "button";
        el.className = `riya-welcome-card riya-welcome-card--${variant || "action"}`;
        el.setAttribute("data-card-id", card.id);
        el.setAttribute("data-action-key", card.actionKey);

        const baseTitle = welcomeText(card.title, lang);
        const title = TITLE_I18N[card.id]?.[lang] || RECOMMENDATION_TRANSLATIONS[lang]?.[baseTitle] || baseTitle;
        const description = welcomeText(card.description, lang);
        el.setAttribute("aria-label", `${title}. ${description}`);

        el.innerHTML = `
            <span class="riya-welcome-card-icon" aria-hidden="true">
                ${WELCOME_ICONS[card.icon] || WELCOME_ICONS.briefcase}
            </span>
            <span class="riya-welcome-card-body">
                <span class="riya-welcome-card-title-row">
                    <span class="riya-welcome-card-title">${title}</span>
                    <span class="riya-welcome-card-chevron" aria-hidden="true">${WELCOME_ICONS.chevron}</span>
                </span>
                <span class="riya-welcome-card-desc">${description}</span>
            </span>`;

        return el;
    }

    document.addEventListener("click", (event) => {
        const btn = event.target.closest(".riya-welcome-card");
        if (!btn) return;
        const actionKey = btn.getAttribute("data-action-key");
        if (!actionKey) return;
        
        event.preventDefault();
        const cardId = btn.getAttribute("data-card-id");
        
        let matchedCard = null;
        for (const role of Object.keys(WELCOME_CONTEXT)) {
            const ctx = WELCOME_CONTEXT[role];
            for (const list of ["quickActions", "recommendations", "guidedPath", "resumeGuidedPath"]) {
                if (ctx[list]) {
                    const found = ctx[list].find(c => c.id === cardId);
                    if (found) {
                        matchedCard = found;
                        break;
                    }
                }
            }
            if (matchedCard) break;
        }
        
        if (!matchedCard) {
            matchedCard = { id: cardId, actionKey: actionKey, title: btn.querySelector(".riya-welcome-card-title")?.textContent || actionKey };
        }
        
        const lang = getSelectedAssistantLanguage();
        const baseTitle = welcomeText(matchedCard.title, lang);
        const title = TITLE_I18N[matchedCard.id]?.[lang] || RECOMMENDATION_TRANSLATIONS[lang]?.[baseTitle] || baseTitle;
        
        runWelcomeAction(matchedCard, title);
    });

    // ---- landing stage pills ---------------------------------------------
    // The stage's five pills come from the central topic mapping
    // (static/js/buddy_visuals.js) while the visitor is looking at a
    // department; otherwise the landing defaults below apply (they are also
    // the fallback if that script is missing). Slots, in order: n, ne, nw, sw, se.
    const LANDING_STAGE_SLOTS = [["n", "0.5s"], ["ne", "0.7s"], ["nw", "0.9s"], ["sw", "1.1s"], ["se", "1.3s"]];
    const LANDING_STAGE_DEFAULT = [
        { icon: "resume", label: "Resume Builder" },
        { icon: "briefcase", label: "Find Jobs" },
        { icon: "cap", label: "Skill Up" },
        { icon: "interview", label: "Interview Practice" },
        { icon: "sparkle", label: "Certifications" },
    ];
    function getLandingStageFeatures() {
        let pills = null;
        let asks = null;
        try {
            pills = window.CBBuddyVisuals && window.CBBuddyVisuals.getStageNodes();
            asks = pills && window.CBBuddyVisuals.getStageQuestions && window.CBBuddyVisuals.getStageQuestions();
        } catch (e) {
            pills = null;
            asks = null;
        }
        if (!Array.isArray(pills) || pills.length !== LANDING_STAGE_SLOTS.length) {
            pills = LANDING_STAGE_DEFAULT;
            asks = null;
        }
        // A topic pill is a button: clicking it asks Buddy that question. The landing defaults stay decoration.
        return pills.map((p, i) => ({
            icon: p.icon,
            label: p.label,
            pos: LANDING_STAGE_SLOTS[i][0],
            d: LANDING_STAGE_SLOTS[i][1],
            ask: Array.isArray(asks) && asks[i] ? String(asks[i]) : "",
        }));
    }
    function stageText(value) {
        return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
    function buildLandingStageNodesHtml(features) {
        return features.map((f) => `
                <span class="riya-visual-node riya-visual-node--${f.pos}" style="--d:${f.d}" title="${stageText(f.ask || f.label)}"${f.ask ? ` data-cb-ask="${stageText(f.ask)}" role="button" tabindex="0"` : ""}>
                    <span class="riya-visual-node-content">
                        <span class="riya-visual-node-icon">${WELCOME_ICONS[f.icon] || WELCOME_ICONS.briefcase}</span>
                        <span class="riya-visual-node-label">${stageText(f.label)}</span>
                    </span>
                </span>`).join("");
    }
    // Same stage, new pills: swapped in place when the visitor opens another
    // department. Only the five pills change - the conversation, the mascot
    // and the rest of the stage are left alone.
    function refreshLandingStageNodes() {
        const stage = assistant.responseSlot && assistant.responseSlot.querySelector(".riya-visual-stage");
        const glow = stage && stage.querySelector(".riya-visual-glow");
        if (!stage || !glow) return;
        const wanted = getLandingStageFeatures();
        const shown = [...stage.querySelectorAll(".riya-visual-node")].map(
            (n) => ((n.querySelector(".riya-visual-node-label") || {}).textContent || "") + "|" + (n.getAttribute("data-cb-ask") || "")
        );
        if (shown.length === wanted.length && shown.every((key, i) => key === wanted[i].label + "|" + wanted[i].ask)) return;
        stage.querySelectorAll(".riya-visual-node").forEach((n) => n.remove());
        glow.insertAdjacentHTML("afterend", buildLandingStageNodesHtml(wanted));
        stage.setAttribute("aria-hidden", wanted.some((f) => f.ask) ? "false" : "true");
        if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            stage.querySelectorAll(".riya-visual-node").forEach((n, i) => {
                try {
                    n.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 350, delay: i * 70, easing: "ease-out", fill: "backwards" });
                } catch (e) { /* cosmetic only */ }
            });
        }
    }
    window.addEventListener("cb:buddy-topic", refreshLandingStageNodes);

    // Clicking a topic pill asks Buddy its question, exactly as if the visitor had typed it
    // (sendTextMessage -> showTranscript + processTranscript). Whatever they were typing is kept.
    function askFromStagePill(question) {
        if (!question || !assistant.textInput) return;
        if (assistant.state === AssistantState.PROCESSING) return; // never interrupt a running answer
        const typedSoFar = assistant.textInput.value;
        assistant.textInput.value = question;
        sendTextMessage();
        assistant.textInput.value = typedSoFar;
    }
    function onStagePillActivate(event) {
        const pill = event.target && event.target.closest ? event.target.closest(".riya-visual-node[data-cb-ask]") : null;
        if (!pill || !assistant.responseSlot || !assistant.responseSlot.contains(pill)) return;
        if (event.type === "keydown" && event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        askFromStagePill(pill.getAttribute("data-cb-ask"));
    }
    document.addEventListener("click", onStagePillActivate);
    document.addEventListener("keydown", onStagePillActivate);

    function renderPersistentWelcome() {
        const panel = getWelcomePanel();
        if (!panel) return;

        const role = getAssistantRole();
        const section0 = getAssistantSection();
        // Landing-page-only override: a signed-out visitor on "/" gets the
        // 5-item guestLanding set; a signed-out visitor anywhere else still
        // gets the normal WELCOME_CONTEXT.guest cards (unchanged, matches
        // "scope to Landing Page only").
        const roleContext = role === "guest"
            ? (section0 === "home" ? WELCOME_CONTEXT.guestLanding : WELCOME_CONTEXT.guest)
            : (WELCOME_CONTEXT[role] || WELCOME_CONTEXT.guest);
        const section = role === "guest" ? "" : section0;
        const context = SECTION_CONTEXT[section] || roleContext;
        const lang = getSelectedAssistantLanguage();
        // /careers/<track>/ is where a department is picked: a signed-out visitor
        // gets the same animated stage there (topic-aware), above the normal guest cards.
        const isCareersExplorer = role === "guest" && /^\/careers\//i.test(String(window.location.pathname || ""));
        const isGuestLanding = roleContext === WELCOME_CONTEXT.guestLanding || role === "student" || isCareersExplorer;

        // guestLanding renders ONCE into the SAME scrollable flow as the
        // greeting/conversation (#riya-response-slot), not into the
        // separate persistent panel -- per spec, it must behave like
        // normal scrollable content that naturally scrolls out of view as
        // the conversation grows, never collapsed/removed/replaced. Guard
        // against duplicating it on repeat calls (language change, etc.):
        // if it's already in the scroll flow, leave it alone entirely and
        // only let every OTHER role continue using the unchanged
        // panel-replace behavior below.
        if (isGuestLanding) {
            if (!assistant.responseSlot) return;
            if (assistant.responseSlot.querySelector(".riya-visual-wrap")) return;
            // Also guard against running before the greeting exists yet --
            // resetToContextView() calls this at page-load time (its own
            // comment: "do NOT render the greeting here", for state-reset
            // only), well before openChat() has added anything. Inserting
            // into an empty response-slot then would put the visual BEFORE
            // the greeting once openChat() later adds it. Skipping here is
            // safe: openChat() calls this again right after the greeting
            // card is actually in the DOM, which is the real, correct
            // insertion point.
            if (!assistant.responseSlot.querySelector(".riya-response-card:not(.is-placeholder)")) return;
        }

        let pillsContainer = panel.querySelector(".riya-suggestion-pills");
        if (pillsContainer) {
            pillsContainer.remove();
        }

        pillsContainer = document.createElement("div");
        pillsContainer.className = "riya-suggestion-pills";

        // guestLanding only -- compact, pure CSS/JS premium intro visual.
        // No image swap, no external GIF: orbit rings + glow + the
        // existing Buddy image + label, sized small (~160px desktop /
        // ~130px mobile, CSS below) so recommendations stay visible. Lives
        // permanently in the normal scroll flow (see the isGuestLanding
        // append branch below) -- NOT collapsed, removed, or replaced on
        // interaction. It simply scrolls out of view as the conversation
        // grows, and back into view if the user scrolls up, exactly like
        // any other content in this same scrollable area.
        if (isGuestLanding) {
            // Application-oriented animation: Buddy at the center, 5 small
            // feature nodes (own icons, own layout -- not the reference
            // image's artwork) orbiting it, replacing the earlier plain
            // rings/particles. Fits the SAME existing .riya-visual-stage
            // container (CSS height unchanged) -- only what's drawn inside
            // it changed, per this round's "animation-only" requirement.
            const launcherSrc = assistant.root ? assistant.root.querySelector(".riya-launcher-img")?.src : "";
            const features = getLandingStageFeatures();
            const nodesHtml = buildLandingStageNodesHtml(features);
            const stageWrap = document.createElement("div");
            stageWrap.className = "riya-visual-wrap";
            stageWrap.innerHTML = `
                <div class="riya-visual-stage" aria-hidden="${features.some((f) => f.ask) ? "false" : "true"}">
                    <svg class="riya-visual-orbit-svg" viewBox="0 0 300 160" preserveAspectRatio="xMidYMid meet">
                        <ellipse cx="150" cy="80" rx="105" ry="40" class="orbit-ring" />
                        <ellipse cx="150" cy="80" rx="50" ry="18" class="orbit-ring" style="stroke-dasharray: 2 6; opacity: 0.5;" />
                        <path d="M150,80 Q150,47 150,15" class="orbit-link orbit-link--n" />
                        <path d="M150,80 Q202,72 255,65" class="orbit-link orbit-link--ne" />
                        <path d="M150,80 Q97,72 45,65" class="orbit-link orbit-link--nw" />
                        <path d="M150,80 Q197,105 245,130" class="orbit-link orbit-link--se" />
                        <path d="M150,80 Q102,105 55,130" class="orbit-link orbit-link--sw" />
                        <circle cx="150" cy="40" r="2.5" class="orbit-particle orbit-particle--1" />
                        <circle cx="150" cy="120" r="2.5" class="orbit-particle orbit-particle--2" />
                    </svg>
                    <span class="riya-visual-glow"></span>
                    ${nodesHtml}
                    <div class="riya-visual-mascot-container">
                        ${launcherSrc ? `<img src="${launcherSrc}" alt="" class="riya-visual-mascot">` : ""}
                        <div class="riya-visual-mascot-label">CareerBuddy</div>
                    </div>
                </div>`;
            pillsContainer.appendChild(stageWrap);
            requestAnimationFrame(() => stageWrap.querySelector(".riya-visual-stage")?.classList.add("is-playing"));
        }

        // guestLanding only (not other roles/pages): a short caption right
        // above the options, matching the "Click on your preferred option"
        // beat from the reference widget. roleContext.heading already
        // existed as a config field but was never actually rendered by this
        // function for any role -- wiring it up ONLY for this one case
        // keeps every other page's pill panel exactly as it was.
        if ((roleContext === WELCOME_CONTEXT.guestLanding || role === "student") && roleContext.heading) {
            const caption = document.createElement("div");
            caption.className = "riya-welcome-caption";
            caption.textContent = roleContext.heading;
            pillsContainer.appendChild(caption);
        }

        const quickGrid = document.createElement("div");
        quickGrid.className = "riya-welcome-grid riya-welcome-grid--landing";
        context.quickActions.forEach((card) => {
            const node = buildWelcomeCard(card, lang, "action");
            if (node) quickGrid.appendChild(node);
        });
        pillsContainer.appendChild(quickGrid);

        if (context.recommendations?.length) {
            const visibleGrid = document.createElement("div");
            visibleGrid.className = "riya-welcome-grid riya-welcome-grid--rec";
            context.recommendations.forEach((card) => {
                const node = buildWelcomeCard(card, lang, "rec");
                if (node) visibleGrid.appendChild(node);
            });
            pillsContainer.appendChild(visibleGrid);
        }

        if (isGuestLanding && assistant.responseSlot) {
            // Normal scrollable content, appended after whatever's already
            // there (the greeting, rendered just before this call) -- not
            // the separate persistent panel. This is what makes it scroll
            // away naturally as later messages are appended below it,
            // and scroll back INTO view when the user scrolls up, with no
            // special-case logic of its own.
            assistant.responseSlot.appendChild(pillsContainer);
            requestAnimationFrame(() => {
                assistant.responseSlot.scrollTop = assistant.responseSlot.scrollHeight;
            });
        } else {
            panel.appendChild(pillsContainer);
        }
        prefetchCardSpeech([...context.quickActions, ...(context.recommendations || [])], lang);
    }

    function refreshPersistentWelcome() {
        renderPersistentWelcome();
    }

    // ============================================================
    // TEXT + VOICE TOGETHER
    // A reply used to appear as text at once, while its voice followed only
    // after synthesis (0.5-2s, and for AI answers after the whole generation).
    // A spoken reply now stays hidden behind the typing dots and is revealed
    // the moment its voice starts: <audio> 'playing', the browser voice
    // starting, or speech ending/failing — so the voice always follows the
    // text within the same frame, in every language. Every failure path
    // already reveals (server 404 -> browser voice -> reveal; finalizeSpeech),
    // so the cap is only a last-resort guard against a hung request. It sits
    // well above any real synthesis time; a short cap (8s) once showed the
    // text seconds before a slow voice began.
    // ============================================================
    const SPEECH_REVEAL_CAP_MS = 20000;

    function revealPendingCard() {
        if (assistant.pendingRevealTimer) {
            clearTimeout(assistant.pendingRevealTimer);
            assistant.pendingRevealTimer = null;
        }
        const card = assistant.pendingRevealCard;
        if (!card) return;
        assistant.pendingRevealCard = null;
        card.hidden = false;
        const slot = assistant.responseSlot;
        if (!slot) return;
        const thinking = slot.querySelector(".is-thinking");
        if (thinking) thinking.remove();
        requestAnimationFrame(() => {
            slot.scrollTop = slot.scrollHeight;
        });
        persistAssistantSession({ lastResponseText: assistant.lastResponseText });
    }

    function renderResponseCard(payload, options = {}) {
        if (!assistant.responseSlot) {
            return;
        }

        const slot = assistant.responseSlot;

        // Thinking card is temporary.
        if (options.vRiyant === "thinking") {
            const card = document.createElement("div");
            card.className = "riya-response-card is-thinking";

            const text = document.createElement("p");
            text.className = "riya-thinking-label";
            text.textContent = payload.reply || uiText().thinking;
            card.appendChild(text);

            const dots = document.createElement("div");
            dots.className = "riya-thinking-dots";
            dots.setAttribute("aria-hidden", "true");

            for (let index = 0; index < 3; index += 1) {
                const dot = document.createElement("span");
                dots.appendChild(dot);
            }

            card.appendChild(dots);

            // Remove only an old temporary thinking card.
            const oldThinking = slot.querySelector(".is-thinking");
            if (oldThinking) {
                oldThinking.remove();
            }

            slot.appendChild(card);
            slot.scrollTop = slot.scrollHeight;
            return;
        }

        const card = document.createElement("div");
        card.className = "riya-response-card";

        if (options.animate !== false) {
            card.classList.add("is-entering");
        }

        const text = document.createElement("p");
        text.textContent = payload.reply || "";
        card.appendChild(text);

        // Remove current streaming card if this is its final response.
        const streamingCard = slot.querySelector("#riya-stream-card");
        if (streamingCard) {
            streamingCard.remove();
        }

        if (options.waitForSpeech) {
            // Text and voice arrive together: the card stays hidden behind the
            // typing dots until the voice actually starts (revealPendingCard).
            revealPendingCard();
            card.hidden = true;
            if (!slot.querySelector(".is-thinking")) {
                renderResponseCard({}, { vRiyant: "thinking" });
            }
            slot.appendChild(card);
            assistant.pendingRevealCard = card;
            assistant.pendingRevealTimer = window.setTimeout(revealPendingCard, SPEECH_REVEAL_CAP_MS);
            return;
        }

        // Remove temporary thinking card only.
        const thinkingCard = slot.querySelector(".is-thinking");
        if (thinkingCard) {
            thinkingCard.remove();
        }

        slot.appendChild(card);

        // Always scroll to newest response.
        requestAnimationFrame(() => {
            slot.scrollTop = slot.scrollHeight;
        });
    }

    function setActionChips(actions) {
        return;
    }

    function clearAutoListenTimer() {
        if (assistant.autoListenTimer) {
            clearTimeout(assistant.autoListenTimer);
            assistant.autoListenTimer = null;
        }
    }

    function scheduleAutoListen(delayMs = 300) {
        clearAutoListenTimer();

        assistant.autoListenTimer = window.setTimeout(() => {
            assistant.autoListenTimer = null;

            // NEVER restart Listening during a language change.
            if (assistant.languageChangeInProgress) {
                return;
            }

            if (
                assistant.state !== AssistantState.CLOSED &&
                !assistant.ttsSpeaking &&
                !assistant.microphoneBlockedByTTS
            ) {
                startVoiceRecording();
            }
        }, Math.max(300, delayMs));
    }

    function renderPayload(payload, options = {}) {
        const normalizedPayload = payload || buildFallbackPayload();
        assistant.lastResponseText = normalizedPayload.reply || "";

        renderResponseCard(normalizedPayload, {
            waitForSpeech: !!(options.speak && assistant.lastResponseText),
        });
        setActionChips(normalizedPayload.actions || buildFallbackPayload().actions);
        clearTranscript(0);
        setAssistantState(
            normalizedPayload.source === "fallback" && options.asError
                ? AssistantState.ERROR
                : AssistantState.RESPONDING
        );
        if (!options.speak) {
            setStatus(options.statusText || "Ready for your next question.");
        }

        // Speak synchronously, NOT inside requestAnimationFrame: a rAF callback
        // can be delayed or skipped (background/throttled tab), and meanwhile
        // commitNavigation()'s no-speech watchdog saw ttsSpeaking=false and
        // left the page silently — "Opening X" printed but never said. Calling
        // speakText now sets ttsSpeaking before the watchdog's first tick, and
        // keeps the audio.play() inside the click's user-activation window.
        if (options.speak && assistant.lastResponseText) {
            speakText(assistant.lastResponseText, {
                audioBase64: normalizedPayload.audio || null,
                // Navigation is independent of speech (see commitNavigation);
                // afterSpeak only carries the auto-listen resume callback.
                afterSpeak: options.afterSpeak
                    || (options.autoResumeListening && assistant.state !== AssistantState.CLOSED
                        ? () => scheduleAutoListen()
                        : null),
            });
            // Reflect the auto-narration on the header speaker button so
            // the user can pause / resume it.
            setSpeakerState("speaking");
        }

        if (!options.speak && options.autoResumeListening) {
            scheduleAutoListen();
        }

        persistAssistantSession({
            isOpen: assistant.state !== AssistantState.CLOSED,
            lastResponseText: assistant.lastResponseText,
        });
    }

    function performAction(action) {
        if (!action) {
            return;
        }

        // Final safety net: never open a route belonging to the other portal.
        if (action.key && !isActionAllowedForCurrentRole(action.key)) {
            return;
        }

        const path = window.location.pathname.toLowerCase();

        // Direct to employer dashboard if already in employer context
        if (action.key === "profile" && path.includes("employer")) {
            action.route = "/employer/employer/dashboard/";
        }

        if (action.key === "history" && path.includes("/evaluation/")) {
            const section = document.getElementById("previousSessionsSection");
            if (section) {
                section.scrollIntoView({ behavior: "smooth", block: "start" });
                closeChat();
                return;
            }
        }

        if (action.key === "analytics" && path.includes("/evaluation/")) {
            window.scrollTo({ top: 0, behavior: "smooth" });
            closeChat();
            return;
        }

        // SPEECH SURVIVES NAV: if narration is still going when we leave (the
        // stall ceiling fired mid-speech, or the 5s-pause move), hand the
        // UNSPOKEN REMAINDER to the destination page so it RESUMES from where
        // it stopped rather than restarting. Normal "speak fully, then
        // navigate" has ttsSpeaking false here, so this does nothing.
        if (assistant.ttsSpeaking) {
            const full = assistant.speechText || assistant.lastResponseText || "";
            const remaining = full.slice(getSpokenIndex(full));
            if (remaining.trim()) {
                stashPendingSpeech(remaining);
            }
        }

        window.location.href = action.route;
    }

    // How many characters of the current utterance have already been spoken —
    // from onboundary (browser TTS) or the audio play position (server TTS).
    function getSpokenIndex(full) {
        if (assistant.ttsPath === "audio" && assistant.ttsAudio) {
            const dur = assistant.ttsAudio.duration;
            const cur = assistant.ttsAudio.currentTime;
            if (dur && isFinite(dur) && dur > 0) {
                return Math.max(0, Math.min(full.length, Math.floor(full.length * (cur / dur))));
            }
            return 0;
        }
        return Math.max(0, Math.min(full.length, assistant.speechCharIndex || 0));
    }

    function closeLauncherBubble() {
        return;
    }

    function resetToContextView() {
        const context = getPageContext();

        // Do NOT add or render the greeting here.
        // This function is only for resetting the assistant state/UI.

        setActionChips(buildActions(context.actionKeys));
        renderPersistentWelcome();

        clearTranscript();

        switchLauncherModel(
            LAUNCHER_MODEL_VRiyaNTS.idle
        );

        setStatus(
            "Click the microphone when you want to speak."
        );
    }

    function stopListeningForSpeechOutput() {
        // Buddy and the microphone must never operate at the same time.
        // Any recognition result currently being captured is discarded
        // because it belongs to the previous user turn.
        assistant.microphoneBlockedByTTS = true;
        setMicIndicatorVisible(false);
        assistant.voiceTurnHandled = true;
        assistant.pendingBackendTranscript = false;
        clearSilenceTimer();
        clearAutoListenTimer();

        if (assistant.recognition && assistant.recognitionRunning) {
            assistant.recognitionStopReason = "tts";
            try {
                assistant.recognition.stop();
            } catch (_error) {
                assistant.recognitionRunning = false;
            }
        }

        if (
            assistant.mediaRecorder &&
            assistant.mediaRecorder.state !== "inactive"
        ) {
            assistant.mediaStopReason = "language_change";
            try {
                assistant.mediaRecorder.stop();
            } catch (_error) {
                // Nothing else is required; the stream will be released below.
            }
        }
    }

    function releaseMicrophoneResources() {
        if (assistant.mediaStream) {
            try {
                assistant.mediaStream.getTracks().forEach((track) => {
                    try {
                        track.stop();
                    } catch (_error) { }
                });
            } catch (_error) { }
            assistant.mediaStream = null;
        }

        if (assistant.mediaAudioContext) {
            try {
                assistant.mediaAudioContext.close();
            } catch (_error) { }
            assistant.mediaAudioContext = null;
        }

        assistant.mediaAnalyser = null;

        if (
            assistant.mediaRecorder &&
            assistant.mediaRecorder.state === "inactive"
        ) {
            assistant.mediaRecorder = null;
        }
    }

    // ============================================================
    // NAVIGATION COMMITMENT
    //
    // Once Buddy has said "Opening the grammar section", it must open the
    // grammar section. Navigation used to ride on pendingAfterSpeak, which
    // stopSpeaking() clears — so any new utterance silently cancelled the
    // pending move. Combined with a duplicated voice turn that produced a
    // second utterance, the user saw "Opening the grammar section." repeat
    // and the page never moved.
    //
    // Speech may now DELAY navigation, never cancel it — but the delay must
    // be governed by whether TTS is ACTUALLY still speaking, not a blind
    // fixed clock. A single fixed timeout (previously 2.6s) fires on
    // schedule regardless of speech state, which cut off longer guided
    // navigation replies ("Inside you'll find X, Y and Z...") mid-sentence
    // before finalizeSpeech() ever got to run the navigation itself.
    //
    // This is a re-arming watchdog instead: while assistant.ttsSpeaking is
    // true, it keeps pushing its own deadline out rather than firing, so it
    // can never interrupt speech that is genuinely still playing. It only
    // acts as a true stall safety net — TTS silently failing to start or
    // to call onend/onerror — and only after a generous absolute ceiling,
    // so it still guarantees the user is never permanently stranded.
    // ============================================================
    // Navigation waits for Buddy to finish the sentence it is saying, then
    // goes immediately — finalizeSpeech() fires runNavigationCommitment the
    // moment the audio ends, so there is no polling lag in the normal case.
    //
    // These two only cover the abnormal case where speech never starts at all
    // (TTS failed, nothing to say, autoplay blocked). Without them a failed
    // synthesis would strand the user on the old page forever.
    const NAVIGATION_POLL_MS = 100;
    // speakText() sets assistant.ttsSpeaking synchronously, BEFORE it fetches
    // any audio, so by the time this window elapses the flag is already true
    // for any reply that is going to be spoken — and the watcher then waits
    // for the whole utterance however long the synthesis takes. This is only
    // the "nothing is ever going to speak" case (a reply the caller asked not
    // to speak, or TTS that failed outright), where waiting longer is dead
    // time the user spends staring at the old page.
    const NAVIGATION_NO_SPEECH_TIMEOUT_MS = 800;

    function commitNavigation(action) {
        if (!action || !action.route) {
            return;
        }

        // A second navigation request supersedes the first rather than
        // stacking behind it.
        clearNavigationCommitment();

        assistant.pendingNavigation = action;
        assistant.navigationDone = false;

        const committedAt = Date.now();

        // While Buddy is speaking, leave the move to finalizeSpeech(): it runs
        // on the audio's own 'ended' event, which is as immediate as it gets.
        // This watcher exists only to catch the case where speech never began.
        const watch = () => {
            assistant.navigationDeadline = window.setTimeout(() => {
                if (!assistant.pendingNavigation || assistant.navigationDone) {
                    return;
                }
                if (assistant.ttsSpeaking || assistant.microphoneBlockedByTTS) {
                    watch();            // speaking — finalizeSpeech will take it
                    return;
                }
                if (Date.now() - committedAt >= NAVIGATION_NO_SPEECH_TIMEOUT_MS) {
                    runNavigationCommitment();
                    return;
                }
                watch();                // TTS may still be on its way
            }, NAVIGATION_POLL_MS);
        };

        watch();
    }

    function runNavigationCommitment() {
        const action = assistant.pendingNavigation;

        if (!action || assistant.navigationDone) {
            return;
        }

        assistant.navigationDone = true;
        clearNavigationCommitment(true);
        performAction(action);
    }

    function clearNavigationCommitment(keepAction) {
        if (assistant.navigationDeadline) {
            clearTimeout(assistant.navigationDeadline);
            assistant.navigationDeadline = null;
        }
        clearPausedNavTimer();
        if (!keepAction) {
            assistant.pendingNavigation = null;
        }
    }

    function stopSpeaking() {
        assistant.ttsGeneration += 1;
        assistant.ttsSpeaking = false;
        assistant.ttsEndedAt = Date.now();
        assistant.microphoneBlockedByTTS = false;
        assistant.pendingAfterSpeak = null;
        setSpeakerState("idle");
        clearPausedNavTimer();
        clearAutoListenTimer();
        switchLauncherModel(LAUNCHER_MODEL_VRiyaNTS.idle);

        if (assistant.ttsAudio) {
            assistant.ttsAudio.pause();
            assistant.ttsAudio.currentTime = 0;
            assistant.ttsAudio.removeAttribute("src");
        }

        // Cancel any pending clause in the prosody chain too: speechSynthesis
        // .cancel() stops the clause being spoken, but not the timer waiting
        // to start the next one.
        if (assistant.prosodyHandle) {
            try { assistant.prosodyHandle.cancel(); } catch (e) { }
            assistant.prosodyHandle = null;
        }

        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
        }
    }

    function finalizeSpeech() {
        revealPendingCard();
        assistant.ttsSpeaking = false;
        assistant.ttsEndedAt = Date.now();
        assistant.microphoneBlockedByTTS = false;
        setSpeakerState("idle");

        const afterSpeak = assistant.pendingAfterSpeak;
        assistant.pendingAfterSpeak = null;

        switchLauncherModel(LAUNCHER_MODEL_VRiyaNTS.idle);

        // Buddy finished speaking its confirmation: go now, ahead of the
        // deadline. Unconditional — a queued navigation is a promise already
        // made out loud to the user.
        if (assistant.pendingNavigation && !assistant.navigationDone) {
            // Immediately: the sentence is finished, so there is nothing left
            // to wait for. The old 250ms pause here was just dead air.
            runNavigationCommitment();
            return;
        }

        if (typeof afterSpeak === "function") {
            // Small acoustic guard so the microphone cannot immediately
            // capture the tail of Buddy's own voice from the speakers.
            window.setTimeout(() => {
                if (
                    assistant.state !== AssistantState.CLOSED &&
                    !assistant.ttsSpeaking &&
                    !assistant.microphoneBlockedByTTS
                ) {
                    afterSpeak();
                }
            }, 350);
            return;
        }

        if (
            assistant.state !== AssistantState.CLOSED &&
            assistant.state !== AssistantState.ERROR
        ) {
            setAssistantState(AssistantState.RESPONDING);
            setStatus("Ready for your next question.");
        }
    }

    // The shared prosody engine (static/js/voice_prosody.js), when the page
    // loaded it. Looked up at call time so a missing script degrades to the
    // plain single-utterance voice instead of throwing.
    // Raw value of the chatbot's language selector ("english", "hindi", ...).
    function chatbotLanguageValue() {
        const select = document.getElementById("chatbotLanguageSelect");
        return (select && select.value) || "english";
    }

    // Two-letter language code for the prosody engine's keyword banks.
    function ttsLanguagePrefix() {
        const select = document.getElementById("chatbotLanguageSelect");
        const value = String((select && select.value) || "english").toLowerCase();
        const map = {
            english: "en", en: "en", hindi: "hi", hi: "hi",
            vietnam: "vi", vietnamese: "vi", vi: "vi",
            arabic: "ar", ar: "ar", russian: "ru", ru: "ru",
        };
        return map[value] || value.slice(0, 2);
    }

    function global_VoiceProsody() {
        return (typeof window !== "undefined" && window.VoiceProsody) || null;
    }

    // Best browser voice for one language tag. Only ever a voice that matches
    // the requested language: falling back to an English voice for
    // Hindi/Arabic/etc. sounds wrong and mangles the pronunciation.
    function pickBrowserVoice(lang) {
        const voices = window.speechSynthesis.getVoices();
        const targetPrefix = String(lang || "en-US").toLowerCase().split("-")[0];
        const languageVoices = voices.filter((voice) =>
            String(voice.lang || "").toLowerCase().startsWith(targetPrefix)
        );

        return (
            FEMALE_VOICE_HINTS.map((hint) =>
                languageVoices.find((voice) => {
                    const voiceName = String(voice.name || "").toLowerCase();
                    const voiceUri = String(voice.voiceURI || "").toLowerCase();
                    return voiceName.includes(hint) || voiceUri.includes(hint);
                })
            ).find(Boolean) ||
            languageVoices.find((voice) => !voice.localService) ||
            languageVoices[0] ||
            null
        );
    }

    function speakWithBrowser(text) {
        if (!("speechSynthesis" in window) || !text) {
            finalizeSpeech();
            return;
        }

        assistant.ttsPath = "browser";
        // cancel() of an older utterance fires its onerror/onend; only the
        // current utterance may finish speech (and so release a navigation).
        const generation = assistant.ttsGeneration;
        const finishIfCurrent = () => {
            if (generation === assistant.ttsGeneration) finalizeSpeech();
        };
        const utterance = new SpeechSynthesisUtterance(text);
        const langMap = {
            "english": "en-US",
            "en": "en-US",
            "hindi": "hi-IN",
            "hi": "hi-IN",
            "vietnam": "vi-VN",
            "vietnamese": "vi-VN",
            "arabic": "ar-SA",
            "ar": "ar-SA",
            "russian": "ru-RU",
            "ru": "ru-RU"
        };
        const currentLang = document.getElementById('chatbotLanguageSelect') ? document.getElementById('chatbotLanguageSelect').value : 'english';
        utterance.lang = langMap[currentLang] || "en-US";

        assistant.speechUtterance = utterance;
        assistant.speechText = text;
        utterance.rate = Riya_BROWSER_VOICE_RATE;
        utterance.pitch = Riya_BROWSER_VOICE_PITCH;
        // Track how far speech has progressed so a mid-reply navigation can
        // resume from the stop point instead of restarting.
        utterance.onboundary = (event) => {
            if (typeof event.charIndex === "number") {
                assistant.speechCharIndex = event.charIndex;
            }
        };
        utterance.onend = finishIfCurrent;
        utterance.onerror = finishIfCurrent;

        const speak = () => {
            revealPendingCard();
            // One flat utterance for a whole reply is what makes the browser
            // voice sound robotic. VoiceProsody speaks it clause by clause,
            // bending pitch and pace around each punctuation mark and tinting
            // the whole reply happy or sad (see static/js/voice_prosody.js).
            // The single-utterance path below stays as the fallback for a
            // browser where the module did not load.
            if (global_VoiceProsody()) {
                const voice = pickBrowserVoice(utterance.lang);
                if (voice) utterance.voice = voice;
                window.speechSynthesis.onvoiceschanged = null;
                window.speechSynthesis.cancel();
                assistant.prosodyHandle = global_VoiceProsody().speak(text, {
                    lang: utterance.lang,
                    voice: voice || null,
                    pitch: Riya_BROWSER_VOICE_PITCH,
                    rate: Riya_BROWSER_VOICE_RATE,
                    volume: 1,
                    language: String(utterance.lang || "en").slice(0, 2),
                }, {
                    onboundary: (charIndex) => { assistant.speechCharIndex = charIndex; },
                    onend: finishIfCurrent,
                });
                return;
            }
            speakFlat();
        };

        const speakFlat = () => {
            const preferredLanguageVoice = pickBrowserVoice(utterance.lang);
            if (preferredLanguageVoice) {
                utterance.voice = preferredLanguageVoice;
            }

            window.speechSynthesis.onvoiceschanged = null;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        };

        if (window.speechSynthesis.getVoices().length > 0) {
            speak();
        } else {
            window.speechSynthesis.onvoiceschanged = () => speak();
            // Safety net, not a behavior change: on a normal browser with
            // system voices installed, onvoiceschanged fires almost
            // immediately and this timer is cleared/made a no-op by the
            // generation check below. It only matters when the voice list
            // never loads at all (confirmed case: headless browsers with
            // zero installed voices) -- without it, ttsSpeaking stays true
            // forever and commitNavigation()'s pending navigation never
            // fires, silently stranding the user on the current page.
            setTimeout(() => {
                if (generation === assistant.ttsGeneration && assistant.ttsSpeaking) {
                    finishIfCurrent();
                }
            }, 1500);
        }
    }

    function speakText(text, options = {}) {
        if (!text) {
            return;
        }

        // Enforce half-duplex audio: stop microphone capture BEFORE
        // starting any TTS. Buddy must never hear its own response.
        stopListeningForSpeechOutput();
        stopSpeaking();

        // Reset resume tracking for this new utterance.
        assistant.speechText = text;
        assistant.speechCharIndex = 0;

        assistant.ttsSpeaking = true;
        assistant.microphoneBlockedByTTS = true;
        assistant.ttsGeneration += 1;
        setMicIndicatorVisible(false);

        // Fallback to the browser voice ONLY for this utterance. When a newer
        // reply replaces the audio source (tapping a card while the greeting
        // is still loading), the old play() rejects with AbortError; its catch
        // used to speak the OLD line in the browser voice, which "finished" at
        // once and fired the pending navigation before the new reply was heard.
        const generation = assistant.ttsGeneration;
        const fallbackToBrowser = () => {
            if (generation === assistant.ttsGeneration) {
                speakWithBrowser(text);
            }
        };

        switchLauncherModel(LAUNCHER_MODEL_VRiyaNTS.speaking);
        assistant.pendingAfterSpeak = options.afterSpeak || null;
        setAssistantState(options.state || AssistantState.RESPONDING);
        setStatus(options.statusText || "Buddy is speaking.");

        // The neural voice (Sarvam bulbul) is what makes Buddy sound like a
        // person; the browser's speechSynthesis is the robot. When the reply
        // already carries neural audio it is ALWAYS used — instantBrowserVoice
        // used to be checked first and returned early, so every reply that had
        // perfectly good neural audio attached was still read by the robot.
        if (options.audioBase64) {
            assistant.ttsPath = "audio";
            assistant.ttsAudio.src = `data:audio/wav;base64,${options.audioBase64}`;
            assistant.ttsAudio.onended = finalizeSpeech;
            assistant.ttsAudio.onerror = fallbackToBrowser;
            assistant.ttsAudio.play().catch(fallbackToBrowser);
            return;
        }

        // No neural audio attached: stream it. The batch endpoint only
        // answers once the WHOLE reply is synthesised (1.8s for a sentence,
        // 4s+ for a paragraph) - that was the silence after the text had
        // already appeared. The streaming endpoint starts sending audio in
        // ~0.5s whatever the length, and <audio> plays it as it arrives, so
        // Buddy begins talking while the rest is still being made.
        //
        // `instantBrowserVoice` now means "do not wait on the network at all"
        // and applies only where speed beats voice quality.
        // Any language the server cannot voice goes straight to the browser
        // voice instead of waiting on an empty clip.
        if (!NEURAL_TTS_LANGS.has(chatbotLanguageValue()) && canUseBrowserSpeech()) {
            speakWithBrowser(text);
            return;
        }

        if (options.instantBrowserVoice && options.preferBrowserVoice && canUseBrowserSpeech()) {
            speakWithBrowser(text);
            return;
        }

        // ONE request for the whole reply. It used to be split so the short
        // opening sentence could start sooner, but two synthesis calls are two
        // independent renders: the model's own variation means the second
        // chunk does not match the first, and Buddy audibly changed voice
        // between "Opening the activities page." and the sentence after it.
        // The streaming endpoint returns first audio in about half a second
        // whatever the length, so there is nothing left to gain from cutting
        // the reply up.
        assistant.ttsPath = "audio";
        assistant.ttsAudio.src = ttsStreamUrl(text, text);
        assistant.ttsAudio.onended = finalizeSpeech;
        assistant.ttsAudio.onerror = () => {
            console.warn("[Buddy] neural TTS failed, using browser voice");
            fallbackToBrowser();
        };
        assistant.ttsAudio.play().catch(fallbackToBrowser);
    }

    // Languages the server voices: Sarvam bulbul for English/Hindi, Google's
    // female voices for Vietnamese, Arabic and Russian.
    const NEURAL_TTS_LANGS = new Set(["english", "hindi", "vietnam", "arabic", "russian"]);

    // Streaming-TTS URL for one reply.
    function ttsStreamUrl(chunk, whole) {
        return "/api/voice/tts/stream/?" + new URLSearchParams({
            text: chunk.slice(0, 500),
            language: chatbotLanguageValue(),
            emotion: global_VoiceProsody()
                ? global_VoiceProsody().detectEmotion(whole || chunk, ttsLanguagePrefix())
                : "neutral",
        }).toString();
    }

    function speakBotText(text) {
        if (!text) {
            return;
        }
        speakText(text, { state: AssistantState.RESPONDING });
    }

    // ============================================================
    // HEADER SPEAKER CONTROL  (pause / resume AI speech — speech only)
    //
    // One button toggles the CURRENT narration between playing and paused
    // using the NATIVE controls of whichever engine is live, so resume
    // continues from the exact paused position (never cancel + restart):
    //   - server TTS -> HTMLAudioElement.pause() / play()
    //   - browser    -> speechSynthesis.pause() / resume()
    // It controls speech ONLY — it never navigates.
    // ============================================================

    // state: "idle" | "speaking" | "paused"
    function setSpeakerState(state) {
        assistant.speakerMode = state;
        const btn = assistant.speakerButton;
        if (!btn) return;
        btn.dataset.state = state;
        if (state === "speaking") {
            btn.setAttribute("aria-label", "Pause AI speech");
            btn.setAttribute("title", "Pause AI speech");
        } else if (state === "paused") {
            btn.setAttribute("aria-label", "Resume AI speech");
            btn.setAttribute("title", "Resume AI speech");
        } else {
            btn.setAttribute("aria-label", "AI narration");
            btn.setAttribute("title", "AI narration");
        }
    }

    // If a navigation is queued behind the reply and the user PAUSES, don't
    // hold the move forever — go after this many ms of pause, and continue the
    // narration on the destination page.
    const PAUSE_NAV_DELAY_MS = 5000;

    function clearPausedNavTimer() {
        if (assistant.pausedNavTimer) {
            clearTimeout(assistant.pausedNavTimer);
            assistant.pausedNavTimer = null;
        }
    }

    function pauseCurrentSpeech() {
        if (assistant.ttsPath === "audio" && assistant.ttsAudio) {
            assistant.ttsAudio.pause();
        } else if ("speechSynthesis" in window) {
            try { window.speechSynthesis.pause(); } catch (e) { }
        }
        setSpeakerState("paused");

        // Paused with a queued navigation: navigate after 5s of pause instead
        // of waiting for the user to resume. performAction() stashes the reply
        // (ttsSpeaking is still true while paused) so speech continues on the
        // destination page.
        clearPausedNavTimer();
        if (assistant.pendingNavigation && !assistant.navigationDone) {
            assistant.pausedNavTimer = window.setTimeout(() => {
                assistant.pausedNavTimer = null;
                runNavigationCommitment();
            }, PAUSE_NAV_DELAY_MS);
        }
    }

    function resumeCurrentSpeech() {
        // User resumed within the window: cancel the pause-triggered move; the
        // reply will finish and navigate normally on speech end.
        clearPausedNavTimer();
        if (assistant.ttsPath === "audio" && assistant.ttsAudio) {
            assistant.ttsAudio.play().catch(() => { });
        } else if ("speechSynthesis" in window) {
            try { window.speechSynthesis.resume(); } catch (e) { }
        }
        setSpeakerState("speaking");
    }

    // Single guarded handler — rapid clicks only ever toggle the current
    // session, never spawn a new utterance.
    function onSpeakerButtonClick() {
        if (assistant.speakerMode === "speaking") {
            pauseCurrentSpeech();
        } else if (assistant.speakerMode === "paused") {
            resumeCurrentSpeech();
        } else if (assistant.lastResponseText) {
            // Idle: replay the latest response from the start.
            speakText(assistant.lastResponseText, {
                state: AssistantState.RESPONDING,
            });
            setSpeakerState("speaking");
        }
    }

    // ============================================================
    // SPEECH SURVIVES NAVIGATION  (resume-after-reload)
    //
    // This is a multi-page app: a real page load destroys any in-flight
    // utterance. When narration is cut short by a move, we stash the reply and
    // the destination page picks it up so Buddy keeps talking after the load.
    // (Continues from the start of the reply on the new page — the browser
    // exposes no exact resume offset across a document unload.)
    // ============================================================
    const PENDING_SPEECH_KEY = "riya_pending_speech";
    const PENDING_SPEECH_TTL_MS = 30000;

    function stashPendingSpeech(text) {
        try {
            if (!text) return;
            sessionStorage.setItem(PENDING_SPEECH_KEY, JSON.stringify({
                text: text,
                ts: Date.now(),
            }));
        } catch (e) { }
    }

    function resumePendingSpeech() {
        let stash = null;
        try {
            const raw = sessionStorage.getItem(PENDING_SPEECH_KEY);
            if (!raw) return;
            sessionStorage.removeItem(PENDING_SPEECH_KEY);
            stash = JSON.parse(raw);
        } catch (e) { return; }
        if (!stash || !stash.text) return;
        if (Date.now() - (stash.ts || 0) > PENDING_SPEECH_TTL_MS) return;

        // Let the page + voice list settle, open the panel, then speak.
        window.setTimeout(() => {
            if (assistant.state === AssistantState.CLOSED) {
                openChat();
            }
            speakText(stash.text, {
                state: AssistantState.RESPONDING,
            });
            setSpeakerState("speaking");

            // Stuck-state guard: if autoplay is blocked, the engine never fires
            // onstart/onend, which would leave ttsSpeaking stuck true and
            // dead-lock the microphone. If speech has not actually begun
            // shortly after, reset to idle.
            window.setTimeout(() => {
                const reallySpeaking =
                    ("speechSynthesis" in window &&
                        (window.speechSynthesis.speaking || window.speechSynthesis.pending)) ||
                    (assistant.ttsAudio && !assistant.ttsAudio.paused);
                if (assistant.ttsSpeaking && !reallySpeaking) {
                    finalizeSpeech();
                }
            }, 1800);
        }, 700);
    }

    function showError(message) {
        renderPayload(buildFallbackPayload(), {
            asError: true,
            statusText: message,
        });
    }

    function requestAssistantReplyStream(message, inputMode) {
        // Returns a Promise that resolves when the stream is fully consumed.
        // Calls renderPayload / renderResponseCard progressively while tokens arrive.
        setAssistantState(AssistantState.PROCESSING);
        setStatus("Buddy is thinking.");
        renderResponseCard({ reply: uiText().thinking }, { vRiyant: "thinking" });

        return fetch("/api/riya/chat/stream/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
                message,
                page: assistant.root?.dataset.riyaPage || "unknown",
                path: assistant.root?.dataset.riyaPath || window.location.pathname,
                // Skill Up routes lessons via the URL hash
                // (#load=<file>&title=<title>). Sending it lets Buddy answer
                // "what is this page about?" against the lesson actually open.
                hash: window.location.hash || "",
                input_mode: inputMode,
                language: document.getElementById('chatbotLanguageSelect')
                    ? document.getElementById('chatbotLanguageSelect').value
                    : 'english',

                // Role separation for the backend.
                is_employer: assistant.isEmployer,
                assistant_role: getAssistantRole(),
                role_context: getRoleContext().description,

                // Keep the same conversation ID across page navigation.
                conversation_id: ensureConversationId(),

                // Prior turns for API views that support conversational history.
                history: assistant.conversationHistory.map((item) => ({
                    role: item.role,
                    content: item.content,
                })),
            }),
        }).then(async (response) => {
            if (!response.ok || !response.body) {
                // Server error — fall back to non-streaming endpoint
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || "Stream unavailable");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let streamedTokens = "";
            let accumulatedMessage = "";

            // Clear the "Thinking…" card and show an empty one to fill in
            if (assistant.responseSlot) {
                // Remove only temporary cards.
                // DO NOT clear the conversation history.
                // The typing dots stay up and the streamed text is kept hidden:
                // the finished reply is revealed together with its voice.
                const oldStream =
                    assistant.responseSlot.querySelector("#riya-stream-card");

                if (oldStream) {
                    oldStream.remove();
                }

                const liveCard = document.createElement("div");

                liveCard.className =
                    "riya-response-card is-entering";

                liveCard.id = "riya-stream-card";
                liveCard.hidden = true;

                const liveP = document.createElement("p");

                liveP.id = "riya-stream-text";

                liveCard.appendChild(liveP);

                assistant.responseSlot.appendChild(liveCard);

                assistant.responseSlot.scrollTop =
                    assistant.responseSlot.scrollHeight;
            }

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed.startsWith("data: ")) continue;
                    const data = trimmed.slice(6).trim();
                    if (data === "[DONE]") return;

                    let parsed;
                    try { parsed = JSON.parse(data); } catch { continue; }

                    // Streaming token from AI
                    if (parsed.t !== undefined) {
                        accumulatedMessage += parsed.t;
                        // Check for <LANG:code> intercept
                        const langMatch = accumulatedMessage.match(/<LANG:([^>]+)>/);
                        if (langMatch) {
                            const newLang = langMatch[1];
                            const ls = document.getElementById('chatbotLanguageSelect');
                            if (ls) {
                                ls.value = newLang;
                                sessionStorage.setItem('riya_chatbot_lang', newLang);
                                if (window.applyGlobalTranslations) {
                                    window.applyGlobalTranslations(newLang);
                                }
                            }
                            accumulatedMessage = accumulatedMessage.replace(/<LANG:[^>]+>/g, '').trim();
                        }
                        streamedTokens = accumulatedMessage;
                        const liveP = document.getElementById("riya-stream-text");
                        if (liveP) liveP.textContent = streamedTokens;
                        assistant.lastResponseText = streamedTokens;
                        // Don't write sessionStorage for every streamed token.
                        // It can make the UI sluggish during fast streaming.
                        if (!assistant.streamPersistTimer) {
                            assistant.streamPersistTimer = window.setTimeout(() => {
                                assistant.streamPersistTimer = null;

                                persistAssistantSession({
                                    isOpen: true,
                                    lastResponseText: assistant.lastResponseText,
                                });
                            }, 250);
                        }
                        setAssistantState(AssistantState.RESPONDING);
                        setStatus("Buddy is responding.");
                    }

                    // Final complete event (fast-path OR AI done)
                    if (parsed.reply !== undefined || parsed.done) {
                        if (parsed.is_unknown_command) {
                            alert("This feature is not available in the application.");
                        }
                        const finalText = parsed.reply || streamedTokens;
                        const actions = parsed.actions || buildFallbackPayload().actions;

                        if (finalText) {
                            addConversationMessage("assistant", finalText);
                        }

                        // A single action with a route means "open this".
                        // Skill Up replies carry source "skillup"; the old test
                        // only accepted "intent", so Skill Up spoke "Opening …"
                        // but never committed the move. Multiple actions mean
                        // "choose one" (an ambiguous or list reply) and must NOT
                        // auto-navigate — the length guard keeps that intact.
                        const isNavigationIntent =
                            (parsed.source === "intent" ||
                                parsed.source === "skillup") &&
                            Array.isArray(actions) &&
                            actions.length === 1 &&
                            actions[0].route;

                        // Wait for the COMPLETE utterance before moving, but
                        // commit to the move now: if TTS fails or a later turn
                        // interrupts it, the deadline still takes the user
                        // where Buddy just said it would take them.
                        if (isNavigationIntent) {
                            commitNavigation({
                                key: actions[0].key,
                                route: actions[0].route,
                            });
                        }

                        renderPayload(
                            { reply: finalText, actions, source: parsed.source || "ai" },
                            {
                                speak: true,
                                afterSpeak: null,
                                autoResumeListening: false,
                            }
                        );

                        /* Navigation now flows through afterSpeak: Riya speaks the confirmation first, then navigates (voice output for every response, including typed). */
                        return;
                    }
                }
            }

            // Reader exhausted without explicit done — use accumulated tokens
            if (streamedTokens) {
                renderPayload(
                    { reply: streamedTokens, actions: buildFallbackPayload().actions, source: "ai" },
                    {
                        speak: true,
                        autoResumeListening: false
                    }
                );
            }
        });
    }

    // Return the COMPLETE navigation sentence in the language selected by the user.
    // Do not speak the English action.response for non-English sessions: doing that
    // makes browser TTS switch pronunciation/language mid-sentence and can sound
    // like it is cutting words (for example: "group disc...").
    function getSelectedAssistantLanguage() {
        const select = document.getElementById("chatbotLanguageSelect");
        return select ? String(select.value || "english").toLowerCase() : "english";
    }

    // ============================================================
    // GUIDED NAVIGATION
    //
    // "Opening the grammar section." is accurate but it is a dead end — it
    // tells the user nothing about what is waiting for them or what they can
    // ask next. Buddy now follows a move with the choices that live at the
    // destination, so a single request opens a conversation instead of
    // closing one.
    //
    // The child lists are keys into ACTION_DEFINITIONS rather than prose, so
    // the labels stay correct automatically as the platform changes and no
    // second list of module names has to be kept in step.
    // ============================================================
    const NAVIGATION_CHILDREN = {
        grammar: [
            "grammar_noun", "grammar_pronoun", "grammar_verb",
            "grammar_adjective", "grammar_adverb", "grammar_conjunction",
            "grammar_tenses", "grammar_sentence_structure",
            "grammar_types_of_sentences",
        ],
        lessons: [
            "professional_speaking", "passage_writing", "vocabulary",
            "negotiation", "communication", "analysis",
        ],
        roleplay: ["storytelling_practice", "situation_practice"],
        english_vocab: [],
        profile: ["lessons", "grammar", "resume_builder"],
        resume_builder: ["mock_interview", "job_search"],
    };

    // Translated section names, rendered into the page by aria_assistant.html
    // from riya_bot/section_names.py (backend keys use "vietnamese").
    let SECTION_NAMES = null;
    function sectionName(key, lang) {
        if (!lang || lang === "english") return "";
        if (SECTION_NAMES === null) {
            try {
                SECTION_NAMES = JSON.parse(document.getElementById("riya-section-names").textContent);
            } catch (_error) {
                SECTION_NAMES = {};
            }
        }
        return SECTION_NAMES[key]?.[lang === "vietnam" ? "vietnamese" : lang] || "";
    }

    const OPENING_FRAMES = {
        english: (name) => `Opening ${name}.`,
        hindi: (name) => `${name} खोल रहा हूँ।`,
        vietnam: (name) => `Đang mở ${name}.`,
        arabic: (name) => `جارٍ فتح ${name}.`,
        russian: (name) => `Открываю ${name}.`,
    };

    const GUIDANCE_TEMPLATES = {
        english: (list) =>
            `Inside you'll find ${list}. Tell me which one you'd like and I'll take you straight there.`,
        hindi: (list) =>
            `अंदर आपको ${list} मिलेंगे। बताइए कौन-सा खोलूँ, मैं सीधे वहीं ले चलता हूँ।`,
        vietnam: (list) =>
            `Bên trong có ${list}. Hãy cho tôi biết bạn muốn phần nào, tôi sẽ mở ngay.`,
        arabic: (list) =>
            `في الداخل ستجد ${list}. أخبرني أيها تريد وسأنقلك إليه مباشرة.`,
        russian: (list) =>
            `Внутри вы найдёте ${list}. Скажите, что открыть, и я сразу вас туда переведу.`,
    };

    const LIST_CONJUNCTION = {
        english: "and",
        hindi: "और",
        vietnam: "và",
        arabic: "و",
        russian: "и",
    };

    function joinLabels(labels, lang) {
        if (labels.length === 1) {
            return labels[0];
        }
        const conjunction = LIST_CONJUNCTION[lang] || LIST_CONJUNCTION.english;
        return `${labels.slice(0, -1).join(", ")} ${conjunction} ${labels[labels.length - 1]}`;
    }

    /**
     * The confirmation plus, where it helps, what the user can do next.
     * Falls back to the plain confirmation whenever there is nothing useful
     * to add — padding every reply would be worse than saying less.
     */
    function buildGuidedNavigationReply(action) {
        const base = getLocalizedActionResponse(action);
        const key = String(action?.key || "").trim();
        const children = NAVIGATION_CHILDREN[key];
        const lang = getSelectedAssistantLanguage();

        if (!children || !children.length) {
            return base;
        }

        const labels = children
            .filter((childKey) => isActionAllowedForCurrentRole(childKey))
            .map((childKey) => sectionName(childKey, lang) || ACTION_DEFINITIONS[childKey]?.label)
            .filter(Boolean)
            .slice(0, 5);

        if (labels.length < 2) {
            return base;
        }

        const template =
            GUIDANCE_TEMPLATES[lang] || GUIDANCE_TEMPLATES.english;

        return `${base} ${template(joinLabels(labels, lang))}`;
    }

    function getLocalizedActionResponse(action) {
        const lang = getSelectedAssistantLanguage();
        const key = String(action?.key || "").trim();
        const label = String(action?.label || "that page");

        const responses = {
            english: {
                mock_interview:
                    "Taking you to the Resume Builder for your AI Mock Interview.",
                resume_builder:
                    "Opening the Resume Builder.",
                aptitude:
                    "Taking you to the Aptitude section.",
                tech:
                    "Taking you to the Tech section.",
                grammar:
                    "Opening the Grammar section.",
                profile:
                    "Opening your dashboard.",
            },

            hindi: {
                mock_interview:
                    "आपको AI Mock Interview के लिए Resume Builder पर ले जा रहा हूँ।",
                resume_builder:
                    "आपको Resume Builder पर ले जा रहा हूँ।",
                aptitude:
                    "आपको Aptitude सेक्शन में ले जा रहा हूँ।",
                tech:
                    "आपको Tech सेक्शन में ले जा रहा हूँ।",
                grammar:
                    "आपको Grammar सेक्शन में ले जा रहा हूँ।",
                profile:
                    "आपका Dashboard खोल रहा हूँ।",
            },

            vietnam: {
                mock_interview:
                    "Đang đưa bạn đến Resume Builder cho AI Mock Interview.",
                resume_builder:
                    "Đang mở Resume Builder.",
                aptitude:
                    "Đang đưa bạn đến phần Aptitude.",
                tech:
                    "Đang đưa bạn đến phần Tech.",
                grammar:
                    "Đang mở phần Grammar.",
                profile:
                    "Đang mở Dashboard của bạn.",
            },

            arabic: {
                mock_interview:
                    "سأنقلك إلى Resume Builder لإجراء AI Mock Interview.",
                resume_builder:
                    "جارٍ فتح Resume Builder.",
                aptitude:
                    "سأنقلك إلى قسم Aptitude.",
                tech:
                    "سأنقلك إلى قسم Tech.",
                grammar:
                    "جارٍ فتح قسم Grammar.",
                profile:
                    "جارٍ فتح لوحة التحكم الخاصة بك.",
            },

            russian: {
                mock_interview:
                    "Перевожу вас в Resume Builder для AI Mock Interview.",
                resume_builder:
                    "Открываю Resume Builder.",
                aptitude:
                    "Перевожу вас в раздел Aptitude.",
                tech:
                    "Перевожу вас в раздел Tech.",
                grammar:
                    "Открываю раздел Grammar.",
                profile:
                    "Открываю вашу панель управления.",
            }
        };

        // Exact action-specific response first.
        const localized =
            responses[lang]?.[key];

        if (localized) {
            return localized;
        }

        // Translated section name, shared with the backend
        // (riya_bot/section_names.py) — "Đang mở chứng chỉ của bạn." rather
        // than "Đang mở Certifications.".
        const name = sectionName(key, lang);
        if (name) {
            return OPENING_FRAMES[lang](name);
        }

        // Existing generic localization for all other actions.
        const labels = {
            english: {
                Home: "home",
                "Go to Activities": "the activities page",
                "Speaking & Presentation": "speaking and presentation",
                "Writing and Correspondence": "writing and correspondence",
                "Vocabulary & Idioms": "vocabulary and idioms",
                "Negotiation & Meetings": "negotiation and meetings",
                "Professional Communication": "professional communication",
                "Analysis & Reporting": "analysis and reporting",
                "View Dashboard": "your dashboard",
                "Job Seeker Sign-In": "the job seeker sign-in page",
                "Employer Login": "the employer portal",
                Grammar: "the grammar section",
                "Resume Builder": "resume builder",
                Membership: "membership plans",
                "AI Mock Interview": "AI Mock Interview"
            },

            hindi: {
                Home: "होम पेज",
                "Go to Activities": "एक्टिविटी पेज",
                "Speaking & Presentation": "प्रोफेशनल स्पीकिंग",
                "Writing and Correspondence": "राइटिंग और कॉरेस्पॉन्डेंस",
                "Vocabulary & Idioms": "वोकैबुलरी और इडियम्स",
                "Negotiation & Meetings": "नेगोशिएशन और मीटिंग्स",
                "Professional Communication": "प्रोफेशनल कम्युनिकेशन",
                "Analysis & Reporting": "एनालिसिस और रिपोर्टिंग",
                "View Dashboard": "आपका डैशबोर्ड",
                "Job Seeker Sign-In": "स्टूडेंट लॉगिन पेज",
                "Employer Login": "एम्प्लॉयर पोर्टल",
                Grammar: "ग्रामर सेक्शन",
                "Resume Builder": "Resume Builder",
                Membership: "मेंबरशिप प्लान्स",
                "AI Mock Interview": "AI Mock Interview"
            },

            vietnam: {
                Home: "trang chủ",
                "Go to Activities": "trang hoạt động",
                "Speaking & Presentation": "luyện nói chuyên nghiệp",
                "Writing and Correspondence": "viết và giao tiếp thư từ",
                "Vocabulary & Idioms": "từ vựng và thành ngữ",
                "Negotiation & Meetings": "đàm phán và cuộc họp",
                "Professional Communication": "giao tiếp chuyên nghiệp",
                "Analysis & Reporting": "phân tích và báo cáo",
                "View Dashboard": "bảng điều khiển của bạn",
                "Job Seeker Sign-In": "trang đăng nhập học viên",
                "Employer Login": "cổng thông tin nhà tuyển dụng",
                Grammar: "phần ngữ pháp",
                "Resume Builder": "Resume Builder",
                Membership: "các gói thành viên",
                "AI Mock Interview": "AI Mock Interview"
            },

            arabic: {
                Home: "الصفحة الرئيسية",
                "Go to Activities": "صفحة الأنشطة",
                "Speaking & Presentation": "التحدث المهني",
                "Writing and Correspondence": "الكتابة والمراسلات",
                "Vocabulary & Idioms": "المفردات والتعابير",
                "Negotiation & Meetings": "التفاوض والاجتماعات",
                "Professional Communication": "التواصل المهني",
                "Analysis & Reporting": "التحليل وإعداد التقارير",
                "View Dashboard": "لوحة التحكم الخاصة بك",
                "Job Seeker Sign-In": "صفحة تسجيل دخول الطالب",
                "Employer Login": "بوابة صاحب العمل",
                Grammar: "قسم القواعد",
                "Resume Builder": "Resume Builder",
                Membership: "خطط العضوية",
                "AI Mock Interview": "AI Mock Interview"
            },

            russian: {
                Home: "главную страницу",
                "Go to Activities": "страницу занятий",
                "Speaking & Presentation": "профессиональную речь",
                "Writing and Correspondence": "письмо и деловую переписку",
                "Vocabulary & Idioms": "лексику и идиомы",
                "Negotiation & Meetings": "переговоры и встречи",
                "Professional Communication": "профессиональное общение",
                "Analysis & Reporting": "анализ и отчётность",
                "View Dashboard": "вашу панель управления",
                "Job Seeker Sign-In": "страницу входа для студента",
                "Employer Login": "портал работодателя",
                Grammar: "раздел грамматики",
                "Resume Builder": "Resume Builder",
                Membership: "тарифы подписки",
                "AI Mock Interview": "AI Mock Interview"
            }
        };

        const translated = labels[lang]?.[label];

        if (translated) {
            if (lang === "hindi") {
                return `खोल रहा हूँ ${translated}।`;
            }

            if (lang === "arabic") {
                return `جارٍ فتح ${translated}.`;
            }

            if (lang === "russian") {
                return `Открываю ${translated}.`;
            }

            if (lang === "vietnam") {
                return `Đang mở ${translated}.`;
            }

            return `Opening ${translated}.`;
        }

        // Fallback for labels not in the map above. Previously returned the
        // English action.response (e.g. "Opening Professional Reading.") even in
        // a Hindi session — the mixed-language reply the user reported. Build the
        // confirmation in the selected language instead, keeping the (English)
        // section name as a proper noun. Navigation itself is unaffected.
        if (lang === "hindi") return `${label} खोल रहा हूँ।`;
        if (lang === "arabic") return `جارٍ فتح ${label}.`;
        if (lang === "russian") return `Открываю ${label}.`;
        if (lang === "vietnam") return `Đang mở ${label}.`;
        return action?.response || `Opening ${label}.`;
    }

    function detectGuestRole(text) {
        const normalized = normalizeText(text);

        if (!normalized) {
            return null;
        }

        // ------------------------------------------------------------
        // Employer / Recruiter — English + supported languages
        // ------------------------------------------------------------
        const employerPatterns = [
            // English
            /\b(employer|employeer|recruiter|recruitment|company|hiring|hire candidates|hire people|business owner|employee)\b/i,

            // Vietnamese
            /\b(nhà tuyển dụng|nha tuyen dung|tuyển dụng|tuyen dung|doanh nghiệp|doanh nghiep)\b/i,

            // Hindi — include the anusvara spelling एंप्लॉयर (एं) alongside एम्प्लॉयर
            // (म्); users type both, and only the latter matched before, so a reply
            // of "एंप्लॉयर" / "माय एंप्लॉयर हूँ" fell through and the role prompt looped.
            /(एंप्लॉयर|एम्प्लॉयर|एंप्लायर|एम्प्लायर|नियोक्ता|भर्ती|कंपनी|रिक्रूटर|नियुक्ति)/u,

            // Arabic
            /(صاحب عمل|صاحب العمل|جهة توظيف|موظف توظيف|توظيف|شركة)/u,

            // Russian
            /(работодатель|рекрутер|рекрутинг|найм|нанимаю|компания)/u,
        ];

        if (employerPatterns.some((pattern) => pattern.test(normalized))) {
            return "employer";
        }

        // ------------------------------------------------------------
        // Student / Job Seeker — English + supported languages
        // ------------------------------------------------------------
        const studentPatterns = [
            // English
            /\b(student|job seeker|jobseeker|job sikar|job seekar|candidate|looking for job|looking for a job|find a job|find jobs)\b/i,

            // Vietnamese
            /\b(sinh viên|sinh vien|người tìm việc|nguoi tim viec|tìm việc|tim viec|ứng viên|ung vien)\b/i,

            // Hindi
            /(छात्र|स्टूडेंट|जॉब सीकर|नौकरी खोजने वाला|नौकरी ढूंढ|नौकरी चाहिए|उम्मीदवार|कैंडिडेट)/u,

            // Arabic
            /(طالب|طالبة|باحث عن عمل|باحثة عن عمل|أبحث عن عمل|البحث عن عمل|مرشح|مرشحة)/u,

            // Russian
            /(студент|студентка|соискатель|ищу работу|поиск работы|кандидат)/u,
        ];

        if (studentPatterns.some((pattern) => pattern.test(normalized))) {
            return "student";
        }

        return null;
    }

    function detectSiteNavigationIntent(text) {
        if (assistant.isEmployer) return null;

        const normalizedInput = normalizeText(text);
        if (!normalizedInput) return null;

        const isWhereIs = /^(where is|where are|how do i find|show me where|where can i find|what is in)\b/i.test(normalizedInput);
        const hasVerb = hasNavigationVerb(normalizedInput);

        if (!isWhereIs && !hasVerb) return null;

        const siteLinks = [];

        document.querySelectorAll('a').forEach(a => {
            let label = (a.textContent || "").replace(/\s+/g, " ").trim();
            const href = a.getAttribute("href");
            if (label && href && !href.startsWith("javascript:") && href !== "#") {
                let location = "the page";
                const parentNav = a.closest('.cb-nav');
                const parentFooter = a.closest('footer') || a.closest('.footer') || a.closest('#contact');
                const parentMega = a.closest('.mega');
                
                if (parentMega) {
                    const toggle = parentMega.previousElementSibling;
                    if (toggle) location = "the " + toggle.textContent.trim() + " dropdown in the navigation bar";
                    else location = "the navigation dropdown";
                } else if (parentNav) {
                    location = "the top navigation bar";
                } else if (parentFooter) {
                    location = "the footer";
                } else if (a.closest('.cbn-header')) {
                    location = "the header";
                }

                const cleanLabel = label.replace(/[&]/g, "and");
                
                siteLinks.push({
                    label: label,
                    route: href,
                    normalizedLabel: normalizeText(cleanLabel),
                    location: location
                });
            }
        });

        Object.keys(ACTION_DEFINITIONS).forEach(key => {
            const def = ACTION_DEFINITIONS[key];
            
            siteLinks.push({
                key: key,
                label: def.label,
                route: def.route,
                normalizedLabel: normalizeText(def.label),
                location: "the site",
                keywords: (def.keywords || []).map(normalizeText)
            });
        });

        siteLinks.push({ label: "Privacy Policy", route: "/#", normalizedLabel: "privacy policy", location: "the footer", keywords: ["privacy"] });
        siteLinks.push({ label: "Terms and Conditions", route: "/#", normalizedLabel: "terms and conditions", location: "the footer", keywords: ["terms"] });

        let bestMatch = null;
        let bestScore = 0;

        const inputTokens = normalizedInput.split(/\s+/).filter(Boolean);

        siteLinks.forEach(link => {
            if (!link.normalizedLabel) return;
            let score = 0;
            
            if (normalizedInput.includes(link.normalizedLabel)) {
                score += 15;
            } else if (link.keywords) {
                link.keywords.forEach(kw => {
                    if (normalizedInput.includes(kw)) {
                        score += 15;
                    } else {
                        const kwTokens = kw.split(/\s+/).filter(Boolean);
                        let matches = 0;
                        kwTokens.forEach(kt => {
                            if (inputTokens.includes(kt)) matches++;
                        });
                        if (matches === kwTokens.length && kwTokens.length > 0) score += 10;
                    }
                });
            }

            const linkTokens = link.normalizedLabel.split(/\s+/).filter(Boolean);
            let matches = 0;
            linkTokens.forEach(lt => {
                if (inputTokens.includes(lt)) matches++;
            });
            if (matches === linkTokens.length && linkTokens.length > 0) score += 8;
            else if (matches > 0) score += matches;

            if (score > bestScore && score >= 5) {
                bestScore = score;
                bestMatch = link;
            } else if (score === bestScore && score >= 5 && link.location !== "the site") {
                bestMatch = link;
            }
        });

        if (bestMatch) {
            let replyText = "";
            let autoNavigate = false;

            const authPaths = ["/dashboard", "/users/profile", "/activities", "/go/resume-builder", "/resume-builder", "/go/activities", "/employer"];
            const requiresJobSeekerAuth = authPaths.some(p => bestMatch.route && bestMatch.route.startsWith(p));
            const isLoginRoute = ["/users/login/", "/users/register/", "/employer/accounts/employer/login/", "/employer/accounts/employer/register/"].includes(bestMatch.route);
            
            if (requiresJobSeekerAuth && !isLoginRoute && getAssistantRole() === "guest" && !assistant.isEmployer) {
                replyText = "That page requires you to log in.";
                return {
                    reply: replyText,
                    source: "site_navigation",
                    autoNavigate: false,
                    navigation: [{ label: "Log In", route: "/users/login/" }]
                };
            }

            if (hasVerb && (bestMatch.key === "aptitude" || bestMatch.key === "tech" || bestMatch.key === "non_it" || bestMatch.key === "certifications")) {
                // Must be resolved by the backend to enforce Pro plan locks on opening
                return null;
            }

            if (isWhereIs) {
                replyText = `${bestMatch.label} is available in ${bestMatch.location}.`;
                autoNavigate = false;
            } else if (hasVerb) {
                replyText = `Opening ${bestMatch.label}.`;
                autoNavigate = true;
            } else {
                return null;
            }

            return {
                reply: replyText,
                source: "site_navigation",
                autoNavigate: autoNavigate,
                navigation: [{ label: `Open ${bestMatch.label}`, route: bestMatch.route }]
            };
        }

        return null;
    }

    function detectIndustriesIntent(text) {
        if (assistant.isEmployer) return null;
        if (!window.CareerBuddyIndustriesKnowledge || !window.CareerBuddyIndustriesKnowledge.isLoaded()) return null;
        
        const q = text.toLowerCase().trim();
        const knowledge = window.CareerBuddyIndustriesKnowledge;
        
        assistant.industriesContext = assistant.industriesContext || null;
        
        const isNavVerb = /^(take me there|open it|open this|open that|show me|take me|go there|let me see)$/i.test(q) ||
                          /^open (this|that|it|there) (role|roles|department|category|industry)$/i.test(q) ||
                          /^(show|view|explore) (those|these|the|this) (roles|role|jobs|job|departments|department)$/i.test(q) ||
                          /^(show me|let me see) (those|these|the) (roles|role|jobs|job|departments|department)$/i.test(q);
                          
        if (isNavVerb && assistant.industriesContext) {
            const ctx = assistant.industriesContext;
            let route = knowledge.getRouteForCategory(ctx.category);
            if (ctx.deptKey) route += '#' + ctx.deptKey;
            else if (ctx.key) route += '#' + ctx.key;
            
            return {
                reply: "Opening your requested industry.",
                navigation: [{ label: "Open", route: route }],
                autoNavigate: true
            };
        }
        
        const optionsMatch = q.match(/^(open|show|view|tell me about) (the )?(options|role details|details|this role)( for this role)?$/i);
        if (optionsMatch && ctx && ctx.key) {
             const auto = /^(open|show|view)/i.test(q);
             let route = ctx.category === 'it' ? '/careers/it/' : '/careers/non-it/';
             route += '#options-' + ctx.key;
             return {
                 reply: auto ? "Opening options for this role." : "Here are the options for this role.",
                 navigation: [{ label: "View Options", route: route }],
                 autoNavigate: auto
             };
        }
        
        const takeMeToItMatch = q.match(/^(take me to|open|show me|show) (it|it roles|it jobs|it department|it departments)$/i);
        if (takeMeToItMatch || q === "it" || q === "it roles" || q === "it jobs") {
             assistant.industriesContext = { category: 'it' };
             const auto = /^(take me|open)/i.test(q) || q === "open it";
             return {
                 reply: "Sure. I can show you the available IT roles.",
                 navigation: [{ label: "Open IT Roles", route: "/careers/it/" }],
                 autoNavigate: auto
             };
        }
        
        const takeMeToNonItTechMatch = q.match(/^(take me to|open|show me|show) (non it technical|non-it technical|technical)(?: (roles|jobs|departments))?$/i);
        if (takeMeToNonItTechMatch || q === "technical" || q === "technical roles" || q === "non it technical" || q === "non-it technical") {
             assistant.industriesContext = { category: 'tech' };
             const auto = /^(take me|open)/i.test(q);
             return {
                 reply: "Sure. I can show you the available Non-IT Technical roles.",
                 navigation: [{ label: "Open Non-IT Technical Roles", route: "/careers/non-it/" }],
                 autoNavigate: auto
             };
        }
        
        const takeMeToNonItNonTechMatch = q.match(/^(take me to|open|show me|show) (non it non technical|non-it non-technical|non technical|non-technical)(?: (roles|jobs|departments))?$/i);
        if (takeMeToNonItNonTechMatch || q === "non technical" || q === "non technical roles" || q === "non it non technical" || q === "non-it non-technical") {
             assistant.industriesContext = { category: 'nt' };
             const auto = /^(take me|open)/i.test(q);
             return {
                 reply: "Sure. I can show you the available Non-IT Non-Technical roles.",
                 navigation: [{ label: "Open Non-IT Non-Technical Roles", route: "/careers/non-it/" }],
                 autoNavigate: auto
             };
        }
        
        const baseIndustriesMatch = q.match(/^(take me to|open|go to|view|explore|show me|show) industries$/i);
        if (baseIndustriesMatch || q === "industries") {
             assistant.industriesContext = null;
             const auto = /^(take me|open|go to|view|explore)/i.test(q);
             if (auto) {
                 return {
                     reply: "Opening Industries.",
                     navigation: [{ label: "Open Industries", route: "/#choose-path" }],
                     autoNavigate: true
                 };
             }
             return {
                 reply: "We support various industries including IT Roles, Non-IT Technical, and Non-IT Non-Technical.",
                 navigation: [
                     { label: "Open IT Roles", route: "/careers/it/" },
                     { label: "Open Non-IT Technical Roles", route: "/careers/non-it/" },
                     { label: "Open Non-IT Non-Technical Roles", route: "/careers/non-it/" }
                 ],
                 autoNavigate: false
             };
        }
        
        let stripped = q.replace(/^(take me to|open|show me|show|what are the|tell me about|what skills are required for) /i, "").trim();
        let cleanQ = stripped.replace(/\s+(roles|jobs|departments|department)$/i, "").trim();
        let baseAns = knowledge.answerIndustriesQuestion(cleanQ) || knowledge.answerIndustriesQuestion(stripped) || knowledge.answerIndustriesQuestion(q);
        
        if (baseAns) {
            let navLabel = "the requested section";
            if (baseAns.navigation && baseAns.navigation.length > 0) {
                const nav = baseAns.navigation[0];
                navLabel = nav.label;
                const route = nav.route;
                assistant.industriesContext = {};
                if (route.includes('/it/')) assistant.industriesContext.category = 'it';
                else if (route.includes('/non-it/')) {
                    if (baseAns.reply.includes('Non-Technical')) assistant.industriesContext.category = 'nt';
                    else assistant.industriesContext.category = 'tech';
                }
                
                if (route.includes('#')) {
                    const hash = route.split('#')[1];
                    assistant.industriesContext.key = hash;
                    assistant.industriesContext.deptKey = hash;
                }
            }
            
            if (/^(take me to|open|show me|show) /i.test(q)) {
                baseAns.autoNavigate = true;
                baseAns.reply = `Sure \u2014 opening ${navLabel}.`;
            }
            
            return baseAns;
        }

        return null;
    }

    function processTranscript(text, inputMode) {
        let cleanText = String(text || "")
            .replace(/\s+/g, " ")
            .trim();

        if (!cleanText) {
            showError(
                "I did not catch that. Click the microphone to try again."
            );
            return;
        }

        // ONE-PER-TURN LATCH (voice): the browser recogniser and the
        // MediaRecorder→backend STT both transcribe the same spoken turn and can
        // each call this. The first consumes the turn; the second is dropped so
        // the reply is not duplicated. Reset when a new recording starts.
        if (inputMode === "voice") {
            if (assistant.voiceTurnConsumed) {
                return;
            }
            assistant.voiceTurnConsumed = true;
        }

        // ============================================================
        // ECHO GUARD
        //
        // On a laptop without headphones the microphone hears Buddy's own
        // reply through the speakers. That transcript then arrives here as
        // though the user had said it, Buddy answers it, speaks again, and
        // the loop feeds itself — which is how "Opening the grammar
        // section." ended up repeating four times.
        //
        // Buddy never needs to answer its own words, so drop them.
        // ============================================================
        if (inputMode === "voice" && isEchoOfLastReply(cleanText)) {
            assistant.voiceTurnHandled = true;
            setStatus("Ready for your next question.");
            return;
        }

        // TTS-TAIL GUARD: right after Buddy speaks (or a speaker-button replay),
        // the mic can catch a short fragment of Buddy's own voice ("resume",
        // "upload your resume") that is too short for the echo test above, then
        // re-answer it and loop. Within a cooldown of TTS ending, drop any voice
        // input whose words are ALL part of the last reply — a real user command
        // ("open X", "what is X") carries a verb the reply does not.
        if (
            inputMode === "voice" &&
            (Date.now() - (assistant.ttsEndedAt || 0)) < 2500 &&
            lastReplyOverlap(cleanText) >= 0.6
        ) {
            assistant.voiceTurnHandled = true;
            setStatus("Ready for your next question.");
            return;
        }

        // ============================================================
        // WAKE WORD ("Hey Buddy" / "Buddy")
        // ============================================================
        // Runs early, for BOTH voice and text, since this is the single
        // entry point both input modes already share. Does not create a
        // second pipeline: it either (a) strips the wake phrase and lets
        // the remaining command fall through to the exact same code below
        // (including history navigation, so "Hey Buddy, go back" still
        // works), or (b) - if wake word only - answers "Yes? How can I
        // help?" and returns, WITHOUT touching conversationId, history,
        // role, subscription, language, or current page context.
        const wake = extractWakeWordCommand(cleanText);
        if (wake.hasWakeWord) {
            if (!wake.command) {
                const now = Date.now();
                if (now < assistant.wakeWordAckCooldownUntil) {
                    // Duplicate wake-word-only trigger from the same
                    // continuous-recognition turn - ignore, do not
                    // repeat "Yes?" multiple times.
                    return;
                }
                assistant.wakeWordAckCooldownUntil = now + 2500;

                if (inputMode === "voice") {
                    assistant.voiceTurnHandled = true;
                }

                const ack = getWakeWordAckText();
                addConversationMessage("user", cleanText);
                addConversationMessage("assistant", ack);

                renderPayload(
                    { reply: ack, actions: [], source: "wake_word" },
                    {
                        speak: inputMode === "voice",
                        autoResumeListening: inputMode === "voice",
                        statusText: ack,
                    }
                );
                return;
            }

            // Wake word + command in a single utterance/message: drop the
            // wake phrase and continue through the SAME pipeline below as
            // if the user had just said/typed the command on its own.
            cleanText = wake.command;
        }

        // ============================================================
        // HISTORY NAVIGATION  ("go back" / "go forward")
        // ============================================================
        // Browser history is client-only — the server cannot move it — so a
        // bare "go back" is handled here, before any role or server routing,
        // and works on every page and in every role. "go back to grammar"
        // names a destination and is deliberately left to normal navigation.
        const historyMove = detectHistoryNavigation(cleanText);
        if (historyMove) {
            if (inputMode === "voice") {
                assistant.voiceTurnHandled = true;
            }
            addConversationMessage("user", cleanText);
            const lang = getSelectedAssistantLanguage();
            const reply =
                HISTORY_REPLIES[historyMove][lang] ||
                HISTORY_REPLIES[historyMove].english;
            addConversationMessage("assistant", reply);
            renderPayload(
                { reply, source: "history" },
                { speak: true, autoResumeListening: false, statusText: reply }
            );
            // Move after a short beat so the confirmation is seen and spoken
            // before the page changes.
            window.setTimeout(function () {
                if (historyMove === "forward") {
                    window.history.forward();
                } else {
                    window.history.back();
                }
            }, 350);
            return;
        }

        // ============================================================
        // SITE-WIDE NAVIGATION & KNOWLEDGE
        // ============================================================
        const siteNavReply = detectSiteNavigationIntent(cleanText);
        if (siteNavReply) {
            if (inputMode === "voice") {
                assistant.voiceTurnHandled = true;
            }
            
            addConversationMessage("user", cleanText);
            addConversationMessage("assistant", siteNavReply.reply);
            
            const actions = [];
            if (siteNavReply.navigation && siteNavReply.navigation.length > 0) {
                siteNavReply.navigation.forEach(nav => {
                    actions.push({
                        key: "site_nav",
                        route: nav.route,
                        label: nav.label,
                        response: nav.label
                    });
                });
            }
            
            renderPayload(
                { reply: siteNavReply.reply, actions: actions, source: "site_navigation" },
                { speak: true, autoResumeListening: false, statusText: "Processing navigation request." }
            );
            
            if (siteNavReply.autoNavigate && actions.length > 0) {
                commitNavigation(actions[0]);
            }
            return;
        }

        // ============================================================
        // INDUSTRIES NAVIGATION & INTENT (Priority over Guest Role)
        // ============================================================
        const indReply = detectIndustriesIntent(cleanText);
        if (indReply) {
            if (inputMode === "voice") {
                assistant.voiceTurnHandled = true;
            }
            
            addConversationMessage("user", cleanText);
            addConversationMessage("assistant", indReply.reply);
            
            const actions = [];
            if (indReply.navigation && indReply.navigation.length > 0) {
                indReply.navigation.forEach(nav => {
                    actions.push({
                        key: "industries_nav",
                        route: nav.route,
                        label: nav.label,
                        response: nav.label
                    });
                });
            }
            
            renderPayload(
                { reply: indReply.reply, actions: actions, source: "intent" },
                { speak: true, autoResumeListening: false, statusText: "Processing industries request." }
            );
            
            if (indReply.autoNavigate && actions.length > 0) {
                // Ensure the reply gets spoken/rendered first, then navigate
                commitNavigation(actions[0]);
            }
            return;
        }

        // ============================================================
        // GUEST LOGIN & NAVIGATION
        // ============================================================
        // If a guest explicitly asks for a login page, home page, or any globally allowed
        // page, navigate directly. Do this BEFORE role selection so "take me to home"
        // does not merely ask "Are you a Job Seeker or an Employer?"
        if (getAssistantRole() === "guest") {
            const guestText = normalizeText(cleanText);

            // 1. Try to match any guest-allowed action key
            const allowedForGuest = getAllowedActionKeys();
            let matchedGuestActionKey = null;

            if (hasNavigationVerb(guestText) || allowedForGuest.includes(guestText)) {
                const stripped = guestText
                    .replace(/\b(go|open|navigate|take|show|start|launch|visit|move|redirect|list|karo|kholo|khulna|kholna|dikhao|jao|chalo|batao|register|sign up)\b/gi, "")
                    .replace(/\btake me to\b/gi, "")
                    .replace(/\btake me\b/gi, "")
                    .replace(/\bgo to\b/gi, "")
                    .trim();

                for (const key of allowedForGuest) {
                    const definition = ACTION_DEFINITIONS[key];
                    if (!definition || !definition.keywords) continue;

                    // If exact match with a keyword
                    if (
                        definition.keywords.includes(guestText) ||
                        definition.keywords.includes(stripped) ||
                        guestText === (definition.label || "").toLowerCase() ||
                        stripped === (definition.label || "").toLowerCase()
                    ) {
                        matchedGuestActionKey = key;
                        break;
                    }
                }
            }

            // 2. Fallback to explicit employer/job seeker login logic
            if (!matchedGuestActionKey) {
                const wantsEmployerLogin =
                    /\b(employer|recruiter|company)\b/.test(guestText) &&
                    /\b(login|log in|sign in|signin|portal)\b/.test(guestText);

                const wantsJobSeekerLogin =
                    /\b(job seeker|jobseeker|candidate|student)\b/.test(guestText) &&
                    /\b(login|log in|sign in|signin|portal)\b/.test(guestText);

                if (wantsEmployerLogin) {
                    matchedGuestActionKey = "login_employer";
                } else if (wantsJobSeekerLogin) {
                    matchedGuestActionKey = "login_job_seeker";
                }
            }

            if (matchedGuestActionKey) {
                const definition = ACTION_DEFINITIONS[matchedGuestActionKey];

                if (definition) {
                    if (inputMode === "voice") {
                        assistant.voiceTurnHandled = true;
                    }

                    const action = {
                        key: matchedGuestActionKey,
                        route: definition.route,
                        label: definition.label,
                        response: definition.response,
                    };

                    const reply =
                        getLocalizedActionResponse(action);

                    addConversationMessage(
                        "user",
                        cleanText
                    );

                    addConversationMessage(
                        "assistant",
                        reply
                    );

                    // Committed before speaking, so a failed or interrupted
                    // utterance can never strand the user on this page.
                    commitNavigation(action);

                    renderPayload(
                        {
                            reply,
                            actions: [action],
                            source: "intent",
                        },
                        {
                            speak: true,
                            statusText: "Opening login page.",
                            // Navigation is committed, not queued behind TTS.
                            afterSpeak: null,
                            autoResumeListening: false,
                        }
                    );

                    /* Navigation now flows through afterSpeak: Riya speaks the confirmation first, then navigates (voice output for every response, including typed). */

                    return;
                }
            }
        }

        // ============================================================
        // GUEST ROLE SELECTION
        // ============================================================
        //
        // A guest must choose Job Seeker or Employer before any
        // role-specific navigation is allowed.
        //
        // IMPORTANT:
        // - Only ONE guest block exists.
        // - selectedRole stays inside this block.
        // - No Employer history can leak into Student.
        // ============================================================

        if (getAssistantRole() === "guest") {
            const selectedRole = detectGuestRole(cleanText);

            if (!selectedRole) {
                const language = getSelectedAssistantLanguage();

                const roleQuestion = {
                    english:
                        "Are you a Job Seeker or an Employer?",

                    vietnam:
                        "Xin chào! Bạn là Người tìm việc hay Nhà tuyển dụng?",

                    hindi:
                        "नमस्ते! आप Job Seeker हैं या Employer?",

                    arabic:
                        "مرحباً! هل أنت باحث عن عمل أم صاحب عمل؟",

                    russian:
                        "Здравствуйте! Вы соискатель или работодатель?"
                };

                if (inputMode === "voice") {
                    assistant.voiceTurnHandled = true;
                }

                const reply =
                    roleQuestion[language] ||
                    roleQuestion.english;

                addConversationMessage("user", cleanText);
                addConversationMessage("assistant", reply);

                renderPayload(
                    {
                        reply,
                        source: "role_selection"
                    },
                    {
                        speak: true,
                        autoResumeListening: inputMode === "voice",
                        statusText: "Please choose Job Seeker or Employer."
                    }
                );

                return;
            }

            // --------------------------------------------------------
            // Role selected
            // --------------------------------------------------------

            if (inputMode === "voice") {
                assistant.voiceTurnHandled = true;
            }

            assistant.role = selectedRole;
            assistant.isEmployer = selectedRole === "employer";

            // Start a completely separate conversation for the selected
            // role. Student and Employer histories never share an ID.
            assistant.conversationId = createConversationId();
            assistant.conversationHistory = [];

            const language = getSelectedAssistantLanguage();
            const roleContext = ROLE_CONTEXT[selectedRole];

            const roleReplies = {
                employer: {
                    english:
                        "Great! I'll help you as an Employer. You can ask me about hiring, candidates, jobs, applications, or your employer dashboard.",

                    vietnam:
                        "Tuyệt vời! Tôi sẽ hỗ trợ bạn với tư cách Nhà tuyển dụng. Bạn có thể hỏi về tuyển dụng, ứng viên, việc làm, hồ sơ ứng tuyển hoặc bảng điều khiển nhà tuyển dụng.",

                    hindi:
                        "बहुत अच्छा! अब मैं Employer के रूप में आपकी मदद करूँगा। आप भर्ती, उम्मीदवारों, नौकरियों, आवेदनों या Employer Dashboard के बारे में पूछ सकते हैं।",

                    arabic:
                        "رائع! سأساعدك بصفتك صاحب عمل. يمكنك السؤال عن التوظيف والمرشحين والوظائف والطلبات أو لوحة تحكم صاحب العمل.",

                    russian:
                        "Отлично! Теперь я буду помогать вам как работодателю. Вы можете спрашивать о найме, кандидатах, вакансиях, заявках или панели работодателя."
                },

                student: {
                    english:
                        "Great! I'll help you as a Job Seeker. You can ask me about learning, activities, grammar, resumes, careers, or jobs.",

                    vietnam:
                        "Tuyệt vời! Tôi sẽ hỗ trợ bạn với tư cách Người tìm việc. Bạn có thể hỏi về việc học, hoạt động, ngữ pháp, CV, nghề nghiệp hoặc việc làm.",

                    hindi:
                        "बहुत अच्छा! अब मैं Job Seeker के रूप में आपकी मदद करूँगा। आप पढ़ाई, गतिविधियों, ग्रामर, रिज्यूमे, करियर या नौकरियों के बारे में पूछ सकते हैं।",

                    arabic:
                        "رائع! سأساعدك بصفتك باحثاً عن عمل. يمكنك السؤال عن التعلم والأنشطة والقواعد والسيرة الذاتية والمسيرة المهنية أو الوظائف.",

                    russian:
                        "Отлично! Теперь я буду помогать вам как соискателю. Вы можете спрашивать об обучении, занятиях, грамматике, резюме, карьере или вакансиях."
                }
            };

            const reply =
                roleReplies[selectedRole]?.[language] ||
                roleReplies[selectedRole]?.english ||
                "Great! Buddy is ready to help you.";

            addConversationMessage("user", cleanText);
            addConversationMessage("assistant", reply);

            GREETING_TEXT =
                roleContext.greeting[language] ||
                roleContext.greeting.english;

            const action = {
                key: selectedRole === "employer" ? "login_employer" : "login_job_seeker",
                route: selectedRole === "employer" ? "/employer/accounts/employer/login/" : "/users/login/"
            };

            commitNavigation(action);

            renderPayload(
                {
                    reply,
                    actions: [action],
                    source: "role_selection"
                },
                {
                    speak: true,
                    autoResumeListening: false,
                    statusText: "Opening page.",
                    afterSpeak: null
                }
            );

            persistAssistantSession();

            /* Navigation now flows through afterSpeak: Riya speaks the confirmation first, then navigates (voice output for every response, including typed). */
            return;
        }

        // ============================================================
        // NORMAL LOGGED-IN STUDENT / EMPLOYER FLOW
        // ============================================================

        // Store the user turn in the role-specific conversation.
        addConversationMessage("user", cleanText);

        // Never allow a cross-role request to reach navigation.
        const roleGuard = getCrossRoleGuardResponse(cleanText);

        if (roleGuard) {
            if (inputMode === "voice") {
                assistant.voiceTurnHandled = true;
            }

            addConversationMessage("assistant", roleGuard.reply);

            renderPayload(roleGuard, {
                speak: true,
                statusText: assistant.isEmployer
                    ? "Employer Buddy is staying in the Employer portal."
                    : "Student Buddy is staying in the Student portal.",
                autoResumeListening: inputMode === "voice",
            });

            return;
        }

        // Premium navigation MUST be resolved by the backend because the
        // browser does not own the user's subscription state. The old local
        // resolver could directly send Free users to /gd/, /jam/, /roleplay/,
        // /resume-builder/ (mock interview), or /resume-builder/analytics/
        // (job search) before the backend plan validation ran.
        const PREMIUM_NAVIGATION_KEYS = new Set([
            "workshop",
            "gd",
            "jam",
            "roleplay",
            "mock_interview",
            "job_search",
        ]);

        // On a Skill Up page the local resolver must stand down. Its Activities
        // action carries the keywords "lesson"/"lessons", so a Skill Up request
        // like "open the first lesson" would score a local match and jump to
        // /activities/ before the server's Skill Up layer ever saw it — which
        // is exactly why Skill Up queries kept landing on the Activities page.
        // Deferring to the server lets Skill Up resolve, ask, or say "not found".
        const onSkillUpPage =
            (assistant.root?.dataset.riyaPage || "").toLowerCase() === "skill_up" ||
            String(window.location.pathname || "").toLowerCase().indexOf("/skill-up/") === 0;

        const navigationAction = onSkillUpPage
            ? null
            : resolveLocalNavigationIntent(cleanText);

        // A category action (e.g. "Speaking & Presentation") and an
        // individual Activity (e.g. "Professional Speaking") can share
        // words in their names/keywords, and this file's local
        // ACTION_DEFINITIONS keyword lists are hand-maintained separately
        // from the backend's, so they can drift and add an ambiguous
        // keyword like "professional speaking" or "speaking" to a category
        // action without anyone noticing. The browser has no copy of the
        // 27-activity catalog and structurally cannot tell "the Speaking
        // category" from "the Professional Speaking activity" the way the
        // backend's resolve_activity_navigation_payload() can (it queries
        // the real Activity table and prefers an exact full-title match
        // over a category match). So: never let a *category* route
        // navigate locally — always defer those to the backend, exactly
        // like premium routes already do below. Non-category actions
        // (home, dashboard, grammar, roleplay, JAM, GD, resume builder,
        // etc.) have no such collision risk and keep their instant local
        // navigation.
        const isCategoryAction =
            !!navigationAction &&
            typeof navigationAction.route === "string" &&
            navigationAction.route.indexOf("/activities/?category=") === 0;

        // For premium actions, DO NOT navigate locally. Let the backend
        // resolve the intent and validate the user's plan. The backend will
        // return /pro/ for Free users and the real route for eligible users.
        if (
            navigationAction &&
            (PREMIUM_NAVIGATION_KEYS.has(navigationAction.key) || isCategoryAction)
        ) {
            // Intentionally fall through to requestAssistantReplyStream().
        } else if (navigationAction) {
            if (inputMode === "voice") {
                assistant.voiceTurnHandled = true;
            }

            // Plain "Opening X." for a bare open/navigate/guide; the description +
            // child menu only when the user ASKED ABOUT it ("what is X"). Matches
            // the backend so local (non-category) nav doesn't dump guidance on a
            // plain open.
            const responseText =
                isInformationalQuestion(normalizeText(cleanText))
                    ? buildGuidedNavigationReply(navigationAction)
                    : getLocalizedActionResponse(navigationAction);

            addConversationMessage(
                "assistant",
                responseText
            );

            commitNavigation(navigationAction);

            renderPayload(
                {
                    reply: responseText,
                    actions: [navigationAction],
                    source: "intent",
                },
                {
                    speak: true,
                    statusText: "Opening page.",
                    afterSpeak: null,
                }
            );

            /* Navigation now flows through afterSpeak: Riya speaks the confirmation first, then navigates (voice output for every response, including typed). */

            return;
        }
        if (inputMode === "voice") {
            assistant.voiceTurnHandled = true;
            showTranscript(cleanText);
        }

        requestAssistantReplyStream(
            cleanText,
            inputMode
        ).catch(() => {
            const fallback = buildFallbackPayload();

            addConversationMessage(
                "assistant",
                fallback.reply
            );

            renderPayload(
                fallback,
                {
                    speak: false,
                    asError: true,
                    autoResumeListening: false,
                    statusText:
                        "I could not reach the assistant. Click the microphone to try again.",
                }
            );
        });
    }

    function clearSilenceTimer() {
        if (assistant.silenceTimer) {
            clearTimeout(assistant.silenceTimer);
            assistant.silenceTimer = null;
        }
    }

    function scheduleRecognitionSilenceStop() {
        clearSilenceTimer();
        assistant.silenceTimer = window.setTimeout(() => {
            stopSpeechRecognition("silence");
        }, 1800);
    }

    function resetRecognitionBuffers() {
        assistant.recognitionFinalText = "";
        assistant.recognitionInterimText = "";
    }

    function stopSpeechRecognition(reason = "manual") {
        if (!assistant.recognition || !assistant.recognitionRunning) {
            return;
        }

        assistant.recognitionStopReason = reason;
        clearSilenceTimer();
        try {
            assistant.recognition.stop();
        } catch (_error) {
            assistant.recognitionRunning = false;
        }
    }

    function handleSpeechRecognitionError(event) {
        assistant.recognitionRunning = false;
        clearSilenceTimer();

        if (assistant.recognitionStopReason === "close") {
            resetRecognitionBuffers();
            return;
        }

        if (assistant.pendingBackendTranscript || (assistant.mediaRecorder && assistant.mediaRecorder.state !== "inactive")) {
            return;
        }

        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            showError("Microphone access is blocked for Buddy.");
            return;
        }

        showError("Browser speech recognition is unavailable right now.");
    }

    function guessRecordingFileName(mimeType) {
        const normalized = String(mimeType || "").toLowerCase();
        if (normalized.includes("ogg")) {
            return "recording.ogg";
        }
        if (normalized.includes("mp4") || normalized.includes("mpeg")) {
            return "recording.m4a";
        }
        if (normalized.includes("wav")) {
            return "recording.wav";
        }
        return "recording.webm";
    }

    /**
     * Append one recognition segment to the accumulated transcript WITHOUT
     * duplicating overlapping words.
     *
     * Why this exists: on mobile (Android) Chrome, continuous
     * webkitSpeechRecognition re-reports the SAME spoken phrase across several
     * onresult events and even re-includes already-finalized words in a later
     * FINAL segment (it emits "open" and then "open Tech" for one utterance).
     * The previous logic appended every final segment verbatim, so a single
     * spoken "open Tech" accumulated into "open open Tech". Desktop Chrome
     * segments cleanly (one disjoint final per phrase), so for desktop input
     * this helper simply joins with a space and leaves the result unchanged.
     */
    function mergeTranscriptSegment(base, segment) {
        const b = String(base || "").trim();
        const s = String(segment || "").trim();
        if (!b) return s;
        if (!s) return b;

        const bl = b.toLowerCase();
        const sl = s.toLowerCase();

        // Exact repeat, or the new segment just re-states the tail we already
        // have (Android re-firing the same final result): keep base as-is.
        if (bl === sl || bl.endsWith(sl)) return b;

        // The new segment is an expansion of what we have ("open" -> "open
        // Tech"): keep the fuller segment and drop the shorter prefix.
        if (sl.startsWith(bl)) return s;

        // Word-level overlap: the tail of base repeats the head of the new
        // segment ("open Tech" + "Tech section" -> "open Tech section").
        const bWords = b.split(/\s+/);
        const sWords = s.split(/\s+/);
        const maxOverlap = Math.min(bWords.length, sWords.length);
        for (let n = maxOverlap; n > 0; n -= 1) {
            const baseTail = bWords.slice(bWords.length - n).join(" ").toLowerCase();
            const segHead = sWords.slice(0, n).join(" ").toLowerCase();
            if (baseTail === segHead) {
                return bWords.concat(sWords.slice(n)).join(" ");
            }
        }

        // Genuinely new words: append normally.
        return `${b} ${s}`;
    }

    function initializeSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            return;
        }

        assistant.recognition = new SpeechRecognition();

        const langMap = {
            "english": "en-US",
            "en": "en-US",
            "hindi": "hi-IN",
            "hi": "hi-IN",
            "vietnam": "vi-VN",
            "vietnamese": "vi-VN",
            "arabic": "ar-SA",
            "ar": "ar-SA",
            "russian": "ru-RU",
            "ru": "ru-RU"
        };
        const currentLang = document.getElementById('chatbotLanguageSelect') ? document.getElementById('chatbotLanguageSelect').value : 'english';
        assistant.recognition.lang = langMap[currentLang] || "en-US";

        assistant.recognition.continuous = true;
        assistant.recognition.interimResults = true;
        assistant.recognition.maxAlternatives = 1;

        assistant.recognition.onstart = () => {
            assistant.recognitionRunning = true;
        };

        assistant.recognition.onresult = (event) => {
            // Rebuild the transcript from the FULL cumulative results list on
            // every event (instead of appending only the new delta). This
            // makes accumulation idempotent: if mobile Chrome re-fires an
            // onresult for a phrase it already finalized, we recompute the
            // same text rather than appending it a second time. mergeTranscript
            // Segment then collapses the overlapping final segments Android
            // emits, so one spoken "open Tech" stays exactly "open Tech".
            let finalText = "";
            let interimText = "";

            for (let index = 0; index < event.results.length; index += 1) {
                const result = event.results[index];
                const transcript = String(result[0]?.transcript || "").trim();
                if (!transcript) {
                    continue;
                }
                if (result.isFinal) {
                    finalText = mergeTranscriptSegment(finalText, transcript);
                } else {
                    interimText = mergeTranscriptSegment(interimText, transcript);
                }
            }

            assistant.recognitionFinalText = finalText;
            assistant.recognitionInterimText = interimText;
            const previewText = mergeTranscriptSegment(finalText, interimText);
            if (previewText) {
                showTranscript(previewText);
            }
            scheduleRecognitionSilenceStop();
        };

        assistant.recognition.onspeechstart = () => {
            clearSilenceTimer();
        };

        assistant.recognition.onspeechend = () => {
            scheduleRecognitionSilenceStop();
        };

        assistant.recognition.onerror = handleSpeechRecognitionError;

        assistant.recognition.onend = () => {
            const stopReason = assistant.recognitionStopReason;
            const transcript = mergeTranscriptSegment(
                assistant.recognitionFinalText,
                assistant.recognitionInterimText
            );
            assistant.recognitionRunning = false;
            clearSilenceTimer();

            if (
                stopReason === "close" ||
                stopReason === "tts" ||
                stopReason === "language_change"
            ) {
                resetRecognitionBuffers();
                assistant.voiceTurnHandled = true;
                assistant.pendingBackendTranscript = false;
                return;
            }

            if (
                assistant.voiceTurnHandled ||
                assistant.pendingBackendTranscript ||
                (assistant.mediaRecorder && assistant.mediaRecorder.state !== "inactive")
            ) {
                return;
            }

            if (!transcript) {
                resetRecognitionBuffers();
                // Manual stop with nothing captured: stay quiet, don't re-listen.
                if (stopReason === "manual") {
                    setStatus("Microphone stopped. Click Speak when you are ready.");
                    return;
                }
                showError("I did not catch that. Listening again.");
                scheduleAutoListen(700);
                return;
            }

            resetRecognitionBuffers();
            processTranscript(transcript, "voice");
        };
    }

    async function initializeMediaRecorder() {
        if (assistant.mediaRecorder) {
            return true;
        }

        if (!navigator.mediaDevices || !window.MediaRecorder) {
            return false;
        }

        try {
            // Enable browser AEC/noise/gain so the mic does not pick up Buddy's
            // own voice from the speakers (the main cause of the self-answer loop
            // on devices without headphones).
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            assistant.mediaStream = stream;

            const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
            if (AudioContextConstructor) {
                assistant.mediaAudioContext = new AudioContextConstructor();
                const source = assistant.mediaAudioContext.createMediaStreamSource(stream);
                assistant.mediaAnalyser = assistant.mediaAudioContext.createAnalyser();
                assistant.mediaAnalyser.fftSize = 256;
                source.connect(assistant.mediaAnalyser);
            }

            const preferredMimeTypes = [
                "audio/webm;codecs=opus",
                "audio/webm",
                "audio/ogg;codecs=opus",
                "audio/mp4",
            ];
            const supportedMimeType = preferredMimeTypes.find(
                (mimeType) => window.MediaRecorder.isTypeSupported && window.MediaRecorder.isTypeSupported(mimeType)
            );
            assistant.mediaMimeType = supportedMimeType || "";
            assistant.mediaRecorder = supportedMimeType
                ? new MediaRecorder(stream, { mimeType: supportedMimeType })
                : new MediaRecorder(stream);
            assistant.mediaMimeType = assistant.mediaRecorder.mimeType || assistant.mediaMimeType || "audio/webm";
            assistant.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    assistant.mediaChunks.push(event.data);
                }
            };

            assistant.mediaRecorder.onstop = async () => {
                clearSilenceTimer();
                if (assistant.barAnimationFrame) {
                    cancelAnimationFrame(assistant.barAnimationFrame);
                    assistant.barAnimationFrame = null;
                }

                const chunks = assistant.mediaChunks.slice();
                assistant.mediaChunks = [];

                if (
                    assistant.mediaStopReason === "close" ||
                    assistant.mediaStopReason === "tts" ||
                    assistant.mediaStopReason === "language_change"
                ) {
                    assistant.pendingBackendTranscript = false;
                    releaseMicrophoneResources();
                    return;
                }

                // The browser's SpeechRecognition and this MediaRecorder both
                // listen to the same spoken turn. recognition.onend already
                // bails out when the turn has been handled; this handler did
                // not, so a single "take me to grammar" was answered twice —
                // and each new answer cancelled the previous one's pending
                // navigation, which is why the same line repeated and the page
                // never actually moved.
                if (assistant.voiceTurnHandled) {
                    assistant.pendingBackendTranscript = false;
                    releaseMicrophoneResources();
                    return;
                }

                if (!chunks.length) {
                    assistant.pendingBackendTranscript = false;
                    if (assistant.mediaStopReason === "manual") {
                        setStatus("Microphone stopped. Click Speak when you are ready.");
                        releaseMicrophoneResources();
                        return;
                    }
                    showError("I did not catch that. Listening again.");
                    scheduleAutoListen(700);
                    return;
                }

                setAssistantState(AssistantState.PROCESSING);
                setStatus("Turning your voice into text.");
                const audioBlob = new Blob(chunks, {
                    type: assistant.mediaMimeType || assistant.mediaRecorder.mimeType || "audio/webm",
                });
                const browserTranscript = mergeTranscriptSegment(
                    assistant.recognitionFinalText,
                    assistant.recognitionInterimText
                );


                // FAST PATH:
                // Browser SpeechRecognition already has the user's words.
                // Do not upload the same audio to the server unless the
                // browser transcript is missing or unusable.
                if (hasMeaningfulClientTranscript(browserTranscript)) {
                    assistant.pendingBackendTranscript = false;
                    releaseMicrophoneResources();
                    processTranscript(browserTranscript, "voice");
                    return;
                }

                try {
                    const base64Audio = await blobToBase64(audioBlob);
                    const response = await fetch("/api/voice/transcribe/", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCsrfToken(),
                        },
                        body: JSON.stringify({
                            audio: base64Audio,
                            mime_type: assistant.mediaMimeType || audioBlob.type || "audio/webm",
                            file_name: guessRecordingFileName(assistant.mediaMimeType || audioBlob.type),
                            client_transcript: browserTranscript,
                            language: document.getElementById('chatbotLanguageSelect') ? document.getElementById('chatbotLanguageSelect').value : 'english'
                        }),
                    });
                    const raw = await response.json().catch(() => ({}));
                    assistant.pendingBackendTranscript = false;
                    if (!raw.success) {
                        throw new Error(raw.error || "Voice transcription failed.");
                    }
                    const payload = raw.data;
                    releaseMicrophoneResources();
                    processTranscript(payload.text || "", "voice");
                } catch (error) {
                    assistant.pendingBackendTranscript = false;
                    const browserTranscript = mergeTranscriptSegment(
                        assistant.recognitionFinalText,
                        assistant.recognitionInterimText
                    );
                    if (browserTranscript) {
                        processTranscript(browserTranscript, "voice");
                        return;
                    }
                    showError(error.message || "Voice transcription failed.");
                }
            };

            return true;
        } catch (_error) {
            return false;
        }
    }

    function updateVisualizer() {
        if (!assistant.mediaAnalyser || assistant.state !== AssistantState.LISTENING) {
            return;
        }

        const dataArray = new Uint8Array(assistant.mediaAnalyser.frequencyBinCount);
        assistant.mediaAnalyser.getByteFrequencyData(dataArray);

        let sum = 0;
        dataArray.forEach((value) => {
            sum += value;
        });
        const averageVolume = sum / dataArray.length;

        if (averageVolume > 18) {
            assistant.mediaVADActive = true;
            clearSilenceTimer();
        } else if (assistant.mediaVADActive && averageVolume < 12 && !assistant.silenceTimer) {
            assistant.silenceTimer = window.setTimeout(() => {
                stopMediaRecorder("silence");
            }, 1800);
        }

        assistant.barAnimationFrame = window.requestAnimationFrame(updateVisualizer);
    }

    function stopMediaRecorder(reason = "manual") {
        if (!assistant.mediaRecorder || assistant.mediaRecorder.state === "inactive") {
            return;
        }

        assistant.mediaStopReason = reason;
        clearSilenceTimer();
        assistant.mediaRecorder.stop();
    }

    async function startVoiceRecording() {
        if (
            assistant.state === AssistantState.CLOSED ||
            assistant.state === AssistantState.PROCESSING ||
            assistant.languageChangeInProgress ||
            assistant.pendingBackendTranscript ||
            assistant.recognitionRunning ||
            assistant.ttsSpeaking ||
            assistant.microphoneBlockedByTTS ||
            (
                assistant.mediaRecorder &&
                assistant.mediaRecorder.state !== "inactive"
            )
        ) {
            return;
        }

        assistant.microphoneBlockedByTTS = false;

        stopSpeaking();
        clearTranscript();

        // ---------------------------------------------------------
        // Prepare voice capture
        // ---------------------------------------------------------
        let mediaReady = false;

        if (!assistant.recognition) {
            mediaReady = await initializeMediaRecorder();
        }

        assistant.voiceCaptureMode =
            assistant.recognition
                ? "recognition"
                : (mediaReady ? "server" : "none");

        if (
            !assistant.recognition &&
            !mediaReady
        ) {
            showError(
                "Voice capture is unavailable."
            );

            setAssistantState(
                AssistantState.RESPONDING
            );

            return;
        }

        assistant.pendingBackendTranscript = false;
        assistant.voiceTurnHandled = false;
        // One transcript per recording turn. Browser SpeechRecognition and the
        // MediaRecorder→backend STT both listen to the same turn; on a manual
        // stop each can reach processTranscript and answer, duplicating the reply
        // (the looping bubbles). This latch is consumed by the first and blocks
        // the second; a fresh recording resets it here.
        assistant.voiceTurnConsumed = false;
        assistant.mediaChunks = [];
        assistant.mediaStopReason = "manual";
        assistant.mediaVADActive = false;

        switchLauncherModel(
            LAUNCHER_MODEL_VRiyaNTS.idle
        );

        // ---------------------------------------------------------
        // IMPORTANT:
        // Set LISTENING before starting the microphone.
        //
        // This makes the Speak/Stop button work correctly.
        // ---------------------------------------------------------
        setAssistantState(
            AssistantState.LISTENING
        );

        setStatus(
            "Listening now."
        );

        // ---------------------------------------------------------
        // Browser Speech Recognition
        // ---------------------------------------------------------
        if (assistant.recognition) {
            resetRecognitionBuffers();

            assistant.recognitionStopReason =
                "manual";

            try {
                assistant.recognition.start();

                if (!mediaReady) {
                    scheduleRecognitionSilenceStop();
                }

            } catch (_error) {
                assistant.recognitionRunning = false;

                // If browser recognition cannot start,
                // fall back to MediaRecorder.
                if (!mediaReady) {
                    mediaReady =
                        await initializeMediaRecorder();

                    assistant.voiceCaptureMode =
                        mediaReady
                            ? "server"
                            : "none";
                }
            }
        }

        // ---------------------------------------------------------
        // No capture available
        // ---------------------------------------------------------
        if (
            !mediaReady &&
            !assistant.recognition
        ) {
            setAssistantState(
                AssistantState.RESPONDING
            );

            showError(
                "Voice capture is unavailable."
            );

            return;
        }

        // ---------------------------------------------------------
        // MediaRecorder fallback
        // ---------------------------------------------------------
        if (
            mediaReady &&
            assistant.mediaRecorder &&
            assistant.mediaRecorder.state ===
            "inactive"
        ) {
            assistant.mediaRecorder.start();

            updateVisualizer();
        }
    }

    function stopVoiceRecording(reason = "manual") {
        clearSilenceTimer();
        clearAutoListenTimer();

        setMicIndicatorVisible(false);

        let stoppedSomething = false;

        // ---------------------------------------------------------
        // Stop browser SpeechRecognition
        // ---------------------------------------------------------
        if (assistant.recognitionRunning) {
            assistant.recognitionStopReason =
                reason;

            stopSpeechRecognition(reason);

            stoppedSomething = true;
        }

        // ---------------------------------------------------------
        // Stop MediaRecorder fallback
        // ---------------------------------------------------------
        if (
            assistant.mediaRecorder &&
            assistant.mediaRecorder.state !==
            "inactive"
        ) {
            assistant.mediaStopReason =
                reason;

            stopMediaRecorder(reason);

            assistant.pendingBackendTranscript =
                reason !== "close";

            stoppedSomething = true;
        }

        // ---------------------------------------------------------
        // IMPORTANT:
        // Manual Stop means:
        // do NOT automatically start listening again.
        // ---------------------------------------------------------
        if (reason === "manual") {
            // Do NOT mark the turn handled here — that made onend/onstop SKIP the
            // captured transcript, so turning the mic off right after speaking
            // dropped the query with no reply. Let onend/onstop process it
            // (dedup via voiceTurnConsumed). onend/onstop also suppress
            // auto-restart on a manual stop, so the mic stays off.
            if (
                assistant.state !==
                AssistantState.CLOSED &&
                assistant.state !==
                AssistantState.PROCESSING
            ) {
                setAssistantState(
                    AssistantState.RESPONDING
                );

                setStatus(
                    "Microphone stopped. Click Speak when you are ready."
                );
            }
        }

        if (
            !stoppedSomething &&
            reason === "close"
        ) {
            assistant.pendingBackendTranscript =
                false;
        }
    }

    function blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const result = typeof reader.result === "string" ? reader.result : "";
                const base64 = result.split(",")[1];
                if (!base64) {
                    reject(new Error("Could not read recorded audio."));
                    return;
                }
                resolve(base64);
            };
            reader.onerror = () => reject(new Error("Could not read recorded audio."));
            reader.readAsDataURL(blob);
        });
    }

    // ============================================================
    // CHATBOT CHROME TEXT (placeholder, status line, history panel)
    // Replies were translated but the frame around them stayed English.
    // ============================================================
    const UI_TEXT = {
        english: { thinking: "Thinking...", placeholder: "Type a question...", online: "Online", history: "Conversation history", noHistory: "No conversation yet.", portal: { guest: "CareerBuddy", student: "Job Seeker Portal", employer: "Employer Portal" } },
        hindi: { thinking: "सोच रहा हूँ...", placeholder: "अपना सवाल लिखें...", online: "ऑनलाइन", history: "बातचीत का इतिहास", noHistory: "अभी कोई बातचीत नहीं।", portal: { guest: "CareerBuddy", student: "जॉब सीकर पोर्टल", employer: "एम्प्लॉयर पोर्टल" } },
        vietnam: { thinking: "Đang suy nghĩ...", placeholder: "Nhập câu hỏi...", online: "Trực tuyến", history: "Lịch sử trò chuyện", noHistory: "Chưa có cuộc trò chuyện nào.", portal: { guest: "CareerBuddy", student: "Cổng người tìm việc", employer: "Cổng nhà tuyển dụng" } },
        arabic: { thinking: "جارٍ التفكير...", placeholder: "اكتب سؤالك...", online: "متصل", history: "سجل المحادثة", noHistory: "لا توجد محادثة بعد.", portal: { guest: "CareerBuddy", student: "بوابة الباحث عن عمل", employer: "بوابة صاحب العمل" } },
        russian: { thinking: "Думаю...", placeholder: "Введите вопрос...", online: "В сети", history: "История разговора", noHistory: "Разговоров пока нет.", portal: { guest: "CareerBuddy", student: "Портал соискателя", employer: "Портал работодателя" } },
    };

    function uiText() {
        return UI_TEXT[getSelectedAssistantLanguage()] || UI_TEXT.english;
    }

    function applyUiText() {
        const t = uiText();
        const input = document.getElementById("riya-text-input");
        if (input) input.placeholder = t.placeholder;
        const title = document.querySelector(".riya-history-title");
        if (title) title.textContent = t.history;
        const historyButton = document.getElementById("riya-history-button");
        if (historyButton) {
            historyButton.setAttribute("aria-label", t.history);
            historyButton.setAttribute("title", t.history);
        }
        const status = document.querySelector(".riya-bubble-status");
        if (status) {
            const dot = status.querySelector(".riya-online-dot");
            status.textContent = ` ${t.online} · ${t.portal[getAssistantRole()] || t.portal.guest}`;
            if (dot) status.prepend(dot);
        }
    }

    // ============================================================
    // CONVERSATION HISTORY
    // The panel shows only the last few messages each time Buddy is opened;
    // the full transcript (assistant.conversationHistory, already persisted
    // per role/user in sessionStorage) is behind the header history button.
    // ============================================================
    const VISIBLE_MESSAGE_LIMIT = 5;

    function trimVisibleMessages() {
        if (!assistant.responseSlot) return;
        const cards = assistant.responseSlot.querySelectorAll(
            ".riya-response-card:not(.is-thinking):not(#riya-stream-card)"
        );
        for (let i = 0; i < cards.length - VISIBLE_MESSAGE_LIMIT; i += 1) {
            cards[i].remove();
        }
    }

    function renderHistoryPanel() {
        const list = document.getElementById("riya-history-list");
        if (!list) return;
        list.textContent = "";
        if (!assistant.conversationHistory.length) {
            const empty = document.createElement("p");
            empty.className = "riya-history-empty";
            empty.textContent = uiText().noHistory;
            list.appendChild(empty);
            return;
        }
        assistant.conversationHistory.forEach((item) => {
            const row = document.createElement("div");
            row.className = `riya-history-item riya-history-item--${item.role === "user" ? "user" : "assistant"}`;
            row.textContent = item.content;
            if (item.timestamp) {
                const time = document.createElement("span");
                time.className = "riya-history-time";
                time.textContent = new Date(item.timestamp).toLocaleString([], {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                });
                row.appendChild(time);
            }
            list.appendChild(row);
        });
        list.scrollTop = list.scrollHeight;
    }

    function setHistoryOpen(open) {
        const panel = document.getElementById("riya-history-panel");
        const button = document.getElementById("riya-history-button");
        if (!panel || !button) return;
        if (open) renderHistoryPanel();
        panel.hidden = !open;
        button.setAttribute("aria-expanded", String(open));
    }

    function openChat() {
        if (!assistant.root) return;

        if (assistant.state !== AssistantState.CLOSED) {
            closeChat();
            return;
        }

        trimVisibleMessages();

        const rawUsername = getDisplayName();

        const isGuest = !rawUsername;

        const langSelect =
            document.getElementById("chatbotLanguageSelect");

        const lang =
            langSelect ? langSelect.value : "english";

        const roleGreeting = getRoleContext().greeting;

        const greetings = {
            english: isGuest
                ? roleGreeting.english
                : roleGreeting.english.replace("Hello there!", `Hello ${rawUsername}!`),

            vietnam: isGuest
                ? roleGreeting.vietnam
                : roleGreeting.vietnam.replace("Xin chào!", `Xin chào ${rawUsername}!`),

            hindi: isGuest
                ? roleGreeting.hindi
                : roleGreeting.hindi.replace("नमस्ते!", `नमस्ते ${rawUsername}!`),

            arabic: isGuest
                ? roleGreeting.arabic
                : roleGreeting.arabic.replace("مرحباً!", `مرحباً ${rawUsername}!`),

            russian: isGuest
                ? roleGreeting.russian
                : roleGreeting.russian.replace("Здравствуйте!", `Здравствуйте, ${rawUsername}!`)
        };

        GREETING_TEXT =
            greetings[lang] || greetings.english;

        const greetSlot =
            document.getElementById("riya-greeting-slot-text");

        if (greetSlot) {
            greetSlot.textContent = GREETING_TEXT;
        }

        // ---------------------------------------------------------
        // Check whether this is the first time Buddy is opened.
        // ---------------------------------------------------------
        const hasHistory =
            assistant.responseSlot &&
            assistant.responseSlot.querySelector(
                ".riya-response-card:not(.is-placeholder)"
            );

        // ---------------------------------------------------------
        // Custom Time-Based Guest Greeting
        // ---------------------------------------------------------
        let chatBubbleGreeting = GREETING_TEXT;

        if (isGuest && lang === "english" && sessionStorage.getItem("careerbuddy_guest_greeting_shown") !== "true") {
            const hour = new Date().getHours();
            let timeStr = "Good Evening";
            if (hour >= 5 && hour < 12) timeStr = "Good Morning";
            else if (hour >= 12 && hour < 17) timeStr = "Good Afternoon";
            
            chatBubbleGreeting = "Hi, " + timeStr + "! Are you a Job Seeker or an Employer?";
            sessionStorage.setItem("careerbuddy_guest_greeting_shown", "true");
        }

        // ---------------------------------------------------------
        // FIRST OPEN ONLY:
        // Show and speak the greeting once.
        // ---------------------------------------------------------
        if (!hasHistory) {

            // Remove the HTML placeholder.
            if (assistant.responseSlot) {
                const placeholder =
                    assistant.responseSlot.querySelector(
                        ".riya-response-card.is-placeholder"
                    );

                if (placeholder) {
                    placeholder.remove();
                }
            }

            assistant.lastResponseText = chatBubbleGreeting;

            addConversationMessage("assistant", chatBubbleGreeting);

            renderResponseCard({
                reply: chatBubbleGreeting,
                source: "greeting"
            }, { waitForSpeech: true });

            setAssistantState(AssistantState.GREETING);
            setStatus("Buddy is greeting you.");

            speakText(chatBubbleGreeting, {
                state: AssistantState.GREETING,
                statusText: "Buddy is greeting you.",
            instantBrowserVoice: true,

            // Do NOT automatically start the microphone.
            afterSpeak: null
            });

            // Render welcome content AFTER the greeting card above, so
            // guestLanding's visual+pills (which insert into this SAME
            // #riya-response-slot, not the separate panel) land in the
            // correct order: greeting first, then the visual, then
            // whatever conversation follows. Every other role still
            // renders into the separate panel as before, where order
            // relative to the greeting never mattered.
            renderPersistentWelcome();

            return;
        }

        // ---------------------------------------------------------
        // REOPEN:
        // History already exists.
        // Do NOT add or speak another greeting.
        // Go directly to listening.
        // ---------------------------------------------------------
        renderPersistentWelcome();

        setAssistantState(
            AssistantState.RESPONDING
        );

        setStatus(
            "Click the microphone when you want to speak."
        );
    }


    function clearGuestRoleOnLogout() {
        try {
            // A real logout creates a fresh guest session.
            sessionStorage.removeItem("riya_active_conversation_id");

            // Also remove any role-specific active state so the next
            // guest cannot reopen the previous Student/Employer chat.
            sessionStorage.removeItem(
                "career_buddy_riya_guest_state_v3_guest"
            );
            sessionStorage.removeItem(
                "career_buddy_riya_student_state_v3_guest"
            );
            sessionStorage.removeItem(
                "career_buddy_riya_employer_state_v3_guest"
            );
        } catch (_error) {
            // Ignore storage errors.
        }
    }

    function isLogoutElement(element) {
        if (!element || element === document) {
            return false;
        }

        const tag = String(element.tagName || "").toLowerCase();

        const href =
            String(element.getAttribute?.("href") || "")
                .toLowerCase();

        const action =
            String(element.getAttribute?.("action") || "")
                .toLowerCase();

        const id =
            String(element.id || "")
                .toLowerCase();

        const name =
            String(element.getAttribute?.("name") || "")
                .toLowerCase();

        const dataAction =
            String(element.getAttribute?.("data-action") || "")
                .toLowerCase();

        const dataLogout =
            String(element.getAttribute?.("data-logout") || "")
                .toLowerCase();

        const text =
            String(element.textContent || "")
                .replace(/\s+/g, " ")
                .trim()
                .toLowerCase();

        if (
            href.includes("logout") ||
            action.includes("logout") ||
            id.includes("logout") ||
            name.includes("logout") ||
            dataAction === "logout" ||
            dataLogout === "logout"
        ) {
            return true;
        }

        // Covers dropdown buttons/links whose visible label is simply
        // "Logout", even when they have no logout-specific attribute.
        if (
            text === "logout" ||
            text === "log out" ||
            text === "sign out" ||
            text === "logout "
        ) {
            return true;
        }

        // If a submit button says Logout, its parent form is the logout
        // operation even when the form action is generic.
        if (
            tag === "button" ||
            tag === "input"
        ) {
            const inputValue =
                String(
                    element.getAttribute?.("value") || ""
                )
                    .trim()
                    .toLowerCase();

            if (
                inputValue === "logout" ||
                inputValue === "log out" ||
                inputValue === "sign out"
            ) {
                return true;
            }
        }

        return false;
    }

    function bindLogoutRoleReset() {
        // Event delegation is intentional:
        // logout buttons/dropdowns may be created after the chatbot
        // script has already loaded.
        if (document.documentElement.dataset.riyaLogoutDelegation === "1") {
            return;
        }

        document.documentElement.dataset.riyaLogoutDelegation = "1";

        document.addEventListener(
            "click",
            (event) => {
                const target =
                    event.target?.closest?.(
                        'a,button,input,[role="button"],[data-action],[data-logout]'
                    );

                if (!target) {
                    return;
                }

                const form =
                    target.closest?.("form");

                if (
                    isLogoutElement(target) ||
                    isLogoutElement(form)
                ) {
                    clearGuestRoleOnLogout();
                }
            },
            true
        );

        document.addEventListener(
            "submit",
            (event) => {
                const form = event.target;

                if (isLogoutElement(form)) {
                    clearGuestRoleOnLogout();
                }
            },
            true
        );
    }

    function startNewChat() {
        // Explicit reset only. Normal navigation and closing Buddy never
        // call this function.
        stopVoiceRecording("close");
        releaseMicrophoneResources();
        stopSpeaking();

        clearSilenceTimer();
        clearAutoListenTimer();

        assistant.conversationId = createConversationId();
        assistant.conversationHistory = [];
        assistant.lastResponseText = "";

        if (assistant.responseSlot) {
            assistant.responseSlot.innerHTML = "";
        }

        persistAssistantSession({
            isOpen: false,
            chatHistory: "",
            lastResponseText: "",
            conversationHistory: [],
            conversationId: assistant.conversationId,
            updatedAt: Date.now(),
        });

        setAssistantState(AssistantState.CLOSED);
        resetToContextView();
    }

    function closeChat() {
        stopVoiceRecording("close");

        releaseMicrophoneResources();

        // Closing the chat is the one action that DOES cancel an announced
        // navigation — the user has visibly changed their mind.
        clearNavigationCommitment();
        assistant.navigationDone = true;

        stopSpeaking();

        assistant.ttsSpeaking = false;
        assistant.microphoneBlockedByTTS = false;

        clearSilenceTimer();
        clearAutoListenTimer();
        setHistoryOpen(false);
        revealPendingCard();

        if (assistant.streamPersistTimer) {
            clearTimeout(assistant.streamPersistTimer);
            assistant.streamPersistTimer = null;
        }

        // IMPORTANT:
        // Do NOT call resetToContextView().
        // The conversation history must remain visible
        // when Buddy is reopened.

        setAssistantState(
            AssistantState.CLOSED
        );

        persistAssistantSession({
            isOpen: false,
            lastResponseText:
                assistant.lastResponseText
        });

        if (assistant.launcher) {
            assistant.launcher.focus();
        }
    }

    function toggleVoiceRecording() {

        // Don't interfere with an active AI request.
        if (
            assistant.state ===
            AssistantState.PROCESSING
        ) {
            return;
        }

        // If Buddy is closed, open it.
        // IMPORTANT: openChat() should NOT start the mic.
        if (
            assistant.state ===
            AssistantState.CLOSED
        ) {
            openChat();
            return;
        }

        // ---------------------------------------------------------
        // MIC IS CURRENTLY ON
        // Clicking the button again = STOP
        // ---------------------------------------------------------
        if (
            assistant.state ===
            AssistantState.LISTENING
        ) {
            stopVoiceRecording("manual");
            return;
        }

        // ---------------------------------------------------------
        // MIC IS OFF
        // Clicking Speak = START
        // ---------------------------------------------------------
        startVoiceRecording();
    }

    function handleChip(_button, chip) {
        if (!chip) {
            return;
        }

        const action =
            typeof chip === "string"
                ? null
                : {
                    key: chip.key,
                    route: chip.route,
                    response: chip.label,
                    label: chip.label,
                };

        if (!action) {
            renderPayload(buildFallbackPayload());
            return;
        }

        if (!isActionAllowedForCurrentRole(action.key)) {
            const guard = {
                reply: assistant.isEmployer
                    ? "That is a Student / Job Seeker feature. I will keep you in the Employer portal."
                    : "That is an Employer feature. I will keep you in the Student / Job Seeker portal.",
                source: "role_guard",
            };

            addConversationMessage("assistant", guard.reply);

            renderPayload(guard, {
                statusText: assistant.isEmployer
                    ? "Employer Buddy is staying in the Employer portal."
                    : "Student Buddy is staying in the Student portal.",
            });

            return;
        }

        renderPayload(
            {
                reply: action.response,
                actions: buildActions([action.key]),
                source: "intent",
            },
            {
                statusText: "Quick route ready.",
            }
        );

        window.setTimeout(() => {
            performAction(action);
        }, 500);
    }

    function handleKeydown(event) {
        if (event.key === "Escape" && assistant.state !== AssistantState.CLOSED) {
            closeChat();
        }
    }

    function updateGreetingHistoryCard(newGreeting) {
        const slot = assistant.responseSlot;

        if (!slot) {
            return;
        }

        // Find the first normal Buddy response.
        // This is our permanent greeting card.
        const greetingCard =
            slot.querySelector(
                ".riya-response-card:not(.riya-user-transcript):not(.is-thinking):not(#riya-stream-card)"
            );

        if (!greetingCard) {
            return;
        }

        const text = greetingCard.querySelector("p");

        if (text) {
            text.textContent = newGreeting;
        }
    }

    function applyLanguageChange(language) {
        const selectedLanguage =
            String(language || "english").toLowerCase();

        const langMap = {
            english: "en-US",
            vietnam: "vi-VN",
            hindi: "hi-IN",
            arabic: "ar-SA",
            russian: "ru-RU"
        };

        // ---------------------------------------------------------
        // HARD LANGUAGE TRANSITION
        // ---------------------------------------------------------
        assistant.languageChangeInProgress = true;
        assistant.languageChangeGeneration += 1;

        const changeGeneration =
            assistant.languageChangeGeneration;

        // Cancel anything waiting to start Listening.
        clearAutoListenTimer();
        clearSilenceTimer();

        // Prevent old recognition/media callbacks from processing
        // the previous language.
        assistant.voiceTurnHandled = true;
        assistant.pendingBackendTranscript = false;

        // Stop current microphone/recognition.
        if (assistant.recognitionRunning) {
            assistant.recognitionStopReason = "language_change";

            try {
                assistant.recognition.stop();
            } catch (_error) {
                assistant.recognitionRunning = false;
            }
        }

        if (
            assistant.mediaRecorder &&
            assistant.mediaRecorder.state !== "inactive"
        ) {
            assistant.mediaStopReason = "language_change";

            try {
                assistant.mediaRecorder.stop();
            } catch (_error) {
                // Ignore; onstop will clean up.
            }
        }

        // Hide Listening immediately.
        setMicIndicatorVisible(false);

        // Stop any currently playing speech.
        stopSpeaking();

        // ---------------------------------------------------------
        // Change recognition language
        // ---------------------------------------------------------
        if (assistant.recognition) {
            assistant.recognition.lang =
                langMap[selectedLanguage] || "en-US";
        }

        // ---------------------------------------------------------
        // Get username
        // ---------------------------------------------------------
        const username = getDisplayName();

        const isGuest = !username;

        // ---------------------------------------------------------
        // Greetings
        // ---------------------------------------------------------
        const roleGreeting = getRoleContext().greeting;
        const roleBubbleGreeting = getRoleContext().bubble;

        const greetings = {
            english: isGuest
                ? roleGreeting.english
                : roleGreeting.english.replace(
                    "Hello there!",
                    `Hello ${username}!`
                ),

            vietnam: isGuest
                ? roleGreeting.vietnam
                : roleGreeting.vietnam.replace(
                    "Xin chào!",
                    `Xin chào ${username}!`
                ),

            hindi: isGuest
                ? roleGreeting.hindi
                : roleGreeting.hindi.replace(
                    "नमस्ते!",
                    `नमस्ते ${username}!`
                ),

            arabic: isGuest
                ? roleGreeting.arabic
                : roleGreeting.arabic.replace(
                    "مرحباً!",
                    `مرحباً ${username}!`
                ),

            russian: isGuest
                ? roleGreeting.russian
                : roleGreeting.russian.replace(
                    "Здравствуйте!",
                    `Здравствуйте, ${username}!`
                )
        };

        const bubbleGreetings = {
            english: isGuest
                ? roleBubbleGreeting.english
                : `Hello ${username}!`,

            vietnam: isGuest
                ? roleBubbleGreeting.vietnam
                : `Xin chào ${username}!`,

            hindi: isGuest
                ? roleBubbleGreeting.hindi
                : `नमस्ते ${username}!`,

            arabic: isGuest
                ? roleBubbleGreeting.arabic
                : `مرحباً ${username}!`,

            russian: isGuest
                ? roleBubbleGreeting.russian
                : `Здравствуйте, ${username}!`
        };

        const newGreeting =
            greetings[selectedLanguage] ||
            greetings.english;

        const newBubbleGreeting =
            bubbleGreetings[selectedLanguage] ||
            bubbleGreetings.english;

        GREETING_TEXT = newGreeting;

        // ---------------------------------------------------------
        // Update floating greeting
        // ---------------------------------------------------------
        const greetingText =
            document.getElementById("riya-greeting-text");

        if (greetingText) {
            greetingText.textContent =
                newBubbleGreeting;
        }

        // ---------------------------------------------------------
        // Update greeting inside chatbot
        // ---------------------------------------------------------
        const greetingSlot =
            document.getElementById(
                "riya-greeting-slot-text"
            );

        if (greetingSlot) {
            greetingSlot.textContent =
                newGreeting;
        }

        // Update the ONE greeting already shown in chat.
        // Do not create another history message.
        updateGreetingHistoryCard(newGreeting);

        // Update recommendation pills to the new language.
        refreshPersistentWelcome();

        // ---------------------------------------------------------
        // If Buddy was closed, don't restart anything.
        // ---------------------------------------------------------
        if (assistant.state === AssistantState.CLOSED) {
            assistant.languageChangeInProgress = false;
            return;
        }

        // ---------------------------------------------------------
        // Language changed.
        // Keep existing conversation history.
        // Do not add another greeting.
        // ---------------------------------------------------------
        clearTranscript();
        resetRecognitionBuffers();

        // ---------------------------------------------------------
        // IMPORTANT:
        // After language change Buddy must WAIT.
        // It must NOT automatically start listening.
        // ---------------------------------------------------------
        setAssistantState(
            AssistantState.RESPONDING
        );

        setStatus(
            "Language changed. Click the microphone when you want to speak."
        );

        // ---------------------------------------------------------
        // Wait for old recognition/media callbacks to finish.
        // ---------------------------------------------------------
        window.setTimeout(() => {

            // Another language was selected while waiting.
            if (
                changeGeneration !==
                assistant.languageChangeGeneration
            ) {
                return;
            }

            if (
                assistant.state === AssistantState.CLOSED
            ) {
                assistant.languageChangeInProgress = false;
                return;
            }

            // Make absolutely sure old microphone state is gone.
            assistant.recognitionRunning = false;
            assistant.pendingBackendTranscript = false;
            assistant.voiceTurnHandled = true;

            // -----------------------------------------------------
            // DO NOT START MICROPHONE HERE.
            //
            // User must click 🎤 manually.
            // -----------------------------------------------------

            assistant.languageChangeInProgress = false;
            assistant.microphoneBlockedByTTS = false;

            setAssistantState(
                AssistantState.RESPONDING
            );

            setStatus(
                "Language changed. Click the microphone when you want to speak."
            );

        }, 80);
    }


    // ============================================================
    // BUDDY TEXT INPUT
    // ============================================================
    // IMPORTANT:
    // Text is NOT a second chatbot. It enters the exact same
    // processTranscript(text, inputMode) pipeline as voice.
    function sendTextMessage() {
        if (!assistant.textInput) {
            return;
        }

        // Don't interfere with an active AI request.
        if (assistant.state === AssistantState.PROCESSING) {
            return;
        }

        const cleanText =
            String(assistant.textInput.value || "")
                .replace(/\s+/g, " ")
                .trim();

        if (!cleanText) {
            assistant.textInput.focus();
            return;
        }

        // Stop voice capture if it is currently running.
        if (assistant.recognitionRunning) {
            assistant.recognitionStopReason = "text_input";

            try {
                assistant.recognition.stop();
            } catch (_error) {
                assistant.recognitionRunning = false;
            }
        }

        if (
            assistant.mediaRecorder &&
            assistant.mediaRecorder.state !== "inactive"
        ) {
            assistant.mediaStopReason = "text_input";

            try {
                assistant.mediaRecorder.stop();
            } catch (_error) {
                // onstop will clean up the stream.
            }
        }

        clearSilenceTimer();
        clearAutoListenTimer();

        // If Buddy is speaking, stop it before processing typed input.
        if (assistant.ttsSpeaking) {
            stopSpeaking();
        }

        assistant.voiceTurnHandled = true;
        assistant.pendingBackendTranscript = false;

        // Display the typed user message in the existing conversation UI.
        // processTranscript() will store the same message in conversationHistory.
        showTranscript(cleanText);

        // THE IMPORTANT PART:
        // Use the same pipeline as voice.
        processTranscript(cleanText, "text");

        assistant.textInput.value = "";
        assistant.textInput.focus();
    }

    function bindEvents() {
        assistant.ttsAudio.preload = "auto";
        assistant.ttsAudio.playsInline = true;
        assistant.ttsAudio.onended = finalizeSpeech;
        assistant.ttsAudio.onerror = finalizeSpeech;
        // The voice is audible: show the text it is reading.
        assistant.ttsAudio.addEventListener("playing", revealPendingCard);

        if (assistant.micButton) {
            assistant.micButton.addEventListener(
                "click",
                function () {
                    toggleVoiceRecording();
                }
            );
        }

        if (assistant.speakerButton) {
            assistant.speakerButton.addEventListener(
                "click",
                function (event) {
                    event.preventDefault();
                    onSpeakerButtonClick();
                }
            );
        }

        // Text input uses the same processTranscript() flow as voice.
        if (assistant.textForm) {
            assistant.textForm.addEventListener(
                "submit",
                function (event) {
                    event.preventDefault();
                    sendTextMessage();
                }
            );
        }

        if (assistant.textInput) {
            assistant.textInput.addEventListener(
                "keydown",
                function (event) {
                    if (event.key === "Enter") {
                        event.preventDefault();

                        if (assistant.textForm) {
                            assistant.textForm.requestSubmit();
                        } else {
                            sendTextMessage();
                        }
                    }
                }
            );
        }

        document.addEventListener("keydown", handleKeydown);

        const historyButton = document.getElementById("riya-history-button");
        if (historyButton) {
            historyButton.addEventListener("click", () => {
                setHistoryOpen(historyButton.getAttribute("aria-expanded") !== "true");
            });
        }
        const historyClose = document.getElementById("riya-history-close");
        if (historyClose) {
            historyClose.addEventListener("click", () => setHistoryOpen(false));
        }

        // Same-page moves (Skill Up's #depth-*, the dashboard's
        // #recommended-jobs) don't reload, so re-derive the section here to
        // keep the follow-up cards in step with where the user now is.
        window.addEventListener("hashchange", refreshPersistentWelcome);

        document.addEventListener(
            "riyaLanguageChanged",
            function (event) {

                const language =
                    event.detail?.language ||
                    "english";

                applyLanguageChange(language);
            }
        );

        const langSelect = document.getElementById('chatbotLanguageSelect');
        if (langSelect) {
            const savedLang = sessionStorage.getItem('riya_chatbot_lang');
            if (savedLang) {
                langSelect.value = savedLang;
            }

            // On load, apply any existing language if needed
            if (savedLang && window.applyGlobalTranslations) {
                window.applyGlobalTranslations(savedLang);
            }

            langSelect.addEventListener('change', () => {
                sessionStorage.setItem('riya_chatbot_lang', langSelect.value);
                refreshPersistentWelcome();
                applyUiText();
                if (window.applyGlobalTranslations) {
                    window.applyGlobalTranslations(langSelect.value);
                }

                // Never keep the old language microphone session alive
                // after the user changes language.
                if (assistant.recognitionRunning) {
                    assistant.recognitionStopReason = "language_change";
                    try {
                        assistant.recognition.stop();
                    } catch (_error) { }
                }

                if (
                    assistant.mediaRecorder &&
                    assistant.mediaRecorder.state !== "inactive"
                ) {
                    assistant.mediaStopReason = "language_change";
                    try {
                        assistant.mediaRecorder.stop();
                    } catch (_error) { }
                }

                assistant.voiceTurnHandled = true;
                assistant.pendingBackendTranscript = false;
                clearSilenceTimer();

                if (assistant.recognition) {
                    const langMap = {
                        "english": "en-US",
                        "hindi": "hi-IN",
                        "vietnam": "vi-VN",
                        "vietnamese": "vi-VN",
                        "arabic": "ar-SA",
                        "russian": "ru-RU"
                    };
                    assistant.recognition.lang =
                        langMap[langSelect.value] || "en-US";
                }
            });
        }

        // Prevent tab-switching exploit during recording
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
                if (assistant.recognitionRunning || (assistant.mediaRecorder && assistant.mediaRecorder.state === "recording")) {
                    stopVoiceRecording("tab_switch");
                    showError("Recording was paused because you switched tabs.");
                }
            }
        });
    }

    function initializeLauncherModel() {
        if (!assistant.launcher || !assistant.launcherModel) {
            return;
        }

        ensureModelViewerScript()
            .then(() => {
                switchLauncherModel(LAUNCHER_MODEL_VRiyaNTS.idle, { immediate: true });
            })
            .catch(() => {
                assistant.launcher.classList.remove("has-model-loaded");
                assistant.launcher.classList.remove("is-model-switching");
            });
    }

    function cacheElements() {
        assistant.root = document.getElementById("riya-assistant-root");

        // If the page explicitly marks the current user as logged out,
        // never restore a role selected before the previous login.
        if (assistant.root) {
            const authState =
                String(
                    assistant.root.dataset.authenticated ||
                    assistant.root.dataset.loggedIn ||
                    ""
                ).toLowerCase().trim();

            if (
                authState === "false" ||
                authState === "0" ||
                authState === "logged-out" ||
                authState === "guest"
            ) {
                clearGuestRoleOnLogout();
            }
        }

        if (!assistant.root) {
            return false;
        }

        // Prefer explicit role metadata, but automatically detect Employer
        // pages from the URL so no template change is required.
        const explicitRole =
            String(assistant.root.dataset.riyaRole || "")
                .toLowerCase()
                .trim();

        const currentPath =
            String(
                assistant.root.dataset.riyaPath ||
                window.location.pathname ||
                ""
            ).toLowerCase();

        const rawUsername =
            String(
                assistant.root.dataset.riyaUsername || ""
            ).trim();

        const userIsGuest =
            !rawUsername ||
            rawUsername.toLowerCase() === "there";

        if (userIsGuest) {
            // We no longer clear guest-state keys on page load because guests
            // now retain their conversation history across public pages.
        }

        const employerPage =
            explicitRole === "employer" ||
            currentPath === "/employer-home/" ||
            currentPath.startsWith("/employer-home/") ||
            currentPath.startsWith("/employer/");

        if (!userIsGuest) {

            // Logged-in users keep their real portal.
            assistant.isEmployer = employerPage;
            assistant.role =
                assistant.isEmployer
                    ? "employer"
                    : "student";

        } else {
            // Guest role is MEMORY-ONLY.
            // A page load is always a fresh guest.
            assistant.isEmployer = false;
            assistant.role = "guest";
        }

        assistant.launcher = document.getElementById("riya-launcher");
        assistant.launcherModel = document.getElementById("riya-launcher-model");
        assistant.launcherModelIdleSrc = String(assistant.root.dataset.riyaIdleModel || "").trim();
        assistant.launcherModelSpeakingSrc = String(assistant.root.dataset.riyaSpeakingModel || "").trim();
        assistant.bubble = document.getElementById("riya-thought-bubble");
        assistant.statusText = document.getElementById("riya-status-text");
        assistant.micButton =
            document.getElementById("riya-mic-button");

        assistant.micLabel =
            document.getElementById("riya-mic-button-label");

        assistant.speakerButton =
            document.getElementById("riya-speaker-button");

        assistant.textForm =
            document.getElementById("riya-text-form");

        assistant.textInput =
            document.getElementById("riya-text-input");

        assistant.responseSlot = document.getElementById("riya-response-slot");
        assistant.audioBars = document.getElementById("riya-audio-bars");
        assistant.closeButton = document.getElementById("riya-close-button");

        return true;
    }

    function initializeAssistant() {
        // Idempotent: a second call (re-render, back/forward cache restore)
        // would otherwise re-bind every listener and double-fire the greeting.
        if (assistant.initialized) return;
        if (!cacheElements()) return;
        assistant.initialized = true;

        // Set personalized greeting bubble above character
        const rawUsername = getDisplayName();
        const isGuest = !rawUsername;
        const langSelect = document.getElementById('chatbotLanguageSelect');
        const lang = langSelect ? langSelect.value : 'english';

        const roleGreeting = getRoleContext().greeting;
        const roleBubbleGreeting = getRoleContext().bubble;

        const greetings = {
            'english': isGuest
                ? roleGreeting.english
                : roleGreeting.english.replace("Hello there!", `Hello ${rawUsername}!`),

            'vietnam': isGuest
                ? roleGreeting.vietnam
                : roleGreeting.vietnam.replace("Xin chào!", `Xin chào ${rawUsername}!`),

            'hindi': isGuest
                ? roleGreeting.hindi
                : roleGreeting.hindi.replace("नमस्ते!", `नमस्ते ${rawUsername}!`),

            'arabic': isGuest
                ? roleGreeting.arabic
                : roleGreeting.arabic.replace("مرحباً!", `مرحباً ${rawUsername}!`),

            'russian': isGuest
                ? roleGreeting.russian
                : roleGreeting.russian.replace("Здравствуйте!", `Здравствуйте, ${rawUsername}!`)
        };

        const bubbleGreetings = {
            'english': isGuest ? roleBubbleGreeting.english : `Hello ${rawUsername}!`,
            'vietnam': isGuest ? roleBubbleGreeting.vietnam : `Xin chào ${rawUsername}!`,
            'hindi': isGuest ? roleBubbleGreeting.hindi : `नमस्ते ${rawUsername}!`,
            'arabic': isGuest ? roleBubbleGreeting.arabic : `مرحباً ${rawUsername}!`,
            'russian': isGuest ? roleBubbleGreeting.russian : `Здравствуйте, ${rawUsername}!`
        };

        GREETING_TEXT = greetings[lang] || greetings['english'];

        const greetBubble = document.getElementById("riya-greeting-bubble");
        const greetBubbleText = document.getElementById("riya-greeting-text");
        if (greetBubbleText) {
            greetBubbleText.textContent = bubbleGreetings[lang] || bubbleGreetings['english'];
        }
        if (greetBubble) {
            if (sessionStorage.getItem("careerbuddy_bubble_shown") !== "true") {
                greetBubble.style.opacity = "1";
                sessionStorage.setItem("careerbuddy_bubble_shown", "true");
            } else {
                greetBubble.style.opacity = "0";
            }
        }

        // Update the placeholder inside the chat bubble too
        const greetSlot = document.getElementById("riya-greeting-slot-text");
        if (greetSlot) greetSlot.textContent = GREETING_TEXT;

        initializeSpeechRecognition();
        initializeLauncherModel();
        bindEvents();
        resetToContextView();
        setAssistantState(AssistantState.CLOSED);

        // Restore chat history from session if available
        const previousSession = readAssistantSession();

        assistant.conversationId =
            previousSession?.conversationId ||
            createConversationId();

        assistant.conversationHistory =
            Array.isArray(previousSession?.conversationHistory)
                ? previousSession.conversationHistory
                : [];

        if (
            previousSession &&
            previousSession.chatHistory &&
            assistant.responseSlot
        ) {
            assistant.responseSlot.innerHTML =
                previousSession.chatHistory;
            // Saved mid-reply (navigation): show held text, drop stale dots.
            assistant.responseSlot.querySelectorAll(".riya-response-card[hidden]")
                .forEach((card) => { card.hidden = false; });
            assistant.responseSlot.querySelectorAll(".is-thinking, #riya-stream-card")
                .forEach((card) => card.remove());
            // The restored HTML includes the previous page's stage: show THIS page's topic pills.
            refreshLandingStageNodes();

            assistant.lastResponseText =
                previousSession.lastResponseText || "";
        }

        if (previousSession && previousSession.isOpen) {
            // Restore assistant open state
            openChat();
        }

        // If narration was cut short by a navigation, continue it here.
        resumePendingSpeech();
        applyUiText();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeAssistant);
    } else {
        initializeAssistant();
    }

    window.openChat = openChat;
    window.closeChat = closeChat;
    window.startNewChat = startNewChat;
    window.toggleVoiceRecording = toggleVoiceRecording;
    window.sendTextMessage = sendTextMessage;
    window.handleChip = handleChip;
    window.closeLauncherBubble = closeLauncherBubble;
    window.speakBotText = speakBotText;

    // Called from inside the IIFE: bindLogoutRoleReset is declared in this
    // closure, so the previous call after `})();` was a ReferenceError on
    // every page load and the logout role reset never actually bound.
    bindLogoutRoleReset();
})();
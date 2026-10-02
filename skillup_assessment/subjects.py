"""
Dynamic certification-subject registry (spec section 23: "Dynamic
Architecture" -- do not hardcode subject counts anywhere).

Single source of truth for every subject a certificate can be earned for.
Built FROM the real quiz registries in activities.views (_QUIZ_SUBJECTS,
plus the two standalone AMCAT/CoCubes endpoints) rather than duplicating a
hardcoded list -- if a new subject is added to _QUIZ_SUBJECTS, it appears
here automatically with no code change required, satisfying spec section 5
("if another Tech quiz is added later, the Certifications system should
automatically recognize it").

Three categories, matching the spec's structure exactly:
    english  -> English & Vocabulary (1 subject: 'english')
    aptitude -> Aptitude & Reasoning (3 subjects: aptitude, amcat, cocubes)
    tech     -> Tech Center (every other subject in _QUIZ_SUBJECTS)

Human-readable labels for the tech subjects are kept in one small mapping
here (question banks only have machine keys like 'dsa', 'nltk'); anything
present in _QUIZ_SUBJECTS but missing from this map still shows up (title-
cased from its key) rather than being silently dropped, so a newly added
subject is never invisible even before someone adds a nicer label for it.
"""
from activities.views import _QUIZ_SUBJECTS

CATEGORY_LABELS = {
    "english": "English & Vocabulary",
    "aptitude": "Aptitude & Reasoning",
    "tech": "Tech Center",
}

# Subjects that get their own named category rather than falling into Tech.
_NON_TECH = {"english", "aptitude"}

# Nicer display names for tech subjects than their raw registry keys.
_TECH_LABELS = {
    "python": "Python", "dsa": "DSA", "oop": "OOP", "devops": "DevOps",
    "claude": "Claude Code", "uiux": "UI/UX Design",
    "design": "Design Classification", "vector": "Vector Databases",
    "nltk": "NLTK NLP", "dbms": "DBMS", "prompt": "Prompt Engineering",
    "genai": "GenAI", "crewai": "CrewAI", "quantum": "Quantum Computing",
    "vr": "Virtual Reality", "robotics": "Robotics", "nodejs": "Node.js",
    "mlops": "MLOps", "ethical": "Ethical Hacking",
    "tensorflow": "TensorFlow & PyTorch", "cyber": "Cybersecurity",
    "blockchain": "Blockchain", "crypto": "Cryptography",
}

PASS_THRESHOLD_PCT = 70  # spec section 2: score >= 70 -> eligible (inclusive)


def _build_registry():
    registry = {
        "english": {"label": "English & Vocabulary", "category": "english"},
        "aptitude": {"label": "Aptitude Mock Test", "category": "aptitude"},
        "amcat": {"label": "AMCAT Mock Test", "category": "aptitude"},
        "cocubes": {"label": "CoCubes Mock Test", "category": "aptitude"},
    }
    for key in _QUIZ_SUBJECTS:
        if key in _NON_TECH:
            continue  # already registered above under its own category
        registry[key] = {
            "label": _TECH_LABELS.get(key, key.replace("_", " ").title()),
            "category": "tech",
        }
    return registry


SUBJECTS = _build_registry()


def is_valid_subject(key):
    return key in SUBJECTS


def subjects_by_category():
    """Returns {category_key: [(subject_key, label), ...]}, tech subjects
    sorted alphabetically by label for a stable, scannable display order.
    """
    out = {"english": [], "aptitude": [], "tech": []}
    for key, meta in SUBJECTS.items():
        out[meta["category"]].append((key, meta["label"]))
    out["tech"].sort(key=lambda pair: pair[1])
    # Keep a stable, spec-matching order for aptitude's fixed 3.
    aptitude_order = {"aptitude": 0, "amcat": 1, "cocubes": 2}
    out["aptitude"].sort(key=lambda pair: aptitude_order.get(pair[0], 99))
    return out


def total_certification_opportunities():
    return len(SUBJECTS)

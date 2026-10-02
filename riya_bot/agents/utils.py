import hashlib
import json
import logging
import re
import requests
import base64
import io
from django.conf import settings
from django.core.cache import caches
from django.core.files.base import ContentFile
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

logger = logging.getLogger(__name__)
# A large share of Buddy's replies are fixed strings (greetings, "Opening the
# activities page.", etc. — see FAST_REPLY_PATTERNS / ACTION_DEFINITIONS in
# riya_assistant.py) that produce byte-for-byte identical audio every time.
# Caching on (text, language, speaker) turns every repeat of one of those into
# a cache hit instead of a fresh ~1-3s round trip to Sarvam's TTS endpoint.
# 7 days is generous for how static this text is; short enough that a wording
# change doesn't linger indefinitely.
TTS_CACHE_TIMEOUT_SECONDS = 60 * 60 * 24 * 7
LANGUAGE_TOOL_API_URL = "https://api.languagetool.org/v2/check"
LANGUAGE_TOOL_SUPPORTED_MODULES = {"writing", "speaking", "listening", "interview"}

TOPIC_PRACTICE_CONFIG = {
    "storytelling": {
        "slug": "storytelling",
        "page_title": "Storytelling Practice",
        "page_description": "Read one short AI story and answer three simple questions below.",
        "input_label": "Story idea",
        "input_placeholder": "A rainy school day, a missing key, a brave child...",
        "button_label": "Tell Story",
        "default_prompt": "a school picnic with a surprise ending",
        "content_heading_label": "Short story",
        "follow_ups_label": "Questions",
        "coach_tip_label": "Coach tip",
        "examples": ["A shy singer on stage", "A rainy day at school", "A puppy in the park"],
    },
    "situations": {
        "slug": "situations",
        "page_title": "Situation Practice",
        "page_description": "Get one real-life speaking situation and practice short responses.",
        "input_label": "Situation idea",
        "input_placeholder": "At the airport, asking for help, ordering food...",
        "button_label": "Create Situation",
        "default_prompt": "asking for help at a railway station",
        "content_heading_label": "Practice situation",
        "follow_ups_label": "Try answering these",
        "coach_tip_label": "Coach tip",
        "examples": ["At the airport", "Speaking to a teacher", "Returning an item at a shop"],
    },
    "roleplay": {
        "slug": "roleplay",
        "page_title": "Roleplay Practice",
        "page_description": "Start a short roleplay scene and reply in your own words.",
        "input_label": "Roleplay idea",
        "input_placeholder": "Student and teacher, customer and cashier, teammate and manager...",
        "button_label": "Start Roleplay",
        "default_prompt": "student asking a teacher for more project time",
        "content_heading_label": "Roleplay scene",
        "follow_ups_label": "Reply to these lines",
        "coach_tip_label": "Coach tip",
        "examples": ["Customer asking for a refund", "Friend inviting you to an event", "Employee asking for leave"],
    },
}

def get_topic_practice_config(topic_slug):
    return TOPIC_PRACTICE_CONFIG.get(str(topic_slug or "").strip().lower())

def trim_text(value, fallback, limit):
    text = str(value or "").strip()
    if not text: text = fallback
    return text[:limit]

def normalize_follow_ups(items, fallback_items):
    normalized = []
    for item in items or []:
        text = str(item or "").strip()
        if text: normalized.append(text[:160])
    return normalized[:3] if len(normalized) >= 3 else fallback_items

def fallback_topic_practice(topic, prompt):
    safe_prompt = str(prompt or "").strip() or topic["default_prompt"]
    prompt_label = safe_prompt.strip().rstrip(".")
    title_text = prompt_label[:1].upper() + prompt_label[1:] if prompt_label else topic["page_title"]

    if topic["slug"] == "storytelling":
        return {
            "title": title_text,
            "intro": "Read the story once, then answer the questions in short sentences.",
            "content_heading": topic["content_heading_label"],
            "content": (
                f"One afternoon, Anika found herself in the middle of {safe_prompt}. "
                "She paused for a moment, took a deep breath, and decided to face the situation bravely. "
                "By the end of the day, she had learned something important about herself and the world around her."
            ),
            "follow_ups": [
                "Who is the main character?",
                f"What happened during {safe_prompt}?",
                "What is the lesson of the story?",
            ],
            "coach_tip": "Answer in 1 or 2 clear sentences.",
        }
    if topic["slug"] == "situations":
        return {
            "title": title_text,
            "content_heading": topic["content_heading_label"],
            "content": (
                f"You are in this situation: {safe_prompt}. "
                "Think about what you would say and how you would handle it politely and clearly."
            ),
            "follow_ups": [
                f"How would you start the conversation for: {safe_prompt}?",
                "What polite phrases would you use?",
                "How would you end the conversation confidently?",
            ],
            "coach_tip": "Keep your responses short, polite, and clear.",
        }
    # roleplay fallback
    return {
        "title": title_text,
        "content_heading": topic["content_heading_label"],
        "content": f"Roleplay scene: {safe_prompt}. Take on your role and respond naturally.",
        "follow_ups": [
            "How would you introduce yourself in this roleplay?",
            "What would you say if the other person disagrees?",
            "How would you end this conversation politely?",
        ],
        "coach_tip": "Stay in character and speak naturally.",
    }

def topic_practice_with_sarvam_chat(topic, prompt, api_key, language="english"):
    safe_prompt = str(prompt or "").strip() or topic["default_prompt"]
    topic_type = topic["slug"]

    from core.agents.utils import language_directive

    system_prompt = f"""You are an elite Business English Coach.
Generate a short {topic_type} session for a student.
Topic: {safe_prompt}

Return ONLY a JSON object with:
- "title": A catchy title
- "content_heading": "{topic['content_heading_label']}"
- "content": A short intro or story (max 3 sentences)
- "follow_ups": EXACTLY 5 specific questions to ask the student one by one.
- "coach_tip": One high-value tip for this topic.

Example JSON structure:
{{
  "title": "...",
  "content_heading": "...",
  "content": "...",
  "follow_ups": ["q1", "q2", "q3", "q4", "q5"],
  "coach_tip": "..."
}}{language_directive(language)}"""

    try:
        response = requests.post(
            SARVAM_CHAT_URL,
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": api_key
            },
            json={
                "model": getattr(settings, 'SARVAM_MODEL', 'sarvam-105b'),
                "messages": [{"role": "user", "content": system_prompt}],
                "temperature": 0.5,
                "reasoning_effort": None
            },
            timeout=30
        )
        response.raise_for_status()
        raw_content = response.json()["choices"][0]["message"]["content"]
        # Remove <think> blocks
        raw_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
        
        # Clean potential markdown fences
        clean_json = re.sub(r"```json|```", "", raw_content).strip()
        
        try:
            return json.loads(clean_json)
        except json.JSONDecodeError:
            # Fallback: extract just the JSON block
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {}
    except Exception as e:
        print(f"Sarvam Chat Error: {e}")
        return {}

SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text-translate"

# Move constants here
HEURISTIC_SINGULAR_VERBS = {
    "ask", "come", "dream", "encourage", "face", "find", "forget", "give", "help", "inspire",
    "learn", "look", "maintain", "need", "put", "read", "say", "show", "speak", "support",
    "teach", "try", "want", "watch", "work", "write",
}

SINGULAR_NOUN_VERBS = set(HEURISTIC_SINGULAR_VERBS) | {
    "seem", "take",
}

SINGULAR_NOUN_HEAD_HINTS = {
    "belief", "dream", "goal", "idea", "mother", "path", "plan", "story", "teacher",
    "ability", "potential", "influence", "passion", "purpose"
}

COMMON_SPELLING_FIXES = {
    "freind": "friend", "responsiblities": "responsibilities", "encourges": "encourages",
    "positve": "positive", "situatons": "situations", "determinatons": "determinations",
    "resilence": "resilience", "perseverence": "perseverance", "receve": "receive",
    "belive": "believe", "definatly": "definitely", "occurance": "occurrence",
    "determinationing": "determination", "unwaver": "unwavering", "guiding": "guide",
    "responsiblity": "responsibility", "freinds": "friends", "happines": "happiness",
    "sucess": "success", "lissen": "listen", "truley": "truly",
    "hardwroking": "hardworking", "littel": "little", "pacience": "patience",
    "drinkin": "drinking",
}

LANGUAGETOOL_ALLOWED_WORDS = {
    "anime", "geisha", "gion", "inari", "kyoto", "matcha", "taisha", "tokyo",
}

WRITING_REPLACEMENTS = [
    (r"\bincluded raise\b", "including raising"),
    (r"\bincluded\b", "including"),
    (r"\bdeterminationing\b", "determination"),
    (r"\bwatch her\b", "watched her"),
    (r"\bwatch him\b", "watched him"),
    (r"\bwatch them\b", "watched them"),
    (r"\bgrate advise\b", "great advice"),
    (r"\bgrate role model\b", "great role model"),
    (r"\bhe always take\b", "he always takes"),
    (r"\bshe always take\b", "she always takes"),
    (r"\bit always take\b", "it always takes"),
    (r"\bI can just relaxing\b", "I can just relax"),
]

def _transcribe_with_sarvam(audio_base64, mime_type="audio/webm", language_code="en-IN"):
    """
    Helper for views to transcribe base64 audio directly.
    """
    try:
        api_key = getattr(settings, "SARVAM_API_KEY", "")
        if not api_key:
            return "", {}, {"message": "Missing API Key", "status": 500}
        
        # Decode base64
        format, imgstr = audio_base64.split(';base64,') if ';base64,' in audio_base64 else (None, audio_base64)
        ext = mime_type.split('/')[-1] if '/' in mime_type else 'webm'
        audio_data = base64.b64decode(imgstr)
        
        # Create a file-like object
        audio_file = ContentFile(audio_data, name=f"temp_speech.{ext}")
        audio_file.content_type = mime_type
        
        return transcribe_with_sarvam(audio_file, api_key, language_code)
    except Exception as e:
        return "", {}, {"message": str(e), "status": 500}

def transcribe_with_sarvam(audio_file, api_key, language_code="en-IN"):
    try:
        response = requests.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": api_key},
            files={"file": (audio_file.name, audio_file.read(), audio_file.content_type)},
            data={"language_code": language_code},
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("transcript", ""), data, None
    except Exception as e:
        return "", {}, {"message": str(e), "status": 500}

def clamp_score(value, fallback=70):
    try:
        val = int(float(value))
        return max(0, min(100, val))
    except (ValueError, TypeError):
        return fallback

def merge_issues(primary, secondary, max_count=50):
    merged = list(primary)
    existing_phrases = {i["phrase"].lower() for i in merged}
    for issue in secondary:
        if len(merged) >= max_count:
            break
        if issue["phrase"].lower() not in existing_phrases:
            merged.append(issue)
            existing_phrases.add(issue["phrase"].lower())
    return merged[:max_count]

def has_meaningful_speech(text):
    if not text:
        return False
    # Unicode-aware tokenization: Hindi/Telugu/Arabic/Russian/Vietnamese
    # transcripts must not be rejected just because they are not ASCII.
    words = re.findall(r"[\w\u00C0-\u024F\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0B80-\u0BFF\u0C00-\u0C7F]+", str(text), flags=re.UNICODE)
    return len(words) >= 2

def to_third_person_singular(verb):
    lower = str(verb or "").strip().lower()
    if not lower: return lower
    irregular = {"be": "is", "do": "does", "go": "goes", "have": "has"}
    if lower in irregular: return irregular[lower]
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return f"{lower[:-1]}ies"
    if lower.endswith(("ch", "sh", "s", "x", "z", "o")):
        return f"{lower}es"
    return f"{lower}s"

def match_replacement_case(replacement, original):
    if not original:
        return replacement
    if original.isupper():
        return replacement.upper()
    return replacement

def subject_head_for_agreement(subject_phrase):
    words = re.findall(r"[A-Za-z']+", subject_phrase or "")
    if not words:
        return ""
    preposition_markers = {"in", "of", "with", "for", "to", "about"}
    relative_pronouns = {"who", "that", "which"}
    core_subject_words = []
    for word in words:
        if word.lower() in preposition_markers:
            break
        core_subject_words.append(word)
    subject_words = core_subject_words or words
    if len(subject_words) >= 2 and subject_words[-1].lower() in relative_pronouns:
        return subject_words[-2].lower()
    return subject_words[-1].lower()

def expected_article(word):
    if not word:
        return None
    lower = word.lower()
    ARTICLE_VOWEL_EXCEPTIONS = {"user", "university", "unique", "unit", "use", "useful", "usual", "euro", "one", "once"}
    ARTICLE_SILENT_H = {"hour", "honest", "honor", "heir", "herb"}
    if lower in ARTICLE_VOWEL_EXCEPTIONS:
        return "a"
    if lower in ARTICLE_SILENT_H:
        return "an"
    return "an" if lower[0] in "aeiou" else "a"

def replace_with_case(text, pattern, replacement):
    def _replacer(match):
        return match_replacement_case(replacement, match.group(0))
    return re.sub(pattern, _replacer, text, flags=re.IGNORECASE)

def normalize_text_for_analysis(text):
    return str(text or "").replace("\u2019", "'").replace("\u2018", "'")

def normalize_spacing_and_punctuation(text):
    corrected = str(text or "")
    corrected = re.sub(r"\s+([,.;:!?])", r"\1", corrected)
    corrected = re.sub(r"([,.;:!?])(?=[A-Za-z])", r"\1 ", corrected)
    corrected = re.sub(r"\s{2,}", " ", corrected)
    corrected = re.sub(r"\n{3,}", "\n\n", corrected)
    return corrected.strip()

def should_keep_languagetool_match(match):
    rule = match.get("rule", {})
    rule_id = str(rule.get("id", "")).upper()
    category_id = str(rule.get("category", {}).get("id", "")).upper()
    issue_type = str(rule.get("issueType", "")).lower()
    if category_id in {"TYPOS", "GRAMMAR", "PUNCTUATION", "CASING", "CONFUSED_WORDS"}:
        return True
    if rule_id in {"WANNA"}:
        return True
    if issue_type in {"misspelling", "typographical", "grammar", "punctuation"}:
        return True
    return False

def get_languagetool_issue_type(match):
    rule = match.get("rule", {})
    rule_id = str(rule.get("id", "")).upper()
    category_id = str(rule.get("category", {}).get("id", "")).upper()
    issue_type = str(rule.get("issueType", "")).lower()
    if category_id == "PUNCTUATION" or issue_type == "punctuation":
        return "Punctuation"
    if rule_id in {"WANNA"}:
        return "Grammar"
    if category_id in {"TYPOS", "CASING"} or issue_type in {"misspelling", "typographical"}:
        return "Spelling"
    if category_id in {"GRAMMAR", "CONFUSED_WORDS"} or issue_type == "grammar":
        return "Grammar"
    return "Grammar"

def is_mid_sentence_titlecase_token(text, offset, phrase):
    if not phrase or not phrase[:1].isupper() or offset <= 0:
        return False
    previous_text = str(text or "")[:offset].rstrip()
    if not previous_text:
        return False
    previous_char = previous_text[-1]
    return previous_char not in ".!?\n"

def should_ignore_languagetool_match(text, match):
    rule = match.get("rule", {})
    category_id = str(rule.get("category", {}).get("id", "")).upper()
    issue_type = str(rule.get("issueType", "")).lower()
    if category_id not in {"TYPOS", "CASING"} and issue_type not in {"misspelling", "typographical"}:
        return False

    source = str(text or "")
    offset = int(match.get("offset", 0))
    length = int(match.get("length", 0))
    end = offset + length
    if offset < 0 or length <= 0 or end > len(source):
        return True

    phrase = source[offset:end]
    normalized_phrase = phrase.strip().lower()
    if normalized_phrase in LANGUAGETOOL_ALLOWED_WORDS:
        return True
    if is_mid_sentence_titlecase_token(source, offset, phrase):
        return True

    replacements = match.get("replacements") or []
    if replacements:
        suggestion = str(replacements[0].get("value", "")).strip()
        if suggestion.isupper() and len(suggestion) > 2:
            return True
    return False

def get_languagetool_matches(text, module):
    from django.conf import settings

    if module not in LANGUAGE_TOOL_SUPPORTED_MODULES:
        return []

    clean_text = normalize_text_for_analysis(text).strip()
    if not clean_text or len(clean_text) > 19000:
        return []

    api_url = str(getattr(settings, "LANGUAGETOOL_API_URL", LANGUAGE_TOOL_API_URL) or "").strip()
    if not api_url:
        return []

    try:
        response = requests.post(
            api_url,
            data={"text": clean_text, "language": "en-US"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            match for match in payload.get("matches", [])
            if should_keep_languagetool_match(match) and not should_ignore_languagetool_match(clean_text, match)
        ]
    except Exception:
        return []

def apply_languagetool_corrections(text, matches):
    corrected = str(text or "")
    applied_ranges = []
    for match in sorted(matches or [], key=lambda item: int(item.get("offset", 0)), reverse=True):
        replacements = match.get("replacements") or []
        if not replacements:
            continue
        offset = int(match.get("offset", 0))
        length = int(match.get("length", 0))
        end = offset + length
        if offset < 0 or length < 0 or end > len(corrected):
            continue
        if any(not (end <= start or offset >= stop) for start, stop in applied_ranges):
            continue
        suggestion = str(replacements[0].get("value", "")).strip()
        if not suggestion:
            continue
        corrected = f"{corrected[:offset]}{suggestion}{corrected[end:]}"
        applied_ranges.append((offset, end))
    return corrected

def derive_languagetool_issues(text, matches, max_count=50):
    issues = []
    seen = set()
    source = str(text or "")

    for match in sorted(matches or [], key=lambda item: int(item.get("offset", 0))):
        if len(issues) >= max_count:
            break
        offset = int(match.get("offset", 0))
        length = int(match.get("length", 0))
        end = offset + length
        if offset < 0 or length <= 0 or end > len(source):
            continue
        phrase = source[offset:end]
        if not phrase.strip():
            continue
        replacements = match.get("replacements") or []
        suggestion = str(replacements[0].get("value", "")).strip() if replacements else ""
        rule = match.get("rule", {})
        add_issue(
            issues,
            {
                "phrase": phrase,
                "type": get_languagetool_issue_type(match),
                "message": str(match.get("shortMessage") or match.get("message") or "Potential issue."),
                "suggestion": suggestion or phrase,
            },
            seen,
            max_count,
        )
    return issues

def tokenize_word_spans(text):
    source = normalize_text_for_analysis(text)
    return [
        {
            "text": match.group(0),
            "norm": match.group(0).lower(),
            "start": match.start(),
            "end": match.end(),
        }
        for match in re.finditer(r"[A-Za-z']+", source)
    ]

def build_phrase_from_tokens(source_text, tokens):
    if not tokens:
        return ""
    return str(source_text or "")[tokens[0]["start"]:tokens[-1]["end"]].strip()

def compute_reference_similarity(reference_text, candidate_text):
    import difflib

    reference_tokens = [token["norm"] for token in tokenize_word_spans(reference_text)]
    candidate_tokens = [token["norm"] for token in tokenize_word_spans(candidate_text)]
    if not candidate_tokens:
        return 0.0
    if not reference_tokens:
        return min(1.0, len(candidate_tokens) / 20.0)

    sequence_ratio = difflib.SequenceMatcher(None, reference_tokens, candidate_tokens).ratio()
    candidate_overlap = len(set(reference_tokens) & set(candidate_tokens)) / max(len(candidate_tokens), 1)
    reference_overlap = len(set(reference_tokens) & set(candidate_tokens)) / max(len(reference_tokens), 1)
    return (sequence_ratio * 0.6) + (candidate_overlap * 0.25) + (reference_overlap * 0.15)

def choose_best_transcript(candidates, reference_text=""):
    unique_candidates = []
    seen = set()
    for candidate in candidates or []:
        text = normalize_text_for_analysis(candidate).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(text)

    if not unique_candidates:
        return ""

    if reference_text:
        return max(
            unique_candidates,
            key=lambda text: (
                compute_reference_similarity(reference_text, text),
                len(re.findall(r"[A-Za-z']+", text)),
                len(text),
            ),
        )

    return max(
        unique_candidates,
        key=lambda text: (len(re.findall(r"[A-Za-z']+", text)), len(text)),
    )

def derive_reading_issues(reference_text, spoken_text, max_count=50):
    import difflib

    reference_source = normalize_text_for_analysis(reference_text)
    spoken_source = normalize_text_for_analysis(spoken_text)
    reference_tokens = tokenize_word_spans(reference_source)
    spoken_tokens = tokenize_word_spans(spoken_source)
    issues = []
    seen = set()

    if not reference_tokens:
        return issues

    matcher = difflib.SequenceMatcher(
        None,
        [token["norm"] for token in reference_tokens],
        [token["norm"] for token in spoken_tokens],
    )

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if len(issues) >= max_count:
            break
        if tag == "equal" or i1 == i2:
            continue

        reference_phrase = build_phrase_from_tokens(reference_source, reference_tokens[i1:i2])
        spoken_phrase = build_phrase_from_tokens(spoken_source, spoken_tokens[j1:j2])
        if not reference_phrase:
            continue

        if tag == "delete":
            issue = {
                "phrase": reference_phrase,
                "type": "Skipped",
                "message": "This word or phrase was skipped or was not heard clearly.",
                "suggestion": reference_phrase,
            }
        elif tag == "replace":
            issue = {
                "phrase": reference_phrase,
                "type": "Pronunciation",
                "message": (
                    f'You said "{spoken_phrase}" instead.'
                    if spoken_phrase else
                    "Your spoken words did not match this part of the passage."
                ),
                "suggestion": reference_phrase,
            }
        else:
            continue

        add_issue(issues, issue, seen, max_count)

    return issues[:max_count]

def apply_singular_subject_fixes(text):
    corrected = text
    verbs_pattern = "|".join(sorted(SINGULAR_NOUN_VERBS))
    pattern = re.compile(rf"\b([A-Za-z][A-Za-z' ]{{0,60}}?)\s+({verbs_pattern})\b", re.IGNORECASE)

    def _replacer(match):
        subject_phrase = match.group(1)
        verb = match.group(2)
        head = subject_head_for_agreement(subject_phrase)
        words = re.findall(r"[A-Za-z']+", subject_phrase)
        if not words:
            return match.group(0)
        if head in {"i", "you", "we", "they"}:
            return match.group(0)
        if head.endswith("s") and head not in SINGULAR_NOUN_HEAD_HINTS:
            return match.group(0)
        if head not in SINGULAR_NOUN_HEAD_HINTS and head not in {w.lower() for w in words}:
            return match.group(0)
        return f"{subject_phrase} {to_third_person_singular(verb)}"

    return pattern.sub(_replacer, corrected)

def apply_relative_clause_singular_fixes(text):
    corrected = text
    verbs_pattern = "|".join(sorted(SINGULAR_NOUN_VERBS))
    pattern = re.compile(rf"\b([A-Za-z']+)\s+(who|that|which)\s+({verbs_pattern})\b", re.IGNORECASE)

    def _replacer(match):
        noun = match.group(1)
        relative = match.group(2)
        verb = match.group(3)
        head = noun.lower()
        if head in {"i", "you", "we", "they"}:
            return match.group(0)
        if head.endswith("s") and head not in SINGULAR_NOUN_HEAD_HINTS:
            return match.group(0)
        return f"{noun} {relative} {to_third_person_singular(verb)}"

    return pattern.sub(_replacer, corrected)

def apply_adverb_singular_fixes(text):
    corrected = text
    verbs_pattern = "|".join(sorted(SINGULAR_NOUN_VERBS))
    pattern = re.compile(rf"\b([A-Za-z']+)\s+(always|often|sometimes|usually|never)\s+({verbs_pattern})\b", re.IGNORECASE)

    def _replacer(match):
        noun = match.group(1)
        adverb = match.group(2)
        verb = match.group(3)
        head = noun.lower()
        if head in {"i", "you", "we", "they"}:
            return match.group(0)
        if head.endswith("s") and head not in SINGULAR_NOUN_HEAD_HINTS:
            return match.group(0)
        return f"{noun} {adverb} {to_third_person_singular(verb)}"

    return pattern.sub(_replacer, corrected)

def apply_basic_grammar_fixes(text):
    corrected = normalize_text_for_analysis(text)
    if not corrected.strip():
        return corrected

    corrected = re.sub(r"\bvisit in ([A-Z][A-Za-z'-]+)\b", r"visit \1", corrected)
    corrected = replace_with_case(corrected, r"\bwanna\b", "want to")
    corrected = re.sub(r"\b([A-Za-z][^.!?\n]{12,}?)\,\s+(I|It|He|She|They|We|This|That|There)\b", r"\1. \2", corrected)

    for typo, replacement in COMMON_SPELLING_FIXES.items():
        corrected = replace_with_case(corrected, rf"\b{re.escape(typo)}\b", replacement)

    for pattern, replacement in WRITING_REPLACEMENTS:
        corrected = replace_with_case(corrected, pattern, replacement)

    corrected = replace_with_case(corrected, r"\bshe never give\b", "she never gives")
    corrected = replace_with_case(corrected, r"\bhe never give\b", "he never gives")
    corrected = replace_with_case(corrected, r"\bit never give\b", "it never gives")
    corrected = replace_with_case(corrected, r"\bthe path seem\b", "the path seems")
    corrected = apply_relative_clause_singular_fixes(corrected)
    corrected = apply_adverb_singular_fixes(corrected)
    corrected = apply_singular_subject_fixes(corrected)
    corrected = normalize_spacing_and_punctuation(corrected)

    if corrected and corrected[-1] not in ".!?":
        corrected = f"{corrected}."

    def _capitalize_sentence(match):
        prefix = match.group(1)
        letter = match.group(2)
        return f"{prefix}{letter.upper()}"

    corrected = re.sub(r"(^|[.!?]\s+)([a-z])", _capitalize_sentence, corrected)
    return corrected

def add_issue(issues, issue, seen, max_count):
    phrase = str(issue.get("phrase", "")).strip().lower()
    if not phrase or phrase in seen or len(issues) >= max_count:
        return
    issues.append(issue)
    seen.add(phrase)

def detect_punctuation_issues(original_text, improved_text, issues, seen, max_count):
    stripped = str(original_text or "").rstrip()
    if not stripped:
        return

    if stripped[-1] not in ".!?":
        last_word_match = re.search(r"([A-Za-z']+)\s*$", stripped)
        if last_word_match:
            word = last_word_match.group(1)
            add_issue(
                issues,
                {
                    "phrase": word,
                    "type": "Punctuation",
                    "message": "This sentence needs ending punctuation.",
                    "suggestion": f"{word}.",
                },
                seen,
                max_count,
            )

    for match in re.finditer(r"([,.;:!?])(?=[A-Za-z])", stripped):
        punct = match.group(1)
        context = stripped[max(0, match.start() - 12):min(len(stripped), match.start() + 12)].strip()
        add_issue(
            issues,
            {
                "phrase": context or punct,
                "type": "Punctuation",
                "message": "Add a space after punctuation for readability.",
                "suggestion": context.replace(punct, f"{punct} ", 1) if context else f"{punct} ",
            },
            seen,
            max_count,
        )

def derive_revision_issues(original_text, improved_text, max_count=50):
    import difflib
    issues = []
    seen = set()
    orig = normalize_text_for_analysis(original_text).strip()
    imp = normalize_text_for_analysis(improved_text).strip()
    ignored_delete_phrases = {"a", "an", "and", "in", "of", "or", "the", "to", "with"}
    if not orig: return []

    # 1. First, apply common spelling fixes
    for typo, correction in COMMON_SPELLING_FIXES.items():
        if len(issues) >= max_count: break
        pattern = r"\b" + re.escape(typo) + r"\b"
        for m in re.finditer(pattern, orig, re.IGNORECASE):
            if len(issues) >= max_count: break
            add_issue(
                issues,
                {
                    "phrase": m.group(0),
                    "type": "Spelling",
                    "message": f"Incorrect spelling of '{m.group(0)}'.",
                    "suggestion": match_replacement_case(correction, m.group(0))
                },
                seen,
                max_count,
            )

    # 2. If we have an improved version, use diffing to find structural/grammar gaps
    if imp and imp != orig:
        orig_words = re.findall(r"[A-Za-z']+|[.,!?;]+", orig)
        imp_words = re.findall(r"[A-Za-z']+|[.,!?;]+", imp)
        
        matcher = difflib.SequenceMatcher(None, orig_words, imp_words)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if len(issues) >= max_count: break
            if tag == 'replace':
                phrase = " ".join(orig_words[i1:i2])
                suggestion = " ".join(imp_words[j1:j2])
                if phrase and suggestion and phrase.lower() != suggestion.lower():
                    issue_type = "Punctuation" if re.search(r"[.,!?;]", phrase + suggestion) else "Grammar"
                    add_issue(
                        issues,
                        {
                            "phrase": phrase,
                            "type": issue_type,
                            "message": f"Better expressed as '{suggestion}'.",
                            "suggestion": suggestion
                        },
                        seen,
                        max_count,
                    )
            elif tag == 'delete':
                phrase = " ".join(orig_words[i1:i2])
                if phrase and phrase.lower() not in ignored_delete_phrases and len(phrase) > 2:
                    add_issue(
                        issues,
                        {
                            "phrase": phrase,
                            "type": "Grammar",
                            "message": "This part seems unnecessary or misplaced.",
                            "suggestion": ""
                        },
                        seen,
                        max_count,
                    )

    # 3. Apply grammar patterns as a final safety net
    grammar_patterns = [
        (r"\ban peaceful\b", "a peaceful", "Grammar", "Use 'a' before words starting with a consonant sound."),
        (r"\bvisit in ([A-Z][A-Za-z'-]+)\b", r"visit \1", "Grammar", "Use 'visit' directly before a place name."),
        (r"\bwhich are used to\b", "which I used to", "Grammar", "Incorrect phrase structure."),
        (r"\bhis always\b", "he is always", "Grammar", "Use 'he is' for a person's state."),
        (r"\bincluded raise\b", "including raising", "Grammar", "Use the gerund form after 'including'."),
        (r"\bshe never give\b", "she never gives", "Grammar", "Use singular verb agreement with 'she'."),
        (r"\bhe never give\b", "he never gives", "Grammar", "Use singular verb agreement with 'he'."),
        (r"\bhe always take\b", "he always takes", "Grammar", "Use singular verb agreement with 'he'."),
        (r"\bshe always take\b", "she always takes", "Grammar", "Use singular verb agreement with 'she'."),
        (r"\bthe path seem\b", "the path seems", "Grammar", "Use singular verb agreement with 'path'."),
        (r"\bgrate advise\b", "great advice", "Spelling", "This phrase uses the wrong word forms."),
        (r"\bgrate role model\b", "great role model", "Spelling", "This phrase uses the wrong word form."),
        (r"\bI can just relaxing\b", "I can just relax", "Grammar", "Use the base verb after 'can'."),
        (r"\bwanna\b", "want to", "Grammar", "Use the full form 'want to' in standard writing."),
    ]
    for pattern, suggestion, i_type, msg in grammar_patterns:
        if len(issues) >= max_count: break
        for m in re.finditer(pattern, orig, re.IGNORECASE):
            if len(issues) >= max_count: break
            suggestion_text = re.sub(pattern, suggestion, m.group(0), flags=re.IGNORECASE) if "\\" in suggestion else suggestion
            add_issue(
                issues,
                {
                    "phrase": m.group(0),
                    "type": i_type,
                    "message": msg,
                    "suggestion": suggestion_text
                },
                seen,
                max_count,
            )

    singular_pattern = re.compile(rf"\b([A-Za-z][A-Za-z' ]{{0,60}}?)\s+({'|'.join(sorted(SINGULAR_NOUN_VERBS))})\b", re.IGNORECASE)
    for match in singular_pattern.finditer(orig):
        subject_phrase = match.group(1)
        verb = match.group(2)
        head = subject_head_for_agreement(subject_phrase)
        if not head or head in {"i", "you", "we", "they"}:
            continue
        if head.endswith("s") and head not in SINGULAR_NOUN_HEAD_HINTS:
            continue
        corrected_verb = to_third_person_singular(verb)
        phrase = match.group(0)
        suggestion = f"{subject_phrase} {corrected_verb}"
        if phrase.lower() != suggestion.lower():
            add_issue(
                issues,
                {
                    "phrase": phrase,
                    "type": "Grammar",
                    "message": "Use singular verb agreement in this clause.",
                    "suggestion": suggestion,
                },
                seen,
                max_count,
            )

    relative_clause_pattern = re.compile(rf"\b([A-Za-z']+)\s+(who|that|which)\s+({'|'.join(sorted(SINGULAR_NOUN_VERBS))})\b", re.IGNORECASE)
    for match in relative_clause_pattern.finditer(orig):
        noun = match.group(1)
        relative = match.group(2)
        verb = match.group(3)
        head = noun.lower()
        if not head or head in {"i", "you", "we", "they"}:
            continue
        if head.endswith("s") and head not in SINGULAR_NOUN_HEAD_HINTS:
            continue
        corrected_verb = to_third_person_singular(verb)
        phrase = f"{relative} {verb}"
        suggestion = f"{relative} {corrected_verb}"
        if phrase.lower() != suggestion.lower():
            add_issue(
                issues,
                {
                    "phrase": phrase,
                    "type": "Grammar",
                    "message": "Use singular verb agreement in this relative clause.",
                    "suggestion": suggestion,
                },
                seen,
                max_count,
            )

    adverb_clause_pattern = re.compile(rf"\b([A-Za-z']+)\s+(always|often|sometimes|usually|never)\s+({'|'.join(sorted(SINGULAR_NOUN_VERBS))})\b", re.IGNORECASE)
    for match in adverb_clause_pattern.finditer(orig):
        noun = match.group(1)
        adverb = match.group(2)
        verb = match.group(3)
        head = noun.lower()
        if not head or head in {"i", "you", "we", "they"}:
            continue
        if head.endswith("s") and head not in SINGULAR_NOUN_HEAD_HINTS:
            continue
        corrected_verb = to_third_person_singular(verb)
        phrase = f"{noun} {adverb} {verb}"
        suggestion = f"{noun} {adverb} {corrected_verb}"
        if phrase.lower() != suggestion.lower():
            add_issue(
                issues,
                {
                    "phrase": phrase,
                    "type": "Grammar",
                    "message": "Use singular verb agreement in this clause.",
                    "suggestion": suggestion,
                },
                seen,
                max_count,
            )

    detect_punctuation_issues(orig, imp, issues, seen, max_count)

    return issues[:max_count]

def fallback_text_module_analysis(module, text, reference_text="", duration_seconds=0, pause_count=0):
    words = [w for w in re.findall(r"[A-Za-z']+", text) if w]
    word_count = len(words)
    sentence_count = max(1, len([s for s in re.split(r"[.!?]+", text) if s.strip()]))
    
    fluency = clamp_score(80 - min(pause_count * 2, 10), 72)
    pronunciation = clamp_score(80, 70)
    confidence = clamp_score(80 - min(pause_count * 3, 15), 72)

    base_text = normalize_text_for_analysis(text)

    if module == "reading":
        reference_source = normalize_text_for_analysis(reference_text or text)
        accuracy_ratio = compute_reference_similarity(reference_source, base_text)
        pronunciation = clamp_score(round(accuracy_ratio * 100), 70)
        fluency = clamp_score(round(max(35, (accuracy_ratio * 100) - min(pause_count * 2, 12))), 72)
        confidence = clamp_score(round(max(35, (accuracy_ratio * 100) - min(pause_count * 3, 18))), 72)
        issues = derive_reading_issues(reference_source, base_text)
        improved_text = reference_source or base_text
        return {
            "text": text,
            "scores": {"fluency": fluency, "pronunciation": pronunciation, "confidence": confidence},
            "issues": issues,
            "improved_passage": improved_text,
            "feedback": "Your reading was checked against the passage for skipped, changed, and unclear words.",
            "quick_tip": "Track each word carefully and try to match the passage exactly as written.",
        }

    improved_text = apply_basic_grammar_fixes(base_text) if module in {"writing", "speaking", "listening", "interview"} else base_text

    lt_matches = get_languagetool_matches(base_text, module)
    lt_issues = derive_languagetool_issues(base_text, lt_matches) if lt_matches else []
    if lt_matches:
        improved_text = apply_basic_grammar_fixes(apply_languagetool_corrections(base_text, lt_matches))

    issues = derive_revision_issues(base_text, improved_text)
    if lt_issues:
        issues = merge_issues(lt_issues, issues)
    feedback_prefix = {
        "writing": "Your writing has been reviewed for grammar, spelling, and punctuation.",
        "speaking": "Your response has been reviewed for clarity and correctness.",
        "reading": "Your response has been reviewed for reading accuracy.",
        "listening": "Your response has been reviewed for meaning and language quality.",
        "interview": "Your answer has been reviewed for professional clarity.",
    }.get(module, f"{module.capitalize()} analysis complete.")
    quick_tip = {
        "writing": "Read your draft once for verb agreement, spelling, and sentence-ending punctuation.",
    }.get(module, "Keep practicing for better results.")

    return {
        "text": text,
        "scores": {"fluency": fluency, "pronunciation": pronunciation, "confidence": confidence},
        "issues": issues,
        "improved_passage": improved_text,
        "feedback": feedback_prefix,
        "quick_tip": quick_tip
    }

def analyze_text_with_sarvam_chat(module, text, reference_text, duration_seconds, pause_count, api_key, language="english"):
    is_vietnam = str(language).lower() == "vietnam"
    lang_directive = ""
    if is_vietnam:
        lang_directive = "\nCRITICAL: You MUST provide the 'message', 'suggestion', 'feedback', and 'quick_tip' in the format: 'Vietnamese text (English text)'. The 'phrase' must still be the exact English text from the user."

    if module == "reading":
        system_prompt = (
            "You are an expert reading evaluator. Compare the 'text' (user's spoken transcript) against the 'reference_text' (the original passage).\n"
            "Identify words or phrases in the 'reference_text' that the user mispronounced, skipped, or struggled with.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the 'reference_text'.\n"
            "For each issue, provide: 'phrase' (from 'reference_text'), 'type' (Pronunciation/Skipped), 'message' (what was wrong), and 'suggestion' (correct pronunciation/usage).\n"
            f"Be extremely strict and accurate.{lang_directive}"
        )
    elif module == "listening":
        system_prompt = (
            "You are an expert listening evaluator. Compare the user's 'text' (their summary) against the 'reference_text' (the original story).\n"
            "Identify parts of the user's summary that are factually incorrect or contain grammar/spelling errors based on the story.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the user's 'text'.\n"
            "For each issue, provide: 'phrase' (from user's text), 'type' (Accuracy/Grammar/Spelling), 'message' (why it's wrong), and 'suggestion' (how to fix it).\n"
            f"Be extremely strict and accurate.{lang_directive}"
        )
    elif module == "speaking":
        system_prompt = (
            "You are an expert speaking coach. Analyze the user's 'text' (spoken transcript) for grammar, pronunciation, and vocabulary errors.\n"
            "Identify EVERY mistake, no matter how small.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the user's 'text'.\n"
            "For each issue, provide: 'phrase' (the exact text in the transcript), 'type' (Grammar/Vocabulary/Pronunciation), 'message' (brief explanation), and 'suggestion' (the correct version).\n"
            f"Be extremely strict. If you find no issues, double check the grammar.{lang_directive}"
        )
    else: # writing
        system_prompt = (
            "You are an expert English writing evaluator. Analyze the user's 'text' for grammar, spelling, punctuation, and vocabulary issues.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the user's 'text'.\n"
            "For each issue, provide: 'phrase' (from user's text), 'type' (Grammar/Spelling/Vocabulary/Punctuation), 'message' (brief explanation), and 'suggestion' (the correct version).\n"
            "If the user writes 'freind', you MUST return { 'phrase': 'freind', 'type': 'Spelling', 'message': 'Incorrect spelling.', 'suggestion': 'friend' }.\n"
            f"Be extremely strict and accurate. Do not skip any errors.{lang_directive}"
        )
    user_payload = {
        "module": module,
        "text": text,
        "reference_text": reference_text,
        "duration_seconds": duration_seconds,
        "pause_count": pause_count,
    }
    try:
        response = requests.post(
            SARVAM_CHAT_URL,
            headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
            json={
                "model": getattr(settings, 'SARVAM_MODEL', 'sarvam-105b'),
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                "reasoning_effort": None,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return extract_json_payload(content)
    except Exception as e:
        raise ValueError(f"Sarvam API error: {str(e)}")


# How the neural voice is shaped per emotion. bulbul:v3 takes `pace` and
# `loudness`; `temperature` controls how much expressive variation it allows.
# A found-it reply is read a little faster, louder and more freely; a
# could-not-do-it reply slower, softer and flatter, which is what a person
# does. Values stay close to 1.0 — a big move sounds theatrical, not human.
# `loudness` above 1.0 CLIPS the waveform — that is the rasp that made Buddy
# sound hoarse, and no change of speaker fixes it. 1.0 is the ceiling; emotion
# is carried by pace and expressiveness instead. `temperature` is the amount
# of random variation the model is allowed: high values add the breathy,
# gravelly artefacts, so it stays low for a calm voice. Pace is unhurried
# throughout — a relaxed voice is a slightly slow one.
TTS_EMOTION_PROFILES = {
    'happy': {'pace': 0.98, 'loudness': 1.0, 'temperature': 0.3},
    'sad': {'pace': 0.90, 'loudness': 0.9, 'temperature': 0.15},
    'neutral': {'pace': 0.95, 'loudness': 1.0, 'temperature': 0.2},
}


SARVAM_TTS_STREAM_URL = "https://api.sarvam.ai/text-to-speech/stream"


def _tts_cache_key(language_code, speaker, emotion, clean_text, suffix=''):
    return (
        "riya_tts:" + suffix
        + hashlib.sha256(
            f"{language_code}:{speaker}:{emotion}:{clean_text}".encode("utf-8")
        ).hexdigest()
    )


# Buddy's voice. Chosen by ear over all 21 bulbul:v3 speakers — calm and
# unhurried rather than bright. Change it here and the whole app follows.
DEFAULT_TTS_SPEAKER = 'ritu'


def cached_riya_tts_audio(text, language_code="en-IN", speaker=DEFAULT_TTS_SPEAKER,
                          emotion="neutral"):
    """Already-synthesised WAV (base64) for this exact line, or None.

    Lets the streaming view answer a warmed reply from cache in ~10ms instead
    of opening a fresh connection to Sarvam.
    """
    clean_text = str(text or "").strip()[:500]
    if not clean_text:
        return None
    return caches['tts'].get(_tts_cache_key(language_code, speaker, emotion, clean_text))


def stream_riya_tts_audio(text, api_key, language_code="en-IN", speaker=DEFAULT_TTS_SPEAKER,
                          emotion="neutral"):
    """Yield MP3 chunks as Sarvam produces them.

    The non-streaming endpoint only answers once the WHOLE reply has been
    synthesised, which is 1.8s for one sentence and over 4s for a paragraph —
    the user watches the text sit there in silence for all of it. Streaming
    returns the first chunk in ~0.5s whatever the length, so Buddy starts
    talking while the rest is still being made.

    The finished audio is cached under a separate key (MP3, not the WAV the
    batch endpoint returns) so a repeat of the same line replays instantly.
    """
    clean_text = str(text or "").strip()
    if not clean_text or not api_key:
        return
    if len(clean_text) > 500:
        clean_text = clean_text[:500]

    profile = TTS_EMOTION_PROFILES.get(emotion) or TTS_EMOTION_PROFILES['neutral']
    tts_cache = caches['tts']
    key = _tts_cache_key(language_code, speaker, emotion, clean_text, suffix='mp3:')

    cached = tts_cache.get(key)
    if cached is not None:
        yield cached
        return

    try:
        response = requests.post(
            SARVAM_TTS_STREAM_URL,
            headers={
                'api-subscription-key': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'text': clean_text,
                'target_language_code': language_code,
                'speaker': speaker,
                'model': 'bulbul:v3',
                'pace': profile['pace'],
                'loudness': profile['loudness'],
                'temperature': profile['temperature'],
                # The batch path asks for 24 kHz; the stream path did not, so
                # it fell back to the API default and came out duller.
                'speech_sample_rate': 24000,
            },
            stream=True,
            timeout=30,
        )
        response.raise_for_status()

        collected = bytearray()
        for chunk in response.iter_content(chunk_size=4096):
            if not chunk:
                continue
            collected.extend(chunk)
            yield chunk

        if collected:
            tts_cache.set(key, bytes(collected), TTS_CACHE_TIMEOUT_SECONDS)
    except Exception as exc:
        # The caller has already sent 200 + the first bytes by now, so there is
        # nothing to report to the browser except silence; the page falls back
        # to its own voice when the clip will not play.
        logger.warning('Sarvam TTS stream failed (lang=%s speaker=%s): %s',
                       language_code, speaker, exc)


# Sarvam bulbul speaks Indian languages only. Vietnamese, Arabic and Russian
# use Google Translate's female voices: ~0.5-0.8s per line. Microsoft's
# edge-tts voices were tried first and took 1.8-5.5s (Arabic, Russian) and
# 5-11s (Vietnamese) - too slow for the reply to be spoken as it appears.
GOOGLE_TTS_LANGS = {
    "vi-VN": "vi",
    "ar-SA": "ar",
    "ru-RU": "ru",
}
GOOGLE_TTS_URL = "https://translate.google.com/translate_tts"
GOOGLE_TTS_MAX_CHARS = 180  # the endpoint rejects text much over ~200 chars


def _split_for_google_tts(text):
    """Pieces of at most GOOGLE_TTS_MAX_CHARS, cut at sentence, then clause,
    then word boundaries so each piece still sounds natural on its own."""
    pieces = []
    for sentence in re.split(r'(?<=[.!?;:,،؟])\s+', text):
        while len(sentence) > GOOGLE_TTS_MAX_CHARS:
            cut = sentence.rfind(' ', 0, GOOGLE_TTS_MAX_CHARS)
            cut = cut if cut > 0 else GOOGLE_TTS_MAX_CHARS
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if pieces and len(pieces[-1]) + 1 + len(sentence) <= GOOGLE_TTS_MAX_CHARS:
            pieces[-1] = f"{pieces[-1]} {sentence}".strip()
        elif sentence.strip():
            pieces.append(sentence.strip())
    return [p for p in pieces if p]


async def stream_google_tts_audio(text, language_code, emotion="neutral"):
    """Yield MP3 for a GOOGLE_TTS_LANGS language: cached per line, and no
    chunks on failure so the page falls back to its own voice. Async on
    purpose: the site runs on daphne (ASGI), where a SYNC streaming iterator
    is buffered to the end before the first byte is sent.

    All pieces are requested at once and yielded in order, so the first is
    audible after one round trip (~0.5s) while the rest are already arriving.
    The voice has no pace/pitch controls, so ``emotion`` only keys the cache.
    """
    import asyncio

    import aiohttp

    lang = GOOGLE_TTS_LANGS.get(language_code)
    clean_text = str(text or "").strip()[:500]
    if not lang or not clean_text:
        return

    tts_cache = caches['tts']
    key = _tts_cache_key(language_code, 'google', emotion, clean_text, suffix='google-mp3:')
    cached = await tts_cache.aget(key)
    if cached is not None:
        yield cached
        return

    async def fetch(session, piece):
        params = {"ie": "UTF-8", "q": piece, "tl": lang, "client": "tw-ob"}
        async with session.get(GOOGLE_TTS_URL, params=params) as response:
            response.raise_for_status()
            return await response.read()

    collected = bytearray()
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            tasks = [asyncio.ensure_future(fetch(session, piece))
                     for piece in _split_for_google_tts(clean_text)]
            try:
                for task in tasks:
                    audio = await task
                    collected.extend(audio)
                    yield audio
            finally:
                for task in tasks:
                    task.cancel()
    except Exception as exc:
        logger.warning('Google TTS failed (lang=%s): %s', lang, exc)
        return
    if collected:
        await tts_cache.aset(key, bytes(collected), TTS_CACHE_TIMEOUT_SECONDS)

def generate_riya_tts_audio(text, api_key, language_code="en-IN", speaker=DEFAULT_TTS_SPEAKER,
                            emotion="neutral"):
    clean_text = str(text or "").strip()
    if not clean_text or not api_key:
        return None

    if len(clean_text) > 500:
        clean_text = clean_text[:500]

    # Only allow valid bulbul:v3 speakers; fall back to the default otherwise.
    valid_speakers = {
        # niharika and karun were in this list but bulbul:v3 answers 400 for
        # both, so a request naming them silently became the default voice.
        'priya', 'shreya', 'neha', 'ritu', 'kavya', 'pooja', 'simran', 'ishita',
        'roopa', 'tanya', 'shruti', 'suhani', 'kavitha', 'rupali',
        'anand', 'rahul', 'rohan', 'aditya', 'amit', 'dev', 'varun',
    }
    if speaker not in valid_speakers:
        speaker = DEFAULT_TTS_SPEAKER

    profile = TTS_EMOTION_PROFILES.get(emotion) or TTS_EMOTION_PROFILES['neutral']

    # Emotion is part of the key: the same sentence read happily and read
    # sadly are two different recordings, and one must not serve the other.
    cache_key = _tts_cache_key(language_code, speaker, emotion, clean_text)
    # Dedicated 'tts' alias (see CACHES in settings.py) so audio never
    # competes for slots with OTP codes and lockout counters in 'default'.
    tts_cache = caches['tts']
    cached_audio = tts_cache.get(cache_key)
    if cached_audio is not None:
        return cached_audio

    try:
        response = requests.post(
            SARVAM_TTS_URL,
            headers={
                'api-subscription-key': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'inputs': [clean_text],
                'target_language_code': language_code,
                'speaker': speaker,
                'model': 'bulbul:v3',
                'pace': profile['pace'],
                'loudness': profile['loudness'],
                'temperature': profile['temperature'],
                'speech_sample_rate': 24000,
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        audios = data.get('audios', [])
        audio = audios[0] if audios else None
        if audio:
            tts_cache.set(cache_key, audio, TTS_CACHE_TIMEOUT_SECONDS)
        else:
            logger.warning('Sarvam TTS returned no audio (lang=%s speaker=%s): %s',
                           language_code, speaker, str(data)[:200])
        return audio
    except Exception as exc:
        # Previously swallowed whole. A deprecated model or a rejected
        # parameter returns 400 here, the caller falls back to the browser
        # voice, and nothing anywhere says why it sounds robotic.
        detail = ''
        response_obj = locals().get('response')
        if response_obj is not None:
            detail = str(getattr(response_obj, 'text', ''))[:200]
        logger.warning('Sarvam TTS failed (lang=%s speaker=%s): %s %s',
                       language_code, speaker, exc, detail)
        return None

def extract_json_payload(text: str) -> dict:
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
        if not match: return {}
        try:
            payload = json.loads(match.group(0))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}

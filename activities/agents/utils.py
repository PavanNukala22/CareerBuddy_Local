import json
import re
import requests
from django.conf import settings
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech-stream"
LANGUAGE_TOOL_API_URL = "https://api.languagetool.org/v2/check"
LANGUAGE_TOOL_SUPPORTED_MODULES = {"writing", "speaking", "listening", "interview"}

# Every provider prompt must pin scores to a 0-100 percentage so a model that
# returns fractions (0.8) or a 1-10 rating never persists as a near-zero mark.
SCORE_SCALE_DIRECTIVE = (
    "SCORING: every value in 'scores' MUST be an INTEGER from 0 to 100 (a "
    "percentage), never a fraction, a rating out of 5, or a rating out of 10."
)

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
            "content": f"One afternoon, during {safe_prompt}...",
            "follow_ups": ["Who is the main character?", f"What happened during {safe_prompt}?", "What is the lesson?"],
            "coach_tip": "Answer in 1 or 2 clear sentences."
        }
    return {"title": title_text, "content": f"Practice setup for {safe_prompt}."}

def topic_practice_with_sarvam_chat(topic, prompt, api_key):
    # Logic to call Sarvam for topic practice
    return {}

SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

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

def transcribe_with_sarvam(audio_file, api_key, prompt=None):
    try:
        # The /speech-to-text endpoint uses the `saarika` family pinned to a
        # language; `saaras` is the translate endpoint and auto-detects the
        # wrong language (e.g. Kannada) for English audio. Fall back to Sarvam's
        # default model if the model/lang combo is rejected.
        base_payload = {}
        if prompt:
            base_payload["prompt"] = str(prompt)[:500]

        audio_file.seek(0)
        audio_bytes = audio_file.read()
        # Strip codec params (e.g. "audio/webm;codecs=opus") from the content type.
        content_type = (getattr(audio_file, "content_type", None) or "audio/webm").split(";")[0].strip()

        last_error = None
        for model_opts in ({"model": "saarika:v2.5", "language_code": "en-IN"}, {}):
            try:
                response = requests.post(
                    SARVAM_STT_URL,
                    headers={"api-subscription-key": api_key},
                    data={**base_payload, **model_opts},
                    files={"file": (audio_file.name, audio_bytes, content_type)},
                    timeout=45,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("transcript", ""), data, None
            except Exception as e:
                last_error = e
                continue
        return "", {}, {"message": str(last_error), "status": 500}
    except Exception as e:
        return "", {}, {"message": str(e), "status": 500}

def clamp_score(value, fallback=70):
    try:
        val = int(float(value))
        return max(0, min(100, val))
    except (ValueError, TypeError):
        return fallback

def normalise_score_scale(scores):
    """Coerce a provider 'scores' dict onto a 0-100 integer scale.

    A model may return a fraction (0.8), a percent (85), or an out-of-range
    value. Fractions (<= 1.0) are read as ratios and multiplied by 100; every
    value is clamped to 0-100 and rounded to an int. Non-numeric values (and
    bools) are dropped; a non-dict yields {}.
    """
    if not isinstance(scores, dict):
        return {}
    normalised = {}
    for key, value in scores.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        val = float(value)
        if val <= 1.0:
            val *= 100
        val = max(0.0, min(100.0, val))
        normalised[key] = int(round(val))
    return normalised

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
    if not text: return False
    words = re.findall(r"[a-zA-Z]+", text)
    return len(words) >= 2


def repetition_ratio(text):
    """Fraction of the text's sentences that are duplicates of an earlier
    sentence, so a submission that pads out to length by cycling through the
    same handful of lines over and over can be caught — even when every
    individual sentence is grammatically clean (nothing for a grammar/spelling
    checker to flag) and even when it's a *rotating* set of repeated lines
    rather than one single line repeated (which a "share of the single most
    common sentence" measure would under-count).
    Returns 0.0 for text with too few sentences to judge repetition from.
    """
    sentences = [s.strip().lower() for s in re.split(r"[.!?•\n]+", text or "") if s.strip()]
    if len(sentences) < 4:
        return 0.0
    unique_count = len(set(sentences))
    return 1 - (unique_count / len(sentences))

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


def compute_listening_score_25(reference_text, candidate_text, pause_count=0, issue_count=0):
    """Score (0-25) a "what did you understand" listening summary against the
    story it's meant to summarise.

    The AI's own 'scores' dict grades generic language quality (fluency,
    grammar, spelling) and can come back a perfect 100 even when the summary
    barely matches what the story was actually about — the two numbers on
    screen (Total Score and Content Match %) would then visibly disagree, as
    a full-marks score sitting next to an 88% match makes no sense to the
    learner. Deriving the score directly from the same content-similarity
    ratio shown as "Content Match" keeps the two numbers consistent, mirrors
    the client-side banding in linguavoice-common.js's
    computeListeningAssessment(), and actually measures what this exercise
    is meant to test: did the learner understand the content.
    """
    content_match = compute_reference_similarity(reference_text, candidate_text)
    content_match = max(0.0, min(1.0, content_match))

    if content_match >= 0.999:
        base_score = 25
    elif content_match >= 0.9:
        base_score = 24
    elif content_match >= 0.8:
        base_score = 16 + (((content_match - 0.8) / 0.1) * 2)
    elif content_match >= 0.6:
        base_score = 13 + (((content_match - 0.6) / 0.2) * 3)
    elif content_match >= 0.5:
        base_score = 10 + (((content_match - 0.5) / 0.1) * 3)
    elif content_match >= 0.2:
        base_score = 5 + (((content_match - 0.2) / 0.3) * 5)
    else:
        base_score = content_match * 20

    issue_penalty = max(0, int(issue_count or 0)) * 0.25
    pause_penalty = min(max(0, int(pause_count or 0)) * 0.25, 1.5)
    score = base_score - issue_penalty - pause_penalty
    if content_match < 0.2:
        score = min(score, 4.5)

    return max(0, min(25, round(score))), round(content_match * 100)


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
    ignored_delete_phrases = {
        "a", "an", "and", "in", "of", "or", "the", "to", "with", 
        "so", "but", "well", "actually", "basically", "like", "also", "just", "then"
    }
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
        overall = clamp_score(round(accuracy_ratio * 100), 70)
        issues = derive_reading_issues(reference_source, base_text)
        improved_text = reference_source or base_text
        return {
            "text": text,
            "scores": {"fluency": fluency, "pronunciation": pronunciation, "confidence": confidence, "accuracy": overall, "overall": overall},
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
            "First check whether 'text' actually addresses 'reference_text': a response that is off-topic, "
            "irrelevant, or gibberish must be scored low overall. "
            "Identify words or phrases in the 'reference_text' that the user mispronounced, skipped, or struggled with.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the 'reference_text'.\n"
            "For each issue, provide: 'phrase' (from 'reference_text'), 'type' (Pronunciation/Skipped), 'message' (what was wrong), and 'suggestion' (correct pronunciation/usage).\n"
            f"{SCORE_SCALE_DIRECTIVE} Use exactly these keys in the scores object: 'pronunciation', 'relevance', 'overall'.\n"
            "CRITICAL: If the 'text' is gibberish, completely random words, or completely unrelated to the 'reference_text', you MUST set BOTH 'relevance' and 'overall' to 0.\n"
            f"Be extremely strict and accurate.{lang_directive}"
        )
    elif module == "listening":
        system_prompt = (
            "You are an expert listening evaluator. Compare the user's 'text' (their summary) against the 'reference_text' (the original story).\n"
            "First check whether 'text' actually addresses 'reference_text': a response that is off-topic, "
            "irrelevant, or gibberish must be scored low overall. "
            "Identify parts of the user's summary that are factually incorrect or contain grammar/spelling errors based on the story.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the user's 'text'.\n"
            "For each issue, provide: 'phrase' (from user's text), 'type' (Accuracy/Grammar/Spelling), 'message' (why it's wrong), and 'suggestion' (how to fix it).\n"
            f"{SCORE_SCALE_DIRECTIVE} Use exactly these keys in the scores object: 'accuracy', 'relevance', 'overall'.\n"
            "CRITICAL: If the 'text' is gibberish, completely random words, or completely unrelated to the 'reference_text', you MUST set BOTH 'relevance' and 'overall' to 0.\n"
            f"Be extremely strict and accurate.{lang_directive}"
        )
    elif module == "speaking":
        system_prompt = (
            "You are an expert speaking coach. Analyze the user's 'text' (spoken transcript) for grammar, clarity, and vocabulary errors.\n"
            "First check whether 'text' actually addresses 'reference_text' (if provided): a response that is off-topic, "
            "irrelevant, or gibberish must be scored low overall. "
            "Identify EVERY mistake, no matter how small.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the user's 'text'.\n"
            "For each issue, provide: 'phrase' (the exact text in the transcript), 'type' (Grammar/Vocabulary/Clarity), 'message' (brief explanation), and 'suggestion' (the correct version).\n"
            f"{SCORE_SCALE_DIRECTIVE} Use exactly these keys in the scores object: 'fluency', 'grammar', 'vocabulary', 'clarity', 'relevance', 'overall'.\n"
            "You must score 'fluency' and 'clarity' based on how coherent, well-structured, and natural the written transcript reads.\n"
            "CRITICAL: If the 'text' is gibberish, completely random words, or completely unrelated to the topic, you MUST set BOTH 'relevance' and 'overall' to 0.\n"
            "A clear, mostly-correct response should score in the 70-95 range; reserve scores below 50 for responses that are largely incorrect or unintelligible. 'overall' should reflect the average quality of the other scores.\n"
            f"Be extremely strict about issues, but fair and consistent with the 0-100 scores. If you find no issues, double check the grammar.{lang_directive}"
        )
    else: # writing
        system_prompt = (
            "You are an expert English writing evaluator. The 'reference_text' is the essay topic/prompt the "
            "user was asked to write about; the 'text' is their response to it.\n"
            "First check whether 'text' actually addresses 'reference_text': a response that is off-topic, "
            "irrelevant to the prompt, incoherent, or that pads out length by repeating the same sentence or "
            "phrase over and over (even if each repeated fragment is individually grammatical) is NOT a "
            "genuine written response and must be scored low overall — regardless of how clean its grammar, "
            "spelling, or punctuation looks in isolation. A perfect or near-perfect score requires both correct "
            "language AND a real, on-topic, non-repetitive answer to the prompt.\n"
            "Otherwise, analyze the user's 'text' for grammar, spelling, punctuation, and vocabulary issues.\n"
            "Return ONLY strict JSON with these keys: scores, issues, improved_passage, feedback, quick_tip.\n"
            f"{SCORE_SCALE_DIRECTIVE} Use these keys: 'grammar', 'vocabulary', 'relevance', 'overall'. 'relevance' "
            "reflects how well 'text' addresses 'reference_text' and avoids repetition; 'overall' must reflect "
            "'relevance' as well as the language-quality scores, not language quality alone. "
            "CRITICAL: If the 'text' is gibberish, completely random words, or does not answer the 'reference_text', you MUST set BOTH 'relevance' and 'overall' to 0.\n"
            "CRITICAL: The 'phrase' in the 'issues' array MUST be an EXACT substring from the user's 'text'.\n"
            "For each issue, provide: 'phrase' (from user's text), 'type' (Grammar/Spelling/Vocabulary/Punctuation/Relevance), 'message' (brief explanation), and 'suggestion' (the correct version, or how to address the prompt for a Relevance issue).\n"
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
    # Non-streaming completions take roughly one time-slice per output token,
    # so the max_tokens cap is the main lever on wall-clock latency. Speaking/
    # roleplay transcripts are short and conversational (a handful of Q&A
    # turns) and never need anywhere near the 2000-token ceiling that
    # long-essay writing analysis does, so give it a much smaller budget to
    # cut analysis time. reading/listening sit in between.
    max_tokens_by_module = {
        "speaking": 900,
        "reading": 1200,
        "listening": 1200,
        "writing": 2000,
    }
    max_tokens = max_tokens_by_module.get(module, 2000)

    try:
        response = requests.post(
            SARVAM_CHAT_URL,
            headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
            json={
                # sarvam-105b is a REASONING model: left to reason it burns the
                # token budget on `reasoning_content`, hits finish_reason "length"
                # and returns content=null -> a billed request with no AI result.
                # The `-conversations` variant does not reason (reasoning_content
                # is empty), so it returns the JSON answer reliably and cheaper.
                "model": getattr(settings, 'SARVAM_ANALYSIS_MODEL', 'sarvam-105b-conversations'),
                "temperature": 0.1,
                # Starter tier caps -conversations at 2048 output tokens; 3000 -> 400.
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        message = response.json().get("choices", [{}])[0].get("message", {}) or {}
        # Prefer the answer channel; if a reasoning model still left it null,
        # salvage the JSON from the reasoning channel rather than fall back blind.
        content = message.get("content") or message.get("reasoning_content") or ""
        return extract_json_payload(content)
    except Exception as e:
        raise ValueError(f"Sarvam API error: {str(e)}")


def generate_riya_tts_audio(text, api_key):
    clean_text = str(text or "").strip()
    if not clean_text or not api_key:
        return None

    if len(clean_text) > 500:
        clean_text = clean_text[:500]

    try:
        response = requests.post(
            SARVAM_TTS_URL,
            headers={
                'api-subscription-key': api_key,
                'Content-Type': 'application/json',
            },
            json={
                'inputs': [clean_text],
                'target_language_code': 'en-IN',
                'speaker': 'meera',
                'model': 'bulbul:v3',
                'pace': 1.7,
                'temperature': 0.35,
                'speech_sample_rate': 24000,
            },
            timeout=18,
        )
        response.raise_for_status()
        data = response.json()
        audios = data.get('audios', [])
        return audios[0] if audios else None
    except Exception:
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

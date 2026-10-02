"""
Shared agent utilities: transcription via Sarvam AI STT, and the bilingual
language directive used by every AI-generated response across the app.
"""
import logging

import requests

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

# Display names for the values sent by includes/language_dropdown.html.
LANGUAGE_NAMES = {'vietnam': 'Vietnamese', 'arabic': 'Arabic', 'russian': 'Russian'}


def language_directive(language):
    """Prompt suffix that makes the model answer in the learner's language.

    The canonical form of the directive originally in
    activities/agents/utils.analyze_text_with_sarvam_chat(). Every place that
    prompts an LLM for a learner-facing response uses this one function, so a
    new language is added in one place instead of drifting across copies.

    English (or an unrecognised value) returns '' — no directive, response
    stays English.
    """
    name = LANGUAGE_NAMES.get(str(language or 'english').strip().lower())
    if not name:
        return ''
    return (
        f"\nCRITICAL: Write the learner-facing text in the format "
        f"'{name} text (English text)' — the {name} first, then the exact "
        f"English original in brackets. Keep any JSON keys and numeric scores "
        f"unchanged and in English."
    )

# Browsers record as audio/webm;codecs=opus. Sarvam rejects the codec suffix and
# a filename with no extension, so both are normalised before upload.
_EXT_BY_TYPE = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
}


def transcribe_with_sarvam(audio_file, api_key):
    """
    Sends an audio file to Sarvam AI STT and returns (transcript, raw_data, error).
    Returns ('', {}, {'message': ..., 'status': 500}) on failure.
    """
    if not api_key:
        logger.error("Sarvam STT: SARVAM_API_KEY is not configured.")
        return "", {}, {"message": "SARVAM_API_KEY is not configured.", "status": 500}

    try:
        audio_file.seek(0)
        audio_bytes = audio_file.read()
    except Exception as e:
        logger.error("Sarvam STT: could not read audio file: %s", e)
        return "", {}, {"message": str(e), "status": 500}

    if len(audio_bytes) == 0:
        logger.warning("Sarvam STT: audio too short (%d bytes).", len(audio_bytes))
        return "", {}, {"message": "Recording too short.", "status": 400}

    # "audio/webm;codecs=opus" -> "audio/webm"; the codec suffix is rejected.
    content_type = (getattr(audio_file, "content_type", "") or "audio/webm").split(";")[0].strip()
    ext = _EXT_BY_TYPE.get(content_type, "webm")

    # Pin the saarika family to Indian English for accuracy, then retry with
    # Sarvam's defaults if that model/language combination is rejected.
    last_error = None
    for data_opts in ({"model": "saarika:v2.5", "language_code": "en-IN"}, {}):
        try:
            response = requests.post(
                SARVAM_STT_URL,
                headers={"api-subscription-key": api_key},
                data=data_opts,
                files={"file": (f"recording.{ext}", audio_bytes, content_type)},
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            transcript = (data.get("transcript") or "").strip()
            if not transcript:
                logger.warning("Sarvam STT returned an empty transcript (opts=%s).", data_opts)
            return transcript, data, None
        except Exception as e:
            last_error = e
            err_response = getattr(e, "response", None)
            last_status = getattr(err_response, "status_code", None)
            if last_status == 400 and len(audio_bytes) < 500_000:
                logger.warning("Sarvam STT rejected short/empty recording (%d bytes) with HTTP 400.", len(audio_bytes))
                return "", {}, {"message": "Recording too short.", "status": 400}

            logger.warning("Sarvam STT attempt failed (opts=%s): %s", data_opts, e)

    logger.error("Sarvam STT failed for %d bytes of %s: %s", len(audio_bytes), content_type, last_error)
    return "", {}, {"message": str(last_error), "status": 500}

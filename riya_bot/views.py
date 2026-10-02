import itertools

from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.shortcuts import render
import base64
import json
import logging
import re
from .riya_assistant import riya_chat_logic, stream_assistant_response, normalize_language, SUPPORTED_LANGUAGES
from .agents.utils import (DEFAULT_TTS_SPEAKER, GOOGLE_TTS_LANGS,
                           _transcribe_with_sarvam, generate_riya_tts_audio,
                           stream_google_tts_audio, stream_riya_tts_audio)

logger = logging.getLogger(__name__)

# A single, generic message for every unexpected failure in this module — the
# real exception (which can otherwise be anything from a JSON parse error to
# a Django "DATA_UPLOAD_MAX_MEMORY_SIZE" setting name) is logged server-side
# via logger.exception() instead of being echoed to the client in str(e).
_GENERIC_ERROR = "Something went wrong on our end. Please try again."

def _speakable_user_name(user) -> str:
    """The name Buddy should call this person, ready to be spoken aloud.

    Accounts hold names in whatever shape the user typed them — "jagadeesh m",
    "KONDAPARTHI SAI PRASAD", or an email address standing in as a username.
    Passed through verbatim they reach the model and the TTS voice unchanged,
    which is how Buddy ended up greeting someone as "jagadeesh m" and reading
    the trailing initial out as a word. Use the first name, capitalised.
    """
    if not getattr(user, "is_authenticated", False):
        return "there"

    raw = (getattr(user, "first_name", "") or getattr(user, "username", "") or "").strip()
    if not raw:
        return "there"

    if "@" in raw:
        raw = raw.split("@", 1)[0]

    raw = re.sub(r"[._\-]+", " ", raw)
    raw = re.sub(r"\d+", " ", raw).strip()

    parts = [p for p in raw.split() if p]
    if not parts:
        return "there"

    return parts[0].capitalize()


@csrf_exempt
def riya_chat(request):
    """Main Riya chat endpoint (non-streaming)."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)
    
    try:
        body = json.loads(request.body)
        message = body.get("message", "").strip()
        page = body.get("page", "unknown")
        path = body.get("path", "")
        # Skill Up uses hash routing (#load=...&title=...). The hash identifies
        # which lesson is actually open, so it must reach the assistant for
        # "what is this page about?" to resolve correctly.
        hash_value = body.get("hash", "")
        if hash_value and hash_value not in path:
            path = f"{path}{hash_value}"
        input_mode = body.get("input_mode", "text")
        user_name = _speakable_user_name(request.user)
        language = body.get("language", "english")
        is_employer = hasattr(request.user, "employer_profile") if request.user.is_authenticated else False
        
        data = riya_chat_logic(message, page, user_name, path=path, input_mode=input_mode, language=language, is_employer=is_employer, user=request.user)
        data["success"] = True

        # ── Master-prompt voice contract ────────────────────────────────────
        # Every response must be speakable regardless of whether the user typed
        # or spoke. Expose the {message, audio, speak} shape the spec requires:
        #   message : text response (alias of `reply`)
        #   speak   : always true — the client must auto-play the audio
        #   audio   : server-generated TTS (base64); null lets the client fall
        #             back to its own TTS endpoint / browser voice.
        reply_text = data.get("reply", "") or ""
        data.setdefault("message", reply_text)
        data["speak"] = True
        data.setdefault("audio", None)

        # Audio generation is synchronous (a 2-4s Sarvam TTS round trip that
        # blocks the whole reply). The chatbot UI speaks with the browser voice
        # and never uses this field, so default to NOT synthesising — a caller
        # that actually needs server audio opts in with {"want_audio": true}.
        want_audio = bool(body.get("want_audio", False))
        api_key = getattr(settings, "SARVAM_API_KEY", "")
        if want_audio and reply_text and api_key:
            try:
                norm_lang = normalize_language(data.get("language", language), message)
                lang_code = SUPPORTED_LANGUAGES.get(norm_lang, {"code": "en-IN"})["code"]
                audio = generate_riya_tts_audio(reply_text, api_key, lang_code)
                if audio:
                    data["audio"] = audio
            except Exception:
                # Never fail the chat response because TTS failed; the client
                # still speaks via its own fallback path.
                data["audio"] = None

        return JsonResponse(data)
    except Exception:
        logger.exception("Unhandled error in %s", request.path)
        return JsonResponse({"success": False, "error": _GENERIC_ERROR}, status=500)

@csrf_exempt
def riya_chat_stream(request):
    """Streaming Riya chat endpoint."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    try:
        body = json.loads(request.body)
        message = body.get("message", "").strip()
        page = body.get("page", "")
        path = body.get("path", "")
        hash_value = body.get("hash", "")
        if hash_value and hash_value not in path:
            path = f"{path}{hash_value}"
        input_mode = body.get("input_mode", "voice")
        language = body.get("language", "english")
        user_name = _speakable_user_name(request.user)
        api_key = getattr(settings, "SARVAM_API_KEY", "")
        is_employer = hasattr(request.user, "employer_profile") if request.user.is_authenticated else False
        history = body.get("history", [])
        if not isinstance(history, list):
            history = []

        def event_stream():
            for chunk in stream_assistant_response(message=message, page=page, api_key=api_key, user_name=user_name, path=path, input_mode=input_mode, language=language, is_employer=is_employer, user=request.user, history=history):
                yield chunk

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
    except Exception:
        logger.exception("Unhandled error in %s", request.path)
        return JsonResponse({"success": False, "error": _GENERIC_ERROR}, status=500)

@csrf_exempt
@require_POST
def riya_voice_transcribe(request):
    """Transcribes audio via Sarvam STT."""
    try:
        body = json.loads(request.body)
        audio_base64 = body.get("audio", "")
        mime_type = body.get("mime_type", "audio/webm")
        language = body.get("language", "english")
        
        language = normalize_language(language)
        lang_code = SUPPORTED_LANGUAGES.get(language, {"code": "en-IN"})["code"]
        
        transcript, _, stt_error = _transcribe_with_sarvam(audio_base64, mime_type, lang_code)
        if stt_error:
            client_transcript = str(body.get("client_transcript", "") or "").strip()
            if client_transcript:
                return JsonResponse({"success": True, "text": client_transcript, "source": "browser_fallback", "language": language})
            return JsonResponse({
                "success": False,
                "error": "Voice transcription is temporarily unavailable for this language.",
                "source": "stt_error",
                "language": language,
            }, status=200)
        return JsonResponse({"success": True, "text": transcript, "source": "sarvam", "language": language})
    except Exception:
        logger.exception("Unhandled error in %s", request.path)
        return JsonResponse({"success": False, "error": _GENERIC_ERROR}, status=500)

@require_GET
async def riya_tts_stream(request):
    """Buddy's voice as a streaming audio response.

    Used directly as an <audio> src, so the browser starts playing on the
    first bytes instead of waiting for the whole clip. Sarvam's batch endpoint
    answers only when synthesis is finished — 1.8s for a sentence, 4s+ for a
    paragraph — which is the silence the user sat through after the text had
    already appeared. Streaming puts the first audio out in ~0.5s whatever the
    length.

    GET (not POST) so it can be assigned straight to audio.src.
    """
    text = (request.GET.get("text") or "").strip()
    language = normalize_language(request.GET.get("language", "english"))
    speaker = (request.GET.get("speaker") or "").strip() or DEFAULT_TTS_SPEAKER
    emotion = (request.GET.get("emotion") or "neutral").strip().lower()
    if emotion not in ("happy", "sad", "neutral"):
        emotion = "neutral"

    if not text:
        return HttpResponse(status=404)

    lang_code = SUPPORTED_LANGUAGES.get(language, {"code": "en-IN"})["code"]
    # Sarvam bulbul speaks Indian languages only (vi-VN / ar-SA / ru-RU came
    # back as an empty clip); those get Google's fast female voices.
    if lang_code in GOOGLE_TTS_LANGS:
        return await _async_audio_stream_response(stream_google_tts_audio(text, lang_code, emotion))

    api_key = getattr(settings, "SARVAM_API_KEY", "")
    if not api_key or not lang_code.endswith("-IN"):
        return HttpResponse(status=404)

    # Everything is served as MP3 from one pipeline, warmed or not. This used
    # to answer a warmed line from the BATCH cache as audio/wav and everything
    # else as audio/mpeg from the stream — same speaker, different codec, so
    # Buddy's voice audibly changed between "Opening the activities page." and
    # the sentence after it. stream_riya_tts_audio() handles its own cache.
    # Sarvam's client is sync (requests): peek its first chunk off the event loop.
    return await sync_to_async(_audio_stream_response)(
        stream_riya_tts_audio(text, api_key, lang_code, speaker, emotion))


def _audio_stream_response(chunks):
    """Stream TTS audio, or 404 when the engine produced nothing.

    The first chunk is pulled before any header goes out. A failed synthesis
    used to be sent as an EMPTY 200 with a one-day cache header, so the
    browser replayed that silence for the same line all day; now the page
    gets a 404, uses its own voice, and the next request tries again.
    """
    first = next(chunks, None)
    if not first:
        return HttpResponse(status=404)
    response = StreamingHttpResponse(itertools.chain([first], chunks), content_type="audio/mpeg")
    response["Cache-Control"] = "private, max-age=86400"
    return response


async def _async_audio_stream_response(chunks):
    """_audio_stream_response() for an async generator, streamed as it arrives."""
    first = await anext(chunks, None)
    if not first:
        return HttpResponse(status=404)

    async def body():
        yield first
        async for chunk in chunks:
            yield chunk

    response = StreamingHttpResponse(body(), content_type="audio/mpeg")
    response["Cache-Control"] = "private, max-age=86400"
    return response


@csrf_exempt
@require_POST
def riya_tts(request):
    """Text-to-Speech for Riya chatbot."""
    try:
        body = json.loads(request.body)
        text = body.get("text", "").strip()
        language = body.get("language", "english")
        speaker = (body.get("speaker") or "").strip() or DEFAULT_TTS_SPEAKER
        # The browser detects the reply's mood (static/js/voice_prosody.js) and
        # sends it here, so the neural voice is shaped the same way the browser
        # fallback is. Anything unrecognised reads as neutral.
        emotion = (body.get("emotion") or "neutral").strip().lower()
        if emotion not in ("happy", "sad", "neutral"):
            emotion = "neutral"
        api_key = getattr(settings, "SARVAM_API_KEY", "")

        if not text or not api_key:
            return JsonResponse({"error": "Missing text or API key."}, status=400)

        language = normalize_language(language)
        lang_code = SUPPORTED_LANGUAGES.get(language, {"code": "en-IN"})["code"]

        audio = generate_riya_tts_audio(text, api_key, lang_code, speaker, emotion)
        return JsonResponse({"success": bool(audio), "audio": audio, "language": language,
                             "emotion": emotion, "available": bool(audio)})
    except Exception:
        logger.exception("Unhandled error in %s", request.path)
        return JsonResponse({"success": False, "error": _GENERIC_ERROR}, status=500)
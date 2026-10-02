import requests
import json
from django.conf import settings
from .base import BaseAgent
from .utils import transcribe_with_sarvam, has_meaningful_speech, SARVAM_CHAT_URL, SARVAM_TTS_URL, generate_riya_tts_audio
from ..riya_assistant import riya_chat_logic, stream_assistant_response, normalize_language, SUPPORTED_LANGUAGES

class RiyaAgent(BaseAgent):
    def __init__(self):
        super().__init__("riya")

    def run(self, payload):
        action = payload.get("action")
        if action == "transcribe":
            return self.transcribe(payload)
        if action == "chat":
            return self.chat(payload)
        if action == "stream":
            return self.stream(payload)
        return {"error": "Invalid action"}

    def transcribe(self, payload):
        import base64
        audio_base64 = payload.get("audio_base64", "")
        mime_type = payload.get("mime_type", "audio/webm")
        file_name = payload.get("file_name", "recording.webm")
        client_transcript = payload.get("client_transcript", "")
        language = normalize_language(payload.get("language", "english"))
        language_code = SUPPORTED_LANGUAGES.get(language, {"code": "en-IN"})["code"]
        api_key = settings.SARVAM_API_KEY

        if not audio_base64:
            raise ValueError("No audio provided")

        if "," in audio_base64:
            audio_base64 = audio_base64.split(",")[1]

        audio_bytes = base64.b64decode(audio_base64)

        if not api_key:
            raise ValueError("STT service not configured.")

        class AudioFile:
            def __init__(self, data, name, content_type):
                self._data = data
                self.name = name
                self.content_type = content_type
            def read(self):
                return self._data

        audio_file = AudioFile(audio_bytes, file_name, mime_type)
        transcript, stt_payload, stt_error = transcribe_with_sarvam(audio_file, api_key, language_code)

        if stt_error:
            if has_meaningful_speech(client_transcript):
                return {"text": client_transcript, "source": "browser_fallback"}
            raise ValueError(stt_error.get("message", "Transcription failed."))

        if not transcript:
            raise ValueError("No speech detected.")

        return {"text": transcript, "source": "hybrid"}

    def chat(self, payload):
        message = str(payload.get("message", "")).strip()
        page = str(payload.get("page", "")).strip()
        path = str(payload.get("path", "")).strip()
        input_mode = str(payload.get("input_mode", "voice")).strip().lower() or "voice"
        language = normalize_language(payload.get("language", "english"), message)
        include_audio = bool(payload.get("include_audio"))

        if not message:
            raise ValueError("Message is required.")

        api_key = settings.SARVAM_API_KEY
        response_payload = riya_chat_logic(
            message=message,
            page=page,
            path=path,
            input_mode=input_mode,
            api_key=api_key,
            user_name=payload.get("user_name"),
            language=language,
        )

        if (
            include_audio
            and input_mode == "voice"
            and api_key
            and response_payload.get("reply")
            and response_payload.get("source") == "ai"
        ):
            response_payload["audio"] = generate_riya_tts_audio(response_payload["reply"], api_key, SUPPORTED_LANGUAGES.get(language, {"code": "en-IN"})["code"])

        return response_payload

    def stream(self, payload):
        message = str(payload.get("message", "")).strip()
        page = str(payload.get("page", "")).strip()
        path = str(payload.get("path", "")).strip()
        input_mode = str(payload.get("input_mode", "voice")).strip().lower() or "voice"
        language = normalize_language(payload.get("language", "english"), message)
        api_key = settings.SARVAM_API_KEY

        if not message:
            raise ValueError("Message is required.")

        return stream_assistant_response(
            message=message,
            page=page,
            path=path,
            input_mode=input_mode,
            api_key=api_key,
            user_name=payload.get("user_name"),
            language=language,
        )

"""
core/aria_assistant.py
Compatibility alias — re-exports everything from core.riya_assistant so that
test patches targeting 'core.aria_assistant.requests.post' work correctly
while the implementation lives in riya_assistant.py.
"""
# Re-export the full public interface
from .riya_assistant import (  # noqa: F401
    ACTION_DEFINITIONS,
    FAST_REPLY_PATTERNS,
    QUICK_GUIDANCE_PATTERNS,
    SUPPORTED_LANGUAGES,
    normalize_language,
    SARVAM_CHAT_URL,
    build_assistant_payload,
    build_fallback_payload,
    normalize_text,
    resolve_navigation_intent,
    stream_assistant_response,
)

# Re-import requests so patching 'core.aria_assistant.requests' intercepts calls
import requests  # noqa: F401

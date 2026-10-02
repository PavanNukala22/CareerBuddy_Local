import logging
from django.conf import settings
from .base import BaseAgent, AgentInputError
from .utils import (
    transcribe_with_sarvam, fallback_text_module_analysis,
    analyze_text_with_sarvam_chat, merge_issues, has_meaningful_speech,
    choose_best_transcript, normalise_score_scale,
    compute_reference_similarity
)

logger = logging.getLogger(__name__)


class ReadingAgent(BaseAgent):
    def __init__(self):
        super().__init__("reading")

    def run(self, payload):
        text = payload.get("text", "")
        client_transcript = payload.get("client_transcript", "")
        reference_text = payload.get("reference_text", "")
        audio_file = payload.get("audio")
        api_key = settings.SARVAM_API_KEY

        duration_seconds = float(payload.get("duration_seconds", 0))
        pause_count = int(payload.get("pause_count", 0))

        stt_text = ""
        stt_error = None

        if audio_file and api_key:
            stt_text, _, stt_error = transcribe_with_sarvam(
                audio_file,
                api_key,
                prompt=reference_text
            )

        text = choose_best_transcript(
            [text, client_transcript, stt_text],
            reference_text
        )

        if not has_meaningful_speech(text):
            # BUG-ACT-05: surface a transcription-service fault instead of blaming
            # the learner when STT errored and there was no other input.
            if stt_error and not str(client_transcript or "").strip():
                logger.error(
                    "reading STT failed: %s",
                    stt_error.get("message")
                )
                raise RuntimeError(
                    "The speech transcription service is temporarily unavailable. "
                    "Please try again shortly."
                )

            # Must be AgentInputError, not a plain ValueError: safe_run() only
            # skips its retry loop for AgentInputError.
            raise AgentInputError(
                "Please provide a longer reading response."
            )

        if reference_text:
            similarity = compute_reference_similarity(
                reference_text,
                text
            )

            if similarity < 0.25:
                # Must be AgentInputError, not a plain ValueError — same
                # reasoning as the has_meaningful_speech check above.
                # safe_run() only skips its retry loop for AgentInputError;
                # a plain ValueError falls into its generic except-Exception
                # branch, which treats it as transient and retries the whole
                # call (including a fresh Sarvam STT round trip) 3 times with
                # backoff sleep before finally giving up — up to ~2.5 minutes
                # of hanging on an outcome that was never going to change,
                # since re-running the same low-similarity transcript through
                # STT again produces the same low similarity every time. That
                # multi-minute hang (and the mislabeled "Internal agent
                # error" it ends with once it does return) is what looked
                # like "the score is never generated."
                raise AgentInputError(
                    "Your reading does not seem to match the passage. "
                    "Please try again and read the passage provided."
                )

        analysis = fallback_text_module_analysis(
            "reading",
            text,
            reference_text,
            duration_seconds,
            pause_count
        )

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "reading",
                    text,
                    reference_text,
                    duration_seconds,
                    pause_count,
                    api_key
                )

                if external.get("scores"):
                    fallback_overall = analysis["scores"].get("overall")

                    analysis["scores"].update(
                        normalise_score_scale(external["scores"])
                    )

                    if fallback_overall is not None:
                        analysis["scores"]["overall"] = fallback_overall
                        analysis["scores"]["accuracy"] = fallback_overall

                if external.get("issues"):
                    analysis["issues"] = merge_issues(
                        external["issues"],
                        analysis["issues"]
                    )

                # BUG-ACT-06: prefer the AI narrative whenever the call succeeds.
                if external.get("improved_passage"):
                    analysis["improved_passage"] = external["improved_passage"]

                if external.get("feedback"):
                    analysis["feedback"] = external["feedback"]

                if external.get("quick_tip"):
                    analysis["quick_tip"] = external["quick_tip"]

            except Exception as exc:
                logger.error(
                    "reading AI analysis failed, using offline fallback: %s",
                    exc
                )

        # In reading, we want to highlight mistakes on the ORIGINAL passage
        # so the user sees where they made mistakes relative to the text.
        return {
            "text": reference_text or text,
            "issues": analysis["issues"],
            "improved_passage": analysis["improved_passage"],
            "scores": analysis["scores"],
            "feedback": analysis.get("feedback"),
            "quick_tip": analysis.get("quick_tip"),
            "user_transcript": text
        }
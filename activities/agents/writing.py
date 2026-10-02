import logging
from django.conf import settings
from .base import BaseAgent, AgentInputError
from .utils import (
    fallback_text_module_analysis, analyze_text_with_sarvam_chat,
    merge_issues, normalise_score_scale, repetition_ratio, clamp_score,
    compute_reference_similarity
)

logger = logging.getLogger(__name__)

class WritingAgent(BaseAgent):
    def __init__(self):
        super().__init__("writing")

    def run(self, payload):
        text = payload.get("text", "")
        # The essay topic/prompt the user was asked to write about. The
        # frontend has always sent this (writing.js appends it as
        # "reference_text"), but it was being silently dropped here — the AI
        # call below hardcoded "" in its place, so the AI graded grammar in
        # total isolation from what the user was actually supposed to write
        # about, with no way to notice an off-topic or repeated-filler answer.
        reference_text = payload.get("reference_text", "")
        api_key = settings.SARVAM_API_KEY
        non_space_chars = len("".join(str(text or "").split()))

        if not str(text or "").strip():
            raise AgentInputError("Please write something before analyzing.")
        if non_space_chars < 500:
            raise AgentInputError("Please write at least 500 characters before analyzing. Spaces are not counted.")
        if non_space_chars > 900:
            raise AgentInputError("Please keep your writing within 900 characters before analyzing. Spaces are not counted.")

        analysis = fallback_text_module_analysis("writing", text)

        if api_key:
            try:
                external = analyze_text_with_sarvam_chat(
                    "writing", text, reference_text, 0, 0, api_key, language=payload.get("language", "english")
                )
                if external:
                    if external.get("scores"):
                        analysis["scores"].update(normalise_score_scale(external["scores"]))
                    if external.get("issues"):
                        # Prioritise AI issues but keep the safety-net fallback issues too.
                        analysis["issues"] = merge_issues(external["issues"], analysis["issues"])
                    # BUG-ACT-06: when the AI call succeeds its narrative wins; the
                    # regex heuristic only supplements, it never overrides the AI.
                    if external.get("improved_passage"):
                        analysis["improved_passage"] = external["improved_passage"]
                    if external.get("feedback"):
                        analysis["feedback"] = external["feedback"]
                        analysis["is_ai_feedback"] = True
                    if external.get("quick_tip"):
                        analysis["quick_tip"] = external["quick_tip"]
            except Exception as exc:
                # AS-02: degrade to the offline result, but never silently — the
                # 404 that shipped BUG-ACT-01 was invisible precisely because this
                # was a bare `pass`.
                logger.error("writing AI analysis failed, using offline fallback: %s", exc)

        # Deterministic safety net, independent of what the AI decided: a
        # submission that pads out to the required length by repeating the
        # same sentence/line over and over is not genuine writing, even when
        # every individual repeated fragment is grammatically clean and the
        # AI graded it leniently anyway. Cap the score rather than trust the
        # AI call alone to have caught it.
        rep_ratio = repetition_ratio(text)
        if rep_ratio >= 0.34:
            capped = clamp_score(round(40 * (1 - rep_ratio)), 5)
            for key in list(analysis["scores"].keys()):
                analysis["scores"][key] = min(analysis["scores"][key], capped)
            if not analysis.get("is_ai_feedback"):
                analysis["feedback"] = (
                    "Your response repeats the same sentence or phrase multiple times instead of "
                    "presenting original writing on the topic. Please write a genuine, varied response."
                )
            analysis.setdefault("issues", [])
            analysis["issues"].insert(0, {
                "phrase": text[:80],
                "type": "Relevance",
                "message": "This response is largely repeated content, not an original answer to the prompt.",
                "suggestion": "Write your own sentences that directly address the given topic.",
            })

        # Another safety net: penalise heavily if the user just copied the prompt.
        if reference_text:
            similarity = compute_reference_similarity(reference_text, text)
            if similarity > 0.65:
                for key in list(analysis["scores"].keys()):
                    analysis["scores"][key] = min(analysis["scores"][key], 10)
                
                if not analysis.get("is_ai_feedback"):
                    analysis["feedback"] = (
                        "Your response is identical or highly similar to the prompt text. "
                        "Please write an original response that answers the prompt."
                    )
                analysis.setdefault("issues", [])
                analysis["issues"].insert(0, {
                    "phrase": text[:80],
                    "type": "Relevance",
                    "message": "This response appears to be a direct copy of the prompt.",
                    "suggestion": "Write your own sentences that directly address the given topic.",
                })

        # Another safety net: penalise if the user copied the AI's previously improved passage.
        previous_improved_passage = payload.get("previous_improved_passage", "")
        if previous_improved_passage:
            # We want to use the same logic, but we might want an even higher penalty if they just copy pasted it.
            similarity = compute_reference_similarity(previous_improved_passage, text)
            if similarity > 0.65:
                for key in list(analysis["scores"].keys()):
                    analysis["scores"][key] = min(analysis["scores"][key], 10)
                
                if not analysis.get("is_ai_feedback"):
                    analysis["feedback"] = (
                        "Your response is identical or highly similar to the improved version provided in your previous attempt. "
                        "Please write an original response."
                    )
                analysis.setdefault("issues", [])
                analysis["issues"].insert(0, {
                    "phrase": text[:80],
                    "type": "Originality",
                    "message": "This response appears to be copied from the previous AI-improved version.",
                    "suggestion": "Write your own original sentences rather than copying the feedback.",
                })

        # Ensure 'overall' is always present so _normalised_module_score in
        # views.py can read it directly rather than falling back to a default.
        scores = analysis["scores"]
        if "overall" not in scores:
            QUALITY_KEYS = {"grammar", "vocabulary"}
            quality_vals = [
                v for k, v in scores.items()
                if k in QUALITY_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            if quality_vals:
                scores["overall"] = round(sum(quality_vals) / len(quality_vals))
            else:
                vals = [
                    v for k, v in scores.items()
                    if k != "relevance" and isinstance(v, (int, float)) and not isinstance(v, bool)
                ]
                scores["overall"] = round(sum(vals) / len(vals)) if vals else 75

        return {
            "text": text,
            "issues": analysis["issues"],
            "improved_passage": analysis["improved_passage"],
            "scores": scores,
            "feedback": analysis.get("feedback"),
            "quick_tip": analysis.get("quick_tip")
        }

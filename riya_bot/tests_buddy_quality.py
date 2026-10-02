"""Buddy conversation-quality and identity regressions.

These cover the faults reported from the Skill Up screen: a navigation reply
that dead-ends instead of guiding, and a greeting that read the account's
stored name back verbatim ("Hello jagadeesh m!").
"""

from django.test import SimpleTestCase

from .riya_assistant import (
    ACTION_DEFINITIONS,
    BUDDY_VOICE_AND_MANNER,
    NAVIGATION_CHILDREN,
    _guided_navigation_reply,
)
from .views import _speakable_user_name


class _FakeUser:
    def __init__(self, first_name="", username="", authenticated=True):
        self.first_name = first_name
        self.username = username
        self.is_authenticated = authenticated


class SpeakableUserNameTests(SimpleTestCase):
    """Buddy greets people by first name, ready to be spoken aloud."""

    def test_trailing_surname_initial_is_dropped(self):
        """Regression: "Hello jagadeesh m!" — TTS read the "m" as a word."""
        user = _FakeUser(first_name="jagadeesh")
        self.assertEqual(_speakable_user_name(user), "Jagadeesh")

    def test_name_is_capitalised(self):
        self.assertEqual(_speakable_user_name(_FakeUser(first_name="jagadeesh")), "Jagadeesh")
        self.assertEqual(_speakable_user_name(_FakeUser(first_name="JAGADEESH")), "Jagadeesh")

    def test_email_username_loses_the_domain(self):
        user = _FakeUser(username="kondaparthisaiprasad227@gmail.com")
        name = _speakable_user_name(user)
        self.assertNotIn("@", name)
        self.assertNotIn("gmail", name.lower())
        self.assertFalse(any(ch.isdigit() for ch in name))

    def test_separators_and_digits_are_stripped(self):
        self.assertEqual(_speakable_user_name(_FakeUser(username="sai_prasad99")), "Sai")

    def test_anonymous_and_empty_fall_back(self):
        self.assertEqual(_speakable_user_name(_FakeUser(authenticated=False)), "there")
        self.assertEqual(_speakable_user_name(_FakeUser()), "there")


class GuidedNavigationTests(SimpleTestCase):
    """A navigation reply should open a conversation, not close one."""

    def test_reply_names_what_is_inside(self):
        reply = _guided_navigation_reply("lessons", "Opening the activities page.")
        self.assertIn("Opening the activities page.", reply)
        self.assertIn("Speaking & Presentation", reply)
        self.assertIn("Tell me which one", reply)

    def test_reply_invites_a_next_step(self):
        for key in ("lessons", "profile", "resume_builder"):
            with self.subTest(key=key):
                base = ACTION_DEFINITIONS[key]["response"]
                self.assertNotEqual(_guided_navigation_reply(key, base), base)

    def test_unknown_destination_is_left_alone(self):
        """Nothing useful to add means add nothing — never pad a reply."""
        base = "Opening your dashboard."
        self.assertEqual(_guided_navigation_reply("pro", base), base)

    def test_children_reference_real_actions(self):
        """Guidance is built from ACTION_DEFINITIONS, so it cannot drift."""
        for parent, children in NAVIGATION_CHILDREN.items():
            for child in children:
                with self.subTest(parent=parent, child=child):
                    self.assertIn(child, ACTION_DEFINITIONS)

    def test_guidance_is_speakable(self):
        """Every reply is also sent to TTS, so no markup or list characters."""
        reply = _guided_navigation_reply("lessons", "Opening the activities page.")
        for junk in ("<", ">", "*", "•", "\n", "1.", "- "):
            self.assertNotIn(junk, reply)

    def test_employer_never_sees_student_destinations(self):
        """Role isolation must survive the added guidance.

        Every child of `lessons` is student-only, so an employer must get the
        bare confirmation rather than a list of the other portal's modules.
        """
        reply = _guided_navigation_reply("lessons", "Opening.", is_employer=True)
        self.assertEqual(reply, "Opening.")

    def test_server_only_offers_what_it_can_deliver(self):
        """Buddy must not offer a choice it cannot then act on."""
        for parent, children in NAVIGATION_CHILDREN.items():
            for child in children:
                with self.subTest(parent=parent, child=child):
                    self.assertIn(child, ACTION_DEFINITIONS)
                    self.assertTrue(ACTION_DEFINITIONS[child].get("route"))


class VoiceAndMannerTests(SimpleTestCase):
    """The register block is shared by both AI paths."""

    def test_manner_block_is_present_and_substantive(self):
        self.assertIn("HOW TO SOUND", BUDDY_VOICE_AND_MANNER)
        self.assertIn("never reuse the same phrasing", BUDDY_VOICE_AND_MANNER)
        self.assertIn("do not stop at announcing it", BUDDY_VOICE_AND_MANNER)

    def test_manner_block_forbids_unspeakable_output(self):
        self.assertIn("no bullet characters", BUDDY_VOICE_AND_MANNER)


class WelcomeCardWiringTests(SimpleTestCase):
    """Every follow-up card in BOTscript.js must point at a real action and icon.

    buildWelcomeCard() silently drops a card whose actionKey is undefined, which
    is how the dashboard's "Job Recommendations" card vanished.
    """

    def test_card_action_keys_and_icons_exist(self):
        import re
        from pathlib import Path

        js = (Path(__file__).resolve().parent.parent / "static" / "js" / "BOTscript.js").read_text(encoding="utf-8")
        actions_block = js[js.index("const ACTION_DEFINITIONS = {"):js.index("const STUDENT_ACTION_KEYS")]
        defined = set(re.findall(r"^        (\w+): \{", actions_block, re.M))
        icons_block = js[js.index("const WELCOME_ICONS = {"):js.index("SECTION-AWARE FOLLOW-UPS")]
        icons = set(re.findall(r"^        (\w+): '<svg", icons_block, re.M))

        used = re.findall(r'actionKey: "(\w+)", icon: "(\w+)"', js)
        used += re.findall(r'c\("[\w-]+", "(\w+)", "(\w+)"', js)
        self.assertGreater(len(used), 30)
        # Every card must carry a context line Buddy speaks before navigating.
        no_context = re.findall(r'c\("([\w-]+)", "\w+", "\w+", "[^"]*", "[^"]*"\)', js)
        no_context += re.findall(r'id: "([\w-]+)"[^}]*description: "[^"]*" \}', js)
        self.assertEqual([], no_context, "cards without a context line")

        # ...and a translation of it in every non-English chatbot language.
        i18n = js[js.index("const CONTEXT_I18N = {"):js.index("function getAssistantSection")]
        card_ids = set(re.findall(r'(?:c\(|id: )"((?:sec|guest|student|employer)-[\w-]+)"', js))
        for card_id in card_ids:
            entry = i18n.split(f'"{card_id}": {{', 1)
            self.assertEqual(2, len(entry), f"no translations for {card_id!r}")
            block = entry[1].split("},", 1)[0]
            for lang in ("vietnam", "hindi", "arabic", "russian"):
                self.assertRegex(block, rf'{lang}: "[^"]+"', f"{card_id!r} missing {lang}")

        # Card titles: section cards via TITLE_I18N, role cards via
        # RECOMMENDATION_TRANSLATIONS (keyed by the English title).
        titles = js[js.index("const TITLE_I18N = {"):js.index("const CONTEXT_I18N = {")]
        for card_id in re.findall(r'c\("(sec-[\w-]+)"', js):
            line = re.search(rf'"{card_id}": \{{(.*)\}},', titles)
            self.assertIsNotNone(line, f"no title translations for {card_id!r}")
            for lang in ("vietnam", "hindi", "arabic", "russian"):
                self.assertRegex(line.group(1), rf'{lang}: "[^"]+"', f"{card_id!r} title missing {lang}")
        rec = js[js.index("const RECOMMENDATION_TRANSLATIONS = {"):js.index("const WELCOME_CONTEXT = {")]
        for lang in ("hindi", "vietnam", "arabic", "russian"):
            lang_block = rec.split(f"{lang}: {{", 1)[1].split("}", 1)[0]
            for title in re.findall(r'id: "(?:guest|student|employer)-[\w-]+",[^}]*title: "([^"]+)"', js):
                self.assertIn(f'"{title}":', lang_block, f"role card title {title!r} missing {lang}")
        for key, icon in used:
            self.assertIn(key, defined, f"card uses undefined action {key!r}")
            self.assertIn(icon, icons, f"card uses undefined icon {icon!r}")
            self.assertIn('width="', icons_block.split(f"{icon}: '")[1].split(">")[0],
                          f"icon {icon!r} needs explicit width so it can't render huge without CSS")


class LanguageParityTests(SimpleTestCase):
    """Non-English sessions must get the same replies as English, translated."""

    LANGS = ("hindi", "vietnamese", "arabic", "russian")

    def test_every_action_has_a_translated_section_name(self):
        from .section_names import SECTION_NAMES

        for key in ACTION_DEFINITIONS:
            for lang in self.LANGS:
                self.assertTrue(SECTION_NAMES.get(key, {}).get(lang), f"{key!r} has no {lang} name")

    def test_opening_uses_translated_name_not_english_label(self):
        from .riya_assistant import localized_action_response

        self.assertEqual(localized_action_response("certifications", "russian"), "Открываю ваши сертификаты.")
        self.assertNotIn("Grammar", localized_action_response("grammar", "vietnam"))

    def test_informational_reply_keeps_translated_menu(self):
        """Regression: non-English got a bare "Opening X" — the menu was dropped."""
        from .riya_assistant import _navigation_reply

        reply = _navigation_reply("lessons", "what is activities", "hindi")
        self.assertIn("अंदर आपको", reply)
        self.assertNotIn("Inside you'll find", reply)

    def test_english_reply_unchanged(self):
        from .riya_assistant import _navigation_reply

        self.assertEqual(_navigation_reply("grammar", "open grammar", "english"),
                         ACTION_DEFINITIONS["grammar"]["response"])

    def test_gate_and_upsell_messages_are_translated(self):
        from .section_names import MESSAGES

        for key, table in MESSAGES.items():
            for lang in self.LANGS:
                self.assertTrue(table.get(lang), f"{key!r} missing {lang}")


class TtsVoiceRoutingTests(SimpleTestCase):
    """Vietnamese, Arabic and Russian are voiced by Google; failures are not cached."""

    def test_non_indian_languages_have_female_voices(self):
        from .agents.utils import GOOGLE_TTS_LANGS
        from .riya_assistant import SUPPORTED_LANGUAGES

        for language in ("vietnam", "arabic", "russian"):
            code = SUPPORTED_LANGUAGES[language]["code"]
            self.assertIn(code, GOOGLE_TTS_LANGS, f"{language} has no voice")

    def test_google_tts_pieces_fit_the_endpoint_and_keep_all_text(self):
        from .agents.utils import GOOGLE_TTS_MAX_CHARS, _split_for_google_tts

        text = ("Chào mừng bạn đến với CareerBuddy, tôi là trợ lý của bạn. " * 6).strip()
        pieces = _split_for_google_tts(text)
        self.assertGreater(len(pieces), 1)
        self.assertTrue(all(0 < len(p) <= GOOGLE_TTS_MAX_CHARS for p in pieces))
        self.assertEqual(" ".join(pieces).split(), text.split())

    def test_empty_synthesis_is_a_404_not_a_cached_empty_200(self):
        from .views import _audio_stream_response

        self.assertEqual(_audio_stream_response(iter([])).status_code, 404)
        ok = _audio_stream_response(iter([b"abc", b"def"]))
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(b"".join(ok.streaming_content), b"abcdef")

    def test_async_stream_404s_when_empty_and_streams_otherwise(self):
        import asyncio

        from .views import _async_audio_stream_response

        async def gen(*parts):
            for part in parts:
                yield part

        async def run():
            empty = await _async_audio_stream_response(gen())
            ok = await _async_audio_stream_response(gen(b"ab", b"cd"))
            body = b"".join([chunk async for chunk in ok.streaming_content])
            return empty.status_code, ok.status_code, body

        self.assertEqual((404, 200, b"abcd"), asyncio.run(run()))

    def test_google_tts_splits_arabic_at_arabic_commas(self):
        from .agents.utils import GOOGLE_TTS_MAX_CHARS, _split_for_google_tts

        clause = "مرحبًا بك في CareerBuddy أنا مساعدك وسأساعدك كل يوم،"
        pieces = _split_for_google_tts(" ".join([clause] * 8))
        self.assertTrue(all(len(p) <= GOOGLE_TTS_MAX_CHARS for p in pieces))
        self.assertTrue(all(p.endswith("،") for p in pieces), pieces)

"""Skill Up regression and hallucination suite.

Run with:  python manage.py test riya_bot.tests_skillup -v 2
"""

from django.test import SimpleTestCase

from .skillup_catalog import get_manifest, skillup_root
from .skillup_intents import try_handle
from .skillup_service import SkillUpKnowledgeService

HUB = "/skill-up/"
GENAI = HUB + "#load=TechCenter/010%20genai-course-guide.html&title=GenAI%20Course%20Guide"


class SkillUpCatalogTests(SimpleTestCase):
    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")
        self.service = SkillUpKnowledgeService()

    def test_catalog_builds(self):
        self.assertTrue(self.service.available)
        self.assertGreater(self.service.count_sections(), 0)
        self.assertGreater(self.service.count_lessons(), 0)

    def test_counts_are_internally_consistent(self):
        """Totals must equal the sum of their parts — no double counting."""
        total = sum(s.lesson_count for s in self.service.get_sections())
        self.assertEqual(total, self.service.count_lessons())
        subs = sum(s.subsection_count for s in self.service.get_sections())
        self.assertEqual(subs, self.service.count_subsections())

    def test_every_lesson_has_a_readable_source(self):
        """PART 64: verify every catalog item resolves to a real file."""
        for lesson in self.service.get_lessons():
            with self.subTest(lesson=lesson.title):
                self.assertTrue(
                    self.service.get_page_content(lesson, max_chars=200),
                    f"{lesson.title} -> {lesson.source_file} unreadable",
                )

    def test_every_route_is_trusted(self):
        for lesson in self.service.get_lessons():
            self.assertTrue(self.service.route_is_trusted(lesson.route))
        for section in self.service.get_sections():
            self.assertTrue(self.service.route_is_trusted(section.route))

    def test_path_traversal_is_rejected(self):
        """A path not vouched for by the catalog must never be read."""
        for evil in ["../../settings.py", "/etc/passwd",
                     "TechCenter/../../../manage.py", "..%2f..%2fsecret"]:
            self.assertIsNone(self.service._safe_path(evil))


class SkillUpResolutionTests(SimpleTestCase):
    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")
        self.service = SkillUpKnowledgeService()

    def test_fuzzy_aliases_resolve(self):
        for query in ["gen ai", "genai", "crew ai", "crewai", "dbms",
                      "vector db", "vector database", "python", "ui ux", "ux",
                      "prompt engineering", "prompting", "cefr"]:
            with self.subTest(query=query):
                self.assertTrue(self.service.resolve(query),
                                f"{query!r} resolved to nothing")

    def test_nonexistent_content_resolves_to_nothing(self):
        """PART 63: the model must never be handed a fabricated match."""
        for query in ["java spring boot", "solidity", "xyz course",
                      "kubernetes helm charts", "rust ownership"]:
            with self.subTest(query=query):
                self.assertEqual(self.service.resolve(query), [],
                                 f"{query!r} produced a phantom match")

    def test_ambiguity_is_detected(self):
        matches = self.service.resolve("logical reasoning")
        if len(matches) > 1:
            self.assertTrue(self.service.is_ambiguous(matches))


class SkillUpIntentTests(SimpleTestCase):
    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")
        self.service = SkillUpKnowledgeService()

    def test_counts_are_deterministic_not_generated(self):
        result = try_handle("How many sections are in Skill Up?", path=HUB)
        self.assertIsNotNone(result)
        self.assertIn(str(self.service.count_sections()), result["reply"])
        self.assertEqual(result["source"], "skillup")

    def test_section_scoped_count(self):
        result = try_handle("How many lessons are under Tech?", path=HUB)
        tech = self.service.get_section("tech")
        self.assertIn(str(tech.lesson_count), result["reply"])

    def test_navigation_returns_a_trusted_route(self):
        result = try_handle("Open GenAI.", path="/")
        self.assertTrue(result["actions"])
        route = result["actions"][0]["route"]
        self.assertTrue(self.service.route_is_trusted(route))

    def test_navigation_reply_is_speakable(self):
        """PART 56: no NAV tag or raw URL may appear in spoken text."""
        result = try_handle("Open Python.", path="/")
        self.assertNotIn("<NAV", result["reply"])
        self.assertNotIn("http", result["reply"])
        self.assertNotIn("#load=", result["reply"])

    def test_ambiguous_navigation_asks_instead_of_guessing(self):
        result = try_handle("Open logical reasoning.", path=HUB)
        self.assertIn("Which one", result["reply"])

    def test_missing_content_is_refused_not_invented(self):
        for message in ["Is there a Solidity course in skill up?",
                        "Open the XYZ course.",
                        "How many Java lessons are in skill up?"]:
            with self.subTest(message=message):
                result = try_handle(message, path=HUB)
                self.assertIsNotNone(result)
                self.assertIn("couldn't", result["reply"].lower())

    def test_current_page_context_resolves_the_open_lesson(self):
        context = self.service.get_current_context(path=GENAI)
        self.assertTrue(context.in_skillup)
        self.assertIsNotNone(context.lesson)
        self.assertIn("genai", context.lesson.lesson_id)
        self.assertEqual(context.section.section_id, "depth-tech")

    def test_current_page_siblings(self):
        result = try_handle("What else is available in this section?", path=GENAI)
        self.assertIsNotNone(result)
        self.assertTrue(result["actions"])

    def test_page_question_returns_grounded_content(self):
        result = try_handle("What is this page about?", path=GENAI)
        self.assertIn("_skillup_grounding", result)
        lesson = result["_skillup_grounding"]["matched_lesson"]
        self.assertTrue(lesson["page_content"])

    def test_retrieved_content_cannot_carry_instructions(self):
        lesson = self.service.get_lesson("genai")
        content = self.service.get_page_content(lesson)
        for probe in ["ignore previous instructions", "<NAV:", "system prompt:"]:
            self.assertNotIn(probe, content.lower())


class BuddyRegressionTests(SimpleTestCase):
    """Existing Buddy behaviour must be untouched."""

    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")

    def test_existing_navigation_is_not_captured(self):
        for message in ["Open Dashboard", "Open Grammar", "Open Activities",
                        "Open Resume Builder", "Open Roleplay",
                        "Open Group Discussion", "Open JAM", "Open Membership",
                        "Post a Job", "Find Candidates", "View Applications",
                        "Open Job Search", "Open Mock Interview"]:
            with self.subTest(message=message):
                self.assertIsNone(
                    try_handle(message, path="/"),
                    f"Skill Up wrongly captured {message!r}",
                )

    def test_general_questions_are_not_captured(self):
        for message in ["What is Python?", "How do I write a resume?",
                        "Tell me a joke", "What is the weather"]:
            with self.subTest(message=message):
                self.assertIsNone(try_handle(message, path="/"))


class SkillUpHubPageTests(SimpleTestCase):
    """The Skill Up page must carry the SAME Buddy every other page carries.

    These guard the three faults that made Buddy absent from, or unusable on,
    /skill-up/ even though the assistant partial was already being included.
    """

    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")

    def test_hub_renders_the_one_buddy(self):
        """Buddy's markup must survive injection of the Skill Up body.

        Skill Up's error handler contains a literal "</body>" inside a
        JavaScript string. A lazy body regex stopped there, truncating the
        injected markup inside an unterminated <script> — the parser then
        swallowed Buddy as script text and no launcher existed in the DOM.
        """
        html = self.client.get(HUB).content.decode("utf-8", "replace")
        for marker in ('id="riya-launcher"',
                       'id="riya-thought-bubble"',
                       'id="riya-assistant-root"',
                       'id="riya-mic-button"',
                       'id="chatbotLanguageSelect"',
                       'id="riya-text-input"'):
            self.assertIn(marker, html, f"Buddy is missing {marker} on Skill Up")

        # Exactly one Buddy — never a second chatbot.
        self.assertEqual(html.count('id="riya-assistant-root"'), 1)

        # The body must be injected whole, up to the real closing tag.
        self.assertIn("data-careerbuddy-hub", html)

    def test_hub_loads_buddys_stylesheet(self):
        """base.html loads this for every other page; the hub must too.

        Without it the launcher and chat panel render unstyled and are
        effectively invisible, which is indistinguishable from "no chatbot".
        """
        html = self.client.get(HUB).content.decode("utf-8", "replace")
        self.assertIn("css/riya_assistant.css", html)
        self.assertIn("js/BOTscript.js", html)

    def test_skillup_routes_keep_the_user_on_the_buddy_page(self):
        """Buddy must never navigate the user off its own page.

        The raw static file never passes through the template engine, so a
        /static/... route would land the user on a Skill Up page with no
        assistant on it — the exact bug this integration exists to fix.
        """
        service = SkillUpKnowledgeService()
        for section in service.get_sections():
            with self.subTest(section=section.title):
                self.assertTrue(section.route.startswith(HUB), section.route)
        for lesson in service.get_lessons():
            with self.subTest(lesson=lesson.title):
                self.assertTrue(lesson.route.startswith(HUB), lesson.route)
                self.assertNotIn("/static/", lesson.route)


class SkillUpNamedButMissingTests(SimpleTestCase):
    """A subject that isn't in Skill Up is reported missing, never substituted."""

    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")

    def test_unknown_subject_is_not_answered_with_the_current_page(self):
        """Regression: "how many Java lessons" answered about the open lesson.

        Standing on a Tech Center lesson, the current-page fallback took over
        whenever the named subject failed to resolve, so Buddy confidently
        described "AI - ML - agents" to someone who asked about Java.
        """
        for message in ["How many Java lessons are in Skill Up?",
                        "How many Solidity lessons are there?",
                        "How many Kubernetes courses are in Skill Up?"]:
            with self.subTest(message=message):
                result = try_handle(message, path=GENAI)
                self.assertIsNotNone(result)
                reply = result["reply"].lower()
                self.assertIn("couldn't find", reply)
                self.assertNotIn("ml", reply.replace("html", ""))

    def test_known_subject_still_counts_correctly(self):
        """The fix must not make real subjects unanswerable."""
        result = try_handle("How many lessons are under Tech?", path=HUB)
        self.assertIsNotNone(result)
        self.assertIn(str(SkillUpKnowledgeService().count_lessons("Tech")), result["reply"])

    def test_unscoped_current_page_question_still_uses_the_page(self):
        """Naming nothing must still fall back to the page the user is on."""
        result = try_handle("How many lessons are here?", path=GENAI)
        self.assertIsNotNone(result)
        self.assertNotIn("couldn't find", result["reply"].lower())


class SkillUpCurrentPageTests(SimpleTestCase):
    """Questions about "here" answer from the catalog, not from the model."""

    PY_LESSON = HUB + "#load=TechCenter/020%20python_learning.html&title=Python%20Learning"

    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")

    def test_breadcrumb_questions_are_deterministic(self):
        """Regression: these fell through to the AI, which answered about the
        platform in general rather than the lesson actually open."""
        for message in ["What section is this under?",
                        "Where am I?",
                        "Which section is this in?"]:
            with self.subTest(message=message):
                result = try_handle(message, path=self.PY_LESSON)
                self.assertIsNotNone(result, "fell through to the AI path")
                self.assertEqual(result["source"], "skillup")
                self.assertIn("Tech Center", result["reply"])
                self.assertIn("Programming foundations", result["reply"])

    def test_breadcrumb_does_not_steal_sibling_or_count_questions(self):
        """The breadcrumb branch must not swallow more specific questions."""
        siblings = try_handle("What else is available in this section?",
                              path=self.PY_LESSON)
        self.assertIn("Also in", siblings["reply"])

        count = try_handle("How many lessons are in this section?",
                           path=self.PY_LESSON)
        self.assertIn(str(SkillUpKnowledgeService().count_lessons(subsection="Programming foundations")), count["reply"])

    def test_replies_are_speakable(self):
        """Every reply is also sent to TTS, so no markup or arrow glyphs."""
        for message in ["Where am I?", "What else is available in this section?"]:
            with self.subTest(message=message):
                reply = try_handle(message, path=self.PY_LESSON)["reply"]
                for junk in ("<", ">", "->", "→", "#load="):
                    self.assertNotIn(junk, reply)


class SkillUpMultilingualTests(SimpleTestCase):
    """Non-English phrasing must not be mistaken for a missing subject."""

    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")

    def test_transliterated_hindi_counts_are_answered(self):
        """Regression: the leftover grammar of a Hindi question ("mein kitne
        hain") was read as the name of a subject, so a valid question about
        Skill Up's size was refused as content that does not exist."""
        for message in ["Skill Up mein kitne sections hain?",
                        "Skill Up mein kitne lessons hain?"]:
            with self.subTest(message=message):
                result = try_handle(message, path=HUB)
                self.assertIsNotNone(result)
                self.assertNotIn("couldn't find", result["reply"].lower())
                self.assertRegex(result["reply"], r"\d")

    def test_missing_subject_is_still_refused(self):
        """Relaxing the filter must not reopen the hallucination hole."""
        for message in ["How many Java lessons are in Skill Up?",
                        "How many Solidity courses are in Skill Up?"]:
            with self.subTest(message=message):
                self.assertIn("couldn't find",
                              try_handle(message, path=HUB)["reply"].lower())

    def test_plain_totals_still_answer(self):
        reply = try_handle("How many lessons are in Skill Up?", path=HUB)["reply"]
        self.assertIn(str(SkillUpKnowledgeService().count_lessons()), reply)


class SkillUpDoesNotHijackBuddyTests(SimpleTestCase):
    """Standing on a Skill Up page must not hand Skill Up the whole assistant.

    The earlier regression test only checked requests made from "/". From
    inside Skill Up every "open …" was claimed by the Skill Up resolver, so
    "open my dashboard" came back as "I couldn't find 'my dashboard' in
    Skill Up" instead of opening the dashboard.
    """

    CORE_REQUESTS = [
        "open my dashboard", "take me to resume builder", "open grammar",
        "open activities", "open group discussion", "open jam",
        "open roleplay", "job search", "find jobs", "open membership",
        "mock interview", "go to home",
    ]

    def setUp(self):
        if not skillup_root():
            self.skipTest("Skill Up content not installed")

    def test_core_navigation_falls_through_from_inside_skill_up(self):
        for message in self.CORE_REQUESTS:
            with self.subTest(message=message):
                self.assertIsNone(
                    try_handle(message, path=HUB),
                    f"Skill Up wrongly captured {message!r} from inside the hub",
                )

    def test_core_navigation_still_falls_through_from_a_lesson(self):
        lesson = HUB + "#load=TechCenter/020%20python_learning.html&title=Python%20Learning"
        for message in self.CORE_REQUESTS:
            with self.subTest(message=message):
                self.assertIsNone(try_handle(message, path=lesson))

    def test_skill_up_requests_are_still_handled(self):
        """The guard must not cost Skill Up its own navigation."""
        for message, expected in [
            ("open python learning", "Python learning"),
            ("open genai", "GenAI"),
            ("open dsa tutorial", "DSA tutorial"),
        ]:
            with self.subTest(message=message):
                result = try_handle(message, path=HUB)
                self.assertIsNotNone(result, f"{message!r} fell through")
                self.assertIn(expected, result["reply"])

    def test_exact_skill_up_title_still_wins(self):
        """"Grammar activities" is a real lesson and must stay in Skill Up,
        even though "grammar" alone belongs to the core Buddy."""
        result = try_handle("open grammar activities", path=HUB)
        self.assertIsNotNone(result)
        self.assertIn("Grammar activities", result["reply"])

    def test_structural_questions_are_unaffected(self):
        result = try_handle("how many lessons are under Tech?", path=HUB)
        self.assertIsNotNone(result)
        self.assertIn(str(SkillUpKnowledgeService().count_lessons("Tech")), result["reply"])

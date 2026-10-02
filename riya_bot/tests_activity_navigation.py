"""
Regression tests for chatbot activity navigation across all 27 activities.

Background: "Professional Speaking" (Activity order 24) and "Professional
Reading" (order 23) are individual activities, distinct from the
"professional_speaking" ACTION_DEFINITIONS entry, which opens the *Speaking
& Presentation category* (/activities/?category=speaking). Several matching
layers (the client-side local resolver's own copy of ACTION_DEFINITIONS,
this module's `_intent_score`, and MULTILINGUAL_INTENT_ALIASES) used
word-boundary-free substring matching and/or had drifted keyword lists,
which let "Open Professional Speaking" resolve to the category page instead
of the individual activity, and let "Open Professional Reading" internally
mis-resolve toward the "pro" (Membership) action.

The fix is not per-activity hardcoding: resolve_navigation_intent() now
never confidently returns an ACTION_DEFINITIONS key whose route is a
`/activities/?category=` listing (see `_is_category_route_key`), for any
of the reasons a key might otherwise be chosen (multilingual alias, direct
label/keyword match, or the scored English resolver). That decision is left
entirely to resolve_activity_navigation_payload(), which queries the real
Activity table and already prefers an exact/full activity-title match over
a category match, for every category action, not just the two named in the
original bug report. This suite exercises all 27 seeded activities to guard
against the underlying class of bug recurring, not just its two symptoms.
"""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from activities.models import Activity
from .riya_assistant import resolve_navigation_intent, riya_chat_logic

User = get_user_model()


class ActivityNavigationTests(TestCase):
    """Every one of the 27 activities must have a unique, deterministic
    chatbot navigation mapping, and must never be shadowed by an
    ACTION_DEFINITIONS category action that happens to share words with
    its title.
    """

    @classmethod
    def setUpTestData(cls):
        call_command("populate_activities")
        call_command("setup_professional_modules")
        cls.user = User.objects.create_user(
            username="nav_test_user", password="x", is_staff=True,
        )
        cls.activities = list(
            Activity.objects.filter(is_active=True).order_by("order")
        )

    def test_all_27_activities_are_seeded(self):
        self.assertEqual(
            len(self.activities), 27,
            "Expected exactly 27 seeded activities (20 Business English + "
            "4 professional AI modules + 3 Interactive Workshop) — a "
            "management-command change likely broke seeding.",
        )

    def test_every_activity_resolves_to_its_own_route(self):
        """User command -> correct activity identified -> correct action ->
        correct route -> correct page, for every activity and several
        natural-language phrasings of each.
        """
        phrasings = [
            "Open {title}",
            "Go to {title}",
            "Take me to {title}",
            "I want {title}",
        ]
        failures = []
        for activity in self.activities:
            expected_route = f"/activities/{activity.pk}/"
            for template in phrasings:
                message = template.format(title=activity.title)
                result = riya_chat_logic(
                    message, page="dashboard", user=self.user, api_key=None,
                )
                actions = result.get("actions") or []
                route = actions[0].get("route") if actions else None
                if route != expected_route:
                    failures.append(
                        (activity.order, activity.title, message, route)
                    )

        self.assertEqual(
            failures, [],
            f"{len(failures)} phrasing(s) did not resolve to their own "
            f"activity's route: {failures}",
        )

    def test_professional_speaking_never_opens_professional_reading(self):
        """The regression named explicitly in the bug report."""
        for message in [
            "Open Professional Speaking", "Go to Professional Speaking",
            "I want Professional Speaking", "Take me to Professional Speaking",
        ]:
            result = riya_chat_logic(
                message, page="dashboard", user=self.user, api_key=None,
            )
            actions = result.get("actions") or []
            self.assertTrue(actions, f"{message!r} produced no action")
            self.assertEqual(actions[0]["label"], "Professional Speaking")
            self.assertNotEqual(actions[0]["label"], "Professional Reading")

    def test_professional_reading_never_opens_professional_speaking(self):
        for message in ["Open Professional Reading", "Go to Professional Reading"]:
            result = riya_chat_logic(
                message, page="dashboard", user=self.user, api_key=None,
            )
            actions = result.get("actions") or []
            self.assertTrue(actions, f"{message!r} produced no action")
            self.assertEqual(actions[0]["label"], "Professional Reading")
            self.assertNotEqual(actions[0]["label"], "Professional Speaking")

    def test_bare_category_words_still_open_the_category(self):
        """The fix must not overcorrect: a message with no specific
        activity name should still open the category listing.
        """
        cases = {
            "open speaking": "/activities/?category=speaking",
            "go to negotiation and meetings": "/activities/?category=negotiation",
            "open writing and correspondence": "/activities/?category=writing",
        }
        for message, expected_route in cases.items():
            result = riya_chat_logic(
                message, page="dashboard", user=self.user, api_key=None,
            )
            actions = result.get("actions") or []
            self.assertTrue(actions, f"{message!r} produced no action")
            self.assertEqual(actions[0]["route"], expected_route)

    def test_free_plan_restriction_is_not_bypassed(self):
        """Locked activities must still paywall for a non-premium/anonymous
        user; the navigation fix must not touch this boundary.
        """
        # The real Free Plan catalogue (activities.views) decides, not order
        # numbers: Professional Reading is free, Professional Speaking is not.
        from activities.views import FREE_PLAN_ACTIVITY_TITLES

        free_activity = next(a for a in self.activities if a.title == "Professional Reading")
        locked_activity = next(a for a in self.activities if a.title == "Professional Speaking")
        self.assertIn(free_activity.title, FREE_PLAN_ACTIVITY_TITLES)
        self.assertNotIn(locked_activity.title, FREE_PLAN_ACTIVITY_TITLES)

        free_result = riya_chat_logic(
            f"Open {free_activity.title}", page="dashboard", user=None, api_key=None,
        )
        self.assertEqual(
            free_result["actions"][0]["route"], f"/activities/{free_activity.pk}/",
        )

        locked_result = riya_chat_logic(
            f"Open {locked_activity.title}", page="dashboard", user=None, api_key=None,
        )
        self.assertEqual(locked_result["actions"][0]["key"], "pro")

    def test_resolve_navigation_intent_never_claims_a_category_key(self):
        """resolve_navigation_intent() alone (before the catalog-aware
        resolver runs) must never confidently return a category-route key
        — that decision belongs entirely to
        resolve_activity_navigation_payload(), which can see the real
        Activity table. This is the structural guard against the bug
        recurring for some other activity/category name pair in future.
        """
        from .riya_assistant import ACTION_DEFINITIONS, _is_category_route_key

        category_keys = {
            key for key in ACTION_DEFINITIONS if _is_category_route_key(key)
        }
        self.assertTrue(category_keys, "Expected at least one category key to test against")

        for activity in self.activities:
            key = resolve_navigation_intent(
                f"Open {activity.title}", language="english", api_key=None, user=None,
            )
            self.assertNotIn(
                key, category_keys,
                f"resolve_navigation_intent() claimed category key {key!r} "
                f"for activity {activity.title!r}",
            )

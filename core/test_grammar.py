"""Grammar module regression tests — FR-GRM-01 … FR-GRM-04 (FSD section 12.6).

The module had no test coverage, so every defect in the 13 Aug review was found
on first contact. These lock down the four requirements and the four defects.

Run: python manage.py test core
"""
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

import subject_views as sv

User = get_user_model()

TOPICS = ['noun', 'pronoun', 'verb', 'adjective', 'adverb', 'conjunction',
          'tenses', 'sentence-structure', 'types-of-sentences']


def make_user(name, plan='free'):
    user = User.objects.create_user(name, f'{name}@x.com', 'pw12345!')
    profile = user.profile
    profile.plan_type = plan
    profile.is_pro = (plan == 'pro')
    profile.subscription_start = None if plan == 'free' else timezone.now()
    profile.save()
    return user


class GrammarIndexTests(TestCase):
    """FR-GRM-01 — nine topics, each with an emoji, summary and link."""

    def setUp(self):
        self.client.force_login(make_user('grm_idx'))

    def test_index_lists_exactly_the_nine_specified_topics_in_order(self):
        cards = self.client.get(reverse('subject')).context['topics']
        self.assertEqual([c['slug'] for c in cards], TOPICS)

    def test_every_card_carries_emoji_summary_and_link(self):
        resp = self.client.get(reverse('subject'))
        body = resp.content.decode()
        for card in resp.context['topics']:
            with self.subTest(topic=card['slug']):
                self.assertTrue(card.get('emoji'), 'GRM-B04: emoji missing from the card')
                self.assertIn(card['emoji'], body, 'GRM-B04: emoji never rendered')
                self.assertTrue(card.get('description'))
                self.assertTrue(card.get('href'))

    def test_every_link_resolves(self):
        for card in self.client.get(reverse('subject')).context['topics']:
            with self.subTest(topic=card['slug']):
                self.assertEqual(self.client.get(card['href']).status_code, 200)


class GrammarSlideTests(TestCase):
    """FR-GRM-02 — ordered slides with title, explanation, examples, illustration."""

    def setUp(self):
        self.client.force_login(make_user('grm_slides'))

    def test_every_topic_page_loads(self):
        for slug in TOPICS:
            with self.subTest(topic=slug):
                url = reverse('subject_topic', kwargs={'slug': slug})
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_topic_404s(self):
        self.assertEqual(self.client.get('/subject/not-a-topic.html').status_code, 404)

    def test_authored_text_reaches_the_page_not_only_the_image(self):
        """GRM-B02: the lesson used to exist only as pixels inside the SVG."""
        for slug in TOPICS:
            with self.subTest(topic=slug):
                resp = self.client.get(reverse('subject_topic', kwargs={'slug': slug}))
                body = resp.content.decode()
                for slide in sv.SUBJECT_TOPICS[slug]['slides']:
                    self.assertIn(escape(slide['title']), body)
                    for line in slide['lines']:
                        self.assertIn(escape(line), body)

    def test_noun_authored_slides_are_shown(self):
        """GRM-B01: noun renders PNG files, so its authored slides were dropped."""
        resp = self.client.get(reverse('subject_topic', kwargs={'slug': 'noun'}))
        cards = resp.context['topic']['slide_cards']
        self.assertEqual(len(cards), len(sv.SUBJECT_TOPICS['noun']['slides']))
        self.assertIn('Spot the Naming Words', resp.content.decode())

    def test_noun_carousel_still_uses_the_authored_images(self):
        """The PNG deck is the noun lesson's artwork and must not regress."""
        resp = self.client.get(reverse('subject_topic', kwargs={'slug': 'noun'}))
        slides = resp.context['topic']['slides']
        self.assertTrue(all('/subject/slides/noun/' in s['src'] for s in slides))

    def test_slide_cards_pair_text_with_an_illustration(self):
        for slug in TOPICS:
            with self.subTest(topic=slug):
                resp = self.client.get(reverse('subject_topic', kwargs={'slug': slug}))
                for card in resp.context['topic']['slide_cards']:
                    self.assertTrue(card['title'])
                    self.assertTrue(card['lines'])
                    self.assertIn('/subject/illustrations/', card['src'])
                    self.assertNotEqual(card['alt'].strip(), '')

    def test_no_authored_line_is_dropped_from_the_illustration(self):
        """GRM-B03: the SVG used to cap at three lines, silently."""
        for slug in TOPICS:
            topic = sv.SUBJECT_TOPICS[slug]
            for index, slide in enumerate(topic['slides'], start=1):
                svg = sv._build_illustration_svg(topic, slide, index)
                for line in slide['lines']:
                    with self.subTest(topic=slug, slide=index, line=line):
                        # The SVG escapes its interpolated values, so compare
                        # against the escaped form.
                        self.assertIn(escape(line.strip()), svg)


    def test_illustration_text_never_collides_or_overflows(self):
        """The slide heading sits on baseline 256 and the panel ends at 414.

        Bullets used to start at 270, so their capitals ran into the heading on
        every slide of every topic.
        """
        TITLE_BASELINE, PANEL_BOTTOM = 256, 414
        CAP_HEIGHT, DESCENT = 17, 6
        for slug in TOPICS:
            topic = sv.SUBJECT_TOPICS[slug]
            for index, slide in enumerate(topic['slides'], start=1):
                svg = sv._build_illustration_svg(topic, slide, index)
                baselines = [int(y) for y in re.findall(r'<text x="152" y="(\d+)"', svg)]
                with self.subTest(topic=slug, slide=index):
                    self.assertEqual(len(baselines), len(slide['lines']))
                    self.assertGreater(baselines[0] - CAP_HEIGHT, TITLE_BASELINE,
                                       'first bullet overlaps the slide heading')
                    self.assertLess(baselines[-1] + DESCENT, PANEL_BOTTOM,
                                    'last bullet falls outside the content panel')


class GrammarIllustrationTests(TestCase):
    """FR-GRM-03 — SVG per slide, noun images, and their boundaries."""

    def setUp(self):
        self.client.force_login(make_user('grm_svg'))

    def test_every_slide_illustration_serves_svg(self):
        for slug in TOPICS:
            for index in range(1, len(sv.SUBJECT_TOPICS[slug]['slides']) + 1):
                with self.subTest(topic=slug, index=index):
                    url = reverse('subject_illustration', kwargs={'slug': slug, 'index': index})
                    resp = self.client.get(url)
                    self.assertEqual(resp.status_code, 200)
                    self.assertTrue(resp.headers['content-type'].startswith('image/svg+xml'))

    def test_out_of_range_and_unknown_slug_404(self):
        self.assertEqual(self.client.get('/subject/illustrations/verb/99.svg').status_code, 404)
        self.assertEqual(self.client.get('/subject/illustrations/nope/1.svg').status_code, 404)

    def test_noun_images_serve_and_traversal_is_blocked(self):
        resp = self.client.get(reverse('subject_topic', kwargs={'slug': 'noun'}))
        first = resp.context['topic']['slides'][0]['src']
        self.assertEqual(self.client.get(first).status_code, 200)
        self.assertEqual(self.client.get('/subject/slides/noun/missing.png').status_code, 404)
        self.assertIn(self.client.get('/subject/slides/noun/..%2f..%2fmanage.py').status_code,
                      (301, 400, 404))


class GrammarAccessTests(TestCase):
    """FR-GRM-04 — available to every authenticated user, whatever their plan."""

    def test_all_plans_reach_every_grammar_route(self):
        for plan in ('free', 'normal', 'pro'):
            user = make_user(f'grm_{plan}', plan)
            client = self.client_class()
            client.force_login(user)
            with self.subTest(plan=plan):
                self.assertEqual(client.get(reverse('subject')).status_code, 200)
                for slug in TOPICS:
                    url = reverse('subject_topic', kwargs={'slug': slug})
                    self.assertEqual(client.get(url).status_code, 200)

    def test_lapsed_paid_plan_keeps_grammar(self):
        user = make_user('grm_lapsed', 'pro')
        profile = user.profile
        profile.subscription_start = timezone.now() - timedelta(days=400)
        profile.save()
        client = self.client_class()
        client.force_login(user)
        self.assertEqual(client.get(reverse('subject')).status_code, 200)

    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(reverse('subject'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_no_plan_guard_exists_in_the_grammar_views(self):
        """CN-14 puts grammar in the free tier; a plan check must never appear."""
        import inspect
        source = inspect.getsource(sv)
        for marker in ('_get_user_plan', 'plan_type', 'is_pro', 'is_subscription_active'):
            self.assertNotIn(marker, source, f'grammar must stay free of {marker}')

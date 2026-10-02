"""Pre-synthesise Buddy's fixed replies so the first user of the day does not
pay for them.

A large share of replies are fixed strings — the greeting, "Opening the
activities page.", and the rest of ACTION_DEFINITIONS in riya_assistant.py.
generate_riya_tts_audio already caches on (text, language, speaker, emotion),
but the cache starts EMPTY: the first person to hit each reply waits ~1s
locally (2-4s against a busier network) before Buddy makes a sound, and the
cache is lost on every restart.

Run this after a deploy, or on a schedule:

    python manage.py warm_tts_cache
    python manage.py warm_tts_cache --language hindi
    python manage.py warm_tts_cache --language vietnamese   # Google voice
"""
import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from riya_bot.agents.utils import (DEFAULT_TTS_SPEAKER, GOOGLE_TTS_LANGS,
                                   stream_google_tts_audio, stream_riya_tts_audio)


def _canned_replies():
    """Every fixed reply string Buddy can speak, as it is actually SPOKEN.

    A navigation reply is spoken as one utterance: the confirmation plus the
    "inside you'll find..." follow-up that _guided_navigation_reply() appends.
    Warming only the bare confirmation left the full sentence uncached, so it
    was synthesised fresh on every navigation.
    """
    from riya_bot import riya_assistant as ra

    replies = set()
    for name in dir(ra):
        value = getattr(ra, name)
        if isinstance(value, dict):
            for key, entry in value.items():
                if not (isinstance(entry, dict) and isinstance(entry.get('response'), str)):
                    continue
                text = entry['response'].strip()
                if not text:
                    continue
                replies.add(text)
                # ...and the guided variant, for both audiences.
                for is_employer in (False, True):
                    try:
                        guided = ra._guided_navigation_reply(key, text, is_employer)
                    except Exception:
                        continue
                    if guided and guided.strip() != text:
                        replies.add(guided.strip())
    return sorted(replies)


def _localized_canned_replies(language):
    """The same fixed lines as spoken in a non-English session."""
    from riya_bot import riya_assistant as ra

    replies = set()
    for key in ra.ACTION_DEFINITIONS:
        replies.add(ra.localized_action_response(key, language))
        for is_employer in (False, True):
            replies.add(ra._navigation_reply(key, "what is it", language, is_employer))
    return sorted(r.strip() for r in replies if r and r.strip())


async def _collect(chunks):
    return b"".join([chunk async for chunk in chunks])


class Command(BaseCommand):
    help = "Pre-generate TTS audio for Buddy's fixed replies so they play instantly."

    def add_arguments(self, parser):
        parser.add_argument('--language', default='english',
                            help='Language key from SUPPORTED_LANGUAGES (default: english).')
        parser.add_argument('--speaker', default=DEFAULT_TTS_SPEAKER,
                            help=f'Sarvam speaker id (default: {DEFAULT_TTS_SPEAKER}).')

    def handle(self, *args, **options):
        from riya_bot.views import SUPPORTED_LANGUAGES, normalize_language

        language = normalize_language(options['language'])
        lang_code = SUPPORTED_LANGUAGES.get(language, {'code': 'en-IN'})['code']
        speaker = options['speaker']

        # Vietnamese / Arabic / Russian are voiced by Google, not Sarvam.
        if lang_code in GOOGLE_TTS_LANGS:
            replies = _localized_canned_replies(language)
            warmed = 0
            for text in replies:
                if asyncio.run(_collect(stream_google_tts_audio(text, lang_code, 'neutral'))):
                    warmed += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  failed: {ascii(text[:60])}'))
            self.stdout.write(self.style.SUCCESS(
                f'Warmed {warmed}/{len(replies)} replies ({language}/google).'))
            return

        api_key = getattr(settings, 'SARVAM_API_KEY', '')
        if not api_key:
            raise CommandError('SARVAM_API_KEY is not set — nothing to warm.')

        replies = _canned_replies()
        if not replies:
            self.stdout.write(self.style.WARNING('No fixed replies found.'))
            return

        warmed = failed = 0
        for text in replies:
            # Warm the STREAM cache, which is what playback reads. Warming the
            # batch cache instead left the fixed lines as WAV while every other
            # sentence streamed as MP3, and the voice changed between them.
            # Neutral only: a fixed navigation line is never read as happy or
            # sad, so the other two emotions would just burn API calls.
            audio = b''.join(stream_riya_tts_audio(text, api_key, lang_code, speaker, 'neutral'))
            if audio:
                warmed += 1
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(f'  failed: {ascii(text[:60])}'))

        self.stdout.write(self.style.SUCCESS(
            f'Warmed {warmed}/{len(replies)} replies ({language}/{speaker}); {failed} failed.'))

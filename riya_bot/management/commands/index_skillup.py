"""Rebuild and inspect the Skill Up catalog.

    python manage.py index_skillup            # rebuild + summary
    python manage.py index_skillup --verify    # also check every route resolves
    python manage.py index_skillup --json      # machine-readable manifest
"""

import json

from django.core.management.base import BaseCommand

from riya_bot.skillup_catalog import get_manifest, invalidate, skillup_root
from riya_bot.skillup_service import SkillUpKnowledgeService


class Command(BaseCommand):
    help = "Rebuild the Skill Up catalog from the actual Skill Up source files."

    def _write(self, text, style=None):
        """Write a line that cannot crash on a narrow console encoding.

        Skill Up titles legitimately contain characters such as "·" and "→".
        On Windows the console is cp1252 by default, where those are
        unencodable, and the command died with UnicodeEncodeError partway
        through the summary. Degrade the character, never the command.
        """
        encoding = getattr(self.stdout, "encoding", None) or "utf-8"
        try:
            text.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            text = text.encode(encoding, errors="replace").decode(encoding, "replace")
        self.stdout.write(style(text) if style else text)

    def add_arguments(self, parser):
        parser.add_argument("--verify", action="store_true",
                            help="Check every lesson's source file exists and is readable.")
        parser.add_argument("--json", action="store_true",
                            help="Emit the manifest as JSON instead of a summary.")

    def handle(self, *args, **options):
        root = skillup_root()
        if not root:
            self.stderr.write(self.style.ERROR(
                "Skill Up directory not found. Expected '001 Career Buddy/index.html' "
                "under a configured static location."))
            return

        invalidate()
        manifest = get_manifest(force=True)
        service = SkillUpKnowledgeService(manifest)

        if options["json"]:
            payload = {
                "counts": {
                    "sections": service.count_sections(),
                    "subsections": service.count_subsections(),
                    "lessons": service.count_lessons(),
                },
                "sections": [
                    {
                        "id": s.section_id,
                        "title": s.title,
                        "route": s.route,
                        "subsections": [
                            {"title": sub.title,
                             "lessons": [{"title": l.title,
                                          "source_file": l.source_file,
                                          "route": l.route,
                                          "aliases": l.aliases}
                                         for l in sub.lessons]}
                            for sub in s.subsections
                        ],
                    }
                    for s in service.get_sections()
                ],
            }
            self.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False))
            return

        self._write(f"Indexed Skill Up from {root}", self.style.SUCCESS)
        self._write(
            f"  {service.count_sections()} sections, "
            f"{service.count_subsections()} subsections, "
            f"{service.count_lessons()} lessons"
        )
        for section in service.get_sections():
            self._write(
                f"\n  {section.title} [{section.section_id}] "
                f"- {section.subsection_count} subsections, {section.lesson_count} lessons"
            )
            for sub in section.subsections:
                self._write(f"      {sub.title} ({sub.lesson_count})")

        if options["verify"]:
            self._write("\nVerifying lesson sources...")
            missing = []
            for lesson in service.get_lessons():
                if not service.get_page_content(lesson, max_chars=200):
                    missing.append(lesson)
            if missing:
                for lesson in missing:
                    self.stderr.write(self.style.WARNING(
                        f"  unreadable: {lesson.title} -> {lesson.source_file}"))
                self.stderr.write(self.style.ERROR(
                    f"{len(missing)} of {service.count_lessons()} lessons unreadable."))
            else:
                self._write(
                    f"  all {service.count_lessons()} lesson sources readable.",
                    self.style.SUCCESS)

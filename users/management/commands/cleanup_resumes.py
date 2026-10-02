"""
Cleans up the media/resumes/ folder so each candidate keeps only ONE resume:

  1. Removes old SAMPLE PDFs (Resume_0*, Sample_*) from the deprecated file-based search.
  2. De-duplicates resume-builder uploads — keeps the LATEST per user, deletes older
     records + files (the repeated "Name_xxxxxx.pdf" copies).
  3. Deletes ORPHANED files not referenced by any candidate (UserProfile.resume),
     resume-builder record (core.Resume) or job application (JobApplication.resume).

Usage:
    python manage.py cleanup_resumes --dry-run   # preview only
    python manage.py cleanup_resumes             # actually delete
"""

import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max

from users.models import UserProfile

SAMPLE_PATTERN = re.compile(r'^(resume_\d|sample_)', re.IGNORECASE)


class Command(BaseCommand):
    help = "Remove sample, duplicate and orphaned resume files from media/resumes/."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be deleted without deleting.')
        parser.add_argument('--registered-only', action='store_true',
                            help='Keep ONLY registered student candidates\' resumes; delete everything else.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        prefix = '[DRY RUN] ' if dry else ''
        resumes_dir = os.path.join(str(settings.MEDIA_ROOT), 'resumes')
        if not os.path.isdir(resumes_dir):
            self.stdout.write('No media/resumes/ directory found.')
            return

        if options['registered_only']:
            return self._registered_only(resumes_dir, dry, prefix)

        removed = 0

        # 1. De-duplicate resume-builder uploads (core.Resume): keep latest per user
        try:
            from core.models import Resume as ResumeModel
            latest_ids = set(
                ResumeModel.objects.values('user')
                .annotate(mx=Max('id')).values_list('mx', flat=True)
            )
            for r in ResumeModel.objects.exclude(id__in=latest_ids):
                if r.file:
                    self.stdout.write(f'  del (builder-duplicate): {os.path.basename(r.file.name)}')
                    if not dry:
                        try:
                            r.file.delete(save=False)
                        except Exception:
                            pass
                    removed += 1
                if not dry:
                    r.delete()
        except Exception as e:
            self.stderr.write(f'  (resume-builder dedup skipped: {e})')

        # 2. Collect every file still referenced by a candidate/record
        referenced = set()

        def _add(field_file):
            if field_file:
                try:
                    referenced.add(os.path.basename(field_file.name))
                except Exception:
                    pass

        for p in UserProfile.objects.exclude(resume='').exclude(resume__isnull=True):
            _add(p.resume)
        try:
            from core.models import Resume as ResumeModel
            for r in ResumeModel.objects.exclude(file='').exclude(file__isnull=True):
                _add(r.file)
        except Exception:
            pass
        try:
            from jobs_app.models import JobApplication
            for ja in JobApplication.objects.exclude(resume='').exclude(resume__isnull=True):
                _add(ja.resume)
        except Exception:
            pass

        # 3. Delete sample files + orphans on disk
        for fname in os.listdir(resumes_dir):
            fpath = os.path.join(resumes_dir, fname)
            if not os.path.isfile(fpath):
                continue
            is_sample = bool(SAMPLE_PATTERN.match(fname))
            is_orphan = fname not in referenced
            if is_sample or is_orphan:
                reason = 'sample' if is_sample else 'orphan'
                self.stdout.write(f'  del ({reason}): {fname}')
                if not dry:
                    try:
                        os.remove(fpath)
                    except Exception as e:
                        self.stderr.write(f'    failed: {e}')
                        continue
                removed += 1

        self.stdout.write(self.style.SUCCESS(f"{prefix}Removed {removed} file(s)."))

    def _registered_only(self, resumes_dir, dry, prefix):
        """Keep ONLY resumes that belong to a REGISTERED STUDENT candidate;
        delete every other file in media/resumes/."""
        # Build the keep-set: resume files of genuine student-portal candidates
        keep = set()
        regd = (
            UserProfile.objects.filter(user__is_active=True, role='student')
            .filter(user__employer_profile__isnull=True)
            .exclude(user__is_staff=True)
            .exclude(user__is_superuser=True)
            .exclude(resume='')
            .exclude(resume__isnull=True)
            .select_related('user')
        )
        for p in regd:
            if p.resume:
                keep.add(os.path.basename(p.resume.name))

        self.stdout.write(f"Registered candidate resumes to KEEP: {len(keep)}")

        removed = 0
        for fname in os.listdir(resumes_dir):
            fpath = os.path.join(resumes_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if fname in keep:
                continue
            self.stdout.write(f'  del (not a registered candidate): {fname}')
            if not dry:
                try:
                    os.remove(fpath)
                except Exception as e:
                    self.stderr.write(f'    failed: {e}')
                    continue
            removed += 1

        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Kept {len(keep)} registered resume(s), removed {removed} other file(s)."
        ))

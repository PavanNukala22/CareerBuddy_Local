"""Copies interview recordings that were saved to media/interview_videos/ on
local disk (before MinIO) into the configured 'interview_videos' storage.

Stored FileField names are identical on both backends, so no DB rows change;
only the bytes move. Local copies are left in place unless --delete-local.
"""
import os

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, storages
from django.core.management.base import BaseCommand, CommandError

from career_app.models import ResumeInterviewSession


class Command(BaseCommand):
    help = "Upload existing on-disk interview recordings to the MinIO bucket."

    def add_arguments(self, parser):
        parser.add_argument('--delete-local', action='store_true',
                            help='Remove the local file after a successful upload.')

    def handle(self, *args, **options):
        storage = storages['interview_videos']
        if isinstance(storage, FileSystemStorage):
            raise CommandError('MINIO_ENDPOINT_URL is not set — the interview_videos storage is still local disk.')

        sessions = ResumeInterviewSession.objects.exclude(interview_video='').exclude(interview_video__isnull=True)
        uploaded = skipped = missing = 0
        for session in sessions:
            name = session.interview_video.name
            local_path = os.path.join(settings.MEDIA_ROOT, name)
            if storage.exists(name):
                skipped += 1
            elif not os.path.isfile(local_path):
                missing += 1
                self.stderr.write(f'session {session.id}: {name} not found locally or in bucket')
                continue
            else:
                with open(local_path, 'rb') as fh:
                    saved_as = storage.save(name, File(fh))
                if saved_as != name:
                    raise CommandError(f'session {session.id}: bucket renamed {name} to {saved_as}; aborting')
                uploaded += 1
                self.stdout.write(f'session {session.id}: uploaded {name}')
            if options['delete_local'] and os.path.isfile(local_path):
                os.remove(local_path)

        self.stdout.write(self.style.SUCCESS(
            f'done — uploaded {uploaded}, already in bucket {skipped}, missing {missing}'
        ))

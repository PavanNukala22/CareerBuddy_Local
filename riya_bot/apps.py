import threading

from django.apps import AppConfig


class RiyaBotConfig(AppConfig):
    name = 'riya_bot'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Build the Skill Up catalog in the background at start-up (~1s), so the
        # first chatbot message after a restart is not the one that waits for it.
        def warm():
            try:
                from .skillup_catalog import get_manifest
                get_manifest()
            except Exception:
                pass
        threading.Thread(target=warm, daemon=True).start()

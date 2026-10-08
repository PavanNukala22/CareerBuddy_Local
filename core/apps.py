from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core Utilities'

    def ready(self):
        from django.template.context import BaseContext
        
        def _patched_copy(self):
            duplicate = type(self).__new__(type(self))
            duplicate.__dict__.update(self.__dict__)
            duplicate.dicts = self.dicts[:]
            return duplicate
            
        BaseContext.__copy__ = _patched_copy

        # Dev only: runserver (daphne) serves /static/ in a handler that runs
        # BEFORE any middleware, which would let a Free user open a locked Skill
        # Up lesson by URL. Hand those lesson pages to the normal request path
        # instead, where SkillUpAccessMiddleware checks the plan and WhiteNoise
        # (which serves from the finders while DEBUG) returns the file.
        from django.conf import settings
        if settings.DEBUG:
            from django.contrib.staticfiles.handlers import StaticFilesHandlerMixin
            from .skillup_access import SKILLUP_PREFIX

            original = StaticFilesHandlerMixin._should_handle

            def _should_handle(handler, path):
                from urllib.parse import unquote
                if unquote(path).startswith(SKILLUP_PREFIX) and unquote(path).lower().endswith(('.html', '.htm')):
                    return False
                return original(handler, path)

            StaticFilesHandlerMixin._should_handle = _should_handle

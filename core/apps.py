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

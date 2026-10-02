from django.apps import AppConfig


class JamConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jam_app'
    verbose_name = 'JAM English'

    def ready(self):
        try:
            from django.contrib.auth.models import User
            from django.db.models.signals import post_save
            from jam_app.models import UserProfile

            def create_profile(sender, instance, created, **kwargs):
                if created:
                    UserProfile.objects.get_or_create(user=instance)

            post_save.connect(create_profile, sender=User)
        except ImportError:
            pass

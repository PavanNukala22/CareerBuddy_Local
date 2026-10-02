"""Authentication backend that accepts either a username or an email address.

Django's default ModelBackend authenticates by username only. This lets a user
sign in with whichever they remember. It is added ahead of the default backend
in AUTHENTICATION_BACKENDS, so username logins keep working unchanged and email
logins are resolved here first.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        identifier = username.strip()
        try:
            user = User.objects.get(Q(username__iexact=identifier) | Q(email__iexact=identifier))
        except User.DoesNotExist:
            # Run the default hasher once so a missing user takes about as long as
            # a real one — this is what ModelBackend does to blunt timing-based
            # account enumeration.
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Ambiguous: e.g. one row's username equals another row's email, or
            # two accounts share an email. Prefer an exact username match, then
            # the most recently created account for the email.
            user = (
                User.objects.filter(username__iexact=identifier).first()
                or User.objects.filter(email__iexact=identifier).order_by('-id').first()
            )
            if user is None:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

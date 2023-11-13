from django.conf import settings
from guardian.utils import get_anonymous_user


# convenience function returns True if user is anonymous
def is_anonymous_user(user):
    anonymous_username = getattr(settings, 'ANONYMOUS_USER_NAME', None)
    return user.is_anonymous or user.username == anonymous_username


# convenience function returns True if user is authenticated
def is_authenticated_user(user):
    anonymous_username = getattr(settings, 'ANONYMOUS_USER_NAME', None)
    return user.is_authenticated and user.username != anonymous_username

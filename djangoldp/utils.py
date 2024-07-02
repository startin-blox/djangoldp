from django.conf import settings
from guardian.utils import get_anonymous_user

PASSTHROUGH_IPS = getattr(settings, 'PASSTHROUGH_IPS', '')

# convenience function returns True if user is anonymous
def is_anonymous_user(user):
    anonymous_username = getattr(settings, 'ANONYMOUS_USER_NAME', None)
    return user.is_anonymous or user.username == anonymous_username


# convenience function returns True if user is authenticated
def is_authenticated_user(user):
    anonymous_username = getattr(settings, 'ANONYMOUS_USER_NAME', None)
    return user.is_authenticated and user.username != anonymous_username


# this method is used to check if a given IP is part of the PASSTHROUGH_IPS list
def check_client_ip(request):
    x_forwarded_for = request.headers.get('x-forwarded-for')
    if x_forwarded_for:
        if any(ip in x_forwarded_for.replace(' ', '').split(',') for ip in PASSTHROUGH_IPS):
            return True
    elif request.META.get('REMOTE_ADDR') in PASSTHROUGH_IPS:
        return True
    return False

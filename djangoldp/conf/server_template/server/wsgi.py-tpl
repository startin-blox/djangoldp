"""
WSGI config for SIB project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.conf import settings as django_settings
from djangoldp.conf import ldpsettings

if not django_settings.configured:
    ldpsettings.configure()

application = get_wsgi_application()

try:
    from djangoldp.activities.services import ActivityQueueService

    ActivityQueueService.start()
except:
    pass

import django
import sys
from django.conf import settings

settings.configure(DEBUG=True,
                   DATABASES={
                       'default': {
                           'ENGINE': 'django.db.backends.sqlite3',
                       }
                   },
                   LDP_RDF_CONTEXT = 'https://cdn.happy-dev.fr/owl/hdcontext.jsonld',
                   ROOT_URLCONF='djangoldp.tests.urls',
                   DJANGOLDP_PACKAGES=['djangoldp.tests'],
                   INSTALLED_APPS=('django.contrib.auth',
                                   'django.contrib.contenttypes',
                                   'django.contrib.sessions',
                                   'django.contrib.admin',
                                   'guardian',
                                   'djangoldp',
                                   'djangoldp.tests',
                                   ))


django.setup()
from django.test.runner import DiscoverRunner

test_runner = DiscoverRunner(verbosity=1)

failures = test_runner.run_tests([
    'djangoldp.tests.tests_ldp_model',
    'djangoldp.tests.tests_save',
    'djangoldp.tests.tests_user_permissions',
    'djangoldp.tests.tests_anonymous_permissions',
    'djangoldp.tests.tests_update',
    'djangoldp.tests.tests_auto_author',
])
if failures:
    sys.exit(failures)


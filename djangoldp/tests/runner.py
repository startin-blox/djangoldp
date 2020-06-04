import sys

import django
from djangoldp.tests import settings_default
from django.conf import settings

settings.configure(default_settings=settings_default)

django.setup()
from django.test.runner import DiscoverRunner

test_runner = DiscoverRunner(verbosity=1)

failures = test_runner.run_tests([
    'djangoldp.tests.tests_ldp_model',
    'djangoldp.tests.tests_save',
    'djangoldp.tests.tests_user_permissions',
    'djangoldp.tests.tests_guardian',
    'djangoldp.tests.tests_anonymous_permissions',
    'djangoldp.tests.tests_update',
    'djangoldp.tests.tests_auto_author',
    'djangoldp.tests.tests_get',
    'djangoldp.tests.tests_delete',
    'djangoldp.tests.tests_sources',
    'djangoldp.tests.tests_pagination',
    'djangoldp.tests.tests_inbox',
    #'djangoldp.tests.tests_temp'
])
if failures:
    sys.exit(failures)

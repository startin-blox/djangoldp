import sys

import django
from djangoldp.tests import settings_default
from django.conf import settings

# configure settings not to use pagination
settings.configure(default_settings=settings_default,
                   REST_FRAMEWORK = {
                       'DEFAULT_PAGINATION_CLASS': None
                   })

django.setup()
from django.test.runner import DiscoverRunner

test_runner = DiscoverRunner(verbosity=1)

failures = test_runner.run_tests([
    # 'djangoldp.tests.tests_performance',
    'djangoldp.tests.tests_perf_get'
])
if failures:
    sys.exit(failures)

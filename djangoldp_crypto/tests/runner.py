import sys

import django
import yaml
from django.conf import settings as django_settings
from djangoldp.conf.ldpsettings import LDPSettings
from djangoldp_crypto.tests.settings_default import yaml_config

# load test config
config = yaml.safe_load(yaml_config)
ldpsettings = LDPSettings(config)
django_settings.configure(ldpsettings)

django.setup()
from django.test.runner import DiscoverRunner

test_runner = DiscoverRunner(verbosity=1)

failures = test_runner.run_tests([
    'djangoldp_crypto.tests.tests_rsakey',
])
if failures:
    sys.exit(failures)

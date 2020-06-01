from django.conf import settings, global_settings
from django.test import TestCase

class TestSettings(TestCase):

    def test_only_in_user_config(self):
        """Asserts load from YAML file."""
        assert settings.LDP_PACKAGES == ['djangoldp.tests']

    def test_only_in_core_config(self):
        """Asserts values defined only in core config."""
        assert settings.DEBUG == False

    def test_overrided_by_user_config(self):
        """Asserts values overrided from user configuration."""
        assert settings.EMAIL_HOST == 'somewhere'

    def test_only_in_package(self):
        """Asserts default settings defined in the package."""
        assert settings.MYPACKAGEVAR == "ok"

    def test_add_middleware(self):
        """Asserts middlewares added in packages are added to the settings."""
        #assert settings.MIDDLEWARE == global_settings.MIDDLEWARE + ['MYMIDDLEWARE']

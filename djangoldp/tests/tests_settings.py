from django.conf import settings
from django.test import TestCase

class TestSettings(TestCase):

    def test_inexistent_returns_default(self):
        """Assert a inexistent key returns the provided default value."""
        assert getattr(settings, 'INEXISTENT', 'something') == 'something'

    def test_only_in_core_config(self):
        """Asserts values defined only in core config."""
        assert settings.DEBUG == False

    def test_only_in_package(self):
        """Asserts default settings defined in the package."""
        assert settings.MYPACKAGEVAR == "ok"

    def test_only_in_user_config(self):
        """Asserts LDP packages are loaded from YAML file."""
        assert settings.DJANGOLDP_PACKAGES == ['djangoldp.tests']

    def test_overrided_core_by_package_config(self):
        assert settings.USE_I18N == False

    def test_overrided_package_by_user_config(self):
        assert settings.USE_TZ == False

    def test_overrided_core_by_user_config(self):
        """Asserts values overrided from user configuration."""
        assert settings.EMAIL_HOST == 'somewhere'

    def test_installed_apps_resolution(self):
        """Asserts LDP packages are referenced along with default installed apps."""
        assert settings.INSTALLED_APPS == [
            'djangoldp.tests',
            'djangoldp.tests.dummy.apps.DummyConfig',
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'djangoldp',
            'guardian',
        ]

    def test_reference_middleware(self):
        """Asserts middlewares added in packages are added to the settings."""
        assert 'djangoldp.tests.dummy.middleware.DummyMiddleware' in settings.MIDDLEWARE

    def test_extra_module(self):
        #FIXME
        pass

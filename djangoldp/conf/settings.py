import os
import sys
import yaml
import logging
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings as django_settings
from . import global_settings

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module


logger = logging.getLogger(__name__)


def configure():

    # ref: https://docs.djangoproject.com/fr/2.2/topics/settings/#custom-default-settings
    settings = LDPSettings('config.yml')
    django_settings.configure(settings)     # gives a LazySettings


class LDPSettings(object):

    def __init__(self, path):

        if django_settings.configured:
            raise ImproperlyConfigured('Settings have been configured already')

        self.path = path
        self._config = None

    @property
    def config(self):

        """Load configuration from file."""

        if not self._config:
            with open(self.path, 'r') as f:
                self._config = yaml.safe_load(f)

        return self._config

    @property
    def LDP_PACKAGES(self):

        """Returns the list of LDP packages configured."""

        pkg = self.config.get('ldppackages', [])
        return [] if pkg is None else pkg

    @property
    def INSTALLED_APPS(self):

        """Returns the default installed apps and the LDP packages."""

        # get default apps
        apps = getattr(global_settings, 'INSTALLED_APPS')

        # add packages
        apps.extend(self.LDP_PACKAGES)
        return apps

    @property
    def MIDDLEWARE(self):

        """Returns the default middlewares and the middlewares found in each LDP packages."""

        # get default middlewares
        middleware = getattr(global_settings, 'MIDDLEWARE')

        # explore packages looking for middleware to reference
        for pkg in self.LDP_PACKAGES:
            try:
                # import from installed package
                mod = import_module(f'{pkg}.default_settings')
                middleware.extend(getattr(mod, 'MIDDLEWARE'))
                logger.debug(f'Middleware found in installed package {pkg}')
            except (ModuleNotFoundError, NameError):
                try:
                    # import from local package
                    mod = import_module(f'{pkg}.{pkg}.default_settings')
                    middleware.extend(getattr(mod, 'MIDDLEWARE'))
                    logger.debug(f'Middleware found in local package {pkg}')
                except (ModuleNotFoundError, NameError):
                    logger.info(f'No middleware found for package {pkg}')
                    pass

        return middleware

    def __getattr__(self, name):

        """Look for the value in config and fallback on defaults."""

        try:
            if not name.startswith('_') and name.isupper():
                return self.config['server'][name]
        except KeyError:
            try:
                return getattr(global_settings, name)
            except AttributeError:
                raise ImproperlyConfigured(f'no "{name}" parameter found in settings')


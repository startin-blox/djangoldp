import os
import sys
import yaml
from django.conf import settings as django_settings
from . import global_settings

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module


def configure():

    # ref: https://docs.djangoproject.com/fr/2.2/topics/settings/#custom-default-settings
    settings = LDPSettings('config.yml')
    django_settings.configure(settings)


class LDPSettings(object):

    def __init__(self, path, *args, **kwargs):

        self.path = path
        self._config = None

    @property
    def config(self):

        """Load configuration from file."""

        if not self._config:
            with open(self.path, 'r') as f:
                self._config = yaml.safe_load(f)

        return self._config

    def __getattr__(self, name):

        """Look for the value in config and fallback on django defaults."""

        try:
            if not name.startswith('_') and name.isupper():
                return self.config['server'][name]
        except KeyError:
            try:
                return getattr(global_settings, name)
            except AttributeError:
                # logger.info(f'The settings {name} is not accessible')
                raise

    @property
    def LDP_PACKAGES(self):
        pkg = self.config.get('ldppackages', [])
        return [] if pkg is None else pkg

    @property
    def INSTALLED_APPS(self):

        # get default apps
        apps = getattr(global_settings, 'INSTALLED_APPS')

        # add packages
        apps.extend(self.LDP_PACKAGES)
        return apps

    @property
    def MIDDLEWARE(self):

        # get default middlewares
        middleware = getattr(global_settings, 'MIDDLEWARE')

        # explore packages looking for middleware to reference
        for pkg in self.LDP_PACKAGES:
            try:
                # import from installed package
                mod = import_module(f'{pkg}.default_settings')
                middleware.extend(getattr(mod, 'MIDDLEWARE'))
            except (ModuleNotFoundError, NameError):
                try:
                    # import from local package
                    mod = import_module(f'{pkg}.{pkg}.default_settings')
                    middleware.extend(getattr(mod, 'MIDDLEWARE'))
                except (ModuleNotFoundError, NameError):
                    print('nothing')
                    # logger.debug()
                    pass

        return middleware

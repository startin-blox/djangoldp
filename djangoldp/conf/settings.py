import os
import sys
import yaml
import logging
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings as django_settings
from pathlib import Path
from typing import Iterable
from . import global_settings

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module


logger = logging.getLogger(__name__)


def configure(filename='settings.yml'):
    """Helper function to configure django from LDPSettings."""

    # ref: https://docs.djangoproject.com/fr/2.2/topics/settings/#custom-default-settings
    ldpsettings = LDPSettings(path=filename)

    django_settings.configure(ldpsettings)


class LDPSettings(object):

    """Class managing the DjangoLDP configuration."""

    def __init__(self, path):

        if django_settings.configured:
            raise ImproperlyConfigured('Settings have been configured already')

        self.path = path
        self._config = None
        self._settings = self.build_settings()

    @property
    def config(self):

        """Load configuration from file."""

        if not self._config:
            with open(self.path, 'r') as f:
                self._config = yaml.safe_load(f)

        return self._config

    @config.setter
    def config(self, value):
        """Set a dict has current configuration."""
        self._config = value

    def fetch(self, attributes):
        """
        Explore packages looking for a list of attributes within the server configuration.
        It returns all elements found and doesn't manage duplications or collisions.
        """

        attr = []
        for pkg in self.DJANGOLDP_PACKAGES:
            try:
                # import from an installed package
                mod = import_module(f'{pkg}.djangoldp_settings')
                logger.debug(f'Settings found for {pkg} in a installed package')
            except ModuleNotFoundError:
                try:
                    # import from a local packages in a subfolder (same name the template is built this way)
                    mod = import_module(f'{pkg}.{pkg}.djangoldp_settings')
                    logger.debug(f'Settings found for {pkg} in a local package')
                except ModuleNotFoundError:
                    logger.debug(f'No settings found for {pkg}')
                    break

            # looking for the attribute list in the module
            try:
                attr.extend(getattr(mod, attributes))
                logger.debug(f'{attributes} found in local package {pkg}')
            except NameError:
                logger.info(f'No {attributes} found for package {pkg}')
                pass

        return attr

    def build_settings(self):
        """
        Look for the parameter in config. Each step override the value of the previous key found.

        Resolution order of the configuration:
          1. Core default settings
          2. Packages settings
          3. Code from a local settings.py file
          4. YAML config file
        """

        # start from default core settings
        settings = global_settings.__dict__
        logger.debug(f'building settings from core defaults')

        # look settings from packages in the order they are given (local override installed)
        for pkg in self.DJANGOLDP_PACKAGES:

            try:
                # override with values from installed package
                mod = import_module(f'{pkg}.djangoldp_settings')
                settings.update({k: v for k, v in mod.__dict__.items() if not k.startswith('_')})
                logger.debug(f'updating settings from installed package {pkg}')
            except ModuleNotFoundError:
                pass

            try:
                # override with values from local package
                mod = import_module(f'{pkg}.{pkg}.djangoldp_settings')
                settings.update({k: v for k, v in mod.__dict__.items() if not k.startswith('_')})
                logger.debug(f'updating settings from local package {pkg}')
            except ModuleNotFoundError:
                pass

        # look in settings.py file in directory
        try:
            mod = import_module('settings')
            settings.update({k: v for k, v in mod.__dict__.items() if not k.startswith('_')})
            logger.debug(f'updating settings from local settings.py file')
        except ModuleNotFoundError:
            pass

        # look in YAML config file 'server' section
        try:
            conf = self.config.get('server', {})
            settings.update({k: v for k, v in conf.items() if not k.startswith('_')})
            logger.debug(f'updating settings with project config')
        except KeyError:
            pass

        return settings

    @property
    def DJANGOLDP_PACKAGES(self):

        """Returns the list of LDP packages configured."""

        pkg = self.config.get('ldppackages', [])
        return [] if pkg is None else pkg

    @property
    def INSTALLED_APPS(self):

        """Return the default installed apps and the LDP packages."""

        # get default apps
        apps = getattr(global_settings, 'INSTALLED_APPS')

        # add ldp packages themselves (they are django apps)
        apps.extend(self.DJANGOLDP_PACKAGES)

        # add apps referenced in packages
        apps.extend(self.fetch('INSTALLED_APPS'))

        return apps

    @property
    def MIDDLEWARE(self):

        """
        Return the default middlewares and the middlewares found in each LDP packages.
        """

        # get default middlewares
        middlewares = getattr(global_settings, 'MIDDLEWARE')

        # explore packages looking for middleware to reference
        middlewares.extend(self.fetch('MIDDLEWARE'))

        return middlewares

    def __getattr__(self, param):
        """Return the requested parameter from cached settings."""
        try:
            return self._settings[param]
        except KeyError:
            # raise the django exception for inexistent parameter
            raise AttributeError(f'no "{param}" parameter found in settings')


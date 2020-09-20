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
    settings = LDPSettings(path=filename)
    django_settings.configure(settings)     # gives a LazySettings


class LDPSettings(object):

    """Class managing the DjangoLDP configuration."""

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
            except (ModuleNotFoundError):
                try:
                    # import from a local packages in a subfolder (same name the template is built this way)
                    mod = import_module(f'{pkg}.{pkg}.djangoldp_settings')
                    logger.debug(f'Settings found for {pkg} in a local package')
                except (ModuleNotFoundError):
                    logger.debug(f'No settings found for {pkg}')
                    break

            # looking for the attribute list in the module
            try:
                attr.extend(getattr(mod, attributes))
                logger.debug(f'{attributes} found in local package {pkg}')
            except (NameError):
                logger.info(f'No {attributes} found for package {pkg}')
                pass

        return attr

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

        """
        Look for the parameter in config and return the first value found.

        Resolution order of the configuration:
          1. YAML config file
          2. Packages settings
          3. Core default settings
        """

        if not param.startswith('_') and param.isupper():

            # look in config file
            try:
                value = self.config['server'][param]
                logger.debug(f'{param} found in project config')
                return value
            except KeyError:
                pass

            # look in all packages config
            for pkg in self.DJANGOLDP_PACKAGES:

                try:
                    # import from local package
                    mod = import_module(f'{pkg}.{pkg}.djangoldp_settings')
                    value = getattr(mod, param)
                    logger.debug(f'{param} found in local package {pkg}')
                    return value
                except (ModuleNotFoundError, NameError, AttributeError):
                    pass

                try:
                    # import from installed package
                    mod = import_module(f'{pkg}.djangoldp_settings')
                    value = getattr(mod, param)
                    logger.debug(f'{param} found in installed package {pkg}')
                    return value
                except (ModuleNotFoundError, NameError, AttributeError):
                    pass

            # look in default settings
            try:
                value = getattr(global_settings, param)
                logger.debug(f'{param} found in core default config')
                return value
            except AttributeError:
                pass

            # raise the django exception for inexistent parameter
            raise AttributeError(f'no "{param}" parameter found in settings')

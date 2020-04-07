import os
import sys
import yaml
from django import conf
from django.conf import LazySettings
from . import global_settings

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module

# Reference: https://github.com/django/django/blob/master/django/conf/__init__.py


def configure():

    # catch djangoldp specific settings
    settings_module = os.getenv('DJANGOLDP_SETTINGS')
    if not settings_module:
        raise ImportError('Settings could not be imported because DJANGOLDP_SETTINGS is not set')

    # patch django.conf.settings
    # ref: https://github.com/rochacbruno/dynaconf/blob/master/dynaconf/contrib/django_dynaconf_v2.py
    # ref: https://docs.djangoproject.com/fr/2.2/topics/settings/#custom-default-settings
    settings = LDPSettings('config.yml')

    lazy = LazySettings()
    lazy.configure(settings)

    class Wrapper(object):

        def __getattribute__(self, name):
            if name == "settings":
                return lazy
            else:
                return getattr(conf, name)

    sys.modules["django.conf"] = Wrapper()

    # setup vars to resume django setup process
    os.environ['DJANGO_SETTINGS_MODULE'] = settings_module



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
        return self.config.get('ldppackages', [])

    @property
    def INSTALLED_APPS(self):

        # set default apps
        apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'djangoldp',
            'guardian'
        ]

        # add packages
        apps.extend(self.LDP_PACKAGES)
        return apps

    @property
    def MIDDLEWARE(self):

        # set default middlewares
        middlewares = [
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware'
        ]

        # explore packages looking for middleware to reference
        for pkg in self.LDP_PACKAGES:
            try:
                # import installed package
                mod = import_module(f'{pkg}.default_settings')
                middlewares.extend(getattr(mod, 'MIDDLEWARE'))
            except (ModuleNotFoundError, NameError):
                try:
                    # import local package
                    mod = import_module(f'{pkg}.{pkg}.default_settings')
                    middlewares.extend(getattr(mod, 'MIDDLEWARE'))
                except (ModuleNotFoundError, NameError):
                    print('nothing')
                    # logger.debug()
                    pass

        return middlewares

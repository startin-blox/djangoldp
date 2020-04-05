import yaml
import os
from django.conf import global_settings

try:
    from importlib import import_module
except ImportError:
    from django.utils.importlib import import_module


def configure():

    # catch djangoldp specific settings
    settings = os.getenv('DJANGOLDP_SETTINGS')
    if not settings:
        raise ImportError('Settings could not be imported because DJANGOLDP_SETTINGS is not set')

    #mod = import_module(settings)

    # craft a settings module from class
    ldpsettings = LDPSettings('config.yml')
    for key in dir(ldpsettings):
        if key.isupper():
            print(getattr(ldpsettings, key))

    # setup vars to resume django setup process
    os.environ['DJANGO_SETTINGS_MODULE'] = settings


# build a class from django default settings
class DefaultSettings(object):
    pass

for attr in vars(global_settings):
    if not attr.startswith('_'):
        value = getattr(global_settings, attr)
        setattr(DefaultSettings, attr, value)


class LDPSettings(DefaultSettings):

    def __init__(self, path):

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
    def PACKAGES(self):
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
        apps.extend(self.PACKAGES)
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
        for pkg in self.PACKAGES:
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

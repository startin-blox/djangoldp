import yaml

class LDPSettings(object):

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

        # add pacakges
        apps.extend(self.PACKAGES)
        return apps

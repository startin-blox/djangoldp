from django.conf import settings
from django.test import TestCase

YAML = """
  DEBUG: true
  ALLOWED_HOSTS:
    - '*'
  SECRET_KEY: 'thetestingsecretkey'
  DATABASES:
    default:
      ENGINE: django.db.backends.sqlite3
      NAME: db.sqlite3
  STATIC_ROOT: static
  MEDIA_ROOT: media
  LDP_RDF_CONTEXT: https://cdn.happy-dev.fr/owl/hdcontext.jsonld
  ROOT_URLCONF: server.urls
  USE_ETAGS: true
  DEFAULT_CONTENT_TYPE: text/html
  FILE_CHARSET: utf-8
"""

class TestSettings(TestCase):

    def test_settings(self):
        """Asserts load from YAML file."""
        assert settings.DEBUG == False

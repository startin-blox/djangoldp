import sys

import django
from django.conf import settings

settings.configure(DEBUG=False,
                   ALLOWED_HOSTS=["*"],
                   DATABASES={
                       'default': {
                           'ENGINE': 'django.db.backends.sqlite3',
                       }
                   },
                   LDP_RDF_CONTEXT={
                       "@context": {
                           "@vocab": "http://happy-dev.fr/owl/#",
                           "foaf": "http://xmlns.com/foaf/0.1/",
                           "doap": "http://usefulinc.com/ns/doap#",
                           "ldp": "http://www.w3.org/ns/ldp#",
                           "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                           "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                           "xsd": "http://www.w3.org/2001/XMLSchema#",
                           "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
                           "acl": "http://www.w3.org/ns/auth/acl#",
                           "name": "rdfs:label",
                           "website": "foaf:homepage",
                           "deadline": "xsd:dateTime",
                           "lat": "geo:lat",
                           "lng": "geo:long",
                           "jabberID": "foaf:jabberID",
                           "permissions": "acl:accessControl",
                           "mode": "acl:mode",
                           "view": "acl:Read",
                           "change": "acl:Write",
                           "add": "acl:Append",
                           "delete": "acl:Delete",
                           "control": "acl:Control"
                       }
                   },
                   AUTH_USER_MODEL='tests.User',
                   ANONYMOUS_USER_NAME = None,
                   AUTHENTICATION_BACKENDS=(
                       'django.contrib.auth.backends.ModelBackend', 'guardian.backends.ObjectPermissionBackend'),
                   ROOT_URLCONF='djangoldp.urls',
                   DJANGOLDP_PACKAGES=['djangoldp.tests'],
                   INSTALLED_APPS=('django.contrib.auth',
                                   'django.contrib.contenttypes',
                                   'django.contrib.sessions',
                                   'django.contrib.admin',
                                   'guardian',
                                   'djangoldp',
                                   'djangoldp.tests',
                                   ),
                   SEND_BACKLINKS=False,
                   SITE_URL='http://happy-dev.fr',
                   BASE_URL='http://happy-dev.fr',
                   REST_FRAMEWORK = {
                       'DEFAULT_PAGINATION_CLASS': 'djangoldp.pagination.LDPPagination',
                       'PAGE_SIZE': 5
                   },
                   )

django.setup()
from django.test.runner import DiscoverRunner

test_runner = DiscoverRunner(verbosity=1)

failures = test_runner.run_tests([
    'djangoldp.tests.tests_ldp_model',
    'djangoldp.tests.tests_save',
    'djangoldp.tests.tests_user_permissions',
    'djangoldp.tests.tests_guardian',
    'djangoldp.tests.tests_anonymous_permissions',
    'djangoldp.tests.tests_update',
    'djangoldp.tests.tests_auto_author',
    'djangoldp.tests.tests_get',
    'djangoldp.tests.tests_delete',
    'djangoldp.tests.tests_sources',
    'djangoldp.tests.tests_pagination',
    'djangoldp.tests.tests_inbox',
    #'djangoldp.tests.tests_temp'
])
if failures:
    sys.exit(failures)

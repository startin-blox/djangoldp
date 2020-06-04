
from django.conf.global_settings import *

# defines default settings for testing DjangoLDP. You can use this in your own packages by following the example in
# runner.py
DEBUG=False

ALLOWED_HOSTS=["*"]
SITE_URL='http://happy-dev.fr'
BASE_URL='http://happy-dev.fr'

DJANGOLDP_PACKAGES=['djangoldp.tests']
INSTALLED_APPS=('django.contrib.auth',
               'django.contrib.contenttypes',
               'django.contrib.sessions',
               'django.contrib.admin',
               'guardian',
               'djangoldp',
               'djangoldp.tests',
               )

DATABASES={
   'default': {
       'ENGINE': 'django.db.backends.sqlite3',
   }
}

REST_FRAMEWORK = {
   'DEFAULT_PAGINATION_CLASS': 'djangoldp.pagination.LDPPagination',
   'PAGE_SIZE': 5
}

AUTH_USER_MODEL='tests.User'
ANONYMOUS_USER_NAME = None
AUTHENTICATION_BACKENDS=(
   'django.contrib.auth.backends.ModelBackend', 'guardian.backends.ObjectPermissionBackend')

ROOT_URLCONF='djangoldp.urls'

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
}
SEND_BACKLINKS=False

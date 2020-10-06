"""This module contains YAML configurations for djangoldp testing."""

yaml_config = """
dependencies:

ldppackages:
  - djangoldp.tests

server:
  ALLOWED_HOSTS:
    - '*'
  LDP_RDF_CONTEXT:
    "@context":
      "@vocab": "http://happy-dev.fr/owl/#"
      "foaf": "http://xmlns.com/foaf/0.1/"
      "doap": "http://usefulinc.com/ns/doap#"
      "ldp": "http://www.w3.org/ns/ldp#"
      "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
      "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      "xsd": "http://www.w3.org/2001/XMLSchema#"
      "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"
      "acl": "http://www.w3.org/ns/auth/acl#"
      "name": "rdfs:label"
      "website": "foaf:homepage"
      "deadline": "xsd:dateTime"
      "lat": "geo:lat"
      "lng": "geo:long"
      "jabberID": "foaf:jabberID"
      "permissions": "acl:accessControl"
      "mode": "acl:mode"
      "view": "acl:Read"
      "change": "acl:Write"
      "add": "acl:Append"
      "delete": "acl:Delete"
      "control": "acl:Control"
  AUTH_USER_MODEL: 'tests.User'
  EMAIL_HOST: somewhere
  ANONYMOUS_USER_NAME: None
  AUTHENTICATION_BACKENDS:
    - django.contrib.auth.backends.ModelBackend
    - guardian.backends.ObjectPermissionBackend
  ROOT_URLCONF: djangoldp.urls
  SEND_BACKLINKS: false
  SITE_URL: http://happy-dev.fr
  BASE_URL: http://happy-dev.fr
  REST_FRAMEWORK:
    DEFAULT_PAGINATION_CLASS: djangoldp.pagination.LDPPagination
    PAGE_SIZE: 5
  USE_ETAGS: true
  USE_TZ: false
  DEFAULT_CONTENT_TYPE: text/html
  FILE_CHARSET: utf-8
  SEND_BACKLINKS: False
"""

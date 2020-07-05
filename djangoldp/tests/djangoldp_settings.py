"""
This module is meant to be used as a testing LDP package.

It contains configuration elements imported by djangoldp
when the django server is setup.
"""

# define an extra variable
MYPACKAGEVAR = 'ok'

# register an extra middleware
MIDDLEWARE = [
    'djangoldp.tests.dummy.middleware.DummyMiddleware'
]

# register an extra installed app
INSTALLED_APPS = [
    'djangoldp.tests.dummy.apps.DummyConfig'
]

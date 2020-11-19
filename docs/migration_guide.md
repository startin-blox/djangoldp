# Migrate data

## [Test] From djangoldp v1 to v2

* Tested with a production config

Setup the test infra:
```
# docker network create sib
# docker run --network sib --name database -e POSTGRES_PASSWORD=postgres -d postgres
# docker run --network sib --name djangoldp -p 127.0.0.1:8000:8000 -it python:3.6 bash
```

The existing `v1`:
```
# pip install sib-manager
# sib startproject v1 --production
# cd v1
# pip show sib-manager djangoldp
Name: sib-manager
Version: 0.5.3
---
Name: djangoldp
Version: 1.3.4
[...]

# curl -OL https://git.startinblox.com/infra/docker/raw/master/djangoldp/packages.yml
# sib install server
# python manage.py createsuperuser
# python manage.py runserver 0.0.0.0:8000
```

Install the `v2` (with unreleased `beta` branch):
```
# python -m venv /venv
# source /venv/bin/activate

# pip install git+https://git.startinblox.com/djangoldp-packages/djangoldp.git@beta
# djangoldp initserver v2
# cd v2

# # change packages.yml in settings.yml
dependencies:
  - git+https://git.startinblox.com/djangoldp-packages/djangoldp-account.git@beta
  - psycopg2

ldppackages:
  - djangoldp_account

server:
  # DjangoLDP required settings
  DEBUG: False
  ALLOWED_HOSTS:
    - '*'
  SECRET_KEY: '^o3i-*w%5k@52!lriphdxp8+iq#zqd-e+()kfx^g6s5bl@l3^w'
  DATABASES:
    default:
      ENGINE: django.db.backends.postgresql
      NAME: postgres
      USER: postgres
      PASSWORD: postgres
      HOST: database
      PORT: 5432
  LDP_RDF_CONTEXT: https://cdn.happy-dev.fr/owl/hdcontext.jsonld
  ROOT_URLCONF: server.urls
  STATIC_ROOT: static
  MEDIA_ROOT: media
  JABBER_DEFAULT_HOST: http://localhost

# djangoldp install
# djangoldp configure
# djangoldp runserver
```

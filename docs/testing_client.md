# Testing the client in docker

## With SQLite backend

### Setup a project

Setup:
```
# docker run --rm -v $PWD:/code -w /code -p 127.0.0.1:8000:8000 -it python:3.6 bash
# pip install .
# cd /tmp/
# djangoldp startproject myproject
# cd myproject
# djangoldp install
# djangoldp configure
```

Run:
```
# djangoldp runserver
```

Test:
```
$ curl -IL localhost:8000/admin/
```

### Create a package

Add a new package:
```
# djangoldp startpackage mypkg
```

The package template contains test values for middleware and custom var:
```
# cat mypkg/mypkg/djangoldp_settings.py
MIDDLEWARE = ['MY_MIDDLEWARE']
MYPACKAGE_VAR = 'MY_DEFAULT_VAR'
```

Reference it in the project config.yml:
```
ldppackages:
  - mypkg
```

Configure:
```
# djangoldp configure
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, djangoldp, guardian, sessions
Running migrations:
  No migrations to apply.
User "admin" already exists. Skipping...
Confguration done!
```

Test:
```
# python manage.py shell
>>> from django.conf import settings
>>> settings.LDP_PACKAGES
['mypkg']
>>> settings.MIDDLEWARE
['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware', 'MY_MIDDLEWARE']
>>> settings.MYPACKAGE_VAR
'MY_DEFAULT_VAR'
```

### Add a distribution dependency

```
dependencies:
  - git+https://git.startinblox.com/djangoldp-packages/djangoldp-account.git
```

## With PostgreSQL backend

```
# docker network create sib
# docker run --rm --network sib --name postgres -e POSTGRES_DB=sib -e POSTGRES_USER=sib -e POSTGRES_PASSWORD=test -d postgres
# docker run --rm --network sib -p 127.0.0.1:80:8000 -v $PWD:/code -it happydev1/sib:3.6 bash
# pip install --user -e .[dev]
# bash tests/integration/run_test.sh
```


## Test a local package with core beta version

```
sudo docker run --rm -v $PWD/djangoldp-account:/code/djangoldp_account -w /code -it -p 127.0.0.1:8000:8000 python:3.6 bash
# pip install -e djangoldp_account[dev]
# pip install git+https://git.startinblox.com/djangoldp-packages/djangoldp.git@beta
# djangoldp startproject
# vim config.yml
ldppackages:
  - djangoldp_account

# djangoldp configure
```

## Develop core and package all along

```
sudo docker run --rm -v $PWD/djangoldp:/code/djangoldp -v $PWD/djangoldp-account:/code/djangoldp_account -w /code -it -p 127.0.0.1:8000:8000 python:3.6 bash
# pip install -e djangoldp_account[dev]
# pip install -e djangoldp[dev]
```

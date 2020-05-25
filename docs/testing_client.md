# Testing the client in docker

## With SQLite backend

### Setup a project

```
# docker run --rm -v $PWD:/code -w /code -p 127.0.0.1:8000:8000 -it python:3.6 bash
# pip install .
# cd /tmp/
# djangoldp startproject myproject
# cd myproject
# djangoldp install
# djangoldp configure
```

Play with it:
```
# djangoldp runserver
```

### Create a package

Add a new package:
```
# djangoldp startpackage mypkg
```

Reference it in the project config.yml:
```
ldppackages:
  - mypkg
```

```
# djangoldp configure
# djangoldp runserver
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

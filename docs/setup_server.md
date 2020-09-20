# Setup a DjangoLDP server

## Requirements

`djangoldp` requires:

* python 3.6
* postgresql database (for production)

## Get started

Install djangoldp:
```
$ python -m pip install djangoldp
```

Setup a project with a server instance:
```
$ djangoldp startproject myproject
$ cd myproject
```

This step setup a default basic configuration.

Initialize the server:
```
$ djangoldp configure
```

And run the server locally:
```
$ djangoldp runserver
```

You can now log on `http://localhost:8000/admin/` and manage the LDP sources.

## Configure your LDP server

The server comes with a default `settings.yml` you can customize.

It contains 3 main sections:

* `dependencies`: contains a list of dependencies to install with pip during the `install` phase
* `ldppackages`: contains a list of djangoldp packages to activate
* `server`: contains all the configuration required by djangoldp server

You need to restart the server after a change in configuration.

### Dependencies

The format for dependencies is the one accepted by pip. For example:
```
dependencies:
  - git+https://git.startinblox.com/djangoldp-packages/djangoldp-account.git
```

As for any python project when you declare a dependency you have to make sure it is installed. You can use the wrapper command `djangoldp install` for this.

### LDP packages

When you want to use a LDP package you need to reference it in the configuration. For example:
```
ldppackages:
  - djangoldp_account
```

Some packages may require some configuration to work properly. It is a good practice to run the `djangoldp configure` command after adding a new package.

### Server

see https://docs.djangoproject.com/fr/2.2/topics/settings/

## Create a DjangoLDP package

From within your project root directory, create a new package:
```
# djangoldp startpackage mypkg
```

This creates a new package from a default template.

Among other things, the package has a special file allowing a package to load settings when the djangoldp server starts. The `djangoldp_settings.py` file can reference custom variables and load extra middlewares (they are added to the ones loaded by the djangoldp server itself).

```
# cat mypkg/mypkg/djangoldp_settings.py
MIDDLEWARE = []
MYPACKAGE_VAR = 'MY_DEFAULT_VAR'
```

Reference it in the project `settings.yml`:
```
ldppackages:
  - mypkg
```

## Contribute

### Develop DjangoLDP in docker

Install the code inside a container:
```
# docker run --rm -v $PWD:/code -w /code -p 127.0.0.1:8000:8000 -it python:3.6 bash
# pip install -e .[dev]
```

Link a postgres container on docker network:
```
# docker network create sib
# docker run --rm --network sib --name postgres -e POSTGRES_DB=sib -e POSTGRES_USER=sib -e POSTGRES_PASSWORD=test -d postgres
# docker run --rm --network sib -p 127.0.0.1:80:8000 -v $PWD:/code -it python:3.6 bash
# pip install -e .[dev]
```

Develop core and package all along:
```
# docker run --rm -v $PWD/djangoldp:/code/djangoldp -v $PWD/djangoldp-account:/code/djangoldp_account -w /code -it -p 127.0.0.1:8000:8000 python:3.6 bash
# pip install -e djangoldp_account[dev]
# pip install -e djangoldp[dev]
```

Then start a new djangoldp server with the matching settings.yml:
```
ldppackages:
  - djangoldp_account
[...]
```

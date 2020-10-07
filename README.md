# Setup a DjangoLDP server

## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

Building a Startin' Blox application? Read this: https://git.happy-dev.fr/startinblox/devops/doc

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
$ djangoldp initserver myldpserver
$ cd myldperver
```

This step setup a default basic configuration (see: .

Initialize the server:
```
$ djangoldp configure
```

And run the server locally:
```
$ djangoldp runserver
```

You can now log on `http://localhost:8000/admin/` and manage the LDP sources.

## Check technical documentation

* [Configure the LDP server](./docs/setup_server)
* [Create a model](./docs/create_model)

## Contribute to DjangoLDP

### Testing

Packaged with DjangoLDP is a tests module, containing unit tests

You can extend these tests and add your own test cases by following the examples in the code. You can then run your tests with:
`python -m unittest djangoldp.tests.runner`

## License

Licence MIT

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
$ djangoldp configure --with-dummy-admin
```

And run the server locally:
```
$ djangoldp runserver
```

You can now log on `http://localhost:8000/admin/` and manage the LDP sources.

## Check technical documentation

* [Configure the LDP server](./docs/setup_server.md)
* [Create a model](./docs/create_model.md)

## Contribute to DjangoLDP

### Testing

Packaged with DjangoLDP is a tests module, containing unit tests

You can extend these tests and add your own test cases by following the examples in the code. You can then run your tests with:
`python -m unittest djangoldp.tests.runner`

## Check your datas integrity

Because of the way the DjangoLDP's federation work, you can reach some integrity issue within your datas.

You can check them with:

```bash
./manage.py check_integrity
```

You can ignore some servers:

```bash
./manage.py check_integrity --ignore "https://server/,https://another-server/"
```

## License

Licence MIT

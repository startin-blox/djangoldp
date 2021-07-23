# Setup a DjangoLDP server

Check the [official documentation](https://docs.startinblox.com/import_documentation/djangoldp_guide/install-djangoldp-server.html).

## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

Building a Startin' Blox application? Read this: https://git.happy-dev.fr/startinblox/devops/doc

## Check technical documentation

* [Using DjangoLDP with your models](./docs/create_model.md)

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

### Add you own commands to the `check_integrity` from your own package

Create a `check_integrity.py` file within your app folder containing:

```python
def add_arguments(parser):
  parser.add_argument(
    "--my-own-argument",
    default=False,
    nargs="?",
    const=True,
    help="Some help text",
  )

def check_integrity(options):
  if(options["my_own_argument"]):
    print("You ran a check_integrity with --my-own-argument!")
  else:
    print("Run me with `./manage.py check_integrity --my-own-argument`")
```

You can see a sample on the `check_integrity.py` file of DjangoLDP.

## License

Licence MIT

# Setup a DjangoLDP server

Check the [official documentation](https://docs.startinblox.com/import_documentation/djangoldp_guide/install-djangoldp-server.html).

## Settings

* `OIDC_ACCESS_CONTROL_ALLOW_HEADERS`: overrides the access control headers allowed in the `Access-Control-Allow-Headers` CORS header of responses. Defaults to `authorization, Content-Type, if-match, accept, DPoP`
* `ANONYMOUS_USER_NAME` a setting inherited from dependency [Django-Guardian](https://django-guardian.readthedocs.io/en/stable/overview.html)
* `DJANGOLDP_PERMISSIONS`: overrides the list of all permissions on all resources
* `SERIALIZER_CACHE`: toggles the use of a built-in cache in the serialization of containers/resources
* `MAX_RECORDS_SERIALIZER_CACHE`: sets the maximum number of serializer cache records, at which point the cache will be cleared (reset). Defaults to 10,000
* `SEND_BACKLINKS`: enables the searching and sending of [Activities](https://git.startinblox.com/djangoldp-packages/djangoldp/-/wikis/guides/federation) to distant resources linked by users to this server
* `MAX_ACTIVITY_RESCHEDULES`, `DEFAULT_BACKOFF_FACTOR`, `DEFAULT_ACTIVITY_DELAY`, `DEFAULT_REQUEST_TIMEOUT` tweaks the behaviour of the ActivityQueueService
* `STORE_ACTIVITIES`: sets whether to store activities sent and backlinks received, or to treat them as transient (value should be `"VERBOSE"`, `"ERROR"` or `None`). Defaults to `"ERROR"`
* `MAX_RECORDS_ACTIVITY_CACHE`: sets the maximum number of serializer cache records, at which point the cache will be cleared (reset). If set to 0 disables the cache. Defaults to 10,000
* `ENABLE_SWAGGER_DOCUMENTATION`: enables the automatic OpenAPI-based API schema and documentation generation, made available at `http://yourserver/docs/` is the flag is set to True. Default to False
* `DISABLE_LOCAL_OBJECT_FILTER`: disabled the LocalObjectBackendFilter which is processing-time costly and only need activation in federated architecture, so we preferred to add a way to disable it as a workaround for in-progress performances improvements. Default to False

## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

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

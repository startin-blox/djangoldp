# djangoldp-crypto

Packages like [djangoldp](https://git.startinblox.com/djangoldp-packages/djangoldp) and [django-webidoidc-provider](https://git.startinblox.com/djangoldp-packages/django-webidoidc-provider) have some models and utilities which make use of cryptography. In general, we want to re-use that code in a supporting package to avoid duplication of effort. However, until it is more clear what ca be re-used, we are using this separate django app in this package. See [this ticket](https://git.startinblox.com/djangoldp-packages/djangoldp/issues/236) for more.

## Install

```bash
$ python -m pip install 'djangoldp[crypto]'
```

Tnen add the app to your `settings.yml` like so:

```yaml
INSTALLED_APPS:
  - djangoldp_crypto
```

## Management commands

- `creatersakey`: Randomly generate a new RSA key for the DjangoLDP server

## Test

```bash
$ python -m unittest djangoldp_crypto.tests.runner
```

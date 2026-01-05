# Changelog

<!--next-version-placeholder-->

## v5.0.0 (2025-01-05)

### Breaking

* **Django 5 LTS Required** - Upgraded from Django 4.2 to Django 5.2 LTS. Applications must ensure Django 5 compatibility.
* **BrotliMiddleware Removed** - Removed from default middleware as it was corrupting ETags. Configure manually if needed.

### Feature

* **Turtle Serialization** - Full RDF Turtle parser and renderer with content negotiation (`Accept: text/turtle`). See [turtle_serialization.md](./docs/turtle_serialization.md).
* **ETag Support** - RFC 7232 conditional requests with `If-Match`, `If-None-Match`, `If-Modified-Since` headers. New `djangoldp/etag.py` module.
* **Link Headers** - W3C LDP-compliant Link headers for resource types and RFC 8288 pagination.
* **OPTIONS Method** - Full implementation with `Allow`, `Accept-Post`, `Accept-Patch` headers.
* **Prefer Headers** - RFC 7240 support with `return=minimal` (204 response) and `return=representation`.
* **CORS Improvements** - Exposed headers for LDP clients: `Link`, `ETag`, `Last-Modified`, `Accept-Post`, `Accept-Patch`, `Preference-Applied`, `Location`, `Allow`.

### Refactor

* **Serializers Package** - Split `serializers.py` into `djangoldp/serializers/` package with `cache.py`, `fields.py`, `mixins.py`, `list_serializer.py`, `model_serializer.py`.
* **Renderers & Parsers** - Split into dedicated `renderers.py` and `parsers.py` files.
* **Backward Compatibility** - Existing imports via `djangoldp.serializers` continue to work.

### Documentation

* Added [HTTP Headers Reference](./docs/http_headers.md)
* Added [Turtle Serialization Guide](./docs/turtle_serialization.md)
* Added [v5.0.0 Changelog](./docs/changelog/v5.0.0_CHANGELOG.md)
* Updated [LDP Compliance Status](./docs/ldp_compliance_status.md)

### Fix

* Fixed double context in some endpoints
* Fixed Turtle serialisation of complete resources
* Fixed missing method from DRF compatibility

## v3.0.5 (2023-07-24)

### Fix

* Readme ([`8792530`](https://github.com/djangoldp-packages/djangoldp/commit/87925305b2093282230511bceb38978db4b279a2))

## v3.0.4 (2023-07-24)

### Fix

* Readme ([`eeedc33`](https://github.com/djangoldp-packages/djangoldp/commit/eeedc3378ed3f4e454377431da6bb50202efdcdc))

## v3.0.3 (2023-07-24)

### Fix

* Readme ([`73597b6`](https://github.com/djangoldp-packages/djangoldp/commit/73597b65430a4d23306f78def0331bda60857493))


## Unreleased

* Imported CLI along with development template from sib-manager project

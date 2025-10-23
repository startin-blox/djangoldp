"""
Backwards compatibility shim for djangoldp.serializers

This file maintains backwards compatibility by re-exporting all classes from the
new serializers package. Code that imports from `djangoldp.serializers` will continue
to work without any changes.

The actual implementation has been split into multiple files in the `serializers/` package:
- cache.py: Caching functionality
- mixins.py: Reusable mixins
- fields.py: Custom field types
- list_serializer.py: Container serializers
- model_serializer.py: Main LDPSerializer

This allows for better code organization while maintaining backwards compatibility.
"""

# Import everything from the package to maintain backwards compatibility
from .serializers import *  # noqa: F401, F403

# Explicitly import key classes to help with IDE autocomplete
from .serializers import (
    GLOBAL_SERIALIZER_CACHE,
    InMemoryCache,
    RDFSerializerMixin,
    LDListMixin,
    IdentityFieldMixin,
    ContainerSerializer,
    ManyJsonLdRelatedField,
    JsonLdField,
    JsonLdRelatedField,
    JsonLdIdentityField,
    LDPSerializer,
)

__all__ = [
    'InMemoryCache',
    'GLOBAL_SERIALIZER_CACHE',
    'MAX_RECORDS_SERIALIZER_CACHE',
    'RDFSerializerMixin',
    'LDListMixin',
    'IdentityFieldMixin',
    'ContainerSerializer',
    'ManyJsonLdRelatedField',
    'JsonLdField',
    'JsonLdRelatedField',
    'JsonLdIdentityField',
    'LDPSerializer',
]

"""
DjangoLDP Serializers Package

This package provides serializers for the Linked Data Platform (LDP) protocol.
Previously all serializers were in a single file. This package maintains backwards
compatibility by re-exporting all public classes.

Organization:
- cache.py: Serializer caching functionality
- mixins.py: Reusable serializer mixins (RDFSerializerMixin, LDListMixin, IdentityFieldMixin)
- fields.py: Custom field types (JsonLdField, JsonLdRelatedField, JsonLdIdentityField)
- list_serializer.py: List/container serializers (ContainerSerializer, ManyJsonLdRelatedField)
- model_serializer.py: Main model serializer (LDPSerializer)
"""

# Cache
from .cache import (
    InMemoryCache,
    GLOBAL_SERIALIZER_CACHE,
    MAX_RECORDS_SERIALIZER_CACHE,
)

# Mixins
from .mixins import (
    RDFSerializerMixin,
    LDListMixin,
    IdentityFieldMixin,
)

# Fields
from .fields import (
    JsonLdField,
    JsonLdRelatedField,
    JsonLdIdentityField,
)

# List Serializers
from .list_serializer import (
    ContainerSerializer,
    ManyJsonLdRelatedField,
)

# Model Serializer
from .model_serializer import (
    LDPSerializer,
)

# Export all public classes for backwards compatibility
__all__ = [
    # Cache
    'InMemoryCache',
    'GLOBAL_SERIALIZER_CACHE',
    'MAX_RECORDS_SERIALIZER_CACHE',
    # Mixins
    'RDFSerializerMixin',
    'LDListMixin',
    'IdentityFieldMixin',
    # Fields
    'JsonLdField',
    'JsonLdRelatedField',
    'JsonLdIdentityField',
    # List Serializers
    'ContainerSerializer',
    'ManyJsonLdRelatedField',
    # Model Serializer
    'LDPSerializer',
]

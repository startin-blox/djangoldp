from django.db.models import options

__version__ = '0.0.0'

options.DEFAULT_NAMES += (
    'lookup_field', 'rdf_type', 'rdf_context', 'auto_author', 'auto_author_field', 'owner_field', 'owner_urlid_field',
    'view_set', 'container_path', 'permission_classes', 'serializer_fields', 'serializer_fields_exclude', 'empty_containers',
    'nested_fields', 'nested_fields_exclude', 'depth', 'permission_roles', 'inherit_permissions', 'public_field')

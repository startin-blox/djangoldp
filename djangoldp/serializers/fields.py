from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.urls.resolvers import get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.relations import HyperlinkedRelatedField, Hyperlink, MANY_RELATION_KWARGS

from djangoldp.models import Model
from .mixins import RDFSerializerMixin, IdentityFieldMixin


class JsonLdField(HyperlinkedRelatedField, IdentityFieldMixin):
    def __init__(self, view_name=None, **kwargs):
        super().__init__(view_name, **kwargs)
        self.get_lookup_args()

    def get_url(self, obj, view_name, request, format):
        '''Overridden from DRF to shortcut on urlid-holding objects'''
        if hasattr(obj, 'urlid') and obj.urlid not in (None, ''):
            return obj.urlid
        return super().get_url(obj, view_name, request, format)

    def get_lookup_args(self):
        try:
            lookup_field = get_resolver().reverse_dict[self.view_name][0][0][1][0]
            self.lookup_field = lookup_field
            self.lookup_url_kwarg = lookup_field
        except MultiValueDictKeyError:
            pass


class JsonLdRelatedField(JsonLdField, RDFSerializerMixin):
    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        try:
            include_context = False
            if Model.is_external(value):
                data = {'@id': value.urlid}
            else:
                include_context = True
                data = {'@id': super().to_representation(value)}
            return self.serialize_rdf_fields(value, data, include_context=include_context)
        except ImproperlyConfigured:
            return value.pk

    @classmethod
    def many_init(cls, *args, **kwargs):
        # Import here to avoid circular dependency
        from .list_serializer import ManyJsonLdRelatedField

        list_kwargs = {'child_relation': cls(*args, **kwargs),}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyJsonLdRelatedField(**list_kwargs)


class JsonLdIdentityField(JsonLdField):
    '''Represents an identity (url) field for a serializer'''
    def __init__(self, view_name=None, **kwargs):
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        super().__init__(view_name, **kwargs)

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value: Any) -> Any:
        '''returns hyperlink representation of identity field'''
        try:
            # we already have a url to return
            if isinstance(value, str):
                return Hyperlink(value, value)
            # expecting a user instance. Compute the webid and return this in hyperlink format
            else:
                return Hyperlink(value.urlid, value)
        except AttributeError:
            return super().to_representation(value)

    def get_attribute(self, instance):
        if Model.is_external(instance):
            return instance.urlid
        else:
            # runs DRF's RelatedField.get_attribute
            # returns the pk only if optimised or the instance itself in the standard case
            return super().get_attribute(instance)

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.relations import HyperlinkedRelatedField, ManyRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer, CharField
from rest_framework.utils.serializer_helpers import ReturnDict

class ContainerSerializer(ListSerializer):
    def to_representation(self, data):
        return {'@id': '', 'ldp:contains':super(ContainerSerializer, self).to_representation(data)}
    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

class JsonLdRelatedField(HyperlinkedRelatedField):
    def __init__(self, view_name=None, **kwargs):
        super().__init__(view_name, **kwargs)
        #get the field name associated with the url of the view
        try:
            lookup_field = get_resolver().reverse_dict[self.view_name][0][0][1][0]
            self.lookup_field = lookup_field
            self.lookup_url_kwarg = lookup_field
        except MultiValueDictKeyError:
            pass
    def to_representation(self, value):
        try:
            return {'@id': super().to_representation(value)}
        except ImproperlyConfigured:
            return value.pk

class LDPSerializer(HyperlinkedModelSerializer):
    url_field_name = "@id"
    serializer_related_field = JsonLdRelatedField
    
    def to_representation(self, obj):
        data = super().to_representation(obj)
        if hasattr(obj._meta, 'rdf_type'):
            data['@type'] = obj._meta.rdf_type
        return data
    
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ContainerSerializer(*args, **kwargs)

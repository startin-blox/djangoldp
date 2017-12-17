from django.core.urlresolvers import get_resolver
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer, CharField
from rest_framework.utils.serializer_helpers import ReturnDict

class ContainerSerializer(ListSerializer):
    def to_representation(self, data):
        return {'@id': '', 'ldp:contains':super(ContainerSerializer, self).to_representation(data)}
    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

class LDPSerializer(HyperlinkedModelSerializer):
    url_field_name = "@id"
    
    def __init__(self, *args, **kwargs):
        super(LDPSerializer, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field, HyperlinkedRelatedField):
                lookup_field = get_resolver().reverse_dict[field.view_name][0][0][1][0]
                field.lookup_field = lookup_field
                field.lookup_url_kwarg = lookup_field
    
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ContainerSerializer(*args, **kwargs)

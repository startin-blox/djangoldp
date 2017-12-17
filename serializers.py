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
    
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ContainerSerializer(*args, **kwargs)

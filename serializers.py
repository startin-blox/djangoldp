from rest_framework.serializers import ModelSerializer, ListSerializer, CharField
from rest_framework.utils.serializer_helpers import ReturnDict

class IdField(CharField):
    def to_native(self, value):
        return "%s"%value
    def to_internal_value(self, instance):
        return super(IdField, self).to_internal_value(instance.split("/")[-1]) or None

class ContainerSerializer(ListSerializer):
    def to_representation(self, data):
        return {'@id': '', 'ldp:contains':super(ContainerSerializer, self).to_representation(data)}
    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

class LDPSerializer(ModelSerializer):
    def __init__(self, *args, **kwargs):
        super(LDPSerializer, self).__init__(*args, **kwargs)
        self.fields['@id'] = IdField(source="id", required=False)
    
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ContainerSerializer(*args, **kwargs)

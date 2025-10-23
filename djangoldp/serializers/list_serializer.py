from rest_framework.relations import ManyRelatedField
from rest_framework.serializers import ListSerializer
from rest_framework.utils.serializer_helpers import ReturnDict

from .mixins import LDListMixin, IdentityFieldMixin


class ContainerSerializer(LDListMixin, ListSerializer, IdentityFieldMixin):
    id = ''

    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)


class ManyJsonLdRelatedField(LDListMixin, ManyRelatedField):
    child_attr = 'child_relation'
    url_field_name = "@id"

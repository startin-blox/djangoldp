from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.relations import HyperlinkedRelatedField, ManyRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer, CharField
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

class ContainerSerializer(ListSerializer):
    def to_representation(self, data):
        return {'@id': '', 'ldp:contains':super(ContainerSerializer, self).to_representation(data)}
    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

class JsonLdField(HyperlinkedRelatedField):
    def __init__(self, view_name=None, **kwargs):
        super().__init__(view_name, **kwargs)
        self.get_lookup_args()
        
    def get_lookup_args(self):
        try:
            lookup_field = get_resolver().reverse_dict[self.view_name][0][0][1][0]
            self.lookup_field = lookup_field
            self.lookup_url_kwarg = lookup_field
        except MultiValueDictKeyError:
            pass

class JsonLdRelatedField(JsonLdField):
    def to_representation(self, value):
        try:
            return {'@id': super().to_representation(value)}
        except ImproperlyConfigured:
            return value.pk

class JsonLdIdentityField(JsonLdField):
    def __init__(self, view_name=None, **kwargs):
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        super().__init__(view_name, **kwargs)

    def use_pk_only_optimization(self):
        return False

class LDPSerializer(HyperlinkedModelSerializer):
    url_field_name = "@id"
    serializer_related_field = JsonLdRelatedField
    serializer_url_field = JsonLdIdentityField
    
    def get_default_field_names(self, declared_fields, model_info):
        return super().get_default_field_names(declared_fields, model_info) + list(getattr(self.Meta, 'extra_fields', []))
    
    def to_representation(self, obj):
        data = super().to_representation(obj)
        if hasattr(obj._meta, 'rdf_type'):
            data['@type'] = obj._meta.rdf_type
        return data
    
    def build_nested_field(self, field_name, relation_info, nested_depth):
        print(nested_depth)
        class NestedSerializer(self.__class__):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = '__all__'
        
        return NestedSerializer, get_nested_relation_kwargs(relation_info)
    
    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ContainerSerializer(*args, **kwargs)

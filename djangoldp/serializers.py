import json

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from guardian.shortcuts import get_perms
from rest_framework.relations import HyperlinkedRelatedField, ManyRelatedField, MANY_RELATION_KWARGS
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.serializer_helpers import ReturnDict

from djangoldp.tests.models import Skill


class LDListMixin:
    def to_internal_value(self, data):
        # data = json.loads(data)
        data = data['ldp:contains']
        if isinstance(data, dict):
           data = [data]
        return [self.child.to_internal_value(item) for item in data]

    def to_representation(self, value):
        return {'@id': self.id, 'ldp:contains': super().to_representation(value)}

    def get_attribute(self, instance):
        parent_id_field = self.parent.fields[self.parent.url_field_name]
        context = self.parent.context
        parent_id = parent_id_field.get_url(instance, parent_id_field.view_name, context['request'], context['format'])
        self.id = parent_id + self.field_name + "/"
        return super().get_attribute(instance)


class ContainerSerializer(LDListMixin, ListSerializer):
    id = ''

    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

    def create(self, validated_data):
        print(validated_data)
        return super().create(validated_data)

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data['@id'])
        except:
            return super().to_internal_value(data)



class ManyJsonLdRelatedField(LDListMixin, ManyRelatedField):
    pass


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

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data['@id'])
        except:
            return super().to_internal_value(data)

    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyJsonLdRelatedField(**list_kwargs)


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
        try:
            fields = list(self.Meta.model._meta.serializer_fields)
        except:
            fields = super().get_default_field_names(declared_fields, model_info)
        return fields + list(getattr(self.Meta, 'extra_fields', []))

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if hasattr(obj._meta, 'rdf_type'):
            data['@type'] = obj._meta.rdf_type
        data['permissions'] = [{'mode': {'@type': name.split('_')[0]}} for name in
                               get_perms(self.context['request'].user, obj)]
        return data

    def build_nested_field(self, field_name, relation_info, nested_depth):
        class NestedLDPSerializer(self.__class__):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                try:
                    fields = ['@id'] + list(model._meta.serializer_fields)
                except AttributeError:
                    fields = '__all__'

            def to_internal_value(self, data):
                return JsonLdRelatedField(view_name="skill-detail", queryset=Skill.objects.all()).to_internal_value(data)
                # super().to_internal_value(data)]

        kwargs = get_nested_relation_kwargs(relation_info)
        kwargs['read_only'] = False
        return NestedLDPSerializer, kwargs
        # return NestedLDPSerializer, {"many": True}

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls()
        return ContainerSerializer(*args, **kwargs)

    def create(self, validated_data):
        skills = validated_data.pop('skills')
        job_offer = self.Meta.model.objects.create(**validated_data)

        for skill in skills:
            skill.save()
            job_offer.skills.add(skill)
        return job_offer


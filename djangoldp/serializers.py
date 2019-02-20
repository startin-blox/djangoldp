from collections import OrderedDict, Mapping
from urllib import parse

from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.urlresolvers import get_resolver, resolve, get_script_prefix, Resolver404
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.encoding import uri_to_iri
from guardian.shortcuts import get_perms
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField, empty
from rest_framework.fields import get_error_detail, set_value
from rest_framework.relations import HyperlinkedRelatedField, ManyRelatedField, MANY_RELATION_KWARGS
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer
from rest_framework.settings import api_settings
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.serializer_helpers import ReturnDict

from djangoldp.models import Model


class LDListMixin:
    def to_internal_value(self, data):
        try:
            data = data['ldp:contains']
        except (TypeError, KeyError):
            pass
        if isinstance(data, dict):
            data = [data]
        return [self.child.to_internal_value(item) for item in data]

    def to_representation(self, value):
        return {'@id': self.id, '@type': 'ldp:Container', 'ldp:contains': super().to_representation(value)}

    def get_attribute(self, instance):
        parent_id_field = self.parent.fields[self.parent.url_field_name]
        context = self.parent.context
        parent_id = parent_id_field.get_url(instance, parent_id_field.view_name, context['request'], context['format'])
        self.id = parent_id + self.field_name + "/"
        return super().get_attribute(instance)

    def get_value(self, dictionary):
        try:
            object_list = dictionary["@graph"]
            container_id = Model.container_id(self.parent.instance)
            obj = next(filter(lambda o: container_id in o['@id'], object_list))
            list = super().get_value(obj)
            try:
                list = next(filter(lambda o: list['@id'] == o['@id'], object_list))
            except (KeyError, TypeError):
                pass

            try:
                list = list['ldp:contains']
            except (KeyError, TypeError):
                pass

            if isinstance(list, dict):
                list = [list]

            ret = []
            for item in list:
                full_item = None
                try:
                    full_item = next(filter(lambda o: item['@id'] == o['@id'], object_list))
                except StopIteration:
                    pass
                if full_item is None:
                    ret.append(item)
                else:
                    ret.append(full_item)

            return ret
        except KeyError:
            return super().get_value(dictionary)


class ContainerSerializer(LDListMixin, ListSerializer):
    id = ''

    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

    def create(self, validated_data):
        return super().create(validated_data)

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data['@id'])
        except (KeyError, TypeError):
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

    def to_internal_value(self, data):
        return super().to_internal_value(data)

    def get_value(self, dictionary):
        return super().get_value(dictionary)


class JsonLdRelatedField(JsonLdField):
    def to_representation(self, value):
        try:
            return {'@id': super().to_representation(value)}
        except ImproperlyConfigured:
            return value.pk

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data['@id'])
        except (KeyError, TypeError):
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

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data['@id'])
        except KeyError:
            return super().to_internal_value(data)

    def get_value(self, dictionary):
        return super().get_value(dictionary)


class LDPSerializer(HyperlinkedModelSerializer):
    url_field_name = "@id"
    serializer_related_field = JsonLdRelatedField
    serializer_url_field = JsonLdIdentityField

    @property
    def data(self):
        return super().data

    def get_default_field_names(self, declared_fields, model_info):
        try:
            fields = list(self.Meta.model._meta.serializer_fields)
        except AttributeError:
            fields = super().get_default_field_names(declared_fields, model_info)
        try:
            fields.remove(self.Meta.model._meta.auto_author)
        except ValueError:
            pass
        except AttributeError:
            pass
        return fields + list(getattr(self.Meta, 'extra_fields', []))

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if hasattr(obj._meta, 'rdf_type'):
            data['@type'] = obj._meta.rdf_type
        data['permissions'] = [{'mode': {'@type': name.split('_')[0]}} for name in
                               get_perms(self.context['request'].user, obj)]
        return data

    def build_standard_field(self, field_name, model_field):
        class JSonLDStandardField:
            parent_view_name = None

            def __init__(self, **kwargs):
                self.parent_view_name = kwargs.pop('parent_view_name')
                super().__init__(**kwargs)

            def get_value(self, dictionary):
                try:
                    object_list = dictionary["@graph"]
                    resource_id = Model.resource_id(self.parent.instance)
                    obj = next(filter(lambda o: resource_id in o['@id'], object_list))
                    return super().get_value(obj)
                except KeyError:
                    return super().get_value(dictionary)

        field_class, field_kwargs = super().build_standard_field(field_name, model_field)
        field_kwargs['parent_view_name'] = '{}-list'.format(model_field.model._meta.object_name.lower())
        return type(field_class.__name__ + 'Valued', (JSonLDStandardField, field_class), {}), field_kwargs

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
                if self.url_field_name in data:
                    if not isinstance(data, Mapping):
                        message = self.error_messages['invalid'].format(
                            datatype=type(data).__name__
                        )
                        raise ValidationError({
                            api_settings.NON_FIELD_ERRORS_KEY: [message]
                        }, code='invalid')

                    ret = OrderedDict()
                    errors = OrderedDict()
                    fields = list(filter(lambda x: x.field_name in data, self._writable_fields))

                    for field in fields:
                        validate_method = getattr(self, 'validate_' + field.field_name, None)
                        primitive_value = field.get_value(data)
                        try:
                            validated_value = field.run_validation(primitive_value)
                            if validate_method is not None:
                                validated_value = validate_method(validated_value)
                        except ValidationError as exc:
                            errors[field.field_name] = exc.detail
                        except DjangoValidationError as exc:
                            errors[field.field_name] = get_error_detail(exc)
                        except SkipField:
                            pass
                        else:
                            set_value(ret, field.source_attrs, validated_value)

                    if errors:
                        raise ValidationError(errors)

                    uri = data[self.url_field_name]
                    http_prefix = uri.startswith(('http:', 'https:'))

                    if http_prefix:
                        uri = parse.urlparse(uri).path
                        prefix = get_script_prefix()
                        if uri.startswith(prefix):
                            uri = '/' + uri[len(prefix):]

                    try:
                        match = resolve(uri_to_iri(uri))
                        ret['pk'] = match.kwargs['pk']
                    except Resolver404:
                        pass

                    return ret
                else:
                    return super().to_internal_value(data)

        kwargs = get_nested_relation_kwargs(relation_info)
        kwargs['read_only'] = False
        kwargs['required'] = False
        return NestedLDPSerializer, kwargs

    @classmethod
    def many_init(cls, *args, **kwargs):
        kwargs['child'] = cls(**kwargs)
        try:
            cls.Meta.depth = kwargs['context']['view'].many_depth
        except KeyError:
            pass
        return ContainerSerializer(*args, **kwargs)

    def get_value(self, dictionary):
        try:
            object_list = dictionary["@graph"]
            container_id = Model.container_path(self.parent.instance)
            obj = next(filter(lambda o: container_id in o[self.url_field_name], object_list))
            item = super().get_value(obj)
            full_item = None
            if item is empty:
                return empty
            try:
                full_item = next(filter(lambda o: item['@id'] == o['@id'], object_list))
            except StopIteration:
                pass
            if full_item is None:
                return item
            else:
                return full_item

        except KeyError:
            return super().get_value(dictionary)

    def create(self, validated_data):
        return self.internal_create(validated_data, model=self.Meta.model)

    def internal_create(self, validated_data, model):
        nested_fields = []
        nested_fields_name = list(filter(lambda key: isinstance(validated_data[key], list), validated_data))
        for field_name in nested_fields_name:
            nested_fields.append((field_name, validated_data.pop(field_name)))

        instance = model.objects.create(**validated_data)

        self.save_or_update_nested_list(instance, nested_fields)

        return instance

    def update(self, instance, validated_data):
        nested_fields = []
        nested_fields_name = list(filter(lambda key: isinstance(validated_data[key], list), validated_data))
        for field_name in nested_fields_name:
            nested_fields.append((field_name, validated_data.pop(field_name)))

        for attr, value in validated_data.items():
            if isinstance(value, dict):
                manager = getattr(instance, attr)
                if 'pk' in value:
                    oldObj = manager._meta.model.objects.get(pk=value['pk'])
                    value = self.update(instance=oldObj, validated_data=value)
                else:
                    value = self.internal_create(validated_data=value, model=manager._meta.model)
            setattr(instance, attr, value)
        instance.save()

        self.save_or_update_nested_list(instance, nested_fields)

        return instance

    def save_or_update_nested_list(self, instance, nested_fields):
        for (field_name, data) in nested_fields:
            try:
                getattr(instance, field_name).clear()
            except AttributeError:
                pass
            for item in data:
                manager = getattr(instance, field_name)
                if 'pk' in item:
                    oldObj = manager.model.objects.get(pk=item['pk'])
                    savedItem = self.update(instance=oldObj, validated_data=item)
                else:
                    rel = getattr(instance._meta.model, field_name).rel
                    try:
                        if rel.related_model == manager.model:
                            reverse_id = rel.remote_field.attname
                            item[reverse_id] = instance.pk
                    except AttributeError:
                        pass
                    savedItem = self.internal_create(validated_data=item, model=manager.model)

                getattr(instance, field_name).add(savedItem)

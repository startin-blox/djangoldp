import uuid
import json
from collections import OrderedDict
from collections.abc import Mapping
from urllib import parse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.urls import resolve, Resolver404, get_script_prefix
from django.utils.encoding import uri_to_iri
from functools import cached_property
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField, empty, ReadOnlyField
from rest_framework.fields import get_error_detail
from rest_framework.serializers import HyperlinkedModelSerializer, ModelSerializer, LIST_SERIALIZER_KWARGS
from rest_framework.settings import api_settings
from rest_framework.utils import model_meta
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.serializer_helpers import BindingDict

# Import set_value if available (DRF < 3.15), otherwise define it ourselves
try:
    from rest_framework.fields import set_value
except ImportError:
    # set_value was removed in DRF 3.15+
    # Implement it ourselves for compatibility
    def set_value(dictionary, keys, value):
        """
        Similar to Python's built in `dictionary[key] = value`,
        but takes a list of nested keys instead of a single key.

        set_value({'a': 1}, [], {'b': 2}) -> {'a': 1, 'b': 2}
        set_value({'a': 1}, ['x'], 2) -> {'a': 1, 'x': 2}
        set_value({'a': 1}, ['x', 'y'], 2) -> {'a': 1, 'x': {'y': 2}}
        """
        if not keys:
            dictionary.update(value)
            return

        for key in keys[:-1]:
            if key not in dictionary:
                dictionary[key] = {}
            dictionary = dictionary[key]

        dictionary[keys[-1]] = value

from djangoldp.fields import LDPUrlField, IdURLField
from djangoldp.models import Model
from .fields import JsonLdRelatedField, JsonLdIdentityField
from .list_serializer import ContainerSerializer
from .mixins import RDFSerializerMixin


class LDPSerializer(HyperlinkedModelSerializer, RDFSerializerMixin):
    url_field_name = "@id"
    serializer_related_field = JsonLdRelatedField
    serializer_url_field = JsonLdIdentityField
    ModelSerializer.serializer_field_mapping[LDPUrlField] = IdURLField

    # The default serializer repr ends in infinite loop. Overloading it prevents that.
    def __repr__(self):
        return self.__class__.__name__

    @cached_property
    def fields(self):
        """
        A dictionary of {field_name: field_instance}.
        """
        # `fields` is evaluated lazily. We do this to ensure that we don't
        # have issues importing modules that use ModelSerializers as fields,
        # even if Django's app-loading stage has not yet run.
        fields = BindingDict(self)

        # we allow the request object to specify a subset of fields which should be serialized
        model_fields = self.get_fields()
        req_header_accept_shape = self.context['request'].META.get('HTTP_ACCEPT_MODEL_FIELDS') if 'request' in self.context else None
        try:
            allowed_fields = list(set(json.loads(req_header_accept_shape)).intersection(model_fields.keys())) if req_header_accept_shape is not None else model_fields.keys()
        except json.decoder.JSONDecodeError:
            raise ValidationError("Please send the HTTP header Accept-Model-Fields as an array of strings")

        for key, value in model_fields.items():
            if key in allowed_fields:
                fields[key] = value

        return fields

    def get_default_field_names(self, declared_fields, model_info):
        try:
            fields = list(self.Meta.model._meta.serializer_fields)
        except AttributeError:
            fields = super().get_default_field_names(declared_fields, model_info)
        return fields + list(getattr(self.Meta, 'extra_fields', []))

    def _get_rdf_field_name(self, model_field):
        """
        :return: a string RDF type, if configured on the model_field directly
         or on a reverse relation. None, if not configured.
        """
        if getattr(model_field, "rdf_type", None) is not None:
            return model_field.rdf_type
        # If an RDF type is not configured on the foreign key directly, it may be on the reverse-key
        elif (
            hasattr(model_field, "field")
            and getattr(model_field.field, "related_rdf_type", None) is not None
        ):
            return model_field.field.related_rdf_type
        return None

    def to_representation(self, obj):
        # external Models should only be returned with rdf values
        if Model.is_external(obj):
            data = {'@id': obj.urlid}
            return self.serialize_rdf_fields(obj, data)

        data = super().to_representation(obj)

        slug_field = Model.slug_field(obj)
        for field in data:
            if isinstance(data[field], dict) and '@id' in data[field]:
                data[field]['@id'] = data[field]['@id'].format(Model.container_id(obj), str(getattr(obj, slug_field)))
        # prioritise urlid field over generated @id
        if 'urlid' in data and data['urlid'] is not None:
            data['@id'] = data.pop('urlid')['@id']
        if not '@id' in data:
            data['@id'] = '{}{}'.format(settings.SITE_URL, Model.resource(obj))

        # Django Rest Framework will by default serialize fields with the field name.
        # LDPFields may have configured an RDF type which is required for valid serialization.
        # This is handled after serialization to avoid overriding the basic serialization of DRF.
        model = self.Meta.model
        for field in self._readable_fields:
            try:
                model_field = model._meta.get_field(field.source)
                if (
                    model_field is not None
                    and field.field_name in data
                    and self._get_rdf_field_name(model_field) is not None
                ):
                    data[self._get_rdf_field_name(model_field)] = data[field.field_name]
                    data.pop(field.field_name)
            except FieldDoesNotExist:
                pass

        data = self.serialize_rdf_fields(obj, data, include_context=True)
        data = self.add_permissions(data, self.context['request'].user, type(obj), obj=obj)
        return data

    def build_property_field(self, field_name, model_class):
        class JSonLDPropertyField(ReadOnlyField):
            def to_representation(self, instance):
                from djangoldp.views.ldp_viewset import LDPViewSet
                if isinstance(instance, QuerySet):
                    model = instance.model
                elif isinstance(instance, Model):
                    model = type(instance)
                else:
                    return instance
                depth = max(getattr(self.parent.Meta, "depth", 0) - 1, 0)
                fields = ["@id"] if depth==0 else getattr(model._meta, 'serializer_fields', [])

                serializer_generator = LDPViewSet(model=model, fields=fields, depth=depth,
                                                    lookup_field=getattr(model._meta, 'lookup_field', 'pk'),
                                                    permission_classes=getattr(model._meta, 'permission_classes', []),
                                                    nested_fields=getattr(model._meta, 'nested_fields', []))
                serializer = serializer_generator.get_serializer_class()(context=self.parent.context)

                if isinstance(instance, QuerySet):
                    id = '{}{}{}/'.format(settings.SITE_URL, '{}{}/', self.source)
                    children = [serializer.to_representation(item) for item in instance]
                    return self.parent.serialize_container(children, id, self.parent.context['request'].user, model)
                else:
                    return serializer.to_representation(instance)

        return JSonLDPropertyField, {}

    def handle_value_object(self, value):
        '''
        In JSON-LD value-objects can be passed in, which store some context on the field passed. By overriding this
        function you can react to this context on a field without overriding build_standard_field
        '''
        return value['@value']

    def build_standard_field(self, field_name, model_field):
        class JSonLDStandardField:
            parent_view_name = None

            def __init__(self, **kwargs):
                self.parent_view_name = kwargs.pop('parent_view_name')
                super().__init__(**kwargs)

            def get_value(self, dictionary):
                if self.field_name == 'urlid':
                    self.field_name = '@id'
                try:
                    object_list = dictionary["@graph"]
                    if self.parent.instance is None:
                        obj = next(filter(
                            lambda o: not self.parent.url_field_name in o or "./" in o[self.parent.url_field_name],
                            object_list))
                        value = super().get_value(obj)
                    else:
                        resource_id = Model.resource_id(self.parent.instance)
                        obj = next(
                            filter(lambda o: resource_id.lstrip('/') in o[self.parent.url_field_name], object_list))
                        value = super().get_value(obj)
                except KeyError:
                    value = super().get_value(dictionary)

                if self.field_name == '@id' and value == './':
                    self.field_name = 'urlid'
                    return None

                if isinstance(value, dict) and '@value' in value:
                    value = self.parent.handle_value_object(value)

                return self.manage_empty(value)

            def manage_empty(self, value):
                if value == '' and self.allow_null:
                    # If the field is blank, and null is a valid value then
                    # determine if we should use null instead.
                    return '' if getattr(self, 'allow_blank', False) else None
                elif value == '' and not self.required:
                    # If the field is blank, and emptiness is valid then
                    # determine if we should use emptiness instead.
                    return '' if getattr(self, 'allow_blank', False) else empty
                return value

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
                if data == '':
                    return ''
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

                    # validate fields passed in the data
                    for field in self._writable_fields:
                        # Consider only fields which are present in data, but try to find alternative keys for that field
                        # in the data, first.
                        if field.field_name not in data:
                            try:
                                model_field = self.Meta.model._meta.get_field(field.source)
                                rdf_field_name = self._get_rdf_field_name(model_field)
                                if (
                                    model_field is not None
                                    and field.field_name not in data
                                    and rdf_field_name is not None
                                    and rdf_field_name in data
                                ):
                                    data[field.field_name] = data[rdf_field_name]
                                    data.pop(rdf_field_name)
                                else:
                                    continue
                            except FieldDoesNotExist:
                                continue

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

                    # if it's a local resource - use the path to resolve the slug_field on the model
                    uri = data[self.url_field_name]
                    if not Model.is_external(uri):
                        http_prefix = uri.startswith(('http:', 'https:'))

                        if http_prefix:
                            uri = parse.urlparse(uri).path
                            prefix = get_script_prefix()
                            if uri.startswith(prefix):
                                uri = '/' + uri[len(prefix):]

                        try:
                            match = resolve(uri_to_iri(uri))
                            slug_field = Model.slug_field(self.__class__.Meta.model)
                            ret[slug_field] = match.kwargs[slug_field]
                        except Resolver404:
                            pass

                    if 'urlid' in data:
                        ret['urlid'] = data['urlid']

                else:
                    ret = super().to_internal_value(data)

                # copy url_field_name value to urlid, if necessary
                if self.url_field_name in data and not 'urlid' in data and data[self.url_field_name].startswith('http'):
                    ret['urlid'] = data[self.url_field_name]

                return ret

        kwargs = get_nested_relation_kwargs(relation_info)
        kwargs['read_only'] = False
        kwargs['required'] = False
        return NestedLDPSerializer, kwargs

    @classmethod
    def many_init(cls, *args, **kwargs):
        allow_empty = kwargs.pop('allow_empty', None)
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            'child': child_serializer,
        }
        if allow_empty is not None:
            list_kwargs['allow_empty'] = allow_empty
        list_kwargs.update({
            key: value for key, value in kwargs.items()
            if key in LIST_SERIALIZER_KWARGS
        })
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', ContainerSerializer)
        serializer = list_serializer_class(*args, **list_kwargs)

        # if the child serializer has disabled the cache, really it means disable it on the container
        if hasattr(child_serializer, 'with_cache'):
            serializer.with_cache = child_serializer.with_cache

        return serializer

    def to_internal_value(self, data):
        # TODO: This hack is needed because external users don't pass validation.
        # Objects require all fields to be optional to be created as external, and username is required.
        is_user_and_external = self.Meta.model is get_user_model() and '@id' in data and Model.is_external(data['@id'])
        if is_user_and_external:
            data['username'] = 'external'

        # Django Rest Framework will by default parse fields using the field name.
        # The user may give us JSON-LD, which will have been compacted by the JSON-LD parser, but which may still have
        # a namespace associated to it.
        # Currently this data may not always find the correct field, but we make a best-effort by matching
        # the namespace of the data given to an rdf_type configured on that field.
        # TODO: This is not a robust solution but a temporary mitigation.
        # The parser may compact the field to a different namespace or it may not be able to compact the field at all.
        for field in self._writable_fields:
            try:
                model_field = self.Meta.model._meta.get_field(field.source)
                rdf_field_name = self._get_rdf_field_name(model_field)
                if (
                    model_field is not None
                    and field.field_name not in data
                    and rdf_field_name is not None
                    and rdf_field_name in data
                ):
                    data[field.field_name] = data[rdf_field_name]
                    data.pop(rdf_field_name)
            except FieldDoesNotExist:
                pass

        ret = super().to_internal_value(data)
        if is_user_and_external:
            ret['urlid'] = data['@id']
            ret.pop('username')
        return ret

    def get_value(self, dictionary):
        '''overrides get_value to handle @graph key'''
        try:
            object_list = dictionary["@graph"]
            if self.parent.instance is None:
                obj = next(filter(
                    lambda o: not hasattr(o, self.parent.url_field_name) or "./" in o[self.url_field_name],
                    object_list))
            else:
                container_id = Model.container_id(self.parent.instance)
                obj = next(filter(lambda o: container_id.lstrip('/') in o[self.url_field_name], object_list))
            item = super().get_value(obj)
            full_item = None
            if item is empty:
                return empty
            try:
                full_item = next(
                    filter(lambda o: self.url_field_name in o and (item[self.url_field_name] == o[self.url_field_name]),
                           object_list))
            except StopIteration:
                pass
            if full_item is None:
                return item
            else:
                return full_item

        except KeyError:
            return super().get_value(dictionary)

    def create(self, validated_data):
        with transaction.atomic():
            instance = self.internal_create(validated_data, model=self.Meta.model)
            self.attach_related_object(instance, validated_data)

        return instance

    def attach_related_object(self, instance, validated_data):
        '''adds m2m relations included in validated_data to the instance'''
        model_class = self.Meta.model

        info = model_meta.get_field_info(model_class)
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and relation_info.reverse and not field_name is None:
                rel = getattr(instance._meta.model, field_name).rel
                if rel.name in validated_data:
                    related = validated_data[rel.name]
                    getattr(instance, field_name).add(related)

    def internal_create(self, validated_data, model):
        validated_data = self.resolve_fk_instances(model, validated_data, True)

        # build tuples list of nested_field keys and their values. All list values are considered nested fields
        nested_fields = []
        nested_list_fields_name = list(filter(lambda key: isinstance(validated_data[key], list), validated_data))
        for field_name in nested_list_fields_name:
            nested_fields.append((field_name, validated_data.pop(field_name)))

        info = model_meta.get_field_info(model)
        many_to_many = []
        one_to_one = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and relation_info.reverse and (
                    field_name in validated_data) and not field_name is None:
                many_to_many.append((field_name, validated_data.pop(field_name)))
            elif relation_info.reverse and (field_name in validated_data) and not field_name is None:
                one_to_one[field_name] = validated_data.pop(field_name)
        validated_data = self.remove_empty_value(validated_data)

        if model is get_user_model() and not 'username' in validated_data:
            validated_data['username'] = str(uuid.uuid4())
        instance = model.objects.create(**validated_data)

        for field_name, value in many_to_many:
            validated_data[field_name] = value

        if one_to_one:
             for field_name, value in one_to_one.items():
                 setattr(instance, field_name, value)
                 value.save()

        self.save_or_update_nested_list(instance, nested_fields)

        return instance

    def remove_empty_value(self, validated_data):
        '''sets any empty strings in the validated_data to None'''
        for attr, value in validated_data.items():
            if value == '':
                validated_data[attr] = None
        return validated_data

    def update(self, instance, validated_data):
        model = self.Meta.model
        nested_fields = []
        nested_fields_name = list(filter(lambda key: isinstance(validated_data[key], list), validated_data))
        for field_name in nested_fields_name:
            nested_fields.append((field_name, validated_data.pop(field_name)))

        for attr, value in validated_data.items():
            if isinstance(value, dict):
                value = self.update_dict_value(attr, instance, value)
            if value == '' and not isinstance(getattr(instance, attr), str):
                setattr(instance, attr, None)
            else:
                setattr(instance, attr, value)

        self.save_or_update_nested_list(instance, nested_fields)
        instance.save()

        return instance

    def resolve_fk_instances(self, model, validated_data, create=False):
        '''
        iterates over every dict object in validated_data and resolves them into instances (get or create)
        :param model: the model being operated on
        :param validated_data: the data passed to the serializer
        :param create: set to True, foreign keys will be created if they do not exist
        '''
        nested_fk_fields_name = list(filter(lambda key: isinstance(validated_data[key], dict), validated_data))
        for field_name in nested_fk_fields_name:
            field_dict = validated_data[field_name]
            field_model = model._meta.get_field(field_name).related_model

            slug_field = Model.slug_field(field_model)
            sub_inst = None
            if 'urlid' in field_dict:
                # has urlid and is a local resource
                model, sub_inst = self.get_inst_by_urlid(field_dict, field_model, model, slug_field, sub_inst)
            # try slug field, assuming that this is a local resource
            elif slug_field in field_dict:
                kwargs = {slug_field: field_dict[slug_field]}
                sub_inst = field_model.objects.get(**kwargs)
            if sub_inst is None:
                if create:
                    sub_inst = self.internal_create(field_dict, field_model)
                else:
                    continue

            validated_data[field_name] = sub_inst
        return validated_data

    def get_inst_by_urlid(self, field_dict, field_model, model, slug_field, sub_inst):
        if parse.urlparse(settings.BASE_URL).netloc == parse.urlparse(field_dict['urlid']).netloc:
            # try slug field if it exists
            if slug_field in field_dict:
                kwargs = {slug_field: field_dict[slug_field]}
                sub_inst = field_model.objects.get(**kwargs)
            else:
                model, sub_inst = Model.resolve(field_dict['urlid'])
        # remote resource - get backlinked copy
        elif hasattr(field_model, 'urlid'):
            sub_inst = Model.get_or_create_external(field_model, field_dict['urlid'])
        return model, sub_inst

    def update_dict_value(self, attr, instance, value):
        info = model_meta.get_field_info(instance)
        relation_info = info.relations.get(attr)
        slug_field = Model.slug_field(relation_info.related_model)

        if slug_field in value:
            value = self.update_dict_value_when_id_is_provided(attr, instance, relation_info, slug_field, value)
        else:
            if 'urlid' in value:
                if parse.urlparse(settings.BASE_URL).netloc == parse.urlparse(value['urlid']).netloc:
                    model, oldObj = Model.resolve(value['urlid'])
                    value = self.update(instance=oldObj, validated_data=value)
                elif hasattr(relation_info.related_model, 'urlid'):
                    value = Model.get_or_create_external(relation_info.related_model, value['urlid'])
            else:
                value = self.update_dict_value_without_slug_field(attr, instance, relation_info, value)
        return value

    def update_dict_value_without_slug_field(self, attr, instance, relation_info, value):
        if relation_info.to_many:
            value = self.internal_create(validated_data=value, model=relation_info.related_model)
        else:
            rel = instance._meta.get_field(attr)
            reverse_attr_name = rel.remote_field.name
            many = rel.one_to_many or rel.many_to_many
            if many:
                value[reverse_attr_name] = [instance]
                oldObj = rel.model.object.get(id=value['urlid'])
            else:
                value[reverse_attr_name] = instance
                oldObj = getattr(instance, attr, None)

            if oldObj is None:
                value = self.internal_create(validated_data=value, model=relation_info.related_model)
            else:
                value = self.update(instance=oldObj, validated_data=value)
        return value

    def update_dict_value_when_id_is_provided(self, attr, instance, relation_info, slug_field, value):
        kwargs = {slug_field: value[slug_field]}
        if relation_info.to_many:
            manager = getattr(instance, attr)
            oldObj = manager._meta.model.objects.get(**kwargs)
        else:
            related_model = relation_info.related_model
            oldObj = related_model.objects.get(**kwargs)

        value = self.update(instance=oldObj, validated_data=value)
        return value

    def save_or_update_nested_list(self, instance, nested_fields):
        for (field_name, data) in nested_fields:
            manager = getattr(instance, field_name)
            field_model = manager.model
            slug_field = Model.slug_field(field_model)
            try:
                item_pk_to_keep = [obj_dict[slug_field] for obj_dict in data if slug_field in obj_dict]
            except TypeError:
                item_pk_to_keep = [getattr(obj, slug_field) for obj in data if hasattr(obj, slug_field)]

            if hasattr(manager, 'through'):
                manager.clear()
            else:
                manager.exclude(pk__in=item_pk_to_keep).delete()

            for item in data:
                if isinstance(item, Model):
                    item.save()
                    saved_item = item
                elif slug_field in item:
                    kwargs = {slug_field: item[slug_field]}
                    saved_item = self.get_or_create(field_model, item, kwargs)
                elif 'urlid' in item:
                    # has urlid and is a local resource
                    if not Model.is_external(item['urlid']):
                        model, old_obj = Model.resolve(item['urlid'])
                        if old_obj is not None:
                            saved_item = self.update(instance=old_obj, validated_data=item)
                        else:
                            saved_item = self.internal_create(validated_data=item, model=field_model)
                    # has urlid and is external resource
                    elif hasattr(field_model, 'urlid'):
                        kwargs = {'urlid': item['urlid']}
                        saved_item = self.get_or_create(field_model, item, kwargs)
                else:
                    rel = getattr(instance._meta.model, field_name).rel
                    try:
                        if rel.related_model == manager.model:
                            reverse_id = rel.remote_field.attname
                            item[reverse_id] = instance.pk
                    except AttributeError:
                        pass
                    saved_item = self.internal_create(validated_data=item, model=manager.model)

                if hasattr(manager, 'through') and manager.through._meta.auto_created:
                    # First remove to avoid duplicates
                    manager.remove(saved_item)
                    manager.add(saved_item)

    def get_or_create(self, field_model, item, kwargs):
        try:
            old_obj = field_model.objects.get(**kwargs)
            saved_item = self.update(instance=old_obj, validated_data=item)
        except field_model.DoesNotExist:
            saved_item = self.internal_create(validated_data=item, model=field_model)
        return saved_item

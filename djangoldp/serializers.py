import uuid
from collections import OrderedDict, Mapping, Iterable
from typing import Any
from urllib import parse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.urlresolvers import get_resolver, resolve, get_script_prefix, Resolver404
from django.db.models import QuerySet
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.encoding import uri_to_iri
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField, empty, ReadOnlyField
from rest_framework.fields import get_error_detail, set_value
from rest_framework.relations import HyperlinkedRelatedField, ManyRelatedField, MANY_RELATION_KWARGS, Hyperlink
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer, ModelSerializer
from rest_framework.settings import api_settings
from rest_framework.utils import model_meta
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.serializer_helpers import ReturnDict

from djangoldp.fields import LDPUrlField, IdURLField
from djangoldp.models import Model
from djangoldp.permissions import LDPPermissions


class LDListMixin:
    '''A Mixin for serializing containers into JSONLD format'''
    child_attr = 'child'

    # converts primitive data representation to the representation used within our application
    def to_internal_value(self, data):
        try:
            # if this is a container, the data will be stored in ldp:contains
            data = data['ldp:contains']
        except (TypeError, KeyError):
            pass

        if len(data) == 0:
            return []
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, str) and data.startswith("http"):
            data = [{'@id': data}]

        return [getattr(self, self.child_attr).to_internal_value(item) for item in data]

    def to_representation(self, value):
        '''
        Converts internal representation to primitive data representation
        Filters objects out which I don't have permission to view
        Permission on container :
         - Can Add if add permission on contained object's type
         - Can view the container is view permission on container model : container obj are filtered by view permission
        '''
        try:
            child_model = getattr(self, self.child_attr).Meta.model
        except AttributeError:
            child_model = value.model

        parent_model = None

        if isinstance(value, QuerySet):
            value = list(value)

        if not isinstance(value, Iterable):
            filtered_values = value
            container_permissions = Model.get_permissions(child_model, self.context['request'].user, ['view', 'add'])
        else:
            # this is a container. Parent model is the containing object, child the model contained
            try:
                parent_model = Model.resolve_parent(self.context['request'].path)
            except:
                parent_model = child_model

            # remove objects from the list which I don't have permission to view
            filtered_values = list(
                filter(lambda v: Model.get_permission_classes(v, [LDPPermissions])[0]().has_object_permission(
                    self.context['request'], self.context['view'], v), value))
            container_permissions = Model.get_permissions(child_model, self.context['request'].user, ['add'])
            container_permissions.extend(
                Model.get_permissions(parent_model, self.context['request'].user,
                                      ['view']))
        if not self.id.startswith('http'):
            self.id = '{}{}{}'.format(settings.BASE_URL, Model.resource(parent_model), self.id)
        return {'@id': self.id,
                '@type': 'ldp:Container',
                'ldp:contains': super().to_representation(filtered_values),
                'permissions': container_permissions
                }

    def get_attribute(self, instance):
        parent_id_field = self.parent.fields[self.parent.url_field_name]
        context = self.parent.context
        parent_id = parent_id_field.get_url(instance, parent_id_field.view_name, context['request'], context['format'])
        self.id = parent_id + self.field_name + "/"
        return super().get_attribute(instance)

    def get_value(self, dictionary):
        try:
            object_list = dictionary['@graph']

            if self.parent.instance is None:
                obj = next(filter(
                    lambda o: not hasattr(o, self.parent.url_field_name) or "./" in o[self.parent.url_field_name],
                    object_list))
            else:
                container_id = Model.container_id(self.parent.instance)
                obj = next(filter(lambda o: container_id.lstrip('/') in o[self.parent.url_field_name], object_list))
            list = super().get_value(obj)
            try:
                list = next(
                    filter(lambda o: list[self.parent.url_field_name] == o[self.parent.url_field_name], object_list))
            except (KeyError, TypeError, StopIteration):
                pass

            try:
                list = list['ldp:contains']
            except (KeyError, TypeError):
                pass

            if list is empty:
                return []

            if isinstance(list, dict):
                list = [list]

            ret = []
            for item in list:
                full_item = None
                try:
                    full_item = next(filter(
                        lambda o: self.parent.url_field_name in o and item[self.parent.url_field_name] == o[
                            self.parent.url_field_name], object_list))
                except StopIteration:
                    pass
                if full_item is None:
                    ret.append(item)
                else:
                    ret.append(full_item)

            return ret
        except KeyError:
            obj = super().get_value(dictionary)
            if isinstance(obj, dict) and self.parent.url_field_name in obj:
                resource_id = obj[self.parent.url_field_name]
                if isinstance(resource_id, str) and resource_id.startswith("_:"):
                    object_list = self.root.initial_data['@graph']
                    obj = [next(filter(lambda o: resource_id in o[self.parent.url_field_name], object_list))]

            return obj


class ContainerSerializer(LDListMixin, ListSerializer):
    id = ''

    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)

    def create(self, validated_data):
        return super().create(validated_data)

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data[self.parent.url_field_name])
        except (KeyError, TypeError):
            return super().to_internal_value(data)


class ManyJsonLdRelatedField(LDListMixin, ManyRelatedField):
    child_attr = 'child_relation'
    url_field_name = "@id"


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
            if Model.is_external(value):
                return {'@id': value.urlid}
            else:
                return {'@id': super().to_representation(value)}
        except ImproperlyConfigured:
            return value.pk

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data[self.parent.url_field_name])
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
    '''Represents an identity (url) field for a serializer'''
    def __init__(self, view_name=None, **kwargs):
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        super().__init__(view_name, **kwargs)

    def use_pk_only_optimization(self):
        return False

    def to_internal_value(self, data):
        '''tells serializer how to write identity field'''
        try:
            return super().to_internal_value(data[self.parent.url_field_name])
        except KeyError:
            return super().to_internal_value(data)

    def get_value(self, dictionary):
        return super().get_value(dictionary)

    def to_representation(self, value: Any) -> Any:
        '''returns hyperlink representation of identity field'''
        try:
            # we already have a url to return
            if isinstance(value, str):
                return Hyperlink(value, value)
            # expecting a user instance. Compute the webid and return this in hyperlink format
            else:
                return Hyperlink(value.webid(), value)
        except AttributeError:
            return super().to_representation(value)

    def get_attribute(self, instance):
        if Model.is_external(instance):
            return instance.urlid
        else:
            # runs DRF's RelatedField.get_attribute
            # returns the pk only if optimised or the instance itself in the standard case
            return super().get_attribute(instance)


class LDPSerializer(HyperlinkedModelSerializer):
    url_field_name = "@id"
    serializer_related_field = JsonLdRelatedField
    serializer_url_field = JsonLdIdentityField
    ModelSerializer.serializer_field_mapping[LDPUrlField] = IdURLField

    def get_default_field_names(self, declared_fields, model_info):
        try:
            fields = list(self.Meta.model._meta.serializer_fields)
        except AttributeError:
            fields = super().get_default_field_names(declared_fields, model_info)
        return fields + list(getattr(self.Meta, 'extra_fields', []))

    def to_representation(self, obj):
        # external Models should only be returned with an id (on GET)
        if self.context['request'].method == 'GET' and Model.is_external(obj):
            return {'@id': obj.urlid}

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
        rdf_type = Model.get_meta(obj, 'rdf_type', None)
        rdf_context = Model.get_meta(obj, 'rdf_context', None)
        if rdf_type is not None:
            data['@type'] = rdf_type
        if rdf_context is not None:
            data['@context'] = rdf_context
        data['permissions'] = Model.get_permissions(obj, self.context['request'].user,
                                                    ['view', 'change', 'control', 'delete'])

        return data

    def build_field(self, field_name, info, model_class, nested_depth):
        return super().build_field(field_name, info, model_class, nested_depth)

    def build_property_field(self, field_name, model_class):
        class JSonLDPropertyField(ReadOnlyField):
            def to_representation(self, instance):
                from djangoldp.views import LDPViewSet

                if isinstance(instance, QuerySet) or isinstance(instance, Model):
                    try:
                        model_class = instance.model
                    except:
                        model_class = instance.__class__
                    serializer_generator = LDPViewSet(model=model_class,
                                                      lookup_field=Model.get_meta(model_class, 'lookup_field', 'pk'),
                                                      permission_classes=Model.get_meta(model_class,
                                                                                        'permission_classes',
                                                                                        [LDPPermissions]),
                                                      fields=Model.get_meta(model_class, 'serializer_fields', []),
                                                      nested_fields=Model.get_meta(model_class, 'nested_fields', []))
                    parent_depth = max(getattr(self.parent.Meta, "depth", 0) - 1, 0)
                    serializer_generator.depth = parent_depth
                    serializer = serializer_generator.build_read_serializer()(context=self.parent.context)
                    if parent_depth is 0:
                        serializer.Meta.fields = ["@id"]

                    if isinstance(instance, QuerySet):
                        data = list(instance)

                        return {'@id': '{}{}{}/'.format(settings.SITE_URL, '{}{}/', self.source),
                                '@type': 'ldp:Container',
                                'ldp:contains': [serializer.to_representation(item) if item is not None else None for
                                                 item
                                                 in data],
                                'permissions': Model.get_permissions(self.parent.Meta.model,
                                                                     self.context['request'].user,
                                                                     ['view', 'add'])
                                }
                    else:
                        return serializer.to_representation(instance)
                else:
                    return instance

        field_class = JSonLDPropertyField
        field_kwargs = {}

        return field_class, field_kwargs

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
                if data is '':
                    return ''
                # workaround for Hubl app - 293
                if 'username' in data and not self.url_field_name in data:
                    data[self.url_field_name] = './'
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

                    # resolve path of the resource
                    uri = data[self.url_field_name]
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
        kwargs['child'] = cls(**kwargs)
        serializer = ContainerSerializer(*args, **kwargs)
        if 'context' in kwargs and getattr(kwargs['context']['view'], 'nested_field', None) is not None:
            serializer.id = '{}{}/'.format(serializer.id, kwargs['context']['view'].nested_field)
        elif 'context' in kwargs:
            serializer.id = '{}{}'.format(settings.BASE_URL, kwargs['context']['view'].request.path)
        return serializer

    def to_internal_value(self, data):
        is_user_and_external = self.Meta.model is get_user_model() and '@id' in data and not data['@id'].startswith(
            settings.BASE_URL)
        if is_user_and_external:
            data['username'] = 'external'
        ret = super().to_internal_value(data)
        if is_user_and_external:
            ret['urlid'] = data['@id']
            ret.pop('username')
        return ret

    def get_value(self, dictionary):
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
        instance = self.internal_create(validated_data, model=self.Meta.model)

        self.attach_related_object(instance, validated_data)

        return instance

    def attach_related_object(self, instance, validated_data):
        model_class = self.Meta.model

        info = model_meta.get_field_info(model_class)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and relation_info.reverse and not field_name is None:
                rel = getattr(instance._meta.model, field_name).rel
                if rel.name in validated_data:
                    related = validated_data[rel.name]
                    getattr(instance, field_name).add(related)

    def internal_create(self, validated_data, model):
        validated_data = self.resolve_fk_instances(model, validated_data)

        # build tuples list of nested_field keys and their values
        nested_fields = []
        nested_list_fields_name = list(filter(lambda key: isinstance(validated_data[key], list), validated_data))
        for field_name in nested_list_fields_name:
            nested_fields.append((field_name, validated_data.pop(field_name)))

        info = model_meta.get_field_info(model)
        many_to_many = []
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and relation_info.reverse and (
                    field_name in validated_data) and not field_name is None:
                many_to_many.append((field_name, validated_data.pop(field_name)))
        validated_data = self.remove_empty_value(validated_data)

        if model is get_user_model() and not 'username' in validated_data:
            validated_data['username'] = str(uuid.uuid4())
        instance = model.objects.create(**validated_data)

        for field_name, value in many_to_many:
            validated_data[field_name] = value

        self.save_or_update_nested_list(instance, nested_fields)

        return instance

    def remove_empty_value(self, validated_data):
        '''sets any empty strings in the validated_data to None'''
        for attr, value in validated_data.items():
            if value is '':
                validated_data[attr] = None
        return validated_data

    def update(self, instance, validated_data):
        model = self.Meta.model
        validated_data = self.resolve_fk_instances(model, validated_data)

        nested_fields = []
        nested_fields_name = list(filter(lambda key: isinstance(validated_data[key], list), validated_data))
        for field_name in nested_fields_name:
            nested_fields.append((field_name, validated_data.pop(field_name)))

        for attr, value in validated_data.items():
            if isinstance(value, dict):
                value = self.update_dict_value(attr, instance, value)
            if value is '' and not isinstance(getattr(instance, attr), str):
                setattr(instance, attr, None)
            else:
                setattr(instance, attr, value)

        self.save_or_update_nested_list(instance, nested_fields)
        instance.save()

        return instance

    def resolve_fk_instances(self, model, validated_data):
        '''iterates over every dict object in validated_data and resolves them into instances (get or create)'''
        nested_fk_fields_name = list(filter(lambda key: isinstance(validated_data[key], dict), validated_data))
        for field_name in nested_fk_fields_name:
            field_dict = validated_data[field_name]
            try:
                field_model = getattr(model, field_name).field.rel.model
            except:
                # not fk
                continue
            slug_field = Model.slug_field(field_model)
            sub_inst = None
            if 'urlid' in field_dict:
                # has urlid and is a local resource
                if parse.urlparse(settings.BASE_URL).netloc == parse.urlparse(field_dict['urlid']).netloc:
                    # try slug field if it exists
                    if slug_field in field_dict:
                        kwargs = {slug_field: field_dict[slug_field]}
                        sub_inst = field_model.objects.get(**kwargs)
                    else:
                        model, sub_inst = Model.resolve(field_dict['urlid'])
                # remote resource - get backlinked copy
                elif hasattr(field_model, 'urlid'):
                    sub_inst = Model.get_or_create(field_model, field_dict['urlid'])
            # try slug field, assuming that this is a local resource
            elif slug_field in field_dict:
                kwargs = {slug_field: field_dict[slug_field]}
                sub_inst = field_model.objects.get(**kwargs)
            if sub_inst is None:
                sub_inst = self.internal_create(field_dict, field_model)
            validated_data[field_name] = sub_inst
        return validated_data

    def update_dict_value(self, attr, instance, value):
        info = model_meta.get_field_info(instance)
        slug_field = Model.slug_field(instance)
        relation_info = info.relations.get(attr)
        if slug_field in value:
            value = self.update_dict_value_when_id_is_provided(attr, instance, relation_info, slug_field, value)
        else:
            value = self.update_dict_value_without_slug_field(attr, instance, relation_info, value)
        return value

    def update_dict_value_without_slug_field(self, attr, instance, relation_info, value):
        if relation_info.to_many:
            value = self.internal_create(validated_data=value, model=relation_info.related_model)
        else:
            try:
                reverse_attr_name = instance._meta.fields_map[attr].remote_field.name
                many = False
            except:
                rel = list(filter(lambda field: field.name == attr, instance._meta.fields))[0].rel
                many = rel.one_to_many
                reverse_attr_name = rel.related_name
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
            oldObj = getattr(instance, attr)

        value = self.update(instance=oldObj, validated_data=value)
        return value

    def save_or_update_nested_list(self, instance, nested_fields):
        for (field_name, data) in nested_fields:
            manager = getattr(instance, field_name)
            field_model = manager.model
            slug_field = Model.slug_field(manager.model)
            try:
                item_pk_to_keep = list(map(lambda e: e[slug_field], filter(lambda x: slug_field in x, data)))
            except TypeError:
                item_pk_to_keep = list(
                    map(lambda e: getattr(e, slug_field), filter(lambda x: hasattr(x, slug_field), data)))

            if getattr(manager, 'through', None) is None:
                for item in list(manager.all()):
                    if not str(getattr(item, slug_field)) in item_pk_to_keep:
                        item.delete()
            else:
                manager.clear()

            for item in data:
                if not isinstance(item, dict):
                    item.save()
                    saved_item = item
                elif slug_field in item:
                    kwargs = {slug_field: item[slug_field]}
                    saved_item = self.get_or_create(field_model, item, kwargs)
                elif 'urlid' in item:
                    # has urlid and is a local resource
                    if parse.urlparse(settings.BASE_URL).netloc == parse.urlparse(item['urlid']).netloc:
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

                if getattr(manager, 'through', None) is not None and manager.through._meta.auto_created:
                    manager.remove(saved_item)
                    manager.add(saved_item)

    def get_or_create(self, field_model, item, kwargs):
        try:
            old_obj = field_model.objects.get(**kwargs)
            saved_item = self.update(instance=old_obj, validated_data=item)
        except field_model.DoesNotExist:
            saved_item = self.internal_create(validated_data=item, model=field_model)
        return saved_item

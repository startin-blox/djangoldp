import uuid
import json
from collections import OrderedDict
from collections.abc import Mapping, Iterable
from copy import copy
from typing import Any
from urllib import parse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.urls import resolve, Resolver404, get_script_prefix
from django.urls.resolvers import get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.encoding import uri_to_iri
from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SkipField, empty, ReadOnlyField
from rest_framework.fields import get_error_detail, set_value
from rest_framework.relations import HyperlinkedRelatedField, ManyRelatedField, Hyperlink, MANY_RELATION_KWARGS
from rest_framework.serializers import HyperlinkedModelSerializer, ListSerializer, ModelSerializer, LIST_SERIALIZER_KWARGS
from rest_framework.settings import api_settings
from rest_framework.utils import model_meta
from rest_framework.utils.field_mapping import get_nested_relation_kwargs
from rest_framework.utils.serializer_helpers import ReturnDict, BindingDict

from djangoldp.fields import LDPUrlField, IdURLField
from djangoldp.models import Model
from djangoldp.permissions import DEFAULT_DJANGOLDP_PERMISSIONS

# defaults for various DjangoLDP settings (see documentation)
MAX_RECORDS_SERIALIZER_CACHE = getattr(settings, 'MAX_RECORDS_SERIALIZER_CACHE', 10000)

class InMemoryCache:
    def __init__(self):
        self.cache = {
        }

    def reset(self):
        self.cache = {
        }

    def has(self, cache_key, container_urlid=None, vary=None):
        return cache_key in self.cache and \
               (container_urlid is None or container_urlid in self.cache[cache_key]) and \
               (vary is None or vary in self.cache[cache_key][container_urlid])

    def get(self, cache_key, container_urlid, vary):
        if self.has(cache_key, container_urlid, vary):
            return self.cache[cache_key][container_urlid][vary]['value']
        else:
            return None

    def set(self, cache_key, container_urlid, vary, value):
        if len(self.cache.keys()) > MAX_RECORDS_SERIALIZER_CACHE:
            self.reset()
        
        if cache_key not in self.cache:
            self.cache[cache_key] = {}
        if container_urlid not in self.cache[cache_key]:
            self.cache[cache_key][container_urlid] = {}
        self.cache[cache_key][container_urlid][vary] = {'value': value}

    def invalidate(self, cache_key, container_urlid=None, vary=None):
        # can clear cache_key -> container_urlid -> vary, cache_key -> container_urlid or cache_key
        if container_urlid is not None:
            if vary is not None:
                self.cache[cache_key][container_urlid].pop(vary, None)
            else:
                self.cache[cache_key].pop(container_urlid, None)
        else:
            self.cache.pop(cache_key, None)
GLOBAL_SERIALIZER_CACHE = InMemoryCache()

class RDFSerializerMixin:
    def add_permissions(self, data, user, model, obj=None):
        '''takes a set or list of permissions and returns them in the JSON-LD format'''
        if self.parent and not settings.LDP_INCLUDE_INNER_PERMS: #Don't serialize permissions on nested objects
            return data

        if user.is_superuser:
            data['permissions'] = getattr(settings, 'DJANGOLDP_PERMISSIONS', DEFAULT_DJANGOLDP_PERMISSIONS)
            return data

        permission_classes = getattr(model._meta, 'permission_classes', [])
        if not permission_classes:
            return data
        # The permissions must be given by all permission classes to be granted
        permissions = set.intersection(*[permission().get_permissions(user, model, obj) for permission in permission_classes])
        # Don't grant delete permissions on containers
        if not obj and 'delete' in permissions:
            permissions.remove('delete')
        data['permissions'] = permissions
        return data
    
    def serialize_rdf_fields(self, obj, data, include_context=False):
        '''adds the @type and the @context to the data'''
        rdf_type = getattr(obj._meta, 'rdf_type', None)
        rdf_context = getattr(obj._meta, 'rdf_context', None)
        if rdf_type:
            data['@type'] = rdf_type
        if include_context and rdf_context:
            data['@context'] = rdf_context
        return data

    def serialize_container(self, data, id, user, model, obj=None):
        '''turns a list into a container representation'''
        return self.add_permissions({'@id': id, '@type': 'ldp:Container', 'ldp:contains': data}, user, model, obj)

class LDListMixin(RDFSerializerMixin):
    '''A Mixin for serializing containers into JSONLD format'''
    child_attr = 'child'
    with_cache = getattr(settings, 'SERIALIZER_CACHE', True)

    def get_child(self):
        return getattr(self, self.child_attr)
    
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

        return [self.get_child().to_internal_value(item) for item in data]
    
    def filter_queryset(self, queryset, child_model):
        '''Applies the permission of the child model to the child queryset'''
        view = copy(self.context['view'])
        view.model = child_model
        filter_backends = list({perm_class().get_filter_backend(child_model) for perm_class in 
                getattr(child_model._meta, 'permission_classes', []) if hasattr(perm_class(), 'get_filter_backend')})
        for backend in filter_backends:
            if backend:
                queryset = backend().filter_queryset(self.context['request'], queryset, view)
        return queryset
    
    def compute_id(self, value):
        '''generates the @id of the container'''
        if not hasattr(self, 'parent_instance'):
            #This is a container
            return f"{settings.BASE_URL}{self.context['request'].path}"
        return f"{settings.BASE_URL}{Model.resource_id(self.parent_instance)}{self.field_name}/"
    
    def get_attribute(self, instance):
        # save the parent object for nested field url
        self.parent_instance = instance
        return super().get_attribute(instance)

    def check_cache(self, value, id, model, cache_vary):
        '''Auxiliary function to avoid code duplication - checks cache and returns from it if it has entry'''
        parent_meta = getattr(self.get_child(), 'Meta', getattr(self.parent, 'Meta', None))
        depth = max(getattr(parent_meta, "depth", 0), 0) if parent_meta else 1
        
        if depth:
            # if the depth is greater than 0, we don't hit the cache, because a nested container might be outdated
            # this Mixin may not have access to the depth of the parent serializer, e.g. if it's a ManyRelatedField
            # in these cases we assume the depth is 0 and so we hit the cache
            return None
        cache_key = getattr(model._meta, 'label', None)

        if self.with_cache and GLOBAL_SERIALIZER_CACHE.has(cache_key, id, cache_vary):
            cache_value = GLOBAL_SERIALIZER_CACHE.get(cache_key, id, cache_vary)
            # this check is to handle the situation where the cache has been invalidated by something we don't check
            # namely if my permissions are upgraded then I may have access to view more objects
            cache_under_value = cache_value['ldp:contains'] if 'ldp:contains' in cache_value else cache_value
            if not hasattr(cache_under_value, '__len__') or not hasattr(value, '__len__') or (len(cache_under_value) == len(value)):
                return cache_value
        return False

    def to_representation(self, value):
        '''
        Converts internal representation to primitive data representation
        Filters objects out which I don't have permission to view
        Permission on container :
         - Can Add if add permission on contained object's type
         - Can view the container is view permission on container model : container obj are filtered by view permission
        '''
        try:
            child_model = self.get_child().Meta.model
        except AttributeError:
            child_model = value.model
        user = self.context['request'].user
        id = self.compute_id(value)
        
        is_container = True
        if getattr(self, 'parent', None): #If we're in a nested container
            if isinstance(value, QuerySet) and getattr(self, 'parent', None):
                value = self.filter_queryset(value, child_model)

            if getattr(self, 'field_name', None) is not None:
                if self.field_name in getattr(self.parent.Meta.model._meta, 'empty_containers', []):
                    return {'@id': id}
                if not self.field_name in getattr(self.parent.Meta.model._meta, 'nested_fields', []):
                    is_container = False

        cache_vary = str(user)
        cache_result = self.check_cache(value, id, child_model, cache_vary)
        if cache_result:
            return cache_result
        
        data = super().to_representation(value)
        if is_container:
            data = self.serialize_container(data, id, user, child_model)

        GLOBAL_SERIALIZER_CACHE.set(getattr(child_model._meta, 'label'), id, cache_vary, data)
        return GLOBAL_SERIALIZER_CACHE.get(getattr(child_model._meta, 'label'), id, cache_vary)

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

class IdentityFieldMixin:
    def to_internal_value(self, data):
        '''Gives the @id as a representation if present'''
        try:
            return super().to_internal_value(data[self.parent.url_field_name])
        except (KeyError, TypeError):
            return super().to_internal_value(data)

class ContainerSerializer(LDListMixin, ListSerializer, IdentityFieldMixin):
    id = ''

    @property
    def data(self):
        return ReturnDict(super(ListSerializer, self).data, serializer=self)


class ManyJsonLdRelatedField(LDListMixin, ManyRelatedField):
    child_attr = 'child_relation'
    url_field_name = "@id"


class JsonLdField(HyperlinkedRelatedField, IdentityFieldMixin):
    def __init__(self, view_name=None, **kwargs):
        super().__init__(view_name, **kwargs)
        self.get_lookup_args()

    def get_url(self, obj, view_name, request, format):
        '''Overridden from DRF to shortcut on urlid-holding objects'''
        if hasattr(obj, 'urlid') and obj.urlid not in (None, ''):
            return obj.urlid
        return super().get_url(obj, view_name, request, format)

    def get_lookup_args(self):
        try:
            lookup_field = get_resolver().reverse_dict[self.view_name][0][0][1][0]
            self.lookup_field = lookup_field
            self.lookup_url_kwarg = lookup_field
        except MultiValueDictKeyError:
            pass

class JsonLdRelatedField(JsonLdField, RDFSerializerMixin):
    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        try:
            include_context = False
            if Model.is_external(value):
                data = {'@id': value.urlid}
            else:
                include_context = True
                data = {'@id': super().to_representation(value)}
            return self.serialize_rdf_fields(value, data, include_context=include_context)
        except ImproperlyConfigured:
            return value.pk

    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs),}
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

    def to_representation(self, value: Any) -> Any:
        '''returns hyperlink representation of identity field'''
        try:
            # we already have a url to return
            if isinstance(value, str):
                return Hyperlink(value, value)
            # expecting a user instance. Compute the webid and return this in hyperlink format
            else:
                return Hyperlink(value.urlid, value)
        except AttributeError:
            return super().to_representation(value)

    def get_attribute(self, instance):
        if Model.is_external(instance):
            return instance.urlid
        else:
            # runs DRF's RelatedField.get_attribute
            # returns the pk only if optimised or the instance itself in the standard case
            return super().get_attribute(instance)


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

        data = self.serialize_rdf_fields(obj, data, include_context=True)
        data = self.add_permissions(data, self.context['request'].user, type(obj), obj=obj)
        return data

    def build_property_field(self, field_name, model_class):
        class JSonLDPropertyField(ReadOnlyField):
            def to_representation(self, instance):
                from djangoldp.views import LDPViewSet
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
        #TODO: This hack is needed because external users don't pass validation.
        # Objects require all fields to be optional to be created as external, and username is required.
        is_user_and_external = self.Meta.model is get_user_model() and '@id' in data and Model.is_external(data['@id'])
        if is_user_and_external:
            data['username'] = 'external'
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
                one_to_one[field_name] = validated_data[field_name]
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
                    #First remove to avoid duplicates
                    manager.remove(saved_item)
                    manager.add(saved_item)

    def get_or_create(self, field_model, item, kwargs):
        try:
            old_obj = field_model.objects.get(**kwargs)
            saved_item = self.update(instance=old_obj, validated_data=item)
        except field_model.DoesNotExist:
            saved_item = self.internal_create(validated_data=item, model=field_model)
        return saved_item
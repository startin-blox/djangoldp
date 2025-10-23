from copy import copy

from django.conf import settings
from django.db.models import QuerySet
from rest_framework.fields import empty

from djangoldp.models import Model
from djangoldp.permissions import DEFAULT_DJANGOLDP_PERMISSIONS
from .cache import GLOBAL_SERIALIZER_CACHE


class RDFSerializerMixin:
    def add_permissions(self, data, user, model, obj=None):
        '''takes a set or list of permissions and returns them in the JSON-LD format'''
        if self.parent and not settings.LDP_INCLUDE_INNER_PERMS:  # Don't serialize permissions on nested objects
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
            # This is a container
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
        if getattr(self, 'parent', None):  # If we're in a nested container
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

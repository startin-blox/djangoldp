from copy import copy
from django.conf import settings
from django.http import Http404
from rest_framework.permissions import BasePermission, DjangoObjectPermissions, OR, AND
from rest_framework.filters import BaseFilterBackend
from rest_framework_guardian.filters import ObjectPermissionsFilter
from djangoldp.filters import OwnerFilterBackend, NoFilterBackend, PublicFilterBackend
from djangoldp.utils import is_anonymous_user, is_authenticated_user

DEFAULT_DJANGOLDP_PERMISSIONS = {'view', 'add', 'change', 'delete', 'control'}
DEFAULT_RESOURCE_PERMISSIONS = {'view', 'change', 'delete', 'control'}
DEFAULT_CONTAINER_PERMISSIONS = {'view', 'add'}

def join_filter_backends(*permissions_or_filters:BaseFilterBackend|BasePermission, model:object, union:bool=False) -> BaseFilterBackend:
    '''Creates a new Filter backend by joining a list of existing backends.
    It chains the filterings or joins them, depending on the argument union'''
    backends = []
    for permission_or_filter in permissions_or_filters:
        if hasattr(permission_or_filter, 'get_filter_backend'):
            backends.append(permission_or_filter.get_filter_backend(model))
        elif isinstance(permission_or_filter, type) and issubclass(permission_or_filter, BaseFilterBackend):
            backends.append(permission_or_filter)
    class JointFilterBackend(BaseFilterBackend):
        def __init__(self) -> None:
            self.filters = []
            for backend in backends:
                if backend:
                    self.filters.append(backend())
        def filter_queryset(self, request:object, queryset:object, view:object) -> object:
            if union:
                result = queryset.none() #starts with empty for union
            else:
                result = queryset
            for filter in self.filters:
                if union:
                    result = result | filter.filter_queryset(request, queryset, view)
                else:
                    result = filter.filter_queryset(request, result, view)
            return result
    return JointFilterBackend

permission_map ={
    'GET': ['%(app_label)s.view_%(model_name)s'],
    'OPTIONS': [],
    'HEAD': ['%(app_label)s.view_%(model_name)s'],
    'POST': ['%(app_label)s.add_%(model_name)s'],
    'PUT': ['%(app_label)s.change_%(model_name)s'],
    'PATCH': ['%(app_label)s.change_%(model_name)s'],
    'DELETE': ['%(app_label)s.delete_%(model_name)s'],
}

# Patch of OR and AND classes to enable chaining of LDPBasePermission
def OR_get_permissions(self, user, model, obj=None):
    perms1 = self.op1.get_permissions(user, model, obj) if hasattr(self.op1, 'get_permissions') else set()
    perms2 = self.op2.get_permissions(user, model, obj) if hasattr(self.op2, 'get_permissions') else set()
    return set.union(perms1, perms2)    
OR.get_permissions = OR_get_permissions
def OR_get_filter_backend(self, model):
    return join_filter_backends(self.op1, self.op2, model=model, union=True)
OR.get_filter_backend = OR_get_filter_backend
OR.__repr__ = lambda self: f"{self.op1}|{self.op2}"

def AND_get_permissions(self, user, model, obj=None):
    perms1 = self.op1.get_permissions(user, model, obj) if hasattr(self.op1, 'get_permissions') else set()
    perms2 = self.op2.get_permissions(user, model, obj) if hasattr(self.op2, 'get_permissions') else set()
    return set.intersection(perms1, perms2)    
AND.get_permissions = AND_get_permissions
def AND_get_filter_backend(self, model):
    return join_filter_backends(self.op1, self.op2, model=model, union=False)
AND.get_filter_backend = AND_get_filter_backend
AND.__repr__ = lambda self: f"{self.op1}&{self.op2}"

class LDPBasePermission(BasePermission):
    """
    A base class from which all permission classes should inherit.
    Extends the DRF permissions class to include the concept of model-permissions, separate from the view, and to
    change to a system of outputting permissions sets for the serialization of WebACLs
    """
    # filter backends associated with the permissions class. This will be used to filter queryset in the (auto-generated)
    # view for a model, and in the serializing nested fields
    filter_backend = NoFilterBackend
    # by default, all permissions
    permissions = getattr(settings, 'DJANGOLDP_PERMISSIONS', DEFAULT_DJANGOLDP_PERMISSIONS)
    # perms_map defines the permissions required for different methods
    perms_map = permission_map

    @classmethod
    def get_filter_backend(cls, model):
        '''returns the Filter backend associated with this permission class'''
        return cls.filter_backend
    def check_all_permissions(self, required_permissions):
        '''returns True if the all the permissions are included in the permissions of the class'''
        return all([permission.split('.')[1].split('_')[0] in self.permissions for permission in required_permissions])
    def get_allowed_methods(self):
        '''returns the list of methods allowed for the permissions of the class, depending on the permission map'''
        return [method for method, permissions in self.perms_map.items() if self.check_all_permissions(permissions)]
    def has_permission(self, request, view):
        '''checks if the request is allowed at all, based on its method and the permissions of the class'''
        return request.method in self.get_allowed_methods()
    def has_object_permission(self, request, view, obj=None):
        '''checks if the access to the object is allowed,'''
        return self.has_permission(request, view)
    def get_permissions(self, user, model, obj=None):
        '''returns the permissions the user has on a given model or on a given object'''
        return self.permissions.intersection(DEFAULT_RESOURCE_PERMISSIONS if obj else DEFAULT_CONTAINER_PERMISSIONS)

class AnonymousReadOnly(LDPBasePermission):
    """Anonymous users can only view, no check for others"""
    permissions = {'view'}
    def has_permission(self, request, view):
        return super().has_permission(request, view) or is_authenticated_user(request.user)
    def get_permissions(self, user, model, obj=None):
        if is_anonymous_user(user):
            return self.permissions
        else:
            return super().permissions #all permissions

class AuthenticatedOnly(LDPBasePermission):
    """Only authenticated users have permissions"""
    def has_permission(self, request, view):
        return request.method=='OPTIONS' or is_authenticated_user(request.user)

class ReadOnly(LDPBasePermission):
    """Users can only view"""
    permissions = {'view'}

class ReadAndCreate(LDPBasePermission):
    """Users can only view and create"""
    permissions = {'view', 'add'}

class CreateOnly(LDPBasePermission):
    """Users can only view and create"""
    permissions = {'add'}

class ACLPermissions(DjangoObjectPermissions, LDPBasePermission):
    """Permissions based on the rights given in db, on model for container requests or on object for resource requests"""
    filter_backend = ObjectPermissionsFilter
    perms_map = permission_map
    def has_permission(self, request, view):
        if view.action in ('list', 'create'): # The container permission only apply to containers requests
            return super().has_permission(request, view)
        return True

    def get_permissions(self, user, model, obj=None):
        model_name = model._meta.model_name
        app_label = model._meta.app_label
        if obj:
            return {perm.replace('_'+model_name, '') for perm in user.get_all_permissions(obj)}

        permissions = set(filter(lambda perm: perm.startswith(app_label) and perm.endswith(model_name), user.get_all_permissions()))
        return {perm.replace(app_label+'.', '').replace('_'+model_name, '') for perm in permissions}

class OwnerPermissions(LDPBasePermission):
    """Gives all permissions to the owner of the object"""
    filter_backend = OwnerFilterBackend
    def check_permission(self, user, model, obj):
        if user.is_superuser:
            return True
        if getattr(model._meta, 'owner_field', None):
            field = model._meta.get_field(model._meta.owner_field)
            if field.many_to_many or field.one_to_many:
                return user in getattr(obj, field.get_accessor_name()).all()
            else:
                return user == getattr(obj, model._meta.owner_field)
        if getattr(model._meta, 'owner_urlid_field', None) is not None:
            return is_authenticated_user(user) and user.urlid == getattr(obj, model._meta.owner_urlid_field)
        return True

    def has_object_permission(self, request, view, obj=None):
        return self.check_permission(request.user, view.model, obj)
    def get_permissions(self, user, model, obj=None):
        if not obj or self.check_permission(user, model, obj):
            return self.permissions
        return set()

class OwnerCreatePermission(LDPBasePermission):
    '''only accepts the creation of new resources if the owner of the created resource is the user of the request'''
    def check_patch(self, first, second, user):
        diff = first - second
        return diff == set() or diff == {user.urlid}

    def has_permission(self, request:object, view:object) -> bool:
        if request.method != 'POST':
            return super().has_permission(request, view)
        if is_anonymous_user(request.user):
            return False
        owner = None
        if getattr(view.model._meta, 'owner_field', None):
            field = view.model._meta.get_field(view.model._meta.owner_field)
            if field.many_to_many or field.one_to_many:
                owner = request.data[field.get_accessor_name()]
            else:
                owner = request.data[view.model._meta.owner_field]
        if getattr(view.model._meta, 'owner_urlid_field', None):
            owner = request.data[view.model._meta.owner_urlid_field]
        return not owner or owner['@id'] == request.user.urlid

class PublicPermission(LDPBasePermission):
    """Gives read-only access to resources which have a public flag to True"""
    filter_backend = PublicFilterBackend
    permissions = {'view', 'add'}
    def has_object_permission(self, request, view, obj=None):
        assert hasattr(view.model._meta, 'public_field'), \
            f'Model {view.model} has PublicPermission applied without "public_field" defined'
        public_field = view.model._meta.public_field

        if getattr(obj, public_field, False):
            return super().has_object_permission(request, view, obj)
        return False

class JoinMembersPermission(LDPBasePermission):
    filter_backend = None
    def has_permission(self, request:object, view:object) -> bool:
        if is_anonymous_user(request.user):
            return False
        return request.method == 'PATCH'

    def check_patch(self, first, second, user):
        diff = first - second
        return diff == set() or diff == {user.urlid}

    def has_object_permission(self, request:object, view:object, obj:object) -> bool:
        '''only accept patch request, only if the only difference on the user_set is the user'''
        if not self.has_permission(request, view) or not obj or not 'user_set' in request.data:
            return False
        new_members = request.data['user_set']
        if not isinstance(new_members, list):
            new_members = [new_members]
        new_ids = {user['@id'] for user in new_members}
        old_ids = {user.urlid for user in obj.members.user_set.all()}
        return self.check_patch(new_ids, old_ids, request.user) and self.check_patch(old_ids, new_ids, request.user)
    
    def get_permissions(self, user, model, obj=None):
        return set()


class InheritPermissions(LDPBasePermission):
    """Gets the permissions from a related objects"""
    @classmethod
    def get_parent_fields(cls, model: object) -> list:
        '''checks that the model is adequately configured and returns the associated model'''
        assert hasattr(model._meta, 'inherit_permissions') and isinstance(model._meta.inherit_permissions, list), \
            f'Model {model} has InheritPermissions applied without "inherit_permissions" defined as a list'

        return model._meta.inherit_permissions

    @classmethod
    def get_parent_model(cls, model:object, field_name:str) -> object:
        parent_model = model._meta.get_field(field_name).related_model
        assert hasattr(parent_model._meta, 'permission_classes'), \
            f'Related model {parent_model} has no "permission_classes" defined'
        return parent_model

    def get_parent_objects(self, obj:object, field_name:str) -> list:
        '''gets the parent object'''
        if obj is None:
            return []
        field = obj._meta.get_field(field_name)
        if field.many_to_many or field.one_to_many:
            return getattr(obj, field.get_accessor_name()).all()
        parent = getattr(obj, field_name, None)
        return [parent] if parent else []
    
    @classmethod
    def clone_with_model(self, request:object, view:object, model:object) -> tuple:
        '''changes the model on the argument, so that they can be called on the parent model'''
        # For some reason if we copy the request itself, we go into an infinite loop, so take the native request instead
        _request = copy(request._request)
        _request.model = model
        _request.data = request.data #because the data is not present on the native request
        _request._request = _request #so that it can be nested
        _view = copy(view)
        _view.queryset = None #to make sure the model is taken into account
        _view.model = model
        return _request, _view

    @classmethod
    def generate_filter_backend(cls, parent:object, field_name:str) -> BaseFilterBackend:
        '''returns a new Filter backend that applies all filters of the parent model'''
        filter_arg = f'{field_name}__in'
        backends = {perm().get_filter_backend(parent) for perm in parent._meta.permission_classes}

        class InheritFilterBackend(BaseFilterBackend):
            def __init__(self) -> None:
                self.filters = []
                for backend in backends:
                    if backend:
                        self.filters.append(backend())
            def filter_queryset(self, request:object, queryset:object, view:object) -> object:
                request, view = InheritPermissions.clone_with_model(request, view, parent)
                for filter in self.filters:
                    allowed_parents = filter.filter_queryset(request, parent.objects.all(), view)
                    queryset = queryset.filter(**{filter_arg: allowed_parents})
                return queryset
        return InheritFilterBackend
    
    @classmethod
    def generate_filter_backend_for_none(cls, fields) -> BaseFilterBackend:
        '''returns a new Filter backend that checks that none of the parent fields are set'''
        class InheritNoneFilterBackend(BaseFilterBackend):
            def filter_queryset(self, request:object, queryset:object, view:object) -> object:
                return queryset.filter(**{field: None for field in fields})
        return InheritNoneFilterBackend

    @classmethod
    def get_filter_backend(cls, model:object) -> BaseFilterBackend:
        '''Returns a union filter backend of all filter backends of parents'''
        fields = cls.get_parent_fields(model)
        backends = [cls.generate_filter_backend(cls.get_parent_model(model, field), field) for field in fields]
        backend_none = cls.generate_filter_backend_for_none(fields)
        return join_filter_backends(*backends, backend_none, model=model, union=True)

    def has_permission(self, request:object, view:object) -> bool:
        '''Returns True unless we're trying to create a resource with a link to a parent we're not allowed to change'''
        if request.method == 'POST':
            for field in InheritPermissions.get_parent_fields(view.model):
                if field in request.data:
                    model = InheritPermissions.get_parent_model(view.model, field)
                    parent = model.objects.get(urlid=request.data[field]['@id'])
                    _request, _view = InheritPermissions.clone_with_model(request, view, model)
                    if not all([perm().has_object_permission(_request, _view, parent) for perm in model._meta.permission_classes]):
                        return False
        return True
    
    def has_object_permission(self, request:object, view:object, obj:object) -> bool:
        '''Returns True if at least one inheriting object has permission'''
        if not obj:
            return super().has_object_permission(request, view, obj)
        parents = []
        for field in InheritPermissions.get_parent_fields(view.model):
            model = InheritPermissions.get_parent_model(view.model, field)
            parent_request, parent_view = InheritPermissions.clone_with_model(request, view, model)
            for parent_object in self.get_parent_objects(obj, field):
                parents.append(parent_object)
                try:
                    if all([perm().has_object_permission(parent_request, parent_view, parent_object) for perm in model._meta.permission_classes]):
                        return True
                except Http404:
                    #keep trying
                    pass
        # return False if there were parent resources but none accepted
        return False if parents else True
    
    def get_permissions(self, user:object, model:object, obj:object=None) -> set:
        '''returns a union of all inheriting linked permissions'''
        perms = set()
        parents = []
        for field in InheritPermissions.get_parent_fields(model):
            parent_model = InheritPermissions.get_parent_model(model, field)
            for parent_object in self.get_parent_objects(obj, field):
                parents.append(parent_object)
                perms = perms.union(set.intersection(*[perm().get_permissions(user, parent_model, parent_object) 
                                               for perm in parent_model._meta.permission_classes]))
        if parents:
            return perms
        return super().get_permissions(user, model, obj)
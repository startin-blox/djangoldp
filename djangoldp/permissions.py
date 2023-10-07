from copy import copy
from django.conf import settings
from django.http import Http404
from rest_framework.permissions import BasePermission, DjangoObjectPermissions, OR, AND
from rest_framework.filters import BaseFilterBackend
from rest_framework_guardian.filters import ObjectPermissionsFilter
from djangoldp.filters import OwnerFilterBackend, NoFilterBackend, PublicFilterBackend
from djangoldp.utils import is_anonymous_user, is_authenticated_user

DEFAULT_DJANGOLDP_PERMISSIONS = {'view', 'add', 'change', 'delete', 'control'}

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

def AND_get_permissions(self, user, model, obj=None):
    perms1 = self.op1.get_permissions(user, model, obj) if hasattr(self.op1, 'get_permissions') else set()
    perms2 = self.op2.get_permissions(user, model, obj) if hasattr(self.op2, 'get_permissions') else set()
    return set.intersection(perms1, perms2)    
AND.get_permissions = AND_get_permissions
def AND_get_filter_backend(self, model):
    return join_filter_backends(self.op1, self.op2, model=model, union=False)
AND.get_filter_backend = AND_get_filter_backend

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
        return self.permissions

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
        return is_authenticated_user(request.user)

class ReadOnly(LDPBasePermission):
    """Users can only view"""
    permissions = {'view'}

class ReadAndCreate(LDPBasePermission):
    """Users can only view and create"""
    permissions = {'view', 'add'}

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
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if getattr(view.model._meta, 'owner_field', None):
            return request.user == getattr(obj, view.model._meta.owner_field)
        if getattr(view.model._meta, 'owner_urlid_field', None) is not None:
            return request.user.urlid == getattr(obj, view.model._meta.owner_urlid_field)
        return True
    def get_permissions(self, request, view, obj=None):
        if not obj or self.has_object_permission(request, view, obj):
            return self.permissions
        return set()

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


class InheritPermissions(LDPBasePermission):
    """Gets the permissions from a related objects"""
    @classmethod
    def get_parent_fields(cls, model: object) -> list:
        '''checks that the model is adequately configured and returns the associated model'''
        assert hasattr(model._meta, 'inherit_permissions'), \
            f'Model {model} has InheritPermissions applied without "inherit_permissions" defined'

        return model._meta.inherit_permissions

    @classmethod
    def get_parent_model(cls, model:object, field_name:str) -> object:
        parent_model = model._meta.get_field(field_name).related_model
        assert hasattr(parent_model._meta, 'permission_classes'), \
            f'Related model {parent_model} has no "permission_classes" defined'
        return parent_model

    def get_parent_object(self, obj:object, field_name:str) -> object|None:
        '''gets the parent object'''
        return getattr(obj, field_name, None)
    
    @classmethod
    def clone_with_model(self, request:object, view:object, model:object) -> tuple:
        '''changes the model on the argument, so that they can be called on the parent model'''
        # For some reason if we copy the request itself, we go into an infinite loop, so take the native request instead
        _request = copy(request._request)
        _request.model = model
        _request.data = request.data #because the data is not present on the native request
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
    def get_filter_backend(cls, model:object) -> BaseFilterBackend:
        '''Returns a union filter backend of all filter backends of parents'''
        backends = [cls.generate_filter_backend(cls.get_parent_model(model, field), field) for field in cls.get_parent_fields(model)]
        return join_filter_backends(*backends, model=model, union=True)

    def has_permission(self, request:object, view:object) -> bool:
        '''Returns True if at least one inheriting link has permission'''
        for field in InheritPermissions.get_parent_fields(view.model):
            model = InheritPermissions.get_parent_model(view.model, field)
            _request, _view = InheritPermissions.clone_with_model(request, view, model)
            if all([perm().has_permission(_request, _view) for perm in model._meta.permission_classes]):
                return True
        return False
    
    def has_object_permission(self, request:object, view:object, obj:object) -> bool:
        '''Returns True if at least one inheriting link has permission'''
        if not obj:
            return super().has_object_permission(request, view, obj)
        for field in InheritPermissions.get_parent_fields(view.model):
            model = InheritPermissions.get_parent_model(view.model, field)
            parent_request, parent_view = InheritPermissions.clone_with_model(request, view, model)
            parent_object = self.get_parent_object(obj, field)
            try:
                if all([perm().has_object_permission(parent_request, parent_view, parent_object) for perm in model._meta.permission_classes]):
                    return True
            except Http404:
                #keep trying
                pass
        return False
    
    def get_permissions(self, user:object, model:object, obj:object=None) -> set:
        '''returns a union of all inheriting linked permissions'''
        perms = set()
        for field in InheritPermissions.get_parent_fields(model):
            parent_model = InheritPermissions.get_parent_model(model, field)
            obj = self.get_parent_object(obj, field)
            perms.union(set.intersection(*[perm().get_permissions(user, parent_model, obj) for perm in parent_model._meta.permission_classes]))
        return perms
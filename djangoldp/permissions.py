from django.conf import settings
from django.contrib.auth import _get_backends
from rest_framework.permissions import DjangoObjectPermissions
from djangoldp.utils import is_anonymous_user
from djangoldp.filters import LDPPermissionsFilterBackend


DEFAULT_DJANGOLDP_PERMISSIONS = ['add', 'change', 'delete', 'view', 'control']


class LDPBasePermission(DjangoObjectPermissions):
    """
    A base class from which all permission classes should inherit.
    Extends the DRF permissions class to include the concept of model-permissions, separate from the view, and to
    change to a system of outputting permissions sets for the serialization of WebACLs
    """
    # filter backends associated with the permissions class. This will be used to filter queryset in the (auto-generated)
    # view for a model, and in the serializing nested fields
    filter_backends = []
    # perms_map defines the permissions required for different methods
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_container_permissions(self, request, view, obj=None):
        """
        outputs a set of permissions of a given container. Used in the generation of WebACLs in LDPSerializer
        """
        return set()

    def get_object_permissions(self, request, view, obj):
        """
        outputs the permissions of a given object instance. Used in the generation of WebACLs in LDPSerializer
        """
        return set()

    def get_user_permissions(self, request, view, obj):
        '''
        returns a set of all model permissions and object permissions for given parameters
        You shouldn't override this function
        '''
        perms = self.get_container_permissions(request, view, obj)
        if obj is not None:
            return perms.union(self.get_object_permissions(request, view, obj))
        return perms

    def has_permission(self, request, view):
        """concerned with the permissions to access the _view_"""
        return True

    def has_container_permission(self, request, view):
        """
        concerned with the permissions to access the _model_
        in most situations you won't need to override this. It is primarily called by has_object_permission
        checked when POSTing to LDPViewSet
        """
        required_perms = self.get_required_permissions(request.method, view.model)
        return self.compare_permissions(required_perms, self.get_container_permissions(request, view))

    def has_object_permission(self, request, view, obj):
        """concerned with the permissions to access the _object_"""
        required_perms = self.get_required_permissions(request.method, view.model)
        return self.compare_permissions(required_perms, self.get_user_permissions(request, view, obj))

    def compare_permissions(self, required_perms, user_perms):
        '''returns True if all user_perms are in required_perms'''
        for perm in required_perms:
            if not perm.split('.')[-1].split('_')[0] in user_perms:
                return False
        return True

def select_container_permissions(request, obj, model, anonymous_perms, authenticated_perms, owner_perms, superuser_perms):
    from djangoldp.models import Model
    
    if is_anonymous_user(request.user):
        return set(anonymous_perms)
    else:
        if obj is not None and Model.is_owner(model, request.user, obj):
            perms = set(owner_perms)
        else:
            perms = set(authenticated_perms)
        if request.user.is_superuser:
            perms = perms.union(set(superuser_perms))
    return perms

class ModelConfiguredPermissions(LDPBasePermission):
    # *DEFAULT* model-level permissions for anon, auth and owner statuses
    anonymous_perms = ['view']
    authenticated_perms = ['inherit']
    owner_perms = ['inherit']
    # superuser has all permissions by default
    superuser_perms = getattr(settings, 'DEFAULT_SUPERUSER_PERMS', DEFAULT_DJANGOLDP_PERMISSIONS)

    def get_container_permissions(self, request, view, obj=None):
        '''analyses the Model's set anonymous, authenticated and owner_permissions and returns these'''
        perms = super().get_container_permissions(request, view, obj=obj)
        from djangoldp.models import Model
        if isinstance(view.model, Model):
            anonymous_perms, authenticated_perms, owner_perms, superuser_perms = view.model.get_permission_settings()
        else:
            anonymous_perms, authenticated_perms, owner_perms, superuser_perms = Model.get_permission_settings(view.model)
        return select_container_permissions(request, obj, view.model, anonymous_perms, authenticated_perms, owner_perms, superuser_perms)

    def has_permission(self, request, view):
        """concerned with the permissions to access the _view_"""
        if is_anonymous_user(request.user):
            if not self.has_container_permission(request, view):
                return False
        return True


class LDPObjectLevelPermissions(LDPBasePermission):
    def get_all_user_object_permissions(self, user, obj):
        return user.get_all_permissions(obj)


    def get_object_permissions(self, request, view, obj):
        '''overridden to append permissions from all backends given to the user (e.g. Groups and object-level perms)'''
        from djangoldp.models import Model

        model_name = Model.get_meta(view.model, 'model_name')

        perms = super().get_object_permissions(request, view, obj)

        if obj is not None and not is_anonymous_user(request.user):
            forbidden_string = "_" + model_name
            return perms.union(set([p.replace(forbidden_string, '') for p in
                                    self.get_all_user_object_permissions(request.user, obj)]))

        return perms


class SuperUserPermission(LDPBasePermission):
    filter_backends = []

    def get_container_permissions(self, request, view, obj=None):
        if request.user.is_superuser:
            return set(DEFAULT_DJANGOLDP_PERMISSIONS)
        return super().get_container_permissions(request, view, obj)

    def get_object_permissions(self, request, view, obj):
        if request.user.is_superuser:
            return set(DEFAULT_DJANGOLDP_PERMISSIONS)
        return super().get_object_permissions(request, view, obj)

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return super().has_permission(request, view)

    def has_container_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return super().has_container_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return super().has_object_permission(request, view, obj)


class LDPPermissions(LDPObjectLevelPermissions, ModelConfiguredPermissions):
    filter_backends = [LDPPermissionsFilterBackend]

    def get_all_user_object_permissions(self, user, obj):
        # if the super_user perms are no different from authenticated_perms, then we want to skip Django's auth backend
        restore_super = False
        if user.is_superuser:
            user.is_superuser = False
            restore_super = True

        perms = super().get_all_user_object_permissions(user, obj)

        user.is_superuser = restore_super
        return perms

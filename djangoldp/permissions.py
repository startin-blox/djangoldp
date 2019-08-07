from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied


class LDPPermissions(BasePermission):
    """
        Default permissions
        Anon: None
        Auth: None but herit from Anon
        Ownr: None but herit from Auth
    """
    anonymous_perms = ['view']
    authenticated_perms = ['inherit']
    owner_perms = ['inherit']

    def user_permissions(self, user, model, obj=None):
        """
            Filter user permissions for a model class
        """
        # Get Anonymous permissions from Model's Meta. If not found use default
        anonymous_perms = getattr(model._meta, 'anonymous_perms', self.anonymous_perms)

        # Get Auth permissions from Model's Meta. If not found use default
        authenticated_perms = getattr(model._meta, 'authenticated_perms', self.authenticated_perms)
        # Extend Auth if inherit is given
        if 'inherit' in authenticated_perms:
            authenticated_perms = authenticated_perms + list(set(anonymous_perms) - set(authenticated_perms))

        # Get Owner permissions from Model's Meta. If not found use default
        owner_perms = getattr(model._meta, 'owner_perms', self.owner_perms)
        # Extend Owner if inherit is given
        if 'inherit' in owner_perms:
            owner_perms = owner_perms + list(set(authenticated_perms) - set(owner_perms))

        if user.is_anonymous():
            return anonymous_perms

        else:
            if obj and hasattr(model._meta, 'owner_field') and getattr(obj, getattr(model._meta, 'owner_field')) == user:
                return owner_perms

            else:
                return authenticated_perms

    def filter_user_perms(self, user_or_group, obj, permissions):
        # Only used on Model.get_permissions to translate permissions to LDP
        return [perm for perm in permissions if perm in self.user_permissions(user_or_group, obj)]


    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_permissions(self, method, obj):
        """
            Translate perms_map to request
        """
        kwargs = {
            'app_label': obj._meta.app_label,
            'model_name': obj._meta.model_name
        }

        # Only allows methods that are on perms_map
        if method not in self.perms_map:
            raise PermissionDenied

        return [perm % kwargs for perm in self.perms_map[method]]

    def has_permission(self, request, view):
        """
            Access to containers
        """
        model = view.model
        perms = self.get_permissions(request.method, model)
        try:
            obj = view.model.resolve_id(request._request.path)
        except:
            obj = None

        for perm in perms:
            if not perm.split('.')[1].split('_')[0] in self.user_permissions(request.user, model, obj):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        """
            Access to objects
            User have permission on request: Continue
            User does not have permission:   403
        """
        perms = self.get_permissions(request.method, obj)
        model = obj

        for perm in perms:
            if not perm.split('.')[1].split('_')[0] in self.user_permissions(request.user, model, obj):
                return False

        return True

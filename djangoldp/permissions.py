import time
from django.conf import settings
from django.contrib.auth.models import _user_get_all_permissions
from django.core.exceptions import PermissionDenied
from django.db.models.base import ModelBase
from rest_framework.permissions import DjangoObjectPermissions
from djangoldp.filters import LDPPermissionsFilterBackend


class LDPPermissions(DjangoObjectPermissions):
    # *DEFAULT* permissions for anon, auth and owner statuses
    anonymous_perms = ['view']
    authenticated_perms = ['inherit']
    owner_perms = ['inherit']
    # filter backends associated with the permissions class. This will be used to filter queryset in the (auto-generated)
    # view for a model, and in the serializing nested fields
    filter_backends = [LDPPermissionsFilterBackend]

    perms_cache = {
        'time': time.time()
    }
    with_cache = getattr(settings, 'PERMISSIONS_CACHE', True)

    @classmethod
    def invalidate_cache(cls):
        cls.perms_cache = {
            'time': time.time()
        }

    @classmethod
    def refresh_cache(cls):
        if (time.time() - cls.perms_cache['time']) > 5:
            cls.invalidate_cache()

    @classmethod
    def is_owner(cls, user, model, obj):
        return obj and hasattr(model._meta, 'owner_field') and (
                getattr(obj, getattr(model._meta, 'owner_field')) == user
                or (hasattr(user, 'urlid') and getattr(obj, getattr(model._meta, 'owner_field')) == user.urlid)
                or getattr(obj, getattr(model._meta, 'owner_field')) == user.id)

    def _get_cache_key(self, model_name, user, obj):
        user_key = 'None' if user is None else user.id
        obj_key = 'None' if obj is None else obj.id
        return 'User{}{}{}'.format(user_key, model_name, obj_key)

    @classmethod
    def get_model_level_perms(cls, model, user, obj=None):
        '''Auxiliary function returns the model-level anon-auth-owner permissions for a given, model, user and object'''
        anonymous_perms = getattr(model._meta, 'anonymous_perms', cls.anonymous_perms)
        authenticated_perms = getattr(model._meta, 'authenticated_perms', cls.authenticated_perms)
        owner_perms = getattr(model._meta, 'owner_perms', cls.owner_perms)

        # 'inherit' permissions means inherit the permissions from the next level 'down'
        if 'inherit' in authenticated_perms:
            authenticated_perms = authenticated_perms + list(set(anonymous_perms) - set(authenticated_perms))
        if 'inherit' in owner_perms:
            owner_perms = owner_perms + list(set(authenticated_perms) - set(owner_perms))

        # apply user permissions and return
        perms = set()
        if user.is_anonymous:
            perms = perms.union(set(anonymous_perms))
        else:
            if cls.is_owner(user, model, obj):
                perms = perms.union(set(owner_perms))
            else:
                perms = perms.union(set(authenticated_perms))
        return perms

    def user_permissions(self, user, obj_or_model, obj=None):
        """
            Filter user permissions for a model class
        """
        self.refresh_cache()
        # this may be a permission for the model class, or an instance
        if isinstance(obj_or_model, ModelBase):
            model = obj_or_model
        else:
            obj = obj_or_model
            model = obj_or_model.__class__
        model_name = model._meta.model_name

        perms_cache_key = self.cache_key(model, obj, user)
        if self.with_cache and perms_cache_key in self.perms_cache:
            return self.perms_cache[perms_cache_key]

        # return permissions - using set to avoid duplicates
        perms = self.get_model_level_perms(model, user, obj)

        if obj is not None and not user.is_anonymous:
            # get permissions from all backends and then remove model name from the permissions
            forbidden_string = "_" + model_name
            perms = perms.union(set([p.replace(forbidden_string, '') for p in _user_get_all_permissions(user, obj)]))

        self.perms_cache[perms_cache_key] = list(perms)

        return self.perms_cache[perms_cache_key]

    def cache_key(self, model, obj, user):
        model_name = model._meta.model_name
        user_key = 'None' if user is None else user.id
        obj_key = 'None' if obj is None else obj.id
        perms_cache_key = 'User{}{}{}'.format(user_key, model_name, obj_key)
        return perms_cache_key

    def filter_user_perms(self, context, obj_or_model, permissions):
        # Only used on Model.get_permissions to translate permissions to LDP
        return [perm for perm in permissions if perm in self.user_permissions(context['request'].user, obj_or_model)]

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

    @classmethod
    def get_permissions(cls, method, obj):
        """
            Translate perms_map to request
        """
        kwargs = {
            'app_label': obj._meta.app_label,
            'model_name': obj._meta.model_name
        }

        # Only allows methods that are on perms_map
        if method not in cls.perms_map:
            raise PermissionDenied

        return [perm % kwargs for perm in cls.perms_map[method]]

    def has_permission(self, request, view):
        """
            Access to containers
        """
        from djangoldp.models import Model

        if self.is_a_container(request._request.path):
            try:
                obj = Model.resolve_parent(request.path)
                model = view.parent_model
            except:
                obj = None
                model = view.model
        else:
            obj = Model.resolve_id(request._request.path)
            model = view.model

        # get permissions required
        perms = LDPPermissions.get_permissions(request.method, model)
        user_perms = self.user_permissions(request.user, model, obj)

        # compare them with the permissions I have
        for perm in perms:
            if not perm.split('.')[-1].split('_')[0] in user_perms:
                return False

        return True

    def is_a_container(self, path):
        from djangoldp.models import Model
        container, id = Model.resolve(path)
        return id is None

    def has_object_permission(self, request, view, obj):
        """
            Access to objects
            User have permission on request: Continue
            User does not have permission:   403
        """
        # get permissions required
        perms = LDPPermissions.get_permissions(request.method, obj)
        model = obj
        user_perms = self.user_permissions(request.user, model, obj)

        return LDPPermissions.compare_permissions(perms, user_perms)

    @classmethod
    def has_model_view_permission(cls, request, model):
        '''
        shortcut to compare the requested user's permissions on the model-level
        :return: True or False
        '''
        # compare required permissions with those I have (on the model)
        perms = LDPPermissions.get_permissions('GET', model)
        user_perms = LDPPermissions.get_model_level_perms(model, request.user)
        return cls.compare_permissions(perms, user_perms)

    @classmethod
    def compare_permissions(self, perms, user_perms):
        # compare them with the permissions I have
        for perm in perms:
            if not perm.split('.')[-1].split('_')[0] in user_perms:
                return False
        return True

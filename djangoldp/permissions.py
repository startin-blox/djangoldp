import time
from django.conf import settings
from django.contrib.auth.models import _user_get_all_permissions
from django.core.exceptions import PermissionDenied
from django.db.models.base import ModelBase
from rest_framework.permissions import DjangoObjectPermissions


class LDPPermissions(DjangoObjectPermissions):
    """
        Default permissions
        Anon: None
        Auth: None but inherit from Anon
        Owner: None but inherit from Auth
    """
    anonymous_perms = ['view']
    authenticated_perms = ['inherit']
    owner_perms = ['inherit']

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

        perms_cache_key = self.cache_key(model, obj, user)
        if self.with_cache and perms_cache_key in self.perms_cache:
            return self.perms_cache[perms_cache_key]

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

        # return permissions - using set to avoid duplicates
        # apply Django-Guardian (object-level) permissions
        perms = set()

        if obj is not None and not user.is_anonymous:
            # get permissions from all backends and then remove model name from the permissions
            model_name = model._meta.model_name
            forbidden_string = "_" + model_name
            perms = set([p.replace(forbidden_string, '') for p in _user_get_all_permissions(user, obj)])

        # apply anon, owner and auth permissions
        if user.is_anonymous:
            perms = perms.union(set(anonymous_perms))

        else:
            if obj and hasattr(model._meta, 'owner_field') and (
                    getattr(obj, getattr(model._meta, 'owner_field')) == user
                    or (hasattr(user, 'urlid') and getattr(obj, getattr(model._meta, 'owner_field')) == user.urlid)
                    or getattr(obj, getattr(model._meta, 'owner_field')) == user.id):
                perms = perms.union(set(owner_perms))

            else:
                perms = perms.union(set(authenticated_perms))

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
        perms = self.get_permissions(request.method, model)
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
        perms = self.get_permissions(request.method, obj)
        model = obj
        user_perms = self.user_permissions(request.user, model, obj)

        # compare them with the permissions I have
        for perm in perms:
            if not perm.split('.')[-1].split('_')[0] in user_perms:
                return False

        return True

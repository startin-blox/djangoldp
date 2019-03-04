from rest_framework import permissions
from rest_framework import filters
from guardian.shortcuts import get_objects_for_user

"""
Liste des actions passées dans views selon le protocole REST :
    list
    create
    retrieve
    update, partial update
    destroy
Pour chacune de ces actions, on va définir si on accepte la requête (True) ou non (False)
"""
"""
    The instance-level has_object_permission method will only be called if the view-level has_permission 
    checks have already passed
"""

class WACPermissions(permissions.DjangoObjectPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    # All LDP permissions must extnd WACPermissions. Otherwise there
    # will be problems when view is nons.

    def has_permission(self, request, view):
        if request.method == 'OPTIONS':
            return True
        elif view:
            return super().has_permission(request, view)
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if view:
            return super().has_object_permission(request, view, obj)
        else:
            return False


class ObjectFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
            Ensure that queryset only contains objects visible by current user
        """
        perm = "view_{}".format(queryset.model._meta.model_name.lower())
        objects = get_objects_for_user(request.user, perm, klass=queryset)
        return objects

class ObjectPermission(WACPermissions):
    filter_class = ObjectFilter

class InboxPermissions(WACPermissions):
    """
        Anonymous users: can create notifications but can't read
        Logged in users: can create notifications but can't read
        Inbox owners: can read + update all notifications
    """
    filter_class = ObjectFilter
    def has_permission(self, request, view):
        if view.action in ['create', 'retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if view.action == "create":
            return True
        if hasattr(obj._meta, 'auto_author'):
            if request.user == getattr(obj, obj._meta.auto_author):
                return True
        return super().has_object_permission(request, view)

class AnonymousReadOnly(WACPermissions):
    """
        Anonymous users: can read all posts
        Logged in users: can read all posts + create new posts
        Author: can read all posts + create new posts + update their own
    """
    def has_permission(self, request, view):
        if request.method == "GET":
            return True
        else:
            return super().has_permission(request, view)
        return False

    def has_object_permission(self, request, view, obj):
        if request.method == "GET":
            return True
        elif request.method == "POST" and request.user.is_authenticated():
            return True
        elif request.method in ('PUT', 'PATCH'):
            if hasattr(obj._meta, 'auto_author'):
                author = getattr(obj, obj._meta.auto_author)
                if author == request.user:
                    return True
        return False
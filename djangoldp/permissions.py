from rest_framework import permissions

"""
Liste des actions passées dans views selon le protocole REST :
    list
    create
    retrieve
    update, partial update
    destroy
Pour chacune de ces actions, on va définir si on accepte la requête (True) ou non (False)
"""


class PublicPostPermissions(permissions.BasePermission):
    """
        Anonymous users: can read all posts
        Logged in users: can read all posts + create new posts
        Author: can read all posts + create new posts + update their own
    """
    def has_permission(self, request, view):

        if view.action == "list":
            return True

        if not request.user.is_authenticated():
            return False
        elif view.action == 'create':
            return True
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):

        if view.action == "create":
            return True

        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            if hasattr(obj._meta, 'auto_author'):
                auth = getattr(obj, obj._meta.auto_author)
                if auth == request.user:
                    return True
        else:
            return False


class PrivateProjectPermissions(permissions.BasePermission):
    """
        Anonymous users: no permissions
        Logged in users: can read projects if they're in the team
        Users of group Partners: can see all projects + update all projects
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated():
            return False
        if view.action == "list":
            return True
        elif view.action == 'create':
            return True
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):

        if view.action in ['retrieve']:
            # Is user in the team ?
            for t in obj.team.all():
                if request.user == t:
                    return True

        elif view.action in ['update', 'partial_update', 'destroy']:
            if request.user.groups.filter(name='Partners').exists():
                return True

        return False


class NotificationsPermissions(permissions.BasePermission):
    """
        Anonymous users: can create notifications but can't read
        Logged in users: can create notifications but can't read
        Inbox owners: can read + update all notifications
    """

    def has_permission(self, request, view):

        if view.action == "list":
            return False
        elif view.action == 'create':
            return True
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):

        if view.action in ["retrieve", 'update', 'partial_update', 'destroy']:
            if hasattr(obj._meta, 'auto_author'):
                auth = getattr(obj, obj._meta.auto_author)
                if auth == request.user:
                    return True
            else:
                return False

        if view.action == "create":
            if request.user == "AnonymousUser" or request.user.is_authenticated():
                return True


from djangoldp.filters import BaseFilterBackend
from djangoldp.permissions import LDPBasePermission

class StartsWithAFilter(BaseFilterBackend):
    """Only objects whose title starts in A get through"""
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(title__startswith='A')

class ReadOnlyStartsWithA(LDPBasePermission):
    """Only gives read-only access and only to objects which title starts with A"""
    filter_backend = StartsWithAFilter
    permissions = {'view', 'list'}
    def check_perms(self, obj):
        return getattr(obj, 'title', '').startswith('A')
    def has_object_permission(self, request, view, obj=None):
        return self.check_perms(obj)
    def get_permissions(self, user, model, obj=None):
        return self.permissions if self.check_perms(obj) else set()


class ContainsSpace(BaseFilterBackend):
    """Only objects whose title contains a space get through"""
    def filter_queryset(self, request, queryset, view):
        if request.user.username != 'toto':
            return queryset.none()
        return queryset.filter(title__contains=' ')

class Only2WordsForToto(LDPBasePermission):
    """Only gives access if the user's username is toto and only to objects whose title has two words (contains space)"""
    filter_backend = ContainsSpace
    def has_permission(self, request, view):
        return request.user.username == 'toto'
    def check_perms(self, obj):
        return ' ' in getattr(obj, 'title', '')
    def has_object_permission(self, request, view, obj=None):
        return self.check_perms(obj)
    def get_permissions(self, user, model, obj=None):
        return self.permissions if self.check_perms(obj) else set()
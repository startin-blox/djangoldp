from django.db.models import QuerySet
from django.db.models.base import ModelBase

from djangoldp.permissions import LDPPermissions


class HalfRandomPermissions(LDPPermissions):

    def prefilter_query_set(self, query_set: QuerySet, request, view, model) -> QuerySet:
        if request.user.is_anonymous:
            return query_set.filter(pk__in=[2, 4, 6, 8])
        else:
            return super().prefilter_query_set(query_set, request, view, model)

    def user_permissions(self, user, obj_or_model, obj=None):
        if isinstance(obj_or_model, ModelBase):
            model = obj_or_model
        else:
            obj = obj_or_model
            model = obj_or_model.__class__

        # perms_cache_key = self.cache_key(model, obj, user)
        # if self.with_cache and perms_cache_key in self.perms_cache:
        #     return self.perms_cache[perms_cache_key]

        # start with the permissions set on the object and model
        perms = set(super().user_permissions(user, obj_or_model, obj))

        if obj is not None and not isinstance(obj, ModelBase) and user.is_anonymous:
            if obj.pk % 2 == 0:
                return ['add', 'view']
            else:
                return []
        else:
            return ['view']

from django.conf import settings
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend
from rest_framework_guardian.filters import ObjectPermissionsFilter
from djangoldp.utils import is_anonymous_user


class LDPPermissionsFilterBackend(ObjectPermissionsFilter):
    """
    Default FilterBackend for LDPPermissions. If user does not have model-level permissions, filters by
    Django-Guardian's get_objects_for_user
    """

    def filter_queryset(self, request, queryset, view):
        from djangoldp.models import Model
        from djangoldp.permissions import LDPPermissions, ModelConfiguredPermissions

        # compares the requirement for GET, with what the user has on the container
        configured_permission_classes = getattr(view.model._meta, 'permission_classes', [LDPPermissions])
        for permission_class in [p() for p in configured_permission_classes]:
            # inherits from LDPBasePermissions
            if hasattr(permission_class, 'has_container_permission') and \
                permission_class.has_container_permission(request, view):
                return queryset

        # the user did not have permission on the container, so now we filter the queryset for permissions on the object
        if not is_anonymous_user(request.user):
            # those objects I have by grace of group or object
            # first figure out if the superuser has special permissions (important to the implementation in superclass)
            from djangoldp.models import Model
            anon_perms, auth_perms, owner_perms, superuser_perms = Model.get_permission_settings(view.model)
            #if no view permission for superuser, set the shortcut to False
            self.shortcut_kwargs['with_superuser'] = ('view' in superuser_perms)
            filtered_queryset = super().filter_queryset(request, queryset, view)

            # those objects I have by grace of being owner
            if 'view' in owner_perms:
                if getattr(view.model._meta, 'owner_field', None) is not None:
                    return (filtered_queryset | queryset.filter(**{view.model._meta.owner_field: request.user})).distinct()
                if getattr(view.model._meta, 'owner_urlid_field', None) is not None:
                    return (filtered_queryset | queryset.filter(**{view.model._meta.owner_urlid_field: request.user.urlid})).distinct()
            return filtered_queryset

        # user is anonymous without anonymous permissions
        return view.model.objects.none()


class LocalObjectFilterBackend(BaseFilterBackend):
    """
    Filter which removes external objects (federated backlinks) from the queryset
    For querysets which should only include local objects
    """
    def filter_queryset(self, request, queryset, view):
        return queryset.filter(urlid__startswith=settings.SITE_URL)


class LocalObjectOnContainerPathBackend(LocalObjectFilterBackend):
    """
    Override of LocalObjectFilterBackend which removes external objects when the view requested
    is the model container path
    """
    def filter_queryset(self, request, queryset, view):
        from djangoldp.models import Model

        if issubclass(view.model, Model) and request.path_info == view.model.get_container_path():
            return super(LocalObjectOnContainerPathBackend, self).filter_queryset(request, queryset, view)
        return queryset


class SearchByQueryParamFilterBackend(BaseFilterBackend):
    """
    Applies search fields in the request query params to the queryset
    """
    def filter_queryset(self, request, queryset, view):

        # the model fields on which to perform the search
        search_fields = request.GET.get('search-fields', None)
        # the terms to search the fields for
        search_terms = request.GET.get('search-terms', None)
        # the method of search to apply to the model fields
        search_method = request.GET.get('search-method', "basic")
        # union or intersection
        search_policy = request.GET.get('search-policy', 'union')

        # check if there is indeed a search requested
        if search_fields is None or search_terms is None:
            return queryset

        def _construct_search_query(search):
            '''Utility function pipes many Django Query objects'''
            search_query = []

            for idx, s in enumerate(search):
                if idx > 0:

                    # the user has indicated to make a union of all query results
                    if search_policy == "union":
                        search_query = search_query | Q(**s)

                    # the user has indicated to make an intersection of all query results
                    else:
                        search_query = search_query & Q(**s)

                    continue

                search_query = Q(**s)

            return search_query

        search_fields = search_fields.split(',')

        if search_method == "basic":
            search = []

            for s in search_fields:
                query = {}
                query["{}__contains".format(s)] = search_terms
                search.append(query)

            queryset = queryset.filter(_construct_search_query(search))

        elif search_method == "ibasic":
            # NOTE: to use, see https://stackoverflow.com/questions/54071944/fielderror-unsupported-lookup-unaccent-for-charfield-or-join-on-the-field-not
            unaccent_extension = getattr(settings, 'SEARCH_UNACCENT_EXTENSION', False) and 'django.contrib.postgres' in settings.INSTALLED_APPS
            middle_term = '__unaccent' if unaccent_extension else ''

            search = []

            for s in search_fields:
                query = {}
                query["{}{}__icontains".format(s, middle_term)] = search_terms
                search.append(query)

            queryset = queryset.filter(_construct_search_query(search))

        elif search_method == "exact":
            search = []

            for s in search_fields:
                query = {}
                query["{}__exact".format(s)] = search_terms
                search.append(query)

            queryset = queryset.filter(_construct_search_query(search))

        return queryset

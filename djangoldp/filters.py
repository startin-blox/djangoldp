from rest_framework.filters import BaseFilterBackend
from rest_framework_guardian.filters import ObjectPermissionsFilter


class LDPPermissionsFilterBackend(ObjectPermissionsFilter):
    """
    Default FilterBackend for LDPPermissions. If user does not have model-level permissions, filters by
    Django-Guardian's get_objects_for_user
    """
    def filter_queryset(self, request, queryset, view):
        from djangoldp.permissions import LDPPermissions

        # compares the requirement for GET, with what the user has on the MODEL
        if LDPPermissions.has_model_view_permission(request, view.model):
            return queryset
        if not request.user.is_anonymous:
            return super().filter_queryset(request, queryset, view)
        # user is anonymous without anonymous permissions
        return view.model.objects.none()


class LocalObjectFilterBackend(BaseFilterBackend):
    """
    Filter which removes external objects (federated backlinks) from the queryset
    For querysets which should only include local objects
    """
    def filter_queryset(self, request, queryset, view):
        from djangoldp.models import Model

        internal_ids = [x.pk for x in queryset if not Model.is_external(x)]
        return queryset.filter(pk__in=internal_ids)


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

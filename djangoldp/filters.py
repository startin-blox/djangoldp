from rest_framework.filters import BaseFilterBackend
from djangoldp.models import Model


class LocalObjectFilterBackend(BaseFilterBackend):
    """
    Filter which removes external objects (federated backlinks) from the queryset
    For querysets which should only include local objects
    """
    def filter_queryset(self, request, queryset, view):
        internal_ids = [x.pk for x in queryset if not Model.is_external(x)]
        return queryset.filter(pk__in=internal_ids)


class LocalObjectOnContainerPathBackend(LocalObjectFilterBackend):
    """
    Override of LocalObjectFilterBackend which removes external objects when the view requested
    is the model container path
    """
    def filter_queryset(self, request, queryset, view):
        if issubclass(view.model, Model) and request.path_info == view.model.get_container_path():
            return super(LocalObjectOnContainerPathBackend, self).filter_queryset(request, queryset, view)
        return queryset

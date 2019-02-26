from importlib import import_module

from django.conf import settings
from django.conf.urls import url, include

from djangoldp.models import LDPSource, Model
from djangoldp.views import LDPSourceViewSet


def __clean_path(path):
    if path.startswith("/"):
        path = path[1:]
    if not path.endswith("/"):
        path = "{}/".format(path)
    return path


urlpatterns = [
    url(r'^sources/', LDPSourceViewSet.urls(model=LDPSource)),
]

for package in settings.DJANGOLDP_PACKAGES:
    import_module('{}.models'.format(package))

model_classes = {cls.__name__: cls for cls in Model.__subclasses__()}

for class_name in model_classes:
    model_class = model_classes[class_name]
    path = __clean_path(model_class.get_container_path())
    urls_fct = model_class.get_view_set().urls
    urlpatterns.append(url(r'^' + path, include(
        urls_fct(model=model_class,
                 permission_classes=getattr(model_class._meta, 'permission_classes', []),
                 fields=getattr(model_class._meta, 'serializer_fields', []),
                 nested_fields=getattr(model_class._meta, 'nested_fields', [])))))

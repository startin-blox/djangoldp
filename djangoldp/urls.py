from importlib import import_module

from django.conf import settings
from django.conf.urls import re_path, include

from djangoldp.models import LDPSource, Model
from djangoldp.permissions import LDPPermissions
from djangoldp.views import LDPSourceViewSet, WebFingerView, InboxView
from djangoldp.views import LDPViewSet


def __clean_path(path):
    '''ensures path is Django-friendly'''
    if path.startswith("/"):
        path = path[1:]
    if not path.endswith("/"):
        path = "{}/".format(path)
    return path


urlpatterns = [
    re_path(r'^sources/(?P<federation>\w+)/', LDPSourceViewSet.urls(model=LDPSource, fields=['federation', 'urlid'],
                                                                permission_classes=[LDPPermissions], )),
    re_path(r'^\.well-known/webfinger/?$', WebFingerView.as_view()),
    re_path(r'^inbox/$', InboxView.as_view()),
]

for package in settings.DJANGOLDP_PACKAGES:
    try:
        import_module('{}.models'.format(package))
        urlpatterns.append(re_path(r'^', include('{}.djangoldp_urls'.format(package))))
    except ModuleNotFoundError:
        pass

if 'djangoldp_account' not in settings.DJANGOLDP_PACKAGES:
    urlpatterns.append(re_path(r'^users/', LDPViewSet.urls(model=settings.AUTH_USER_MODEL, permission_classes=[])))

# fetch a list of all models which subclass DjangoLDP Model
model_classes = {cls.__name__: cls for cls in Model.__subclasses__()}

# append urls for all DjangoLDP Model subclasses
for class_name in model_classes:
    model_class = model_classes[class_name]
    # the path is the url for this model
    path = __clean_path(model_class.get_container_path())
    # urls_fct will be a method which generates urls for a ViewSet (defined in LDPViewSetGenerator)
    urls_fct = model_class.get_view_set().urls
    urlpatterns.append(re_path(r'^' + path,
        urls_fct(model=model_class,
                 lookup_field=Model.get_meta(model_class, 'lookup_field', 'pk'),
                 permission_classes=Model.get_meta(model_class, 'permission_classes', [LDPPermissions]),
                 fields=Model.get_meta(model_class, 'serializer_fields', []),
                 nested_fields=model_class.nested.fields())))

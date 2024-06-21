from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import Group
from django.urls import path, re_path, include

from djangoldp.models import LDPSource, Model
from djangoldp.permissions import ReadOnly
from djangoldp.views import LDPSourceViewSet, WebFingerView, InboxView
from djangoldp.views import LDPViewSet, serve_static_content


def __clean_path(path):
    '''ensures path is Django-friendly'''
    if path.startswith("/"):
        path = path[1:]
    if not path.endswith("/"):
        path = "{}/".format(path)
    return path


def get_all_non_abstract_subclasses(cls):
    '''
    returns a set of all subclasses for a given Python class (recursively calls cls.__subclasses__()). Ignores Abstract
    classes
    '''
    def valid_subclass(sc):
        '''returns True if the parameterised subclass is valid and should be returned'''
        return not getattr(sc._meta, 'abstract', False)

    return set(c for c in cls.__subclasses__() if valid_subclass(c)).union(
        [subclass for c in cls.__subclasses__() for subclass in get_all_non_abstract_subclasses(c) if valid_subclass(subclass)])

urlpatterns = [
    path('groups/', LDPViewSet.urls(model=Group)),
    re_path(r'^sources/(?P<federation>\w+)/', LDPSourceViewSet.urls(model=LDPSource, fields=['federation', 'urlid'],
                                                                    permission_classes=[ReadOnly], )),
    re_path(r'^\.well-known/webfinger/?$', WebFingerView.as_view()),
    path('inbox/', InboxView.as_view()),
    re_path(r'^ssr/(?P<path>.*)$', serve_static_content, name='serve_static_content'),
]

if settings.ENABLE_SWAGGER_DOCUMENTATION:
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
    urlpatterns.extend([
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "docs/",
            SpectacularSwaggerView.as_view(
                template_name="swagger-ui.html", url_name="schema"
            ),
            name="swagger-ui",
        )
    ])

for package in settings.DJANGOLDP_PACKAGES:
    try:
        import_module('{}.models'.format(package))
    except ModuleNotFoundError:
        pass
    try:
        urlpatterns.append(path('', include('{}.djangoldp_urls'.format(package))))
    except ModuleNotFoundError:
        pass

# append urls for all DjangoLDP Model subclasses
for model in get_all_non_abstract_subclasses(Model):
    # the path is the url for this model
    model_path = __clean_path(model.get_container_path())
    # urls_fct will be a method which generates urls for a ViewSet (defined in LDPViewSetGenerator)
    urls_fct = getattr(model, 'view_set', LDPViewSet).urls
    urlpatterns.append(path('' + model_path,
        urls_fct(model=model,
                 lookup_field=getattr(model._meta, 'lookup_field', 'pk'),
                 permission_classes=getattr(model._meta, 'permission_classes', []),
                 fields=getattr(model._meta, 'serializer_fields', []),
                 nested_fields=getattr(model._meta, 'nested_fields', [])
                 )))

# NOTE: this route will be ignored if a custom (subclass of Model) user model is used, or it is registered by a package
# Django matches the first url it finds for a given path
urlpatterns.append(re_path('users/', LDPViewSet.urls(model=settings.AUTH_USER_MODEL, permission_classes=[])))
from pyld import jsonld
from django.conf import settings
from django.conf.urls import url
from django.utils.decorators import classonlymethod
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.viewsets import ModelViewSet
from .serializers import LDPSerializer

class JSONLDRenderer(JSONRenderer):
    media_type = 'application/ld+json'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data["@context"] = settings.LDP_RDF_CONTEXT
        return super(JSONLDRenderer, self).render(data, accepted_media_type, renderer_context)

class JSONLDParser(JSONParser):
    media_type = 'application/ld+json'
    def parse(self, stream, media_type=None, parser_context=None):
        data = super(JSONLDParser, self).parse(stream, media_type, parser_context)
        return jsonld.compact(data, ctx=data["@context"])


class LDPViewSet(ModelViewSet):
    model = None
    renderer_classes = (JSONLDRenderer, )
    parser_classes = (JSONLDParser, )
    
    def __init__(self, model, **kwargs):
        class_attrs = {'Meta': type('Meta', (), {'model': model, 'exclude': ()})}
        self.serializer_class = type(LDPSerializer)(model.__name__+'Serializer', (LDPSerializer,), class_attrs)
        super().__init__(model=model, **kwargs)
    
    def get_queryset(self, *args, **kwargs):
        if self.model:
            return self.model.objects.all()
        else:
            return super(LDPView, self).get_queryset(*args, **kwargs)
    
    @classonlymethod
    def urls(cls, **kwargs):
        if isinstance(kwargs['model'], str):
            model = kwargs['model'].split('.')[-1].lower()
        else:
            model = kwargs['model']._meta.object_name.lower()
        return [
            url(r'^$', cls.as_view({'get': 'list', 'post': 'create'}, **kwargs), name='{}-list'.format(model)),
            url(r'^(?P<pk>\d+)$', cls.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}, **kwargs), name='{}-detail'.format(model)),
        ]
    
    def dispatch(self, request, *args, **kwargs):
        response = super(LDPViewSet, self).dispatch(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST,PUT"
        response["Access-Control-Allow-Headers"] = "Content-Type, if-match"
        response["Accept-Post"] = "application/ld+json"
        return response

from pyld import jsonld
from django.apps import apps
from django.conf import settings
from django.conf.urls import url, include
from django.core.urlresolvers import get_resolver
from django.utils.decorators import classonlymethod
from rest_framework.authentication import SessionAuthentication
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

class NoCSRFAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

class LDPViewSetGenerator(ModelViewSet):
    @classonlymethod
    def get_model(cls, **kwargs):
        '''gets the model in the arguments or in the viewset definition'''
        model = kwargs.get('model') or cls.model
        if isinstance(model, str):
            model = apps.get_model(model)
        return model
    
    @classonlymethod
    def get_detail_url(cls, lookup_field=None, base_url='', **kwargs):
        '''builds the detail url based on the lookup_field'''
        lookup_field = lookup_field or kwargs.get('lookup_field') or cls.lookup_field
        if lookup_field and lookup_field != 'pk':
            return r'{}(?P<{}>[\w-]+)/'.format(base_url, lookup_field)
        return  r'{}(?P<pk>\d+)/'.format(base_url)
    
    @classonlymethod
    def get_nested_urls(cls, detail_url, model_name, **kwargs):
        nested_field = kwargs.get('nested_field') or cls.nested_field
        if not nested_field:
            return []
        
        base_url = r'{}{}/'.format(detail_url, nested_field)
        related_field = kwargs['model']._meta.get_field(nested_field)
        related_name = related_field.related_query_name()
        related_model = related_field.related_model
        nested_lookup_field = related_model._meta.object_name.lower()+'_id'
        
        nested_args = {
             'model': related_model,
             'exclude': (), #exclude related_name for foreignkey attributes 
             'parent_model': kwargs['model'],
             'nested_field': nested_field,
             'nested_related_name': related_name
        }
        nested_detail_url = cls.get_detail_url(nested_lookup_field, base_url)
#        return [
#            url(base_url+'$', cls.as_view(cls.list_actions, **nested_args), name='{}-{}-list'.format(model_name, nested_field)),
#            url(nested_detail_url+'$', cls.as_view(cls.detail_actions, **nested_args), name='{}-{}-detail'.format(model_name, nested_field)),
#        ]
        return [
            url(base_url+'$', cls.as_view(cls.detail_actions, **nested_args), name='{}-{}-detail'.format(model_name, nested_field)),
        ]
    
    @classonlymethod
    def urls(cls, **kwargs):
        kwargs['model'] = cls.get_model(**kwargs)
        model_name = kwargs['model']._meta.object_name.lower()
        detail_url = cls.get_detail_url(**kwargs)
        
        return include(
            cls.get_nested_urls(detail_url, model_name, **kwargs) + [
                url(r'^$', cls.as_view(cls.list_actions, **kwargs), name='{}-list'.format(model_name)),
                url(detail_url+'$', cls.as_view(cls.detail_actions, **kwargs), name='{}-detail'.format(model_name)),
            ])

class LDPViewSet(LDPViewSetGenerator):
    model = None
    fields = None
    exclude = None
    parent_model = None
    nested_field = None
    nested_related_name = None
    list_actions = {'get': 'list', 'post': 'create'}
    detail_actions = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}
    renderer_classes = (JSONLDRenderer, )
    parser_classes = (JSONLDParser, )
    authentication_classes = (NoCSRFAuthentication,)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model_name = self.model._meta.object_name.lower()
        lookup_field = get_resolver().reverse_dict[model_name+'-detail'][0][0][1][0]
        meta_args =  {'model': self.model, 'extra_kwargs': {'@id': {'lookup_field': lookup_field}}}
        if self.fields:
            meta_args['fields'] = self.fields
        else:
            meta_args['exclude'] = self.exclude or ()
        meta_class = type('Meta', (), meta_args)
        self.serializer_class = type(LDPSerializer)(model_name+'Serializer', (LDPSerializer,), {'Meta': meta_class})
    
    def get_parent(self):
        return self.parent_model.objects.get(id=self.kwargs[self.lookup_field])
    
    def perform_create(self, serializer):
        create_args = {}
        if self.parent_model:
            create_args[self.nested_related_name] = self.get_parent()
        if hasattr(self.model._meta, 'auto_author'):
            create_args[self.model._meta.auto_author] = self.request.user
        serializer.save(**create_args)
    
    def get_queryset(self, *args, **kwargs):
        if self.parent_model:
            return getattr(self.get_parent(), self.nested_field).all()
        if self.model:
            return self.model.objects.all()
        else:
            return super(LDPView, self).get_queryset(*args, **kwargs)
    
    def dispatch(self, request, *args, **kwargs):
        response = super(LDPViewSet, self).dispatch(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = request.META.get('HTTP_ORIGIN')
        response["Access-Control-Allow-Methods"] = "POST,PUT"
        response["Access-Control-Allow-Headers"] = "Content-Type, if-match"
        response["Access-Control-Allow-Credentials"] = 'true'
        response["Accept-Post"] = "application/ld+json"
        return response

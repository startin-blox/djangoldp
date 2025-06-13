# Django imports
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import get_object_or_404
from django.urls import include, path, re_path
from django.urls.resolvers import get_resolver
from django.utils.decorators import classonlymethod

# DjangoLDP imports
from djangoldp.filters import LocalObjectOnContainerPathBackend, SearchByQueryParamFilterBackend
from djangoldp.models import DynamicNestedField, LDPSource
from djangoldp.related import get_prefetch_fields
from djangoldp.utils import is_authenticated_user
from djangoldp.views.commons import JSONLDParser, JSONLDRenderer, NoCSRFAuthentication

# DRF imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

import logging

logger = logging.getLogger('djangoldp')
get_user_model()._meta.rdf_context = {"get_full_name": "rdfs:label"}


class LDPViewSetGenerator(ModelViewSet):
    """An extension of ModelViewSet that generates automatically URLs for the model"""
    model = None
    nested_fields = []
    model_prefix = None
    list_actions = {'get': 'list', 'post': 'create'}
    detail_actions = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lookup_field = LDPViewSetGenerator.get_lookup_arg(**kwargs)

    @classonlymethod
    def get_model(cls, **kwargs):
        '''gets the model in the arguments or in the viewset definition'''
        model = kwargs.get('model') or cls.model
        if isinstance(model, str):
            model = apps.get_model(model)
        return model

    @classonlymethod
    def get_lookup_arg(cls, **kwargs):
        return kwargs.get('lookup_url_kwarg') or cls.lookup_url_kwarg or kwargs.get('lookup_field') or \
               getattr(kwargs['model']._meta, 'lookup_field', 'pk') or cls.lookup_field

    @classonlymethod
    def get_detail_expr(cls, lookup_field=None, **kwargs):
        '''builds the detail url based on the lookup_field'''
        lookup_field = lookup_field or cls.get_lookup_arg(**kwargs)
        lookup_group = r'\d' if lookup_field == 'pk' else r'[\w\-\.]'
        return r'(?P<{}>{}+)/'.format(lookup_field, lookup_group)

    @classonlymethod
    def build_nested_view_set(cls, view_set=None):
        '''returns the the view_set parameter mixed into the LDPNestedViewSet class'''
        if view_set is not None:
            class LDPNestedCustomViewSet(LDPNestedViewSet, view_set):
                pass
            return LDPNestedCustomViewSet
        return LDPNestedViewSet

    @classonlymethod
    def urls(cls, **kwargs):
        '''constructs urls list for model passed in kwargs'''
        kwargs['model'] = cls.get_model(**kwargs)
        model_name = kwargs['model']._meta.object_name.lower()
        if kwargs.get('model_prefix'):
            model_name = '{}-{}'.format(kwargs['model_prefix'], model_name)
        detail_expr = cls.get_detail_expr(**kwargs)
        # Gets permissions on the model if not explicitely passed to the view
        if not 'permission_classes' in kwargs and hasattr(kwargs['model']._meta, 'permission_classes'):
            kwargs['permission_classes'] = kwargs['model']._meta.permission_classes

        urls = [
            path('', cls.as_view(cls.list_actions, **kwargs), name='{}-list'.format(model_name)),
            re_path('^' + detail_expr + '$', cls.as_view(cls.detail_actions, **kwargs),
                    name='{}-detail'.format(model_name)),
        ]

        # append nested fields to the urls list
        for field_name in kwargs.get('nested_fields') or cls.nested_fields:
            try:
                nested_field = kwargs['model']._meta.get_field(field_name)
                nested_model = nested_field.related_model
                field_name_to_parent = nested_field.remote_field.name
            except FieldDoesNotExist:
                nested_model = getattr(kwargs['model'], field_name).field.model
                nested_field = getattr(kwargs['model'], field_name).field.remote_field
                field_name_to_parent = getattr(kwargs['model'], field_name).field.name

            # urls should be called from _nested_ view set, which may need a custom view set mixed in
            view_set = getattr(nested_model._meta, 'view_set', None)
            nested_view_set = cls.build_nested_view_set(view_set)

            urls.append(re_path('^' + detail_expr + field_name + '/',
                    nested_view_set.urls(
                    model=nested_model,
                    model_prefix=kwargs['model']._meta.object_name.lower(), # prefix with parent name
                    lookup_field=getattr(nested_model._meta, 'lookup_field', 'pk'),
                    exclude=(field_name_to_parent,) if nested_field.one_to_many else (),
                    permission_classes=getattr(nested_model._meta, 'permission_classes', []),
                    nested_field_name=field_name,
                    fields=getattr(nested_model._meta, 'serializer_fields', []),
                    nested_fields=[],
                    parent_model=kwargs['model'],
                    parent_lookup_field=cls.get_lookup_arg(**kwargs),
                    nested_field=nested_field,
                    field_name_to_parent=field_name_to_parent)))

        return include(urls)



# LDPViewSetGenerator is a ModelViewSet (DRF) with methods to automatically generate model urls
class LDPViewSet(LDPViewSetGenerator):
    """An automatically generated viewset that serves models following the Linked Data Platform convention"""
    fields = None
    exclude = None
    renderer_classes = (JSONLDRenderer,)
    parser_classes = (JSONLDParser,)
    authentication_classes = (NoCSRFAuthentication,)
    filter_backends = [SearchByQueryParamFilterBackend, LocalObjectOnContainerPathBackend]
    prefetch_fields = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # attach filter backends based on permissions classes, to reduce the queryset based on these permissions
        # https://www.django-rest-framework.org/api-guide/filtering/#generic-filtering
        self.filter_backends = type(self).filter_backends + list({perm_class().get_filter_backend(self.model)
                for perm_class in self.permission_classes if hasattr(perm_class(), 'get_filter_backend')})
        if None in self.filter_backends:
            self.filter_backends.remove(None)
    
    def filter_queryset(self, queryset):
        if self.request.user.is_superuser:
            return queryset
        return super().filter_queryset(queryset)

    def check_permissions(self, request):
        if request.user.is_superuser:
            return True
        return super().check_permissions(request)

    def check_object_permissions(self, request, obj):
        if request.user.is_superuser:
            return True
        return super().check_object_permissions(request, obj)
    
    def get_depth(self) -> int:
        if getattr(self, 'force_depth', None):
            #TODO: this exception on depth for writing should be handled by the serializer itself
            return self.force_depth
        if hasattr(self, 'request') and 'HTTP_DEPTH' in self.request.META:
            return int(self.request.META['HTTP_DEPTH'])
        if hasattr(self, 'depth'):
            return self.depth
        return getattr(self.model._meta, 'depth', 0)

    def get_serializer_class(self):
        model_name = self.model._meta.object_name.lower()
        try:
            lookup_field = get_resolver().reverse_dict[model_name + '-detail'][0][0][1][0]
        except:
            lookup_field = 'urlid'
        
        meta_args = {'model': self.model, 'extra_kwargs': {
                '@id': {'lookup_field': lookup_field}},
                'depth': self.get_depth(),
                'extra_fields': self.nested_fields}

        if self.fields:
            meta_args['fields'] = self.fields
        else:
            meta_args['exclude'] = self.exclude or getattr(self.model._meta, 'serializer_fields_exclude', ())
        # create the Meta class to associate to LDPSerializer, using meta_args param

        from djangoldp.serializers import LDPSerializer
        if self.serializer_class is None:
            self.serializer_class = LDPSerializer

        parent_meta = (self.serializer_class.Meta,) if hasattr(self.serializer_class, 'Meta') else ()
        meta_class = type('Meta', parent_meta, meta_args)

        return type(self.serializer_class)(self.model._meta.object_name.lower() + 'Serializer',
                                   (self.serializer_class,),
                                   {'Meta': meta_class})

    # The chaining of filter through | may lead to duplicates and distinct should only be applied in the end.
    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).distinct()

    def create(self, request, *args, **kwargs):
        self.force_depth = 10
        serializer = self.get_serializer(data=request.data)
        self.force_depth = None
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)
        response_serializer = self.get_serializer()
        data = response_serializer.to_representation(serializer.instance)
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self.force_depth = 10
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        self.force_depth = None
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        response_serializer = self.get_serializer()
        data = response_serializer.to_representation(serializer.instance)
        return Response(data)

    def perform_create(self, serializer, **kwargs):
        if hasattr(self.model._meta, 'auto_author') and isinstance(self.request.user, get_user_model()):
            kwargs[self.model._meta.auto_author] = get_user_model().objects.get(pk=self.request.user.pk)
        return serializer.save(**kwargs)

    def get_queryset(self, *args, **kwargs):
        if self.model:
            queryset = self.model.objects.all()
        else:
            queryset = super(LDPViewSet, self).get_queryset(*args, **kwargs)
        if self.prefetch_fields is None:
            self.prefetch_fields = get_prefetch_fields(self.model, self.get_serializer(), self.get_depth())
        return queryset.prefetch_related(*self.prefetch_fields)

    def dispatch(self, request, *args, **kwargs):
        '''overriden dispatch method to append some custom headers'''
        response = super(LDPViewSet, self).dispatch(request, *args, **kwargs)
        response["Accept-Post"] = "application/ld+json"

        if response.status_code in [201, 200] and '@id' in response.data:
            response["Location"] = str(response.data['@id'])
        else:
            pass

        if is_authenticated_user(request.user):
            try:
                response['User'] = request.user.urlid
            except AttributeError:
                pass
        return response


class LDPNestedViewSet(LDPViewSet):
    """
    A special case of LDPViewSet serving objects of a relation of a given object
    (e.g. members of a group, or skills of a user)
    """
    parent_model = None
    parent_lookup_field = None
    nested_field = None
    nested_field_name = None
    field_name_to_parent = None

    def get_parent(self):
        return get_object_or_404(self.parent_model, **{self.parent_lookup_field: self.kwargs[self.parent_lookup_field]})

    def perform_create(self, serializer, **kwargs):
        kwargs[self.field_name_to_parent] = self.get_parent()
        super().perform_create(serializer, **kwargs)

    def get_queryset(self, *args, **kwargs):
        related = getattr(self.get_parent(), self.nested_field_name)
        if self.nested_field.many_to_many or self.nested_field.one_to_many:
            if isinstance(self.nested_field, DynamicNestedField):
                return related()
            return related.all()
        if self.nested_field.one_to_one or self.nested_field.many_to_one:
            return type(related).objects.filter(pk=related.pk)


        return response


class LDPSourceViewSet(LDPViewSet):
    model = LDPSource
    federation = None

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(federation=self.kwargs['federation'])

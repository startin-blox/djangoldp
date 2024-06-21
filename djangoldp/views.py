import json
import validators
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import JsonResponse, Http404, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.urls import include, re_path, path
from django.urls.resolvers import get_resolver
from django.utils.decorators import classonlymethod
from django.views import View
from pyld import jsonld
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.utils import model_meta
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from djangoldp.endpoints.webfinger import WebFingerEndpoint, WebFingerError
from djangoldp.models import LDPSource, Model, Follower, DynamicNestedField
from djangoldp.filters import LocalObjectOnContainerPathBackend, SearchByQueryParamFilterBackend
from djangoldp.related import get_prefetch_fields
from djangoldp.utils import is_authenticated_user
from djangoldp.activities import ActivityQueueService, as_activitystream, ACTIVITY_SAVING_SETTING, ActivityPubService
from djangoldp.activities.errors import ActivityStreamDecodeError, ActivityStreamValidationError
import logging
import os

logger = logging.getLogger('djangoldp')
get_user_model()._meta.rdf_context = {"get_full_name": "rdfs:label"}


# renders into JSONLD format by applying context to the data
# https://github.com/digitalbazaar/pyld
class JSONLDRenderer(JSONRenderer):
    media_type = 'application/ld+json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, dict):
            context = data.get("@context")
            if isinstance(context, list):
                data["@context"] = [settings.LDP_RDF_CONTEXT] + context
            elif isinstance(context, str) or isinstance(context, dict):
                data["@context"] = [settings.LDP_RDF_CONTEXT, context]
            else:
                data["@context"] = settings.LDP_RDF_CONTEXT
        return super(JSONLDRenderer, self).render(data, accepted_media_type, renderer_context)


# https://github.com/digitalbazaar/pyld
class JSONLDParser(JSONParser):
    #TODO: It current only works with pyld 1.0. We need to check our support of JSON-LD
    media_type = 'application/ld+json'

    def parse(self, stream, media_type=None, parser_context=None):
        data = super(JSONLDParser, self).parse(stream, media_type, parser_context)
        # compact applies the context to the data and makes it a format which is easier to work with
        # see: http://json-ld.org/spec/latest/json-ld/#compacted-document-form
        try:
            return jsonld.compact(data, ctx=settings.LDP_RDF_CONTEXT)
        except jsonld.JsonLdError as e:
            raise ParseError(str(e.cause))


# an authentication class which exempts CSRF authentication
class NoCSRFAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


class InboxView(APIView):
    """
    Receive linked data notifications
    """
    permission_classes = [AllowAny, ]

    def post(self, request, *args, **kwargs):
        '''
        receiver for inbox messages. See https://www.w3.org/TR/ldn/
        '''
        try:
            activity = json.loads(request.body, object_hook=as_activitystream)
            activity.validate()
        except ActivityStreamDecodeError:
            return Response('Activity type unsupported', status=status.HTTP_405_METHOD_NOT_ALLOWED)
        except ActivityStreamValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        try:
            self._handle_activity(activity, **kwargs)
        except IntegrityError:
            return Response({'Unable to save due to an IntegrityError in the receiver model'},
                            status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        # save the activity and return 201
        if ACTIVITY_SAVING_SETTING == 'VERBOSE':
            obj = ActivityQueueService._save_sent_activity(activity.to_json(), local_id=request.path_info, success=True,
                                                           type=activity.type)

            response = Response({}, status=status.HTTP_201_CREATED)
            response['Location'] = obj.urlid
        
        else:
            response = Response({}, status=status.HTTP_200_OK)

        return response

    def _handle_activity(self, activity, **kwargs):
        if activity.type == 'Add':
            self.handle_add_activity(activity, **kwargs)
        elif activity.type == 'Remove':
            self.handle_remove_activity(activity, **kwargs)
        elif activity.type == 'Delete':
            self.handle_delete_activity(activity, **kwargs)
        elif activity.type == 'Create' or activity.type == 'Update':
            self.handle_create_or_update_activity(activity, **kwargs)
        elif activity.type == 'Follow':
            self.handle_follow_activity(activity, **kwargs)

    def atomic_get_or_create_nested_backlinks(self, obj, object_model=None, update=False):
        '''
        a version of get_or_create_nested_backlinks in which all nested backlinks are created, or none of them are
        '''
        try:
            with transaction.atomic():
                return self._get_or_create_nested_backlinks(obj, object_model, update)
        except IntegrityError as e:
            logger.error(str(e))
            logger.warning(
                'received a backlink which you were not able to save because of a constraint on the model field.')
            raise e

    def _get_or_create_nested_backlinks(self, obj, object_model=None, update=False):
        '''
        recursively deconstructs a tree of nested objects, using get_or_create on each leaf/branch
        :param obj: Dict representation of the object
        :param object_model: The Model class of the object. Will be discovered if set to None
        :param update: if True will update retrieved objects with new data
        :raises Exception: if get_or_create fails on a branch, the creation will be reversed and the Exception re-thrown
        '''
        # store a list of the object's sub-items
        if object_model is None:
            object_model = Model.get_subclass_with_rdf_type(obj['@type'])
        if object_model is None:
            raise Http404('unable to store type ' + obj['@type'] + ', model with this rdf_type not found')
        branches = {}

        for item in obj.items():
            # TODO: parse other data types. Match the key to the field_name
            if isinstance(item[1], dict):
                item_value = item[1]
                item_model = Model.get_subclass_with_rdf_type(item_value['@type'])
                if item_model is None:
                    raise Http404(
                        'unable to store type ' + item_value['@type'] + ', model with this rdf_type not found')

                # push nested object tuple as a branch
                backlink = self._get_or_create_nested_backlinks(item_value, item_model)
                branches[item[0]] = backlink

        # get or create the backlink
        try:
            if obj['@id'] is None or not validators.url(obj['@id']):
                raise ValueError('received invalid urlid ' + str(obj['@id']))
            external = Model.get_or_create_external(object_model, obj['@id'], update=update, **branches)

            # creating followers, to inform distant resource of changes to local connection
            if Model.is_external(external):
                # this is handled with Followers, where each local child of the branch is followed by its external parent
                for item in obj.items():
                    urlid = item[1]
                    if isinstance(item[1], dict):
                        urlid = urlid['@id']
                    if not isinstance(urlid, str) or not validators.url(urlid):
                        continue

                    if not Model.is_external(urlid):
                        ActivityPubService.save_follower_for_target(external.urlid, urlid)

            return external

        # this will be raised when the object was local, but it didn't exist
        except ObjectDoesNotExist:
            raise Http404(getattr(object_model._meta, 'label', 'Unknown Model') + ' ' + str(obj['@id']) + ' does not exist')

    # TODO: a fallback here? Saving the backlink as Object or similar
    def _get_subclass_with_rdf_type_or_404(self, rdf_type):
        model = Model.get_subclass_with_rdf_type(rdf_type)
        if model is None:
            raise Http404('unable to store type ' + rdf_type + ', model not found')
        return model

    def handle_add_activity(self, activity, **kwargs):
        '''
        handles Add Activities. See https://www.w3.org/ns/activitystreams
        Indicates that the actor has added the object to the target
        '''
        object_model = self._get_subclass_with_rdf_type_or_404(activity.object['@type'])
        target_model = self._get_subclass_with_rdf_type_or_404(activity.target['@type'])

        try:
            target = target_model.objects.get(urlid=activity.target['@id'])
        except target_model.DoesNotExist:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

        # store backlink(s) in database
        backlink = self.atomic_get_or_create_nested_backlinks(activity.object, object_model)

        # add object to target
        target_info = model_meta.get_field_info(target_model)

        for field_name, relation_info in target_info.relations.items():
            if relation_info.related_model == object_model:
                attr = getattr(target, field_name)
                if not attr.filter(urlid=backlink.urlid).exists():
                    attr.add(backlink)
                    ActivityPubService.save_follower_for_target(backlink.urlid, target.urlid)

    def handle_remove_activity(self, activity, **kwargs):
        '''
        handles Remove Activities. See https://www.w3.org/ns/activitystreams
        Indicates that the actor has removed the object from the origin
        '''
        # TODO: Remove Activity may pass target instead
        object_model = self._get_subclass_with_rdf_type_or_404(activity.object['@type'])
        origin_model = self._get_subclass_with_rdf_type_or_404(activity.origin['@type'])

        # get the model reference to saved object
        try:
            origin = origin_model.objects.get(urlid=activity.origin['@id'])
            object_instance = object_model.objects.get(urlid=activity.object['@id'])
        except origin_model.DoesNotExist:
            raise Http404(activity.origin['@id'] + ' did not exist')
        except object_model.DoesNotExist:
            return

        # remove object from origin
        origin_info = model_meta.get_field_info(origin_model)

        for field_name, relation_info in origin_info.relations.items():
            if relation_info.related_model == object_model:
                attr = getattr(origin, field_name)
                if attr.filter(urlid=object_instance.urlid).exists():
                    attr.remove(object_instance)
                    ActivityPubService.remove_followers_for_resource(origin.urlid, object_instance.urlid)

    def handle_create_or_update_activity(self, activity, **kwargs):
        '''
        handles Create & Update Activities. See https://www.w3.org/ns/activitystreams
        '''
        object_model = self._get_subclass_with_rdf_type_or_404(activity.object['@type'])
        self.atomic_get_or_create_nested_backlinks(activity.object, object_model, update=True)

    def handle_delete_activity(self, activity, **kwargs):
        '''
        handles Remove Activities. See https://www.w3.org/ns/activitystreams
        Indicates that the actor has deleted the object
        '''
        object_model = self._get_subclass_with_rdf_type_or_404(activity.object['@type'])

        # get the model reference to saved object
        try:
            object_instance = object_model.objects.get(urlid=activity.object['@id'])
        except object_model.DoesNotExist:
            return

        # disable backlinks first - prevents a duplicate being sent back
        object_instance.allow_create_backlink = False
        object_instance.save()
        object_instance.delete()
        urlid = getattr(object_instance, 'urlid', None)
        if urlid is not None:
            for follower in Follower.objects.filter(follower=urlid):
                follower.delete()

    def handle_follow_activity(self, activity, **kwargs):
        '''
        handles Follow Activities. See https://www.w3.org/ns/activitystreams
        Indicates that the actor is following the object, and should receive Updates on what happens to it
        '''
        object_model = self._get_subclass_with_rdf_type_or_404(activity.object['@type'])

        # get the model reference to saved object
        try:
            object_instance = object_model.objects.get(urlid=activity.object['@id'])
        except object_model.DoesNotExist:
            raise Http404(activity.object['@id'] + ' did not exist')
        if Model.is_external(object_instance):
            raise Http404(activity.object['@id'] + ' is not local to this server')

        # get the inbox field from the actor
        if isinstance(activity.actor, str):
            inbox = activity.actor
        else:
            inbox = getattr(activity.actor, 'inbox', None)
            if inbox is None:
                inbox = getattr(activity.actor, 'id', getattr(activity.actor, '@id'))

        if not Follower.objects.filter(object=object_instance.urlid, inbox=inbox).exists():
            Follower.objects.create(object=object_instance.urlid, inbox=inbox)


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


class LDPAPIView(APIView):
    '''extends rest framework APIView to support Solid standards'''
    authentication_classes = (NoCSRFAuthentication,)

    def dispatch(self, request, *args, **kwargs):
        '''overriden dispatch method to append some custom headers'''
        response = super().dispatch(request, *args, **kwargs)
        
        if response.status_code in [201, 200] and isinstance(response.data, dict) and '@id' in response.data:
            response["Location"] = str(response.data['@id'])
        else:
            pass

        if is_authenticated_user(request.user):
            try:
                response['User'] = request.user.urlid
            except AttributeError:
                pass
        return response


class LDPSourceViewSet(LDPViewSet):
    model = LDPSource
    federation = None

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(federation=self.kwargs['federation'])


class WebFingerView(View):
    endpoint_class = WebFingerEndpoint

    def get(self, request, *args, **kwargs):
        return self.on_request(request)

    def on_request(self, request):
        endpoint = self.endpoint_class(request)
        try:
            endpoint.validate_params()

            return JsonResponse(endpoint.response())

        except WebFingerError as error:
            return JsonResponse(error.create_dict(), status=400)

    def post(self, request, *args, **kwargs):
        return self.on_request(request)


def serve_static_content(request, path):
    file_path = os.path.join('ssr', path[:-1])
    if not file_path.endswith('.jsonld'):
        file_path += '.jsonld'

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read()

        json_content = json.loads(content)
        return JsonResponse(json_content, safe=False, status=200,
                            content_type='application/ld+json',
                            headers={
                              'Access-Control-Allow-Origin': '*',
                              'Cache-Control': 'public, max-age=3600',
                            })
    else:
        return HttpResponseNotFound('File not found')

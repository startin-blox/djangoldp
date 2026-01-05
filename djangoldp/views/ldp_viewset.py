# Django imports
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import get_object_or_404
from django.urls import include, path, re_path
from django.urls.resolvers import get_resolver
from django.utils.decorators import classonlymethod
from django.utils.http import parse_etags, http_date, parse_http_date

# DjangoLDP imports
from djangoldp.etag import generate_etag, generate_container_etag, normalize_etag
from djangoldp.filters import LocalObjectOnContainerPathBackend, SearchByQueryParamFilterBackend
from djangoldp.models import DynamicNestedField, LDPSource
from djangoldp.parsers import JSONLDParser, TurtleParser
from djangoldp.related import get_prefetch_fields
from djangoldp.renderers import JSONLDRenderer, TurtleRenderer
from djangoldp.utils import is_authenticated_user
from djangoldp.views.commons import NoCSRFAuthentication

# DRF imports
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

import logging
import re

logger = logging.getLogger('djangoldp')
get_user_model()._meta.rdf_context = {"get_full_name": "rdfs:label"}


class LDPViewSetGenerator(ModelViewSet):
    """An extension of ModelViewSet that generates automatically URLs for the model"""
    model = None
    nested_fields = []
    model_prefix = None
    list_actions = {'get': 'list', 'post': 'create', 'options': 'options'}
    detail_actions = {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy', 'options': 'options'}

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
    renderer_classes = (JSONLDRenderer, TurtleRenderer)
    parser_classes = (JSONLDParser, TurtleParser)
    authentication_classes = (NoCSRFAuthentication,)
    filter_backends = [SearchByQueryParamFilterBackend, LocalObjectOnContainerPathBackend]
    prefetch_fields = None
    metadata_class = None  # Disable DRF metadata to use custom OPTIONS handler

    # Fix Issues #3, #5: Define CORS expose headers once at class level
    # These headers are exposed to JavaScript clients in cross-origin requests
    LDP_EXPOSE_HEADERS = ['Link', 'ETag', 'Last-Modified', 'Accept-Post', 'Accept-Patch',
                          'Preference-Applied', 'Location', 'User', 'Allow', 'Content-Type']

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

        # Check If-None-Match for creation (should fail if resource exists)
        if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
        if if_none_match == '*':
            # Client wants to ensure resource doesn't exist
            # For create operations, this is always satisfied
            pass

        self.perform_create(serializer)
        response_serializer = self.get_serializer()
        data = response_serializer.to_representation(serializer.instance)
        headers = self.get_success_headers(data)

        # Generate ETag for newly created resource
        etag = generate_etag(serializer.instance, data)

        # Check Prefer header for return preference (RFC 7240)
        # Fix Issue #4: Use regex for precise parsing
        prefer_header = request.META.get('HTTP_PREFER', '')
        prefer_minimal = bool(re.search(r'\breturn\s*=\s*minimal\b', prefer_header, re.IGNORECASE))
        prefer_representation = bool(re.search(r'\breturn\s*=\s*representation\b', prefer_header, re.IGNORECASE))

        # If Prefer: return=minimal, return 204 with Location header
        if prefer_minimal and not prefer_representation:
            response = Response(status=status.HTTP_204_NO_CONTENT, headers=headers)
            # Fix Issue #1: Ensure Location header is not empty
            location = data.get('@id', '')
            if not location:
                # Fallback to building Location from request path and instance pk
                location = request.build_absolute_uri(f"{request.path.rstrip('/')}/{serializer.instance.pk}/")
            response['Location'] = str(location)
            response['ETag'] = etag
            response['Preference-Applied'] = 'return=minimal'
            logger.debug(f"CREATE: Applied Prefer: return=minimal, returning 204 with Location: {response['Location']}")
        else:
            # Default or explicit return=representation
            response = Response(data, status=status.HTTP_201_CREATED, headers=headers)
            response['ETag'] = etag
            if prefer_representation:
                response['Preference-Applied'] = 'return=representation'
            logger.debug(f"CREATE: Returning full representation with 201")

        # Add Last-Modified if available
        # Fix Issue #2: Check for both existence and non-None value
        if hasattr(serializer.instance, 'updated_at') and serializer.instance.updated_at:
            response['Last-Modified'] = http_date(serializer.instance.updated_at.timestamp())

        return response

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # IMPORTANT: Check If-Match for updates
        precondition_response = self.check_preconditions(request, instance)
        if precondition_response:
            return precondition_response

        # Existing update logic...
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

        # Generate new ETag after update
        new_etag = generate_etag(serializer.instance, data)

        # Check Prefer header for return preference (RFC 7240)
        # Fix Issue #4: Use regex for precise parsing
        prefer_header = request.META.get('HTTP_PREFER', '')
        prefer_minimal = bool(re.search(r'\breturn\s*=\s*minimal\b', prefer_header, re.IGNORECASE))
        prefer_representation = bool(re.search(r'\breturn\s*=\s*representation\b', prefer_header, re.IGNORECASE))

        # If Prefer: return=minimal, return 204 with Location header
        if prefer_minimal and not prefer_representation:
            response = Response(status=status.HTTP_204_NO_CONTENT)
            # Fix Issue #1: Ensure Location header is not empty
            location = data.get('@id', '')
            if not location:
                # Fallback to building Location from request path
                location = request.build_absolute_uri(request.path)
            response['Location'] = str(location)
            response['ETag'] = new_etag
            response['Preference-Applied'] = 'return=minimal'
            logger.debug(f"UPDATE: Applied Prefer: return=minimal, returning 204 with Location: {response['Location']}")
        else:
            # Default or explicit return=representation
            response = Response(data)
            response['ETag'] = new_etag
            if prefer_representation:
                response['Preference-Applied'] = 'return=representation'
            logger.debug(f"UPDATE: Returning full representation with 200")

        return response

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

    def check_preconditions(self, request, instance=None):
        """
        Check conditional request headers.
        Returns Response if precondition fails, None if passes.

        Handles:
        - If-Match: Require ETag to match for updates (PUT/PATCH) - weak comparison
        - If-None-Match: Return 304 for GET, 412 for PUT/POST if ETag matches - weak comparison
        - If-Modified-Since: Return 304 if resource hasn't changed (GET only)
        """
        # If-Match: require ETag to match for updates (weak comparison)
        if_match = request.META.get('HTTP_IF_MATCH')
        if if_match and instance:
            try:
                # Serialize the instance to get consistent ETag (same as retrieve())
                serializer = self.get_serializer(instance)
                data = serializer.data
                current_etag = generate_etag(instance, data)
                # normalize_etag returns (is_weak, etag_value)
                _, current_etag_value = normalize_etag(current_etag)

                # Parse If-Match ETags
                match_etags = parse_etags(if_match)

                # For If-Match, use weak comparison (ignore weak/strong distinction)
                # Only the values need to match
                match_found = False
                if '*' in match_etags:
                    match_found = True
                else:
                    for etag in match_etags:
                        _, etag_value = normalize_etag(etag)
                        # Weak comparison: just compare values, ignore weak/strong status
                        if etag_value == current_etag_value:
                            match_found = True
                            break

                if not match_found:
                    return Response(
                        {'detail': 'Precondition failed: ETag does not match'},
                        status=status.HTTP_412_PRECONDITION_FAILED
                    )
            except Exception as e:
                # Malformed ETag should return 400 Bad Request
                logger.warning(f"Malformed If-Match header: {if_match}, error: {e}")
                return Response(
                    {'detail': 'Bad Request: Malformed If-Match header'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # If-None-Match: behavior depends on HTTP method
        if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
        if if_none_match and instance:
            try:
                # Serialize the instance to get consistent ETag (same as retrieve())
                serializer = self.get_serializer(instance)
                data = serializer.data
                current_etag = generate_etag(instance, data)
                _, current_etag_value = normalize_etag(current_etag)

                # Parse If-None-Match ETags
                none_match_etags = parse_etags(if_none_match)

                # Check if current ETag matches any of the provided ETags (weak comparison)
                etag_matches = False
                if '*' in none_match_etags:
                    etag_matches = True
                else:
                    for etag in none_match_etags:
                        _, etag_value = normalize_etag(etag)
                        # Weak comparison: just compare values
                        if etag_value == current_etag_value:
                            etag_matches = True
                            break

                if etag_matches:
                    # For GET/HEAD: return 304 Not Modified
                    if request.method in ['GET', 'HEAD']:
                        return Response(status=status.HTTP_304_NOT_MODIFIED)
                    # For PUT/POST/PATCH: return 412 Precondition Failed
                    elif request.method in ['PUT', 'POST', 'PATCH']:
                        return Response(
                            {'detail': 'Precondition failed: Resource already exists or ETag matches'},
                            status=status.HTTP_412_PRECONDITION_FAILED
                        )
            except Exception as e:
                # Malformed ETag should return 400 Bad Request
                logger.warning(f"Malformed If-None-Match header: {if_none_match}, error: {e}")
                return Response(
                    {'detail': 'Bad Request: Malformed If-None-Match header'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # If-Modified-Since (for GET/HEAD requests only)
        if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
        if if_modified_since and instance and request.method in ['GET', 'HEAD']:
            if hasattr(instance, 'updated_at') and instance.updated_at:
                try:
                    modified_since = parse_http_date(if_modified_since)
                    # Compare at second precision (HTTP dates don't include microseconds)
                    resource_timestamp = int(instance.updated_at.timestamp())
                    if resource_timestamp <= modified_since:
                        return Response(status=status.HTTP_304_NOT_MODIFIED)
                except (ValueError, TypeError) as e:
                    # Log malformed date but continue (don't return 400)
                    logger.warning(f"Malformed If-Modified-Since header: {if_modified_since}, error: {e}")

        return None

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single resource with ETag and conditional request support.
        """
        instance = self.get_object()

        # Check conditional headers
        precondition_response = self.check_preconditions(request, instance)
        if precondition_response:
            return precondition_response

        serializer = self.get_serializer(instance)
        data = serializer.data
        etag = generate_etag(instance, data)

        response = Response(data)
        response['ETag'] = etag

        # Add Last-Modified if available
        if hasattr(instance, 'updated_at'):
            response['Last-Modified'] = http_date(instance.updated_at.timestamp())

        return response

    def list(self, request, *args, **kwargs):
        """
        List resources in a container with container ETag support.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Get total count for ETag generation
        count = queryset.count()

        # Handle pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)

            # Extract page number from request for paginated ETag
            page_number = None
            try:
                # Try to get page number from paginator
                if hasattr(self, 'paginator') and hasattr(self.paginator, 'page'):
                    page_number = self.paginator.page.number
                # Fallback to query param
                elif 'page' in request.query_params:
                    page_number = int(request.query_params['page'])
            except (AttributeError, ValueError, TypeError):
                pass

            # Generate container ETag with page number
            etag = generate_container_etag(queryset, count, page_number)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = Response(serializer.data)
            # Generate container ETag without pagination
            etag = generate_container_etag(queryset, count)

        response['ETag'] = etag

        return response

    def options(self, request, *args, **kwargs):
        """
        Handle OPTIONS requests with proper LDP headers.
        Returns allowed methods and accepted content types.
        """
        # Determine if this is a detail or list view
        is_detail = self.lookup_field in kwargs

        # Build Allow header based on view type
        if is_detail:
            # Detail view: GET, PUT, PATCH, DELETE, HEAD, OPTIONS
            allowed_methods = ['GET', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
        else:
            # Container view: GET, POST, HEAD, OPTIONS
            allowed_methods = ['GET', 'POST', 'HEAD', 'OPTIONS']

        # Use HttpResponse instead of DRF Response to avoid content-type rendering issues
        from django.http import HttpResponse
        response = HttpResponse(status=200)
        response['Allow'] = ', '.join(allowed_methods)

        # Add Accept-Post for container views
        if not is_detail:
            response['Accept-Post'] = 'application/ld+json, text/turtle'

        # Add Accept-Patch for detail views (resources can be patched)
        if is_detail:
            response['Accept-Patch'] = 'application/ld+json, text/turtle'

        # Add Link headers for LDP types
        link_headers = []
        if is_detail:
            link_headers.append('<http://www.w3.org/ns/ldp#Resource>; rel="type"')
            link_headers.append('<http://www.w3.org/ns/ldp#RDFSource>; rel="type"')
        else:
            link_headers.append('<http://www.w3.org/ns/ldp#Resource>; rel="type"')
            link_headers.append('<http://www.w3.org/ns/ldp#RDFSource>; rel="type"')
            link_headers.append('<http://www.w3.org/ns/ldp#Container>; rel="type"')
            link_headers.append('<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"')

        response['Link'] = ', '.join(link_headers)

        # Add CORS expose headers for OPTIONS using class-level constant
        response['Access-Control-Expose-Headers'] = ', '.join(self.LDP_EXPOSE_HEADERS)

        logger.debug(f"OPTIONS: is_detail={is_detail}, Allow={response['Allow']}")

        return response

    def dispatch(self, request, *args, **kwargs):
        '''
        Overridden dispatch method to append custom headers for LDP compliance.

        Adds:
        - Accept-Post header for supported content types
        - Link headers for LDP resource types
        - Location header for created/updated resources
        - User header for authenticated users

        Note: CORS headers (Access-Control-Expose-Headers) are handled by
        AllowRequestedCORSMiddleware to ensure consistency across all responses.
        '''
        # Handle OPTIONS requests directly to bypass DRF metadata handling
        if request.method == 'OPTIONS':
            return self.options(request, *args, **kwargs)

        response = super(LDPViewSet, self).dispatch(request, *args, **kwargs)

        # Update Accept-Post to include text/turtle (for non-OPTIONS requests)
        response["Accept-Post"] = "application/ld+json, text/turtle"

        # Only add Link headers for successful responses (2xx status codes)
        if 200 <= response.status_code < 300:
            # Add Link headers for LDP resource types
            link_headers = []

            # Preserve existing Link headers (e.g., from pagination) - PUT THESE FIRST
            existing_link = response.get('Link', '')
            if existing_link:
                link_headers.append(existing_link)

            # For detail views (single resource) - use explicit key check
            if self.lookup_field in kwargs:
                link_headers.append('<http://www.w3.org/ns/ldp#Resource>; rel="type"')
                link_headers.append('<http://www.w3.org/ns/ldp#RDFSource>; rel="type"')

            # For container views (list)
            else:
                link_headers.append('<http://www.w3.org/ns/ldp#Resource>; rel="type"')
                link_headers.append('<http://www.w3.org/ns/ldp#RDFSource>; rel="type"')
                link_headers.append('<http://www.w3.org/ns/ldp#Container>; rel="type"')
                link_headers.append('<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"')

            response['Link'] = ', '.join(link_headers)

        if response.status_code in [201, 200] and hasattr(response, 'data') and isinstance(response.data, dict) and '@id' in response.data:
            response["Location"] = str(response.data['@id'])

        if is_authenticated_user(request.user):
            try:
                response['User'] = request.user.urlid
            except AttributeError:
                pass

        # Add Access-Control-Expose-Headers for CORS to allow JavaScript to access LDP headers
        # Preserve any existing expose headers from middleware
        existing_expose = response.get('Access-Control-Expose-Headers', '')

        if existing_expose:
            # Combine existing headers with LDP headers
            existing_list = [h.strip() for h in existing_expose.split(',')]
            # Fix Issue #6: Use dict.fromkeys() for order-preserving deduplication instead of set()
            all_headers = list(dict.fromkeys(existing_list + self.LDP_EXPOSE_HEADERS))
        else:
            all_headers = self.LDP_EXPOSE_HEADERS

        response['Access-Control-Expose-Headers'] = ', '.join(all_headers)

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


class LDPSourceViewSet(LDPViewSet):
    model = LDPSource
    federation = None

    def get_queryset(self, *args, **kwargs):
        return super().get_queryset(*args, **kwargs).filter(federation=self.kwargs['federation'])

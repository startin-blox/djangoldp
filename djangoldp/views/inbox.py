import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.http import Http404
from django.views import View

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.utils import model_meta
from rest_framework.views import APIView

import validators

from djangoldp.activities import (
    ACTIVITY_SAVING_SETTING,
    ActivityPubService,
    ActivityQueueService,
    as_activitystream,
)
from djangoldp.activities.errors import (
    ActivityStreamDecodeError,
    ActivityStreamValidationError,
)
from djangoldp.models import Follower, Model

logger = logging.getLogger('djangoldp')


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

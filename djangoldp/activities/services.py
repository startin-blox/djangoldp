import threading
import json
import requests
from urllib.parse import urlparse
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from rest_framework.utils import model_meta

from djangoldp.models import Model, Follower
from djangoldp.models import Activity as ActivityModel

import logging


logger = logging.getLogger('djangoldp')
BACKLINKS_ACTOR = {
    "type": "Service",
    "name": "Backlinks Service"
}


class ActivityPubService(object):
    '''A service for sending ActivityPub notifications'''

    @classmethod
    def build_object_tree(cls, instance):
        '''builds an object tree from a parameterised instance'''
        model = type(instance)
        info = model_meta.get_field_info(model)

        if not hasattr(instance, 'urlid'):
            return

        obj = {
            "@type": Model.get_model_rdf_type(model),
            "@id": instance.urlid
        }
        if obj['@type'] is None:
            return

        # append relations
        for field_name, relation_info in info.relations.items():
            if not relation_info.to_many:
                value = getattr(instance, field_name, None)
                if value is None:
                    continue

                sub_object = {
                    "@id": value.urlid,
                    "@type": Model.get_model_rdf_type(type(value))
                }

                if sub_object['@type'] is None:
                    continue

                obj[field_name] = sub_object

        return obj

    @classmethod
    def get_actor_from_user_instance(cls, user):
        '''Auxiliary function returns valid Actor object from parameterised user instance, None if parameter invalid'''
        if isinstance(user, get_user_model()) and hasattr(user, 'urlid'):
            return {
                '@type': 'foaf:user',
                '@id': user.urlid
            }
        return None

    @classmethod
    def discover_inbox(cls, target_id):
        url = urlparse(target_id)
        return target_id.replace(url.path, "/") + "inbox/"

    @classmethod
    def _build_activity(self, actor, obj, activity_type='Activity', **kwargs):
        '''Auxiliary function returns an activity object with kwargs in the body'''
        res = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                settings.LDP_RDF_CONTEXT
            ],
            "type": activity_type,
            "actor": actor,
            "object": obj
        }

        for kwarg in kwargs:
            res.update({kwarg: kwargs[kwarg]})

        return res

    @classmethod
    def send_add_activity(cls, actor, obj, target):
        '''
        Sends an Add activity
        :param actor: a valid Actor object
        :param obj: a valid ActivityStreams Object
        :param target: an object representing the target collection
        '''
        summary = str(obj['@id']) + " was added to " + str(target['@id'])
        activity = cls._build_activity(actor, obj, activity_type='Add', summary=summary, target=target)

        # send request
        inbox = ActivityPubService.discover_inbox(target['@id'])
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()
        cls._save_sent_activity(activity)

    @classmethod
    def send_remove_activity(cls, actor, obj, origin):
        '''
        Sends a Remove activity
        :param actor: a valid Actor object, or a user instance
        :param obj: a valid ActivityStreams Object
        :param origin: the context the object has been removed from
        '''
        summary = str(obj['@id']) + " was removed from " + str(origin['@id'])
        activity = cls._build_activity(actor, obj, activity_type='Remove', summary=summary, origin=origin)

        # send request
        inbox = ActivityPubService.discover_inbox(origin['@id'])
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()
        cls._save_sent_activity(activity)

    @classmethod
    def send_create_activity(cls, actor, obj, inbox):
        '''
        Sends a Create activity
        :param actor: a valid Actor object, or a user instance
        :param obj: a valid ActivityStreams Object
        :param inbox: the inbox to send the activity to
        '''
        summary = str(obj['@id']) + " was created"
        activity = cls._build_activity(actor, obj, activity_type='Create', summary=summary)

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()
        cls._save_sent_activity(activity)

    @classmethod
    def send_update_activity(cls, actor, obj, inbox):
        '''
        Sends an Update activity
        :param actor: a valid Actor object, or a user instance
        :param obj: a valid ActivityStreams Object
        :param inbox: the inbox to send the activity to
        '''
        summary = str(obj['@id']) + " was updated"
        activity = cls._build_activity(actor, obj, activity_type='Update', summary=summary)

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()
        cls._save_sent_activity(activity)

    @classmethod
    def send_delete_activity(cls, actor, obj, inbox):
        '''
        Sends a Remove activity
        :param actor: a valid Actor object, or a user instance
        :param obj: a valid ActivityStreams Object
        :param inbox: the inbox to send the activity to
        '''
        summary = str(obj['@id']) + " was deleted"
        activity = cls._build_activity(actor, obj, activity_type='Delete', summary=summary)

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()
        cls._save_sent_activity(activity)

    @classmethod
    def _save_sent_activity(cls, activity):
        '''Auxiliary function saves a record of parameterised activity'''
        payload = bytes(json.dumps(activity), "utf-8")
        local_id = settings.SITE_URL + "/outbox/"
        obj = ActivityModel.objects.create(local_id=local_id, payload=payload)
        obj.aid = Model.absolute_url(obj)
        obj.save()

    @classmethod
    def do_post(cls, url, activity, auth=None):
        '''
        makes a POST request to url, passing activity (json) content
        :return: response, or None if the request was unsuccessful
        '''
        headers = {'Content-Type': 'application/ld+json'}
        response = None
        try:
            logger.debug('[Sender] sending Activity... ' + str(activity))
            if not getattr(settings, 'DISABLE_OUTBOX', False):
                response = requests.post(url, data=json.dumps(activity), headers=headers)
                logger.debug('[Sender] sent, receiver responded ' + response.text)
        except:
            logger.error('Failed to deliver backlink to ' + str(url) +', was attempting ' + str(activity))
        return response

    @classmethod
    def get_related_externals(cls, sender, instance):
        '''Auxiliary function returns a set of urlids of distant resources connected to paramertised instance'''
        info = model_meta.get_field_info(sender)

        # bounds checking
        if not hasattr(instance, 'urlid') or Model.get_model_rdf_type(sender) is None:
            return set()

        # check each foreign key for a distant resource
        targets = set()
        for field_name, relation_info in info.relations.items():
            if not relation_info.to_many:
                value = getattr(instance, field_name, None)
                if value is not None and Model.is_external(value):
                    target_type = Model.get_model_rdf_type(type(value))

                    if target_type is None:
                        continue

                    targets.add(value.urlid)
                    logger.debug('[Sender] model has external relation ' + str(value.urlid))

        return targets

    @classmethod
    def get_target_inboxes(cls, urlids):
        '''Auxiliary function returns a set of inboxes, from a set of target object urlids'''
        inboxes = set()
        for urlid in urlids:
            inboxes.add(ActivityPubService.discover_inbox(urlid))
        return inboxes

    @classmethod
    def get_follower_inboxes(cls, object_urlid):
        '''Auxiliary function returns a set of inboxes, from the followers of parameterised object urlid'''
        inboxes = set(Follower.objects.filter(object=object_urlid).values_list('inbox', flat=True))
        return inboxes

    @classmethod
    def save_follower_for_target(cls, external_urlid, obj_id):
        inbox = ActivityPubService.discover_inbox(external_urlid)

        if not Follower.objects.filter(object=obj_id, follower=external_urlid).exists():
            Follower.objects.create(object=obj_id, inbox=inbox, follower=external_urlid,
                                    is_backlink=True)

    @classmethod
    def save_followers_for_targets(cls, external_urlids, obj_id):
        '''
        saves Follower objects for any external urlid which isn't already following the object in question
        :param external_urlids: list of external urlids to populate the follower inbox
        :param obj_id: object id to be followed
        '''
        existing_followers = Follower.objects.filter(object=obj_id).values_list('follower', flat=True)
        for urlid in external_urlids:
            if urlid not in existing_followers:
                Follower.objects.create(object=obj_id, inbox=ActivityPubService.discover_inbox(urlid),
                                        follower=urlid, is_backlink=True)

    @classmethod
    def remove_followers_for_resource(cls, external_urlid, obj_id):
        '''removes all followers which match the follower urlid, obj urlid combination'''
        inbox = ActivityPubService.discover_inbox(external_urlid)

        for follower in Follower.objects.filter(object=obj_id, follower=external_urlid,
                                                inbox=inbox, is_backlink=True):
            follower.delete()


@receiver([post_save])
def check_save_for_backlinks(sender, instance, created, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True) and getattr(instance, 'allow_create_backlink', False) \
            and not Model.is_external(instance) \
            and getattr(instance, 'username', None) != 'hubl-workaround-493':
        external_urlids = ActivityPubService.get_related_externals(sender, instance)
        inboxes = ActivityPubService.get_follower_inboxes(instance.urlid)
        targets = set().union(ActivityPubService.get_target_inboxes(external_urlids), inboxes)

        if len(targets) > 0:
            obj = ActivityPubService.build_object_tree(instance)
            actor = BACKLINKS_ACTOR
            # Create Activity
            if created:
                for target in targets:
                    ActivityPubService.send_create_activity(actor, obj, target)
            # Update Activity
            else:
                for target in targets:
                    ActivityPubService.send_update_activity(actor, obj, target)

            # create Followers to update external resources of changes in future
            ActivityPubService.save_followers_for_targets(external_urlids, obj['@id'])


@receiver([post_delete])
def check_delete_for_backlinks(sender, instance, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True) and getattr(instance, 'allow_create_backlink', False) \
            and getattr(instance, 'username', None) != 'hubl-workaround-493':
        targets = ActivityPubService.get_follower_inboxes(instance.urlid)

        if len(targets) > 0:
            for target in targets:
                ActivityPubService.send_delete_activity(BACKLINKS_ACTOR, {
                    "@id": instance.urlid,
                    "@type": Model.get_model_rdf_type(sender)
                }, target)

    # remove any Followers on this resource
    urlid = getattr(instance, 'urlid', None)
    if urlid is not None:
        for follower in Follower.objects.filter(object=urlid):
            follower.delete()


@receiver([m2m_changed])
def check_m2m_for_backlinks(sender, instance, action, *args, **kwargs):
    def build_targets(query_set):
        '''analyses parameterised queryset (removed or added members) for backlinks'''
        targets = []

        for obj in query_set:
            condition = Model.is_external(obj) and getattr(obj, 'allow_create_backlink', False)
            if action == "post_add":
                condition = condition and not getattr(obj, 'is_backlink', True)

            if condition:
                targets.append({
                    "@type": member_rdf_type,
                    "@id": obj.urlid
                })

        return targets

    if getattr(settings, 'SEND_BACKLINKS', True):
        member_model = kwargs['model']
        pk_set = kwargs['pk_set']

        # we can only send backlinks on pre_clear because on post_clear the objects are gone
        if action != "pre_clear" and pk_set is None:
            return
        member_rdf_type = Model.get_model_rdf_type(member_model)
        container_rdf_type = Model.get_model_rdf_type(type(instance))

        if member_rdf_type is None:
            return
        if container_rdf_type is None:
            return

        # build list of targets (models affected by the change)
        if action == "pre_clear":
            pk_set = sender.objects.all().values_list(member_model.__name__.lower(), flat=True)
        query_set = member_model.objects.filter(pk__in=pk_set)
        targets = build_targets(query_set)

        logger.debug('[Sender] checking many2many for backlinks')
        logger.debug('[Sender] built targets: ' + str(targets))

        if len(targets) > 0:
            obj = {
                "@type": container_rdf_type,
                "@id": instance.urlid
            }
            if action == 'post_add':
                for target in targets:
                    ActivityPubService.send_add_activity(BACKLINKS_ACTOR, obj, target)
                    ActivityPubService.save_follower_for_target(target['@id'], obj['@id'])

            elif action == "post_remove" or action == "pre_clear":
                for target in targets:
                    ActivityPubService.send_remove_activity(BACKLINKS_ACTOR, obj, target)
                    ActivityPubService.remove_followers_for_resource(target['@id'], obj['@id'])

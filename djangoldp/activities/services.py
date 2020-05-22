import threading
from urllib.parse import urlparse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from rest_framework.utils import model_meta

from djangoldp.models import Model, Follower

from .objects import *
from .verbs import *
import logging


logger = logging.getLogger('djangoldp')


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
            logger.warning('[Backlink-Creation] model ' + str(model) + ' has no rdf_type')
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
                    logger.warning('[Backlink-Creation] model ' + str(type(value)) + ' has no rdf_type')
                    continue

                obj[field_name] = sub_object

        return obj

    @classmethod
    def _discover_inbox(cls, target_id):
        url = urlparse(target_id)
        return target_id.replace(url.path, "/") + "inbox/"

    @classmethod
    def send_add_activity(cls, actor, object, target):
        '''
        Sends an Add activity
        :param actor: a valid Actor object, or a user instance
        :param object: a valid ActivityStreams Object
        :param target: an object representing the target collection
        '''
        # bounds checking
        if isinstance(actor, get_user_model()):
            actor = {
                '@type': 'foaf:user',
                '@id': actor.urlid
            }

        summary = str(object['@id']) + " was added to " + str(target['@id'])

        activity = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                settings.LDP_RDF_CONTEXT
            ],
            "summary": summary,
            "type": "Add",
            "actor": actor,
            "object": object,
            "target": target
        }

        logger.debug('[Sender] sending add activity ' + str(activity))

        inbox = ActivityPubService._discover_inbox(target['@id'])

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()

    @classmethod
    def send_remove_activity(cls, actor, object, origin):
        '''
        Sends a Remove activity
        :param actor: a valid Actor object, or a user instance
        :param object: a valid ActivityStreams Object
        :param origin: the context the object has been removed from
        '''
        # bounds checking
        if isinstance(actor, get_user_model()):
            actor = {
                '@type': 'foaf:user',
                '@id': actor.urlid
            }

        summary = str(object['@id']) + " was removed from " + str(origin['@id'])

        activity = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                settings.LDP_RDF_CONTEXT
            ],
            "summary": summary,
            "type": "Remove",
            "actor": actor,
            "object": object,
            "origin": origin
        }

        logger.debug('[Sender] sending remove activity ' + str(activity))

        inbox = ActivityPubService._discover_inbox(origin['@id'])

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()

    @classmethod
    def send_create_activity(cls, actor, object, inbox):
        '''
        Sends a Create activity
        :param actor: a valid Actor object, or a user instance
        :param object: a valid ActivityStreams Object
        :param inbox: the inbox to send the activity to
        '''
        # bounds checking
        if isinstance(actor, get_user_model()):
            actor = {
                '@type': 'foaf:user',
                '@id': actor.urlid
            }

        summary = str(object['@id']) + " was created"

        activity = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                settings.LDP_RDF_CONTEXT
            ],
            "summary": summary,
            "type": "Create",
            "actor": actor,
            "object": object
        }

        logger.debug('[Sender] sending create activity ' + str(activity))

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()

    @classmethod
    def send_update_activity(cls, actor, object, inbox):
        '''
        Sends an Update activity
        :param actor: a valid Actor object, or a user instance
        :param object: a valid ActivityStreams Object
        :param inbox: the inbox to send the activity to
        '''
        # bounds checking
        if isinstance(actor, get_user_model()):
            actor = {
                '@type': 'foaf:user',
                '@id': actor.urlid
            }

        summary = str(object['@id']) + " was created"

        activity = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                settings.LDP_RDF_CONTEXT
            ],
            "summary": summary,
            "type": "Update",
            "actor": actor,
            "object": object
        }

        logger.debug('[Sender] sending update activity ' + str(activity))

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()

    @classmethod
    def send_delete_activity(cls, actor, object, inbox):
        '''
        Sends a Remove activity
        :param actor: a valid Actor object, or a user instance
        :param object: a valid ActivityStreams Object
        :param inbox: the inbox to send the activity to
        '''
        # bounds checking
        if isinstance(actor, get_user_model()):
            actor = {
                '@type': 'foaf:user',
                '@id': actor.urlid
            }

        summary = str(object['@id']) + " was deleted"

        activity = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                settings.LDP_RDF_CONTEXT
            ],
            "summary": summary,
            "type": "Delete",
            "actor": actor,
            "object": object
        }

        logger.debug('[Sender] sending delete activity ' + str(activity))

        # send request
        t = threading.Thread(target=cls.do_post, args=[inbox, activity])
        t.start()

    @classmethod
    def do_post(cls, url, activity, auth=None):
        '''makes a POST request to passed url'''
        headers = {'Content-Type': 'application/ld+json'}
        response = None
        try:
            response = requests.post(url, data=json.dumps(activity), headers=headers)
            logger.debug('[Sender] sent, receiver responded ' + response.text)
        except:
            logger.error('Failed to deliver backlink to ' + str(url) +', was attempting ' + str(activity))
        return response


def _check_instance_for_backlinks(sender, instance):
    '''Auxiliary function returns a dictionary of backlink targets from paramertised instance'''
    info = model_meta.get_field_info(sender)

    # bounds checking
    if not hasattr(instance, 'urlid') or Model.get_model_rdf_type(sender) is None:
        logger.warning('[Create-Backlink] model ' + str(sender) + ' has no rdf_type')
        return {}

    # check each foreign key for a distant resource
    targets = {}
    for field_name, relation_info in info.relations.items():
        if not relation_info.to_many:
            value = getattr(instance, field_name, None)
            logger.debug('[Sender] model has relation ' + str(value))
            if value is not None and Model.is_external(value):
                target_type = Model.get_model_rdf_type(type(value))

                if target_type is None:
                    logger.warning('[Create-Backlink] model ' + str(type(value)) + ' has no rdf_type')
                    continue

                targets[value.urlid] = ActivityPubService._discover_inbox(value.urlid)

    # append Followers as targets
    followers = Follower.objects.filter(object=instance.urlid)
    for follower in followers:
        targets[follower.inbox] = follower.inbox

    logger.debug('[Sender] built dict of targets: ' + str(targets))
    return targets


@receiver([post_save])
def check_save_for_backlinks(sender, instance, created, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True) and not getattr(instance, 'is_backlink', False) \
            and getattr(instance, 'allow_create_backlink', False)\
            and getattr(instance, 'username', None) != 'hubl-workaround-493':
        logger.debug("[Sender] Received created non-backlink instance " + str(instance) + "(" + str(sender) + ")")
        targets = _check_instance_for_backlinks(sender, instance)

        if len(targets.items()) > 0:
            obj = ActivityPubService.build_object_tree(instance)
            actor = {
                "type": "Service",
                "name": "Backlinks Service"
            }
            # Create Activity
            if created:
                for key in targets.keys():
                    ActivityPubService.send_create_activity(actor, obj, targets[key])
                    Follower.objects.create(object=obj['@id'], inbox=targets[key])
            # Update Activity
            else:
                for key in targets.keys():
                    ActivityPubService.send_update_activity(actor, obj, targets[key])
                    if not Follower.objects.filter(object=obj['@id'], inbox=targets[key]).exists():
                        Follower.objects.create(object=obj['@id'], inbox=targets[key])


@receiver([post_delete])
def check_delete_for_backlinks(sender, instance, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True) and getattr(instance, 'allow_create_backlink', False) \
            and getattr(instance, 'username', None) != 'hubl-workaround-493':
        logger.debug("[Sender] Received deleted non-backlink instance " + str(instance) + "(" + str(sender) + ")")
        targets = _check_instance_for_backlinks(sender, instance)

        if len(targets.items()) > 0:
            for key in targets.keys():
                ActivityPubService.send_delete_activity({
                    "type": "Service",
                    "name": "Backlinks Service"
                }, {
                    "@id": instance.urlid,
                    "@type": Model.get_model_rdf_type(sender)
                }, targets[key])

    # remove any Followers on this resource
    urlid = getattr(instance, 'urlid', None)
    if urlid is not None:
        for follower in Follower.objects.filter(object=urlid):
            follower.delete()


@receiver([m2m_changed])
def check_m2m_for_backlinks(sender, instance, action, *args, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True):
        member_model = kwargs['model']
        pk_set = kwargs['pk_set']
        if pk_set is None:
            return
        member_rdf_type = Model.get_model_rdf_type(member_model)
        container_rdf_type = Model.get_model_rdf_type(type(instance))

        if member_rdf_type is None:
            logger.warning('[Backlink-Creation] model ' + str(member_model) + ' has no rdf_type')
            return
        if container_rdf_type is None:
            logger.warning('[Backlink-Creation] model ' + str(type(instance)) + ' has no rdf_type')
            return

        # build list of targets (models affected by the change)
        query_set = member_model.objects.filter(pk__in=pk_set)
        targets = []

        for obj in query_set:
            condition = Model.is_external(obj) and getattr(obj, 'allow_create_backlink', False)
            if action == "post_add":
                condition = condition and not getattr(instance, 'is_backlink', False)

            if condition:
                targets.append({
                    "@type": member_rdf_type,
                    "@id": obj.urlid
                })

        logger.debug('[Sender] checking many2many for backlinks')
        logger.debug('[Sender] built targets: ' + str(targets))

        if len(targets) > 0:
            obj = {
                "@type": container_rdf_type,
                "@id": instance.urlid
            }
            if action == 'post_add':
                for target in targets:
                    ActivityPubService.send_add_activity({
                        "type": "Service",
                        "name": "Backlinks Service"
                    }, obj, target)

            elif action == "post_remove":
                for target in targets:
                    ActivityPubService.send_remove_activity({
                        "type": "Service",
                        "name": "Backlinks Service"
                    }, obj, target)

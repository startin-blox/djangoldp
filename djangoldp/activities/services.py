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

        summary = str(object['@id']) + " was updated"

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
    '''Auxiliary function returns a set of backlink targets from paramertised instance'''
    info = model_meta.get_field_info(sender)

    # bounds checking
    if not hasattr(instance, 'urlid') or Model.get_model_rdf_type(sender) is None:
        return {}

    # check each foreign key for a distant resource
    targets = set()
    for field_name, relation_info in info.relations.items():
        if not relation_info.to_many:
            value = getattr(instance, field_name, None)
            logger.debug('[Sender] model has relation ' + str(value))
            if value is not None and Model.is_external(value):
                target_type = Model.get_model_rdf_type(type(value))

                if target_type is None:
                    continue

                targets.add(ActivityPubService._discover_inbox(value.urlid))

    # append Followers as targets
    followers = Follower.objects.filter(object=instance.urlid)
    for follower in followers:
        targets.add(follower.inbox)

    logger.debug('[Sender] built set of targets: ' + str(targets))
    return targets


@receiver([post_save])
def check_save_for_backlinks(sender, instance, created, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True) and getattr(instance, 'allow_create_backlink', False) \
            and not Model.is_external(instance) \
            and getattr(instance, 'username', None) != 'hubl-workaround-493':
        logger.debug("[Sender] Received created non-backlink instance " + str(instance) + "(" + str(sender) + ")")
        targets = _check_instance_for_backlinks(sender, instance)

        if len(targets) > 0:
            obj = ActivityPubService.build_object_tree(instance)
            actor = {
                "type": "Service",
                "name": "Backlinks Service"
            }
            # Create Activity
            if created:
                for target in targets:
                    ActivityPubService.send_create_activity(actor, obj, target)
                    Follower.objects.create(object=obj['@id'], inbox=target)
            # Update Activity
            else:
                for target in targets:
                    ActivityPubService.send_update_activity(actor, obj, target)
                    if not Follower.objects.filter(object=obj['@id'], inbox=target).exists():
                        Follower.objects.create(object=obj['@id'], inbox=target)


@receiver([post_delete])
def check_delete_for_backlinks(sender, instance, **kwargs):
    if getattr(settings, 'SEND_BACKLINKS', True) and getattr(instance, 'allow_create_backlink', False) \
            and getattr(instance, 'username', None) != 'hubl-workaround-493':
        logger.debug("[Sender] Received deleted non-backlink instance " + str(instance) + "(" + str(sender) + ")")
        targets = _check_instance_for_backlinks(sender, instance)

        if len(targets) > 0:
            for target in targets:
                ActivityPubService.send_delete_activity({
                    "type": "Service",
                    "name": "Backlinks Service"
                }, {
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
                condition = condition and not Model.is_external(instance)

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
                    ActivityPubService.send_add_activity({
                        "type": "Service",
                        "name": "Backlinks Service"
                    }, obj, target)

            elif action == "post_remove" or action == "pre_clear":
                for target in targets:
                    ActivityPubService.send_remove_activity({
                        "type": "Service",
                        "name": "Backlinks Service"
                    }, obj, target)

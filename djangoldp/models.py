import json
import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError, FieldDoesNotExist
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.signals import post_save, pre_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.urls import get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import classonlymethod
from guardian.shortcuts import assign_perm
from rest_framework.utils import model_meta
from djangoldp.fields import LDPUrlField
from djangoldp.permissions import DEFAULT_DJANGOLDP_PERMISSIONS, OwnerPermissions, InheritPermissions, ReadOnly

logger = logging.getLogger('djangoldp')

Group._meta.serializer_fields = ['name', 'user_set']
Group._meta.rdf_type = 'foaf:Group'
# Group._meta.rdf_context = {'user_set': 'foaf:member'}
Group._meta.permission_classes = [(OwnerPermissions&ReadOnly)|InheritPermissions]
Group._meta.owner_field = 'user'
Group._meta.inherit_permissions = []

class LDPModelManager(models.Manager):
    def local(self):
        '''an alternative to all() which exlcudes external resources'''
        queryset = super(LDPModelManager, self).all()
        internal_ids = [x.pk for x in queryset if not Model.is_external(x)]
        return queryset.filter(pk__in=internal_ids)

class Model(models.Model):
    urlid = LDPUrlField(blank=True, null=True, unique=True, db_index=True)
    is_backlink = models.BooleanField(default=False, help_text='set automatically to indicate the Model is a backlink')
    allow_create_backlink = models.BooleanField(default=True,
                                                help_text='set to False to disable backlink creation after Model save')
    objects = LDPModelManager()

    class Meta:
        default_permissions = DEFAULT_DJANGOLDP_PERMISSIONS
        abstract = True
        depth = 0

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)

    @classmethod
    def get_container_path(cls):
        '''returns the url path which is used to access actions on this model (e.g. /users/)'''
        path = getattr(cls._meta, 'container_path', getattr(cls.Meta, 'container_path', None))
        if path is None:
            path = "{}s".format(cls._meta.object_name.lower())

        return cls.__clean_path(path)

    def get_absolute_url(self):
        return Model.absolute_url(self)

    @classonlymethod
    def absolute_url(cls, instance_or_model):
        if isinstance(instance_or_model, ModelBase) or not instance_or_model.urlid:
            return '{}{}'.format(settings.SITE_URL, Model.resource(instance_or_model))
        else:
            return instance_or_model.urlid

    def get_container_id(self):
        return Model.container_id(self)

    @classonlymethod
    def resource(cls, instance_or_model):
        if isinstance(instance_or_model, ModelBase):
            return cls.container_id(instance_or_model)
        else:
            return cls.resource_id(instance_or_model)

    @classonlymethod
    def resource_id(cls, instance):
        r_id = "{}{}".format(cls.container_id(instance), getattr(instance, cls.slug_field(instance), ""))
        return cls.__clean_path(r_id)

    @classonlymethod
    def slug_field(cls, instance_or_model):
        if isinstance(instance_or_model, ModelBase):
            model = instance_or_model
        else:
            model = type(instance_or_model)
        
        # Use cached value if present
        if hasattr(model, "_slug_field"):
            return model._slug_field
        object_name = model.__name__.lower()
        view_name = '{}-detail'.format(object_name)

        try:
            slug_field = '/{}'.format(get_resolver().reverse_dict[view_name][0][0][1][0])
        except MultiValueDictKeyError:
            slug_field = getattr(model._meta, 'lookup_field', 'pk')
        if slug_field.startswith('/'):
            slug_field = slug_field[1:]
        
        model._slug_field = slug_field
        return slug_field

    @classonlymethod
    def container_id(cls, instance):
        if isinstance(instance, cls):
            path = instance.get_container_path()
        else:
            view_name = '{}-list'.format(instance._meta.object_name.lower())
            path = get_resolver().reverse(view_name)

        path = cls.__clean_path(path)

        return path

    @classonlymethod
    def resolve_id(cls, id):
        '''
        Resolves the id of a given path (e.g. /container/1/)
        Raises Resolver404 if the path cannot be found, ValidationError if the path is for a model base
        and an ObjectDoesNotExist exception if the resource does not exist
        '''
        id = cls.__clean_path(id)
        match = get_resolver().resolve(id)
        kwargs = match.kwargs
        view = match.func

        if match.url_name.endswith('-list') or len(match.kwargs.keys()) == 0:
            raise ValidationError('resolve_id received a path for a container or nested container')
        return view.initkwargs['model'].objects.get(**kwargs)

    @classonlymethod
    def resolve_parent(cls, path):
        split = path.strip('/').split('/')
        parent_path = "/".join(split[:-1])
        return Model.resolve_id(parent_path)

    @classonlymethod
    def resolve_container(cls, path):
        '''retruns the model container of passed URL path'''
        path = cls.__clean_path(path)
        view, args, kwargs = get_resolver().resolve(path)
        return view.initkwargs['model']

    @classonlymethod
    def resolve(cls, path):
        '''
        resolves the containing model and associated id in the path. If there is no id in the path returns None
        :param path: a URL path to check
        :return: the container model and resolved id in a tuple
        '''
        if path.startswith(settings.BASE_URL):
            path = path.replace(settings.BASE_URL, '')
        container = cls.resolve_container(path)
        try:
            resolve_id = cls.resolve_id(path)
        except:
            resolve_id = None
        return container, resolve_id

    @classonlymethod
    def __clean_path(cls, path):
        '''ensures path is Django-friendly'''
        if not path.startswith("/"):
            path = "/{}".format(path)
        if not path.endswith("/"):
            path = "{}/".format(path)
        return path

    @classonlymethod
    def get_or_create(cls, model, urlid, update=False, **field_tuples):
        '''
        gets an object with the passed urlid if it exists, creates it if not
        :param model: the model class which the object belongs to
        :param update: if set to True the object will be updated with the passed field_tuples
        :param field_tuples: kwargs for the model creation/updating
        :return: the object, fetched or created
        :raises Exception: if the object does not exist, but the data passed is invalid
        '''
        try:
            rval = model.objects.get(urlid=urlid)
            if update:
                for field in field_tuples.keys():
                    setattr(rval, field, field_tuples[field])
                rval.save()
            return rval
        except ObjectDoesNotExist:
            if model is get_user_model():
                field_tuples['username'] = str(uuid.uuid4())
            return model.objects.create(urlid=urlid, is_backlink=True, **field_tuples)

    @classonlymethod
    def get_or_create_external(cls, model, urlid, **kwargs):
        '''
        checks that the parameterised urlid is external and then returns the result of Model.get_or_create
        :raises ObjectDoesNotExist: if the urlid is not external and the object doesn't exist
        '''
        if not Model.is_external(urlid) and not model.objects.filter(urlid=urlid).exists():
            raise ObjectDoesNotExist
        return Model.get_or_create(model, urlid, **kwargs)

    @classonlymethod
    def get_subclass_with_rdf_type(cls, type):
        #TODO: deprecate
        '''returns Model subclass with Meta.rdf_type matching parameterised type, or None'''
        if type == 'foaf:user':
            return get_user_model()

        for subcls in Model.__subclasses__():
            if getattr(subcls._meta, "rdf_type", None) == type:
                return subcls

        return None

    @classmethod
    def is_external(cls, value):
        '''
        :param value: string urlid or an instance with urlid field
        :return: True if the urlid is external to the server, False otherwise
        '''
        try:
            if not value:
                return False
            if not isinstance(value, str):
                value = value.urlid

            # This expects all @ids to start with http which mlight not be universal. Maybe needs a fix.
            return value.startswith('http') and not value.startswith(settings.SITE_URL)
        except:
            return False

#TODO: this breaks the serializer, which probably assumes that traditional models don't have a urlid.
# models.Model.urlid = property(lambda self: '{}{}'.format(settings.SITE_URL, Model.resource(self)))

class LDPSource(Model):
    federation = models.CharField(max_length=255)

    class Meta(Model.Meta):
        rdf_type = 'sib:federatedContainer'
        ordering = ('federation',)
        container_path = 'sources'
        lookup_field = 'federation'

    def __str__(self):
        return "{}: {}".format(self.federation, self.urlid)


class Activity(Model):
    '''Models an ActivityStreams Activity'''
    local_id = LDPUrlField(help_text='/inbox or /outbox url (local - this server)')  # /inbox or /outbox full url
    external_id = LDPUrlField(null=True, help_text='the /inbox or /outbox url (from the sender or receiver)')
    payload = models.TextField()
    response_location = LDPUrlField(null=True, blank=True, help_text='Location saved activity can be found')
    response_code = models.CharField(null=True, blank=True, help_text='Response code sent by receiver', max_length=8)
    response_body = models.TextField(null=True)
    type = models.CharField(null=True, blank=True, help_text='the ActivityStreams type of the Activity',
                            max_length=64)
    is_finished = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False, help_text='set to True when an Activity is successfully delivered')

    class Meta(Model.Meta):
        container_path = "activities"
        rdf_type = 'as:Activity'

    def to_activitystream(self):
        return json.loads(self.payload)

    def response_to_json(self):
        return self.to_activitystream()


# temporary database-side storage used for scheduled tasks in the ActivityQueue
class ScheduledActivity(Activity):
    failed_attempts = models.PositiveIntegerField(default=0,
                                                  help_text='a log of how many failed retries have been made sending the activity')

    def save(self, *args, **kwargs):
        self.is_finished = False
        super(ScheduledActivity, self).save(*args, **kwargs)


class Follower(Model):
    '''Models a subscription on a model. When the model is saved, an Update activity will be sent to the inbox'''
    object = models.URLField(help_text='the object being followed')
    inbox = models.URLField(help_text='the inbox recipient of updates')
    follower = models.URLField(help_text='(optional) the resource/actor following the object', blank=True)

    def __str__(self):
        return 'Inbox ' + str(self.inbox) + ' on ' + str(self.object)

class DynamicNestedField:
    '''
    Used to define a method as a nested_field.
    Usage:
        LDPUser.circles = lambda self: Circle.objects.filter(members__user=self)
        LDPUser.circles.field = DynamicNestedField(Circle, 'circles')
    '''
    related_query_name = None
    one_to_many = False
    many_to_many = True
    many_to_one = False
    one_to_one = False
    read_only = True
    name = ''
    def __init__(self, model:models.Model|None, remote_name:str, name:str='', remote:object|None=None) -> None:
        self.model = model
        self.name = name
        if remote:
            self.remote_field = remote
        else:
            self.remote_field = DynamicNestedField(None, '', remote_name, self)

@receiver([post_save])
def auto_urlid(sender, instance, **kwargs):
    if isinstance(instance, Model):
        changed = False
        if getattr(instance, Model.slug_field(instance), None) is None:
            setattr(instance, Model.slug_field(instance), instance.pk)
            changed = True
        if (not instance.urlid or 'None' in instance.urlid):
            instance.urlid = instance.get_absolute_url()
            changed = True
        if changed:
            instance.save()

@receiver(post_save)
def create_role_groups(sender, instance, created, **kwargs):
    if created:
        for name, params in getattr(instance._meta, 'permission_roles', {}).items():
            group = Group.objects.create(name=f'LDP_{instance._meta.model_name}_{name}_{instance.id}')
            setattr(instance, name, group)
            instance.save()
            if params.get('add_author'):
                assert hasattr(instance._meta, 'auto_author'), "add_author requires to also define auto_author"
                author = getattr(instance, instance._meta.auto_author)
                if author:
                    group.user_set.add(author)
            for permission in params.get('perms', []):
                assign_perm(f'{permission}_{instance._meta.model_name}', group, instance)


def invalidate_cache_if_has_entry(entry):
    from djangoldp.serializers import GLOBAL_SERIALIZER_CACHE

    if GLOBAL_SERIALIZER_CACHE.has(entry):
        GLOBAL_SERIALIZER_CACHE.invalidate(entry)

def invalidate_model_cache_if_has_entry(model):
    entry = getattr(model._meta, 'label', None)
    invalidate_cache_if_has_entry(entry)

@receiver([pre_save, pre_delete])
def invalidate_caches(sender, instance, **kwargs):
    invalidate_model_cache_if_has_entry(sender)

@receiver([m2m_changed])
def invalidate_caches_m2m(sender, instance, action, *args, **kwargs):
    invalidate_model_cache_if_has_entry(kwargs['model'])
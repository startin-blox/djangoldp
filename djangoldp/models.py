import json
import logging
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import BinaryField, DateTimeField
from django.db.models.base import ModelBase
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse_lazy, get_resolver, NoReverseMatch
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import classonlymethod
from rest_framework.utils import model_meta

from djangoldp.fields import LDPUrlField
from djangoldp.permissions import LDPPermissions

logger = logging.getLogger('djangoldp')


class LDPModelManager(models.Manager):
    def local(self):
        '''an alternative to all() which exlcudes external resources'''
        queryset = super(LDPModelManager, self).all()
        internal_ids = [x.pk for x in queryset if not Model.is_external(x)]
        return queryset.filter(pk__in=internal_ids)

    def nested_fields(self):
        '''parses the relations on the model, and returns a list of nested field names'''
        nested_fields = set()
        # include all many-to-many relations
        for field_name, relation_info in model_meta.get_field_info(self.model).relations.items():
            if relation_info.to_many:
                if field_name is not None:
                    nested_fields.add(field_name)
        # include all nested fields explicitly included on the model
        nested_fields.update(set(Model.get_meta(self.model, 'nested_fields', set())))
        # exclude anything marked explicitly to be excluded
        nested_fields = nested_fields.difference(set(Model.get_meta(self.model, 'nested_fields_exclude', set())))
        return list(nested_fields)

    def fields(self):
        return self.nested_fields()


class Model(models.Model):
    urlid = LDPUrlField(blank=True, null=True, unique=True)
    is_backlink = models.BooleanField(default=False, help_text='set automatically to indicate the Model is a backlink')
    allow_create_backlink = models.BooleanField(default=True,
                                                help_text='set to False to disable backlink creation after Model save')
    objects = LDPModelManager()
    nested = LDPModelManager()

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)

    @classmethod
    def get_view_set(cls):
        '''returns the view_set defined in the model Meta or the LDPViewSet class'''
        view_set = getattr(cls._meta, 'view_set', getattr(cls.Meta, 'view_set', None))
        if view_set is None:
            from djangoldp.views import LDPViewSet
            view_set = LDPViewSet
        return view_set

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
        if isinstance(instance_or_model, ModelBase) or instance_or_model.urlid is None or instance_or_model.urlid == '':
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
            object_name = instance_or_model.__name__.lower()
        else:
            object_name = instance_or_model._meta.object_name.lower()
        view_name = '{}-detail'.format(object_name)
        try:
            slug_field = '/{}'.format(get_resolver().reverse_dict[view_name][0][0][1][0])
        except MultiValueDictKeyError:
            slug_field = Model.get_meta(instance_or_model, 'lookup_field', 'pk')
        if slug_field.startswith('/'):
            slug_field = slug_field[1:]
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

    class Meta:
        default_permissions = ('add', 'change', 'delete', 'view', 'control')
        abstract = True
        depth = 0

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
        parent_path = "/".join(split[0:len(split) - 1])
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
        if settings.BASE_URL in path:
            path = path[len(settings.BASE_URL):]
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
    def get_model_rdf_type(cls, model):
        if model is get_user_model():
            return "foaf:user"
        else:
            return Model.get_meta(model, "rdf_type")

    @classonlymethod
    def get_subclass_with_rdf_type(cls, type):
        '''returns Model subclass with Meta.rdf_type matching parameterised type, or None'''
        if type == 'foaf:user':
            return get_user_model()

        for subcls in Model.__subclasses__():
            if Model.get_meta(subcls, 'rdf_type') == type:
                return subcls

        return None

    @classonlymethod
    def get_permission_classes(cls, related_model, default_permissions_classes):
        '''returns the permission_classes set in the models Meta class'''
        return cls.get_meta(related_model, 'permission_classes', default_permissions_classes)

    @classonlymethod
    def get_meta(cls, model_class, meta_name, default=None):
        '''returns the models Meta class'''
        if hasattr(model_class, 'Meta'):
            meta = getattr(model_class.Meta, meta_name, default)
        else:
            meta = default
        return getattr(model_class._meta, meta_name, meta)

    @staticmethod
    def get_permissions(obj_or_model, context, filter):
        permissions = filter
        for permission_class in Model.get_permission_classes(obj_or_model, [LDPPermissions]):
            permissions = permission_class().filter_user_perms(context, obj_or_model, permissions)
        return [{'mode': {'@type': name.split('_')[0]}} for name in permissions]

    @classmethod
    def is_external(cls, value):
        '''
        :param value: string urlid or an instance with urlid field
        :return: True if the urlid is external to the server, False otherwise
        '''
        try:
            if not isinstance(value, str):
                value = value.urlid

            return value is not None and not value.startswith(settings.SITE_URL)
        except:
            return False


class LDPSource(Model):
    federation = models.CharField(max_length=255)

    class Meta(Model.Meta):
        rdf_type = 'ldp:Container'
        ordering = ('federation',)
        container_path = 'sources'
        lookup_field = 'federation'

    def __str__(self):
        return "{}: {}".format(self.federation, self.urlid)


class Activity(Model):
    '''Models an ActivityStreams Activity'''
    local_id = LDPUrlField(help_text='/inbox or /outbox url (local - this server)')  # /inbox or /outbox full url
    external_id = LDPUrlField(null=True, help_text='the /inbox or /outbox url (from the sender or receiver)')
    payload = BinaryField()
    response_location = LDPUrlField(null=True, blank=True, help_text='Location saved activity can be found')
    response_code = models.CharField(null=True, blank=True, help_text='Response code sent by receiver', max_length=8)
    response_body = BinaryField(null=True)
    type = models.CharField(null=True, blank=True, help_text='the ActivityStreams type of the Activity',
                            max_length=64)
    is_finished = models.BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False, help_text='set to True when an Activity is successfully delivered')

    class Meta(Model.Meta):
        container_path = "activities"
        rdf_type = 'as:Activity'

    def _bytes_to_json(self, obj):
        if hasattr(obj, 'tobytes'):
            obj = obj.tobytes()
        if obj is None or obj == b'':
            return {}
        return json.loads(obj)

    def to_activitystream(self):
        return self._bytes_to_json(self.payload)

    def response_to_json(self):
        return self._bytes_to_json(self.response_body)


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


@receiver([post_save])
def auto_urlid(sender, instance, **kwargs):
    if isinstance(instance, Model):
        if getattr(instance, Model.slug_field(instance), None) is None:
            setattr(instance, Model.slug_field(instance), instance.pk)
            instance.save()
        if (instance.urlid is None or instance.urlid == '' or 'None' in instance.urlid):
            instance.urlid = instance.get_absolute_url()
            instance.save()


if 'djangoldp_account' not in settings.DJANGOLDP_PACKAGES:
    def webid(self):
        # an external user should have urlid set
        webid = getattr(self, 'urlid', None)
        if webid is not None and urlparse(settings.BASE_URL).netloc != urlparse(webid).netloc:
            webid = self.urlid
        # local user use user-detail URL with primary key
        else:
            webid = '{0}{1}'.format(settings.BASE_URL, reverse_lazy('user-detail', kwargs={'pk': self.pk}))
        return webid


    get_user_model().webid = webid


@receiver(pre_save)
def invalidate_caches(instance, **kwargs):
    if isinstance(instance, Model):
        from djangoldp.serializers import LDListMixin, LDPSerializer
        LDPPermissions.invalidate_cache()
        LDListMixin.to_representation_cache.reset()
        LDPSerializer.to_representation_cache.reset()

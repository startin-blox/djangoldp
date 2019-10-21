import validators
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse_lazy, get_resolver
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.decorators import classonlymethod

from djangoldp.fields import LDPUrlField
from djangoldp.permissions import LDPPermissions


class Model(models.Model):
    urlid = LDPUrlField(blank=True, null=True, unique=True)

    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)

    @classmethod
    def get_view_set(cls):
        view_set = getattr(cls._meta, 'view_set', getattr(cls.Meta, 'view_set', None))
        if view_set is None:
            from djangoldp.views import LDPViewSet
            view_set = LDPViewSet
        return view_set

    @classmethod
    def get_container_path(cls):
        path = getattr(cls._meta, 'container_path', getattr(cls.Meta, 'container_path', None))
        if path is None:
            path = "{}s".format(cls._meta.object_name.lower())

        return cls.__clean_path(path)

    def get_absolute_url(self):
        return Model.absolute_url(self)

    @classonlymethod
    def absolute_url(cls, instance_or_model):
        if isinstance(instance_or_model, ModelBase) or instance_or_model.urlid is None or instance_or_model.urlid == '':
            return '{}{}'.format(settings.BASE_URL, Model.resource(instance_or_model))
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
        id = cls.__clean_path(id)
        view, args, kwargs = get_resolver().resolve(id)
        return view.initkwargs['model'].objects.get(**kwargs)

    @classonlymethod
    def resolve_parent(cls, path):
        split = path.strip('/').split('/')
        parent_path = "/".join(split[0:len(split) - 1])
        return Model.resolve_id(parent_path)

    @classonlymethod
    def resolve_container(cls, path):
        path = cls.__clean_path(path)
        view, args, kwargs = get_resolver().resolve(path)
        return view.initkwargs['model']

    @classonlymethod
    def resolve(cls, path):
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
        if not path.startswith("/"):
            path = "/{}".format(path)
        if not path.endswith("/"):
            path = "{}/".format(path)
        return path

    @classonlymethod
    def get_permission_classes(cls, related_model, default_permissions_classes):
        return cls.get_meta(related_model, 'permission_classes', default_permissions_classes)

    @classonlymethod
    def get_meta(cls, model_class, meta_name, default=None):
        if hasattr(model_class, 'Meta'):
            meta = getattr(model_class.Meta, meta_name, default)
        else:
            meta = default
        return getattr(model_class._meta, meta_name, meta)

    @staticmethod
    def get_permissions(obj_or_model, user_or_group, filter):
        permissions = filter
        for permission_class in Model.get_permission_classes(obj_or_model, [LDPPermissions]):
            permissions = permission_class().filter_user_perms(user_or_group, obj_or_model, permissions)
        return [{'mode': {'@type': name.split('_')[0]}} for name in permissions]

    @classmethod
    def is_external(cls, value):
        try:
            return value.urlid is not None and not value.urlid.startswith(settings.SITE_URL)
        except:
            return False


class LDPSource(Model):
    federation = models.CharField(max_length=255)

    class Meta:
        rdf_type = 'ldp:Container'
        ordering = ('federation',)
        container_path = 'sources'
        lookup_field = 'federation'
        permissions = (
            ('view_source', 'acl:Read'),
            ('control_source', 'acl:Control'),
        )

    def __str__(self):
        return "{}: {}".format(self.federation, self.urlid)


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
        # hack : We user webid as username for external user (since it's an uniq identifier too)
        if validators.url(self.username):
            webid = self.username
        else:
            webid = '{0}{1}'.format(settings.BASE_URL, reverse_lazy('user-detail', kwargs={'pk': self.pk}))
        return webid

    get_user_model()._meta.serializer_fields = ['@id']
    get_user_model().webid = webid

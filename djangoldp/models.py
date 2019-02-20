from django.conf import settings
from django.db import models
from django.urls import get_resolver


class Model(models.Model):
    container_path = None

    def get_container_path(self):
        return self.container_path

    def get_absolute_url(self):
        return Model.resource_id(self)

    def get_container_id(self):
        return Model.container_id(self)

    @classmethod
    def resource_id(cls, instance):
        view_name = '{}-detail'.format(instance._meta.object_name.lower())
        slug_field = '/{}'.format(get_resolver().reverse_dict[view_name][0][0][1][0])
        if slug_field.startswith('/'):
            slug_field = slug_field[1:]
        return "{}{}".format(cls.container_id(instance), getattr(instance, slug_field))

    @classmethod
    def container_id(cls, instance):
        if isinstance(instance, cls):
            path = instance.container_path
            if path is None:
                path = "{}s".format(instance._meta.object_name.lower())
        else:
            view_name = '{}-list'.format(instance._meta.object_name.lower())
            path = get_resolver().reverse(view_name)

        path = cls.__clean_path(path)

        return path

    class Meta:
        abstract = True

    @classmethod
    def resolve_id(cls, id):
        id = cls.__clean_path(id)
        view, args, kwargs = get_resolver().resolve(id)
        return view.initkwargs['model'].objects.get(**kwargs)

    @classmethod
    def resolve_container(cls, path):
        path = cls.__clean_path(path)
        view, args, kwargs = get_resolver().resolve(path)
        return view.initkwargs['model']

    @classmethod
    def resolve(cls, path):
        container = cls.resolve_container(path)
        try:
            resolve_id = cls.resolve_id(path)
        except:
            resolve_id = None
        return container, resolve_id

    @classmethod
    def __clean_path(cls, path):
        if not path.startswith("/"):
            path = "/{}".format(path)
        if not path.endswith("/"):
            path = "{}/".format(path)
        return path


class LDPSource(models.Model):
    container = models.URLField()
    federation = models.CharField(max_length=255)

    class Meta:
        rdf_type = 'sib:source'
        ordering = ('federation',)
        permissions = (
            ('view_source', 'acl:Read'),
            ('control_source', 'acl:Control'),
        )

    def __str__(self):
        return "{}: {}".format(self.federation, self.container)


class LDNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    author = models.URLField()
    object = models.URLField()
    type = models.CharField(max_length=255)
    summary = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = (
            ('view_todo', 'Read'),
            ('control_todo', 'Control'),
        )

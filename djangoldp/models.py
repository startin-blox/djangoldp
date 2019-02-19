from django.conf import settings
from django.db import models


class Model(models.Model):
    container_path = None

    def get_absolute_url(self):
        return Model.resource_id(self)

    def get_container_id(self):
        return Model.container_id(self)

    @classmethod
    def resource_id(cls, instance):
        return "{}{}".format(Model.container_id(instance), instance.pk)

    @classmethod
    def container_id(cls, instance):
        if isinstance(instance, cls):
            path = instance.container_path
        else:
            from django.urls import get_resolver
            view_name = '{}-list'.format(instance._meta.object_name.lower())
            path = '/{}'.format(get_resolver().reverse_dict[view_name][0][0][0], instance.pk)

        if not path.startswith("/"):
            path = "/{}".format(path)

        if not path.endswith("/"):
            path = "{}/".format(path)

        return path

    class Meta:
        abstract = True


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

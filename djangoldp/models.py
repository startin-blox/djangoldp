from django.conf import settings
from django.db import models


class LDPModel(models.Model):
    ldp_path = None

    def get_resource_path(self):
        return LDPModel.resource_path(self)

    def get_container_path(self):
        return LDPModel.container_path(self)

    @classmethod
    def resource_path(cls, instance):
        return "{}{}".format(LDPModel.container_path(instance), instance.pk)

    @classmethod
    def container_path(cls, instance):
        if isinstance(instance, cls):
            path = instance.ldp_path
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

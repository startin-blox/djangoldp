from django.conf import settings
from django.db import models
from rest_framework import fields

class LDPUrlField (fields.URLField):
    def to_representation(self, value):
        str = super(LDPUrlField, self).to_representation(value)
        return {'@id': str}

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

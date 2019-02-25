from django.db import models
from rest_framework import fields

class IdURLField (fields.URLField):
    def to_representation(self, value):
        str = super(IdURLField, self).to_representation(value)
        return {'@id': str}

class LDPUrlField (models.URLField):
    pass

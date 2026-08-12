import requests
from django.db import models
from rest_framework import fields


class IdURLField(fields.URLField):

    def to_representation(self, value):
        str = super(IdURLField, self).to_representation(value)
        return {"@id": str}

    def get(self, value):
        url = super(IdURLField, self).to_representation(value)
        datas = requests.get(url).json()
        return datas


class LDPFieldMixin(models.Field):
    """
    Extends Django field to store linked data information.
    """

    def __init__(
        self,
        *args,
        rdf_type=None,
        related_rdf_type=None,
        other_rdf_types=None,
        **kwargs
    ):
        """
        :param rdf_type: the preferred RDF type for the field serialization.
        :param related_rdf_type: the RDF type applied to the reverse relation in a to-many field.
        :param rdf_type_flalbacks: other accepted RDF types for the field.
        """
        super().__init__(*args, **kwargs)
        self.rdf_type = rdf_type
        self.related_rdf_type = related_rdf_type
        self.other_rdf_types = other_rdf_types

    def get_rdf_types(self):
        """Returns a set of all accepted RDF types for the field."""
        rdf_types = getattr(self, "other_rdf_types", set())
        if rdf_types is None:
            rdf_types = set()
        if not isinstance(rdf_types, set):
            rdf_types = set(rdf_types)

        preferred_rdf_type = getattr(self, "rdf_type", None)
        if preferred_rdf_type is not None:
            rdf_types.add(preferred_rdf_type)

        if (
            hasattr(self, "field")
            and getattr(self.field, "related_rdf_type", None) is not None
        ):
            rdf_types.add(self.field.related_rdf_type)
        return rdf_types


class BigIntegerField(LDPFieldMixin, models.BigIntegerField):
    pass


class BinaryField(LDPFieldMixin, models.BinaryField):
    pass


class BooleanField(LDPFieldMixin, models.BooleanField):
    pass


class CharField(LDPFieldMixin, models.CharField):
    pass


class DateField(LDPFieldMixin, models.DateField):
    pass


class DateTimeField(LDPFieldMixin, models.DateTimeField):
    pass


class DecimalField(LDPFieldMixin, models.DecimalField):
    pass


class DurationField(LDPFieldMixin, models.DurationField):
    pass


class EmailField(LDPFieldMixin, models.EmailField):
    pass


class FileField(LDPFieldMixin, models.FileField):
    pass


class FilePathField(LDPFieldMixin, models.FilePathField):
    pass


class FloatField(LDPFieldMixin, models.FloatField):
    pass


class GenericIPAddressField(LDPFieldMixin, models.GenericIPAddressField):
    pass


class ImageField(LDPFieldMixin, models.ImageField):
    pass


class IntegerField(LDPFieldMixin, models.IntegerField):
    pass


class JSONField(LDPFieldMixin, models.JSONField):
    pass


class PositiveBigIntegerField(LDPFieldMixin, models.PositiveBigIntegerField):
    pass


class PositiveIntegerField(LDPFieldMixin, models.PositiveIntegerField):
    pass


class PositiveSmallIntegerField(LDPFieldMixin, models.PositiveSmallIntegerField):
    pass


class SlugField(LDPFieldMixin, models.SlugField):
    pass


class SmallAutoField(LDPFieldMixin, models.SmallAutoField):
    pass


class SmallIntegerField(LDPFieldMixin, models.SmallIntegerField):
    pass


class TextField(LDPFieldMixin, models.TextField):
    pass


class TimeField(LDPFieldMixin, models.TimeField):
    pass


class LDPUrlField(LDPFieldMixin, models.URLField):
    pass


class UUIDField(LDPFieldMixin, models.UUIDField):
    pass


class ForeignKey(LDPFieldMixin, models.ForeignKey):
    pass


class ManyToManyField(LDPFieldMixin, models.ManyToManyField):
    pass


class OneToOneField(LDPFieldMixin, models.OneToOneField):
    pass

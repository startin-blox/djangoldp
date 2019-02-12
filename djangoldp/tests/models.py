from django.conf import settings
from django.db import models


class Skill(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    obligatoire = models.CharField(max_length=255)


class JobOffer(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True)


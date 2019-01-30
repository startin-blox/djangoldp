from django.db import models


class Skill(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)


class JobOffer(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True)
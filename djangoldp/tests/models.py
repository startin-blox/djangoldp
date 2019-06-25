from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from djangoldp.models import Model
from djangoldp.permissions import AnonymousReadOnly


class Skill(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    obligatoire = models.CharField(max_length=255)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta:
        serializer_fields = ["@id", "title"]
        lookup_field = 'slug'


class JobOffer(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta:
        nested_fields = ["skills"]
        container_path = "job-offers/"
        lookup_field = 'slug'


class Conversation(models.Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)


class UserProfile(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL)

    class Meta:
        depth = 1


class Message(models.Model):
    text = models.CharField(max_length=255, blank=True, null=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.DO_NOTHING)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)


class Dummy(models.Model):
    some = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True, unique=True)


class LDPDummy(Model):
    some = models.CharField(max_length=255, blank=True, null=True)


class Invoice(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)


    class Meta:
        depth = 2
        permission_classes = [AnonymousReadOnly]
        nested_fields = ["batches"]


class Batch(Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        serializer_fields = ['@id', 'title', 'invoice', 'tasks']
        nested_fields = ["tasks", 'invoice']


class Task(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)

    class Meta:
        serializer_fields = ['@id', 'title', 'batch']


class Post(Model):
    content = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)

    class Meta:
        auto_author = 'author'


get_user_model()._meta.serializer_fields = ['@id', 'username', 'first_name', 'last_name', 'email', 'userprofile', 'conversation_set']
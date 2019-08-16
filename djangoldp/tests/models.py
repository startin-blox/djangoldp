from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.datetime_safe import date

from djangoldp.models import Model


class Skill(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    obligatoire = models.CharField(max_length=255)
    slug = models.SlugField(blank=True, null=True, unique=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)

    def recent_jobs(self):
        return self.joboffer_set.filter(date__gte=date.today())

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        serializer_fields = ["@id", "title", "recent_jobs"]
        lookup_field = 'slug'


class JobOffer(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True)
    slug = models.SlugField(blank=True, null=True, unique=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)

    def recent_skills(self):
        return self.skills.filter(date__gte=date.today())

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'change', 'add']
        owner_perms = ['inherit', 'delete', 'control']
        nested_fields = ["skills"]
        serializer_fields = ["@id", "title", "skills", "recent_skills"]
        container_path = "job-offers/"
        lookup_field = 'slug'


class Conversation(models.Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    peer_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="peers_conv")

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class UserProfile(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL)

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit']
        owner_perms = ['inherit', 'change', 'control']
        depth = 1


class Message(models.Model):
    text = models.CharField(max_length=255, blank=True, null=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.DO_NOTHING)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class Dummy(models.Model):
    some = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class LDPDummy(Model):
    some = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class Invoice(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        depth = 2
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        nested_fields = ["batches"]


class Batch(Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        serializer_fields = ['@id', 'title', 'invoice', 'tasks']
        anonymous_perms = ['view', 'add']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        nested_fields = ["tasks", 'invoice']
        depth = 1


class Task(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)

    class Meta:
        serializer_fields = ['@id', 'title', 'batch']
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class Post(Model):
    content = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    peer_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="peers_post")

    class Meta:
        auto_author = 'author'
        anonymous_perms = ['view', 'add', 'delete', 'add', 'change', 'control']
        authenticated_perms = ['inherit']
        owner_perms = ['inherit']


get_user_model()._meta.serializer_fields = ['@id', 'username', 'first_name', 'last_name', 'email', 'userprofile',
                                            'conversation_set', ]

import json
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import BinaryField, DateField
from django.utils.datetime_safe import date

from djangoldp.fields import LDPUrlField
from djangoldp.models import Model


class User(AbstractUser, Model):

    class Meta(AbstractUser.Meta, Model.Meta):
        serializer_fields = ['@id', 'username', 'first_name', 'last_name', 'email', 'userprofile',
                             'conversation_set', 'circle_set', 'projects']
        anonymous_perms = ['view', 'add']
        authenticated_perms = ['inherit', 'change']
        owner_perms = ['inherit']
        nested_fields = ['circles', 'projects']


class Skill(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    obligatoire = models.CharField(max_length=255)
    slug = models.SlugField(blank=True, null=True, unique=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)

    def recent_jobs(self):
        return self.joboffer_set.filter(date__gte=date.today())

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        serializer_fields = ["@id", "title", "recent_jobs", "slug"]
        lookup_field = 'slug'


class JobOffer(Model):
    title = models.CharField(max_length=255, null=True)
    skills = models.ManyToManyField(Skill, blank=True)
    slug = models.SlugField(blank=True, null=True, unique=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)

    def recent_skills(self):
        return self.skills.filter(date__gte=date.today())

    def some_skill(self):
        return self.skills.all().first()

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'change', 'add']
        owner_perms = ['inherit', 'delete', 'control']
        nested_fields = ["skills"]
        serializer_fields = ["@id", "title", "skills", "recent_skills", "resources", "slug", "some_skill", "urlid"]
        container_path = "job-offers/"
        lookup_field = 'slug'


class Conversation(models.Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    peer_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="peers_conv")

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        owner_field = 'author_user'


class Resource(Model):
    joboffers = models.ManyToManyField(JobOffer, blank=True, related_name='resources')
    description = models.CharField(max_length=255)

    class Meta(Model.Meta):
        anonymous_perms = ['view', 'add', 'delete', 'change', 'control']
        authenticated_perms = ['inherit']
        owner_perms = ['inherit']
        serializer_fields = ["@id", "joboffers"]
        nested_fields = ["joboffers"]
        depth = 1


class UserProfile(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL)

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit']
        owner_perms = ['inherit', 'change', 'control']
        depth = 1


class Message(models.Model):
    text = models.CharField(max_length=255, blank=True, null=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.DO_NOTHING)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class Dummy(models.Model):
    some = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class LDPDummy(Model):
    some = models.CharField(max_length=255, blank=True, null=True)

    class Meta(Model.Meta):
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


# model used in django-guardian permission tests (no anonymous etc permissions set)
class PermissionlessDummy(Model):
    some = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta(Model.Meta):
        anonymous_perms = []
        authenticated_perms = []
        owner_perms = []
        permissions = (
            ('custom_permission_permissionlessdummy', 'Custom Permission'),
        )


class Invoice(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta(Model.Meta):
        depth = 2
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        nested_fields = ["batches"]


class Batch(Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta(Model.Meta):
        serializer_fields = ['@id', 'title', 'invoice', 'tasks']
        anonymous_perms = ['view', 'add']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']
        nested_fields = ["tasks", 'invoice']
        depth = 1


class Task(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)

    class Meta(Model.Meta):
        serializer_fields = ['@id', 'title', 'batch']
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'delete', 'control']


class Post(Model):
    content = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    peer_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="peers_post")

    class Meta(Model.Meta):
        auto_author = 'author'
        anonymous_perms = ['view', 'add', 'delete', 'add', 'change', 'control']
        authenticated_perms = ['inherit']
        owner_perms = ['inherit']


class Circle(Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    team = models.ManyToManyField(settings.AUTH_USER_MODEL, through="CircleMember", blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="owned_circles", on_delete=models.DO_NOTHING,
                              null=True, blank=True)

    class Meta(Model.Meta):
        nested_fields = ["team"]
        anonymous_perms = ['view', 'add', 'delete', 'add', 'change', 'control']
        authenticated_perms = ["inherit"]
        rdf_type = 'hd:circle'
        depth = 1


class CircleMember(Model):
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circles")
    is_admin = models.BooleanField(default=False)

    class Meta(Model.Meta):
        container_path = "circle-members/"
        anonymous_perms = ['view', 'add', 'delete', 'add', 'change', 'control']
        authenticated_perms = ['inherit']
        unique_together = ['user', 'circle']
        rdf_type = 'hd:circlemember'


class Project(Model):
    description = models.CharField(max_length=255, null=True, blank=False)
    team = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='projects')

    class Meta(Model.Meta):
        nested_fields = ["team"]
        anonymous_perms = ['view', 'add', 'delete', 'add', 'change', 'control']
        authenticated_perms = ["inherit"]
        rdf_type = 'hd:project'
        depth = 1

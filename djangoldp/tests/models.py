from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.datetime_safe import date

from djangoldp.models import Model
from djangoldp.permissions import LDPPermissions, AuthenticatedOnly, ReadOnly, \
    ReadAndCreate, AnonymousReadOnly, OwnerPermissions, InheritPermissions

from .permissions import Only2WordsForToto, ReadOnlyStartsWithA


class User(AbstractUser, Model):
    class Meta(AbstractUser.Meta, Model.Meta):
        ordering = ['pk']
        serializer_fields = ['@id', 'username', 'first_name', 'last_name', 'email', 'userprofile',
                             'conversation_set','groups', 'projects', 'owned_circles']
        permission_classes = [ReadAndCreate|OwnerPermissions]
        rdf_type = 'foaf:user'


class Skill(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    obligatoire = models.CharField(max_length=255)
    slug = models.SlugField(blank=True, null=True, unique=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)

    def recent_jobs(self):
        return self.joboffer_set.filter(date__gte=date.today())

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]
        serializer_fields = ["@id", "title", "recent_jobs", "slug", "obligatoire"]
        lookup_field = 'slug'
        rdf_type = 'hd:skill'


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
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly, ReadOnly|OwnerPermissions]
        serializer_fields = ["@id", "title", "skills", "recent_skills", "resources", "slug", "some_skill", "urlid"]
        container_path = "job-offers/"
        lookup_field = 'slug'
        rdf_type = 'hd:joboffer'


class Conversation(models.Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    peer_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="peers_conv",
                                  on_delete=models.DO_NOTHING)
    observers = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='observed_conversations')

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]
        nested_fields=["message_set", "observers"]
        owner_field = 'author_user'


class Resource(Model):
    joboffers = models.ManyToManyField(JobOffer, blank=True, related_name='resources')
    description = models.CharField(max_length=255)

    class Meta(Model.Meta):
        ordering = ['pk']
        serializer_fields = ["@id", "joboffers"]
        depth = 1
        rdf_type = 'hd:Resource'


# a resource in which only the owner has permissions (for testing owner permissions)
class OwnedResource(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="owned_resources",
                             on_delete=models.CASCADE)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [OwnerPermissions]
        owner_field = 'user'
        serializer_fields = ['@id', 'description', 'user']
        depth = 1


class OwnedResourceVariant(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="owned_variant_resources",
                             on_delete=models.CASCADE)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [ReadOnly|OwnerPermissions]
        owner_field = 'user'
        serializer_fields = ['@id', 'description', 'user']
        depth = 1


class OwnedResourceNestedOwnership(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey(OwnedResource, blank=True, null=True, related_name="owned_resources",
                               on_delete=models.CASCADE)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [OwnerPermissions]
        owner_field = 'parent__user'
        serializer_fields = ['@id', 'description', 'parent']
        depth = 1


class OwnedResourceTwiceNestedOwnership(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey(OwnedResourceNestedOwnership, blank=True, null=True, related_name="owned_resources",
                               on_delete=models.CASCADE)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [OwnerPermissions]
        owner_field = 'parent__parent__user'
        serializer_fields = ['@id', 'description', 'parent']
        depth = 1


class UserProfile(Model):
    description = models.CharField(max_length=255, blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile', on_delete=models.CASCADE)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AuthenticatedOnly,ReadOnly|OwnerPermissions]
        owner_field = 'user'
        lookup_field = 'slug'
        serializer_fields = ['@id', 'description', 'settings', 'user', 'post_set']
        depth = 1


class NotificationSetting(Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="settings")
    receiveMail = models.BooleanField(default=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [ReadAndCreate|OwnerPermissions]


class Message(models.Model):
    text = models.CharField(max_length=255, blank=True, null=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.DO_NOTHING)
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]


class Dummy(models.Model):
    some = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True, unique=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]


class LDPDummy(Model):
    some = models.CharField(max_length=255, blank=True, null=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]


# model used in django-guardian permission tests (no permission to anyone except suuperusers)
class PermissionlessDummy(Model):
    some = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(blank=True, null=True, unique=True)
    parent = models.ForeignKey(LDPDummy, on_delete=models.DO_NOTHING, related_name="anons", blank=True, null=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [LDPPermissions]
        lookup_field='slug'
        permissions = (('custom_permission_permissionlessdummy', 'Custom Permission'),)


class Post(Model):
    content = models.CharField(max_length=255)
    author = models.ForeignKey(UserProfile, blank=True, null=True, on_delete=models.SET_NULL)
    peer_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="peers_post",
                                  on_delete=models.SET_NULL)

    class Meta(Model.Meta):
        ordering = ['pk']
        auto_author = 'author'
        auto_author_field = 'userprofile'
        rdf_type = 'hd:post'

class AnonymousReadOnlyPost(Model):
    content = models.CharField(max_length=255)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AnonymousReadOnly]
class AuthenticatedOnlyPost(Model):
    content = models.CharField(max_length=255)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [AuthenticatedOnly]
class ReadOnlyPost(Model):
    content = models.CharField(max_length=255)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [ReadOnly]
class ReadAndCreatePost(Model):
    content = models.CharField(max_length=255)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [ReadAndCreate]
        
class ANDPermissionsDummy(Model):
    title = models.CharField(max_length=255)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [ReadOnlyStartsWithA&Only2WordsForToto]
class ORPermissionsDummy(Model):
    title = models.CharField(max_length=255)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [ReadOnlyStartsWithA|Only2WordsForToto]


class Invoice(Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        depth = 2
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]


class Circle(Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="owned_circles", on_delete=models.DO_NOTHING, null=True, blank=True)
    members = models.ForeignKey(Group, related_name="circles", on_delete=models.SET_NULL, null=True, blank=True)
    admins = models.ForeignKey(Group, related_name="admin_circles", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        auto_author = 'owner'
        depth = 1
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions|LDPPermissions]
        permission_roles = {
            'members': {'perms': ['view'], 'add_author': True},
            'admins': {'perms': ['view', 'change', 'control'], 'add_author': True},
        }
        serializer_fields = ['@id', 'name', 'description', 'members', 'owner', 'space']
        rdf_type = 'hd:circle'


class RestrictedCircle(Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="owned_restrictedcircles", on_delete=models.DO_NOTHING, null=True, blank=True)
    members = models.ForeignKey(Group, related_name="restrictedcircles", on_delete=models.SET_NULL, null=True, blank=True)
    admins = models.ForeignKey(Group, related_name="admin_restrictedcircles", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        auto_author = 'owner'
        permission_classes = [LDPPermissions]
        permission_roles = {
            'members': {'perms': ['view'], 'add_author': True},
            'admins': {'perms': ['view', 'change', 'control'], 'add_author': True},
        }
        rdf_type = 'hd:circle'
class RestrictedResource(Model):
    content = models.CharField(max_length=255, blank=True)
    circle = models.ForeignKey(RestrictedCircle, on_delete=models.CASCADE)
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [InheritPermissions]
        inherit_permissions = 'circle'

class Space(Model):
    name = models.CharField(max_length=255, blank=True)
    circle = models.OneToOneField(to=Circle, null=True, blank=True, on_delete=models.CASCADE, related_name='space')

    class Meta(Model.Meta):
        ordering = ['pk']


class Batch(Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='batches')
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        serializer_fields = ['@id', 'title', 'invoice', 'tasks']
        permission_classes = [ReadAndCreate|OwnerPermissions]
        depth = 1
        rdf_type = 'hd:batch'


class Task(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)

    class Meta(Model.Meta):
        ordering = ['pk']
        serializer_fields = ['@id', 'title', 'batch']
        permission_classes = [AnonymousReadOnly,ReadAndCreate|OwnerPermissions]


class ModelTask(Model, Task):
    class Meta(Model.Meta):
        ordering = ['pk']

STATUS_CHOICES = [
    ('Public', 'Public'),
    ('Private', 'Private'),
    ('Archived', 'Archived'),
]

class Project(Model):
    description = models.CharField(max_length=255, null=True, blank=False)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default='Private', null=True, blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='projects')

    class Meta(Model.Meta):
        ordering = ['pk']
        rdf_type = 'hd:project'


class DateModel(Model):
    excluded = models.CharField(max_length=255, null=True, default='test')
    value = models.DateField()

    class Meta(Model.Meta):
        ordering = ['pk']
        rdf_type = "hd:date"
        serializer_fields_exclude = ['excluded']


class DateChild(Model):
    parent = models.ForeignKey(DateModel, on_delete=models.CASCADE, related_name='children')

    class Meta(Model.Meta):
        ordering = ['pk']
        rdf_type = 'hd:datechild'


class MyAbstractModel(Model):
    defaultsomething = models.CharField(max_length=255, blank=True)

    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [LDPPermissions]
        abstract = True
        rdf_type = "wow:defaultrdftype"


class NoSuperUsersAllowedModel(Model):
    class Meta(Model.Meta):
        ordering = ['pk']
        permission_classes = [LDPPermissions]
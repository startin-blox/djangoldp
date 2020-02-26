from django.conf import settings
from django.conf.urls import url, include

from djangoldp.permissions import LDPPermissions
from djangoldp.tests.models import Skill, JobOffer, Message, Conversation, Dummy, PermissionlessDummy, Task
from djangoldp.views import LDPViewSet

urlpatterns = [
    url(r'^messages/', LDPViewSet.urls(model=Message, permission_classes=[LDPPermissions], fields=["@id", "text", "conversation"], nested_fields=['conversation'])),
    url(r'^conversations/', LDPViewSet.urls(model=Conversation, nested_fields=["message_set"], permission_classes=[LDPPermissions])),
    url(r'^tasks/', LDPViewSet.urls(model=Task, permission_classes=[LDPPermissions])),
    url(r'^dummys/', LDPViewSet.urls(model=Dummy, permission_classes=[LDPPermissions], lookup_field='slug',)),
    url(r'^permissionless-dummys/', LDPViewSet.urls(model=PermissionlessDummy, permission_classes=[LDPPermissions], lookup_field='slug',)),
]


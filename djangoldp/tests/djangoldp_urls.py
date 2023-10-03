from django.urls import path
from djangoldp.tests.models import Message, Conversation, Dummy, PermissionlessDummy, Task, DateModel, LDPDummy
from djangoldp.permissions import ACLPermissions
from djangoldp.views import LDPViewSet

urlpatterns = [
    path('messages/', LDPViewSet.urls(model=Message, fields=["@id", "text", "conversation"], nested_fields=['conversation'])),
    path('tasks/', LDPViewSet.urls(model=Task)),
    path('conversations/', LDPViewSet.urls(model=Conversation, nested_fields=["message_set", "observers"])),
    path('dummys/', LDPViewSet.urls(model=Dummy, lookup_field='slug',)),
    path('permissionless-dummys/', LDPViewSet.urls(model=PermissionlessDummy, lookup_field='slug', permission_classes=[ACLPermissions])),
]


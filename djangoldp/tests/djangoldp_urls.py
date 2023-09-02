from django.urls import path
from djangoldp.tests.models import Message, Conversation, Dummy, PermissionlessDummy, Task, DateModel, LDPDummy
from djangoldp.permissions import LDPPermissions,AnonymousReadOnly,ReadAndCreate,OwnerPermissions
from djangoldp.views import LDPViewSet

urlpatterns = [
    path('messages/', LDPViewSet.urls(model=Message, fields=["@id", "text", "conversation"], nested_fields=['conversation'])),
    path('tasks/', LDPViewSet.urls(model=Task)),
    # # path('dates/', LDPViewSet.urls(model=DateModel)),
    path('conversations/', LDPViewSet.urls(model=Conversation, nested_fields=["message_set", "observers"])),
    path('dummys/', LDPViewSet.urls(model=Dummy, lookup_field='slug',)),
    # path('ldpdummys/', LDPViewSet.urls(model=LDPDummy, nested_fields=['anons'], permission_classes=[AnonymousReadOnly,ReadAndCreate|OwnerPermissions])),
    path('permissionless-dummys/', LDPViewSet.urls(model=PermissionlessDummy, lookup_field='slug', permission_classes=[LDPPermissions])),
]


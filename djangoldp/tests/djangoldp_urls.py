from django.conf import settings
from django.conf.urls import url, include

from djangoldp.tests.models import Skill, JobOffer, Message, Conversation, Dummy, Task
from djangoldp.views import LDPViewSet

urlpatterns = [
    url(r'^messages/', LDPViewSet.urls(model=Message, permission_classes=[], fields=["@id", "text", "conversation"], nested_fields=['conversation'])),
    url(r'^conversations/', LDPViewSet.urls(model=Conversation, nested_fields=["message_set"], permission_classes=())),
    url(r'^tasks/', LDPViewSet.urls(model=Task, permission_classes=())),
    url(r'^users/', LDPViewSet.urls(model=settings.AUTH_USER_MODEL, permission_classes=[])),
    url(r'^dummys/', LDPViewSet.urls(model=Dummy, permission_classes=[], lookup_field='slug',)),
]


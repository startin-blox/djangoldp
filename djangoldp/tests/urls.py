from django.conf import settings
from django.conf.urls import url, include

from djangoldp.tests.models import Skill, JobOffer, Message, Thread, Dummy
from djangoldp.views import LDPViewSet

urlpatterns = [
    url(r'^messages/', LDPViewSet.urls(model=Message, permission_classes=[], fields=["@id", "text"], nested_fields=[])),
    url(r'^threads/', LDPViewSet.urls(model=Thread, nested_fields=["message_set"], permission_classes=())),
    url(r'^users/', LDPViewSet.urls(model=settings.AUTH_USER_MODEL, permission_classes=[])),
    url(r'^dummys/', LDPViewSet.urls(model=Dummy, permission_classes=[], lookup_field='slug',)),
    url(r'^', include('djangoldp.urls')),
]


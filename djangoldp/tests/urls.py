from django.conf import settings

from djangoldp.tests.models import Skill, JobOffer, Message, Thread, Dummy, LDPDummy
from djangoldp.views import LDPViewSet
from django.conf.urls import url


urlpatterns = [
    url(r'^skills/', LDPViewSet.urls(model=Skill, permission_classes=[], fields=["@id", "title"], nested_fields=[])),
    url(r'^job-offers/', LDPViewSet.urls(model=JobOffer, nested_fields=["skills"], permission_classes=())),
    url(r'^messages/', LDPViewSet.urls(model=Message, permission_classes=[], fields=["@id", "text"], nested_fields=[])),
    url(r'^threads/', LDPViewSet.urls(model=Thread, nested_fields=["message_set"], permission_classes=())),
    url(r'^users/', LDPViewSet.urls(model=settings.AUTH_USER_MODEL, permission_classes=[])),
    url(r'^dummys/', LDPViewSet.urls(model=Dummy, permission_classes=[])),
    url(r'^ldp-dummys/', LDPViewSet.urls(model=LDPDummy, permission_classes=[])),
]
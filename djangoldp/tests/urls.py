from djangoldp.tests.models import Skill, JobOffer
from djangoldp.views import LDPViewSet
from django.conf.urls import url


urlpatterns = [
    url(r'^skills/', LDPViewSet.urls(model=Skill, permission_classes=[], fields=["@id", "title"], nested_fields=[])),
    url(r'^job-offers/', LDPViewSet.urls(model=JobOffer, nested_fields=["skills"], permission_classes=())),
]
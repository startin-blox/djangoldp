from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from guardian.shortcuts import get_anonymous_user

from djangoldp.tests.models import JobOffer
from djangoldp.views import LDPViewSet

import json


class TestAnonymousUserPermissions(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_anonymous_user()
        self.job = JobOffer.objects.create(title="job")

    def test_get_request_for_anonymousUser(self):
        request = self.factory.get("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'get': 'list'},
                                     model=JobOffer,
                                     nested_fields=["skills"])
        response = my_view(request)
        self.assertEqual(response.status_code, 200)

    def test_post_request_for_anonymousUser(self):
        data = {'title': 'new idea'}
        request = self.factory.post('/job-offers/', json.dumps(data), content_type='application/ld+json')
        my_view = LDPViewSet.as_view({'post': 'create'}, model=JobOffer, nested_fields=["skills"])
        response = my_view(request, pk=1)
        self.assertEqual(response.status_code, 403)

    def test_put_request_for_anonymousUser(self):
        request = self.factory.put("/job-offers/")
        my_view = LDPViewSet.as_view({'put': 'update'},
                                     model=JobOffer,
                                     nested_fields=["skills"])
        response = my_view(request, pk=self.job.pk)
        self.assertEqual(response.status_code, 403)

    def test_patch_request_for_anonymousUser(self):
        request = self.factory.patch("/job-offers/")
        my_view = LDPViewSet.as_view({'patch': 'partial_update'},
                                     model=JobOffer,
                                     nested_fields=["skills"])
        response = my_view(request, pk=self.job.pk)
        self.assertEqual(response.status_code, 403)

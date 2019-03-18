from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from djangoldp.permissions import AnonymousReadOnly
from .models import JobOffer
from djangoldp.views import LDPViewSet

import json


class TestUserPermissions(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        self.job = JobOffer.objects.create(title="job")

    def tearDown(self):
        self.user.delete()

    def test_get_for_authenticated_user(self):
        request = self.factory.get('/job-offers/')
        request.user = self.user
        my_view = LDPViewSet.as_view({'get': 'list'}, model=JobOffer, permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 200)

    def test_post_request_for_authenticated_user(self):
        data = {'title': 'new idea'}
        request = self.factory.post('/job-offers/', json.dumps(data), content_type='application/ld+json')
        request.user = self.user
        my_view = LDPViewSet.as_view({'post': 'create'}, model=JobOffer, nested_fields=["skills"], permission_classes=[AnonymousReadOnly])
        response = my_view(request, pk=1)
        self.assertEqual(response.status_code, 201)

    # def test_put_request_for_authenticated_user(self):
    #     data = {'title':"job_updated"}
    #     request = self.factory.put('/job-offers/' + str(self.job.pk) + "/", data)
    #     request.user = self.user
    #     my_view = LDPViewSet.as_view({'put': 'update'}, model=JobOffer, permission_classes=[AnonymousReadOnly])
    #     response = my_view(request, pk=self.job.pk)
    #     self.assertEqual(response.status_code, 200)
    #
    # def test_request_patch_for_authenticated_user(self):
    #     request = self.factory.patch('/job-offers/' + str(self.job.pk) + "/")
    #     request.user = self.user
    #     my_view = LDPViewSet.as_view({'patch': 'partial_update'}, model=JobOffer, permission_classes=[AnonymousReadOnly])
    #     response = my_view(request, pk=self.job.pk)
    #     self.assertEqual(response.status_code, 200)
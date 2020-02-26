from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from guardian.shortcuts import assign_perm

from djangoldp.permissions import LDPPermissions
from .models import JobOffer, PermissionlessDummy
from djangoldp.views import LDPViewSet

import json

class TestUserPermissions(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_authenticate(user=self.user)
        self.job = JobOffer.objects.create(title="job", slug="slug1")

    def test_get_for_authenticated_user(self):
        response = self.client.get('/job-offers/')
        self.assertEqual(response.status_code, 200)

    def test_get_1_for_authenticated_user(self):
        response = self.client.get('/job-offers/{}/'.format(self.job.slug))
        self.assertEqual(response.status_code, 200)

    def test_post_request_for_authenticated_user(self):
        post = {'title': "job_created", "slug": 'slug1'}
        response = self.client.post('/job-offers/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

    def test_put_request_for_authenticated_user(self):
        body = {'title':"job_updated"}
        response = self.client.put('/job-offers/{}/'.format(self.job.slug), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

    def test_request_patch_for_authenticated_user(self):
        response = self.client.patch('/job-offers/' + str(self.job.slug) + "/",
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

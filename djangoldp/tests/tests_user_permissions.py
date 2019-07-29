from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from djangoldp.permissions import LDPPermissions
from .models import JobOffer
from djangoldp.views import LDPViewSet

import json

class TestUserPermissions(APITestCase):

    def setUp(self):
        user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_authenticate(user=user)
        self.job = JobOffer.objects.create(title="job", slug=1)

    def test_get_for_authenticated_user(self):
        response = self.client.get('/job-offers/')
        self.assertEqual(response.status_code, 200)

    def test_get_1_for_authenticated_user(self):
        response = self.client.get('/job-offers/1/')
        self.assertEqual(response.status_code, 200)

    def test_post_request_for_authenticated_user(self):
        post = {'title': "job_created"}
        response = self.client.post('/job-offers/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

    def test_put_request_for_authenticated_user(self):
        body = {'title':"job_updated"}
        response = self.client.put('/job-offers/{}/'.format(self.job.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
    
    def test_request_patch_for_authenticated_user(self):
        response = self.client.patch('/job-offers/' + str(self.job.pk) + "/",
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

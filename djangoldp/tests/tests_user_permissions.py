from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from rest_framework.test import APIClient, APITestCase
from .models import JobOffer, LDPDummy, PermissionlessDummy

import json


class TestUserPermissions(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_authenticate(user=self.user)
        self.job = JobOffer.objects.create(title="job", slug="slug1")

    def setUpGroup(self):
        self.group = Group.objects.create(name='Test')
        view_perm = Permission.objects.get(codename='view_permissionlessdummy')
        self.group.permissions.add(view_perm)
        self.group.save()

    # list - simple
    def test_get_for_authenticated_user(self):
        response = self.client.get('/job-offers/')
        self.assertEqual(response.status_code, 200)

    # list - I do not have permission from the model, but I do have permission via a Group I am assigned
    # TODO: https://git.startinblox.com/djangoldp-packages/djangoldp/issues/291
    '''def test_group_list_access(self):
        self.setUpGroup()

        response = self.client.get('/permissionless-dummys/')
        self.assertEqual(response.status_code, 403)

        self.user.groups.add(self.group)
        self.user.save()
        response = self.client.get('/permissionless-dummys/')
        self.assertEqual(response.status_code, 200)'''

    # TODO: repeat of the above test on nested field
    '''def test_group_list_access_nested(self):
        self.setUpGroup()
        parent = LDPDummy.objects.create()
        dummy = PermissionlessDummy.objects.create(parent=parent)'''

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

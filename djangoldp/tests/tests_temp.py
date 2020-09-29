import json

from guardian.shortcuts import assign_perm

from .models import PermissionlessDummy, Dummy, Resource, UserProfile
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from djangoldp.models import LDPSource
from djangoldp.tests.models import Invoice, Circle, Conversation
from ..permissions import LDPPermissions


class TestTemp(TestCase):

    def setUp(self):
        self.client = APIClient()

    def setUpLoggedInUser(self):
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                         password='glass onion')
        self.client.force_authenticate(user=self.user)

    # optional setup for testing PermissionlessDummy model with parameterised perms
    def setUpGuardianDummyWithPerms(self, perms=[]):
        self.dummy = PermissionlessDummy.objects.create(some='test', slug='test')
        model_name = PermissionlessDummy._meta.model_name

        for perm in perms:
            assign_perm(perm + '_' + model_name, self.user, self.dummy)

    def tearDown(self):
        pass

    # def test_nested_container_federated_609(self):
    #     resource = Resource.objects.create()
    #     body = {
    #         'http://happy-dev.fr/owl/#@id': "http://testserver/resources/{}".format(resource.pk),
    #         'http://happy-dev.fr/owl/#joboffers': [
    #             {
    #                 'http://happy-dev.fr/owl/#@id': "https://external.com/job-offers/1"
    #             },
    #             {
    #                 'http://happy-dev.fr/owl/#@id': "https://external.com/job-offers/2"
    #             }
    #         ]
    #     }
    #
    #     response = self.client.put('/resources/{}/'.format(resource.pk),
    #                                 data=json.dumps(body),
    #                                 content_type='application/ld+json')
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(len(response.data['joboffers']['ldp:contains']), 2)
    #
    #     body2 = {
    #         'http://happy-dev.fr/owl/#@id': "http://testserver/resources/{}".format(resource.pk),
    #         'http://happy-dev.fr/owl/#joboffers': [
    #             {
    #                 'http://happy-dev.fr/owl/#@id': "https://external.com/job-offers/1"
    #             },
    #             {
    #                 'http://happy-dev.fr/owl/#@id': "https://external.com/job-offers/3"
    #             },
    #             {
    #                 'http://happy-dev.fr/owl/#@id': "https://external.com/job-offers/4"
    #             }
    #         ]
    #     }
    #     response = self.client.put('/resources/{}/'.format(resource.pk),
    #                                 data=json.dumps(body2),
    #                                 content_type='application/ld+json')
    #
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(len(response.data['joboffers']['ldp:contains']), 3)
    #
    #     response = self.client.put('/resources/{}/job-offers'.format(resource.pk),
    #                                data=json.dumps(body2),
    #                                content_type='application/ld+json')

    def test_create_sub_object_in_existing_object_with_existing_reverse_1to1_relation(self):
        user = get_user_model().objects.create(username="alex", password="test")
        profile = UserProfile.objects.create(user=user, description="user description")
        body = {
                '@id': '/users/{}/'.format(user.pk),
                "first_name": "Alexandre",
                "last_name": "Bourlier",
                "username": "alex",
                'userprofile': {
                    '@id': "http://happy-dev.fr/userprofiles/{}/".format(profile.pk),
                    'description': "user update"
                },
                '@context': {
                    "@vocab": "http://happy-dev.fr/owl/#",
                }
            }

        response = self.client.put('/users/{}/'.format(user.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('userprofile', response.data)

        response = self.client.get('/userprofiles/{}/'.format(profile.pk),
                                   content_type='application/ld+json')
        self.assertEqual(response.data['description'], "user update")



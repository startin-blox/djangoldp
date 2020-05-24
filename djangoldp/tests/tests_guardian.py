import json
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from guardian.shortcuts import assign_perm

from .models import PermissionlessDummy, Dummy
from djangoldp.permissions import LDPPermissions


class TestsGuardian(APITestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

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

    # test that dummy with no permissions set returns no results
    def test_get_dummy_no_permissions(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms()
        response = self.client.get('/permissionless-dummys/{}/'.format(self.dummy.slug))
        self.assertEqual(response.status_code, 403)

    # test with anonymous user
    def test_get_dummy_anonymous_user(self):
        self.setUpGuardianDummyWithPerms()
        response = self.client.get('/permissionless-dummys/')
        self.assertEqual(response.status_code, 403)

    def test_get_dummy_permission_granted(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms(['view'])
        response = self.client.get('/permissionless-dummys/{}/'.format(self.dummy.slug))
        self.assertEqual(response.status_code, 200)

    def test_get_dummy_permission_rejected(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms(['view'])
        dummy_without = PermissionlessDummy.objects.create(some='test2', slug='test2')
        response = self.client.get('/permissionless-dummys/{}/'.format(dummy_without.slug))
        self.assertEqual(response.status_code, 403)

    def test_patch_dummy_permission_granted(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms(['change'])
        body = {'some': "some_new"}
        response = self.client.patch('/permissionless-dummys/{}/'.format(self.dummy.slug), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

    def test_patch_dummy_permission_rejected(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms(['change'])
        dummy_without = PermissionlessDummy.objects.create(some='test2', slug='test2')
        body = {'some': "some_new"}
        response = self.client.patch('/permissionless-dummys/{}/'.format(dummy_without.slug), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 403)

    # test that custom permissions are returned on a model
    def test_custom_permissions(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms(['custom_permission'])

        permissions = LDPPermissions()
        result = permissions.user_permissions(self.user, self.dummy)
        self.assertIn('custom_permission', result)

    # test that duplicate permissions aren't returned
    def test_no_duplicate_permissions(self):
        self.setUpLoggedInUser()
        dummy = Dummy.objects.create(some='test', slug='test')
        model_name = Dummy._meta.model_name

        assign_perm('view_' + model_name, self.user, dummy)

        permissions = LDPPermissions()
        result = permissions.user_permissions(self.user, dummy)
        self.assertEqual(result.count('view'), 1)

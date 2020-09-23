import json

from guardian.shortcuts import assign_perm

from .models import PermissionlessDummy, Dummy
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


    # test with anonymous user
    def test_invalidate_cache_permissions(self):
        self.setUpLoggedInUser()
        self.setUpGuardianDummyWithPerms()
        response = self.client.get('/permissionless-dummys/{}/'.format(self.dummy.slug))
        self.assertEqual(response.status_code, 403)
        assign_perm('view' + '_' + PermissionlessDummy._meta.model_name, self.user, self.dummy)
        LDPPermissions.invalidate_cache()
        response = self.client.get('/permissionless-dummys/{}/'.format(self.dummy.slug))
        self.assertEqual(response.status_code, 200)


import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from djangoldp.models import LDPSource


class TestTemp(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        self.client.force_authenticate(self.user)

    def tearDown(self):
        pass


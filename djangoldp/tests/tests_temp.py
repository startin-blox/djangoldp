from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from djangoldp.tests.models import Skill, JobOffer


class TestTemp(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()

    def tearDown(self):
        pass

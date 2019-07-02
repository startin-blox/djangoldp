from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.utils import json

from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Post, UserProfile
from djangoldp.tests.models import Skill, JobOffer, Conversation, Message


class TestTemp(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()

    def tearDown(self):
        pass

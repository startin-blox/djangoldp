from rest_framework.test import APIClient, APITestCase
from djangoldp.tests.models import User, Project


class TestsInbox(APITestCase):
    fixtures = ['test.json',]

    def test_populated(self):
        self.assertEqual(User.objects.count(), 100)
        self.assertEqual(Project.objects.count(), 100)

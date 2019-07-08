import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from djangoldp.tests.models import Skill, JobOffer


class TestTemp(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')


    def tearDown(self):
        pass

    def test_post_should_accept_missing_field_id_nullable(self):
        body = [
            {
                '@id': "./",
                'http://happy-dev.fr/owl/#content': "post update",
            }
        ]
        response = self.client.post('/posts/', data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('peer_user', response.data)

    def test_post_should_accept_empty_field_if_nullable(self):
        body = [
            {
                '@id': "./",
                'http://happy-dev.fr/owl/#content': "post update",
                'http://happy-dev.fr/owl/#peer_user': ""
            }
        ]
        response = self.client.post('/posts/', data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['peer_user'], None)

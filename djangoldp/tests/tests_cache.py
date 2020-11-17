from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.utils import json

from djangoldp.models import Model
from djangoldp.serializers import LDPSerializer, LDListMixin
from djangoldp.tests.models import Skill, JobOffer, Invoice, LDPDummy, Resource, Post, Circle, Project, Conversation


class TestCache(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                         password='glass onion')
        self.client.force_authenticate(self.user)
        LDListMixin.to_representation_cache.reset()
        LDPSerializer.to_representation_cache.reset()

    def tearDown(self):
        pass

    def test_save_fk_graph_with_nested(self):
        response = self.client.get('/batchs/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

        post = {
            '@graph': [
                {
                    'http://happy-dev.fr/owl/#title': "title",
                    'http://happy-dev.fr/owl/#invoice': {
                        '@id': "_.123"
                    }
                },
                {
                    '@id': "_.123",
                    'http://happy-dev.fr/owl/#title': "title 2"
                }
            ]
        }

        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/batchs/', content_type='application/ld+json')
        self.assertIn('ldp:contains', response.data)
        self.assertEquals(response.data['ldp:contains'][0]['title'], "title")
        self.assertEquals(response.data['ldp:contains'][0]['invoice']['title'], "title 2")

    def test_update_with_new_fk_relation(self):
        conversation = Conversation.objects.create(author_user=self.user,
                                                   description="conversation description")
        response = self.client.get('/conversations/{}/'.format(conversation.pk), content_type='application/ld+json')
        body = [
            {
                '@id': "/conversations/{}/".format(conversation.pk),
                'http://happy-dev.fr/owl/#description': "conversation update",
                'http://happy-dev.fr/owl/#peer_user': {
                    '@id': 'http://happy-dev.fr/users/{}'.format(self.user.pk),
                }
            }
        ]
        response = self.client.put('/conversations/{}/'.format(conversation.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/conversations/{}/'.format(conversation.pk), content_type='application/ld+json')
        self.assertIn('peer_user', response.data)
        self.assertEquals('conversation update', response.data['description'])
        self.assertIn('@id', response.data['peer_user'])


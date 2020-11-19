from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.utils import json

from djangoldp.serializers import LDPSerializer, LDListMixin
from djangoldp.tests.models import Conversation, Project


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

    # test container cache after new resource added
    @override_settings(SERIALIZER_CACHE=True)
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

    # test resource cache after it is updated
    @override_settings(SERIALIZER_CACHE=True)
    def test_update_with_new_fk_relation(self):
        conversation = Conversation.objects.create(author_user=self.user, description="conversation description")
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

    # test container cache after member is deleted by view
    @override_settings(SERIALIZER_CACHE=True)
    def test_cached_container_deleted_resource_view(self):
        conversation = Conversation.objects.create(author_user=self.user, description="conversation description")
        response = self.client.get('/conversations/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 1)

        response = self.client.delete('/conversations/{}/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/conversations/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

    # test container cache after member is deleted manually
    @override_settings(SERIALIZER_CACHE=True)
    def test_cached_container_deleted_resource_manual(self):
        conversation = Conversation.objects.create(author_user=self.user, description="conversation description")
        response = self.client.get('/conversations/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 1)

        conversation.delete()

        response = self.client.get('/conversations/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

    # test resource cache after it is deleted manually
    @override_settings(SERIALIZER_CACHE=True)
    def test_cached_resource_deleted_resource_manual(self):
        conversation = Conversation.objects.create(author_user=self.user, description="conversation description")
        response = self.client.get('/conversations/{}/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

        conversation.delete()

        response = self.client.get('/conversations/{}/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 404)

    # test container cache following m2m_changed - Project (which inherits from djangoldp.models.Model)
    @override_settings(SERIALIZER_CACHE=True)
    def test_cached_container_m2m_changed_project(self):
        project = Project.objects.create(description='Test')
        response = self.client.get('/projects/{}/team/'.format(project.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

        project.team.add(self.user)
        response = self.client.get('/projects/{}/team/'.format(project.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 1)

        project.team.remove(self.user)
        response = self.client.get('/projects/{}/team/'.format(project.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

        project.team.add(self.user)
        project.team.clear()
        response = self.client.get('/projects/{}/team/'.format(project.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

    # test container cache following m2m_changed - Conversation (which does not inherit from djangoldp.models.Model)
    @override_settings(SERIALIZER_CACHE=True)
    def test_cached_container_m2m_changed_conversation(self):
        conversation = Conversation.objects.create(author_user=self.user, description="conversation description")
        response = self.client.get('/conversations/{}/observers/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

        conversation.observers.add(self.user)
        response = self.client.get('/conversations/{}/observers/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 1)

        conversation.observers.remove(self.user)
        response = self.client.get('/conversations/{}/observers/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)

        conversation.observers.add(self.user)
        conversation.observers.clear()
        response = self.client.get('/conversations/{}/observers/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 0)


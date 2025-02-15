from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.utils import json

from djangoldp.models import Model
from djangoldp.tests.models import (Circle, Invoice, LDPDummy, Post, Project,
                                    Resource, Space)


class PostTestCase(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                         password='glass onion')
        self.client.force_authenticate(self.user)

    def test_save_fk_graph_with_nested(self):
        post = {
            '@graph': [
                {
                    'https://cdn.startinblox.com/owl#title': "title",
                    'https://cdn.startinblox.com/owl#invoice': {
                        '@id': "_.123"
                    }
                },
                {
                    '@id': "_.123",
                    'https://cdn.startinblox.com/owl#title': "title 2"
                }
            ]
        }

        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('author', response.data)
        self.assertEqual(response.data['title'], "title")
        self.assertEqual(response.data['invoice']['title'], "title 2")

    def test_save_fk_graph_with_existing_nested(self):
        invoice = Invoice.objects.create(title="title 3")
        post = {
            '@graph': [
                {
                    'https://cdn.startinblox.com/owl#title': "title",
                    'https://cdn.startinblox.com/owl#invoice': {
                        '@id': "http://happy-dev.fr{}{}/".format(Model.container_id(invoice), invoice.id)
                    }
                }
            ]
        }

        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('author', response.data)
        self.assertEqual(response.data['title'], "title")
        self.assertEqual(response.data['invoice']['title'], "title 3")

    def test_post_should_accept_missing_field_id_nullable(self):
            body = [
                {
                    '@id': "./",
                    'https://cdn.startinblox.com/owl#content': "post update",
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
                'https://cdn.startinblox.com/owl#content': "post update",
                'https://cdn.startinblox.com/owl#peer_user': ""
            }
        ]
        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['peer_user'], None)

    def test_save_sub_object_in_new_object_with_reverse_1to1_relation(self):
        dummy = LDPDummy.objects.create(some="foo")

        body = [
            {
                '@id': "_:b216",
                'https://cdn.startinblox.com/owl#description': "user update",
                'https://cdn.startinblox.com/owl#ddummy': {
                    "@id": "http://happy-dev.fr{}{}/".format(Model.container_id(dummy), dummy.id)
                }
            },
            {
                '@id': './',
                "https://cdn.startinblox.com/owl#first_name": "Alexandre",
                "https://cdn.startinblox.com/owl#last_name": "Bourlier",
                "https://cdn.startinblox.com/owl#username": "alex",
                'https://cdn.startinblox.com/owl#userprofile': {'@id': "_:b216"}
            }
        ]
        response = self.client.post('/users/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('userprofile', response.data)

    def test_embedded_context(self):
        body = {
            '@graph': [
                {
                    '@id': "./",
                    'content': "post update",
                    'peer_user': ""
                }
            ],
            '@context': {
                "@vocab": "https://cdn.startinblox.com/owl#",
            }
        }
        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

    def test_nested_container(self):
        resource = Resource.objects.create()
        body = {
            'https://cdn.startinblox.com/owl#title': "new job",
            'https://cdn.startinblox.com/owl#slug': "job1",
        }

        response = self.client.post('/resources/{}/joboffers/'.format(resource.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['resources']['ldp:contains'][0]['@id'], resource.urlid)
        self.assertEqual(response.data['title'], "new job")


    def test_nested_container_bis(self):
        invoice = Invoice.objects.create()
        body = {
            'https://cdn.startinblox.com/owl#title': "new batch",
        }

        response = self.client.post('/invoices/{}/batches/'.format(invoice.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['invoice']['@id'],
                         "http://happy-dev.fr/invoices/{}/".format(invoice.pk))
        self.assertEqual(response.data['title'], "new batch")

    def test_nested_container_federated(self):
        resource = Resource.objects.create()
        body = {
            'https://cdn.startinblox.com/owl#@id': "http://external.job/job/1",
        }

        response = self.client.post('/resources/{}/joboffers/'.format(resource.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['@id'], "http://external.job/job/1")
        self.assertIn('@type', response.data)
        response = self.client.get('/resources/{}/'.format(resource.pk))
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'], "http://external.job/job/1")

    def test_embedded_context_2(self):
        body = {
            '@id': "./",
            'content': "post update",
            'peer_user': "",
            '@context': {
                "@vocab": "https://cdn.startinblox.com/owl#",
            }
        }

        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

    def test_auto_id(self):
        body = {
            '@id': "./",
            'content': "post update",
            'peer_user': "",
            '@context': {
                "@vocab": "https://cdn.startinblox.com/owl#",
            }
        }

        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        saved_post = Post.objects.get(pk=1)
        self.assertEqual(saved_post.urlid, "http://happy-dev.fr/posts/1/")

    def test_save_invalid_nested_user(self):
        body = {
            '@id': "./",
            'content': "post update",
            'peer_user': {'none': None},
            '@context': {
                "@vocab": "https://cdn.startinblox.com/owl#",
            }
        }

        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 400)

    def test_nested_container_user_federated(self):
        project = Project.objects.create()
        body = {
            'https://cdn.startinblox.com/owl#@id': "http://external.user/user/1/",
        }

        response = self.client.post('/projects/{}/members/'.format(project.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['@id'], "http://external.user/user/1/")
        self.assertIn('@type', response.data)
        response = self.client.get('/projects/{}/'.format(project.pk))
        self.assertEqual(response.data['members']['ldp:contains'][0]['@id'], "http://external.user/user/1/")

    #  https://www.w3.org/TR/json-ld/#value-objects
    def test_post_field_with_value_object(self):
        post = {
            'https://cdn.startinblox.com/owl#title': {
                '@value': "title",
                '@language': "en"
            }
        }
        response = self.client.post('/invoices/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], "title")

    # from JSON-LD spec: "The value associated with the @value key MUST be either a string, a number, true, false or null"
    def test_save_field_with_invalid_value_object(self):
        invoice = Invoice.objects.create(title="title 3")
        post = {
            'https://cdn.startinblox.com/owl#invoice': {
                '@value': {'title': 'title',
                           '@id': "http://happy-dev.fr{}{}/".format(Model.container_id(invoice), invoice.id)}
            }
        }
        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 400)

    # TODO: bug with PyLD: https://github.com/digitalbazaar/pyld/issues/142
    # from JSON-LD spec: "If the value associated with the @type key is @json, the value MAY be either an array or an object"
    '''
    def test_save_field_with_object_value_object(self):
        invoice = Invoice.objects.create(title="title 3")
        post = {
            'https://cdn.startinblox.com/owl#invoice': {
                '@value': {'title': 'title', '@id': "http://happy-dev.fr{}{}/".format(Model.container_id(invoice), invoice.id)},
                '@type': '@json'
            }
        }
        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
    '''

    # the below test is necessary because of an obscure bug where the OneToOne field is successfully applied
    # during the life of the serializer (and response) but is not persisted in the database,
    # when it is posted onto the reverse relation
    def test_one_to_one_field_reverse_post(self):
        self.assertEqual(Circle.objects.count(), 0)
        self.assertEqual(Space.objects.count(), 0)

        body = {
            '@context': {'@vocab': "https://cdn.startinblox.com/owl#" },
            'space': {'name': "Etablissement"}
        }

        response = self.client.post('/circles/', data=json.dumps(body), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Circle.objects.count(), 1)
        self.assertEqual(Space.objects.count(), 1)

        circle = Circle.objects.all()[0]
        space = circle.space

        self.assertIsNotNone(space)
        self.assertIsNotNone(space.circle)

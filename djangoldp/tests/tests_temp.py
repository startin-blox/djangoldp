from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from djangoldp.tests.models import Resource


class TestTemp(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')

    def tearDown(self):
        pass

    def test_nested_container_federated(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#@id': "http://external.job/job/1",
        }

        response = self.client.post('/resources/{}/joboffers/'.format(resource.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['resources']['ldp:contains'][0]['@id'], "http://testserver/resources/{}/".format(resource.pk))
        self.assertEqual(response.data['@id'], "http://external.job/job/1")

    def test_m2m_new_link_federated(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                'http://happy-dev.fr/owl/#@id': 'http://external.job/job/1',
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://external.job/job/1")


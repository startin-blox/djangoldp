import json

from django.test import TestCase
from rest_framework.test import APIRequestFactory, APITestCase
from djangoldp.views.type_index import PublicTypeIndexView


class PublicTypeIndexViewTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_public_type_index_has_graph(self):
        request = self.factory.get('/profile/publicTypeIndex')
        view = PublicTypeIndexView.as_view()
        response = view(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/ld+json')

        data = json.loads(response.content)
        self.assertIn('@context', data)
        self.assertIn('@graph', data)
        self.assertIsInstance(data['@graph'], list)

        first = data['@graph'][0]
        self.assertIn('@id', first)
        self.assertIn('@type', first)
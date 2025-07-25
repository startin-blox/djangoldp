# tests/test_views.py
import json
from rest_framework.test import APITestCase, APIRequestFactory, APIClient

from djangoldp.views.instance_container import InstanceRootContainerView

class InstanceRootContainerViewTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()

    def test_instance_root_container_returns_valid_jsonld(self):
        request = self.factory.get('/')
        view = InstanceRootContainerView.as_view()
        response = view(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/ld+json')

        data = json.loads(response.content)
        self.assertIn('@context', data)
        self.assertIn('@id', data)
        self.assertIn('@type', data)
        self.assertEqual(data['@type'], 'ldp:Container')
        self.assertIn('ldp:contains', data)
        self.assertIsInstance(data['ldp:contains'], list)
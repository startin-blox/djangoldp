import json
from django.test import override_settings
from rest_framework.test import APIRequestFactory, APITestCase
from djangoldp.views.webid import InstanceWebIDView

class InstanceWebIDViewTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @override_settings(TYPE_INDEX_LOCATION='/customTypeIndex')
    def test_instance_webid_returns_expected_profile(self):
        request = self.factory.get('/profile')
        view = InstanceWebIDView.as_view()
        response = view(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn('@context', data)
        self.assertIn('@graph', data)
        self.assertEqual(len(data['@graph']), 2)

        doc, agent = data['@graph']
        self.assertIn('foaf:primaryTopic', doc)
        self.assertIn('solid:publicTypeIndex', agent)
        self.assertTrue(agent['solid:publicTypeIndex'].endswith('/customTypeIndex'))
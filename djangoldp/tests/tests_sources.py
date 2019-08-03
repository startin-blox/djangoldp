from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from djangoldp.models import LDPSource


class TestSource(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()

    def tearDown(self):
        pass

    def test_get_resource(self):
        source = LDPSource.objects.create(federation="source_name", container="http://bar.foo/")
        response = self.client.get('/sources/{}/'.format(source.federation), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

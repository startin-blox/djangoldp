from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from djangoldp.tests.models import Post


class TestPagination(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        for i in range(0, 30):
            Post.objects.create(content="content {}".format(i))

    def tearDown(self):
        pass

    def test_next(self):
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('link', response.headers)
        # Check for pagination link
        self.assertIn('<http://testserver/posts/?p=2>; rel="next"', response.headers['link'])
        # Check for LDP type links (added in Phase 1)
        self.assertIn('ldp#Resource', response.headers['link'])
        self.assertIn('ldp#Container', response.headers['link'])

    def test_previous(self):
        response = self.client.get('/posts/?p=2', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('link', response.headers)
        # Check for pagination links
        self.assertIn('<http://testserver/posts/>; rel="prev"', response.headers['link'])
        self.assertIn('<http://testserver/posts/?p=3>; rel="next"', response.headers['link'])
        # Check for LDP type links (added in Phase 1)
        self.assertIn('ldp#Resource', response.headers['link'])
        self.assertIn('ldp#Container', response.headers['link'])

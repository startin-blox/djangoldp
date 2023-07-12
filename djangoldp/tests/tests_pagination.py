from rest_framework.test import APIRequestFactory, APIClient, APITestCase

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
        self.assertEquals(response.headers['link'], '<http://testserver/posts/?p=2>; rel="next"')

    def test_previous(self):
        response = self.client.get('/posts/?p=2', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('link', response.headers)
        self.assertEquals(response.headers['link'],
                          '<http://testserver/posts/>; rel="prev", <http://testserver/posts/?p=3>; rel="next"')

import json

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from djangoldp.tests.models import Post


class TestGET(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')

    def tearDown(self):
        self.user.delete()

    def test_get(self):
        post = Post.objects.create(content="content")
        response = self.client.get('/posts/{}/'.format(post.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['content'], "content")
        self.assertIn('author', response.data)

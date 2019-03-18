import json

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient, APITestCase


class TestAutoAuthor(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')

    def tearDown(self):
        self.user.delete()

    def test_save_with_anonymous_user(self):
        post = {
            '@context': "http://owl.openinitiative.com/oicontext.jsonld",
            '@graph': [{'http://happy-dev.fr/owl/#content': "post content"}]}

        response = self.client.post('/posts/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('author', response.data)
        self.assertEquals(response.data['content'], "post content")

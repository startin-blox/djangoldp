from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APIRequestFactory, APIClient, APITestCase
from djangoldp.tests.models import User, Circle, Project
from djangoldp.serializers import LDPSerializer
from djangoldp.related import get_prefetch_fields


class LDPViewSet(APITestCase):

    user_serializer_fields = ['@id', 'username', 'first_name', 'last_name', 'email', 'userprofile', 'conversation_set',
                              'circle_set', 'projects']
    user_expected_fields = {'userprofile', 'conversation_set', 'circle_set', 'projects', 'circle_set__owner',
                            'conversation_set__author_user', 'conversation_set__peer_user', 'circle_set__space'}
    project_serializer_fields = ['@id', 'description', 'members']
    project_expected_fields = {'members', 'members__userprofile'}

    def setUpLoggedInUser(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                         password='glass onion', first_name='John')
        self.client.force_authenticate(self.user)

    def _get_serializer(self, model, depth, fields):
        meta_args = {'model': model, 'depth': depth, 'fields': fields}
        meta_class = type('Meta', (), meta_args)
        return (type(LDPSerializer)('TestSerializer', (LDPSerializer,), {'Meta': meta_class}))()

    def test_get_prefetch_fields_user(self):
        model = User
        depth = 0
        serializer_fields = self.user_serializer_fields
        expected_fields = self.user_expected_fields
        serializer = self._get_serializer(model, depth, serializer_fields)
        result = get_prefetch_fields(model, serializer, depth)
        self.assertEqual(expected_fields, result)

    def test_get_prefetch_fields_circle(self):
        model = Circle
        depth = 0
        serializer_fields = ['@id', 'name', 'description', 'owner', 'members', 'team']
        expected_fields = {'owner', 'members', 'team', 'members__user', 'members__circle', 'team__userprofile', 'space'}
        serializer = self._get_serializer(model, depth, serializer_fields)
        result = get_prefetch_fields(model, serializer, depth)
        self.assertEqual(expected_fields, result)

    def test_get_prefetch_fields_project(self):
        model = Project
        depth = 0
        serializer_fields = self.project_serializer_fields
        expected_fields = self.project_expected_fields
        serializer = self._get_serializer(model, depth, serializer_fields)
        result = get_prefetch_fields(model, serializer, depth)
        self.assertEqual(expected_fields, result)

    # TODO: dynamically generating serializer fields is necessary to retrieve many-to-many fields at depth > 0,
    #  but the _all_ default has issues detecting reverse many-to-many fields
    '''def test_get_prefetch_fields_depth_1(self):
        model = Project
        depth = 2
        serializer_fields = self.project_serializer_fields
        user_expected = set(['team__' + x for x in self.user_expected_fields])
        expected_fields = self.project_expected_fields.union(user_expected)
        serializer = self._get_serializer(model, depth, serializer_fields)
        result = get_prefetch_fields(model, serializer, depth)
        self.assertEqual(expected_fields, result)'''

    def test_get_shape_param(self):
        self.setUpLoggedInUser()
        circle = Circle.objects.create(name='test circle')

        # request id and name only
        fields_shape = '["@id", "name"]'

        response = self.client.get('/circles/', HTTP_ACCEPT_MODEL_FIELDS=fields_shape)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data_keys = response.data['ldp:contains'][0].keys()
        self.assertEqual(len(response_data_keys), 4)
        self.assertIn('@id', response_data_keys)
        self.assertIn('name', response_data_keys)
        self.assertIn('@type', response_data_keys)
        self.assertIn('permissions', response_data_keys)

    def test_search_fields_basic(self):
        self.setUpLoggedInUser()
        lowercase_circle = Circle.objects.create(name='test circle')
        uppercase_circle = Circle.objects.create(name='hello world', description='test')

        response = self.client.get('/circles/?search-fields=name&search-terms=test&search-method=basic')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['ldp:contains']), 1)
        self.assertEqual(response.data['ldp:contains'][0]['name'], lowercase_circle.name)

        # test multiple search fields
        response = self.client.get('/circles/?search-fields=name,description&search-terms=test&search-method=basic')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['ldp:contains']), 2)
    
    def test_search_fields_ibasic(self):
        self.setUpLoggedInUser()
        lowercase_circle = Circle.objects.create(name='test circle')
        uppercase_circle = Circle.objects.create(name='TEST')

        response = self.client.get('/circles/?search-fields=name&search-terms=test&search-method=ibasic')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['ldp:contains']), 2)
    
    def test_search_fields_exact(self):
        self.setUpLoggedInUser()
        lowercase_circle = Circle.objects.create(name='test circle')
        uppercase_circle = Circle.objects.create(name='TEST')

        response = self.client.get('/circles/?search-fields=name&search-terms=test&search-method=exact')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['ldp:contains']), 0)

        response = self.client.get('/circles/?search-fields=name&search-terms=test%20circle&search-method=exact')
        self.assertEqual(response.data['ldp:contains'][0]['name'], lowercase_circle.name)

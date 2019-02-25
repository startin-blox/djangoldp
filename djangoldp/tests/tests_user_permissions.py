from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory

from djangoldp.permissions import AnonymousReadOnly
from djangoldp.tests.models import JobOffer
from djangoldp.views import LDPViewSet


class TestUserPermissions(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        #        self.c = Client()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        self.job = JobOffer.objects.create(title="job")

    def tearDown(self):
        self.user.delete()

    def test_get_with_user(self):
        request = self.factory.get('/job-offers/')
        request.user = self.user
        my_view = LDPViewSet.as_view({'get': 'list'}, model=JobOffer, nested_fields=["skills"],
                                     permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 200)

    def test_request_options_create_with_user(self):
        request = self.factory.options('/job-offers/')
        request.user = self.user
        my_view = LDPViewSet.as_view({'options': 'create'}, model=JobOffer, nested_fields=["skills"],
                                     permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 201)

    def test_request_options_update_with_user(self):
        request = self.factory.options('/job-offers/' + str(self.job.pk) + "/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'options': 'update'}, model=JobOffer, nested_fields=["skills"],
                                     permission_classes=[AnonymousReadOnly])
        response = my_view(request, pk=self.job.pk)
        self.assertEqual(response.status_code, 200)

    def test_request_patch_with_user(self):
        request = self.factory.patch('/job-offers/' + str(self.job.pk) + "/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'patch': 'partial_update'}, model=JobOffer, nested_fields=["skills"])
        response = my_view(request, pk=self.job.pk)
        self.assertEqual(response.status_code, 200)
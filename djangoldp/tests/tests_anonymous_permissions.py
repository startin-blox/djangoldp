from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory

from djangoldp.permissions import AnonymousReadOnly
from djangoldp.tests.models import JobOffer
from djangoldp.views import LDPViewSet


class TestAnonymousUserPermissions(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        #        self.c = Client()
        self.user = AnonymousUser

    def test_get_request_with_anonymousUser(self):
        request = self.factory.get("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'get': 'list'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 200)

    def test_request_options_create_with_anonymousUser(self):
        request = self.factory.options("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'options': 'create'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 403)

    def test_request_options_update_with_anonymousUser(self):
        request = self.factory.options("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'options': 'update'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 403)

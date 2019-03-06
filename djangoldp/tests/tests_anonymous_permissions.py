from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory

from guardian.shortcuts import get_anonymous_user

from djangoldp.permissions import AnonymousReadOnly
from djangoldp.tests.models import JobOffer
from djangoldp.views import LDPViewSet


class TestAnonymousUserPermissions(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_anonymous_user()
        self.job = JobOffer.objects.create(title="job")

    def test_get_request_with_anonymousUser(self):
        request = self.factory.get("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'get': 'list'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=(AnonymousReadOnly,))
        response = my_view(request)
        self.assertEqual(response.status_code, 200)

    def test_post_request_with_anonymousUser(self):
        request = self.factory.post("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'post': 'create'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=(AnonymousReadOnly,))
        response = my_view(request)
        self.assertEqual(response.status_code, 403)

    def test_put_request_with_anonymousUser(self):
        request = self.factory.put("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'put': 'update'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=(AnonymousReadOnly,))
        response = my_view(request, pk=self.job.pk)
        self.assertEqual(response.status_code, 403)

    def test_patch_request_with_anonymousUser(self):
        request = self.factory.patch("/job-offers/")
        request.user = self.user
        my_view = LDPViewSet.as_view({'patch': 'partial_update'},
                                     model=JobOffer,
                                     nested_fields=["skills"],
                                     permission_classes=(AnonymousReadOnly,))
        response = my_view(request, pk=self.job.pk)
        self.assertEqual(response.status_code, 403)
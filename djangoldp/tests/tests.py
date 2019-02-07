from django.test import TestCase

from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Skill, JobOffer


class Serializer(TestCase):

    def test_container_serializer_save(self):
        skill1 = Skill.objects.create(title="skill1")
        skill2 = Skill.objects.create(title="skill2")
        job = {"title": "job test",
               "skills": {
                   "ldp:contains": [
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk)},
                   ]}
               }

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 2)

    def test_save_without_nested_fields(self):
        skill1 = Skill.objects.create(title="skill1")
        skill2 = Skill.objects.create(title="skill2")
        job = {"title": "job test"}

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 0)

from django.test import TestCase, Client, RequestFactory
from djangoldp.views import LDPViewSet
from djangoldp.permissions import AnonymousReadOnly

from django.contrib.auth.models import AnonymousUser, User
from djangoldp_joboffer.models import JobOffer


class TestUserPermissions (TestCase):
    def setUp(self):
        self.factory = RequestFactory()
#        self.c = Client()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')

    def tearDown(self):
        self.user.delete()

    def test_get_with_user(self):
        request = self.factory.get('/job-offers/')
        request.user = self.user
        my_view = LDPViewSet.as_view({'get': 'list'}, model=JobOffer, nested_fields=["skills"], permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 200)

    def test_request_options_create_with_user(self):
        request = self.factory.options('/job-offers/')
        request.user = self.user
        my_view = LDPViewSet.as_view({'options': 'create'}, model=JobOffer, nested_fields=["skills"], permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 201)

    def test_request_options_update_with_user(self):
        request = self.factory.options('/job-offers/')
        request.user = self.user
        my_view = LDPViewSet.as_view({'options': 'update'}, model=JobOffer, nested_fields=["skills"], permission_classes=[AnonymousReadOnly])
        response = my_view(request)
        self.assertEqual(response.status_code, 201)


class TestAnonymousUserPermissions (TestCase):
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



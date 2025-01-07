from django.test import TestCase

from djangoldp.models import Model
from djangoldp.tests.models import (Dummy, JobOffer, LDPDummy,
                                    NoSuperUsersAllowedModel)


class LDPModelTest(TestCase):

    def test_class_not_inheriting_ldp_model(self):
        dummy = Dummy.objects.create(some="text")
        self.assertEqual("/dummys/", Model.container_id(dummy))
        self.assertEqual("/dummys/{}/".format(dummy.slug), Model.resource_id(dummy))

    def test_class_inheriting_ldp_model(self):
        dummy = LDPDummy.objects.create(some="text")
        self.assertEqual("/ldpdummys/", dummy.get_container_id())
        self.assertEqual("http://happy-dev.fr/ldpdummys/{}/".format(dummy.pk), dummy.get_absolute_url())
        self.assertEqual("/ldpdummys/", Model.container_id(dummy))
        self.assertEqual("/ldpdummys/{}/".format(dummy.pk), Model.resource_id(dummy))

    def test_from_resolve_id(self):
        saved_instance = Dummy.objects.create(some="text", slug="someid")
        result = Model.resolve_id("/dummys/{}/".format(saved_instance.slug))
        self.assertEqual(saved_instance, result)

    def test_resolve_container(self):
        result = Model.resolve_container("/dummys/")
        self.assertEqual(Dummy, result)

    def test_auto_url(self):
        from django.urls import get_resolver
        dummy = LDPDummy.objects.create(some="text")
        view_name = '{}-list'.format(dummy._meta.object_name.lower())
        path = 'http://happy-dev.fr/{}{}/'.format(get_resolver().reverse_dict[view_name][0][0][0], dummy.pk)

        self.assertEqual(path, dummy.get_absolute_url())

    def test_ldp_manager_local_objects(self):
        local = LDPDummy.objects.create(some='text')
        external = LDPDummy.objects.create(some='text', urlid='https://distant.com/ldpdummys/1/')
        self.assertEqual(LDPDummy.objects.count(), 2)
        local_queryset = LDPDummy.objects.local()
        self.assertEqual(local_queryset.count(), 1)
        self.assertIn(local, local_queryset)
        self.assertNotIn(external, local_queryset)
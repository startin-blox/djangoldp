import unittest

from django.test import TestCase

from djangoldp.models import Model
from djangoldp.tests.models import Dummy, LDPDummy


class LDPModelTest(TestCase):

    def test_class_not_inheriting_ldp_model(self):
        dummy = Dummy.objects.create(some="text")
        self.assertEquals("/dummys/", Model.container_id(dummy))
        self.assertEquals("/dummys/{}".format(dummy.pk), Model.resource_id(dummy))

    def test_class_inheriting_ldp_model(self):
        dummy = LDPDummy.objects.create(some="text")
        self.assertEquals("/ldp-dummys/", dummy.get_container_id())
        self.assertEquals("/ldp-dummys/{}".format(dummy.pk), dummy.get_absolute_url())
        self.assertEquals("/ldp-dummys/", Model.container_id(dummy))
        self.assertEquals("/ldp-dummys/{}".format(dummy.pk), Model.resource_id(dummy))


    @unittest.skip("futur feature: avoid urls.py on apps")
    def test_auto_url(self):
        from django.urls import get_resolver
        dummy = LDPDummy.objects.create(some="text")
        view_name = '{}-list'.format(dummy._meta.object_name.lower())
        path = '/{}'.format(get_resolver().reverse_dict[view_name][0][0][0], dummy.pk)

        self.assertEquals(path, dummy.get_absolute_url())

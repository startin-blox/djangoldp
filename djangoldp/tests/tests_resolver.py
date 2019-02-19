from django.test import TestCase

from djangoldp.models import LDPModel
from djangoldp.tests.models import Dummy, LDPDummy


class UrlUtils(TestCase):

    def test_class_not_inheriting_ldp_model(self):
        dummy = Dummy.objects.create(some="text")
        self.assertEquals("/dummys/", LDPModel.container_path(dummy))
        self.assertEquals("/dummys/{}".format(dummy.pk), LDPModel.resource_path(dummy))

    def test_class_inheriting_ldp_model(self):
        dummy = LDPDummy.objects.create(some="text")
        self.assertEquals("/ldp-dummys/", dummy.get_container_path())
        self.assertEquals("/ldp-dummys/{}".format(dummy.pk), dummy.get_resource_path())
        self.assertEquals("/ldp-dummys/", LDPModel.container_path(dummy))
        self.assertEquals("/ldp-dummys/{}".format(dummy.pk), LDPModel.resource_path(dummy))

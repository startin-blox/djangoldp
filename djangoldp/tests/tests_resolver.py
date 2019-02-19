from django.test import TestCase

from djangoldp.resolver import LDPResolver
from djangoldp.tests.models import Dummy, LDPDummy


class UrlUtils(TestCase):

    def test_class_not_inheriting_ldp_model(self):
        dummy = Dummy.objects.create(some="text")
        self.assertEquals("http://localhost/dummys/{}".format(dummy.pk), LDPResolver.resource_url(dummy))
        self.assertEquals("/dummys/{}".format(dummy.pk), LDPResolver.resource_path(dummy))
        self.assertEquals("http://localhost/dummys", LDPResolver.container_url(dummy))
        self.assertEquals("/dummys", LDPResolver.container_path(dummy))

    def test_class_inheriting_ldp_model(self):
        dummy = LDPDummy.objects.create(some="text")
        self.assertEquals("http://localhost/ldp-dummys/{}".format(dummy.pk), LDPResolver.resource_url(dummy))
        self.assertEquals("/ldp-dummys/{}".format(dummy.pk), LDPResolver.resource_path(dummy))
        self.assertEquals("http://localhost/ldp-dummys/{}".format(dummy.pk), dummy.resource_url())
        self.assertEquals("/ldp-dummys/{}".format(dummy.pk), dummy.resource_path())
        self.assertEquals("http://localhost/ldp-dummys", LDPResolver.container_url(dummy))
        self.assertEquals("/ldp-dummys", LDPResolver.container_path(dummy))
        self.assertEquals("http://localhost/dummys/", dummy.container_url())
        self.assertEquals("/ldp-dummys", dummy.container_path())

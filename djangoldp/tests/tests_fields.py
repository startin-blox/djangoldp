from django.test import TestCase

from djangoldp.tests.models import Enterprise


class LDPFieldTest(TestCase):
    def test_get_field_from_rdf_type(self):
        name_field = Enterprise._meta.get_field("name")
        self.assertEqual(name_field.get_rdf_types(), {"dfc-b:name", "alt:name"})
        vat_field = Enterprise._meta.get_field("VATstatus")
        self.assertEqual(
            vat_field.get_rdf_types(), {"dfc-b:VATStatus", "alt:VATStatus"}
        )
        affiliated_field = Enterprise._meta.get_field("affiliated_to")
        self.assertEqual(
            affiliated_field.get_rdf_types(), {"dfc-b:affiliatedTo", "alt:affiliatedTo"}
        )

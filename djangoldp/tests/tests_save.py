from django.test import TestCase

from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Skill, JobOffer, Invoice


class Save(TestCase):

    def test_save_m2m_graph_with_many_nested(self):
        invoice = {
            "@graph": [
                {
                    "@id": "./",
                    "batches": {"@id": "_:b381"},
                    "title": "Nouvelle facture",
                },
                {
                    "@id": "_:b381",
                    "tasks": {"@id": "_:b382"},
                    "title": "Batch 1"
                },
                {
                    "@id": "_:b382",
                    "title": "Tache 1"
                }
            ]
        }

        meta_args = {'model': Invoice, 'depth': 2, 'fields': ("@id", "title", "batches")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('InvoiceSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=invoice)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "Nouvelle facture")
        self.assertIs(result.batches.count(), 1)
        self.assertEquals(result.batches.all()[0].title, "Batch 1")
        self.assertIs(result.batches.all()[0].tasks.count(), 1)
        #self.assertEquals(result.batches.all()[0].tasks.all()[0].title, "Tache 1")

    def test_save_m2m(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")

        job = {"title": "job test",
               "skills": {
                   "ldp:contains": [
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk), "title": "skill2 UP"},
                       {"title": "skill3 NEW", "obligatoire": "obligatoire"},
                   ]}
               }

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 3)
        self.assertEquals(result.skills.all()[0].title, "skill1")  # no change
        self.assertEquals(result.skills.all()[1].title, "skill2 UP")  # title updated
        self.assertEquals(result.skills.all()[2].title, "skill3 NEW")  # creation on the fly

    def test_save_m2m_graph_simple(self):
        job = {"@graph": [
            {"title": "job test",
             },
        ]}

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 0)

    def test_save_m2m_graph_with_nested(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")

        job = {"@graph": [
            {"title": "job test",
             "skills": {"@id": "_.123"}
             },
            {"@id": "_.123", "title": "skill3 NEW", "obligatoire": "obligatoire"},
        ]}

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 1)
        self.assertEquals(result.skills.all()[0].title, "skill3 NEW")  # creation on the fly

    def test_save_without_nested_fields(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")
        job = {"title": "job test"}

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 0)

    def test_save_on_sub_iri(self):
        """
            POST /job-offers/1/skills/
        """
        job = JobOffer.objects.create(title="job test")
        skill = {"title": "new SKILL"}

        meta_args = {'model': Skill, 'depth': 1, 'fields': ("@id", "title")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('SkillSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=skill)
        serializer.is_valid()
        kwargs = {}
        kwargs['joboffer'] = job
        result = serializer.save(**kwargs)

        self.assertEquals(result.title, "new SKILL")
        self.assertIs(result.joboffer_set.count(), 1)
        self.assertEquals(result.joboffer_set.get(), job)
        self.assertIs(result.joboffer_set.get().skills.count(), 1)

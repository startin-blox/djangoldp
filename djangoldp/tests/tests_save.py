from django.test import TestCase

from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Skill, JobOffer


class Save(TestCase):

    def test_save_m2m(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")

        job = {"title": "job test",
               "skills": {
                   "ldp:contains": [
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk), "title": "skill2 UP"},
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
        self.assertEquals(result.skills.all()[0].title, "skill1")     # no change
        self.assertEquals(result.skills.all()[1].title, "skill2 UP")  # title updated

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


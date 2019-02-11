from django.test import TestCase

from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Skill, JobOffer


class Serializer(TestCase):

    def test_update(self):
        skill1 = Skill.objects.create(title="skill1")
        skill2 = Skill.objects.create(title="skill2")
        job1 = JobOffer.objects.create(title="job test")

        job = {"@id": "https://happy-dev.fr/job-offers/{}/".format(job1.pk),
               "title": "job test updated",
               "skills": {
                   "ldp:contains": [
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk)},
                   ]}
               }

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job, instance=job1)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test updated")
        self.assertIs(result.skills.count(), 2)

    def test_update_graph(self):
        skill1 = Skill.objects.create(title="skill1")
        skill2 = Skill.objects.create(title="skill2")
        job1 = JobOffer.objects.create(title="job test")

        job = {"@graph": [{"@id": "https://happy-dev.fr/job-offers/{}/".format(job1.pk),
               "title": "job test updated",
               "skills": {
                   "ldp:contains": [
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk)},
                   ]}
               }]
            }

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job, instance=job1)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test updated")
        self.assertIs(result.skills.count(), 2)

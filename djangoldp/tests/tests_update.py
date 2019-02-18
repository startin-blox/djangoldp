from django.test import TestCase

from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Skill, JobOffer, Thread, Message


class Serializer(TestCase):

    def test_update(self):
        skill = Skill.objects.create(title="to drop", obligatoire="obligatoire")
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")
        job1 = JobOffer.objects.create(title="job test")
        job1.skills.add(skill)

        job = {"@id": "https://happy-dev.fr/job-offers/{}/".format(job1.pk),
               "title": "job test updated",
               "skills": {
                   "ldp:contains": [
                       {"title": "new skill", "obligatoire": "okay"},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk), "title": "skill2 UP"},
                   ]}
               }

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job, instance=job1)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test updated")
        self.assertIs(result.skills.count(), 3)
        skills = result.skills.all().order_by('title')
        self.assertEquals(skills[0].title, "new skill")  # new skill
        self.assertEquals(skills[1].title, "skill1")  # no change
        self.assertEquals(skills[2].title, "skill2 UP")  # title updated

    def test_update_graph(self):
        skill = Skill.objects.create(title="to drop", obligatoire="obligatoire")
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")
        job1 = JobOffer.objects.create(title="job test")
        job1.skills.add(skill)

        job = {"@graph": [{"@id": "https://happy-dev.fr/job-offers/{}/".format(job1.pk),
                           "title": "job test updated",
                           "skills": {
                               "ldp:contains": [
                                   {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                                   {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk)},
                                   {"@id": "_.123"},
                               ]}
                           },
                          {
                              "@id": "_.123",
                              "title": "new skill",
                              "obligatoire": "okay"
                          },
                          {
                              "@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk),
                          },
                          {
                              "@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk),
                              "title": "skill2 UP"
                          }]
               }

        meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job, instance=job1)
        serializer.is_valid()
        result = serializer.save()

        skills = result.skills.all().order_by('title')

        self.assertEquals(result.title, "job test updated")
        self.assertIs(result.skills.count(), 3)
        self.assertEquals(skills[0].title, "new skill")  # new skill
        self.assertEquals(skills[1].title, "skill1")  # no change
        self.assertEquals(skills[2].title, "skill2 UP")  # title updated

        def test_update_graph_2(self):
            skill = Skill.objects.create(title="to drop", obligatoire="obligatoire")
            skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire")
            skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire")
            job1 = JobOffer.objects.create(title="job test")
            job1.skills.add(skill)

            job = {"@graph":[{"@id": "https://happy-dev.fr/job-offers/{}/".format(job1.pk),
                               "title": "job test updated",
                               "skills": {
                                   "@id": "https://happy-dev.fr/job-offers/{}/skills/".format(job1.pk)
                                    }
                              },
                              {
                                  "@id": "_.123",
                                  "title": "new skill",
                                  "obligatoire": "okay"
                              },
                              {
                                  "@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk),
                              },
                              {
                                  "@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk),
                                  "title": "skill2 UP"
                              },
                              {
                                  '@id': "https://happy-dev.fr/job-offers/{}/skills/".format(job1.pk),
                                  "ldp:contains": [
                                      {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.pk)},
                                      {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.pk)},
                                      {"@id": "_.123"},
                                  ]
                              }]
                   }

            meta_args = {'model': JobOffer, 'depth': 1, 'fields': ("@id", "title", "skills")}

            meta_class = type('Meta', (), meta_args)
            serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
            serializer = serializer_class(data=job, instance=job1)
            serializer.is_valid()
            result = serializer.save()

            skills = result.skills.all().order_by('title')

            self.assertEquals(result.title, "job test updated")
            self.assertIs(result.skills.count(), 3)
            self.assertEquals(skills[0].title, "new skill")  # new skill
            self.assertEquals(skills[1].title, "skill1")  # no change
            self.assertEquals(skills[2].title, "skill2 UP")  # title updated

    def test_update_list_with_reverse_relation(self):
        thread = Thread.objects.create(description="Thread 1")
        message1 = Message.objects.create(text="Message 1", thread=thread)
        message2 = Message.objects.create(text="Message 2", thread=thread)


        json = {"@graph": [
                {"@id": "https://happy-dev.fr/messages/{}/".format(message1.pk),
             "text": "Message 1 UP"
                },
                {"@id": "https://happy-dev.fr/messages/{}/".format(message2.pk),
                 "text": "Message 2 UP"
                },
                {
                 '@id': "https://happy-dev.fr/threads/{}/".format(thread.pk),
                 'description': "Thread 1 UP",
                 "message_set": [
                     {"@id": "https://happy-dev.fr/messages/{}/".format(message1.pk)},
                     {"@id": "https://happy-dev.fr/messages/{}/".format(message2.pk)},
                 ]
                 }
                ]
           }

        meta_args = {'model': Thread, 'depth': 1, 'fields': ("@id", "description", "message_set" )}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('ThreadSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=json, instance=thread)
        serializer.is_valid()
        result = serializer.save()

        messages = result.message_set.all().order_by('text')

        self.assertEquals(result.description, "Thread 1 UP")
        self.assertIs(result.message_set.count(), 2)
        self.assertEquals(messages[0].text, "Message 1 UP")
        self.assertEquals(messages[1].text, "Message 2 UP")

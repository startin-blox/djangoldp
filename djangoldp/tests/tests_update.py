import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.utils import json

from djangoldp.serializers import LDPSerializer, LDListMixin
from djangoldp.tests.models import Post, UserProfile, Resource, Circle
from djangoldp.tests.models import Skill, JobOffer, Conversation, Message, Project


class Update(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                         password='glass onion')
        self.client.force_authenticate(user=self.user)
        LDListMixin.to_representation_cache.reset()
        LDPSerializer.to_representation_cache.reset()

    def tearDown(self):
        pass

    def test_update(self):
        skill = Skill.objects.create(title="to drop", obligatoire="obligatoire", slug="slug1")
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire", slug="slug2")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire", slug="slug3")
        job1 = JobOffer.objects.create(title="job test")
        job1.skills.add(skill)

        job = {"@id": "https://happy-dev.fr/job-offers/{}/".format(job1.slug),
               "title": "job test updated",
               "skills": {
                   "ldp:contains": [
                       {"title": "new skill", "obligatoire": "okay"},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.slug)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.slug), "title": "skill2 UP"},
                   ]}
               }

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills")}

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
        skill = Skill.objects.create(title="to drop", obligatoire="obligatoire", slug="slug1")
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire", slug="slug2")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire", slug="slug3")
        job1 = JobOffer.objects.create(title="job test", slug="slug4")
        job1.skills.add(skill)

        job = {"@graph":
            [
                {
                    "@id": "https://happy-dev.fr/job-offers/{}/".format(job1.slug),
                    "title": "job test updated",
                    "skills": {
                        "ldp:contains": [
                            {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.slug)},
                            {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.slug)},
                            {"@id": "_.123"},
                        ]}
                },
                {
                    "@id": "_.123",
                    "title": "new skill",
                    "obligatoire": "okay"
                },
                {
                    "@id": "https://happy-dev.fr/skills/{}/".format(skill1.slug),
                },
                {
                    "@id": "https://happy-dev.fr/skills/{}/".format(skill2.slug),
                    "title": "skill2 UP"
                }
            ]
        }

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills")}

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
        skill = Skill.objects.create(title="to drop", obligatoire="obligatoire", slug="slug")
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire", slug="slug1")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire", slug="slug2")
        job1 = JobOffer.objects.create(title="job test", slug="slug1")
        job1.skills.add(skill)

        job = {"@graph":
            [
                {
                    "@id": "https://happy-dev.fr/job-offers/{}/".format(job1.slug),
                    "title": "job test updated",
                    "skills": {
                        "@id": "https://happy-dev.fr/job-offers/{}/skills/".format(job1.slug)
                    }
                },
                {
                    "@id": "_.123",
                    "title": "new skill",
                    "obligatoire": "okay"
                },
                {
                    "@id": "https://happy-dev.fr/skills/{}/".format(skill1.slug),
                },
                {
                    "@id": "https://happy-dev.fr/skills/{}/".format(skill2.slug),
                    "title": "skill2 UP"
                },
                {
                    '@id': "https://happy-dev.fr/job-offers/{}/skills/".format(job1.slug),
                    "ldp:contains": [
                        {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.slug)},
                        {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.slug)},
                        {"@id": "_.123"},
                    ]
                }
            ]
        }

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills", "slug")}

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
        self.assertEquals(skill, skill._meta.model.objects.get(pk=skill.pk))  # title updated

    def test_update_list_with_reverse_relation(self):
        user1 = get_user_model().objects.create()
        conversation = Conversation.objects.create(description="Conversation 1", author_user=user1)
        message1 = Message.objects.create(text="Message 1", conversation=conversation, author_user=user1)
        message2 = Message.objects.create(text="Message 2", conversation=conversation, author_user=user1)

        json = {"@graph": [
            {
                "@id": "https://happy-dev.fr/messages/{}/".format(message1.pk),
                "text": "Message 1 UP"
            },
            {
                "@id": "https://happy-dev.fr/messages/{}/".format(message2.pk),
                "text": "Message 2 UP"
            },
            {
                '@id': "https://happy-dev.fr/conversations/{}/".format(conversation.pk),
                'description': "Conversation 1 UP",
                "message_set": [
                    {"@id": "https://happy-dev.fr/messages/{}/".format(message1.pk)},
                    {"@id": "https://happy-dev.fr/messages/{}/".format(message2.pk)},
                ]
            }
        ]
        }

        meta_args = {'model': Conversation, 'depth': 2, 'fields': ("@id", "description", "message_set")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('ConversationSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=json, instance=conversation)
        serializer.is_valid()
        result = serializer.save()

        messages = result.message_set.all().order_by('text')

        self.assertEquals(result.description, "Conversation 1 UP")
        self.assertIs(result.message_set.count(), 2)
        self.assertEquals(messages[0].text, "Message 1 UP")
        self.assertEquals(messages[1].text, "Message 2 UP")

    def test_add_new_element_with_foreign_key_id(self):
        user1 = get_user_model().objects.create()
        conversation = Conversation.objects.create(description="Conversation 1", author_user=user1)
        message1 = Message.objects.create(text="Message 1", conversation=conversation, author_user=user1)
        message2 = Message.objects.create(text="Message 2", conversation=conversation, author_user=user1)

        json = {"@graph": [
            {
                "@id": "https://happy-dev.fr/messages/{}/".format(message1.pk),
                "text": "Message 1 UP",
                "author_user": {
                    '@id': "https://happy-dev.fr/users/{}/".format(user1.pk)
                }
            },
            {
                "@id": "https://happy-dev.fr/messages/{}/".format(message2.pk),
                "text": "Message 2 UP",
                "author_user": {
                    '@id': "https://happy-dev.fr/users/{}/".format(user1.pk)
                }
            },
            {
                "@id": "_:b1",
                "text": "Message 3 NEW",
                "author_user": {
                    '@id': "https://happy-dev.fr/users/{}/".format(user1.pk)
                }
            },
            {
                '@id': "https://happy-dev.fr/conversations/{}/".format(conversation.pk),
                "author_user": {
                    '@id': "https://happy-dev.fr/users/{}/".format(user1.pk)
                },
                'description': "Conversation 1 UP",
                'message_set': {
                    "@id": "https://happy-dev.fr/conversations/{}/message_set/".format(conversation.pk)
                }
            },
            {
                '@id': "https://happy-dev.fr/conversations/{}/message_set/".format(conversation.pk),
                "ldp:contains": [
                    {"@id": "https://happy-dev.fr/messages/{}/".format(message1.pk)},
                    {"@id": "https://happy-dev.fr/messages/{}/".format(message2.pk)},
                    {"@id": "_:b1"}
                ]
            }
        ]
        }

        meta_args = {'model': Conversation, 'depth': 2, 'fields': ("@id", "description", "message_set")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('ConversationSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=json, instance=conversation)
        serializer.is_valid()
        result = serializer.save()

        messages = result.message_set.all().order_by('text')

        self.assertEquals(result.description, "Conversation 1 UP")
        self.assertIs(result.message_set.count(), 3)
        self.assertEquals(messages[0].text, "Message 1 UP")
        self.assertEquals(messages[1].text, "Message 2 UP")
        self.assertEquals(messages[2].text, "Message 3 NEW")

    def test_put_resource(self):
        post = Post.objects.create(content="content")
        body = [{
            '@id': 'http://testserver.com/posts/{}/'.format(post.pk),
            'http://happy-dev.fr/owl/#content': "post content"}]
        response = self.client.put('/posts/{}/'.format(post.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['content'], "post content")
        self.assertIn('location', response._headers)



    def test_create_sub_object_in_existing_object_with_existing_reverse_1to1_relation(self):
        user = get_user_model().objects.create(username="alex", password="test")
        profile = UserProfile.objects.create(user=user, description="user description")
        body = [
            {
                '@id': "/userprofiles/{}/".format(profile.pk),
                'http://happy-dev.fr/owl/#description': "user update"
            },
            {
                '@id': '/users/{}/'.format(user.pk),
                "http://happy-dev.fr/owl/#first_name": "Alexandre",
                "http://happy-dev.fr/owl/#last_name": "Bourlier",
                "http://happy-dev.fr/owl/#username": "alex",
                'http://happy-dev.fr/owl/#userprofile': {'@id': "/userprofiles/{}/".format(profile.pk)}
            }
        ]
        response = self.client.put('/users/{}/'.format(user.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('userprofile', response.data)

    def test_create_sub_object_in_existing_object_with_reverse_fk_relation(self):
        """
        Doesn't work with depth = 0 on UserProfile Model. Should it be ?
        """
        user = get_user_model().objects.create(username="alex", password="test")
        body = [
            {
                '@id': "_:b975",
                'http://happy-dev.fr/owl/#description': "conversation description"
            },
            {
                '@id': '/users/{}/'.format(user.pk),
                "http://happy-dev.fr/owl/#first_name": "Alexandre",
                "http://happy-dev.fr/owl/#last_name": "Bourlier",
                "http://happy-dev.fr/owl/#username": "alex",
                'http://happy-dev.fr/owl/#conversation_set': {'@id': "_:b975"}
            }
        ]
        response = self.client.put('/users/{}/'.format(user.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversation_set', response.data)

    def test_create_sub_object_in_existing_object_with_existing_reverse_fk_relation(self):
        user = get_user_model().objects.create(username="alex", password="test")
        conversation = Conversation.objects.create(author_user=user, description="conversation description")
        body = [
            {
                '@id': "/conversations/{}/".format(conversation.pk),
                'http://happy-dev.fr/owl/#description': "conversation update"
            },
            {
                '@id': '/users/{}/'.format(user.pk),
                "http://happy-dev.fr/owl/#first_name": "Alexandre",
                "http://happy-dev.fr/owl/#last_name": "Bourlier",
                "http://happy-dev.fr/owl/#username": "alex",
                'http://happy-dev.fr/owl/#conversation_set': {'@id': "/conversations/{}/".format(conversation.pk)}
            }
        ]
        response = self.client.put('/users/{}/'.format(user.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversation_set', response.data)

    def test_missing_field_should_not_be_removed_with_fk_relation(self):
        peer = get_user_model().objects.create(username="sylvain", password="test2")
        conversation = Conversation.objects.create(author_user=self.user, peer_user=peer,
                                                   description="conversation description")
        body = [
            {
                '@id': "/conversations/{}/".format(conversation.pk),
                'http://happy-dev.fr/owl/#description': "conversation update",
            }
        ]
        response = self.client.put('/conversations/{}/'.format(conversation.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('peer_user', response.data)

    def test_empty_field_should_be_removed_with_fk_relation(self):
        peer = get_user_model().objects.create(username="sylvain", password="test2")
        conversation = Conversation.objects.create(author_user=self.user, peer_user=peer,
                                                   description="conversation description")
        body = [
            {
                '@id': "/conversations/{}/".format(conversation.pk),
                'http://happy-dev.fr/owl/#description': "conversation update",
                'http://happy-dev.fr/owl/#peer_user': ""
            }
        ]
        response = self.client.put('/conversations/{}/'.format(conversation.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['peer_user'], None)

    def test_m2m_new_link_bis(self):
        resource = Resource.objects.create()
        job = JobOffer.objects.create(title="first title", slug="job")
        body = {
            'http://happy-dev.fr/owl/#joboffers':
                {
                    '@id': "http://testserver.com/resources/{}/joboffers/".format(resource.pk),
                    'ldp:contains': [
                        {'@id': 'http://testserver.com/job-offers/{}/'.format(job.slug),
                         'http://happy-dev.fr/owl/#title': "new job",
                         },
                    ]
                }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://testserver.com/job-offers/{}/".format(job.slug))
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "new job")

    def test_m2m_new_link_embedded(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                'http://happy-dev.fr/owl/#slug': 'aaa',
                'http://happy-dev.fr/owl/#title': "new job",
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://happy-dev.fr/job-offers/aaa/")
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "new job")

    def test_m2m_existing_link(self):
        resource = Resource.objects.create()
        job = JobOffer.objects.create(title="first title", slug="job")
        resource.joboffers.add(job)
        resource.save()
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                # '@id': "http://testserver/resources/{}/joboffers/".format(resource.pk),
                'ldp:contains': [
                    {
                        '@id': 'http://testserver.com/job-offers/{}/'.format(job.slug),
                        'http://happy-dev.fr/owl/#title': "new job",
                    }
                ]
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://testserver.com/job-offers/{}/".format(job.slug))
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "new job")

    def test_m2m_new_link_federated(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                'http://happy-dev.fr/owl/#@id': 'http://external.job/job/1',
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://external.job/job/1")

    def test_m2m_new_link_external(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                '@id': 'http://testserver.com/job-offers/stuff/',
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://testserver.com/job-offers/stuff/")

    def test_m2m_new_link_local(self):
        resource = Resource.objects.create()
        job = JobOffer.objects.create(title="first title", slug="job")
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                '@id': 'http://happy-dev.fr/job-offers/{}/'.format(job.slug),
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://happy-dev.fr/job-offers/{}/".format(job.slug))
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "first title")

    def test_update_with_new_fk_relation(self):
        conversation = Conversation.objects.create(author_user=self.user,
                                                   description="conversation description")
        body = [
            {
                '@id': "/conversations/{}/".format(conversation.pk),
                'http://happy-dev.fr/owl/#description': "conversation update",
                'http://happy-dev.fr/owl/#peer_user': {
                    '@id': 'http://happy-dev.fr/users/{}'.format(self.user.pk),
                }
            }
        ]
        response = self.client.put('/conversations/{}/'.format(conversation.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('peer_user', response.data)

        conversation = Conversation.objects.get(pk=conversation.pk)
        self.assertIsNotNone(conversation.peer_user)

        user = get_user_model().objects.get(pk=self.user.pk)
        self.assertEqual(user.peers_conv.count(), 1)

    def test_m2m_user_link_federated(self):
        project = Project.objects.create(description="project name")
        body = {
            'http://happy-dev.fr/owl/#description': 'project name',
            'http://happy-dev.fr/owl/#team': {
                'http://happy-dev.fr/owl/#@id': 'http://external.user/user/1',
            }
        }

        response = self.client.put('/projects/{}/'.format(project.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['team']['ldp:contains'][0]['@id'],
                         "http://external.user/user/1")

    def test_m2m_user_link_existing_external(self):
        project = Project.objects.create(description="project name")
        ext_user = get_user_model().objects.create(username=str(uuid.uuid4()), urlid='http://external.user/user/1')
        body = {
            'http://happy-dev.fr/owl/#description': 'project name',
            'http://happy-dev.fr/owl/#team': {
                'http://happy-dev.fr/owl/#@id': ext_user.urlid,
            }
        }

        response = self.client.put('/projects/{}/'.format(project.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['team']['ldp:contains'][0]['@id'], ext_user.urlid)

        project = Project.objects.get(pk=project.pk)
        self.assertEqual(project.team.count(), 1)

        user = get_user_model().objects.get(pk=ext_user.pk)
        self.assertEqual(user.projects.count(), 1)

    def test_create_sub_object_in_existing_object_with_reverse_1to1_relation(self):
        """
        Doesn't work with depth = 0 on UserProfile Model. Should it be ?
        """
        user = get_user_model().objects.create(username="alex", password="test")
        body = [
            {
                '@id': "_:b975",
                'http://happy-dev.fr/owl/#description': "user description",
                'http://happy-dev.fr/owl/#dummy': {
                    '@id': './'
                }
            },
            {
                '@id': '/users/{}/'.format(user.pk),
                "http://happy-dev.fr/owl/#first_name": "Alexandre",
                "http://happy-dev.fr/owl/#last_name": "Bourlier",
                "http://happy-dev.fr/owl/#username": "alex",
                'http://happy-dev.fr/owl/#userprofile': {'@id': "_:b975"}
            }
        ]
        response = self.client.put('/users/{}/'.format(user.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('userprofile', response.data)
        self.assertIsNotNone(response.data['userprofile'])

    def test_m2m_user_link_remove_existing_link(self):
        ext_user = get_user_model().objects.create(username=str(uuid.uuid4()), urlid='http://external.user/user/1')
        project = Project.objects.create(description="project name")
        project.team.add(ext_user)
        project.save()
        body = {
            'http://happy-dev.fr/owl/#description': 'project name',
            'http://happy-dev.fr/owl/#team': {
            }
        }

        response = self.client.put('/projects/{}/'.format(project.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

        project = Project.objects.get(pk=project.pk)
        self.assertEqual(project.team.count(), 0)

        user = get_user_model().objects.get(pk=ext_user.pk)
        self.assertEqual(user.projects.count(), 0)

    def test_update_sub_object_with_urlid(self):
        user = get_user_model().objects.create(username="alex", password="test")
        profile = UserProfile.objects.create(user=user, description="user description")
        body = {
            '@id': '/users/{}/'.format(user.pk),
            "first_name": "Alexandre",
            "last_name": "Bourlier",
            "username": "alex",
            'userprofile': {
                '@id': "http://happy-dev.fr/userprofiles/{}/".format(profile.pk),
                'description': "user update"
            },
            '@context': {
                "@vocab": "http://happy-dev.fr/owl/#",
            }
        }

        response = self.client.put('/users/{}/'.format(user.pk), data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('userprofile', response.data)

        response = self.client.get('/userprofiles/{}/'.format(profile.pk),
                                   content_type='application/ld+json')
        self.assertEqual(response.data['description'], "user update")



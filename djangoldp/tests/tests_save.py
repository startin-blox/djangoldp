from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework.utils import json

from djangoldp.models import Model
from djangoldp.serializers import LDPSerializer
from djangoldp.tests.models import Skill, JobOffer, Invoice, LDPDummy, Resource, Post, Circle, Project


class Save(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                         password='glass onion')
        self.client.force_authenticate(self.user)

    def tearDown(self):
        pass

    def test_save_m2m_graph_with_many_nested(self):
        invoice = {
            "@graph": [
                {
                    "@id": "./",
                    "batches": {"@id": "_:b381"},
                    "title": "Nouvelle facture",
                    "date": ""
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

        meta_args = {'model': Invoice, 'depth': 2, 'fields': ("@id", "title", "batches", "date")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('InvoiceSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=invoice)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "Nouvelle facture")
        self.assertIs(result.batches.count(), 1)
        self.assertEquals(result.batches.all()[0].title, "Batch 1")
        self.assertIs(result.batches.all()[0].tasks.count(), 1)
        self.assertEquals(result.batches.all()[0].tasks.all()[0].title, "Tache 1")

    def test_save_m2m(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire", slug="slug1")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire", slug="slug2")

        job = {"title": "job test",
               "slug": "slug1",
               "skills": {
                   "ldp:contains": [
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill1.slug)},
                       {"@id": "https://happy-dev.fr/skills/{}/".format(skill2.slug), "title": "skill2 UP"},
                       {"title": "skill3", "obligatoire": "obligatoire", "slug": "slug3"},
                   ]}
               }

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills", "slug")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 3)
        self.assertEquals(result.skills.all()[0].title, "skill1")  # no change
        self.assertEquals(result.skills.all()[1].title, "skill2 UP")  # title updated
        self.assertEquals(result.skills.all()[2].title, "skill3")  # creation on the fly

    def test_save_m2m_graph_simple(self):
        job = {"@graph": [
            {"title": "job test", "slug": "slugjob",
             },
        ]}

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills", "slug")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 0)

    def test_save_m2m_graph_with_nested(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire", slug="a")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire", slug="b")

        job = {"@graph": [
            {"title": "job test",
             "slug": "slugj",
             "skills": {"@id": "_.123"}
             },
            {"@id": "_.123", "title": "skill3 NEW", "obligatoire": "obligatoire", "slug": "skill3"},
        ]}

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills", "slug")}

        meta_class = type('Meta', (), meta_args)
        serializer_class = type(LDPSerializer)('JobOfferSerializer', (LDPSerializer,), {'Meta': meta_class})
        serializer = serializer_class(data=job)
        serializer.is_valid()
        result = serializer.save()

        self.assertEquals(result.title, "job test")
        self.assertIs(result.skills.count(), 1)
        self.assertEquals(result.skills.all()[0].title, "skill3 NEW")  # creation on the fly

    def test_save_without_nested_fields(self):
        skill1 = Skill.objects.create(title="skill1", obligatoire="obligatoire", slug="a")
        skill2 = Skill.objects.create(title="skill2", obligatoire="obligatoire", slug="b")
        job = {"title": "job test", "slug": "c"}

        meta_args = {'model': JobOffer, 'depth': 2, 'fields': ("@id", "title", "skills", "slug")}

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

        meta_args = {'model': Skill, 'depth': 2, 'fields': ("@id", "title")}

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

    def test_save_fk_graph_with_nested(self):
        post = {
            '@graph': [
                {
                    'http://happy-dev.fr/owl/#title': "title",
                    'http://happy-dev.fr/owl/#invoice': {
                        '@id': "_.123"
                    }
                },
                {
                    '@id': "_.123",
                    'http://happy-dev.fr/owl/#title': "title 2"
                }
            ]
        }

        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('author', response.data)
        self.assertEquals(response.data['title'], "title")
        self.assertEquals(response.data['invoice']['title'], "title 2")

    def test_save_fk_graph_with_existing_nested(self):
        invoice = Invoice.objects.create(title="title 3")
        post = {
            '@graph': [
                {
                    'http://happy-dev.fr/owl/#title': "title",
                    'http://happy-dev.fr/owl/#invoice': {
                        '@id': "https://happy-dev.fr{}{}/".format(Model.container_id(invoice), invoice.id)
                    }
                }
            ]
        }

        response = self.client.post('/batchs/', data=json.dumps(post), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('author', response.data)
        self.assertEquals(response.data['title'], "title")
        self.assertEquals(response.data['invoice']['title'], "title 3")

    def test_post_should_accept_missing_field_id_nullable(self):
        body = [
            {
                '@id': "./",
                'http://happy-dev.fr/owl/#content': "post update",
            }
        ]
        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('peer_user', response.data)

    def test_post_should_accept_empty_field_if_nullable(self):
        body = [
            {
                '@id': "./",
                'http://happy-dev.fr/owl/#content': "post update",
                'http://happy-dev.fr/owl/#peer_user': ""
            }
        ]
        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['peer_user'], None)

    def test_save_sub_object_in_new_object_with_reverse_1to1_relation(self):
        dummy = LDPDummy.objects.create(some="foo")

        body = [
            {
                '@id': "_:b216",
                'http://happy-dev.fr/owl/#description': "user update",
                'http://happy-dev.fr/owl/#ddummy': {
                    "@id": "https://happy-dev.fr{}{}/".format(Model.container_id(dummy), dummy.id)
                }
            },
            {
                '@id': './',
                "http://happy-dev.fr/owl/#first_name": "Alexandre",
                "http://happy-dev.fr/owl/#last_name": "Bourlier",
                "http://happy-dev.fr/owl/#username": "alex",
                'http://happy-dev.fr/owl/#userprofile': {'@id': "_:b216"}
            }
        ]
        response = self.client.post('/users/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('userprofile', response.data)

    def test_embedded_context(self):
        body = {
            '@graph': [
                {
                    '@id': "./",
                    'content': "post update",
                    'peer_user': ""
                }
            ],
            '@context': {
                "@vocab": "http://happy-dev.fr/owl/#",
            }
        }
        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

    def test_nested_container(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#title': "new job",
            'http://happy-dev.fr/owl/#slug': "job1",
        }

        response = self.client.post('/resources/{}/joboffers/'.format(resource.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['resources']['ldp:contains'][0]['@id'],
                         "http://testserver/resources/{}/".format(resource.pk))
        self.assertEqual(response.data['title'], "new job")

    def test_nested_container_federated(self):
        resource = Resource.objects.create()
        body = {
            'http://happy-dev.fr/owl/#@id': "http://external.job/job/1",
        }

        response = self.client.post('/resources/{}/joboffers/'.format(resource.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['resources']['ldp:contains'][0]['@id'],
                         "http://testserver/resources/{}/".format(resource.pk))
        self.assertEqual(response.data['@id'], "http://external.job/job/1")

    def test_embedded_context_2(self):
        body = {
            '@id': "./",
            'content': "post update",
            'peer_user': "",
            '@context': {
                "@vocab": "http://happy-dev.fr/owl/#",
            }
        }

        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

    def test_auto_id(self):
        body = {
            '@id': "./",
            'content': "post update",
            'peer_user': "",
            '@context': {
                "@vocab": "http://happy-dev.fr/owl/#",
            }
        }

        response = self.client.post('/posts/', data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        saved_post = Post.objects.get(pk=1)
        self.assertEqual(saved_post.urlid, "http://happy-dev.fr/posts/1/")

    def test_nested_container_user_federated(self):
        project = Project.objects.create()
        body = {
            'http://happy-dev.fr/owl/#@id': "http://external.user/user/1/",
        }

        response = self.client.post('/projects/{}/team/'.format(project.pk),
                                    data=json.dumps(body),
                                    content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['projects']['ldp:contains'][0]['@id'],
                         "http://testserver/projects/{}/".format(project.pk))
        self.assertEqual(response.data['@id'], "http://external.user/user/1/")

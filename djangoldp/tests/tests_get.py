from datetime import datetime
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from djangoldp.tests.models import User, Post, Invoice, JobOffer, Skill, Batch, DateModel, Circle, UserProfile, Conversation, Message
from djangoldp.serializers import GLOBAL_SERIALIZER_CACHE

class TestGET(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.ordered_fields = ['@context', '@type', '@id']
        setattr(Circle._meta, 'depth', 0)
        setattr(Circle._meta, 'empty_containers', [])

    def tearDown(self):
        GLOBAL_SERIALIZER_CACHE.reset()

    def test_get_resource(self):
        post = Post.objects.create(content="content")
        response = self.client.get('/posts/{}/'.format(post.pk), content_type='application/ld+json', HTTP_ORIGIN='http://localhost:8080/test/')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['content'], "content")
        self.assertIn('author', response.data)
        self.assertIn('@type', response.data)

        # test headers returned
        self.assertEqual(response['Content-Type'], 'application/ld+json') 
        self.assertEqual(response['Accept-Post'], 'application/ld+json')
        self.assertEqual(response['Allow'], 'GET, PUT, PATCH, DELETE, HEAD, OPTIONS')
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:8080/test/')
        self.assertIn('DPoP', response['Access-Control-Allow-Headers'])

    def test_get_resource_urlid(self):
        user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                    password='glass onion')
        UserProfile.objects.create(user=user)
        post = Post.objects.create(content="content", author=user)
        response = self.client.get('/posts/{}/'.format(post.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['content'], "content")
        self.assertEqual(response.data['author']['@id'], user.urlid)

    def test_get_container(self):
        Post.objects.create(content="content")
        # federated object - should not be returned in the container view
        Post.objects.create(content="federated", urlid="https://external.com/posts/1/")
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(1, len(response.data['ldp:contains']))
        self.assertIn('@type', response.data)
        self.assertIn('@type', response.data['ldp:contains'][0])
        self.assertNotIn('permissions', response.data['ldp:contains'][0])

        Invoice.objects.create(title="content")
        response = self.client.get('/invoices/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('permissions', response.data)
        self.assertEquals(1, len(response.data['permissions']))  # read only

    def test_get_empty_container(self):
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(0, len(response.data['ldp:contains']))

    def test_get_filtered_fields(self):
        skill = Skill.objects.create(title="Java", obligatoire="ok", slug="1")
        skill2 = Skill.objects.create(title="Java", obligatoire="ok", slug="2")
        skill3 = Skill.objects.create(urlid="http://happy-dev.hubl.fr/skills/1")
        job = JobOffer.objects.create(title="job", slug="1")
        job.skills.add(skill)
        job.skills.add(skill2)
        job.skills.add(skill3)
        job.save()
        response = self.client.get('/job-offers/{}/'.format(job.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_skills', response.data)
        self.assertEqual(response.data['recent_skills']['@id'], "http://happy-dev.fr/job-offers/1/recent_skills/")
        # the external resource should be serialized with its @id and @type.. and only these fields
        self.assertEqual(response.data['skills']['ldp:contains'][2]['@id'], "http://happy-dev.hubl.fr/skills/1")
        self.assertIn('@type', response.data['skills']['ldp:contains'][1])
        self.assertIn('@type', response.data['skills']['ldp:contains'][2])
        self.assertEqual(len(response.data['skills']['ldp:contains'][2].items()), 2)

    def test_get_reverse_filtered_fields(self):
        skill = Skill.objects.create(title="Java", obligatoire="ok", slug="1")
        job = JobOffer.objects.create(title="job", slug="1")
        job.skills.add(skill)
        job.save()
        response = self.client.get('/skills/{}/'.format(skill.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_jobs', response.data)
        self.assertEqual(response.data['recent_jobs']['@id'], "http://happy-dev.fr/skills/1/recent_jobs/")

    def test_get_virtual_field(self):
        skill = Skill.objects.create(title="Java", obligatoire="ok", slug="1")
        skill2 = Skill.objects.create(title="Java", obligatoire="ok", slug="2")
        job = JobOffer.objects.create(title="job", slug="1")
        job.skills.add(skill)
        job.skills.add(skill2)
        job.save()
        response = self.client.get('/job-offers/{}/'.format(job.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('some_skill', response.data)
        self.assertEqual(response.data['some_skill']['@id'], skill.urlid)
        response = self.client.get('/job-offers/{}/recent_skills/'.format(job.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ldp:contains']), 2)

    def test_get_nested(self):
        invoice = Invoice.objects.create(title="invoice")
        batch = Batch.objects.create(invoice=invoice, title="batch")
        distant_batch = Batch.objects.create(invoice=invoice, title="distant", urlid="https://external.com/batch/1/")
        response = self.client.get('/invoices/{}/batches/'.format(invoice.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['@id'], 'http://happy-dev.fr/invoices/{}/batches/'.format(invoice.pk))
        self.assertIn('permissions', response.data)
        self.assertEquals(len(response.data['ldp:contains']), 2)
        self.assertIn('@type', response.data['ldp:contains'][0])
        self.assertIn('@type', response.data['ldp:contains'][1])
        self.assertNotIn('permissions', response.data['ldp:contains'][0])
        self.assertNotIn('permissions', response.data['ldp:contains'][1])
        self.assertEquals(response.data['ldp:contains'][0]['invoice']['@id'], invoice.urlid)
        self.assertEqual(response.data['ldp:contains'][1]['@id'], distant_batch.urlid)

    def test_get_nested_without_related_name(self):
        user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')
        conversation = Conversation.objects.create(author_user=user)
        message = Message.objects.create(conversation=conversation, author_user=user)
        response = self.client.get('/conversations/{}/message_set/'.format(conversation.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['@id'], 'http://happy-dev.fr/conversations/{}/message_set/'.format(conversation.pk))
        self.assertEquals(len(response.data['ldp:contains']), 1)

    # TODO: https://git.startinblox.com/djangoldp-packages/djangoldp/issues/335
    #  test getting a route with multiple nested fields (/job-offers/X/skills/Y/)
    '''def test_get_twice_nested(self):
        job = JobOffer.objects.create(title="job", slug="slug1")
        skill = Skill.objects.create(title='old', obligatoire='old', slug='skill1')
        job.skills.add(skill)
        self.assertEqual(job.skills.count(), 1)
        
        response = self.client.get('/job-offers/{}/skills/{}/'.format(job.slug, skill.slug))
        self.assertEqual(response.status_code, 200)'''

    def test_serializer_excludes(self):
        date = DateModel.objects.create(excluded='test', value=datetime.now())
        response = self.client.get('/datemodels/{}/'.format(date.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('excluded', response.data.keys())

    def test_serializer_excludes_serializer_fields_set_also(self):
        setattr(DateModel._meta, 'serializer_fields', ['value', 'excluded'])
        date = DateModel.objects.create(excluded='test', value=datetime.now())
        response = self.client.get('/datemodels/{}/'.format(date.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('excluded', response.data.keys())

    def _set_up_circle_and_user(self):
        user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                    password='glass onion')
        circle = Circle.objects.create(name='test', description='test', owner=user)
        self.client.force_authenticate(user)
        circle.members.user_set.add(user)
        return user

    # tests for functionality allowing me to set containers to be serialized without content\
    # test for normal functioning (without setting)
    def test_empty_container_serialization_nested_serializer_no_empty(self):
        setattr(Circle._meta, 'depth', 1)
        self._set_up_circle_and_user()

        response = self.client.get('/circles/', content_type='application/ld+json')
        self.assertEqual(response.data['@type'], 'ldp:Container')
        self.assertIn('@id', response.data)
        self.assertIn('permissions', response.data)
        self.assertIn('members', response.data['ldp:contains'][0])
        self.assertEqual(response.data['ldp:contains'][0]['members']['@type'], 'foaf:Group')
        self.assertIn('@id', response.data['ldp:contains'][0]['members'])
        self.assertEqual(len(response.data['ldp:contains'][0]['members']['user_set']), 1)

    # test for functioning with setting
    def test_empty_container_serialization_nested_serializer_empty(self):
        setattr(User._meta, 'depth', 1)
        setattr(User._meta, 'empty_containers', ['owned_circles'])
        self._set_up_circle_and_user()

        response = self.client.get('/users/', content_type='application/ld+json')
        self.assertEqual(response.data['@type'], 'ldp:Container')
        self.assertIn('owned_circles', response.data['ldp:contains'][0])
        self.assertIn('@id', response.data['ldp:contains'][0]['owned_circles'])
        self.assertNotIn('permissions', response.data['ldp:contains'][0]['owned_circles'])
        self.assertNotIn('ldp:contains', response.data['ldp:contains'][0]['owned_circles'])

    # should serialize as normal on the nested viewset (directly asking for the container)
    # test for normal functioning (without setting)
    def test_empty_container_serialization_nested_viewset_no_empty(self):
        user = self._set_up_circle_and_user()

        response = self.client.get(f'/users/{user.pk}/owned_circles/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['@type'], 'ldp:Container')
        self.assertIn('@id', response.data)
        self.assertIn('ldp:contains', response.data)
        self.assertIn('permissions', response.data)
        self.assertIn('owner', response.data['ldp:contains'][0])

    # test for functioning with setting
    def test_empty_container_serialization_nested_viewset_empty(self):
        setattr(User._meta, 'empty_containers', ['owned_circles'])
        user = self._set_up_circle_and_user()

        response = self.client.get(f'/users/{user.pk}/owned_circles/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['@type'], 'ldp:Container')
        self.assertIn('@id', response.data)
        self.assertIn('ldp:contains', response.data)
        self.assertIn('permissions', response.data)
        self.assertIn('owner', response.data['ldp:contains'][0])

    # # test for checking fields ordering
    # def test_ordered_field(self):
    #     self._set_up_circle_and_user()
    #     response = self.client.get('/users/', content_type='application/ld+json')
    #     fields_to_test = [
    #         response.data.keys(),
    #         response.data['ldp:contains'][-1],
    #         response.data['ldp:contains'][-1]['circle_set']
    #     ]

    #     for test_fields in fields_to_test:
    #         test_fields = list(test_fields)
    #         o_f = [field for field in self.ordered_fields if field in test_fields]
    #         self.assertEquals(o_f, test_fields[:len(o_f)])

import json

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from djangoldp.tests.models import Post, Task, Invoice, JobOffer, Skill


class TestGET(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()

    def tearDown(self):
        pass

    def test_get_resource(self):
        post = Post.objects.create(content="content")
        response = self.client.get('/posts/{}/'.format(post.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['content'], "content")
        self.assertIn('author', response.data)

    def test_get_container(self):
        Post.objects.create(content="content")
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('permissions', response.data)
        self.assertEquals(2, len(response.data['permissions'])) # read and add

        Invoice.objects.create(title="content")
        response = self.client.get('/invoices/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('permissions', response.data)
        self.assertEquals(1, len(response.data['permissions'])) # read only

    def test_get_empty_container(self):
        Post.objects.all().delete()
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)

    def test_get_filtered_fields(self):
        skill = Skill.objects.create(title="Java", obligatoire="ok", slug="1")
        skill2 = Skill.objects.create(title="Java", obligatoire="ok", slug="2")
        job = JobOffer.objects.create(title="job", slug="1")
        job.skills.add(skill)
        job.skills.add(skill2)
        job.save()
        response = self.client.get('/job-offers/{}/'.format(job.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_skills', response.data)

    def test_get_reverse_filtered_fields(self):
        skill = Skill.objects.create(title="Java", obligatoire="ok", slug="1")
        job = JobOffer.objects.create(title="job", slug="1")
        job.skills.add(skill)
        job.save()
        response = self.client.get('/skills/{}/'.format(skill.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_jobs', response.data)

from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from djangoldp.tests.models import Post, Invoice, JobOffer, Skill, Batch


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
        # federated object - should not be returned in the container view
        Post.objects.create(content="federated", urlid="https://external.com/posts/1/")
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('permissions', response.data)
        self.assertEquals(1, len(response.data['ldp:contains']))
        self.assertEquals(2, len(response.data['permissions']))  # read and add

        Invoice.objects.create(title="content")
        response = self.client.get('/invoices/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('permissions', response.data)
        self.assertEquals(1, len(response.data['permissions']))  # read only

    def test_get_empty_container(self):
        Post.objects.all().delete()
        response = self.client.get('/posts/', content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(0, len(response.data['ldp:contains']))

    def test_get_filtered_fields(self):
        skill = Skill.objects.create(title="Java", obligatoire="ok", slug="1")
        skill2 = Skill.objects.create(title="Java", obligatoire="ok", slug="2")
        skill3 = Skill.objects.create(urlid="http://external/skills/1")
        job = JobOffer.objects.create(title="job", slug="1")
        job.skills.add(skill)
        job.skills.add(skill2)
        job.skills.add(skill3)
        job.save()
        response = self.client.get('/job-offers/{}/'.format(job.slug), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('recent_skills', response.data)
        self.assertEqual(response.data['recent_skills']['@id'], "http://happy-dev.fr/job-offers/1/recent_skills/")
        self.assertEqual(response.data['skills']['ldp:contains'][2]['@id'], "http://external/skills/1")

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
        self.assertEqual(response.data['some_skill']['@id'], "http://testserver/skills/1/")

    def test_get_nested(self):
        invoice = Invoice.objects.create(title="invoice")
        batch = Batch.objects.create(invoice=invoice, title="batch")
        distant_batch = Batch.objects.create(invoice=invoice, title="distant", urlid="https://external.com/batch/1/")
        response = self.client.get('/invoices/{}/batches/'.format(invoice.pk), content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.data['@id'], 'http://happy-dev.fr/invoices/{}/batches/'.format(invoice.pk))
        self.assertEquals(len(response.data['ldp:contains']), 2)

import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient

from djangoldp.tests.models import Resource, JobOffer


class TestTemp(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user(username='john', email='jlennon@beatles.com', password='glass onion')

    def tearDown(self):
        pass

    # def test_m2m_existing_link(self):
    #     resource = Resource.objects.create()
    #     job = JobOffer.objects.create(title="first title", slug="job")
    #     resource.joboffers.add(job)
    #     resource.save()
    #     body = {
    #         'http://happy-dev.fr/owl/#joboffers': {
    #             '@id': '/job-offers/{}'.format(job.slug),
    #             'http://happy-dev.fr/owl/#title': "new job",
    #         }
    #     }
    #
    #     response = self.client.put('/resources/{}/'.format(resource.pk),
    #                                data=json.dumps(body),
    #                                content_type='application/ld+json')
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
    #                      "http://testserver/job-offers/aaa/")
    #     self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "new job")

    def test_m2m_new_link(self):
        resource = Resource.objects.create()
        job = JobOffer.objects.create(title="first title", slug="job")
        body = {
            'http://happy-dev.fr/owl/#joboffers': {
                '@id': 'http://testserver/job-offers/{}/'.format(job.slug),
            }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://testserver/job-offers/{}/".format(job.slug))
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "job")

    def test_m2m_new_link_bis(self):
        resource = Resource.objects.create()
        job = JobOffer.objects.create(title="first title", slug="job")
        body = {
            'http://happy-dev.fr/owl/#joboffers':
                {
                    '@id': "http://testserver/resources/{}/joboffers/".format(resource.pk),
                    "ldp:contains": [
                        {'@id': 'http://testserver/job-offers/{}/'.format(job.slug)},
                    ]
                }
        }

        response = self.client.put('/resources/{}/'.format(resource.pk),
                                   data=json.dumps(body),
                                   content_type='application/ld+json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['@id'],
                         "http://testserver/job-offers/{}/".format(job.slug))
        self.assertEqual(response.data['joboffers']['ldp:contains'][0]['title'], "job")

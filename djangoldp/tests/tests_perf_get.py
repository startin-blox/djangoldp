import datetime
import platform

import time
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, APIClient, APITestCase
from statistics import mean, variance

from djangoldp.tests.models import Post, Invoice, JobOffer, Skill, Batch, DateModel


class TestPerformanceGET(APITestCase):
    posts = []
    skills = []
    jobs = []
    test_volume = 200
    result_line = []
    withAuth = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("Init", end='', flush=True)

        step = cls.test_volume / 10
        cls.factory = APIRequestFactory()
        cls.client = APIClient()
        if cls.withAuth:
            for i in range(cls.test_volume):
                user = get_user_model().objects.create_user(username='john{}'.format(i), email='jlennon{}@beatles.com'.format(i),
                                                         password='glass onion')
            cls.client.force_authenticate(user=user)

        for i in range(cls.test_volume):
            cls.posts.append(Post.objects.create(content="content"))

        for i in range(cls.test_volume):
            cls.skills.append(Skill.objects.create(title="Java", obligatoire="ok", slug=str(i)))

        for i in range(cls.test_volume):
            job = JobOffer.objects.create(title="job", slug=str(i))
            for skill in cls.skills:
                job.skills.add(skill)
            if i % step == 0:
                print(".", end='', flush=True)
            job.save()
            cls.jobs.append(job)

        cls.result_line.append(platform.node())
        cls.result_line.append(datetime.datetime.today().strftime("%b %d %Y %H:%M:%S"))
        cls.result_line.append(cls.withAuth)
        cls.result_line.append(cls.test_volume)
        cls.result_line.append("N/A")
        cls.result_line.append("N/A")
        cls.result_line.append("N/A")
        cls.result_line.append("N/A")
        cls.result_line.append("N/A")

    @classmethod
    def tearDownClass(cls):
        import csv
        with open('perf_result.csv', 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',',
                                    quotechar='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(cls.result_line)

    def test_get_resource(self):
        times = []

        for post in self.posts:
            start_time = time.time()
            response = self.client.get('/posts/{}/'.format(post.pk), content_type='application/ld+json')
            end_time = time.time()
            times.append(end_time - start_time)

        self.result_line[4] = str(mean(times))
        print("Variance execution time :" + str(variance(times)))

    def test_get_container(self):
        times = []

        for post in self.posts:
            start_time = time.time()
            response = self.client.get('/posts/', content_type='application/ld+json')
            end_time = time.time()
            times.append(end_time - start_time)

        self.result_line[5] = str(mean(times))
        print("Variance execution time :" + str(variance(times)))

    def test_get_filtered_fields(self):
        times = []

        for job in self.jobs:
            start_time = time.time()
            response = self.client.get('/job-offers/{}/'.format(job.slug), content_type='application/ld+json')
            end_time = time.time()
            times.append(end_time - start_time)

        self.result_line[6] = str(mean(times))

        print("Variance execution time :" + str(variance(times)))

    def test_get_reverse_filtered_fields(self):
        times = []

        for skill in self.skills:
            start_time = time.time()
            response = self.client.get('/skills/{}/'.format(skill.slug), content_type='application/ld+json')
            end_time = time.time()
            times.append(end_time - start_time)

        self.result_line[7] = str(mean(times))
        print("Variance execution time :" + str(variance(times)))

    def test_get_nested(self):
        times = []

        for job in self.jobs:
            start_time = time.time()
            response = self.client.get('/jobs/{}/skills'.format(job.slug), content_type='application/ld+json')
            end_time = time.time()
            times.append(end_time - start_time)

        self.result_line[8] = str(mean(times))
        print("Variance execution time :" + str(variance(times)))


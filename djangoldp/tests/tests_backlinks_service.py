import json
import uuid
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from djangoldp.tests.models import Circle, CircleMember, Project, UserProfile, DateModel, DateChild
from djangoldp.models import Activity, Follower


class TestsBacklinksService(APITestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.local_user = get_user_model().objects.create_user(username='john', email='jlennon@beatles.com',
                                                               password='glass onion')

    def _get_random_external_user(self):
        '''Auxiliary function creates a user with random external urlid and returns it'''
        username = str(uuid.uuid4())
        email = username + '@test.com'
        urlid = 'https://distant.com/users/' + username
        return get_user_model().objects.create_user(username=username, email=email, password='test', urlid=urlid)

    @override_settings(SEND_BACKLINKS=True, DISABLE_OUTBOX=True)
    def test_local_object_with_distant_foreign_key(self):
        # a local Circle with a distant owner
        local_circle = Circle.objects.create(description='Test')
        external_user = self._get_random_external_user()
        local_circle.owner = external_user
        local_circle.save()

        # assert that a activity was sent
        self.assertEqual(Activity.objects.all().count(), 1)

        # reset to a local user, another (update) activity should be sent
        local_circle.owner = self.local_user
        local_circle.save()
        self.assertEqual(Activity.objects.all().count(), 2)

        # external user should no longer be following the object. A further update should not send an activity
        # TODO: https://git.startinblox.com/djangoldp-packages/djangoldp/issues/257
        '''another_user = get_user_model().objects.create_user(username='test', email='test@test.com',
                                                            password='glass onion')
        local_circle.owner = another_user
        local_circle.save()
        self.assertEqual(Activity.objects.all().count(), 2)'''

        # re-add the external user as owner
        local_circle.owner = external_user
        local_circle.save()

        # delete parent
        local_circle.delete()
        self.assertEqual(Activity.objects.all().count(), 4)

    @override_settings(SEND_BACKLINKS=True, DISABLE_OUTBOX=True)
    def test_local_object_with_external_m2m_join_leave(self):
        # a local project with three distant users
        project = Project.objects.create(description='Test')
        external_a = self._get_random_external_user()
        external_b = self._get_random_external_user()
        external_c = self._get_random_external_user()
        project.team.add(external_a)
        project.team.add(external_b)
        project.team.add(external_c)
        self.assertEqual(Activity.objects.all().count(), 3)

        # remove one individual
        project.team.remove(external_a)
        self.assertEqual(Activity.objects.all().count(), 4)

        # clear the rest
        project.team.clear()
        self.assertEqual(Activity.objects.all().count(), 6)
        prior_count = Activity.objects.all().count()

        # once removed I should not be following the object anymore
        project.delete()
        self.assertEqual(Activity.objects.all().count(), prior_count)

    @override_settings(SEND_BACKLINKS=True, DISABLE_OUTBOX=True)
    def test_local_object_with_external_m2m_delete_parent(self):
        # a local project with three distant users
        project = Project.objects.create(description='Test')
        external_a = self._get_random_external_user()
        project.team.add(external_a)
        prior_count = Activity.objects.all().count()

        project.delete()
        self.assertEqual(Activity.objects.all().count(), prior_count + 1)

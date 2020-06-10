import json
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from djangoldp.tests.models import Circle, CircleMember, Project, UserProfile
from djangoldp.models import Activity, Follower


class TestsInbox(APITestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    #
    #   CREATE ACTIVITY
    #
    def test_create_activity_circle(self):
        # a local user has been set as the owner of a distant circle
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        payload = {
          "@context": [
              "https://www.w3.org/ns/activitystreams",
              {"hd": "http://happy-dev.fr/owl/#"}
          ],
          "summary": "A circle was created",
          "type": "Create",
          "actor": {
            "type": "Service",
            "name": "Backlinks Service"
          },
          "object": {
            "@type": "hd:circle",
            "@id": "https://distant.com/circles/1/",
            "owner": {
                "@type": "foaf:user",
                "@id": user.urlid
            }
          }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

        # assert that the circle was created and the user associated as owner
        circles = Circle.objects.all()
        activities = Activity.objects.all()
        self.assertEquals(len(circles), 1)
        self.assertEquals(len(activities), 1)
        self.assertIn("https://distant.com/circles/1/", circles.values_list('urlid', flat=True))
        self.assertEqual(circles[0].owner, user)
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    #
    #   ADD ACTIVITIES
    #
    # project model has a direct many-to-many with User
    def test_add_activity_project(self):
        # a local user has joined a distant project
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": user.get_full_name() + " was added to Test Project",
            "type": "Add",
            "actor": {
              "type": "Service",
              "name": "Backlinks Service"
            },
            "object": {
                "@type": "hd:project",
                "@id": "https://distant.com/projects/1/"
            },
            "target": {
                "@type": "foaf:user",
                "name": user.get_full_name(),
                "@id": user.urlid
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

        # assert that the project backlink(s) & activity were created
        projects = Project.objects.all()
        user_projects = user.projects.all()
        activities = Activity.objects.all()
        self.assertEquals(len(projects), 1)
        self.assertEquals(len(user_projects), 1)
        self.assertEquals(len(activities), 1)
        self.assertIn("https://distant.com/projects/1/", projects.values_list('urlid', flat=True))
        self.assertIn("https://distant.com/projects/1/", user_projects.values_list('urlid', flat=True))
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    # circle model has a many-to-many with user, through an intermediate model
    def test_add_activity_circle(self):
        # a local user has joined a distant circle
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": user.get_full_name() + " was added to Test Circle",
            "type": "Add",
            "actor": {
              "type": "Service",
              "name": "Backlinks Service"
            },
            "object": {
                "@type": "hd:circlemember",
                "@id": "https://distant.com/circle-members/1/",
                "user": {
                  "@type": "foaf:user",
                  "@id": user.urlid
                },
                "circle": {
                    "@type": "hd:circle",
                    "@id": "https://distant.com/circles/1/"
                }
            },
            "target": {
                "@type": "foaf:user",
                "name": user.get_full_name(),
                "@id": user.urlid
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload), content_type='application/ld+json;profile="https://www.w3.org/ns/activitystreams"')
        self.assertEqual(response.status_code, 201)

        # assert that the circle backlink(s) & activity were created
        circles = Circle.objects.all()
        user_circles = user.circles.all()
        activities = Activity.objects.all()
        self.assertEquals(len(circles), 1)
        self.assertEquals(len(user_circles), 1)
        self.assertEquals(len(activities), 1)
        self.assertIn("https://distant.com/circles/1/", circles.values_list('urlid', flat=True))
        self.assertIn("https://distant.com/circle-members/1/", user_circles.values_list('urlid', flat=True))
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    # test sending an add activity when the backlink already exists
    def test_add_activity_object_already_added(self):
        # a local user has joined a distant circle
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        # ..but the receiver already knows about it
        circle = Circle.objects.create(urlid="https://distant.com/circles/1/")
        CircleMember.objects.create(urlid="https://distant.com/circle-members/1/", circle=circle, user=user)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": user.get_full_name() + " was added to Test Circle",
            "type": "Add",
            "actor": {
                "type": "Service",
                "name": "Backlinks Service"
            },
            "object": {
                "@type": "hd:circlemember",
                "@id": "https://distant.com/circle-members/1/",
                "user": {
                    "@type": "foaf:user",
                    "@id": user.urlid
                },
                "circle": {
                    "@type": "hd:circle",
                    "@id": "https://distant.com/circles/1/"
                }
            },
            "target": {
                "@type": "foaf:user",
                "name": user.get_full_name(),
                "@id": user.urlid
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload),
                                    content_type='application/ld+json;profile="https://www.w3.org/ns/activitystreams"')
        self.assertEqual(response.status_code, 201)

        # assert that the circle backlink(s) & activity were created
        circles = Circle.objects.all()
        user_circles = user.circles.all()
        activities = Activity.objects.all()
        self.assertEquals(len(circles), 1)
        self.assertEquals(len(user_circles), 1)
        self.assertEquals(len(activities), 1)
        self.assertIn("https://distant.com/circles/1/", circles.values_list('urlid', flat=True))
        self.assertIn("https://distant.com/circle-members/1/", user_circles.values_list('urlid', flat=True))
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    # TODO: adding to a model which has multiple relationships with this RDF type

    # error behaviour - unknown model
    def test_add_activity_unknown(self):
        # a local user has joined a distant circle
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": user.get_full_name() + " was added to Test Circle",
            "type": "Add",
            "actor": {
              "type": "Service",
              "name": "Backlinks Service"
            },
            "object": {
                "@type": "hd:somethingunknown",
                "@id": "https://distant.com/somethingunknown/1/"
            },
            "target": {
                "@type": "foaf:user",
                "name": user.get_full_name(),
                "@id": user.urlid
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload), content_type='application/ld+json;profile="https://www.w3.org/ns/activitystreams"')
        self.assertEqual(response.status_code, 404)

    #
    #   REMOVE & DELETE ACTIVITIES
    #
    # project model has a direct many-to-many with User
    def test_remove_activity_project_using_origin(self):
        # a local user has a distant project attached
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)
        project = Project.objects.create(urlid="https://distant.com/projects/1/")
        user.projects.add(project)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": user.get_full_name() + " removed Test Project",
            "type": "Remove",
            "actor": {
              "type": "Service",
              "name": "Backlinks Service"
            },
            "object": {
                "@type": "hd:project",
                "@id": "https://distant.com/projects/1/"
            },
            "origin": {
                "@type": "foaf:user",
                "name": user.get_full_name(),
                "@id": user.urlid
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload),
                                    content_type='application/ld+json;profile="https://www.w3.org/ns/activitystreams"')
        self.assertEqual(response.status_code, 201)

        # assert that the circle backlink(s) were removed & activity were created
        projects = Project.objects.all()
        user_projects = user.projects.all()
        activities = Activity.objects.all()
        self.assertEquals(len(projects), 1)
        self.assertEquals(len(user_projects), 0)
        self.assertEquals(len(activities), 1)
        self.assertIn("https://distant.com/projects/1/", projects.values_list('urlid', flat=True))
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    # TODO: test_remove_activity_project_using_target
    # TODO: error behaviour - project does not exist on user

    # Delete CircleMember
    def test_delete_activity_circle_using_origin(self):
        # a local user has a distant circle attached
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)
        circle = Circle.objects.create(urlid="https://distant.com/circles/1/", allow_create_backlink=False)
        CircleMember.objects.create(urlid="https://distant.com/circle-members/1/",circle=circle, user=user)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": "CircleMember was deleted",
            "type": "Delete",
            "actor": {
              "type": "Service",
              "name": "Backlinks Service"
            },
            "object": {
                "@type": "hd:circlemember",
                "@id": "https://distant.com/circle-members/1/",
                "user": {
                    "@type": "foaf:user",
                    "@id": user.urlid
                },
                "circle": {
                    "@type": "hd:circle",
                    "@id": "https://distant.com/circles/1/"
                }
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload),
                                    content_type='application/ld+json;profile="https://www.w3.org/ns/activitystreams"')
        self.assertEqual(response.status_code, 201)

        # assert that the CircleMember was deleted and activity was created
        circles = Circle.objects.all()
        user_circles = user.circles.all()
        activities = Activity.objects.all()
        self.assertEquals(len(circles), 1)
        self.assertEquals(len(user_circles), 0)
        self.assertEquals(len(activities), 1)
        self.assertIn("https://distant.com/circles/1/", circles.values_list('urlid', flat=True))
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    # TODO: test_delete_activity_circle_using_target

    #
    #   UPDATE Activities
    #
    def test_update_activity_circle(self):
        # a local user was set as the owner of a distant circle, but the owner has been changed
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        circle = Circle.objects.create(urlid="https://distant.com/circles/1/", owner=user)
        self.assertEqual(circle.owner, user)

        payload = {
          "@context": [
              "https://www.w3.org/ns/activitystreams",
              {"hd": "http://happy-dev.fr/owl/#"}
          ],
          "summary": "A circle was updated",
          "type": "Update",
          "actor": {
            "type": "Service",
            "name": "Backlinks Service"
          },
          "object": {
            "@type": "hd:circle",
            "@id": "https://distant.com/circles/1/",
            "owner": {
                "@type": "foaf:user",
                "@id": "https://distant.com/users/1/"
            }
          }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

        # assert that the circle was created and the user associated as owner
        circles = Circle.objects.all()
        activities = Activity.objects.all()
        users = get_user_model().objects.all()
        self.assertEquals(len(circles), 1)
        self.assertEquals(len(activities), 1)
        self.assertEquals(len(users), 2)
        distant_user = get_user_model().objects.get(urlid="https://distant.com/users/1/")
        self.assertIn("https://distant.com/circles/1/", circles.values_list('urlid', flat=True))
        self.assertEqual(circles[0].owner, distant_user)
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))

    #
    #   FOLLOW activities
    #
    def test_follow_activity(self):
        # a local user was set as the owner of a distant circle, but the owner has been changed
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        circle = Circle.objects.create(description='Test Description')

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {"hd": "http://happy-dev.fr/owl/#"}
            ],
            "summary": user.urlid + " followed " + circle.urlid,
            "type": "Follow",
            "actor": {
                "type": "Service",
                "name": "Backlinks Service",
                "inbox": "http://127.0.0.1:8000/inbox/"
            },
            "object": {
                "@type": "hd:circle",
                "@id": circle.urlid
            }
        }

        response = self.client.post('/inbox/',
                                    data=json.dumps(payload), content_type='application/ld+json')
        self.assertEqual(response.status_code, 201)

        # assert that Follower was created with correct values
        followers = Follower.objects.all()
        activities = Activity.objects.all()
        self.assertEquals(len(followers), 1)
        self.assertEquals(len(activities), 1)
        self.assertIn(response["Location"], activities.values_list('urlid', flat=True))
        follower = followers[0]
        self.assertEqual("http://127.0.0.1:8000/inbox/", follower.inbox)
        self.assertEqual(circle.urlid, follower.object)

    # test Followers are auto-deleted when the object they're following is deleted
    def test_follower_auto_delete(self):
        user = get_user_model().objects.create(username='john', email='jlennon@beatles.com', password='glass onion')
        UserProfile.objects.create(user=user)

        circle = Circle.objects.create(description='Test Description')
        Follower.objects.create(object=circle.urlid, inbox="http://127.0.0.1:8000/inbox/")
        followers = Follower.objects.all()
        self.assertEquals(len(followers), 1)
        circle.delete()
        followers = Follower.objects.all()
        self.assertEquals(len(followers), 0)

    #
    #   GET Inbox
    #
    def test_get_inbox(self):
        response = self.client.get('/inbox/')
        self.assertEqual(response.status_code, 405)

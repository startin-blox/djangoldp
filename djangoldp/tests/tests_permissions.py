import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from guardian.models import GroupObjectPermission
from rest_framework.test import APIRequestFactory, APIClient, APITestCase
from djangoldp.tests.models import AnonymousReadOnlyPost, AuthenticatedOnlyPost, ReadOnlyPost, DoubleInheritModel, \
    ReadAndCreatePost, OwnedResource, RestrictedCircle, RestrictedResource, ANDPermissionsDummy, ORPermissionsDummy

class TestPermissions(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()

    def authenticate(self):
        self.user = get_user_model().objects.create_user(username='random', email='random@user.com', password='Imrandom')
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_authenticate(user=self.user)

    def check_can_add(self, url, status_code=201, field='content', extra_content={}):
        data = extra_content
        extra_content[f"https://cdn.startinblox.com/owl#{field}"] = "new post"
        response = self.client.post(url, data=json.dumps(data), content_type='application/ld+json')
        self.assertEqual(response.status_code, status_code)
        if status_code == 201:
            self.assertIn('@id', response.data)
            return response.data['@id']
    
    def check_can_change(self, id, status_code=200, field='content'):
        data = { f"https://cdn.startinblox.com/owl#{field}": "changed post" }
        response = self.client.put(id, data=json.dumps(data), content_type='application/ld+json')
        self.assertEqual(response.status_code, status_code)
        if status_code == 200:
            self.assertIn('@id', response.data)
            self.assertEqual(response.data['@id'], id)
        
    def check_can_view_one(self, id, status_code=200):
        response = self.client.get(id, content_type='application/ld+json')
        self.assertEqual(response.status_code, status_code)
        if status_code == 200:
            self.assertEqual(response.data['@id'], id)

    def check_can_view(self, url, ids, status_code=200):
        response = self.client.get(url, content_type='application/ld+json')
        self.assertEqual(response.status_code, status_code)
        if status_code == 200:
            self.assertEqual(len(response.data['ldp:contains']), len(ids))
            for resource, id in zip(response.data['ldp:contains'], ids):
                self.assertEqual(resource['@id'], id)
        for id in ids:
            self.check_can_view_one(id, status_code)
        

    def test_permissionless_model(self):
        id = self.check_can_add('/posts/')
        self.check_can_view('/posts/', [id])

    def test_anonymous_readonly(self):
        post = AnonymousReadOnlyPost.objects.create(content = "test post")
        self.check_can_view('/anonymousreadonlyposts/', [post.urlid])
        self.check_can_add('/anonymousreadonlyposts/', 403)
        self.check_can_change(post.urlid, 403)

        self.authenticate()
        self.check_can_add('/anonymousreadonlyposts/')
        self.check_can_change(post.urlid)
    
    def test_authenticated_only(self):
        post = AuthenticatedOnlyPost.objects.create(content = "test post")
        self.check_can_view('/authenticatedonlyposts/', [post.urlid], 403)
        self.check_can_add('/authenticatedonlyposts/', 403)
        self.check_can_change(post.urlid, 403)
        post.delete()

        self.authenticate()
        #When authenticated it should behave like a non protected model
        id = self.check_can_add('/authenticatedonlyposts/')
        self.check_can_view('/authenticatedonlyposts/', [id])
        self.check_can_change(id)

    def test_readonly(self):
        post = ReadOnlyPost.objects.create(content = "test post")
        self.check_can_view('/readonlyposts/', [post.urlid])
        self.check_can_add('/readonlyposts/', 403)
        self.check_can_change(post.urlid, 403)

    def test_readandcreate(self):
        post = ReadAndCreatePost.objects.create(content = "test post")
        self.check_can_view('/readandcreateposts/', [post.urlid])
        self.check_can_add('/readandcreateposts/')
        self.check_can_change(post.urlid, 403)
        
    def test_owner_permissions(self):
        self.authenticate()
        them = get_user_model().objects.create_user(username='them', email='them@user.com', password='itstheirsecret')
        mine = OwnedResource.objects.create(description="Mine!", user=self.user)
        theirs = OwnedResource.objects.create(description="Theirs", user=them)
        noones = OwnedResource.objects.create(description="I belong to NO ONE!")
        self.check_can_view('/ownedresources/', [mine.urlid]) #checks I can access mine and only mine
        self.check_can_change(mine.urlid)
        self.check_can_view_one(theirs.urlid, 404)
        self.check_can_change(theirs.urlid, 404)
        self.check_can_view_one(noones.urlid, 404)
        self.check_can_change(noones.urlid, 404)


    def check_permissions(self, obj, group, required_perms):
        perms = GroupObjectPermission.objects.filter(group=group)
        for perm in perms:
            self.assertEqual(perm.content_type.model, obj._meta.model_name)
            self.assertEqual(perm.object_pk, str(obj.pk))
        self.assertEqual(set(perms.values_list('permission__codename', flat=True)),
                         {f'{perm}_{obj._meta.model_name}' for perm in required_perms})
    
    def create_circles(self):
        self.authenticate()
        self.user.user_permissions.add(Permission.objects.get(codename='view_restrictedcircle'))
        them = get_user_model().objects.create_user(username='them', email='them@user.com', password='itstheirsecret')
        mine = RestrictedCircle.objects.create(name="mine", description="Mine!", owner=self.user)
        theirs = RestrictedCircle.objects.create(name="theirs", description="Theirs", owner=them)
        noones = RestrictedCircle.objects.create(name="no one's", description="I belong to NO ONE!")
        return mine, theirs, noones

    def test_role_permissions(self):
        mine, theirs, noones = self.create_circles()
        self.assertIn(self.user, mine.members.user_set.all())
        self.assertIn(self.user, mine.admins.user_set.all())
        self.assertNotIn(self.user, theirs.members.user_set.all())
        self.assertNotIn(self.user, theirs.admins.user_set.all())
        self.assertNotIn(self.user, noones.members.user_set.all())
        self.assertNotIn(self.user, noones.admins.user_set.all())

        self.check_can_view('/restrictedcircles/', [mine.urlid]) #check filtering

        self.check_permissions(mine, mine.members, RestrictedCircle._meta.permission_roles['members']['perms'])
        self.check_permissions(mine, mine.admins, RestrictedCircle._meta.permission_roles['admins']['perms'])

    def test_inherit_permissions(self):
        mine, theirs, noones = self.create_circles()
        myresource = RestrictedResource.objects.create(content="mine", circle=mine)
        their_resource = RestrictedResource.objects.create(content="theirs", circle=theirs)
        noones_resource  = RestrictedResource.objects.create(content="noones", circle=noones)

        self.check_can_view('/restrictedresources/', [myresource.urlid])
        self.check_can_change(myresource.urlid)
        self.check_can_change(their_resource.urlid, 404)
        self.check_can_change(noones_resource.urlid, 404)

    def test_inherit_several_permissions(self):
        mine, theirs, noones = self.create_circles()
        ro_resource = ReadOnlyPost.objects.create(content="read only")
        myresource = DoubleInheritModel.objects.create(content="mine", circle=mine, ro_ancestor=None)
        some = DoubleInheritModel.objects.create(content="some", circle=theirs, ro_ancestor=ro_resource)
        other = DoubleInheritModel.objects.create(content="other", circle=noones, ro_ancestor=None)

        self.check_can_view('/doubleinheritmodels/', [myresource.urlid, some.urlid])
        self.check_can_change(myresource.urlid)
        self.check_can_change(some.urlid, 403)
        self.check_can_change(other.urlid, 404)

    def test_inherit_permissions_none(self):
        id = self.check_can_add('/doubleinheritmodels/')
        resource = DoubleInheritModel.objects.get(urlid=id)
        self.check_can_view('/doubleinheritmodels/', [resource.urlid])

        circle = RestrictedCircle.objects.create()
        id = self.check_can_add('/doubleinheritmodels/', 404, extra_content={'https://cdn.startinblox.com/owl#circle': {'@id': circle.urlid}})

    
    def test_and_permissions(self):
        self.authenticate()
        abc = ANDPermissionsDummy.objects.create(title='ABC')
        youpi = ANDPermissionsDummy.objects.create(title='youpi woopaa')
        wonder = ANDPermissionsDummy.objects.create(title='A Wonderful World!!')
        plop = ANDPermissionsDummy.objects.create(title='plop')
        self.check_can_view('/andpermissionsdummys/', [wonder.urlid], 403)
        self.check_can_add('/andpermissionsdummys/', 403, field='title')
        self.check_can_change(wonder.urlid, 403, field='title')

        self.user.username = 'toto'
        self.user.save()
        self.check_can_view('/andpermissionsdummys/', [wonder.urlid])
        self.check_can_view_one(abc.urlid, 404)
        self.check_can_view_one(youpi.urlid, 404)
        self.check_can_view_one(plop.urlid, 404)
        self.check_can_add('/andpermissionsdummys/', 403, field='title')
        self.check_can_change(wonder.urlid, 403, field='title')
        self.check_can_change(youpi.urlid, 403, field='title')

    def test_or_permissions(self):
        self.authenticate()
        abc = ORPermissionsDummy.objects.create(title='ABC')
        youpi = ORPermissionsDummy.objects.create(title='youpi woopaa')
        wonder = ORPermissionsDummy.objects.create(title='A Wonderful World!!')
        plop = ORPermissionsDummy.objects.create(title='plop')
        self.check_can_view('/orpermissionsdummys/', [abc.urlid, wonder.urlid])
        self.check_can_add('/andpermissionsdummys/', 403, field='title')
        self.check_can_change(wonder.urlid, 403, field='title')

        self.user.username = 'toto'
        self.user.save()
        self.check_can_view('/orpermissionsdummys/', [abc.urlid, youpi.urlid, wonder.urlid])
        self.check_can_view_one(plop.urlid, 404)
        self.check_can_add('/orpermissionsdummys/', field='title')
        self.check_can_change(wonder.urlid, field='title')
        self.check_can_change(plop.urlid, 404, field='title')
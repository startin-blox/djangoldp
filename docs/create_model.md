
### User model requirements

When implementing authentication in your own application, you have two options:

* Using or extending [DjangoLDP-Account](https://git.startinblox.com/djangoldp-packages/djangoldp-account), a DjangoLDP package modelling federated users
* Using your own user model & defining the authentication behaviour yourself

Please see the [Authentication guide](https://git.startinblox.com/djangoldp-packages/djangoldp/wikis/guides/authentication) for full information

If you're going to use your own model then for federated login to work your user model must extend `DjangoLDP.Model`, or define a `urlid` field on the user model, for example:
```python
urlid = LDPUrlField(blank=True, null=True, unique=True)
```
If you don't include this field, then all users will be treated as users local to your instance

The `urlid` field is used to uniquely identify the user and is part of the Linked Data Protocol standard. For local users it can be generated at runtime, but for some resources which are from distant servers this is required to be stored

## Creating your first model

1. Create your django model inside a file myldpserver/myldpserver/models.py
Note that container_path will be use to resolve instance iri and container iri
In the future it could also be used to auto configure django router (e.g. urls.py)

```python
from djangoldp.models import Model

class Todo(Model):
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()
```

1.1. Configure container path (optional)
By default it will be "todos/" with an S for model called Todo

```python
<Model>._meta.container_path = "/my-path/"
```

1.2. Configure field visibility (optional) 
Note that at this stage you can limit access to certain fields of models using

```python
<Model>._meta.serializer_fields (<>list of field names to show>)
```

 For example, if you have a model with a related field with type **django.contrib.auth.models.User** you don't want to show personal details or password hashes.

E.g.

```python
from django.contrib.auth.models import User

User._meta.serializer_fields  = ('username','first_name','last_name')
```

Note that this will be overridden if you explicitly set the fields= parameter as an argument to LDPViewSet.urls(), and filtered if you set the excludes= parameter.

2. Add a url in your urls.py:

```python
from django.conf.urls import url
from django.contrib import admin
from djangoldp.views import LDPViewSet
from .models import Todo

urlpatterns = [
    url(r'^', include('djangoldp.urls')),
    url(r'^admin/', admin.site.urls), # Optional
]
```

This creates 2 routes for each Model, one for the list, and one with an ID listing the detail of an object.

You could also only use this line in settings.py instead:

```python
ROOT_URLCONF = 'djangoldp.urls'
```

3. In the settings.py file, add your application name at the beginning of the application list, and add the following lines

```python
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'static')
LDP_RDF_CONTEXT = 'https://cdn.happy-dev.fr/owl/hdcontext.jsonld'
DJANGOLDP_PACKAGES = []
SITE_URL = 'http://localhost:8000'
BASE_URL = SITE_URL
```

* `LDP_RDF_CONTEXT` tells DjangoLDP where our RDF [ontology](https://www.w3.org/standards/semanticweb/ontology) is defined, which will be returned as part of our views in the 'context' field. This is a web URL and you can visit the value to view the full ontology online. The ontology can be a string, as in the example, but it can also be a dictionary, or a list of ontologies (see the [JSON-LD spec](https://json-ld.org) for examples)
* `DJANGOLDP_PACKAGES` defines which other [DjangoLDP packages](https://git.happy-dev.fr/startinblox/djangoldp-packages) we're using in this installation
* `SITE_URL` is the URL serving the site, e.g. `https://example.com/`. Note that if you include the DjangoLDP urls in a nested path (e.g. `https://example.com/api/`), then `SITE_URL` will need to be set to this value
* `BASE_URL` may be different from SITE_URL, e.g. `https://example.com/app/`


4. You can also register your model for the django administration site

```python
from django.contrib import admin
from djangoldp.admin import DjangoLDPAdmin
from .models import Todo

admin.site.register(Todo, DjangoLDPAdmin)
```

5. You then need to have your WSGI server pointing on myldpserver/myldpserver/wsgi.py

6. You will probably need to create a super user

```bash
$ ./manage.py createsuperuser
```

7. If you have no CSS on the admin screens :

```bash
$ ./manage.py collectstatic
```

## Execution

To start the server, `cd` to the root of your Django project and run :

```bash
$ python3 manage.py runserver
```

## Using DjangoLDP

### Models

To use DjangoLDP in your models you just need to extend djangoldp.Model

The Model class allows you to use your models in federation, adding a `urlid` field, and some key methods useful in federation

If you define a Meta for your Model, you will [need to explicitly inherit Model.Meta](https://docs.djangoproject.com/fr/2.2/topics/db/models/#meta-inheritance) in order to inherit the default settings, e.g. `default_permissions`

```python
from djangoldp.models import Model, LDPMetaMixin

class Todo(Model):
    name = models.CharField(max_length=255)

    class Meta(Model.Meta):
```

See "Custom Meta options" below to see some helpful ways you can tweak the behaviour of DjangoLDP

Your model will be automatically detected and registered with an LDPViewSet and corresponding URLs, as well as being registered with the Django admin panel. If you register your model with the admin panel manually, make sure to extend djangoldp.DjangoLDPAdmin so that the model is registered with [Django-Guardian object permissions](https://django-guardian.readthedocs.io/en/stable/userguide/admin-integration.html). An alternative version which extends Django's `UserAdmin` is available as djangoldp.DjangoLDPUserAdmin

#### Model Federation

Model `urlid`s can be **local** (matching `settings.SITE_URL`), or **external**

To maintain consistency between federated servers, [Activities](https://www.w3.org/TR/activitystreams-vocabulary) such as Create, Update, Delete are sent to external resources referenced in a ForeignKey relation, instructing them on how to manage the reverse-links with the local server

This behaviour can be disabled in settings.py
```python
SEND_BACKLINKS = False
```

It can also be disabled on a model instance
```python
instance.allow_create_backlinks = False
```

### LDPManager

DjangoLDP Models override `models.Manager`, accessible by `Model.objects`

#### local()

For situations where you don't want to include federated resources in a queryset e.g.

```python
Todo.objects.create(name='Local Todo')
Todo.objects.create(name='Distant Todo', urlid='https://anotherserversomewhere.com/todos/1/')

Todo.objects.all() # query set containing { Local Todo, Distant Todo }
Todo.objects.local() # { Local Todo } only
```

For Views, we also define a FilterBackend to achieve the same purpose. See the section on ViewSets for this purpose

## LDPViewSet

DjangoLDP automatically generates ViewSets for your models, and registers these at urls, according to the settings configured in the model Meta (see below for options)

### Custom Parameters

#### lookup_field

Can be used to use a slug in the url instead of the primary key.

```python
LDPViewSet.urls(model=User, lookup_field='username')
```

#### nested_fields

list of ForeignKey, ManyToManyField, OneToOneField and their reverse relations. When a field is listed in this parameter, a container will be created inside each single element of the container.

In the following example, besides the urls `/members/` and `/members/<pk>/`, two others will be added to serve a container of the skills of the member: `/members/<pk>/skills/` and `/members/<pk>/skills/<pk>/`.

ForeignKey, ManyToManyField, OneToOneField that are not listed in the `nested_fields` option will be rendered as a flat list and will not have their own container endpoint.

```python
Meta:
    nested_fields=["skills"]
```

Methods can be used to create custom read-only fields, by adding the name of the method in the `serializer_fields`. The same can be done for nested fields, but the method must be decorated with a `DynamicNestedField`.

```python
LDPUser.circles = lambda self: Circle.objects.filter(members__user=self)
LDPUser.circles.field = DynamicNestedField(Circle, 'circles')
```

### Improving Performance

On certain endpoints, you may find that you only need a subset of fields on a model, and serializing them all is expensive (e.g. if I only need the `name` and `id` of each group chat, then why serialize all of their members?). To optimise the fields serialized, you can pass a custom header in the request, `Accept-Model-Fields`, with a `list` value of desired fields e.g. `['@id', 'name']`


### Searching on LDPViewSets

It's common to allow search parameters on our ViewSet fields. Djangoldp provides automated searching on fields via the query parameters of a request via the class `djangoldp.filters.SearchByQueryParamFilterBackend`, a FilterBackend applied by default to `LDPViewSet` and any subclasses which don't override the `filter_backends` property

To use this on a request, for example: `/circles/?search-fields=name,description&search-terms=test&search-method=ibasic&search-policy=union`. For detail:

* `search-fields`: a list of one or more fields to search on the model
* `search-terms`: the terms to search
* `search-method` (optional): the method to apply the search with (supports `basic` (contains), case-insensitive `ibasic` and `exact`)
* `search-policy` (optional): the policy to apply when merging the results from different fields searched (`union`, meaning include the union of all result sets. Or `intersection`, meaning include only the results matched against all fields)

Some databases might treat accented characters as different from non-accented characters (e.g. grève vs. greve). To avoid this behaviour, please follow the [Stackoverflow post](https://stackoverflow.com/questions/54071944/fielderror-unsupported-lookup-unaccent-for-charfield-or-join-on-the-field-not) here, and then add the setting `SEARCH_UNACCENT_EXTENSION = True` and make sure that `'django.contrib.postgres'` is in your `INSTALLED_APPS`.


## Filter Backends

To achieve federation, DjangoLDP includes links to objects from federated servers and stores these as local objects (see 1.0 - Models). In some situations, you will want to exclude these from the queryset of a custom view

To provide for this need, there is defined in `djangoldp.filters` a FilterBackend which can be included in custom viewsets to restrict the queryset to only objects which were created locally:

```python
from djangoldp.filters import LocalObjectFilterBackend

class MyViewSet(..):
    filter_backends=[LocalObjectFilterBackend]
```

By default, LDPViewset applies filter backends from the `permission_classes` defined on the model (see 3.1 for configuration)

By default, `LDPViewSets` use another FilterBackend, `LocalObjectOnContainerPathBackend`, which ensures that only local objects are returned when the path matches that of the Models `container_path` (e.g. /users/ will return a list of local users). In very rare situations where this might be undesirable, it's possible to extend `LDPViewSet` and remove the filter_backend:

```python
class LDPSourceViewSet(LDPViewSet):
    model = LDPSource
    filter_backends = []
```

Following this you will need to update the model's Meta to use the custom `view_set`:

```python
class Meta:
    view_set = LDPSourceViewSet
```


## Custom Meta options on models

### rdf_type

Indicates the type the model corresponds to in the ontology. E.g. where `'hd:circle'` is defined in an ontology from `settings.LDP_RDF_CONTEXT`

```python
rdf_type = 'hd:circle'
```

### rdf_context

Sets added `context` fields to be serialized with model instances
```python
rdf_context = {'picture': 'foaf:depiction'}
```

### auto_author

This property allows to associate a model with the logged in user.


```python
class MyModel(models.Model):
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    class Meta:
        auto_author = 'author_user'
```

Now when an instance of `MyModel` is saved, its `author_user` property will be set to the authenticated user. 

## permissions

Django-Guardian is used by default to support object-level permissions. Custom permissions can be added to your model using this attribute. See the [Django-Guardian documentation](https://django-guardian.readthedocs.io/en/stable/userguide/assign.html) for more information.

By default, no permission class is applied on your model, which means there will be no permission check. In other words, anyone will be able to run any kind of request, read and write, even without being authenticated. Superusers always have all permissions on all resources.

### Default Permission classes

DjangoLDP comes with a set of permission classes that you can use for standard behaviour.

 * AuthenticatedOnly: Refuse access to anonymous users
 * ReadOnly: Refuse access to any write request
 * ReadAndCreate: Refuse access to any request changing an existing resource
 * CreateOnly: Refuse access to any request other than creation
 * AnonymousReadOnly: Refuse access to anonymous users with any write request
 * LDDPermissions: Give access based on the permissions in the database. For container requests (list and create), based on model level permissions. For all others, based on object level permissions. This permission class is associated with a filter that only renders objects on which the user has access.
 * PublicPermission: Give access based on a public flag on the object. This class must be used in conjonction with the Meta option `public_field`. This permission class is associated with a filter that only render objects that have the public flag set.
 * OwnerPermissions: Give access based on the owner of the object. This class must be used in conjonction with the Meta option `owner_field` or `owner_urlid_field`. This permission class is associated with a filter that only render objects of which the user is owner. When using a reverse ForeignKey or M2M field with no related_name specified, do not add the '_set' suffix in the `owner_field`.
 * OwnerCreatePermission: Refuse the creation of resources which owner is different from the request user.
 * InheritPermissions: Give access based on the permissions on a related model. This class must be used in conjonction with the Meta option `inherit_permission`, which value must be a list of names of the `ForeignKey` or `OneToOneField` pointing to the objects bearing the permission classes. It also applies filter based on the related model. If several fields are given, at least one must give permission for the permission to be granted.

 Permission classes can be chained together in a list, or through the | and & operators. Chaining in a list is equivalent to using the & operator.

```python
class MyModel(models.Model):
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    related = models.ForeignKey(SomeOtherModel)
    class Meta:
        permission_classes = [InheritPermissions, AuthenticatedOnly&(ReadOnly|OwnerPermissions|ACLPermissions)]
        inherit_permissions = ['related']
        owner_field = 'author_user'
```

### Role based permissions

Permissions can also be defind through roles defined in the Meta option `permission_roles`. When set, DjangoLDP will automatically create groups and assigne permissions on these groups when the object is created. The author can also be added automatically using the option `add_author`. The permission class `ACLPermissions` must be applied in order for the data base permission to be taken into account.

```python
class Circle(Model):
    name = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="owned_circles", on_delete=models.DO_NOTHING, null=True, blank=True)
    members = models.ForeignKey(Group, related_name="circles", on_delete=models.SET_NULL, null=True, blank=True)
    admins = models.ForeignKey(Group, related_name="admin_circles", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta(Model.Meta):
        auto_author = 'owner'
        permission_classes = [ACLPermissions]
        permission_roles = {
            'members': {'perms': ['view'], 'add_author': True},
            'admins': {'perms': ['view', 'change', 'control'], 'add_author': True},
        }
```

### Custom permission classes

Custom classes can be defined to handle specific permission checks. These class must inherit `djangoldp.permissions.LDPBasePermission` and can override the following method:

* get_filter_backend: returns a Filter class to be applied on the queryset before rendering. You can also define `filter_backend` as a field of the class directly.
* has_permission: called at the very begining of the request to check whether the user has permissions to call the specific HTTP method.
* has_object_permission: called on object requests on the first access to the object to check whether the user has rights on the request object.
* get_permissions: called on every single resource rendered to output the permissions of the user on that resource. This method should not access the database as it could severly affect performances.

### Inner permission rendering

For performance reasons, ACLs of resources inside a list are not rendered, which may require the client to request each single resource inside a list to get its ACLs. In some cases it's preferable to render these ACLs. This can be done using the setting `LDP_INCLUDE_INNER_PERMS`, setting its value to True.

## Other model options

### view_set

In case of custom viewset, you can use 

```python
from djangoldp.models import Model

class Todo(Model):
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()
    
    class Meta:
        view_set =  TodoViewSet

```

### serializer_fields

```python
from djangoldp.models import Model

class Todo(Model):
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()

    class Meta:
        serializer_fields =  ['name']

```

Only `name` will be serialized

### serializer_fields_exclude

```python
from djangoldp.models import Model

class Todo(Model):
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()

    class Meta:
        serializer_fields_exclude =  ['name']

```

Only `deadline` will be serialized

This is achieved when `LDPViewSet` sets the `exclude` in the serializer constructor. Note that if you use a custom viewset which does not extend LDPSerializer then you will need to set this property yourself.

### empty_containers

Slightly different from `serializer_fields` and `nested_fields` is the `empty_containers`, which allows for a list of nested containers which should be serialized, but without content, i.e. producing something like the following:
```
{ ..., 'members': {'@id': 'https://myserver.com/circles/x/members/'}, ... }
```

Where normally the serializer would output:
```
{ ..., 'members': {'@id': 'https://myserver.com/circles/x/members/',}, ... }
```

Note that this only applies when the field is nested in the serializer, i.e.:
* `https://myserver.com/circles/x/members/` **would not** serialize the container members
* `https://myserver.com/circles/x/members/` **would** serialize the container members

## Custom urls

To add customs urls who can not be add through the `Model` class, it's possible de create a file named `djangoldp_urls.py`. It will be executed like an `urls.py` file

## Pagination

To enable pagination feature just add this configuration to the server `settings.py` :

```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'djangoldp.pagination.LDPPagination',
    'PAGE_SIZE': 20
}
```

## 301 on domain mismatch

To enable 301 redirection on domain mismatch, add `djangoldp.middleware.AllowOnlySiteUrl` in `MIDDLEWARE`

This ensures that your clients will use `SITE_URL` and avoid mismatch betwen url & the id of a resource/container

```python
MIDDLEWARE = [
    'djangoldp.middleware.AllowOnlySiteUrl',
]
```

Notice that it will return only HTTP 200 Code.

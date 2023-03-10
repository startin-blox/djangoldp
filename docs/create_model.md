
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

#### nested_fields()

returns a list of all nested field names for the model, built of a union of the model class' `nested_fields` setting, the to-many relations on the model, excluding all fields detailed by `nested_fields_exclude`

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

In the following example, besides the urls `/members/` and `/members/<pk>/`, two other will be added to serve a container of the skills of the member: `/members/<pk>/skills/` and `/members/<pk>/skills/<pk>/`

```python
<Model>._meta.nested_fields=["skills"]
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

Some databases might treat accented characters as different from non-accented characters (e.g. gr??ve vs. greve). To avoid this behaviour, please follow the [Stackoverflow post](https://stackoverflow.com/questions/54071944/fielderror-unsupported-lookup-unaccent-for-charfield-or-join-on-the-field-not) here, and then add the setting `SEARCH_UNACCENT_EXTENSION = True` and make sure that `'django.contrib.postgres'` is in your `INSTALLED_APPS`.


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

### auto_author_field

Set this property to make the value of the `auto_author` field a property on the authenticated use.

```python
class MyModel(models.Model):
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    class Meta:
        auto_author = 'author_user'
	auto_author_field = 'profile'
```

Now when an instance of `MyModel` is saved, its `author_user` property will be set to the **profile** of the authenticated user.

## permissions

Django-Guardian is used by default to support object-level permissions. Custom permissions can be added to your model using this attribute. See the [Django-Guardian documentation](https://django-guardian.readthedocs.io/en/stable/userguide/assign.html) for more information

### Serializing Permissions

* `SERIALIZE_EXCLUDE_PERMISSIONS`. Permissions which should always be excluded from serialization defaults to `['inherit']`
* `SERIALIZE_EXCLUDE_CONTAINER_PERMISSIONS_DEFAULT`. Excluded also when serializing containers `['delete']`
* `SERIALIZE_EXCLUDE_OBJECT_PERMISSIONS_DEFAULT`. Excluded also when serializing objects `[]`

## permissions_classes

This allows you to add permissions for anonymous, logged in user, author ... in the url:
By default `LDPPermissions` is used.
Specific permissin classes can be developed to fit special needs.

## anonymous_perms, user_perms, owner_perms, superuser_perms

Those allow you to set permissions from your model's meta.

You can give the following permission to them:

* `view`
* `add`
* `change`
* `control`
* `delete`
* `inherit`

With inherit, Users can herit from Anons. Also Owners can herit from Users.

Eg. with this model Anons can view, Auths can add & Owners can edit & delete.

Note that `owner_perms` need a `owner_field` meta that point the field with owner user.

```python
from djangoldp.models import Model

class Todo(Model):
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        anonymous_perms = ['view']
        authenticated_perms = ['inherit', 'add'] # inherits from anonymous
        owner_perms = ['inherit', 'change', 'control', 'delete'] # inherits from authenticated
        superuser_perms = ['inherit'] # inherits from owner
        owner_field = 'user' # can be nested, e.g. user__parent
```


Important note:
If you need to give permissions to owner's object, don't forget to add auto_author in model's meta

Superuser's are by default configured to have all of the default DjangoLDP permissions
* you can restrict their permissions globally by setting `DEFAULT_SUPERUSER_PERMS = []` in your server settings
* you can change it on a per-model basis as described here. Please note that if you use a custom permissions class you will need to give superusers this permission explicitly, or use the `SuperUsersPermission` class on the model which will grant superusers all permissions

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

### container_path

See 3.1. Configure container path (optional)

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

This is achieved when `LDPViewSet` sets the `exclude` property on the serializer in `build_serializer` method. Note that if you use a custom viewset which does not extend LDPSerializer then you will need to set this property yourself

### nested_fields -- DEPRECIATED

Set on a model to auto-generate viewsets and containers for nested relations (e.g. `/circles/<pk>/members/`)

Depreciated in DjangoLDP 0.8.0, as all to-many fields are included as nested fields by default

### nested_fields_exclude

```python
<Model>._meta.nested_fields_exclude=["skills"]
```

Will exclude the field `skills` from the model's nested fields, and prevent a container `/model/<pk>/skills/` from being generated

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

## Sources

To enable sources auto creation for all models, change `djangoldp` by `djangoldp.apps.DjangoldpConfig`, on `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    'djangoldp.apps.DjangoldpConfig',
]
```

## 301 on domain mismatch

To enable 301 redirection on domain mismatch, add `djangoldp.middleware.AllowOnlySiteUrl` on `MIDDLEWARE`

This ensure that your clients will use `SITE_URL` and avoid mismatch betwen url & the id of a resource/container

```python
MIDDLEWARE = [
    'djangoldp.middleware.AllowOnlySiteUrl',
]
```

Notice tht it'll redirect only HTTP 200 Code.

## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

Building a Startin' Blox application? Read this: https://git.happy-dev.fr/startinblox/devops/doc

## Requirements

* Django (known to work with django 1.11)
* Django Rest Framework
* pyld==1.0.5
* django-guardian
* djangorestframework-guardian

## Installation

1. Install this module and all its dependencies

```bash
$ pip install djangoldp
```

2. Create a django project
 
```bash
$ django-admin startproject myldpserver
```

3. Add DjangoLDP to INSTALLED_APPS
```python
INSTALLED_APPS = [
    ...
    # make sure all of your own apps are installed BEFORE DjangoLDP
    'djangoldp.apps.DjangoldpConfig',
]
```

IMPORTANT: DjangoLDP will register any models which haven't been registered, with the admin. As such it is important to add your own apps above DjangoLDP, so that you can use custom Admin classes if you wish

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

### Models

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

### Model Federation

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

For situations where you don't want to include federated resources in a queryset, DjangoLDP Models override `models.Manager`, allowing you to write `Todo.objects.local()`, for example:
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

In the following example, besides the urls `/members/` and `/members/<pk>/`, two other will be added to serve a container of the skills of the member: `/members/<pk>/skills/` and `/members/<pk>/skills/<pk>/`

```python
<Model>._meta.nested_fields=["skills"]
```

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

## permissions_classes

This allows you to add permissions for anonymous, logged in user, author ... in the url:
By default `LDPPermissions` is used.
Specific permissin classes can be developed to fit special needs.

## anonymous_perms, user_perms, owner_perms

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
        authenticated_perms = ['inherit', 'add']
        owner_perms = ['inherit', 'change', 'control', 'delete']
        owner_field = 'user'
```


Important note:
If you need to give permissions to owner's object, don't forget to add auto_author in model's meta

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

## Extending DjangoLDP

### Testing

Packaged with DjangoLDP is a tests module, containing unit tests

You can extend these tests and add your own test cases by following the examples in the code. You can then run your tests with:
`python -m unittest tests.runner`

## License

Licence MIT

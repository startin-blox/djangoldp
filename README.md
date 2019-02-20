## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

## Requirements

* Django (known to work with django 1.11)
* Django Rest Framework
* pyld
* django-guardian
* djangorestframework-guardian

## Installation

1. Install this module and all its dependencies

```
pip install djangoldp
```

2. Create a django project
 
```
django-admin startproject myldpserver
```

3. Create your django model inside a file myldpserver/myldpserver/models.py
Note that container_path will be use to resolve instance iri and container iri
In the future it could also be used to auto configure django router (e.g. urls.py)

```
from djangoldp.models import Model

class Todo(Model):
    container_path = "/my-path/"
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()

```

3.1. Configure field visibility (optional) 
Note that at this stage you can limit access to certain fields of models using

```
<Model>._meta.serializer_fields (<>list of field names to show>)
```

 For example, if you have a model with a related field with type **django.contrib.auth.models.User** you don't want to show personal details or password hashes.

E.g.

```
from django.contrib.auth.models import User

User._meta.serializer_fields  = ('username','first_name','last_name')
```

Note that this will be overridden if you explicitly set the fields= parameter as an argument to LDPViewSet.urls(), and filtered if you set the excludes= parameter.

4. Add a url in your urls.py:

```
from django.conf.urls import url
from django.contrib import admin
from djangoldp.views import LDPViewSet
from .models import Todo

urlpatterns = [
    url(r'^todos/', LDPViewSet.urls(model=Todo)),
    url(r'^admin/', admin.site.urls),
]
```

This creates 2 routes, one for the list, and one with an ID listing the detail of an object.

5. In the settings.py file, add your application name at the beginning of the application list, and add the following lines

```
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'static')
LDP_RDF_CONTEXT = 'https://cdn.happy-dev.fr/owl/hdcontext.jsonld'
```

6. You can also register your model for the django administration site

```
from django.contrib import admin
from .models import Todo

admin.site.register(Todo)
```

7. You then need to have your WSGI server pointing on myldpserver/myldpserver/wsgi.py

8. You will probably need to create a super user
```
./manage.py createsuperuser
```

9. If you have no CSS on the admin screens : 
```
./manage.py collectstatic
```

## Execution
To start the server, `cd` to the root of your Django project and run :
```
python3 manage.py runserver
```

## Custom Parameters to LDPViewSet

### lookup_field
Can be used to use a slug in the url instead of the primary key.
```
LDPViewSet.urls(model=User, lookup_field='username')
```

### nested_fields
list of ForeignKey, ManyToManyField, OneToOneField and their reverse relations. When a field is listed in this parameter, a container will be created inside each single element of the container.

In the following example, besides the urls `/members/` and `/members/<pk>/`, two other will be added to serve a container of the skills of the member: `/members/<pk>/skills/` and `/members/<pk>/skills/<pk>/` 
```
    url(r'^members/', LDPViewSet.urls(model=Member, nested_fields=("skills",))),
```

From the 0.5 we added permissions check by default on every route, so you may encounter 400 errors code on your POST requests. You can disable those checks by specifying the permission_classes as an empty array in our URLs files.


```
url(r'^posts/', LDPViewSet.urls(model=Post, permission_classes=(), filter_backends = ())),
```

## Custom Meta options on models

### rdf_type
### auto_author
This property allows to associate a model with the logged in user.

```python
class MyModel(models.Model):
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL)
    class Meta:
        auto_author = 'author_user'
```
## permissions
This allows you to add permissions for AnonymousUser, logged in user, author ... in the url:
Currently, there are 3 choices :
* PublicPostPermissions
* PrivateProjectPermissions
* NotificationsPermissions
Specific permissin classes can be developed to fit special needs.

PublicPostPermissions gives these permissions: 
* Anonymous users: can read all posts
* Logged in users: can read all posts + create new posts
* Author: can read all posts + create new posts + update their own

```
from django.conf.urls import url
from djangoldp.views import LDPViewSet
from djangoldp.permissions import PublicPostPermissions

urlpatterns = [
    url(r'^projects/', ProjectViewSet.urls(permission_classes=(PublicPostPermissions,))),
    url(r'^customers/', LDPViewSet.urls(model=Customer)),
]
```

PrivateProjectPermissions provides the following
* Anonymous users: no permissions
* Logged in users: can read projects if they're in the team
* Users of group Partners: can see all projects + update all projects

```
from django.conf.urls import url
from djangoldp.views import LDPViewSet
from djangoldp.permissions import PrivateProjectPermissions

urlpatterns = [
    url(r'^projects/', ProjectViewSet.urls(permission_classes=(PrivateProjectPermissions,))),
    url(r'^customers/', LDPViewSet.urls(model=Customer)),
]
```
NotificationsPermissions is used for, well, notifications:
* Anonymous users: can create notifications but can't read
* Logged in users: can create notifications but can't read
* Inbox owners: can read + update all notifications 

```
from django.conf.urls import url
from djangoldp.views import LDPViewSet
from djangoldp.permissions import NotificationsPermissions

urlpatterns = [
    url(r'^projects/', ProjectViewSet.urls(permission_classes=(NotificationsPermissions,))),
    url(r'^customers/', LDPViewSet.urls(model=Customer)),
]
```

Important note:
If you need to give permissions to owner's object, don't forget to add auto_author in model's meta


## License

Licence MIT

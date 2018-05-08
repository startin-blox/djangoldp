## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

## Requirements

* Django (known to work with django 1.11)
* Django Rest Framework
* pyld

## Installation

### 1- Install this module and all its dependencies

```
pip install djangoldp
```

### 2- Create a django project
 
```
django-admin startproject myldpserver
```

### 3- Create your django model inside a file myldpserver/myldpserver/models.py

```
from django.db import models

class Todo(models.Model):
    name = models.CharField(max_length=255)
    deadline = models.DateTimeField()

```

### 4- Add a url in your urls.py:

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

### 5- In the settings.py file, add your application name at the beginning of the application list, and add the following lines

```
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'static')
LDP_RDF_CONTEXT = 'https://cdn.happy-dev.fr/owl/hdcontext.jsonld'
```

### 6- You can also register your model for the django administration site

```
from django.contrib import admin
from .models import Todo

admin.site.register(Todo)
```

### 7- You then need to have your WSGI server pointing on myldpserver/myldpserver/wsgi.py

## Execution
To start the server, `cd` to the root of your Django project and run :
```
python3 manage.py runserver
```

## Lic ense

No licence yet. Please wait...

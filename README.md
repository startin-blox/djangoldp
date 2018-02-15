## Synopsis

This module is an add-on for Django REST Framework that serves a django model respecting the Linked Data Platform convention.

It aims at enabling people with little development skills to serve their own data, to be used with a LDP application.

## Requirements

* Django (known to work with django 1.11)
* Django Rest Framework
* pyld

## Installation

1. Add this module to your application, or place it in a directory included in your PYTHONPATH
2. Create your model normally
3. Add a url in your urls.py:

```
from djangoldp.views import LDPViewSet
from .models import MyModel

urlpatterns = [
    url(r'^my-model/', include(LDPViewSet.urls(model=MyModel))),
    url(r'^admin/', admin.site.urls),
]
```

This creates 2 routes, one for the list, and one with an ID listing the detail of an object.

## Execution
To start the server, `cd` to the root of your Django project and run :
```
python3 manage.py runserver
```

## License

No licence yet. Please wait...

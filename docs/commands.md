# Available commands

## generate_static_content

You can generate and make available at a /ssr/xxx URI a static copy of the AnonymousUser view of given models.
Those models need to be configured with the `static_version` and `static_params` Meta options like:

```python
class Location(Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    zip_code = models.IntegerField()
    visible = models.BooleanField(default=False)

    class Meta:
        # Allow generating a static version of the container view
        static_version = 1

        # Add some GET parameters to configure the selection of data
        static_params = {
          "search-fields": "visible",
          "search-terms": True,
          "search-method": "exact"
        }
```

You will need additional settings defined either in your settings.yml or settings.py file:

```yml
BASE_URL: 'http://localhost:8000/'
MAX_RECURSION_DEPTH: 10 # Default value: 5
SSR_REQUEST_TIME: 20 # Default value 10 (seconds)
```

Then you can try it out by executing the following command:

```sh
python manage.py generate_static_content
```

You can also set a cron task or a celery Task to launch this command in a regular basis.
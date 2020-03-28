# Using the client

```
# docker run --rm -v $PWD:/code -w /code -it python:3.6 bash
# pip install .
# cd /tmp/
# djangoldp start myproject
```

BUGFIX: Configure `djangoldp_account` in `packages.yml` and install it:
```
# pip install djangoldp_account
```

Play with the installation:
```
# python manage.py runserver --settings=sibserver.setting
```

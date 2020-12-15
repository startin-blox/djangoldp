import argparse
from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings
from djangoldp.models import LDPSource
from urllib.parse import urlparse
import requests

class Command(BaseCommand):
  help = "Check the datas integrity"

  def add_arguments(self, parser):
    parser.add_argument(
      "--fix-faulted-resources",
      default=False,
      nargs="?",
      const=True,
      help="Fix faulted resources",
    )
    parser.add_argument(
      "--fix-404-resources",
      default=False,
      nargs="?",
      const=True,
      help="Fix 404 resources",
    )

  def handle(self, *args, **options):
    models = apps.get_models()
    resources = set()
    resources_map = dict()
    base_urls = set()
    for model in models:
      for obj in model.objects.all():
        if hasattr(obj, "urlid"):
          if(obj.urlid):
            if(not obj.urlid.startswith(settings.BASE_URL)):
              resources.add(obj.urlid)
              resources_map[obj.urlid] = obj
              base_urls.add(urlparse(obj.urlid).netloc)

    if(len(base_urls) > 0):
      print("Servers that I have backlinks to:")
      for server in base_urls:
        print("- "+server)
    else:
      print("I don't have any backlink")

    source_urls = set()
    for source in LDPSource.objects.all():
      source_urls.add(urlparse(source.urlid).netloc)

    if(len(source_urls) > 0):
      print("Servers that I'm allowed to get federated to:")
      for server in source_urls:
        print("- "+server)
    else:
      print("I'm not federated")

    difference_servers = base_urls.difference(source_urls)
    if(len(difference_servers) > 0):
      print("Servers that I should not get aware of:")
      for server in difference_servers:
        print("- "+server)

      faulted_resources = set()
      for server in difference_servers:
        for resource in resources:
          if(urlparse(resource).netloc in server):
            faulted_resources.add(resource)

      if(len(faulted_resources) > 0):
        print("Resources in fault:")
        for resource in faulted_resources:
          print("- "+resource)
      else:
        print("No resource are in fault")
      if(options["fix_faulted_resources"]):
        for resource in faulted_resources:
          resources_map[resource].delete()
        print("Fixed faulted resources")
      else:
        print("Fix them with `./manage.py check_integrity --fix-faulted-resources`")
    else:
      print("I accept datas for every of those servers")

    resources_404 = set()
    for resource in resources:
      try:
        if(requests.get(resource).status_code == 404):
          resources_404.add(resource)
      except:
        pass

    if(len(resources_404) > 0):
      print("Faulted resources, 404:")
      for resource in resources_404:
        print("- "+resource)
      if(options["fix_404_resources"]):
        for resource in resources_404:
          resources_map[resource].delete()
        print("Fixed 404 resources")
      else:
        print("Fix them with `./manage.py check_integrity --fix-404-resources`")
    else:
      print("No 404 in known resources")

    exit(0)

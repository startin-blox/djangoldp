import os
import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.apps import apps
from urllib.parse import urlparse, urlunparse

class Command(BaseCommand):
    help = 'Generate static content for models with a specific meta attribute'

    def handle(self, *args, **kwargs):
        output_dir = 'ssr'
        if not os.path.exists(output_dir):
          os.makedirs(output_dir, exist_ok=True)

        base_uri = getattr(settings, 'BASE_URL', '')
        max_depth = getattr(settings, 'MAX_RECURSION_DEPTH', 5)  # Ad

        for model in apps.get_models():
            if hasattr(model._meta, 'static_version'):
                print(f"model: {model}")
                container_path = model.get_container_path()
                url = f'{base_uri}{container_path}'
                print(f"current request url before adding params: {url}")

                if hasattr(model._meta, 'static_params'):
                    # static_params which is a json must be decomposed and added to the url as query parameters, first with ? then with &
                    url += '?'
                    for key, value in model._meta.static_params.items():
                        url += f'{key}={value}&'
                    url = url[:-1]

                print(f"current request url after adding params: {url}")
                response = requests.get(url, timeout=settings.SSR_REQUEST_TIMEOUT)

                if response.status_code == 200:
                    content = response.text
                    content = self.update_ids_and_fetch_associated(content, base_uri,  output_dir, 0, max_depth)

                    filename = container_path[1:-1]
                    file_path = os.path.join(output_dir, f'{filename}.json')

                    print(f"file_path: {file_path}")
                    with open(file_path, 'w') as f:
                        f.write(content)
                    self.stdout.write(self.style.SUCCESS(f'Successfully fetched and saved content for {model._meta.model_name} from {url}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Failed to fetch content from {url}: {response.status_code}'))

    def update_ids_and_fetch_associated(self, content, base_uri, output_dir, depth, max_depth):
        if depth > max_depth:
            return content

        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    self.update_and_fetch_id(item, base_uri, output_dir, depth, max_depth)
            else:
                self.update_and_fetch_id(data, base_uri, output_dir, depth, max_depth)

            print(f"Content: {data}")
            return json.dumps(data)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Failed to decode JSON: {e}'))
            return content

    def update_and_fetch_id(self, item, base_uri, output_dir, depth, max_depth):
        if '@id' in item:
            parsed_url = urlparse(item['@id'])
            path = f'/ssr{parsed_url.path}'
            item['@id'] = urlunparse((parsed_url.scheme, parsed_url.netloc, path, parsed_url.params, parsed_url.query, parsed_url.fragment))
            associated_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment))
            associated_file_path = path[1:-1] + '.json'
            print(f"associated_file_path: {associated_file_path}")
            associated_file_dir = os.path.dirname(associated_file_path)
            if not os.path.exists(associated_file_dir):
                os.makedirs(associated_file_dir)

            if not os.path.exists(associated_file_path):
              # Fetch associated content
              try:
                  response = requests.get(associated_url, timeout=settings.SSR_REQUEST_TIMEOUT)
                  if response.status_code == 200:
                      associated_content = self.update_ids_and_fetch_associated(response.text, base_uri, output_dir, depth + 1, max_depth)
                      print(f"associated_file_path: {associated_file_path}")
                      associated_file_dir = os.path.dirname(associated_file_path)
                      print(f"associated_file_path: {associated_file_dir}")
                      if not os.path.exists(associated_file_dir):
                          os.makedirs(associated_file_dir)
                      with open(associated_file_path, 'w') as f:
                          f.write(associated_content)
                      self.stdout.write(self.style.SUCCESS(f'Successfully fetched and saved associated content for {associated_url}'))
                  else:
                      self.stdout.write(self.style.ERROR(f'Failed to fetch associated content from {associated_url}: {response.status_code}'))
              except requests.exceptions.Timeout:
                  self.stdout.write(self.style.ERROR(f'Request to {associated_url} timed out'))
              except requests.exceptions.RequestException as e:
                  self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Associated file already exists for {associated_url}, skipping fetch'))

        for key, value in item.items():
            if isinstance(value, dict):
                self.update_and_fetch_id(value, base_uri, output_dir, depth, max_depth)
            elif isinstance(value, list):
                for sub_item in value:
                    if isinstance(sub_item, dict):
                        self.update_and_fetch_id(sub_item, base_uri, output_dir, depth, max_depth)
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
                response = requests.get(url)

                if response.status_code == 200:
                    content = response.text
                    content = self.update_ids(content, base_uri)

                    filename = container_path[1:-1]
                    file_path = os.path.join(output_dir, f'{filename}.json')

                    print(f"file_path: {file_path}")
                    with open(file_path, 'w') as f:
                        f.write(content)
                    self.stdout.write(self.style.SUCCESS(f'Successfully fetched and saved content for {model._meta.model_name} from {url}'))
                else:
                    self.stdout.write(self.style.ERROR(f'Failed to fetch content from {url}: {response.status_code}'))

    def update_ids(self, content, base_uri):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    self.update_item_id(item, base_uri)
            elif isinstance(data, dict):
                self.update_item_id(data, base_uri)
            return json.dumps(data)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Failed to decode JSON: {e}'))
            return content

    def update_item_id(self, item, base_uri):
        if '@id' in item:
            parsed_url = urlparse(item['@id'])
            path = f'/ssr{parsed_url.path}'
            item['@id'] = urlunparse((parsed_url.scheme, parsed_url.netloc, path, parsed_url.params, parsed_url.query, parsed_url.fragment))
        for key, value in item.items():
            if isinstance(value, dict):
                self.update_item_id(value, base_uri)
            elif isinstance(value, list):
                for sub_item in value:
                    if isinstance(sub_item, dict):
                        self.update_item_id(sub_item, base_uri)
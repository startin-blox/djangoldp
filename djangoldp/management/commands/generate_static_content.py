import os
import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.apps import apps
from urllib.parse import urlparse, urljoin

class StaticContentGenerator:
    def __init__(self, stdout, style):
        self.stdout = stdout
        self.style = style
        self.base_uri = getattr(settings, 'BASE_URL', '')
        self.max_depth = getattr(settings, 'MAX_RECURSION_DEPTH', 5)
        self.request_timeout = getattr(settings, 'SSR_REQUEST_TIMEOUT', 10)
        self.regenerated_urls = set()
        self.failed_urls = set()
        self.output_dir = 'ssr'
        self.output_dir_filtered = 'ssr_filtered'

    def generate_content(self):
        self._create_output_directory()
        for model in self._get_static_models():
            self._process_model(model)

    def _create_output_directory(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.output_dir_filtered, exist_ok=True)

    def _get_static_models(self):
        return [model for model in apps.get_models() if hasattr(model._meta, 'static_version')]

    def _process_model(self, model):
        self.stdout.write(f"Generating content for model: {model}")
        url = self._build_url(model)
        if url not in self.regenerated_urls and url not in self.failed_urls:
            self._fetch_and_save_content(model, url, self.output_dir)
        else:
            self.stdout.write(self.style.WARNING(f'Skipping {url} as it has already been fetched'))
        if hasattr(model._meta, 'static_params'):
            url = self._build_url(model, True)
            if url not in self.regenerated_urls and url not in self.failed_urls:
                self._fetch_and_save_content(model, url, self.output_dir_filtered)
            else:
                self.stdout.write(self.style.WARNING(f'Skipping {url} as it has already been fetched'))

    def _build_url(self, model, use_static_params=False):
        container_path = model.get_container_path()
        url = urljoin(self.base_uri, container_path)
        if hasattr(model._meta, 'static_params') and use_static_params:
            url += '?' + '&'.join(f'{k}={v}' for k, v in model._meta.static_params.items())
        return url

    def _fetch_and_save_content(self, model, url, output_dir):
        try:
            response = requests.get(url, timeout=self.request_timeout)
            if response.status_code == 200:
                content = self._update_ids_and_fetch_associated(response.text)
                self._save_content(model, url, content, output_dir)
            else:
                self.stdout.write(self.style.ERROR(f'Failed to fetch content from {url}: HTTP {response.status_code}'))
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching content from {url}: {str(e)}'))

    def _save_content(self, model, url, content, output_dir):
        relative_path = urlparse(url).path.strip('/')
        file_path = os.path.join(output_dir, relative_path)
        if file_path.endswith('/'):
            file_path = file_path[:-1]
        if not file_path.endswith('.jsonld'):
            file_path += '.jsonld'
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS(f'Successfully saved content for {model._meta.model_name} from {url} to {file_path}'))
        except IOError as e:
            self.stdout.write(self.style.ERROR(f'Error saving content for {model._meta.model_name}: {str(e)}'))

    def _update_ids_and_fetch_associated(self, content, depth=0):
        if depth > self.max_depth:
            return content

        try:
            data = json.loads(content)
            self._process_data(data, depth)
            return json.dumps(data)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Failed to decode JSON: {e}'))
            return content

    def _process_data(self, data, depth):
        if isinstance(data, dict):
            self._process_item(data, depth)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._process_item(item, depth)

    def _process_item(self, item, depth):
        if '@id' in item:
            self._update_and_fetch_content(item, depth)

        for value in item.values():
            if isinstance(value, (dict, list)):
                self._process_data(value, depth)

    def _update_and_fetch_content(self, item, depth):
        original_id = item['@id']
        parsed_url = urlparse(original_id)

        if not parsed_url.netloc:
            original_id = urljoin(self.base_uri, original_id)
            parsed_url = urlparse(original_id)

        path = parsed_url.path
        if path.startswith(urlparse(self.base_uri).path):
            path = path[len(urlparse(self.base_uri).path):]

        new_id = f'/ssr{path}'
        item['@id'] = urljoin(self.base_uri, new_id)

        self._fetch_and_save_associated_content(original_id, path, depth)

    def _rewrite_ids_before_saving(self, data):
        if isinstance(data, dict):
            if '@id' in data:
                original_id = data['@id']
                parsed_url = urlparse(data['@id'])
                if not parsed_url.netloc:
                    content_id = urljoin(self.base_uri, original_id)
                    parsed_url = urlparse(content_id)

                if 'ssr/' not in data['@id']:
                    path = parsed_url.path
                    if path.startswith(urlparse(self.base_uri).path):
                        path = path[len(urlparse(self.base_uri).path):]

                    new_id = f'/ssr{path}'
                    data['@id'] = urljoin(self.base_uri, new_id)
            for value in data.values():
                if isinstance(value, (dict, list)):
                    self._rewrite_ids_before_saving(value)
        elif isinstance(data, list):
            for item in data:
                self._rewrite_ids_before_saving(item)
        return data

    def _fetch_and_save_associated_content(self, url, new_path, depth):
        if url in self.regenerated_urls:
            self.stdout.write(self.style.WARNING(f'Skipping {url} as it has already been fetched'))
            return
        if url in self.failed_urls:
            self.stdout.write(self.style.WARNING(f'Skipping {url} as it has already been tried and failed'))
            return

        file_path = os.path.join(self.output_dir, new_path.strip('/'))
        if file_path.endswith('/'):
            file_path = file_path[:-1]
        if not file_path.endswith('.jsonld'):
            file_path += '.jsonld'
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            response = requests.get(url, timeout=self.request_timeout)
            if response.status_code == 200:
                updated_content = json.loads(self._update_ids_and_fetch_associated(response.text, depth + 1))
                updated_content = self._rewrite_ids_before_saving(updated_content)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(updated_content))
                self.regenerated_urls.add(url)
                self.stdout.write(self.style.SUCCESS(f'Successfully fetched and saved associated content from {url} to {file_path}'))
            else:
                self.failed_urls.add(url)
                self.stdout.write(self.style.ERROR(f'Failed to fetch associated content from {url}: HTTP {response.status_code}'))
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error fetching associated content from {url}: {str(e)}'))
        except IOError as e:
            self.stdout.write(self.style.ERROR(f'Error saving associated content from {url}: {str(e)}'))

class Command(BaseCommand):
    help = 'Generate static content for models having the static_version meta attribute set to 1/true'

    def handle(self, *args, **options):
        generator = StaticContentGenerator(self.stdout, self.style)
        generator.generate_content()
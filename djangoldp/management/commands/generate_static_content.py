import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.apps import apps
from django.core.management.base import BaseCommand

from djangoldp.views.static_helpers import (
    BASE_URL,
    PARSED_BASE_URL,
    RDF_CONTEXT,
    build_file_path,
    extract_content_from_response,
    get_model_from_path,
    get_response_from_view,
    rewrite_ids,
    save_content_to_file,
)


class StaticContentGenerator:
    def __init__(self, stdout, style):
        self.stdout = stdout
        self.style = style
        self.max_depth = 5
        self.regenerated_urls = set()
        self.failed_urls = set()
        self.output_dir = "ssr"
        self.output_dir_filtered = "ssr_filtered"
        self.fetch_queue = []

    def generate_content(self):
        self._create_output_directory()
        models = self._get_static_models()
        for model in models:
            self._process_model(model)
        self._process_fetch_queue()

    def _create_output_directory(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.output_dir_filtered, exist_ok=True)

    def _get_static_models(self):
        return [
            model
            for model in apps.get_models()
            if hasattr(model._meta, "static_version")
        ]

    def _process_model(self, model):
        self.stdout.write(f"Generating content for model: {model}")
        depth = getattr(model._meta, "depth", None)
        path = self._build_path(model)
        if path not in self.regenerated_urls and path not in self.failed_urls:
            self._fetch_and_save_content(model, path, self.output_dir, depth)
        else:
            self.stdout.write(
                self.style.WARNING(f"Skipping {path} as it has already been fetched")
            )
        if hasattr(model._meta, "static_params"):
            path = self._build_path(model, True)
            if path not in self.regenerated_urls and path not in self.failed_urls:
                self._fetch_and_save_content(
                    model, path, self.output_dir_filtered, depth
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {path} as it has already been fetched"
                    )
                )

    def _build_path(self, model, use_static_params=False):
        container_path = model.get_container_path()
        if container_path.startswith("/"):
            container_path = container_path[1:]
        container_path = container_path.rstrip("/")
        if hasattr(model._meta, "static_params") and use_static_params:
            params = "&".join(f"{k}={v}" for k, v in model._meta.static_params.items())
            container_path += "?" + params
        return container_path

    def _fetch_and_save_content(self, model, path, output_dir, depth=None):
        response = get_response_from_view(path, depth=depth)
        if response and response.status_code == 200:
            content = extract_content_from_response(response)
            self._save_content(model, path, content, output_dir)
        else:
            self.failed_urls.add(path)
            status = response.status_code if response else "Unknown"
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch content for {path}: HTTP {status}")
            )

    def _save_content(self, model, path, content, output_dir):
        processed_content = self._update_ids_and_fetch_associated(content)

        file_path = build_file_path(output_dir, path)

        try:
            save_content_to_file(file_path, processed_content)
            self.regenerated_urls.add(path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully saved content for {model._meta.model_name} to {file_path}"
                )
            )
        except IOError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error saving content for {model._meta.model_name}: {str(e)}"
                )
            )

    def _update_ids_and_fetch_associated(self, content, depth=0):
        if depth > self.max_depth:
            return content

        try:
            data = json.loads(content)
            self._process_data(data, depth)
            processed_data = rewrite_ids(data)
            if isinstance(processed_data, dict) and "@context" not in processed_data:
                processed_data["@context"] = RDF_CONTEXT
            return json.dumps(processed_data)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Failed to decode JSON: {e}"))
            return content

    def _process_data(self, data, depth):
        if isinstance(data, dict):
            self._process_item(data, depth)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._process_item(item, depth)

    def _process_item(self, item, depth):
        if "@id" in item:
            self._update_and_fetch_content(item, depth)

        for value in item.values():
            if isinstance(value, (dict, list)):
                self._process_data(value, depth)

    def _update_and_fetch_content(self, item, depth):
        from urllib.parse import urljoin, urlparse

        original_id = item["@id"]
        parsed_url = urlparse(original_id)

        if not parsed_url.netloc:
            original_id = urljoin(BASE_URL, original_id)
            parsed_url = urlparse(original_id)

        path = parsed_url.path
        if path.startswith(PARSED_BASE_URL.path):
            path = path[len(PARSED_BASE_URL.path) :]

        new_id = f"/ssr{path}"
        item["@id"] = urljoin(BASE_URL, new_id)

        path_stripped = path.lstrip("/")
        if (
            path_stripped not in self.regenerated_urls
            and path_stripped not in self.failed_urls
        ):
            self.fetch_queue.append((original_id, path_stripped, depth + 1))

    def _process_fetch_queue(self):
        unique_fetches = {}
        for url, path, depth in self.fetch_queue:
            if path not in unique_fetches:
                unique_fetches[path] = (url, depth)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self._process_single_fetch, url, path, depth): path
                for path, (url, depth) in unique_fetches.items()
            }
            for future in as_completed(futures):
                path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing {path}: {e}"))

    def _process_single_fetch(self, url, path, depth):
        if path in self.regenerated_urls:
            self.stdout.write(
                self.style.WARNING(f"Skipping {url} as it has already been fetched")
            )
            return
        if path in self.failed_urls:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping {url} as it has already been tried and failed"
                )
            )
            return

        file_path = build_file_path(self.output_dir, path)

        model = get_model_from_path(path)
        model_depth = getattr(model._meta, "depth", None) if model else None
        response = get_response_from_view(
            path, depth=model_depth if model_depth is not None else None
        )
        if response and response.status_code == 200:
            content = extract_content_from_response(response)
            updated_content = self._update_ids_and_fetch_associated(content, depth)

            try:
                save_content_to_file(file_path, updated_content)
                self.regenerated_urls.add(path)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully fetched and saved associated content from {url} to {file_path}"
                    )
                )
            except IOError as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error saving associated content from {url}: {str(e)}"
                    )
                )
        else:
            self.failed_urls.add(path)
            status = response.status_code if response else "Unknown"
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to fetch associated content from {url}: HTTP {status}"
                )
            )


class Command(BaseCommand):
    help = "Generate static content for models having the static_version meta attribute set to 1/true"

    def handle(self, *args, **options):
        generator = StaticContentGenerator(self.stdout, self.style)
        generator.generate_content()
